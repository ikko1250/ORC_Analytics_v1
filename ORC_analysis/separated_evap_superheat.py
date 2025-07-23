# -*- coding: utf-8 -*-
"""Enhanced ORC performance model with separated evaporator and superheater analysis.

This module provides improved ORC analysis by separating evaporator and superheater
calculations for more accurate LMTD and exergy analysis.
"""

import numpy as np
import pandas as pd
import CoolProp.CoolProp as CP
from typing import Dict, Tuple, Optional
from .config import get_component_setting

def calculate_separated_evap_superheat(
    P_evap: float,
    T_turb_in: float,
    T_cond: float,
    eta_pump: float,
    eta_turb: float,
    *,
    fluid: str = "R245fa",
    m_orc: float = 5.0,
    T0: float = 298.15,
    P0: float = 101.325e3,
    T_htf_in: float = None,
    T_htf_out: float = None,
    superheat_K: float = 10.0
) -> Dict:
    """
    Calculate ORC performance with separated evaporator and superheater analysis.
    
    This function provides more accurate LMTD and exergy calculations by treating
    evaporator and superheater as separate components.
    
    Args:
        P_evap: Evaporation pressure [Pa]
        T_turb_in: Turbine inlet temperature [K]
        T_cond: Condensation temperature [K]
        eta_pump: Pump efficiency [-]
        eta_turb: Turbine efficiency [-]
        fluid: Working fluid name
        m_orc: Mass flow rate [kg/s]
        T0: Dead state temperature [K]
        P0: Dead state pressure [Pa]
        T_htf_in: Heat source inlet temperature [K]
        T_htf_out: Heat source outlet temperature [K]
        superheat_K: Superheat degree [K]
        
    Returns:
        Dictionary with separated component analysis results
    """
    
    # Constants
    J_PER_KJ = 1000.0
    PA_PER_KPA = 1000.0
    
    # Reference state properties
    h0 = CP.PropsSI("HMASS", "T", T0, "P", P0, fluid) / J_PER_KJ
    s0 = CP.PropsSI("SMASS", "T", T0, "P", P0, fluid) / J_PER_KJ
    
    # Determine saturation temperature from pressure
    T_sat = CP.PropsSI("T", "P", P_evap, "Q", 1, fluid)
    
    # Validate superheat consistency
    if abs(T_turb_in - (T_sat + superheat_K)) > 1.0:
        print(f"Warning: T_turb_in ({T_turb_in:.1f}K) != T_sat + superheat ({T_sat + superheat_K:.1f}K)")
    
    # Calculate thermodynamic states
    states = {}
    
    # State 1: Condenser outlet (saturated liquid)
    T1 = T_cond
    P1 = CP.PropsSI("P", "T", T1, "Q", 0, fluid)
    h1 = CP.PropsSI("HMASS", "T", T1, "Q", 0, fluid) / J_PER_KJ
    s1 = CP.PropsSI("SMASS", "T", T1, "Q", 0, fluid) / J_PER_KJ
    states["1"] = {"h": h1, "s": s1, "T": T1, "P": P1}
    
    # State 2: Pump outlet
    P2 = P_evap
    s2s = s1
    h2s = CP.PropsSI("HMASS", "P", P2, "S", s2s * J_PER_KJ, fluid) / J_PER_KJ
    h2 = h1 + (h2s - h1) / eta_pump
    T2 = CP.PropsSI("T", "P", P2, "H", h2 * J_PER_KJ, fluid)
    s2 = CP.PropsSI("SMASS", "P", P2, "H", h2 * J_PER_KJ, fluid) / J_PER_KJ
    states["2"] = {"h": h2, "s": s2, "T": T2, "P": P2}
    
    # State 2': Evaporator outlet (saturated vapor)
    T2_prime = T_sat
    P2_prime = P_evap
    h2_prime = CP.PropsSI("HMASS", "T", T2_prime, "Q", 1, fluid) / J_PER_KJ
    s2_prime = CP.PropsSI("SMASS", "T", T2_prime, "Q", 1, fluid) / J_PER_KJ
    states["2'"] = {"h": h2_prime, "s": s2_prime, "T": T2_prime, "P": P2_prime}
    
    # State 3: Superheater outlet (superheated vapor)
    T3 = T_turb_in
    P3 = P_evap
    h3 = CP.PropsSI("HMASS", "T", T3, "P", P3, fluid) / J_PER_KJ
    s3 = CP.PropsSI("SMASS", "T", T3, "P", P3, fluid) / J_PER_KJ
    states["3"] = {"h": h3, "s": s3, "T": T3, "P": P3}
    
    # State 4: Turbine outlet
    P4 = P1
    s4s = s3
    h4s = CP.PropsSI("HMASS", "P", P4, "S", s4s * J_PER_KJ, fluid) / J_PER_KJ
    h4 = h3 - eta_turb * (h3 - h4s)
    T4 = CP.PropsSI("T", "P", P4, "H", h4 * J_PER_KJ, fluid)
    s4 = CP.PropsSI("SMASS", "P", P4, "H", h4 * J_PER_KJ, fluid) / J_PER_KJ
    states["4"] = {"h": h4, "s": s4, "T": T4, "P": P4}
    
    # Calculate specific exergy for each state
    def specific_exergy(h, s, h0, s0, T0):
        return (h - h0) - T0 * (s - s0)
    
    psi = {k: specific_exergy(v["h"], v["s"], h0, s0, T0) for k, v in states.items()}
    
    # Heat quantities
    Q_evap = m_orc * (h2_prime - h2)  # Evaporation heat
    Q_superheat = m_orc * (h3 - h2_prime)  # Superheating heat
    Q_total = Q_evap + Q_superheat
    
    # Component analysis
    results = {}
    
    # === Evaporator Analysis ===
    if T_htf_in is not None and T_htf_out is not None:
        # Estimate heat source temperature at evaporator/superheater boundary
        Q_ratio_evap = Q_evap / Q_total
        T_htf_mid = T_htf_in - Q_ratio_evap * (T_htf_in - T_htf_out)
        
        # Evaporator LMTD (T_htf_in -> T_htf_mid, T2 -> T2')
        try:
            dT_lm_evap = lmtd_counter_current(T_htf_in, T_htf_mid, T2, T2_prime)
            lmtd_evap_valid = True
        except ValueError as e:
            dT_lm_evap = np.nan
            lmtd_evap_valid = False
            print(f"Evaporator LMTD calculation failed: {e}")
        
        T_hot_avg_evap = 0.5 * (T_htf_in + T_htf_mid)
    else:
        # Fallback calculation
        dT_lm_evap = T2_prime - T2
        T_hot_avg_evap = 0.5 * (T2 + T2_prime) + 50  # Assume 50K temperature difference
        lmtd_evap_valid = True
        T_htf_mid = None
    
    # Evaporator exergy analysis
    def exergy_of_heat(Qdot, T_surf, T0):
        if T_surf <= 0 or Qdot == 0:
            return 0.0
        return (1.0 - T0 / T_surf) * Qdot
    
    E_heat_evap = exergy_of_heat(Q_evap, T_hot_avg_evap, T0)
    E_dest_evap = E_heat_evap - m_orc * (psi["2'"] - psi["2"])
    
    results["Evaporator"] = {
        "Q [kW]": Q_evap,
        "E_heat [kW]": E_heat_evap,
        "E_dest [kW]": E_dest_evap,
        "ε [-]": m_orc * (psi["2'"] - psi["2"]) / E_heat_evap if E_heat_evap else np.nan,
        "ΔT_lm [K]": dT_lm_evap,
        "T_hot_avg [K]": T_hot_avg_evap,
        "LMTD_valid": lmtd_evap_valid,
    }
    
    # === Superheater Analysis ===
    if T_htf_in is not None and T_htf_out is not None and T_htf_mid is not None:
        # Superheater LMTD (T_htf_mid -> T_htf_out, T2' -> T3)
        try:
            dT_lm_superheat = lmtd_counter_current(T_htf_mid, T_htf_out, T2_prime, T3)
            lmtd_superheat_valid = True
        except ValueError as e:
            dT_lm_superheat = np.nan
            lmtd_superheat_valid = False
            print(f"Superheater LMTD calculation failed: {e}")
        
        T_hot_avg_superheat = 0.5 * (T_htf_mid + T_htf_out)
    else:
        # Fallback calculation
        dT_lm_superheat = T3 - T2_prime
        T_hot_avg_superheat = 0.5 * (T2_prime + T3) + 30  # Assume 30K temperature difference
        lmtd_superheat_valid = True
    
    # Superheater exergy analysis
    E_heat_superheat = exergy_of_heat(Q_superheat, T_hot_avg_superheat, T0)
    E_dest_superheat = E_heat_superheat - m_orc * (psi["3"] - psi["2'"])
    
    results["Superheater"] = {
        "Q [kW]": Q_superheat,
        "E_heat [kW]": E_heat_superheat,
        "E_dest [kW]": E_dest_superheat,
        "ε [-]": m_orc * (psi["3"] - psi["2'"]) / E_heat_superheat if E_heat_superheat else np.nan,
        "ΔT_lm [K]": dT_lm_superheat,
        "T_hot_avg [K]": T_hot_avg_superheat,
        "LMTD_valid": lmtd_superheat_valid,
    }
    
    # === Combined Evaporator+Superheater (for comparison) ===
    if T_htf_in is not None and T_htf_out is not None:
        try:
            dT_lm_combined = lmtd_counter_current(T_htf_in, T_htf_out, T2, T3)
            lmtd_combined_valid = True
        except ValueError as e:
            dT_lm_combined = np.nan
            lmtd_combined_valid = False
    else:
        dT_lm_combined = T3 - T2
        lmtd_combined_valid = True
    
    T_hot_avg_combined = 0.5 * (T_htf_in + T_htf_out) if T_htf_in and T_htf_out else T_hot_avg_evap
    E_heat_combined = exergy_of_heat(Q_total, T_hot_avg_combined, T0)
    E_dest_combined = E_heat_combined - m_orc * (psi["3"] - psi["2"])
    
    results["Combined_Evap_Superheat"] = {
        "Q [kW]": Q_total,
        "E_heat [kW]": E_heat_combined,
        "E_dest [kW]": E_dest_combined,
        "ε [-]": m_orc * (psi["3"] - psi["2"]) / E_heat_combined if E_heat_combined else np.nan,
        "ΔT_lm [K]": dT_lm_combined,
        "T_hot_avg [K]": T_hot_avg_combined,
        "LMTD_valid": lmtd_combined_valid,
    }
    
    # === Other components (pump, turbine, condenser) ===
    # Pump
    W_p = m_orc * (h2 - h1)
    W_p_rev = m_orc * (psi["2"] - psi["1"])
    results["Pump"] = {
        "W [kW]": W_p,
        "E_dest [kW]": W_p - W_p_rev,
        "η_exergy [-]": W_p_rev / W_p if W_p else np.nan,
    }
    
    # Turbine
    W_t = m_orc * (h3 - h4)
    W_t_rev = m_orc * (psi["3"] - psi["4"])
    results["Turbine"] = {
        "W [kW]": W_t,
        "E_dest [kW]": W_t_rev - W_t,
        "η_exergy [-]": W_t / W_t_rev if W_t_rev else np.nan,
    }
    
    # Condenser
    Q_c = m_orc * (h1 - h4)
    T_cold_avg = 0.5 * (T4 + T1)
    E_heat_rejected = exergy_of_heat(abs(Q_c), T_cold_avg, T0)
    E_dest_condenser = m_orc * (psi["4"] - psi["1"]) - E_heat_rejected
    
    results["Condenser"] = {
        "Q [kW]": Q_c,
        "E_heat_rejected [kW]": E_heat_rejected,
        "E_dest [kW]": E_dest_condenser,
        "T_cold_avg [K]": T_cold_avg,
    }
    
    # === Summary and comparison ===
    # Area-weighted average LMTD
    if lmtd_evap_valid and lmtd_superheat_valid and not np.isnan(dT_lm_evap) and not np.isnan(dT_lm_superheat):
        UA_evap = Q_evap / dT_lm_evap
        UA_superheat = Q_superheat / dT_lm_superheat
        UA_total = UA_evap + UA_superheat
        dT_lm_area_weighted = Q_total / UA_total if UA_total > 0 else np.nan
    else:
        dT_lm_area_weighted = np.nan
    
    # Energy-weighted average temperature
    T_hot_avg_energy_weighted = (Q_evap * T_hot_avg_evap + Q_superheat * T_hot_avg_superheat) / Q_total
    
    # Errors compared to combined calculation
    lmtd_error = ((dT_lm_combined - dT_lm_area_weighted) / dT_lm_area_weighted * 100) if not np.isnan(dT_lm_area_weighted) and not np.isnan(dT_lm_combined) else np.nan
    temp_error = ((T_hot_avg_combined - T_hot_avg_energy_weighted) / T_hot_avg_energy_weighted * 100) if T_hot_avg_energy_weighted > 0 else np.nan
    
    # Exergy comparison
    E_separated_total = E_heat_evap + E_heat_superheat
    exergy_error = ((E_heat_combined - E_separated_total) / E_separated_total * 100) if E_separated_total > 0 else np.nan
    
    summary = {
        "Heat_Distribution": {
            "Q_evap [kW]": Q_evap,
            "Q_superheat [kW]": Q_superheat, 
            "Q_evap_ratio [%]": Q_evap / Q_total * 100,
            "Q_superheat_ratio [%]": Q_superheat / Q_total * 100,
        },
        "LMTD_Analysis": {
            "dT_lm_evap [K]": dT_lm_evap,
            "dT_lm_superheat [K]": dT_lm_superheat,
            "dT_lm_area_weighted [K]": dT_lm_area_weighted,
            "dT_lm_combined [K]": dT_lm_combined,
            "LMTD_error [%]": lmtd_error,
        },
        "Temperature_Analysis": {
            "T_hot_avg_evap [K]": T_hot_avg_evap,
            "T_hot_avg_superheat [K]": T_hot_avg_superheat,
            "T_hot_avg_energy_weighted [K]": T_hot_avg_energy_weighted,
            "T_hot_avg_combined [K]": T_hot_avg_combined,
            "Temp_error [%]": temp_error,
        },
        "Exergy_Analysis": {
            "E_heat_evap [kW]": E_heat_evap,
            "E_heat_superheat [kW]": E_heat_superheat,
            "E_heat_separated_total [kW]": E_separated_total,
            "E_heat_combined [kW]": E_heat_combined,
            "Exergy_error [%]": exergy_error,
        }
    }
    
    return {
        "states": states,
        "psi": psi,
        "components": results,
        "summary": summary,
    }


def lmtd_counter_current(T_hot_in, T_hot_out, T_cold_in, T_cold_out):
    """Calculate logarithmic mean temperature difference for counter-current flow."""
    dT1 = T_hot_in - T_cold_out   # High-end approach
    dT2 = T_hot_out - T_cold_in   # Low-end approach
    
    # Check for temperature cross or invalid profile
    if dT1 <= 0 or dT2 <= 0:
        raise ValueError(
            f"Temperature cross or invalid profile detected. "
            f"dT1 = {dT1:.2f} K, dT2 = {dT2:.2f} K. "
            f"T_hot: {T_hot_in:.1f} -> {T_hot_out:.1f} K, "
            f"T_cold: {T_cold_in:.1f} -> {T_cold_out:.1f} K"
        )
    
    # Handle case where temperature differences are nearly equal
    if abs(dT1 - dT2) < 1e-9:
        return dT1
    
    return (dT1 - dT2) / np.log(dT1 / dT2)
