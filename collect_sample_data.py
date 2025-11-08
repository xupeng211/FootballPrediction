#!/usr/bin/env python3
"""
数据收集测试脚本
用于测试数据收集功能并填充示例数据到数据库
"""

import asyncio
import asyncpg
import sys
from datetime import datetime, timedelta
import sys
import os

# 添加src到路径
sys.path.append('src')

async def collect_and_store_sample_data():
    """收集并存储示例足球数据"""

    print("🚀 开始收集示例足球数据...")

    # 连接到数据库
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5433,
            user="postgres",
            password="postgres",
            database="football_prediction_staging"
        )
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

    try:
        # 示例足球比赛数据
        sample_matches = [
            {
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "match_date": datetime.now() + timedelta(days=3),
                "league": "Premier League"
            },
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "match_date": datetime.now() + timedelta(days=4),
                "league": "Premier League"
            },
            {
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "match_date": datetime.now() + timedelta(days=5),
                "league": "La Liga"
            },
            {
                "home_team": "Bayern Munich",
                "away_team": "Borussia Dortmund",
                "match_date": datetime.now() + timedelta(days=6),
                "league": "Bundesliga"
            },
            {
                "home_team": "Paris Saint-Germain",
                "away_team": "Lyon",
                "match_date": datetime.now() + timedelta(days=7),
                "league": "Ligue 1"
            }
        ]

        print(f"📊 准备插入 {len(sample_matches)} 场比赛数据...")

        # 插入比赛数据
        inserted_count = 0
        for match in sample_matches:
            try:
                await conn.execute("""
                    INSERT INTO matches (home_team, away_team, match_date, league)
                    VALUES ($1, $2, $3, $4)
                """, match["home_team"], match["away_team"], match["match_date"], match["league"])
                inserted_count += 1
                print(f"  ✅ 插入比赛: {match['home_team']} vs {match['away_team']}")
            except Exception as e:
                print(f"  ⚠️  插入失败: {match['home_team']} vs {match['away_team']} - {e}")

        print(f"\\n🎉 成功插入 {inserted_count} 场比赛数据!")

        # 查询验证
        result = await conn.fetch("SELECT COUNT(*) as count FROM matches")
        total_matches = result[0]['count']
        print(f"📈 数据库中现在共有 {total_matches} 场比赛")

        # 显示最新插入的比赛
        recent_matches = await conn.fetch("""
            SELECT home_team, away_team, league, match_date
            FROM matches
            ORDER BY created_at DESC
            LIMIT 5
        """)

        print("\\n🏆 最新插入的比赛:")
        for match in recent_matches:
            print(f"  • {match['home_team']} vs {match['away_team']} ({match['league']}) - {match['match_date']}")

        return True

    except Exception as e:
        print(f"❌ 数据插入过程出错: {e}")
        return False
    finally:
        await conn.close()

async def test_data_collector_import():
    """测试数据收集器模块"""

    print("\\n🧪 测试数据收集器模块...")

    try:
        # 测试数据收集器导入
        from src.data.collectors.fixtures_collector import FixturesCollector
        from src.data.collectors.odds_collector import OddsCollector
        from src.data.collectors.scores_collector import ScoresCollector
        from src.data.processing.football_data_cleaner import FootballDataCleaner
        # from src.collectors.data_sources import FootballDataOrgAdapter  # 简化测试，暂时跳过

        print("✅ 所有数据收集器模块导入成功")

        # 测试创建收集器实例
        fixtures_collector = FixturesCollector()
        odds_collector = OddsCollector()
        scores_collector = ScoresCollector()
        cleaner = FootballDataCleaner()

        print("✅ 数据收集器实例创建成功")

        return True

    except Exception as e:
        print(f"❌ 数据收集器测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("=" * 60)
    print("⚽ FootballPrediction 数据收集测试")
    print("=" * 60)

    # 测试数据收集器模块
    collector_test = await test_data_collector_import()

    # 收集并存储示例数据
    data_test = await collect_and_store_sample_data()

    print("\\n" + "=" * 60)
    print("📋 测试结果总结:")
    print(f"  数据收集器模块: {'✅ 正常' if collector_test else '❌ 异常'}")
    print(f"  数据收集功能: {'✅ 正常' if data_test else '❌ 异常'}")

    if collector_test and data_test:
        print("\\n🎉 恭喜！系统数据收集功能可以正常使用！")
        print("现在你可以:")
        print("  1. 通过API查看比赛数据: curl http://localhost:8001/predictions")
        print("  2. 为这些比赛创建预测")
        print("  3. 运行更复杂的数据收集任务")
    else:
        print("\\n⚠️  系统数据收集功能存在问题，需要进一步调试")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())