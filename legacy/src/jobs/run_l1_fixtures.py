#!/usr/bin/env python3
"""
FotMob L1 赛程采集任务 - L1 Fixtures Collection Job
使用 enhanced_fotmob_collector 采集比赛赛程数据，为L2深度补全提供基础数据

规范化生产任务 - 技术负责人标准化版本
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
# 添加项目根路径 - 标准化导入
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
from src.database.async_manager import get_db_session
from sqlalchemy import text

# 配置日志 - 标准化路径
logging.basicConfig(
    level=logging.INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers=[
        logging.FileHandler("logs/l1_fixtures.log")
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class FotMobL1FixturesJob:
    """FotMob L1 赛程采集任务"""

    def __init__(self):
        self.logger = logger

    async def ensure_team_exists(self, session, team_name: str) -> int:
        """
        确保team记录存在，返回team_id

        关键方法：解决外键约束问题的核心逻辑
        """
        try:
            # 检查team是否存在
            check_query = text("SELECT id FROM teams WHERE name = :team_name")
            result = await session.execute(check_query, {"team_name": team_name})
            existing = result.fetchone()

            if existing:
                return existing[0]

            # 生成新的team_id（简单递增）
            max_id_query = text("SELECT COALESCE(MAX(id), 0) FROM teams")
            max_result = await session.execute(max_id_query)
            new_id = max_result.scalar() + 1

            # 创建新team记录
            insert_query = text(
                """
                INSERT INTO teams (id, name, country, created_at, updated_at)
                VALUES (:id, :name, :country, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """
            )
            await session.execute(
                insert_query
                {
                    "id": new_id
                    "name": team_name
                    "country": "Unknown"
                    "created_at": datetime.now()
                    "updated_at": datetime.now()
                }
            )

            self.logger.info(f"✅ 创建新球队记录: {team_name} (ID: {new_id})")
            return new_id

        except Exception as e:
            self.logger.error(f"❌ 创建球队记录失败 {team_name}: {e}")
            raise

    async def process_match_data(
        self, matches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        处理比赛数据，确保球队记录存在

        架构关键点：L1负责创建teams和matches的基础记录
        """
        processed_matches = []

        async with get_db_session() as session:
            for match in matches:
                try:
                    # 提取球队信息
                    home_team = match.get("home", {})
                    away_team = match.get("away", {})

                    if not home_team or not away_team:
                        continue

                    home_team_name = home_team.get("name", "Unknown")
                    away_team_name = away_team.get("name", "Unknown")

                    # 确保球队记录存在 - 关键依赖关系
                    home_team_id = await self.ensure_team_exists(
                        session, home_team_name
                    )
                    away_team_id = await self.ensure_team_exists(
                        session, away_team_name
                    )

                    # 处理比赛数据
                    processed_match = {
                        "home_team_id": home_team_id
                        "away_team_id": away_team_id
                        "home_team_name": home_team_name
                        "away_team_name": away_team_name
                        "home_score": home_team.get("score", 0)
                        "away_score": away_team.get("score", 0)
                        "status": match.get("status", "NS")
                        "match_date": match.get("start_time")
                        "venue": match.get("venue", "Unknown")
                        "fotmob_id": match.get("id")
                        "league_id": match.get("league_id", 47),  # 默认英超
                        "season": "2023/2024"
                    }

                    processed_matches.append(processed_match)

                except Exception as e:
                    self.logger.error(f"❌ 处理比赛数据失败: {e}")
                    continue

        return processed_matches

    async def save_matches_to_db(self, matches: list[dict[str, Any]]) -> int:
        """保存比赛数据到数据库"""
        saved_count = 0

        async with get_db_session() as session:
            for match in matches:
                try:
                    insert_query = text(
                        """
                        INSERT INTO matches (
                            home_team_id, away_team_id, home_score, away_score
                            status, match_date, venue, league_id, season
                            created_at, updated_at, fotmob_id, data_source
                            data_completeness
                        ) VALUES (
                            :home_team_id, :away_team_id, :home_score, :away_score
                            :status, :match_date, :venue, :league_id, :season
                            :created_at, :updated_at, :fotmob_id, :data_source
                            :data_completeness
                        )
                        ON CONFLICT (home_team_id, away_team_id, match_date)
                        DO UPDATE SET
                            home_score = EXCLUDED.home_score
                            away_score = EXCLUDED.away_score
                            status = EXCLUDED.status
                            updated_at = EXCLUDED.updated_at
                            fotmob_id = EXCLUDED.fotmob_id
                            data_source = EXCLUDED.data_source
                        RETURNING id
                    """
                    )

                    await session.execute(
                        insert_query
                        {
                            "home_team_id": match["home_team_id"]
                            "away_team_id": match["away_team_id"]
                            "home_score": match["home_score"]
                            "away_score": match["away_score"]
                            "status": match["status"]
                            "match_date": match["match_date"] or datetime.now()
                            "venue": match["venue"]
                            "league_id": match["league_id"]
                            "season": match["season"]
                            "created_at": datetime.now()
                            "updated_at": datetime.now()
                            "fotmob_id": match["fotmob_id"]
                            "data_source": "fotmob_v2"
                            "data_completeness": "partial"
                        }
                    )

                    saved_count += 1

                except Exception as e:
                    self.logger.error(f"❌ 保存比赛失败: {e}")
                    continue

        return saved_count

    async def run_job(self):
        """运行L1赛程采集任务"""
        try:
            self.logger.info("🚀 启动FotMob L1赛程采集任务")

            # 初始化采集器
            collector = EnhancedFotMobCollector()
            await collector.initialize()

            # 采集测试日期的数据（生产环境可扩展为日期范围）
            test_dates = ["2024-11-30", "2024-12-01", "2024-12-02"]
            total_saved = 0

            for date_str in test_dates:
                self.logger.info(f"📅 采集日期: {date_str}")

                try:
                    # 采集比赛列表 - 使用HTTP API，严禁Playwright
                    matches = await collector.collect_matches_by_date(date_str)

                    if matches:
                        self.logger.info(f"✅ 获取到 {len(matches)} 场比赛")

                        # 处理比赛数据（包含球队创建逻辑）
                        processed_matches = await self.process_match_data(matches)

                        # 保存到数据库
                        saved_count = await self.save_matches_to_db(processed_matches)
                        total_saved += saved_count

                        self.logger.info(f"💾 保存了 {saved_count} 场比赛到数据库")
                    else:
                        self.logger.warning(f"⚠️ 未获取到 {date_str} 的比赛数据")

                except Exception as e:
                    self.logger.error(f"❌ 采集日期 {date_str} 失败: {e}")
                    continue

            self.logger.info(f"🎉 L1赛程采集完成，总共保存了 {total_saved} 场比赛")

        except Exception as e:
            self.logger.error(f"❌ L1赛程采集失败: {e}")
            raise

        finally:
            await collector.close()


async def main():
    """主函数"""
    job = FotMobL1FixturesJob()
    await job.run_job()


if __name__ == "__main__":
    asyncio.run(main())
