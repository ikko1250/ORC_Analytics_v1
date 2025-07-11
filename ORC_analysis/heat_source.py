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
        # 将来の拡張ポイント
        raise NotImplementedError("Gas heat source calculation is not yet implemented.")
        
    elif heat_source_type == "steam":
        # 将来の拡張ポイント
        raise NotImplementedError("Steam heat source calculation is not yet implemented.")

    else:
        raise ValueError(f"Unknown heat_source_type: {heat_source_type}")