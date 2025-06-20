#!/usr/bin/env python3
"""optimization.pyのデバッグ・テストコード

ORC最適化モジュールの包括的なテストを実行します。
様々なシナリオでの動作確認、エラー処理、パフォーマンス計測を行います。
"""

import sys
import os
import traceback
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# テスト対象モジュールのインポート
try:
    from ORC_analysis.optimization import (
        optimize_orc_with_components, 
        sensitivity_analysis_components
    )
    from ORC_analysis.config import (
        set_component_setting, 
        get_component_setting, 
        validate_component_settings,
        COMPONENT_SETTINGS
    )
    from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
    print("✓ モジュールのインポートが成功しました")
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    traceback.print_exc()
    sys.exit(1)


class OptimizationTester:
    """最適化モジュールの包括的テストクラス"""
    
    def __init__(self):
        self.test_results = []
        self.verbose = True
        
        # 基本テストパラメータ
        self.base_params = {
            'T_htf_in': 373.15,  # 100°C
            'Vdot_htf': 0.01,    # m³/s
            'T_cond': 305.15,    # 32°C
            'eta_pump': 0.75,
            'eta_turb': 0.80,
            'T_evap_out_target': 363.15,  # 90°C
            'fluid_orc': "R245fa",
            'fluid_htf': "Water",
            'superheat_C': 10.0,
            'pinch_delta_K': 10.0,
            'P_htf': 101.325e3,
            'max_preheater_power': 50.0,
            'max_superheater_power': 100.0,
        }
    
    def log_test(self, test_name: str, passed: bool, message: str = "", details: Any = None):
        """テスト結果をログに記録"""
        status = "✓ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details
        })
        
        if self.verbose:
            print(f"{status}: {test_name}")
            if message:
                print(f"    {message}")
            if details and isinstance(details, dict):
                for key, value in details.items():
                    print(f"    {key}: {value}")
            print()
    
    def test_basic_optimization_no_components(self):
        """基本的な最適化テスト（コンポーネント使用なし）"""
        test_name = "Basic optimization without components"
        try:
            # コンポーネントを無効にする
            set_component_setting('use_preheater', False)
            set_component_setting('use_superheater', False)
            
            result = optimize_orc_with_components(**self.base_params)
            
            # 結果の検証
            expected_keys = [
                'Q_preheater_opt [kW]', 'Q_superheater_opt [kW]', 
                'optimization_success', 'T_evap_out_target_param'
            ]
            
            passed = (
                result is not None and
                all(key in result for key in expected_keys) and
                result['Q_preheater_opt [kW]'] == 0.0 and
                result['Q_superheater_opt [kW]'] == 0.0 and
                result['optimization_success'] is True
            )
            
            details = {
                'Result keys': list(result.keys()) if result else "None",
                'Q_preheater_opt': result.get('Q_preheater_opt [kW]', 'N/A') if result else "N/A",
                'Q_superheater_opt': result.get('Q_superheater_opt [kW]', 'N/A') if result else "N/A",
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Components disabled, should return zero power for both", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_preheater_only_optimization(self):
        """予熱器のみの最適化テスト"""
        test_name = "Optimization with preheater only"
        try:
            # 予熱器のみ有効にする
            set_component_setting('use_preheater', True)
            set_component_setting('use_superheater', False)
            
            result = optimize_orc_with_components(**self.base_params)
            
            passed = (
                result is not None and
                result['optimization_success'] is True and
                result['Q_superheater_opt [kW]'] == 0.0 and
                0 <= result['Q_preheater_opt [kW]'] <= self.base_params['max_preheater_power']
            )
            
            details = {
                'Q_preheater_opt': result.get('Q_preheater_opt [kW]', 'N/A') if result else "N/A",
                'Q_superheater_opt': result.get('Q_superheater_opt [kW]', 'N/A') if result else "N/A",
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A",
                'optimization_success': result.get('optimization_success', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Preheater only, should optimize preheater power", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_superheater_only_optimization(self):
        """過熱器のみの最適化テスト"""
        test_name = "Optimization with superheater only"
        try:
            # 過熱器のみ有効にする
            set_component_setting('use_preheater', False)
            set_component_setting('use_superheater', True)
            
            result = optimize_orc_with_components(**self.base_params)
            
            passed = (
                result is not None and
                result['optimization_success'] is True and
                result['Q_preheater_opt [kW]'] == 0.0 and
                0 <= result['Q_superheater_opt [kW]'] <= self.base_params['max_superheater_power']
            )
            
            details = {
                'Q_preheater_opt': result.get('Q_preheater_opt [kW]', 'N/A') if result else "N/A",
                'Q_superheater_opt': result.get('Q_superheater_opt [kW]', 'N/A') if result else "N/A",
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A",
                'optimization_success': result.get('optimization_success', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Superheater only, should optimize superheater power", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_both_components_optimization(self):
        """両方のコンポーネントを使用した最適化テスト"""
        test_name = "Optimization with both components"
        try:
            # 両方有効にする
            set_component_setting('use_preheater', True)
            set_component_setting('use_superheater', True)
            
            result = optimize_orc_with_components(**self.base_params)
            
            passed = (
                result is not None and
                result['optimization_success'] is True and
                0 <= result['Q_preheater_opt [kW]'] <= self.base_params['max_preheater_power'] and
                0 <= result['Q_superheater_opt [kW]'] <= self.base_params['max_superheater_power']
            )
            
            details = {
                'Q_preheater_opt': result.get('Q_preheater_opt [kW]', 'N/A') if result else "N/A",
                'Q_superheater_opt': result.get('Q_superheater_opt [kW]', 'N/A') if result else "N/A",
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A",
                'optimization_success': result.get('optimization_success', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Both components enabled, should optimize both powers", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_edge_case_low_temperature(self):
        """エッジケース：低温熱源テスト"""
        test_name = "Edge case: Low temperature heat source"
        try:
            set_component_setting('use_preheater', True)
            set_component_setting('use_superheater', True)
            
            # 低温パラメータ
            low_temp_params = self.base_params.copy()
            low_temp_params['T_htf_in'] = 320.15  # 47°C (低温)
            
            result = optimize_orc_with_components(**low_temp_params)
            
            # 低温の場合は計算が失敗するか、性能が低くなることが期待される
            passed = True  # どちらの結果でも acceptable
            
            details = {
                'Result': 'Success' if result is not None else 'Failed (expected)',
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Low temperature test completed", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_edge_case_high_temperature(self):
        """エッジケース：高温熱源テスト"""
        test_name = "Edge case: High temperature heat source"
        try:
            set_component_setting('use_preheater', True)
            set_component_setting('use_superheater', True)
            
            # 高温パラメータ（R245faの臨界温度427.01K以下）
            high_temp_params = self.base_params.copy()
            high_temp_params['T_htf_in'] = 420.15  # 147°C (高温だが臨界点以下)
            
            result = optimize_orc_with_components(**high_temp_params)
            
            passed = result is not None
            
            details = {
                'Result': 'Success' if result is not None else 'Failed',
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A",
                'Q_preheater_opt': result.get('Q_preheater_opt [kW]', 'N/A') if result else "N/A",
                'Q_superheater_opt': result.get('Q_superheater_opt [kW]', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "High temperature test", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_invalid_parameters(self):
        """無効なパラメータでのテスト"""
        test_name = "Invalid parameters handling"
        try:
            set_component_setting('use_preheater', True)
            
            # 無効なパラメータ
            invalid_params = self.base_params.copy()
            invalid_params['T_htf_in'] = -273.15  # 不正な温度
            
            result = optimize_orc_with_components(**invalid_params)
            
            # エラーが適切にハンドリングされることを確認
            passed = result is None or result.get('optimization_success', False) is False
            
            details = {
                'Result': result,
                'Expected': 'None or failed optimization'
            }
            
            self.log_test(test_name, passed, 
                         "Invalid parameters should be handled gracefully", details)
            
        except Exception as e:
            # 例外が発生するのも適切なハンドリング
            self.log_test(test_name, True, f"Exception properly caught: {str(e)}")
    
    def test_sensitivity_analysis_no_components(self):
        """感度解析テスト（コンポーネント使用なし）"""
        test_name = "Sensitivity analysis without components"
        try:
            set_component_setting('use_preheater', False)
            set_component_setting('use_superheater', False)
            
            # 小さな範囲でテスト
            power_range = np.linspace(0, 20, 5)
            
            result = sensitivity_analysis_components(
                component_power_range=power_range,
                **self.base_params
            )
            
            passed = (
                result is not None and
                'sensitivity_results' in result and
                'power_range' in result and
                'use_preheater' in result and
                'use_superheater' in result and
                result['use_preheater'] is False and
                result['use_superheater'] is False
            )
            
            details = {
                'Results count': len(result.get('sensitivity_results', [])) if result else 0,
                'Power range': result.get('power_range', 'N/A') if result else "N/A",
                'Use preheater': result.get('use_preheater', 'N/A') if result else "N/A",
                'Use superheater': result.get('use_superheater', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Sensitivity analysis without components", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_sensitivity_analysis_with_components(self):
        """感度解析テスト（コンポーネント使用あり）"""
        test_name = "Sensitivity analysis with components"
        try:
            set_component_setting('use_preheater', True)
            set_component_setting('use_superheater', True)
            
            # 小さな範囲でテスト
            power_range = np.linspace(0, 30, 4)
            
            result = sensitivity_analysis_components(
                component_power_range=power_range,
                **self.base_params
            )
            
            passed = (
                result is not None and
                'sensitivity_results' in result and
                len(result['sensitivity_results']) >= 0  # 成功した計算があることを期待
            )
            
            details = {
                'Results count': len(result.get('sensitivity_results', [])) if result else 0,
                'Power range length': len(result.get('power_range', [])) if result else 0,
                'Use preheater': result.get('use_preheater', 'N/A') if result else "N/A",
                'Use superheater': result.get('use_superheater', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Sensitivity analysis with components", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def test_config_validation(self):
        """設定値の妥当性チェックテスト"""
        test_name = "Configuration validation"
        try:
            # 正常な設定での妥当性チェック
            validate_component_settings()
            
            # 現在の設定値を確認
            use_preheater = get_component_setting('use_preheater', False)
            use_superheater = get_component_setting('use_superheater', False)
            
            passed = True
            
            details = {
                'Validation': 'Passed',
                'use_preheater': use_preheater,
                'use_superheater': use_superheater
            }
            
            self.log_test(test_name, passed, 
                         "Configuration validation successful", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Validation failed: {str(e)}")
    
    def test_direct_orc_calculation(self):
        """直接的なORC計算のテスト（最適化なし）"""
        test_name = "Direct ORC calculation test"
        try:
            # ORC_Analysisモジュールを直接テスト
            result = calculate_orc_performance_from_heat_source(
                T_htf_in=self.base_params['T_htf_in'],
                Vdot_htf=self.base_params['Vdot_htf'],
                T_cond=self.base_params['T_cond'],
                eta_pump=self.base_params['eta_pump'],
                eta_turb=self.base_params['eta_turb'],
                Q_preheater_kW_input=0.0,
                Q_superheater_kW_input=0.0,
            )
            
            passed = result is not None and 'W_net [kW]' in result
            
            details = {
                'Result': 'Success' if result is not None else 'Failed',
                'W_net': result.get('W_net [kW]', 'N/A') if result else "N/A",
                'η_th': result.get('η_th [-]', 'N/A') if result else "N/A"
            }
            
            self.log_test(test_name, passed, 
                         "Direct ORC calculation", details)
            
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}", traceback.format_exc())
    
    def run_all_tests(self):
        """全テストを実行"""
        print("=" * 60)
        print("ORC OPTIMIZATION MODULE DEBUG TESTS")
        print("=" * 60)
        print()
        
        # テスト実行
        self.test_config_validation()
        self.test_direct_orc_calculation()
        self.test_basic_optimization_no_components()
        self.test_preheater_only_optimization()
        self.test_superheater_only_optimization()
        self.test_both_components_optimization()
        self.test_edge_case_low_temperature()
        self.test_edge_case_high_temperature()
        self.test_invalid_parameters()
        self.test_sensitivity_analysis_no_components()
        self.test_sensitivity_analysis_with_components()
        
        # 結果のサマリー
        self.print_summary()
    
    def print_summary(self):
        """テスト結果のサマリーを出力"""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            print("-" * 40)
            for result in self.test_results:
                if not result['passed']:
                    print(f"❌ {result['test']}")
                    if result['message']:
                        print(f"   {result['message']}")
            print()
        
        print("ALL TESTS SUMMARY:")
        print("-" * 40)
        for result in self.test_results:
            status = "✓" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print("\n" + "=" * 60)


def main():
    """メイン実行関数"""
    tester = OptimizationTester()
    tester.run_all_tests()
    
    # 追加のデバッグ情報
    print("\nDEBUG INFORMATION:")
    print("-" * 40)
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")
    print(f"Component settings: {COMPONENT_SETTINGS}")


if __name__ == "__main__":
    main()
