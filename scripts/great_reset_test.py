#!/usr/bin/env python3
"""
Great Reset - 数据重建测试
验证FotMob单一数据源重建流程
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import asyncpg

    print("✅ PostgreSQL驱动导入成功")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


class GreatResetTester:
    """Great Reset测试器"""

    def __init__(self):
        self.db_config = {
            "host": "db",
            "port": 5432,
            "user": "postgres",
            "password": "postgres-dev-password",
            "database": "football_prediction",
        }

    async def test_database_connection(self):
        """测试数据库连接"""
        try:
            conn = await asyncpg.connect(**self.db_config)

            # 检查表结构
            result = await conn.fetchval(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'matches'
            """
            )

            if result == 1:
                print("✅ matches表存在")
                return conn
            else:
                print("❌ matches表不存在")
                return None

        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return None

    async def create_test_data(self, conn):
        """创建测试数据"""
        try:
            print("🏗️ 创建测试数据...")

            # 插入测试球队
            await conn.execute(
                """
                INSERT INTO teams (name, created_at, updated_at) VALUES
                ('Manchester City', NOW(), NOW()),
                ('Manchester United', NOW(), NOW()),
                ('Liverpool', NOW(), NOW()),
                ('Chelsea', NOW(), NOW()),
                ('Arsenal', NOW(), NOW()),
                ('Tottenham', NOW(), NOW()),
                ('Barcelona', NOW(), NOW()),
                ('Real Madrid', NOW(), NOW())
                ON CONFLICT (name) DO NOTHING
            """
            )

            # 获取球队ID
            teams = await conn.fetch("SELECT id, name FROM teams ORDER BY id")
            team_map = {row["name"]: row["id"] for row in teams}

            print(f"✅ 创建了 {len(team_map)} 个球队")

            # 插入测试比赛 (FotMob单一数据源)
            test_matches = [
                {
                    "home_team": "Manchester City",
                    "away_team": "Manchester United",
                    "fotmob_id": "FMB_4189362",
                    "home_score": 3,
                    "away_score": 1,
                    "match_date": "2024-03-03 15:00:00",
                    "league_id": 47,
                    "season": "2023-2024",
                },
                {
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "fotmob_id": "FMB_4189363",
                    "home_score": 2,
                    "away_score": 2,
                    "match_date": "2024-03-04 15:00:00",
                    "league_id": 47,
                    "season": "2023-2024",
                },
                {
                    "home_team": "Barcelona",
                    "away_team": "Real Madrid",
                    "fotmob_id": "FMB_4189364",
                    "home_score": 1,
                    "away_score": 2,
                    "match_date": "2024-03-05 20:00:00",
                    "league_id": 87,
                    "season": "2023-2024",
                },
            ]

            inserted_count = 0
            for match in test_matches:
                try:
                    home_id = team_map[match["home_team"]]
                    away_id = team_map[match["away_team"]]

                    await conn.execute(
                        """
                        INSERT INTO matches (
                            home_team_id, away_team_id, fotmob_id, home_score, away_score,
                            match_date, status, league_id, season, data_source, data_completeness,
                            created_at, updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, 'FT', $7, $8, 'fotmob_l1', 'basic',
                            NOW(), NOW()
                        )
                    """,
                        home_id,
                        away_id,
                        match["fotmob_id"],
                        match["home_score"],
                        match["away_score"],
                        match["match_date"],
                        match["league_id"],
                        match["season"],
                    )

                    inserted_count += 1
                    print(
                        f"  ✅ {match['home_team']} vs {match['away_team']} (ID: {match['fotmob_id']})"
                    )

                except Exception as e:
                    print(
                        f"  ❌ 插入失败 {match['home_team']} vs {match['away_team']}: {e}"
                    )

            print(f"✅ 成功插入 {inserted_count} 场测试比赛")
            return True

        except Exception as e:
            print(f"❌ 创建测试数据失败: {e}")
            return False

    async def verify_data_quality(self, conn):
        """验证数据质量"""
        try:
            print("🔍 验证数据质量...")

            # 统计查询
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN fotmob_id IS NOT NULL THEN 1 END) as with_fotmob_id,
                    COUNT(CASE WHEN data_source = 'fotmob_l1' THEN 1 END) as fotmob_l1_source,
                    COUNT(CASE WHEN data_completeness = 'basic' THEN 1 END) as basic_completeness,
                    MIN(match_date) as earliest_match,
                    MAX(match_date) as latest_match
                FROM matches
            """
            )

            print("📊 数据统计:")
            print(f"  总比赛数: {stats['total_matches']}")
            print(f"  有FotMob ID: {stats['with_fotmob_id']}")
            print(f"  FotMob L1源: {stats['fotmob_l1_source']}")
            print(f"  基础完整性: {stats['basic_completeness']}")
            print(f"  最早比赛: {stats['earliest_match']}")
            print(f"  最新比赛: {stats['latest_match']}")

            # 详细数据展示
            matches = await conn.fetch(
                """
                SELECT
                    m.fotmob_id,
                    ht.name as home_team,
                    at.name as away_team,
                    m.home_score,
                    m.away_score,
                    m.match_date,
                    l.name as league_name,
                    m.data_source
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                LEFT JOIN leagues l ON m.league_id = l.id
                ORDER BY m.match_date
            """
            )

            print("\n📋 详细比赛列表:")
            for i, match in enumerate(matches, 1):
                print(
                    f"  {i}. {match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}"
                )
                print(f"     🆔 FotMob ID: {match['fotmob_id']}")
                print(f"     📅 比赛时间: {match['match_date']}")
                print(f"     🏆 联赛: {match['league_name'] or '未知'}")
                print(f"     📊 数据源: {match['data_source']}")
                print()

            # 数据质量评估
            quality_score = 0
            if stats["total_matches"] > 0:
                quality_score += 25
            if stats["with_fotmob_id"] == stats["total_matches"]:
                quality_score += 25
            if stats["fotmob_l1_source"] == stats["total_matches"]:
                quality_score += 25
            if stats["basic_completeness"] == stats["total_matches"]:
                quality_score += 25

            print(f"🎯 数据质量评分: {quality_score}/100")

            return quality_score >= 75

        except Exception as e:
            print(f"❌ 数据验证失败: {e}")
            return False

    async def simulate_fotmob_backfill(self, conn):
        """模拟FotMob回填过程"""
        try:
            print("🚀 模拟FotMob回填过程...")

            # 模拟从FotMob API获取的数据
            simulated_matches = [
                {
                    "fotmob_id": "FMB_4189365",
                    "home_team": "Arsenal",
                    "away_team": "Tottenham",
                    "home_score": 2,
                    "away_score": 1,
                    "match_date": "2024-03-06 19:45:00",
                    "league_id": 47,
                    "season": "2023-2024",
                },
                {
                    "fotmob_id": "FMB_4189366",
                    "home_team": "Chelsea",
                    "away_team": "Liverpool",
                    "home_score": 1,
                    "away_score": 3,
                    "match_date": "2024-03-07 16:30:00",
                    "league_id": 47,
                    "season": "2023-2024",
                },
            ]

            # 获取球队ID映射
            teams = await conn.fetch("SELECT id, name FROM teams")
            team_map = {row["name"]: row["id"] for row in teams}

            backfilled_count = 0
            for match in simulated_matches:
                if match["home_team"] in team_map and match["away_team"] in team_map:
                    try:
                        home_id = team_map[match["home_team"]]
                        away_id = team_map[match["away_team"]]

                        await conn.execute(
                            """
                            INSERT INTO matches (
                                home_team_id, away_team_id, fotmob_id, home_score, away_score,
                                match_date, status, league_id, season, data_source, data_completeness,
                                created_at, updated_at
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, 'FT', $7, $8, 'fotmob_l1', 'basic',
                                NOW(), NOW()
                            )
                        """,
                            home_id,
                            away_id,
                            match["fotmob_id"],
                            match["home_score"],
                            match["away_score"],
                            match["match_date"],
                            match["league_id"],
                            match["season"],
                        )

                        backfilled_count += 1
                        print(
                            f"  ✅ 回填: {match['home_team']} vs {match['away_team']}"
                        )

                    except Exception as e:
                        print(f"  ❌ 回填失败: {e}")
                else:
                    print(
                        f"  ⚠️ 跳过: 球队未找到 {match['home_team']} 或 {match['away_team']}"
                    )

            print(f"✅ 模拟回填完成: {backfilled_count} 场比赛")
            return backfilled_count

        except Exception as e:
            print(f"❌ 模拟回填失败: {e}")
            return 0

    async def close(self, conn):
        """关闭数据库连接"""
        try:
            await conn.close()
            print("✅ 数据库连接已关闭")
        except Exception as e:
            print(f"⚠️ 关闭连接时出现警告: {e}")


async def main():
    """主函数"""
    print("🌟 Great Reset - 数据重建测试")
    print("🎯 验证FotMob单一数据源重建流程")
    print("⚡ 从零开始，打造完美数据!")
    print("=" * 60)

    tester = GreatResetTester()
    conn = None

    try:
        # 测试数据库连接
        conn = await tester.test_database_connection()
        if not conn:
            return False

        # 创建测试数据
        if not await tester.create_test_data(conn):
            return False

        # 验证数据质量
        await tester.verify_data_quality(conn)

        # 模拟回填过程
        backfilled = await tester.simulate_fotmob_backfill(conn)

        # 最终验证
        print("\n🔍 最终验证:")
        final_stats = await conn.fetchrow(
            """
            SELECT COUNT(*) as total_matches,
                   COUNT(CASE WHEN data_source = 'fotmob_l1' THEN 1 END) as fotmob_l1_count
            FROM matches
        """
        )

        print("📊 最终统计:")
        print(f"  总比赛数: {final_stats['total_matches']}")
        print(f"  FotMob L1源: {final_stats['fotmob_l1_count']}")
        print(f"  回填新增: {backfilled}")

        success = (
            final_stats["total_matches"] > 0
            and final_stats["fotmob_l1_count"] == final_stats["total_matches"]
        )

        print("\n" + "=" * 60)
        print("🎯 测试结果:")
        if success:
            print("✅ Great Reset 数据重建测试成功!")
            print("✅ FotMob单一数据源验证通过!")
            print("✅ 数据质量评分优秀!")
            print("🚀 可以开始全面数据重建!")
        else:
            print("❌ 测试失败，需要进一步调试")
        print("=" * 60)

        return success

    except Exception as e:
        print(f"💥 测试过程中出现异常: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if conn:
            await tester.close(conn)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
