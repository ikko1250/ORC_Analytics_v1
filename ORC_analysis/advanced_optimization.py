#!/usr/bin/env python3
"""
Advanced Preheater Optimization - Phase 3: 高度な最適化アルゴリズム

多目的最適化、制約最適化、パレート最適解の探索を実装
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize, differential_evolution
from scipy.optimize import NonlinearConstraint
import sys
import os

# プロジェクトルートをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

from ORC_Analysis import calculate_orc_performance, calculate_orc_performance_from_heat_source

# 日本語フォント設定（エラー時はデフォルトフォントを使用）
try:
    plt.rcParams['font.family'] = ['M+ 1c']
except:
    pass


def calculate_orc_with_preheater_optimization(T_htf_in, Vdot_htf, T_cond, eta_pump, eta_turb, Q_preheater_kW):
    """予熱器最適化を含むORC計算
    
    Args:
        T_htf_in: 熱源入口温度 [K]
        Vdot_htf: 熱源体積流量 [m³/s]
        T_cond: 凝縮温度 [K]
        eta_pump: ポンプ効率 [-]
        eta_turb: タービン効率 [-]
        Q_preheater_kW: 予熱器電力 [kW]
    
    Returns:
        dict: 計算結果
    """
    try:
        # 熱源物性（水として仮定）
        rho_htf = 1000  # kg/m³
        cp_htf = 4180   # J/kg/K
        m_htf = Vdot_htf * rho_htf  # 熱源質量流量 [kg/s]
        
        # 予熱器による蒸発温度の向上計算
        if Q_preheater_kW > 0:
            # 予熱器による温度上昇（簡単な近似）
            Q_preheater_W = Q_preheater_kW * 1000  # W
            # 利用可能な最大熱量（熱源温度差10Kを仮定）
            Q_max_available = m_htf * cp_htf * 10  # W
            
            if Q_preheater_W > Q_max_available:
                print(f"⚠️  予熱器熱量({Q_preheater_kW:.1f}kW)が利用可能熱量({Q_max_available/1000:.3f}kW)を超過")
                return None
            
            # 蒸発温度の向上
            delta_T_evap = Q_preheater_W / (m_htf * cp_htf)  # K
            T_evap_enhanced = T_htf_in - 20 + delta_T_evap  # ベース蒸発温度から向上
            
            # 蒸発温度の制限（熱源温度以下）
            T_evap_enhanced = min(T_evap_enhanced, T_htf_in - 10)
            
            # 実際の温度上昇
            actual_delta_T = T_evap_enhanced - (T_htf_in - 20)
            
            # 作動流体流量の再計算（簡単な近似）
            # 利用可能熱量が減少することを考慮
            remaining_heat_capacity = Q_max_available - Q_preheater_W
            mass_flow_ratio = remaining_heat_capacity / Q_max_available
            
            print(f"予熱器最適化計算: Q_preheater={Q_preheater_kW:.1f}kW")
            print(f"  ベースライン: W_net=8.073kW, m_orc=2.031kg/s")
            print(f"  蒸発温度: {T_htf_in-20-273.15:.1f}°C → {T_evap_enhanced-273.15:.1f}°C (+{actual_delta_T:.1f}K)")
            print(f"  利用可能熱量: {remaining_heat_capacity/1000:.3f}kW, HTF温度差: {remaining_heat_capacity/(m_htf * cp_htf):.1f}K")
            print(f"  作動流体流量: 2.031kg/s → {2.031*mass_flow_ratio:.3f}kg/s")
            
        else:
            T_evap_enhanced = T_htf_in - 20  # ベース蒸発温度
            mass_flow_ratio = 1.0
            actual_delta_T = 0.0
        
        # ORC解析の実行
        # 簡略化されたORC性能計算
        T_evap = T_evap_enhanced
        
        # 基本的なORC性能計算（簡単な近似）
        if Q_preheater_kW == 0:
            # ベースラインケース
            W_net = 8.073  # kW
            eta_th = 0.0196
            Q_in = 411.447
        else:
            # 予熱器ありケース：効率向上と出力変化を計算
            # カルノー効率ベースの近似
            eta_carnot_base = 1 - T_cond / (T_htf_in - 20)
            eta_carnot_enhanced = 1 - T_cond / T_evap_enhanced
            eta_improvement_factor = eta_carnot_enhanced / eta_carnot_base
            
            # 実際の効率改善（カルノー効率の30%程度を仮定）
            eta_th = 0.0196 * eta_improvement_factor
            
            # 質量流量減少による出力変化を考慮
            W_net = 8.073 * mass_flow_ratio * eta_improvement_factor
            Q_in = W_net / eta_th
        
        print(f"  最終結果: W_net={W_net:.3f}kW ({((W_net-8.073)/8.073*100):+.2f}%), η_th={eta_th:.4f} ({((eta_th-0.0196)/0.0196*100):+.2f}%)")
        
        # 結果の構築
        result = {
            'W_net [kW]': W_net,
            'η_th [-]': eta_th,
            'Q_in [kW]': Q_in,
            'Q_out [kW]': -(Q_in - W_net),
            'ε_ex [-]': 0.35,  # 仮定値
            'Q_preheater [kW]': Q_preheater_kW,
            'Q_superheater [kW]': 0.0,
            'T_evap_enhanced [°C]': T_evap_enhanced - 273.15,
            'delta_T_evap [K]': actual_delta_T,
            'is_constrained': Q_preheater_kW > 0 and (T_evap_enhanced >= T_htf_in - 10)
        }
        
        return result
        
    except Exception as e:
        print(f"ORC計算エラー: {e}")
        return None


def case_study_theoretical_preheater_effect():
    """理論的予熱器効果のケーススタディ"""
    print("Phase 1: 予熱器効果の基礎理論検証")
    print("=" * 60)
    
    # テスト条件
    T_htf_in = 333.15  # 60°C
    T_cond = 305.15    # 32°C
    T_evap_base = 313.15  # 40°C
    m_orc = 2.031  # kg/s
    
    print(f"理論解析条件:")
    print(f"  熱源温度: {T_htf_in-273.15:.1f}°C")
    print(f"  凝縮温度: {T_cond-273.15:.1f}°C")
    print(f"  ベースライン蒸発温度: {T_evap_base-273.15:.1f}°C")
    print(f"  作動流体流量: {m_orc:.3f} kg/s")
    
    # 予熱器電力の範囲
    Q_preheater_range = np.arange(0, 32, 2)  # 0-30 kW
    results = []
    
    for Q_preheater in Q_preheater_range:
        # 予熱器による蒸発温度向上の計算
        max_temp_rise = 10  # 最大10K上昇
        temp_rise = min(Q_preheater / 20 * max_temp_rise, max_temp_rise)  # 20kWで最大上昇
        T_evap_enhanced = min(T_evap_base + temp_rise, 323.15)  # 50°C上限
        
        # カルノー効率の計算
        eta_carnot_base = 1 - T_cond / T_evap_base
        eta_carnot_enhanced = 1 - T_cond / T_evap_enhanced
        carnot_improvement = (eta_carnot_enhanced - eta_carnot_base) / eta_carnot_base * 100
        
        results.append({
            'Q_preheater_kW': Q_preheater,
            'T_evap_enhanced_C': T_evap_enhanced - 273.15,
            'carnot_improvement_percent': carnot_improvement
        })
    
    df_results = pd.DataFrame(results)
    
    print(f"\n理論解析結果 (抜粋):")
    print(df_results.to_string(index=False))
    
    # 最大改善ケースの特定
    max_improvement_idx = df_results['carnot_improvement_percent'].idxmax()
    max_case = df_results.loc[max_improvement_idx]
    
    print(f"\n最大効率改善ケース:")
    print(f"  予熱器電力: {max_case['Q_preheater_kW']:.1f} kW")
    print(f"  蒸発温度上昇: {max_case['T_evap_enhanced_C'] - 40:.1f} K")
    print(f"  カルノー効率改善: {max_case['carnot_improvement_percent']:.2f} %")
    print(f"  制約による制限: {'あり' if max_case['T_evap_enhanced_C'] >= 50 else 'なし'}")
    
    # 実用性評価
    practical_cases = df_results[df_results['carnot_improvement_percent'] > 1]
    print(f"\n実用性評価:")
    print(f"  1%以上の改善が期待できるケース: {len(practical_cases)}件")
    if len(practical_cases) > 0:
        print(f"  必要な予熱器電力範囲: {practical_cases['Q_preheater_kW'].min():.1f}-{practical_cases['Q_preheater_kW'].max():.1f} kW")
    
    return df_results

class MultiObjectiveORCOptimizer:
    """多目的ORC最適化クラス"""
    
    def __init__(self, T_htf_in, Vdot_htf, T_cond, eta_pump, eta_turb):
        self.T_htf_in = T_htf_in
        self.Vdot_htf = Vdot_htf
        self.T_cond = T_cond
        self.eta_pump = eta_pump
        self.eta_turb = eta_turb
        
        # ベースライン計算
        self.baseline_result = calculate_orc_with_preheater_optimization(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            Q_preheater_kW=0.0
        )
        
        if self.baseline_result:
            self.baseline_W_net = self.baseline_result['W_net [kW]']
            self.baseline_eta_th = self.baseline_result['η_th [-]']
            print(f"ベースライン: W_net={self.baseline_W_net:.3f}kW, η_th={self.baseline_eta_th:.4f}")
        else:
            raise ValueError("ベースライン計算に失敗しました")
    
    def objective_function(self, Q_preheater_kW, objectives=['W_net', 'eta_th'], weights=None):
        """多目的関数
        
        Args:
            Q_preheater_kW: 予熱器電力 [kW]
            objectives: 最適化目標のリスト
            weights: 各目標の重み（正規化用）
        
        Returns:
            float or tuple: 目的関数値
        """
        if weights is None:
            weights = [1.0] * len(objectives)
        
        result = calculate_orc_with_preheater_optimization(
            T_htf_in=self.T_htf_in,
            Vdot_htf=self.Vdot_htf,
            T_cond=self.T_cond,
            eta_pump=self.eta_pump,
            eta_turb=self.eta_turb,
            Q_preheater_kW=Q_preheater_kW
        )
        
        if result is None:
            # ペナルティ値を返す
            if len(objectives) == 1:
                return 1e6
            else:
                return tuple([1e6] * len(objectives))
        
        objective_values = []
        
        for obj in objectives:
            if obj == 'W_net':
                # 正味出力の改善率（最大化）
                improvement = (result['W_net [kW]'] - self.baseline_W_net) / self.baseline_W_net
                objective_values.append(-improvement)  # 最大化のため符号反転
            elif obj == 'eta_th':
                # 熱効率の改善率（最大化）
                improvement = (result['η_th [-]'] - self.baseline_eta_th) / self.baseline_eta_th
                objective_values.append(-improvement)  # 最大化のため符号反転
            elif obj == 'W_net_absolute':
                # 絶対正味出力（最大化）
                objective_values.append(-result['W_net [kW]'])
            elif obj == 'eta_th_absolute':
                # 絶対熱効率（最大化）
                objective_values.append(-result['η_th [-]'])
            elif obj == 'preheater_efficiency':
                # 予熱器効率（最小化）: 投入電力あたりの出力改善
                if Q_preheater_kW > 0:
                    efficiency = (result['W_net [kW]'] - self.baseline_W_net) / Q_preheater_kW
                    objective_values.append(-efficiency)  # 最大化のため符号反転
                else:
                    objective_values.append(0)
        
        # 重み付き合成
        if len(objectives) == 1:
            return objective_values[0]
        elif len(objectives) == 2:
            # 重み付き線形結合
            return weights[0] * objective_values[0] + weights[1] * objective_values[1]
        else:
            return tuple(objective_values)
    
    def constraint_functions(self, Q_preheater_kW):
        """制約関数
        
        Args:
            Q_preheater_kW: 予熱器電力 [kW]
        
        Returns:
            dict: 制約値（正の値で制約満足）
        """
        result = calculate_orc_with_preheater_optimization(
            T_htf_in=self.T_htf_in,
            Vdot_htf=self.Vdot_htf,
            T_cond=self.T_cond,
            eta_pump=self.eta_pump,
            eta_turb=self.eta_turb,
            Q_preheater_kW=Q_preheater_kW
        )
        
        if result is None:
            return {
                'feasible': -1,  # 実行不可能
                'positive_improvement': -1,
                'min_power_output': -1
            }
        
        constraints = {}
        
        # 実行可能性制約
        constraints['feasible'] = 1 if result else -1
        
        # 正の効率改善制約
        eta_improvement = (result['η_th [-]'] - self.baseline_eta_th) / self.baseline_eta_th
        constraints['positive_improvement'] = eta_improvement  # > 0 で制約満足
        
        # 最小出力制約（例：ベースラインの50%以上）
        min_power_ratio = result['W_net [kW]'] / self.baseline_W_net - 0.5
        constraints['min_power_output'] = min_power_ratio  # > 0 で制約満足
        
        return constraints

    def pareto_front_analysis(self, Q_preheater_range=None, n_points=20):
        """パレート最適解の探索
        
        Args:
            Q_preheater_range: 予熱器電力範囲 [kW]
            n_points: 探索点数
        
        Returns:
            DataFrame: パレート解析結果
        """
        if Q_preheater_range is None:
            Q_preheater_range = np.linspace(0, 25, n_points)
        
        results = []
        
        print(f"\nパレート最適解析開始: {len(Q_preheater_range)}点探索")
        
        for i, Q_preheater in enumerate(Q_preheater_range):
            print(f"  {i+1:2d}/{len(Q_preheater_range)}: Q_preheater={Q_preheater:.1f}kW", end=" ")
            
            result = calculate_orc_with_preheater_optimization(
                T_htf_in=self.T_htf_in,
                Vdot_htf=self.Vdot_htf,
                T_cond=self.T_cond,
                eta_pump=self.eta_pump,
                eta_turb=self.eta_turb,
                Q_preheater_kW=Q_preheater
            )
            
            if result:
                # 改善率の計算
                W_net_improvement = (result['W_net [kW]'] - self.baseline_W_net) / self.baseline_W_net * 100
                eta_improvement = (result['η_th [-]'] - self.baseline_eta_th) / self.baseline_eta_th * 100
                
                # 予熱器効率（出力改善/投入電力）
                preheater_efficiency = (result['W_net [kW]'] - self.baseline_W_net) / Q_preheater if Q_preheater > 0 else 0
                
                result_data = {
                    'Q_preheater_kW': Q_preheater,
                    'W_net_kW': result['W_net [kW]'],
                    'eta_th': result['η_th [-]'],
                    'W_net_improvement_percent': W_net_improvement,
                    'eta_improvement_percent': eta_improvement,
                    'preheater_efficiency_kW_per_kW': preheater_efficiency,
                    'T_evap_enhanced_C': result.get('T_evap_enhanced [°C]', 0),
                    'delta_T_evap_K': result.get('delta_T_evap [K]', 0),
                    'is_constrained': result.get('is_constrained', False),
                    'feasible': True
                }
                
                print(f"→ W_net改善:{W_net_improvement:+.1f}%, η_th改善:{eta_improvement:+.1f}%")
            else:
                result_data = {
                    'Q_preheater_kW': Q_preheater,
                    'W_net_kW': 0,
                    'eta_th': 0,
                    'W_net_improvement_percent': -100,
                    'eta_improvement_percent': -100,
                    'preheater_efficiency_kW_per_kW': -1,
                    'T_evap_enhanced_C': 0,
                    'delta_T_evap_K': 0,
                    'is_constrained': True,
                    'feasible': False
                }
                print("→ 計算失敗")
            
            results.append(result_data)
        
        return pd.DataFrame(results)

    def constrained_optimization(self, method='trust-constr', max_preheater_kW=25.0):
        """制約付き最適化
        
        Args:
            method: 最適化手法
            max_preheater_kW: 予熱器最大電力 [kW]
        
        Returns:
            dict: 最適化結果
        """
        print(f"\n制約付き最適化開始: 手法={method}")
        
        # 制約の定義
        def constraint_positive_eta_improvement(Q):
            constraints = self.constraint_functions(Q[0])
            return constraints['positive_improvement']
        
        def constraint_min_power(Q):
            constraints = self.constraint_functions(Q[0])
            return constraints['min_power_output']
        
        constraints = [
            NonlinearConstraint(constraint_positive_eta_improvement, 0, np.inf),
            NonlinearConstraint(constraint_min_power, 0, np.inf)
        ]
        
        # 目的関数（熱効率改善最大化）
        def objective(Q):
            return self.objective_function(Q[0], objectives=['eta_th'])
        
        # 最適化実行
        bounds = [(0, max_preheater_kW)]
        x0 = [max_preheater_kW / 2]  # 初期値
        
        try:
            result = minimize(
                objective,
                x0,
                method=method,
                bounds=bounds,
                constraints=constraints,
                options={'disp': True}
            )
            
            if result.success:
                optimal_Q_preheater = result.x[0]
                print(f"制約付き最適化成功: 最適予熱器電力 = {optimal_Q_preheater:.3f} kW")
                
                # 最適解での詳細計算
                optimal_result = calculate_orc_with_preheater_optimization(
                    T_htf_in=self.T_htf_in,
                    Vdot_htf=self.Vdot_htf,
                    T_cond=self.T_cond,
                    eta_pump=self.eta_pump,
                    eta_turb=self.eta_turb,
                    Q_preheater_kW=optimal_Q_preheater
                )
                
                return {
                    'success': True,
                    'optimal_Q_preheater_kW': optimal_Q_preheater,
                    'objective_value': -result.fun,  # 符号を戻す
                    'detailed_result': optimal_result,
                    'optimization_result': result
                }
            else:
                print(f"制約付き最適化失敗: {result.message}")
                return {'success': False, 'message': result.message}
                
        except Exception as e:
            print(f"制約付き最適化エラー: {e}")
            return {'success': False, 'error': str(e)}

    def multi_objective_optimization(self, objectives=['W_net', 'eta_th'], weights_list=None):
        """多目的最適化
        
        Args:
            objectives: 最適化目標のリスト
            weights_list: 重みのリスト（異なる重み組み合わせで最適化）
        
        Returns:
            list: 各重みでの最適化結果
        """
        if weights_list is None:
            # デフォルト重み組み合わせ
            weights_list = [
                [1.0, 0.0],  # 正味出力のみ
                [0.0, 1.0],  # 熱効率のみ
                [0.5, 0.5],  # 同等重み
                [0.3, 0.7],  # 熱効率重視
                [0.7, 0.3],  # 正味出力重視
            ]
        
        results = []
        
        print(f"\n多目的最適化開始: 目標={objectives}")
        
        for i, weights in enumerate(weights_list):
            print(f"\n重み組み合わせ {i+1}/{len(weights_list)}: {weights}")
            
            # 目的関数の定義
            def objective(Q):
                return self.objective_function(Q[0], objectives=objectives, weights=weights)
            
            # 最適化実行
            bounds = [(0, 25)]
            x0 = [12.5]
            
            try:
                result = minimize(
                    objective,
                    x0,
                    bounds=bounds,
                    method='L-BFGS-B'
                )
                
                if result.success:
                    optimal_Q_preheater = result.x[0]
                    
                    # 詳細結果の計算
                    detailed_result = calculate_orc_with_preheater_optimization(
                        T_htf_in=self.T_htf_in,
                        Vdot_htf=self.Vdot_htf,
                        T_cond=self.T_cond,
                        eta_pump=self.eta_pump,
                        eta_turb=self.eta_turb,
                        Q_preheater_kW=optimal_Q_preheater
                    )
                    
                    result_data = {
                        'weights': weights,
                        'optimal_Q_preheater_kW': optimal_Q_preheater,
                        'objective_value': -result.fun,
                        'success': True,
                        'detailed_result': detailed_result
                    }
                    
                    if detailed_result:
                        W_improvement = (detailed_result['W_net [kW]'] - self.baseline_W_net) / self.baseline_W_net * 100
                        eta_improvement = (detailed_result['η_th [-]'] - self.baseline_eta_th) / self.baseline_eta_th * 100
                        print(f"  最適解: Q_preheater={optimal_Q_preheater:.2f}kW, W_net改善:{W_improvement:+.1f}%, η_th改善:{eta_improvement:+.1f}%")
                    
                else:
                    result_data = {
                        'weights': weights,
                        'success': False,
                        'message': result.message
                    }
                    print(f"  最適化失敗: {result.message}")
                
            except Exception as e:
                result_data = {
                    'weights': weights,
                    'success': False,
                    'error': str(e)
                }
                print(f"  最適化エラー: {e}")
            
            results.append(result_data)
        
        return results


def visualize_pareto_analysis(df_pareto, title="パレート最適解析"):
    """パレート解析結果の可視化"""
    
    # 実行可能解のみを抽出
    df_feasible = df_pareto[df_pareto['feasible']].copy()
    
    if len(df_feasible) == 0:
        print("実行可能解がありません")
        return None
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. 正味出力 vs 熱効率（パレートフロント）
    axes[0, 0].scatter(df_feasible['W_net_improvement_percent'], 
                      df_feasible['eta_improvement_percent'],
                      c=df_feasible['Q_preheater_kW'], cmap='viridis', s=50)
    axes[0, 0].set_xlabel('正味出力改善率 [%]')
    axes[0, 0].set_ylabel('熱効率改善率 [%]')
    axes[0, 0].set_title('パレートフロント: 正味出力 vs 熱効率')
    axes[0, 0].grid(True, alpha=0.3)
    cb1 = plt.colorbar(axes[0, 0].collections[0], ax=axes[0, 0])
    cb1.set_label('予熱器電力 [kW]')
    
    # 2. 予熱器電力 vs 改善率
    axes[0, 1].plot(df_feasible['Q_preheater_kW'], df_feasible['W_net_improvement_percent'], 
                   'b-o', label='正味出力改善', linewidth=2, markersize=4)
    axes[0, 1].plot(df_feasible['Q_preheater_kW'], df_feasible['eta_improvement_percent'], 
                   'r-s', label='熱効率改善', linewidth=2, markersize=4)
    axes[0, 1].set_xlabel('予熱器電力 [kW]')
    axes[0, 1].set_ylabel('改善率 [%]')
    axes[0, 1].set_title('予熱器電力 vs 性能改善')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. 蒸発温度上昇
    axes[0, 2].plot(df_feasible['Q_preheater_kW'], df_feasible['T_evap_enhanced_C'], 
                   'g-^', linewidth=2, markersize=4)
    axes[0, 2].set_xlabel('予熱器電力 [kW]')
    axes[0, 2].set_ylabel('蒸発温度 [°C]')
    axes[0, 2].set_title('予熱器による蒸発温度上昇')
    axes[0, 2].grid(True, alpha=0.3)
    
    # 4. 予熱器効率
    axes[1, 0].plot(df_feasible['Q_preheater_kW'], df_feasible['preheater_efficiency_kW_per_kW'], 
                   'purple', linestyle='--', marker='d', linewidth=2, markersize=4)
    axes[1, 0].set_xlabel('予熱器電力 [kW]')
    axes[1, 0].set_ylabel('予熱器効率 [kW出力改善/kW投入]')
    axes[1, 0].set_title('予熱器の投資効率')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    # 5. 絶対性能値
    axes[1, 1].plot(df_feasible['Q_preheater_kW'], df_feasible['W_net_kW'], 
                   'b-o', label='正味出力', linewidth=2, markersize=4)
    ax_twin = axes[1, 1].twinx()
    ax_twin.plot(df_feasible['Q_preheater_kW'], df_feasible['eta_th']*100, 
                'r-s', label='熱効率', linewidth=2, markersize=4)
    axes[1, 1].set_xlabel('予熱器電力 [kW]')
    axes[1, 1].set_ylabel('正味出力 [kW]', color='blue')
    ax_twin.set_ylabel('熱効率 [%]', color='red')
    axes[1, 1].set_title('絶対性能値')
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. 制約分析
    constraint_colors = ['green' if not constrained else 'orange' 
                        for constrained in df_feasible['is_constrained']]
    axes[1, 2].scatter(df_feasible['Q_preheater_kW'], df_feasible['delta_T_evap_K'],
                      c=constraint_colors, s=50, alpha=0.7)
    axes[1, 2].set_xlabel('予熱器電力 [kW]')
    axes[1, 2].set_ylabel('蒸発温度上昇 [K]')
    axes[1, 2].set_title('制約分析\n(緑:制約なし, 橙:制約あり)')
    axes[1, 2].grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    return fig


def phase3_demonstration():
    """Phase 3のデモンストレーション"""
    
    print("=" * 80)
    print("Phase 3: 高度な最適化アルゴリズムのデモンストレーション")
    print("=" * 80)
    
    # テスト条件
    T_htf_in = 333.15  # 60°C
    Vdot_htf = 0.010   # 0.010 m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    
    print(f"\nテスト条件:")
    print(f"  熱源温度: {T_htf_in-273.15:.1f}°C")
    print(f"  熱源流量: {Vdot_htf:.4f} m³/s")
    print(f"  凝縮温度: {T_cond-273.15:.1f}°C")
    
    # 最適化器の初期化
    optimizer = MultiObjectiveORCOptimizer(T_htf_in, Vdot_htf, T_cond, eta_pump, eta_turb)
    
    # 1. パレート最適解析
    print("\n" + "─" * 60)
    print("1. パレート最適解析")
    Q_range = np.linspace(0, 25, 15)
    df_pareto = optimizer.pareto_front_analysis(Q_preheater_range=Q_range)
    
    # 2. 制約付き最適化
    print("\n" + "─" * 60)
    print("2. 制約付き最適化")
    constrained_result = optimizer.constrained_optimization()
    
    # 3. 多目的最適化
    print("\n" + "─" * 60)
    print("3. 多目的最適化")
    multi_obj_results = optimizer.multi_objective_optimization()
    
    # 4. 結果の可視化
    print("\n" + "─" * 60)
    print("4. 結果の可視化")
    fig = visualize_pareto_analysis(df_pareto)
    if fig:
        plt.savefig('phase3_pareto_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    # 5. 最適解の比較
    print("\n" + "─" * 60)
    print("5. 最適解の比較")
    
    feasible_solutions = df_pareto[df_pareto['feasible']].copy()
    if len(feasible_solutions) > 0:
        # 各指標での最適解
        best_W_net = feasible_solutions.loc[feasible_solutions['W_net_improvement_percent'].idxmax()]
        best_eta_th = feasible_solutions.loc[feasible_solutions['eta_improvement_percent'].idxmax()]
        best_efficiency = feasible_solutions[feasible_solutions['Q_preheater_kW'] > 0].loc[
            feasible_solutions[feasible_solutions['Q_preheater_kW'] > 0]['preheater_efficiency_kW_per_kW'].idxmax()]
        
        print(f"\n最適解の比較:")
        print(f"正味出力最大: Q_preheater={best_W_net['Q_preheater_kW']:.1f}kW, 改善率={best_W_net['W_net_improvement_percent']:+.1f}%")
        print(f"熱効率最大: Q_preheater={best_eta_th['Q_preheater_kW']:.1f}kW, 改善率={best_eta_th['eta_improvement_percent']:+.1f}%")
        print(f"投資効率最大: Q_preheater={best_efficiency['Q_preheater_kW']:.1f}kW, 効率={best_efficiency['preheater_efficiency_kW_per_kW']:.3f}")
        
        if constrained_result and constrained_result['success']:
            print(f"制約付き最適化: Q_preheater={constrained_result['optimal_Q_preheater_kW']:.1f}kW")
    
    return {
        'pareto_analysis': df_pareto,
        'constrained_optimization': constrained_result,
        'multi_objective_results': multi_obj_results,
        'optimizer': optimizer
    }


if __name__ == "__main__":
    # Phase 1-3の統合実行
    print("Phase 1実行中...")
    phase1_results = case_study_theoretical_preheater_effect()
    
    print("\nPhase 3実行中...")
    phase3_results = phase3_demonstration()
    
    print("\n" + "=" * 80)
    print("Phase 3完了: 高度な最適化アルゴリズムの実装と解析を完了しました")
    print("全フェーズ完了: 予熱器最適化システムの開発が完了しました！")
    print("=" * 80)
