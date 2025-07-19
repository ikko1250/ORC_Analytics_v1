from dataclasses import dataclass
import CoolProp.CoolProp as CP

def _get_cantera_gas_properties(gas_composition: dict, T: float, P: float):
    """
    Canteraを使用してガス混合物の物性を計算する。
    CoolPropが失敗した場合の代替手段として使用。
    
    Args:
        gas_composition: 各成分のモル分率辞書
        T: 温度 [K]
        P: 圧力 [Pa]
    
    Returns:
        dict: {'density': 密度[kg/m³], 'cp': 比熱[J/kg/K], 'enthalpy': エンタルピー[J/kg]}
    """
    try:
        import cantera as ct
        
        # GRI-Mech 3.0を試す（包括的な燃焼メカニズム）
        try:
            gas = ct.Solution('gri30.yaml')
        except:
            # カスタムメカニズムを使用
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
        
        # 組成を設定（利用可能な成分のみ使用し、正規化）
        species_dict = {}
        for species, fraction in gas_composition.items():
            if species in gas.species_names:
                species_dict[species] = fraction
        
        # 組成の正規化
        total_frac = sum(species_dict.values())
        if total_frac > 0:
            species_dict = {k: v/total_frac for k, v in species_dict.items()}
        
        # 状態を設定
        gas.TPX = T, P, species_dict
        
        return {
            'density': gas.density,     # kg/m³
            'cp': gas.cp_mass,         # J/kg/K
            'enthalpy': gas.enthalpy_mass  # J/kg
        }
        
    except ImportError:
        # Canteraがインストールされていない場合は理想ガス近似にフォールバック
        return None
    except Exception as e:
        # その他のCanteraエラーの場合も理想ガス近似にフォールバック
        return None

def _calculate_ideal_gas_density(gas_composition: dict, T: float, P: float) -> float:
    """
    理想ガス法を使用してガス混合物の密度を計算する。
    
    Args:
        gas_composition: 各成分のモル分率辞書 (例: {"CO2": 0.11, "H2O": 0.20, "N2": 0.69})
        T: 温度 [K]
        P: 圧力 [Pa]
    
    Returns:
        密度 [kg/m³]
    """
    R = 8.314  # 気体定数 [J/mol/K]
    
    # 各成分の分子量 [g/mol]
    molecular_weights = {
        "CO2": 44.01,
        "H2O": 18.015,
        "N2": 28.014,
        "O2": 31.998,
        "SO2": 64.066,
        "CO": 28.010
    }
    
    # 平均分子量の計算
    MW_avg = 0.0
    for species, fraction in gas_composition.items():
        if species in molecular_weights:
            MW_avg += fraction * molecular_weights[species]
    
    MW_avg_kg = MW_avg / 1000  # kg/mol に変換
    
    # 理想ガス法: ρ = P * MW / (R * T)
    density = P * MW_avg_kg / (R * T)
    
    return density

def _calculate_ideal_gas_cp(gas_composition: dict, T: float) -> float:
    """
    各成分の比熱を重み付き平均して混合物の比熱を計算する。
    
    Args:
        gas_composition: 各成分のモル分率辞書
        T: 温度 [K]
    
    Returns:
        比熱 [J/kg/K]
    """
    # 温度依存の比熱係数 (Cp = a + bT + cT^2 + dT^3) [J/mol/K]
    # NIST webbook等の係数を使用
    cp_coefficients = {
        "CO2": {"a": 24.99735, "b": 55.18696e-3, "c": -33.69137e-6, "d": 7.948387e-9},
        "H2O": {"a": 30.09200, "b": 6.832514e-3, "c": 6.793435e-6, "d": -2.534480e-9},
        "N2": {"a": 28.98641, "b": 1.853978e-3, "c": -9.647459e-6, "d": 16.63537e-9},
        "O2": {"a": 31.32234, "b": -20.23531e-3, "c": 57.86644e-6, "d": -36.50624e-9},
    }
    
    # 各成分の分子量 [g/mol]
    molecular_weights = {
        "CO2": 44.01,
        "H2O": 18.015,
        "N2": 28.014,
        "O2": 31.998,
    }
    
    cp_mix_molar = 0.0  # [J/mol/K]
    MW_avg = 0.0
    
    for species, fraction in gas_composition.items():
        if species in cp_coefficients and species in molecular_weights:
            coeffs = cp_coefficients[species]
            # 温度依存の比熱計算
            cp_species = (coeffs["a"] + 
                         coeffs["b"] * T + 
                         coeffs["c"] * T**2 + 
                         coeffs["d"] * T**3)
            
            cp_mix_molar += fraction * cp_species
            MW_avg += fraction * molecular_weights[species]
    
    # 質量基準の比熱に変換 [J/kg/K]
    MW_avg_kg = MW_avg / 1000  # kg/mol
    cp_mix_mass = cp_mix_molar / MW_avg_kg
    
    return cp_mix_mass

@dataclass
class HeatSourceProfile:
    """
    熱源の物理特性を保持するデータクラス。
    このクラスを介して、計算に必要な情報を一貫した形式で受け渡す。
    """
    m_dot: float          # 質量流量 [kg/s]
    cp: float             # 平均比熱 [J/kg/K]
    T_in: float           # 熱交換器への入口温度 [K]
    T_out_min: float      # 熱交換器からの最低出口温度 [K]
    Q_available: float    # 利用可能熱量 [W]

def get_heat_source_profile(
    T_htf_in: float,
    Vdot_htf: float,
    T_htf_out: float,
    heat_source_type: str = "liquid",
    fluid_htf: str = "Water",
    **kwargs
) -> HeatSourceProfile:
    """
    熱源の種類と条件に基づき、その物理特性プロファイルを計算して返す。
    将来的にはこの関数に "gas" や "steam" の分岐を追加していく。
    """
    if heat_source_type == "liquid":
        # 現在のORC_Analysis.pyにある液体熱源の計算ロジックをここに集約
        P_htf = kwargs.get('P_htf', 101325)  # デフォルト圧力
        
        rho_htf = CP.PropsSI("D", "T", T_htf_in, "P", P_htf, fluid_htf)
        cp_htf = CP.PropsSI("C", "T", T_htf_in, "P", P_htf, fluid_htf)
        m_dot_htf = Vdot_htf * rho_htf
        
        Q_available = m_dot_htf * cp_htf * (T_htf_in - T_htf_out)

        return HeatSourceProfile(
            m_dot=m_dot_htf,
            cp=cp_htf,
            T_in=T_htf_in,
            T_out_min=T_htf_out,
            Q_available=Q_available
        )

    elif heat_source_type == "gas":
        # ガス熱源の計算ロジック
        P_gas = kwargs.get('P_gas', 101325)  # デフォルト圧力
        gas_composition = kwargs.get('gas_composition', None)
        mass_flow_mode = kwargs.get('mass_flow_mode', False)
        # 安全のため、デフォルトの最低出口温度を酸露点腐食リスクの低い120℃ (393.15 K)に設定
        T_gas_out_min = kwargs.get('T_gas_out_min', 393.15)

        # デフォルトガス組成（天然ガス燃焼排ガスを想定）
        if gas_composition is None:
            gas_composition = {
                "CO2": 0.11,
                "H2O": 0.20,
                "N2": 0.69
            }

        # 組成の妥当性チェック
        total_fraction = sum(gas_composition.values())
        if abs(total_fraction - 1.0) > 0.01:
            raise ValueError(f"Gas composition fractions sum to {total_fraction:.3f}, should be 1.0")

        # CoolProp混合物文字列を作成
        coolprop_components = []
        coolprop_mapping = {
            "CO2": "CO2",
            "H2O": "Water",
            "N2": "Nitrogen",
            "O2": "Oxygen",
            "SO2": "SulfurDioxide",
            "CO": "CarbonMonoxide"
        }

        for species, fraction in gas_composition.items():
            if species in coolprop_mapping and fraction > 0:
                coolprop_components.append(f"{coolprop_mapping[species]}[{fraction}]")

        if not coolprop_components:
            raise ValueError("No valid gas components found for CoolProp calculation")

        mixture_string = "&".join(coolprop_components)

        try:
            # 質量流量計算
            if mass_flow_mode:
                m_dot_gas = Vdot_htf  # 単位: kg/s
            else:
                # 体積流量(m3/s)から質量流量(kg/s)へ変換
                # 1. まずCoolPropを試す
                rho_gas_in = None
                try:
                    rho_gas_in = CP.PropsSI("D", "T", T_htf_in, "P", P_gas, mixture_string)
                    m_dot_gas = Vdot_htf * rho_gas_in
                except Exception as coolprop_error:
                    # 2. CoolPropが失敗した場合、Canteraを試す
                    cantera_props = _get_cantera_gas_properties(gas_composition, T_htf_in, P_gas)
                    if cantera_props is not None:
                        print(f"Warning: CoolProp failed, using Cantera for gas property calculation.")
                        rho_gas_in = cantera_props['density']
                        m_dot_gas = Vdot_htf * rho_gas_in
                    else:
                        # 3. 最後の手段として理想ガス近似を使用
                        print(f"Warning: Both CoolProp and Cantera failed, using ideal gas approximation. CoolProp error: {coolprop_error}")
                        rho_gas_in = _calculate_ideal_gas_density(gas_composition, T_htf_in, P_gas)
                        m_dot_gas = Vdot_htf * rho_gas_in

            # エンタルピー差を用いて、より正確な熱量を計算
            Q_available = None
            cp_gas_avg = None
            
            # 1. まずCoolPropを試す
            try:
                h_in = CP.PropsSI("H", "T", T_htf_in, "P", P_gas, mixture_string)
                h_out = CP.PropsSI("H", "T", T_gas_out_min, "P", P_gas, mixture_string)
                Q_available = m_dot_gas * (h_in - h_out)
                cp_gas_avg = (h_in - h_out) / (T_htf_in - T_gas_out_min)
            except Exception as coolprop_error:
                # 2. CoolPropが失敗した場合、Canteraを試す
                cantera_props_in = _get_cantera_gas_properties(gas_composition, T_htf_in, P_gas)
                cantera_props_out = _get_cantera_gas_properties(gas_composition, T_gas_out_min, P_gas)
                
                if cantera_props_in is not None and cantera_props_out is not None:
                    print(f"Warning: CoolProp enthalpy calculation failed, using Cantera.")
                    h_in = cantera_props_in['enthalpy']
                    h_out = cantera_props_out['enthalpy']
                    Q_available = m_dot_gas * (h_in - h_out)
                    cp_gas_avg = (h_in - h_out) / (T_htf_in - T_gas_out_min)
                else:
                    # 3. 最後の手段として理想ガス近似を使用
                    print(f"Warning: Both CoolProp and Cantera failed for enthalpy, using ideal gas approximation. CoolProp error: {coolprop_error}")
                    cp_gas_avg = _calculate_ideal_gas_cp(gas_composition, (T_htf_in + T_gas_out_min) / 2)
                    Q_available = m_dot_gas * cp_gas_avg * (T_htf_in - T_gas_out_min)

            return HeatSourceProfile(
                m_dot=m_dot_gas,
                cp=cp_gas_avg,
                T_in=T_htf_in,
                T_out_min=T_gas_out_min,
                Q_available=Q_available
            )
            
        except Exception as e:
            raise ValueError(f"Gas property calculation failed: {e}")
        
    elif heat_source_type == "steam":
        # 将来の拡張ポイント
        raise NotImplementedError("Steam heat source calculation is not yet implemented.")

    else:
        raise ValueError(f"Unknown heat_source_type: {heat_source_type}")