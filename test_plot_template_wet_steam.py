#!/usr/bin/env python3
"""
Plot_Template.pyの湿り蒸気モードをテストするスクリプト
"""

import sys
import os

# ORC_analysisモジュールのパスを追加
sys.path.insert(0, '/home/ubuntu/cur/program/seminar_fresh')

# Plot_Template.pyの設定を湿り蒸気モードに変更してテスト
def test_wet_steam_mode():
    """湿り蒸気モードのテスト"""
    
    print("=== Plot_Template.py 湿り蒸気モード テスト ===\n")
    
    # Plot_Template.pyの設定をインポートして変更
    from ORC_analysis.Plot_Template import config
    
    # 湿り蒸気モードに変更
    config["thermo_params"]["heat_source_type"] = "wet_steam"
    
    # 設定確認
    print("変更後の設定:")
    print(f"熱源タイプ: {config['thermo_params']['heat_source_type']}")
    print(f"湿り蒸気設定: {config['wet_steam_params']}")
    print(f"温度範囲: {config['sweep_params']['wet_steam']['T_htf_min_C']}-{config['sweep_params']['wet_steam']['T_htf_max_C']}°C")
    print(f"流量範囲: {config['sweep_params']['wet_steam']['Vdot_values_m3h']}")
    print()
    
    # 単一点での計算テスト
    from ORC_analysis.Plot_Template import run_single_orc_stage
    
    T_test = 60 + 273.15  # 60°C
    Vdot_test = 10 / 3600  # 10 kg/s を m3/s として扱う（質量流量モードなので実質 kg/s）
    
    thermo_cfg = config["thermo_params"]
    econ_cfg = config["economic_params"]
    extra_duties_cfg = config["extra_duties_config"]
    wet_steam_cfg = config["wet_steam_params"]
    
    print(f"テスト条件:")
    print(f"  温度: {T_test - 273.15}°C")
    print(f"  流量: {Vdot_test * 3600} kg/s (質量流量モード)")
    print(f"  圧力: {wet_steam_cfg['P_steam']/100000:.3f} bar")
    print(f"  品質: {wet_steam_cfg['quality']}")
    print()
    
    try:
        perf_result, econ_result = run_single_orc_stage(
            T_htf_in_K=T_test,
            Vdot_m3s=Vdot_test,
            T_cond_K=thermo_cfg["T_cond_K"],
            eta_pump_val=thermo_cfg["eta_pump"],
            eta_turb_val=thermo_cfg["eta_turb"],
            orc_fluid=thermo_cfg["fluid_orc"],
            htf_fluid=thermo_cfg["fluid_htf"],
            sc_C=thermo_cfg["superheat_C"],
            pinch_K=thermo_cfg["pinch_delta_K"],
            econ_params_dict=econ_cfg,
            extra_duties_config_dict=extra_duties_cfg,
            heat_source_type="wet_steam",
            gas_config=None,
            wet_steam_config=wet_steam_cfg,
            thermo_params=thermo_cfg
        )
        
        print("計算結果:")
        if perf_result:
            print(f"  正味出力: {perf_result.get('W_net [kW]', 'N/A')} kW")
            print(f"  熱効率: {perf_result.get('η_th [-]', 'N/A')}")
            print(f"  入熱量: {perf_result.get('Q_in [kW]', 'N/A')} kW")
            print(f"  タービン入口温度: {perf_result.get('T_turb_in [°C]', 'N/A')}°C")
        else:
            print("  性能計算結果がありません")
        
        if econ_result:
            print(f"  設備総コスト: ${econ_result.get('PEC_total [$]', 'N/A'):,.0f}")
            print(f"  発電単価: {econ_result.get('Unit_elec_cost [$/kWh]', 'N/A')} $/kWh")
        else:
            print("  経済計算結果がありません")
            
    except Exception as e:
        print(f"計算エラー: {e}")
        import traceback
        traceback.print_exc()

def demonstrate_parameter_options():
    """パラメータオプションの説明"""
    
    print("\n=== 湿り蒸気パラメータの設定オプション ===\n")
    
    print("1. 基本パラメータ:")
    print("   - P_steam: 湿り蒸気圧力 [Pa]")
    print("   - quality: 品質（乾き度）[0-1]")
    print("   - mass_flow_mode: 質量流量モード (True推奨)")
    print("   - T_steam_out_offset_K: 出口温度オフセット [K]")
    print()
    
    print("2. 典型的な設定例:")
    examples = [
        {
            "name": "60°C飽和条件",
            "P_steam": 19900,
            "quality": 0.5,
            "description": "温泉地熱やボイラー排水"
        },
        {
            "name": "80°C飽和条件", 
            "P_steam": 47400,
            "quality": 0.3,
            "description": "工業廃熱の低品質蒸気"
        },
        {
            "name": "100°C飽和条件",
            "P_steam": 101325,
            "quality": 0.8,
            "description": "高品質プロセス蒸気"
        }
    ]
    
    for example in examples:
        print(f"   {example['name']}:")
        print(f"     P_steam: {example['P_steam']} Pa ({example['P_steam']/100000:.3f} bar)")
        print(f"     quality: {example['quality']}")
        print(f"     用途: {example['description']}")
        print()
    
    print("3. Plot_Template.pyでの設定方法:")
    print('   config["thermo_params"]["heat_source_type"] = "wet_steam"')
    print('   config["wet_steam_params"]["P_steam"] = 19900  # 圧力[Pa]')
    print('   config["wet_steam_params"]["quality"] = 0.5   # 品質')
    print()

if __name__ == "__main__":
    test_wet_steam_mode()
    demonstrate_parameter_options()
