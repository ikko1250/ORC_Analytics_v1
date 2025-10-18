"""
Quick validator for wet steam economics vs NTU-based evaporator area.

Runs a wet-steam driven ORC using calculate_orc_performance_from_heat_source,
extracts NTU-based UA/Area (if U is provided), and contrasts economic results
from the current Economic.evaluate_orc_economics.

Usage:
  python -m ORC_analysis.validate_wet_steam_payback \
      --P_steam 19900 --quality_in 0.9 --quality_out 0.0 \
      --flow 70 --flow_mode mass \
      --U_evap_Wm2K 600

Notes:
  - If you omit --U_evap_Wm2K, NTU area will be reported as NaN (UA still shown).
  - This script does NOT change Economic.py behavior; it helps diagnose if
    small LMTD-based area is the cause of short payback in wet_steam runs.
"""

import argparse
import pprint

import numpy as np

from ORC_analysis.ORC_Analysis import (
    calculate_orc_performance_from_heat_source,
    DEFAULT_FLUID as ORC_DEFAULT_FLUID,
)
from ORC_analysis.Economic import (
    evaluate_orc_economics,
    _calculate_pec_evaporator_liquid,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--P_steam', type=float, default=19900.0, help='Steam pressure [Pa] (saturated)')
    ap.add_argument('--quality_in', type=float, default=0.90, help='Inlet quality x_in [-]')
    ap.add_argument('--quality_out', type=float, default=0.0, help='Outlet quality x_out [-]')
    ap.add_argument('--flow', type=float, default=10.0, help='Flow value (kg/s if mass, m3/s if volumetric)')
    ap.add_argument('--flow_mode', choices=['mass','volumetric'], default='mass')
    ap.add_argument('--T_cond', type=float, default=305.0, help='Condenser temperature [K]')
    ap.add_argument('--eta_pump', type=float, default=0.4)
    ap.add_argument('--eta_turb', type=float, default=0.8)
    ap.add_argument('--orc_fluid', type=str, default=ORC_DEFAULT_FLUID)
    ap.add_argument('--superheat_C', type=float, default=5.0)
    ap.add_argument('--pinch_K', type=float, default=5.0)
    ap.add_argument('--U_evap_Wm2K', type=float, default=None, help='Overall U for evaporator [W/m2-K] used for NTU area')
    args = ap.parse_args()

    # Wet steam operates at saturation temperature for given pressure
    # Use detailed heat exchange splitting to expose NTU metrics.
    perf = calculate_orc_performance_from_heat_source(
        T_htf_in=None,  # unused for wet_steam
        Vdot_htf=args.flow,
        T_cond=args.T_cond,
        eta_pump=args.eta_pump,
        eta_turb=args.eta_turb,
        fluid_orc=args.orc_fluid,
        superheat_C=args.superheat_C,
        pinch_delta_K=args.pinch_K,
        use_detailed_hex=True,
        heat_source_type='wet_steam',
        P_steam=args.P_steam,
        quality=args.quality_in,
        quality_out=args.quality_out,
        mass_flow_mode=(args.flow_mode=='mass'),
        U_evaporator_W_m2K=args.U_evap_Wm2K,
    )

    if perf is None:
        print('Performance calculation returned None – infeasible operating point.')
        return

    print('\n=== ORC performance (from wet_steam) ===')
    pprint.pprint({k: v for k, v in perf.items() if k in (
        'W_net [kW]','Q_in [kW]','η_th [-]','ε_ex [-]','m_orc [kg/s]','P_evap [bar]',
        'Evaporator_UA_NTU [kW/K]','Evaporator_A_NTU [m²]','Evap_dT_lm [K]','T_htf_in [°C]','T_htf_out [°C]'
    )})

    # Run current economics (which uses LMTD-based area internally)
    econ = evaluate_orc_economics(
        P_evap=perf['P_evap [bar]']*1e5,
        T_turb_in=perf['T_turb_in [°C]']+273.15,
        T_cond=args.T_cond,
        eta_pump=args.eta_pump,
        eta_turb=args.eta_turb,
        m_orc=perf['m_orc [kg/s]'],
        heat_source_type='wet_steam',
    )
    comp_costs = econ['component_costs']
    summary = econ['summary']

    print('\n=== Current economics (LMTD-based area) ===')
    print(comp_costs)
    print('\nSummary:')
    print(summary)

    # If NTU-based area is available, compute a corrected Evaporator PEC
    A_ntu = perf.get('Evaporator_A_NTU [m²]', np.nan)
    if A_ntu is None or not np.isfinite(A_ntu) or A_ntu <= 0:
        print('\nNo NTU-based area available (provide --U_evap_Wm2K to compute A_NTU).')
        return

    pec_evap_ntu = _calculate_pec_evaporator_liquid(A_ntu)
    pec_evap_old = comp_costs.loc['Evaporator','PEC [$]'] if 'Evaporator' in comp_costs.index else 0.0
    pec_total_corr = summary['PEC_total [$]'] - pec_evap_old + pec_evap_ntu

    # Recompute unit cost and simple PB using corrected PEC
    # Pull defaults used in Economic for CRF and hours indirectly
    from ORC_analysis.Economic import capital_recovery_factor, INTEREST_RATE, LIFETIME_YR, ANNUAL_HOURS, ELEC_PRICE, MAINT_FACTOR
    CRF = capital_recovery_factor(INTEREST_RATE, LIFETIME_YR)
    W_net = perf['W_net [kW]']
    c_unit_corr = (CRF * pec_total_corr + MAINT_FACTOR) / (W_net * ANNUAL_HOURS)
    annual_revenue = W_net * ANNUAL_HOURS * ELEC_PRICE
    denom_pb = annual_revenue - MAINT_FACTOR
    PB_corr = pec_total_corr / denom_pb if denom_pb > 0 else float('inf')

    print('\n=== Corrected (use NTU-based Evaporator area) ===')
    print(f"A_NTU (Evaporator) = {A_ntu:,.1f} m²")
    print(f"Evaporator PEC (NTU) = ${pec_evap_ntu:,.0f}")
    print(f"PEC_total (corrected) = ${pec_total_corr:,.0f}")
    print(f"Unit elec cost (corrected) = ${c_unit_corr:.4f}/kWh")
    print(f"Simple PB (corrected) = {PB_corr:.1f} years")


if __name__ == '__main__':
    main()

