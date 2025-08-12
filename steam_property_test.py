#!/usr/bin/env python3
"""
蒸気の流体プロファイル取得テストスクリプト
CoolPropを使用して、74t/h、60℃の蒸気の物性値を計算します。

蒸気の状態を完全に決定するには、温度と圧力が必要です。
流量は物性値の計算には直接影響しませんが、系の設計には重要な情報です。
"""

import CoolProp.CoolProp as CP
import numpy as np
import pandas as pd

def get_steam_properties(T_C, P_Pa, quality=None, force_calculation=False):
    """
    指定された温度と圧力での蒸気物性値を取得
    
    Parameters:
    T_C: 温度 [°C]
    P_Pa: 圧力 [Pa]
    quality: クオリティ（乾き度）[-], Noneの場合は温度・圧力から自動決定
    force_calculation: 物理的に不可能な条件でも強制的に計算するかどうか
    
    Returns:
    dict: 物性値の辞書
    """
    try:
        if T_C is None:
            raise ValueError("温度は必須パラメータです")
            
        T_K = T_C + 273.15
        
        # CoolPropで水蒸気の物性値を計算
        properties = {}
        
        # 基本物性（固定値）
        properties['Temperature [°C]'] = T_C
        properties['Temperature [K]'] = T_K
        properties['Pressure [Pa]'] = P_Pa
        properties['Pressure [bar]'] = P_Pa / 1e5
        properties['Pressure [MPa]'] = P_Pa / 1e6
        
        # 飽和圧力と飽和温度の計算
        try:
            P_sat = CP.PropsSI('P', 'T', T_K, 'Q', 0, 'Water')
            T_sat = CP.PropsSI('T', 'P', P_Pa, 'Q', 0, 'Water')
            T_sat_C = T_sat - 273.15
            properties['Saturation Pressure [Pa]'] = P_sat
            properties['Saturation Pressure [bar]'] = P_sat / 1e5
            properties['Saturation Temperature [°C]'] = T_sat_C
        except:
            P_sat = None
            T_sat = None
            T_sat_C = None
            properties['Saturation Pressure [Pa]'] = 'N/A'
            properties['Saturation Pressure [bar]'] = 'N/A'
            properties['Saturation Temperature [°C]'] = 'N/A'
        
        # 物理的妥当性のチェック
        warnings = []
        
        if P_sat is not None and T_sat_C is not None:
            # 指定条件の物理的妥当性をチェック
            if quality is not None:
                # 湿り飽和蒸気として指定された場合
                temp_diff = abs(T_C - T_sat_C)
                if temp_diff > 0.1:  # 0.1℃以上の差がある場合
                    warnings.append(f"警告: 湿り飽和蒸気では温度は飽和温度({T_sat_C:.1f}°C)である必要があります。指定温度{T_C:.1f}°Cは不適切です。")
                    if not force_calculation:
                        warnings.append("計算を中止します。force_calculation=Trueで強制計算可能です。")
                        properties['Warnings'] = warnings
                        return properties
            else:
                # 単相として指定された場合
                if P_Pa < P_sat and T_C >= T_sat_C:
                    warnings.append(f"警告: 圧力{P_Pa/1e5:.3f}barは温度{T_C:.1f}°Cでの飽和圧力{P_sat/1e5:.3f}barより低いです。")
                    warnings.append(f"この条件では{T_C:.1f}°Cで単相の蒸気として存在できません。")
                elif P_Pa > P_sat and T_C < T_sat_C:
                    warnings.append(f"警告: 温度{T_C:.1f}°Cは圧力{P_Pa/1e5:.3f}barでの飽和温度{T_sat_C:.1f}°Cより低いです。")
                    warnings.append(f"この条件では液体として存在します。")
        
        properties['Warnings'] = warnings
        
        # クオリティが指定されている場合（湿り飽和蒸気）
        if quality is not None:
            properties['Quality [-]'] = quality
            
            if warnings and not force_calculation:
                # 警告があり、強制計算が無効な場合は計算をスキップ
                properties['Phase'] = f"Invalid two-phase (Q={quality:.3f})"
                return properties
            
            try:
                # 飽和温度での物性値を計算（圧力固定、クオリティ指定）
                density = CP.PropsSI('D', 'P', P_Pa, 'Q', quality, 'Water')
                enthalpy = CP.PropsSI('H', 'P', P_Pa, 'Q', quality, 'Water')
                entropy = CP.PropsSI('S', 'P', P_Pa, 'Q', quality, 'Water')
                
                properties['Phase'] = f"two-phase (Q={quality:.3f})"
                
                # 2相状態では比熱は定義が複雑なので、飽和液と飽和蒸気の値を表示
                cp_liquid = CP.PropsSI('C', 'P', P_Pa, 'Q', 0, 'Water')
                cp_vapor = CP.PropsSI('C', 'P', P_Pa, 'Q', 1, 'Water')
                properties['Specific Heat (Cp) [J/kg/K]'] = f"Liquid: {cp_liquid:.1f}, Vapor: {cp_vapor:.1f}"
                properties['Specific Heat (Cp) [kJ/kg/K]'] = f"Liquid: {cp_liquid/1000:.3f}, Vapor: {cp_vapor/1000:.3f}"
                
                # 粘性と熱伝導率も同様
                viscosity_liquid = CP.PropsSI('V', 'P', P_Pa, 'Q', 0, 'Water')
                viscosity_vapor = CP.PropsSI('V', 'P', P_Pa, 'Q', 1, 'Water')
                properties['Viscosity [Pa·s]'] = f"Liquid: {viscosity_liquid:.2e}, Vapor: {viscosity_vapor:.2e}"
                
                conductivity_liquid = CP.PropsSI('L', 'P', P_Pa, 'Q', 0, 'Water')
                conductivity_vapor = CP.PropsSI('L', 'P', P_Pa, 'Q', 1, 'Water')
                properties['Thermal Conductivity [W/m/K]'] = f"Liquid: {conductivity_liquid:.3f}, Vapor: {conductivity_vapor:.3f}"
                
            except Exception as calc_error:
                warnings.append(f"計算エラー: {calc_error}")
                properties['Warnings'] = warnings
                return properties
                
        else:
            # 通常の単相計算
            try:
                density = CP.PropsSI('D', 'T', T_K, 'P', P_Pa, 'Water')
                enthalpy = CP.PropsSI('H', 'T', T_K, 'P', P_Pa, 'Water')
                entropy = CP.PropsSI('S', 'T', T_K, 'P', P_Pa, 'Water')
                
                # 比熱
                cp = CP.PropsSI('C', 'T', T_K, 'P', P_Pa, 'Water')
                properties['Specific Heat (Cp) [J/kg/K]'] = cp
                properties['Specific Heat (Cp) [kJ/kg/K]'] = cp / 1000
                
                # 粘性
                viscosity = CP.PropsSI('V', 'T', T_K, 'P', P_Pa, 'Water')
                properties['Viscosity [Pa·s]'] = viscosity
                
                # 熱伝導率
                conductivity = CP.PropsSI('L', 'T', T_K, 'P', P_Pa, 'Water')
                properties['Thermal Conductivity [W/m/K]'] = conductivity
                
                # 相の判定
                phase = CP.PhaseSI('T', T_K, 'P', P_Pa, 'Water')
                properties['Phase'] = phase
                
                # クオリティ（2相領域の場合）
                try:
                    quality_calc = CP.PropsSI('Q', 'T', T_K, 'P', P_Pa, 'Water')
                    if 0 <= quality_calc <= 1:
                        properties['Quality [-]'] = quality_calc
                    else:
                        properties['Quality [-]'] = 'N/A (single phase)'
                except:
                    properties['Quality [-]'] = 'N/A (single phase)'
                    
            except Exception as calc_error:
                warnings.append(f"計算エラー: {calc_error}")
                properties['Warnings'] = warnings
                return properties
        
        # 共通の物性値
        properties['Density [kg/m³]'] = density
        properties['Enthalpy [J/kg]'] = enthalpy
        properties['Enthalpy [kJ/kg]'] = enthalpy / 1000
        properties['Entropy [J/kg/K]'] = entropy
        properties['Entropy [kJ/kg/K]'] = entropy / 1000
        
        return properties
        
    except Exception as e:
        return {
            'Temperature [°C]': T_C if T_C is not None else 'N/A',
            'Pressure [bar]': P_Pa / 1e5 if P_Pa is not None else 'N/A',
            'Warnings': [f"致命的エラー: {e}"],
            'Phase': 'Error'
        }

def calculate_mass_flow_properties(mass_flow_kg_h, density_kg_m3):
    """
    質量流量から体積流量を計算
    
    Parameters:
    mass_flow_kg_h: 質量流量 [kg/h]
    density_kg_m3: 密度 [kg/m³]
    
    Returns:
    dict: 流量関連の計算結果
    """
    mass_flow_kg_s = mass_flow_kg_h / 3600
    volume_flow_m3_s = mass_flow_kg_s / density_kg_m3
    volume_flow_m3_h = volume_flow_m3_s * 3600
    
    return {
        'Mass Flow [kg/h]': mass_flow_kg_h,
        'Mass Flow [kg/s]': mass_flow_kg_s,
        'Volume Flow [m³/s]': volume_flow_m3_s,
        'Volume Flow [m³/h]': volume_flow_m3_h
    }

def main():
    """メイン関数"""
    print("蒸気物性値計算テスト")
    print("=" * 50)
    
    # 条件設定
    T_steam_C = 60.0  # 温度 [°C]
    mass_flow_t_h = 74.0  # 質量流量 [t/h]
    mass_flow_kg_h = mass_flow_t_h * 1000  # [kg/h]に変換
    
    print(f"条件:")
    print(f"  温度: {T_steam_C}°C")
    print(f"  質量流量: {mass_flow_t_h} t/h ({mass_flow_kg_h} kg/h)")
    print()
    
    # 異なる圧力での計算
    # 60℃での飽和圧力を先に確認
    T_K = T_steam_C + 273.15
    P_sat_Pa = CP.PropsSI('P', 'T', T_K, 'Q', 0, 'Water')
    P_sat_bar = P_sat_Pa / 1e5
    
    print(f"60℃での飽和圧力: {P_sat_bar:.3f} bar ({P_sat_Pa:.0f} Pa)")
    
    # 0.05barでの飽和温度を計算
    P_target_Pa = 0.05e5
    T_sat_at_005bar_K = CP.PropsSI('T', 'P', P_target_Pa, 'Q', 0, 'Water')
    T_sat_at_005bar_C = T_sat_at_005bar_K - 273.15
    print(f"0.05barでの飽和温度: {T_sat_at_005bar_C:.1f}°C")
    print()
    
    # 固定条件での計算
    fixed_conditions = [
        ('0.05 bar, 60°C (単相として試行)', 0.05e5, T_steam_C, None, False),
        ('0.05 bar, 60°C (単相として強制計算)', 0.05e5, T_steam_C, None, True),
        ('0.05 bar, 60°C (湿り飽和蒸気 Q=0.8)', 0.05e5, T_steam_C, 0.8, False),
        ('0.05 bar, 60°C (湿り飽和蒸気 Q=0.8, 強制)', 0.05e5, T_steam_C, 0.8, True),
        ('0.05 bar, 60°C (湿り飽和蒸気 Q=0.5)', 0.05e5, T_steam_C, 0.5, False),
        ('1 bar, 60°C (単相)', 1e5, T_steam_C, None, False),
        ('2 bar, 60°C (単相)', 2e5, T_steam_C, None, False),
    ]
    
    results_list = []
    
    for case_info in fixed_conditions:
        case_name, P_Pa, T_case_C, quality, force_calc = case_info
            
        print(f"\n【{case_name}】")
        print("-" * 50)
        
        print(f"条件: 圧力={P_Pa/1e5:.3f}bar, 温度={T_case_C:.1f}°C, 流量={mass_flow_t_h}t/h")
        if quality is not None:
            print(f"湿り飽和蒸気として計算 (クオリティ = {quality})")
        
        properties = get_steam_properties(T_case_C, P_Pa, quality, force_calc)
        
        # 警告の表示
        if 'Warnings' in properties and properties['Warnings']:
            print("\n⚠️  警告:")
            for warning in properties['Warnings']:
                print(f"   {warning}")
        
        if properties and 'Density [kg/m³]' in properties:
            # 流量関連の計算
            flow_properties = calculate_mass_flow_properties(mass_flow_kg_h, properties['Density [kg/m³]'])
            
            # 結果の表示
            print(f"\n✅ 計算結果:")
            print(f"圧力: {properties['Pressure [bar]']:.3f} bar")
            print(f"温度: {properties['Temperature [°C]']:.1f}°C")
            if 'Saturation Temperature [°C]' in properties and properties['Saturation Temperature [°C]'] != 'N/A':
                print(f"飽和温度: {properties['Saturation Temperature [°C]']:.1f}°C")
            print(f"密度: {properties['Density [kg/m³]']:.3f} kg/m³")
            print(f"エンタルピー: {properties['Enthalpy [kJ/kg]']:.1f} kJ/kg")
            print(f"エントロピー: {properties['Entropy [kJ/kg/K]']:.3f} kJ/kg/K")
            
            # 比熱の表示（湿り飽和蒸気の場合は文字列）
            if isinstance(properties.get('Specific Heat (Cp) [kJ/kg/K]'), str):
                print(f"比熱: {properties['Specific Heat (Cp) [kJ/kg/K]']}")
            elif 'Specific Heat (Cp) [kJ/kg/K]' in properties:
                print(f"比熱: {properties['Specific Heat (Cp) [kJ/kg/K]']:.3f} kJ/kg/K")
            
            # 粘性の表示（湿り飽和蒸気の場合は文字列）
            if isinstance(properties.get('Viscosity [Pa·s]'), str):
                print(f"粘性: {properties['Viscosity [Pa·s]']}")
            elif 'Viscosity [Pa·s]' in properties:
                print(f"粘性: {properties['Viscosity [Pa·s]']:.2e} Pa·s")
            
            # 熱伝導率の表示（湿り飽和蒸気の場合は文字列）
            if isinstance(properties.get('Thermal Conductivity [W/m/K]'), str):
                print(f"熱伝導率: {properties['Thermal Conductivity [W/m/K]']}")
            elif 'Thermal Conductivity [W/m/K]' in properties:
                print(f"熱伝導率: {properties['Thermal Conductivity [W/m/K]']:.3f} W/m/K")
            
            print(f"相: {properties['Phase']}")
            print(f"クオリティ: {properties.get('Quality [-]', 'N/A')}")
            print(f"体積流量: {flow_properties['Volume Flow [m³/h]']:.2f} m³/h")
            print(f"体積流量: {flow_properties['Volume Flow [m³/s]']:.4f} m³/s")
            
            # 結果をリストに保存
            result_row = {**properties, **flow_properties, 'Case': case_name}
            results_list.append(result_row)
        else:
            print(f"\n❌ 計算に失敗しました。")
    
    # 結果をDataFrameに変換して保存
    if results_list:
        df = pd.DataFrame(results_list)
        csv_filename = "fixed_conditions_steam_properties_74th.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n計算結果を {csv_filename} に保存しました。")
        
        # 主要な結果をまとめて表示
        print("\n" + "=" * 60)
        print("主要結果サマリー")
        print("=" * 60)
        
        summary_columns = ['Case', 'Temperature [°C]', 'Pressure [bar]', 'Quality [-]', 
                          'Density [kg/m³]', 'Enthalpy [kJ/kg]', 'Volume Flow [m³/h]', 'Phase']
        if not df.empty:
            print(df[summary_columns].to_string(index=False))
    
    # 固定条件(0.05bar, 60°C)での詳細分析
    print(f"\n" + "=" * 60)
    print("固定条件(0.05bar, 60°C)での詳細分析")
    print("=" * 60)
    
    P_fixed = 0.05e5
    T_fixed = 60.0
    
    print(f"固定条件: 圧力={P_fixed/1e5:.3f}bar, 温度={T_fixed:.1f}°C, 流量={mass_flow_t_h}t/h")
    print(f"0.05barでの飽和温度: {T_sat_at_005bar_C:.1f}°C")
    print(f"60℃での飽和圧力: {P_sat_bar:.3f}bar")
    print()
    
    print("異なる解釈での比較:")
    
    # 1. 単相として強制計算
    print(f"\n--- 単相として強制計算 ---")
    properties_single = get_steam_properties(T_fixed, P_fixed, None, True)
    if 'Warnings' in properties_single:
        for warning in properties_single['Warnings']:
            print(f"警告: {warning}")
    if 'Density [kg/m³]' in properties_single:
        flow_single = calculate_mass_flow_properties(mass_flow_kg_h, properties_single['Density [kg/m³]'])
        print(f"密度: {properties_single['Density [kg/m³]']:.3f} kg/m³")
        print(f"エンタルピー: {properties_single['Enthalpy [kJ/kg]']:.1f} kJ/kg")
        print(f"体積流量: {flow_single['Volume Flow [m³/h]']:.0f} m³/h")
        print(f"相: {properties_single['Phase']}")
    
    # 2. 湿り飽和蒸気として計算（様々なクオリティ）
    qualities = [0.2, 0.5, 0.8]
    
    for q in qualities:
        print(f"\n--- 湿り飽和蒸気 (Q={q:.1f}) として強制計算 ---")
        properties_q = get_steam_properties(T_fixed, P_fixed, q, True)
        
        if 'Warnings' in properties_q:
            for warning in properties_q['Warnings']:
                print(f"警告: {warning}")
        
        if 'Density [kg/m³]' in properties_q:
            flow_q = calculate_mass_flow_properties(mass_flow_kg_h, properties_q['Density [kg/m³]'])
            
            print(f"密度: {properties_q['Density [kg/m³]']:.3f} kg/m³")
            print(f"エンタルピー: {properties_q['Enthalpy [kJ/kg]']:.1f} kJ/kg")
            print(f"体積流量: {flow_q['Volume Flow [m³/h]']:.0f} m³/h")
            print(f"相: {properties_q['Phase']}")
    
    print(f"\n" + "=" * 60)
    print("結論")
    print("=" * 60)
    print("・0.05bar, 60℃の条件は物理的に矛盾しています")
    print("・60℃では最低0.199barの圧力が必要です")
    print("・0.05barでは最高32.9℃までしか温度を上げられません")
    print("・強制計算は可能ですが、実際の系では成立しません")

if __name__ == "__main__":
    main()
