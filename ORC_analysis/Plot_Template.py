import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
# import CoolProp.CoolProp as CP # Not directly used here, but by imported modules
import os

from ORC_Analysis import (
    calculate_orc_performance_from_heat_source,
    DEFAULT_FLUID,
)
# Economic.pyから経済分析関数をインポート
from Economic import evaluate_orc_economics

# --- Helper functions for NaN dictionaries (from Plot_IHIdual.py) ---
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
        "Simple_PB [yr]": np.nan, "CRF [-]": np.nan, # Added CRF
    }
    for comp in ["Evaporator", "Condenser", "Turbine", "Pump", "Superheater", "Regenerator"]:
        nan_econ[f"{comp}_cost [$]"] = np.nan
    return nan_econ

# --- Function to run a single ORC stage (performance and economics) (from Plot_IHIdual.py) ---
def run_single_orc_stage(T_htf_in_K, Vdot_m3s, T_cond_K, eta_pump_val, eta_turb_val,
                         orc_fluid, htf_fluid, sc_C, pinch_K,
                         econ_params_dict, extra_duties_config_dict):
    """Calculates performance and economics for a single ORC stage."""
    perf_res = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in_K, Vdot_htf=Vdot_m3s, T_cond=T_cond_K,
        eta_pump=eta_pump_val, eta_turb=eta_turb_val, fluid_orc=orc_fluid,
        fluid_htf=htf_fluid, superheat_C=sc_C, pinch_delta_K=pinch_K
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
        if Q_in > 0 and Q_in is not np.nan : # Ensure Q_in is valid
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

# --------------------------------------------------
# 1. 設定
# --------------------------------------------------
config = {
    "thermo_params": {
        "T_cond_K": 305.0,  # 凝縮温度 [K] (例: 32 ℃)
        "eta_pump": 0.40,
        "eta_turb": 0.80,
        "fluid_orc": DEFAULT_FLUID,
        "fluid_htf": "Water",
        "superheat_C": 8.0,  # ORC過熱度
        "pinch_delta_K": 10.0,
    },
    "economic_params": {
        "interest_rate": 0.05,  # 金利 (5%)
        "project_life": 20,     # プロジェクト期間 [年]
        "annual_hours": 8000,   # 年間運転時間 [時間]
        "elec_price": 0.12,     # 電力販売価格 [$/kWh]
        "maint_factor": 1.06,   # メンテナンスファクター (evaluate_orc_economicsでは φ として使用)
    },
    "extra_duties_config": { # 追加熱交換器の設定
        "ratios": {"Superheater": 0.2, "Regenerator": 0.1}, # Q_in に対する熱負荷の割合
        "lmtds": {"Superheater": 15.0, "Regenerator": 10.0} # LMTD [K]
    },
    "sweep_params": {
        "T_htf_min_C": 70,
        "T_htf_max_C": 99,
        "n_T_points": 100, # 元の n_T_points
        "Vdot_values_m3h": np.arange(20, 50 + 5, 5),  # 20から50まで5刻み
    },
    "run_params": {
        "base_filename": "ORC_analysis_IHI20_template_ver", # ベースファイル名変更
    },
    "plot_params": {
        "font_family": "M+ 1c",
        "cmap_name": "viridis",
        "markers": ["o", "s", "^", "D", "x", "*", "<", ">", "p", "h"],
        "fig1_size": (10, 20), # Performance plots
        "fig2_size": (10, 15), # Economic plots
        "fig3_size": (12, 6),  # Stacked bar plot
    }
}

thermo_cfg = config["thermo_params"]
econ_cfg = config["economic_params"]
extra_duties_cfg = config["extra_duties_config"]
sweep_cfg = config["sweep_params"]
run_cfg = config["run_params"]
plot_cfg = config["plot_params"]

T_htf_values_K = np.linspace(sweep_cfg["T_htf_min_C"] + 273.15, sweep_cfg["T_htf_max_C"] + 273.15, sweep_cfg["n_T_points"])

# --------------------------------------------------
# 2. 計算
# --------------------------------------------------
results_list = []
econ_list = []

print("Heat-source sweep simulation running...")
for Vdot_m3h in sweep_cfg["Vdot_values_m3h"]:
    Vdot_m3s = Vdot_m3h / 3600.0
    for T_htf_K in T_htf_values_K:
        perf_data, econ_data = run_single_orc_stage(
            T_htf_K, Vdot_m3s, thermo_cfg["T_cond_K"], thermo_cfg["eta_pump"], thermo_cfg["eta_turb"],
            thermo_cfg["fluid_orc"], thermo_cfg["fluid_htf"], thermo_cfg["superheat_C"], thermo_cfg["pinch_delta_K"],
            econ_cfg, extra_duties_cfg
        )
        results_list.append(perf_data)
        econ_list.append(econ_data)

print("Simulation finished.")

if not results_list:
    raise RuntimeError("有効な計算結果が得られませんでした。熱源温度範囲を上げるか、設定を確認してください。")

results_df = pd.DataFrame(results_list)
econ_df = pd.DataFrame(econ_list)

# --------------------------------------------------
# 3. プロット
# --------------------------------------------------
plt.rcParams["font.family"] = plot_cfg["font_family"]
plt.rcParams["axes.unicode_minus"] = False

# --- Plotting helper functions (from Plot_IHIdual.py) ---
def plot_lines(ax, df, x_col, y_col, Vdots_m3h_list, cmap_obj, markers_list, label_prefix="", linestyle="-", y_factor=1.0):
    """Helper function to plot lines for different Vdot values."""
    for idx, Vdot_m3h in enumerate(Vdots_m3h_list):
        df_sub = df[df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if df_sub.empty or df_sub[y_col].isnull().all(): # Skip if no data or all y data is NaN
            continue
        ax.plot(df_sub[x_col], df_sub[y_col] * y_factor,
                  marker=markers_list[idx % len(markers_list)], color=cmap_obj(idx),
                  label=f"{label_prefix}Vdot={Vdot_m3h} m³/h", linestyle=linestyle)

def setup_axis(ax, xlabel, ylabel, legend_title, title=None):
    """Helper function to set common axis properties."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    if title:
        ax.set_title(title)
    if ax.has_data():
         ax.legend(title=legend_title)

# 性能プロット
fig1_title = (f"ORC性能プロット\n条件: 熱源温度={sweep_cfg['T_htf_min_C']:.1f}〜{sweep_cfg['T_htf_max_C']:.1f}°C, "
              f"η_p={thermo_cfg['eta_pump']:.2f}, η_t={thermo_cfg['eta_turb']:.2f}, 作動流体={thermo_cfg['fluid_orc']}, "
              f"熱源={thermo_cfg['fluid_htf']}, 過熱度={thermo_cfg['superheat_C']:.1f}°C, ピンチ={thermo_cfg['pinch_delta_K']:.1f}K")

fig1, axes1 = plt.subplots(4, 1, figsize=plot_cfg["fig1_size"], sharex=True)
fig1.suptitle(fig1_title, fontsize=12, y=0.985)

cmap = cm.get_cmap(plot_cfg["cmap_name"], len(sweep_cfg["Vdot_values_m3h"]))
markers = plot_cfg["markers"]

# Thermal efficiency plot
plot_lines(axes1[0], results_df, "T_htf_in [°C]", "η_th [-]", sweep_cfg["Vdot_values_m3h"], cmap, markers, y_factor=100)
setup_axis(axes1[0], "熱源入口温度 [°C]", "熱効率 η_th [%]", "熱源流量")

# Net power plot
plot_lines(axes1[1], results_df, "T_htf_in [°C]", "W_net [kW]", sweep_cfg["Vdot_values_m3h"], cmap, markers)
setup_axis(axes1[1], "熱源入口温度 [°C]", "正味出力 W_net [kW]", "熱源流量")

# Turbine inlet pressure (P_evap)
plot_lines(axes1[2], results_df, "T_htf_in [°C]", "P_evap [bar]", sweep_cfg["Vdot_values_m3h"], cmap, markers)
setup_axis(axes1[2], "熱源入口温度 [°C]", "タービン入口圧力 P_evap [bar]", "熱源流量")

# Exergy efficiency (eps_e)
plot_lines(axes1[3], results_df, "T_htf_in [°C]", "ε_ex [-]", sweep_cfg["Vdot_values_m3h"], cmap, markers)
setup_axis(axes1[3], "熱源入口温度 [°C]", "エクセルギー効率 ε [-]", "熱源流量")

plt.tight_layout()
filename1 = f"{run_cfg['base_filename']}_performance.png"
plt.savefig(filename1, dpi=300)
print(f"性能プロットを {filename1} に保存しました。")
plt.close(fig1)

# 経済性プロット（経済分析結果が存在する場合）
if econ_df is not None and not econ_df.empty:
    fig2_title = (f"ORC経済性プロット\n条件: 熱源温度={sweep_cfg['T_htf_min_C']:.1f}〜{sweep_cfg['T_htf_max_C']:.1f}°C, "
                  f"η_p={thermo_cfg['eta_pump']:.2f}, η_t={thermo_cfg['eta_turb']:.2f}, 作動流体={thermo_cfg['fluid_orc']}, "
                  f"熱源={thermo_cfg['fluid_htf']}, 過熱度={thermo_cfg['superheat_C']:.1f}°C, ピンチ={thermo_cfg['pinch_delta_K']:.1f}K")

    fig2, axes2 = plt.subplots(3, 1, figsize=plot_cfg["fig2_size"], sharex=True)
    fig2.suptitle(fig2_title, fontsize=12)

    # 設備総コストプロット
    plot_lines(axes2[0], econ_df, "T_htf_in [°C]", "PEC_total [$]", sweep_cfg["Vdot_values_m3h"], cmap, markers, y_factor=1e-3)
    setup_axis(axes2[0], "熱源入口温度 [°C]", "設備総コスト [千$]", "熱源流量")

    # 電力単価プロット
    plot_lines(axes2[1], econ_df, "T_htf_in [°C]", "Unit_elec_cost [$/kWh]", sweep_cfg["Vdot_values_m3h"], cmap, markers)
    setup_axis(axes2[1], "熱源入口温度 [°C]", "発電単価 [$/kWh]", "熱源流量")

    # 単純回収期間プロット
    plot_lines(axes2[2], econ_df, "T_htf_in [°C]", "Simple_PB [yr]", sweep_cfg["Vdot_values_m3h"], cmap, markers)
    setup_axis(axes2[2], "熱源入口温度 [°C]", "単純回収期間 [年]", "熱源流量")

    plt.tight_layout()
    filename2 = f"{run_cfg['base_filename']}_economic.png"
    plt.savefig(filename2, dpi=300)
    print(f"経済性プロットを {filename2} に保存しました。")
    plt.close(fig2)

    # コンポーネント別コストの積み上げ図
    def plot_stacked_bars(df_to_plot, Vdot_m3h_val, x_col, cost_suffix, fig_title_prefix, ylabel_text, filename_suffix, base_fname, fig_size):
        fig, ax = plt.subplots(figsize=fig_size)
        full_title = (f"{fig_title_prefix}コンポーネント別コスト 積み上げ図 (Vdot={Vdot_m3h_val:.1f} m³/h)\n"
                      f"条件: 熱源温度={sweep_cfg['T_htf_min_C']:.1f}〜{sweep_cfg['T_htf_max_C']:.1f}°C, η_p={thermo_cfg['eta_pump']:.2f}, "
                      f"η_t={thermo_cfg['eta_turb']:.2f}, 作動流体={thermo_cfg['fluid_orc']}, 熱源={thermo_cfg['fluid_htf']}, "
                      f"過熱度={thermo_cfg['superheat_C']:.1f}°C, ピンチ={thermo_cfg['pinch_delta_K']:.1f}K")
        fig.suptitle(full_title, fontsize=10)

        df_sub = df_to_plot[df_to_plot["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h_val / 3600.0).round(6)]
        if not df_sub.empty:
            cost_columns = [col for col in df_sub.columns if col.endswith(cost_suffix)]
            df_sub_sorted = df_sub.sort_values(by=x_col).copy()
            
            bottom = np.zeros(len(df_sub_sorted))
            for col in cost_columns:
                component_name = col.replace(cost_suffix, "")
                costs_to_plot = pd.to_numeric(df_sub_sorted[col], errors='coerce').fillna(0) / 1e3
                ax.bar(df_sub_sorted[x_col], costs_to_plot, bottom=bottom, label=component_name)
                bottom += costs_to_plot
            
            setup_axis(ax, "熱源入口温度 [°C]", ylabel_text, "コンポーネント")
            plt.tight_layout()
            fname = f"{base_fname}_{filename_suffix}.png"
            plt.savefig(fname, dpi=300)
            print(f"{fig_title_prefix}コンポーネント別コストプロットを {fname} に保存しました。")
        else:
            print(f"データがありません。{fig_title_prefix}コンポーネント別コストプロット (Vdot={Vdot_m3h_val:.1f} m³/h)。")
        plt.close(fig)

    Vdot_for_stacked_plot = sweep_cfg["Vdot_values_m3h"][0]
    plot_stacked_bars(econ_df, Vdot_for_stacked_plot, "T_htf_in [°C]", "_cost [$]",
                      "", "コンポーネント別コスト [千$]", "component_costs",
                      run_cfg['base_filename'], plot_cfg["fig3_size"])

# 計算結果をCSVファイルに出力
csv_filename_perf = f"{run_cfg['base_filename']}_performance.csv"
results_df.to_csv(csv_filename_perf, index=False, encoding='utf-8-sig')
print(f"性能計算結果を {csv_filename_perf} に保存しました。")

# 経済計算結果をCSVファイルに出力（結果が存在する場合）
if econ_df is not None and not econ_df.empty:
    econ_csv_filename = f"{run_cfg['base_filename']}_economic.csv"
    econ_df.to_csv(econ_csv_filename, index=False, encoding='utf-8-sig')
    print(f"経済計算結果を {econ_csv_filename} に保存しました。")
