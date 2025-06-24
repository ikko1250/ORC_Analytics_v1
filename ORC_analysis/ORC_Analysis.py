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

# Try relative import first, fallback to absolute import for direct execution
try:
    from .config import get_component_setting
except ImportError:
    from config import get_component_setting

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
    Q_preheater_kW=0.0,
    Q_superheater_kW=0.0,
):
    """Return (ψ‑table, component‑table, cycle‑kpi) for ORC with optional preheater/superheater."""

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

    # (2b) after preheater (if used) - 出力向上のための修正版
    if Q_preheater_kW > 0:
        # 予熱器による最大可能エンタルピー増加
        delta_h_preheater = Q_preheater_kW / m_orc  # kJ/kg
        h2b_target = h2 + delta_h_preheater
        
        # 温度制限チェック: 蒸発温度-5K以下に制限
        T_sat_evap = _get_coolprop_property("T", fluid, P_Pa=P2, Q_frac=1)
        T_max_preheater = T_sat_evap - 5.0  # 5K マージン
        
        # 目標温度の計算
        try:
            T2b_target = _get_coolprop_property("T", fluid, P_Pa=P2, H_J_per_kg=h2b_target * J_PER_KJ)
            
            if T2b_target > T_max_preheater:
                # 温度制限に達した場合は制限温度で再計算
                T2b = T_max_preheater
                h2b = _get_coolprop_property("HMASS", fluid, T_K=T2b, P_Pa=P2, divisor=J_PER_KJ)
                Q_preheater_actual = m_orc * (h2b - h2)  # 実際の予熱器熱量
            else:
                T2b = T2b_target
                h2b = h2b_target
                Q_preheater_actual = Q_preheater_kW
                
        except Exception as e:
            # CoolProp計算エラーの場合は予熱器なしとして処理
            print(f"Warning: Preheater calculation failed, using no preheater: {e}")
            T2b = T2
            h2b = h2
            Q_preheater_actual = 0.0
    else:
        T2b = T2
        h2b = h2
        Q_preheater_actual = 0.0
    
    # プリヒーターによる蒸発器負荷軽減を記録（後でタービン入口温度上昇に使用）
    preheater_evap_reduction = Q_preheater_actual  # kW
    
    s2b = _get_coolprop_property("SMASS", fluid, P_Pa=P2, H_J_per_kg=h2b * J_PER_KJ, divisor=J_PER_KJ)
    states["2b"] = {"h": h2b, "s": s2b, "T": T2b, "P": P2}

    # (3) evaporator outlet - 基本蒸発温度（飽和蒸気）
    # プリヒーターがある場合は、基本的に飽和蒸気温度で蒸発器を出る
    P3 = P_evap
    T3_evap = _get_coolprop_property("T", fluid, P_Pa=P3, Q_frac=1)  # 飽和蒸気温度
    h3_evap = _get_coolprop_property("HMASS", fluid, P_Pa=P3, Q_frac=1, divisor=J_PER_KJ)  # 飽和蒸気エンタルピー
    s3_evap = _get_coolprop_property("SMASS", fluid, P_Pa=P3, Q_frac=1, divisor=J_PER_KJ)  # 飽和蒸気エントロピー
    states["3"] = {"h": h3_evap, "s": s3_evap, "T": T3_evap, "P": P3}

    # (3b) after superheater (if used) - 出力向上のための修正版
    # 基本タービン入口温度を設定
    T_turb_in_base = T_turb_in  # 元の入力値を保存
    
    # 新しいアプローチ: プリヒーターとスーパーヒーターの効果を直接タービン入口温度に適用
    # プリヒーターは蒸発器負荷を減らし、その分でタービン入口温度を上げる
    # スーパーヒーターは直接タービン入口温度を上げる
    
    # 各コンポーネントの温度上昇効果を積算
    total_temp_boost_kW = preheater_evap_reduction + Q_superheater_kW
    
    if total_temp_boost_kW > 0:
        # 総熱量をエンタルピー増加に変換
        delta_h_total = total_temp_boost_kW / m_orc  # kJ/kg
        h_enhanced = h3_evap + delta_h_total
        
        try:
            T_turb_in_enhanced = _get_coolprop_property("T", fluid, P_Pa=P3, H_J_per_kg=h_enhanced * J_PER_KJ)
        except Exception as e:
            print(f"Warning: Enhanced temperature calculation failed: {e}")
            T_turb_in_enhanced = T_turb_in_base
    else:
        T_turb_in_enhanced = T_turb_in_base
    
    # 温度制限チェック: 臨界温度-10K以下に制限
    try:
        T_critical = CP.PropsSI("Tcrit", fluid)
        T_max_limit = T_critical - 10.0  # 10K マージン
        
        if T_turb_in_enhanced > T_max_limit:
            T3b = T_max_limit
        else:
            T3b = T_turb_in_enhanced
            
        # 過熱温度での物性計算
        if T3b > T3_evap + 1.0:  # 過熱状態であることを確認
            h3b = _get_coolprop_property("HMASS", fluid, T_K=T3b, P_Pa=P3, divisor=J_PER_KJ)
        else:
            # 飽和温度に近い場合は飽和蒸気状態を使用
            h3b = h3_evap
            T3b = T3_evap
        
        # 実際のスーパーヒーター熱量（蒸発器出口からの増加分のみ）
        # 注意: ここでは実際に使用された熱量を計算
        Q_superheater_actual = m_orc * (h3b - h3_evap) if h3b > h3_evap else 0.0
        
    except Exception as e:
        # CoolProp計算エラーの場合は基本温度を使用
        print(f"Warning: Enhanced temperature calculation failed, using base temperature: {e}")
        T3b = T_turb_in_base
        if T3b > T3_evap + 1.0:  # 過熱状態であることを確認
            h3b = _get_coolprop_property("HMASS", fluid, T_K=T3b, P_Pa=P3, divisor=J_PER_KJ)
        else:
            h3b = h3_evap
            T3b = T3_evap
        Q_superheater_actual = m_orc * (h3b - h3_evap) if h3b > h3_evap else 0.0
    
    s3b = _get_coolprop_property("SMASS", fluid, P_Pa=P3, H_J_per_kg=h3b * J_PER_KJ, divisor=J_PER_KJ)
    states["3b"] = {"h": h3b, "s": s3b, "T": T3b, "P": P3}
    
    # Turbine inlet is now after superheater
    h3 = h3b
    s3 = s3b

    # (4) turbine outlet
    P4 = P1
    s4s = s3
    h4s = _get_coolprop_property("HMASS", fluid, P_Pa=P4, S_J_per_kgK=s4s * J_PER_KJ, divisor=J_PER_KJ)
    h4  = h3 - eta_turb * (h3 - h4s)
    T4  = _get_coolprop_property("T", fluid, P_Pa=P4, H_J_per_kg=h4 * J_PER_KJ)
    s4  = _get_coolprop_property("SMASS", fluid, P_Pa=P4, H_J_per_kg=h4 * J_PER_KJ, divisor=J_PER_KJ)
    states["4"] = {"h": h4, "s": s4, "T": T4, "P": P4}

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

    # (b) Preheater --------------------------------------------------------
    if Q_preheater_kW > 0:
        # 実際の予熱器熱量を使用（温度制限考慮後）
        Q_preheater_used = Q_preheater_actual if 'Q_preheater_actual' in locals() else Q_preheater_kW
        results["Preheater"] = {
            "Q [kW]": Q_preheater_used,
            "Q_input [kW]": Q_preheater_kW,  # 入力熱量
            "E_dest [kW]": Q_preheater_used - m_orc * (psi["2b"] - psi["2"]),
            "constraint_active": Q_preheater_used < Q_preheater_kW,
        }

    # (c) Evaporator --------------------------------------------------------
    Q_e = m_orc * (h3_evap - h2b)

    if T_htf_in is not None and T_htf_out is not None:
        dT_lm = lmtd_counter_current(T_htf_in, T_htf_out, T2b, T3_evap)
        T_hot_avg = 0.5 * (T_htf_in + T_htf_out)
    else:
        dT_lm = T3_evap - T2b        # fallback dummy
        T_hot_avg = 0.5 * (T2b + T3_evap)  # fallback if HTF temps not provided

    E_heat_e = exergy_of_heat(Q_e, T_hot_avg, T0)
    results["Evaporator"] = {
        "Q [kW]": Q_e,
        "E_heat [kW]": E_heat_e,
        "E_dest [kW]": E_heat_e - m_orc * (psi["3"] - psi["2b"]),
        "ε [-]": m_orc * (psi["3"] - psi["2b"]) / E_heat_e if E_heat_e else np.nan,
        "ΔT_lm [K]": dT_lm,
        "T_hot_avg [K]": T_hot_avg,
    }

    # (d) Superheater -------------------------------------------------------
    if Q_superheater_kW > 0:
        # 実際の過熱器熱量を使用（温度制限考慮後）
        Q_superheater_used = Q_superheater_actual if 'Q_superheater_actual' in locals() else Q_superheater_kW
        results["Superheater"] = {
            "Q [kW]": Q_superheater_used,
            "Q_input [kW]": Q_superheater_kW,  # 入力熱量
            "E_dest [kW]": Q_superheater_used - m_orc * (psi["3b"] - psi["3"]),
            "constraint_active": Q_superheater_used < Q_superheater_kW,
        }

    # (e) Turbine -----------------------------------------------------------
    W_t = m_orc * (h3 - h4)
    W_t_rev = m_orc * (psi["3b"] - psi["4"])
    results["Turbine"] = {
        "W [kW]": W_t,
        "E_dest [kW]": W_t_rev - W_t,
        "η_exergy [-]": W_t / W_t_rev if W_t_rev else np.nan,
    }

    # (f) Condenser ---------------------------------------------------------
    Q_c = m_orc * (h1 - h4)         # should be < 0
    T_cold_avg = 0.5 * (T4 + T1)
    E_heat_c = exergy_of_heat(Q_c, T_cold_avg, T0)
    results["Condenser"] = {
        "Q [kW]": Q_c,
        "E_heat [kW]": E_heat_c,
        "E_dest [kW]": m_orc * (psi["4"] - psi["1"]) + E_heat_c,
        "T_cold_avg [K]": T_cold_avg,
    }

    # -----------------------------------------------------------------------
    # 5. Cycle KPIs
    # -----------------------------------------------------------------------
    W_net = W_t - W_p  # 予熱器・過熱器は電力消費ではない（熱交換器）
    
    # 実際に使用された熱量を計算
    Q_preheater_used = Q_preheater_actual if 'Q_preheater_actual' in locals() else 0.0
    Q_superheater_used = Q_superheater_actual if 'Q_superheater_actual' in locals() else 0.0
    
    Q_total_in = Q_e + Q_preheater_used + Q_superheater_used
    eta_th = W_net / Q_total_in if Q_total_in else np.nan
    eps_ex = W_net / E_heat_e if E_heat_e else np.nan

    cycle_perf = {
        "W_net [kW]": W_net,
        "Q_in [kW]": Q_total_in,
        "Q_out [kW]": Q_c,
        "η_th [-]": eta_th,
        "ε_ex [-]": eps_ex,
        "Q_preheater [kW]": Q_preheater_used,
        "Q_superheater [kW]": Q_superheater_used,
        "Q_preheater_input [kW]": Q_preheater_kW,  # 入力値
        "Q_superheater_input [kW]": Q_superheater_kW,  # 入力値
        "preheater_constraint_active": Q_preheater_used < Q_preheater_kW if Q_preheater_kW > 0 else False,
        "superheater_constraint_active": Q_superheater_used < Q_superheater_kW if Q_superheater_kW > 0 else False,
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
    fluid_htf: str = "Water",
    superheat_C: float = 10.0,
    pinch_delta_K: float = 10.0,
    P_htf: float = 101.325e3,
    T0: float = DEFAULT_T0,
    P0: float = DEFAULT_P0,
    Q_preheater_kW_input: float = 0.0,  # 外部から与えられる予熱器熱量
    Q_superheater_kW_input: float = 0.0, # 外部から与えられる過熱器熱量
):
    """Compute ORC KPIs when driven by a single‑phase heat source with optional optimization."""
    try:
        superheat_K = superheat_C
        T_sat_evap = T_htf_in - pinch_delta_K - superheat_K

        # --- 臨界温度・凝縮温度チェック ---

        if not hasattr(calculate_orc_performance_from_heat_source, '_tcrit_cache'):
            calculate_orc_performance_from_heat_source._tcrit_cache = {}

        if fluid_orc not in calculate_orc_performance_from_heat_source._tcrit_cache:
            # キャッシュにない場合：CoolProp で計算してキャッシュに保存
            try:
                Tcrit = CP.PropsSI("Tcrit", fluid_orc)
                calculate_orc_performance_from_heat_source._tcrit_cache[fluid_orc] = Tcrit

            except (ValueError, RuntimeError, KeyError) as e:
                raise ValueError(f"Could not get critical temperature for fluid '{fluid_orc}': {str(e)}")
        else:
            Tcrit = calculate_orc_performance_from_heat_source._tcrit_cache[fluid_orc]

        if T_sat_evap >= Tcrit or T_sat_evap <= T_cond + 1.0:
            raise ValueError(
                f"Calculated evaporator saturation temperature ({T_sat_evap:.2f} K) is invalid. "
                f"It must be below critical temperature ({Tcrit:.2f} K) and above condenser temperature + 1K ({T_cond + 1.0:.2f} K). "
                f"(Input T_htf_in: {T_htf_in:.2f} K, T_cond: {T_cond:.2f} K, pinch: {pinch_delta_K:.2f} K, superheat: {superheat_K:.2f} K)"
            )
        # --- 臨界温度・凝縮温度チェックここまで ---

        P_evap = _get_coolprop_property("P", fluid_orc, T_K=T_sat_evap, Q_frac=1)
        T_turb_in = T_sat_evap + superheat_K

        # Assuming T_htf_in is the average temperature for property calculation if not specified otherwise
        # For more accuracy, properties could be evaluated at mean temp or integrated
        rho_htf = _get_coolprop_property("DMASS", fluid_htf, T_K=T_htf_in, P_Pa=P_htf) # 密度の計算
        Cpm_htf = _get_coolprop_property("CPMASS", fluid_htf, T_K=T_htf_in, P_Pa=P_htf) # J/kg.K, 定圧比熱の計算
        m_htf = rho_htf * Vdot_htf # 質量流量の計算
        T_htf_out = T_sat_evap + pinch_delta_K # 出口温度の計算
        Q_available = m_htf * Cpm_htf * (T_htf_in - T_htf_out) / J_PER_KJ  # kW, 熱量の計算
        if Q_available <= 0:
            return None

        # quick ORC enthalpy rise to estimate m_orc
        T1 = T_cond
        # P1 = _get_coolprop_property("P", fluid_orc, T_K=T1, Q_frac=0) # Not strictly needed for h1, s1
        h1 = _get_coolprop_property("HMASS", fluid_orc, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
        s1 = _get_coolprop_property("SMASS", fluid_orc, T_K=T1, Q_frac=0, divisor=J_PER_KJ)
        h2s = _get_coolprop_property("HMASS", fluid_orc, P_Pa=P_evap, S_J_per_kgK=s1 * J_PER_KJ, divisor=J_PER_KJ)
        h2 = h1 + (h2s - h1) / eta_pump
        h3 = _get_coolprop_property("HMASS", fluid_orc, T_K=T_turb_in, P_Pa=P_evap, divisor=J_PER_KJ)
        delta_h_evap = h3 - h2
        if delta_h_evap <= 0:
            return None
        m_orc = Q_available / delta_h_evap

        # 最終的な性能計算
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
            T_htf_in=T_htf_in,
            T_htf_out=T_htf_out,
            Q_preheater_kW=Q_preheater_kW_input,
            Q_superheater_kW=Q_superheater_kW_input,
        )

        # Populate output dictionary
        output = cycle_kpi.copy() # Start with cycle KPIs
        output["m_orc [kg/s]"] = m_orc
        output["T_htf_in [°C]"] = T_htf_in - 273.15
        output["T_htf_out [°C]"] = T_htf_out - 273.15
        output["Vdot_htf [m3/s]"] = Vdot_htf # Keep original input for grouping
        output["P_evap [bar]"] = P_evap / PA_PER_BAR
        output["T_turb_in [°C]"] = T_turb_in - 273.15
        # Access DataFrame using .loc["index", "column"]
        output["E_dest_Pump [kW]"] = comp_results.loc["Pump", "E_dest [kW]"]
        output["E_dest_Evaporator [kW]"] = comp_results.loc["Evaporator", "E_dest [kW]"]
        output["E_dest_Turbine [kW]"] = comp_results.loc["Turbine", "E_dest [kW]"]
        output["E_dest_Condenser [kW]"] = comp_results.loc["Condenser", "E_dest [kW]"]
        # Use DataFrame column sum for total exergy destruction
        output["E_dest_Total [kW]"] = comp_results["E_dest [kW]"].sum()
        # Add other potentially useful info from comp_results if needed
        output["Evap_dT_lm [K]"] = comp_results.loc["Evaporator", "ΔT_lm [K]"]
        output["Evap_E_heat_in [kW]"] = comp_results.loc["Evaporator", "E_heat [kW]"]

        # コンポーネント状態を出力に含める
        output["use_preheater"] = True if Q_preheater_kW_input > 0 else False
        output["use_superheater"] = True if Q_superheater_kW_input > 0 else False
        output["Q_preheater_kW"] = Q_preheater_kW_input
        output["Q_superheater_kW"] = Q_superheater_kW_input
        return output
    except Exception as e:
        print("ERROR in calculate_orc_performance_from_heat_source:", e)
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
