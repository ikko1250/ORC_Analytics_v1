"""optimization.py の修正版

エンタルピー制限を考慮した安全な最適化を実装
"""

import numpy as np
from scipy.optimize import minimize_scalar, minimize
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.config import get_component_setting


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
    max_enthalpy_increase_kJ_per_kg=5000.0,  # 安全なエンタルピー増加限界
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
            return 0.0, 0.0
            
        m_orc = base_result.get('m_orc [kg/s]', 0.001)  # デフォルト値
        
        # 安全な電力限界を計算: Power = delta_h * m_orc
        max_safe_power = max_enthalpy_increase_kJ_per_kg * m_orc
        
        # 最小値を0.1kWとする
        max_safe_power = max(0.1, max_safe_power)
        
        return max_safe_power, max_safe_power
        
    except Exception:
        # エラーの場合は保守的に小さな値を返す
        return 0.5, 0.5


def optimize_orc_with_components_safe(
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
    use_dynamic_limits=True,
    max_enthalpy_increase_kJ_per_kg=5000.0,
):
    """
    安全な電力制限を使用した最適化計算
    
    新機能:
    - 動的電力制限の計算
    - エンタルピー増加制限の適用
    - より堅牢なエラーハンドリング
    """
    
    use_preheater = get_component_setting('use_preheater', False)
    use_superheater = get_component_setting('use_superheater', False)
    
    # 動的電力制限の計算
    if use_dynamic_limits:
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
            max_enthalpy_increase_kJ_per_kg=max_enthalpy_increase_kJ_per_kg,
        )
        
        # 実際の制限値は指定値と安全制限値の小さい方
        actual_max_preheater = min(max_preheater_power, safe_preheater_limit)
        actual_max_superheater = min(max_superheater_power, safe_superheater_limit)
    else:
        actual_max_preheater = max_preheater_power
        actual_max_superheater = max_superheater_power
    
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
                Q_preheater_kW_input=current_Q_preheater,
                Q_superheater_kW_input=current_Q_superheater,
            )
            
            if result is None:
                return 1e6  # 実行不可能解にペナルティ
            
            w_net = result.get("W_net [kW]", 0)
            if np.isnan(w_net) or w_net <= 0:
                return 1e6
                
            return -w_net  # 最大化のため符号反転
            
        except Exception:
            return 1e6  # エラー時のペナルティ
    
    # 最適化の実行
    optimization_run_success = False
    
    if use_preheater and use_superheater:
        # 両方使用する場合
        bounds = [(0, actual_max_preheater), (0, actual_max_superheater)]
        x0 = [min(1.0, actual_max_preheater/2), min(1.0, actual_max_superheater/2)]
        
        opt_result_obj = minimize(objective, x0=x0, bounds=bounds, method='L-BFGS-B')
        Q_preheater_opt, Q_superheater_opt = opt_result_obj.x if opt_result_obj.success else [0.0, 0.0]
        optimization_run_success = opt_result_obj.success
        
    elif use_preheater:
        # 予熱器のみ使用
        opt_result_obj = minimize_scalar(
            objective, 
            bounds=(0, actual_max_preheater), 
            method='bounded'
        )
        Q_preheater_opt = opt_result_obj.x if opt_result_obj.success else 0.0
        Q_superheater_opt = 0.0
        optimization_run_success = opt_result_obj.success
        
    elif use_superheater:
        # 過熱器のみ使用
        opt_result_obj = minimize_scalar(
            objective, 
            bounds=(0, actual_max_superheater), 
            method='bounded'
        )
        Q_preheater_opt = 0.0
        Q_superheater_opt = opt_result_obj.x if opt_result_obj.success else 0.0
        optimization_run_success = opt_result_obj.success
        
    else:
        # どちらも使用しない
        Q_preheater_opt = 0.0
        Q_superheater_opt = 0.0
        optimization_run_success = True
    
    # 最適解での最終計算
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
        Q_preheater_kW_input=Q_preheater_opt,
        Q_superheater_kW_input=Q_superheater_opt,
    )
    
    if final_result is not None:
        final_result.update({
            "Q_preheater_opt [kW]": Q_preheater_opt,
            "Q_superheater_opt [kW]": Q_superheater_opt,
            "optimization_success": optimization_run_success,
            "T_evap_out_target_param": T_evap_out_target,
            "max_preheater_power_used [kW]": actual_max_preheater,
            "max_superheater_power_used [kW]": actual_max_superheater,
            "dynamic_limits_applied": use_dynamic_limits,
        })
    else:
        final_result = {
            "Q_preheater_opt [kW]": Q_preheater_opt,
            "Q_superheater_opt [kW]": Q_superheater_opt,
            "optimization_success": False,
            "W_net [kW]": np.nan,
            "T_evap_out_target_param": T_evap_out_target,
            "max_preheater_power_used [kW]": actual_max_preheater,
            "max_superheater_power_used [kW]": actual_max_superheater,
            "dynamic_limits_applied": use_dynamic_limits,
        }
    
    return final_result


def sensitivity_analysis_components_safe(
    T_htf_in,
    Vdot_htf,
    T_cond,
    eta_pump,
    eta_turb,
    T_evap_out_target,
    component_power_range=None,
    use_dynamic_limits=True,
    **kwargs
):
    """
    安全な電力制限を使用した感度解析
    """
    
    use_preheater = get_component_setting('use_preheater', False)
    use_superheater = get_component_setting('use_superheater', False)
    
    # 動的制限の計算
    if use_dynamic_limits:
        safe_limit, _ = calculate_safe_power_limits(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            **kwargs
        )
        
        if component_power_range is None:
            # 安全制限内で範囲を設定
            component_power_range = np.linspace(0, safe_limit, 11)
        else:
            # 指定範囲を安全制限でクリップ
            component_power_range = np.clip(component_power_range, 0, safe_limit)
    else:
        if component_power_range is None:
            component_power_range = np.linspace(0, 20, 11)
    
    results = []
    
    for power in component_power_range:
        current_Q_preheater_sens = 0.0
        current_Q_superheater_sens = 0.0
        
        if use_preheater and use_superheater:
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
        
        except Exception:
            continue
    
    return {
        "sensitivity_results": results,
        "power_range": component_power_range.tolist(),
        "use_preheater": use_preheater,
        "use_superheater": use_superheater,
        "dynamic_limits_applied": use_dynamic_limits,
    }
