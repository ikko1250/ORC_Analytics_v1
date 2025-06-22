#!/usr/bin/env python3
"""cycle_kpiデバッグ用スクリプト"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ORC_analysis.ORC_Analysis import calculate_orc_performance

# テスト条件（直接calculate_orc_performanceを呼び出し）
P_evap = 251000  # 2.5 bar in Pa (60°Cケースから)
T_turb_in = 323.15  # 50°C
T_cond = 305.15  # 32°C
eta_pump = 0.75
eta_turb = 0.80
m_orc = 2.031  # kg/s (デバッグ結果から)

print("cycle_kpiデバッグテスト")
print("=" * 50)

print("1. 予熱器なし:")
psi_df1, comp_df1, cycle_kpi1 = calculate_orc_performance(
    P_evap=P_evap,
    T_turb_in=T_turb_in,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    m_orc=m_orc,
    Q_preheater_kW=0.0,
    Q_superheater_kW=0.0,
)

print("  cycle_kpi1:", cycle_kpi1)

print("\n2. 予熱器 10kW:")
psi_df2, comp_df2, cycle_kpi2 = calculate_orc_performance(
    P_evap=P_evap,
    T_turb_in=T_turb_in,
    T_cond=T_cond,
    eta_pump=eta_pump,
    eta_turb=eta_turb,
    m_orc=m_orc,
    Q_preheater_kW=10.0,
    Q_superheater_kW=0.0,
)

print("  cycle_kpi2:", cycle_kpi2)

print("\n比較:")
if cycle_kpi1 and cycle_kpi2:
    print(f"  Q_in差: {cycle_kpi2.get('Q_in [kW]', 0) - cycle_kpi1.get('Q_in [kW]', 0):.3f} kW")
    print(f"  W_net差: {cycle_kpi2.get('W_net [kW]', 0) - cycle_kpi1.get('W_net [kW]', 0):.3f} kW")
    print(f"  η_th比: {cycle_kpi2.get('η_th [-]', 0) / cycle_kpi1.get('η_th [-]', 1):.4f}")
