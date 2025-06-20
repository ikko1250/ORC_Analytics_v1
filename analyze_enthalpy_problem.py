#!/usr/bin/env python3
"""ORC最適化における物性限界の詳細分析とバグ修正の提案"""

import sys
import os
import numpy as np
import CoolProp.CoolProp as CP

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source

print("=== Enthalpy Limit Analysis ===")
print()

def analyze_enthalpy_problem():
    """エンタルピー問題の根本原因を分析"""
    print("1. R245fa物性限界の確認:")
    print("-" * 40)
    
    # R245faの基本物性
    T_crit = CP.PropsSI("Tcrit", "R245fa")
    P_crit = CP.PropsSI("Pcrit", "R245fa")
    
    print(f"R245fa 臨界温度: {T_crit:.2f} K ({T_crit-273.15:.2f} °C)")
    print(f"R245fa 臨界圧力: {P_crit/1e5:.2f} bar")
    
    # 問題のある圧力での最大エンタルピー
    problem_pressure = 789008.0785  # Pa from error message
    
    try:
        # 臨界点近くでの最大エンタルピー
        h_max_at_problem_P = CP.PropsSI("H", "T", T_crit-1, "P", problem_pressure, "R245fa")
        print(f"圧力 {problem_pressure/1e5:.2f} bar での最大エンタルピー: {h_max_at_problem_P:.0f} J/kg")
        print(f"これは {h_max_at_problem_P/1e6:.2f} MJ/kg です")
        
        # エラーメッセージの値と比較
        error_enthalpy = 93547483.9  # J/kg from error message  
        ratio = error_enthalpy / h_max_at_problem_P
        print(f"エラーのエンタルピー値: {error_enthalpy:.0f} J/kg")
        print(f"最大値との比率: {ratio:.1f} (つまり {ratio:.1f}倍)")
        
    except Exception as e:
        print(f"エンタルピー計算エラー: {e}")

def analyze_mass_flow_vs_power():
    """質量流量と追加電力の関係を分析"""
    print("\n2. 質量流量と追加熱量の関係:")
    print("-" * 40)
    
    # 基本ORC計算で質量流量を取得
    try:
        result = calculate_orc_performance_from_heat_source(
            T_htf_in=373.15,  # 100°C
            Vdot_htf=0.01,    # m³/s
            T_cond=305.15,    # 32°C
            eta_pump=0.75,
            eta_turb=0.80,
            Q_preheater_kW_input=0.0,
            Q_superheater_kW_input=0.0,
        )
        
        if result:
            m_orc = result.get('m_orc [kg/s]', 0.01)
            print(f"基本条件でのORC質量流量: {m_orc:.6f} kg/s")
            
            # 予熱器電力とエンタルピー増加の関係
            preheater_powers = [1, 5, 10, 25, 50, 100]  # kW
            
            print("\n予熱器電力 vs エンタルピー増加:")
            print("電力[kW]  エンタルピー増加[kJ/kg]  エンタルピー増加[MJ/kg]")
            print("-" * 60)
            
            for power in preheater_powers:
                delta_h = power / m_orc  # kJ/kg
                delta_h_MJ = delta_h / 1000  # MJ/kg
                print(f"{power:6.0f}    {delta_h:12.0f}           {delta_h_MJ:8.1f}")
                
                # 危険レベルの判定
                if delta_h > 50000:  # 50 MJ/kg以上は危険
                    print(f"        ⚠️  危険: 物性限界を超える可能性")
        else:
            print("基本ORC計算が失敗しました")
            
    except Exception as e:
        print(f"分析エラー: {e}")

def test_safe_limits():
    """安全な電力限界をテスト"""
    print("\n3. 安全な電力限界のテスト:")
    print("-" * 40)
    
    # 基本条件
    base_params = {
        'T_htf_in': 373.15,  # 100°C
        'Vdot_htf': 0.01,    # m³/s  
        'T_cond': 305.15,    # 32°C
        'eta_pump': 0.75,
        'eta_turb': 0.80,
    }
    
    # 質量流量を取得
    result_base = calculate_orc_performance_from_heat_source(**base_params)
    if not result_base:
        print("基本計算が失敗")
        return
        
    m_orc = result_base.get('m_orc [kg/s]', 0.01)
    print(f"ORC質量流量: {m_orc:.6f} kg/s")
    
    # 安全なエンタルピー増加を10 MJ/kg以下とする
    safe_delta_h = 10000  # kJ/kg
    max_safe_power = safe_delta_h * m_orc  # kW
    
    print(f"安全なエンタルピー増加限界: {safe_delta_h} kJ/kg")
    print(f"安全な電力限界: {max_safe_power:.2f} kW")
    
    # テスト電力範囲
    test_powers = np.linspace(0, max_safe_power * 1.5, 8)
    
    print("\n電力テスト結果:")
    print("電力[kW]  結果       W_net[kW]")
    print("-" * 35)
    
    for power in test_powers:
        try:
            result = calculate_orc_performance_from_heat_source(
                Q_preheater_kW_input=power,
                **base_params
            )
            
            if result:
                w_net = result.get('W_net [kW]', 0)
                status = "✓ 成功" if not np.isnan(w_net) else "⚠️ NaN"
                print(f"{power:6.2f}    {status:8}   {w_net:.4f}")
            else:
                print(f"{power:6.2f}    ❌ None     ---")
                
        except Exception as e:
            print(f"{power:6.2f}    ❌ Error    {str(e)[:20]}")

def propose_fix():
    """修正案の提案"""
    print("\n4. 修正案の提案:")
    print("=" * 50)
    
    print("""
問題の根本原因:
- 最適化で大きな電力値（50-100kW）をテスト
- 小さな質量流量（~0.01 kg/s）で除算  
- 結果として巨大なエンタルピー増加（>50 MJ/kg）
- CoolPropの物性計算範囲を超える

修正案:
1. 質量流量ベースの電力制限を実装
2. エンタルピー増加の上限チェックを追加  
3. 最適化の境界条件を動的に調整
4. より堅牢なエラーハンドリング

実装すべき制限:
- 最大エンタルピー増加: 10-20 MJ/kg
- 質量流量ベースの電力上限: power_max = delta_h_max * m_orc
- 臨界温度からの安全マージン確保
""")

if __name__ == "__main__":
    analyze_enthalpy_problem()
    analyze_mass_flow_vs_power()
    test_safe_limits()
    propose_fix()
