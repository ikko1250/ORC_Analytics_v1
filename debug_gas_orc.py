#!/usr/bin/env python3
"""
Debug script to identify why gas heat source ORC calculation returns NaN
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source, DEFAULT_FLUID

# Test single point with gas heat source
gas_composition = {
    "CO2": 0.11,
    "H2O": 0.20,
    "N2": 0.69
}

# Test conditions
T_htf_in = 473.15  # 200°C
Vdot_htf = 1000 / 3600  # 1000 m³/h to m³/s
T_cond = 305.0  # 32°C
eta_pump = 0.40
eta_turb = 0.80
fluid_orc = "Toluene"  # 高温ガス熱源用
superheat_C = 8.0
pinch_delta_K = 10.0

# Gas parameters
P_gas = 101325
mass_flow_mode = False
T_gas_out_offset_K = 20
T_gas_out_min = T_cond + T_gas_out_offset_K

print("=== ORC Gas Heat Source Debug ===")
print(f"Heat source temperature: {T_htf_in - 273.15:.1f}°C")
print(f"Volume flow rate: {Vdot_htf * 3600:.1f} m³/h")
print(f"ORC working fluid: {fluid_orc}")
print(f"Gas composition: {gas_composition}")
print(f"Gas out min temperature: {T_gas_out_min - 273.15:.1f}°C")
print()

# Calculate evaporator saturation temperature
T_sat_evap = T_htf_in - pinch_delta_K - superheat_C
print(f"Calculated saturation temperature: {T_sat_evap - 273.15:.1f}°C")

# Check critical temperature
import CoolProp.CoolProp as CP
try:
    Tcrit = CP.PropsSI("Tcrit", fluid_orc)
    print(f"Critical temperature of {fluid_orc}: {Tcrit - 273.15:.1f}°C")
    
    if T_sat_evap >= Tcrit:
        print("ERROR: Saturation temperature exceeds critical temperature!")
    elif T_sat_evap <= T_cond + 1.0:
        print("ERROR: Saturation temperature too close to condensation temperature!")
    else:
        print("Temperature check: OK")
except Exception as e:
    print(f"Error getting critical temperature: {e}")

print()

# Test the calculation
try:
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=T_htf_in,
        Vdot_htf=Vdot_htf,
        T_cond=T_cond,
        eta_pump=eta_pump,
        eta_turb=eta_turb,
        fluid_orc=fluid_orc,
        superheat_C=superheat_C,
        pinch_delta_K=pinch_delta_K,
        heat_source_type="gas",
        gas_composition=gas_composition,
        P_gas=P_gas,
        mass_flow_mode=mass_flow_mode,
        T_gas_out_min=T_gas_out_min
    )
    
    if result is None:
        print("Result: None (calculation failed)")
    else:
        print("Result: Success")
        for key, value in result.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
        
except Exception as e:
    print(f"Calculation error: {e}")
    import traceback
    traceback.print_exc()

# Test with different temperatures
print("\n=== Testing different heat source temperatures ===")
test_temps = [300, 350, 400, 450, 500]  # °C

for temp_c in test_temps:
    T_test = temp_c + 273.15
    T_sat_test = T_test - pinch_delta_K - superheat_C
    
    print(f"\nTesting {temp_c}°C heat source:")
    print(f"  Calculated T_sat_evap: {T_sat_test - 273.15:.1f}°C")
    
    # Quick check
    if T_sat_test >= Tcrit:
        print(f"  SKIP: T_sat exceeds T_crit ({Tcrit - 273.15:.1f}°C)")
        continue
    elif T_sat_test <= T_cond + 1.0:
        print(f"  SKIP: T_sat too low (< {T_cond + 1.0 - 273.15:.1f}°C)")
        continue
    
    try:
        result = calculate_orc_performance_from_heat_source(
            T_htf_in=T_test,
            Vdot_htf=Vdot_htf,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid_orc=fluid_orc,
            superheat_C=superheat_C,
            pinch_delta_K=pinch_delta_K,
            heat_source_type="gas",
            gas_composition=gas_composition,
            P_gas=P_gas,
            mass_flow_mode=mass_flow_mode,
            T_gas_out_min=T_cond + T_gas_out_offset_K
        )
        
        if result is None:
            print("  Result: None")
        else:
            print(f"  Net power: {result.get('W_net [kW]', 'N/A'):.1f} kW")
            print(f"  Efficiency: {result.get('η_th [-]', 'N/A'):.1%}")
        
    except Exception as e:
        print(f"  Error: {e}")