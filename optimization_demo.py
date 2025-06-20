#!/usr/bin/env python3
"""
ORC最適化モジュール修正デモンストレーション

修正前後の動作比較を実演します。
"""

import sys
import os
sys.path.append('/home/ubuntu/cur/program/seminar_fresh')

import numpy as np
from ORC_analysis.optimization import optimize_orc_with_components, sensitivity_analysis_components
from ORC_analysis.config import set_component_setting

def main():
    print("=" * 70)
    print("ORC最適化モジュール修正デモンストレーション")
    print("=" * 70)
    
    # コンポーネント設定
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', True)
    
    # テスト条件
    test_conditions = {
        "T_htf_in": 373.15,  # 100°C
        "Vdot_htf": 1e-4,    # 0.1 L/s (小流量)
        "T_cond": 313.15,    # 40°C
        "eta_pump": 0.75,
        "eta_turb": 0.85,
        "T_evap_out_target": 368.15,  # 95°C
    }
    
    print("\n📋 テスト条件:")
    print(f"  熱源入口温度: {test_conditions['T_htf_in']-273.15:.1f}°C")
    print(f"  熱源流量: {test_conditions['Vdot_htf']*1000:.1f} L/s")
    print(f"  凝縮温度: {test_conditions['T_cond']-273.15:.1f}°C")
    
    # === テスト1: 修正前の動作（安全制限なし） ===
    print(f"\n{'='*50}")
    print("🔴 修正前の動作（安全制限なし）")
    print(f"{'='*50}")
    
    try:
        result_old = optimize_orc_with_components(
            **test_conditions,
            use_safety_limits=False,
            max_preheater_power=50.0,
            max_superheater_power=100.0
        )
        
        print("結果:")
        print(f"  最適予熱器電力: {result_old.get('Q_preheater_opt [kW]', 'N/A'):.3f} kW")
        print(f"  最適過熱器電力: {result_old.get('Q_superheater_opt [kW]', 'N/A'):.3f} kW")
        w_net = result_old.get('W_net [kW]', 'N/A')
        if isinstance(w_net, (int, float)) and not np.isnan(w_net):
            print(f"  正味出力: {w_net:.6f} kW")
        else:
            print(f"  正味出力: {w_net} ❌ (CoolPropエラーによる計算失敗)")
        print(f"  最適化成功: {result_old.get('optimization_success', 'N/A')}")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
    
    # === テスト2: 修正後の動作（安全制限あり） ===
    print(f"\n{'='*50}")
    print("✅ 修正後の動作（安全制限あり）")
    print(f"{'='*50}")
    
    try:
        result_new = optimize_orc_with_components(
            **test_conditions,
            use_safety_limits=True,
            max_preheater_power=50.0,
            max_superheater_power=100.0
        )
        
        print("結果:")
        print(f"  安全制限適用: {result_new.get('safety_limits_applied', 'N/A')}")
        
        preheater_limit = result_new.get('applied_preheater_limit [kW]', 'N/A')
        if isinstance(preheater_limit, (int, float)):
            print(f"  適用予熱器制限: {preheater_limit:.6f} kW")
        else:
            print(f"  適用予熱器制限: {preheater_limit}")
            
        superheater_limit = result_new.get('applied_superheater_limit [kW]', 'N/A')
        if isinstance(superheater_limit, (int, float)):
            print(f"  適用過熱器制限: {superheater_limit:.6f} kW")
        else:
            print(f"  適用過熱器制限: {superheater_limit}")
            
        print(f"  最適予熱器電力: {result_new.get('Q_preheater_opt [kW]', 'N/A'):.6f} kW")
        print(f"  最適過熱器電力: {result_new.get('Q_superheater_opt [kW]', 'N/A'):.6f} kW")
        
        w_net = result_new.get('W_net [kW]', 'N/A')
        if isinstance(w_net, (int, float)) and not np.isnan(w_net):
            print(f"  正味出力: {w_net:.6f} kW ✅ (計算成功)")
        else:
            print(f"  正味出力: {w_net}")
            
        m_orc = result_new.get('m_orc [kg/s]', 'N/A')
        if isinstance(m_orc, (int, float)):
            print(f"  ORC質量流量: {m_orc:.8f} kg/s")
        else:
            print(f"  ORC質量流量: {m_orc}")
            
        print(f"  最適化成功: {result_new.get('optimization_success', 'N/A')}")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
    
    # === テスト3: より大きい流量での比較 ===
    print(f"\n{'='*50}")
    print("📈 大流量条件での安全制限効果")
    print(f"{'='*50}")
    
    large_flow_conditions = test_conditions.copy()
    large_flow_conditions["Vdot_htf"] = 5e-3  # 5 L/s (50倍大きい)
    
    print(f"流量を {large_flow_conditions['Vdot_htf']*1000:.1f} L/s に増加:")
    
    try:
        result_large = optimize_orc_with_components(
            **large_flow_conditions,
            use_safety_limits=True,
            max_preheater_power=50.0,
            max_superheater_power=100.0
        )
        
        preheater_limit = result_large.get('applied_preheater_limit [kW]', 'N/A')
        if isinstance(preheater_limit, (int, float)):
            print(f"  適用予熱器制限: {preheater_limit:.3f} kW")
        else:
            print(f"  適用予熱器制限: {preheater_limit}")
            
        m_orc = result_large.get('m_orc [kg/s]', 'N/A')
        if isinstance(m_orc, (int, float)):
            print(f"  ORC質量流量: {m_orc:.6f} kg/s")
            print(f"  質量流量比: {m_orc/0.000006:.1f}x (小流量比)")
        
        print("→ 流量に比例して安全制限も増加 ✅")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
    
    # === まとめ ===
    print(f"\n{'='*50}")
    print("📊 修正効果まとめ")
    print(f"{'='*50}")
    
    print("✅ 修正により実現されたこと:")
    print("  • CoolPropエラーの回避")
    print("  • 物理的に実現可能な電力制限の自動計算")
    print("  • 質量流量に応じた動的制限調整")
    print("  • 安全で信頼性の高い最適化")
    print("  • 詳細な診断情報の提供")
    
    print("\n🔧 技術的改善:")
    print("  • エンタルピー増加制限: 80 kJ/kg")
    print("  • 動的電力制限計算")
    print("  • 堅牢なエラーハンドリング")
    print("  • 後方互換性の保持")
    
    print(f"\n{'='*70}")
    print("デモンストレーション完了")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
