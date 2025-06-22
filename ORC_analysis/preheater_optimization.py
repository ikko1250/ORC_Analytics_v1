"""予熱器のみを使用したORC最適化計算

このファイルは、予熱器のみを使用したORC最適化計算を行い、
熱源温度と流量を変化させて発電効率を高める可能性のある部分を探索します。
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

# 日本語フォント設定
plt.rcParams['font.family'] = 'M+ 1c'

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ORC_analysis.config import set_component_setting, validate_component_settings
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.optimization import optimize_orc_with_components

def calculate_r245fa_saturation_temp(P_bar):
    """R245faの飽和温度を計算 (修正されたCorrelation)
    
    Args:
        P_bar: 圧力 [bar]
    
    Returns:
        飽和温度 [°C]
    """
    import math
    if P_bar <= 0:
        return -40  # デフォルト値
    
    # R245faの実験値に基づく近似式
    # P(bar) vs T_sat(°C)の関係: T_sat ≈ 13.8 * ln(P_bar) + 36.5
    try:
        T_sat = 13.8 * math.log(P_bar) + 36.5
        # 合理的な範囲に制限（R245faの実用範囲）
        T_sat = max(-40, min(T_sat, 120))
        return T_sat
    except (ValueError, ZeroDivisionError):
        # フォールバック：線形近似
        # 1bar → 15°C, 10bar → 70°C程度
        T_sat = 15 + (P_bar - 1) * 6.1
        return max(-40, min(T_sat, 120))


def optimize_preheater_only(
    T_htf_in: float,
    Vdot_htf: float,
    T_cond: float = 305.15,
    eta_pump: float = 0.75,
    eta_turb: float = 0.80,
    T_evap_out_target: float = 323.15,
    max_preheater_power: float = 30.0
) -> Optional[Dict]:
    """予熱器のみを使用したORC最適化計算
    
    Args:
        T_htf_in: 熱源入口温度 [K]
        Vdot_htf: 熱源流量 [m³/s]
        T_cond: 凝縮温度 [K]
        eta_pump: ポンプ効率 [-]
        eta_turb: タービン効率 [-]
        T_evap_out_target: 目標蒸発出口温度 [K]
        max_preheater_power: 予熱器最大電力 [kW]
    
    Returns:
        最適化結果辞書
    """
    # 予熱器のみを有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    set_component_setting('preheater_params', {
        'max_power_kW': max_preheater_power,
        'efficiency': 0.95
    })
    
    try:
        print(f"    最適化設定: max_preheater_power={max_preheater_power}kW, use_safety_limits=False")
        
        result = optimize_orc_with_components(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            T_evap_out_target=T_evap_out_target,
            max_preheater_power=max_preheater_power,
            use_safety_limits=False,  # 安全制限を無効化
        )
        
        if result:
            print(f"    最適化結果: success={result.get('optimization_success', False)}, Q_preheater_opt={result.get('Q_preheater_opt [kW]', 0):.3f}kW")
        
        # 予熱器なしの場合も計算（ベースライン）
        set_component_setting('use_preheater', False)
        set_component_setting('use_superheater', False)
        baseline_result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            Q_preheater_kW_input=0.0,
            Q_superheater_kW_input=0.0,
        )
        
        if result and baseline_result:
            result['baseline_W_net'] = baseline_result['W_net [kW]']
            result['baseline_eta_th'] = baseline_result['η_th [-]']
            
            # 最適化後の性能を明示的に再計算（設定が混在しないよう）
            optimized_power = result.get('W_net [kW]', 0)
            baseline_power = baseline_result['W_net [kW]']
            
            result['efficiency_improvement'] = (
                (optimized_power - baseline_power) / baseline_power * 100
            ) if baseline_power > 0 else 0.0  # パーセント
            
            print(f"    効率計算詳細: optimized={optimized_power:.3f}kW, baseline={baseline_power:.3f}kW")
        
        return result
        
    except Exception as e:
        print(f"最適化計算エラー: {e}")
        return None
    finally:
        # 設定を元に戻す
        set_component_setting('use_preheater', False)


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
        'optimal_preheater_powers': [],
        'net_powers': [],
        'pinch_point_data': [],  # ピンチポイント温度差データ
    }
    
    print("パラメータスイープ解析開始...")
    total_cases = len(T_htf_range) * len(Vdot_htf_range)
    case_count = 0
    
    for T_htf in T_htf_range:
        for Vdot_htf in Vdot_htf_range:
            case_count += 1
            print(f"ケース {case_count}/{total_cases}: T_htf={T_htf-273.15:.1f}°C, Vdot_htf={Vdot_htf:.3f}m³/s")
            
            result = optimize_preheater_only(
                T_htf_in=T_htf,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                T_evap_out_target=T_evap_out_target
            )
            
            # 予熱器効果の手動テスト（最適化が0kWの場合）
            if result and result.get('Q_preheater_opt [kW]', 0) <= 0.001:  # 0に近い値も含める
                print(f"    手動テスト: 予熱器5kW, 10kW, 15kWでの効果確認")
                
                for test_power in [5.0, 10.0, 15.0]:
                    set_component_setting('use_preheater', True)
                    set_component_setting('use_superheater', False)
                    try:
                        test_result = calculate_orc_performance_from_heat_source(
                            T_htf_in=T_htf,
                            Vdot_htf=Vdot_htf,
                            T_cond=T_cond,
                            eta_pump=eta_pump,
                            eta_turb=eta_turb,
                            Q_preheater_kW_input=test_power,
                            Q_superheater_kW_input=0.0,
                        )
                        if test_result:
                            baseline_power = result.get('baseline_W_net', 0)
                            test_net_power = test_result.get('W_net [kW]', 0)
                            test_improvement = (test_net_power - baseline_power) / baseline_power * 100 if baseline_power > 0 else 0
                            print(f"      {test_power}kW → 正味出力: {test_net_power:.3f}kW, 改善率: {test_improvement:.3f}%")
                    except Exception as e:
                        print(f"      {test_power}kW → エラー: {e}")
                    finally:
                        set_component_setting('use_preheater', False)
            
            # ピンチポイント温度差のトレース
            pinch_data = None
            if result and result.get('optimization_success', False):
                optimal_preheater_power = result.get('Q_preheater_opt [kW]', 0)
                
                # 最適条件でのピンチポイント解析
                set_component_setting('use_preheater', True)
                set_component_setting('preheater_params', {
                    'max_power_kW': 30.0,
                    'efficiency': 0.95
                })
                
                try:
                    # 最適化結果でORC計算を実行してピンチポイントデータを取得
                    detailed_result = calculate_orc_performance_from_heat_source(
                        T_htf_in=T_htf,
                        Vdot_htf=Vdot_htf,
                        T_cond=T_cond,
                        eta_pump=eta_pump,
                        eta_turb=eta_turb,
                        Q_preheater_kW_input=optimal_preheater_power,
                        Q_superheater_kW_input=0.0,
                    )
                    
                    if detailed_result:
                        T_htf_in_C = T_htf - 273.15
                        T_htf_out_C = detailed_result.get('T_htf_out [°C]', 0)
                        T_turb_in_C = detailed_result.get('T_turb_in [°C]', 0)
                        evap_lmtd = detailed_result.get('Evap_dT_lm [K]', 0)
                        
                        # より正確なピンチポイント解析
                        # 高温端アプローチ: HTF入口 - 作動流体出口
                        high_end_approach = T_htf_in_C - T_turb_in_C
                        
                        # 低温端アプローチ: HTF出口 - 作動流体入口（飽和温度）
                        # 蒸発圧力から飽和温度を推定
                        P_evap_bar = detailed_result.get('P_evap [bar]', 0)
                        P_evap_kPa = P_evap_bar * 100  # kPaに変換
                        
                        # R245faの正確な飽和温度を計算
                        T_sat_approx = calculate_r245fa_saturation_temp(P_evap_bar)
                        
                        low_end_approach = T_htf_out_C - T_sat_approx
                        
                        actual_pinch = min(high_end_approach, low_end_approach)
                        
                        pinch_data = {
                            'T_htf_in': T_htf_in_C,
                            'T_htf_out': T_htf_out_C,
                            'T_turb_in': T_turb_in_C,
                            'T_sat_evap_approx': T_sat_approx,
                            'Evap_dT_lm': evap_lmtd,
                            'P_evap': P_evap_bar,
                            'Q_preheater_opt': optimal_preheater_power,
                            'pinch_delta_used': 10.0,  # デフォルト値
                            'high_end_approach': high_end_approach,
                            'low_end_approach': low_end_approach,
                            'actual_min_dT': actual_pinch
                        }
                        
                        print(f"  温度解析: HTF({T_htf_in_C:.1f}→{T_htf_out_C:.1f}°C), 作動流体({T_sat_approx:.1f}→{T_turb_in_C:.1f}°C)")
                        print(f"  ピンチポイント: LMTD={evap_lmtd:.2f}K, 高温端ΔT={high_end_approach:.2f}K, 低温端ΔT={low_end_approach:.2f}K")
                        print(f"  圧力情報: P_evap={P_evap_bar:.1f}bar ({P_evap_kPa:.0f}kPa)")
                        
                        # 効率改善の診断
                        if result:
                            baseline_power = result.get('baseline_W_net', 0)
                            optimized_power = result.get('W_net [kW]', 0)
                            improvement = result.get('efficiency_improvement', 0)
                            preheater_power = result.get('Q_preheater_opt [kW]', 0)
                            print(f"  効率診断: ベースライン={baseline_power:.3f}kW, 最適化後={optimized_power:.3f}kW, 改善={improvement:.2f}%, 予熱器={preheater_power:.3f}kW")
                        
                        # 異常値の警告
                        if T_turb_in_C > 150:
                            print(f"  ⚠️  警告: タービン入口温度が異常に高い ({T_turb_in_C:.1f}°C > 150°C)")
                        if abs(low_end_approach) > 50:
                            print(f"  ⚠️  警告: 低温端アプローチが異常 ({low_end_approach:.1f}K)")
                        if P_evap_bar > 35:
                            print(f"  ⚠️  警告: 蒸発圧力が異常に高い ({P_evap_bar:.1f}bar)")
                        if improvement == 0 and preheater_power > 0:
                            print(f"  ⚠️  効率改善なし: 予熱器電力={preheater_power:.3f}kW")
                        elif improvement > 0:
                            print(f"  ✅  効率改善成功: +{improvement:.2f}%")
                    
                except Exception as e:
                    print(f"  ピンチポイント解析エラー: {e}")
                finally:
                    set_component_setting('use_preheater', False)
            
            if result and result.get('optimization_success', False):
                results['optimization_results'].append(result)
                results['efficiency_improvements'].append(result.get('efficiency_improvement', 0))
                results['optimal_preheater_powers'].append(result.get('Q_preheater_opt [kW]', 0))
                results['net_powers'].append(result.get('W_net [kW]', 0))
                results['pinch_point_data'].append(pinch_data)
            else:
                results['optimization_results'].append(None)
                results['efficiency_improvements'].append(0)
                results['optimal_preheater_powers'].append(0)
                results['net_powers'].append(0)
                results['pinch_point_data'].append(None)
    
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
    optimal_powers = np.array(results['optimal_preheater_powers'])
    net_powers = np.array(results['net_powers'])
    
    # ピンチポイントデータの抽出
    pinch_data_list = results['pinch_point_data']
    lmtd_values = []
    min_dt_values = []
    
    for data in pinch_data_list:
        if data is not None:
            lmtd_values.append(data['Evap_dT_lm'])
            min_dt_values.append(data['actual_min_dT'])
        else:
            lmtd_values.append(0)
            min_dt_values.append(0)
    
    lmtd_array = np.array(lmtd_values)
    min_dt_array = np.array(min_dt_values)
    
    # データを2Dマトリックスに変換
    n_T = len(T_htf_values)
    n_V = len(Vdot_htf_values)
    
    efficiency_matrix = efficiency_improvements.reshape(n_T, n_V)
    power_matrix = optimal_powers.reshape(n_T, n_V)
    net_power_matrix = net_powers.reshape(n_T, n_V)
    lmtd_matrix = lmtd_array.reshape(n_T, n_V)
    min_dt_matrix = min_dt_array.reshape(n_T, n_V)
    
    # 温度を摂氏に変換
    T_celsius = T_htf_values - 273.15
    
    # 5つのサブプロット（ピンチポイント関連を追加）
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # 効率改善率のコンターマップ
    im1 = axes[0, 0].contourf(Vdot_htf_values, T_celsius, efficiency_matrix, 
                             levels=20, cmap='RdYlBu_r')
    axes[0, 0].set_xlabel('熱源流量 [m³/s]')
    axes[0, 0].set_ylabel('熱源温度 [°C]')
    axes[0, 0].set_title('効率改善率 [%]')
    plt.colorbar(im1, ax=axes[0, 0])
    
    # 最適予熱器電力のコンターマップ
    im2 = axes[0, 1].contourf(Vdot_htf_values, T_celsius, power_matrix, 
                             levels=20, cmap='viridis')
    axes[0, 1].set_xlabel('熱源流量 [m³/s]')
    axes[0, 1].set_ylabel('熱源温度 [°C]')
    axes[0, 1].set_title('最適予熱器電力 [kW]')
    plt.colorbar(im2, ax=axes[0, 1])
    
    # 正味出力のコンターマップ
    im3 = axes[0, 2].contourf(Vdot_htf_values, T_celsius, net_power_matrix, 
                             levels=20, cmap='plasma')
    axes[0, 2].set_xlabel('熱源流量 [m³/s]')
    axes[0, 2].set_ylabel('熱源温度 [°C]')
    axes[0, 2].set_title('正味出力 [kW]')
    plt.colorbar(im3, ax=axes[0, 2])
    
    # 蒸発器LMTD（対数平均温度差）のコンターマップ
    im4 = axes[1, 0].contourf(Vdot_htf_values, T_celsius, lmtd_matrix, 
                             levels=20, cmap='coolwarm')
    axes[1, 0].set_xlabel('熱源流量 [m³/s]')
    axes[1, 0].set_ylabel('熱源温度 [°C]')
    axes[1, 0].set_title('蒸発器LMTD [K]')
    plt.colorbar(im4, ax=axes[1, 0])
    
    # 最小温度差（近似ピンチポイント）のコンターマップ
    im5 = axes[1, 1].contourf(Vdot_htf_values, T_celsius, min_dt_matrix, 
                             levels=20, cmap='YlOrRd_r')
    axes[1, 1].set_xlabel('熱源流量 [m³/s]')
    axes[1, 1].set_ylabel('熱源温度 [°C]')
    axes[1, 1].set_title('最小温度差 [K]')
    plt.colorbar(im5, ax=axes[1, 1])
    
    # 空きスペースを使用してピンチポイント制約の可視化
    axes[1, 2].remove()  # 元のサブプロットを削除
    ax_constraint = plt.subplot(2, 3, 6)  # 新しいサブプロットを作成
    
    # ピンチポイント制約（10K未満）の領域をマーク
    constraint_violation = min_dt_matrix < 10.0
    ax_constraint.contourf(Vdot_htf_values, T_celsius, constraint_violation.astype(int), 
                          levels=[0, 0.5, 1], colors=['lightgreen', 'orange'], alpha=0.7)
    ax_constraint.set_xlabel('熱源流量 [m³/s]')
    ax_constraint.set_ylabel('熱源温度 [°C]')
    ax_constraint.set_title('ピンチポイント制約\n(赤: ΔT<10K)')
    
    # 効率改善率のコンターラインをオーバーレイ
    cs = ax_constraint.contour(Vdot_htf_values, T_celsius, efficiency_matrix, 
                              levels=10, colors='black', alpha=0.5, linewidths=0.5)
    ax_constraint.clabel(cs, inline=True, fontsize=8)
    
    plt.tight_layout()
    plt.savefig('preheater_optimization_results.png', dpi=300, bbox_inches='tight')
    plt.show()
    plt.close(fig)
    
    # 最良条件の特定
    max_improvement_idx = np.argmax(efficiency_improvements)
    best_T_htf = T_htf_values[max_improvement_idx // n_V]
    best_Vdot_htf = Vdot_htf_values[max_improvement_idx % n_V]
    best_improvement = efficiency_improvements[max_improvement_idx]
    best_power = optimal_powers[max_improvement_idx]
    best_lmtd = lmtd_array[max_improvement_idx]
    best_min_dt = min_dt_array[max_improvement_idx]
    
    print(f"\n最高効率改善条件:")
    print(f"  熱源温度: {best_T_htf-273.15:.1f}°C")
    print(f"  熱源流量: {best_Vdot_htf:.4f} m³/s")
    print(f"  効率改善率: {best_improvement:.2f}%")
    print(f"  最適予熱器電力: {best_power:.2f} kW")
    print(f"  蒸発器LMTD: {best_lmtd:.2f} K")
    print(f"  最小温度差: {best_min_dt:.2f} K")
    
    # ピンチポイント制約違反の統計
    constraint_violations = np.sum(min_dt_matrix < 10.0)
    total_successful = np.sum(efficiency_improvements > 0)
    if total_successful > 0:
        violation_rate = constraint_violations / total_successful * 100
        print(f"\nピンチポイント制約解析:")
        print(f"  制約違反ケース数: {constraint_violations}/{total_successful} ({violation_rate:.1f}%)")
        print(f"  平均LMTD: {np.mean(lmtd_array[lmtd_array > 0]):.2f} K")
        print(f"  平均最小温度差: {np.mean(min_dt_array[min_dt_array > 0]):.2f} K")


def main():
    """メイン実行関数"""
    print("予熱器最適化解析システム")
    print("=" * 50)
    
    try:
        # 設定検証
        validate_component_settings()
        print("設定検証: OK\n")
        
        # 飽和温度計算の検証
        print("R245fa飽和温度検証:")
        for P_test in [1.0, 2.5, 5.0, 10.0]:
            T_sat = calculate_r245fa_saturation_temp(P_test)
            print(f"  {P_test:.1f}bar → {T_sat:.1f}°C")
        print()
        
        # パラメータ範囲設定（テスト用に縮小）
        T_htf_range = np.linspace(333.15, 343.15, 2)  # 60-70°C (2点) - テスト用
        Vdot_htf_range = np.linspace(0.010, 0.015, 2)  # 0.010-0.015 m³/s (2点) - テスト用
        
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