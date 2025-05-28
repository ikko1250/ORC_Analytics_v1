"""
ORC_Analysis/Economic.pyのpreheater/superheaterトグルのテスト
"""
<<<<<<< HEAD
import io
import sys
from contextlib import redirect_stdout

from ORC_analysis.config import set_component_setting, get_component_setting
from ORC_analysis.Economic import evaluate_orc_economics

# Tolerance for floating point comparison
FLOAT_TOLERANCE = 1e-6

=======
import sys
import io
from ORC_analysis.config import set_component_setting, get_component_setting
from ORC_analysis.Economic import evaluate_orc_economics

>>>>>>> Preheater/Superheaterトグル機能・テスト追加
def run_toggle_test(use_preheater, use_superheater):
    # トグル設定
    set_component_setting('use_preheater', use_preheater)
    set_component_setting('use_superheater', use_superheater)
<<<<<<< HEAD
    
    # 標準出力キャプチャ（context managerを使用）
    with redirect_stdout(io.StringIO()) as buf:
=======
    # 標準出力キャプチャ
    buf = io.StringIO()
    sys_stdout = sys.stdout
    sys.stdout = buf
    try:
>>>>>>> Preheater/Superheaterトグル機能・テスト追加
        res = evaluate_orc_economics(
            P_evap=15.0e5,
            T_turb_in=450.0,
            T_cond=308.15,
            eta_pump=0.75,
            eta_turb=0.80,
            m_orc=5.0,
            extra_duties={
                "Superheater": (200.0, 20.0),
                "Preheater": (100.0, 15.0),
                "Regenerator": (150.0, 15.0),
            },
        )
<<<<<<< HEAD
=======
    finally:
        sys.stdout = sys_stdout
>>>>>>> Preheater/Superheaterトグル機能・テスト追加
    output = buf.getvalue()
    # コスト確認
    df = res["component_costs"]
    pre_cost = df.loc["Preheater", "PEC [$]"] if "Preheater" in df.index else None
    sup_cost = df.loc["Superheater", "PEC [$]"] if "Superheater" in df.index else None
    # 結果表示
    print(f"\n--- Test: use_preheater={use_preheater}, use_superheater={use_superheater} ---")
    print(f"Preheater cost: {pre_cost}")
    print(f"Superheater cost: {sup_cost}")
<<<<<<< HEAD
    
    # 浮動小数点の比較に許容誤差を使用
    if not use_preheater and pre_cost is not None and abs(pre_cost) > FLOAT_TOLERANCE:
        print("[ERROR] Preheater OFFなのにコストが0でない！")
    if not use_superheater and sup_cost is not None and abs(sup_cost) > FLOAT_TOLERANCE:
        print("[ERROR] Superheater OFFなのにコストが0でない！")
    if use_preheater and (pre_cost is None or abs(pre_cost) <= FLOAT_TOLERANCE):
        print("[ERROR] Preheater ONなのにコストが0！")
    if use_superheater and (sup_cost is None or abs(sup_cost) <= FLOAT_TOLERANCE):
=======
    if not use_preheater and pre_cost != 0.0:
        print("[ERROR] Preheater OFFなのにコストが0でない！")
    if not use_superheater and sup_cost != 0.0:
        print("[ERROR] Superheater OFFなのにコストが0でない！")
    if use_preheater and (pre_cost is None or pre_cost == 0.0):
        print("[ERROR] Preheater ONなのにコストが0！")
    if use_superheater and (sup_cost is None or sup_cost == 0.0):
>>>>>>> Preheater/Superheaterトグル機能・テスト追加
        print("[ERROR] Superheater ONなのにコストが0！")
    # 警告出力確認
    if "警告" in output:
        print("[WARNING OUTPUT]", output.strip())

def main():
    # 4パターン
    for pre, sup in [(True, True), (True, False), (False, True), (False, False)]:
        run_toggle_test(pre, sup)

if __name__ == "__main__":
    main()
