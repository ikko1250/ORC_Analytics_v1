"""最適化計算のデバッグ用スクリプト

効率改善が正しく計算されているかを詳細に検証します。
"""

import sys
import os
import numpy as np

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORC_analysis.config import set_component_setting, validate_component_settings
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.optimization import optimize_orc_with_components


def debug_single_case():
    """単一ケースでの詳細デバッグ"""
    print("=== 単一ケースデバッグ ===")
    
    # example_usage.pyと同じ条件を使用
    T_htf_in = 343.15  # 70°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    T_evap_out_target = 323.15  # 50°C
    
    print(f"条件: T_htf={T_htf_in-273.15:.1f}°C, Vdot_htf={Vdot_htf:.3f}m³/s")
    
    # 1. ベースライン計算（コンポーネントなし）
    print("\n1. ベースライン計算...")
    baseline_result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
    )
    
    if baseline_result:
        print(f"  ベースライン正味出力: {baseline_result['W_net [kW]']:.3f} kW")
        print(f"  ベースライン熱効率: {baseline_result['η_th [-]']:.4f}")
    else:
        print("  ベースライン計算失敗")
        return
    
    # 2. 予熱器のみ（固定電力）
    print("\n2. 予熱器テスト（固定電力10kW）...")
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    set_component_setting('preheater_params', {
        'max_power_kW': 30.0,
        'efficiency': 0.95
    })
    
    preheater_result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        Q_preheater_kW_input=10.0,
    )
    
    if preheater_result:
        improvement = (preheater_result['W_net [kW]'] - baseline_result['W_net [kW]']) / baseline_result['W_net [kW]'] * 100
        print(f"  予熱器あり正味出力: {preheater_result['W_net [kW]']:.3f} kW")
        print(f"  予熱器あり熱効率: {preheater_result['η_th [-]']:.4f}")
        print(f"  効率改善率: {improvement:.2f}%")
    else:
        print("  予熱器計算失敗")
    
    # 3. 予熱器最適化
    print("\n3. 予熱器最適化計算...")
    optimization_result = optimize_orc_with_components(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        T_evap_out_target=T_evap_out_target,
        max_preheater_power=30.0,
        use_safety_limits=False,
    )
    
    if optimization_result and optimization_result.get('optimization_success', False):
        opt_improvement = (optimization_result['W_net [kW]'] - baseline_result['W_net [kW]']) / baseline_result['W_net [kW]'] * 100
        print(f"  最適化成功: True")
        print(f"  最適予熱器電力: {optimization_result['Q_preheater_opt [kW]']:.3f} kW")
        print(f"  最適化後正味出力: {optimization_result['W_net [kW]']:.3f} kW")
        print(f"  最適化効率改善率: {opt_improvement:.2f}%")
    else:
        print(f"  最適化失敗")
        if optimization_result:
            print(f"  optimization_success: {optimization_result.get('optimization_success', 'N/A')}")
            print(f"  applied_preheater_limit: {optimization_result.get('applied_preheater_limit [kW]', 'N/A')} kW")
    
    # 4. 過熱器テスト
    print("\n4. 過熱器テスト（固定電力15kW）...")
    set_component_setting('use_preheater', False)
    set_component_setting('use_superheater', True)
    set_component_setting('superheater_params', {
        'max_power_kW': 50.0,
        'efficiency': 0.95
    })
    
    superheater_result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        Q_superheater_kW_input=15.0,
    )
    
    if superheater_result:
        improvement = (superheater_result['W_net [kW]'] - baseline_result['W_net [kW]']) / baseline_result['W_net [kW]'] * 100
        print(f"  過熱器あり正味出力: {superheater_result['W_net [kW]']:.3f} kW")
        print(f"  過熱器あり熱効率: {superheater_result['η_th [-]']:.4f}")
        print(f"  効率改善率: {improvement:.2f}%")
    else:
        print("  過熱器計算失敗")
    
    # 設定をリセット
    set_component_setting('use_preheater', False)
    set_component_setting('use_superheater', False)


def test_parameter_ranges():
    """パラメータ範囲での効率改善テスト"""
    print("\n=== パラメータ範囲テスト ===")
    
    T_htf_values = [333.15, 353.15, 373.15]  # 60, 80, 100°C
    Vdot_htf_values = [0.005, 0.01, 0.015]   # 異なる流量
    
    set_component_setting('use_preheater', True)
    set_component_setting('preheater_params', {
        'max_power_kW': 30.0,
        'efficiency': 0.95
    })
    
    for T_htf in T_htf_values:
        for Vdot_htf in Vdot_htf_values:
            print(f"\n条件: T_htf={T_htf-273.15:.0f}°C, Vdot_htf={Vdot_htf:.3f}m³/s")
            
            # ベースライン
            baseline = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf,
                Vdot_htf=Vdot_htf,
                T_cond=305.15,
                eta_pump=0.75,
                eta_turb=0.80,
            )
            
            # 予熱器あり
            with_preheater = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf,
                Vdot_htf=Vdot_htf,
                T_cond=305.15,
                eta_pump=0.75,
                eta_turb=0.80,
                Q_preheater_kW_input=10.0,
            )
            
            if baseline and with_preheater:
                improvement = (with_preheater['W_net [kW]'] - baseline['W_net [kW]']) / baseline['W_net [kW]'] * 100
                print(f"  ベースライン: {baseline['W_net [kW]']:.3f} kW")
                print(f"  予熱器あり: {with_preheater['W_net [kW]']:.3f} kW")
                print(f"  改善率: {improvement:.2f}%")
            else:
                print("  計算失敗")
    
    set_component_setting('use_preheater', False)


def main():
    """メイン実行関数"""
    print("最適化計算デバッグ")
    print("=" * 50)
    
    try:
        validate_component_settings()
        debug_single_case()
        test_parameter_ranges()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("デバッグ完了")


if __name__ == "__main__":
    main()