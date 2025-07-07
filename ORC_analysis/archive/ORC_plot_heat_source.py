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

superheat_C = 12.0  # ORC過熱度
pinch_delta_K = 10.0

# --------------------------------------------------
# 2. 計算
# --------------------------------------------------
results = []
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
print("Simulation finished.")

if not results:
    raise RuntimeError("有効な計算結果が得られませんでした。熱源温度範囲を上げるか、設定を確認してください。")

results_df = pd.DataFrame(results)

# --------------------------------------------------
# 3. プロット
# --------------------------------------------------
plt.rcParams["font.family"] = "M+ 1c"
plt.rcParams["axes.unicode_minus"] = False

fig, axes = plt.subplots(4, 1, figsize=(10, 20), sharex=True)

cmap = cm.get_cmap("viridis", len(Vdot_values_m3h))
markers = ["o", "s", "^", "D", "x", "*", "<", ">", "p", "h"]

# Thermal efficiency plot
ax1 = axes[0]
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    ax1.plot(df_sub["T_htf_in [°C]"], df_sub["η_th [-]"] * 100,
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    ax1.set_ylabel("熱効率 η_th [%]")
    ax1.grid(True)
    ax1.legend(title="熱源流量")

# Net power plot
ax2 = axes[1]
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    ax2.plot(df_sub["T_htf_in [°C]"], df_sub["W_net [kW]"],
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    ax2.set_xlabel("熱源入口温度 [°C]")
    ax2.set_ylabel("正味出力 W_net [kW]")
    ax2.grid(True)

# New plot for turbine inlet pressure (P_evap)
ax3 = axes[2]
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    ax3.plot(df_sub["T_htf_in [°C]"], df_sub["P_evap [bar]"],
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    ax3.set_xlabel("熱源入口温度 [°C]")
    ax3.set_ylabel("タービン内圧力 P_evap [bar]")
    ax3.grid(True)
    ax3.legend(title="熱源流量")

# New plot for exergy efficiency (eps_e)
ax4 = axes[3]
for idx, Vdot_m3h in enumerate(Vdot_values_m3h):
    df_sub = results_df[results_df["Vdot_htf [m3/s]"].round(6) == (Vdot_m3h / 3600.0).round(6)]
    if df_sub.empty:
        continue
    ax4.plot(df_sub["T_htf_in [°C]"], df_sub["ε_ex [-]"],
              marker=markers[idx % len(markers)], color=cmap(idx), label=f"Vdot={Vdot_m3h} m³/h")
    ax4.set_xlabel("熱源入口温度 [°C]")
    ax4.set_ylabel("エクセルギー効率 ε [-]")
    ax4.grid(True)
    ax4.legend(title="熱源流量")

plt.tight_layout()
filename = f"orc_performance_vs_HTF_{fluid_orc}.png"
plt.savefig(filename, dpi=300)
print(f"プロットを {filename} に保存しました。")

# 計算結果をCSVファイルに出力
csv_filename = filename.replace('.png', '.csv')
results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
print(f"計算結果を {csv_filename} に保存しました。") 