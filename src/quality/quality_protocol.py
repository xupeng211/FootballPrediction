"""
Data Quality Rules Protocol - 数据质量规则标准接口

定义数据质量检查的统一协议接口，支持可插拔的规则系统。
与 P0-2 FeatureStore 完全集成，提供现代化的异步数据质量检查能力。

核心功能：
- 统一的数据质量规则接口定义
- 支持多种类型的数据质量检查规则
- 与 FeatureStoreProtocol 完全兼容
- 异步处理支持
- JSON-safe 错误报告格式

生成时间: 2025-12-05
作者: Data Engineering Lead
"""

from typing import Protocol, Any, List
from src.features.feature_store_interface import FeatureStoreProtocol


class DataQualityRule(Protocol):
    """数据质量规则的抽象协议。

    定义所有数据质量规则必须实现的标准接口，确保规则的可插拔性和一致性。
    所有规则都应该是异步的，以支持大规模数据处理场景。
    """

    # 规则的唯一名称，用于报告输出和日志记录
    rule_name: str

    # 规则的描述，说明规则的具体用途和检查内容
    rule_description: str

    async def check(self, features: dict[str, Any]) -> list[str]:
        """
        检查特征数据是否满足规则要求。

        Args:
            features: 从 FeatureStore 加载的特征数据字典，包含所有相关特征字段
                     格式: {feature_name: feature_value, ...}

        Returns:
            list[str]: 如果发现数据质量问题，返回错误描述字符串列表；
                     如果数据完全符合规则要求，返回空列表 []。
                     错误描述应该简洁明了，便于后续分析和报告。

        Examples:
            >>> # 示例：MissingValueRule 的实现
            >>> if features.get('xg_home') is None:
            ...     return ["xg_home 字段缺失"]
            >>> return []

            >>> # 示例：RangeRule 的实现
            >>> xg = features.get('xg_home', 0)
            >>> if xg < 0 or xg > 10:
            ...     return [f"xg_home 值 {xg} 超出合理范围 [0, 10]"]
            >>> return []
        """
        ...


class RuleSeverity:
    """规则严重程度枚举。

    定义不同严重程度的数据质量问题，用于优先级处理和告警分级。
    """
    LOW = "low"          # 低严重性：轻微的数据质量问题，不影响核心功能
    MEDIUM = "medium"    # 中等严重性：可能影响分析结果，需要关注
    HIGH = "high"        # 高严重性：严重影响数据质量，需要立即处理
    CRITICAL = "critical" # 关键严重性：导致系统无法正常工作，必须立即修复


class DataQualityResult:
    """数据质量检查结果的标准格式。

    提供统一的数据质量检查结果数据结构，便于报告生成和分析。
    所有结果都应该是 JSON-safe 的，便于序列化和存储。
    """

    def __init__(
        self,
        rule_name: str,
        passed: bool,
        errors: List[str],
        severity: str = RuleSeverity.MEDIUM,
        metadata: dict[str, Any] = None
    ):
        """
        初始化数据质量检查结果。

        Args:
            rule_name: 执行的规则名称
            passed: 是否通过检查 (True/False)
            errors: 错误信息列表，通过时为空列表
            severity: 问题严重程度 (LOW/MEDIUM/HIGH/CRITICAL)
            metadata: 额外的元数据信息，如检查时间、数据版本等
        """
        self.rule_name = rule_name
        self.passed = passed
        self.errors = errors
        self.severity = severity
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，确保 JSON-safe。"""
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "errors": self.errors,
            "severity": self.severity,
            "metadata": self.metadata
        }


# 具体规则类型的 Protocol 定义
class MissingValueRule(DataQualityRule):
    """检查关键特征的缺失值规则。

    检查特征数据中关键字段是否为 None、空字符串或特殊标记值。
    主要用于确保核心特征字段的完整性。
    """
    rule_name: str = "missing_value_check"
    rule_description: str = "检查关键特征字段的缺失值"


class RangeRule(DataQualityRule):
    """检查数值特征是否在预期的合理范围内。

    基于业务知识和统计分布，定义数值特征的合理取值范围。
    用于发现异常值和可能的数据录入错误。
    """
    rule_name: str = "range_check"
    rule_description: str = "检查数值特征的取值范围是否合理"


class TypeRule(DataQualityRule):
    """检查特征的数据类型是否正确。

    确保特征字段的数据类型符合预期，如数值字段为 float/int，
    字符串字段为 str 等。防止类型错误导致的计算异常。
    """
    rule_name: str = "type_check"
    rule_description: str = "检查特征字段的数据类型是否正确"


class LogicalRelationRule(DataQualityRule):
    """检查特征之间是否满足逻辑关系。

    基于足球业务的逻辑约束，检查不同特征之间的逻辑一致性。
    例如：进球数 <= 射门数，xG 值合理等。
    """
    rule_name: str = "logical_relation_check"
    rule_description: str = "检查特征之间的逻辑关系是否一致"


class ConsistencyRule(DataQualityRule):
    """检查数据一致性的通用规则。

    检查数据在不同时间点或不同来源间的一致性，
    确保数据的可信度和可靠性。
    """
    rule_name: str = "consistency_check"
    rule_description: str = "检查数据的一致性和可信度"


class CompletenessRule(DataQualityRule):
    """检查数据完整性的规则。

    评估数据集的完整性，包括字段覆盖率、
    记录完整度等方面。
    """
    rule_name: str = "completeness_check"
    rule_description: str = "检查数据的完整性和覆盖率"


class TimelinessRule(DataQualityRule):
    """检查数据及时性的规则。

    评估数据的新鲜度和更新频率，
    确保数据的时效性满足业务需求。
    """
    rule_name: str = "timeliness_check"
    rule_description: str = "检查数据的及时性和新鲜度"


class UniquenessRule(DataQualityRule):
    """检查数据唯一性的规则。

    检查关键字段或记录组合的唯一性，
    防止重复数据导致的统计偏差。
    """
    rule_name: str = "uniqueness_check"
    rule_description: str = "检查数据的唯一性，防止重复记录"


# 规则工厂接口定义
class RuleFactory(Protocol):
    """规则工厂协议，用于创建和配置数据质量规则实例。"""

    def create_rule(self, rule_type: str, config: dict[str, Any]) -> DataQualityRule:
        """
        根据规则类型和配置创建规则实例。

        Args:
            rule_type: 规则类型标识符
            config: 规则配置参数

        Returns:
            DataQualityRule: 配置好的规则实例
        """
        ...


# 常用规则类型映射
RULE_TYPES = {
    "missing_value": MissingValueRule,
    "range": RangeRule,
    "type": TypeRule,
    "logical_relation": LogicalRelationRule,
    "consistency": ConsistencyRule,
    "completeness": CompletenessRule,
    "timeliness": TimelinessRule,
    "uniqueness": UniquenessRule,
}


def get_rule_class(rule_type: str) -> type[DataQualityRule]:
    """
    根据规则类型获取对应的规则类。

    Args:
        rule_type: 规则类型字符串

    Returns:
        type[DataQualityRule]: 对应的规则类

    Raises:
        ValueError: 当规则类型不存在时
    """
    if rule_type not in RULE_TYPES:
        available_types = ", ".join(RULE_TYPES.keys())
        raise ValueError(
            f"未知的规则类型: {rule_type}. "
            f"可用的规则类型: {available_types}"
        )

    return RULE_TYPES[rule_type]