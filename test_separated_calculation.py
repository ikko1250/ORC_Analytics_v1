#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the improved ORC analysis with separated evaporator and superheater calculations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ORC_analysis'))

from ORC_analysis.config import set_component_setting
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source
from ORC_analysis.separated_evap_superheat import calculate_separated_evap_superheat
import pandas as pd
import numpy as np

def test_separated_calculation():
    """Test separated evaporator+superheater calculation vs integrated calculation."""
    
    print("=== 分離計算方式テスト ===")
    print()
    
    # Test conditions
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.05    # m³/s
    T_cond = 308.15    # 35°C
    eta_pump = 0.75
    eta_turb = 0.80
    superheat_C = 10.0
    pinch_delta_K = 10.0
    
    # Enable separated calculation
    set_component_setting('use_separated_evap_superheat', True)
    
    print("Test Conditions:")
    print(f"  Heat source inlet: {T_htf_in-273.15:.1f}°C")
    print(f"  Heat source flow: {Vdot_htf:.3f} m³/s")
    print(f"  Condensation temp: {T_cond-273.15:.1f}°C")
    print(f"  Superheat: {superheat_C:.1f}°C")
    print(f"  Pinch point: {pinch_delta_K:.1f} K")
    print()
    
    # Run ORC calculation with separated analysis
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        superheat_C=superheat_C,
        pinch_delta_K=pinch_delta_K,
        heat_source_type="liquid",
        fluid_htf="Water"
    )
    
    if result is None:
        print("ERROR: ORC calculation failed!")
        return
    
    print("=== Basic ORC Results ===")
    print(f"Net power: {result['W_net [kW]']:.1f} kW")
    print(f"Thermal efficiency: {result['η_th [-]']:.3f}")
    print(f"Exergetic efficiency: {result['ε_ex [-]']:.3f}")
    print(f"Mass flow rate: {result['m_orc [kg/s]']:.2f} kg/s")
    print()
    
    # Check if separated analysis was performed
    if 'separated_analysis' in result:
        print("=== Separated Analysis Results ===")
        
        sep_analysis = result['separated_analysis']
        
        # Heat distribution
        heat_dist = sep_analysis['Heat_Distribution']
        print("Heat Distribution:")
        print(f"  Evaporator: {heat_dist['Q_evap [kW]']:.1f} kW ({heat_dist['Q_evap_ratio [%]']:.1f}%)")
        print(f"  Superheater: {heat_dist['Q_superheat [kW]']:.1f} kW ({heat_dist['Q_superheat_ratio [%]']:.1f}%)")
        print()
        
        # LMTD analysis
        lmtd_analysis = sep_analysis['LMTD_Analysis']
        print("LMTD Analysis:")
        print(f"  Evaporator LMTD: {lmtd_analysis['dT_lm_evap [K]']:.1f} K")
        print(f"  Superheater LMTD: {lmtd_analysis['dT_lm_superheat [K]']:.1f} K")
        print(f"  Area-weighted average: {lmtd_analysis['dT_lm_area_weighted [K]']:.1f} K")
        print(f"  Combined calculation: {lmtd_analysis['dT_lm_combined [K]']:.1f} K")
        print(f"  LMTD Error: {lmtd_analysis['LMTD_error [%]']:.1f}%")
        print()
        
        # Temperature analysis
        temp_analysis = sep_analysis['Temperature_Analysis']
        print("Temperature Analysis:")
        print(f"  Evaporator avg temp: {temp_analysis['T_hot_avg_evap [K]']-273.15:.1f}°C")
        print(f"  Superheater avg temp: {temp_analysis['T_hot_avg_superheat [K]']-273.15:.1f}°C")
        print(f"  Energy-weighted avg: {temp_analysis['T_hot_avg_energy_weighted [K]']-273.15:.1f}°C")
        print(f"  Combined calculation: {temp_analysis['T_hot_avg_combined [K]']-273.15:.1f}°C")
        print(f"  Temperature Error: {temp_analysis['Temp_error [%]']:.1f}%")
        print()
        
        # Exergy analysis
        exergy_analysis = sep_analysis['Exergy_Analysis']
        print("Exergy Analysis:")
        print(f"  Evaporator exergy: {exergy_analysis['E_heat_evap [kW]']:.1f} kW")
        print(f"  Superheater exergy: {exergy_analysis['E_heat_superheat [kW]']:.1f} kW")
        print(f"  Separated total: {exergy_analysis['E_heat_separated_total [kW]']:.1f} kW")
        print(f"  Combined calculation: {exergy_analysis['E_heat_combined [kW]']:.1f} kW")
        print(f"  Exergy Error: {exergy_analysis['Exergy_error [%]']:.1f}%")
        print()
        
        # Component details
        if 'evap_separated' in result:
            evap_comp = result['evap_separated']
            super_comp = result['superheat_separated']
            
            print("=== Component Details ===")
            print("Evaporator:")
            print(f"  Heat transfer: {evap_comp['Q [kW]']:.1f} kW")
            print(f"  Exergy efficiency: {evap_comp['ε [-]']:.3f}")
            print(f"  Exergy destruction: {evap_comp['E_dest [kW]']:.1f} kW")
            print(f"  LMTD valid: {evap_comp['LMTD_valid']}")
            print()
            
            print("Superheater:")
            print(f"  Heat transfer: {super_comp['Q [kW]']:.1f} kW")
            print(f"  Exergy efficiency: {super_comp['ε [-]']:.3f}")
            print(f"  Exergy destruction: {super_comp['E_dest [kW]']:.1f} kW")
            print(f"  LMTD valid: {super_comp['LMTD_valid']}")
            print()
        
        # Assessment
        print("=== Assessment ===")
        lmtd_error = lmtd_analysis['LMTD_error [%]']
        temp_error = temp_analysis['Temp_error [%]']
        exergy_error = exergy_analysis['Exergy_error [%]']
        
        if not np.isnan(lmtd_error) and abs(lmtd_error) > 10:
            print(f"⚠️  LARGE LMTD ERROR: {lmtd_error:.1f}% - Heat exchanger sizing will be inaccurate")
        elif not np.isnan(lmtd_error) and abs(lmtd_error) > 5:
            print(f"⚠️  Moderate LMTD error: {lmtd_error:.1f}% - Consider separated calculation")
        else:
            print(f"✅ LMTD error acceptable: {lmtd_error:.1f}%")
            
        if not np.isnan(temp_error) and abs(temp_error) > 5:
            print(f"⚠️  Temperature error: {temp_error:.1f}% - Exergy analysis affected")
        else:
            print(f"✅ Temperature error acceptable: {temp_error:.1f}%")
            
        if not np.isnan(exergy_error) and abs(exergy_error) > 5:
            print(f"⚠️  Exergy error: {exergy_error:.1f}% - Performance assessment affected")
        else:
            print(f"✅ Exergy error acceptable: {exergy_error:.1f}%")
            
    else:
        print("❌ Separated analysis was not performed (check configuration)")
    
    # Reset setting
    set_component_setting('use_separated_evap_superheat', False)


def test_superheat_sensitivity():
    """Test how calculation errors vary with superheat degree."""
    
    print("\n" + "="*60)
    print("=== Superheat Sensitivity Analysis ===")
    
    superheats = [5, 10, 15, 20, 25, 30]
    T_htf_in = 473.15  # 200°C
    Vdot_htf = 0.05
    T_cond = 308.15
    
    # Enable separated calculation
    set_component_setting('use_separated_evap_superheat', True)
    
    print(f"{'Superheat':<10} {'LMTD Err':<10} {'Temp Err':<10} {'Exergy Err':<12} {'Q_evap%':<8} {'Q_super%':<8}")
    print("-" * 60)
    
    for superheat in superheats:
        result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_in,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=0.75,
            eta_turb=0.80,
            superheat_C=superheat,
            pinch_delta_K=10.0,
            heat_source_type="liquid",
            fluid_htf="Water"
        )
        
        if result and 'separated_analysis' in result:
            sep = result['separated_analysis']
            lmtd_err = sep['LMTD_Analysis']['LMTD_error [%]']
            temp_err = sep['Temperature_Analysis']['Temp_error [%]']
            exergy_err = sep['Exergy_Analysis']['Exergy_error [%]']
            q_evap_pct = sep['Heat_Distribution']['Q_evap_ratio [%]']
            q_super_pct = sep['Heat_Distribution']['Q_superheat_ratio [%]']
            
            print(f"{superheat:<10.0f} {lmtd_err:<10.1f} {temp_err:<10.1f} {exergy_err:<12.1f} {q_evap_pct:<8.1f} {q_super_pct:<8.1f}")
        else:
            print(f"{superheat:<10.0f} {'Failed':<10} {'Failed':<10} {'Failed':<12} {'Failed':<8} {'Failed':<8}")
    
    # Reset setting
    set_component_setting('use_separated_evap_superheat', False)


if __name__ == "__main__":
    test_separated_calculation()
    test_superheat_sensitivity()
