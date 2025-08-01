# -*- coding: utf-8 -*-
"""Enhanced ORC performance model with LMTD-based evaporator exergy evaluation.

This script models the performance of an Organic Rankine Cycle (ORC).
It includes:
  - Calculation of thermodynamic states of the working fluid.
  - Performance analysis of individual components (pump, evaporator, turbine, condenser).
  - Calculation of overall cycle Key Performance Indicators (KPIs).
  - Logarithmic Mean Temperature Difference (LMTD) for the evaporator.
  - Exergy analysis for components and the overall cycle.
  - A wrapper function to calculate ORC performance based on a heat source.

"""

# ---------------------------------------------------------------------------
# 1. Imports & global constants
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd
import CoolProp.CoolProp as CP  # Thermophysical properties
from .config import get_component_setting
from .heat_source import get_heat_source_profile

DEFAULT_T0 = 298.15            # Dead‑state temperature [K] (25 °C)
DEFAULT_FLUID = "R245fa"       # Working fluid (HFC‑245fa)
DEFAULT_P0 = 101.325e3         # Dead‑state pressure [Pa] (1 atm)

J_PER_KJ = 1000.0              # Conversion factor from Joules to kiloJoules
PA_PER_KPA = 1000.0            # Conversion factor from Pascals to kiloPascals
PA_PER_BAR = 100000.0          # Conversion factor from Pascals to Bar

# ---------------------------------------------------------------------------
# 2. Utility functions
# ---------------------------------------------------------------------------

def lmtd_counter_current(T_hot_in, T_hot_out, T_cold_in, T_cold_out):
    """Return logarithmic‑mean ΔT for a *counter‑current* heat exchanger."""
    dT1 = T_hot_in  - T_cold_out  # high‑end approach
    dT2 = T_hot_out - T_cold_in   # low‑end approach

    # --- ADDED: Temperature cross or invalid profile check ---
    if dT1 <= 0 or dT2 <= 0:
        raise ValueError(
            f"Temperature cross or invalid profile detected in LMTD calculation. "
            f"dT1 = {dT1:.2f} K, dT2 = {dT2:.2f} K. "
            f"Inputs: T_hot_in={T_hot_in:.2f} K, T_hot_out={T_hot_out:.2f} K, "
            f"T_cold_in={T_cold_in:.2f} K, T_cold_out={T_cold_out:.2f} K"
        )
    # -----------------------------------------------------------

    # Existing guard against division by zero when dT1 is close to dT2
    if abs(dT1 - dT2) < 1e-9:
        return dT1 # or dT2, since they are almost equal

    # Normal LMTD calculation
    return (dT1 - dT2) / np.log(dT1 / dT2)


def specific_exergy(h, s, h0, s0, T0):
    """Classical specific flow exergy ψ = (h − h₀) − T₀(s − s₀)."""
    return (h - h0) - T0 * (s - s0)


def exergy_of_heat(Qdot, T_surf, T0=DEFAULT_T0):
    """Heat‑exergy rate (1 − T₀/Tₛ)·Q̇ with guards for invalid inputs."""
    if T_surf <= 0 or Qdot == 0:
        return 0.0
    return (1.0 - T0 / T_surf) * Qdot

# ---------------------------------------------------------------------------
# 3. Thermodynamic property helper
# ---------------------------------------------------------------------------

def _get_coolprop_property(
    output_prop: str,
    fluid: str,
    *,
    T_K: float = None,
    P_Pa: float = None,
    Q_frac: float = None,  # Quality (0 for sat. liquid, 1 for sat. vapor)
    H_J_per_kg: float = None,
    S_J_per_kgK: float = None,
    divisor: float = 1.0,
):
    """
    Wrapper for CoolProp.PropsSI to get a property with specified inputs.
    Converts result by dividing by 'divisor' (e.g., for kJ/kg).
    """
    inputs = {}
    if T_K is not None: inputs["T"] = T_K
    if P_Pa is not None: inputs["P"] = P_Pa
    if Q_frac is not None: inputs["Q"] = Q_frac
    if H_J_per_kg is not None: inputs["H"] = H_J_per_kg
    if S_J_per_kgK is not None: inputs["S"] = S_J_per_kgK

    if len(inputs) != 2:
        raise ValueError("Exactly two input properties must be provided to CoolProp.")

    input_keys = list(inputs.keys())
    return CP.PropsSI(output_prop, input_keys[0], inputs[input_keys[0]], input_keys[1], inputs[input_keys[1]], fluid) / divisor

# ---------------------------------------------------------------------------
# 4. Core ORC routine
# ---------------------------------------------------------------------------

def calculate_orc_performance(
    P_evap,
    T_turb_in,
    T_cond,
    eta_pump,
    eta_turb,
    *,
    fluid=DEFAULT_FLUID,
    m_orc=5.0,
    T0=DEFAULT_T0,
    P0=DEFAULT_P0,
    T_htf_in=None,
    T_htf_out=None,
    heat_exchanger_data: dict = None,
):
    """Return (ψ‑table, component‑table, cycle‑kpi) for a simple ORC."""

    # --- 3.1 Environmental reference state ---------------------------------
    h0 = CP.PropsSI("HMASS", "T", T0, "P", P0, fluid) / 1e3  # kJ/kg
    s0 = CP.PropsSI("SMASS", "T", T0, "P", P0, fluid) / J_PER_KJ  # kJ/kg·K

    # --- 3.2 Thermodynamic states ------------------------------------------
    states = {}
    # (1) condenser outlet (sat. liquid)
    T1 = T_cond
    P1 = _get_coolprop_property("P", fluid, T_K=T1, Q_frac=0)
    h1 = _get_coolprop_property("HMASS", fluid, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
    s1 = _get_coolprop_property("SMASS", fluid, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
    states["1"] = {"h": h1, "s": s1, "T": T1, "P": P1}

    # (2) pump outlet
    P2 = P_evap
    s2s = s1             # isentropic assumption
    h2s = _get_coolprop_property("HMASS", fluid, P_Pa=P2, S_J_per_kgK=s2s * J_PER_KJ, divisor=J_PER_KJ)
    h2  = h1 + (h2s - h1) / eta_pump
    T2  = _get_coolprop_property("T", fluid, P_Pa=P2, H_J_per_kg=h2 * J_PER_KJ)
    s2  = _get_coolprop_property("SMASS", fluid, P_Pa=P2, H_J_per_kg=h2 * J_PER_KJ, divisor=J_PER_KJ)
    states["2"] = {"h": h2, "s": s2, "T": T2, "P": P2}

    # (3) turbine inlet (superheated or sat. vapour)
    T3 = T_turb_in
    P3 = P_evap
    h3 = _get_coolprop_property("HMASS", fluid, T_K=T3, P_Pa=P3, divisor=J_PER_KJ)
    s3 = _get_coolprop_property("SMASS", fluid, T_K=T3, P_Pa=P3, divisor=J_PER_KJ)
    states["3"] = {"h": h3, "s": s3, "T": T3, "P": P3}

    # (4) turbine outlet
    P4 = P1
    s4s = s3
    h4s = _get_coolprop_property("HMASS", fluid, P_Pa=P4, S_J_per_kgK=s4s * J_PER_KJ, divisor=J_PER_KJ)
    h4  = h3 - eta_turb * (h3 - h4s)
    T4  = _get_coolprop_property("T", fluid, P_Pa=P4, H_J_per_kg=h4 * J_PER_KJ)
    s4  = _get_coolprop_property("SMASS", fluid, P_Pa=P4, H_J_per_kg=h4 * J_PER_KJ, divisor=J_PER_KJ)
    states["4"] = {"h": h4, "s": s4, "T": T4, "P": P4}

    # --- ADDED: Add intermediate states for detailed heat exchange ---
    if heat_exchanger_data and heat_exchanger_data.get("use_detailed_hex", False):
        # State 2a: Preheater outlet (Saturated Liquid)
        h2a = _get_coolprop_property("HMASS", fluid, P_Pa=P_evap, Q_frac=0, divisor=J_PER_KJ)
        s2a = _get_coolprop_property("SMASS", fluid, P_Pa=P_evap, Q_frac=0, divisor=J_PER_KJ)
        T2a = _get_coolprop_property("T", fluid, P_Pa=P_evap, Q_frac=0)
        states["2a"] = {"h": h2a, "s": s2a, "T": T2a, "P": P_evap}
        
        # State 2b: Evaporator outlet (Saturated Vapor)
        h2b = _get_coolprop_property("HMASS", fluid, P_Pa=P_evap, Q_frac=1, divisor=J_PER_KJ)
        s2b = _get_coolprop_property("SMASS", fluid, P_Pa=P_evap, Q_frac=1, divisor=J_PER_KJ)
        T2b = _get_coolprop_property("T", fluid, P_Pa=P_evap, Q_frac=1)
        states["2b"] = {"h": h2b, "s": s2b, "T": T2b, "P": P_evap}

    # --- 3.3 Specific exergy ψ at each state --------------------------------
    psi = {k: specific_exergy(v["h"], v["s"], h0, s0, T0) for k, v in states.items()}

    psi_df = pd.DataFrame(
        {
            "h [kJ/kg]": {k: v["h"] for k, v in states.items()},
            "s [kJ/kgK]": {k: v["s"] for k, v in states.items()},
            "T [K]": {k: v["T"] for k, v in states.items()},
            "P [kPa]": {k: v["P"] / PA_PER_KPA for k, v in states.items()},
            "ψ [kJ/kg]": psi,
        }
    ).T

    # -----------------------------------------------------------------------
    # 4. Component balances
    # -----------------------------------------------------------------------
    results = {}

    # (a) Pump --------------------------------------------------------------
    W_p = m_orc * (h2 - h1)
    W_p_rev = m_orc * (psi["2"] - psi["1"])
    results["Pump"] = {
        "W [kW]": W_p,
        "E_dest [kW]": W_p - W_p_rev,
        "η_exergy [-]": W_p_rev / W_p if W_p else np.nan,
    }

    # (b) Evaporator (or Heat Exchanger System) -----------------------------
    if heat_exchanger_data and heat_exchanger_data.get("use_detailed_hex", False):
        # Detailed calculation for Preheater, Evaporator, Superheater
        # Preheater
        Q_pre = m_orc * (states["2a"]["h"] - states["2"]["h"])
        T_htf_in_pre = heat_exchanger_data["T_htf_mid2"]
        T_htf_out_pre = heat_exchanger_data["T_htf_out"]
        dT_lm_pre = lmtd_counter_current(T_htf_in_pre, T_htf_out_pre, states["2"]["T"], states["2a"]["T"])
        T_hot_avg_pre = 0.5 * (T_htf_in_pre + T_htf_out_pre)
        E_heat_pre = exergy_of_heat(Q_pre, T_hot_avg_pre, T0)
        results["Preheater"] = {
            "Q [kW]": Q_pre, "E_heat [kW]": E_heat_pre,
            "E_dest [kW]": E_heat_pre - m_orc * (psi["2a"] - psi["2"]),
            "ε [-]": m_orc * (psi["2a"] - psi["2"]) / E_heat_pre if E_heat_pre else np.nan,
            "ΔT_lm [K]": dT_lm_pre,
        }
        
        # Evaporator (2a → 2b)
        Q_evap = m_orc * (states["2b"]["h"] - states["2a"]["h"])
        T_htf_in_evap = heat_exchanger_data["T_htf_mid1"]
        T_htf_out_evap = heat_exchanger_data["T_htf_mid2"]
        dT_lm_evap = lmtd_counter_current(T_htf_in_evap, T_htf_out_evap, states["2a"]["T"], states["2b"]["T"])
        T_hot_avg_evap = 0.5 * (T_htf_in_evap + T_htf_out_evap)
        E_heat_evap = exergy_of_heat(Q_evap, T_hot_avg_evap, T0)
        results["Evaporator"] = {
            "Q [kW]": Q_evap, "E_heat [kW]": E_heat_evap,
            "E_dest [kW]": E_heat_evap - m_orc * (psi["2b"] - psi["2a"]),
            "ε [-]": m_orc * (psi["2b"] - psi["2a"]) / E_heat_evap if E_heat_evap else np.nan,
            "ΔT_lm [K]": dT_lm_evap,
        }
        
        # Superheater (2b → 3)
        Q_super = m_orc * (states["3"]["h"] - states["2b"]["h"])
        T_htf_in_super = heat_exchanger_data["T_htf_in"]
        T_htf_out_super = heat_exchanger_data["T_htf_mid1"]
        dT_lm_super = lmtd_counter_current(T_htf_in_super, T_htf_out_super, states["2b"]["T"], states["3"]["T"])
        T_hot_avg_super = 0.5 * (T_htf_in_super + T_htf_out_super)
        E_heat_super = exergy_of_heat(Q_super, T_hot_avg_super, T0)
        results["Superheater"] = {
            "Q [kW]": Q_super, "E_heat [kW]": E_heat_super,
            "E_dest [kW]": E_heat_super - m_orc * (psi["3"] - psi["2b"]),
            "ε [-]": m_orc * (psi["3"] - psi["2b"]) / E_heat_super if E_heat_super else np.nan,
            "ΔT_lm [K]": dT_lm_super,
        }
        Q_e = Q_pre + Q_evap + Q_super
        E_heat_e = E_heat_pre + E_heat_evap + E_heat_super
    else:
        # Original simplified calculation
        Q_e = m_orc * (h3 - h2)
        T_htf_in = heat_exchanger_data.get("T_htf_in") if heat_exchanger_data else T_htf_in
        T_htf_out = heat_exchanger_data.get("T_htf_out") if heat_exchanger_data else T_htf_out
        
        if T_htf_in is not None and T_htf_out is not None:
            dT_lm = lmtd_counter_current(T_htf_in, T_htf_out, T2, T3)
            T_hot_avg = 0.5 * (T_htf_in + T_htf_out)
        else:
            dT_lm = T3 - T2              # fallback dummy
            T_hot_avg = 0.5 * (T2 + T3)  # fallback if HTF temps not provided

        E_heat_e = exergy_of_heat(Q_e, T_hot_avg, T0)
        results["Evaporator"] = {
            "Q [kW]": Q_e,
            "E_heat [kW]": E_heat_e,
            "E_dest [kW]": E_heat_e - m_orc * (psi["3"] - psi["2"]),
            "ε [-]": m_orc * (psi["3"] - psi["2"]) / E_heat_e if E_heat_e else np.nan,
            "ΔT_lm [K]": dT_lm,
            "T_hot_avg [K]": T_hot_avg,
        }

    # (c) Turbine -----------------------------------------------------------
    W_t = m_orc * (h3 - h4)
    W_t_rev = m_orc * (psi["3"] - psi["4"])
    results["Turbine"] = {
        "W [kW]": W_t,
        "E_dest [kW]": W_t_rev - W_t,
        "η_exergy [-]": W_t / W_t_rev if W_t_rev else np.nan,
    }

    # (d) Condenser ---------------------------------------------------------
    Q_c = m_orc * (h1 - h4)         # Heat removed (should be < 0)
    T_cold_avg = 0.5 * (T4 + T1)

    # Calculate the magnitude of exergy rejected with heat (positive value)
    E_heat_rejected_magnitude = exergy_of_heat(abs(Q_c), T_cold_avg, T0)

    # Calculate exergy destruction (should be positive)
    # Exergy balance: E_in - E_out - E_heat_rejected = E_dest
    E_dest_Condenser = m_orc * (psi["4"] - psi["1"]) - E_heat_rejected_magnitude

    results["Condenser"] = {
        "Q [kW]": Q_c,
        "E_heat_rejected [kW]": E_heat_rejected_magnitude,
        "E_dest [kW]": E_dest_Condenser,
        "T_cold_avg [K]": T_cold_avg,
    }

    # -----------------------------------------------------------------------
    # 5. Cycle KPIs
    # -----------------------------------------------------------------------
    W_net = W_t - W_p
    eta_th = W_net / Q_e if Q_e else np.nan
    eps_ex = W_net / E_heat_e if E_heat_e else np.nan

    cycle_perf = {
        "W_net [kW]": W_net,
        "Q_in [kW]": Q_e,
        "Q_out [kW]": Q_c,
        "η_th [-]": eta_th,
        "ε_ex [-]": eps_ex,
    }

    comp_df = pd.DataFrame(results).T
    return psi_df, comp_df, cycle_perf

# ---------------------------------------------------------------------------
# 5. Wrapper: match ORC to external heat source
# ---------------------------------------------------------------------------

def calculate_orc_performance_from_heat_source(
    T_htf_in,
    Vdot_htf,
    T_cond,
    eta_pump,
    eta_turb,
    *,
    fluid_orc: str = DEFAULT_FLUID,
    superheat_C: float = 10.0,
    pinch_delta_K: float = 10.0,
    T0: float = DEFAULT_T0,
    P0: float = DEFAULT_P0,
    # --- Heat source specific ---
    heat_source_type: str = "liquid",
    fluid_htf: str = "Water",
    P_htf: float = 101.325e3,
    gas_composition: dict = None,
    P_gas: float = 101325,
    mass_flow_mode: bool = False,
    T_gas_out_min: float = None,
    use_detailed_hex: bool = True  # ADDED: Toggle for detailed simulation
):
    """Compute ORC KPIs when driven by a heat source (liquid or gas)."""
    try:
        superheat_K = superheat_C
        T_sat_evap = T_htf_in - pinch_delta_K - superheat_K

        # --- 臨界温度・凝縮温度チェック ---
        if not hasattr(calculate_orc_performance_from_heat_source, '_tcrit_cache'):
            calculate_orc_performance_from_heat_source._tcrit_cache = {}

        if fluid_orc not in calculate_orc_performance_from_heat_source._tcrit_cache:
            try:
                Tcrit = CP.PropsSI("Tcrit", fluid_orc)
                calculate_orc_performance_from_heat_source._tcrit_cache[fluid_orc] = Tcrit
            except (ValueError, RuntimeError, KeyError) as e:
                raise ValueError(f"Could not get critical temperature for fluid '{fluid_orc}': {str(e)}")
        else:
            Tcrit = calculate_orc_performance_from_heat_source._tcrit_cache[fluid_orc]

        if T_sat_evap >= Tcrit or T_sat_evap <= T_cond + 1.0:
            # This state is thermodynamically impossible, so we return None
            # The calling function should handle this case gracefully
            return None
        # --- 臨界温度・凝縮温度チェックここまで ---

        P_evap = _get_coolprop_property("P", fluid_orc, T_K=T_sat_evap, Q_frac=1)
        T_turb_in = T_sat_evap + superheat_K

        # --- MODIFIED: Detailed Heat Exchange Calculation ---
        if use_detailed_hex:
            # 1. Define ORC-side state points for heat exchange
            h3 = _get_coolprop_property("HMASS", fluid_orc, T_K=T_turb_in, P_Pa=P_evap, divisor=J_PER_KJ)
            h2b = _get_coolprop_property("HMASS", fluid_orc, P_Pa=P_evap, Q_frac=1, divisor=J_PER_KJ) # sat. vapor
            h2a = _get_coolprop_property("HMASS", fluid_orc, P_Pa=P_evap, Q_frac=0, divisor=J_PER_KJ) # sat. liquid
            
            T1 = T_cond
            h1 = _get_coolprop_property("HMASS", fluid_orc, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
            s1 = _get_coolprop_property("SMASS", fluid_orc, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
            h2s = _get_coolprop_property("HMASS", fluid_orc, P_Pa=P_evap, S_J_per_kgK=s1 * J_PER_KJ, divisor=J_PER_KJ)
            h2 = h1 + (h2s - h1) / eta_pump

            delta_h_super = h3 - h2b
            delta_h_evap = h2b - h2a
            delta_h_pre = h2a - h2

            # 2. Get heat source profile (total available heat)
            # We need a temporary T_htf_out to get the profile, let's use the pinch point temp
            T_htf_out_guess = T_sat_evap + pinch_delta_K
            if heat_source_type == "gas":
                heat_source = get_heat_source_profile(
                    T_htf_in=T_htf_in, Vdot_htf=Vdot_htf, T_htf_out=T_htf_out_guess,
                    heat_source_type="gas", gas_composition=gas_composition, P_gas=P_gas,
                    mass_flow_mode=mass_flow_mode, T_gas_out_min=T_gas_out_min
                )
            else:
                heat_source = get_heat_source_profile(
                    T_htf_in=T_htf_in, Vdot_htf=Vdot_htf, T_htf_out=T_htf_out_guess,
                    heat_source_type="liquid", fluid_htf=fluid_htf, P_htf=P_htf
                )
            if heat_source is None or heat_source.Q_available <= 0: 
                return None
            
            # 3. Iteratively find m_orc and heat source temperatures
            # Energy balance: m_orc * delta_h = m_htf * cp_htf * delta_T_htf
            # m_orc * (delta_h_super + delta_h_evap + delta_h_pre) = Q_available
            total_delta_h_orc = (h3 - h2)
            if total_delta_h_orc <= 0: 
                return None
            m_orc = (heat_source.Q_available / J_PER_KJ) / total_delta_h_orc

            # 4. Calculate intermediate HTF temperatures
            Q_super = m_orc * delta_h_super
            T_htf_mid1 = heat_source.get_temp_for_heat(Q_super)

            Q_evap = m_orc * delta_h_evap
            T_htf_mid2 = heat_source.get_temp_for_heat(Q_super + Q_evap)

            Q_pre = m_orc * delta_h_pre
            T_htf_out = heat_source.get_temp_for_heat(Q_super + Q_evap + Q_pre)

            # Pinch point check
            if T_htf_mid2 < (T_sat_evap + pinch_delta_K):
                 # This indicates the operating point is not feasible with the given pinch.
                 # A more advanced model would iterate on T_sat_evap, but for now we return None.
                 return None

            hex_data = {
                "use_detailed_hex": True,
                "T_htf_in": T_htf_in, "T_htf_mid1": T_htf_mid1,
                "T_htf_mid2": T_htf_mid2, "T_htf_out": T_htf_out,
            }
        else:
            # --- Original simplified logic ---
            T_htf_out = T_sat_evap + pinch_delta_K
            if heat_source_type == "gas":
                heat_source = get_heat_source_profile(
                    T_htf_in=T_htf_in, Vdot_htf=Vdot_htf, T_htf_out=T_htf_out,
                    heat_source_type="gas", gas_composition=gas_composition, P_gas=P_gas,
                    mass_flow_mode=mass_flow_mode, T_gas_out_min=T_gas_out_min
                )
            else:
                heat_source = get_heat_source_profile(
                    T_htf_in=T_htf_in, Vdot_htf=Vdot_htf, T_htf_out=T_htf_out,
                    heat_source_type="liquid", fluid_htf=fluid_htf, P_htf=P_htf
                )
            if heat_source is None or heat_source.Q_available <= 0: 
                return None
            Q_available = heat_source.Q_available / J_PER_KJ
            
            T1 = T_cond
            h1 = _get_coolprop_property("HMASS", fluid_orc, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
            s1 = _get_coolprop_property("SMASS", fluid_orc, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
            h2s = _get_coolprop_property("HMASS", fluid_orc, P_Pa=P_evap, S_J_per_kgK=s1 * J_PER_KJ, divisor=J_PER_KJ)
            h2 = h1 + (h2s - h1) / eta_pump
            h3 = _get_coolprop_property("HMASS", fluid_orc, T_K=T_turb_in, P_Pa=P_evap, divisor=J_PER_KJ)
            delta_h_evap = h3 - h2
            if delta_h_evap <= 0: 
                return None
            m_orc = Q_available / delta_h_evap
            hex_data = {"use_detailed_hex": False, "T_htf_in": T_htf_in, "T_htf_out": T_htf_out}
        # --- End of modification ---

        # Calculate final performance with determined m_orc
        psi_df, comp_results, cycle_kpi = calculate_orc_performance(
            P_evap=P_evap,
            T_turb_in=T_turb_in,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid=fluid_orc,
            m_orc=m_orc,
            T0=T0,
            P0=P0,
            heat_exchanger_data=hex_data,
        )

        # Populate output dictionary
        output = cycle_kpi.copy()
        output["m_orc [kg/s]"] = m_orc
        output["T_htf_in [°C]"] = T_htf_in - 273.15
        output["T_htf_out [°C]"] = T_htf_out - 273.15
        output["Vdot_htf [m3/s]"] = Vdot_htf
        output["P_evap [bar]"] = P_evap / PA_PER_BAR
        output["T_turb_in [°C]"] = T_turb_in - 273.15
        output["E_dest_Pump [kW]"] = comp_results.loc["Pump", "E_dest [kW]"]
        if use_detailed_hex:
            output["E_dest_Preheater [kW]"] = comp_results.loc["Preheater", "E_dest [kW]"]
            output["E_dest_Evaporator [kW]"] = comp_results.loc["Evaporator", "E_dest [kW]"]
            output["E_dest_Superheater [kW]"] = comp_results.loc["Superheater", "E_dest [kW]"]
        else:
            output["E_dest_Evaporator [kW]"] = comp_results.loc["Evaporator", "E_dest [kW]"]
        output["E_dest_Turbine [kW]"] = comp_results.loc["Turbine", "E_dest [kW]"]
        output["E_dest_Condenser [kW]"] = comp_results.loc["Condenser", "E_dest [kW]"]
        output["E_dest_Total [kW]"] = comp_results["E_dest [kW]"].sum()
        if use_detailed_hex:
            output["Preheater_dT_lm [K]"] = comp_results.loc["Preheater", "ΔT_lm [K]"]
            output["Evap_dT_lm [K]"] = comp_results.loc["Evaporator", "ΔT_lm [K]"]
            output["Superheater_dT_lm [K]"] = comp_results.loc["Superheater", "ΔT_lm [K]"]
        else:
            output["Evap_dT_lm [K]"] = comp_results.loc["Evaporator", "ΔT_lm [K]"]
            output["Evap_E_heat_in [kW]"] = comp_results.loc["Evaporator", "E_heat [kW]"]

        # トグル状態取得
        use_preheater = get_component_setting('use_preheater', False)
        use_superheater = get_component_setting('use_superheater', False)
        preheater_params = get_component_setting('preheater_params', {}) if use_preheater else None
        superheater_params = get_component_setting('superheater_params', {}) if use_superheater else None

        # トグル状態とパラメータを出力に含める
        output["use_preheater"] = use_preheater
        output["use_superheater"] = use_superheater
        output["preheater_params"] = preheater_params
        output["superheater_params"] = superheater_params
        return output
    except Exception as e:
        print("ERROR in calculate_orc_performance_from_heat_source:", e)
        import traceback
        traceback.print_exc()
        return None

# ---------------------------------------------------------------------------
# 6. Example usage when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    P_evap = 15.0e5
    T_cond = 308.15
    T_turb_in = 450.0
    eta_pump = 0.75
    eta_turb = 0.80
    m_orc = 5.0

    psi_df, comp_df, kpi = calculate_orc_performance(
        P_evap,
        T_turb_in,
        T_cond,
        eta_pump,
        eta_turb,
        fluid=DEFAULT_FLUID,
        m_orc=m_orc,
        # dummy HTF data just to demonstrate LMTD path
        T_htf_in=473.15,
        T_htf_out=413.15,
    )

    pd.options.display.width = 120
    print("Thermodynamic states:\n", psi_df)
    print("\nComponents:\n", comp_df)
    print("\nCycle KPIs:\n", kpi)
