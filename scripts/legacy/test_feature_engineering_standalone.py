#!/usr/bin/env python3
"""
特征工程模块独立测试脚本
Standalone test script for feature engineering module
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from ml.feature_engineering import FeatureTransformer


def test_feature_transformer():
    """测试FeatureTransformer的所有功能"""
    print("=== FeatureTransformer 完整功能测试 ===\n")

    # 创建转换器
    transformer = FeatureTransformer()
    print("✅ 1. 初始化测试通过")

    # 创建测试数据
    test_data = pd.DataFrame(
        {
            "match_id": [1, 2, 3, 4, 5],
            "home_odds": [2.50, 1.80, 3.20, 1.45, 2.10],
            "away_odds": [2.80, 4.50, 2.30, 6.80, 3.40],
            "draw_odds": [3.20, 3.60, 2.90, 4.20, 3.15],
            "home_goals_last_5": [8, 12, 6, 15, 9],
            "away_goals_last_5": [7, 5, 8, 4, 11],
        }
    )
    print("✅ 2. 测试数据创建完成")

    # 测试隐含概率计算
    home_prob = transformer._calculate_implied_probability(2.50)
    assert home_prob == 0.40, f"期望0.40，实际{home_prob}"
    print("✅ 3. 隐含概率计算测试通过")

    # 测试赔率熵计算
    probs = [0.4, 0.3, 0.3]
    entropy = transformer._calculate_odds_entropy(probs)
    expected_entropy = -sum(p * np.log2(p) for p in probs)
    assert abs(entropy - expected_entropy) < 1e-10, "熵计算不正确"
    print("✅ 4. 赔率熵计算测试通过")

    # 测试完整转换
    result = transformer.transform(test_data)
    assert len(result) == len(test_data), "行数不匹配"
    expected_features = [
        "Implied_Prob_Home",
        "Implied_Prob_Away",
        "Odds_Entropy",
        "Avg_Goals_Diff_L5",
    ]
    for feature in expected_features:
        assert feature in result.columns, f"缺少特征: {feature}"
    print("✅ 5. 完整转换测试通过")

    # 验证特征值范围
    assert all(result["Implied_Prob_Home"] > 0) and all(
        result["Implied_Prob_Home"] <= 1
    )
    assert all(result["Implied_Prob_Away"] > 0) and all(
        result["Implied_Prob_Away"] <= 1
    )
    assert all(result["Odds_Entropy"] > 0)
    print("✅ 6. 特征值范围验证通过")

    # 验证输出
    assert transformer.validate_output(result), "输出验证失败"
    print("✅ 7. 输出验证测试通过")

    # 错误处理测试
    try:
        invalid_data = pd.DataFrame(
            {
                "match_id": [1, 2],
                "home_odds": [2.50, -1.80],  # 负赔率
                "away_odds": [2.80, 4.50],
                "draw_odds": [3.20, 3.60],
                "home_goals_last_5": [8, 12],
                "away_goals_last_5": [7, 5],
            }
        )
        transformer.transform(invalid_data)
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "赔率不能为负数" in str(e)
        print("✅ 8. 错误处理测试通过")

    print("\n🎉 所有测试通过！FeatureTransformer 功能正常！")

    # 显示转换结果示例
    print("\n=== 转换结果示例 ===")
    display_cols = [
        "match_id",
        "Implied_Prob_Home",
        "Implied_Prob_Away",
        "Odds_Entropy",
        "Avg_Goals_Diff_L5",
    ]
    print(result[display_cols].round(4))

    # 显示特征描述
    print("\n=== 特征描述 ===")
    for name, desc in transformer.get_feature_descriptions().items():
        print(f"{name}: {desc}")


if __name__ == "__main__":
    test_feature_transformer()
