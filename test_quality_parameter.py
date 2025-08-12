#!/usr/bin/env python3
"""
品質（Quality）パラメータの詳細説明とテスト
"""

from ORC_analysis.heat_source import get_heat_source_profile
import CoolProp.CoolProp as CP

def demonstrate_quality_parameter():
    """品質パラメータの影響を詳細に説明"""
    
    print("=== 品質（Quality/乾き度）パラメータの詳細説明 ===\n")
    
    # 基本条件
    T_in = 60 + 273.15   # 60°C
    T_out = 40 + 273.15  # 40°C
    P_steam = 19900      # 0.199 bar
    m_dot = 1.0          # 1 kg/s
    
    print("基本条件:")
    print(f"  温度: {T_in-273.15}°C → {T_out-273.15}°C")
    print(f"  圧力: {P_steam/100000:.3f} bar")
    print(f"  質量流量: {m_dot} kg/s")
    print()
    
    # まず、60°Cでの飽和液体と飽和蒸気の物性を表示
    print("60°Cでの飽和状態物性:")
    rho_l = CP.PropsSI("D", "T", T_in, "Q", 0, "Water")
    rho_g = CP.PropsSI("D", "T", T_in, "Q", 1, "Water")
    h_l = CP.PropsSI("H", "T", T_in, "Q", 0, "Water")
    h_g = CP.PropsSI("H", "T", T_in, "Q", 1, "Water")
    
    print(f"  飽和液体: 密度={rho_l:.1f} kg/m³, エンタルピー={h_l:.0f} J/kg")
    print(f"  飽和蒸気: 密度={rho_g:.3f} kg/m³, エンタルピー={h_g:.0f} J/kg")
    print(f"  潜熱: {h_g - h_l:.0f} J/kg")
    print()
    
    # 異なる品質での計算結果を比較
    qualities = [0.0, 0.25, 0.5, 0.75, 1.0]
    
    print("品質の違いによる物性変化:")
    print("Quality | 蒸気% | 液体% | 混合密度[kg/m³] | 混合エンタルピー[J/kg] | 利用可能熱量[kW]")
    print("-" * 85)
    
    for quality in qualities:
        try:
            profile = get_heat_source_profile(
                T_htf_in=T_in,
                Vdot_htf=m_dot,
                T_htf_out=T_out,
                heat_source_type="wet_steam",
                P_steam=P_steam,
                quality=quality,
                mass_flow_mode=True
            )
            
            # 混合物の物性を手動計算（確認用）
            h_mix = quality * h_g + (1 - quality) * h_l
            v_l = 1.0 / rho_l
            v_g = 1.0 / rho_g
            v_mix = quality * v_g + (1 - quality) * v_l
            rho_mix = 1.0 / v_mix
            
            print(f"{quality:7.2f} | {quality*100:4.0f}% | {(1-quality)*100:4.0f}% | "
                  f"{rho_mix:10.2f} | {h_mix:15.0f} | {profile.Q_available/1000:14.0f}")
            
        except Exception as e:
            print(f"{quality:7.2f} | エラー: {e}")
    
    print()

def practical_examples():
    """実際の運用例"""
    
    print("=== 実際の運用例 ===\n")
    
    T_in = 60 + 273.15
    T_out = 40 + 273.15
    P_steam = 19900
    
    scenarios = [
        {"name": "完全液体（冷却水）", "quality": 0.0, "description": "100%液体状態、通常の冷却水として使用"},
        {"name": "低品質湿り蒸気", "quality": 0.1, "description": "蒸気10%、液体90%、凝縮器出口付近の状態"},
        {"name": "中品質湿り蒸気", "quality": 0.5, "description": "蒸気50%、液体50%、典型的な二相流状態"},
        {"name": "高品質湿り蒸気", "quality": 0.9, "description": "蒸気90%、液体10%、蒸発器出口付近の状態"},
        {"name": "完全蒸気", "quality": 1.0, "description": "100%蒸気状態、乾き飽和蒸気"}
    ]
    
    for scenario in scenarios:
        print(f"{scenario['name']} (Quality = {scenario['quality']})")
        print(f"  説明: {scenario['description']}")
        
        try:
            profile = get_heat_source_profile(
                T_htf_in=T_in,
                Vdot_htf=1.0,  # 1 kg/s
                T_htf_out=T_out,
                heat_source_type="wet_steam",
                P_steam=P_steam,
                quality=scenario['quality'],
                mass_flow_mode=True
            )
            
            print(f"  → 利用可能熱量: {profile.Q_available/1000:.0f} kW")
            print(f"  → 平均比熱: {profile.cp:.0f} J/kg/K")
            
        except Exception as e:
            print(f"  → エラー: {e}")
        
        print()

def usage_guidelines():
    """使用ガイドライン"""
    
    print("=== 品質パラメータの使用ガイドライン ===\n")
    
    guidelines = [
        "1. 工業プロセスでの典型的な品質範囲:",
        "   - 蒸気タービン出口: 0.85 - 0.95",
        "   - 凝縮器: 0.0 - 0.1",
        "   - 蒸発器: 0.9 - 1.0",
        "",
        "2. 品質の測定・推定方法:",
        "   - 直接測定: 蒸気品質計（Steam Quality Meter）",
        "   - 間接推定: 温度・圧力・エンタルピーから計算",
        "   - プロセス条件: 蒸発率や凝縮率から推定",
        "",
        "3. システム設計での考慮点:",
        "   - 低品質(x<0.3): 液体が支配的、配管内流動注意",
        "   - 中品質(0.3<x<0.7): 二相流効果が顕著",
        "   - 高品質(x>0.7): 蒸気が支配的、断熱材必要",
        "",
        "4. デフォルト値 0.5 の意味:",
        "   - 保守的な中間値",
        "   - 計算が安定しやすい",
        "   - 実際の運用では適切な値に調整が必要"
    ]
    
    for guideline in guidelines:
        print(guideline)

if __name__ == "__main__":
    demonstrate_quality_parameter()
    practical_examples()
    usage_guidelines()
