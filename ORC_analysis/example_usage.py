"""ORC解析システムの使用例

このファイルは、新しく追加されたpreheater/superheaterコンポーネントと
最適化機能の使用方法を示します。
"""

from ORC_analysis.config import set_component_setting, validate_component_settings
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.optimization import optimize_orc_with_components, sensitivity_analysis_components


def example_basic_orc():
    """基本的なORC計算の例"""
    print("=== 基本的なORC計算 ===")
    
    # パラメータ設定
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    
    # 計算実行
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
    )
    
    if result:
        print(f"正味出力: {result['W_net [kW]']:.2f} kW")
        print(f"熱効率: {result['η_th [-]']:.3f}")
        print(f"蒸発圧力: {result['P_evap [bar]']:.2f} bar")
    else:
        print("計算に失敗しました")


def example_with_preheater():
    """予熱器を使用したORC計算の例"""
    print("\n=== 予熱器使用ORC計算 ===")
    
    # 予熱器を有効化
    set_component_setting('use_preheater', True)
    set_component_setting('preheater_params', {
        'max_power_kW': 30.0,
        'efficiency': 0.95
    })
    
    # パラメータ設定
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    
    # 計算実行
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
    )
    
    if result:
        print(f"正味出力: {result['W_net [kW]']:.2f} kW")
        print(f"熱効率: {result['η_th [-]']:.3f}")
        print(f"予熱器使用: {result['use_preheater']}")
        print(f"予熱器電力: {result.get('Q_preheater_kW', 0):.2f} kW")
    else:
        print("計算に失敗しました")
    
    # 設定を元に戻す
    set_component_setting('use_preheater', False)


def example_with_superheater():
    """過熱器を使用したORC計算の例"""
    print("\n=== 過熱器使用ORC計算 ===")
    
    # 過熱器を有効化
    set_component_setting('use_superheater', True)
    set_component_setting('superheater_params', {
        'max_power_kW': 50.0,
        'efficiency': 0.95
    })
    
    # パラメータ設定
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    
    # 計算実行
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
    )
    
    if result:
        print(f"正味出力: {result['W_net [kW]']:.2f} kW")
        print(f"熱効率: {result['η_th [-]']:.3f}")
        print(f"過熱器使用: {result['use_superheater']}")
        print(f"過熱器電力: {result.get('Q_superheater_kW', 0):.2f} kW")
    else:
        print("計算に失敗しました")
    
    # 設定を元に戻す
    set_component_setting('use_superheater', False)


def example_optimization():
    """最適化計算の例"""
    print("\n=== 最適化計算 ===")
    
    # 過熱器を有効化
    set_component_setting('use_superheater', True)
    
    # パラメータ設定
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    T_evap_out_target = 453.15  # 180°C
    
    # 最適化実行
    result = optimize_orc_with_components(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        T_evap_out_target=T_evap_out_target,
    )
    
    if result and result.get('optimization_success', False):
        print(f"最適化成功")
        print(f"最適正味出力: {result['W_net [kW]']:.2f} kW")
        print(f"最適過熱器電力: {result['Q_superheater_opt [kW]']:.2f} kW")
        print(f"最適予熱器電力: {result['Q_preheater_opt [kW]']:.2f} kW")
    else:
        print("最適化に失敗しました")
    
    # 設定を元に戻す
    set_component_setting('use_superheater', False)


def example_sensitivity_analysis():
    """感度解析の例"""
    print("\n=== 感度解析 ===")
    
    # 過熱器を有効化
    set_component_setting('use_superheater', True)
    
    # パラメータ設定
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    T_evap_out_target = 453.15  # 180°C
    
    # 感度解析実行（簡略化版）
    import numpy as np
    power_range = np.linspace(0, 50, 6)  # 0-50kWを6点
    
    results = sensitivity_analysis_components(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        T_evap_out_target=T_evap_out_target,
        component_power_range=power_range,
    )
    
    print(f"感度解析結果数: {len(results['sensitivity_results'])}")
    if results['sensitivity_results']:
        for i, result in enumerate(results['sensitivity_results']):
            power = power_range[i]
            net_power = result['W_net [kW]']
            print(f"  過熱器電力 {power:.1f} kW → 正味出力 {net_power:.2f} kW")
    
    # 設定を元に戻す
    set_component_setting('use_superheater', False)


def main():
    """メイン実行関数"""
    print("ORC解析システム使用例")
    print("=" * 50)
    
    try:
        # 設定検証
        validate_component_settings()
        print("設定検証: OK\n")
        
        # 各例の実行
        example_basic_orc()
        example_with_preheater()
        example_with_superheater()
        example_optimization()
        example_sensitivity_analysis()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    
    print("\n" + "=" * 50)
    print("実行完了")


if __name__ == "__main__":
    main()