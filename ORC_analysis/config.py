"""ORCシステムのコンポーネント定義

このファイルではORCシステムのコンポーネントタイプを定義します。
コンポーネントの使用は実際の計算ロジックによって決定されます。
"""

from enum import Enum


class ComponentType(Enum):
    """コンポーネントタイプの列挙型"""
    PREHEATER = "Preheater"
    SUPERHEATER = "Superheater"
    EVAPORATOR = "Evaporator"
    CONDENSER = "Condenser"
    TURBINE = "Turbine"
    PUMP = "Pump"
    REGENERATOR = "Regenerator"
