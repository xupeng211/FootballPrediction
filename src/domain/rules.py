"""
业务规则模块

定义和验证领域模型的业务规则。
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from .match import Match, MatchStatus, MatchResult
from .team import Team
from .prediction import Prediction, PredictionType, PredictionStatus
from .league import League, LeagueStatus
from .odds import Odds, MarketType


class RuleType(Enum):
    """规则类型枚举"""

    VALIDATION = "validation"  # 验证规则
    BUSINESS = "business"  # 业务规则
    CONSTRAINT = "constraint"  # 约束规则
    POLICY = "policy"  # 策略规则


class RuleSeverity(Enum):
    """规则严重级别"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


@dataclass
class RuleViolation:
    """规则违规信息"""

    rule_name: str
    rule_type: RuleType
    severity: RuleSeverity
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    expected: Optional[Any] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    violations: List[RuleViolation]
    score: float = 0.0  # 0-100的质量分数

    @property
    def errors(self) -> List[RuleViolation]:
        """获取所有错误"""
        return [
            v
            for v in self.violations
            if v.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL]
        ]

    @property
    def warnings(self) -> List[RuleViolation]:
        """获取所有警告"""
        return [v for v in self.violations if v.severity == RuleSeverity.WARNING]

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0


class BusinessRule:
    """业务规则基类"""

    def __init__(
        self, name: str, description: str, rule_type: RuleType = RuleType.BUSINESS
    ):
        self.name = name
        self.description = description
        self.rule_type = rule_type
        self.is_active = True

    def validate(self, target: Any) -> ValidationResult:
        """验证目标对象"""
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


class MatchRule(BusinessRule):
    """比赛相关规则"""

    def __init__(self, name: str, description: str):
        super().__init__(name, description, RuleType.VALIDATION)


class TeamRule(BusinessRule):
    """球队相关规则"""

    def __init__(self, name: str, description: str):
        super().__init__(name, description, RuleType.VALIDATION)


class PredictionRule(BusinessRule):
    """预测相关规则"""

    def __init__(self, name: str, description: str):
        super().__init__(name, description, RuleType.VALIDATION)


class OddsRule(BusinessRule):
    """赔率相关规则"""

    def __init__(self, name: str, description: str):
        super().__init__(name, description, RuleType.VALIDATION)


# ==================== 具体规则实现 ====================


class MatchStartTimeRule(MatchRule):
    """比赛开始时间规则"""

    def __init__(self):
        super().__init__("match_start_time_rule", "比赛时间不能是过去时")

    def validate(self, match: Match) -> ValidationResult:
        violations = []

        if match.match_time and match.match_time < datetime.now():
            if match.status == MatchStatus.SCHEDULED:
                violations.append(
                    RuleViolation(
                        rule_name=self.name,
                        rule_type=self.rule_type,
                        severity=RuleSeverity.ERROR,
                        message="过去的比赛不能是SCHEDULED状态",
                        field="match_time",
                        value=match.match_time,
                        expected="未来时间",
                        suggestion="将状态改为FINISHED或更新比赛时间",
                    )
                )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            score=100 if not violations else 50,
        )


class MatchTeamRule(MatchRule):
    """比赛球队规则"""

    def __init__(self):
        super().__init__("match_team_rule", "比赛必须有主客队")

    def validate(self, match: Match) -> ValidationResult:
        violations = []

        if not match.home_team:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.ERROR,
                    message="缺少主队信息",
                    field="home_team",
                    suggestion="添加主队信息",
                )
            )

        if not match.away_team:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.ERROR,
                    message="缺少客队信息",
                    field="away_team",
                    suggestion="添加客队信息",
                )
            )

        if (
            match.home_team
            and match.away_team
            and match.home_team.id == match.away_team.id
        ):
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.CRITICAL,
                    message="主队和客队不能相同",
                    field="teams",
                    value=f"主队:{match.home_team.id}, 客队:{match.away_team.id}",
                    suggestion="选择不同的球队",
                )
            )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            score=100 if not violations else 30,
        )


class PredictionSettlementRule(PredictionRule):
    """预测结算规则"""

    def __init__(self):
        super().__init__("prediction_settlement_rule", "预测只能结算一次")

    def validate(self, prediction: Prediction) -> ValidationResult:
        violations = []

        if prediction.status != PredictionStatus.PENDING:
            if prediction.status == PredictionStatus.CORRECT:
                status_text = "已正确"
            elif prediction.status == PredictionStatus.INCORRECT:
                status_text = "已错误"
            elif prediction.status == PredictionStatus.VOID:
                status_text = "已无效"
            else:
                status_text = "未知状态"

            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.WARNING,
                    message=f"预测已经结算过（{status_text}）",
                    field="status",
                    value=prediction.status.value,
                    suggestion="避免重复结算",
                )
            )

        return ValidationResult(
            is_valid=len([v for v in violations if v.severity == RuleSeverity.ERROR])
            == 0,
            violations=violations,
            score=100 if not violations else 60,
        )


class PredictionConfidenceRule(PredictionRule):
    """预测置信度规则"""

    def __init__(self):
        super().__init__("prediction_confidence_rule", "预测置信度必须在合理范围内")

    def validate(self, prediction: Prediction) -> ValidationResult:
        violations = []

        if prediction.confidence < 0.0 or prediction.confidence > 1.0:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.ERROR,
                    message="置信度必须在0-1之间",
                    field="confidence",
                    value=prediction.confidence,
                    expected="0.0 - 1.0",
                    suggestion="调整置信度到有效范围",
                )
            )
        elif prediction.confidence < 0.5:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.WARNING,
                    message="置信度较低，可能影响预测质量",
                    field="confidence",
                    value=prediction.confidence,
                    suggestion="检查预测依据，提高置信度",
                )
            )

        return ValidationResult(
            is_valid=len([v for v in violations if v.severity == RuleSeverity.ERROR])
            == 0,
            violations=violations,
            score=100
            if not violations
            else (
                80
                if not any(v.severity == RuleSeverity.ERROR for v in violations)
                else 40
            ),
        )


class OddsValueRule(OddsRule):
    """赔率值规则"""

    def __init__(self):
        super().__init__("odds_value_rule", "赔率必须大于1.0")

    def validate(self, odds: Odds) -> ValidationResult:
        violations = []

        # 检查各种赔率
        odds_fields = [
            ("home_odds", odds.home_odds),
            ("draw_odds", odds.draw_odds),
            ("away_odds", odds.away_odds),
            ("over_odds", odds.over_odds),
            ("under_odds", odds.under_odds),
        ]

        for field_name, odds_value in odds_fields:
            if odds_value is not None and odds_value <= 1.0:
                violations.append(
                    RuleViolation(
                        rule_name=self.name,
                        rule_type=self.rule_type,
                        severity=RuleSeverity.ERROR,
                        message=f"{field_name} 必须大于 1.0",
                        field=field_name,
                        value=odds_value,
                        expected="> 1.0",
                        suggestion="更新赔率值",
                    )
                )

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            score=100 if not violations else 20,
        )


class TeamStrengthRule(TeamRule):
    """球队实力规则"""

    def __init__(self):
        super().__init__("team_strength_rule", "球队实力评分必须在合理范围")

    def validate(self, team: Team) -> ValidationResult:
        violations = []

        strength_score = team.get_strength_score()

        if strength_score < 0 or strength_score > 100:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.ERROR,
                    message="实力评分必须在0-100之间",
                    field="strength_score",
                    value=strength_score,
                    expected="0 - 100",
                    suggestion="检查实力计算逻辑",
                )
            )
        elif strength_score > 90:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.WARNING,
                    message="实力评分异常高",
                    field="strength_score",
                    value=strength_score,
                    suggestion="验证数据准确性",
                )
            )

        return ValidationResult(
            is_valid=len([v for v in violations if v.severity == RuleSeverity.ERROR])
            == 0,
            violations=violations,
            score=100
            if not violations
            else (
                90
                if not any(v.severity == RuleSeverity.ERROR for v in violations)
                else 50
            ),
        )


class LeagueTeamCountRule(BusinessRule):
    """联赛球队数量规则"""

    def __init__(self):
        super().__init__("league_team_count_rule", "联赛球队数量必须在合理范围")

    def validate(self, league: League) -> ValidationResult:
        violations = []

        team_count = len(league.teams)

        if team_count < 4:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.ERROR,
                    message="联赛球队数量过少",
                    field="teams",
                    value=team_count,
                    expected=">= 4",
                    suggestion="添加更多球队到联赛",
                )
            )
        elif team_count > 30:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.WARNING,
                    message="联赛球队数量过多",
                    field="teams",
                    value=team_count,
                    expected="<= 30",
                    suggestion="考虑分组或限制参赛球队",
                )
            )
        elif team_count % 2 != 0:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    severity=RuleSeverity.WARNING,
                    message="联赛球队数量应为偶数",
                    field="teams",
                    value=team_count,
                    expected="偶数",
                    suggestion="添加或删除一支球队",
                )
            )

        return ValidationResult(
            is_valid=len([v for v in violations if v.severity == RuleSeverity.ERROR])
            == 0,
            violations=violations,
            score=100
            if not violations
            else (
                80
                if not any(v.severity == RuleSeverity.ERROR for v in violations)
                else 60
            ),
        )


# ==================== 验证引擎 ====================


class ValidationEngine:
    """验证引擎

    管理和执行所有业务规则。
    """

    def __init__(self):
        self.rules: Dict[str, List[BusinessRule]] = {
            "match": [],
            "team": [],
            "prediction": [],
            "odds": [],
            "league": [],
        }

        # 注册默认规则
        self._register_default_rules()

    def _register_default_rules(self):
        """注册默认规则"""
        # 比赛规则
        self.rules["match"].extend([MatchStartTimeRule(), MatchTeamRule()])

        # 球队规则
        self.rules["team"].extend([TeamStrengthRule()])

        # 预测规则
        self.rules["prediction"].extend(
            [PredictionSettlementRule(), PredictionConfidenceRule()]
        )

        # 赔率规则
        self.rules["odds"].extend([OddsValueRule()])

        # 联赛规则
        self.rules["league"].extend([LeagueTeamCountRule()])

    def register_rule(self, target_type: str, rule: BusinessRule):
        """注册规则"""
        if target_type in self.rules:
            self.rules[target_type].append(rule)

    def unregister_rule(self, target_type: str, rule_name: str):
        """注销规则"""
        if target_type in self.rules:
            self.rules[target_type] = [
                r for r in self.rules[target_type] if r.name != rule_name
            ]

    def validate(
        self, target: Any, target_type: Optional[str] = None
    ) -> ValidationResult:
        """验证目标对象"""
        if target_type is None:
            # 自动推断类型
            target_type = type(target).__name__.lower()
            if target_type == "match":
                target_type = "match"
            elif target_type == "team":
                target_type = "team"
            elif target_type == "prediction":
                target_type = "prediction"
            elif target_type == "odds":
                target_type = "odds"
            elif target_type == "league":
                target_type = "league"
            else:
                target_type = "unknown"

        if target_type not in self.rules:
            return ValidationResult(is_valid=True, violations=[], score=100)

        all_violations = []
        total_score = 0
        rule_count = 0

        for rule in self.rules[target_type]:
            if rule.is_active:
                result = rule.validate(target)
                all_violations.extend(result.violations)
                total_score += result.score
                rule_count += 1

        final_score = total_score / rule_count if rule_count > 0 else 100
        has_errors = any(
            v.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL]
            for v in all_violations
        )

        return ValidationResult(
            is_valid=not has_errors, violations=all_violations, score=final_score
        )

    def validate_batch(self, targets: List[Tuple[Any, str]]) -> List[ValidationResult]:
        """批量验证"""
        results = []
        for target, target_type in targets:
            result = self.validate(target, target_type)
            results.append(result)
        return results

    def get_rules_summary(self) -> Dict[str, Dict[str, int]]:
        """获取规则摘要"""
        summary = {}
        for target_type, rules in self.rules.items():
            summary[target_type] = {
                "total": len(rules),
                "active": sum(1 for r in rules if r.is_active),
                "inactive": sum(1 for r in rules if not r.is_active),
            }
        return summary


# ==================== 单例验证引擎 ====================

_validation_engine = None


def get_validation_engine() -> ValidationEngine:
    """获取全局验证引擎实例"""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()
    return _validation_engine
