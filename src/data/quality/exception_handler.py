"""
import asyncio
数据质量异常处理机制

实现数据质量问题的自动化处理和修复策略：
1. 缺失值处理：使用历史平均值填充
2. 异常赔率处理：标记为可疑并记录
3. 错误数据处理：写入质量日志供人工排查

基于阶段三要求：
- 缺失值 → 使用历史平均填充
- 异常赔率 → 标记为 suspicious_odds = true
- 错误数据 → 写入 data_quality_logs 表，供人工排查
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager
from src.database.models.data_quality_log import DataQualityLog


class DataQualityException(Exception):
    """数据质量异常基类"""

    pass


class DataQualityExceptionHandler:
    """
    数据质量异常处理器

    负责处理数据质量检查中发现的各类异常和问题，
    实现自动化修复策略和人工排查机制。
    """

    def __init__(self):
        """初始化异常处理器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 异常处理策略配置
        self.handling_strategies = {
            "missing_values": {
                "strategy": "historical_average",
                "lookback_days": 30,
                "min_sample_size": 5,
            },
            "suspicious_odds": {
                "min_odds": 1.01,
                "max_odds": 1000.0,
                "probability_range": [0.95, 1.20],
                "mark_suspicious": True,
            },
            "invalid_scores": {
                "min_score": 0,
                "max_score": 99,
                "require_manual_review": True,
            },
            "data_consistency": {"auto_fix": False, "require_manual_review": True},
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

        except Exception as e:
            self.logger.error(f"处理缺失值失败 {table_name}: {str(e)}")
            await self._log_exception("missing_value_handling", table_name, str(e))
            return records  # 返回原始记录

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
                        "home", record.get("home_team_id")
                    )
                    record["home_score"] = (
                        round(avg_score) if avg_score is not None else 0
                    )

                if record.get("away_score") is None:
                    avg_score = await self._get_historical_average_score(
                        "away", record.get("away_team_id")
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

        except Exception as e:
            self.logger.error(f"处理比赛缺失值失败: {str(e)}")
            return record

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
                    "home_odds", match_id, bookmaker
                )
                record["home_odds"] = avg_odds

            # 处理缺失的平局赔率
            if record.get("draw_odds") is None:
                avg_odds = await self._get_historical_average_odds(
                    "draw_odds", match_id, bookmaker
                )
                record["draw_odds"] = avg_odds

            # 处理缺失的客胜赔率
            if record.get("away_odds") is None:
                avg_odds = await self._get_historical_average_odds(
                    "away_odds", match_id, bookmaker
                )
                record["away_odds"] = avg_odds

            return record

        except Exception as e:
            self.logger.error(f"处理赔率缺失值失败: {str(e)}")
            return record

    async def handle_suspicious_odds(
        self, odds_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理可疑赔率

        Args:
            odds_records: 赔率记录列表

        Returns:
            Dict: 处理结果统计
        """
        try:
            suspicious_count = 0
            processed_records = []

            async with self.db_manager.get_async_session() as session:
                for record in odds_records:
                    is_suspicious = self._is_odds_suspicious(record)

                    if is_suspicious:
                        # 标记为可疑赔率
                        record["suspicious_odds"] = True
                        suspicious_count += 1

                        # 记录可疑赔率日志
                        await self._log_suspicious_odds(session, record)
                    else:
                        record["suspicious_odds"] = False

                    processed_records.append(record)

            result = {
                "total_processed": len(odds_records),
                "suspicious_count": suspicious_count,
                "processed_records": processed_records,
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(
                f"可疑赔率处理完成：{suspicious_count}/{len(odds_records)} 条记录被标记为可疑"
            )
            return result

        except Exception as e:
            self.logger.error(f"处理可疑赔率失败: {str(e)}")
            await self._log_exception("suspicious_odds_handling", "odds", str(e))
            return {
                "total_processed": len(odds_records),
                "suspicious_count": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _is_odds_suspicious(self, odds_record: Dict[str, Any]) -> bool:
        """判断赔率是否可疑"""
        try:
            home_odds = odds_record.get("home_odds")
            draw_odds = odds_record.get("draw_odds")
            away_odds = odds_record.get("away_odds")

            # 检查赔率是否为空
            if any(odds is None for odds in [home_odds, draw_odds, away_odds]):
                return False  # 缺失值不算可疑，由缺失值处理器处理

            # 检查赔率范围
            min_odds = self.handling_strategies["suspicious_odds"]["min_odds"]
            max_odds = self.handling_strategies["suspicious_odds"]["max_odds"]

            for odds in [home_odds, draw_odds, away_odds]:
                if odds < min_odds or odds > max_odds:
                    return True

            # 检查隐含概率总和
            try:
                total_probability = sum(
                    1 / odds for odds in [home_odds, draw_odds, away_odds]
                )
                prob_range = self.handling_strategies["suspicious_odds"][
                    "probability_range"
                ]

                if (
                    total_probability < prob_range[0]
                    or total_probability > prob_range[1]
                ):
                    return True
            except (ZeroDivisionError, TypeError):
                return True  # 无法计算概率，认为可疑

            return False

        except Exception as e:
            self.logger.error(f"判断赔率可疑性失败: {str(e)}")
            return True  # 出错时保守处理，标记为可疑

    async def handle_invalid_data(
        self, table_name: str, invalid_records: List[Dict[str, Any]], error_type: str
    ) -> Dict[str, Any]:
        """
        处理无效数据

        Args:
            table_name: 表名
            invalid_records: 无效记录列表
            error_type: 错误类型

        Returns:
            Dict: 处理结果
        """
        try:
            logged_count = 0

            async with self.db_manager.get_async_session() as session:
                for record in invalid_records:
                    # 写入数据质量日志表
                    await self._create_quality_log(
                        session=session,
                        table_name=table_name,
                        record_id=record.get("id"),
                        error_type=error_type,
                        error_data=record,
                        requires_manual_review=True,
                    )
                    logged_count += 1

            result = {
                "table_name": table_name,
                "error_type": error_type,
                "invalid_records_count": len(invalid_records),
                "logged_count": logged_count,
                "requires_manual_review": True,
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.warning(
                f"无效数据处理完成：表 {table_name}，错误类型 {error_type}，"
                f"{logged_count} 条记录已记录到质量日志"
            )

            return result

        except Exception as e:
            self.logger.error(f"处理无效数据失败: {str(e)}")
            await self._log_exception("invalid_data_handling", table_name, str(e))
            return {
                "table_name": table_name,
                "error_type": error_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

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
                        "days": self.handling_strategies["missing_values"][
                            "lookback_days"
                        ],
                    },
                )
                row = result.fetchone()

                return float(row.avg_score) if row and row.avg_score else None

        except Exception as e:
            self.logger.error(f"获取历史平均进球数失败: {str(e)}")
            return None

    async def _get_historical_average_odds(
        self, odds_type: str, match_id: int, bookmaker: str
    ) -> Optional[float]:
        """获取历史平均赔率"""
        try:
            async with self.db_manager.get_async_session() as session:
                # 查询同一博彩商的历史平均赔率 - 使用白名单验证列名
                allowed_odds_types = ["home_odds", "draw_odds", "away_odds"]
                if odds_type not in allowed_odds_types:
                    return None

                # Use column mapping for safe query construction
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
                        "days_interval": f"{self.handling_strategies['missing_values']['lookback_days']} days",
                    },
                )
                row = result.fetchone()

                return float(row.avg_odds) if row and row.avg_odds else None

        except Exception as e:
            self.logger.error(f"获取历史平均赔率失败: {str(e)}")
            return None

    async def _log_suspicious_odds(
        self, session: AsyncSession, odds_record: Dict[str, Any]
    ) -> None:
        """记录可疑赔率到日志"""
        try:
            await self._create_quality_log(
                session=session,
                table_name="odds",
                record_id=odds_record.get("id"),
                error_type="suspicious_odds",
                error_data={
                    "match_id": odds_record.get("match_id"),
                    "bookmaker": odds_record.get("bookmaker"),
                    "home_odds": odds_record.get("home_odds"),
                    "draw_odds": odds_record.get("draw_odds"),
                    "away_odds": odds_record.get("away_odds"),
                    "collected_at": odds_record.get("collected_at"),
                },
                requires_manual_review=False,
            )

        except Exception as e:
            self.logger.error(f"记录可疑赔率日志失败: {str(e)}")

    async def _log_missing_value_handling(
        self, table_name: str, missing_counts: Dict[str, int]
    ) -> None:
        """记录缺失值处理日志"""
        try:
            async with self.db_manager.get_async_session() as session:
                await self._create_quality_log(
                    session=session,
                    table_name=table_name,
                    record_id=None,
                    error_type="missing_values_filled",
                    error_data={
                        "filled_columns": missing_counts,
                        "total_filled": sum(missing_counts.values()),
                        "strategy": self.handling_strategies["missing_values"][
                            "strategy"
                        ],
                    },
                    requires_manual_review=False,
                )

        except Exception as e:
            self.logger.error(f"记录缺失值处理日志失败: {str(e)}")

    async def _create_quality_log(
        self,
        session: AsyncSession,
        table_name: str,
        record_id: Optional[int],
        error_type: str,
        error_data: Dict[str, Any],
        requires_manual_review: bool,
    ) -> None:
        """创建数据质量日志记录"""
        try:
            quality_log = DataQualityLog(
                table_name=table_name,
                record_id=record_id,
                error_type=error_type,
                error_data=error_data,
                requires_manual_review=requires_manual_review,
                status="logged",
                detected_at=datetime.now(),
            )

            session.add(quality_log)
            await session.commit()

        except Exception as e:
            self.logger.error(f"创建质量日志记录失败: {str(e)}")
            await session.rollback()

    async def _log_exception(
        self, operation: str, table_name: str, error_message: str
    ) -> None:
        """记录异常处理日志"""
        try:
            async with self.db_manager.get_async_session() as session:
                await self._create_quality_log(
                    session=session,
                    table_name=table_name,
                    record_id=None,
                    error_type=f"exception_handling_{operation}",
                    error_data={
                        "operation": operation,
                        "error_message": error_message,
                        "timestamp": datetime.now().isoformat(),
                    },
                    requires_manual_review=True,
                )

        except Exception as e:
            self.logger.error(f"记录异常处理日志失败: {str(e)}")

    async def get_handling_statistics(self) -> Dict[str, Any]:
        """
        获取异常处理统计信息

        Returns:
            Dict: 处理统计
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 查询最近24小时的处理统计
                query = text(
                    """
                    SELECT
                        error_type,
                        table_name,
                        COUNT(*) as count,
                        COUNT(CASE WHEN requires_manual_review THEN 1 END) as manual_review_count
                    FROM data_quality_logs
                    WHERE detected_at > NOW() - INTERVAL '24 hours'
                    GROUP BY error_type, table_name
                    ORDER BY count DESC
                """
                )

                result = await session.execute(query)
                rows = result.fetchall()

                statistics = {
                    "period": "last_24_hours",
                    "total_issues": sum(row.count for row in rows),
                    "manual_review_required": sum(
                        row.manual_review_count for row in rows
                    ),
                    "by_error_type": {},
                    "by_table": {},
                    "timestamp": datetime.now().isoformat(),
                }

                for row in rows:
                    # 按错误类型统计
                    if row.error_type not in statistics["by_error_type"]:
                        statistics["by_error_type"][row.error_type] = 0
                    statistics["by_error_type"][row.error_type] += row.count

                    # 按表统计
                    if row.table_name not in statistics["by_table"]:
                        statistics["by_table"][row.table_name] = 0
                    statistics["by_table"][row.table_name] += row.count

                return statistics

        except Exception as e:
            self.logger.error(f"获取处理统计失败: {str(e)}")
            return {
                "period": "last_24_hours",
                "total_issues": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
