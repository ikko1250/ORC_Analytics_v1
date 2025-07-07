import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm # カラーマップ用
import CoolProp.CoolProp as CP # CoolPropライブラリをインポート
import os # ファイルパス操作用

# 解析用関数をインポート (ene_anal.py ファイルが必要です)
try:
    # ene_anal.py から実際の関数と定数をインポート
    # calculate_orc_performance, DEFAULT_FLUID, DEFAULT_T0 などの定義が必要
    from ORC_analysis.archive.ene_anal import calculate_orc_performance, DEFAULT_FLUID, DEFAULT_T0
    print("ene_anal.py から calculate_orc_performance をインポートしました。")
except ImportError:
    print("エラー: ene_anal.py が見つからないか、必要な関数/定数が定義されていません。")
    print("スクリプトを続行できません。ene_anal.py を同じディレクトリに配置してください。")
    exit() # ene_anal.py が必須のため終了
except NameError:
    print("エラー: ene_anal.py 内で DEFAULT_FLUID または DEFAULT_T0 が定義されていません。")
    print("スクリプトを続行できません。ene_anal.py を確認してください。")
    exit()

# 日本語フォント設定 (環境に合わせて調整が必要な場合があります)
try:
    font_name = 'M+ 1c' # 例: Linux
    # font_name = 'Yu Gothic' # 例: Windows
    # font_name = 'Hiragino Sans' # 例: macOS
    plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False # マイナス記号の文字化け対策
    print(f"フォント '{plt.rcParams['font.family']}' を設定しました。")
except Exception as e:
    print(f"指定されたフォント '{font_name}' の設定に失敗しました: {e}")
    try:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        print("警告: 日本語フォントが見つからないため、デフォルトのフォントを使用します。グラフの日本語が文字化けする可能性があります。")
    except Exception as e_fallback:
        print(f"デフォルトフォントの設定にも失敗しました: {e_fallback}")

# --------------------------------------------------
# 熱源ベースの計算を実行する関数 (プロット機能は削除)
# --------------------------------------------------
def calculate_orc_performance_for_heat_source(
    T_hs_in_values_C, m_hs, Cp_hs, PPTD_K,
    P_evap_values_bar, # 試行するORC蒸発圧力の範囲
    T_cond, eta_pump, eta_turb, fluid, T0, superheat_C
):
    """
    特定の熱源流量に対して、熱源条件に基づいてORC性能解析を行い、結果のDataFrameを返す関数。

    Args:
        (略 - run_orc_analysis_with_heat_source と同じ)
        m_hs (float): *単一の*熱源の質量流量 [kg/s]

    Returns:
        pd.DataFrame: 計算結果（クリーンアップ済み）。有効な結果がない場合は空のDataFrame。
                      カラム: "T_hs_in [°C]", "P_evap [bar]", "T_sat_evap [°C]",
                              "T_turb_in [°C]", "Q_in [kW]", "m_orc [kg/s]",
                              "W_net [kW]", "η_th [-]", "Error"
    """
    print(f"\n--- 解析開始: 熱源流量 m_hs = {m_hs:.2f} kg/s ---")
    # print(f"  熱源条件: Cp={Cp_hs} kJ/kg/K, PPTD={PPTD_K} K")
    # print(f"  ORC条件: T_cond={T_cond-273.15:.1f}°C, Superheat={superheat_C}°C, Fluid={fluid}")
    # print(f"  試行する蒸発圧力範囲: {min(P_evap_values_bar):.1f} - {max(P_evap_values_bar):.1f} bar")

    superheat_K = superheat_C
    T_hs_in_values_K = T_hs_in_values_C + 273.15
    P_evap_values_pa = P_evap_values_bar * 1e5

    results_list = []
    total_iterations = len(T_hs_in_values_K) * len(P_evap_values_pa)
    completed_iterations = 0

    # 外側ループ: 熱源入口温度
    for t_hs_in_K in T_hs_in_values_K:
        t_hs_in_C = t_hs_in_K - 273.15

        # 内側ループ: ORC蒸発圧力
        for p_evap_pa in P_evap_values_pa:
            p_evap_bar = p_evap_pa / 1e5
            completed_iterations += 1
            print(f" 計算中 (m_hs={m_hs:.1f}): {completed_iterations}/{total_iterations} (T_hs_in={t_hs_in_C:.1f}°C, P_evap={p_evap_bar:.1f} bar)", end='\r')

            # 各ループでの変数を初期化
            T_sat_evap_K = np.nan
            T_hs_out_K = np.nan
            t_turb_in_K = np.nan
            t_turb_in_C = np.nan
            q_hs_available = np.nan
            m_orc = np.nan
            w_net = np.nan
            eta_th = np.nan
            error_message = None

            try:
                # --- (計算ロジックは以前と同様) ---
                # 1. ORC飽和温度と熱源出口温度の計算
                T_sat_evap_K = CP.PropsSI('T', 'P', p_evap_pa, 'Q', 1, fluid)
                T_hs_out_K = T_sat_evap_K + PPTD_K

                # 2. 物理的制約チェック
                if T_hs_out_K >= t_hs_in_K:
                    raise ValueError(f"熱源出口温度 ({T_hs_out_K-273.15:.1f}°C) >= 入口 ({t_hs_in_C:.1f}°C)")
                P_crit_pa = CP.PropsSI('Pcrit', fluid)
                if p_evap_pa >= P_crit_pa:
                    raise ValueError(f"蒸発圧力 ({p_evap_bar:.1f} bar) >= 臨界圧 ({P_crit_pa/1e5:.1f} bar)")
                P_cond_pa_check = CP.PropsSI('P', 'T', T_cond, 'Q', 0, fluid)
                if p_evap_pa <= P_cond_pa_check:
                    raise ValueError(f"蒸発圧力 ({p_evap_bar:.1f} bar) <= 凝縮圧 ({P_cond_pa_check/1e5:.1f} bar)")

                # 3. 熱源からの利用可能熱量
                q_hs_available = m_hs * Cp_hs * (t_hs_in_K - T_hs_out_K) # kW
                if q_hs_available <= 0:
                    raise ValueError("利用可能熱量 <= 0")

                # 4. ORCタービン入口温度の計算
                t_turb_in_K = T_sat_evap_K + superheat_K
                t_turb_in_C = t_turb_in_K - 273.15
                if t_turb_in_K >= t_hs_in_K:
                     raise ValueError(f"T_turb_in ({t_turb_in_C:.1f}°C) >= T_hs_in ({t_hs_in_C:.1f}°C)")
                T_crit_orc = CP.PropsSI('Tcrit', fluid)
                if t_turb_in_K >= T_crit_orc:
                    raise ValueError(f"T_turb_in ({t_turb_in_C:.1f}°C) >= 臨界温度 ({T_crit_orc-273.15:.1f}°C)")

                # 5. ORCエンタルピーと質量流量の計算
                h1 = CP.PropsSI('H', 'T', T_cond, 'Q', 0, fluid) / 1000 # kJ/kg
                s1 = CP.PropsSI('S', 'T', T_cond, 'Q', 0, fluid) / 1000 # kJ/kg/K
                s2_ideal = s1
                h2_ideal = CP.PropsSI('H', 'P', p_evap_pa, 'S', s2_ideal * 1000, fluid) / 1000
                h2 = h1 + (h2_ideal - h1) / eta_pump # kJ/kg
                h3 = CP.PropsSI('H', 'T', t_turb_in_K, 'P', p_evap_pa, fluid) / 1000 # kJ/kg
                delta_h_evap = h3 - h2
                if delta_h_evap <= 0:
                    raise ValueError("Δh_evap <= 0 (h3 <= h2)")
                m_orc = q_hs_available / delta_h_evap # kg/s
                if m_orc <= 0:
                    raise ValueError("m_orc <= 0")

                # 6. ORC性能計算 (外部関数呼び出し)
                psi_df, component_df, cycle_performance = calculate_orc_performance(
                    P_evap=p_evap_pa, T_turb_in=t_turb_in_K, T_cond=T_cond,
                    eta_pump=eta_pump, eta_turb=eta_turb,
                    fluid=fluid, m_orc=m_orc, T0=T0
                )
                if cycle_performance is None:
                    raise ValueError("calculate_orc_performance returned None")
                w_net = cycle_performance.get("W_net [kW]", np.nan)
                eta_th = cycle_performance.get("η_th [-]", np.nan)
                if np.isnan(w_net) or np.isnan(eta_th):
                    raise ValueError("calculate_orc_performance returned NaN")
                # --- (計算ロジックここまで) ---

            except ValueError as ve:
                error_message = str(ve)
            except Exception as e:
                error_message = f"予期せぬエラー: {str(e)}"

            # 結果をリストに追加
            results_list.append({
                "T_hs_in [°C]": t_hs_in_C,
                "P_evap [bar]": p_evap_bar,
                "T_sat_evap [°C]": T_sat_evap_K - 273.15 if not np.isnan(T_sat_evap_K) else np.nan,
                "T_turb_in [°C]": t_turb_in_C if not np.isnan(t_turb_in_C) else np.nan,
                "Q_in [kW]": q_hs_available if not np.isnan(q_hs_available) else np.nan,
                "m_orc [kg/s]": m_orc if not np.isnan(m_orc) else np.nan,
                "W_net [kW]": w_net if not np.isnan(w_net) else np.nan,
                "η_th [-]": eta_th if not np.isnan(eta_th) else np.nan,
                "Error": error_message
            })

    print(f"\n計算完了 (m_hs={m_hs:.1f})。                                                       ")
    results_df = pd.DataFrame(results_list)

    # NaNを含む（計算失敗した）結果を除外してクリーンなデータフレームを作成
    results_df_cleaned = results_df.dropna(subset=["W_net [kW]", "η_th [-]"]).copy()

    # エラーが発生した組み合わせを表示 (オプション)
    errors_df = results_df[results_df['Error'].notna()]
    if not errors_df.empty:
        print(f"--- m_hs={m_hs:.1f} kg/s でエラー/制約違反が発生した組み合わせ: {len(errors_df)} 件 ---")
        # print(errors_df[['T_hs_in [°C]', 'P_evap [bar]', 'Error']].head())

    if results_df_cleaned.empty:
        print(f"警告: m_hs={m_hs:.1f} kg/s では有効な計算結果が得られませんでした。")

    return results_df_cleaned

# --------------------------------------------------
# メイン処理
# --------------------------------------------------
if __name__ == "__main__":
    # --- ORC 固定パラメータ ---
    T_cond_main = 30 + 273.15       # 凝縮温度 [K] (例: 30 °C)
    eta_pump_main = 0.75            # ポンプ効率 [-]
    eta_turb_main = 0.80            # タービン効率 [-]
    fluid_main = DEFAULT_FLUID      # 作動流体 (ene_anal.py から取得)
    T0_main = DEFAULT_T0            # 環境温度 [K] (ene_anal.py から取得)
    superheat_C_main = 5.0          # ORC過熱度 [°C] (例: 5°C)
    Cp_hs_main = 4.186              # 熱源比熱 [kJ/kg/K] (例: 水)
    PPTD_K_main = 10.0              # 最小接近温度差 [K] (例: 10K)

    # --- 解析条件 ---
    # 熱源入口温度の範囲 [°C] (例: 70-180°C, 23点)
    T_hs_in_values_C_main = np.linspace(70, 180, 23)
    # 試行する熱源質量流量のリスト [kg/s]
    m_hs_values_main = np.array([5.0, 10.0, 15.0, 20.0]) # 例

    # --- 試行するORC蒸発圧力の範囲 (全流量で共通) ---
    try:
        P_cond_pa = CP.PropsSI('P', 'T', T_cond_main, 'Q', 0, fluid_main)
        P_crit_pa = CP.PropsSI('Pcrit', fluid_main)
        P_evap_min_pa = P_cond_pa * 1.1
        P_evap_max_pa = P_crit_pa * 0.90
        if P_evap_min_pa >= P_evap_max_pa:
             raise ValueError("蒸発圧力範囲が無効 (min >= max)")
        P_evap_min_bar = P_evap_min_pa / 1e5
        P_evap_max_bar = P_evap_max_pa / 1e5
        num_pressure_points = 20 # 圧力の試行点数を増やすと最適値の精度向上
        P_evap_values_bar_main = np.linspace(P_evap_min_bar, P_evap_max_bar, num_pressure_points)
        print(f"設定された蒸発圧力試行範囲: {P_evap_min_bar:.2f} - {P_evap_max_bar:.2f} bar ({num_pressure_points} 点)")
    except Exception as e:
        print(f"エラー: 試行する蒸発圧力範囲の設定に失敗: {e}")
        print("デフォルトの圧力範囲を使用します。")
        P_evap_values_bar_main = np.linspace(2.0, 15.0, 15) # フォールバック

    # --- プロット準備 ---
    fig_opt, ax_opt = plt.subplots(3, 1, figsize=(10, 15), sharex=True)
    cmap_mhs = cm.get_cmap('coolwarm', len(m_hs_values_main)) # 流量用のカラーマップ
    markers = ['o', 's', '^', 'D', 'v', '<', '>'] # マーカー
    all_optimal_dfs_list = [] # 各流量での最適結果を格納するリスト

    # --- 各熱源流量について解析と最適化を実行 ---
    for i, m_hs_current in enumerate(m_hs_values_main):

        # 現在の流量で性能計算を実行
        results_df_current_mhs = calculate_orc_performance_for_heat_source(
            T_hs_in_values_C=T_hs_in_values_C_main,
            m_hs=m_hs_current, # 現在の流量を渡す
            Cp_hs=Cp_hs_main,
            PPTD_K=PPTD_K_main,
            P_evap_values_bar=P_evap_values_bar_main,
            T_cond=T_cond_main,
            eta_pump=eta_pump_main,
            eta_turb=eta_turb_main,
            fluid=fluid_main,
            T0=T0_main,
            superheat_C=superheat_C_main
        )

        # --- 現在の流量における最適圧力の探索 ---
        optimal_results_current_mhs = []
        if not results_df_current_mhs.empty:
            # 有効な結果が得られた T_hs_in のユニークな値でループ
            for t_hs in results_df_current_mhs["T_hs_in [°C]"].unique():
                df_temp = results_df_current_mhs[results_df_current_mhs["T_hs_in [°C]"] == t_hs]
                if not df_temp.empty:
                    # W_net が最大となる行を見つける
                    best_row_idx = df_temp['W_net [kW]'].idxmax()
                    best_row = df_temp.loc[best_row_idx]
                    optimal_results_current_mhs.append(best_row)

            if optimal_results_current_mhs:
                optimal_df_current_mhs = pd.DataFrame(optimal_results_current_mhs).sort_values("T_hs_in [°C]")
                all_optimal_dfs_list.append(optimal_df_current_mhs) # 後で表示するために保存

                print(f"\n--- 熱源流量 {m_hs_current:.1f} kg/s における最大出力時の条件 (一部抜粋) ---")
                print(optimal_df_current_mhs[["T_hs_in [°C]", "P_evap [bar]", "W_net [kW]", "η_th [-]"]].round(2).head())

                # --- 最適性能のプロット (現在の流量) ---
                color = cmap_mhs(i / (len(m_hs_values_main)-1) if len(m_hs_values_main)>1 else 0)
                marker = markers[i % len(markers)]
                label_mhs = f'm_hs={m_hs_current:.1f} kg/s'

                # 最大出力
                ax_opt[0].plot(optimal_df_current_mhs["T_hs_in [°C]"], optimal_df_current_mhs["W_net [kW]"],
                               marker=marker, linestyle='-', markersize=5, color=color, label=label_mhs)
                # 最大出力時の熱効率
                ax_opt[1].plot(optimal_df_current_mhs["T_hs_in [°C]"], optimal_df_current_mhs["η_th [-]"] * 100,
                               marker=marker, linestyle='--', markersize=5, color=color, label=label_mhs)
                # 最適蒸発圧力
                ax_opt[2].plot(optimal_df_current_mhs["T_hs_in [°C]"], optimal_df_current_mhs["P_evap [bar]"],
                               marker=marker, linestyle=':', markersize=5, color=color, label=label_mhs)
            else:
                 print(f"警告: m_hs={m_hs_current:.1f} kg/s では最適条件が見つかりませんでした。")
        else:
            # 有効な結果が全くない場合
             print(f"スキップ: m_hs={m_hs_current:.1f} kg/s では有効な計算結果がありませんでした。")


    # --- 全流量のプロット完了後 ---
    if not any(ax.has_data() for ax in ax_opt):
         print("\nエラー: プロットできる有効な最適性能データがありませんでした。")
    else:
        # グラフの装飾
        ax_opt[0].set_ylabel("最大正味出力 W_net [kW]")
        ax_opt[0].grid(True, linestyle='--', alpha=0.7)
        ax_opt[0].legend(title="熱源流量", fontsize='small')
        title_opt = (f"熱源温度に対する最大出力と最適蒸発圧力 (流量別)\n"
                     f"(ORC: {fluid_main}, T_cond={T_cond_main-273.15:.1f}°C, Superheat={superheat_C_main}°C, PPTD={PPTD_K_main}K)")
        ax_opt[0].set_title(title_opt)

        ax_opt[1].set_ylabel("最大出力時の熱効率 η_th [%]")
        ax_opt[1].grid(True, linestyle='--', alpha=0.7)
        ax_opt[1].legend(title="熱源流量", fontsize='small')

        ax_opt[2].set_xlabel("熱源入口温度 T_hs_in [°C]")
        ax_opt[2].set_ylabel("最適蒸発圧力 P_evap [bar]")
        ax_opt[2].grid(True, linestyle='--', alpha=0.7)
        ax_opt[2].legend(title="熱源流量", fontsize='small')

        plt.tight_layout(rect=[0, 0.03, 1, 0.96]) # タイトルスペースを考慮
        plot_filename_opt = f"orc_optimal_performance_vs_ThsIn_by_mhs_{fluid_main}_PPTD{PPTD_K_main}K_SH{superheat_C_main}C.png"
        try:
            plt.savefig(plot_filename_opt, dpi=300)
            print(f"\n最適性能プロット (流量別) を {plot_filename_opt} に保存しました。")
        except Exception as e:
            print(f"最適性能プロットの保存中にエラーが発生しました: {e}")
        plt.close(fig_opt) # メモリ解放

        # (オプション) 全ての最適化結果を結合して表示
        # if all_optimal_dfs_list:
        #     all_optimal_df_combined = pd.concat(all_optimal_dfs_list)
        #     print("\n--- 全流量における最適性能データ (結合) ---")
        #     print(all_optimal_df_combined[["T_hs_in [°C]", "m_hs [kg/s]", "P_evap [bar]", "W_net [kW]", "η_th [-]"]].round(2)) # m_hs カラムを追加する必要あり

    print("\n全ての解析が完了しました。")
