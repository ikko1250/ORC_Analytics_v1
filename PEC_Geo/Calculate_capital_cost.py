def calculate_geothermal_payback(
    plant_capacity_kw: float = 20,      # 発電所規模 [kW]
    capital_cost_per_kw: float = 1700000,  # 資本費単価 [円/kW]
    om_cost_per_kw: float = 19000,         # 運転維持費 [円/kW/年]
    electricity_price: float = 40,          # 売電価格 [円/kWh]
    capacity_factor: float = 0.43          # 暦日利用率
) -> dict:
    """
    地熱発電所の資本費回収年数を計算する関数
    
    Returns:
        dict: 計算結果を含む辞書
    """
    # 1. 総資本費の計算
    total_capital_cost = plant_capacity_kw * capital_cost_per_kw
    
    # 2. 年間運転維持費の計算
    annual_om_cost = plant_capacity_kw * om_cost_per_kw
    
    # 3. 年間発電電力量の計算
    annual_power_generation = (
        plant_capacity_kw * 24 * 365 * capacity_factor
    )
    
    # 4. 年間売電収入の計算
    annual_revenue = annual_power_generation * electricity_price
    
    # 5. 年間純収入の計算
    annual_net_income = annual_revenue - annual_om_cost
    
    # 6. 資本費回収年数の計算
    payback_years = total_capital_cost / annual_net_income
    
    # 結果を辞書にまとめる
    results = {
        "総資本費": total_capital_cost,
        "年間運転維持費": annual_om_cost,
        "年間発電電力量": annual_power_generation,
        "年間売電収入": annual_revenue,
        "年間純収入": annual_net_income,
        "資本費回収年数": payback_years
    }
    
    return results

# 計算例
if __name__ == "__main__":
    results = calculate_geothermal_payback()
    
    # 結果の表示
    print("計算結果:")
    for key, value in results.items():
        if key == "年間発電電力量":
            print(f"{key}: {value:,.0f} kWh/年")
        elif key == "資本費回収年数":
            print(f"{key}: {value:.1f} 年")
        else:
            print(f"{key}: {value:,.0f} 円")
            # デフォルト値での計算 
