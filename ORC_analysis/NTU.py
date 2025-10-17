# Let's compute the feasibility under simplified, defensible assumptions:
# - Steam at 19,900 Pa is saturated at ~60.06 °C (approx.)
# - Latent heat of vaporization at ~60 °C is ~2358 kJ/kg
# - Inlet steam mass flow = 70 kg/s with quality x=0.9 => vapor mass = 63 kg/s
# - Goal: condense all vapor to saturated liquid (no subcooling), so Q = m_vap * h_fg
# - Cooling water warms from 25 °C to 35 °C (10 K rise); cp ~ 4180 J/kg-K (assume weak T dependence)
# - Counterflow, phase-change side behaves as Cr ~ 0 (effectiveness method special case)
# - Negligible pressure drop on steam side (=> Tsat constant)
#
# We'll compute:
# 1) Required water mass flow to absorb Q with 10 K rise
# 2) LMTD for 60.06 °C vs 25->35 °C and corresponding required area A for a range of overall U values
# 3) Cross-check with ε–NTU: for Cr=0, ε = 1 - exp(-NTU), ε = (T_c,out - T_c,in)/(T_h,in - T_c,in)
#    => NTU = -ln(1 - ε); then UA = NTU * Cmin ; A = UA/U
#
# We'll produce a small table and a plot of A vs U to show feasibility ranges.


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import log

# Given/assumed constants
p_sat = 19900.0  # Pa (not used directly in this simplified calc)
T_sat = 60.06    # °C (approx saturation temperature for ~19.9 kPa)
h_fg = 2.358e6   # J/kg (latent heat near 60 °C)
m_total = 70.0   # kg/s
x_in = 0.9       # quality
m_vap = m_total * x_in  # kg/s to be condensed
cp_w = 4180.0    # J/kg-K for water
Tc_in = 25.0     # °C
Tc_out = 35.0    # °C
dT_water = Tc_out - Tc_in  # K

# 1) Heat duty required to condense vapor to saturated liquid (no subcooling)
Q = m_vap * h_fg  # W

# Required water mass flow for a 10 K rise
m_w = Q / (cp_w * dT_water)

# 2) LMTD for counterflow when hot side remains at Tsat (phase change, constant T)
# ΔT_hot_out = T_sat - Tc_in (counterflow cold end)
# ΔT_hot_in  = T_sat - Tc_out (counterflow hot end)
dT2 = T_sat - Tc_in
dT1 = T_sat - Tc_out
LMTD = (dT2 - dT1) / np.log(dT2 / dT1)

# Range of plausible overall U values (W/m^2-K). Condensation in tubes often 1000–5000+, but we sample wider.
U_values = np.array([500, 1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000], dtype=float)

# Required area via LMTD: A = Q / (U * LMTD)
A_lmtd = Q / (U_values * LMTD)

# 3) ε–NTU cross-check for Cr=0
epsilon = (Tc_out - Tc_in) / (T_sat - Tc_in)  # effectiveness
NTU = -np.log(1.0 - epsilon)
Cmin = m_w * cp_w
UA_ntu = NTU * Cmin
# For each U, A should be UA/U; should match A_lmtd (up to rounding)
A_ntu = UA_ntu / U_values

# Assemble results
df = pd.DataFrame({
    "U [W/m^2-K]": U_values,
    "Area LMTD [m^2]": A_lmtd,
    "Area ε–NTU [m^2]": A_ntu
})

# Some headline numbers
headline = {
    "Tsat [°C] (assumed)": T_sat,
    "Latent heat h_fg [kJ/kg] (assumed)": h_fg/1000.0,
    "Vapor mass flow [kg/s]": m_vap,
    "Heat duty Q [MW]": Q/1e6,
    "Water mass flow for 10 K rise [kg/s]": m_w,
    "ΔT1 = Tsat - Tc_out [K]": dT1,
    "ΔT2 = Tsat - Tc_in [K]": dT2,
    "LMTD [K]": LMTD,
    "Effectiveness ε (Cr≈0)": epsilon,
    "NTU (Cr≈0)": NTU,
    "UA (from ε–NTU) [MW/K]": UA_ntu/1e6
}

# Display table to user
import caas_jupyter_tools
caas_jupyter_tools.display_dataframe_to_user("Required area vs U (LMTD vs ε–NTU cross-check)", df.round(3))

# Plot Area vs U
plt.figure()
plt.plot(U_values, A_lmtd, marker='o')
plt.xlabel('Overall heat transfer coefficient U [W/m^2-K]')
plt.ylabel('Required area A [m^2]')
plt.title('Required area vs U (Tsat≈60.06°C, water 25→35°C)')
plt.grid(True)
plt.show()

headline
