"""
数据处理器

负责处理不同类型的数据消息并写入数据库。
"""

import logging
from datetime import datetime
from typing import Any, Dict

from src.database.models.raw_data import RawMatchData, RawOddsData, RawScoresData


class DataProcessor:
    """数据处理器"""

    def __init__(self, db_manager):
        """
        初始化数据处理器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    async def process_match_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理比赛数据消息

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            # 提取实际的比赛数据
            match_data = message_data.get("data", {})
            data_source = message_data.get("source", "kafka_stream")

            # 创建RawMatchData对象
            raw_match = RawMatchData(
                data_source=data_source,
                raw_data=match_data,
                collected_at=datetime.now(),
                external_match_id=str(match_data.get("match_id", "")),
                external_league_id=str(match_data.get("league_id", "")),
                match_time=(
                    datetime.fromisoformat(match_data["match_time"])
                    if match_data.get("match_time")
                    else None
                ),
            )

            # 写入数据库
            async with self.db_manager.get_async_session() as session:
                session.add(raw_match)
                await session.commit()

            self.logger.info(
                f"比赛数据已写入数据库 - Match ID: {match_data.get('match_id')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"处理比赛数据失败: {e}")
            return False

    async def process_odds_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理赔率数据消息

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            # 提取实际的赔率数据
            odds_data = message_data.get("data", {})
            data_source = message_data.get("source", "kafka_stream")

            # 创建RawOddsData对象
            raw_odds = RawOddsData(
                data_source=data_source,
                raw_data=odds_data,
                collected_at=datetime.now(),
                external_match_id=str(odds_data.get("match_id", "")),
                bookmaker=odds_data.get("bookmaker"),
                market_type=odds_data.get("market_type"),
            )

            # 写入数据库
            async with self.db_manager.get_async_session() as session:
                session.add(raw_odds)
                await session.commit()

            self.logger.debug(
                f"赔率数据已写入数据库 - Match: {odds_data.get('match_id')}, "
                f"Bookmaker: {odds_data.get('bookmaker')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"处理赔率数据失败: {e}")
            return False

    async def process_scores_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理比分数据消息

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            # 提取实际的比分数据
            scores_data = message_data.get("data", {})
            data_source = message_data.get("source", "kafka_stream")

            # 创建RawScoresData对象
            raw_scores = RawScoresData(
                data_source=data_source,
                raw_data=scores_data,
                collected_at=datetime.now(),
                external_match_id=str(scores_data.get("match_id", "")),
                match_status=scores_data.get("match_status"),
                home_score=scores_data.get("home_score"),
                away_score=scores_data.get("away_score"),
                match_minute=scores_data.get("match_minute"),
            )

            # 写入数据库
            async with self.db_manager.get_async_session() as session:
                session.add(raw_scores)
                await session.commit()

            self.logger.debug(
                f"比分数据已写入数据库 - Match: {scores_data.get('match_id')}, "
                f"Status: {scores_data.get('match_status')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"处理比分数据失败: {e}")
            return False