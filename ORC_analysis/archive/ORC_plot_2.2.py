import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm # カラーマップ用
import CoolProp.CoolProp as CP # CoolPropライブラリをインポート

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
# 1. 計算条件の設定
# --------------------------------------------------
# --- 固定パラメータ ---
T_cond = 305.0              # 凝縮温度 [K] (例: 32 °C)
eta_pump = 0.75             # ポンプ効率 [-]
eta_turb = 0.80             # タービン効率 [-]
fluid = DEFAULT_FLUID       # 作動流体 (ene_analからインポート)
T0 = DEFAULT_T0             # 環境温度 [K] (ene_analからインポート)
superheat_C = 10.0          # 過熱度 [°C] (ケルビンでの差も同じ)
superheat_K = superheat_C

# --- 可変パラメータの範囲 ---
# 蒸発圧力の範囲を設定 [Pa]
# まず凝縮圧力を計算
try:
    P_cond_pa = CP.PropsSI('P', 'T', T_cond, 'Q', 0, fluid)
    P_cond_bar = P_cond_pa / 1e5
    print(f"凝縮圧力 P_cond = {P_cond_bar:.2f} bar")
    # 凝縮圧力より十分高く、臨界圧力より低い範囲で設定 (例)
    P_crit_pa = CP.PropsSI('Pcrit', fluid)
    # 蒸発圧力の最小値は凝縮圧力より少し高く設定 (例: P_cond * 1.1)
    P_evap_min_pa = P_cond_pa * 1.1
    # 蒸発圧力の最大値は臨界圧力より低く設定 (例: P_crit * 0.9)
    P_evap_max_pa = P_crit_pa * 0.9
    # 対数スケールで圧力を生成するか、線形スケールで生成するか選択
    # P_evap_values_pa = np.logspace(np.log10(P_evap_min_pa), np.log10(P_evap_max_pa), 50) # 対数スケール (50点)
    P_evap_values_pa = np.linspace(P_evap_min_pa, P_evap_max_pa, 50) # 線形スケール (50点)
    P_evap_values_bar = P_evap_values_pa / 1e5 # bar 単位も用意
    print(f"蒸発圧力範囲: {P_evap_values_bar.min():.2f} bar から {P_evap_values_bar.max():.2f} bar まで")
except Exception as e:
    print(f"エラー: 圧力範囲の設定に失敗しました: {e}")
    print(f"作動流体 {fluid} の臨界圧力を確認してください。")
    exit()

# 質量流量の範囲を設定 [kg/s]
m_orc_values = np.linspace(3.0, 7.0, 5) # 3.0 kg/s から 7.0 kg/s まで 5点

# --------------------------------------------------
# 2. パラメータスイープ計算の実行
# --------------------------------------------------
results_list = []

print(f"蒸発圧力と質量流量を変化させてORC性能を計算中 (過熱度 = {superheat_C}°C)...")
total_iterations = len(P_evap_values_pa) * len(m_orc_values)
completed_iterations = 0

# 蒸発圧力でループ
for p_evap_pa in P_evap_values_pa:
    p_evap_bar = p_evap_pa / 1e5 # bar 単位

    # 蒸発圧力から飽和温度とタービン入口温度を計算
    t_turb_in_K = np.nan # 初期化
    t_turb_in_C = np.nan # 初期化
    try:
        # 蒸発圧力における飽和温度を計算
        T_sat_evap_K = CP.PropsSI('T', 'P', p_evap_pa, 'Q', 1, fluid) # 飽和蒸気温度 (Q=1)
        # タービン入口温度を計算 (飽和温度 + 過熱度)
        t_turb_in_K = T_sat_evap_K + superheat_K
        t_turb_in_C = t_turb_in_K - 273.15

        # 計算されたタービン入口温度が妥当かチェック (オプション)
        # 例えば、臨界温度を超えていないかなど
        T_crit = CP.PropsSI('Tcrit', fluid)
        if t_turb_in_K >= T_crit:
             # print(f"\n警告: 計算された T_turb_in ({t_turb_in_K:.1f} K) が臨界温度 ({T_crit:.1f} K) 以上です (P_evap={p_evap_bar:.2f} bar)。")
             raise ValueError("計算されたタービン入口温度が臨界温度以上")

    except Exception as e:
        # print(f"\n警告: P_evap={p_evap_bar:.2f} bar におけるタービン入口温度の計算に失敗しました: {e}")
        # この圧力での計算をスキップ (内側のループも実行されない)
        # NaNを記録しておく（プロット用に）
        for m_orc in m_orc_values:
             completed_iterations += 1
             results_list.append({
                "P_evap [bar]": p_evap_bar,
                "T_turb_in [K]": np.nan,
                "T_turb_in [°C]": np.nan,
                "Q_in [kW]": np.nan, # 熱入力も計算できない
                "W_net [kW]": np.nan,
                "η_th [-]": np.nan,
                "ε_ex [-]": np.nan,
                "m_orc [kg/s]": m_orc
             })
        print(f" 計算中: {completed_iterations}/{total_iterations} (P_evap={p_evap_bar:.2f} bar - T_turb_in 計算エラー)", end='\r')
        continue # 次の圧力へ

    # 質量流量でループ
    for m_orc in m_orc_values:
        completed_iterations += 1

        # 進捗表示 (タービン入口温度も表示)
        print(f" 計算中: {completed_iterations}/{total_iterations} (P_evap={p_evap_bar:.2f} bar, T_turb_in={t_turb_in_C:.1f} °C, m_orc={m_orc:.1f} kg/s)", end='\r')

        # ORC性能計算関数を呼び出し
        try:
            psi_df, component_df, cycle_performance = calculate_orc_performance(
                P_evap=p_evap_pa,       # 現在のループでの蒸発圧力 (Pa)
                T_turb_in=t_turb_in_K, # 計算されたタービン入口温度 (K)
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                fluid=fluid,
                m_orc=m_orc,           # 現在のループでの質量流量
                T0=T0
            )

            if cycle_performance is not None:
                # 計算成功時、結果をリストに追加 (熱入力 Q_in も取得)
                results_list.append({
                    "P_evap [bar]": p_evap_bar,
                    "T_turb_in [K]": t_turb_in_K,
                    "T_turb_in [°C]": t_turb_in_C,
                    "Q_in [kW]": cycle_performance.get("Q_in [kW]", np.nan), # 蒸発器熱入力
                    "W_net [kW]": cycle_performance.get("W_net [kW]", np.nan),
                    "η_th [-]": cycle_performance.get("η_th [-]", np.nan),
                    "ε_ex [-]": cycle_performance.get("ε_ex [-]", np.nan),
                    "m_orc [kg/s]": m_orc
                })
            else:
                raise ValueError("calculate_orc_performance returned None")

        except Exception as calc_e:
             # ORC性能計算関数内でエラーが発生した場合
            # print(f"\n警告: P_evap={p_evap_bar:.2f} bar, T_turb_in={t_turb_in_C:.1f}°C, m_orc={m_orc:.1f} kg/s でのORC性能計算に失敗しました: {calc_e}")
            results_list.append({
                "P_evap [bar]": p_evap_bar,
                "T_turb_in [K]": t_turb_in_K, # 温度は計算できていたかもしれない
                "T_turb_in [°C]": t_turb_in_C,
                "Q_in [kW]": np.nan,
                "W_net [kW]": np.nan,
                "η_th [-]": np.nan,
                "ε_ex [-]": np.nan,
                "m_orc [kg/s]": m_orc
            })
            print(f" 計算中: {completed_iterations}/{total_iterations} (P_evap={p_evap_bar:.2f} bar, m_orc={m_orc:.1f} kg/s - 計算失敗)", end='\r')


print("\n計算完了。                                                                      ") # 進捗表示をクリア

# 結果をDataFrameに変換
results_df = pd.DataFrame(results_list)

# NaN値を含む行を削除 (計算が失敗した点をプロットから除外するため)
results_df_cleaned = results_df.dropna().copy() # dropna() ですべてのNaNを含む行を削除

# 結果がない場合の処理
if results_df_cleaned.empty:
    print("有効な計算結果が得られませんでした。プロットをスキップします。")
    print("\n--- 計算結果 (生データ) ---")
    print(results_df) # 生データを表示して問題を確認できるようにする
else:
    # --------------------------------------------------
    # 3. 結果のプロット
    # --------------------------------------------------
    print("結果をプロット中...")
    # 5つのサブプロットを作成 (5行1列), x軸を共有
    fig, axes = plt.subplots(5, 1, figsize=(10, 25), sharex=True) # 図のサイズと数を調整

    # カラーマップとマーカーの設定 (質量流量ごと)
    cmap = cm.get_cmap('viridis', len(m_orc_values))
    markers = ['o', 's', '^', 'D', 'x'] # 質量流量ごとにマーカーを変える

    # --- 熱効率のプロット (η_th vs P_evap) ---
    ax1 = axes[0]
    for i, m_val in enumerate(m_orc_values):
        df_subset = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_val]
        if not df_subset.empty:
            ax1.plot(df_subset["P_evap [bar]"], df_subset["η_th [-]"] * 100, marker=markers[i % len(markers)], linestyle='-',
                     color=cmap(i), markersize=5, label=f'm={m_val:.1f} kg/s')
    ax1.set_ylabel("熱効率 η_th [%]")
    ax1.grid(True)
    ax1.legend(title="質量流量", fontsize='small')
    # タイトルに主要な固定パラメータを含める
    title_text = (f"ORC性能 vs 蒸発圧力\n"
                  f"(作動流体: {fluid}, T_cond={T_cond-273.15:.1f}°C, 過熱度={superheat_C}°C, "
                  f"η_pump={eta_pump:.2f}, η_turb={eta_turb:.2f})")
    ax1.set_title(title_text)

    # --- エクセルギー効率のプロット (ε_ex vs P_evap) ---
    ax2 = axes[1]
    for i, m_val in enumerate(m_orc_values):
        df_subset = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_val]
        if not df_subset.empty:
            ax2.plot(df_subset["P_evap [bar]"], df_subset["ε_ex [-]"] * 100, marker=markers[i % len(markers)], linestyle='--',
                     color=cmap(i), markersize=5, label=f'm={m_val:.1f} kg/s')
    ax2.set_ylabel("エクセルギー効率 ε_ex [%]")
    ax2.grid(True)
    # ax2.legend(title="質量流量", fontsize='small') # 凡例は一つにまとめても良い

    # --- 正味出力のプロット (W_net vs P_evap) ---
    ax3 = axes[2]
    for i, m_val in enumerate(m_orc_values):
        df_subset = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_val]
        if not df_subset.empty:
            ax3.plot(df_subset["P_evap [bar]"], df_subset["W_net [kW]"], marker=markers[i % len(markers)], linestyle=':',
                     color=cmap(i), markersize=5, label=f'm={m_val:.1f} kg/s')
    ax3.set_ylabel("正味出力 W_net [kW]")
    ax3.grid(True)
    # ax3.legend(title="質量流量", fontsize='small')

    # --- タービン入口温度のプロット (T_turb_in vs P_evap) ---
    # T_turb_in は P_evap と superheat で決まるため、m_orc によらず同じ線になるはず
    ax4 = axes[3]
    # 代表として最初の m_orc のデータでプロット (NaN除去後なので存在するはず)
    m_first = m_orc_values[0]
    df_subset_first = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_first]
    if not df_subset_first.empty:
         # 重複する可能性があるので P_evap でソートし、重複を除去してプロット
        df_plot = df_subset_first.sort_values("P_evap [bar]").drop_duplicates(subset=["P_evap [bar]"])
        ax4.plot(df_plot["P_evap [bar]"], df_plot["T_turb_in [°C]"], marker='.', linestyle='-', color='purple')
    ax4.set_ylabel("タービン入口温度 T_turb_in [°C]")
    ax4.grid(True)
    # ax4.legend() # 不要

    # --- 蒸発器熱入力のプロット (Q_in vs P_evap) ---
    ax5 = axes[4]
    for i, m_val in enumerate(m_orc_values):
        df_subset = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_val]
        if not df_subset.empty:
            ax5.plot(df_subset["P_evap [bar]"], df_subset["Q_in [kW]"], marker=markers[i % len(markers)], linestyle='-.',
                     color=cmap(i), markersize=5, label=f'm={m_val:.1f} kg/s')
    ax5.set_xlabel("蒸発圧力 P_evap [bar]") # X軸ラベルは一番下にのみ表示
    ax5.set_ylabel("蒸発器熱入力 Q_in [kW]")
    ax5.grid(True)
    # ax5.legend(title="質量流量", fontsize='small')

    plt.tight_layout(rect=[0, 0.03, 1, 0.97]) # タイトルスペース等を考慮してレイアウト調整
    plot_filename = f"orc_performance_vs_Pevap_{fluid}_SH{superheat_C}C.png"
    plt.savefig(plot_filename, dpi=300) # ファイル名と解像度を指定して保存

    print(f"プロットを {plot_filename} に保存しました。")

    # --- (オプション) 結果の表示 ---
    print("\n--- 計算結果概要 ---")
    print(f"作動流体: {fluid}")
    print(f"凝縮温度: {T_cond-273.15:.1f} °C (P_cond={P_cond_bar:.2f} bar)")
    print(f"過熱度: {superheat_C} °C")
    print(f"ポンプ効率: {eta_pump:.2f}")
    print(f"タービン効率: {eta_turb:.2f}")
    print(f"質量流量範囲: {min(m_orc_values):.1f} - {max(m_orc_values):.1f} kg/s")
    print(f"環境温度 (T0): {T0-273.15:.1f} °C")
    print("-" * 30)
    print(f"蒸発圧力範囲 (計算成功): {results_df_cleaned['P_evap [bar]'].min():.2f} - {results_df_cleaned['P_evap [bar]'].max():.2f} bar")
    print(f"タービン入口温度範囲 (計算成功): {results_df_cleaned['T_turb_in [°C]'].min():.1f} - {results_df_cleaned['T_turb_in [°C]'].max():.1f} °C")

    # 質量流量ごとに最大値を表示 (最大効率が得られる圧力など)
    print("\n--- 質量流量ごとの最大性能 (計算成功範囲内) ---")
    for m_val in m_orc_values:
        df_subset = results_df_cleaned[results_df_cleaned["m_orc [kg/s]"] == m_val]
        if not df_subset.empty:
            print(f"\n[質量流量: {m_val:.1f} kg/s]")
            try:
                max_eff_th_row = df_subset.loc[df_subset['η_th [-]'].idxmax()]
                print(f"  最大 熱効率: {max_eff_th_row['η_th [-]']*100:.2f}% (P_evap = {max_eff_th_row['P_evap [bar]']:.2f} bar, T_turb_in = {max_eff_th_row['T_turb_in [°C]']:.1f}°C)")
            except ValueError: print("  熱効率の最大値が見つかりません。")
            try:
                max_eff_ex_row = df_subset.loc[df_subset['ε_ex [-]'].idxmax()]
                print(f"  最大 エクセルギー効率: {max_eff_ex_row['ε_ex [-]']*100:.2f}% (P_evap = {max_eff_ex_row['P_evap [bar]']:.2f} bar, T_turb_in = {max_eff_ex_row['T_turb_in [°C]']:.1f}°C)")
            except ValueError: print("  エクセルギー効率の最大値が見つかりません。")
            try:
                max_wnet_row = df_subset.loc[df_subset['W_net [kW]'].idxmax()]
                print(f"  最大 正味出力: {max_wnet_row['W_net [kW]']:.1f} kW (P_evap = {max_wnet_row['P_evap [bar]']:.2f} bar, T_turb_in = {max_wnet_row['T_turb_in [°C]']:.1f}°C)")
            except ValueError: print("  正味出力の最大値が見つかりません。")
        else:
            print(f"\n[質量流量: {m_val:.1f} kg/s] - この流量での有効な計算結果なし")
