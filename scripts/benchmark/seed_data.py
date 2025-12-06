#!/usr/bin/env python3
"""P1-7 压测数据生成器
Benchmark Data Seeding Script for P1-7.

批量生成压测数据，包括比赛、球队、特征等数据。
Generates benchmark data including matches, teams, features, etc.

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

from src.database.async_manager import get_db_session, initialize_database
from src.features.feature_store import FootballFeatureStore


class BenchmarkDataSeeder:
    """压测数据生成器."""

    def __init__(self):
        """初始化数据生成器."""
        self.teams = []
        self.matches = []
        self.features = []
        self.feature_store = None

    async def setup(self):
        """设置生成环境."""
        print("🔧 初始化数据生成器...")

        # 初始化数据库
        print("   📊 初始化数据库...")
        await initialize_database()
        print("   ✅ 数据库初始化完成")

        # 初始化特征存储
        self.feature_store = FootballFeatureStore()
        await self.feature_store.initialize()
        print("✅ 特征存储初始化完成")

    async def generate_teams(self, count: int = 50) -> List[Dict[str, Any]]:
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
                "market_value": random.randint(50_000_000, 500_000_000),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            teams.append(team)

        self.teams = teams
        print(f"✅ 生成 {len(teams)} 个球队")
        return teams

    async def save_teams_to_db(self, teams: List[Dict[str, Any]]):
        """保存球队到数据库."""
        print("💾 保存球队到数据库...")

        async def save_single_team(team_data):
            async with get_db_session() as session:
                try:
                    # 检查球队是否已存在
                    result = await session.execute(
                        "SELECT id FROM teams WHERE id = %s", (team_data["id"],)
                    )
                    if result.fetchone():
                        return False  # 已存在

                    # 插入新球队
                    await session.execute(
                        """
                        INSERT INTO teams (id, name, short_name, country, founded,
                                         stadium_capacity, market_value, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            team_data["id"],
                            team_data["name"],
                            team_data["short_name"],
                            team_data["country"],
                            team_data["founded"],
                            team_data["stadium_capacity"],
                            team_data["market_value"],
                            team_data["created_at"],
                            team_data["updated_at"]
                        )
                    )
                    await session.commit()
                    return True
                except Exception as e:
                    print(f"   ⚠️ 保存球队 {team_data['id']} 失败: {e}")
                    await session.rollback()
                    return False

        # 并发保存球队
        tasks = [save_single_team(team) for team in teams]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        print(f"✅ 成功保存 {success_count}/{len(teams)} 个球队")
        return success_count

    async def generate_matches(self, count: int = 1000) -> List[Dict[str, Any]]:
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
            match_time = f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}"

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
                "home_team_name": home_team["name"],
                "away_team_name": away_team["name"],
                "season_id": random.choice(seasons),
                "competition": random.choice(competitions),
                "match_date": match_date.date().isoformat(),
                "match_time": match_time,
                "venue": f"{home_team['name']} Stadium",
                "home_score": home_score,
                "away_score": away_score,
                "final_score": final_score,
                "status": status,
                "attendance": random.randint(15000, 75000) if status == "completed" else None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            matches.append(match)

        self.matches = matches
        print(f"✅ 生成 {len(matches)} 场比赛")
        return matches

    async def save_matches_to_db(self, matches: List[Dict[str, Any]]):
        """保存比赛到数据库."""
        print("💾 保存比赛到数据库...")

        async def save_single_match(match_data):
            async with get_db_session() as session:
                try:
                    # 检查比赛是否已存在
                    result = await session.execute(
                        "SELECT id FROM matches WHERE id = %s", (match_data["id"],)
                    )
                    if result.fetchone():
                        return False  # 已存在

                    # 插入新比赛
                    await session.execute(
                        """
                        INSERT INTO matches (id, home_team_id, away_team_id, season_id,
                                          competition, match_date, match_time, venue,
                                          home_score, away_score, final_score, status,
                                          attendance, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            match_data["id"],
                            match_data["home_team_id"],
                            match_data["away_team_id"],
                            match_data["season_id"],
                            match_data["competition"],
                            match_data["match_date"],
                            match_data["match_time"],
                            match_data["venue"],
                            match_data["home_score"],
                            match_data["away_score"],
                            match_data["final_score"],
                            match_data["status"],
                            match_data["attendance"],
                            match_data["created_at"],
                            match_data["updated_at"]
                        )
                    )
                    await session.commit()
                    return True
                except Exception as e:
                    print(f"   ⚠️ 保存比赛 {match_data['id']} 失败: {e}")
                    await session.rollback()
                    return False

        # 分批保存比赛（避免过大的事务）
        batch_size = 50
        success_count = 0

        for i in range(0, len(matches), batch_size):
            batch = matches[i:i + batch_size]
            tasks = [save_single_match(match) for match in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_success = sum(1 for r in results if r is True)
            success_count += batch_success

            print(f"   进度: {min(i + batch_size, len(matches))}/{len(matches)} "
                  f"({batch_success}/{len(batch)} 成功)")

        print(f"✅ 成功保存 {success_count}/{len(matches)} 场比赛")
        return success_count

    async def generate_features(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成特征数据."""
        print(f"📊 生成 {len(matches)} 组特征数据...")

        features_list = []

        for match in matches:
            # 生成基础特征
            features = {
                "match_id": match["id"],
                "season_id": match["season_id"],
                "competition": match["competition"],

                # 主队特征
                "home_team_form": round(random.uniform(0.0, 1.0), 3),
                "home_team_recent_goals": round(random.uniform(0.5, 3.0), 2),
                "home_team_recent_conceded": round(random.uniform(0.3, 2.5), 2),
                "home_team_home_form": round(random.uniform(0.0, 1.0), 3),
                "home_team_injuries": random.randint(0, 5),
                "home_team_yellow_cards": random.randint(0, 10),
                "home_team_red_cards": random.randint(0, 3),

                # 客队特征
                "away_team_form": round(random.uniform(0.0, 1.0), 3),
                "away_team_recent_goals": round(random.uniform(0.5, 3.0), 2),
                "away_team_recent_conceded": round(random.uniform(0.3, 2.5), 2),
                "away_team_away_form": round(random.uniform(0.0, 1.0), 3),
                "away_team_injuries": random.randint(0, 5),
                "away_team_yellow_cards": random.randint(0, 10),
                "away_team_red_cards": random.randint(0, 3),

                # 历史对战特征
                "h2h_home_wins": random.randint(0, 10),
                "h2h_away_wins": random.randint(0, 10),
                "h2h_draws": random.randint(0, 5),
                "h2h_home_win_rate": round(random.uniform(0.2, 0.8), 3),
                "h2h_away_win_rate": round(random.uniform(0.1, 0.6), 3),
                "h2h_avg_goals": round(random.uniform(1.5, 4.0), 2),

                # 市场特征
                "home_win_odds": round(random.uniform(1.5, 4.0), 2),
                "draw_odds": round(random.uniform(2.5, 4.5), 2),
                "away_win_odds": round(random.uniform(1.8, 5.0), 2),
                "over_2_5_odds": round(random.uniform(1.6, 2.8), 2),
                "under_2_5_odds": round(random.uniform(1.4, 2.5), 2),

                # 比赛环境特征
                "day_of_week": random.randint(0, 6),
                "month": random.randint(1, 12),
                "is_weekend": random.choice([0, 1]),
                "venue_capacity": random.randint(20000, 80000),
                "travel_distance": round(random.uniform(10, 500), 1),

                # 高级统计特征
                "home_team_xg": round(random.uniform(0.8, 3.5), 2),
                "away_team_xg": round(random.uniform(0.6, 3.0), 2),
                "home_team_ppda": round(random.uniform(8.0, 15.0), 2),
                "away_team_ppda": round(random.uniform(8.0, 15.0), 2),
                "home_team_corsi": round(random.uniform(45, 65), 1),
                "away_team_corsi": round(random.randint(35, 60), 1),

                # 复杂特征
                "momentum_factor": round(random.uniform(-0.5, 0.5), 3),
                "fatigue_index": round(random.uniform(0.0, 1.0), 3),
                "weather_impact": round(random.uniform(0.8, 1.2), 2),
                "referee_strictness": round(random.uniform(0.0, 1.0), 3),

                # 元数据
                "generated_at": datetime.now().isoformat(),
                "feature_version": "v2.0",
                "data_quality_score": round(random.uniform(0.7, 1.0), 3)
            }

            features_list.append({
                "match_id": match["id"],
                "features": features,
                "metadata": {
                    "source": "benchmark_generator",
                    "generation_timestamp": datetime.now().isoformat(),
                    "feature_count": len(features)
                }
            })

        self.features = features_list
        print(f"✅ 生成 {len(features_list)} 组特征数据")
        return features_list

    async def save_features_to_store(self, features_list: List[Dict[str, Any]]):
        """保存特征到特征存储."""
        print("💾 保存特征到特征存储...")

        success_count = 0
        batch_size = 20  # 特征数据较大，使用小批次

        for i in range(0, len(features_list), batch_size):
            batch = features_list[i:i + batch_size]

            # 并发保存批次
            async def save_feature_data(feature_data):
                try:
                    await self.feature_store.save_features(
                        match_id=feature_data["match_id"],
                        features=feature_data["features"],
                        version="latest",
                        metadata=feature_data["metadata"]
                    )
                    return True
                except Exception as e:
                    print(f"   ⚠️ 保存特征 {feature_data['match_id']} 失败: {e}")
                    return False

            tasks = [save_feature_data(fd) for fd in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_success = sum(1 for r in results if r is True)
            success_count += batch_success

            print(f"   进度: {min(i + batch_size, len(features_list))}/{len(features_list)} "
                  f"({batch_success}/{len(batch)} 成功)")

        print(f"✅ 成功保存 {success_count}/{len(features_list)} 组特征")
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
                "features_count": len(self.features)
            },
            "data_distribution": {
                "seasons": sorted(list(set(m["season_id"] for m in self.matches))),
                "competitions": sorted(list(set(m["competition"] for m in self.matches))),
                "match_status": {
                    "completed": len([m for m in self.matches if m["status"] == "completed"]),
                    "scheduled": len([m for m in self.matches if m["status"] == "scheduled"])
                }
            },
            "feature_statistics": {
                "avg_features_per_match": len(self.features[0]["features"]) if self.features else 0,
                "feature_categories": [
                    "team_performance", "h2h_history", "market_odds",
                    "match_environment", "advanced_stats"
                ]
            },
            "generation_config": {
                "teams_target": 50,
                "matches_target": 1000,
                "batch_size_teams": 10,
                "batch_size_matches": 50,
                "batch_size_features": 20
            }
        }

        # 保存报告
        report_path = "/app/artifacts/benchmark_seeding_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"   📊 球队数量: {report['data_summary']['teams_count']}")
        print(f"   📊 比赛数量: {report['data_summary']['matches_count']}")
        print(f"   📊 特征数量: {report['data_summary']['features_count']}")
        print(f"   📊 赛季分布: {report['data_distribution']['seasons']}")
        print(f"   📊 比赛状态: {report['data_distribution']['match_status']}")
        print(f"   ✅ 报告已保存: {report_path}")

        return report

    async def cleanup(self):
        """清理资源."""
        print("\n🧹 清理生成器资源...")

        try:
            if self.feature_store:
                await self.feature_store.close()
            print("✅ 清理完成")
        except Exception as e:
            print(f"⚠️ 清理过程中出现错误: {e}")

    async def run_seeding(self):
        """运行完整的数据生成流程."""
        print("🚀 开始P1-7压测数据生成")
        print("=" * 60)

        try:
            # 设置环境
            await self.setup()

            # 生成球队数据
            teams = await self.generate_teams(50)
            teams_saved = await self.save_teams_to_db(teams)

            # 生成比赛数据
            matches = await self.generate_matches(1000)
            matches_saved = await self.save_matches_to_db(matches)

            # 生成特征数据
            features = await self.generate_features(matches)
            features_saved = await self.save_features_to_store(features)

            # 生成报告
            report = await self.generate_summary_report()

            # 总结结果
            print("\n" + "=" * 60)
            print("🎯 数据生成结果总结")
            print("=" * 60)

            print(f"✅ 球队数据: {teams_saved}/{len(teams)} 成功")
            print(f"✅ 比赛数据: {matches_saved}/{len(matches)} 成功")
            print(f"✅ 特征数据: {features_saved}/{len(features)} 成功")

            overall_success = (
                teams_saved == len(teams) and
                matches_saved == len(matches) and
                features_saved == len(features)
            )

            print(f"\n🏆 总体状态: {'✅ 全部成功' if overall_success else '⚠️ 部分失败'}")

            if report:
                print(f"📊 详细报告: artifacts/benchmark_seeding_report.json")

            return overall_success

        except Exception as e:
            print(f"\n❌ 数据生成过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await self.cleanup()


async def main():
    """主函数."""
    seeder = BenchmarkDataSeeder()
    success = await seeder.run_seeding()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # 设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())