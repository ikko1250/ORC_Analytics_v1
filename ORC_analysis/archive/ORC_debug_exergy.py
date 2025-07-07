import numpy as np
import pandas as pd
import CoolProp.CoolProp as CP

# Import the modified function and constants from the ORC_Analysis module
from ORC_Analysis import (
    calculate_orc_performance_from_heat_source,
    DEFAULT_FLUID,
    DEFAULT_T0,
)

# --------------------------------------------------
# 1. Settings (Copied from ORC_plot_heat_source.py)
# --------------------------------------------------
T_cond = 305.0  # Condensation temperature [K] (e.g., 32 °C)
eta_pump = 0.75
eta_turb = 0.80
fluid_orc = DEFAULT_FLUID
fluid_htf = "Water"

# Heat source fluid temperature range (°C) -> convert to K
T_htf_min_C = 70
T_htf_max_C = 100.0
n_T_points = 100
T_htf_values_K = np.linspace(T_htf_min_C + 273.15, T_htf_max_C + 273.15, n_T_points)

# New: Add flow rate array and unit specification
flow_rate_array = np.arange(45, 150, 5)  # Example: 5 to 35, adjust as needed
flow_unit = 't/h'  # Set to 'm3/h' or 't/h'. Change this to switch units.

superheat_C = 10.0  # ORC superheating [°C]
pinch_delta_K = 10.0 # Pinch point temperature difference [K]
T0 = DEFAULT_T0 # Dead state temperature [K]

# --------------------------------------------------
# 2. Calculation Loop
# --------------------------------------------------
results_list = []
print("Exergy analysis simulation running...")
print(f"Settings: Fluid={fluid_orc}, T_cond={T_cond-273.15:.1f}°C, T0={T0-273.15:.1f}°C")
print(f"Superheat={superheat_C}°C, Pinch Point ΔT={pinch_delta_K}K")
print(f"η_pump={eta_pump:.2f}, η_turb={eta_turb:.2f}")
print(f"Flow Unit: {flow_unit}")

for flow_rate in flow_rate_array:
    print(f"\nCalculating for Heat Source Flow Rate: {flow_rate} {flow_unit}")
    count = 0
    for T_htf_K in T_htf_values_K:
        if flow_unit == 'm3/h':
            # Directly convert m3/h to m3/s
            Vdot_m3s = flow_rate / 3600.0
        elif flow_unit == 't/h':
            # Convert t/h to kg/s, then to m3/s using density
            Mdot_kgs = flow_rate * 1000.0 / 3600.0  # t/h to kg/s
            try:
                rho_htf = CP.PropsSI("D", "T", T_htf_K, "P", 101325, fluid_htf)  # Density [kg/m³]
                Vdot_m3s = Mdot_kgs / rho_htf  # kg/s to m3/s
            except ValueError as e:
                print(f"Warning: Could not calculate density for {fluid_htf} at T={T_htf_K:.2f}K. Skipping this point. Error: {e}")
                continue  # Skip if density calculation fails
        else:
            print(f"Invalid flow_unit: {flow_unit}. Skipping.")
            continue
        
        res = calculate_orc_performance_from_heat_source(
            T_htf_in=T_htf_K,
            Vdot_htf=Vdot_m3s,
            T_cond=T_cond,
            eta_pump=eta_pump,
            eta_turb=eta_turb,
            fluid_orc=fluid_orc,
            fluid_htf=fluid_htf,
            superheat_C=superheat_C,
            pinch_delta_K=pinch_delta_K,
            T0=T0,
        )
        if res is not None:
            # Add the original flow rate for reference
            if flow_unit == 'm3/h':
                res["Flow_Rate [m3/h]"] = flow_rate
            elif flow_unit == 't/h':
                res["Flow_Rate [t/h]"] = flow_rate
                # Optionally add calculated m3/h for reference
                res["Calculated_Vdot [m3/h]"] = Vdot_m3s * 3600.0  # m3/s to m3/h
            results_list.append(res)
            count += 1
    print(f"  -> Completed {count} valid calculations for T_htf = {T_htf_min_C}-{T_htf_max_C}°C")

print("\nSimulation finished.")

if not results_list:
    raise RuntimeError(
        "No valid results were obtained. "
        "Consider increasing the heat source temperature range or check settings."
    )

# Convert list of dictionaries to DataFrame
results_df = pd.DataFrame(results_list)

# --------------------------------------------------
# 3. Output Results to CSV
# --------------------------------------------------
# Reorder columns for clarity
output_columns = [
    "Flow_Rate [m3/h]",
    "T_htf_in [°C]",
    "T_htf_out [°C]",
    "P_evap [bar]",
    "T_turb_in [°C]",
    "m_orc [kg/s]",
    "W_net [kW]",
    "Q_in [kW]",
    "η_th [-]",
    "ε_ex [-]",
    "E_dest_Pump [kW]",
    "E_dest_Evaporator [kW]",
    "E_dest_Turbine [kW]",
    "E_dest_Condenser [kW]",
    "E_dest_Total [kW]",
    "Evap_dT_lm [K]", # Log Mean Temperature Difference in Evaporator
]
# Ensure all expected columns exist, add missing ones with NaN if necessary
for col in output_columns:
    if col not in results_df.columns:
        results_df[col] = np.nan

results_df = results_df[output_columns] # Select and order columns

# Sort results for better readability
results_df = results_df.sort_values(by=["Flow_Rate [m3/h]", "T_htf_in [°C]"])

# Define CSV filename
csv_filename = f"orc_exergy_analysis_{fluid_orc}_Tcond{T_cond-273.15:.0f}C.csv"

# Save to CSV
results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig', float_format='%.4f')

print(f"\nExergy analysis results saved to: {csv_filename}")

# Display first few rows as confirmation
print("\nFirst 5 rows of the output CSV:")
print(results_df.head().to_string()) 