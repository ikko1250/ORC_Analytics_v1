"""ORC最適化計算モジュール

蒸発器出口温度を目標として、正味出力を最大化するための最適化機能を提供します。
"""

import numpy as np
from scipy.optimize import minimize_scalar, minimize
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.config import get_component_setting


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
        
    Returns:
        dict: 最適化結果
    """
    
    use_preheater = get_component_setting('use_preheater', False)
    use_superheater = get_component_setting('use_superheater', False)
    
    def objective(params):
        """目的関数：正味出力を最大化（符号反転）"""
        if use_preheater and use_superheater:
            Q_preheater, Q_superheater = params
        elif use_preheater:
            Q_preheater = params[0]
            Q_superheater = 0.0
        elif use_superheater:
            Q_preheater = 0.0
            Q_superheater = params[0]
        else:
            Q_preheater = 0.0
            Q_superheater = 0.0
        
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
                T_evap_out_target=T_evap_out_target,
            )
            
            if result is None:
                return 1e6  # 実行不可能解にペナルティ
            
            return -result["W_net [kW]"]  # 最大化のため符号反転
            
        except Exception:
            return 1e6  # エラー時のペナルティ
    
    # 最適化の実行
    if use_preheater and use_superheater:
        # 両方使用する場合
        bounds = [(0, max_preheater_power), (0, max_superheater_power)]
        result = minimize(objective, x0=[10.0, 10.0], bounds=bounds, method='L-BFGS-B')
        Q_preheater_opt, Q_superheater_opt = result.x if result.success else [0.0, 0.0]
    elif use_preheater:
        # 予熱器のみ使用
        result = minimize_scalar(objective, bounds=(0, max_preheater_power), method='bounded')
        Q_preheater_opt = result.x if result.success else 0.0
        Q_superheater_opt = 0.0
    elif use_superheater:
        # 過熱器のみ使用
        result = minimize_scalar(objective, bounds=(0, max_superheater_power), method='bounded')
        Q_preheater_opt = 0.0
        Q_superheater_opt = result.x if result.success else 0.0
    else:
        # どちらも使用しない
        Q_preheater_opt = 0.0
        Q_superheater_opt = 0.0
    
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
        T_evap_out_target=T_evap_out_target,
    )
    
    if final_result is not None:
        final_result.update({
            "Q_preheater_opt [kW]": Q_preheater_opt,
            "Q_superheater_opt [kW]": Q_superheater_opt,
            "optimization_success": True,
        })
    else:
        final_result = {
            "Q_preheater_opt [kW]": Q_preheater_opt,
            "Q_superheater_opt [kW]": Q_superheater_opt,
            "optimization_success": False,
            "W_net [kW]": 0.0,
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
        **kwargs: その他のパラメータ
        
    Returns:
        dict: 感度解析結果
    """
    
    use_preheater = get_component_setting('use_preheater', False)
    use_superheater = get_component_setting('use_superheater', False)
    
    results = []
    
    for power in component_power_range:
        if use_preheater and use_superheater:
            # 両方使用する場合は簡略化して同じ電力を使用
            Q_preheater = power
            Q_superheater = power
        elif use_preheater:
            Q_preheater = power
            Q_superheater = 0.0
        elif use_superheater:
            Q_preheater = 0.0
            Q_superheater = power
        else:
            Q_preheater = 0.0
            Q_superheater = 0.0
        
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                T_evap_out_target=T_evap_out_target,
                **kwargs
            )
            
            if result is not None:
                result.update({
                    "Q_preheater_test [kW]": Q_preheater,
                    "Q_superheater_test [kW]": Q_superheater,
                })
                results.append(result)
        
        except Exception:
            continue
    
    return {
        "sensitivity_results": results,
        "power_range": component_power_range.tolist(),
        "use_preheater": use_preheater,
        "use_superheater": use_superheater,
    }