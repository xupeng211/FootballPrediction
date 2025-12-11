"""
Range Rule - 数值范围检查规则

检查数值特征是否在预期的合理范围内。
基于业务知识和统计分布，定义数值特征的合理取值范围，用于发现异常值和可能的数据录入错误。

核心功能：
- 支持不同类型数值的范围检查（整数、浮点数）
- 可配置的范围阈值和容忍度
- 支持相对范围和绝对范围检查
- 提供详细的范围违规报告
- 支持字段级别的自定义范围

实现版本: P0-3
实现时间: 2025-12-05
依赖: quality_protocol.py
"""

import logging
from typing import Any, Optional


from src.quality.quality_protocol import (
    RangeRule as RangeRuleProtocol,
    RuleSeverity,
)

logger = logging.getLogger(__name__)


class RangeRule(RangeRuleProtocol):
    """
    检查数值特征范围的数据质量规则实现。

    基于业务知识和统计分布，定义数值特征的合理取值范围。
    用于发现异常值、数据录入错误和不合理的数值。
    """

    def __init__(
        self,
        field_ranges: Optional[dict[str, tuple[float, float]]] = None,
        tolerance: float = 0.0,
        strict_mode: bool = True,
    ):
        """
        初始化数值范围检查规则。

        Args:
            field_ranges: 字段范围配置字典 {field_name: (min_value, max_value)}
            tolerance: 容忍度，允许超出范围的百分比 (0.0-1.0)
            strict_mode: 严格模式，为True时超出范围直接失败，为False时仅警告
        """
        self.rule_name = "range_check"
        self.rule_description = "检查数值特征的取值范围是否合理"

        # 默认的字段范围配置 - 基于足球业务常识
        self.field_ranges = field_ranges or {
            # 比分相关范围 (0-99, 足过正常足球比分)
            "full_time_score_home": (0, 99),
            "full_time_score_away": (0, 99),
            "half_time_score_home": (0, 99),
            "half_time_score_away": (0, 99),
            # xG 期望进球数 (0-10, 足过极端情况)
            "xg_home": (0.0, 10.0),
            "xg_away": (0.0, 10.0),
            "xg_draw": (0.0, 5.0),
            # 射门数 (0-50, 超过正常比赛数据)
            "shot_home": (0, 50),
            "shot_away": (0, 50),
            "shot_on_target_home": (0, 30),
            "shot_on_target_away": (0, 30),
            # 控球率 (0-100, 百分比)
            "possession_home": (0.0, 100.0),
            "possession_away": (0.0, 100.0),
            # 角球数 (0-30, 超过正常比赛)
            "corners_home": (0, 30),
            "corners_away": (0, 30),
            # 犯规数 (0-20, 超过正常比赛)
            "fouls_home": (0, 20),
            "fouls_away": (0, 20),
            # 黄牌数 (0-10, 超过正常比赛)
            "cards_yellow_home": (0, 10),
            "cards_yellow_away": (0, 10),
            # 红牌数 (0-5, 超过正常比赛)
            "cards_red_home": (0, 5),
            "cards_red_away": (0, 5),
            # 赔率相关 (1.01-100.0, 正常赔率范围)
            "odds_b365_home": (1.01, 100.0),
            "odds_b365_draw": (1.01, 100.0),
            "odds_b365_away": (1.01, 100.0),
            # 传球数 (0-1000, 超过正常比赛)
            "passes_home": (0, 1000),
            "passes_away": (0, 1000),
            # 越位数 (0-100, 超过正常比赛)
            "crosses_home": (0, 100),
            "crosses_away": (0, 100),
            # 比分差计算范围 (-50, 50)
            "score_difference": (-50, 50),
            # 总进球数范围 (0-150)
            "total_goals": (0, 150),
        }

        self.tolerance = tolerance
        self.strict_mode = strict_mode

        logger.debug(
            f"RangeRule 初始化: 配置了 {len(self.field_ranges)} 个字段的范围检查, "
            f"容忍度 {self.tolerance}, 严格模式 {self.strict_mode}"
        )

    async def check(self, features: dict[str, Any]) -> list[str]:
        """
        检查特征数据中的数值范围。

        Args:
            features: 从 FeatureStore 加载的特征数据字典

        Returns:
            list[str]: 发现的范围违规错误描述列表
        """
        errors = []

        if not features:
            return ["特征数据字典为空"]

        # 检查每个配置了范围的字段
        for field_name, (min_val, max_val) in self.field_ranges.items():
            if field_name not in features:
                continue  # 字段缺失由 MissingValueRule 检查

            value = features[field_name]

            # 检查值是否为数值类型
            if not isinstance(value, int | float):
                continue  # 非数值类型由 TypeRule 检查

            # 检查范围
            violation = self._check_value_range(field_name, value, min_val, max_val)

            if violation:
                self._determine_severity(violation)
                errors.append(violation)

        logger.debug(
            f"范围检查完成: 检查了 {len(self.field_ranges)} 个字段, "
            f"发现 {len(errors)} 个范围违规"
        )

        return errors

    def _check_value_range(
        self, field_name: str, value: float, min_val: float, max_val: float
    ) -> Optional[str]:
        """
        检查单个值是否在指定范围内。

        Args:
            field_name: 字段名称
            value: 要检查的数值
            min_val: 最小值
            max_val: 最大值

        Returns:
            Optional[str]: 范围违规描述，如果没有违规返回None
        """
        # 处理特殊情况：无穷大值
        try:
            import math

            if math.isinf(value):
                return f"字段 '{field_name}' 值为无穷大: {value}"
            if math.isnan(value):
                return f"字段 '{field_name}' 值为 NaN"
        except ValueError:
            pass

        # 检查范围
        if value < min_val or value > max_val:
            # 应用容忍度
            if self.tolerance > 0:
                range_width = max_val - min_val
                tolerance_amount = range_width * self.tolerance

                min_with_tolerance = min_val - tolerance_amount
                max_with_tolerance = max_val + tolerance_amount

                if min_with_tolerance <= value <= max_with_tolerance:
                    return None  # 在容忍范围内

            # 构造错误信息
            if value < min_val:
                return (
                    f"字段 '{field_name}' 值 {value} 小于最小值 {min_val} "
                    f"(超出范围 {abs(value - min_val):.2f})"
                )
            else:
                return (
                    f"字段 '{field_name}' 值 {value} 大于最大值 {max_val} "
                    f"(超出范围 {abs(value - max_val):.2f})"
                )

        return None

    def _determine_severity(self, error_message: str) -> str:
        """
        根据错误信息确定严重程度。

        Args:
            error_message: 错误信息

        Returns:
            str: 严重程度
        """
        # 基于违规程度确定严重性
        if any(
            keyword in error_message.lower()
            for keyword in ["无穷大", "nan", "超出范围 1e"]
        ):
            return RuleSeverity.HIGH
        elif any(
            keyword in error_message.lower() for keyword in ["超出范围 1", "超出范围 5"]
        ):
            return RuleSeverity.MEDIUM
        else:
            return RuleSeverity.LOW

    def get_field_range(self, field_name: str) -> Optional[tuple[float, float]]:
        """
        获取指定字段的范围配置。

        Args:
            field_name: 字段名称

        Returns:
            Optional[tuple[float, float]]: (min_value, max_value)，如果未配置返回None
        """
        return self.field_ranges.get(field_name)

    def configure_field_range(
        self, field_name: str, min_value: float, max_value: float
    ) -> None:
        """
        配置字段的检查范围。

        Args:
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
        """
        if min_value > max_value:
            raise ValueError(f"最小值 {min_value} 不能大于最大值 {max_value}")

        self.field_ranges[field_name] = (min_value, max_value)
        logger.info(f"字段 '{field_name}' 范围已设置为: [{min_value}, {max_value}]")

    def configure_tolerance(self, tolerance: float) -> None:
        """
        配置容忍度。

        Args:
            tolerance: 容忍度 (0.0-1.0)
        """
        if not 0.0 <= tolerance <= 1.0:
            raise ValueError("容忍度必须在 0.0 到 1.0 之间")

        self.tolerance = tolerance
        logger.info(f"容忍度已设置为: {tolerance}")

    def configure_strict_mode(self, strict_mode: bool) -> None:
        """
        配置严格模式。

        Args:
            strict_mode: 是否启用严格模式
        """
        self.strict_mode = strict_mode
        logger.info(f"严格模式已设置为: {strict_mode}")

    def validate_field_ranges(self) -> list[str]:
        """
        验证所有字段范围配置的有效性。

        Returns:
            list[str]: 配置错误列表，空列表表示配置有效
        """
        errors = []

        for field_name, (min_val, max_val) in self.field_ranges.items():
            try:
                if min_val > max_val:
                    errors.append(
                        f"字段 '{field_name}' 最小值 {min_val} 大于最大值 {max_val}"
                    )
            except Exception as e:
                errors.append(f"字段 '{field_name}' 范围配置错误: {str(e)}")

        return errors

    def get_range_summary(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        获取范围检查的详细摘要。

        Args:
            features: 特征数据字典

        Returns:
            dict[str, Any]: 范围检查摘要
        """
        summary = {
            "total_configured_fields": len(self.field_ranges),
            "checked_fields": 0,
            "within_range": 0,
            "out_of_range": 0,
            "field_details": {},
            "violations": [],
        }

        for field_name, (min_val, max_val) in self.field_ranges.items():
            if field_name not in features:
                continue  # 字段缺失

            value = features[field_name]
            if not isinstance(value, int | float):
                continue  # 非数值，跳过范围检查

            summary["checked_fields"] += 1

            violation = self._check_value_range(field_name, value, min_val, max_val)

            field_detail = {
                "field_name": field_name,
                "value": value,
                "min_val": min_val,
                "max_val": max_val,
                "in_range": violation is None,
                "violation": violation,
            }

            summary["field_details"][field_name] = field_detail

            if violation is None:
                summary["within_range"] += 1
            else:
                summary["out_of_range"] += 1
                summary["violations"].append(violation)

        # 计算合规率
        if summary["checked_fields"] > 0:
            summary["compliance_rate"] = (
                summary["within_range"] / summary["checked_fields"] * 100
            )
        else:
            summary["compliance_rate"] = 0

        return summary
