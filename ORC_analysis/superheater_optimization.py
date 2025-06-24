"""過熱器のみを使用したORC最適化計算

このファイルは、過熱器のみを使用したORC最適化計算を行い、
熱源温度と流量を変化させて発電効率を高める可能性のある部分を探索します。
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

# 日本語フォント設定
plt.rcParams['font.family'] = 'M+ 1c'

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORC_analysis.config import set_component_setting, validate_component_settings
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.optimization import optimize_orc_with_components


def optimize_superheater_only(
    T_htf_in: float,
    Vdot_htf: float,
    T_cond: float = 305.15,
    eta_pump: float = 0.75,
    eta_turb: float = 0.80,
    T_evap_out_target: float = 323.15,
    max_superheater_power: float = 50.0
) -> Optional[Dict]:
    """過熱器のみを使用したORC最適化計算
    
    Args:
        T_htf_in: 熱源入口温度 [K]
        Vdot_htf: 熱源流量 [m³/s]
        T_cond: 凝縮温度 [K]
        eta_pump: ポンプ効率 [-]
        eta_turb: タービン効率 [-]
        T_evap_out_target: 目標蒸発出口温度 [K]
        max_superheater_power: 過熱器最大電力 [kW]
    
    Returns:
        最適化結果辞書
    """
    # 過熱器のみを有効化
    set_component_setting('use_superheater', True)
    set_component_setting('use_preheater', False)
    set_component_setting('superheater_params', {
        'max_power_kW': max_superheater_power,
        'efficiency': 0.95
    })
    
    try:
        result = optimize_orc_with_components(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            T_evap_out_target=T_evap_out_target,
            max_superheater_power=max_superheater_power,
            use_safety_limits=False,  # 安全制限を無効化
        )
        
        # 過熱器なしの場合も計算
        set_component_setting('use_superheater', False)
        baseline_result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
        )
        
        if result and baseline_result:
            result['baseline_W_net'] = baseline_result['W_net [kW]']
            result['baseline_eta_th'] = baseline_result['η_th [-]']
            result['efficiency_improvement'] = (
                result['W_net [kW]'] - baseline_result['W_net [kW]']
            ) / baseline_result['W_net [kW]'] * 100  # パーセント
        
        return result
        
    except Exception as e:
        print(f"最適化計算エラー: {e}")
        return None
    finally:
        # 設定を元に戻す
        set_component_setting('use_superheater', False)


def parameter_sweep_analysis(
    T_htf_range: List[float],
    Vdot_htf_range: List[float],
    T_cond: float = 305.15,
    eta_pump: float = 0.75,
    eta_turb: float = 0.80,
    T_evap_out_target: float = 323.15
) -> Dict:
    """熱源温度と流量をスイープして最適化解析
    
    Args:
        T_htf_range: 熱源温度範囲 [K]
        Vdot_htf_range: 熱源流量範囲 [m³/s]
        T_cond: 凝縮温度 [K]
        eta_pump: ポンプ効率 [-]
        eta_turb: タービン効率 [-]
        T_evap_out_target: 目標蒸発出口温度 [K]
    
    Returns:
        解析結果辞書
    """
    results = {
        'T_htf_values': T_htf_range,
        'Vdot_htf_values': Vdot_htf_range,
        'optimization_results': [],
        'efficiency_improvements': [],
        'optimal_superheater_powers': [],
        'net_powers': [],
    }
    
    print("パラメータスイープ解析開始...")
    total_cases = len(T_htf_range) * len(Vdot_htf_range)
    case_count = 0
    
    for T_htf in T_htf_range:
        for Vdot_htf in Vdot_htf_range:
            case_count += 1
            print(f"ケース {case_count}/{total_cases}: T_htf={T_htf-273.15:.1f}°C, Vdot_htf={Vdot_htf:.3f}m³/s")
            
            result = optimize_superheater_only(
                T_htf_in=T_htf,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                T_evap_out_target=T_evap_out_target
            )
            
            if result and result.get('optimization_success', False):
                results['optimization_results'].append(result)
                results['efficiency_improvements'].append(result.get('efficiency_improvement', 0))
                results['optimal_superheater_powers'].append(result.get('Q_superheater_opt [kW]', 0))
                results['net_powers'].append(result.get('W_net [kW]', 0))
            else:
                results['optimization_results'].append(None)
                results['efficiency_improvements'].append(0)
                results['optimal_superheater_powers'].append(0)
                results['net_powers'].append(0)
    
    print("パラメータスイープ解析完了")
    return results


def visualize_results(results: Dict) -> None:
    """結果の可視化
    
    Args:
        results: parameter_sweep_analysis の結果
    """
    T_htf_values = np.array(results['T_htf_values'])
    Vdot_htf_values = np.array(results['Vdot_htf_values'])
    efficiency_improvements = np.array(results['efficiency_improvements'])
    optimal_powers = np.array(results['optimal_superheater_powers'])
    net_powers = np.array(results['net_powers'])
    
    # データを2Dマトリックスに変換
    n_T = len(T_htf_values)
    n_V = len(Vdot_htf_values)
    
    efficiency_matrix = efficiency_improvements.reshape(n_T, n_V)
    power_matrix = optimal_powers.reshape(n_T, n_V)
    net_power_matrix = net_powers.reshape(n_T, n_V)
    
    # 温度を摂氏に変換
    T_celsius = T_htf_values - 273.15
    
    # 3つのサブプロット
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # 効率改善率のコンターマップ
    im1 = axes[0].contourf(Vdot_htf_values, T_celsius, efficiency_matrix, 
                          levels=20, cmap='RdYlBu_r')
    axes[0].set_xlabel('熱源流量 [m³/s]')
    axes[0].set_ylabel('熱源温度 [°C]')
    axes[0].set_title('効率改善率 [%]')
    plt.colorbar(im1, ax=axes[0])
    
    # 最適過熱器電力のコンターマップ
    im2 = axes[1].contourf(Vdot_htf_values, T_celsius, power_matrix, 
                          levels=20, cmap='viridis')
    axes[1].set_xlabel('熱源流量 [m³/s]')
    axes[1].set_ylabel('熱源温度 [°C]')
    axes[1].set_title('最適過熱器電力 [kW]')
    plt.colorbar(im2, ax=axes[1])
    
    # 正味出力のコンターマップ
    im3 = axes[2].contourf(Vdot_htf_values, T_celsius, net_power_matrix, 
                          levels=20, cmap='plasma')
    axes[2].set_xlabel('熱源流量 [m³/s]')
    axes[2].set_ylabel('熱源温度 [°C]')
    axes[2].set_title('正味出力 [kW]')
    plt.colorbar(im3, ax=axes[2])
    
    plt.tight_layout()
    plt.savefig('superheater_optimization_results.png', dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)
    
    # 最良条件の特定
    max_improvement_idx = np.argmax(efficiency_improvements)
    best_T_htf = T_htf_values[max_improvement_idx // n_V]
    best_Vdot_htf = Vdot_htf_values[max_improvement_idx % n_V]
    best_improvement = efficiency_improvements[max_improvement_idx]
    best_power = optimal_powers[max_improvement_idx]
    
    print(f"\n最高効率改善条件:")
    print(f"  熱源温度: {best_T_htf-273.15:.1f}°C")
    print(f"  熱源流量: {best_Vdot_htf:.4f} m³/s")
    print(f"  効率改善率: {best_improvement:.2f}%")
    print(f"  最適過熱器電力: {best_power:.2f} kW")


def main():
    """メイン実行関数"""
    print("過熱器最適化解析システム")
    print("=" * 50)
    
    try:
        # 設定検証
        validate_component_settings()
        print("設定検証: OK\n")
        
        # パラメータ範囲設定
        T_htf_range = np.linspace(333.15, 373.15, 5)  # 60-100°C (5点)
        Vdot_htf_range = np.linspace(0.005, 0.020, 4)  # 0.005-0.020 m³/s (4点)
        
        print(f"解析条件:")
        print(f"  熱源温度範囲: {T_htf_range[0]-273.15:.1f}-{T_htf_range[-1]-273.15:.1f}°C ({len(T_htf_range)}点)")
        print(f"  熱源流量範囲: {Vdot_htf_range[0]:.3f}-{Vdot_htf_range[-1]:.3f} m³/s ({len(Vdot_htf_range)}点)")
        print(f"  総計算ケース数: {len(T_htf_range) * len(Vdot_htf_range)}\n")
        
        # パラメータスイープ解析実行
        results = parameter_sweep_analysis(
            T_htf_range=T_htf_range.tolist(),
            Vdot_htf_range=Vdot_htf_range.tolist()
        )
        
        # 結果の可視化
        print("\n結果を可視化中...")
        visualize_results(results)
        
        # 成功したケース数の報告
        successful_cases = sum(1 for r in results['optimization_results'] if r is not None)
        total_cases = len(results['optimization_results'])
        print(f"\n最適化成功率: {successful_cases}/{total_cases} ({successful_cases/total_cases*100:.1f}%)")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("実行完了")


if __name__ == "__main__":
    main()