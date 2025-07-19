#!/usr/bin/env python3
"""
Test script to evaluate Cantera for gas mixture property calculations
as an alternative to CoolProp for problematic gas compositions.
"""
import sys

def test_cantera_availability():
    """Check if Cantera is available and test basic functionality."""
    try:
        import cantera as ct
        print(f"Cantera version: {ct.__version__}")
        return True
    except ImportError:
        print("Cantera is not installed. To install:")
        print("conda install -c cantera cantera")
        print("or")
        print("pip install cantera")
        return False

def test_cantera_gas_properties():
    """Test Cantera for gas mixture property calculations."""
    import cantera as ct
    import numpy as np
    
    # Test the problematic composition from the original error
    gas_composition = {
        "CO2": 0.11,
        "H2O": 0.20,
        "N2": 0.69
    }
    
    # Test conditions that failed with CoolProp
    test_conditions = [
        {"T": 444.867, "P": 101325},  # Original failing condition
        {"T": 400.0, "P": 101325},    # Lower temperature
        {"T": 500.0, "P": 101325},    # Higher temperature
    ]
    
    print("\n" + "=" * 60)
    print("Testing Cantera gas mixture property calculations...")
    
    try:
        # Try to use built-in mechanisms first
        try:
            gas = ct.Solution('gri30.yaml')  # GRI-Mech 3.0 - comprehensive combustion mechanism
            print("Using GRI-Mech 3.0 mechanism (comprehensive)")
        except:
            try:
                gas = ct.Solution('air.yaml')  # Air mechanism
                print("Using air.yaml mechanism (limited species)")
            except:
                print("Built-in mechanisms not available, creating custom mechanism")
                # Create a simple custom mechanism string
                mechanism_string = """
phases:
- name: gas
  thermo: ideal-gas
  elements: [C, H, O, N]
  species: [CO2, H2O, N2]
  state:
    T: 300.0
    P: 1 atm

species:
- name: CO2
  composition: {C: 1, O: 2}
  thermo:
    model: NASA7
    temperature-ranges: [200.0, 1000.0, 3500.0]
    data:
    - [2.35677352, 8.98459677e-03, -7.12356269e-06, 2.45919022e-09, -1.43699548e-13,
       -4.83719697e+04, 9.90105222]
    - [3.85746029, 4.41437026e-03, -2.21481404e-06, 5.23490188e-10, -4.72084164e-14,
       -4.8759166e+04, 2.27163806]
- name: H2O
  composition: {H: 2, O: 1}
  thermo:
    model: NASA7
    temperature-ranges: [200.0, 1000.0, 3500.0]
    data:
    - [4.19864056, -2.0364341e-03, 6.52040211e-06, -5.48797062e-09, 1.77197817e-12,
       -3.02937267e+04, -0.849032208]
    - [3.03399249, 2.17691804e-03, -1.64072518e-07, -9.7041987e-11, 1.68200992e-14,
       -3.00042971e+04, 4.9667701]
- name: N2
  composition: {N: 2}
  thermo:
    model: NASA7
    temperature-ranges: [300.0, 1000.0, 5000.0]
    data:
    - [3.298677, 1.4082404e-03, -3.963222e-06, 5.641515e-09, -2.444854e-12,
       -1020.8999, 3.950372]
    - [2.92664, 1.4879768e-03, -5.68476e-07, 1.0097038e-10, -6.753351e-15,
       -922.7977, 5.980528]
"""
                
                gas = ct.Solution(yaml=mechanism_string)
                print("Using custom mechanism")
        
        # Set the gas composition (mole fractions)
        species_dict = {}
        for species, fraction in gas_composition.items():
            if species in gas.species_names:
                species_dict[species] = fraction
        
        # Normalize if not all species are present
        total_frac = sum(species_dict.values())
        if total_frac > 0:
            species_dict = {k: v/total_frac for k, v in species_dict.items()}
        
        print(f"Available species: {gas.species_names}")
        print(f"Using composition: {species_dict}")
        
        for i, conditions in enumerate(test_conditions):
            T = conditions["T"]
            P = conditions["P"]
            print(f"\nCondition {i+1}: T={T}K, P={P}Pa")
            
            try:
                # Set the state
                gas.TPX = T, P, species_dict
                
                # Get properties
                density = gas.density  # kg/m³
                cp = gas.cp_mass      # J/kg/K
                enthalpy = gas.enthalpy_mass  # J/kg
                
                print(f"  Density: {density:.3f} kg/m³")
                print(f"  Cp: {cp:.1f} J/kg/K")
                print(f"  Enthalpy: {enthalpy:.1f} J/kg")
                print("  ✓ SUCCESS with Cantera")
                
            except Exception as e:
                print(f"  ✗ Cantera ERROR: {e}")
        
        return True
        
    except Exception as e:
        print(f"Cantera test failed: {e}")
        return False

def compare_with_ideal_gas():
    """Compare Cantera results with our ideal gas approximation."""
    print("\n" + "=" * 60)
    print("Comparing Cantera with ideal gas approximation...")
    
    # Import our ideal gas functions
    sys.path.append('/home/ubuntu/cur/program/seminar_fresh/ORC_analysis')
    from heat_source import _calculate_ideal_gas_density, _calculate_ideal_gas_cp
    
    gas_composition = {"CO2": 0.11, "H2O": 0.20, "N2": 0.69}
    T = 444.867
    P = 101325
    
    # Ideal gas calculation
    rho_ideal = _calculate_ideal_gas_density(gas_composition, T, P)
    cp_ideal = _calculate_ideal_gas_cp(gas_composition, T)
    
    print(f"Ideal gas - Density: {rho_ideal:.3f} kg/m³")
    print(f"Ideal gas - Cp: {cp_ideal:.1f} J/kg/K")
    
    # Try Cantera calculation if available
    try:
        import cantera as ct
        try:
            gas = ct.Solution('gri30.yaml')
        except:
            # Use our custom mechanism
            mechanism_string = """
phases:
- name: gas
  thermo: ideal-gas
  elements: [C, H, O, N]
  species: [CO2, H2O, N2]
  state:
    T: 300.0
    P: 1 atm

species:
- name: CO2
  composition: {C: 1, O: 2}
  thermo:
    model: NASA7
    temperature-ranges: [200.0, 1000.0, 3500.0]
    data:
    - [2.35677352, 8.98459677e-03, -7.12356269e-06, 2.45919022e-09, -1.43699548e-13,
       -4.83719697e+04, 9.90105222]
    - [3.85746029, 4.41437026e-03, -2.21481404e-06, 5.23490188e-10, -4.72084164e-14,
       -4.8759166e+04, 2.27163806]
- name: H2O
  composition: {H: 2, O: 1}
  thermo:
    model: NASA7
    temperature-ranges: [200.0, 1000.0, 3500.0]
    data:
    - [4.19864056, -2.0364341e-03, 6.52040211e-06, -5.48797062e-09, 1.77197817e-12,
       -3.02937267e+04, -0.849032208]
    - [3.03399249, 2.17691804e-03, -1.64072518e-07, -9.7041987e-11, 1.68200992e-14,
       -3.00042971e+04, 4.9667701]
- name: N2
  composition: {N: 2}
  thermo:
    model: NASA7
    temperature-ranges: [300.0, 1000.0, 5000.0]
    data:
    - [3.298677, 1.4082404e-03, -3.963222e-06, 5.641515e-09, -2.444854e-12,
       -1020.8999, 3.950372]
    - [2.92664, 1.4879768e-03, -5.68476e-07, 1.0097038e-10, -6.753351e-15,
       -922.7977, 5.980528]
"""
            gas = ct.Solution(yaml=mechanism_string)
        
        species_dict = {"CO2": 0.11, "H2O": 0.20, "N2": 0.69}
        gas.TPX = T, P, species_dict
        
        rho_cantera = gas.density
        cp_cantera = gas.cp_mass
        
        print(f"Cantera   - Density: {rho_cantera:.3f} kg/m³")
        print(f"Cantera   - Cp: {cp_cantera:.1f} J/kg/K")
        
        # Calculate relative differences
        rho_diff = abs(rho_cantera - rho_ideal) / rho_cantera * 100
        cp_diff = abs(cp_cantera - cp_ideal) / cp_cantera * 100
        
        print(f"\nRelative differences:")
        print(f"Density: {rho_diff:.1f}%")
        print(f"Cp: {cp_diff:.1f}%")
        
    except Exception as e:
        print(f"Cantera comparison failed: {e}")

if __name__ == "__main__":
    print("Testing Cantera as alternative to CoolProp for gas mixtures")
    print("=" * 60)
    
    if test_cantera_availability():
        success = test_cantera_gas_properties()
        if success:
            compare_with_ideal_gas()
    else:
        print("\nCantera is not available. The ideal gas approximation")
        print("we implemented should provide reasonable accuracy for")
        print("most engineering applications at moderate pressures.")