#!/usr/bin/env python3
"""CoolProp エラーの詳細分析とデバッグ"""

import sys
import os
import numpy as np
import CoolProp.CoolProp as CP

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source

print("=== CoolProp Error Analysis ===")
print()

def analyze_coolprop_limits():
    """R245faの物性範囲を分析"""
    print("R245fa Properties Analysis:")
    print("-" * 40)
    
    try:
        # 臨界点
        T_crit = CP.PropsSI("Tcrit", "R245fa")
        P_crit = CP.PropsSI("Pcrit", "R245fa")
        H_crit = CP.PropsSI("H", "T", T_crit, "P", P_crit, "R245fa")
        
        print(f"Critical temperature: {T_crit:.2f} K ({T_crit-273.15:.2f} °C)")
        print(f"Critical pressure: {P_crit/1e5:.2f} bar")
        print(f"Critical enthalpy: {H_crit:.2f} J/kg")
        
        # 最大エンタルピー
        T_max = CP.PropsSI("Tmax", "R245fa")
        P_test = 1e5  # 1 bar
        
        print(f"Maximum temperature: {T_max:.2f} K ({T_max-273.15:.2f} °C)")
        
        # エンタルピー範囲をテスト
        test_temps = np.linspace(250, min(T_crit-1, T_max-1), 10)
        test_pressures = [1e5, 5e5, 10e5, 15e5]  # 1, 5, 10, 15 bar
        
        print("\nEnthalpy values at different conditions:")
        print("T[K]   P[bar]   H[J/kg]")
        print("-" * 30)
        
        for T in test_temps:
            for P in test_pressures:
                try:
                    if T < T_crit and P < P_crit:
                        H = CP.PropsSI("H", "T", T, "P", P, "R245fa")
                        print(f"{T:.1f}  {P/1e5:.0f}      {H:.0f}")
                except Exception as e:
                    print(f"{T:.1f}  {P/1e5:.0f}      ERROR: {str(e)[:50]}")
                    
    except Exception as e:
        print(f"Error analyzing CoolProp properties: {e}")

def test_specific_conditions():
    """特定の条件での動作テスト"""
    print("\n" + "="*50)
    print("Testing specific thermodynamic conditions:")
    print("="*50)
    
    # 基本条件
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 0.01    # m³/s
    T_cond = 305.15    # 32°C
    eta_pump = 0.75
    eta_turb = 0.80
    
    test_cases = [
        {"Q_preheater": 0.0, "Q_superheater": 0.0, "desc": "No components"},
        {"Q_preheater": 5.0, "Q_superheater": 0.0, "desc": "Low preheater"},
        {"Q_preheater": 10.0, "Q_superheater": 0.0, "desc": "Medium preheater"},
        {"Q_preheater": 25.0, "Q_superheater": 0.0, "desc": "High preheater"},
        {"Q_preheater": 50.0, "Q_superheater": 0.0, "desc": "Very high preheater"},
        {"Q_preheater": 0.0, "Q_superheater": 10.0, "desc": "Low superheater"},
        {"Q_preheater": 0.0, "Q_superheater": 50.0, "desc": "High superheater"},
    ]
    
    for case in test_cases:
        print(f"\nTesting: {case['desc']}")
        print(f"Q_preheater: {case['Q_preheater']} kW, Q_superheater: {case['Q_superheater']} kW")
        
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_in,
                Vdot_htf=Vdot_htf,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                Q_preheater_kW_input=case['Q_preheater'],
                Q_superheater_kW_input=case['Q_superheater'],
            )
            
            if result is not None:
                print(f"✓ Success: W_net = {result.get('W_net [kW]', 'N/A')} kW")
                print(f"  η_th = {result.get('η_th [-]', 'N/A')}")
                print(f"  P_evap = {result.get('P_evap [bar]', 'N/A')} bar")
                print(f"  T_turb_in = {result.get('T_turb_in [°C]', 'N/A')} °C")
            else:
                print("❌ Failed: Function returned None")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)[:100]}")

def test_temperature_ranges():
    """異なる熱源温度での動作テスト"""
    print("\n" + "="*50)
    print("Testing different heat source temperatures:")
    print("="*50)
    
    temp_ranges = [
        (323.15, "50°C - Very low"),
        (343.15, "70°C - Low"), 
        (363.15, "90°C - Medium"),
        (373.15, "100°C - High"),
        (393.15, "120°C - Very high"),
        (413.15, "140°C - Near critical"),
    ]
    
    for T_htf, desc in temp_ranges:
        print(f"\nTesting {desc}")
        
        try:
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf,
                Vdot_htf=0.01,
                T_cond=305.15,
                eta_pump=0.75,
                eta_turb=0.80,
                Q_preheater_kW_input=0.0,
                Q_superheater_kW_input=0.0,
            )
            
            if result is not None:
                print(f"✓ Success: W_net = {result.get('W_net [kW]', 'N/A'):.4f} kW")
                print(f"  P_evap = {result.get('P_evap [bar]', 'N/A'):.2f} bar")
            else:
                print("❌ Failed: Function returned None")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)[:80]}")

def check_pressure_enthalpy_relationship():
    """圧力とエンタルピーの関係をチェック"""
    print("\n" + "="*50)
    print("Checking problematic pressure-enthalpy combinations:")
    print("="*50)
    
    # エラーメッセージから問題のある値を抽出
    problem_pressure = 789008.0785  # Pa
    problem_enthalpies = [
        35882069.2,   # J/kg
        57908302.05,  # J/kg  
        71521262.6,   # J/kg
        93547483.9,   # J/kg (最後のエラー)
    ]
    
    print(f"Problem pressure: {problem_pressure} Pa ({problem_pressure/1e5:.2f} bar)")
    
    # R245faの限界を確認
    try:
        T_crit = CP.PropsSI("Tcrit", "R245fa")
        P_crit = CP.PropsSI("Pcrit", "R245fa") 
        H_max_at_problem_P = CP.PropsSI("H", "T", T_crit-1, "P", problem_pressure, "R245fa")
        
        print(f"Critical temperature: {T_crit:.2f} K")
        print(f"Critical pressure: {P_crit/1e5:.2f} bar")
        print(f"Max enthalpy at {problem_pressure/1e5:.2f} bar: {H_max_at_problem_P:.0f} J/kg")
        
        print("\nProblem enthalpies:")
        for H in problem_enthalpies:
            ratio = H / H_max_at_problem_P
            print(f"  {H:.0f} J/kg (ratio: {ratio:.2f})")
            
    except Exception as e:
        print(f"Error checking limits: {e}")

if __name__ == "__main__":
    analyze_coolprop_limits()
    test_specific_conditions()
    test_temperature_ranges()
    check_pressure_enthalpy_relationship()
    
    print("\n" + "="*50)
    print("Analysis complete")
    print("="*50)
