#!/usr/bin/env python3
"""
Football-Data.org API 集成测试脚本
Test script for Football-Data.org API integration
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

# 设置环境变量
os.environ["FOOTBALL_DATA_API_KEY"] = "ed809154dc1f422da46a18d8961a98a0"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:enhanced_db_password_2024@localhost:5433/football_prediction_staging"
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_api_connection():
    """测试API连接"""
    try:
        from src.collectors.match_collector import MatchCollector

        async with MatchCollector() as collector:
            logger.info("✅ 测试API连接...")

            # 测试获取联赛信息
            competitions = await collector.fetch_competitions()
            logger.info(f"✅ 获取到 {len(competitions)} 个联赛")

            # 测试获取英超球队
            teams = await collector.fetch_teams("2021")  # Premier League ID
            logger.info(f"✅ 获取到 {len(teams)} 支英超球队")

            # 测试获取即将开始的比赛
            upcoming_matches = await collector.collect_upcoming_matches(days_ahead=3)
            logger.info(f"✅ 获取到 {len(upcoming_matches)} 场即将开始的比赛")

            # 测试获取最近的比赛结果
            recent_matches = await collector.collect_recent_matches(days_back=7)
            logger.info(f"✅ 获取到 {len(recent_matches)} 场最近的比赛结果")

            return True

    except Exception as e:
        logger.error(f"❌ API连接测试失败: {e}")
        return False


async def test_data_normalization():
    """测试数据标准化"""
    try:
        from src.collectors.match_collector import MatchCollector

        async with MatchCollector() as collector:
            logger.info("✅ 测试数据标准化...")

            # 获取即将开始的比赛
            upcoming_matches = await collector.collect_upcoming_matches(days_ahead=1)

            if upcoming_matches:
                # 标准化前几场比赛
                for i, match in enumerate(upcoming_matches[:3]):
                    normalized = collector.normalize_match_data(match)
                    logger.info(
                        f"✅ 比赛 {i+1} 标准化成功: {normalized.get('match_title', 'Unknown')}"
                    )

            return True

    except Exception as e:
        logger.error(f"❌ 数据标准化测试失败: {e}")
        return False


async def test_database_model():
    """测试数据库模型"""
    try:
        from src.models.external.match import ExternalMatch

        logger.info("✅ 测试数据库模型...")

        # 创建测试数据
        test_data = {
            "id": "test_12345",
            "utcDate": "2025-12-01T20:00:00Z",
            "status": "SCHEDULED",
            "matchday": 15,
            "stage": "REGULAR_SEASON",
            "homeTeam": {
                "id": 57,
                "name": "Arsenal FC",
                "shortName": "Arsenal",
                "crest": "https://example.com/arsenal.png",
            },
            "awayTeam": {
                "id": 58,
                "name": "Aston Villa FC",
                "shortName": "Aston Villa",
                "crest": "https://example.com/astonvilla.png",
            },
            "score": {"fullTime": {"home": None, "away": None}, "winner": None},
            "competition": {"id": 2021, "name": "Premier League", "code": "PL"},
            "lastUpdated": "2025-10-31T10:00:00Z",
        }

        # 从API数据创建模型
        match_model = ExternalMatch.from_api_data(test_data)

        logger.info(f"✅ 创建比赛模型成功: {match_model.match_title}")
        logger.info(f"   外部ID: {match_model.external_id}")
        logger.info(f"   比赛时间: {match_model.match_date}")
        logger.info(f"   状态: {match_model.status}")

        # 测试转换为字典
        match_dict = match_model.to_dict()
        logger.info(f"✅ 转换为字典成功，包含 {len(match_dict)} 个字段")

        return True

    except Exception as e:
        logger.error(f"❌ 数据库模型测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始 Football-Data.org API 集成测试")
    print("=" * 60)

    start_time = datetime.now()

    tests = [
        ("API连接测试", test_api_connection),
        ("数据标准化测试", test_data_normalization),
        ("数据库模型测试", test_database_model),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n🔍 执行 {test_name}...")
        try:
            if await test_func():
                print(f"✅ {test_name} 通过")
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            failed += 1

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("📊 测试完成!")
    print(f"   通过: {passed}")
    print(f"   失败: {failed}")
    print(f"   总计: {passed + failed}")
    print(f"   耗时: {duration.total_seconds():.2f} 秒")

    if failed == 0:
        print("🎉 所有测试通过！Football-Data.org API 集成基础功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关实现")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
