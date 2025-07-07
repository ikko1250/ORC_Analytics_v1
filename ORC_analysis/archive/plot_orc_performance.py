import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm # カラーマップ用

# 解析用関数をインポート
from ORC_analysis.archive.ene_anal import calculate_orc_performance, DEFAULT_FLUID, DEFAULT_T0

# 日本語フォント設定 (環境に合わせて調整が必要な場合があります)
try:
    plt.rcParams['font.family'] = 'M+ 1c' # または 'MS Gothic' など
    plt.rcParams['axes.unicode_minus'] = False # マイナス記号の文字化け対策
except Exception as e:
    print(f"日本語フォントの設定に失敗しました: {e}")
    print("英語のラベルを使用します。日本語を表示するには、適切なフォントをインストール・設定してください。")

# --------------------------------------------------
# 1. 計算条件の設定
# --------------------------------------------------
# --- 固定パラメータ ---
T_cond = 308.0                   # 凝縮温度 [K] (例: 35 °C)
eta_pump = 0.75                  # ポンプ効率 [-]
eta_turb = 0.80                  # タービン効率 [-]
fluid = DEFAULT_FLUID            # 作動流体 (ene_analからインポート)
m_orc = 5.0                      # 質量流量 [kg/s]
T0 = DEFAULT_T0                  # 環境温度 [K] (ene_analからインポート)

# --- 可変パラメータの範囲 --- 
P_evap_values_bar = np.linspace(5, 12, 6) # 蒸発圧力 [bar] (25, 33.3, 41.7, 50 bar)
# P_evap_values_bar = np.array([12]) # 蒸発圧力 [bar] (25 bar に固定)
P_evap_values_pa = P_evap_values_bar * 1e5   # Paに変換
# タービン入口温度を摂氏で指定
T_turb_in_values_C = np.linspace(70, 140, 100) # タービン入口温度 [℃] 
T_turb_in_values_K = T_turb_in_values_C + 273.15 # ケルビンに変換

# --------------------------------------------------
# 2. パラメータスイープ計算の実行
# --------------------------------------------------
results_list = []

print("Calculating ORC performance for parameter sweep...")
for p_evap in P_evap_values_pa:
    for t_turb_in in T_turb_in_values_K:
        print(f"  P_evap={p_evap/1e5:.1f} bar, T_turb_in={t_turb_in:.1f} K", end='\r') # 進捗表示
        psi_df, component_df, cycle_performance = calculate_orc_performance(
            P_evap=p_evap,
            T_turb_in=t_turb_in,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid=fluid,
            m_orc=m_orc,
            T0=T0
        )

        if cycle_performance is not None: # 計算が成功した場合のみ結果を格納
            results_list.append({
                "P_evap [bar]": p_evap / 1e5,
                "T_turb_in [K]": t_turb_in,
                "W_net [kW]": cycle_performance.get("W_net [kW]", np.nan),
                "η_th [-]": cycle_performance.get("η_th [-]", np.nan),
                "ε_ex [-]": cycle_performance.get("ε_ex [-]", np.nan)
            })
        else:
             results_list.append({
                "P_evap [bar]": p_evap / 1e5,
                "T_turb_in [K]": t_turb_in,
                "W_net [kW]": np.nan,
                "η_th [-]": np.nan,
                "ε_ex [-]": np.nan
            })

print("\nCalculation complete.")

# 結果をDataFrameに変換
results_df = pd.DataFrame(results_list)

# --- 結果をCSVファイルに保存 ---
csv_filename = "orc_performance_results.csv"
results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig') # インデックスなし、UTF-8(BOM付き)で保存
print(f"Results saved to {csv_filename}")

# --------------------------------------------------
# 3. 結果のプロット
# --------------------------------------------------
print("Plotting results...")
fig, axes = plt.subplots(2, 1, figsize=(8, 10), sharex=True)

colors = cm.viridis(np.linspace(0, 1, len(P_evap_values_bar)))

# --- 熱効率のプロット (η_th) ---
ax1 = axes[0]
for i, p_evap_bar in enumerate(P_evap_values_bar):
    subset = results_df[results_df["P_evap [bar]"] == p_evap_bar]
    ax1.plot(subset["T_turb_in [K]"] - 273.15, subset["η_th [-]"], 'o-',
             label=f"{p_evap_bar:.0f} bar", color=colors[i])

ax1.set_ylabel("熱効率 η_th [-]")
ax1.set_title(f"ORC性能 ({fluid}, P_evap={P_evap_values_bar[0]:.0f} bar, T_cond={T_cond}K, η_pump={eta_pump}, η_turb={eta_turb})")
ax1.legend(title="蒸発圧力", loc='best')
ax1.grid(True)

# --- エクセルギー効率のプロット (ε_ex) ---
ax2 = axes[1]
for i, p_evap_bar in enumerate(P_evap_values_bar):
    subset = results_df[results_df["P_evap [bar]"] == p_evap_bar]
    ax2.plot(subset["T_turb_in [K]"] - 273.15, subset["ε_ex [-]"], 's--',
             label=f"{p_evap_bar:.0f} bar", color=colors[i])

ax2.set_xlabel("タービン入口温度 T_turb_in [K]")
ax2.set_ylabel("エクセルギー効率 ε_ex [-]")
# ax2.legend(title="蒸発圧力", loc='best') # 凡例は上と共通なので不要ならコメントアウト
ax2.grid(True)

plt.tight_layout()
# plt.show() # 画面表示の代わりにファイルに保存
plt.savefig("orc_performance_plot.png", dpi=300) # ファイル名と解像度を指定して保存

print("Plot saved to orc_performance_plot.png")

# --- (オプション) 結果の表示 ---
# print("\nResults DataFrame:")
# pd.set_option('display.max_rows', None)
# print(results_df) 