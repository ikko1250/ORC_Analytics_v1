#!/usr/bin/env python3
"""
極小電力での安全性テスト

実質的に使用可能な最小電力を見つける
"""

import sys
import os
sys.path.append('/home/ubuntu/cur/program/seminar_fresh')

import numpy as np
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.config import set_component_setting

def test_micro_powers():
    """極小電力レベルをテスト"""
    print("=== 極小電力レベルテスト ===")
    
    # コンポーネントを有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    
    # テスト条件
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 1e-4  # 0.1 L/s
    T_cond = 313.15  # 40°C
    eta_pump = 0.75
    eta_turb = 0.85
    
    # 基本ケースで質量流量を取得
    base_result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        Q_preheater_kW_input=0.0,
        Q_superheater_kW_input=0.0,
    )
    
    m_orc = base_result.get("m_orc [kg/s]", None)
    print(f"ORC質量流量: {m_orc:.8f} kg/s")
    
    # 1W での理論的エンタルピー増加を計算
    power_1w = 0.001  # 1W = 0.001 kW
    enthalpy_increase_1w = power_1w / m_orc  # kJ/kg
    print(f"1W追加での理論エンタルピー増加: {enthalpy_increase_1w:.1f} kJ/kg")
    
    # CoolPropの限界を考慮した最大安全電力を計算
    max_safe_enthalpy_increase = 50.0  # 非常に保守的な値 [kJ/kg]
    max_safe_power = max_safe_enthalpy_increase * m_orc  # kW
    print(f"推定最大安全電力: {max_safe_power*1000:.3f} W")
    
    # 極小電力レベルをテスト
    # ワット単位で計算
    power_levels_watts = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
    
    last_successful_power_watts = 0.0
    
    for power_watts in power_levels_watts:
        power_kw = power_watts / 1000.0  # ワットからキロワットに変換
        expected_enthalpy_increase = power_kw / m_orc
        
        print(f"\n電力 {power_watts:.1f} W ({power_kw:.6f} kW) をテスト...")
        print(f"  予想エンタルピー増加: {expected_enthalpy_increase:.1f} kJ/kg")
        
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                Q_preheater_kW_input=power_kw,
                Q_superheater_kW_input=0.0,
            )
            
            if result is not None:
                w_net = result.get('W_net [kW]', None)
                if w_net is not None and not np.isnan(w_net):
                    print(f"  ✅ 成功: 正味出力 = {w_net:.6f} kW")
                    last_successful_power_watts = power_watts
                else:
                    print(f"  ⚠️  計算は成功したが結果が無効 (nan)")
                    break
            else:
                print(f"  ❌ 結果がNone")
                break
                
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            break
    
    print(f"\n=== 結果 ===")
    print(f"最後に成功した電力レベル: {last_successful_power_watts:.1f} W")
    
    if last_successful_power_watts > 0:
        safe_power_kw = last_successful_power_watts / 1000.0
        safe_enthalpy_increase = safe_power_kw / m_orc
        print(f"対応するエンタルピー増加: {safe_enthalpy_increase:.1f} kJ/kg")
        
        # 新しい安全制限を提案
        recommended_limit = safe_enthalpy_increase * 0.5  # 50%マージン
        print(f"推奨安全制限: {recommended_limit:.1f} kJ/kg (50%マージン)")
    else:
        print("どの電力レベルでも成功しませんでした")
        print("この条件では追加電力は実質的に使用不可能です")

if __name__ == "__main__":
    test_micro_powers()
