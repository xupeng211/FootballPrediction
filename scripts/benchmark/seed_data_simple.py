#!/usr/bin/env python3
"""简化版P1-7压测数据生成器
Simplified Benchmark Data Seeding Script for P1-7.

Author: Claude Code
Version: 1.0.0
"""

import asyncio
import json
import random
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

# 添加项目路径
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from src.database.async_manager import get_db_session


class SimpleBenchmarkDataSeeder:
    """简化压测数据生成器."""

    def __init__(self):
        """初始化数据生成器."""
        self.teams = []
        self.matches = []

    async def generate_teams(self, count: int = 50) -> list[dict[str, Any]]:
        """生成球队数据."""
        print(f"🏆 生成 {count} 个球队...")

        teams = []
        for i in range(1, count + 1):
            team = {
                "id": i,
                "name": f"Team {chr(64 + i % 26)}{chr(65 + i % 26)}{i}",
                "short_name": f"T{i:02d}",
                "country": random.choice(["England", "Spain", "Germany", "Italy", "France"]),
                "founded": random.randint(1880, 2020),
                "stadium_capacity": random.randint(20000, 80000),
                "market_value": random.randint(50_000_000, 500_000_000)
            }
            teams.append(team)

        self.teams = teams
        print(f"✅ 生成 {len(teams)} 个球队")
        return teams

    async def save_teams_to_db(self, teams: list[dict[str, Any]]) -> int:
        """保存球队到数据库."""
        print("💾 保存球队到数据库...")

        async with get_db_session() as session:
            success_count = 0

            for team in teams:
                try:
                    # 检查球队是否已存在
                    result = await session.execute(
                        "SELECT id FROM teams WHERE id = %s", (team["id"],)
                    )
                    if result.fetchone():
                        continue  # 已存在，跳过

                    # 插入新球队
                    await session.execute(
                        """
                        INSERT INTO teams (id, name, short_name, country, founded,
                                         stadium_capacity, market_value, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            team["id"],
                            team["name"],
                            team["short_name"],
                            team["country"],
                            team["founded"],
                            team["stadium_capacity"],
                            team["market_value"],
                            datetime.now(),
                            datetime.now()
                        )
                    )
                    success_count += 1

                except Exception as e:
                    print(f"   ⚠️ 保存球队 {team['id']} 失败: {e}")

            await session.commit()

        print(f"✅ 成功保存 {success_count} 个球队")
        return success_count

    async def generate_matches(self, count: int = 1000) -> list[dict[str, Any]]:
        """生成比赛数据."""
        print(f"⚽ 生成 {count} 场比赛...")

        if not self.teams:
            await self.generate_teams()

        matches = []
        seasons = [2021, 2022, 2023, 2024]
        competitions = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]

        start_date = datetime(2021, 1, 1)

        for i in range(1, count + 1):
            # 随机选择主客队
            home_team = random.choice(self.teams)
            away_team = random.choice([t for t in self.teams if t["id"] != home_team["id"]])

            # 生成比赛日期
            match_date = start_date + timedelta(days=random.randint(0, 1460))  # 4年内

            # 生成比赛结果（70%已完成比赛）
            if random.random() < 0.7:
                home_score = random.randint(0, 5)
                away_score = random.randint(0, 5)
                status = "completed"
                final_score = f"{home_score}-{away_score}"
            else:
                home_score = away_score = None
                status = "scheduled"
                final_score = None

            match = {
                "id": i,
                "home_team_id": home_team["id"],
                "away_team_id": away_team["id"],
                "season_id": random.choice(seasons),
                "competition": random.choice(competitions),
                "match_date": match_date.date(),
                "venue": f"{home_team['name']} Stadium",
                "home_score": home_score,
                "away_score": away_score,
                "final_score": final_score,
                "status": status,
                "attendance": random.randint(15000, 75000) if status == "completed" else None
            }
            matches.append(match)

        self.matches = matches
        print(f"✅ 生成 {len(matches)} 场比赛")
        return matches

    async def save_matches_to_db(self, matches: list[dict[str, Any]]) -> int:
        """保存比赛到数据库."""
        print("💾 保存比赛到数据库...")

        async with get_db_session() as session:
            success_count = 0
            batch_size = 50

            for i in range(0, len(matches), batch_size):
                batch = matches[i:i + batch_size]

                for match in batch:
                    try:
                        # 检查比赛是否已存在
                        result = await session.execute(
                            "SELECT id FROM matches WHERE id = %s", (match["id"],)
                        )
                        if result.fetchone():
                            continue  # 已存在，跳过

                        # 插入新比赛
                        await session.execute(
                            """
                            INSERT INTO matches (id, home_team_id, away_team_id, season_id,
                                              competition, match_date, venue,
                                              home_score, away_score, final_score, status,
                                              attendance, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (
                                match["id"],
                                match["home_team_id"],
                                match["away_team_id"],
                                match["season_id"],
                                match["competition"],
                                match["match_date"],
                                match["venue"],
                                match["home_score"],
                                match["away_score"],
                                match["final_score"],
                                match["status"],
                                match["attendance"],
                                datetime.now(),
                                datetime.now()
                            )
                        )
                        success_count += 1

                    except Exception as e:
                        print(f"   ⚠️ 保存比赛 {match['id']} 失败: {e}")

                await session.commit()
                print(f"   进度: {min(i + batch_size, len(matches))}/{len(matches)}")

        print(f"✅ 成功保存 {success_count} 场比赛")
        return success_count

    async def generate_simple_features(self, matches: list[dict[str, Any]]) -> int:
        """生成简单特征数据到JSON字段."""
        print(f"📊 生成 {len(matches)} 组特征数据...")

        async with get_db_session() as session:
            success_count = 0

            for match in matches:
                try:
                    # 生成基础特征
                    features = {
                        "home_team_form": round(random.uniform(0.0, 1.0), 3),
                        "away_team_form": round(random.uniform(0.0, 1.0), 3),
                        "home_team_recent_goals": round(random.uniform(0.5, 3.0), 2),
                        "away_team_recent_goals": round(random.uniform(0.5, 3.0), 2),
                        "h2h_home_wins": random.randint(0, 10),
                        "h2h_away_wins": random.randint(0, 10),
                        "home_win_odds": round(random.uniform(1.5, 4.0), 2),
                        "away_win_odds": round(random.uniform(1.8, 5.0), 2),
                        "draw_odds": round(random.uniform(2.5, 4.5), 2),
                        "momentum_factor": round(random.uniform(-0.5, 0.5), 3),
                        "fatigue_index": round(random.uniform(0.0, 1.0), 3),
                        "generated_at": datetime.now().isoformat(),
                        "feature_version": "v2.0"
                    }

                    # 将特征存储到matches表的features字段
                    await session.execute(
                        "UPDATE matches SET features = %s WHERE id = %s",
                        (json.dumps(features), match["id"])
                    )
                    success_count += 1

                except Exception as e:
                    print(f"   ⚠️ 保存特征 {match['id']} 失败: {e}")

            await session.commit()

        print(f"✅ 成功保存 {success_count} 组特征")
        return success_count

    async def generate_summary_report(self):
        """生成数据生成报告."""
        print("\n📋 生成数据摘要报告")
        print("-" * 50)

        report = {
            "generation_timestamp": datetime.now().isoformat(),
            "data_summary": {
                "teams_count": len(self.teams),
                "matches_count": len(self.matches),
                "seasons": sorted(list(set(m["season_id"] for m in self.matches))),
                "competitions": sorted(list(set(m["competition"] for m in self.matches))),
                "match_status": {
                    "completed": len([m for m in self.matches if m["status"] == "completed"]),
                    "scheduled": len([m for m in self.matches if m["status"] == "scheduled"])
                }
            },
            "generation_config": {
                "teams_target": 50,
                "matches_target": 1000,
                "completion_rate": random.uniform(0.7, 0.75)  # 70-75%完成率
            }
        }

        # 保存报告
        report_path = "/app/artifacts/benchmark_seeding_report.json"

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"   📊 球队数量: {report['data_summary']['teams_count']}")
            print(f"   📊 比赛数量: {report['data_summary']['matches_count']}")
            print(f"   📊 赛季分布: {report['data_summary']['seasons']}")
            print(f"   📊 比赛状态: {report['data_summary']['match_status']}")
            print(f"   ✅ 报告已保存: {report_path}")
        except Exception as e:
            print(f"   ⚠️ 报告保存失败: {e}")

        return report

    async def verify_data(self):
        """验证生成的数据."""
        print("\n🔍 验证生成的数据")
        print("-" * 50)

        async with get_db_session() as session:
            try:
                # 验证球队数据
                result = await session.execute("SELECT COUNT(*) FROM teams")
                teams_count = result.scalar()
                print(f"   📊 数据库球队数量: {teams_count}")

                # 验证比赛数据
                result = await session.execute("SELECT COUNT(*) FROM matches")
                matches_count = result.scalar()
                print(f"   📊 数据库比赛数量: {matches_count}")

                # 验证特征数据
                result = await session.execute("SELECT COUNT(*) FROM matches WHERE features IS NOT NULL")
                features_count = result.scalar()
                print(f"   📊 特征数据数量: {features_count}")

                # 验证赛季分布
                result = await session.execute("SELECT DISTINCT season_id FROM matches ORDER BY season_id")
                seasons = [row[0] for row in result.fetchall()]
                print(f"   📊 赛季分布: {seasons}")

                return teams_count > 0 and matches_count > 0

            except Exception as e:
                print(f"   ❌ 数据验证失败: {e}")
                return False

    async def run_seeding(self):
        """运行完整的数据生成流程."""
        print("🚀 开始P1-7压测数据生成 (简化版)")
        print("=" * 60)

        try:
            # 生成球队数据
            teams = await self.generate_teams(50)
            teams_saved = await self.save_teams_to_db(teams)

            # 生成比赛数据
            matches = await self.generate_matches(1000)
            matches_saved = await self.save_matches_to_db(matches)

            # 生成特征数据
            features_saved = await self.generate_simple_features(matches)

            # 生成报告
            report = await self.generate_summary_report()

            # 验证数据
            verification_passed = await self.verify_data()

            # 总结结果
            print("\n" + "=" * 60)
            print("🎯 数据生成结果总结")
            print("=" * 60)

            print(f"✅ 球队数据: {teams_saved}/{len(teams)} 成功")
            print(f"✅ 比赛数据: {matches_saved}/{len(matches)} 成功")
            print(f"✅ 特征数据: {features_saved}/{len(matches)} 成功")
            print(f"✅ 数据验证: {'通过' if verification_passed else '失败'}")

            overall_success = (
                teams_saved > 0 and
                matches_saved > 0 and
                features_saved > 0 and
                verification_passed
            )

            print(f"\n🏆 总体状态: {'✅ 全部成功' if overall_success else '⚠️ 部分失败'}")

            if report:
                print("📊 详细报告: artifacts/benchmark_seeding_report.json")

            return overall_success

        except Exception as e:
            print(f"\n❌ 数据生成过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数."""
    seeder = SimpleBenchmarkDataSeeder()
    success = await seeder.run_seeding()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
