"""
ORC_Economic_Assessment.py ─────────────────────────────────────────────

Economic evaluation companion to *ORC_Analysis.py*
---------------------------------------------------
This script couples the thermodynamic model provided in ``ORC_Analysis`` with
empirical cost correlations (Tables 5–7 of the reference paper) in order to
estimate:
  • Purchased‑equipment cost (PEC) for major ORC components
  • Total capital investment and annualised capital charge
  • Annual operation & maintenance (O&M) cost via a maintenance factor φ
  • Unit electricity cost C_elec   [$/kWh]
  • Simple pay‑back period PB      [year]

Assumptions & data source
─────────────────────────
All cost equations, heat‑transfer coefficients U, and economic factors come
directly from the images supplied by the user (cf. Tables 5–7 and Eqs. 9–15).
Where data are missing (e.g. heat‑duty for the super‑heater or regenerator in
the simplified thermodynamic model), the script either skips the item or lets
the user supply a value through ``extra_duties``.

The default numbers reproduce the paper’s example:
  • Interest rate                  i  = 0.20   (20 %)
  • Lifetime of the project        N  = 20 yr
  • Annual operating hours         n  = 8000 h
  • Maintenance factor             φ  = 1.06   (dimensionless – $ ×10⁶ in paper)
  • Electricity sale price         c_elec = 0.07 $/kWh

Usage (stand‑alone) ─────────────────────────────────────────────────────
$ python ORC_Economic_Assessment.py          # runs the demo case embedded below

Programmatic use ─────────────────────────────────────────────────────────
>>> from ORC_Economic_Assessment import evaluate_orc_economics
>>> econ = evaluate_orc_economics(P_evap=15e5, T_cond=308.15, T_turb_in=450.0,
...                               eta_pump=0.75, eta_turb=0.80,
...                               m_orc=5.0)
>>> print(econ["summary"])

Dependencies
────────────
• ORC_Analysis.py (must be importable – keep both scripts in the same folder)
• NumPy, Pandas, CoolProp (transitively via ORC_Analysis)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

# ─── import the thermodynamic routine ───────────────────────────────────
try:
    from ORC_Analysis import calculate_orc_performance
except ImportError as exc:  # pragma: no cover
    raise SystemExit("❌ Could not import ORC_Analysis.py – keep the file in the "
                    "same directory or adjust PYTHONPATH.") from exc

# ─── Constants from Tables 6 & 7 ─────────────────────────────────────────
U_VALUES = {
    "Evaporator": 0.6,   # kW/m²·K  (Evaporator_ORC)
    "Condenser":  0.5,   # kW/m²·K
    # components below depend on design — user may supply via extra_duties
    "Superheater": 0.6,
    "Regenerator": 0.6,
    "Preheater":  0.6,
}

ANNUAL_HOURS = 8000        # h        (n)
INTEREST_RATE = 0.20       # –        (i)
LIFETIME_YR   = 20         # year     (N)
MAINT_FACTOR  = 1.06       # φ        (dimensionless additive term)
ELEC_PRICE    = 0.07       # $/kWh    (c_pric)

# ─── Helper functions ----------------------------------------------------

def capital_recovery_factor(i: float, N: int) -> float:
    """CRF = i(1+i)^N / [ (1+i)^N − 1 ]"""
    numerator = i * (1 + i) ** N
    denominator = (1 + i) ** N - 1
    return numerator / denominator


def area_from_duty(Q_kW: float, U: float, lmtd_K: float) -> float:
    """Return heat‑transfer area *A* [m²] via Eq.(9): A = Q̇ / (U·LMTD)."""
    if U * lmtd_K <= 0:
        return 0.0
    return Q_kW / (U * lmtd_K)


# ─── Component-specific PEC calculation functions ───────────────────────
# These functions calculate Purchased Equipment Cost (PEC) based on area (m²)
# for heat exchangers, or power (kW) for turbine and pump.
# Formulas from Table 5 of the reference paper.

def _calculate_pec_heat_exchanger_common(area: float) -> float:
    """PEC [$] for Evaporator, Superheater, Preheater.
    Formula: 130 * (Area_m2 / 0.093)^0.78
    0.093は㎡ to  ft²の換算係数
    """
    if area <= 0:  # Avoid math errors for non-existent or zero-area components
        return 0.0
    return 130.0 * (area / 0.093) ** 0.78

def _calculate_pec_regenerator(area: float) -> float:
    """PEC [$] for Regenerator.
    Formula: 2681 * Area_m2^0.59
    """
    if area <= 0:
        return 0.0
    return 2681.0 * area ** 0.59

def _calculate_pec_condenser(area: float) -> float:
    """PEC [$] for Condenser.
    Formula: 1773 * Area_m2^0.80 (approx.)
    """
    if area <= 0:
        return 0.0
    return 1773.0 * area ** 0.80

def _calculate_pec_turbine(W_kW: float) -> float:
    """PEC [$] for Turbine.
    Formula: 6000 * Power_kW^0.70
    """
    if W_kW <= 0: # Turbine power should be positive (produced)
        return 0.0
    return 6000.0 * W_kW ** 0.70

def _calculate_pec_pump(W_kW: float) -> float:
    """PEC [$] for Pump.
    Formula: 3540 * Power_kW^0.70
    """
    # Pump power (W_p) from thermo model is positive (work input)
    if W_kW <= 0:
        return 0.0
    return 3540.0 * W_kW ** 0.70



# ─── Public API ──────────────────────────────────────────────────────────

def evaluate_orc_economics(
    *,
    P_evap: float,
    T_turb_in: float,
    T_cond: float,
    eta_pump: float,
    eta_turb: float,
    m_orc: float,
    T0: float = 298.15,
    P0: float = 101.325e3,
    extra_duties: Optional[Dict[str, Tuple[float, float]]] = None,
    c_elec: float = ELEC_PRICE,
    φ: float = MAINT_FACTOR,
    i_rate: float = INTEREST_RATE,
    project_life: int = LIFETIME_YR,
    annual_hours: int = ANNUAL_HOURS,
) -> Dict[str, pd.DataFrame | float | dict]:
    """Run a combined **thermo‑economic** evaluation for a single ORC design.

    Parameters
    ----------
    P_evap, T_turb_in, T_cond, eta_pump, eta_turb, m_orc
        As described in ORC_Analysis.calculate_orc_performance().
    extra_duties : dict[str, (Q_kW, lmtd_K)], optional
        Heat duty and LMTD for components **not** returned by the simplified
        model (e.g. Superheater). Keys must match those in *U_VALUES*.

    Returns
    -------
    dict with three entries:
        ``"component_costs"``  → *pd.DataFrame*
        ``"summary"``          → *pd.Series* (scalar KPIs)
        ``"thermo"``           → k‑v mapping returned by ORC_Analysis
    """

    # 1) Run thermodynamic model ––––––––––––––––––––––––––––––––––––––––
    psi_df, comp_df, kpi = calculate_orc_performance(
        P_evap,
        T_turb_in,
        T_cond,
        eta_pump,
        eta_turb,
        m_orc=m_orc,
        T0=T0,
        P0=P0,
        # pass‑through HTF info only for Evaporator dT_lm calc (ignored here)
    )

    # 2) Assemble heat duties & LMTDs ––––––––––––––––––––––––––––––––––––
    duties: Dict[str, Tuple[float, float]] = {
        "Evaporator": (
            comp_df.loc["Evaporator", "Q [kW]"],
            comp_df.loc["Evaporator", "ΔT_lm [K]"] or 1.0,  # avoid div/0
        ),
        "Condenser": (
            abs(comp_df.loc["Condenser", "Q [kW]"]),  # magnitude
            10.0,  # missing in thermo‑model → placeholder LMTD [K]
        ),
    }
    if extra_duties:
        duties.update(extra_duties)

    # 3) Purchased‑equipment cost per component –––––––––––––––––––––––––
    cost_rows = {}

    # Dispatch dictionary for PEC calculation functions
    # Maps component name to its specific PEC calculation function.
    # Heat exchanger functions expect area (m²), power component functions expect power (kW).
    COMPONENT_PEC_CALCULATORS = {
        "Evaporator": _calculate_pec_heat_exchanger_common,
        "Superheater": _calculate_pec_heat_exchanger_common,
        "Preheater": _calculate_pec_heat_exchanger_common,
        "Regenerator": _calculate_pec_regenerator,
        "Condenser": _calculate_pec_condenser,
        "Turbine": _calculate_pec_turbine,
        "Pump": _calculate_pec_pump,
    }

    # Calculate PEC for Heat Exchangers
    # `duties` contains "Evaporator", "Condenser", and any valid `extra_duties`
    for comp_name, (Q_kW, lmtd_K) in duties.items():
        if comp_name in U_VALUES and comp_name in COMPONENT_PEC_CALCULATORS:
            U_val = U_VALUES[comp_name]
            area = area_from_duty(Q_kW, U_val, lmtd_K)
            
            pec_func = COMPONENT_PEC_CALCULATORS[comp_name]
            pec = pec_func(area) 
            
            cost_rows[comp_name] = {
                "Q [kW]": Q_kW,
                "A [m²]": area,
                "LMTD [K]": lmtd_K,
                "U [kW/m²K]": U_val,
                "PEC [$]": pec,
            }

    # Calculate PEC for Power Components (Turbine, Pump)
    # Turbine
    W_t = comp_df.loc["Turbine", "W [kW]"]
    if "Turbine" in COMPONENT_PEC_CALCULATORS:
        pec_func_turb = COMPONENT_PEC_CALCULATORS["Turbine"]
        pec_turb = pec_func_turb(W_t)
        cost_rows["Turbine"] = {
            "W [kW]": W_t,
            "PEC [$]": pec_turb
        }

    # Pump
    W_p = comp_df.loc["Pump", "W [kW]"]
    if "Pump" in COMPONENT_PEC_CALCULATORS:
        pec_func_pump = COMPONENT_PEC_CALCULATORS["Pump"]
        pec_pump = pec_func_pump(W_p)
        cost_rows["Pump"] = {
            "W [kW]": W_p,
            "PEC [$]": pec_pump
        }

    standard_columns = ["Q [kW]", "LMTD [K]", "U [kW/m²K]", "A [m²]", "W [kW]", "PEC [$]"]
    cost_df = pd.DataFrame.from_dict(cost_rows, orient='index')
    cost_df = cost_df.reindex(columns=standard_columns).fillna(0.0)

    # 4) Aggregate economics ––––––––––––––––––––––––––––––––––––––––––––
    PEC_total = cost_df["PEC [$]"].sum()
    CRF = capital_recovery_factor(i_rate, project_life)
    W_net = kpi["W_net [kW]"]

    # Eq.(14) unit electricity cost – $/kWh
    c_unit = (CRF * PEC_total + φ) / (W_net * annual_hours)

    # Simple pay‑back: PEC / annual gross revenue (neglecting O&M)
    annual_revenue = W_net * annual_hours * c_elec
    PB_simple = PEC_total / (annual_revenue - φ)

    summary = pd.Series(
        {
            "PEC_total [$]": PEC_total,
            "CRF [-]": CRF,
            "Unit elec cost [$/kWh]": c_unit,
            "Simple PB [yr]": PB_simple,
        }
    )

    return {
        "component_costs": cost_df,
        "summary": summary,
        "thermo": {"states": psi_df, "components": comp_df, "kpi": kpi},
    }


# ─── Demonstration when executed directly ───────────────────────────────
if __name__ == "__main__":
    res = evaluate_orc_economics(
        P_evap=15.0e5,   # Pa
        T_turb_in=450.0, # K
        T_cond=308.15,   # K
        eta_pump=0.75,
        eta_turb=0.80,
        m_orc=5.0,
        # extra heat‑exchanger duties (kW, dT_LM[K]) – illustrative only
        extra_duties={
            "Superheater": (200.0, 20.0),
            "Regenerator": (150.0, 15.0),
        },
    )

    pd.options.display.max_columns = 10
    print("\nPurchased‑equipment costs (PEC):\n", res["component_costs"].round(2))
    print("\nEconomic summary:\n", res["summary"].round(4))
