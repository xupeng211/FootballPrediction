#!/usr/bin/env python3
"""
V20.5 数据资产一致性卫士
========================

功能:
- 在保存到 match_features_training 之前强制验证
- 哪怕舍弃数据也不允许格式错误写入数据库
- Schema 验证、数据类型检查、值域约束

作者: SRE Team
日期: 2025-12-24
版本: V20.5
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证严重级别"""

    WARNING = "warning"  # 警告，但允许保存
    ERROR = "error"  # 错误，拒绝保存
    CRITICAL = "critical"  # 严重错误，强制拒绝


@dataclass
class ValidationIssue:
    """验证问题"""

    field_name: str
    severity: ValidationSeverity
    message: str
    actual_value: Any = None
    expected_type: str = None


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        """获取所有错误级别的问题"""
        return [
            i
            for i in self.issues
            if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
        ]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """获取所有警告级别的问题"""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def add_error(
        self, field: str, message: str, actual_value: Any = None, expected_type: str | None = None
    ):
        """添加错误"""
        self.issues.append(
            ValidationIssue(
                field_name=field,
                severity=ValidationSeverity.ERROR,
                message=message,
                actual_value=actual_value,
                expected_type=expected_type,
            )
        )
        self.is_valid = False

    def add_warning(self, field: str, message: str, actual_value: Any = None):
        """添加警告"""
        self.issues.append(
            ValidationIssue(
                field_name=field,
                severity=ValidationSeverity.WARNING,
                message=message,
                actual_value=actual_value,
            )
        )

    def add_critical(self, field: str, message: str, actual_value: Any = None):
        """添加严重错误"""
        self.issues.append(
            ValidationIssue(
                field_name=field,
                severity=ValidationSeverity.CRITICAL,
                message=message,
                actual_value=actual_value,
            )
        )
        self.is_valid = False

    def summary(self) -> str:
        """生成摘要"""
        error_count = len(self.errors)
        warning_count = len(self.warnings)

        status = "✅ 有效" if self.is_valid else "❌ 无效"
        summary = f"{status} | 错误: {error_count}, 警告: {warning_count}"

        if self.errors:
            summary += "\n错误详情:\n"
            for issue in self.errors[:5]:  # 只显示前5个
                summary += f"  - [{issue.field_name}] {issue.message}\n"
            if len(self.errors) > 5:
                summary += f"  ... 还有 {len(self.errors) - 5} 个错误\n"

        if self.warnings and len(self.warnings) <= 10:
            summary += "\n警告详情:\n"
            for issue in self.warnings:
                summary += f"  - [{issue.field_name}] {issue.message}\n"

        return summary


class FeatureSchemaValidator:
    """特征 Schema 验证器"""

    # 允许的特征名模式 (字母开头，可包含字母、数字、下划线)
    FEATURE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    # 必需字段
    REQUIRED_FIELDS: set[str] = {"match_id", "league_id", "season_id", "home_team", "away_team"}

    # 有效值域约束
    VALUE_CONSTRAINTS: dict[str, tuple[float, float]] = {
        "possession": (0, 100),  # 控球率 0-100%
        "rating": (0, 10),  # 评分 0-10
        "xg": (0, 10),  # xG 0-10
        "passes": (0, 2000),  # 传球数
        "shots": (0, 50),  # 射门数
    }

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: 严格模式，任何验证失败都拒绝保存
        """
        self.strict_mode = strict_mode
        logger.info(f"数据验证卫士初始化: strict_mode={strict_mode}")

    def validate_match_features(
        self, match_data: dict[str, Any], features: dict[str, Any]
    ) -> ValidationResult:
        """
        验证比赛特征数据

        Args:
            match_data: 比赛元数据 {match_id, league_id, season_id, ...}
            features: 提取的特征字典

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # 1. 验证必需字段
        self._validate_required_fields(match_data, result)

        # 2. 验证特征名格式
        self._validate_feature_names(features, result)

        # 3. 验证特征值类型
        self._validate_feature_types(features, result)

        # 4. 验证特征值域
        self._validate_value_ranges(features, result)

        # 5. 验证特征数量合理性
        self._validate_feature_count(features, result)

        # 严格模式下，任何错误都标记为无效
        if self.strict_mode and result.errors:
            result.is_valid = False

        return result

    def _validate_required_fields(self, match_data: dict[str, Any], result: ValidationResult):
        """验证必需字段"""
        for field in self.REQUIRED_FIELDS:
            if field not in match_data or match_data[field] is None:
                result.add_critical(
                    field=field, message="必需字段缺失或为空", actual_value=match_data.get(field)
                )

    def _validate_feature_names(self, features: dict[str, Any], result: ValidationResult):
        """验证特征名格式"""
        for name in features:
            if not isinstance(name, str):
                result.add_error(
                    field=str(name),
                    message=f"特征名必须是字符串，实际类型: {type(name)}",
                    actual_value=name,
                    expected_type="str",
                )
                continue

            if not self.FEATURE_NAME_PATTERN.match(name):
                result.add_warning(field=name, message=f"特征名不符合命名规范: {name}")

    def _validate_feature_types(self, features: dict[str, Any], result: ValidationResult):
        """验证特征值类型"""
        valid_types = (int, float, bool, str, type(None))

        for name, value in features.items():
            # 允许的原子类型
            if isinstance(value, valid_types):
                continue

            # 允许列表/字典 (用于 JSONB 存储)
            if isinstance(value, (list, dict)):
                # 检查嵌套元素
                if isinstance(value, list) and len(value) > 0 and not all(
                    isinstance(v, (valid_types, list, dict)) for v in value
                ):
                    result.add_warning(field=name, message="列表包含无效类型的元素")
                continue

            result.add_error(
                field=name,
                message=f"特征值类型无效: {type(value)}",
                actual_value=value,
                expected_type="int/float/bool/str/list/dict/None",
            )

    def _validate_value_ranges(self, features: dict[str, Any], result: ValidationResult):
        """验证特征值域"""
        for name, value in features.items():
            if not isinstance(value, (int, float)):
                continue

            # V20.5.3 FIX: 跳过 diff_* 字段的值范围验证
            # diff_* 字段表示差值，可以为负数
            if name.startswith("diff_"):
                continue

            # 检查预定义约束
            for constraint_key, (min_val, max_val) in self.VALUE_CONSTRAINTS.items():
                if constraint_key in name.lower():
                    if value < min_val or value > max_val:
                        result.add_error(
                            field=name,
                            message=f"值 {value} 超出约束范围 [{min_val}, {max_val}]",
                            actual_value=value,
                        )
                    break

            # 检查 NaN/Inf
            import math

            if math.isnan(value) or math.isinf(value):
                result.add_error(field=name, message="包含 NaN 或 Inf 值", actual_value=value)

    def _validate_feature_count(self, features: dict[str, Any], result: ValidationResult):
        """验证特征数量合理性"""
        feature_count = len(features)

        # V20.5.3 FIX: 动态特征数阈值
        # 全息模式 (3 periods): >= 600
        # 兼容模式 (1 period): >= 250
        MIN_HOLOGRAPHIC = 600
        MIN_COMPATIBILITY = 250

        if feature_count < MIN_COMPATIBILITY:
            result.add_error(
                field="feature_count",
                message=f"特征数量 {feature_count} 低于最小阈值 {MIN_COMPATIBILITY}",
            )
        elif feature_count < MIN_HOLOGRAPHIC:
            result.add_warning(
                field="feature_count",
                message=f"特征数量 {feature_count} 低于全息模式预期 ({MIN_HOLOGRAPHIC}+), 可能是兼容模式",
            )

        # 异常高特征数可能表示数据错误
        if feature_count > 2000:
            result.add_warning(
                field="feature_count", message=f"特征数量 {feature_count} 异常高，可能包含冗余数据"
            )


class DataGuard:
    """
    数据卫士 - 门卫模式

    在数据写入数据库前进行最后把关
    """

    def __init__(self, validator: FeatureSchemaValidator = None, enable_logging: bool = True):
        self.validator = validator or FeatureSchemaValidator(strict_mode=True)
        self.enable_logging = enable_logging
        self._rejected_count = 0
        self._accepted_count = 0

    def verify_before_save(
        self, match_data: dict[str, Any], features: dict[str, Any]
    ) -> tuple[bool, ValidationResult]:
        """
        在保存前验证数据

        Args:
            match_data: 比赛元数据
            features: 特征字典

        Returns:
            (是否允许保存, 验证结果)
        """
        result = self.validator.validate_match_features(match_data, features)

        if result.is_valid:
            self._accepted_count += 1
            if self.enable_logging:
                logger.info(f"✅ Match {match_data.get('match_id')} 数据验证通过")
            return True, result
        self._rejected_count += 1
        logger.error(f"❌ Match {match_data.get('match_id')} 数据验证失败:\n{result.summary()}")
        return False, result

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        total = self._accepted_count + self._rejected_count
        return {
            "accepted": self._accepted_count,
            "rejected": self._rejected_count,
            "total": total,
            "rejection_rate": self._rejected_count / total if total > 0 else 0,
        }


# 全局单例
_data_guard_instance: DataGuard | None = None


def get_data_guard() -> DataGuard:
    """获取全局数据卫士实例"""
    global _data_guard_instance
    if _data_guard_instance is None:
        _data_guard_instance = DataGuard()
    return _data_guard_instance


def verify_schema(match_data: dict[str, Any], features: dict[str, Any]) -> bool:
    """
    便捷函数: 验证数据 Schema

    Args:
        match_data: 比赛元数据
        features: 特征字典

    Returns:
        True 如果验证通过，False 否则
    """
    guard = get_data_guard()
    allowed, _ = guard.verify_before_save(match_data, features)
    return allowed
