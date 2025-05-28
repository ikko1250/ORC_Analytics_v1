# ORCシステムのコンポーネント利用設定
# このファイルでpreheater/superheater等の利用有無やパラメータを一元管理します。

COMPONENT_SETTINGS = {
    'use_preheater': False,  # 予熱器を利用する場合はTrue
    'use_superheater': False,  # 過熱器を利用する場合はTrue
    'preheater_params': {
        # 例: 'Q_kW': 0.0, 'LMTD_K': 10.0
    },
    'superheater_params': {
        # 例: 'Q_kW': 0.0, 'LMTD_K': 20.0
    }
}

def get_component_setting(key, default=None):
    return COMPONENT_SETTINGS.get(key, default)

def set_component_setting(key, value):
    COMPONENT_SETTINGS[key] = value

def validate_component_settings():
    # 必要に応じて妥当性チェックを追加
    assert isinstance(COMPONENT_SETTINGS['use_preheater'], bool)
    assert isinstance(COMPONENT_SETTINGS['use_superheater'], bool)
    # 追加チェック可
