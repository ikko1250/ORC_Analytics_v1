#!/usr/bin/env python3
"""
飽和条件での品質の独立性を説明するテストスクリプト
60℃、0.199barでは品質は一意に決まらない！
"""

from ORC_analysis.heat_source import get_heat_source_profile
import CoolProp.CoolProp as CP
import matplotlib.pyplot as plt
import numpy as np

def explain_quality_independence():
    """品質が温度・圧力から一意に決まらないことを説明"""
    
    print("=== 品質の独立性：重要な熱力学概念 ===\n")
    
    T = 60 + 273.15   # 60°C
    P = 19900         # 0.199 bar
    
    print("重要な概念:")
    print("飽和条件（T, P）が決まっても、品質（x）は0～1の範囲で任意の値を取れる！")
    print()
    print("理由:")
    print("- 温度と圧力は強度性質（intensive property）")
    print("- 品質は示量性質（extensive property）に関連")
    print("- 同じT, Pでも、蒸気と液体の「量的比率」は様々")
    print()
    
    # 60°Cでの飽和圧力を確認
    P_sat = CP.PropsSI('P', 'T', T, 'Q', 0, 'Water')
    print(f"60°Cでの飽和圧力: {P_sat:.0f} Pa = {P_sat/100000:.3f} bar")
    print(f"指定圧力: {P:.0f} Pa = {P/100000:.3f} bar")
    print(f"圧力差: {abs(P - P_sat):.0f} Pa (ほぼ一致)")
    print()
    
    print("同じ60°C、0.199barでも、以下のすべての状態が存在可能:")

def demonstrate_different_qualities():
    """同じT, Pで異なる品質の状態を実演"""
    
    T = 60 + 273.15   # 60°C
    P = 19900         # 0.199 bar
    
    print("=== 同じ温度・圧力、異なる品質の物性 ===\n")
    print(f"条件: T = {T-273.15}°C, P = {P/100000:.3f} bar\n")
    
    # 各品質での物性計算
    qualities = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    
    print("Quality | 状態説明               | 密度[kg/m³] | エンタルピー[J/kg] | 比容積[m³/kg]")
    print("-" * 80)
    
    for x in qualities:
        # CoolPropで直接計算
        rho = CP.PropsSI("D", "T", T, "Q", x, "Water")
        h = CP.PropsSI("H", "T", T, "Q", x, "Water")
        v = 1.0 / rho
        
        # 状態の説明
        if x == 0.0:
            state_desc = "飽和液体（全て液体）"
        elif x == 1.0:
            state_desc = "飽和蒸気（全て蒸気）"
        else:
            state_desc = f"湿り蒸気（液{(1-x)*100:.0f}%+蒸{x*100:.0f}%）"
        
        print(f"{x:7.1f} | {state_desc:20} | {rho:8.3f} | {h:12.0f} | {v:10.6f}")

def physical_interpretation():
    """物理的解釈"""
    
    print("\n=== 物理的解釈 ===\n")
    
    scenarios = [
        {
            "situation": "容器内の水を60℃まで加熱",
            "x": 0.0,
            "explanation": "水を60℃まで加熱しただけ。まだ沸騰していない。全て液体状態。"
        },
        {
            "situation": "60℃の水に少量の熱を加える",
            "x": 0.1,
            "explanation": "一部が蒸発し始める。液体90% + 蒸気10%の混合状態。"
        },
        {
            "situation": "さらに熱を加え続ける",
            "x": 0.5,
            "explanation": "半分が蒸発。液体50% + 蒸気50%の平衡状態。"
        },
        {
            "situation": "ほぼ全て蒸発させる",
            "x": 0.9,
            "explanation": "ほとんど蒸発完了。液体10% + 蒸気90%。"
        },
        {
            "situation": "完全に蒸発",
            "x": 1.0,
            "explanation": "全て蒸気になった。これ以上の蒸発は不可能。"
        }
    ]
    
    for scenario in scenarios:
        print(f"品質 x = {scenario['x']:.1f}:")
        print(f"  状況: {scenario['situation']}")
        print(f"  説明: {scenario['explanation']}")
        print()

def engineering_implications():
    """工学的含意"""
    
    print("=== 工学的含意 ===\n")
    
    T = 60 + 273.15   # 60°C
    T_out = 40 + 273.15  # 40°C
    P = 19900         # 0.199 bar
    m_dot = 1.0       # 1 kg/s
    
    print("同じ熱源条件でも、品質により利用可能熱量が大きく変わる:")
    print()
    
    # 異なる品質での熱量計算
    for x in [0.0, 0.3, 0.5, 0.7, 1.0]:
        try:
            profile = get_heat_source_profile(
                T_htf_in=T,
                Vdot_htf=m_dot,
                T_htf_out=T_out,
                heat_source_type="wet_steam",
                P_steam=P,
                quality=x,
                mass_flow_mode=True
            )
            
            print(f"品質 {x:.1f}: 利用可能熱量 = {profile.Q_available/1000:.0f} kW")
            
        except Exception as e:
            print(f"品質 {x:.1f}: エラー - {e}")
    
    print()
    print("重要なポイント:")
    print("1. 設計者は熱源の品質を正確に把握する必要がある")
    print("2. 品質の測定・推定が重要な設計パラメータ")
    print("3. 品質により最適なシステム設計が変わる")
    print("4. 運転条件により品質が変化する可能性")

def how_to_determine_quality():
    """品質の決定方法"""
    
    print("\n=== 品質の決定方法 ===\n")
    
    methods = [
        {
            "method": "1. 熱収支から計算",
            "description": "加えた熱量と潜熱から品質を逆算",
            "formula": "x = (H_total - H_liquid) / (H_vapor - H_liquid)"
        },
        {
            "method": "2. 直接測定",
            "description": "蒸気品質計（Steam Quality Meter）を使用",
            "formula": "機器による直接測定"
        },
        {
            "method": "3. プロセス条件から推定",
            "description": "蒸発器の性能や運転条件から推定",
            "formula": "x = 蒸発量 / 総流量"
        },
        {
            "method": "4. 圧力降下測定",
            "description": "二相流の圧力降下特性から推定",
            "formula": "実験式や相関式を使用"
        },
        {
            "method": "5. デフォルト値使用",
            "description": "設計段階での保守的な仮定",
            "formula": "x = 0.5（中間値）"
        }
    ]
    
    for method in methods:
        print(f"{method['method']}")
        print(f"  内容: {method['description']}")
        print(f"  計算: {method['formula']}")
        print()

if __name__ == "__main__":
    explain_quality_independence()
    demonstrate_different_qualities()
    physical_interpretation()
    engineering_implications()
    how_to_determine_quality()
