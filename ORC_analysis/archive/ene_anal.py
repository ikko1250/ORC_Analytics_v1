# Python demonstration of energy & exergy balance calculations for an idealized ORC component set
import pandas as pd
import CoolProp.CoolProp as CP # CoolPropライブラリをインポート

# --------------------------------------------------
# 1.  Helper functions and Constants (Global Scope)
# --------------------------------------------------
DEFAULT_T0 = 298.15                # デフォルトの環境温度 [K] (25 ℃)
# DEFAULT_FLUID = 'R11'                 # デフォルトの作動流体 (変更前)
DEFAULT_FLUID = 'R245fa'              # デフォルトの作動流体 (HFC-245fa)
DEFAULT_P0 = 101.325e3                   # デフォルトの周囲圧力 [Pa] (1 atm)

def calculate_orc_performance(
    P_evap, T_turb_in, T_cond,
    eta_pump, eta_turb,
    fluid=DEFAULT_FLUID, m_orc=5.0, T0=DEFAULT_T0, P0=DEFAULT_P0
):
    """
    指定されたパラメータに基づいてORCサイクルの性能を計算します。

    Args:
        P_evap (float): 蒸発圧力 [Pa]
        T_turb_in (float): タービン入口温度 [K]
        T_cond (float): 凝縮温度 [K]
        eta_pump (float): ポンプの等エントロピー効率 [-]
        eta_turb (float): タービンの等エントロピー効率 [-]
        fluid (str, optional): 作動流体名. Defaults to DEFAULT_FLUID.
        m_orc (float, optional): 作動流体の質量流量 [kg/s]. Defaults to 5.0.
        T0 (float, optional): 周囲（デッドステート）温度 [K]. Defaults to DEFAULT_T0.
        P0 (float, optional): 周囲（デッドステート）圧力 [Pa]. Defaults to DEFAULT_P0.

    Returns:
        tuple: 以下の要素を含むタプル
            - psi_df (pd.DataFrame): 各状態点の物性値と比エクセルギー
            - component_df (pd.DataFrame): 各コンポーネントの性能（仕事、エクセルギー破壊など）
            - cycle_performance (dict): サイクル全体の性能（正味仕事、熱効率、エクセルギー効率）
    """
    # --- Helper functions specific to this calculation ---
    h0 = CP.PropsSI('H','T',T0,'P',P0,fluid) / 1000
    s0 = CP.PropsSI('S','T',T0,'P',P0,fluid) / 1000

    def specific_exergy(h, s, h0=h0, s0=s0, T0=T0):
        """
        Calculate the specific exergy based on the given state and environmental state.

        Args:
            h (float): Specific enthalpy of the state [kJ/kg].
            s (float): Specific entropy of the state [kJ/kg·K].
            h0 (float): Specific enthalpy of the environmental state [kJ/kg].
            s0 (float): Specific entropy of the environmental state [kJ/kg·K].
            T0 (float): Environmental temperature [K].

        Returns:
            float: The specific exergy [kJ/kg].
        """
        return (h - h0) - T0 * (s - s0)

    def exergy_of_heat(Qdot, T_surf, T0=T0):
        if T_surf <= 0 or Qdot <= 0:  # Avoid division by zero, negative temperature, or negative heat flow
             return 0  # Return zero for invalid or negative heat input
        return (1.0 - T0 / T_surf) * Qdot

    # --------------------------------------------------
    # 2.  Calculate thermodynamic states using CoolProp
    # --------------------------------------------------
    states = {} # 計算結果を格納する空のディクショナリ

    # 状態点 1: 凝縮器出口 (飽和液)
    try:
        T1 = T_cond
        P1 = CP.PropsSI('P', 'T', T1, 'Q', 0, fluid) # T_condにおける飽和圧力
        h1 = CP.PropsSI('H', 'T', T1, 'Q', 0, fluid) / 1000 # kJ/kg
        s1 = CP.PropsSI('S', 'T', T1, 'Q', 0, fluid) / 1000 # kJ/(kg K)
        states["1"] = (h1, s1, T1, P1) # (h, s, T, P) のタプルで格納

        # 状態点 2: ポンプ出口
        P2 = P_evap # ポンプ出口圧力は蒸発圧力と同じ
        s2_ideal = s1 # 等エントロピー圧縮を仮定した場合のエントロピー
        h2_ideal = CP.PropsSI('H', 'P', P2, 'S', s2_ideal * 1000, fluid) / 1000 # 理想的な出口エンタルピー (kJ/kg)
        h2 = h1 + (h2_ideal - h1) / eta_pump # ポンプ効率を考慮した実際の出口エンタルピー (kJ/kg)
        T2 = CP.PropsSI('T', 'P', P2, 'H', h2 * 1000, fluid) # 実際の出口温度 (K)
        s2 = CP.PropsSI('S', 'P', P2, 'H', h2 * 1000, fluid) / 1000 # 実際の出口エントロピー (kJ/kg K)
        states["2"] = (h2, s2, T2, P2)

        # 状態点 3: 蒸発器出口 / タービン入口
        P3 = P_evap
        T3 = T_turb_in
        # Ensure the state is valid (e.g., superheated or saturated vapor)
        phase3 = CP.PhaseSI('T', T3, 'P', P3, fluid)
        # --- 改1：フェーズ判定の拡張 -----------------------------
        valid_phases = ("gas", "vapor", "supercritical", "supercritical_gas")
        if phase3 not in valid_phases:
            raise ValueError(f"Invalid turbine‑inlet phase: {phase3}")
        h3 = CP.PropsSI('H', 'T', T3, 'P', P3, fluid) / 1000
        s3 = CP.PropsSI('S', 'T', T3, 'P', P3, fluid) / 1000
        states["3"] = (h3, s3, T3, P3)

        # 状態点 4: タービン出口 / 凝縮器入口
        P4 = P1 # タービン出口圧力は凝縮圧力と同じ
        s4_ideal = s3 # 等エントロピー膨張を仮定した場合のエントロピー
        h4_ideal = CP.PropsSI('H', 'P', P4, 'S', s4_ideal * 1000, fluid) / 1000 # 理想的な出口エンタルピー (kJ/kg)
        h4 = h3 - eta_turb * (h3 - h4_ideal) # タービン効率を考慮した実際の出口エンタルピー (kJ/kg)
        T4 = CP.PropsSI('T', 'P', P4, 'H', h4 * 1000, fluid) # 実際の出口温度 (K)
        s4 = CP.PropsSI('S', 'P', P4, 'H', h4 * 1000, fluid) / 1000 # 実際の出口エントロピー (kJ/kg K)
        states["4"] = (h4, s4, T4, P4)

    except ValueError as e:
        print(f"Error calculating thermodynamic state with CoolProp: {e}")
        print(f"Parameters: P_evap={P_evap/1e5:.2f} bar, T_turb_in={T_turb_in} K, T_cond={T_cond} K, Fluid={fluid}")
        # Consider how to handle the error, e.g., return None or raise it
        return None, None, None # Indicate failure

    # --------------------------------------------------
    # 3.  Derived properties (specific exergy)
    # --------------------------------------------------
    psi = {k: specific_exergy(states[k][0], states[k][1], T0=T0) for k in states}

    psi_df = pd.DataFrame(
        { "h [kJ/kg]": {k: states[k][0] for k in states},
          "s [kJ/kgK]": {k: states[k][1] for k in states},
          "T [K]":     {k: states[k][2] for k in states},
          "P [kPa]":   {k: states[k][3] / 1000 for k in states}, # 圧力も追加 (kPa)
          "ψ [kJ/kg]": psi }
    ).T # Transpose for better readability similar to original

    # --------------------------------------------------
    # 4.  Component‑wise calculations (energy & exergy)
    # --------------------------------------------------
    results = {}

    # ポンプ (Pump)
    h1, s1, T1, P1 = states["1"]
    h2, s2, T2, P2 = states["2"]
    W_p_actual = m_orc * (h2 - h1)
    W_p_rev = m_orc * (psi["2"] - psi["1"])
    # Avoid division by zero if h2 == h1 (e.g., zero flow or ideal pump with incompressible fluid)
    eta_p_exergy = W_p_rev / W_p_actual if W_p_actual != 0 else None
    E_p_dest = W_p_actual - W_p_rev # Or m_orc * T0 * (s2 - s1)
    results["Pump"] = {
        "W [kW]": W_p_actual, "E_dest [kW]": E_p_dest, "η_exergy [-]": eta_p_exergy
    }

    # 蒸発器 (Evaporator)
    h3, s3, T3, P3 = states["3"]
    Q_e = m_orc * (h3 - h2)
    # Using logarithmic mean temperature difference (LMTD) might be more accurate
    # but requires heat source temperature profile. Using average fluid temp as a proxy for T_surf.
    # A fixed T_surf might be misleading if T2/T3 change significantly.
    # Let's use a simple average fluid temperature as an approximation for surface temperature
    T_surf_e_approx = (T2 + T3) / 2
    # T_surf_e = 435.0 # Keep fixed T_surf for now, as in original? Or use approximation? Let's use approx.
    E_heat_e = exergy_of_heat(Q_e, T_surf_e_approx, T0=T0)
    E_e_dest = E_heat_e - m_orc * (psi["3"] - psi["2"]) if E_heat_e is not None else None
    eps_e = m_orc * (psi["3"] - psi["2"]) / E_heat_e if E_heat_e is not None and E_heat_e != 0 else None
    results["Evaporator"] = {
        "Q [kW]": Q_e, "E_heat [kW]": E_heat_e,
        "E_dest [kW]": E_e_dest, "ε [-]": eps_e, "T_surf_approx [K]": T_surf_e_approx
    }



    # タービン (Turbine)
    h4, s4, T4, P4 = states["4"]
    W_t_actual = m_orc * (h3 - h4)
    W_t_rev = m_orc * (psi["3"] - psi["4"])          # 最大取り出し仕事
    eps_e = W_t_rev / E_heat_e                       # ≤1 が保証される
    eta_t_exergy = W_t_actual / W_t_rev if W_t_rev != 0 else None
    E_t_dest = W_t_rev - W_t_actual
    results["Turbine"] = {
        "W [kW]": W_t_actual, "E_dest [kW]": E_t_dest, "η_exergy [-]": eta_t_exergy
    }

    # 凝縮器 (Condenser)
    Q_c = m_orc * (h1 - h4) # Should be negative (heat rejection)
    # Using average fluid temperature as approximation for T_surf
    T_surf_c_approx = (T4 + T1) / 2
    # T_surf_c = 305.0 # Keep fixed T_surf or use approximation? Let's use approx.
    E_heat_c = exergy_of_heat(Q_c, T_surf_c_approx, T0=T0) # Should be negative
    # E_dest = Sum(E_in) - Sum(E_out) for the component
    # E_dest = (m*psi4 + E_heat_c) - m*psi1 -> E_dest = m*(psi4 - psi1) + E_heat_c
    E_c_dest = m_orc * (psi["4"] - psi["1"]) + E_heat_c if E_heat_c is not None else None # E_heat is negative
    results["Condenser"] = {
        "Q [kW]": Q_c, "E_heat [kW]": E_heat_c, "E_dest [kW]": E_c_dest, "T_surf_approx [K]": T_surf_c_approx
    }

    # サイクル全体 (Overall cycle performance)
    W_net = W_t_actual - W_p_actual
    Q_in = Q_e
    # Avoid division by zero if Q_in is zero or negative (though unlikely for evaporator)
    eta_th = W_net / Q_in if Q_in > 0 else None # Thermal efficiency
    # Exergy input is the exergy of the heat supplied to the evaporator
    E_in_total = E_heat_e if E_heat_e is not None else 0 # Assuming no work input exergy credit needed
    # Avoid division by zero
    eps_ex = W_net / E_in_total if E_in_total is not None and E_in_total > 0 else None # Exergy efficiency

    cycle_performance = { "W_net [kW]": W_net, "Q_in [kW]": Q_in, "Q_out [kW]": Q_c,
                          "η_th [-]": eta_th, "ε_ex [-]": eps_ex }

    component_df = pd.DataFrame(results).T # Transpose to have components as rows

    return psi_df, component_df, cycle_performance

# --------------------------------------------------
# 1b. Wrapper to link external heat source to ORC cycle
# --------------------------------------------------

def calculate_orc_performance_from_heat_source(
    T_htf_in,                # Heat-source inlet temperature [K]
    Vdot_htf,               # Heat-source volumetric flow rate [m^3/s]
    T_cond,                 # ORC condenser temperature [K]
    eta_pump, eta_turb,     # ORC component efficiencies [-]
    fluid_orc: str = DEFAULT_FLUID,
    fluid_htf: str = "Water", # Heat source working fluid
    superheat_C: float = 10.0,   # ORC superheat degree [°C]
    pinch_delta_K: float = 10.0, # Minimum temperature difference at evaporator pinch [K]
    P_htf: float = 101.325e3,    # Heat-source pressure [Pa]
    T0: float = DEFAULT_T0,
    P0: float = DEFAULT_P0,
):
    """Compute ORC performance when the available heat is supplied by an external heat source.

    The function estimates the available evaporator heat duty from a single-phase
    heat-source fluid (default *Water*) that cools from *T_htf_in* to a temperature
    close to the ORC evaporation temperature while keeping at least *pinch_delta_K*
    temperature approach. The ORC evaporation pressure is chosen such that the
    saturation temperature plus the superheat equals (*T_htf_in* – pinch_delta_K).

    The mass flow rate of the ORC working fluid is then adjusted so that the heat
    absorbed in the evaporator equals the heat released by the heat source.  After
    the correct mass flow is found, :pyfunc:`calculate_orc_performance` is called
    to obtain detailed cycle metrics.

    Parameters
    ----------
    T_htf_in : float
        Heat-source inlet temperature [K].
    Vdot_htf : float
        Heat-source volumetric flow rate [m^3/s].  The density at *T_htf_in* and
        *P_htf* is used to convert to kg/s.
    T_cond : float
        ORC condenser temperature [K].
    eta_pump, eta_turb : float
        Isentropic efficiencies of pump and turbine.
    fluid_orc : str, optional
        ORC working fluid (default "R245fa").
    fluid_htf : str, optional
        Heat-source fluid (default "Water").
    superheat_C : float, optional
        Degree of superheat at turbine inlet [°C].
    pinch_delta_K : float, optional
        Minimum temperature difference between heat-source outlet and ORC
        evaporation temperature [K].  Default 10 K.
    P_htf : float, optional
        Absolute pressure of the heat-source stream [Pa].
    T0, P0 : float, optional
        Dead-state temperature and pressure [K, Pa].

    Returns
    -------
    dict | None
        Dictionary containing key results (see below) or *None* if the heat
        source temperature is too low to drive the ORC (i.e., negative available
        heat).

    The result dictionary contains at least the following fields (all *np.nan* if
    calculation fails):
        - "T_htf_in [°C]"
        - "Vdot_htf [m3/s]"
        - "P_evap [bar]"
        - "T_turb_in [°C]"
        - "m_orc [kg/s]"
        - "Q_in [kW]"
        - "W_net [kW]"
        - "η_th [-]"
    """
    import numpy as np

    try:
        # DEBUG: Print variables around 100 C (373.15 K)
        if 372.0 < T_htf_in < 375.0:
            print(f"DEBUG: T_htf_in={T_htf_in:.2f} K ({T_htf_in-273.15:.2f} C)")
            try:
                rho_htf_debug = CP.PropsSI("Dmass", "T", T_htf_in, "P", P_htf, fluid_htf)
                Cpm_htf_debug = CP.PropsSI("Cpmass", "T", T_htf_in, "P", P_htf, fluid_htf)
                print(f"  rho_htf={rho_htf_debug:.2f}, Cpm_htf={Cpm_htf_debug:.2f}")
            except Exception as e_debug:
                print(f"  Error getting HTF props: {e_debug}")
            # T_sat_evap などはこの時点では未計算なのでコメントアウト、または計算後に表示
            # print(f"  T_sat_evap={T_sat_evap:.2f} K, P_evap={P_evap/1e5:.2f} bar")
            # print(f"  T_htf_out={T_htf_out:.2f} K")

        # --- 1. Determine evaporation temperature & pressure ---
        superheat_K = superheat_C  # °C difference == K difference
        # Target evaporation saturation temperature keeps pinch and superheat
        T_sat_evap = T_htf_in - pinch_delta_K - superheat_K
        if T_sat_evap <= T_cond + 1.0:
            # Heat-source temperature too low; evaporator cannot operate
            return None

        P_evap = CP.PropsSI("P", "T", T_sat_evap, "Q", 1, fluid_orc)  # Pa
        T_turb_in = T_sat_evap + superheat_K

        # --- 2. Heat available from HTF ---
        # Density & specific heat of heat source fluid (mass basis)
        rho_htf = CP.PropsSI("Dmass", "T", T_htf_in, "P", P_htf, fluid_htf)  # kg/m3
        Cpm_htf = CP.PropsSI("Cpmass", "T", T_htf_in, "P", P_htf, fluid_htf)  # J/(kg·K)
        m_dot_htf = rho_htf * Vdot_htf  # kg/s
        # Outlet temperature of HTF (ensuring pinch)
        T_htf_out = T_sat_evap + pinch_delta_K
        Q_available = m_dot_htf * Cpm_htf * (T_htf_in - T_htf_out) / 1000.0  # kW
        if Q_available <= 0:
            return None  # No useful heat

        # --- 3. Determine enthalpy rise of ORC working fluid across evaporator ---
        # Compute state 1 & 2 enthalpies to get Δh23 without knowing m_orc yet
        T1 = T_cond
        P1 = CP.PropsSI("P", "T", T1, "Q", 0, fluid_orc)
        h1 = CP.PropsSI("H", "T", T1, "Q", 0, fluid_orc) / 1000  # kJ/kg
        s1 = CP.PropsSI("S", "T", T1, "Q", 0, fluid_orc) / 1000  # kJ/kgK

        s2_ideal = s1
        h2_ideal = CP.PropsSI("H", "P", P_evap, "S", s2_ideal * 1000, fluid_orc) / 1000
        h2 = h1 + (h2_ideal - h1) / eta_pump
        # State 3 enthalpy
        h3 = CP.PropsSI("H", "T", T_turb_in, "P", P_evap, fluid_orc) / 1000

        delta_h_evap = h3 - h2  # kJ/kg
        if delta_h_evap <= 0:
            return None  # Physically impossible

        # --- 4. Required ORC mass flow to match heat available ---
        m_orc = Q_available / delta_h_evap  # kg/s

        # DEBUG: Print Q_available and m_orc around 100 C
        if 372.0 < T_htf_in < 375.0:
             # T_sat_evap 等の計算後の値もここで表示
             print(f"  T_sat_evap={T_sat_evap:.2f} K, P_evap={P_evap/1e5:.2f} bar, T_htf_out={T_htf_out:.2f} K")
             print(f"  Q_available={Q_available:.2f} kW, delta_h_evap={delta_h_evap:.2f} kJ/kg, m_orc={m_orc:.4f} kg/s")

        # --- 5. Use existing routine to compute detailed performance ---
        psi_df, comp_df, cycle_perf = calculate_orc_performance(
            P_evap=P_evap,
            T_turb_in=T_turb_in,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid=fluid_orc,
            m_orc=m_orc,
            T0=T0,
            P0=P0,
        )

        if cycle_perf is None:
            return None

        # Assemble results dictionary
        result = {
            "T_htf_in [°C]": T_htf_in - 273.15,
            "Vdot_htf [m3/s]": Vdot_htf,
            "P_evap [bar]": P_evap / 1e5,
            "T_turb_in [°C]": T_turb_in - 273.15,
            "m_orc [kg/s]": m_orc,
            "Q_in [kW]": cycle_perf.get("Q_in [kW]", np.nan),
            "W_net [kW]": cycle_perf.get("W_net [kW]", np.nan),
            "η_th [-]": cycle_perf.get("η_th [-]", np.nan),
            "eps_e [-]": comp_df.loc["Evaporator", "ε [-]"] if "Evaporator" in comp_df.index else np.nan  # eps_e を追加
        }
        return result

    except Exception as e:
        # Any error results in None; optionally print for debugging
        print(f"Error in calculate_orc_performance_from_heat_source: {e}")
        return None

# --------------------------------------------------
# 5.  Example Usage (when script is run directly)
# --------------------------------------------------
if __name__ == "__main__":
    # --- ORCサイクル設計パラメータ (例) ---
    P_evap_example = 15.0e5                  # 蒸発圧力 [Pa] (例: 15 bar)
    T_cond_example = 308.0                   # 凝縮温度 [K] (例: 35 °C)
    T_turb_in_example = 450.0                # タービン入口温度 [K] (例: 177 °C)
    eta_pump_example = 0.75                  # ポンプの等エントロピー効率 [-] (例: 75%)
    eta_turb_example = 0.80                  # タービンの等エントロピー効率 [-] (例: 80%)
    m_orc_example = 5.0                      # 作動流体の質量流量 [kg/s]
    fluid_example = 'R245fa'                 # 作動流体
    T0_example = 291.0                       # 周囲温度 [K]

    print(f"Running example calculation with:")
    print(f"  P_evap = {P_evap_example/1e5:.1f} bar")
    print(f"  T_turb_in = {T_turb_in_example:.1f} K")
    print(f"  T_cond = {T_cond_example:.1f} K")
    print(f"  Fluid = {fluid_example}")
    print("-" * 30)


    # 関数を呼び出して計算を実行
    psi_df_result, component_df_result, cycle_performance_result = calculate_orc_performance(
        P_evap=P_evap_example,
        T_turb_in=T_turb_in_example,
        T_cond=T_cond_example,
        eta_pump=eta_pump_example,
        eta_turb=eta_turb_example,
        fluid=fluid_example,
        m_orc=m_orc_example,
        T0=T0_example
    )

    # 結果を表示
    if psi_df_result is not None: # Check if calculation was successful
        pd.set_option('display.precision', 3)
        pd.set_option('display.width', 120) # Adjust display width if needed

        print("Thermodynamic states:")
        print(psi_df_result)
        print("\nComponent performance:") # 少し間を空ける
        print(component_df_result)
        print("\nOverall Cycle Performance:")
        # Print cycle performance dictionary nicely
        for key, value in cycle_performance_result.items():
            print(f"  {key:<15}: {value:.3f}" if isinstance(value, (int, float)) else f"  {key:<15}: {value}")
    else:
        print("Calculation failed.")

# --- 削除されたセクション ---
# 2. Input data (Now function arguments)
# 6. Present results (Now inside if __name__ == "__main__")
# Hardcoded states dictionary (replaced by CoolProp calculation)
# Regenerator calculations (removed as per previous state)
# Original Helper function definitions (moved inside or kept global if constant)

# --------------------------------------------------
# 旧コードの名残 (コメントアウトまたは削除)
# --------------------------------------------------
# T0 = 291.0                       # 周囲（デッドステート）温度 [K] (=18 °C)
# fluid = 'R245fa'                 # 作動流体
# P0 = 101.325e3  # 1 atm
# h0 = CP.PropsSI('H','T',T0,'P',P0,fluid) / 1000
# s0 = CP.PropsSI('S','T',T0,'P',P0,fluid) / 1000
# ... (other old code snippets if any) ...
