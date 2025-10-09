"""
数据质量评分计算器 / Data Quality Score Calculator

负责计算数据质量的综合评分。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from ..checks.freshness import FreshnessChecker
from ..checks.completeness import CompletenessChecker
from ..checks.consistency import ConsistencyChecker

logger = logging.getLogger(__name__)


class QualityScoreCalculator:
    """数据质量评分计算器"""

    def __init__(
        self,
        freshness_checker: FreshnessChecker,
        completeness_checker: CompletenessChecker,
        consistency_checker: ConsistencyChecker,
    ):
        """
        初始化评分计算器

        Args:
            freshness_checker: 新鲜度检查器
            completeness_checker: 完整性检查器
            consistency_checker: 一致性检查器
        """
        self.freshness_checker = freshness_checker
        self.completeness_checker = completeness_checker
        self.consistency_checker = consistency_checker

    async def calculate_overall_quality_score(self) -> Dict[str, Any]:
        """
        计算总体数据质量评分

        Returns:
            Dict[str, Any]: 质量评分结果
        """
        try:
            # 获取各项检查结果
            freshness_results = await self.freshness_checker.check_data_freshness()
            completeness_results = await self.completeness_checker.check_data_completeness()
            consistency_results = await self.consistency_checker.check_data_consistency()

            # 计算新鲜度得分
            fresh_tables = sum(1 for r in freshness_results.values() if r.is_fresh)
            freshness_score = (
                (fresh_tables / len(freshness_results)) * 100
                if freshness_results
                else 0
            )

            # 计算完整性得分
            completeness_scores = [
                r.completeness_score for r in completeness_results.values()
            ]
            avg_completeness_score = (
                sum(completeness_scores) / len(completeness_scores)
                if completeness_scores
                else 0
            )

            # 计算一致性得分（基于错误数量）
            consistency_errors = 0
            fk_consistency = consistency_results.get(str("foreign_key_consistency"), {})
            odds_consistency = consistency_results.get(str("odds_consistency"), {})
            match_consistency = consistency_results.get(
                str("match_status_consistency"), {}
            )

            consistency_errors += sum(
                v for v in fk_consistency.values() if isinstance(v, int)
            )
            consistency_errors += sum(
                v for v in odds_consistency.values() if isinstance(v, int)
            )
            consistency_errors += sum(
                v for v in match_consistency.values() if isinstance(v, int)
            )

            # 一致性得分：错误数量越少分数越高
            consistency_score = max(0, 100 - consistency_errors * 0.1)

            # 计算总体评分（加权平均）
            overall_score = (
                freshness_score * 0.3
                + avg_completeness_score * 0.4
                + consistency_score * 0.3
            )

            return {
                "overall_score": round(overall_score, 2),
                "freshness_score": round(freshness_score, 2),
                "completeness_score": round(avg_completeness_score, 2),
                "consistency_score": round(consistency_score, 2),
                "detailed_results": {
                    "freshness": {
                        table: result.to_dict()
                        for table, result in freshness_results.items()
                    },
                    "completeness": {
                        table: result.to_dict()
                        for table, result in completeness_results.items()
                    },
                    "consistency": consistency_results,
                },
                "quality_level": self._get_quality_level(overall_score),
                "check_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"计算总体质量评分失败: {e}")
            return {
                "overall_score": 0,
                "error": str(e),
                "check_time": datetime.now().isoformat(),
            }

    def _get_quality_level(self, score: float) -> str:
        """
        获取质量等级

        Args:
            score: 质量评分

        Returns:
            str: 质量等级
        """
        if score >= 95:
            return "优秀"
        elif score >= 85:
            return "良好"
        elif score >= 70:
            return "一般"
        elif score >= 50:
            return "较差"
        else:
            return "很差"