"""
        from ..models import AlertChannel

告警规则引擎

管理告警规则的创建、评估和执行。
"""



logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """告警规则引擎"""

    def __init__(self):
        """初始化规则引擎"""
        self.rules: Dict[str, AlertRule] = {}
        self.logger = logging.getLogger(f"alerts.{self.__class__.__name__}")

        # 初始化默认规则
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """初始化默认告警规则"""

        default_rules = [
            AlertRule(
                rule_id="data_quality_critical",
                name="数据质量严重告警",
                condition="data_quality_score < 0.5",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=300,
            ),
            AlertRule(
                rule_id="data_quality_warning",
                name="数据质量警告",
                condition="0.5 <= data_quality_score < 0.8",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=600,
            ),
            AlertRule(
                rule_id="data_freshness",
                name="数据新鲜度告警",
                condition="data_freshness_hours > 24",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG],
                throttle_seconds=1800,
            ),
            AlertRule(
                rule_id="anomaly_critical",
                name="数据异常严重告警",
                condition="anomaly_score > 0.2",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=300,
            ),
            AlertRule(
                rule_id="anomaly_warning",
                name="数据异常警告",
                condition="0.1 < anomaly_score <= 0.2",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=600,
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: AlertRule) -> None:
        """
        添加告警规则

        Args:
            rule: 告警规则
        """
        self.rules[rule.rule_id] = rule
        self.logger.info(f"添加告警规则: {rule.name} ({rule.rule_id})")

    def remove_rule(self, rule_id: str) -> bool:
        """
        删除告警规则

        Args:
            rule_id: 规则ID

        Returns:
            是否删除成功
        """
        if rule_id in self.rules:
            rule = self.rules.pop(rule_id)
            self.logger.info(f"删除告警规则: {rule.name} ({rule_id})")
            return True
        else:
            self.logger.warning(f"未找到告警规则: {rule_id}")
            return False

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        获取告警规则

        Args:
            rule_id: 规则ID

        Returns:
            告警规则或None
        """
        return self.rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """
        列出所有规则

        Args:
            enabled_only: 是否只列出启用的规则

        Returns:
            规则列表
        """
        rules = list(self.rules.values())
        if enabled_only:
            rules = [rule for rule in rules if rule.enabled]
        return rules

    def evaluate_rule(
        self,
        rule_id: str,
        context: Dict,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """
        评估规则是否应该触发

        Args:
            rule_id: 规则ID
            context: 评估上下文
            current_time: 当前时间

        Returns:
            是否应该触发
        """
        rule = self.get_rule(rule_id)
        if not rule or not rule.enabled:
            return False

        # 检查限流
        current_time = current_time or datetime.now()
        if rule.should_throttle(current_time):
            return False

        # 评估条件（简化实现）
        # 实际应用中应该使用更复杂的表达式解析器
        if self._evaluate_condition(rule.condition, context):
            rule.update_last_fired(current_time)
            return True

        return False

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        评估条件表达式

        Args:
            condition: 条件表达式
            context: 上下文变量

        Returns:
            评估结果
        """
        try:
            # 这是一个简化的实现
            # 实际应用中应该使用安全的表达式解析器
            # 例如: eval(condition, {"__builtins__": {}}, context)

            # 处理常见的数据质量条件
            if "data_quality_score" in condition:
                score = context.get("data_quality_score", 1.0)
                if "< 0.5" in condition:
                    return score < 0.5
                elif "< 0.8" in condition:
                    return score < 0.8

            if "data_freshness_hours" in condition:
                hours = context.get("data_freshness_hours", 0)
                return hours > 24

            if "anomaly_score" in condition:
                score = context.get("anomaly_score", 0)
                if "> 0.2" in condition:
                    return score > 0.2
                elif "> 0.1" in condition:
                    return score > 0.1

            return False

        except Exception as e:
            self.logger.error(f"评估条件失败: {condition}, 错误: {e}")
            return False

    def enable_rule(self, rule_id: str) -> bool:
        """
        启用规则

        Args:
            rule_id: 规则ID

        Returns:
            是否成功
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            self.logger.info(f"启用告警规则: {rule.name}")
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """
        禁用规则

        Args:
            rule_id: 规则ID

        Returns:
            是否成功
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            self.logger.info(f"禁用告警规则: {rule.name}")
            return True


        return False