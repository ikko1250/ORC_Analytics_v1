"""ORC最適化計算モジュール

蒸発器出口温度を目標として、正味出力を最大化するための最適化機能を提供します。
"""

import numpy as np
from scipy.optimize import minimize_scalar, minimize

# Try relative import first, fallback to absolute import for direct execution
try:
    from .ORC_Analysis import calculate_orc_performance_from_heat_source
    from .config import get_component_setting
except ImportError:
    from ORC_Analysis import calculate_orc_performance_from_heat_source
    from config import get_component_setting


def calculate_safe_power_limits(
    T_htf_in,
    Vdot_htf,
    T_cond,
    eta_pump,
    eta_turb,
    fluid_orc="R245fa",
    fluid_htf="Water",
    superheat_C=10.0,
    pinch_delta_K=10.0,
    P_htf=101.325e3,
    max_enthalpy_increase_kJ_per_kg=80.0,  # 実用的安全制限 (1W相当から少しマージン)
):
    """
    質量流量に基づいて安全な電力限界を計算
    
    Args:
        max_enthalpy_increase_kJ_per_kg: 最大エンタルピー増加 [kJ/kg]
        
    Returns:
        tuple: (max_safe_preheater_power, max_safe_superheater_power) [kW]
    """
    try:
        # 基本ORC計算で質量流量を取得
        base_result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid_orc=fluid_orc,
            fluid_htf=fluid_htf,
            superheat_C=superheat_C,
            pinch_delta_K=pinch_delta_K,
            P_htf=P_htf,
            Q_preheater_kW_input=0.0,
            Q_superheater_kW_input=0.0,
        )
        
        if base_result is None:
            return 0.0001, 0.0001  # フォールバック値
        
        m_orc = base_result.get("m_orc [kg/s]", 0.001)  # デフォルト値
        
        # 安全な電力限界を計算
        max_safe_power = max_enthalpy_increase_kJ_per_kg * m_orc  # kW
        
        # 最小値として0.0001kW (0.1W) を設定
        max_safe_power = max(max_safe_power, 0.0001)
        
        return max_safe_power, max_safe_power
        
    except Exception as e:
        print(f"Warning: Failed to calculate safe power limits: {e}")
        return 0.0001, 0.0001  # 非常に保守的なフォールバック値


def optimize_orc_with_components(
    T_htf_in,
    Vdot_htf,
    T_cond,
    eta_pump,
    eta_turb,
    T_evap_out_target,
    *,
    fluid_orc="R245fa",
    fluid_htf="Water",
    superheat_C=10.0,
    pinch_delta_K=10.0,
    P_htf=101.325e3,
    max_preheater_power=50.0,
    max_superheater_power=100.0,
    use_safety_limits=True,  # 新しいパラメータ
):
    """
    蒸発器出口温度を目標として、preheater/superheaterの電力を調整し、
    正味出力を最大化する最適化計算を行います。
    
    Args:
        T_htf_in: 熱源入口温度 [K]
        Vdot_htf: 熱源体積流量 [m³/s]
        T_cond: 凝縮温度 [K]
        eta_pump: ポンプ効率 [-]
        eta_turb: タービン効率 [-]
        T_evap_out_target: 蒸発器出口目標温度 [K]
        fluid_orc: 作動媒体
        fluid_htf: 熱源流体
        superheat_C: 過熱度 [°C]
        pinch_delta_K: ピンチ点温度差 [K]
        P_htf: 熱源圧力 [Pa]
        max_preheater_power: 予熱器最大電力 [kW]
        max_superheater_power: 過熱器最大電力 [kW]
        use_safety_limits: 安全制限を使用するかどうか
        
    Returns:
        dict: 最適化結果
    """
    
    use_preheater = get_component_setting('use_preheater', False)
    use_superheater = get_component_setting('use_superheater', False)
    
    # 安全制限の計算
    if use_safety_limits:
        try:
            safe_preheater_limit, safe_superheater_limit = calculate_safe_power_limits(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                fluid_orc=fluid_orc,
                fluid_htf=fluid_htf,
                superheat_C=superheat_C,
                pinch_delta_K=pinch_delta_K,
                P_htf=P_htf,
            )
            
            # 元の限界値と安全制限の小さい方を使用
            max_preheater_power = min(max_preheater_power, safe_preheater_limit)
            max_superheater_power = min(max_superheater_power, safe_superheater_limit)
            
            safety_limits_applied = True
            applied_preheater_limit = max_preheater_power
            applied_superheater_limit = max_superheater_power
            
        except Exception as e:
            print(f"Warning: Failed to calculate safety limits, using original limits: {e}")
            safety_limits_applied = False
            applied_preheater_limit = max_preheater_power
            applied_superheater_limit = max_superheater_power
    else:
        safety_limits_applied = False
        applied_preheater_limit = max_preheater_power
        applied_superheater_limit = max_superheater_power
    use_superheater = get_component_setting('use_superheater', False)
    
    def objective(params):
        """目的関数：正味出力を最大化（符号反転）"""
        current_Q_preheater = 0.0
        current_Q_superheater = 0.0
        if use_preheater and use_superheater:
            current_Q_preheater, current_Q_superheater = params
        elif use_preheater:
            current_Q_preheater = params
        elif use_superheater:
            current_Q_superheater = params
        
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                fluid_orc=fluid_orc,
                fluid_htf=fluid_htf,
                superheat_C=superheat_C,
                pinch_delta_K=pinch_delta_K,
                P_htf=P_htf,
                # T_evap_out_target はここでは渡さない
                Q_preheater_kW_input=current_Q_preheater,
                Q_superheater_kW_input=current_Q_superheater,
            )
            
            if result is None:
                return 1e6  # 実行不可能解にペナルティ
            
            return -result["W_net [kW]"]  # 最大化のため符号反転
            
        except Exception:
            return 1e6  # エラー時のペナルティ
    
    # 最適化の実行
    optimization_run_success = False
    if use_preheater and use_superheater:
        # 両方使用する場合
        bounds = [(0, applied_preheater_limit), (0, applied_superheater_limit)]
        opt_result_obj = minimize(objective, x0=[min(10.0, applied_preheater_limit/2), min(10.0, applied_superheater_limit/2)], bounds=bounds, method='L-BFGS-B')
        Q_preheater_opt, Q_superheater_opt = opt_result_obj.x if opt_result_obj.success else [0.0, 0.0]
        optimization_run_success = opt_result_obj.success
    elif use_preheater:
        # 予熱器のみ使用
        opt_result_obj = minimize_scalar(objective, bounds=(0, applied_preheater_limit), method='bounded')
        Q_preheater_opt = opt_result_obj.x if opt_result_obj.success else 0.0
        Q_superheater_opt = 0.0
        optimization_run_success = opt_result_obj.success
    elif use_superheater:
        # 過熱器のみ使用
        opt_result_obj = minimize_scalar(objective, bounds=(0, applied_superheater_limit), method='bounded')
        Q_preheater_opt = 0.0
        Q_superheater_opt = opt_result_obj.x if opt_result_obj.success else 0.0
        optimization_run_success = opt_result_obj.success
    else:
        # どちらも使用しない
        Q_preheater_opt = 0.0
        Q_superheater_opt = 0.0
        optimization_run_success = True # 最適化処理自体は不要なので成功とみなす
    
    # 最適解での最終計算
    try:
        final_result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid_orc=fluid_orc,
            fluid_htf=fluid_htf,
            superheat_C=superheat_C,
            pinch_delta_K=pinch_delta_K,
            P_htf=P_htf,
            # T_evap_out_target はここでは渡さない
            Q_preheater_kW_input=Q_preheater_opt,
            Q_superheater_kW_input=Q_superheater_opt,
        )
    except Exception as e:
        print(f"Warning: Final calculation failed with optimized powers, trying zero powers: {e}")
        try:
            # フォールバック: ゼロ電力で計算
            final_result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                fluid_orc=fluid_orc,
                fluid_htf=fluid_htf,
                superheat_C=superheat_C,
                pinch_delta_K=pinch_delta_K,
                P_htf=P_htf,
                Q_preheater_kW_input=0.0,
                Q_superheater_kW_input=0.0,
            )
            # ゼロ電力での計算が成功した場合、最適値をゼロに修正
            Q_preheater_opt = 0.0
            Q_superheater_opt = 0.0
        except Exception as e2:
            print(f"Warning: Fallback calculation also failed: {e2}")
            final_result = None
    
    if final_result is not None:
        final_result.update({
            "Q_preheater_opt [kW]": Q_preheater_opt,
            "Q_superheater_opt [kW]": Q_superheater_opt,
            "optimization_success": optimization_run_success,
            "T_evap_out_target_param": T_evap_out_target, # 元の引数を記録
            "safety_limits_applied": safety_limits_applied,
            "applied_preheater_limit [kW]": applied_preheater_limit,
            "applied_superheater_limit [kW]": applied_superheater_limit,
        })
    else:
        final_result = {
            "Q_preheater_opt [kW]": Q_preheater_opt,
            "Q_superheater_opt [kW]": Q_superheater_opt,
            "optimization_success": False, # 最終計算が失敗した場合
            "W_net [kW]": np.nan, # または 0.0
            "T_evap_out_target_param": T_evap_out_target, # 元の引数を記録
            "safety_limits_applied": safety_limits_applied,
            "applied_preheater_limit [kW]": applied_preheater_limit,
            "applied_superheater_limit [kW]": applied_superheater_limit,
        }
    
    return final_result


def sensitivity_analysis_components(
    T_htf_in,
    Vdot_htf,
    T_cond,
    eta_pump,
    eta_turb,
    T_evap_out_target,
    component_power_range=np.linspace(0, 100, 21),
    use_safety_limits=True,  # 新しいパラメータ
    **kwargs
):
    """
    コンポーネント電力に対する感度解析を実行します。
    
    Args:
        T_htf_in: 熱源入口温度 [K]
        Vdot_htf: 熱源体積流量 [m³/s]
        T_cond: 凝縮温度 [K]
        eta_pump: ポンプ効率 [-]
        eta_turb: タービン効率 [-]
        T_evap_out_target: 蒸発器出口目標温度 [K]
        component_power_range: コンポーネント電力の範囲 [kW]
        use_safety_limits: 安全制限を使用するかどうか
        **kwargs: その他のパラメータ
        
    Returns:
        dict: 感度解析結果
    """
    
    use_preheater = get_component_setting('use_preheater', False)
    use_superheater = get_component_setting('use_superheater', False)
    
    # 安全制限の計算
    max_safe_power = None
    if use_safety_limits:
        try:
            safe_preheater_limit, safe_superheater_limit = calculate_safe_power_limits(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                **kwargs
            )
            max_safe_power = min(safe_preheater_limit, safe_superheater_limit)
        except Exception as e:
            print(f"Warning: Failed to calculate safety limits for sensitivity analysis: {e}")
    
    results = []
    
    for power in component_power_range:
        # 安全制限チェック
        if use_safety_limits and max_safe_power is not None and power > max_safe_power:
            print(f"Skipping power {power:.1f} kW (exceeds safe limit {max_safe_power:.1f} kW)")
            continue
            
        current_Q_preheater_sens = 0.0
        current_Q_superheater_sens = 0.0
        if use_preheater and use_superheater: # 感度分析では両方に同じ電力を割り当てる
            # 両方使用する場合は簡略化して同じ電力を使用
            current_Q_preheater_sens = power
            current_Q_superheater_sens = power
        elif use_preheater:
            current_Q_preheater_sens = power
        elif use_superheater:
            current_Q_superheater_sens = power
        
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                # T_evap_out_target はここでは渡さない
                Q_preheater_kW_input=current_Q_preheater_sens,
                Q_superheater_kW_input=current_Q_superheater_sens,
                **kwargs
            )
            
            if result is not None:
                result.update({
                    "Q_preheater_test [kW]": current_Q_preheater_sens,
                    "Q_superheater_test [kW]": current_Q_superheater_sens,
                })
                results.append(result)
        
        except Exception as e:
            print(f"Error at power {power:.1f} kW: {e}")
            continue
    
    return {
        "sensitivity_results": results,
        "power_range": component_power_range.tolist(),
        "use_preheater": use_preheater,
        "use_superheater": use_superheater,
        "safety_limits_applied": use_safety_limits,
        "max_safe_power": max_safe_power,
    }