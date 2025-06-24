#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script for ORC preheater and superheater functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ORC_analysis'))

from ORC_analysis.ORC_Analysis import calculate_orc_performance
import pandas as pd
import numpy as np

def test_preheater_functionality():
    """Test preheater component functionality"""
    print("=" * 60)
    print("PREHEATER FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Base case parameters
    P_evap = 10.0e5  # Pa
    T_cond = 308.15  # K
    T_turb_in = 420.0  # K
    eta_pump = 0.75
    eta_turb = 0.80
    m_orc = 5.0  # kg/s
    
    # Test cases
    test_cases = [
        {"Q_preheater_kW": 0.0, "name": "No preheater"},
        {"Q_preheater_kW": 50.0, "name": "50kW preheater"},
        {"Q_preheater_kW": 100.0, "name": "100kW preheater"},
        {"Q_preheater_kW": 200.0, "name": "200kW preheater (high - may hit constraints)"},
    ]
    
    results = []
    
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print("-" * 40)
        
        try:
            psi_df, comp_df, cycle_kpi = calculate_orc_performance(
                P_evap=P_evap,
                T_turb_in=T_turb_in,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                m_orc=m_orc,
                Q_preheater_kW=case["Q_preheater_kW"]
            )
            
            # Extract key temperatures
            T2 = psi_df.loc["T [K]", "2"]  # After pump
            T2b = psi_df.loc["T [K]", "2b"]  # After preheater
            
            # Calculate temperature rise
            delta_T_preheater = T2b - T2
            
            print(f"  Input preheater heat: {case['Q_preheater_kW']:.1f} kW")
            print(f"  Temperature after pump (T2): {T2:.2f} K")
            print(f"  Temperature after preheater (T2b): {T2b:.2f} K")
            print(f"  Temperature rise: {delta_T_preheater:.2f} K")
            
            # Check if preheater is in the component results
            if "Preheater" in comp_df.index:
                Q_preheater_actual = comp_df.loc["Preheater", "Q [kW]"]
                constraint_active = comp_df.loc["Preheater", "constraint_active"]
                print(f"  Actual preheater heat: {Q_preheater_actual:.1f} kW")
                print(f"  Constraint active: {constraint_active}")
            else:
                print("  No preheater component found in results")
            
            # Check cycle performance
            W_net = cycle_kpi["W_net [kW]"]
            eta_th = cycle_kpi["η_th [-]"]
            print(f"  Net power: {W_net:.2f} kW")
            print(f"  Thermal efficiency: {eta_th:.4f}")
            
            # Store results
            results.append({
                "case": case["name"],
                "Q_preheater_input": case["Q_preheater_kW"],
                "T2": T2,
                "T2b": T2b,
                "delta_T": delta_T_preheater,
                "W_net": W_net,
                "eta_th": eta_th,
                "success": True
            })
            
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            results.append({
                "case": case["name"],
                "Q_preheater_input": case["Q_preheater_kW"],
                "error": str(e),
                "success": False
            })
    
    # Summary table
    print("\n" + "=" * 60)
    print("PREHEATER TEST SUMMARY")
    print("=" * 60)
    
    success_results = [r for r in results if r["success"]]
    if success_results:
        df = pd.DataFrame(success_results)
        print(df[["case", "Q_preheater_input", "T2", "T2b", "delta_T", "W_net", "eta_th"]].to_string(index=False))
    
    # Print errors if any
    error_results = [r for r in results if not r["success"]]
    if error_results:
        print("\nERROR CASES:")
        for r in error_results:
            print(f"  {r['case']}: {r['error']}")
    
    return results

def test_superheater_functionality():
    """Test superheater component functionality"""
    print("\n" + "=" * 60)
    print("SUPERHEATER FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Base case parameters
    P_evap = 10.0e5  # Pa
    T_cond = 308.15  # K
    T_turb_in = 420.0  # K
    eta_pump = 0.75
    eta_turb = 0.80
    m_orc = 5.0  # kg/s
    
    # Test cases
    test_cases = [
        {"Q_superheater_kW": 0.0, "name": "No superheater"},
        {"Q_superheater_kW": 50.0, "name": "50kW superheater"},
        {"Q_superheater_kW": 100.0, "name": "100kW superheater"},
        {"Q_superheater_kW": 200.0, "name": "200kW superheater (high - may hit constraints)"},
    ]
    
    results = []
    
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print("-" * 40)
        
        try:
            psi_df, comp_df, cycle_kpi = calculate_orc_performance(
                P_evap=P_evap,
                T_turb_in=T_turb_in,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                m_orc=m_orc,
                Q_superheater_kW=case["Q_superheater_kW"]
            )
            
            # Extract key temperatures
            T3 = psi_df.loc["T [K]", "3"]  # After evaporator
            T3b = psi_df.loc["T [K]", "3b"]  # After superheater
            
            # Calculate temperature rise
            delta_T_superheater = T3b - T3
            
            print(f"  Input superheater heat: {case['Q_superheater_kW']:.1f} kW")
            print(f"  Temperature after evaporator (T3): {T3:.2f} K")
            print(f"  Temperature after superheater (T3b): {T3b:.2f} K")
            print(f"  Temperature rise: {delta_T_superheater:.2f} K")
            
            # Check if superheater is in the component results
            if "Superheater" in comp_df.index:
                Q_superheater_actual = comp_df.loc["Superheater", "Q [kW]"]
                constraint_active = comp_df.loc["Superheater", "constraint_active"]
                print(f"  Actual superheater heat: {Q_superheater_actual:.1f} kW")
                print(f"  Constraint active: {constraint_active}")
            else:
                print("  No superheater component found in results")
            
            # Check cycle performance
            W_net = cycle_kpi["W_net [kW]"]
            eta_th = cycle_kpi["η_th [-]"]
            print(f"  Net power: {W_net:.2f} kW")
            print(f"  Thermal efficiency: {eta_th:.4f}")
            
            # Store results
            results.append({
                "case": case["name"],
                "Q_superheater_input": case["Q_superheater_kW"],
                "T3": T3,
                "T3b": T3b,
                "delta_T": delta_T_superheater,
                "W_net": W_net,
                "eta_th": eta_th,
                "success": True
            })
            
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            results.append({
                "case": case["name"],
                "Q_superheater_input": case["Q_superheater_kW"],
                "error": str(e),
                "success": False
            })
    
    # Summary table
    print("\n" + "=" * 60)
    print("SUPERHEATER TEST SUMMARY")
    print("=" * 60)
    
    success_results = [r for r in results if r["success"]]
    if success_results:
        df = pd.DataFrame(success_results)
        print(df[["case", "Q_superheater_input", "T3", "T3b", "delta_T", "W_net", "eta_th"]].to_string(index=False))
    
    # Print errors if any
    error_results = [r for r in results if not r["success"]]
    if error_results:
        print("\nERROR CASES:")
        for r in error_results:
            print(f"  {r['case']}: {r['error']}")
    
    return results

def test_combined_functionality():
    """Test preheater and superheater working together"""
    print("\n" + "=" * 60)
    print("COMBINED PREHEATER + SUPERHEATER TEST")
    print("=" * 60)
    
    # Base case parameters
    P_evap = 10.0e5  # Pa
    T_cond = 308.15  # K
    T_turb_in = 420.0  # K
    eta_pump = 0.75
    eta_turb = 0.80
    m_orc = 5.0  # kg/s
    
    # Test cases
    test_cases = [
        {"Q_preheater_kW": 0.0, "Q_superheater_kW": 0.0, "name": "No preheater/superheater"},
        {"Q_preheater_kW": 50.0, "Q_superheater_kW": 50.0, "name": "50kW each"},
        {"Q_preheater_kW": 100.0, "Q_superheater_kW": 100.0, "name": "100kW each"},
        {"Q_preheater_kW": 50.0, "Q_superheater_kW": 100.0, "name": "50kW preheater + 100kW superheater"},
    ]
    
    results = []
    
    for case in test_cases:
        print(f"\nTesting: {case['name']}")
        print("-" * 40)
        
        try:
            psi_df, comp_df, cycle_kpi = calculate_orc_performance(
                P_evap=P_evap,
                T_turb_in=T_turb_in,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_turb=eta_turb,
                m_orc=m_orc,
                Q_preheater_kW=case["Q_preheater_kW"],
                Q_superheater_kW=case["Q_superheater_kW"]
            )
            
            # Extract key temperatures
            T2 = psi_df.loc["T [K]", "2"]   # After pump
            T2b = psi_df.loc["T [K]", "2b"] # After preheater
            T3 = psi_df.loc["T [K]", "3"]   # After evaporator
            T3b = psi_df.loc["T [K]", "3b"] # After superheater
            
            print(f"  Input preheater heat: {case['Q_preheater_kW']:.1f} kW")
            print(f"  Input superheater heat: {case['Q_superheater_kW']:.1f} kW")
            print(f"  T2 (after pump): {T2:.2f} K")
            print(f"  T2b (after preheater): {T2b:.2f} K")
            print(f"  T3 (after evaporator): {T3:.2f} K")
            print(f"  T3b (after superheater): {T3b:.2f} K")
            
            # Check cycle performance
            W_net = cycle_kpi["W_net [kW]"]
            eta_th = cycle_kpi["η_th [-]"]
            Q_in = cycle_kpi["Q_in [kW]"]
            print(f"  Net power: {W_net:.2f} kW")
            print(f"  Total heat input: {Q_in:.2f} kW")
            print(f"  Thermal efficiency: {eta_th:.4f}")
            
            # Store results
            results.append({
                "case": case["name"],
                "Q_preheater": case["Q_preheater_kW"],
                "Q_superheater": case["Q_superheater_kW"],
                "T2": T2,
                "T2b": T2b,
                "T3": T3,
                "T3b": T3b,
                "W_net": W_net,
                "Q_in": Q_in,
                "eta_th": eta_th,
                "success": True
            })
            
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            results.append({
                "case": case["name"],
                "error": str(e),
                "success": False
            })
    
    # Summary table
    print("\n" + "=" * 60)
    print("COMBINED TEST SUMMARY")
    print("=" * 60)
    
    success_results = [r for r in results if r["success"]]
    if success_results:
        df = pd.DataFrame(success_results)
        print(df[["case", "Q_preheater", "Q_superheater", "W_net", "Q_in", "eta_th"]].to_string(index=False))
    
    return results

if __name__ == "__main__":
    print("ORC PREHEATER/SUPERHEATER DEBUG TEST")
    print("=" * 60)
    
    # Run all tests
    preheater_results = test_preheater_functionality()
    superheater_results = test_superheater_functionality()
    combined_results = test_combined_functionality()
    
    print("\n" + "=" * 60)
    print("OVERALL TEST RESULTS")
    print("=" * 60)
    
    preheater_success = sum(1 for r in preheater_results if r["success"])
    superheater_success = sum(1 for r in superheater_results if r["success"])
    combined_success = sum(1 for r in combined_results if r["success"])
    
    print(f"Preheater tests: {preheater_success}/{len(preheater_results)} passed")
    print(f"Superheater tests: {superheater_success}/{len(superheater_results)} passed")
    print(f"Combined tests: {combined_success}/{len(combined_results)} passed")
    
    if preheater_success == len(preheater_results) and \
       superheater_success == len(superheater_results) and \
       combined_success == len(combined_results):
        print("\n✅ ALL TESTS PASSED - Preheater and Superheater functionality is working correctly!")
    else:
        print("\n❌ Some tests failed - Check the error messages above")