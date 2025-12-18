#!/usr/bin/env python3
"""
多联赛L1数据采集器 - 五大联赛横向扩展
Multi-League L1 Data Collector - Horizontal expansion for top 5 leagues

基于premier_league_l1.py的成功经验，支持五大联赛并行采集
"""

import asyncio
import httpx
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MultiLeagueCollector:
    """多联赛数据采集器"""

    def __init__(self):
        # 使用修复后的API令牌
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.fotmob.com/",
            "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=",
            "x-foo": "eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZGRmYyIsInRpbWVzdGFtcCI6MTc2NTEyMTgxMn0=",
        }

        # 五大联赛配置
        self.target_leagues = [
            {
                "id": 47,
                "name": "Premier League",
                "country": "ENG",
                "short_name": "premier-league",
            },
            {"id": 87, "name": "LaLiga", "country": "ESP", "short_name": "laliga"},
            {"id": 55, "name": "Serie A", "country": "ITA", "short_name": "serie-a"},
            {
                "id": 54,
                "name": "Bundesliga",
                "country": "GER",
                "short_name": "bundesliga",
            },
            {"id": 53, "name": "Ligue 1", "country": "FRA", "short_name": "ligue-1"},
        ]

    async def get_db_connection(self):
        """获取数据库连接"""
        return await asyncpg.connect(
            user="postgres",
            password="postgres",
            database="football_prediction",
            host="db",
        )

    async def fetch_league_matches(self, league_info: dict) -> Optional[list[dict]]:
        """获取联赛比赛数据"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = f"https://www.fotmob.com/api/leagues?id={league_info['id']}"
                logger.info(f"📊 获取{league_info['name']}数据: {url}")

                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(
                        f"❌ {league_info['name']} API请求失败: {response.status_code}"
                    )
                    return None

                data = response.json()

                # 使用已验证的正确解析路径
                if "fixtures" in data and isinstance(data["fixtures"], dict):
                    if "allMatches" in data["fixtures"]:
                        matches = data["fixtures"]["allMatches"]
                        logger.info(
                            f"✅ {league_info['name']}: 找到 {len(matches)} 场比赛"
                        )
                        return matches

                logger.error(f"❌ {league_info['name']}: 未找到比赛数据")
                return None

        except Exception as e:
            logger.error(f"❌ 获取{league_info['name']}数据失败: {e}")
            return None

    async def save_league_data(
        self, league_info: dict, matches: list[dict]
    ) -> dict[str, int]:
        """保存联赛数据到数据库"""
        try:
            conn = await self.get_db_connection()

            try:
                # 1. 确保联赛存在
                league_id = await conn.fetchval(
                    "SELECT id FROM leagues WHERE name = $1", league_info["name"]
                )
                if not league_id:
                    league_id = await conn.fetchval(
                        """
                        INSERT INTO leagues (name, country, season, created_at, updated_at)
                        VALUES ($1, $2, '2024/2025', NOW(), NOW())
                        RETURNING id
                        """,
                        league_info["name"],
                        league_info["country"],
                    )
                logger.info(f"✅ {league_info['name']} 联赛ID: {league_id}")

                # 2. 保存比赛和球队数据
                saved_count = 0
                future_matches = 0

                for match in matches:
                    # 提取比赛信息
                    fotmob_id = match.get("id")
                    home_team = match.get("home", {}).get("name", "")
                    away_team = match.get("away", {}).get("name", "")

                    if not fotmob_id or not home_team or not away_team:
                        continue

                    # 提取比赛时间 (使用验证过的时区处理逻辑)
                    status_data = match.get("status", {})
                    utc_time = status_data.get("utcTime", "")
                    is_finished = status_data.get("finished", False)

                    # 解析比赛时间 (移除时区信息)
                    match_date = datetime.now()
                    if utc_time:
                        try:
                            aware_date = datetime.fromisoformat(
                                utc_time.replace("Z", "+00:00")
                            )
                            match_date = aware_date.replace(tzinfo=None)
                        except:
                            pass

                    # 确定比赛状态
                    status = "finished" if is_finished else "scheduled"
                    if status_data.get("started", False) and not is_finished:
                        status = "live"

                    # 统计未来比赛
                    if not is_finished and match_date > datetime.now():
                        future_matches += 1

                    # 获取或创建球队 (使用验证过的逻辑)
                    home_team_id = await conn.fetchval(
                        "SELECT id FROM teams WHERE name = $1", home_team
                    )
                    if not home_team_id:
                        home_team_id = await conn.fetchval(
                            "INSERT INTO teams (name, created_at, updated_at) VALUES ($1, NOW(), NOW()) RETURNING id",
                            home_team,
                        )

                    away_team_id = await conn.fetchval(
                        "SELECT id FROM teams WHERE name = $1", away_team
                    )
                    if not away_team_id:
                        away_team_id = await conn.fetchval(
                            "INSERT INTO teams (name, created_at, updated_at) VALUES ($1, NOW(), NOW()) RETURNING id",
                            away_team,
                        )

                    if not home_team_id or not away_team_id:
                        logger.warning(f"⚠️ 无法获取球队ID: {home_team} vs {away_team}")
                        continue

                    # 检查比赛是否已存在 (使用验证过的逻辑)
                    existing_id = await conn.fetchval(
                        "SELECT id FROM matches WHERE id = $1", fotmob_id
                    )
                    if existing_id:
                        # 更新现有比赛
                        await conn.execute(
                            """
                            UPDATE matches SET
                                match_date = $1,
                                status = $2,
                                updated_at = NOW()
                            WHERE id = $3
                            """,
                            match_date,
                            status,
                            fotmob_id,
                        )
                    else:
                        # 创建新比赛
                        await conn.execute(
                            """
                            INSERT INTO matches (
                                id, home_team, away_team, league, league_id,
                                status, match_date, data_source, data_completeness,
                                home_team_id, away_team_id, season, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                            """,
                            fotmob_id,
                            home_team,
                            away_team,
                            league_info["name"],
                            league_id,
                            status,
                            match_date,
                            "fotmob_api",
                            "partial",
                            home_team_id,
                            away_team_id,
                            "2024/2025",
                        )

                    saved_count += 1

                    if saved_count <= 3:  # 只打印前3场比赛
                        logger.info(
                            f"✅ 保存{league_info['name']}: {home_team} vs {away_team} ({match_date.strftime('%Y-%m-%d')})"
                        )

                return {
                    "total_matches": saved_count,
                    "future_matches": future_matches,
                    "league_id": league_id,
                }

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"❌ 保存{league_info['name']}数据失败: {e}")
            return {"total_matches": 0, "future_matches": 0, "league_id": None}

    async def run_collection(self):
        """运行多联赛数据采集"""
        logger.info("🏆 开始多联赛L1数据采集")
        logger.info(f"📊 目标联赛: {[l['name'] for l in self.target_leagues]}")

        total_stats = {"total_matches": 0, "future_matches": 0, "successful_leagues": 0}

        # 串行处理避免API限制
        for league_info in self.target_leagues:
            logger.info(f"\n🏆 处理联赛: {league_info['name']}")

            # 获取比赛数据
            matches = await self.fetch_league_matches(league_info)
            if not matches:
                logger.warning(f"⚠️ 无法获取{league_info['name']}数据")
                continue

            # 保存数据
            stats = await self.save_league_data(league_info, matches)

            total_stats["total_matches"] += stats["total_matches"]
            total_stats["future_matches"] += stats["future_matches"]

            if stats["total_matches"] > 0:
                total_stats["successful_leagues"] += 1
                logger.info(
                    f"✅ {league_info['name']}: {stats['total_matches']}场总比赛, {stats['future_matches']}场未来比赛"
                )
            else:
                logger.warning(f"⚠️ {league_info['name']}: 保存失败")

        logger.info("\n🎉 多联赛采集完成!")
        logger.info(
            f"📊 总计: {total_stats['successful_leagues']}个联赛, {total_stats['total_matches']}场总比赛, {total_stats['future_matches']}场未来比赛"
        )

        return total_stats["successful_leagues"] > 0


async def main():
    """主函数"""
    collector = MultiLeagueCollector()

    try:
        success = await collector.run_collection()

        if success:
            logger.info("✅ 多联赛L1数据采集成功完成")
            return 0
        else:
            logger.error("❌ 多联赛L1数据采集失败")
            return 1

    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
