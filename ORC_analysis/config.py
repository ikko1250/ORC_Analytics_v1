"""ORCシステムのコンポーネント利用設定

このファイルでpreheater/superheater等の利用有無やパラメータを一元管理します。
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional, Union

# Setup logging
logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """コンポーネントタイプの列挙型"""
    PREHEATER = "Preheater"
    SUPERHEATER = "Superheater"
    EVAPORATOR = "Evaporator"
    CONDENSER = "Condenser"
    TURBINE = "Turbine"
    PUMP = "Pump"
    REGENERATOR = "Regenerator"


COMPONENT_SETTINGS = {
    'use_preheater': False,  # 予熱器を利用する場合はTrue
    'use_superheater': False,  # 過熱器を利用する場合はTrue
    'preheater_params': {
        'max_power_kW': 50.0,  # 最大電力 [kW]
        'efficiency': 0.95,    # 効率 [-]
    },
    'superheater_params': {
        'max_power_kW': 100.0,  # 最大電力 [kW]
        'efficiency': 0.95,     # 効率 [-]
    },
    'optimization_settings': {
        'enable_optimization': True,  # 最適化を有効にする場合はTrue
        'target_evap_out_temp_K': None,  # 蒸発器出口目標温度 [K]
        'max_iterations': 100,  # 最大反復回数
        'tolerance': 1e-6,      # 収束判定値
    }
}


def get_component_setting(key: str, default: Any = None) -> Any:
    """コンポーネント設定を取得
    
    Args:
        key: 設定キー
        default: デフォルト値
        
    Returns:
        設定値
    """
    return COMPONENT_SETTINGS.get(key, default)


def set_component_setting(key: str, value: Any) -> None:
    """コンポーネント設定を設定（型チェック付き）
    
    Args:
        key: 設定キー
        value: 設定値
        
    Raises:
        TypeError: 型が不正な場合
        ValueError: 値が不正な場合
    """
    # Type validation
    if key in ['use_preheater', 'use_superheater'] and not isinstance(value, bool):
        raise TypeError(f"Setting '{key}' must be a boolean, got {type(value).__name__}")
    
    if key in ['preheater_params', 'superheater_params'] and not isinstance(value, dict):
        raise TypeError(f"Setting '{key}' must be a dictionary, got {type(value).__name__}")
    
    COMPONENT_SETTINGS[key] = value
    logger.debug(f"Component setting updated: {key} = {value}")


def validate_component_settings() -> None:
    """コンポーネント設定の包括的な妥当性チェック
    
    Raises:
        KeyError: 必要な設定が不足している場合
        TypeError: 型が不正な場合
        ValueError: 値が不正な場合
    """
    required_keys = ['use_preheater', 'use_superheater', 'preheater_params', 'superheater_params', 'optimization_settings']
    
    # Check for required keys
    for key in required_keys:
        if key not in COMPONENT_SETTINGS:
            raise KeyError(f"Missing required setting: {key}")
    
    # Type validation
    if not isinstance(COMPONENT_SETTINGS['use_preheater'], bool):
        raise TypeError("'use_preheater' must be a boolean")
    
    if not isinstance(COMPONENT_SETTINGS['use_superheater'], bool):
        raise TypeError("'use_superheater' must be a boolean")
    
    if not isinstance(COMPONENT_SETTINGS['preheater_params'], dict):
        raise TypeError("'preheater_params' must be a dictionary")
    
    if not isinstance(COMPONENT_SETTINGS['superheater_params'], dict):
        raise TypeError("'superheater_params' must be a dictionary")
    
    if not isinstance(COMPONENT_SETTINGS['optimization_settings'], dict):
        raise TypeError("'optimization_settings' must be a dictionary")
    
    # Value validation for optimization settings
    opt_settings = COMPONENT_SETTINGS['optimization_settings']
    if 'max_iterations' in opt_settings and opt_settings['max_iterations'] <= 0:
        raise ValueError("'max_iterations' must be positive")
    
    if 'tolerance' in opt_settings and opt_settings['tolerance'] <= 0:
        raise ValueError("'tolerance' must be positive")
    
    logger.info("Component settings validation passed")
