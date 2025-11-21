#!/usr/bin/env python3
"""
Silver层ETL脚本 / Silver Layer ETL Script

该脚本实现从Bronze层到Silver层的ETL流程：
1. 从raw_match_data表中读取未处理的原始数据
2. 使用FootballDataCleaner解析JSON数据
3. Upsert球队和联赛数据到Silver层
4. Upsert比赛数据到Silver层
5. 标记原始数据为已处理

This script implements the ETL process from Bronze to Silver layer:
1. Read unprocessed data from raw_match_data table
2. Parse JSON data using FootballDataCleaner
3. Upsert teams and leagues to Silver layer
4. Upsert matches to Silver layer
5. Mark raw data as processed

使用方法 / Usage:
    python scripts/run_etl_silver.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

# 尝试加载.env文件
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已加载环境文件: {env_file}")
        break
else:
    print("⚠️  未找到.env文件，将使用系统环境变量")

# 导入模块
try:
    from src.data.processing.football_data_cleaner import FootballDataCleaner
    from src.database.connection import get_async_session, initialize_database
    from src.database.models.raw_data import RawMatchData
    from src.database.models.team import Team
    from src.database.models.league import League
    from src.database.models.match import Match, MatchStatus
    from sqlalchemy import select, and_, or_
    from sqlalchemy.orm import selectinload
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("💡 提示: 请确保已安装所有依赖: pip install asyncpg sqlalchemy")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SilverETLProcessor:
    """Silver层ETL处理器."""

    def __init__(self):
        """初始化ETL处理器."""
        self.cleaner = FootballDataCleaner()
        self.processing_stats = {
            "total_raw_records": 0,
            "processed_matches": 0,
            "upserted_teams": 0,
            "upserted_leagues": 0,
            "errors": 0,
            "start_time": datetime.now(),
        }

    async def run_etl(self):
        """执行完整的ETL流程."""
        logger.info("=" * 60)
        logger.info("🚀 开始Silver层ETL流程")
        logger.info("=" * 60)

        try:
            # 初始化数据库连接
            initialize_database()
            logger.info("✅ 数据库连接初始化成功")

            async with get_async_session() as session:
                # 1. 读取未处理的原始数据
                raw_records = await self._fetch_unprocessed_data(session)
                if not raw_records:
                    logger.info("📄 没有未处理的原始数据")
                    return True

                self.processing_stats["total_raw_records"] = len(raw_records)
                logger.info(f"📊 找到 {len(raw_records)} 条未处理的原始数据")

                # 2. 处理每条记录
                for record in raw_records:
                    await self._process_single_record(session, record)

                # 3. 提交所有更改
                await session.commit()
                logger.info("✅ 所有数据已成功提交到数据库")

            # 4. 打印处理统计
            await self._print_processing_summary()
            return True

        except Exception as e:
            logger.error(f"❌ ETL流程失败: {e}")
            self.processing_stats["errors"] += 1
            return False

    async def _fetch_unprocessed_data(self, session) -> list:
        """获取未处理的原始数据."""
        try:
            stmt = select(RawMatchData).where(RawMatchData.processed == False)
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取未处理数据失败: {e}")
            raise

    async def _process_single_record(self, session, raw_record):
        """处理单条原始记录."""
        try:
            # 解析JSON数据
            match_data = self.cleaner.parse_match_json(raw_record.match_data)
            logger.debug(f"解析比赛数据: external_id={match_data.get('external_id')}")

            # 1. Upsert联赛
            league_id = await self._upsert_league(session, match_data)

            # 2. Upsert主队和客队
            home_team_id = await self._upsert_team(session, match_data, 'home')
            away_team_id = await self._upsert_team(session, match_data, 'away')

            # 3. Upsert比赛
            await self._upsert_match(session, match_data, home_team_id, away_team_id, league_id)

            # 4. 标记原始数据为已处理
            raw_record.processed = True
            raw_record.processed_at = datetime.utcnow()

            self.processing_stats["processed_matches"] += 1
            if self.processing_stats["processed_matches"] % 50 == 0:
                logger.info(f"📈 已处理 {self.processing_stats['processed_matches']} 条记录")

        except Exception as e:
            logger.error(f"处理记录失败 (external_id={raw_record.external_id}): {e}")
            self.processing_stats["errors"] += 1
            # 不标记为已处理，下次重试
            raise

    async def _upsert_league(self, session, match_data: Dict[str, Any]) -> int:
        """Upsert联赛数据."""
        try:
            league_info = self.cleaner.extract_league_from_match(match_data)
            external_id = league_info.get("external_id")

            if not external_id:
                logger.warning("联赛缺少external_id，跳过")
                return None

            # 查找现有联赛
            stmt = select(League).where(League.name == league_info["name"])
            result = await session.execute(stmt)
            existing_league = result.scalar_one_or_none()

            if existing_league:
                return existing_league.id
            else:
                # 创建新联赛（这里需要先添加external_id字段到League模型，暂时使用name查找）
                new_league = League(
                    name=league_info["name"],
                    country=league_info["country"],
                    is_active=league_info.get("is_active", True)
                )
                session.add(new_league)
                await session.flush()  # 获取ID
                self.processing_stats["upserted_leagues"] += 1
                logger.debug(f"创建新联赛: {league_info['name']}")
                return new_league.id

        except Exception as e:
            logger.error(f"Upsert联赛失败: {e}")
            raise

    async def _upsert_team(self, session, match_data: Dict[str, Any], team_type: str) -> int:
        """Upsert球队数据."""
        try:
            team_info = self.cleaner.extract_team_from_match(match_data, team_type)
            external_id = team_info.get("external_id")

            if not external_id or not team_info.get("name"):
                logger.warning(f"{team_type}球队缺少ID或名称，跳过")
                return None

            # 查找现有球队（这里暂时通过external_id查找，但Team模型可能需要添加这个字段）
            stmt = select(Team).where(Team.name == team_info["name"])
            result = await session.execute(stmt)
            existing_team = result.scalar_one_or_none()

            if existing_team:
                return existing_team.id
            else:
                # 创建新球队
                new_team = Team(
                    name=team_info["name"],
                    short_name=team_info.get("short_name"),
                    country=team_info.get("country", "England"),
                )
                session.add(new_team)
                await session.flush()  # 获取ID
                self.processing_stats["upserted_teams"] += 1
                logger.debug(f"创建新球队: {team_info['name']}")
                return new_team.id

        except Exception as e:
            logger.error(f"Upsert {team_type} 球队失败: {e}")
            raise

    async def _upsert_match(self, session, match_data: Dict[str, Any],
                           home_team_id: int, away_team_id: int, league_id: int):
        """Upsert比赛数据."""
        try:
            # 移除时区信息以匹配数据库字段类型
            match_date = match_data["match_date"]
            if match_date.tzinfo is not None:
                match_date = match_date.replace(tzinfo=None)

            # 检查是否已存在相同的比赛
            stmt = select(Match).where(
                and_(
                    Match.home_team_id == home_team_id,
                    Match.away_team_id == away_team_id,
                    Match.match_date == match_date
                )
            )
            result = await session.execute(stmt)
            existing_match = result.scalar_one_or_none()

            if existing_match:
                # 更新现有比赛
                existing_match.home_score = match_data.get("home_score", 0)
                existing_match.away_score = match_data.get("away_score", 0)
                existing_match.status = match_data.get("status", "SCHEDULED")
                existing_match.league_id = league_id
                existing_match.venue = match_data.get("venue")
                existing_match.season = str(match_data.get("season", ""))
                logger.debug(f"更新比赛: home={home_team_id}, away={away_team_id}")
            else:
                # 创建新比赛
                new_match = Match(
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_score=match_data.get("home_score", 0),
                    away_score=match_data.get("away_score", 0),
                    status=match_data.get("status", "SCHEDULED"),
                    match_date=match_date,  # 使用已去除时区的日期
                    league_id=league_id,
                    venue=match_data.get("venue"),
                    season=str(match_data.get("season", "")),
                )
                session.add(new_match)
                logger.debug(f"创建新比赛: home={home_team_id}, away={away_team_id}")

        except Exception as e:
            logger.error(f"Upsert比赛失败: {e}")
            raise

    async def _print_processing_summary(self):
        """打印处理摘要."""
        end_time = datetime.now()
        duration = end_time - self.processing_stats["start_time"]

        logger.info("=" * 60)
        logger.info("📊 ETL处理摘要")
        logger.info("=" * 60)
        logger.info(f"⏱️  处理时间: {duration}")
        logger.info(f"📄 原始记录数: {self.processing_stats['total_raw_records']}")
        logger.info(f"⚽ 处理比赛数: {self.processing_stats['processed_matches']}")
        logger.info(f"🏆 新增球队数: {self.processing_stats['upserted_teams']}")
        logger.info(f"🏆 新增联赛数: {self.processing_stats['upserted_leagues']}")
        logger.info(f"❌ 错误数: {self.processing_stats['errors']}")

        if self.processing_stats["errors"] > 0:
            logger.warning("⚠️  处理过程中有错误，请检查日志")
        else:
            logger.info("✅ ETL流程完成，所有数据已成功处理")

        logger.info("=" * 60)


async def main():
    """主函数."""
    logger.info("🎯 Silver层ETL处理器启动")

    try:
        processor = SilverETLProcessor()
        success = await processor.run_etl()

        if success:
            logger.info("🎉 ETL流程成功完成！")
            sys.exit(0)
        else:
            logger.error("💥 ETL流程失败！")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，ETL流程停止")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 ETL流程异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())