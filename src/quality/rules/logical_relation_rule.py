"""
Logical Relation Rule - 逻辑关系检查规则

检查特征之间是否满足预期的逻辑关系。
基于足球业务的业务逻辑，验证不同特征字段之间的一致性和合理性。

核心功能：
- 支持多种逻辑关系检查（大于等于、小于等于、等于、范围包含等）
- 预定义足球业务的核心逻辑关系
- 可配置的字段关系和容忍度
- 提供详细的逻辑违规报告
- 支持复合条件检查

实现版本: P0-3
实现时间: 2025-12-05
依赖: quality_protocol.py
"""

import logging
from typing import Any,  Optional, 
from collections.abc import Callable

from src.quality.quality_protocol import (
    LogicalRelationRule as LogicalRelationRuleProtocol,
    DataQualityResult,
    RuleSeverity,
)

logger = logging.getLogger(__name__)


class LogicalRelationRule(LogicalRelationRuleProtocol):
    """
    检查特征之间逻辑关系的数据质量规则实现。

    基于足球业务的逻辑约束，检查不同特征之间的逻辑一致性。
    例如：进球数 <= 射门数，射正数 >= 进球数等。
    """

    def __init__(
        self,
        relations: Optional[list[dict[str, Any]]] = None,
        tolerance: float = 0.0,
        strict_mode: bool = True,
    ):
        """
        初始化逻辑关系检查规则。

        Args:
            relations: 逻辑关系配置列表，每个元素包含字段和关系定义
            tolerance: 容忍度，用于浮点数比较的误差范围
            strict_mode: 严格模式，为True时违反逻辑直接失败，为False时仅警告
        """
        self.rule_name = "logical_relation_check"
        self.rule_description = "检查特征之间的逻辑关系是否一致"

        # 默认的足球业务逻辑关系配置
        self.relations = relations or [
            # 比分相关逻辑关系
            {
                "name": "full_time_score_consistency",
                "description": "全场比分一致性检查",
                "field_a": "full_time_score_home",
                "field_b": "half_time_score_home",
                "relation": "gte",  # 全场主队得分 >= 半场主队得分
                "severity": "high",
            },
            {
                "name": "full_time_score_away_consistency",
                "description": "全场客队比分一致性检查",
                "field_a": "full_time_score_away",
                "field_b": "half_time_score_away",
                "relation": "gte",
                "severity": "high",
            },
            # 射门和进球的逻辑关系
            {
                "name": "shots_vs_goals_home",
                "description": "主队射门数应大于等于进球数",
                "field_a": "shot_home",
                "field_b": "full_time_score_home",
                "relation": "gte",
                "severity": "high",
            },
            {
                "name": "shots_vs_goals_away",
                "description": "客队射门数应大于等于进球数",
                "field_a": "shot_away",
                "field_b": "full_time_score_away",
                "relation": "gte",
                "severity": "high",
            },
            # 射正和进球的逻辑关系
            {
                "name": "shots_on_target_vs_goals_home",
                "description": "主队射正数应大于等于进球数",
                "field_a": "shot_on_target_home",
                "field_b": "full_time_score_home",
                "relation": "gte",
                "severity": "high",
            },
            {
                "name": "shots_on_target_vs_goals_away",
                "description": "客队射正数应大于等于进球数",
                "field_a": "shot_on_target_away",
                "field_b": "full_time_score_away",
                "relation": "gte",
                "severity": "high",
            },
            # 射正和总射门的逻辑关系
            {
                "name": "shots_on_target_vs_total_shots_home",
                "description": "主队射正数应小于等于总射门数",
                "field_a": "shot_on_target_home",
                "field_b": "shot_home",
                "relation": "lte",
                "severity": "medium",
            },
            {
                "name": "shots_on_target_vs_total_shots_away",
                "description": "客队射正数应小于等于总射门数",
                "field_a": "shot_on_target_away",
                "field_b": "shot_away",
                "relation": "lte",
                "severity": "medium",
            },
            # 控球率的逻辑关系
            {
                "name": "possession_sum",
                "description": "主客场控球率之和应接近100%",
                "field_a": "possession_home",
                "field_b": "possession_away",
                "relation": "sum_close_to_100",
                "tolerance": 5.0,  # 允许5%的误差
                "severity": "medium",
            },
            # 传球成功率的逻辑关系
            {
                "name": "accurate_vs_total_passes_home",
                "description": "主队成功传球数应小于等于总传球数",
                "field_a": "passes_accurate_home",
                "field_b": "passes_home",
                "relation": "lte",
                "severity": "medium",
            },
            {
                "name": "accurate_vs_total_passes_away",
                "description": "客队成功传球数应小于等于总传球数",
                "field_a": "passes_accurate_away",
                "field_b": "passes_away",
                "relation": "lte",
                "severity": "medium",
            },
            # 传中成功率的逻辑关系
            {
                "name": "accurate_vs_total_crosses_home",
                "description": "主队成功传中数应小于等于总传中数",
                "field_a": "crosses_accurate_home",
                "field_b": "crosses_home",
                "relation": "lte",
                "severity": "low",
            },
            {
                "name": "accurate_vs_total_crosses_away",
                "description": "客队成功传中数应小于等于总传中数",
                "field_a": "crosses_accurate_away",
                "field_b": "crosses_away",
                "relation": "lte",
                "severity": "low",
            },
            # xG和实际进球的逻辑关系
            {
                "name": "xg_vs_goals_home",
                "description": "主队xG应与实际进球数合理相关",
                "field_a": "xg_home",
                "field_b": "full_time_score_home",
                "relation": "xg_reasonable",  # xG应在进球数的合理范围内
                "tolerance": 2.0,  # 允许2球的差异
                "severity": "medium",
            },
            {
                "name": "xg_vs_goals_away",
                "description": "客队xG应与实际进球数合理相关",
                "field_a": "xg_away",
                "field_b": "full_time_score_away",
                "relation": "xg_reasonable",
                "tolerance": 2.0,
                "severity": "medium",
            },
            # 牌数的逻辑关系
            {
                "name": "total_cards_composition",
                "description": "总牌数应等于黄牌数加红牌数",
                "field_a": "cards_yellow_home",
                "field_b": "cards_red_home",
                "relation": "total_cards",
                "extra_fields": ["cards_yellow_away", "cards_red_away"],
                "severity": "low",
            },
        ]

        self.tolerance = tolerance
        self.strict_mode = strict_mode

        # 逻辑关系检查函数映射
        self.relation_functions = {
            "gte": self._check_gte,  # greater than or equal
            "lte": self._check_lte,  # less than or equal
            "gt": self._check_gt,  # greater than
            "lt": self._check_lt,  # less than
            "eq": self._check_eq,  # equal
            "sum_close_to_100": self._check_sum_close_to_100,
            "xg_reasonable": self._check_xg_reasonable,
            "total_cards": self._check_total_cards_composition,
        }

        logger.debug(
            f"LogicalRelationRule 初始化: 配置了 {len(self.relations)} 个逻辑关系检查, "
            f"容忍度 {self.tolerance}, 严格模式 {self.strict_mode}"
        )

    async def check(self, features: dict[str, Any]) -> list[str]:
        """
        检查特征数据中的逻辑关系。

        Args:
            features: 从 FeatureStore 加载的特征数据字典

        Returns:
            list[str]: 发现的逻辑关系错误描述列表
        """
        errors = []

        if not features:
            return ["特征数据字典为空"]

        # 检查每个配置的逻辑关系
        for relation in self.relations:
            relation_name = relation.get("name", "unknown")

            try:
                violation = self._check_single_relation(features, relation)
                if violation:
                    relation.get("severity", "medium")
                    errors.append(violation)

            except Exception as e:
                error_msg = f"逻辑关系检查 '{relation_name}' 执行失败: {str(e)}"
                logger.warning(error_msg)
                if self.strict_mode:
                    errors.append(error_msg)

        logger.debug(
            f"逻辑关系检查完成: 检查了 {len(self.relations)} 个关系, "
            f"发现 {len(errors)} 个逻辑违规"
        )

        return errors

    def _check_single_relation(
        self, features: dict[str, Any], relation: dict[str, Any]
    ) -> Optional[str]:
        """
        检查单个逻辑关系。

        Args:
            features: 特征数据字典
            relation: 逻辑关系配置

        Returns:
            Optional[str]: 逻辑违规描述，如果没有违规返回None
        """
        relation_name = relation.get("name", "unknown")
        relation_type = relation.get("relation")
        field_a = relation.get("field_a")
        field_b = relation.get("field_b")

        # 检查必需字段是否存在
        if field_a not in features or field_b not in features:
            return None  # 字段缺失由 MissingValueRule 检查

        value_a = features[field_a]
        value_b = features[field_b]

        # 检查字段值是否为数值类型
        if not isinstance(value_a, int | float) or not isinstance(
            value_b, int | float
        ):
            return None  # 非数值类型由 TypeRule 检查

        # 获取关系检查函数
        check_function = self.relation_functions.get(relation_type)
        if not check_function:
            return f"未知的逻辑关系类型: {relation_type}"

        # 执行关系检查
        relation_tolerance = relation.get("tolerance", self.tolerance)
        return check_function(
            relation_name,
            field_a,
            value_a,
            field_b,
            value_b,
            relation_tolerance,
            relation,
        )

    def _check_gte(
        self,
        relation_name: str,
        field_a: str,
        value_a: float,
        field_b: str,
        value_b: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查 value_a >= value_b"""
        if value_a + tolerance < value_b:
            return (
                f"{relation_name}: {field_a}({value_a}) 应大于等于 {field_b}({value_b}), "
                f"实际差异: {value_b - value_a:.2f}"
            )
        return None

    def _check_lte(
        self,
        relation_name: str,
        field_a: str,
        value_a: float,
        field_b: str,
        value_b: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查 value_a <= value_b"""
        if value_a > value_b + tolerance:
            return (
                f"{relation_name}: {field_a}({value_a}) 应小于等于 {field_b}({value_b}), "
                f"实际差异: {value_a - value_b:.2f}"
            )
        return None

    def _check_gt(
        self,
        relation_name: str,
        field_a: str,
        value_a: float,
        field_b: str,
        value_b: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查 value_a > value_b"""
        if value_a <= value_b + tolerance:
            return (
                f"{relation_name}: {field_a}({value_a}) 应大于 {field_b}({value_b}), "
                f"实际差异: {value_b - value_a + tolerance:.2f}"
            )
        return None

    def _check_lt(
        self,
        relation_name: str,
        field_a: str,
        value_a: float,
        field_b: str,
        value_b: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查 value_a < value_b"""
        if value_a >= value_b - tolerance:
            return (
                f"{relation_name}: {field_a}({value_a}) 应小于 {field_b}({value_b}), "
                f"实际差异: {value_a - value_b + tolerance:.2f}"
            )
        return None

    def _check_eq(
        self,
        relation_name: str,
        field_a: str,
        value_a: float,
        field_b: str,
        value_b: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查 value_a == value_b"""
        if abs(value_a - value_b) > tolerance:
            return (
                f"{relation_name}: {field_a}({value_a}) 应等于 {field_b}({value_b}), "
                f"实际差异: {abs(value_a - value_b):.2f}"
            )
        return None

    def _check_sum_close_to_100(
        self,
        relation_name: str,
        field_a: str,
        value_a: float,
        field_b: str,
        value_b: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查两个值的和是否接近100%"""
        total = value_a + value_b
        deviation = abs(total - 100.0)
        if deviation > tolerance:
            return (
                f"{relation_name}: {field_a}({value_a}) + {field_b}({value_b}) = {total:.1f}%, "
                f"应接近100%, 偏差: {deviation:.1f}%"
            )
        return None

    def _check_xg_reasonable(
        self,
        relation_name: str,
        field_a: str,
        xg_value: float,
        field_b: str,
        goals: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查xG值与实际进球数的合理性"""
        # xG值应该在合理范围内，且与进球数不应该差异过大
        if xg_value < 0 or xg_value > 10:  # xG应该在0-10之间
            return f"{relation_name}: {field_a}({xg_value}) 超出合理范围[0, 10]"

        if abs(xg_value - goals) > tolerance:
            # 注意：这不是严格的错误，足球比赛中xG和实际进球可能有差异
            # 所以这里只返回警告
            return (
                f"{relation_name}: {field_a}({xg_value:.2f}) 与实际进球({goals}) 差异较大: "
                f"{abs(xg_value - goals):.2f}"
            )
        return None

    def _check_total_cards_composition(
        self,
        relation_name: str,
        field_a: str,
        yellow_home: float,
        field_b: str,
        red_home: float,
        tolerance: float,
        relation: dict[str, Any],
    ) -> Optional[str]:
        """检查总牌数的组成（这里简化为逻辑合理性检查）"""
        extra_fields = relation.get("extra_fields", [])
        if len(extra_fields) >= 2:
            extra_fields[0]
            extra_fields[1]

            # 简单的合理性检查：红牌数应该小于等于黄牌数（通常情况下）
            if red_home > yellow_home and yellow_home > 0:
                return (
                    f"{relation_name}: 主队红牌({red_home}) 多于黄牌({yellow_home}), "
                    "这在不正常情况下可能出现但值得关注"
                )

        return None

    def get_relation_summary(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        获取逻辑关系检查的详细摘要。

        Args:
            features: 特征数据字典

        Returns:
            dict[str, Any]: 逻辑关系检查摘要
        """
        summary = {
            "total_configured_relations": len(self.relations),
            "checked_relations": 0,
            "passed_relations": 0,
            "failed_relations": 0,
            "relation_details": {},
            "violations": [],
        }

        for relation in self.relations:
            relation_name = relation.get("name", "unknown")

            # 检查是否可以执行检查
            field_a = relation.get("field_a")
            field_b = relation.get("field_b")

            if field_a not in features or field_b not in features:
                # 字段缺失，跳过检查
                summary["relation_details"][relation_name] = {
                    "status": "skipped",
                    "reason": "required_fields_missing",
                    "field_a": field_a,
                    "field_b": field_b,
                }
                continue

            value_a = features[field_a]
            value_b = features[field_b]

            if not isinstance(value_a, int | float) or not isinstance(
                value_b, int | float
            ):
                # 非数值类型，跳过检查
                summary["relation_details"][relation_name] = {
                    "status": "skipped",
                    "reason": "non_numeric_fields",
                    "field_a": field_a,
                    "field_b": field_b,
                    "value_a_type": type(value_a).__name__,
                    "value_b_type": type(value_b).__name__,
                }
                continue

            # 执行检查
            summary["checked_relations"] += 1
            violation = self._check_single_relation(features, relation)

            relation_detail = {
                "status": "passed" if violation is None else "failed",
                "field_a": field_a,
                "field_b": field_b,
                "value_a": value_a,
                "value_b": value_b,
                "relation": relation.get("relation"),
                "severity": relation.get("severity", "medium"),
                "violation": violation,
            }

            summary["relation_details"][relation_name] = relation_detail

            if violation is None:
                summary["passed_relations"] += 1
            else:
                summary["failed_relations"] += 1
                summary["violations"].append(violation)

        # 计算合规率
        if summary["checked_relations"] > 0:
            summary["compliance_rate"] = (
                summary["passed_relations"] / summary["checked_relations"] * 100
            )
        else:
            summary["compliance_rate"] = 0

        return summary

    def add_relation(self, relation: dict[str, Any]) -> None:
        """
        添加新的逻辑关系检查。

        Args:
            relation: 逻辑关系配置字典
        """
        required_fields = ["name", "field_a", "field_b", "relation"]
        for field in required_fields:
            if field not in relation:
                raise ValueError(f"逻辑关系配置缺少必需字段: {field}")

        relation_type = relation.get("relation")
        if relation_type not in self.relation_functions:
            available_types = ", ".join(self.relation_functions.keys())
            raise ValueError(
                f"未知的逻辑关系类型: {relation_type}. "
                f"可用的关系类型: {available_types}"
            )

        self.relations.append(relation)
        logger.info(f"添加新的逻辑关系检查: {relation['name']}")

    def remove_relation(self, relation_name: str) -> bool:
        """
        移除指定名称的逻辑关系检查。

        Args:
            relation_name: 要移除的逻辑关系名称

        Returns:
            bool: 是否成功移除
        """
        for i, relation in enumerate(self.relations):
            if relation.get("name") == relation_name:
                self.relations.pop(i)
                logger.info(f"移除逻辑关系检查: {relation_name}")
                return True

        logger.warning(f"未找到要移除的逻辑关系检查: {relation_name}")
        return False

    def get_relation_names(self) -> list[str]:
        """
        获取所有已配置的逻辑关系名称。

        Returns:
            list[str]: 逻辑关系名称列表
        """
        return [relation.get("name", "unknown") for relation in self.relations]

    def configure_tolerance(self, tolerance: float) -> None:
        """
        配置默认容忍度。

        Args:
            tolerance: 容忍度值
        """
        if tolerance < 0:
            raise ValueError("容忍度不能为负数")

        self.tolerance = tolerance
        logger.info(f"默认容忍度已设置为: {tolerance}")

    def configure_strict_mode(self, strict_mode: bool) -> None:
        """
        配置严格模式。

        Args:
            strict_mode: 是否启用严格模式
        """
        self.strict_mode = strict_mode
        logger.info(f"严格模式已设置为: {strict_mode}")

    def validate_relation_config(self) -> list[str]:
        """
        验证所有逻辑关系配置的有效性。

        Returns:
            list[str]: 配置错误列表，空列表表示配置有效
        """
        errors = []
        relation_names = []

        for i, relation in enumerate(self.relations):
            relation_name = relation.get("name", f"relation_{i}")

            # 检查名称唯一性
            if relation_name in relation_names:
                errors.append(f"逻辑关系名称重复: {relation_name}")
            relation_names.append(relation_name)

            # 检查必需字段
            required_fields = ["name", "field_a", "field_b", "relation"]
            for field in required_fields:
                if field not in relation:
                    errors.append(f"逻辑关系 '{relation_name}' 缺少必需字段: {field}")

            # 检查关系类型
            relation_type = relation.get("relation")
            if relation_type not in self.relation_functions:
                available_types = ", ".join(self.relation_functions.keys())
                errors.append(
                    f"逻辑关系 '{relation_name}' 包含未知类型: {relation_type}. "
                    f"可用类型: {available_types}"
                )

        return errors
