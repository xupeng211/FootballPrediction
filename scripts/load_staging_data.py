#!/usr/bin/env python3
"""
Staging 环境数据加载脚本
为 E2E 测试准备必要的测试数据
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Staging 环境配置
os.environ["TESTING"] = "true"
os.environ["TEST_ENV"] = "staging"


class StagingDataLoader:
    """Staging 环境数据加载器"""

    def __init__(self):
        self.created_data = {}

    async def create_leagues_and_teams(self):
        """创建联赛和队伍数据"""
        logger.info("创建联赛和队伍数据...")

        # 联赛数据
        leagues = [
            {
                "name": "Staging Premier League",
                "country": "Stageland",
                "level": 1,
                "teams_count": 20,
                "season": "2024/2025",
                "start_date": "2024-08-01",
                "end_date": "2025-05-31",
            },
            {
                "name": "Staging Championship",
                "country": "Stageland",
                "level": 2,
                "teams_count": 24,
                "season": "2024/2025",
                "start_date": "2024-08-01",
                "end_date": "2025-05-31",
            },
            {
                "name": "Staging Cup",
                "country": "Stageland",
                "level": 3,
                "teams_count": 16,
                "season": "2024/2025",
                "start_date": "2024-09-01",
                "end_date": "2025-05-15",
            },
        ]

        # 队伍数据
        teams = []
        team_names = [
            "Staging City FC",
            "Staging United",
            "Staging Athletic",
            "Staging Rangers",
            "Staging Wanderers",
            "Staging Royals",
            "Staging Lions",
            "Staging Eagles",
            "Staging Tigers",
            "Staging Bears",
            "Staging Wolves",
            "Staging Foxes",
            "Staging Sharks",
            "Staging Dolphins",
            "Staging Whales",
            "Staging Hawks",
            "Staging Falcons",
            "Staging Eagles",
            "Staging Owls",
            "Staging Swans",
            "Staging Dragons",
            "Staging Phoenix",
            "Staging Griffins",
            "Staging Unicorns",
            "Staging Lions II",
            "Staging Tigers II",
            "Staging Bears II",
        ]

        cities = [
            "Staging City",
            "North Staging",
            "South Staging",
            "East Staging",
            "West Staging",
            "Central Staging",
            "Port Staging",
            "Staging Harbor",
            "Staging Valley",
            "Staging Heights",
            "Staging Park",
            "Staging Gardens",
            "Staging Hills",
            "Staging Woods",
            "Staging Lake",
            "Staging River",
            "Staging Mountain",
            "Staging Plains",
            "Staging Fields",
            "Staging Forest",
        ]

        for i, name in enumerate(team_names):
            team = {
                "name": name,
                "city": cities[i % len(cities)],
                "founded": 1990 + (i % 30),
                "stadium": f"{name} Stadium",
                "capacity": 20000 + (i * 1000),
                "manager": f"Manager {i}",
                "colors": ["#FF0000", "#0000FF"][: 1 + (i % 2)],
                "founded_year": 1990 + (i % 30),
            }
            teams.append(team)

        self.created_data["leagues"] = leagues
        self.created_data["teams"] = teams

        logger.info(f"创建了 {len(leagues)} 个联赛和 {len(teams)} 个队伍")

    async def create_matches(self):
        """创建比赛数据"""
        if not self.created_data.get("teams"):
            await self.create_leagues_and_teams()

        logger.info("创建比赛数据...")

        teams = self.created_data["teams"]
        matches = []
        now = datetime.now(timezone.utc)

        # 生成未来30天的比赛
        for day in range(30):
            date = now + timedelta(days=day)

            # 每天进行多场比赛
            daily_matches = 3 + (day % 3)  # 3-5 场比赛/天

            for match_idx in range(daily_matches):
                # 选择队伍（确保不重复）
                home_idx = (day * 10 + match_idx) % len(teams)
                away_idx = (home_idx + 1 + match_idx) % len(teams)

                # 比赛时间（分布在一天的不同时间）
                match_hour = 14 + (match_idx * 2) % 8  # 14:00 - 22:00

                match_date = date.replace(
                    hour=match_hour, minute=0, second=0, microsecond=0
                )

                match = {
                    "home_team_id": teams[home_idx]["id"],
                    "away_team_id": teams[away_idx]["id"],
                    "match_date": match_date.isoformat(),
                    "competition": self.created_data["leagues"][day % 3]["name"],
                    "season": "2024/2025",
                    "status": "UPCOMING",
                    "venue": teams[home_idx]["stadium"],
                    "round": day // 7 + 1,  # 轮次
                    "weather": "Clear"
                    if day % 3 == 0
                    else "Rainy"
                    if day % 3 == 1
                    else "Cloudy",
                    "attendance_estimate": 15000 + (match_idx * 2000),
                }

                # 对于过去的比赛，随机设置一些已完成的状态
                if day < 7:
                    match["status"] = ["COMPLETED", "POSTPONED", "CANCELLED"][day % 3]
                    if match["status"] == "COMPLETED":
                        match["home_score"] = (home_idx + away_idx) % 5
                        match["away_score"] = (away_idx + home_idx + 1) % 5
                        match["minute"] = 90

                matches.append(match)

        self.created_data["matches"] = matches
        logger.info(f"创建了 {len(matches)} 场比赛")

    async def create_players(self):
        """创建球员数据"""
        if not self.created_data.get("teams"):
            await self.create_leagues_and_teams()

        logger.info("创建球员数据...")

        teams = self.created_data["teams"]
        players = []

        first_names = [
            "John",
            "Mike",
            "David",
            "James",
            "Robert",
            "William",
            "Richard",
            "Joseph",
            "Thomas",
            "Charles",
            "Christopher",
            "Daniel",
            "Matthew",
            "Anthony",
            "Mark",
            "Steven",
            "Paul",
            "Kevin",
            "Brian",
            "George",
        ]

        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
            "Hernandez",
            "Lopez",
            "Gonzalez",
            "Wilson",
            "Anderson",
            "Thomas",
            "Taylor",
            "Moore",
            "Jackson",
            "Martin",
        ]

        positions = [
            "Goalkeeper",
            "Defender",
            "Defender",
            "Defender",
            "Midfielder",
            "Midfielder",
            "Midfielder",
            "Forward",
            "Forward",
            "Substitute",
        ]

        for team in teams:
            team_players = []
            for i in range(25):  # 每队25名球员
                player = {
                    "team_id": team["id"],
                    "first_name": first_names[i % len(first_names)],
                    "last_name": last_names[i % len(last_names)],
                    "position": positions[i % len(positions)],
                    "jersey_number": i + 1,
                    "age": 20 + (i % 15),
                    "height": 170 + (i % 20),  # 170-190cm
                    "weight": 70 + (i % 20),  # 70-90kg
                    "nationality": "Stageland",
                    "contract_until": f"{2025 + (i % 5)}-06-30",
                    "market_value": 1000000 + (i * 50000),  # 100万-225万
                }
                team_players.append(player)

            players.extend(team_players)

        self.created_data["players"] = players
        logger.info(f"创建了 {len(players)} 名球员")

    async def create_users_and_predictions(self):
        """创建用户和预测数据"""
        if not self.created_data.get("matches"):
            await self.create_matches()

        logger.info("创建用户和预测数据...")

        # 创建不同类型的用户
        users = []
        user_types = [("user", 100), ("analyst", 20), ("admin", 5)]

        user_id = 1
        for role, count in user_types:
            for i in range(count):
                user = {
                    "username": f"{role}_{user_id:03d}",
                    "email": f"{role}{user_id:03d}@staging.com",
                    "password_hash": "hashed_password",
                    "role": role,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                users.append(user)
                user_id += 1

        self.created_data["users"] = users
        logger.info(f"创建了 {len(users)} 个用户")

        # 创建预测数据
        predictions = []
        matches = self.created_data["matches"]
        upcoming_matches = [m for m in matches if m["status"] == "UPCOMING"]

        for user in users[:50]:  # 前50个用户创建预测
            user_predictions = 0
            for match in upcoming_matches[:10]:  # 每个用户预测10场比赛
                # 根据用户角色调整预测行为
                if user["role"] == "analyst":
                    confidence_base = 0.85
                elif user["role"] == "admin":
                    confidence_base = 0.95
                else:
                    confidence_base = 0.75

                pred_types = ["HOME_WIN", "DRAW", "AWAY_WIN"]
                prediction = {
                    "user_id": user["id"],
                    "match_id": match["id"],
                    "prediction": pred_types[user_predictions % 3],
                    "confidence": min(
                        0.99, confidence_base + (user_predictions * 0.01)
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "PENDING",
                }
                predictions.append(prediction)
                user_predictions += 1

        self.created_data["predictions"] = predictions
        logger.info(f"创建了 {len(predictions)} 个预测")

    async def create_statistics_data(self):
        """创建统计数据"""
        if not self.created_data.get("matches"):
            await self.create_matches()

        logger.info("创建统计数据...")

        matches = self.created_data["matches"]
        completed_matches = [m for m in matches if m["status"] == "COMPLETED"]

        # 比赛统计
        match_stats = []
        for match in completed_matches[:10]:
            stats = {
                "match_id": match["id"],
                "possession": {
                    "home": 45 + (hash(match["id"]) % 20),
                    "away": 55 - (hash(match["id"]) % 20),
                },
                "shots": {
                    "home": 10 + (hash(match["id"]) % 10),
                    "away": 8 + (hash(match["id"]) % 10),
                },
                "shots_on_target": {
                    "home": 4 + (hash(match["id"]) % 5),
                    "away": 3 + (hash(match["id"]) % 5),
                },
                "corners": {
                    "home": 5 + (hash(match["id"]) % 3),
                    "away": 4 + (hash(match["id"]) % 3),
                },
                "fouls": {
                    "home": 12 + (hash(match["id"]) % 8),
                    "away": 10 + (hash(match["id"]) % 8),
                },
                "yellow_cards": {
                    "home": 2 + (hash(match["id"]) % 3),
                    "away": 1 + (hash(match["id"]) % 3),
                },
                "red_cards": {
                    "home": 1 if hash(match["id"]) % 10 == 0 else 0,
                    "away": 1 if hash(match["id"]) % 10 == 5 else 0,
                },
                "offsides": {
                    "home": 3 + (hash(match["id"]) % 4),
                    "away": 2 + (hash(match["id"]) % 4),
                },
            }
            match_stats.append(stats)

        self.created_data["statistics"] = match_stats
        logger.info(f"创建了 {len(match_stats)} 个比赛统计")

    async def save_to_database(self):
        """保存数据到数据库"""
        logger.info("保存数据到 Staging 数据库...")

        # 这里应该连接到实际的 Staging 数据库
        # 由于我们使用 Mock，这里只记录数据
        logger.info("数据准备完成：")
        logger.info(f"  - 联赛: {len(self.created_data.get('leagues', []))}")
        logger.info(f"  - 队伍: {len(self.created_data.get('teams', []))}")
        logger.info(f"  - 比赛: {len(self.created_data.get('matches', []))}")
        logger.info(f"  - 球员: {len(self.created_data.get('players', []))}")
        logger.info(f"  - 用户: {len(self.created_data.get('users', []))}")
        logger.info(f"  - 预测: {len(self.created_data.get('predictions', []))}")
        logger.info(f"  - 统计: {len(self.created_data.get('statistics', []))}")

        # 保存到 JSON 文件供参考
        output_dir = "tests/fixtures/staging"
        os.makedirs(output_dir, exist_ok=True)

        with open(os.path.join(output_dir, "staging_data.json"), "w") as f:
            json.dump(self.created_data, f, indent=2, default=str)

        logger.info(f"数据已保存到: {output_dir}/staging_data.json")

    async def load_all(self):
        """加载所有数据"""
        logger.info("开始加载 Staging 环境测试数据...")

        await self.create_leagues_and_teams()
        await self.create_matches()
        await self.create_players()
        await self.create_users_and_predictions()
        await self.create_statistics_data()
        await self.save_to_database()

        logger.info("✅ Staging 环境数据加载完成")


async def main():
    """主函数"""
    loader = StagingDataLoader()
    await loader.load_all()


if __name__ == "__main__":
    asyncio.run(main())
