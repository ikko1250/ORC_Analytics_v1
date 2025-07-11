from dataclasses import dataclass
import CoolProp.CoolProp as CP

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
        T_gas_out_min = kwargs.get('T_gas_out_min', T_htf_out)
        
        # デフォルトガス組成（天然ガス燃焼）
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
            # ガス物性計算
            rho_gas = CP.PropsSI("D", "T", T_htf_in, "P", P_gas, mixture_string)
            cp_gas = CP.PropsSI("C", "T", T_htf_in, "P", P_gas, mixture_string)
            
            # 質量流量計算
            if mass_flow_mode:
                m_dot_gas = Vdot_htf  # kg/s
            else:
                m_dot_gas = Vdot_htf * rho_gas  # m3/s → kg/s
            
            # 利用可能熱量計算
            Q_available = m_dot_gas * cp_gas * (T_htf_in - T_gas_out_min)
            
            return HeatSourceProfile(
                m_dot=m_dot_gas,
                cp=cp_gas,
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