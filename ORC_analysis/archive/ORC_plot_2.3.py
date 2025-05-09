import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm # カラーマップ用
import CoolProp.CoolProp as CP # CoolPropライブラリをインポート
import os # ファイルパス操作用

# 解析用関数をインポート (ene_anal.py ファイルが必要です)
try:
    # ene_anal.py から実際の関数と定数をインポート
    from ORC_analysis.archive.ene_anal import calculate_orc_performance, DEFAULT_FLUID, DEFAULT_T0
    print("ene_anal.py から calculate_orc_performance をインポートしました。")
except ImportError:
    print("エラー: ene_anal.py が見つからないか、必要な関数/定数が定義されていません。")
    print("スクリプトを続行できません。ene_anal.py を同じディレクトリに配置してください。")
    exit() # ene_anal.py が必須のため終了

# 日本語フォント設定 (環境に合わせて調整が必要な場合があります)
try:
    plt.rcParams['font.family'] = 'M+ 1c' # デフォルトのサンセリフを使用
    # 日本語対応フォントが利用可能な場合は 'IPAexGothic' などに変更してください
    # 例: plt.rcParams['font.family'] = 'IPAexGothic'
    plt.rcParams['axes.unicode_minus'] = False # マイナス記号の文字化け対策
    print(f"フォント '{plt.rcParams['font.family']}' を設定しました。日本語表示が必要な場合は適切なフォントに変更してください。")
except Exception as e:
    print(f"フォントの設定に失敗しました: {e}")
    print("デフォルトのフォントを使用します。")
    plt.rcParams['font.family'] = 'sans-serif'

# --------------------------------------------------
# 計算とプロットを実行する関数
# --------------------------------------------------
def run_orc_analysis_and_plot(max_P_evap_bar, T_cond, eta_pump, eta_turb, fluid, T0, superheat_C, m_orc_values):
    """
    指定された蒸発圧力上限でORC性能解析を行い、結果をプロットする関数。

    Args:
        max_P_evap_bar (float): 蒸発圧力の上限 [bar]
        T_cond (float): 凝縮温度 [K]
        eta_pump (float): ポンプ効率 [-]
        eta_turb (float): タービン効率 [-]
        fluid (str): 作動流体
        T0 (float): 環境温度 [K]
        superheat_C (float): 過熱度 [°C]
        m_orc_values (np.array): 質量流量の範囲 [kg/s]
    """
    print(f"\n--- 解析開始: 蒸発圧力上限 = {max_P_evap_bar} bar ---")
    superheat_K = superheat_C

    # --- 可変パラメータの範囲 ---
    # 蒸発圧力の範囲を設定 [Pa]
    try:
        P_cond_pa = CP.PropsSI('P', 'T', T_cond, 'Q', 0, fluid)
        P_cond_bar = P_cond_pa / 1e5
        print(f"  凝縮圧力 P_cond = {P_cond_bar:.2f} bar")

        # 蒸発圧力の最小値は凝縮圧力より少し高く設定
        P_evap_min_pa = P_cond_pa * 1.1
        # 蒸発圧力の最大値は指定された上限値 [Pa]
        P_evap_max_pa = max_P_evap_bar * 1e5

        # 臨界圧力をチェック (上限が臨界を超えていないか)
        P_crit_pa = CP.PropsSI('Pcrit', fluid)
        if P_evap_max_pa >= P_crit_pa:
             print(f"  警告: 指定された蒸発圧力上限 ({max_P_evap_bar} bar) が臨界圧力 ({P_crit_pa/1e5:.2f} bar) 以上です。")
             # 上限を臨界圧力の少し手前に制限するなどの処理も可能
             # P_evap_max_pa = P_crit_pa * 0.98 # 例

        # 最小圧力が最大圧力を超えていないかチェック
        if P_evap_min_pa >= P_evap_max_pa:
            print(f"  エラー: 計算された最小蒸発圧力 ({P_evap_min_pa/1e5:.2f} bar) が指定された最大蒸発圧力 ({max_P_evap_bar} bar) 以上です。")
            print(f"  凝縮温度や上限圧力を見直してください。")
            return # この上限での処理を中断

        P_evap_values_pa = np.linspace(P_evap_min_pa, P_evap_max_pa, 50) # 線形スケール (50点)
        P_evap_values_bar = P_evap_values_pa / 1e5 # bar 単位も用意
        print(f"  蒸発圧力範囲 (計算用): {P_evap_values_bar.min():.2f} bar から {P_evap_values_bar.max():.2f} bar まで")

    except Exception as e:
        print(f"  エラー: 圧力範囲の設定に失敗しました: {e}")
        return # この上限での処理を中断

    # --- パラメータスイープ計算の実行 ---
    results_list = []
    print(f"  蒸発圧力と質量流量を変化させてORC性能を計算中 (過熱度 = {superheat_C}°C)...")
    total_iterations = len(P_evap_values_pa) * len(m_orc_values)
    completed_iterations = 0

    for p_evap_pa in P_evap_values_pa:
        p_evap_bar = p_evap_pa / 1e5
        t_turb_in_K = np.nan
        t_turb_in_C = np.nan
        try:
            T_sat_evap_K = CP.PropsSI('T', 'P', p_evap_pa, 'Q', 1, fluid)
            t_turb_in_K = T_sat_evap_K + superheat_K
            t_turb_in_C = t_turb_in_K - 273.15
            T_crit = CP.PropsSI('Tcrit', fluid)
            if t_turb_in_K >= T_crit:
                 raise ValueError(f"計算されたT_turb_in ({t_turb_in_K:.1f} K) が臨界温度 ({T_crit:.1f} K) 以上")
        except Exception as e:
            for m_orc in m_orc_values:
                 completed_iterations += 1
                 results_list.append({ "P_evap [bar]": p_evap_bar, "T_turb_in [K]": np.nan, "T_turb_in [°C]": np.nan, "Q_in [kW]": np.nan, "W_net [kW]": np.nan, "η_th [-]": np.nan, "ε_ex [-]": np.nan, "m_orc [kg/s]": m_orc })
            print(f"   計算中: {completed_iterations}/{total_iterations} (P_evap={p_evap_bar:.2f} bar - T_turb_in 計算エラー: {e})", end='\r')
            continue

        for m_orc in m_orc_values:
            completed_iterations += 1
            print(f"   計算中: {completed_iterations}/{total_iterations} (P_evap={p_evap_bar:.2f} bar, T_turb_in={t_turb_in_C:.1f} °C, m_orc={m_orc:.1f} kg/s)", end='\r')
            try:
                psi_df, component_df, cycle_performance = calculate_orc_performance( P_evap=p_evap_pa, T_turb_in=t_turb_in_K, T_cond=T_cond, eta_pump=eta_pump, eta_turb=eta_turb, fluid=fluid, m_orc=m_orc, T0=T0 )
                if cycle_performance is not None:
                    results_list.append({ "P_evap [bar]": p_evap_bar, "T_turb_in [K]": t_turb_in_K, "T_turb_in [°C]": t_turb_in_C, "Q_in [kW]": cycle_performance.get("Q_in [kW]", np.nan), "W_net [kW]": cycle_performance.get("W_net [kW]", np.nan), "η_th [-]": cycle_performance.get("η_th [-]", np.nan), "ε_ex [-]": cycle_performance.get("ε_ex [-]", np.nan), "m_orc [kg/s]": m_orc })
                else: raise ValueError("calculate_orc_performance returned None")
            except Exception as calc_e:
                results_list.append({ "P_evap [bar]": p_evap_bar, "T_turb_in [K]": t_turb_in_K, "T_turb_in [°C]": t_turb_in_C, "Q_in [kW]": np.nan, "W_net [kW]": np.nan, "η_th [-]": np.nan, "ε_ex [-]": np.nan, "m_orc [kg/s]": m_orc })
                print(f"   計算中: {completed_iterations}/{total_iterations} (P_evap={p_evap_bar:.2f} bar, m_orc={m_orc:.1f} kg/s - 計算失敗: {calc_e})", end='\r')

    print("\n  計算完了。                                                                      ")
    results_df = pd.DataFrame(results_list)
    results_df_cleaned = results_df.dropna().copy()

    if results_df_cleaned.empty:
        print("  有効な計算結果が得られませんでした。プロットをスキップします。")
        print("\n  --- 計算結果 (生データ) ---")
        print(results_df)
        return # プロットせずに終了

    # --- 結果のプロット ---
    print("  結果をプロット中...")
    fig, axes = plt.subplots(5, 1, figsize=(10, 25), sharex=True)
    cmap = cm.get_cmap('viridis', len(m_orc_values))
    markers = ['o', 's', '^', 'D', 'x']

    # 各プロットのループ処理
    plot_configs = [
        {"ax_idx": 0, "y_col": "η_th [-]", "y_label": "熱効率 η_th [%]", "multiplier": 100, "linestyle": "-"},
        {"ax_idx": 1, "y_col": "ε_ex [-]", "y_label": "エクセルギー効率 ε_ex [%]", "multiplier": 100, "linestyle": "--"},
        {"ax_idx": 2, "y_col": "W_net [kW]", "y_label": "正味出力 W_net [kW]", "multiplier": 1, "linestyle": ":"},
        # T_turb_in は m_orc に依存しないため、ループ外でプロット
        {"ax_idx": 4, "y_col": "Q_in [kW]", "y_label": "蒸発器熱入力 Q_in [kW]", "multiplier": 1, "linestyle": "-."}
    ]

    for config in plot_configs:
        ax = axes[config["ax_idx"]]
        for i, m_val in enumerate(m_orc_values):
            df_subset = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_val]
            if not df_subset.empty:
                ax.plot(df_subset["P_evap [bar]"], df_subset[config["y_col"]] * config["multiplier"],
                        marker=markers[i % len(markers)], linestyle=config["linestyle"],
                        color=cmap(i), markersize=5, label=f'm={m_val:.1f} kg/s')
        ax.set_ylabel(config["y_label"])
        ax.grid(True)
        if config["ax_idx"] == 0: # 最初のプロットに凡例とタイトル
             ax.legend(title="質量流量", fontsize='small')
             title_text = (f"ORC性能 vs 蒸発圧力 (上限 {max_P_evap_bar} bar)\n"
                           f"(作動流体: {fluid}, T_cond={T_cond-273.15:.1f}°C, 過熱度={superheat_C}°C, "
                           f"η_pump={eta_pump:.2f}, η_turb={eta_turb:.2f})")
             ax.set_title(title_text)

    # タービン入口温度のプロット (ax4) - m_orc に依存しない
    ax4 = axes[3]
    m_first = m_orc_values[0]
    df_subset_first = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_first]
    if not df_subset_first.empty:
        df_plot = df_subset_first.sort_values("P_evap [bar]").drop_duplicates(subset=["P_evap [bar]"])
        ax4.plot(df_plot["P_evap [bar]"], df_plot["T_turb_in [°C]"], marker='.', linestyle='-', color='purple')
    ax4.set_ylabel("タービン入口温度 T_turb_in [°C]")
    ax4.grid(True)

    # X軸ラベルを一番下に設定
    axes[-1].set_xlabel("蒸発圧力 P_evap [bar]")

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    # ファイル名に上限圧力を入れる
    plot_filename = f"orc_performance_vs_Pevap_max{max_P_evap_bar}bar_{fluid}_SH{superheat_C}C.png"
    plt.savefig(plot_filename, dpi=300)
    print(f"  プロットを {plot_filename} に保存しました。")
    plt.close(fig) # メモリ解放のためフィギュアを閉じる

    # --- (オプション) 結果の表示 ---
    print("\n  --- 計算結果概要 ---")
    print(f"  作動流体: {fluid}")
    print(f"  凝縮温度: {T_cond-273.15:.1f} °C (P_cond={P_cond_bar:.2f} bar)")
    print(f"  過熱度: {superheat_C} °C")
    print(f"  蒸発圧力上限: {max_P_evap_bar} bar")
    # ... (他のパラメータ表示) ...
    print("-" * 30)
    print(f"  蒸発圧力範囲 (計算成功): {results_df_cleaned['P_evap [bar]'].min():.2f} - {results_df_cleaned['P_evap [bar]'].max():.2f} bar")
    print(f"  タービン入口温度範囲 (計算成功): {results_df_cleaned['T_turb_in [°C]'].min():.1f} - {results_df_cleaned['T_turb_in [°C]'].max():.1f} °C")
    # ... (質量流量ごとの最大値表示) ...

# --------------------------------------------------
# メイン処理
# --------------------------------------------------
if __name__ == "__main__":
    # --- 固定パラメータ ---
    T_cond_main = 305.0              # 凝縮温度 [K] (例: 32 °C)
    eta_pump_main = 0.75             # ポンプ効率 [-]
    eta_turb_main = 0.80             # タービン効率 [-]
    fluid_main = DEFAULT_FLUID       # 作動流体 (ene_analからインポート)
    T0_main = DEFAULT_T0             # 環境温度 [K] (ene_analからインポート)
    superheat_C_main = 10.0          # 過熱度 [°C]
    m_orc_values_main = np.linspace(1.0, 7.0, 5) # 質量流量の範囲 [kg/s]

    # --- 上限圧力を変えて解析を実行 ---
    max_pressures_to_run = [15.0, 20.0] # 上限圧力リスト [bar]

    for max_p in max_pressures_to_run:
        run_orc_analysis_and_plot(
            max_P_evap_bar=max_p,
            T_cond=T_cond_main,
            eta_pump=eta_pump_main,
            eta_turb=eta_turb_main,
            fluid=fluid_main,
            T0=T0_main,
            superheat_C=superheat_C_main,
            m_orc_values=m_orc_values_main
        )

    print("\n全ての解析が完了しました。")

