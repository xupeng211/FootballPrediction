#!/usr/bin/env python3
"""
英超L1数据采集器 - 专注英超数据快速入库
Premier League L1 Data Collector - Fast dedicated PL data import
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


class PremierLeagueCollector:
    """英超数据采集器"""

    def __init__(self):
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

    async def fetch_premier_league_matches(self) -> Optional[list[dict]]:
        """获取英超比赛数据"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = "https://www.fotmob.com/api/leagues?id=47"
                logger.info(f"📊 获取英超数据: {url}")

                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"❌ API请求失败: {response.status_code}")
                    return None

                data = response.json()

                # 提取比赛数据 - 使用已知的正确路径
                if "fixtures" in data and isinstance(data["fixtures"], dict):
                    if "allMatches" in data["fixtures"]:
                        matches = data["fixtures"]["allMatches"]
                        logger.info(f"✅ 找到 {len(matches)} 场英超比赛")
                        return matches

                logger.error("❌ 未找到比赛数据")
                return None

        except Exception as e:
            logger.error(f"❌ 获取英超数据失败: {e}")
            return None

    async def save_premier_league_data(self, matches: list[dict]) -> bool:
        """保存英超数据到数据库"""
        try:
            conn = await self.get_db_connection()

            try:
                # 1. 获取或创建英超联赛
                league_id = await conn.fetchval(
                    "SELECT id FROM leagues WHERE name = 'Premier League'"
                )
                if not league_id:
                    league_id = await conn.fetchval(
                        """
                        INSERT INTO leagues (name, country, season, created_at, updated_at)
                        VALUES ('Premier League', 'ENG', '2024/2025', NOW(), NOW())
                        RETURNING id
                        """
                    )
                logger.info(f"✅ 英超联赛ID: {league_id}")

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

                    # 提取比赛时间
                    status_data = match.get("status", {})
                    utc_time = status_data.get("utcTime", "")
                    is_finished = status_data.get("finished", False)

                    # 解析比赛时间
                    match_date = datetime.now()
                    if utc_time:
                        try:
                            # 解析并移除时区信息
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

                    # 获取或创建主队
                    home_team_id = await conn.fetchval(
                        "SELECT id FROM teams WHERE name = $1", home_team
                    )
                    if not home_team_id:
                        home_team_id = await conn.fetchval(
                            "INSERT INTO teams (name, created_at, updated_at) VALUES ($1, NOW(), NOW()) RETURNING id",
                            home_team,
                        )

                    # 获取或创建客队
                    away_team_id = await conn.fetchval(
                        "SELECT id FROM teams WHERE name = $1", away_team
                    )
                    if not away_team_id:
                        away_team_id = await conn.fetchval(
                            "INSERT INTO teams (name, created_at, updated_at) VALUES ($1, NOW(), NOW()) RETURNING id",
                            away_team,
                        )

                    # 已在上面的步骤中获取了球队ID

                    if not home_team_id or not away_team_id:
                        logger.warning(f"⚠️ 无法获取球队ID: {home_team} vs {away_team}")
                        continue

                    # 检查比赛是否已存在
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
                            "Premier League",
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

                    if saved_count <= 5:  # 只打印前5场比赛
                        logger.info(
                            f"✅ 保存: {home_team} vs {away_team} ({match_date.strftime('%Y-%m-%d')})"
                        )

                logger.info(f"✅ 英超数据保存完成: {saved_count} 场比赛")
                logger.info(f"📅 未来比赛: {future_matches} 场")

                return saved_count > 0

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def run(self) -> bool:
        """运行英超数据采集"""
        logger.info("🏆 开始英超L1数据采集")

        # 获取比赛数据
        matches = await self.fetch_premier_league_matches()
        if not matches:
            logger.error("❌ 无法获取英超比赛数据")
            return False

        # 保存数据
        success = await self.save_premier_league_data(matches)

        if success:
            logger.info("🎉 英超L1数据采集成功完成")
        else:
            logger.error("❌ 英超L1数据采集失败")

        return success


async def main():
    """主函数"""
    collector = PremierLeagueCollector()

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
