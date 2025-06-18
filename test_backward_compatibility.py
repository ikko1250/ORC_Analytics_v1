"""後方互換性テスト

新しいコンポーネント機能が無効な場合、従来通りの計算が行われることを確認します。
"""

import sys
sys.path.append('/home/ubuntu/cur/program/seminar_fresh')

from ORC_analysis.config import COMPONENT_SETTINGS, set_component_setting
from ORC_analysis.ORC_Analysis import calculate_orc_performance_from_heat_source


def test_backward_compatibility():
    """後方互換性のテスト"""
    print("=== 後方互換性テスト ===")
    
    # コンポーネント設定を確認（デフォルトはFalse）
    print(f"use_preheater: {COMPONENT_SETTINGS['use_preheater']}")
    print(f"use_superheater: {COMPONENT_SETTINGS['use_superheater']}")
    
    # 従来通りのパラメータで計算（温度を調整）
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=393.15,  # 120°C (R245faの臨界温度以下)
        Vdot_htf=0.01,    # m³/s
        T_cond=305.15,    # 32°C
        eta_pump=0.75,
        eta_turb=0.80,
        superheat_C=5.0,  # 過熱度を小さく
    )
    
    if result:
        print(f"\n従来通りの計算結果:")
        print(f"正味出力: {result['W_net [kW]']:.2f} kW")
        print(f"熱効率: {result['η_th [-]']:.3f}")
        print(f"予熱器使用: {result['use_preheater']}")
        print(f"過熱器使用: {result['use_superheater']}")
        print(f"予熱器電力: {result.get('Q_preheater_kW', 0):.2f} kW")
        print(f"過熱器電力: {result.get('Q_superheater_kW', 0):.2f} kW")
        
        # 新しい機能が無効化されていることを確認
        assert result['use_preheater'] == False, "予熱器が意図せず有効になっています"
        assert result['use_superheater'] == False, "過熱器が意図せず有効になっています"
        assert result.get('Q_preheater_kW', 0) == 0, "予熱器電力が0でありません"
        assert result.get('Q_superheater_kW', 0) == 0, "過熱器電力が0でありません"
        
        print("\n✓ 後方互換性テスト: 成功")
        return True
    else:
        print("✗ 計算に失敗しました")
        return False


def test_component_activation():
    """コンポーネント有効化のテスト"""
    print("\n=== コンポーネント有効化テスト ===")
    
    # 過熱器を有効化
    set_component_setting('use_superheater', True)
    
    result = calculate_orc_performance_from_heat_source(
        T_htf_in=393.15,  # 120°C (R245faの臨界温度以下)
        Vdot_htf=0.01,    # m³/s
        T_cond=305.15,    # 32°C
        eta_pump=0.75,
        eta_turb=0.80,
        superheat_C=5.0,  # 過熱度を小さく
    )
    
    if result:
        print(f"過熱器有効時の計算結果:")
        print(f"正味出力: {result['W_net [kW]']:.2f} kW")
        print(f"過熱器使用: {result['use_superheater']}")
        print(f"過熱器電力: {result.get('Q_superheater_kW', 0):.2f} kW")
        
        # 過熱器が有効化されていることを確認
        assert result['use_superheater'] == True, "過熱器が有効になっていません"
        
        print("✓ コンポーネント有効化テスト: 成功")
        
        # 設定を元に戻す
        set_component_setting('use_superheater', False)
        return True
    else:
        print("✗ 計算に失敗しました")
        return False


if __name__ == "__main__":
    success1 = test_backward_compatibility()
    success2 = test_component_activation()
    
    if success1 and success2:
        print("\n" + "="*50)
        print("✓ すべてのテストが成功しました")
        print("従来通りの計算が正常に動作し、新機能も正しく制御されています")
    else:
        print("\n" + "="*50)
        print("✗ テストに失敗しました")