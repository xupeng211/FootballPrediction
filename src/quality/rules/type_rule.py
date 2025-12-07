"""
Type Rule - 数据类型检查规则

检查特征字段的数据类型是否正确。
确保数值字段为float/int，字符串字段为str，防止类型错误导致的计算异常。

核心功能：
- 支持多种数据类型的检查（int, float, str, bool等）
- 支持类型转换和兼容性检查
- 可配置的类型映射关系
- 提供详细的类型错误报告
- 支持字段级别的类型要求

实现版本: P0-3
实现时间: 2025-12-05
依赖: quality_protocol.py
"""

import logging
from typing import Any, Dict, List, Optional, Type

from src.quality.quality_protocol import (
    TypeRule as TypeRuleProtocol,
    DataQualityResult,
    RuleSeverity,
)

logger = logging.getLogger(__name__)


class TypeRule(TypeRuleProtocol):
    """
    检查特征数据类型的数据质量规则实现。

    确保特征字段的数据类型符合预期，如数值字段为 float/int，
    字符串字段为 str 等。防止类型错误导致的计算异常。
    """

    def __init__(
        self,
        field_types: Optional[dict[str, type]] = None,
        strict_type_checking: bool = True,
        allow_type_conversion: bool = True,
    ):
        """
        初始化数据类型检查规则。

        Args:
            field_types: 字段类型映射字典 {field_name: expected_type}
            strict_type_checking: 是否进行严格类型检查
            allow_type_conversion: 是否允许类型转换
        """
        self.rule_name = "type_check"
        self.rule_description = "检查特征字段的数据类型是否正确"

        # 默认的字段类型配置 - 基于足球预测业务
        self.field_types = field_types or {
            # 比分相关 - 应该为整数
            "full_time_score_home": int,
            "full_time_score_away": int,
            "half_time_score_home": int,
            "half_time_score_away": int,
            # xG相关 - 应该为浮点数
            "xg_home": float,
            "xg_away": float,
            "xg_draw": float,
            # 射门相关 - 应该为整数
            "shot_home": int,
            "shot_away": int,
            "shot_on_target_home": int,
            "shot_on_target_away": int,
            # 控球率 - 应该为浮点数（百分比）
            "possession_home": float,
            "possession_away": float,
            # 角球数 - 应该为整数
            "corners_home": int,
            "corners_away": int,
            # 犯规数 - 应该为整数
            "fouls_home": int,
            "fouls_away": int,
            # 牌牌数 - 应该为整数
            "cards_yellow_home": int,
            "cards_yellow_away": int,
            "cards_red_home": int,
            "cards_red_away": int,
            # 赔率相关 - 应该为浮点数
            "odds_b365_home": float,
            "odds_b365_draw": float,
            "odds_b365_away": float,
            # 传球数 - 应该为整数
            "passes_home": int,
            "passes_away": int,
            "passes_accurate_home": int,
            "passes_accurate_away": int,
            # 越位数 - 应该为整数
            "crosses_home": int,
            "crosses_away": int,
            "crosses_accurate_home": int,
            "crosses_accurate_away": int,
            # 比赛ID - 应该为整数
            "match_id": int,
            # 时间戳 - 应该为字符串或数字
            "match_time": str,  # ISO格式字符串
            # 比赛状态 - 应该为字符串
            "match_status": str,
            # 球队ID - 应该为整数
            "home_team_id": int,
            "away_team_id": int,
            # 联赛日 - 应该为字符串或数字
            "match_date": str,
        }

        self.strict_type_checking = strict_type_checking
        self.allow_type_conversion = allow_type_conversion

        logger.debug(
            f"TypeRule 初始化: 配置了 {len(self.field_types)} 个字段的类型检查, "
            f"严格模式 {self.strict_type_checking}, 允许转换 {self.allow_type_conversion}"
        )

    async def check(self, features: dict[str, Any]) -> list[str]:
        """
        检查特征数据中的数据类型。

        Args:
            features: 从 FeatureStore 加载的特征数据字典

        Returns:
            List[str]: 发现的类型错误描述列表
        """
        errors = []

        if not features:
            return ["特征数据字典为空"]

        # 检查每个配置了类型的字段
        for field_name, expected_type in self.field_types.items():
            if field_name not in features:
                continue  # 字段缺失由 MissingValueRule 检查

            value = features[field_name]
            type_error = self._check_field_type(field_name, value, expected_type)

            if type_error:
                self._determine_severity(type_error)
                errors.append(type_error)

        logger.debug(
            f"类型检查完成: 检查了 {len(self.field_types)} 个字段, "
            f"发现 {len(errors)} 个类型错误"
        )

        return errors

    def _check_field_type(
        self, field_name: str, value: Any, expected_type: type
    ) -> Optional[str]:
        """
        检查单个字段的数据类型。

        Args:
            field_name: 字段名称
            value: 要检查的值
            expected_type: 期望的类型

        Returns:
            Optional[str]: 类型错误描述，如果没有错误返回None
        """
        # 处理 None 值 - 由 MissingValueRule 检查
        if value is None:
            return None

        # 直接类型检查
        if isinstance(value, expected_type):
            return None

        # 允许类型转换的情况
        if self.allow_type_conversion:
            try:
                converted_value = self._convert_type(value, expected_type)
                if converted_value is not None:
                    # 转换成功，更新字段值（这里只是模拟，实际不会修改原数据）
                    logger.debug(
                        f"字段 '{field_name}' 类型转换成功: "
                        f"{type(value).__name__} -> {expected_type.__name__}"
                    )
                    return None
            except Exception as e:
                return (
                    f"字段 '{field_name}' 类型转换失败: {type(value).__name__} -> {expected_type.__name__}, "
                    f"错误: {str(e)}"
                )

        # 严格模式或转换失败时报告错误
        if self.strict_type_checking:
            return (
                f"字段 '{field_name}' 类型错误: 期望 {expected_type.__name__}, "
                f"实际 {type(value).__name__}, 值: {self._format_value(value)}"
            )
        else:
            return (
                f"字段 '{field_name}' 类型警告: 期望 {expected_type.__name__}, "
                f"实际 {type(value).__name__}, 值: {self._format_value(value)}"
            )

    def _convert_type(self, value: Any, target_type: type) -> Optional[Any]:
        """
        尝试将值转换为目标类型。

        Args:
            value: 要转换的值
            target_type: 目标类型

        Returns:
            Optional[Any]: 转换后的值，失败返回None
        """
        try:
            # 特殊处理 None 值
            if value is None:
                return None

            # 转换到整数
            if target_type is int:
                if isinstance(value, int | float):
                    return int(float(value))
                elif isinstance(value, str):
                    # 尝试解析字符串为整数
                    stripped_value = value.strip()
                    if stripped_value.isdigit() or (
                        stripped_value.startswith("-") and stripped_value[1:].isdigit()
                    ):
                        return int(stripped_value)
                return None

            # 转换到浮点数
            elif target_type is float:
                if isinstance(value, int | float):
                    return float(value)
                elif isinstance(value, str):
                    stripped_value = value.strip()
                    try:
                        return float(stripped_value)
                    except ValueError:
                        return None
                return None

            # 转换到字符串
            elif target_type is str:
                return str(value)

            # 转换到布尔值
            elif target_type is bool:
                if isinstance(value, bool):
                    return value
                elif isinstance(value, int | float):
                    return bool(value)
                elif isinstance(value, str):
                    lowered = value.lower().strip()
                    if lowered in ("true", "1", "yes", "on"):
                        return True
                    elif lowered in ("false", "0", "no", "off"):
                        return False
                return None

            return None

        except Exception:
            return None

    def _determine_severity(self, error_message: str) -> str:
        """
        根据错误信息确定严重程度。

        Args:
            error_message: 错误信息

        Returns:
            str: 严重程度
        """
        # 基于字段类型和错误类型确定严重性
        if any(
            keyword in error_message.lower()
            for keyword in ["match_id", "team_id", "score"]
        ):
            return RuleSeverity.HIGH
        elif any(
            keyword in error_message.lower() for keyword in ["xg", "odds", "critical"]
        ):
            return RuleSeverity.MEDIUM
        else:
            return RuleSeverity.LOW

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
            return f"{value} ({type(value).__name__})"

    def get_expected_type(self, field_name: str) -> Optional[type]:
        """
        获取指定字段的期望类型。

        Args:
            field_name: 字段名称

        Returns:
            Optional[Type]: 期望的类型，如果未配置返回None
        """
        return self.field_types.get(field_name)

    def configure_field_type(self, field_name: str, expected_type: type) -> None:
        """
        配置字段的期望类型。

        Args:
            field_name: 字段名称
            expected_type: 期望的类型
        """
        if not isinstance(expected_type, type):
            raise ValueError("expected_type 必须是一个类型对象")

        self.field_types[field_name] = expected_type
        logger.info(f"字段 '{field_name}' 期望类型已设置为: {expected_type.__name__}")

    def configure_strict_mode(self, strict_mode: bool) -> None:
        """
        配置严格模式。

        Args:
            strict_mode: 是否启用严格模式
        """
        self.strict_type_checking = strict_mode
        logger.info(f"严格模式已设置为: {strict_mode}")

    def configure_type_conversion(self, allow_conversion: bool) -> None:
        """
        配置是否允许类型转换。

        Args:
            allow_conversion: 是否允许类型转换
        """
        self.allow_type_conversion = allow_conversion
        logger.info(f"类型转换已设置为: {allow_conversion}")

    def validate_type_configuration(self) -> list[str]:
        """
        验证类型配置的有效性。

        Returns:
            List[str]: 配置错误列表，空列表表示配置有效
        """
        errors = []

        for field_name, expected_type in self.field_types.items():
            try:
                if not isinstance(expected_type, type):
                    errors.append(
                        f"字段 '{field_name}' 配置的类型 {expected_type} 不是有效的类型对象"
                    )
            except Exception as e:
                errors.append(f"字段 '{field_name}' 类型配置错误: {str(e)}")

        return errors

    def get_type_summary(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        获取类型检查的详细摘要。

        Args:
            features: 特征数据字典

        Returns:
            Dict[str, Any]: 类型检查摘要
        """
        summary = {
            "total_configured_fields": len(self.field_types),
            "checked_fields": 0,
            "type_matches": 0,
            "type_mismatches": 0,
            "type_conversions": 0,
            "field_details": {},
            "errors": [],
        }

        for field_name, expected_type in self.field_types.items():
            if field_name not in features:
                continue  # 字段缺失

            value = features[field_name]
            summary["checked_fields"] += 1

            field_detail = {
                "field_name": field_name,
                "actual_type": type(value).__name__,
                "expected_type": expected_type.__name__,
                "value": self._format_value(value),
                "type_match": isinstance(value, expected_type),
                "can_convert": self._can_convert_type(value, expected_type),
            }

            summary["field_details"][field_name] = field_detail

            if isinstance(value, expected_type):
                summary["type_matches"] += 1
            else:
                summary["type_mismatches"] += 1

                # 检查是否可以转换
                if self.allow_type_conversion and field_detail["can_convert"]:
                    summary["type_conversions"] += 1

            # 模拟类型检查（仅用于摘要）
            error = self._check_field_type(field_name, value, expected_type)
            if error:
                summary["errors"].append(error)

        # 计算合规率
        if summary["checked_fields"] > 0:
            summary["compliance_rate"] = (
                (summary["type_matches"] + summary["type_conversions"])
                / summary["checked_fields"]
                * 100
            )
        else:
            summary["compliance_rate"] = 0

        return summary

    def _can_convert_type(self, value: Any, target_type: type) -> bool:
        """
        检查值是否可以转换为目标类型。

        Args:
            value: 要检查的值
            target_type: 目标类型

        Returns:
            bool: 是否可以转换
        """
        if self.allow_type_conversion:
            try:
                converted = self._convert_type(value, target_type)
                return converted is not None
            except Exception:
                # 类型转换失败是预期的行为，返回False即可
                return False

        return False
