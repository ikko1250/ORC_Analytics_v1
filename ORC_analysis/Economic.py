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

import logging
import math
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

# Try relative import first, fallback to absolute import for direct execution
try:
    from .config import get_component_setting
except ImportError:
    from config import get_component_setting

# Setup logging
logger = logging.getLogger(__name__)

# ─── import the thermodynamic routine ───────────────────────────────────
try:
    try:
        from .ORC_Analysis import calculate_orc_performance
    except ImportError:
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

CURRENT_CEPCI = 799.5      # Chemical Engineering Plant Cost Index (reference year 2023)
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

def _calculate_pec_evaporator(area_m2: float) -> float:
    """PEC [$] for Horizontal Tube Evaporator.
    Formula based on Seider et al. (2016), Table 22.4, item (d).
    Cost = min_cost * (area_ft2 / min_area_ft2) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    """
    if area_m2 <= 0:  # Avoid math errors for non-existent or zero-area components
        return 0.0

    min_cost = 52861.0
    min_area_ft2 = 100.0
    scaling_factor = 0.53
    listed_CEPCI = 567.0  # CEPCI in 2016, when Seider et al. book was published
    m2_to_ft2_conversion_factor = 10.7639

    area_ft2 = area_m2 * m2_to_ft2_conversion_factor

    cost = min_cost * (area_ft2 / min_area_ft2) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    return cost

def _calculate_pec_hot_water_heater(power_kW: float) -> float:
    """PEC [$] for Hot Water Heater (used for Preheater and Superheater).
    Formula based on internal data for Hot Water Heater.
    Cost = min_cost * (power_kW / min_power_kW) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    """
    if power_kW <= 0:
        return 0.0

    min_cost = 37868.0
    min_power_kW = 650.0
    scaling_factor = 0.74
    listed_CEPCI = 542.0  # CEPCI for the base cost year of the Hot Water Heater

    cost = min_cost * (power_kW / min_power_kW) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    return cost

def _calculate_pec_heat_exchanger_common(area: float) -> float:
    """PEC [$] for generic heat exchangers (currently unused).
    Original Formula: 130 * (Area_m2 / 0.093)^0.78
    0.093は㎡ to  ft²の換算係数
    This function is currently not mapped to any component in COMPONENT_PEC_CALCULATORS.
    """
    if area <= 0:  # Avoid math errors for non-existent or zero-area components
        return 0.0
    # logger.warning("_calculate_pec_heat_exchanger_common is called but might be deprecated.")
    return 130.0 * (area / 0.093) ** 0.78

def _calculate_pec_regenerator(area: float) -> float:
    """PEC [$] for Regenerator.
    Formula: 2681 * Area_m2^0.59
    """
    if area <= 0:
        return 0.0
    return 2681.0 * area ** 0.59

def _calculate_pec_condenser_new(area_m2: float) -> float:
    """PEC [$] for Condenser.
    Formula based on Sinnott & Towler (2020), "Chemical Engineering Design", 6th Ed., Table 6.1.
    Cost = min_cost * (area_m2 / min_area_m2) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    """
    if area_m2 <= 0:
        return 0.0

    min_cost = 24729.0       # Cost for min_area_m2 in base year
    min_area_m2 = 10.0       # Minimum area for base cost
    scaling_factor = 0.46    # Cost exponent
    listed_CEPCI = 509.7     # CEPCI in Q4 2008 (Sinnott & Towler reference year for this cost)

    cost = min_cost * (area_m2 / min_area_m2) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    return cost

def _calculate_pec_condenser(mass_flow_rate_kg_s: float) -> float:
    """PEC [$] for Condenser, based on mass flow rate at condenser inlet.
    Formula: Placeholder - USER MUST PROVIDE THE CORRECT FORMULA.
    (This function is currently not used for the primary 'Condenser' component
     after changes for area-based calculation via _calculate_pec_condenser_new)
    """
    if mass_flow_rate_kg_s <= 0:
        return 0.0

    return 1773.0 * mass_flow_rate_kg_s ** 0.8

def _calculate_pec_turbine(W_kW: float) -> float:
    """PEC [$] for Turbine.
    New formula based on Woods 2007, Steam Turbine Noncondensing.
    Cost = min_cost * (W_kW / min_power_kW) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    """
    if W_kW <= 0:  # Turbine power should be positive (produced)
        return 0.0

    min_cost = 13241.0
    min_power_kW = 7.0
    scaling_factor = 0.51
    listed_CEPCI = 1000.0  # CEPCI for the base cost year (Woods 2007)

    cost = min_cost * (W_kW / min_power_kW) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    return cost

def _calculate_pec_pump(W_kW: float) -> float:
    """PEC [$] for Pump.
    New formula based on Sinnott & Towler 2020, Single Stage Centrifugal Pump, Table 6.1.
    Cost = min_cost * (W_kW / min_power_kW) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    min_power_kW = 1.0 kW is an assumed reference for the given min_cost.
    """
    # Pump power (W_p) from thermo model is positive (work input)
    if W_kW <= 0:
        return 0.0

    min_cost = 6948.0
    min_power_kW = 1.0  # Assumed reference power for the base cost from S&T Table 6.1
    scaling_factor = 0.19
    listed_CEPCI = 509.7  # CEPCI in Q4 2008 (Sinnott & Towler reference year for this cost)

    cost = min_cost * (W_kW / min_power_kW) ** scaling_factor * (CURRENT_CEPCI / listed_CEPCI)
    return cost



# ─── Public API ──────────────────────────────────────────────────────────

def check_orc_toggle_consistency():
    """ORC_Analysis.pyのトグル状態とconfig.pyの設定値の整合性を1回だけチェックする。"""
    try:
        from .ORC_Analysis import calculate_orc_performance_from_heat_source
    except ImportError:
        from ORC_Analysis import calculate_orc_performance_from_heat_source
    analysis_flags = {}
    try:
        dummy_result = calculate_orc_performance_from_heat_source(
            T_htf_in=400.0, Vdot_htf=1.0, T_cond=300.0, eta_pump=0.7, eta_turb=0.8
        )
        if dummy_result is not None:
            analysis_flags['use_preheater'] = dummy_result.get('use_preheater', None)
            analysis_flags['use_superheater'] = dummy_result.get('use_superheater', None)
    except (ImportError, AttributeError, ValueError, RuntimeError) as e:
        logger.debug(f"Could not perform consistency check: {e}")
        return
    config_preheater = get_component_setting('use_preheater', False)
    config_superheater = get_component_setting('use_superheater', False)
    if (analysis_flags.get('use_preheater') is not None and
        analysis_flags['use_preheater'] != config_preheater):
        logger.warning("ORC_Analysis.pyとEconomic.pyでuse_preheaterの設定が一致していません！")
    if (analysis_flags.get('use_superheater') is not None and
        analysis_flags['use_superheater'] != config_superheater):
        logger.warning("ORC_Analysis.pyとEconomic.pyでuse_superheaterの設定が一致していません！")

# 一度だけ整合性チェックを行うためのフラグ
# _consistency_checked = False # このグローバル変数は現在使用されていません

def _check_consistency_once():
    # global _consistency_checked # この行は不要です。関数属性を使用しています。
    if not getattr(_check_consistency_once, '_consistency_checked', False):
        # このチェックは、ORC_Analysis.py が config.py の設定を正しく参照していることを
        # 確認することを目的としています。通常、両者は同じ config.py を参照するため一致しますが、
        # 開発中の変更等で意図せず不整合が生じる可能性を警告するために実行されます。
        check_orc_toggle_consistency()
        _check_consistency_once._consistency_checked = True

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
    """Run a combined **thermo‑economic** evaluation for a single ORC design."""

    _check_consistency_once()

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
        "Evaporator": _calculate_pec_evaporator,
        "Superheater": _calculate_pec_hot_water_heater, # Updated
        "Preheater": _calculate_pec_hot_water_heater,  # Updated
        "Regenerator": _calculate_pec_regenerator,
        "Condenser": _calculate_pec_condenser_new,
        "Turbine": _calculate_pec_turbine,
        "Pump": _calculate_pec_pump,
    }

    # Calculate PEC for Heat Exchangers
    # `duties` contains "Evaporator", "Condenser", and any valid `extra_duties`
    for comp_name, (Q_kW, lmtd_K) in duties.items():
        # Preheater/Superheaterのトグル判定
        if comp_name == "Preheater" and not get_component_setting('use_preheater', False):
            pec = 0.0
            area = 0.0 # Still calculate area for reporting if needed, or set to 0
            U_val = U_VALUES.get(comp_name, 0.0)
        elif comp_name == "Superheater" and not get_component_setting('use_superheater', False):
            pec = 0.0
            area = 0.0 # Still calculate area for reporting if needed, or set to 0
            U_val = U_VALUES.get(comp_name, 0.0)
        elif comp_name in U_VALUES and comp_name in COMPONENT_PEC_CALCULATORS:
            U_val = U_VALUES[comp_name]
            # Area is calculated for all HXs for reporting purposes.
            area = area_from_duty(Q_kW, U_val, lmtd_K)
            pec_func = COMPONENT_PEC_CALCULATORS[comp_name]
            
            component_specific_data = {} # Initialize for all components

            # Preheater and Superheater use power_kW (Q_kW) for PEC.
            # Other HXs (Evaporator, Condenser, Regenerator) use area_m2 for PEC.
            if comp_name in ["Superheater", "Preheater"]:
                pec = pec_func(Q_kW) # Pass Q_kW as power_kW
            else: # Evaporator, Condenser, Regenerator
                pec = pec_func(area) # Pass area_m2

        else:
            logger.debug(f"Component {comp_name} skipped or handled differently in PEC calculation loop.")
            continue # Skip if no U_VALUE or calculator (e.g. if it's not a HX handled here)
        
        cost_rows[comp_name] = {
            "Q [kW]": Q_kW,
            "A [m²]": area, # Area is now consistently calculated and stored
            "LMTD [K]": lmtd_K,
            "U [kW/m²K]": U_val,
            "PEC [$]": pec,
            **component_specific_data # This will be empty for Condenser now
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

    standard_columns = ["Q [kW]", "LMTD [K]", "U [kW/m²K]", "A [m²]", "W [kW]", "m_orc_for_PEC [kg/s]", "PEC [$]"]
    cost_df = pd.DataFrame.from_dict(cost_rows, orient='index')
    # Fill NaN with 0.0 for numeric columns, and empty string for potential object/string columns if any were added.
    # For now, all these standard_columns are expected to be numeric or can be filled with 0.0 if absent for a component.
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
        # extra heat‑exchangers duties (kW, dT_LM[K]) – illustrative only
        extra_duties={
            "Superheater": (200.0, 20.0),
            "Regenerator": (150.0, 15.0),
        },
    )

    pd.options.display.max_columns = 10
    print("\nPurchased‑equipment costs (PEC):\n", res["component_costs"].round(2))
    print("\nEconomic summary:\n", res["summary"].round(4))
