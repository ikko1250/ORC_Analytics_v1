#!/usr/bin/env python3
"""optimization.py デバッグ用テストスクリプト"""

import sys
import os
import traceback
import numpy as np

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("=== ORC Optimization Debug Test ===")
print(f"Project root: {project_root}")
print(f"Python version: {sys.version}")
print()

# Step 1: インポートテスト
print("Step 1: Testing imports...")
try:
    from ORC_analysis.config import set_component_setting, get_component_setting
    print("✓ config module imported successfully")
except ImportError as e:
    print(f"❌ config import failed: {e}")
    traceback.print_exc()

try:
    from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
    print("✓ ORC_Analysis module imported successfully")
except ImportError as e:
    print(f"❌ ORC_Analysis import failed: {e}")
    traceback.print_exc()

try:
    from ORC_analysis.optimization import optimize_orc_with_components, sensitivity_analysis_components
    print("✓ optimization module imported successfully")
except ImportError as e:
    print(f"❌ optimization import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print()

# Step 2: 基本設定テスト
print("Step 2: Testing basic configuration...")
try:
    # 設定を無効にする
    set_component_setting('use_preheater', False)
    set_component_setting('use_superheater', False)
    
    use_preheater = get_component_setting('use_preheater')
    use_superheater = get_component_setting('use_superheater')
    
    print(f"✓ use_preheater: {use_preheater}")
    print(f"✓ use_superheater: {use_superheater}")
except Exception as e:
    print(f"❌ Configuration test failed: {e}")
    traceback.print_exc()

print()

# Step 3: 基本的なORC計算テスト
print("Step 3: Testing basic ORC calculation...")
try:
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=373.15,  # 100°C
        Vdot_htf=0.01,    # m³/s
        T_cond=305.15,    # 32°C
        eta_pump=0.75,
        eta_turb=0.80,
        Q_preheater_kW_input=0.0,
        Q_superheater_kW_input=0.0,
    )
    
    if result is not None:
        print(f"✓ ORC calculation successful")
        print(f"  W_net: {result.get('W_net [kW]', 'N/A')} kW")
        print(f"  η_th: {result.get('η_th [-]', 'N/A')}")
    else:
        print("❌ ORC calculation returned None")
        
except Exception as e:
    print(f"❌ ORC calculation failed: {e}")
    traceback.print_exc()

print()

# Step 4: 最適化テスト（コンポーネントなし）
print("Step 4: Testing optimization without components...")
try:
    set_component_setting('use_preheater', False)
    set_component_setting('use_superheater', False)
    
    result = optimize_orc_with_components(
        T_htf_in=373.15,  # 100°C
        Vdot_htf=0.01,    # m³/s
        T_cond=305.15,    # 32°C
        eta_pump=0.75,
        eta_turb=0.80,
        T_evap_out_target=363.15,  # 90°C (この値は現在使われていない)
    )
    
    if result is not None:
        print(f"✓ Optimization successful")
        print(f"  Q_preheater_opt: {result.get('Q_preheater_opt [kW]', 'N/A')} kW")
        print(f"  Q_superheater_opt: {result.get('Q_superheater_opt [kW]', 'N/A')} kW")
        print(f"  W_net: {result.get('W_net [kW]', 'N/A')} kW")
        print(f"  optimization_success: {result.get('optimization_success', 'N/A')}")
    else:
        print("❌ Optimization returned None")
        
except Exception as e:
    print(f"❌ Optimization failed: {e}")
    traceback.print_exc()

print()

# Step 5: 最適化テスト（予熱器のみ）
print("Step 5: Testing optimization with preheater only...")
try:
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    
    result = optimize_orc_with_components(
        T_htf_in=373.15,  # 100°C
        Vdot_htf=0.01,    # m³/s
        T_cond=305.15,    # 32°C
        eta_pump=0.75,
        eta_turb=0.80,
        T_evap_out_target=363.15,  # 90°C
        max_preheater_power=50.0,
    )
    
    if result is not None:
        print(f"✓ Optimization with preheater successful")
        print(f"  Q_preheater_opt: {result.get('Q_preheater_opt [kW]', 'N/A')} kW")
        print(f"  Q_superheater_opt: {result.get('Q_superheater_opt [kW]', 'N/A')} kW")
        print(f"  W_net: {result.get('W_net [kW]', 'N/A')} kW")
        print(f"  optimization_success: {result.get('optimization_success', 'N/A')}")
    else:
        print("❌ Optimization with preheater returned None")
        
except Exception as e:
    print(f"❌ Optimization with preheater failed: {e}")
    traceback.print_exc()

print()

# Step 6: 感度解析テスト（簡単版）
print("Step 6: Testing sensitivity analysis...")
try:
    set_component_setting('use_preheater', True)
    set_component_setting('use_superheater', False)
    
    # 小さな範囲でテスト
    power_range = np.array([0, 10, 20])
    
    result = sensitivity_analysis_components(
        T_htf_in=373.15,
        Vdot_htf=0.01,
        T_cond=305.15,
        eta_pump=0.75,
        eta_turb=0.80,
        T_evap_out_target=363.15,
        component_power_range=power_range,
    )
    
    if result is not None:
        print(f"✓ Sensitivity analysis successful")
        print(f"  Results count: {len(result.get('sensitivity_results', []))}")
        print(f"  Power range: {result.get('power_range', 'N/A')}")
        print(f"  use_preheater: {result.get('use_preheater', 'N/A')}")
        print(f"  use_superheater: {result.get('use_superheater', 'N/A')}")
    else:
        print("❌ Sensitivity analysis returned None")
        
except Exception as e:
    print(f"❌ Sensitivity analysis failed: {e}")
    traceback.print_exc()

print()
print("=== Debug Test Complete ===")
