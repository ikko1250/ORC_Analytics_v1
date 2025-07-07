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
from Economic import evaluate_orc_economics

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
eta_pump = 0.70  # Improved pump efficiency
eta_turb = 0.85  # Improved turbine efficiency
fluid_orc = DEFAULT_FLUID
fluid_htf = "Water"

# 熱源流体温度範囲 (横軸) [°C] -> convert to K
T_htf_min_C = 70
T_htf_max_C = 100.0
n_T_points = 100
T_htf_values_K = np.linspace(T_htf_min_C + 273.15, T_htf_max_C + 273.15, n_T_points)

# 熱源流量範囲 [m3/h]
Vdot_values_m3h = np.array([80])  # 60 m3/h のみ

superheat_C = 12.0  # ORC過熱度
pinch_delta_K = 10.0

# 経済評価のパラメータ
interest_rate = 0.05  # 金利 (5%)
project_life = 20     # プロジェクト期間 [年]
annual_hours = 8000   # 年間運転時間 [時間]
elec_price = 0.12     # 電力販売価格 [$/kWh]
maint_factor = 1.06   # メンテナンスファクター

# ベースファイル名を定義（全出力ファイルで共通）
# base_filename = f"ORC_analysis_{fluid_orc}_HTF{int(T_htf_min_C)}-{int(T_htf_max_C)}C"  # option
base_filename = f"ORC_analysis_Thermapower"  

# --------------------------------------------------
# 2. 計算
# --------------------------------------------------
results = []
econ_results = []
print("Heat-source sweep simulation running...")
for Vdot_m3h in Vdot_values_m3h:
    # m3/h を m3/s に変換
    Vdot_m3s = Vdot_m3h / 3600.0
    for T_htf_K in T_htf_values_K:
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
        if res is not None:
            results.append(res)
            
            # 経済評価を実行
            try:
                # 経済分析に必要なパラメータを取得
                P_evap = res["P_evap [bar]"] * 1e5  # bar to Pa
                T_turb_in = res["T_turb_in [°C]"] + 273.15  # °C to K
                m_orc = res["m_orc [kg/s]"]
                
                # 追加のヒート交換器の熱負荷とLMTD（例として設定）
                extra_duties = {
                    "Superheater": (res["Q_in [kW]"] * 0.2, 15.0),  # 例: 全熱入力の20%を過熱器が担当
                    "Regenerator": (res["Q_in [kW]"] * 0.1, 10.0),  # 例: 全熱入力の10%を再生器が担当
                }
                
                # 経済分析の実行
                econ = evaluate_orc_economics(
                    P_evap=P_evap,
                    T_turb_in=T_turb_in,
                    T_cond=T_cond,
                    eta_pump=eta_pump,
                    eta_turb=eta_turb,
                    m_orc=m_orc,
                    extra_duties=extra_duties,
                    c_elec=elec_price,
                    φ=maint_factor,
                    i_rate=interest_rate,
                    project_life=project_life,
                    annual_hours=annual_hours,
                )
                
                # 経済分析結果を辞書に格納
                econ_dict = {
                    "T_htf_in [°C]": res["T_htf_in [°C]"],
                    "Vdot_htf [m3/s]": res["Vdot_htf [m3/s]"],
                    "PEC_total [$]": econ["summary"]["PEC_total [$]"],
                    "Unit_elec_cost [$/kWh]": econ["summary"]["Unit elec cost [$/kWh]"],
                    "Simple_PB [yr]": econ["summary"]["Simple PB [yr]"],
                    "CRF [-]": econ["summary"]["CRF [-]"],
                    "Evaporator_cost [$]": econ["component_costs"].loc["Evaporator", "PEC [$]"],
                    "Condenser_cost [$]": econ["component_costs"].loc["Condenser", "PEC [$]"],
                    "Turbine_cost [$]": econ["component_costs"].loc["Turbine", "PEC [$]"],
                    "Pump_cost [$]": econ["component_costs"].loc["Pump", "PEC [$]"],
                }
                
                # Superheaterなど追加の熱交換器のコストが存在する場合は追加
                for component in ["Superheater", "Regenerator"]:
                    if component in econ["component_costs"].index:
                        econ_dict[f"{component}_cost [$]"] = econ["component_costs"].loc[component, "PEC [$]"]
                
                econ_results.append(econ_dict)
            except Exception as e:
                print(f"経済分析でエラーが発生しました: {e}")
print("Simulation finished.")

if not results:
    raise RuntimeError("有効な計算結果が得られませんでした。熱源温度範囲を上げるか、設定を確認してください。")

results_df = pd.DataFrame(results)
econ_df = pd.DataFrame(econ_results) if econ_results else None

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
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    axes1[1].plot(df_sub["T_htf_in [°C]"], df_sub["W_net [kW]"],
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    axes1[1].set_xlabel("熱源入口温度 [°C]")
    axes1[1].set_ylabel("正味出力 W_net [kW]")
    axes1[1].grid(True)

# Turbine inlet pressure (P_evap)
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    axes1[2].plot(df_sub["T_htf_in [°C]"], df_sub["P_evap [bar]"],
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    axes1[2].set_xlabel("熱源入口温度 [°C]")
    axes1[2].set_ylabel("タービン内圧力 P_evap [bar]")
    axes1[2].grid(True)
    axes1[2].legend(title="熱源流量")

# Exergy efficiency (eps_e)
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    axes1[3].plot(df_sub["T_htf_in [°C]"], df_sub["ε_ex [-]"],
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    axes1[3].set_xlabel("熱源入口温度 [°C]")
    axes1[3].set_ylabel("エクセルギー効率 ε [-]")
    axes1[3].grid(True)
    axes1[3].legend(title="熱源流量")

plt.tight_layout()
filename1 = get_unique_filename(f"{base_filename}_performance.png")  # 変更
plt.savefig(filename1, dpi=300)
print(f"性能プロットを {filename1} に保存しました。")

# 経済性プロット（経済分析結果が存在する場合）
if econ_df is not None and not econ_df.empty:
    fig2, axes2 = plt.subplots(3, 1, figsize=(10, 15), sharex=True)
    fig2.suptitle(f"ORC経済性プロット\n条件: 熱源温度={T_htf_min_C:.1f}〜{T_htf_max_C:.1f}°C, η_p={eta_pump:.2f}, η_t={eta_turb:.2f}, 作動流体={fluid_orc}, 熱源={fluid_htf}, 過熱度={superheat_C:.1f}°C, ピンチ={pinch_delta_K:.1f}K", fontsize=12)
    
    # 設備総コストプロット
    ax1_econ = axes2[0]
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if df_sub.empty:
            continue
        ax1_econ.plot(df_sub["T_htf_in [°C]"], df_sub["PEC_total [$]"] / 1e3,
                marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
        ax1_econ.set_ylabel("設備総コスト [千$]")
        ax1_econ.grid(True)
        ax1_econ.legend(title="熱源流量")
    
    # 電力単価プロット
    ax2_econ = axes2[1]
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if df_sub.empty:
            continue
        ax2_econ.plot(df_sub["T_htf_in [°C]"], df_sub["Unit_elec_cost [$/kWh]"],
                marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
        ax2_econ.set_ylabel("発電単価 [$/kWh]")
        ax2_econ.grid(True)
    
    # 単純回収期間プロット
    ax3_econ = axes2[2]
    for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
        df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
        if df_sub.empty:
            continue
        ax3_econ.plot(df_sub["T_htf_in [°C]"], df_sub["Simple_PB [yr]"],
                marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
        ax3_econ.set_xlabel("熱源入口温度 [°C]")
        ax3_econ.set_ylabel("単純回収期間 [年]")
        ax3_econ.grid(True)
        ax3_econ.legend(title="熱源流量")
    
    plt.tight_layout()
    filename2 = get_unique_filename(f"{base_filename}_economic.png")  # 変更
    plt.savefig(filename2, dpi=300)
    print(f"経済性プロットを {filename2} に保存しました。")
    
    # コンポーネント別コストの積み上げ図
    fig3, ax = plt.subplots(figsize=(12, 6))
    
    # 最初の流量のデータを使用（単一流量の場合は問題なし）
    Vdot_m3h_used = Vdot_values_m3h[0] # プロットに使用する流量を取得
    fig3.suptitle(f"コンポーネント別コスト 積み上げ図 (Vdot={Vdot_m3h_used:.1f} m³/h)\n条件: 熱源温度={T_htf_min_C:.1f}〜{T_htf_max_C:.1f}°C, η_p={eta_pump:.2f}, η_t={eta_turb:.2f}, 作動流体={fluid_orc}, 熱源={fluid_htf}, 過熱度={superheat_C:.1f}°C, ピンチ={pinch_delta_K:.1f}K", fontsize=12)
    
    df_sub = econ_df[econ_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h_used / 3600.0).round(6)] # 取得した流量を使用
    
    if not df_sub.empty:
        # コンポーネント別コスト列を抽出
        cost_columns = [col for col in df_sub.columns if col.endswith("_cost [$]")]
        
        # 温度でソート
        df_sub = df_sub.sort_values(by="T_htf_in [°C]")
        
        # 積み上げ棒グラフ用のデータ準備
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
        filename3 = get_unique_filename(f"{base_filename}_component_costs.png")  # 変更
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
