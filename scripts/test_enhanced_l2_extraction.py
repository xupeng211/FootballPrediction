#!/usr/bin/env python3
"""
测试升级后的L2数据提取功能

验证新增的赔率和球员评分提取方法是否能正确工作。
测试使用现有的fotmob_match_data.json文件。
"""

import sys
import logging
from pathlib import Path
import json
from typing import Dict, Any

# 设置项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入升级后的collector
try:
    from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
    logger.info("✅ EnhancedFotMobCollector 导入成功")
except ImportError as e:
    logger.error(f"❌ EnhancedFotMobCollector 导入失败: {e}")
    sys.exit(1)


def test_odds_extraction():
    """测试赔率数据提取功能"""
    logger.info("💰 测试赔率数据提取功能...")

    try:
        # 创建collector实例
        collector = EnhancedFotMobCollector()

        # 加载测试数据
        test_data_path = project_root / "fotmob_match_data.json"
        if not test_data_path.exists():
            logger.error(f"❌ 测试数据文件不存在: {test_data_path}")
            return False

        with open(test_data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        logger.info(f"✅ 成功加载测试数据: {test_data_path}")

        # 提取content部分
        if "content" not in test_data:
            logger.error("❌ 测试数据中缺少content字段")
            return False

        content = test_data["content"]

        # 测试赔率提取
        odds_data = collector._extract_odds(content)

        logger.info("📊 赔率提取结果:")
        for key, value in odds_data.items():
            logger.info(f"   {key}: {value}")

        # 验证结果
        if odds_data["pre_match_home_odds"]:
            logger.info("✅ 成功提取主队赔率")
        else:
            logger.warning("⚠️ 未找到主队赔率数据")

        if odds_data["home_win_probability"]:
            logger.info("✅ 成功计算主队获胜概率")
        else:
            logger.warning("⚠️ 未能计算获胜概率")

        # 检查数据质量
        valid_odds = sum([
            1 for v in [odds_data["pre_match_home_odds"], odds_data["pre_match_draw_odds"], odds_data["pre_match_away_odds"]]
            if v is not None and isinstance(v, (int, float)) and v > 1.0
        ])

        if valid_odds >= 2:
            logger.info(f"✅ 赔率数据质量良好: {valid_odds}/3 项有效")
            return True
        else:
            logger.warning(f"⚠️ 赔率数据质量不足: {valid_odds}/3 项有效")
            return False

    except Exception as e:
        logger.error(f"❌ 赔率提取测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_player_ratings_extraction():
    """测试球员评分提取功能"""
    logger.info("⭐ 测试球员评分提取功能...")

    try:
        # 创建collector实例
        collector = EnhancedFotMobCollector()

        # 加载测试数据
        test_data_path = project_root / "fotmob_match_data.json"
        with open(test_data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        # 提取content部分
        content = test_data["content"]

        # 测试球员评分提取
        ratings_data = collector._extract_player_ratings(content)

        logger.info("📊 球员评分提取结果:")
        logger.info(f"   总评分球员数: {ratings_data['total_players_rated']}")
        logger.info(f"   主队平均评分: {ratings_data['avg_home_rating']}")
        logger.info(f"   客队平均评分: {ratings_data['avg_away_rating']}")
        logger.info(f"   主队最佳球员: {ratings_data['best_home_player']}")
        logger.info(f"   客队最佳球员: {ratings_data['best_away_player']}")

        # 详细球员评分信息
        if ratings_data["home_team_ratings"]:
            logger.info(f"   主队评分球员数: {len(ratings_data['home_team_ratings'])}")
            # 显示前3名主队球员评分
            top_home_players = sorted(
                [p for p in ratings_data["home_team_ratings"] if p["rating"]],
                key=lambda x: x["rating"],
                reverse=True
            )[:3]
            for i, player in enumerate(top_home_players, 1):
                logger.info(f"     {i}. {player['player_name']}: {player['rating']}")

        if ratings_data["away_team_ratings"]:
            logger.info(f"   客队评分球员数: {len(ratings_data['away_team_ratings'])}")
            # 显示前3名客队球员评分
            top_away_players = sorted(
                [p for p in ratings_data["away_team_ratings"] if p["rating"]],
                key=lambda x: x["rating"],
                reverse=True
            )[:3]
            for i, player in enumerate(top_away_players, 1):
                logger.info(f"     {i}. {player['player_name']}: {player['rating']}")

        # 验证结果质量
        if ratings_data["total_players_rated"] > 0:
            logger.info(f"✅ 成功提取 {ratings_data['total_players_rated']} 名球员评分")

            # 检查评分合理性（评分通常在6-10之间）
            valid_ratings = []
            for team_ratings in [ratings_data["home_team_ratings"], ratings_data["away_team_ratings"]]:
                valid_ratings.extend([p["rating"] for p in team_ratings if p["rating"] and 6.0 <= p["rating"] <= 10.0])

            if len(valid_ratings) >= ratings_data["total_players_rated"] * 0.8:  # 80%的评分在合理范围
                logger.info("✅ 球员评分数据质量良好")
                return True
            else:
                logger.warning("⚠️ 部分球员评分超出合理范围")
                return False
        else:
            logger.warning("⚠️ 未找到任何球员评分数据")
            return False

    except Exception as e:
        logger.error(f"❌ 球员评分提取测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_data_quality_validation():
    """测试增强的数据质量验证功能"""
    logger.info("🔍 测试增强的数据质量验证功能...")

    try:
        # 创建collector实例
        collector = EnhancedFotMobCollector()

        # 加载测试数据
        test_data_path = project_root / "fotmob_match_data.json"
        with open(test_data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        # 模拟match_id
        test_match_id = "test_123"

        # 测试数据质量验证（现在包含赔率和评分检查）
        is_valid = collector._validate_data_quality(test_data, test_match_id)

        if is_valid:
            logger.info("✅ 数据质量验证通过 - 包含新的L2特征")
            return True
        else:
            logger.warning("⚠️ 数据质量验证失败")
            return False

    except Exception as e:
        logger.error(f"❌ 数据质量验证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_workflow():
    """测试完整的工作流程"""
    logger.info("🔄 测试完整的增强L2提取工作流程...")

    try:
        # 创建collector实例
        collector = EnhancedFotMobCollector()

        # 加载测试数据
        test_data_path = project_root / "fotmob_match_data.json"
        with open(test_data_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        content = test_data["content"]
        test_match_id = "integration_test"

        # 1. 提取所有增强数据
        odds_data = collector._extract_odds(content)
        ratings_data = collector._extract_player_ratings(content)

        # 2. 生成集成报告
        logger.info("📋 L2增强数据集成报告:")
        logger.info(f"   比赛ID: {test_match_id}")
        logger.info(f"   赔率数据: {'✅ 可用' if any(odds_data.values()) else '❌ 不可用'}")
        logger.info(f"   球员评分: {'✅ 可用' if ratings_data['total_players_rated'] > 0 else '❌ 不可用'}")

        # 3. 计算业务指标
        if odds_data["home_win_probability"]:
            logger.info(f"   主队获胜概率: {odds_data['home_win_probability']}%")

        if ratings_data["avg_home_rating"] and ratings_data["avg_away_rating"]:
            rating_diff = ratings_data["avg_home_rating"] - ratings_data["avg_away_rating"]
            logger.info(f"   评分差异: 主队{ratings_data['avg_home_rating']} vs 客队{ratings_data['avg_away_rating']} (差值: {rating_diff:+.2f})")

        # 4. 生成ML特征向量示例
        ml_features = {
            "has_odds_data": any(odds_data.values()),
            "has_ratings_data": ratings_data["total_players_rated"] > 0,
            "total_players": ratings_data["total_players_rated"],
            "home_rating_avg": ratings_data["avg_home_rating"] or 0,
            "away_rating_avg": ratings_data["avg_away_rating"] or 0,
            "rating_advantage": (ratings_data["avg_home_rating"] or 0) - (ratings_data["avg_away_rating"] or 0)
        }

        logger.info("🎯 ML特征向量示例:")
        for feature, value in ml_features.items():
            logger.info(f"   {feature}: {value}")

        # 5. 验证数据完整性
        enhanced_features_count = sum([
            1 for v in [ml_features["has_odds_data"], ml_features["has_ratings_data"]] if v
        ])

        if enhanced_features_count >= 1:
            logger.info(f"✅ L2增强数据集成成功: {enhanced_features_count}/2 类特征可用")
            return True
        else:
            logger.warning("⚠️ L2增强数据集成失败")
            return False

    except Exception as e:
        logger.error(f"❌ 集成工作流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数 - 运行所有测试"""
    logger.info("🚀 开始测试升级后的L2数据提取功能")
    logger.info("=" * 80)

    # 运行所有测试
    tests = [
        ("赔率数据提取", test_odds_extraction),
        ("球员评分提取", test_player_ratings_extraction),
        ("增强数据质量验证", test_enhanced_data_quality_validation),
        ("完整工作流程", test_integration_workflow)
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n--- 开始测试 {test_name} ---")
        try:
            if test_func():
                passed_tests += 1
                logger.info(f"--- {test_name} 测试通过 ✅ ---")
            else:
                logger.error(f"--- {test_name} 测试失败 ❌ ---")
        except Exception as e:
            logger.error(f"--- {test_name} 测试异常 ❌: {e} ---")

    # 测试总结
    logger.info("\n" + "=" * 80)
    logger.info(f"📊 测试总结: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        logger.info("🎉 所有测试通过！L2增强数据提取功能升级成功！")
        logger.info("📈 新功能:")
        logger.info("   ✅ 赔率数据提取 - 支持多种赔率数据源")
        logger.info("   ✅ 球员评分提取 - 从playerStats提取FotMob评分")
        logger.info("   ✅ 隐含概率计算 - 赔率转概率")
        logger.info("   ✅ 增强数据质量验证 - 4类特征检查")
        logger.info("🚀 准备集成到生产ML流程中！")
        return True
    else:
        logger.error(f"❌ {total_tests - passed_tests} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)