"""
数据质量监控器主类 / Data Quality Monitor Main Class

整合所有检查器，提供统一的数据质量监控接口。
"""

import logging
from typing import Any, Dict, List, Optional

from ..checks.freshness import FreshnessChecker
from ..checks.completeness import CompletenessChecker
from ..checks.consistency import ConsistencyChecker
from ..scores.calculator import QualityScoreCalculator
from ..trends.analyzer import QualityTrendAnalyzer
from .results import DataFreshnessResult, DataCompletenessResult

logger = logging.getLogger(__name__)


class QualityMonitor:
    """
    数据质量监控器主类 / Data Quality Monitor Main Class

    提供以下监控功能：
    - 数据新鲜度监控
    - 数据完整性检查
    - 数据一致性验证
    - 质量评分计算
    - 历史趋势分析
    """

    def __init__(
        self,
        freshness_thresholds: Optional[Dict[str, float]] = None,
        critical_fields: Optional[Dict[str, List[str]]] = None,
    ):
        """
        初始化数据质量监控器

        Args:
            freshness_thresholds: 各表的新鲜度阈值（小时）
            critical_fields: 各表的关键字段列表
        """
        # 初始化各个检查器
        self.freshness_checker = FreshnessChecker(freshness_thresholds)
        self.completeness_checker = CompletenessChecker(critical_fields)
        self.consistency_checker = ConsistencyChecker()

        # 初始化评分计算器和趋势分析器
        self.score_calculator = QualityScoreCalculator(
            self.freshness_checker,
            self.completeness_checker,
            self.consistency_checker,
        )
        self.trend_analyzer = QualityTrendAnalyzer(self.score_calculator)

        logger.info("数据质量监控器初始化完成")

    async def check_data_freshness(
        self, table_names: Optional[List[str]] = None
    ) -> Dict[str, DataFreshnessResult]:
        """
        检查数据新鲜度 / Check Data Freshness

        检查指定表或所有配置表的数据新鲜度，基于最后更新时间计算。
        Check data freshness for specified tables or all configured tables,
        calculated based on last update time.

        Args:
            table_names (Optional[List[str]]): 要检查的表名列表，为空时检查所有配置的表 /
                                              List of table names to check, checks all configured tables if empty
                Defaults to None

        Returns:
            Dict[str, DataFreshnessResult]: 各表的新鲜度检查结果 / Freshness check results for each table
                Keys are table names, values are DataFreshnessResult objects

        Raises:
            Exception: 当数据库查询发生错误时抛出 / Raised when database query fails

        Example:
            ```python
            monitor = QualityMonitor()

            # 检查所有表的新鲜度
            results = await monitor.check_data_freshness()

            # 检查特定表的新鲜度
            results = await monitor.check_data_freshness(["matches", "odds"])

            for table_name, result in results.items():
                if result.is_fresh:
                    print(f"表 {table_name} 数据新鲜 (更新于 {result.freshness_hours} 小时前)")
                else:
                    print(f"表 {table_name} 数据过期 (更新于 {result.freshness_hours} 小时前)")
            ```

        Note:
            新鲜度阈值在初始化时配置。
            Freshness thresholds are configured during initialization.
        """
        return await self.freshness_checker.check_data_freshness(table_names)

    async def check_data_completeness(
        self, table_names: Optional[List[str]] = None
    ) -> Dict[str, DataCompletenessResult]:
        """
        检查数据完整性

        Args:
            table_names: 要检查的表名列表

        Returns:
            Dict[str, DataCompletenessResult]: 各表的完整性检查结果
        """
        return await self.completeness_checker.check_data_completeness(table_names)

    async def check_data_consistency(self) -> Dict[str, Any]:
        """
        检查数据一致性

        Returns:
            Dict[str, Any]: 一致性检查结果
        """
        return await self.consistency_checker.check_data_consistency()

    async def calculate_overall_quality_score(self) -> Dict[str, Any]:
        """
        计算总体数据质量评分

        Returns:
            Dict[str, Any]: 质量评分结果
        """
        return await self.score_calculator.calculate_overall_quality_score()

    async def get_quality_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        获取质量趋势（需要历史数据支持）

        Args:
            days: 查看天数

        Returns:
            Dict[str, Any]: 质量趋势数据
        """
        return await self.trend_analyzer.get_quality_trends(days)

    def _get_quality_level(self, score: float) -> str:
        """
        获取质量等级

        Args:
            score: 质量评分

        Returns:
            str: 质量等级
        """
        return self.score_calculator._get_quality_level(score)

    def _generate_quality_recommendations(
        self, quality_data: Dict[str, Any]
    ) -> List[str]:
        """
        生成质量改进建议

        Args:
            quality_data: 质量数据

        Returns:
            List[str]: 改进建议列表
        """
        return self.trend_analyzer._generate_quality_recommendations(quality_data)