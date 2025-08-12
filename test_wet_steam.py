#!/usr/bin/env python3
"""
湿り蒸気（二相混合）熱源のテストスクリプト
"""

from ORC_analysis.heat_source import get_heat_source_profile

def test_wet_steam():
    """60℃、0.199barの湿り蒸気をテスト"""
    
    # テスト条件
    T_in = 60 + 273.15  # K (60°C)
    T_out = 40 + 273.15  # K (40°C)
    P_steam = 0.199 * 100000  # Pa (0.199 bar)
    m_dot = 1.0  # kg/s
    quality = 0.5  # 50%品質
    
    print("=== 湿り蒸気熱源テスト ===")
    print(f"入口温度: {T_in - 273.15}°C")
    print(f"出口温度: {T_out - 273.15}°C")
    print(f"圧力: {P_steam/100000:.3f} bar")
    print(f"質量流量: {m_dot} kg/s")
    print(f"品質（乾き度）: {quality}")
    print()
    
    try:
        # 湿り蒸気プロファイル計算
        profile = get_heat_source_profile(
            T_htf_in=T_in,
            Vdot_htf=m_dot,  # 質量流量として扱う
            T_htf_out=T_out,
            heat_source_type="wet_steam",
            P_steam=P_steam,
            quality=quality,
            mass_flow_mode=True
        )
        
        print("計算結果:")
        print(f"質量流量: {profile.m_dot:.3f} kg/s")
        print(f"平均比熱: {profile.cp:.0f} J/kg/K")
        print(f"入口温度: {profile.T_in - 273.15:.1f}°C")
        print(f"最低出口温度: {profile.T_out_min - 273.15:.1f}°C")
        print(f"利用可能熱量: {profile.Q_available/1000:.0f} kW")
        print(f"二相流フラグ: {profile.is_two_phase}")
        print()
        
        # 温度計算テスト
        print("熱交換量による温度変化:")
        for Q_frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            Q_test = Q_frac * profile.Q_available
            T_result = profile.get_temp_for_heat(Q_test)
            print(f"  {Q_frac*100:3.0f}%熱交換時: {T_result - 273.15:.1f}°C")
        
    except Exception as e:
        print(f"エラー: {e}")

def test_comparison():
    """単相液体と湿り蒸気の比較"""
    
    T_in = 60 + 273.15  # K
    T_out = 40 + 273.15  # K
    V_dot = 0.001  # m³/s (1 L/s)
    
    print("\n=== 単相液体 vs 湿り蒸気 比較 ===")
    
    # 単相液体
    try:
        liquid_profile = get_heat_source_profile(
            T_htf_in=T_in,
            Vdot_htf=V_dot,
            T_htf_out=T_out,
            heat_source_type="liquid",
            P_htf=19900  # 0.199 bar
        )
        
        print("単相液体（60℃水）:")
        print(f"  質量流量: {liquid_profile.m_dot:.3f} kg/s")
        print(f"  利用可能熱量: {liquid_profile.Q_available/1000:.1f} kW")
        print(f"  二相流フラグ: {liquid_profile.is_two_phase}")
        
    except Exception as e:
        print(f"単相液体計算エラー: {e}")
    
    # 湿り蒸気（50%品質）
    try:
        wet_steam_profile = get_heat_source_profile(
            T_htf_in=T_in,
            Vdot_htf=V_dot,
            T_htf_out=T_out,
            heat_source_type="wet_steam",
            P_steam=19900,
            quality=0.5,
            mass_flow_mode=False  # 体積流量モード
        )
        
        print("湿り蒸気（50%品質）:")
        print(f"  質量流量: {wet_steam_profile.m_dot:.6f} kg/s")
        print(f"  利用可能熱量: {wet_steam_profile.Q_available/1000:.1f} kW")
        print(f"  二相流フラグ: {wet_steam_profile.is_two_phase}")
        
    except Exception as e:
        print(f"湿り蒸気計算エラー: {e}")

if __name__ == "__main__":
    test_wet_steam()
    test_comparison()
