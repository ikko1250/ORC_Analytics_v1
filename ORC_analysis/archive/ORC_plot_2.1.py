import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm # カラーマップ用
import CoolProp.CoolProp as CP # CoolPropライブラリをインポート（飽和圧力計算用）

# 解析用関数をインポート (ene_anal.py ファイルが必要です)
try:
    # ene_anal.py から実際の関数と定数をインポート
    from ORC_analysis.archive.ene_anal import calculate_orc_performance, DEFAULT_FLUID, DEFAULT_T0
    print("ene_anal.py から calculate_orc_performance をインポートしました。")
except ImportError:
    print("エラー: ene_anal.py が見つからないか、必要な関数/定数が定義されていません。")
    print("スクリプトを続行できません。ene_anal.py を同じディレクトリに配置してください。")
    # エラーが発生した場合、ここで処理を中断するか、代替処理を行う
    # 例: exit()
    # --- フォールバック用のダミー定義 (もし ene_anal がない場合に実行したい場合) ---
    # print("警告: ene_anal.py が見つかりません。ダミー関数を使用します。")
    # DEFAULT_FLUID = 'R245fa'
    # DEFAULT_T0 = 298.15
    # def calculate_orc_performance(P_evap, T_turb_in, T_cond, eta_pump, eta_turb, fluid, m_orc, T0, P0=101.325e3):
    #     print("  (Dummy Calculation - ene_anal.py not found)")
    #     # ここに最小限のダミーロジックを記述 (上記ダミー実装を参照)
    #     return None, None, None # ダミーは失敗を返す
    exit() # ene_anal.py が必須のため終了

# 日本語フォント設定 (環境に合わせて調整が必要な場合があります)
try:
    # 使用可能な日本語フォントの例: 'MS Gothic', 'Meiryo', 'TakaoGothic', 'IPAexGothic'
    # システムにインストールされているフォント名を確認してください
    # plt.rcParams['font.family'] = 'M+ 1c' # M+ 1c に固定 (環境にない場合エラーになる可能性)
    plt.rcParams['font.family'] = 'sans-serif' # デフォルトのサンセリフを使用
    plt.rcParams['axes.unicode_minus'] = False # マイナス記号の文字化け対策
    print(f"フォント '{plt.rcParams['font.family']}' を設定しました。") # 日本語フォント -> フォント
except Exception as e:
    print(f"フォントの設定に失敗しました: {e}") # 日本語フォント -> フォント
    print("デフォルトのフォントを使用します。")
    # フォント設定をデフォルトに戻すか、英語フォントを指定
    plt.rcParams['font.family'] = 'sans-serif'


# --------------------------------------------------
# 1. 計算条件の設定
# --------------------------------------------------
# --- 固定パラメータ ---
T_cond = 305.0                  # 凝縮温度 [K] (例: 32 °C)
eta_pump = 0.75                 # ポンプ効率 [-]
eta_turb = 0.80                 # タービン効率 [-]
fluid = DEFAULT_FLUID           # 作動流体 (ene_analからインポート)
m_orc = 5.0                     # 質量流量 [kg/s]
T0 = DEFAULT_T0                 # 環境温度 [K] (ene_analからインポート)
# P0 = DEFAULT_P0               # 環境圧力 [Pa] (ene_analで定義されているものを使用)

# --- 可変パラメータの範囲 ---
# タービン入口温度を摂氏で指定
T_turb_in_values_C = np.linspace(70, 140, 50) # 点数を減らして計算時間を短縮 (元は100)
T_turb_in_values_K = T_turb_in_values_C + 273.15 # ケルビンに変換

# 過熱度 [℃]
superheat_C = 10.0
superheat_K = superheat_C # ケルビンでの差は同じ

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
    T_sat_evap_K = t_turb_in_K - superheat_K

    # 飽和温度における作動流体の飽和圧力を計算し、蒸発圧力とする
    p_evap_pa = np.nan # 初期化
    p_evap_bar = np.nan # 初期化
    try:
        # CoolPropはSI単位系 (K, Pa) を使用
        # T_sat_evap_K が作動流体の有効範囲内か確認
        T_crit = CP.PropsSI('Tcrit', fluid)
        T_triple = CP.PropsSI('Ttriple', fluid)
        if not (T_triple < T_sat_evap_K < T_crit):
             # print(f"\nWarning: T_sat_evap={T_sat_evap_K:.2f} K is outside the valid range ({T_triple:.2f} K - {T_crit:.2f} K) for fluid {fluid}.")
             raise ValueError("Saturation temperature out of range") # エラーとして扱う

        p_evap_pa = CP.PropsSI('P', 'T', T_sat_evap_K, 'Q', 0, fluid) # 飽和液点での圧力 (=飽和蒸気圧)
        p_evap_bar = p_evap_pa / 1e5

        # 同様に凝縮圧力も計算し、蒸発圧力が凝縮圧力より高いか確認
        P_cond_pa = CP.PropsSI('P', 'T', T_cond, 'Q', 0, fluid)
        if p_evap_pa <= P_cond_pa:
             # print(f"\nWarning: Calculated P_evap ({p_evap_bar:.2f} bar) is not greater than P_cond ({P_cond_pa/1e5:.2f} bar).")
             raise ValueError("Evaporation pressure not higher than condensation pressure")

    except Exception as e:
        # print(f"\nWarning: Could not calculate saturation pressure or pressure check failed for T_sat_evap={T_sat_evap_K:.2f} K ({T_sat_evap_K-273.15:.2f} °C) for fluid {fluid}: {e}")
        # 飽和圧力計算に失敗した場合は、この点の計算をスキップまたは NaN を記録
        results_list.append({
                "T_turb_in [K]": t_turb_in_K,
                "T_turb_in [°C]": t_turb_in_C,
                "P_evap [bar]": np.nan, # 圧力計算失敗を示す
                "W_net [kW]": np.nan,
                "η_th [-]": np.nan,
                "ε_ex [-]": np.nan
            })
        print(f" Calculating: {completed_iterations}/{total_iterations} (T_turb_in={t_turb_in_C:.1f} °C, P_evap=N/A - Error)", end='\r')
        continue # 次の温度へスキップ


    # 進捗表示
    print(f" Calculating: {completed_iterations}/{total_iterations} (T_turb_in={t_turb_in_C:.1f} °C, P_evap={p_evap_bar:.2f} bar)", end='\r')

    # ORC性能計算関数を呼び出し (ene_anal.py からインポートしたものを使用)
    # calculate_orc_performance は P0 も引数に取るが、デフォルト値が設定されているため省略可能
    psi_df, component_df, cycle_performance = calculate_orc_performance(
        P_evap=p_evap_pa, # 計算した蒸発圧力をPaで渡す
        T_turb_in=t_turb_in_K,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        fluid=fluid,
        m_orc=m_orc,
        T0=T0
        # P0=P0 # 必要であれば指定
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
    else: # 計算が失敗した場合 (calculate_orc_performance が None を返した場合)
         results_list.append({
            "T_turb_in [K]": t_turb_in_K,
            "T_turb_in [°C]": t_turb_in_C,
            "P_evap [bar]": p_evap_bar, # 圧力は計算できたかもしれない
            "W_net [kW]": np.nan,
            "η_th [-]": np.nan,
            "ε_ex [-]": np.nan
         })
         # 計算失敗時のメッセージは calculate_orc_performance 内で出力される想定
         # print(f" Calculating: {completed_iterations}/{total_iterations} (T_turb_in={t_turb_in_C:.1f} °C, P_evap={p_evap_bar:.2f} bar - Calc Failed)", end='\r')


print("\nCalculation complete.                                          ") # 進捗表示をクリア

# 結果をDataFrameに変換
results_df = pd.DataFrame(results_list)

# NaN値を含む行を削除 (計算が失敗した点をプロットから除外するため)
results_df_cleaned = results_df.dropna(subset=["T_turb_in [°C]", "P_evap [bar]", "W_net [kW]", "η_th [-]", "ε_ex [-]"]).copy()

# 結果がない場合の処理
if results_df_cleaned.empty:
    print("有効な計算結果が得られませんでした。プロットをスキップします。")
    print("\n--- 計算結果 (生データ) ---")
    print(results_df)
else:
    # --------------------------------------------------
    # 3. 結果のプロット
    # --------------------------------------------------
    print("Plotting results...")
    # 3つのサブプロットを作成 (3行1列)
    fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=True) # 図のサイズを調整

    # --- 熱効率のプロット (η_th) ---
    ax1 = axes[0]
    # タービン入口温度は摂氏を使用
    ax1.plot(results_df_cleaned["T_turb_in [°C]"], results_df_cleaned["η_th [-]"] * 100, 'o-', # %表示に変更
             color='blue', markersize=4, label='Thermal Efficiency') # ラベル追加

    ax1.set_ylabel("Thermal Efficiency η_th [%]") # ラベル変更
    # タイトルに作動流体名と過熱度条件を含める
    title_text = (f"ORC Performance vs. Turbine Inlet Temp.\n"
                  f"(Fluid: {fluid}, T_cond={T_cond-273.15:.1f}°C, Superheat={superheat_C}°C, "
                  f"η_pump={eta_pump:.2f}, η_turb={eta_turb:.2f}, m_orc={m_orc} kg/s)")
    ax1.set_title(title_text)
    ax1.grid(True)
    # ax1.legend() # 凡例は不要かも

    # --- エクセルギー効率のプロット (ε_ex) ---
    ax2 = axes[1]
    # タービン入口温度は摂氏を使用
    ax2.plot(results_df_cleaned["T_turb_in [°C]"], results_df_cleaned["ε_ex [-]"] * 100, 's--', # %表示に変更
             color='red', markersize=4, label='Exergy Efficiency') # ラベル追加

    ax2.set_ylabel("Exergy Efficiency ε_ex [%]") # ラベル変更
    ax2.grid(True)
    # ax2.legend() # 凡例は不要かも

    # --- 蒸発圧力のプロット (P_evap) ---
    ax3 = axes[2]
    # タービン入口温度は摂氏を使用, 圧力はbarを使用
    ax3.plot(results_df_cleaned["T_turb_in [°C]"], results_df_cleaned["P_evap [bar]"], '^-',
             color='green', markersize=4, label='Evaporation Pressure') # ラベル追加

    ax3.set_xlabel("Turbine Inlet Temperature T_turb_in [°C]") # 英語に変更 (フォント問題回避のため)
    ax3.set_ylabel("Evaporation Pressure P_evap [bar]")
    ax3.grid(True)
    # ax3.legend() # 凡例は不要かも

    plt.tight_layout(rect=[0, 0.03, 1, 0.97]) # タイトルスペースを考慮
    # plt.show() # 画面表示の代わりにファイルに保存
    plot_filename = f"orc_performance_{fluid}_SH{superheat_C}C.png"
    plt.savefig(plot_filename, dpi=300) # ファイル名と解像度を指定して保存

    print(f"Plot saved to {plot_filename}")

    # --- (オプション) 結果の表示 ---
    print("\n--- Calculation Summary ---")
    print(f"Fluid: {fluid}")
    print(f"Condensation Temperature: {T_cond-273.15:.1f} °C")
    print(f"Superheat: {superheat_C} °C")
    print(f"Pump Efficiency: {eta_pump:.2f}")
    print(f"Turbine Efficiency: {eta_turb:.2f}")
    print(f"Mass Flow Rate: {m_orc} kg/s")
    print(f"Ambient Temperature (T0): {T0-273.15:.1f} °C")
    print("-" * 30)
    print(f"Turbine Inlet Temp Range: {results_df_cleaned['T_turb_in [°C]'].min():.1f} - {results_df_cleaned['T_turb_in [°C]'].max():.1f} °C")
    print(f"Evaporation Pressure Range: {results_df_cleaned['P_evap [bar]'].min():.2f} - {results_df_cleaned['P_evap [bar]'].max():.2f} bar")
    try:
        max_eff_th_row = results_df_cleaned.loc[results_df_cleaned['η_th [-]'].idxmax()]
        print(f"Max Thermal Efficiency: {max_eff_th_row['η_th [-]']*100:.2f}% at T_turb_in = {max_eff_th_row['T_turb_in [°C]']:.1f}°C")
    except ValueError:
        print("Could not determine max thermal efficiency (no valid results).")
    try:
        max_eff_ex_row = results_df_cleaned.loc[results_df_cleaned['ε_ex [-]'].idxmax()]
        print(f"Max Exergy Efficiency: {max_eff_ex_row['ε_ex [-]']*100:.2f}% at T_turb_in = {max_eff_ex_row['T_turb_in [°C]']:.1f}°C")
    except ValueError:
        print("Could not determine max exergy efficiency (no valid results).")
    try:
        max_wnet_row = results_df_cleaned.loc[results_df_cleaned['W_net [kW]'].idxmax()]
        print(f"Max Net Power Output: {max_wnet_row['W_net [kW]']:.1f} kW at T_turb_in = {max_wnet_row['T_turb_in [°C]']:.1f}°C")
    except ValueError:
        print("Could not determine max net power output (no valid results).")

