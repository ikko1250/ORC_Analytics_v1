import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import CoolProp.CoolProp as CP
import os # osモジュールをインポート

# 自作モジュールから関数をインポート
from ORC_Analysis import (
    calculate_orc_performance_from_heat_source,
    DEFAULT_FLUID,
    DEFAULT_T0,
)
# Economic.pyから経済分析関数をインポート
from Economic import evaluate_orc_economics, capital_recovery_factor

def get_unique_filename(base_filename): # ユニークなファイル名を生成する関数を定義
    """
    Generates a unique filename by appending a number if the file already exists.
    e.g., 'report.txt' -> 'report_1.txt' -> 'report_2.txt'
    """
    if not os.path.exists(base_filename):
        return base_filename

    name, ext = os.path.splitext(base_filename)
    i = 1
    while True:
        new_filename = f"{name}_{i}{ext}"
        if not os.path.exists(new_filename):
            return new_filename
        i += 1

# --------------------------------------------------
# 1. 設定
# --------------------------------------------------

T_cond = 305.0  # 凝縮温度 [K] (例: 32 ℃)
eta_pump = 0.40  # Improved pump efficiency
eta_turb = 0.80  # Improved turbine efficiency
fluid_orc = DEFAULT_FLUID
fluid_htf = "Water"

# 熱源流体温度範囲 (横軸) [°C] -> convert to K
T_htf_min_C = 70
T_htf_max_C = 99
n_T_points = 20
T_htf_values_K = np.linspace(T_htf_min_C + 273.15, T_htf_max_C + 273.15, n_T_points)

# 熱源流量範囲 [m3/h]
Vdot_values_m3h = np.array([28])  # 60 m3/h のみ

superheat_C = 8.0  # ORC過熱度
pinch_delta_K = 10.0

# 経済評価のパラメータ
interest_rate = 0.05  # 金利 (5%)
project_life = 20     # プロジェクト期間 [年]
annual_hours = 8000   # 年間運転時間 [時間]
elec_price = 0.12     # 電力販売価格 [$/kWh]
maint_factor = 1.06   # メンテナンスファクター

# ベースファイル名を定義（全出力ファイルで共通）
# 熱源流量を追加（配列の最初の値を使用）
# base_filename = f"ORC_analysis_{fluid_orc}_HTF{int(T_htf_max_C)}C_V{int(Vdot_values_m3h[0])}"  # 変更点
base_filename = f"ORC_analysis_IHI20"  

# 追加: シリーズORC運転フラグ
two_stage = True  # True にすると 2台直列ORC をシミュレーション

# --------------------------------------------------
# 2. 計算
# --------------------------------------------------
results = []
econ_results = []
# 追加: シリーズORC用リスト
results_series = []
econ_series   = []

print("Heat-source sweep simulation running...")
for Vdot_m3h in Vdot_values_m3h:
    Vdot_m3s = Vdot_m3h / 3600.0
    for T_htf_K in T_htf_values_K:
        # 1台目の性能計算
        res = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_K,
            Vdot_htf=Vdot_m3s,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid_orc=fluid_orc,
            fluid_htf=fluid_htf,
            superheat_C=superheat_C,
            pinch_delta_K=pinch_delta_K,
        )
        if res is None:
            print(f"  Skipping T_htf_in={T_htf_K-273.15:.1f}°C for 1st stage, calculation failed.")
            # 1段目が失敗した場合、シリーズ計算もスキップするため、対応するNaNデータを追加
            if two_stage:
                results_series.append({
                    "T_htf_in [°C]": T_htf_K - 273.15, "Vdot_htf [m3/s]": Vdot_m3s,
                    "W_net_total [kW]": np.nan, "η_th_total [-]": np.nan,
                    "P_evap1_series [bar]": np.nan,
                    "P_evap2_series [bar]": np.nan,
                    "eps_ex_total [-]": np.nan,
                    "T_htf_in_stage2 [°C]": np.nan,
                })
                econ_series.append({
                    "T_htf_in [°C]": T_htf_K - 273.15, "Vdot_htf [m3/s]": Vdot_m3s,
                    "PEC_total_series [$]": np.nan, "Unit_elec_cost_series [$/kWh]": np.nan,
                    "Simple_PB_series [yr]": np.nan,
                })
            continue
        results.append(res) # 1台目の性能結果

        # 1台目の経済評価
        econ1 = None # 初期化
        try:
            P_evap1 = res["P_evap [bar]"] * 1e5
            T_turb_in1 = res["T_turb_in [°C]"] + 273.15
            m_orc1 = res["m_orc [kg/s]"]
            Q_in1 = res["Q_in [kW]"]

            extra_duties1 = {
                "Superheater": (Q_in1 * 0.2, 15.0),
                "Regenerator": (Q_in1 * 0.1, 10.0),
            }
            
            econ1 = evaluate_orc_economics(
                P_evap=P_evap1,
                T_turb_in=T_turb_in1,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                m_orc=m_orc1,
                extra_duties=extra_duties1,
                c_elec=elec_price,
                φ=maint_factor,
                i_rate=interest_rate,
                project_life=project_life,
                annual_hours=annual_hours,
            )
            
            econ_dict = {
                "T_htf_in [°C]": res["T_htf_in [°C]"],
                "Vdot_htf [m3/s]": res["Vdot_htf [m3/s]"],
                "PEC_total [$]": econ1["summary"]["PEC_total [$]"],
                "Unit_elec_cost [$/kWh]": econ1["summary"]["Unit elec cost [$/kWh]"],
                "Simple_PB [yr]": econ1["summary"]["Simple PB [yr]"],
                "CRF [-]": econ1["summary"]["CRF [-]"],
                "Evaporator_cost [$]": econ1["component_costs"].loc["Evaporator", "PEC [$]"],
                "Condenser_cost [$]": econ1["component_costs"].loc["Condenser", "PEC [$]"],
                "Turbine_cost [$]": econ1["component_costs"].loc["Turbine", "PEC [$]"],
                "Pump_cost [$]": econ1["component_costs"].loc["Pump", "PEC [$]"],
            }
            for component in ["Superheater", "Regenerator"]:
                if component in econ1["component_costs"].index:
                    econ_dict[f"{component}_cost [$]"] = econ1["component_costs"].loc[component, "PEC [$]"]
            econ_results.append(econ_dict)
        except Exception as e:
            print(f"1台目の経済分析でエラーが発生しました (T_htf_in={res['T_htf_in [°C]']:.1f}°C): {e}")
            # 1台目の経済分析が失敗した場合でも、対応するNaNをecon_resultsに追加
            econ_results.append({
                "T_htf_in [°C]": res["T_htf_in [°C]"], "Vdot_htf [m3/s]": res["Vdot_htf [m3/s]"],
                "PEC_total [$]": np.nan, "Unit_elec_cost [$/kWh]": np.nan, "Simple_PB [yr]": np.nan, "CRF [-]": np.nan,
                "Evaporator_cost [$]": np.nan, "Condenser_cost [$]": np.nan, "Turbine_cost [$]": np.nan, "Pump_cost [$]": np.nan,
            })
            econ1 = None # エラー時は econ1 を None に設定

        # --- 追加: 2台直列ORC のシミュレーション ---
        if two_stage:
            if econ1 is None: # 1台目の経済計算が失敗していたら、2台直列もスキップ（NaNで埋める）
                print(f"  Skipping series economic calculation for T_htf_in={res['T_htf_in [°C]']:.1f}°C due to 1st stage economic error.")
                results_series.append({
                    "T_htf_in [°C]": res["T_htf_in [°C]"], "Vdot_htf [m3/s]": Vdot_m3s,
                    "W_net_total [kW]": np.nan, "η_th_total [-]": np.nan,
                    "P_evap1_series [bar]": np.nan,
                    "P_evap2_series [bar]": np.nan,
                    "eps_ex_total [-]": np.nan,
                    "T_htf_in_stage2 [°C]": np.nan,
                })
                econ_series.append({
                    "T_htf_in [°C]": res["T_htf_in [°C]"], "Vdot_htf [m3/s]": Vdot_m3s,
                    "PEC_total_series [$]": np.nan, "Unit_elec_cost_series [$/kWh]": np.nan,
                    "Simple_PB_series [yr]": np.nan,
                })
                continue

            T_htf_out1_K = res["T_htf_out [°C]"] + 273.15
            res2 = calculate_orc_performance_from_heat_source(
                T_htf_in=T_htf_out1_K,
                Vdot_htf=Vdot_m3s,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                fluid_orc=fluid_orc,
                fluid_htf=fluid_htf,
                superheat_C=superheat_C,
                pinch_delta_K=pinch_delta_K,
            )

            if res2 is None:
                print(f"  Skipping series calculation for T_htf_in={res['T_htf_in [°C]']:.1f}°C (T_htf_out1={T_htf_out1_K-273.15:.1f}°C), not enough temperature for 2nd stage.")
                results_series.append({
                    "T_htf_in [°C]": res["T_htf_in [°C]"], "Vdot_htf [m3/s]": Vdot_m3s,
                    "W_net_total [kW]": np.nan, "η_th_total [-]": np.nan,
                    "P_evap1_series [bar]": np.nan,
                    "P_evap2_series [bar]": np.nan,
                    "eps_ex_total [-]": np.nan,
                    "T_htf_in_stage2 [°C]": np.nan,
                })
                econ_series.append({
                    "T_htf_in [°C]": res["T_htf_in [°C]"], "Vdot_htf [m3/s]": Vdot_m3s,
                    "PEC_total_series [$]": np.nan, "Unit_elec_cost_series [$/kWh]": np.nan,
                    "Simple_PB_series [yr]": np.nan,
                })
                continue

            W1 = res["W_net [kW]"]
            W2 = res2["W_net [kW]"]
            Q1_for_series_eff = res["Q_in [kW]"]
            W_total = W1 + W2
            eta_total = W_total / Q1_for_series_eff if Q1_for_series_eff > 0 else np.nan

            # 2台直列時の追加性能データ
            P_evap1_s = res["P_evap [bar]"]
            P_evap2_s = res2["P_evap [bar]"]
            E_heat_in_evap1 = res.get("Evap_E_heat_in [kW]")
            eps_ex_total = W_total / E_heat_in_evap1 if E_heat_in_evap1 is not None and E_heat_in_evap1 > 0 else np.nan

            results_series.append({
                "T_htf_in [°C]": res["T_htf_in [°C]"],
                "Vdot_htf [m3/s]": Vdot_m3s,
                "W_net_total [kW]": W_total,
                "η_th_total [-]": eta_total,
                "P_evap1_series [bar]": P_evap1_s,
                "P_evap2_series [bar]": P_evap2_s,
                "eps_ex_total [-]": eps_ex_total,
                "T_htf_in_stage2 [°C]": T_htf_out1_K - 273.15,
            })

            try:
                P_evap2 = res2["P_evap [bar]"] * 1e5
                T_turb_in2 = res2["T_turb_in [°C]"] + 273.15
                m_orc2 = res2["m_orc [kg/s]"]
                Q_in2 = res2["Q_in [kW]"]

                extra_duties2 = {
                    "Superheater": (Q_in2 * 0.2, 15.0),
                    "Regenerator": (Q_in2 * 0.1, 10.0),
                }
                
                econ2 = evaluate_orc_economics(
                    P_evap=P_evap2,
                    T_turb_in=T_turb_in2,
                    T_cond=T_cond,
                    eta_pump=eta_pump,
                    eta_turb=eta_turb,
                    m_orc=m_orc2,
                    extra_duties=extra_duties2,
                    c_elec=elec_price,
                    φ=maint_factor,
                    i_rate=interest_rate,
                    project_life=project_life,
                    annual_hours=annual_hours,
                )

                pec_total_series = econ1["summary"]["PEC_total [$]"] + econ2["summary"]["PEC_total [$]"]
                CRF = econ1["summary"]["CRF [-]"] 

                annual_generation_series = W_total * annual_hours
                if annual_generation_series <= 0:
                    c_unit_s = np.nan
                    PB_s = np.nan
                else:
                    # maint_factor はプロジェクト全体で一つと仮定（2倍しない）
                    c_unit_s  = (CRF * pec_total_series + maint_factor) / annual_generation_series
                    annual_revenue_series = W_total * annual_hours * elec_price
                    denominator_pb = annual_revenue_series - maint_factor
                    PB_s = pec_total_series / denominator_pb if denominator_pb > 0 else np.nan
                
                econ_series_dict = {
                    "T_htf_in [°C]": res["T_htf_in [°C]"],
                    "Vdot_htf [m3/s]": Vdot_m3s,
                    "PEC_total_series [$]": pec_total_series,
                    "Unit_elec_cost_series [$/kWh]": c_unit_s,
                    "Simple_PB_series [yr]": PB_s,
                }

                # 2台直列時のコンポーネント別コストを計算・格納
                for component_name in ["Evaporator", "Condenser", "Turbine", "Pump", "Superheater", "Regenerator"]:
                    cost1 = 0
                    if econ1 and "component_costs" in econ1 and component_name in econ1["component_costs"].index:
                        cost1 = econ1["component_costs"].loc[component_name, "PEC [$]"]
                    cost2 = 0
                    if econ2 and "component_costs" in econ2 and component_name in econ2["component_costs"].index:
                        cost2 = econ2["component_costs"].loc[component_name, "PEC [$]"]
                    econ_series_dict[f"{component_name}_cost_series [$]"] = cost1 + cost2
                
                econ_series.append(econ_series_dict)
            except Exception as e:
                print(f"2台目の経済分析でエラーが発生しました (T_htf_in={res['T_htf_in [°C]']:.1f}°C): {e}")
                econ_series.append({
                    "T_htf_in [°C]": res["T_htf_in [°C]"], "Vdot_htf [m3/s]": Vdot_m3s,
                    "PEC_total_series [$]": np.nan, "Unit_elec_cost_series [$/kWh]": np.nan,
                    "Simple_PB_series [yr]": np.nan,
                })

print("Simulation finished.")

if not results:
    raise RuntimeError("有効な計算結果が得られませんでした。熱源温度範囲を上げるか、設定を確認してください。")

results_df        = pd.DataFrame(results)
econ_df           = pd.DataFrame(econ_results) if econ_results else None
# 追加: シリーズORC用DataFrame
results_series_df = pd.DataFrame(results_series) if results_series else None
econ_series_df    = pd.DataFrame(econ_series)   if econ_series else None

# --------------------------------------------------
# 3. プロット
# --------------------------------------------------
plt.rcParams["font.family"] = "M+ 1c"
plt.rcParams["axes.unicode_minus"] = False

# 性能プロット
fig1, axes1 = plt.subplots(4, 1, figsize=(10, 20), sharex=True)
fig1.suptitle(f"ORC性能プロット\n条件: 熱源温度={T_htf_min_C:.1f}〜{T_htf_max_C:.1f}°C, η_p={eta_pump:.2f}, η_t={eta_turb:.2f}, 作動流体={fluid_orc}, 熱源={fluid_htf}, 過熱度={superheat_C:.1f}°C, ピンチ={pinch_delta_K:.1f}K", fontsize=12, y=0.99)
fig1.subplots_adjust(top=0.50) # クセあり, プロットの上に余白を設置, suptitleのy座標を調整すること. 

cmap = cm.get_cmap("viridis", len(Vdot_values_m3h))
markers = ["o", "s", "^", "D", "x", "*", "<", ">", "p", "h"]

# Thermal efficiency plot
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    axes1[0].plot(df_sub["T_htf_in [°C]"], df_sub["η_th [-]"] * 100,
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    axes1[0].set_ylabel("熱効率 η_th [%]")
    axes1[0].grid(True)
    axes1[0].legend(title="熱源流量")

# Net power plot
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    # 1台目のデータプロット
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if not df_sub.empty:
        axes1[1].plot(df_sub["T_htf_in [°C]"], df_sub["W_net [kW]"],
                  marker=markers[idx % len(markers)], color=cmap(idx), label=f"1台 Vdot={Vdot_m3h} m³/h")

    # 2台直列のデータプロット (two_stageがTrueで、データが存在する場合)
    if two_stage and results_series_df is not None and not results_series_df.empty:
        df_sub_series = results_series_df[
            results_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)
        ]
        if not df_sub_series.empty:
            axes1[1].plot(
                df_sub_series["T_htf_in [°C]"],
                df_sub_series["W_net_total [kW]"], # <- results_series_df の W_net_total を使用
                linestyle="--",
                marker=markers[idx % len(markers)], # マーカーも追加して区別しやすくする（任意）
                color=cmap(idx),
                label=f"2台直列 Vdot={Vdot_m3h} m³/h"
            )

axes1[1].set_xlabel("熱源入口温度 [°C]")
axes1[1].set_ylabel("正味出力 W_net [kW]")
axes1[1].grid(True)
axes1[1].legend(title="構成／熱源流量") # 凡例を表示

# Turbine inlet pressure (P_evap)
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    # 1台目のデータプロット
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if not df_sub.empty:
        axes1[2].plot(df_sub["T_htf_in [°C]"], df_sub["P_evap [bar]"],
                  marker=markers[idx % len(markers)], color=cmap(idx), label=f"1台 Vdot={Vdot_m3h} m³/h")

    # 2台直列のデータプロット
    if two_stage and results_series_df is not None and not results_series_df.empty:
        df_sub_series = results_series_df[
            results_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)
        ]
        if not df_sub_series.empty:
            axes1[2].plot(
                df_sub_series["T_htf_in [°C]"],
                df_sub_series["P_evap1_series [bar]"],
                linestyle="--",
                marker=markers[idx % len(markers)],
                color=cmap(idx),
                label=f"2台-1段目 Vdot={Vdot_m3h} m³/h"
            )
            axes1[2].plot(
                df_sub_series["T_htf_in [°C]"],
                df_sub_series["P_evap2_series [bar]"],
                linestyle=":",
                marker=markers[idx % len(markers)],
                color=cmap(idx),
                label=f"2台-2段目 Vdot={Vdot_m3h} m³/h"
            )

axes1[2].set_xlabel("熱源入口温度 [°C]")
axes1[2].set_ylabel("タービン入口圧力 P_evap [bar]")
axes1[2].grid(True)
axes1[2].legend(title="構成・段／熱源流量")

# Exergy efficiency (eps_e)
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    # 1台目のデータプロット
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if not df_sub.empty:
        axes1[3].plot(df_sub["T_htf_in [°C]"], df_sub["ε_ex [-]"],
                  marker=markers[idx % len(markers)], color=cmap(idx), label=f"1台 Vdot={Vdot_m3h} m³/h")

    # 2台直列のデータプロット
    if two_stage and results_series_df is not None and not results_series_df.empty:
        df_sub_series = results_series_df[
            results_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)
        ]
        if not df_sub_series.empty:
            axes1[3].plot(
                df_sub_series["T_htf_in [°C]"],
                df_sub_series["eps_ex_total [-]"], # <- `eps_ex_total` を使用
                linestyle="--",
                marker=markers[idx % len(markers)],
                color=cmap(idx),
                label=f"2台直列 Vdot={Vdot_m3h} m³/h (Total)"
            )

axes1[3].set_xlabel("熱源入口温度 [°C]")
axes1[3].set_ylabel("エクセルギー効率 ε [-]")
axes1[3].grid(True)
axes1[3].legend(title="構成／熱源流量")

# 追加: 性能プロットに2台直列ORCの熱効率を重ね書き
if two_stage and results_series_df is not None:
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        df2 = results_series_df[
            results_series_df["Vdot_htf [m3/s]"]
            .round(6)==(Vdot_m3h/3600.0).round(6)
        ]
        if df2.empty:
            continue
        axes1[0].plot(
            df2["T_htf_in [°C]"],
            df2["η_th_total [-]"]*100,
            linestyle="--",
            color=cmap(idx),
            label=f"2台直列 Vdot={Vdot_m3h} m³/h"
        )
    axes1[0].legend(title="熱源流量／運転モード")

plt.tight_layout()
filename1 = get_unique_filename(f"{base_filename}_performance.png")  # 変更
plt.savefig(filename1, dpi=300)
print(f"性能プロットを {filename1} に保存しました。")

# 経済性プロット（経済分析結果が存在する場合）
if econ_df is not None and not econ_df.empty:
    fig2, axes2 = plt.subplots(3, 1, figsize=(10, 15), sharex=True)
    fig2.suptitle(f"ORC経済性プロット\\n条件: 熱源温度={T_htf_min_C:.1f}〜{T_htf_max_C:.1f}°C, η_p={eta_pump:.2f}, η_t={eta_turb:.2f}, 作動流体={fluid_orc}, 熱源={fluid_htf}, 過熱度={superheat_C:.1f}°C, ピンチ={pinch_delta_K:.1f}K", fontsize=12)
    
    # 設備総コストプロット
    ax1_econ = axes2[0]
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        # 1台目のデータプロット
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if not df_sub.empty:
            ax1_econ.plot(df_sub["T_htf_in [°C]"], df_sub["PEC_total [$]"] / 1e3,
                    marker=markers[idx % len(markers)], color=cmap(idx), label=f"1台 Vdot={Vdot_m3h} m³/h")
        
        # 2台直列のデータプロット (two_stageがTrueで、データが存在する場合)
        if two_stage and econ_series_df is not None and not econ_series_df.empty:
            df_sub_series = econ_series_df[econ_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
            if not df_sub_series.empty:
                ax1_econ.plot(df_sub_series["T_htf_in [°C]"], df_sub_series["PEC_total_series [$]"] / 1e3,
                        marker=markers[idx % len(markers)], color=cmap(idx), linestyle="--", label=f"2台直列 Vdot={Vdot_m3h} m³/h")

    ax1_econ.set_ylabel("設備総コスト [千$]")
    ax1_econ.grid(True)
    ax1_econ.legend(title="構成／熱源流量")
    
    # 電力単価プロット
    ax2_econ = axes2[1]
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        # 1台目のデータプロット
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if not df_sub.empty:
            ax2_econ.plot(df_sub["T_htf_in [°C]"], df_sub["Unit_elec_cost [$/kWh]"],
                    marker=markers[idx % len(markers)], color=cmap(idx), label=f"1台 Vdot={Vdot_m3h} m³/h")

        # 2台直列のデータプロット
        if two_stage and econ_series_df is not None and not econ_series_df.empty:
            df_sub_series = econ_series_df[econ_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
            if not df_sub_series.empty:
                ax2_econ.plot(df_sub_series["T_htf_in [°C]"], df_sub_series["Unit_elec_cost_series [$/kWh]"],
                        marker=markers[idx % len(markers)], color=cmap(idx), linestyle="--", label=f"2台直列 Vdot={Vdot_m3h} m³/h")
                        
    ax2_econ.set_ylabel("発電単価 [$/kWh]")
    ax2_econ.grid(True)
    ax2_econ.legend(title="構成／熱源流量")
    
    # 単純回収期間プロット
    ax3_econ = axes2[2]
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        # 1台目のデータプロット
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if not df_sub.empty:
            ax3_econ.plot(df_sub["T_htf_in [°C]"], df_sub["Simple_PB [yr]"],
                    marker=markers[idx % len(markers)], color=cmap(idx), label=f"1台 Vdot={Vdot_m3h} m³/h")

        # 2台直列のデータプロット
        if two_stage and econ_series_df is not None and not econ_series_df.empty:
            df_sub_series = econ_series_df[econ_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
            if not df_sub_series.empty:
                ax3_econ.plot(df_sub_series["T_htf_in [°C]"], df_sub_series["Simple_PB_series [yr]"],
                        marker=markers[idx % len(markers)], color=cmap(idx), linestyle="--", label=f"2台直列 Vdot={Vdot_m3h} m³/h")

    ax3_econ.set_xlabel("熱源入口温度 [°C]")
    ax3_econ.set_ylabel("単純回収期間 [年]")
    ax3_econ.grid(True)
    ax3_econ.legend(title="構成／熱源流量")
    
    plt.tight_layout()
    filename2 = get_unique_filename(f"{base_filename}_economic.png")  # 変更
    plt.savefig(filename2, dpi=300)
    print(f"経済性プロットを {filename2} に保存しました。")
    
    # コンポーネント別コストの積み上げ図
    if two_stage and econ_series_df is not None and not econ_series_df.empty:
        fig3_series, ax_series = plt.subplots(figsize=(12, 6))
        Vdot_m3h_used = Vdot_values_m3h[0] # プロットに使用する流量を取得
        fig3_series.suptitle(f"【2台直列】コンポーネント別コスト 積み上げ図 (Vdot={Vdot_m3h_used:.1f} m³/h)\n条件: 熱源温度={T_htf_min_C:.1f}〜{T_htf_max_C:.1f}°C, η_p={eta_pump:.2f}, η_t={eta_turb:.2f}, 作動流体={fluid_orc}, 熱源={fluid_htf}, 過熱度={superheat_C:.1f}°C, ピンチ={pinch_delta_K:.1f}K", fontsize=12)
        
        df_sub_series = econ_series_df[econ_series_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h_used / 3600.0).round(6)]
        
        if not df_sub_series.empty:
            cost_columns_series = [col for col in df_sub_series.columns if col.endswith("_cost_series [$")]
            df_sub_series = df_sub_series.sort_values(by="T_htf_in [°C]")
            bottom_series = np.zeros(len(df_sub_series))
            for col in cost_columns_series:
                component_name = col.replace("_cost_series [$]", "")
                ax_series.bar(df_sub_series["T_htf_in [°C]"], df_sub_series[col]/1e3, bottom=bottom_series, label=component_name)
                bottom_series += df_sub_series[col]/1e3
            
            ax_series.set_xlabel("熱源入口温度 [°C]")
            ax_series.set_ylabel("コンポーネント別コスト (2台合計) [千$]")
            ax_series.legend(title="コンポーネント")
            ax_series.grid(True, axis='y')
            
            plt.tight_layout()
            filename3_series = get_unique_filename(f"{base_filename}_component_costs_series.png")
            plt.savefig(filename3_series, dpi=300)
            print(f"2台直列コンポーネント別コストプロットを {filename3_series} に保存しました。")

    # 1台構成の場合のコンポーネント別コスト積み上げ図 (two_stageがFalseの場合、または常に表示する場合)
    if not two_stage or (econ_df is not None and not econ_df.empty): # 常に1台構成も表示する場合は `if econ_df ...` のみ
        fig3, ax = plt.subplots(figsize=(12, 6))
        Vdot_m3h_used = Vdot_values_m3h[0] # プロットに使用する流量を取得
        title_prefix = "【1台構成】" if two_stage else ""
        fig3.suptitle(f"{title_prefix}コンポーネント別コスト 積み上げ図 (Vdot={Vdot_m3h_used:.1f} m³/h)\n条件: 熱源温度={T_htf_min_C:.1f}〜{T_htf_max_C:.1f}°C, η_p={eta_pump:.2f}, η_t={eta_turb:.2f}, 作動流体={fluid_orc}, 熱源={fluid_htf}, 過熱度={superheat_C:.1f}°C, ピンチ={pinch_delta_K:.1f}K", fontsize=12)
        
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h_used / 3600.0).round(6)]
        
        if not df_sub.empty:
            cost_columns = [col for col in df_sub.columns if col.endswith("_cost [$]") and not col.endswith("_series_cost [$]")]
            df_sub = df_sub.sort_values(by="T_htf_in [°C]")
            bottom = np.zeros(len(df_sub))
            for col in cost_columns:
                component_name = col.replace("_cost [$]", "")
                ax.bar(df_sub["T_htf_in [°C]"], df_sub[col]/1e3, bottom=bottom, label=component_name)
                bottom += df_sub[col]/1e3
            
            ax.set_xlabel("熱源入口温度 [°C]")
            ax.set_ylabel("コンポーネント別コスト [千$]")
            ax.legend(title="コンポーネント")
            ax.grid(True, axis='y')
            
            plt.tight_layout()
            filename3 = get_unique_filename(f"{base_filename}_component_costs.png")
            plt.savefig(filename3, dpi=300)
            print(f"コンポーネント別コストプロットを {filename3} に保存しました。")

# 計算結果をCSVファイルに出力
csv_filename = get_unique_filename(f"{base_filename}_performance.csv")  # 変更
results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
print(f"性能計算結果を {csv_filename} に保存しました。")

# 経済計算結果をCSVファイルに出力（結果が存在する場合）
if econ_df is not None and not econ_df.empty:
    econ_csv_filename = get_unique_filename(f"{base_filename}_economic.csv")  # 変更
    econ_df.to_csv(econ_csv_filename, index=False, encoding='utf-8-sig')
    print(f"経済計算結果を {econ_csv_filename} に保存しました。")

# ---- 追加: 2台直列の結果をCSVに出力 ----
# 2台直列の性能計算結果をCSVファイルに出力 (結果が存在する場合)
if two_stage and results_series_df is not None and not results_series_df.empty:
    series_perf_csv_filename = get_unique_filename(f"{base_filename}_performance_series.csv")
    results_series_df.to_csv(series_perf_csv_filename, index=False, encoding='utf-8-sig')
    print(f"2台直列 性能計算結果を {series_perf_csv_filename} に保存しました。")

# 2台直列の経済計算結果をCSVファイルに出力 (結果が存在する場合)
if two_stage and econ_series_df is not None and not econ_series_df.empty:
    series_econ_csv_filename = get_unique_filename(f"{base_filename}_economic_series.csv")
    econ_series_df.to_csv(series_econ_csv_filename, index=False, encoding='utf-8-sig')
    print(f"2台直列 経済計算結果を {series_econ_csv_filename} に保存しました。")
