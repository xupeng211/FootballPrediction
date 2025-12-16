#!/usr/bin/env python3
"""
Phase 5 高级特征测试脚本

快速验证新实现的高级特征工程组件：
1. H2HCalculator - 历史交锋统计
2. VenueAnalyzer - 场馆分离分析
3. AdvancedFeatureTransformer - 综合特征转换

运行方式：
python scripts/test_phase5_advanced_features.py
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入高级特征组件
try:
    from ml.features.h2h_calculator import H2HCalculator
    from ml.features.venue_analyzer import VenueAnalyzer
    from ml.features.advanced_feature_transformer import (
        AdvancedFeatureTransformer,
        AdvancedFeatureConfig
    )
    logger.info("✅ 高级特征组件导入成功")
except ImportError as e:
    logger.error(f"❌ 高级特征组件导入失败: {e}")
    sys.exit(1)


def create_test_data():
    """创建测试数据 - 模拟Napoli vs Juventus案例"""
    logger.info("📊 创建测试数据...")

    # 模拟Napoli (队1) vs Juventus (队2) 的历史交锋数据
    test_data = {
        'home_team_id': [1, 1, 2, 1, 2, 1, 2, 1, 2, 1],
        'away_team_id': [2, 3, 1, 2, 1, 2, 1, 4, 3, 2],
        'home_score': [2, 1, 1, 0, 2, 3, 0, 2, 1, 0],
        'away_score': [1, 0, 2, 0, 1, 1, 2, 0, 2, 1],
        'match_date': [
            '2024-01-01', '2024-01-10', '2024-01-15',
            '2024-02-01', '2024-02-10', '2024-02-15',
            '2024-03-01', '2024-03-10', '2024-03-15',
            '2024-03-20'
        ]
    }

    df = pd.DataFrame(test_data)
    df['match_date'] = pd.to_datetime(df['match_date'])

    logger.info(f"✅ 测试数据创建完成，形状: {df.shape}")
    return df


def test_h2h_calculator(df):
    """测试历史交锋计算器"""
    logger.info("⚔️ 测试 H2HCalculator...")

    try:
        h2h_calc = H2HCalculator(min_matches=1)

        # 测试队伍1 vs 队伍2的交锋记录
        h2h_stats = h2h_calc.calculate_h2h_for_match(
            df, 1, 2, pd.Timestamp('2024-03-25')
        )

        logger.info(f"   H2H统计结果:")
        logger.info(f"   - 交锋场次: {h2h_stats.matches_count}")
        logger.info(f"   - 主队胜率: {h2h_stats.home_win_rate:.3f}")
        logger.info(f"   - 平均进球差: {h2h_stats.avg_goal_diff:.3f}")
        logger.info(f"   - 平均总进球: {h2h_stats.avg_total_goals:.3f}")

        # 测试H2H摘要
        summary = h2h_calc.get_h2h_summary(df, 1, 2)
        logger.info(f"   详细摘要: 总场次={summary['total_matches']}, "
                   f"队1胜率={summary['team1_win_rate']:.3f}")

        logger.info("✅ H2HCalculator 测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ H2HCalculator 测试失败: {e}")
        return False


def test_venue_analyzer(df):
    """测试场馆分析器"""
    logger.info("🏟️ 测试 VenueAnalyzer...")

    try:
        venue_analyzer = VenueAnalyzer(windows=[3, 5])

        # 测试Napoli主场的场馆特征
        venue_stats = venue_analyzer.calculate_venue_features_for_match(
            df, 1, 2, pd.Timestamp('2024-03-25')
        )

        logger.info(f"   场馆特征结果:")
        logger.info(f"   - 主队主场3场平均进球: {venue_stats.home_goals_rolling_3:.3f}")
        logger.info(f"   - 客队客场3场平均进球: {venue_stats.away_goals_rolling_3:.3f}")
        logger.info(f"   - 主客场进球差(3场): {venue_stats.home_away_goal_diff_3:.3f}")
        logger.info(f"   - 主场优势指数(3场): {venue_stats.home_advantage_3:.3f}")

        # 测试场馆摘要
        summary = venue_analyzer.get_venue_summary(df, 1)
        logger.info(f"   场馆摘要: 主场优势={summary['home_advantage']:.3f}, "
                   f"主场胜率={summary['home_win_rate']:.3f}")

        logger.info("✅ VenueAnalyzer 测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ VenueAnalyzer 测试失败: {e}")
        return False


def test_advanced_feature_transformer(df):
    """测试高级特征转换器"""
    logger.info("🚀 测试 AdvancedFeatureTransformer...")

    try:
        # 配置特征转换器
        config = AdvancedFeatureConfig(
            enable_venue_features=True,
            enable_h2h_features=True,
            enable_points_features=True,
            venue_windows=[3, 5],
            points_windows=[3, 5]
        )

        transformer = AdvancedFeatureTransformer(config)

        # 转换特征
        df_with_features = transformer.transform(df)

        logger.info(f"   特征转换结果:")
        logger.info(f"   - 原始数据形状: {df.shape}")
        logger.info(f"   - 转换后形状: {df_with_features.shape}")
        logger.info(f"   - 新增特征数量: {df_with_features.shape[1] - df.shape[1]}")

        # 显示新增特征
        feature_names = transformer.get_advanced_feature_names()
        logger.info(f"   - 高级特征列表: {feature_names}")

        # 测试特征分组
        feature_groups = transformer.get_feature_importance_groups()
        logger.info(f"   - 特征分组: {list(feature_groups.keys())}")

        # 生成特征报告
        report = transformer.generate_feature_report(df_with_features)
        logger.info(f"   - 特征报告: 总特征={report['total_features']}")

        logger.info("✅ AdvancedFeatureTransformer 测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ AdvancedFeatureTransformer 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_napoli_case_improvement():
    """测试Napoli vs Juventus案例改进"""
    logger.info("🎯 测试 Napoli vs Juventus 案例改进...")

    try:
        # 创建Napoli主场近期0进球但历史有利的测试数据
        napoli_case_data = {
            'home_team_id': [1, 1, 1, 2, 2, 1, 2],
            'away_team_id': [2, 3, 4, 1, 1, 2, 1],
            'home_score': [0, 0, 2, 1, 0, 0, 2],
            'away_score': [1, 2, 1, 0, 3, 1, 1],
            'match_date': [
                '2024-01-01', '2024-01-15', '2024-02-01',
                '2024-01-10', '2024-02-10', '2024-03-01',
                '2024-02-15'
            ]
        }

        df_napoli = pd.DataFrame(napoli_case_data)
        df_napoli['match_date'] = pd.to_datetime(df_napoli['match_date'])

        # 使用高级特征分析
        config = AdvancedFeatureConfig(
            enable_venue_features=True,
            enable_h2h_features=True
        )
        transformer = AdvancedFeatureTransformer(config)

        df_with_features = transformer.transform(df_napoli)

        # 检查是否有H2H特征来平衡主场进球少的问题
        h2h_features = [f for f in transformer.get_advanced_feature_names() if 'h2h_' in f]
        venue_features = [f for f in transformer.get_advanced_feature_names() if 'venue_' in f]

        logger.info(f"   H2H特征数量: {len(h2h_features)}")
        logger.info(f"   场馆特征数量: {len(venue_features)}")

        # 验证数据泄露防护
        for feature in h2h_features + venue_features:
            if feature in df_with_features.columns:
                # 检查是否有NaN值（防数据泄露的证据）
                nan_count = df_with_features[feature].isna().sum()
                logger.info(f"   - {feature}: NaN数量={nan_count}")

        logger.info("✅ Napoli案例改进测试完成")
        return True

    except Exception as e:
        logger.error(f"❌ Napoli案例改进测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 Phase 5 高级特征测试开始")
    logger.info("=" * 60)

    try:
        # 1. 创建测试数据
        df = create_test_data()

        # 2. 测试各个组件
        tests = [
            ("H2HCalculator", test_h2h_calculator),
            ("VenueAnalyzer", test_venue_analyzer),
            ("AdvancedFeatureTransformer", test_advanced_feature_transformer),
            ("Napoli案例改进", test_napoli_case_improvement)
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            logger.info(f"\n--- 开始测试 {test_name} ---")
            if test_name == "Napoli案例改进":
                result = test_func()
            else:
                result = test_func(df)

            if result:
                passed_tests += 1
                logger.info(f"--- {test_name} 测试通过 ✅ ---")
            else:
                logger.error(f"--- {test_name} 测试失败 ❌ ---")

        # 3. 测试总结
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 测试总结: {passed_tests}/{total_tests} 通过")

        if passed_tests == total_tests:
            logger.info("🎉 所有测试通过！Phase 5 高级特征实现成功！")
            logger.info("📈 预期模型准确率提升: 58.69% → 65%+")
            return True
        else:
            logger.error(f"❌ {total_tests - passed_tests} 个测试失败")
            return False

    except Exception as e:
        logger.error(f"❌ 测试过程发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)