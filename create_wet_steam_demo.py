#!/usr/bin/env python3
"""
Plot_Template.pyで湿り蒸気モードを実行するためのサンプル設定変更スクリプト
"""

import sys
import os

# パスを追加
sys.path.insert(0, '/home/ubuntu/cur/program/seminar_fresh')

def create_wet_steam_config():
    """湿り蒸気用の設定ファイルを作成"""
    
    # Plot_Template.pyをコピーして湿り蒸気用に修正
    template_content = '''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import os
import sys

# Add parent directory to path for absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from ORC_analysis.ORC_Analysis import (
        calculate_orc_performance_from_heat_source,
        DEFAULT_FLUID,
    )
    from ORC_analysis.Economic import evaluate_orc_economics
except ImportError:
    from .ORC_Analysis import (
        calculate_orc_performance_from_heat_source,
        DEFAULT_FLUID,
    )
    from .Economic import evaluate_orc_economics

# --- Helper functions for NaN dictionaries ---
def get_nan_perf_dict(T_htf_in_C, Vdot_m3s):
    return {
        "T_htf_in [°C]": T_htf_in_C, "Vdot_htf [m3/s]": Vdot_m3s,
        "W_net [kW]": np.nan, "η_th [-]": np.nan, "P_evap [bar]": np.nan,
        "ε_ex [-]": np.nan, "T_turb_in [°C]": np.nan, "m_orc [kg/s]": np.nan,
        "Q_in [kW]": np.nan, "T_htf_out [°C]": np.nan, "Evap_E_heat_in [kW]": np.nan,
        "Q_out [kW]": np.nan, "E_dest_Pump [kW]": np.nan, "E_dest_Evaporator [kW]": np.nan,
        "E_dest_Turbine [kW]": np.nan, "E_dest_Condenser [kW]": np.nan,
        "E_dest_Total [kW]": np.nan, "Evap_dT_lm [K]": np.nan,
    }

def get_nan_econ_dict(T_htf_in_C, Vdot_m3s):
    nan_econ = {
        "T_htf_in [°C]": T_htf_in_C, "Vdot_htf [m3/s]": Vdot_m3s,
        "PEC_total [$]": np.nan, "Unit_elec_cost [$/kWh]": np.nan,
        "Simple_PB [yr]": np.nan, "CRF [-]": np.nan,
    }
    for comp in ["Evaporator", "Condenser", "Turbine", "Pump", "Superheater", "Regenerator"]:
        nan_econ[f"{comp}_cost [$]"] = np.nan
    return nan_econ

def run_single_orc_stage(T_htf_in_K, Vdot_m3s, T_cond_K, eta_pump_val, eta_turb_val,
                         orc_fluid, htf_fluid, sc_C, pinch_K,
                         econ_params_dict, extra_duties_config_dict, 
                         heat_source_type="liquid", gas_config=None, wet_steam_config=None, thermo_params=None):
    """Calculates performance and economics for a single ORC stage."""
    
    if heat_source_type == "wet_steam" and wet_steam_config is not None:
        perf_res = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in_K, 
            Vdot_htf=Vdot_m3s, 
            T_cond=T_cond_K,
            eta_pump=eta_pump_val, 
            eta_turb=eta_turb_val, 
            fluid_orc=orc_fluid,
            superheat_C=sc_C, 
            pinch_delta_K=pinch_K,
            heat_source_type="wet_steam",
            P_steam=wet_steam_config["P_steam"],
            quality=wet_steam_config["quality"],
            mass_flow_mode=wet_steam_config["mass_flow_mode"],
            T_htf_out=T_cond_K + wet_steam_config["T_steam_out_offset_K"]
        )
    else:
        perf_res = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in_K, 
            Vdot_htf=Vdot_m3s, 
            T_cond=T_cond_K,
            eta_pump=eta_pump_val, 
            eta_turb=eta_turb_val, 
            fluid_orc=orc_fluid,
            fluid_htf=htf_fluid, 
            superheat_C=sc_C, 
            pinch_delta_K=pinch_K
        )
    
    T_htf_in_C = T_htf_in_K - 273.15
    if perf_res is None:
        return get_nan_perf_dict(T_htf_in_C, Vdot_m3s), get_nan_econ_dict(T_htf_in_C, Vdot_m3s)

    econ_res_dict = get_nan_econ_dict(perf_res["T_htf_in [°C]"], perf_res["Vdot_htf [m3/s]"])

    try:
        P_evap = perf_res["P_evap [bar]"] * 1e5
        T_turb_in = perf_res["T_turb_in [°C]"] + 273.15
        m_orc = perf_res["m_orc [kg/s]"]
        Q_in = perf_res["Q_in [kW]"]

        current_extra_duties = {}
        if Q_in > 0 and Q_in is not np.nan:
            ratios = extra_duties_config_dict.get("ratios", {})
            lmtds = extra_duties_config_dict.get("lmtds", {})
            if "Superheater" in ratios and "Superheater" in lmtds:
                 current_extra_duties["Superheater"] = (
                    Q_in * ratios["Superheater"], lmtds["Superheater"]
                )
            if "Regenerator" in ratios and "Regenerator" in lmtds:
                 current_extra_duties["Regenerator"] = (
                    Q_in * ratios["Regenerator"], lmtds["Regenerator"]
                )

        econ_eval = evaluate_orc_economics(
            P_evap=P_evap, T_turb_in=T_turb_in, T_cond=T_cond_K,
            eta_pump=eta_pump_val, eta_turb=eta_turb_val, m_orc=m_orc,
            extra_duties=current_extra_duties,
            c_elec=econ_params_dict["elec_price"], φ=econ_params_dict["maint_factor"],
            i_rate=econ_params_dict["interest_rate"], project_life=econ_params_dict["project_life"],
            annual_hours=econ_params_dict["annual_hours"],
        )
        econ_res_dict["PEC_total [$]"] = econ_eval["summary"]["PEC_total [$]"]
        econ_res_dict["Unit_elec_cost [$/kWh]"] = econ_eval["summary"]["Unit elec cost [$/kWh]"]
        econ_res_dict["Simple_PB [yr]"] = econ_eval["summary"]["Simple PB [yr]"]
        econ_res_dict["CRF [-]"] = econ_eval["summary"]["CRF [-]"]
        for comp in ["Evaporator", "Condenser", "Turbine", "Pump", "Superheater", "Regenerator"]:
            if comp in econ_eval["component_costs"].index:
                econ_res_dict[f"{comp}_cost [$]"] = econ_eval["component_costs"].loc[comp, "PEC [$]"]
    except Exception as e:
        print(f"Error in economic calculation for T_htf_in={perf_res['T_htf_in [°C]']:.1f}°C: {e}")
    return perf_res, econ_res_dict

# 湿り蒸気専用設定
config = {
    "thermo_params": {
        "T_cond_K": 305.0,
        "eta_pump": 0.40,
        "eta_turb": 0.80,
        "fluid_orc": DEFAULT_FLUID,
        "fluid_htf": "Water",
        "superheat_C": 8.0,
        "pinch_delta_K": 10.0,
        "heat_source_type": "wet_steam",  # 湿り蒸気モード
    },
    "economic_params": {
        "interest_rate": 0.05,
        "project_life": 20,
        "annual_hours": 8000,
        "elec_price": 0.12,
        "maint_factor": 1.06,
    },
    "extra_duties_config": {
        "ratios": {"Superheater": 0.2, "Regenerator": 0.1},
        "lmtds": {"Superheater": 15.0, "Regenerator": 10.0}
    },
    "sweep_params": {
        "wet_steam": {
            "T_htf_min_C": 50,
            "T_htf_max_C": 80,
            "n_T_points": 20,
            "Vdot_values_m3h": np.arange(50, 200 + 50, 50),  # 50から200まで50刻み（kg/s）
        }
    },
    "wet_steam_params": {
        "P_steam": 19900,        # 0.199 bar (60°C飽和圧力相当)
        "quality": 0.5,          # 50%品質
        "mass_flow_mode": True,
        "T_steam_out_offset_K": 20,
    },
    "run_params": {
        "base_filename": "ORC_analysis_wet_steam_demo",
    },
    "plot_params": {
        "font_family": "DejaVu Sans",
        "cmap_name": "viridis",
        "markers": ["o", "s", "^", "D"],
        "fig1_size": (10, 15),
        "fig2_size": (10, 12),
        "fig3_size": (12, 6),
    }
}

if __name__ == "__main__":
    print("=== 湿り蒸気ORC解析実行 ===")
    print(f"設定: P={config['wet_steam_params']['P_steam']/100000:.3f} bar, x={config['wet_steam_params']['quality']}")
    print(f"温度範囲: {config['sweep_params']['wet_steam']['T_htf_min_C']}-{config['sweep_params']['wet_steam']['T_htf_max_C']}°C")
    print(f"流量範囲: {config['sweep_params']['wet_steam']['Vdot_values_m3h']} kg/s")
    print()
    
    # 短時間実行用に計算点を削減
    config["sweep_params"]["wet_steam"]["n_T_points"] = 10
    config["sweep_params"]["wet_steam"]["Vdot_values_m3h"] = np.array([50, 100])
    
    # 実行部分は元のコードをそのまま使用（簡略化）
    thermo_cfg = config["thermo_params"]
    sweep_cfg = config["sweep_params"]["wet_steam"]
    wet_steam_cfg = config["wet_steam_params"]
    econ_cfg = config["economic_params"]
    extra_duties_cfg = config["extra_duties_config"]
    
    T_htf_values_K = np.linspace(
        sweep_cfg["T_htf_min_C"] + 273.15, 
        sweep_cfg["T_htf_max_C"] + 273.15, 
        sweep_cfg["n_T_points"]
    )
    
    results_list = []
    print("計算開始...")
    for Vdot_m3h in sweep_cfg["Vdot_values_m3h"]:
        Vdot_m3s = Vdot_m3h / 3600.0  # 質量流量として扱う
        for T_htf_K in T_htf_values_K:
            perf_data, econ_data = run_single_orc_stage(
                T_htf_K, Vdot_m3s, 
                thermo_cfg["T_cond_K"], thermo_cfg["eta_pump"], thermo_cfg["eta_turb"],
                thermo_cfg["fluid_orc"], thermo_cfg["fluid_htf"], 
                thermo_cfg["superheat_C"], thermo_cfg["pinch_delta_K"],
                econ_cfg, extra_duties_cfg,
                heat_source_type="wet_steam",
                wet_steam_config=wet_steam_cfg,
                thermo_params=thermo_cfg
            )
            results_list.append(perf_data)
    
    print("計算完了。結果サンプル:")
    results_df = pd.DataFrame(results_list)
    valid_results = results_df.dropna(subset=["W_net [kW]"])
    if not valid_results.empty:
        max_power_row = valid_results.loc[valid_results["W_net [kW]"].idxmax()]
        print(f"最大出力: {max_power_row['W_net [kW]']:.2f} kW")
        print(f"対応温度: {max_power_row['T_htf_in [°C]']:.1f}°C")
        print(f"熱効率: {max_power_row['η_th [-]']*100:.1f}%")
    else:
        print("有効な結果がありませんでした。")
    
    # CSVに保存
    results_df.to_csv("wet_steam_demo_results.csv", index=False)
    print("結果をwet_steam_demo_results.csvに保存しました。")
'''
    
    with open('/home/ubuntu/cur/program/seminar_fresh/wet_steam_demo.py', 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print("湿り蒸気デモファイル 'wet_steam_demo.py' を作成しました。")

if __name__ == "__main__":
    create_wet_steam_config()
