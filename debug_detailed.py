#!/usr/bin/env python3
"""詳細デバッグ用スクリプト"""

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

print("詳細デバッグテスト")
print("=" * 50)

print("1. 予熱器なし:")
result1 = calculate_orc_performance_from_heat_source(
    T_htf_in=T_htf_in,
    Vdot_htf=Vdot_htf,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    Q_preheater_kW_input=0.0,
    Q_superheater_kW_input=0.0,
)

if result1:
    print(f"  Q_preheater: {result1.get('Q_preheater_kW', 'N/A')} kW")
    print(f"  Q_superheater: {result1.get('Q_superheater_kW', 'N/A')} kW")
    print(f"  Q_in: {result1.get('Q_in [kW]', 0):.3f} kW")
    print(f"  W_net: {result1.get('W_net [kW]', 0):.3f} kW")
    print(f"  use_preheater: {result1.get('use_preheater', 'N/A')}")
    print(f"  use_superheater: {result1.get('use_superheater', 'N/A')}")

print("\n2. 予熱器 10kW:")
result2 = calculate_orc_performance_from_heat_source(
    T_htf_in=T_htf_in,
    Vdot_htf=Vdot_htf,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    Q_preheater_kW_input=10.0,
    Q_superheater_kW_input=0.0,
)

if result2:
    print(f"  Q_preheater: {result2.get('Q_preheater_kW', 'N/A')} kW")
    print(f"  Q_superheater: {result2.get('Q_superheater_kW', 'N/A')} kW")
    print(f"  Q_in: {result2.get('Q_in [kW]', 0):.3f} kW")
    print(f"  W_net: {result2.get('W_net [kW]', 0):.3f} kW")
    print(f"  use_preheater: {result2.get('use_preheater', 'N/A')}")
    print(f"  use_superheater: {result2.get('use_superheater', 'N/A')}")

print("\n入力熱量の詳細比較:")
if result1 and result2:
    print(f"  ベースライン Q_in: {result1.get('Q_in [kW]', 0):.3f} kW")
    print(f"  予熱器10kW Q_in: {result2.get('Q_in [kW]', 0):.3f} kW")
    print(f"  差: {result2.get('Q_in [kW]', 0) - result1.get('Q_in [kW]', 0):.3f} kW")
    print(f"  予想される差: 10.0 kW (予熱器分)")
