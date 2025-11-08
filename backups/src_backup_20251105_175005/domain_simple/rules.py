"""
业务规则和验证引擎
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any


class ValidationResult:
    """类文档字符串"""

    pass  # 添加pass语句
    """验证结果"""

    def __init__(self, is_valid: bool = True, message: str = ""):
        """函数文档字符串"""
        # 添加pass语句
        self.is_valid = is_valid
        self.message = message
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.timestamp = datetime.now()

    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
        }


class Rule(ABC):
    """规则抽象基类"""

    def __init__(self, name: str, description: str = ""):
        """函数文档字符串"""
        # 添加pass语句
        self.name = name
        self.description = description
        self.enabled = True

    @abstractmethod
    def validate(self, obj: Any) -> ValidationResult:
        """验证对象"""


class BusinessRule(Rule):
    """业务规则"""

    def __init__(
        self,
        name: str,
        condition: Callable[[Any], bool],
        error_message: str,
        description: str = "",
    ):
        super().__init__(name, description)
        self.condition = condition
        self.error_message = error_message

    def validate(self, obj: Any) -> ValidationResult:
        """验证业务规则"""
        result = ValidationResult()

        if not self.enabled:
            result.add_warning(f"Rule {self.name} is disabled")
            return result

        try:
            if not self.condition(obj):
                result.add_error(self.error_message)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            result.add_error(f"Error validating rule {self.name}: {str(e)}")

        return result


class ValidationEngine:
    """类文档字符串"""

    pass  # 添加pass语句
    """验证引擎"""

    def __init__(self):
        """函数文档字符串"""
        # 添加pass语句
        self._rules: dict[str, list[Rule]] = {}
        self._global_rules: list[Rule] = []

    def add_rule(self, entity_type: str, rule: Rule) -> None:
        """为特定实体类型添加规则"""
        if entity_type not in self._rules:
            self._rules[entity_type] = []
        self._rules[entity_type].append(rule)

    def add_global_rule(self, rule: Rule) -> None:
        """添加全局规则（适用于所有实体）"""
        self._global_rules.append(rule)

    def remove_rule(self, entity_type: str, rule_name: str) -> bool:
        """移除规则"""
        if entity_type in self._rules:
            self._rules[entity_type] = [
                rule for rule in self._rules[entity_type] if rule.name != rule_name
            ]
            return True
        return False

    def get_rules(self, entity_type: str | None = None) -> list[Rule]:
        """获取规则"""
        rules = self._global_rules.copy()

        if entity_type and entity_type in self._rules:
            rules.extend(self._rules[entity_type])

        return rules

    def validate(self, obj: Any, entity_type: str | None = None) -> ValidationResult:
        """验证对象"""
        result = ValidationResult()

        # 获取相关规则
        rules = self.get_rules(entity_type)

        # 应用所有规则
        for rule in rules:
            rule_result = rule.validate(obj)

            # 合并结果
            result.errors.extend(rule_result.errors)
            result.warnings.extend(rule_result.warnings)

            # 如果有错误,标记为无效
            if rule_result.has_errors():
                result.is_valid = False

        # 设置总体消息
        if result.has_errors():
            result.message = f"Validation failed with {len(result.errors)} error(s)"
        elif result.has_warnings():
            result.message = f"Validation passed with {len(result.warnings)} warning(s)"
        else:
            result.message = "Validation passed successfully"

        return result

    def validate_batch(
        self, objects: list[Any], entity_type: str | None = None
    ) -> list[ValidationResult]:
        """批量验证"""
        results = []

        for obj in objects:
            result = self.validate(obj, entity_type)
            results.append(result)

        return results

    def enable_rule(self, rule_name: str) -> None:
        """启用规则"""
        for rules in self._rules.values():
            for rule in rules:
                if rule.name == rule_name:
                    rule.enabled = True

        for rule in self._global_rules:
            if rule.name == rule_name:
                rule.enabled = True

    def disable_rule(self, rule_name: str) -> None:
        """禁用规则"""
        for rules in self._rules.values():
            for rule in rules:
                if rule.name == rule_name:
                    rule.enabled = False

        for rule in self._global_rules:
            if rule.name == rule_name:
                rule.enabled = False

    def clear_rules(self, entity_type: str | None = None) -> None:
        """清除规则"""
        if entity_type:
            self._rules[entity_type] = []
        else:
            self._rules.clear()
            self._global_rules.clear()


class BusinessRules:
    """类文档字符串"""

    pass  # 添加pass语句
    """预定义的业务规则集合"""

    @staticmethod
    def create_match_rules() -> list[Rule]:
        """创建比赛相关的业务规则"""
        rules = []

        # 规则1:比赛必须有两支不同的球队
        rules.append(
            BusinessRule(
                name="different_teams",
                condition=lambda m: hasattr(m, "home_team_id")
                and hasattr(m, "away_team_id")
                and m.home_team_id != m.away_team_id,
                error_message="Home team and away team must be different",
                description="Ensures a match has two different teams",
            )
        )

        # 规则2:比赛时间不能是过去
        rules.append(
            BusinessRule(
                name="future_match_time",
                condition=lambda m: hasattr(m, "scheduled_time")
                and (m.scheduled_time is None or m.scheduled_time > datetime.now()),
                error_message="Match time cannot be in the past",
                description="Ensures matches are scheduled for future times",
            )
        )

        # 规则3:比分不能为负数
        rules.append(
            BusinessRule(
                name="non_negative_scores",
                condition=lambda m: (not hasattr(m, "home_score") or m.home_score >= 0)
                and (not hasattr(m, "away_score") or m.away_score >= 0),
                error_message="Scores cannot be negative",
                description="Ensures scores are non-negative",
            )
        )

        return rules

    @staticmethod
    def create_prediction_rules() -> list[Rule]:
        """创建预测相关的业务规则"""
        rules = []

        # 规则1:置信度必须在0-1之间
        rules.append(
            BusinessRule(
                name="valid_confidence",
                condition=lambda p: hasattr(p, "confidence") and 0 <= p.confidence <= 1,
                error_message="Confidence must be between 0 and 1",
                description="Ensures confidence is valid",
            )
        )

        # 规则2:投注金额必须为正数
        rules.append(
            BusinessRule(
                name="positive_stake",
                condition=lambda p: hasattr(p, "stake") and p.stake > 0,
                error_message="Stake must be positive",
                description="Ensures stake amount is positive",
            )
        )

        # 规则3:赔率必须大于1
        rules.append(
            BusinessRule(
                name="valid_odds",
                condition=lambda p: p.odds is None or p.odds > 1,
                error_message="Odds must be greater than 1",
                description="Ensures odds are valid",
            )
        )

        return rules

    @staticmethod
    def create_team_rules() -> list[Rule]:
        """创建球队相关的业务规则"""
        rules = []

        # 规则1:球队名称不能为空
        rules.append(
            BusinessRule(
                name="non_empty_name",
                condition=lambda t: hasattr(t, "name")
                and t.name
                and len(t.name.strip()) > 0,
                error_message="Team name cannot be empty",
                description="Ensures team has a valid name",
            )
        )

        # 规则2:成立年份不能在未来
        rules.append(
            BusinessRule(
                name="valid_founding_year",
                condition=lambda t: t.founded_year is None
                or t.founded_year <= datetime.now().year,
                error_message="Founding year cannot be in the future",
                description="Ensures founding year is valid",
            )
        )

        # 规则3:实力评分必须在0-100之间
        rules.append(
            BusinessRule(
                name="valid_strength_score",
                condition=lambda t: 0 <= t.strength_score <= 100,
                error_message="Strength score must be between 0 and 100",
                description="Ensures strength score is valid",
            )
        )

        return rules


# 全局验证引擎实例
_validation_engine = None


def get_validation_engine() -> ValidationEngine:
    """获取全局验证引擎实例"""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()

        # 添加预定义规则
        for rule in BusinessRules.create_match_rules():
            _validation_engine.add_rule("match", rule)

        for rule in BusinessRules.create_prediction_rules():
            _validation_engine.add_rule("prediction", rule)

        for rule in BusinessRules.create_team_rules():
            _validation_engine.add_rule("team", rule)

    return _validation_engine
