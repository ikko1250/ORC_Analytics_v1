#!/usr/bin/env python3
"""
Economic.pyの修正をテストするスクリプト
"""

from ORC_analysis.Economic import evaluate_orc_economics
import numpy as np

def test_normal_case():
    """正常なケースのテスト"""
    print('=== 正常ケースのテスト ===')
    try:
        result = evaluate_orc_economics(
            P_evap=15.0e5,
            T_turb_in=450.0,
            T_cond=308.15,
            eta_pump=0.75,
            eta_turb=0.80,
            m_orc=5.0
        )
        print('正常ケース: 成功')
        print(f'PEC_total: ${result["summary"]["PEC_total [$]"]:,.0f}')
        print(f'CRF: {result["summary"]["CRF [-]"]:,.4f}')
        return True
    except Exception as e:
        print(f'正常ケース: エラー - {e}')
        return False

def test_invalid_input():
    """異常な入力値のテスト"""
    print('\n=== 異常ケースのテスト（負の圧力） ===')
    try:
        result = evaluate_orc_economics(
            P_evap=-15.0e5,  # 負の値
            T_turb_in=450.0,
            T_cond=308.15,
            eta_pump=0.75,
            eta_turb=0.80,
            m_orc=5.0
        )
        print('異常ケース: 予期しない成功')
        return False
    except Exception as e:
        print(f'異常ケース: 期待通りエラー - {e}')
        return True

def test_invalid_efficiency():
    """効率の異常値テスト"""
    print('\n=== 異常ケースのテスト（効率>1） ===')
    try:
        result = evaluate_orc_economics(
            P_evap=15.0e5,
            T_turb_in=450.0,
            T_cond=308.15,
            eta_pump=1.5,  # 効率>1
            eta_turb=0.80,
            m_orc=5.0
        )
        print('異常ケース: 予期しない成功')
        return False
    except Exception as e:
        print(f'異常ケース: 期待通りエラー - {e}')
        return True

if __name__ == "__main__":
    print("Economic.py 入力値検証のテスト")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    if test_normal_case():
        success_count += 1
    if test_invalid_input():
        success_count += 1
    if test_invalid_efficiency():
        success_count += 1
    
    print(f"\n結果: {success_count}/{total_tests} テスト成功")
    
    if success_count == total_tests:
        print("✅ 全てのテストが成功しました！")
    else:
        print("❌ 一部のテストが失敗しました。")
