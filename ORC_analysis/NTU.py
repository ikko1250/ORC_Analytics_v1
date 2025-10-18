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

# --- Minimal, reusable NTU utilities (kept simple and self-contained) ---

def effectiveness_counterflow(NTU: float, C_r: float) -> float:
    """Effectiveness ε for a counterflow heat exchanger.

    Parameters
    - NTU: Number of Transfer Units (>= 0)
    - C_r: Capacity ratio C_min / C_max in [0, 1]

    Returns
    - ε in (0,1)
    """
    if NTU < 0:
        return 0.0
    # Special case: phase-change on one side -> C_r = 0 => ε = 1 - exp(-NTU)
    if C_r <= 1e-12:
        return 1.0 - np.exp(-NTU)
    # General counterflow expression
    num = 1.0 - np.exp(-NTU * (1.0 - C_r))
    den = 1.0 - C_r * np.exp(-NTU * (1.0 - C_r))
    if den == 0:
        return 0.0
    return num / den


def ntu_from_effectiveness_counterflow(epsilon: float, C_r: float, *, tol: float = 1e-8, max_iter: int = 200) -> float:
    """Invert ε(NTU, C_r) for counterflow to obtain NTU from ε and C_r.

    - Closed form for C_r=0: NTU = -ln(1-ε)
    - Otherwise: monotone bisection on NTU in [0, NTU_max]
    """
    eps = max(1e-12, min(1.0 - 1e-12, epsilon))
    if C_r <= 1e-12:
        return -np.log(1.0 - eps)

    # Bisection on NTU; set a generous upper bound
    lo, hi = 0.0, 100.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = effectiveness_counterflow(mid, C_r)
        if abs(f_mid - eps) < tol:
            return mid
        if f_mid < eps:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def sizing_via_ntu(Q_W: float,
                   T_hot_in: float, T_hot_out: float,
                   T_cold_in: float, T_cold_out: float,
                   U_W_m2K: float | None = None,
                   *,
                   arrangement: str = "counterflow") -> dict:
    """Compute UA, NTU, ε, and A (if U is provided) from segment data using ε–NTU.

    This routine intentionally uses only local segment data (Q and end temperatures)
    to avoid strong coupling; it handles the phase‑change case via C_r=0.

    Returns a dict with keys: 'UA_W_per_K', 'NTU', 'epsilon', 'C_min_W_per_K',
    'C_r', and if U provided, 'A_m2'.
    """
    if arrangement != "counterflow":
        # For minimal changes we only support counterflow here.
        raise NotImplementedError("Only counterflow arrangement is supported in minimal NTU utility.")

    # Use absolute Q for sizing, sign does not matter for UA
    Q = abs(Q_W)

    # Detect phase‑change on the cold side (isothermal): ΔT_cold ≈ 0
    dT_hot = float(T_hot_in - T_hot_out)
    dT_cold = float(T_cold_out - T_cold_in)

    # Guard against degenerate data: both sides isothermal (e.g., condensing → boiling)
    if abs(dT_hot) < 1e-12 and abs(dT_cold) < 1e-12:
        # For isothermal–isothermal exchange, UA follows from Q = UA * ΔT (constant approach)
        delta_T = float(T_hot_in - T_cold_in)
        UA = Q / max(1e-12, abs(delta_T))
        out = {
            "UA_W_per_K": UA,
            "NTU": np.nan,
            "epsilon": np.nan,
            "C_min_W_per_K": np.nan,
            "C_r": np.nan,
        }
        if U_W_m2K:
            out["A_m2"] = UA / U_W_m2K
        return out

    # Segment capacity rates from energy balance (piecewise constant assumption)
    # C_hot_seg = Q / |ΔT_hot|; C_cold_seg = Q / |ΔT_cold| (if ΔT_cold>0)
    C_hot = Q / max(1e-12, abs(dT_hot))
    if abs(dT_cold) < 1e-12:
        # Phase‑change on cold side (e.g., evaporator): C_r = 0, C_min = C_hot
        C_min = C_hot
        C_r = 0.0
        # ΔT_max = T_hot_in − T_cold_in (approach at hot inlet)
        dT_max = float((T_hot_in - T_cold_in))
        # Observed effectiveness from temperatures
        eps_obs = max(1e-12, min(1.0 - 1e-12, abs(dT_hot) / max(1e-12, abs(dT_max))))
        NTU = -np.log(1.0 - eps_obs)
        UA = NTU * C_min
    else:
        C_cold = Q / abs(dT_cold)
        C_min = min(C_hot, C_cold)
        C_max = max(C_hot, C_cold)
        C_r = C_min / C_max if C_max > 0 else 0.0
        dT_max = float((T_hot_in - T_cold_in))
        eps_obs = Q / max(1e-12, (C_min * abs(dT_max)))
        eps_obs = max(1e-12, min(1.0 - 1e-12, eps_obs))
        NTU = ntu_from_effectiveness_counterflow(eps_obs, C_r)
        UA = NTU * C_min

    out = {
        "UA_W_per_K": UA,
        "NTU": NTU,
        "epsilon": float(eps_obs),
        "C_min_W_per_K": C_min,
        "C_r": float(C_r),
    }
    if U_W_m2K:
        out["A_m2"] = UA / U_W_m2K
    return out

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

# Display table to user (optional in non-notebook environments)
try:
    import caas_jupyter_tools  # only available in certain notebook runtimes
    caas_jupyter_tools.display_dataframe_to_user(
        "Required area vs U (LMTD vs ε–NTU cross-check)", df.round(3)
    )
except Exception:
    pass

# Plot Area vs U
plt.figure()
plt.plot(U_values, A_lmtd, marker='o')
plt.xlabel('Overall heat transfer coefficient U [W/m^2-K]')
plt.ylabel('Required area A [m^2]')
plt.title('Required area vs U (Tsat≈60.06°C, water 25→35°C)')
plt.grid(True)
plt.show()

headline
