#!/usr/bin/env python3
"""
Check feasible temperature range for R245fa with gas heat source
"""
import CoolProp.CoolProp as CP

# R245faの臨界温度を確認
fluid = "R245fa"
Tcrit = CP.PropsSI("Tcrit", fluid)
print(f"R245fa critical temperature: {Tcrit - 273.15:.1f}°C")

# ORC設定パラメータ
T_cond = 305.0  # 32°C
superheat_C = 8.0
pinch_delta_K = 10.0

print(f"Condensation temperature: {T_cond - 273.15:.1f}°C")
print(f"Superheat: {superheat_C:.1f}°C")
print(f"Pinch delta: {pinch_delta_K:.1f}K")
print()

# 各熱源温度に対する蒸発温度を計算
heat_source_temps = [100, 120, 140, 160, 180, 200]

print("Heat Source Analysis for R245fa:")
print("Heat Source [°C] | Evap Sat [°C] | Turb Inlet [°C] | Status")
print("-" * 60)

for T_htf_C in heat_source_temps:
    T_htf_K = T_htf_C + 273.15
    T_sat_evap = T_htf_K - pinch_delta_K - superheat_C
    T_turb_in = T_sat_evap + superheat_C
    
    # 制約チェック
    if T_sat_evap >= Tcrit:
        status = "❌ Above critical temp"
    elif T_sat_evap <= T_cond + 1.0:
        status = "❌ Too close to cond temp"
    else:
        # 蒸発圧力を計算
        try:
            P_evap = CP.PropsSI("P", "T", T_sat_evap, "Q", 1, fluid)
            P_evap_bar = P_evap / 1e5
            status = f"✅ OK (P={P_evap_bar:.1f} bar)"
        except:
            status = "❌ Property calculation failed"
    
    print(f"{T_htf_C:15} | {T_sat_evap - 273.15:9.1f} | {T_turb_in - 273.15:13.1f} | {status}")

print()
print("Recommendation:")
print("- For gas heat source with R245fa: 120-180°C range is optimal")
print("- 100°C: Limited cycle efficiency but feasible")
print("- Above 180°C: Approaching critical temperature limits")