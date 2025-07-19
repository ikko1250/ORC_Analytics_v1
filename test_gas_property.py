#!/usr/bin/env python3
"""
Test script to reproduce and diagnose the CoolProp gas property calculation error.
"""
import CoolProp.CoolProp as CP
import sys

def test_gas_mixture_properties():
    """Test gas mixture property calculations with different compositions and conditions."""
    
    # Original failing composition from error message
    original_composition = {
        "CO2": 0.11,
        "H2O": 0.20,
        "N2": 0.69
    }
    
    # Alternative compositions to test
    test_compositions = [
        {"CO2": 0.11, "H2O": 0.20, "N2": 0.69},  # Original
        {"CO2": 0.10, "H2O": 0.15, "N2": 0.75},  # Lower water content
        {"CO2": 0.12, "H2O": 0.10, "N2": 0.78},  # Much lower water content
        {"CO2": 0.05, "H2O": 0.05, "N2": 0.90},  # Very low CO2 and water
    ]
    
    # Test conditions
    test_conditions = [
        {"T": 444.867, "P": 101325},  # Original failing condition
        {"T": 400.0, "P": 101325},    # Lower temperature
        {"T": 500.0, "P": 101325},    # Higher temperature
        {"T": 444.867, "P": 200000},  # Higher pressure
    ]
    
    coolprop_mapping = {
        "CO2": "CO2",
        "H2O": "Water", 
        "N2": "Nitrogen"
    }
    
    print("Testing gas mixture property calculations...")
    print("=" * 60)
    
    for i, composition in enumerate(test_compositions):
        print(f"\nTest Composition {i+1}: {composition}")
        
        # Create CoolProp mixture string
        coolprop_components = []
        for species, fraction in composition.items():
            if species in coolprop_mapping and fraction > 0:
                coolprop_components.append(f"{coolprop_mapping[species]}[{fraction}]")
        
        mixture_string = "&".join(coolprop_components)
        print(f"CoolProp mixture string: {mixture_string}")
        
        for j, conditions in enumerate(test_conditions):
            T = conditions["T"]
            P = conditions["P"]
            print(f"  Condition {j+1}: T={T}K, P={P}Pa")
            
            try:
                # Test density calculation (the failing property)
                density = CP.PropsSI("D", "T", T, "P", P, mixture_string)
                print(f"    Density: {density:.3f} kg/m³")
                
                # Test other properties
                enthalpy = CP.PropsSI("H", "T", T, "P", P, mixture_string)
                print(f"    Enthalpy: {enthalpy:.1f} J/kg")
                
                cp = CP.PropsSI("C", "T", T, "P", P, mixture_string)
                print(f"    Cp: {cp:.1f} J/kg/K")
                
                print("    ✓ SUCCESS")
                
            except Exception as e:
                print(f"    ✗ ERROR: {e}")
                
                # Try with different backends
                try:
                    print("    Trying HEOS backend...")
                    density = CP.PropsSI("D", "T", T, "P", P, f"HEOS::{mixture_string}")
                    print(f"    HEOS Density: {density:.3f} kg/m³ ✓")
                except Exception as e2:
                    print(f"    HEOS also failed: {e2}")
                
                try:
                    print("    Trying REFPROP backend...")
                    density = CP.PropsSI("D", "T", T, "P", P, f"REFPROP::{mixture_string}")
                    print(f"    REFPROP Density: {density:.3f} kg/m³ ✓")
                except Exception as e3:
                    print(f"    REFPROP also failed: {e3}")

def test_individual_components():
    """Test individual gas components to isolate the problem."""
    print("\n" + "=" * 60)
    print("Testing individual gas components...")
    
    components = ["CO2", "Water", "Nitrogen"]
    T = 444.867
    P = 101325
    
    for component in components:
        print(f"\nTesting {component}:")
        try:
            density = CP.PropsSI("D", "T", T, "P", P, component)
            print(f"  Density: {density:.3f} kg/m³ ✓")
        except Exception as e:
            print(f"  ERROR: {e}")

def test_simpler_mixtures():
    """Test with simpler binary mixtures."""
    print("\n" + "=" * 60)
    print("Testing simpler binary mixtures...")
    
    binary_mixtures = [
        "CO2[0.5]&Nitrogen[0.5]",
        "Water[0.2]&Nitrogen[0.8]", 
        "CO2[0.1]&Nitrogen[0.9]",
    ]
    
    T = 444.867
    P = 101325
    
    for mixture in binary_mixtures:
        print(f"\nTesting {mixture}:")
        try:
            density = CP.PropsSI("D", "T", T, "P", P, mixture)
            print(f"  Density: {density:.3f} kg/m³ ✓")
        except Exception as e:
            print(f"  ERROR: {e}")

def test_alternative_approaches():
    """Test alternative approaches for gas property calculation."""
    print("\n" + "=" * 60)
    print("Testing alternative approaches...")
    
    # Test using ideal gas approximation
    composition = {"CO2": 0.11, "H2O": 0.20, "N2": 0.69}
    T = 444.867
    P = 101325
    R = 8.314  # J/mol/K
    
    # Molecular weights (g/mol)
    MW = {"CO2": 44.01, "H2O": 18.015, "N2": 28.014}
    
    # Calculate average molecular weight
    MW_avg = sum(fraction * MW[species] for species, fraction in composition.items())
    MW_avg_kg = MW_avg / 1000  # Convert to kg/mol
    
    # Ideal gas density
    rho_ideal = P * MW_avg_kg / (R * T)
    print(f"Ideal gas density estimate: {rho_ideal:.3f} kg/m³")
    
    # Test with reduced precision in composition
    print("\nTesting with rounded composition fractions:")
    rounded_composition = {k: round(v, 2) for k, v in composition.items()}
    print(f"Rounded composition: {rounded_composition}")
    
    coolprop_components = []
    coolprop_mapping = {"CO2": "CO2", "H2O": "Water", "N2": "Nitrogen"}
    
    for species, fraction in rounded_composition.items():
        if species in coolprop_mapping and fraction > 0:
            coolprop_components.append(f"{coolprop_mapping[species]}[{fraction}]")
    
    mixture_string = "&".join(coolprop_components)
    print(f"CoolProp mixture string: {mixture_string}")
    
    try:
        density = CP.PropsSI("D", "T", T, "P", P, mixture_string)
        print(f"CoolProp density: {density:.3f} kg/m³ ✓")
    except Exception as e:
        print(f"Still failed: {e}")

if __name__ == "__main__":
    print("CoolProp Gas Property Calculation Test")
    try:
        version = CP.get_global_param_string("version")
        print(f"CoolProp version: {version}")
    except:
        print("CoolProp version: unknown")
    print(f"Python version: {sys.version}")
    
    try:
        test_individual_components()
        test_simpler_mixtures()
        test_gas_mixture_properties()
        test_alternative_approaches()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest completed.")