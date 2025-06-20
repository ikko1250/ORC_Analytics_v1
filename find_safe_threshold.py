#!/usr/bin/env python3
"""
非常に小さい電力での安全性テスト

CoolPropエラーが発生しない最大電力を見つける
"""

import sys
import os
sys.path.append('/home/ubuntu/cur/program/seminar_fresh')

import numpy as np
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.config import set_component_setting

def find_safe_power_threshold():
    """安全な電力の閾値を見つける"""
    print("=== 安全な電力閾値の探索 ===")
    
    # コンポーネントを有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    
    # テスト条件
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 1e-4  # 0.1 L/s
    T_cond = 313.15  # 40°C
    eta_pump = 0.75
    eta_turb = 0.85
    
    # まず基本ケース（電力なし）をテスト
    print("基本ケース（電力なし）をテスト...")
    try:
        base_result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            Q_preheater_kW_input=0.0,
            Q_superheater_kW_input=0.0,
        )
        
        if base_result is not None:
            print("✅ 基本ケース成功")
            m_orc = base_result.get("m_orc [kg/s]", None)
            print(f"ORC質量流量: {m_orc:.6f} kg/s")
            print(f"正味出力: {base_result.get('W_net [kW]', 'N/A'):.6f} kW")
        else:
            print("❌ 基本ケース失敗")
            return
            
    except Exception as e:
        print(f"❌ 基本ケースでエラー: {e}")
        return
    
    # 非常に小さい電力から段階的にテスト
    power_levels = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
    
    last_successful_power = 0.0
    
    for power in power_levels:
        print(f"\n電力 {power:.3f} kW をテスト...")
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                Q_preheater_kW_input=power,
                Q_superheater_kW_input=0.0,
            )
            
            if result is not None:
                w_net = result.get('W_net [kW]', None)
                if w_net is not None and not np.isnan(w_net):
                    print(f"✅ 成功: 正味出力 = {w_net:.6f} kW")
                    last_successful_power = power
                else:
                    print(f"⚠️  計算は成功したが結果が無効 (nan)")
                    break
            else:
                print(f"❌ 結果がNone")
                break
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            break
    
    print(f"\n=== 結果 ===")
    print(f"最後に成功した電力レベル: {last_successful_power:.3f} kW")
    
    if m_orc is not None:
        enthalpy_increase_per_kw = 1000.0 / m_orc  # kJ/kg per kW
        safe_enthalpy_increase = last_successful_power * enthalpy_increase_per_kw
        print(f"対応するエンタルピー増加: {safe_enthalpy_increase:.1f} kJ/kg")
        print(f"推奨安全制限: {safe_enthalpy_increase * 0.8:.1f} kJ/kg (80%マージン)")

if __name__ == "__main__":
    find_safe_power_threshold()
