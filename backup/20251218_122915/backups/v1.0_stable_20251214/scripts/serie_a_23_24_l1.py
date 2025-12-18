#!/usr/bin/env python3
"""
意甲 23-24 赛季 L1 数据采集器
Serie A 2023/2024 Season L1 Data Collector

专门用于采集意甲 2023/2024 赛季的比赛数据，为 L2 回填提供原材料

使用示例:
    python scripts/serie_a_23_24_l1.py

目标参数:
    League ID: 55 (Serie A)
    Season: 2023/2024
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


class SerieACollector:
    """意甲数据采集器"""

    def __init__(self, league_id: int = 55, season: str = "2024/2025"):
        self.league_id = league_id
        self.season = season
        self.league_name = "Serie A"

        # 使用修复后的API令牌
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.fotmob.com/",
            "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=",
            "x-foo": "eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZGRmYyIsInRpbWVzdGFtcCI6MTc2NTEyMTgxMn0=",
        }

    async def get_db_connection(self):
        """获取数据库连接"""
        return await asyncpg.connect(
            user="postgres",
            password="postgres",
            database="football_prediction",
            host="db",
        )

    async def fetch_serie_a_matches(self) -> Optional[list[dict]]:
        """获取意甲比赛数据"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = f"https://www.fotmob.com/api/leagues?id={self.league_id}"
                logger.info(f"📊 获取意甲数据: {url}")

                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"❌ 意甲 API请求失败: {response.status_code}")
                    return None

                data = response.json()

                # 提取比赛数据
                if "fixtures" in data and isinstance(data["fixtures"], dict):
                    if "allMatches" in data["fixtures"]:
                        matches = data["fixtures"]["allMatches"]
                        logger.info(f"✅ 找到 {len(matches)} 场意甲比赛")
                        return matches

                logger.error("❌ 未找到意甲比赛数据")
                return None

        except Exception as e:
            logger.error(f"❌ 获取意甲数据失败: {e}")
            return None

    def filter_current_season_matches(self, matches: list[dict]) -> list[dict]:
        """筛选当前赛季 (2024/2025) 的比赛"""
        filtered_matches = []

        for match in matches:
            # 提取比赛时间
            status_data = match.get("status", {})
            utc_time = status_data.get("utcTime", "")

            if not utc_time:
                continue

            try:
                # 解析比赛时间
                aware_date = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
                match_date = aware_date.replace(tzinfo=None)

                # 筛选 2024/2025 赛季的比赛 (2024-07-01 到 2025-06-30)
                season_start = datetime(2024, 7, 1)
                season_end = datetime(2025, 6, 30)

                if season_start <= match_date <= season_end:
                    filtered_matches.append(match)

            except Exception as e:
                logger.warning(f"⚠️ 解析比赛时间失败: {utc_time}, {e}")
                continue

        logger.info(f"✅ 筛选到 {len(filtered_matches)} 场 2024/2025 赛季意甲比赛")
        return filtered_matches

    async def save_serie_a_data(self, matches: list[dict]) -> bool:
        """保存意甲数据到数据库"""
        try:
            conn = await self.get_db_connection()

            try:
                # 1. 获取或创建意甲联赛
                league_id = await conn.fetchval(
                    "SELECT id FROM leagues WHERE name = $1", self.league_name
                )
                if not league_id:
                    league_id = await conn.fetchval(
                        """
                        INSERT INTO leagues (name, country, season, is_active, created_at, updated_at)
                        VALUES ($1, $2, $3, true, NOW(), NOW())
                        RETURNING id
                        """,
                        self.league_name,
                        "ITA",
                        self.season,
                    )
                logger.info(f"✅ 意甲联赛ID: {league_id}")

                # 2. 保存比赛和球队数据
                saved_count = 0
                updated_count = 0
                finished_matches = 0

                for match in matches:
                    # 提取比赛信息
                    fotmob_id = match.get("id")
                    home_team = match.get("home", {}).get("name", "")
                    away_team = match.get("away", {}).get("name", "")

                    if not fotmob_id or not home_team or not away_team:
                        continue

                    # 提取比赛时间
                    status_data = match.get("status", {})
                    utc_time = status_data.get("utcTime", "")
                    is_finished = status_data.get("finished", False)
                    is_started = status_data.get("started", False)

                    # 解析比赛时间
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
                    status = "scheduled"
                    if is_finished:
                        status = "FT"  # Full Time
                    elif is_started:
                        status = "live"

                    # 统计已结束比赛
                    if is_finished:
                        finished_matches += 1

                    # 获取或创建主队
                    home_team_id = await conn.fetchval(
                        "SELECT id FROM teams WHERE name = $1", home_team
                    )
                    if not home_team_id:
                        home_team_id = await conn.fetchval(
                            "INSERT INTO teams (name, country, created_at, updated_at) VALUES ($1, $2, NOW(), NOW()) RETURNING id",
                            home_team,
                            "ITA",
                        )

                    # 获取或创建客队
                    away_team_id = await conn.fetchval(
                        "SELECT id FROM teams WHERE name = $1", away_team
                    )
                    if not away_team_id:
                        away_team_id = await conn.fetchval(
                            "INSERT INTO teams (name, country, created_at, updated_at) VALUES ($1, $2, NOW(), NOW()) RETURNING id",
                            away_team,
                            "ITA",
                        )

                    if not home_team_id or not away_team_id:
                        logger.warning(f"⚠️ 无法获取球队ID: {home_team} vs {away_team}")
                        continue

                    # 检查比赛是否已存在 (使用 fotmob_id 字段查询，而不是 id 字段)
                    existing_id = await conn.fetchval(
                        "SELECT id FROM matches WHERE fotmob_id = $1", str(fotmob_id)
                    )
                    if existing_id:
                        # 更新现有比赛
                        await conn.execute(
                            """
                            UPDATE matches SET
                                match_date = $1,
                                status = $2,
                                updated_at = NOW()
                            WHERE fotmob_id = $3
                            """,
                            match_date,
                            status,
                            str(fotmob_id),
                        )
                        updated_count += 1
                    else:
                        # 创建新比赛 - 生成新的自增 ID，存储 fotmob_id 在 fotmob_id 字段
                        await conn.execute(
                            """
                            INSERT INTO matches (
                                fotmob_id, home_team_name, away_team_name, league_id,
                                status, match_date, data_source, data_completeness,
                                home_team_id, away_team_id, season, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
                            """,
                            str(fotmob_id),
                            home_team,
                            away_team,
                            league_id,
                            status,
                            match_date,
                            "fotmob_api",
                            "partial",
                            home_team_id,
                            away_team_id,
                            self.season,
                        )
                        saved_count += 1

                    if saved_count + updated_count <= 5:  # 只打印前5场比赛
                        logger.info(
                            f"✅ 保存: {home_team} vs {away_team} ({match_date.strftime('%Y-%m-%d')}) - {status}"
                        )

                logger.info("✅ 意甲数据保存完成:")
                logger.info(f"   📊 新增比赛: {saved_count} 场")
                logger.info(f"   🔄 更新比赛: {updated_count} 场")
                logger.info(f"   🏁 已结束比赛: {finished_matches} 场")

                return saved_count > 0 or updated_count > 0

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"❌ 保存意甲数据失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def run(self) -> bool:
        """运行意甲数据采集"""
        logger.info("🏆 开始意甲 L1 数据采集 (为 L2 回填提供原材料)")
        logger.info(f"📊 联赛ID: {self.league_id}, 赛季: {self.season}")

        # 获取比赛数据
        all_matches = await self.fetch_serie_a_matches()
        if not all_matches:
            logger.error("❌ 无法获取意甲比赛数据")
            return False

        # 直接使用所有比赛，不进行赛季筛选，以获得最多的 L2 回填原材料
        logger.info(f"📋 使用所有 {len(all_matches)} 场比赛作为 L2 回填原材料")
        season_matches = all_matches

        # 保存数据
        success = await self.save_serie_a_data(season_matches)

        if success:
            logger.info("🎉 意甲 L1 数据采集成功完成")
        else:
            logger.error("❌ 意甲 L1 数据采集失败")

        return success


async def main():
    """主函数"""
    collector = SerieACollector()

    try:
        success = await collector.run()
        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
