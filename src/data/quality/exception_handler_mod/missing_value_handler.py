"""
缺失值处理模块

负责处理数据中的缺失值，包括历史平均填充等策略。
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .exceptions import MissingValueException


class MissingValueHandler:
    """缺失值处理器"""

    def __init__(self, db_manager: Any, config: Dict[str, Any] = None):
        """
        初始化缺失值处理器

        Args:
            db_manager: 数据库管理器
            config: 配置参数
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 默认配置
        self.config = config or {
            "strategy": "historical_average",
            "lookback_days": 30,
            "min_sample_size": 5,
        }

    async def handle_missing_values(
        self, table_name: str, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理缺失值

        Args:
            table_name: 表名
            records: 包含缺失值的记录列表

        Returns:
            List[Dict]: 处理后的记录列表
        """
        try:
            processed_records = []
            missing_value_counts: Dict[str, int] = {}

            for record in records:
                processed_record = record.copy()

                # 根据表名选择处理策略
                if table_name == "matches":
                    processed_record = await self._handle_missing_match_values(
                        processed_record
                    )
                elif table_name == "odds":
                    processed_record = await self._handle_missing_odds_values(
                        processed_record
                    )

                # 统计缺失值处理数量
                for key, value in processed_record.items():
                    if key not in record or record[key] is None:
                        if value is not None:  # 成功填充
                            missing_value_counts[key] = (
                                missing_value_counts.get(str(key), 0) + 1
                            )

                processed_records.append(processed_record)

            # 记录缺失值处理日志
            if missing_value_counts:
                await self._log_missing_value_handling(table_name, missing_value_counts)

            self.logger.info(
                f"表 {table_name} 缺失值处理完成，处理 {len(records)} 条记录"
            )
            return processed_records

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理缺失值失败 {table_name}: {str(e)}")
            raise MissingValueException(
                f"处理缺失值失败: {str(e)}", table_name=table_name
            )

    async def _handle_missing_match_values(
        self, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理比赛数据的缺失值"""
        try:
            # 处理缺失的比分（已完成比赛才处理）
            if record.get("match_status") == "finished":
                if record.get("home_score") is None:
                    # 使用历史平均比分填充
                    avg_score = await self._get_historical_average_score(
                        "home",
                        record.get("home_team_id"),  # type: ignore
                    )
                    record["home_score"] = (
                        round(avg_score) if avg_score is not None else 0
                    )

                if record.get("away_score") is None:
                    avg_score = await self._get_historical_average_score(
                        "away",
                        record.get("away_team_id"),  # type: ignore
                    )
                    record["away_score"] = (
                        round(avg_score) if avg_score is not None else 0
                    )

            # 处理缺失的场地信息
            if record.get("venue") is None:
                record["venue"] = "Unknown Venue"

            # 处理缺失的裁判信息
            if record.get("referee") is None:
                record["referee"] = "Unknown Referee"

            # 处理缺失的天气信息
            if record.get("weather") is None:
                record["weather"] = "Unknown Weather"

            return record

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理比赛缺失值失败: {str(e)}")
            raise MissingValueException(
                f"处理比赛缺失值失败: {str(e)}",
                table_name="matches",
                column_name="scores",
            )

    async def _handle_missing_odds_values(
        self, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理赔率数据的缺失值"""
        try:
            match_id = record.get("match_id")
            bookmaker = record.get("bookmaker")

            # 处理缺失的主胜赔率
            if record.get("home_odds") is None:
                avg_odds = await self._get_historical_average_odds(
                    "home_odds",
                    match_id,
                    bookmaker,  # type: ignore
                )
                record["home_odds"] = avg_odds

            # 处理缺失的平局赔率
            if record.get("draw_odds") is None:
                avg_odds = await self._get_historical_average_odds(
                    "draw_odds",
                    match_id,
                    bookmaker,  # type: ignore
                )
                record["draw_odds"] = avg_odds

            # 处理缺失的客胜赔率
            if record.get("away_odds") is None:
                avg_odds = await self._get_historical_average_odds(
                    "away_odds",
                    match_id,
                    bookmaker,  # type: ignore
                )
                record["away_odds"] = avg_odds

            return record

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理赔率缺失值失败: {str(e)}")
            raise MissingValueException(
                f"处理赔率缺失值失败: {str(e)}",
                table_name="odds",
                column_name="odds_values",
            )

    async def _get_historical_average_score(
        self, score_type: str, team_id: int
    ) -> Optional[float]:
        """获取球队历史平均进球数"""
        try:
            async with self.db_manager.get_async_session() as session:
                if score_type == "home":
                    query = text(
                        """
                        SELECT AVG(home_score::float) as avg_score
                        FROM matches
                        WHERE home_team_id = :team_id
                        AND match_status = 'finished'
                        AND home_score IS NOT NULL
                        AND match_time > NOW() - INTERVAL ':days days'
                    """
                    )
                else:  # away
                    query = text(
                        """
                        SELECT AVG(away_score::float) as avg_score
                        FROM matches
                        WHERE away_team_id = :team_id
                        AND match_status = 'finished'
                        AND away_score IS NOT NULL
                        AND match_time > NOW() - INTERVAL ':days days'
                    """
                    )

                result = await session.execute(
                    query,
                    {
                        "team_id": team_id,
                        "days": self.config.get("lookback_days", 30),
                    },
                )
                row = result.fetchone()

                return float(row.avg_score) if row and row.avg_score else None

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取历史平均进球数失败: {str(e)}")
            return None

    async def _get_historical_average_odds(
        self, odds_type: str, match_id: int, bookmaker: str
    ) -> Optional[float]:
        """获取历史平均赔率"""
        try:
            async with self.db_manager.get_async_session() as session:
                # 查询同一博彩商的历史平均赔率
                allowed_odds_types = ["home_odds", "draw_odds", "away_odds"]
                if odds_type not in allowed_odds_types:
                    return None

                # 构建查询
                odds_queries = {
                    "home_odds": text(
                        """
                        SELECT AVG(home_odds::float) as avg_odds
                        FROM odds
                        WHERE bookmaker = :bookmaker
                        AND home_odds IS NOT NULL
                        AND home_odds > 1.0
                        AND collected_at > NOW() - INTERVAL :days_interval
                    """
                    ),
                    "draw_odds": text(
                        """
                        SELECT AVG(draw_odds::float) as avg_odds
                        FROM odds
                        WHERE bookmaker = :bookmaker
                        AND draw_odds IS NOT NULL
                        AND draw_odds > 1.0
                        AND collected_at > NOW() - INTERVAL :days_interval
                    """
                    ),
                    "away_odds": text(
                        """
                        SELECT AVG(away_odds::float) as avg_odds
                        FROM odds
                        WHERE bookmaker = :bookmaker
                        AND away_odds IS NOT NULL
                        AND away_odds > 1.0
                        AND collected_at > NOW() - INTERVAL :days_interval
                    """
                    ),
                }

                query = odds_queries[odds_type]

                result = await session.execute(
                    query,
                    {
                        "bookmaker": bookmaker,
                        "days_interval": f"{self.config.get('lookback_days', 30)} days",
                    },
                )
                row = result.fetchone()

                return float(row.avg_odds) if row and row.avg_odds else None

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取历史平均赔率失败: {str(e)}")
            return None

    async def _log_missing_value_handling(
        self, table_name: str, missing_counts: Dict[str, int]
    ) -> None:
        """记录缺失值处理日志"""
        try:
            from .quality_logger import QualityLogger

            logger = QualityLogger(self.db_manager)
            await logger.log_missing_value_handling(
                table_name, missing_counts, self.config
            )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"记录缺失值处理日志失败: {str(e)}")

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            new_config: 新的配置参数
        """
        self.config.update(new_config)
        self.logger.info(f"缺失值处理器配置已更新: {new_config}")
