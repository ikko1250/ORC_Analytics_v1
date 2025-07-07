import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm # カラーマップ用
import CoolProp.CoolProp as CP # CoolPropライブラリをインポート（飽和圧力計算用）

# 解析用関数をインポート (ene_anal.py ファイルが必要です)
from ORC_analysis.archive.ene_anal import calculate_orc_performance, DEFAULT_FLUID, DEFAULT_T0

# 日本語フォント設定 (環境に合わせて調整が必要な場合があります)
try:
    # 使用可能な日本語フォントの例: 'MS Gothic', 'Meiryo', 'TakaoGothic', 'IPAexGothic'
    # システムにインストールされているフォント名を確認してください
    plt.rcParams['font.family'] = 'M+ 1c' # M+ 1c に固定
    plt.rcParams['axes.unicode_minus'] = False # マイナス記号の文字化け対策
    print(f"日本語フォント '{plt.rcParams['font.family']}' を設定しました。")
except Exception as e:
    print(f"日本語フォントの設定に失敗しました: {e}")
    print("英語のラベルを使用します。日本語を表示するには、適切なフォントをインストール・設定してください。")
    # フォント設定をデフォルトに戻すか、英語フォントを指定
    plt.rcParams['font.family'] = 'sans-serif'


# --------------------------------------------------
# 1. 計算条件の設定
# --------------------------------------------------
# --- 固定パラメータ ---
T_cond = 305.0                   # 凝縮温度 [K] (例: 32 °C に変更)
eta_pump = 0.75                  # ポンプ効率 [-]
eta_turb = 0.80                  # タービン効率 [-]
fluid = DEFAULT_FLUID            # 作動流体 (ene_analからインポート)
m_orc = 5.0                      # 質量流量 [kg/s]
T0 = DEFAULT_T0                  # 環境温度 [K] (ene_analからインポート)

# --- 可変パラメータの範囲 ---
# タービン入口温度を摂氏で指定
T_turb_in_values_C = np.linspace(70, 140, 100) # タービン入口温度 [℃]
T_turb_in_values_K = T_turb_in_values_C + 273.15 # ケルビンに変換

# 過熱度 [℃]
superheat_C = 10.0

# --------------------------------------------------
# 2. パラメータスイープ計算の実行
# --------------------------------------------------
results_list = []

print(f"Calculating ORC performance with variable evaporation pressure (Superheat = {superheat_C}°C)...")
total_iterations = len(T_turb_in_values_K)
completed_iterations = 0

for t_turb_in_K in T_turb_in_values_K:
    completed_iterations += 1
    t_turb_in_C = t_turb_in_K - 273.15

    # タービン入口温度から、飽和温度を計算 (過熱度を考慮)
    T_sat_evap_K = t_turb_in_K - superheat_C

    # 飽和温度における作動流体の飽和圧力を計算し、蒸発圧力とする
    try:
        # CoolPropはSI単位系 (K, Pa) を使用
        # T_sat_evap_K が作動流体の有効範囲内か確認が必要な場合がある
        p_evap_pa = CP.PropsSI('P', 'T', T_sat_evap_K, 'Q', 0, fluid) # 飽和液点での圧力 (=飽和蒸気圧)
        p_evap_bar = p_evap_pa / 1e5
    except Exception as e:
        # print(f"\nWarning: Could not calculate saturation pressure for T_sat_evap={T_sat_evap_K:.2f} K ({T_sat_evap_K-273.15:.2f} °C) for fluid {fluid}: {e}")
        # 飽和圧力計算に失敗した場合は、この点の計算をスキップまたは NaN を記録
        results_list.append({
             "T_turb_in [K]": t_turb_in_K,
             "T_turb_in [°C]": t_turb_in_C,
             "P_evap [bar]": np.nan, # 圧力計算失敗を示す
             "W_net [kW]": np.nan,
             "η_th [-]": np.nan,
             "ε_ex [-]": np.nan
         })
        print(f"  Calculating: {completed_iterations}/{total_iterations} (T_turb_in={t_turb_in_C:.1f} °C, P_evap=N/A)", end='\r')
        continue # 次の温度へスキップ


    # 進捗表示
    print(f"  Calculating: {completed_iterations}/{total_iterations} (T_turb_in={t_turb_in_C:.1f} °C, P_evap={p_evap_bar:.2f} bar)", end='\r')

    # ORC性能計算関数を呼び出し
    psi_df, component_df, cycle_performance = calculate_orc_performance(
        P_evap=p_evap_pa, # 計算した蒸発圧力をPaで渡す
        T_turb_in=t_turb_in_K,
        T_cond=T_cond, # 更新されたT_condを使用
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        fluid=fluid,
        m_orc=m_orc,
        T0=T0
    )

    if cycle_performance is not None: # 計算が成功した場合のみ結果を格納
        results_list.append({
            "T_turb_in [K]": t_turb_in_K,
            "T_turb_in [°C]": t_turb_in_C,
            "P_evap [bar]": p_evap_bar,
            "W_net [kW]": cycle_performance.get("W_net [kW]", np.nan),
            "η_th [-]": cycle_performance.get("η_th [-]", np.nan),
            "ε_ex [-]": cycle_performance.get("ε_ex [-]", np.nan)
        })
    else: # 計算が失敗した場合
         results_list.append({
             "T_turb_in [K]": t_turb_in_K,
             "T_turb_in [°C]": t_turb_in_C,
             "P_evap [bar]": p_evap_bar,
             "W_net [kW]": np.nan,
             "η_th [-]": np.nan,
             "ε_ex [-]": np.nan
         })

print("\nCalculation complete.")

# 結果をDataFrameに変換
results_df = pd.DataFrame(results_list)

# NaN値を含む行を削除 (計算が失敗した点をプロットから除外するため)
results_df_cleaned = results_df.dropna(subset=["T_turb_in [°C]", "P_evap [bar]", "W_net [kW]", "η_th [-]", "ε_ex [-]"]).copy()


# --------------------------------------------------
# 3. 結果のプロット
# --------------------------------------------------
print("Plotting results...")
# 3つのサブプロットを作成 (2行1列から3行1列に変更)
fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=True) # 図のサイズを調整

# --- 熱効率のプロット (η_th) ---
ax1 = axes[0]
# タービン入口温度は摂氏を使用
ax1.plot(results_df_cleaned["T_turb_in [°C]"], results_df_cleaned["η_th [-]"], 'o-',
         color='blue', markersize=4) # 単一の色とスタイル

ax1.set_ylabel("熱効率 η_th [-]")
# タイトルに作動流体名と過熱度条件を含める
ax1.set_title(f"ORC性能 ({fluid}, T_cond={T_cond}K, η_pump={eta_pump}, η_turb={eta_turb}, 過熱度={superheat_C}°C)")
# ax1.legend(title="蒸発圧力", loc='best') # 凡例は不要
ax1.grid(True)

# --- エクセルギー効率のプロット (ε_ex) ---
ax2 = axes[1]
# タービン入口温度は摂氏を使用
ax2.plot(results_df_cleaned["T_turb_in [°C]"], results_df_cleaned["ε_ex [-]"], 's--',
         color='red', markersize=4) # 単一の色とスタイル

ax2.set_ylabel("エクセルギー効率 ε_ex [-]")
# ax2.legend(title="蒸発圧力", loc='best') # 凡例は不要
ax2.grid(True)

# --- 蒸発圧力のプロット (P_evap) ---
ax3 = axes[2]
# タービン入口温度は摂氏を使用, 圧力はbarを使用
ax3.plot(results_df_cleaned["T_turb_in [°C]"], results_df_cleaned["P_evap [bar]"], '^-',
         color='green', markersize=4) # 単一の色とスタイル

ax3.set_xlabel("タービン入口温度 T_turb_in [°C]") # ラベルを摂氏に変更
ax3.set_ylabel("蒸発圧力 P_evap [bar]")
ax3.grid(True)


plt.tight_layout()
# plt.show() # 画面表示の代わりにファイルに保存
plt.savefig("orc_performance_variable_pressure_plot.png", dpi=300) # ファイル名と解像度を指定して保存

print("Plot saved to orc_performance_variable_pressure_plot.png")

# --- (オプション) 結果の表示 ---
# print("\nResults DataFrame:")
# pd.set_option('display.max_rows', None)
# print(results_df)
