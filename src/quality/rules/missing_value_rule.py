"""
Missing Value Rule - 缺失值检查规则

检查关键特征字段是否存在缺失值（None、空字符串、特殊标记值等）。
确保核心特征数据的完整性，防止因数据缺失导致的分析错误。

核心功能：
- 检查多种类型的缺失值（None、空字符串、'N/A'、'-'等）
- 支持配置化的重要字段列表
- 提供详细的缺失值报告
- 支持字段级别的缺失值容忍度

实现版本: P0-3
实现时间: 2025-12-05
依赖: quality_protocol.py
"""

import logging
from typing import Any, Dict, List

from src.quality.quality_protocol import (
    MissingValueRule as MissingValueRuleProtocol,
    DataQualityResult,
    RuleSeverity,
)

logger = logging.getLogger(__name__)


class MissingValueRule(MissingValueRuleProtocol):
    """
    检查关键特征缺失值的数据质量规则实现。

    检查特征数据中关键字段是否为 None、空字符串或特殊标记值。
    主要用于确保核心特征字段的完整性和数据质量。
    """

    def __init__(
        self,
        critical_fields: List[str] = None,
        optional_fields: List[str] = None,
        missing_value_indicators: List[str] = None,
        case_sensitive: bool = True
    ):
        """
        初始化缺失值检查规则。

        Args:
            critical_fields: 必须存在的字段列表，缺失时报告高严重性错误
            optional_fields: 可选字段列表，缺失时报告低严重性警告
            missing_value_indicators: 被视为缺失值的标记列表
            case_sensitive: 是否区分大小写
        """
        self.rule_name = "missing_value_check"
        self.rule_description = "检查关键特征字段的缺失值"

        # 默认关键字段 - 足球预测中的核心特征
        self.critical_fields = critical_fields or [
            "match_id",
            "full_time_score_home",
            "full_time_score_away",
            "xg_home",
            "xg_away",
            "odds_b365_home",
            "odds_b365_draw",
            "odds_b365_away"
        ]

        # 可选字段 - 有用但不是必需的
        self.optional_fields = optional_fields or [
            "shot_home",
            "shot_away",
            "shot_on_target_home",
            "shot_on_target_away",
            "possession_home",
            "possession_away",
            "corners_home",
            "corners_away",
            "fouls_home",
            "fouls_away",
            "cards_yellow_home",
            "cards_yellow_away",
            "cards_red_home",
            "cards_red_away"
        ]

        # 被视为缺失值的标记
        self.missing_value_indicators = missing_value_indicators or [
            None,
            "",
            "null",
            "NULL",
            "n/a",
            "N/A",
            "-",
            "--",
            "na",
            "NA",
            "missing",
            "MISSING"
        ]

        self.case_sensitive = case_sensitive

        logger.debug(
            f"MissingValueRule 初始化: "
            f"关键字段 {len(self.critical_fields)} 个, "
            f"可选字段 {len(self.optional_fields)} 个"
        )

    async def check(self, features: Dict[str, Any]) -> List[str]:
        """
        检查特征数据中的缺失值。

        Args:
            features: 从 FeatureStore 加载的特征数据字典

        Returns:
            List[str]: 发现的缺失值错误描述列表
        """
        errors = []

        if not features:
            return ["特征数据字典为空"]

        # 检查关键字段
        critical_errors = self._check_critical_fields(features)
        errors.extend(critical_errors)

        # 检查可选字段
        optional_errors = self._check_optional_fields(features)
        errors.extend(optional_errors)

        # 记录检查结果
        field_count = len(features)
        critical_count = len([f for f in self.critical_fields if f in features])
        optional_count = len([f for f in self.optional_fields if f in features])

        logger.debug(
            f"缺失值检查完成: 总字段 {field_count} 个, "
            f"关键字段 {critical_count}/{len(self.critical_fields)} 个, "
            f"可选字段 {optional_count}/{len(self.optional_fields)} 个, "
            f"发现 {len(errors)} 个问题"
        )

        return errors

    def _check_critical_fields(self, features: Dict[str, Any]) -> List[str]:
        """
        检查关键字段的缺失值。

        Args:
            features: 特征数据字典

        Returns:
            List[str]: 关键字段的缺失值错误列表
        """
        errors = []

        for field in self.critical_fields:
            if field not in features:
                errors.append(f"关键字段 '{field}' 缺失")
                continue

            value = features[field]
            if self._is_missing_value(value):
                errors.append(f"关键字段 '{field}' 值为缺失: {self._format_value(value)}")

        return errors

    def _check_optional_fields(self, features: Dict[str, Any]) -> List[str]:
        """
        检查可选字段的缺失值。

        Args:
            features: 特征数据字典

        Returns:
            List[str]: 可选字段的缺失值警告列表
        """
        warnings = []

        for field in self.optional_fields:
            if field not in features:
                warnings.append(f"可选字段 '{field}' 缺失")
                continue

            value = features[field]
            if self._is_missing_value(value):
                warnings.append(f"可选字段 '{field}' 值为缺失: {self._format_value(value)}")

        # 可选字段的警告级别较低，这里只是记录
        # 实际使用中可以通过配置决定是否包含在错误中

        return warnings

    def _is_missing_value(self, value: Any) -> bool:
        """
        判断值是否为缺失值。

        Args:
            value: 要检查的值

        Returns:
            bool: 是否为缺失值
        """
        # 直接检查 None
        if value is None:
            return True

        # 检查字符串类型的缺失值
        if isinstance(value, str):
            check_value = value if self.case_sensitive else value.lower()
            indicators = self.missing_value_indicators if self.case_sensitive else [
                indicator.lower() for indicator in self.missing_value_indicators
            ]
            return check_value in indicators

        # 检查数字类型的特殊值（如 NaN, inf 等）
        if isinstance(value, (int, float)):
            try:
                import math
                if math.isnan(value) or math.isinf(value):
                    return True
            except (TypeError, ValueError):
                pass

        return False

    def _format_value(self, value: Any) -> str:
        """
        格式化值用于显示。

        Args:
            value: 要格式化的值

        Returns:
            str: 格式化后的字符串表示
        """
        if value is None:
            return "None"
        elif isinstance(value, str):
            return f"'{value}'"
        else:
            return str(value)

    def get_missing_field_summary(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取缺失字段的详细摘要。

        Args:
            features: 特征数据字典

        Returns:
            Dict[str, Any]: 缺失字段摘要
        """
        summary = {
            "total_fields": len(self.critical_fields + self.optional_fields),
            "available_fields": len(features),
            "critical_missing": [],
            "optional_missing": [],
            "critical_available": [],
            "optional_available": []
        }

        for field in self.critical_fields:
            if field in features and not self._is_missing_value(features[field]):
                summary["critical_available"].append(field)
            else:
                summary["critical_missing"].append(field)

        for field in self.optional_fields:
            if field in features and not self._is_missing_value(features[field]):
                summary["optional_available"].append(field)
            else:
                summary["optional_missing"].append(field)

        # 计算完整性指标
        total_critical = len(self.critical_fields)
        total_optional = len(self.optional_fields)

        summary["critical_completeness"] = (
            (len(summary["critical_available"]) / total_critical) * 100
            if total_critical > 0 else 0
        )

        summary["optional_completeness"] = (
            (len(summary["optional_available"]) / total_optional) * 100
            if total_optional > 0 else 0
        )

        summary["overall_completeness"] = (
            (summary["critical_available"].count + summary["optional_available"].count) /
            (total_critical + total_optional) * 100
            if (total_critical + total_optional) > 0 else 0
        )

        return summary

    def configure_critical_fields(self, fields: List[str]) -> None:
        """
        配置关键字段列表。

        Args:
            fields: 关键字段列表
        """
        self.critical_fields = fields
        logger.info(f"关键字段已更新为: {fields}")

    def configure_optional_fields(self, fields: List[str]) -> None:
        """
        配置可选字段列表。

        Args:
            fields: 可选字段列表
        """
        self.optional_fields = fields
        logger.info(f"可选字段已更新为: {fields}")

    def configure_missing_indicators(self, indicators: List[str]) -> None:
        """
        配置缺失值标记列表。

        Args:
            indicators: 缺失值标记列表
        """
        self.missing_value_indicators = indicators
        logger.info(f"缺失值标记已更新为: {indicators}")