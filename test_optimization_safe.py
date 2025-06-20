#!/usr/bin/env python3
"""安全な最適化コードのテストスクリプト"""

import sys
import os
import numpy as np

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ORC_analysis.config import set_component_setting, get_component_setting
from optimization_safe import (
    calculate_safe_power_limits,
    optimize_orc_with_components_safe,
    sensitivity_analysis_components_safe
)

print("=== 安全な最適化コードのテスト ===")
print()

def test_safe_power_limits():
    """安全電力制限の計算テスト"""
    print("1. 安全電力制限の計算テスト:")
    print("-" * 40)
    
    # テスト条件
    test_params = {
        'T_htf_in': 373.15,  # 100°C
        'Vdot_htf': 0.01,    # m³/s
        'T_cond': 305.15,    # 32°C
        'eta_pump': 0.75,
        'eta_turb': 0.80,
    }
    
    try:
        # 異なるエンタルピー制限での安全電力計算
        enthalpy_limits = [1000, 2000, 5000, 10000]  # kJ/kg
        
        print("エンタルピー制限[kJ/kg]  安全電力制限[kW]")
        print("-" * 45)
        
        for limit in enthalpy_limits:
            max_pre, max_sup = calculate_safe_power_limits(
                max_enthalpy_increase_kJ_per_kg=limit,
                **test_params
            )
            print(f"{limit:15.0f}        {max_pre:.3f}")
            
    except Exception as e:
        print(f"エラー: {e}")

def test_safe_optimization():
    """安全な最適化のテスト"""
    print("\n2. 安全な最適化のテスト:")
    print("-" * 40)
    
    # 基本パラメータ
    test_params = {
        'T_htf_in': 373.15,  # 100°C
        'Vdot_htf': 0.01,    # m³/s
        'T_cond': 305.15,    # 32°C
        'eta_pump': 0.75,
        'eta_turb': 0.80,
        'T_evap_out_target': 363.15,  # 90°C
    }
    
    test_cases = [
        {
            'desc': 'コンポーネントなし',
            'use_preheater': False,
            'use_superheater': False,
        },
        {
            'desc': '予熱器のみ（動的制限あり）',
            'use_preheater': True,
            'use_superheater': False,
            'use_dynamic_limits': True,
        },
        {
            'desc': '予熱器のみ（動的制限なし）',
            'use_preheater': True,
            'use_superheater': False,
            'use_dynamic_limits': False,
            'max_preheater_power': 1.0,  # 小さな値に制限
        },
        {
            'desc': '過熱器のみ（動的制限あり）',
            'use_preheater': False,
            'use_superheater': True,
            'use_dynamic_limits': True,
        },
        {
            'desc': '両方（動的制限あり）',
            'use_preheater': True,
            'use_superheater': True,
            'use_dynamic_limits': True,
        },
    ]
    
    for case in test_cases:
        print(f"\nテスト: {case['desc']}")
        print("-" * 30)
        
        try:
            # 設定
            set_component_setting('use_preheater', case['use_preheater'])
            set_component_setting('use_superheater', case['use_superheater'])
            
            # 最適化実行
            result = optimize_orc_with_components_safe(
                max_preheater_power=case.get('max_preheater_power', 50.0),
                max_superheater_power=case.get('max_superheater_power', 100.0),
                use_dynamic_limits=case.get('use_dynamic_limits', True),
                **test_params
            )
            
            if result:
                print(f"✓ 成功")
                print(f"  Q_preheater_opt: {result.get('Q_preheater_opt [kW]', 'N/A'):.4f} kW")
                print(f"  Q_superheater_opt: {result.get('Q_superheater_opt [kW]', 'N/A'):.4f} kW")
                print(f"  W_net: {result.get('W_net [kW]', 'N/A'):.6f} kW")
                print(f"  最適化成功: {result.get('optimization_success', 'N/A')}")
                print(f"  使用された制限値:")
                print(f"    予熱器: {result.get('max_preheater_power_used [kW]', 'N/A'):.3f} kW")
                print(f"    過熱器: {result.get('max_superheater_power_used [kW]', 'N/A'):.3f} kW")
                print(f"  動的制限適用: {result.get('dynamic_limits_applied', 'N/A')}")
            else:
                print("❌ 失敗: 結果がNone")
                
        except Exception as e:
            print(f"❌ エラー: {e}")

def test_safe_sensitivity_analysis():
    """安全な感度解析のテスト"""
    print("\n3. 安全な感度解析のテスト:")
    print("-" * 40)
    
    # 基本パラメータ
    test_params = {
        'T_htf_in': 373.15,  # 100°C
        'Vdot_htf': 0.01,    # m³/s
        'T_cond': 305.15,    # 32°C
        'eta_pump': 0.75,
        'eta_turb': 0.80,
        'T_evap_out_target': 363.15,  # 90°C
    }
    
    try:
        # 予熱器のみで感度解析
        set_component_setting('use_preheater', True)
        set_component_setting('use_superheater', False)
        
        result = sensitivity_analysis_components_safe(
            use_dynamic_limits=True,
            **test_params
        )
        
        if result:
            print(f"✓ 感度解析成功")
            print(f"  結果数: {len(result.get('sensitivity_results', []))}")
            print(f"  電力範囲: {result.get('power_range', [])[:5]}... (最初の5点)")
            print(f"  動的制限適用: {result.get('dynamic_limits_applied', 'N/A')}")
            
            # いくつかの結果を表示
            results = result.get('sensitivity_results', [])
            if results:
                print(f"  サンプル結果:")
                for i, res in enumerate(results[:3]):  # 最初の3つ
                    power = res.get('Q_preheater_test [kW]', 0)
                    w_net = res.get('W_net [kW]', 0)
                    print(f"    電力{power:.3f}kW -> W_net={w_net:.6f}kW")
        else:
            print("❌ 感度解析失敗")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

def test_comparison_with_original():
    """元のコードとの比較テスト"""
    print("\n4. 元のコードとの比較:")
    print("-" * 40)
    
    # 元のコードをインポート
    try:
        from ORC_analysis.optimization import optimize_orc_with_components
        
        test_params = {
            'T_htf_in': 373.15,  # 100°C
            'Vdot_htf': 0.01,    # m³/s
            'T_cond': 305.15,    # 32°C
            'eta_pump': 0.75,
            'eta_turb': 0.80,
            'T_evap_out_target': 363.15,  # 90°C
            'max_preheater_power': 1.0,  # 小さな値に制限
        }
        
        # 予熱器のみのテスト
        set_component_setting('use_preheater', True)
        set_component_setting('use_superheater', False)
        
        print("元のコード（小さな電力制限）:")
        try:
            original_result = optimize_orc_with_components(**test_params)
            if original_result:
                print(f"  ✓ 成功: W_net={original_result.get('W_net [kW]', 'N/A'):.6f} kW")
                print(f"  Q_preheater_opt: {original_result.get('Q_preheater_opt [kW]', 'N/A'):.4f} kW")
            else:
                print(f"  ❌ 失敗: None")
        except Exception as e:
            print(f"  ❌ エラー: {str(e)[:50]}")
        
        print("\n新しい安全コード:")
        try:
            safe_result = optimize_orc_with_components_safe(
                use_dynamic_limits=True,
                **test_params
            )
            if safe_result:
                print(f"  ✓ 成功: W_net={safe_result.get('W_net [kW]', 'N/A'):.6f} kW")
                print(f"  Q_preheater_opt: {safe_result.get('Q_preheater_opt [kW]', 'N/A'):.4f} kW")
                print(f"  適用された制限: {safe_result.get('max_preheater_power_used [kW]', 'N/A'):.3f} kW")
            else:
                print(f"  ❌ 失敗: None")
        except Exception as e:
            print(f"  ❌ エラー: {str(e)[:50]}")
            
    except ImportError:
        print("元のoptimization.pyをインポートできませんでした")

if __name__ == "__main__":
    test_safe_power_limits()
    test_safe_optimization()
    test_safe_sensitivity_analysis()
    test_comparison_with_original()
    
    print("\n" + "=" * 50)
    print("テスト完了")
    print("=" * 50)
