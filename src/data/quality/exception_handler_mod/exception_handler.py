"""
数据质量异常处理器主模块

协调各个子处理器，提供统一的数据质量异常处理接口。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .exceptions import DataQualityException
from .missing_value_handler import MissingValueHandler
from .suspicious_odds_handler import SuspiciousOddsHandler
from .invalid_data_handler import InvalidDataHandler
from .quality_logger import QualityLogger
from .statistics_provider import StatisticsProvider


class DataQualityExceptionHandler:
    """
    数据质量异常处理器

    负责处理数据质量检查中发现的各类异常和问题，
    实现自动化修复策略和人工排查机制。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化异常处理器

        Args:
            config: 配置参数
        """
        from ...database.connection import DatabaseManager  # type: ignore

        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")

        # 配置参数
        self.config = config or self._get_default_config()

        # 初始化子处理器
        self.missing_value_handler = MissingValueHandler(
            self.db_manager, self.config.get("missing_values", {})
        )
        self.suspicious_odds_handler = SuspiciousOddsHandler(
            self.db_manager, self.config.get("suspicious_odds", {})
        )
        self.invalid_data_handler = InvalidDataHandler(
            self.db_manager, self.config.get("invalid_data", {})
        )
        self.quality_logger = QualityLogger(self.db_manager)
        self.statistics_provider = StatisticsProvider(self.db_manager)  # type: ignore

        self.logger.info("数据质量异常处理器初始化完成")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
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
            "invalid_data": {
                "require_manual_review": True,
                "batch_size": 100,
                "max_retry_attempts": 3,
            },
            "data_consistency": {
                "auto_fix": False,
                "require_manual_review": True,
            },
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
            return await self.missing_value_handler.handle_missing_values(
                table_name, records
            )
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理缺失值失败: {str(e)}")
            await self.quality_logger.log_exception(
                "missing_value_handling", table_name, str(e)
            )
            return records  # 返回原始记录

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
            return await self.suspicious_odds_handler.handle_suspicious_odds(
                odds_records
            )
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理可疑赔率失败: {str(e)}")
            await self.quality_logger.log_exception(
                "suspicious_odds_handling", "odds", str(e)
            )
            return {
                "total_processed": len(odds_records),
                "suspicious_count": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

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
            return await self.invalid_data_handler.handle_invalid_data(
                table_name, invalid_records, error_type
            )
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"处理无效数据失败: {str(e)}")
            await self.quality_logger.log_exception(
                "invalid_data_handling", table_name, str(e)
            )
            return {
                "table_name": table_name,
                "error_type": error_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def validate_data_integrity(
        self, table_name: str, records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证数据完整性

        Args:
            table_name: 表名
            records: 待验证的记录列表

        Returns:
            Dict: 验证结果
        """
        return await self.invalid_data_handler.validate_data_integrity(
            table_name, records
        )

    async def analyze_suspicious_patterns(
        self, odds_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析可疑赔率模式

        Args:
            odds_records: 赔率记录列表

        Returns:
            Dict: 分析结果
        """
        return await self.suspicious_odds_handler.analyze_suspicious_patterns(
            odds_records
        )

    async def get_handling_statistics(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        获取异常处理统计信息

        Args:
            period_hours: 统计周期（小时）

        Returns:
            Dict: 处理统计
        """
        try:
            return await self.statistics_provider.get_handling_statistics(period_hours)  # type: ignore
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取处理统计失败: {str(e)}")
            return {
                "period_hours": period_hours,
                "total_issues": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_quality_dashboard(
        self, table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取数据质量仪表板数据

        Args:
            table_name: 表名（可选）

        Returns:
            Dict: 仪表板数据
        """
        try:
            # 并行获取各种统计数据
            import asyncio

            tasks = [
                self.statistics_provider.get_handling_statistics(24),  # type: ignore
                self.statistics_provider.get_daily_trend(7),  # type: ignore
                self.statistics_provider.get_top_issues(10, 24),  # type: ignore
                self.statistics_provider.get_quality_score(table_name),  # type: ignore
                self.quality_logger.get_pending_reviews(table_name, 20),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            dashboard = {
                "table_name": table_name,
                "last_24h_stats": results[0]
                if not isinstance(results[0], Exception)
                else {},
                "daily_trend": results[1]
                if not isinstance(results[1], Exception)
                else [],
                "top_issues": results[2]
                if not isinstance(results[2], Exception)
                else [],
                "quality_score": results[3]
                if not isinstance(results[3], Exception)
                else {},
                "pending_reviews": results[4]
                if not isinstance(results[4], Exception)
                else [],
                "timestamp": datetime.now().isoformat(),
            }

            return dashboard

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取质量仪表板失败: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def process_quality_report(
        self, table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成质量报告

        Args:
            table_name: 表名（可选）

        Returns:
            Dict: 质量报告
        """
        try:
            # 获取统计数据
            stats = await self.get_handling_statistics(24 * 7)  # 最近7天
            quality_score = await self.statistics_provider.get_quality_score(table_name)  # type: ignore
            pending_reviews = await self.quality_logger.get_pending_reviews(table_name)

            # 生成报告
            report = {
                "report_period": "7_days",
                "table_name": table_name,
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_issues": stats.get("total_issues", 0),
                    "quality_score": quality_score.get("quality_score", 0),
                    "quality_grade": quality_score.get("grade", "N/A"),
                    "pending_reviews": len(pending_reviews),
                },
                "statistics": stats,
                "quality_metrics": quality_score,
                "recommendations": self._generate_recommendations(stats, quality_score),
            }

            return report

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"生成质量报告失败: {str(e)}")
            raise DataQualityException(
                f"生成质量报告失败: {str(e)}", error_code="QUALITY_REPORT_ERROR"
            )

    def _generate_recommendations(
        self, stats: Dict[str, Any], quality_score: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于质量评分的建议
        score = quality_score.get("quality_score", 0)
        if score < 0.8:
            recommendations.append("数据质量评分较低，建议检查数据源质量")

        # 基于问题类型的建议
        error_types = stats.get("by_error_type", {})
        if "missing_values_filled" in error_types:
            recommendations.append("存在较多缺失值，建议改进数据收集流程")

        if "suspicious_odds" in error_types:
            recommendations.append("发现可疑赔率，建议增加赔率验证规则")

        if "invalid_data" in error_types:
            recommendations.append("存在无效数据，建议加强数据验证机制")

        # 基于待审核数量的建议
        pending = stats.get("pending_review", 0)
        if pending > 100:
            recommendations.append(f"有{pending}条待审核记录，建议及时处理")

        return recommendations

    def update_config(self, module: str, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            module: 模块名称
            new_config: 新的配置参数
        """
        if module in self.config:
            self.config[module].update(new_config)

            # 更新对应的处理器配置
            if module == "missing_values":
                self.missing_value_handler.update_config(new_config)
            elif module == "suspicious_odds":
                self.suspicious_odds_handler.update_config(new_config)
            elif module == "invalid_data":
                self.invalid_data_handler.update_config(new_config)

            self.logger.info(f"{module} 模块配置已更新: {new_config}")

    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要

        Returns:
            Dict: 配置摘要
        """
        return {
            "missing_values": self.missing_value_handler.config,
            "suspicious_odds": self.suspicious_odds_handler.get_config_summary(),
            "invalid_data": self.invalid_data_handler.config,
        }
