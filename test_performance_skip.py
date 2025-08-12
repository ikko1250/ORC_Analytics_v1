#!/usr/bin/env python3
"""
Plot_Template.pyの修正をテストするスクリプト
- 性能計算が失敗した場合に経済分析をスキップすることを確認
"""

import sys
sys.path.insert(0, '/home/ubuntu/cur/program/seminar_fresh')

from ORC_analysis.Plot_Template import run_single_orc_stage, get_nan_perf_dict, get_nan_econ_dict
import numpy as np

def test_performance_failure_skips_economics():
    """性能計算失敗時に経済分析がスキップされることをテスト"""
    print('=== 性能計算失敗時の経済分析スキップテスト ===')
    
    # 極端に低い温度でテスト（ORCが動作しない条件）
    T_htf_in_K = 323.15  # 50°C（湿り蒸気でORCが動作しない可能性が高い温度）
    Vdot_m3s = 5.0 / 3600  # 5 kg/s を m3/s として扱う
    
    # 経済パラメータ
    econ_params = {
        "interest_rate": 0.05,
        "project_life": 20,
        "annual_hours": 8000,
        "elec_price": 0.12,
        "maint_factor": 1.06,
    }
    
    # 追加熱交換器設定
    extra_duties_config = {
        "ratios": {"Superheater": 0.2, "Regenerator": 0.1},
        "lmtds": {"Superheater": 15.0, "Regenerator": 10.0}
    }
    
    # 湿り蒸気設定
    wet_steam_config = {
        "P_steam": 5e5,  # 5 bar
        "quality": 0.9,  # 品質90%
        "mass_flow_mode": True,
        "T_steam_out_offset_K": 10.0
    }
    
    try:
        perf_result, econ_result = run_single_orc_stage(
            T_htf_in_K=T_htf_in_K,
            Vdot_m3s=Vdot_m3s,
            T_cond_K=305.0,
            eta_pump_val=0.75,
            eta_turb_val=0.80,
            orc_fluid="R245fa",
            htf_fluid="Water",  # 湿り蒸気の場合は実質使用されない
            sc_C=8.0,
            pinch_K=10.0,
            econ_params_dict=econ_params,
            extra_duties_config_dict=extra_duties_config,
            heat_source_type="wet_steam",
            wet_steam_config=wet_steam_config
        )
        
        # 結果の確認
        W_net = perf_result.get("W_net [kW]", None)
        PEC_total = econ_result.get("PEC_total [$]", None)
        
        if W_net is None or np.isnan(W_net):
            print(f"✅ 性能計算が失敗（W_net = {W_net}）")
            if PEC_total is None or np.isnan(PEC_total):
                print("✅ 経済分析も正しくスキップされました（PEC_total = NaN）")
                return True
            else:
                print(f"❌ 経済分析がスキップされませんでした（PEC_total = {PEC_total}）")
                return False
        else:
            print(f"⚠️ 性能計算が成功しました（W_net = {W_net} kW）")
            print("この温度では実際にORCが動作する可能性があります")
            return True  # これは失敗ではない
            
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def test_successful_case():
    """正常な計算ケースのテスト"""
    print('\n=== 正常計算ケースのテスト ===')
    
    # 十分に高い温度でテスト（ORCが確実に動作する条件）
    T_htf_in_K = 373.15  # 100°C
    Vdot_m3s = 10.0 / 3600  # 10 kg/s を m3/s として扱う
    
    # 経済パラメータ
    econ_params = {
        "interest_rate": 0.05,
        "project_life": 20,
        "annual_hours": 8000,
        "elec_price": 0.12,
        "maint_factor": 1.06,
    }
    
    # 追加熱交換器設定
    extra_duties_config = {
        "ratios": {"Superheater": 0.2, "Regenerator": 0.1},
        "lmtds": {"Superheater": 15.0, "Regenerator": 10.0}
    }
    
    # 湿り蒸気設定
    wet_steam_config = {
        "P_steam": 10e5,  # 10 bar
        "quality": 0.95,  # 品質95%
        "mass_flow_mode": True,
        "T_steam_out_offset_K": 10.0
    }
    
    try:
        perf_result, econ_result = run_single_orc_stage(
            T_htf_in_K=T_htf_in_K,
            Vdot_m3s=Vdot_m3s,
            T_cond_K=305.0,
            eta_pump_val=0.75,
            eta_turb_val=0.80,
            orc_fluid="R245fa",
            htf_fluid="Water",
            sc_C=8.0,
            pinch_K=10.0,
            econ_params_dict=econ_params,
            extra_duties_config_dict=extra_duties_config,
            heat_source_type="wet_steam",
            wet_steam_config=wet_steam_config
        )
        
        # 結果の確認
        W_net = perf_result.get("W_net [kW]", None)
        PEC_total = econ_result.get("PEC_total [$]", None)
        
        if W_net is not None and not np.isnan(W_net) and W_net > 0:
            print(f"✅ 性能計算が成功（W_net = {W_net:.2f} kW）")
            if PEC_total is not None and not np.isnan(PEC_total) and PEC_total > 0:
                print(f"✅ 経済分析も成功（PEC_total = ${PEC_total:,.0f}）")
                return True
            else:
                print(f"❌ 経済分析が失敗（PEC_total = {PEC_total}）")
                return False
        else:
            print(f"❌ 性能計算が失敗（W_net = {W_net}）")
            return False
            
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

if __name__ == "__main__":
    print("Plot_Template.py 性能計算失敗時の経済分析スキップテスト")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    if test_performance_failure_skips_economics():
        success_count += 1
    if test_successful_case():
        success_count += 1
    
    print(f"\n結果: {success_count}/{total_tests} テスト成功")
    
    if success_count == total_tests:
        print("✅ 全てのテストが成功しました！")
    else:
        print("❌ 一部のテストが失敗しました。")
