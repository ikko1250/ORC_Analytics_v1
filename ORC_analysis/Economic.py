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


def _pec_evap(area: float) -> float:        # Z = 130(A/0.093)^0.78
    return 130.0 * (area / 0.093) ** 0.78

def _pec_superheater(area: float) -> float:  # same corr. as evap.
    return 130.0 * (area / 0.093) ** 0.78

def _pec_preheater(area: float) -> float:    # same corr. as evap.
    return 130.0 * (area / 0.093) ** 0.78

def _pec_regenerator(area: float) -> float:  # Z = 2681 A^0.59
    return 2681.0 * area ** 0.59

def _pec_condenser(area: float) -> float:    # Z = 1773 A^0.8 (approx.)
    return 1773.0 * area ** 0.80

def _pec_turbine(W_kW: float) -> float:      # Z = 6000 W^0.7
    return 6000.0 * W_kW ** 0.70

def _pec_pump(W_kW: float) -> float:         # Z = 3540 W^0.7
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

    # Evaporator
    Q_e, dT_e = duties.get("Evaporator", (0.0, 1.0))
    A_e = area_from_duty(Q_e, U_VALUES["Evaporator"], dT_e)
    cost_rows["Evaporator"] = {
        "Q [kW]": Q_e,
        "A [m²]": A_e,
        "PEC [$]": _pec_evap(A_e),
    }

    # Condenser
    Q_c, dT_c = duties.get("Condenser", (0.0, 1.0))
    A_c = area_from_duty(Q_c, U_VALUES["Condenser"], dT_c)
    cost_rows["Condenser"] = {
        "Q [kW]": Q_c,
        "A [m²]": A_c,
        "PEC [$]": _pec_condenser(A_c),
    }

    # Turbine & Pump (from power)
    W_t = comp_df.loc["Turbine", "W [kW]"]
    W_p = comp_df.loc["Pump", "W [kW]"]
    cost_rows["Turbine"] = {"W [kW]": W_t, "PEC [$]": _pec_turbine(W_t)}
    cost_rows["Pump"]    = {"W [kW]": W_p, "PEC [$]": _pec_pump(W_p)}

    # Optional heat exchangers supplied by user – iterate to compute PECs
    for comp, (Q_kW, lmtd) in duties.items():
        if comp in ("Evaporator", "Condenser"):
            continue
        if comp not in U_VALUES:
            continue
        A = area_from_duty(Q_kW, U_VALUES[comp], lmtd)
        if comp == "Superheater":
            pec = _pec_superheater(A)
        elif comp == "Regenerator":
            pec = _pec_regenerator(A)
        elif comp == "Preheater":
            pec = _pec_preheater(A)
        else:
            continue
        cost_rows[comp] = {"Q [kW]": Q_kW, "A [m²]": A, "PEC [$]": pec}

    cost_df = pd.DataFrame(cost_rows).T.fillna(0.0)

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

