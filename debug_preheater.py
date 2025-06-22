#!/usr/bin/env python3
"""予熱器効果のデバッグ用スクリプト"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source

# テスト条件
T_htf_in = 333.15  # 60°C
Vdot_htf = 0.010   # 0.010 m³/s
T_cond = 305.15    # 32°C
eta_pump = 0.75
eta_turb = 0.80

print("予熱器効果デバッグテスト")
print("=" * 50)

# ベースライン（予熱器なし）
print("1. ベースライン（予熱器なし）:")
result_baseline = calculate_orc_performance_from_heat_source(
    T_htf_in=T_htf_in,
    Vdot_htf=Vdot_htf,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    Q_preheater_kW_input=0.0,
    Q_superheater_kW_input=0.0,
)

if result_baseline:
    print(f"  正味出力: {result_baseline.get('W_net [kW]', 0):.3f} kW")
    print(f"  熱効率: {result_baseline.get('η_th [-]', 0):.4f}")
    print(f"  総入力熱量: {result_baseline.get('Q_in [kW]', 0):.3f} kW")
    print(f"  作動流体流量: {result_baseline.get('m_orc [kg/s]', 0):.3f} kg/s")
else:
    print("  計算失敗")

print()

# 予熱器 5kW
print("2. 予熱器 5kW:")
result_5kw = calculate_orc_performance_from_heat_source(
    T_htf_in=T_htf_in,
    Vdot_htf=Vdot_htf,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    Q_preheater_kW_input=5.0,
    Q_superheater_kW_input=0.0,
)

if result_5kw:
    print(f"  正味出力: {result_5kw.get('W_net [kW]', 0):.3f} kW")
    print(f"  熱効率: {result_5kw.get('η_th [-]', 0):.4f}")
    print(f"  総入力熱量: {result_5kw.get('Q_in [kW]', 0):.3f} kW")
    print(f"  作動流体流量: {result_5kw.get('m_orc [kg/s]', 0):.3f} kg/s")
    
    if result_baseline:
        improvement = (result_5kw.get('W_net [kW]', 0) - result_baseline.get('W_net [kW]', 0)) / result_baseline.get('W_net [kW]', 1) * 100
        print(f"  改善率: {improvement:.3f}%")
else:
    print("  計算失敗")

print()

# 予熱器 30kW
print("3. 予熱器 30kW:")
result_30kw = calculate_orc_performance_from_heat_source(
    T_htf_in=T_htf_in,
    Vdot_htf=Vdot_htf,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    Q_preheater_kW_input=30.0,
    Q_superheater_kW_input=0.0,
)

if result_30kw:
    print(f"  正味出力: {result_30kw.get('W_net [kW]', 0):.3f} kW")
    print(f"  熱効率: {result_30kw.get('η_th [-]', 0):.4f}")
    print(f"  総入力熱量: {result_30kw.get('Q_in [kW]', 0):.3f} kW")
    print(f"  作動流体流量: {result_30kw.get('m_orc [kg/s]', 0):.3f} kg/s")
    
    if result_baseline:
        improvement = (result_30kw.get('W_net [kW]', 0) - result_baseline.get('W_net [kW]', 0)) / result_baseline.get('W_net [kW]', 1) * 100
        print(f"  改善率: {improvement:.3f}%")
else:
    print("  計算失敗")

print("\n" + "=" * 50)
print("デバッグ完了")
