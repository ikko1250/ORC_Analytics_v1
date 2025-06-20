#!/usr/bin/env python3
"""
optimization.py の修正版をテストするスクリプト

安全制限が適用された最適化関数をテストします。
"""

import sys
import os
sys.path.append('/home/ubuntu/cur/program/seminar_fresh')

import numpy as np
from ORC_analysis.optimization import optimize_orc_with_components, sensitivity_analysis_components
from ORC_analysis.config import set_component_setting

def test_original_conditions():
    """元の条件でテスト"""
    print("=== テスト1: 元の条件 (安全制限適用) ===")
    
    # コンポーネントを有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', True)
    
    # テスト条件
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 1e-4  # 0.1 L/s
    T_cond = 313.15  # 40°C
    eta_pump = 0.75
    eta_turb = 0.85
    T_evap_out_target = 368.15  # 95°C
    
    try:
        result = optimize_orc_with_components(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            T_evap_out_target=T_evap_out_target,
            use_safety_limits=True
        )
        
        if result is not None:
            print("✅ 最適化成功!")
            print(f"最適予熱器電力: {result.get('Q_preheater_opt [kW]', 'N/A'):.3f} kW")
            print(f"最適過熱器電力: {result.get('Q_superheater_opt [kW]', 'N/A'):.3f} kW")
            
            w_net = result.get('W_net [kW]', 'N/A')
            if isinstance(w_net, (int, float)) and not np.isnan(w_net):
                print(f"正味出力: {w_net:.6f} kW")
            else:
                print(f"正味出力: {w_net}")
                
            m_orc = result.get('m_orc [kg/s]', 'N/A')
            if isinstance(m_orc, (int, float)):
                print(f"ORC質量流量: {m_orc:.6f} kg/s")
            else:
                print(f"ORC質量流量: {m_orc}")
                
            print(f"安全制限適用: {result.get('safety_limits_applied', 'N/A')}")
            
            preheater_limit = result.get('applied_preheater_limit [kW]', 'N/A')
            if isinstance(preheater_limit, (int, float)):
                print(f"適用予熱器制限: {preheater_limit:.3f} kW")
            else:
                print(f"適用予熱器制限: {preheater_limit}")
                
            superheater_limit = result.get('applied_superheater_limit [kW]', 'N/A')
            if isinstance(superheater_limit, (int, float)):
                print(f"適用過熱器制限: {superheater_limit:.3f} kW")
            else:
                print(f"適用過熱器制限: {superheater_limit}")
                
            print(f"最適化成功: {result.get('optimization_success', 'N/A')}")
        else:
            print("❌ 最適化失敗")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

def test_without_safety_limits():
    """安全制限なしでテスト（元の動作）"""
    print("\n=== テスト2: 安全制限なし (元の動作) ===")
    
    # コンポーネントを有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', True)
    
    # テスト条件
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 1e-4  # 0.1 L/s
    T_cond = 313.15  # 40°C
    eta_pump = 0.75
    eta_turb = 0.85
    T_evap_out_target = 368.15  # 95°C
    
    try:
        result = optimize_orc_with_components(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            T_evap_out_target=T_evap_out_target,
            use_safety_limits=False  # 安全制限なし
        )
        
        if result is not None:
            print("✅ 最適化成功!")
            print(f"最適予熱器電力: {result.get('Q_preheater_opt [kW]', 'N/A'):.3f} kW")
            print(f"最適過熱器電力: {result.get('Q_superheater_opt [kW]', 'N/A'):.3f} kW")
            print(f"正味出力: {result.get('W_net [kW]', 'N/A'):.6f} kW")
            print(f"安全制限適用: {result.get('safety_limits_applied', 'N/A')}")
        else:
            print("❌ 最適化失敗")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")

def test_sensitivity_analysis():
    """感度解析テスト"""
    print("\n=== テスト3: 感度解析 (安全制限適用) ===")
    
    # 予熱器のみ有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    
    # テスト条件
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 1e-4  # 0.1 L/s
    T_cond = 313.15  # 40°C
    eta_pump = 0.75
    eta_turb = 0.85
    T_evap_out_target = 368.15  # 95°C
    
    # 小さい範囲でテスト
    power_range = np.linspace(0, 10, 6)  # 0-10kW
    
    try:
        result = sensitivity_analysis_components(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            T_evap_out_target=T_evap_out_target,
            component_power_range=power_range,
            use_safety_limits=True
        )
        
        print(f"✅ 感度解析成功!")
        print(f"安全制限適用: {result.get('safety_limits_applied', 'N/A')}")
        print(f"最大安全電力: {result.get('max_safe_power', 'N/A'):.3f} kW")
        print(f"結果数: {len(result.get('sensitivity_results', []))}")
        
        # 一部の結果を表示
        results = result.get('sensitivity_results', [])
        if results:
            print("\n電力 [kW] | 正味出力 [kW]")
            print("-" * 25)
            for i, res in enumerate(results[:5]):  # 最初の5つだけ表示
                power = res.get('Q_preheater_test [kW]', 0)
                w_net = res.get('W_net [kW]', 0)
                print(f"{power:8.2f} | {w_net:12.6f}")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

def test_large_flow_rate():
    """大きい流量でテスト（安全制限の影響が小さい場合）"""
    print("\n=== テスト4: 大きい流量 (安全制限の影響確認) ===")
    
    # コンポーネントを有効化
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', True)
    
    # より大きい流量
    T_htf_in = 373.15  # 100°C
    Vdot_htf = 1e-3  # 1 L/s (10倍)
    T_cond = 313.15  # 40°C
    eta_pump = 0.75
    eta_turb = 0.85
    T_evap_out_target = 368.15  # 95°C
    
    try:
        result = optimize_orc_with_components(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            T_evap_out_target=T_evap_out_target,
            use_safety_limits=True
        )
        
        if result is not None:
            print("✅ 最適化成功!")
            
            m_orc = result.get('m_orc [kg/s]', 'N/A')
            if isinstance(m_orc, (int, float)):
                print(f"ORC質量流量: {m_orc:.6f} kg/s")
            else:
                print(f"ORC質量流量: {m_orc}")
                
            preheater_limit = result.get('applied_preheater_limit [kW]', 'N/A')
            if isinstance(preheater_limit, (int, float)):
                print(f"適用予熱器制限: {preheater_limit:.3f} kW")
            else:
                print(f"適用予熱器制限: {preheater_limit}")
                
            superheater_limit = result.get('applied_superheater_limit [kW]', 'N/A')
            if isinstance(superheater_limit, (int, float)):
                print(f"適用過熱器制限: {superheater_limit:.3f} kW")
            else:
                print(f"適用過熱器制限: {superheater_limit}")
                
            print(f"最適予熱器電力: {result.get('Q_preheater_opt [kW]', 'N/A'):.3f} kW")
            print(f"最適過熱器電力: {result.get('Q_superheater_opt [kW]', 'N/A'):.3f} kW")
            
            w_net = result.get('W_net [kW]', 'N/A')
            if isinstance(w_net, (int, float)) and not np.isnan(w_net):
                print(f"正味出力: {w_net:.6f} kW")
            else:
                print(f"正味出力: {w_net}")
        else:
            print("❌ 最適化失敗")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    print("ORC最適化モジュール修正版テスト開始")
    print("=" * 50)
    
    test_original_conditions()
    test_without_safety_limits()
    test_sensitivity_analysis()
    test_large_flow_rate()
    
    print("\n" + "=" * 50)
    print("テスト完了")
