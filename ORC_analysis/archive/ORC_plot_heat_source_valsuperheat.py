import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import CoolProp.CoolProp as CP

# 自作モジュールから関数をインポート
from ORC_Analysis import (
    calculate_orc_performance_from_heat_source,
    DEFAULT_FLUID,
    DEFAULT_T0,
)

# --------------------------------------------------
# 1. 設定
# --------------------------------------------------
T_cond = 305.0  # 凝縮温度 [K] (例: 32 ℃)
eta_pump = 0.75
eta_turb = 0.80
fluid_orc = DEFAULT_FLUID
fluid_htf = "Water"

# 熱源流体温度範囲 (横軸) [°C] -> convert to K
T_htf_min_C = 70
T_htf_max_C = 100.0
n_T_points = 100
T_htf_values_K = np.linspace(T_htf_min_C + 273.15, T_htf_max_C + 273.15, n_T_points)

# 熱源流量範囲 [m3/h]
# Vdot_values_m3h = np.arange(5, 40, 5)  # 5 〜 35 m3/h
Vdot_values_m3h = np.array([60])  # 28 m3/h のみ

# 複数の過熱度を設定
superheat_values_C = np.arange(5, 25, 5) # 5, 10, 15, 20 °C
pinch_delta_K = 8.0

# 熱源流体の圧力 [Pa] (例: 標準大気圧を想定)
P_htf = 101325.0

# --------------------------------------------------
# 2. 計算
# --------------------------------------------------
results = []
print("Heat-source and superheat sweep simulation running...")
# 過熱度のループを追加
for superheat_C in superheat_values_C:
    print(f"  Calculating for superheat = {superheat_C} °C...")
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
                superheat_C=superheat_C, # ここでループ変数を使用
                pinch_delta_K=pinch_delta_K,
            )
            if res is not None:
                # 熱源流体の密度を計算 [kg/m3] (入口温度と圧力を使用)
                rho_htf = CP.PropsSI("D", "T", T_htf_K, "P", P_htf, fluid_htf)
                # 熱源流体の質量流量を計算 [kg/s]
                m_htf = Vdot_m3s * rho_htf
                # 結果に質量流量の情報を追加
                res['m_htf [kg/s]'] = m_htf

                # 結果に熱源入口温度の情報を追加
                res['T_htf_in [K]'] = T_htf_K
                
                # 熱源出口温度をケルビン単位でも追加
                T_htf_out_K = res['T_htf_out [°C]'] + 273.15
                res['T_htf_out [K]'] = T_htf_out_K
                
                # 熱源エクセルギー効率の計算をここで行う
                # 平均温度を計算
                T_avg = 0.5 * (T_htf_K + T_htf_out_K)
                # 比熱を計算
                Cp_htf = CP.PropsSI("Cpmass", "T", T_avg, "P", P_htf, fluid_htf)
                # 熱源エクセルギー効率を計算
                eps_ex_hs = res["W_net [kW]"] / (m_htf * (T_htf_K - DEFAULT_T0) * Cp_htf / 1e3)
                # 結果に追加
                res['eps_ex_hs [-]'] = eps_ex_hs

                # 結果に過熱度の情報を追加
                res['superheat_C'] = superheat_C
                results.append(res)
print("Simulation finished.")

if not results:
    raise RuntimeError("有効な計算結果が得られませんでした。熱源温度範囲を上げるか、設定を確認してください。")

results_df = pd.DataFrame(results)

# --------------------------------------------------
# 3. プロット
# --------------------------------------------------
plt.rcParams["font.family"] = "M+ 1c"
plt.rcParams["axes.unicode_minus"] = False

# 5つのサブプロットを初めから作成するように変更
fig, axes = plt.subplots(5, 1, figsize=(10, 25), sharex=True)

# cmap = cm.get_cmap("viridis", len(Vdot_values_m3h)) <- Vdot ではなく superheat で色分け
import matplotlib
cmap = matplotlib.colormaps["viridis"].resampled(len(superheat_values_C))
markers = ["o", "s", "^", "D", "x", "*", "<", ">", "p", "h"]

# Thermal efficiency plot
ax1 = axes[0]
# Vdot_values_m3h ではなく superheat_values_C でループ
for idx, sh_C in enumerate(superheat_values_C):
    # superheat_C でフィルタリング
    df_sub = results_df[results_df["superheat_C"] == sh_C]
    if df_sub.empty:
        continue
    # Vdot_m3h ではなく sh_C でラベル付け
    ax1.plot(df_sub["T_htf_in [°C]"], df_sub["η_th [-]"] * 100,
              marker=markers[idx % len(markers)], color=cmap(idx / (len(superheat_values_C) - 1)), label=f"過熱度={sh_C} °C")
    ax1.set_ylabel("熱効率 η_th [%]")
    ax1.grid(True)
    ax1.legend(title="ORC過熱度") # 凡例タイトル変更

# Net power plot
ax2 = axes[1]
# Vdot_values_m3h ではなく superheat_values_C でループ
for idx, sh_C in enumerate(superheat_values_C):
    # superheat_C でフィルタリング
    df_sub = results_df[results_df["superheat_C"] == sh_C]
    if df_sub.empty:
        continue
    # Vdot_m3h ではなく sh_C でラベル付け
    ax2.plot(df_sub["T_htf_in [°C]"], df_sub["W_net [kW]"],
              marker=markers[idx % len(markers)], color=cmap(idx / (len(superheat_values_C) - 1)), label=f"過熱度={sh_C} °C")
    ax2.set_ylabel("正味出力 W_net [kW]")
    ax2.grid(True)
    ax2.legend(title="ORC過熱度") # 凡例追加

# New plot for turbine inlet pressure (P_evap)
ax3 = axes[2]
# Vdot_values_m3h ではなく superheat_values_C でループ
for idx, sh_C in enumerate(superheat_values_C):
    # superheat_C でフィルタリング
    df_sub = results_df[results_df["superheat_C"] == sh_C]
    if df_sub.empty:
        continue
    # Vdot_m3h ではなく sh_C でラベル付け
    ax3.plot(df_sub["T_htf_in [°C]"], df_sub["P_evap [bar]"],
              marker=markers[idx % len(markers)], color=cmap(idx / (len(superheat_values_C) - 1)), label=f"過熱度={sh_C} °C")
    ax3.set_ylabel("タービン入口圧力 P_evap [bar]") # 修正: "内" -> "入口"
    ax3.grid(True)
    ax3.legend(title="ORC過熱度") # 凡例タイトル変更

# New plot for exergy efficiency (eps_e)
ax4 = axes[3]
# Vdot_values_m3h ではなく superheat_values_C でループ
for idx, sh_C in enumerate(superheat_values_C):
    # superheat_C でフィルタリング
    df_sub = results_df[results_df["superheat_C"] == sh_C]
    if df_sub.empty:
        continue
    # Vdot_m3h ではなく sh_C でラベル付け
    ax4.plot(df_sub["T_htf_in [°C]"], df_sub["ε_ex [-]"],
              marker=markers[idx % len(markers)], color=cmap(idx / (len(superheat_values_C) - 1)), label=f"過熱度={sh_C} °C")
    ax4.set_ylabel("ORCエクセルギー効率 ε [-]")
    ax4.grid(True)
    ax4.legend(title="ORC過熱度") # 凡例タイトル変更

# New plot for heat source exergy efficiency (eps_ex_hs)
# fig.add_subplotではなく、axes[4]を使用するように変更
ax5 = axes[4]
for idx, sh_C in enumerate(superheat_values_C):
    df_sub = results_df[results_df["superheat_C"] == sh_C]
    if df_sub.empty:
        continue
    ax5.plot(df_sub["T_htf_in [°C]"], df_sub["eps_ex_hs [-]"],
              marker=markers[idx % len(markers)], color=cmap(idx / (len(superheat_values_C) - 1)), label=f"過熱度={sh_C} °C")
    ax5.set_xlabel("熱源入口温度 [°C]")
    ax5.set_ylabel("熱源エクセルギー効率 [-]")
    ax5.grid(True)
    ax5.legend(title="ORC過熱度")

# X軸ラベルは最後のプロットにのみ表示（他は削除）
for ax in axes[:-1]:
    ax.set_xlabel("")

plt.tight_layout()
filename = f"orc_performance_vs_HTF_vary_superheat_{fluid_orc}.png"
plt.savefig(filename, dpi=300)
print(f"プロットを {filename} に保存しました。")

csv_filename = filename.replace('.png', '.csv')
results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
print(f"計算結果を {csv_filename} に保存しました。")
