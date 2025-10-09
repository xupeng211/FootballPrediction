"""

"""











    """


    """

        """初始化上下文"""

        """初始化内置函数"""



        """检查值是否在范围内"""

        """检查值是否在元组范围内"""

        """检查是否为空"""

        """检查容器是否包含项目"""

        """检查文本是否匹配模式"""

        """检查上升趋势"""

        """检查下降趋势"""

        """更新上下文变量"""

        """获取安全的执行上下文"""


    """


    """

        """初始化规则引擎"""


        """初始化默认规则"""



        """

        """

        """

        """

        """

        """

        """

        """

        """

        """

        """


        """









        """


        """






        """


        """





        """

        """



        """

        """




        """


        """




        """


        """

        """

        """

        """

        """

        """


        """

        """

        """

        """

        """




        """

        """


    from ..models import Alert, AlertLevel, AlertRule, AlertStatus
        from monitoring.alerts.models import Alert, AlertLevel, AlertRule, AlertStatus
        from enum import Enum
        from datetime import datetime
        from typing import Any, Dict, Optional
                from enum import Enum
            import re
            import ast
        import ast
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging

告警规则引擎
Alert Rule Engine
实现告警规则的评估和触发逻辑，从AlertManager中提取规则相关功能。
Extracted from AlertManager to handle rule evaluation and triggering logic.
# 尝试从不同位置导入模型
try:
except ImportError:
    try:
    except ImportError:
        # 创建基本类型
        class AlertLevel(Enum):
            CRITICAL = "critical"
            HIGH = "high"
            MEDIUM = "medium"
            LOW = "low"
        class AlertStatus(Enum):
            ACTIVE = "active"
            RESOLVED = "resolved"
            SUPPRESSED = "suppressed"
            SILENCED = "silenced"
        class Alert:
            def __init__(self, alert_id: str, title: str, message: str, level: AlertLevel, source: str, **kwargs):
                self.alert_id = alert_id
                self.title = title
                self.message = message
                self.level = level
                self.source = source
                self.status = AlertStatus.ACTIVE
                self.created_at = datetime.utcnow()
                self.labels = kwargs.get('labels', {})
            @property
            def type(self):
                class AlertType(Enum):
                    SYSTEM = "system"
                return AlertType.SYSTEM
            @property
            def severity(self):
                return self.level
        class AlertRule:
            def __init__(self, rule_id: str, name: str, condition: str, severity: str = "medium", **kwargs):
                self.rule_id = rule_id
                self.name = name
                self.condition = condition
                self.severity = severity
                self.description = kwargs.get('description', '')
                self.enabled = kwargs.get('enabled', True)
logger = logging.getLogger(__name__)
class RuleEvaluationContext:
    规则评估上下文
    Rule Evaluation Context
    提供规则评估时的上下文信息和函数。
    Provides context information and functions for rule evaluation.
    Attributes:
        variables (Dict[str, Any]): 可用变量 / Available variables
        functions (Dict[str, Callable]): 可用函数 / Available functions
        metrics (Dict[str, Any]): 指标数据 / Metrics data
        history (Dict[str, List]): 历史数据 / Historical data
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Callable] = {}
        self.metrics: Dict[str, Any] = {}
        self.history: Dict[str, List] = {}
        self._init_builtin_functions()
    def _init_builtin_functions(self):
        # 数值比较函数
        self.functions.update({
            "abs": abs,
            "min": min,
            "max": max,
            "len": len,
            "sum": sum,
            "avg": lambda x: sum(x) / len(x) if x else 0,
        })
        # 时间函数
        self.functions.update({
            "now": datetime.utcnow,
            "minutes": lambda x: timedelta(minutes=x),
            "hours": lambda x: timedelta(hours=x),
            "days": lambda x: timedelta(days=x),
        })
        # 条件函数
        self.functions.update({
            "between": self._between,
            "in_range": self._in_range,
            "is_empty": self._is_empty,
            "contains": self._contains,
            "matches": self._matches,
            "trend_up": self._trend_up,
            "trend_down": self._trend_down,
        })
    def _between(self, value, min_val, max_val):
        try:
            return min_val <= value <= max_val
        except TypeError:
            return False
    def _in_range(self, value, range_tuple):
        return value in range_tuple
    def _is_empty(self, value):
        return value is None or (hasattr(value, "__len__") and len(value) == 0)
    def _contains(self, container, item):
        try:
            return item in container
        except TypeError:
            return False
    def _matches(self, text, pattern):
        try:
            return re.search(pattern, str(text)) is not None
        except re.error:
            return False
    def _trend_up(self, values, threshold=0.1):
        if len(values) < 2:
            return False
        try:
            return (values[-1] - values[0]) / abs(values[0]) > threshold
        except (TypeError, ZeroDivisionError):
            return False
    def _trend_down(self, values, threshold=-0.1):
        if len(values) < 2:
            return False
        try:
            return (values[-1] - values[0]) / abs(values[0]) < threshold
        except (TypeError, ZeroDivisionError):
            return False
    def update_variables(self, variables: Dict[str, Any]):
        self.variables.update(variables)
    def get_safe_eval_context(self) -> Dict[str, Any]:
        context = {}
        context.update(self.variables)
        context.update(self.functions)
        return context
class AlertRuleEngine:
    告警规则引擎
    Alert Rule Engine
    负责规则的注册、评估和触发。
    Responsible for rule registration, evaluation, and triggering.
    Attributes:
        rules (Dict[str, AlertRule]): 注册的规则 / Registered rules
        context (RuleEvaluationContext): 评估上下文 / Evaluation context
        rule_history (Dict[str, List]): 规则执行历史 / Rule execution history
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.context = RuleEvaluationContext()
        self.rule_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_size = 1000
        self.logger = logging.getLogger(__name__)
        # 初始化默认规则
        self._init_default_rules()
    def _init_default_rules(self):
        # 系统监控规则
        self.register_rule(AlertRule(
            rule_id="system_cpu_high",
            name="高CPU使用率",
            description="CPU使用率超过80%",
            condition="cpu_usage > 80",
            severity="high",
            enabled=True
        ))
        self.register_rule(AlertRule(
            rule_id="system_memory_high",
            name="高内存使用率",
            description="内存使用率超过90%",
            condition="memory_usage > 90",
            severity="high",
            enabled=True
        ))
        self.register_rule(AlertRule(
            rule_id="disk_space_low",
            name="磁盘空间不足",
            description="磁盘使用率超过95%",
            condition="disk_usage > 95",
            severity="critical",
            enabled=True
        ))
    def register_rule(self, rule: AlertRule):
        注册规则
        Register Rule
        Args:
            rule: 告警规则 / Alert rule
        self.rules[rule.rule_id] = rule
        self.rule_history[rule.rule_id] = []
        self.logger.info(f"Registered rule: {rule.rule_id}")
    def unregister_rule(self, rule_id: str):
        注销规则
        Unregister Rule
        Args:
            rule_id: 规则ID / Rule ID
        if rule_id in self.rules:
            del self.rules[rule_id]
            if rule_id in self.rule_history:
                del self.rule_history[rule_id]
            self.logger.info(f"Unregistered rule: {rule_id}")
    def enable_rule(self, rule_id: str):
        启用规则
        Enable Rule
        Args:
            rule_id: 规则ID / Rule ID
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            self.logger.info(f"Enabled rule: {rule_id}")
    def disable_rule(self, rule_id: str):
        禁用规则
        Disable Rule
        Args:
            rule_id: 规则ID / Rule ID
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            self.logger.info(f"Disabled rule: {rule_id}")
    def update_context_variables(self, variables: Dict[str, Any]):
        更新上下文变量
        Update Context Variables
        Args:
            variables: 变量字典 / Variables dictionary
        self.context.update_variables(variables)
    async def evaluate_rule(self, rule_id: str) -> bool:
        评估单个规则
        Evaluate Single Rule
        Args:
            rule_id: 规则ID / Rule ID
        Returns:
            bool: 是否触发 / Whether triggered
        rule = self.rules.get(rule_id)
        if not rule:
            self.logger.warning(f"Rule not found: {rule_id}")
            return False
        if not rule.enabled:
            return False
        try:
            # 获取安全上下文
            safe_context = self.context.get_safe_eval_context()
            # 评估条件
            condition_result = self._evaluate_condition(rule.condition, safe_context)
            # 记录评估历史
            evaluation_record = {
                "timestamp": datetime.utcnow(),
                "condition": rule.condition,
                "result": condition_result,
                "context_snapshot": dict(self.context.variables)
            }
            self._record_evaluation(rule_id, evaluation_record)
            if condition_result:
                self.logger.info(f"Rule triggered: {rule_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error evaluating rule {rule_id}: {e}")
            return False
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        安全地评估条件表达式
        Safely Evaluate Condition Expression
        Args:
            condition: 条件表达式 / Condition expression
            context: 上下文变量 / Context variables
        Returns:
            bool: 评估结果 / Evaluation result
        try:
            # 使用ast进行安全的表达式解析
            # 解析AST
            tree = ast.parse(condition, mode='eval')
            # 检查AST安全性
            if not self._is_safe_ast(tree):
                raise ValueError("Unsafe expression detected")
            # 编译并执行
            code = compile(tree, '<string>', 'eval')
            result = eval(code, {"__builtins__": {}}, context)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {condition}, error: {e}")
            return False
    def _is_safe_ast(self, node) -> bool:
        检查AST是否安全
        Check if AST is Safe
        Args:
            node: AST节点 / AST node
        Returns:
            bool: 是否安全 / Whether safe
        # 允许的节点类型
        allowed_nodes = {
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare,
            ast.Name, ast.Load, ast.Constant, ast.Num, ast.Str,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
            ast.And, ast.Or, ast.Not, ast.BoolOp, ast.Call,
            ast.List, ast.Tuple, ast.Dict, ast.Subscript, ast.Index,
            ast.Attribute
        }
        # 检查节点类型
        if type(node) not in allowed_nodes:
            return False
        # 递归检查子节点
        for child in ast.iter_child_nodes(node):
            if not self._is_safe_ast(child):
                return False
        return True
    def _record_evaluation(self, rule_id: str, record: Dict[str, Any]):
        记录规则评估历史
        Record Rule Evaluation History
        Args:
            rule_id: 规则ID / Rule ID
            record: 评估记录 / Evaluation record
        if rule_id not in self.rule_history:
            self.rule_history[rule_id] = []
        self.rule_history[rule_id].append(record)
        # 限制历史记录大小
        if len(self.rule_history[rule_id]) > self.max_history_size:
            self.rule_history[rule_id] = self.rule_history[rule_id][-self.max_history_size:]
    async def evaluate_all_rules(self) -> Dict[str, bool]:
        评估所有规则
        Evaluate All Rules
        Returns:
            Dict[str, bool]: 规则ID到触发结果的映射 / Rule ID to trigger result mapping
        results = {}
        tasks = []
        # 创建评估任务
        for rule_id in self.rules:
            task = asyncio.create_task(self.evaluate_rule(rule_id))
            tasks.append((rule_id, task))
        # 等待所有任务完成
        for rule_id, task in tasks:
            try:
                result = await task
                results[rule_id] = result
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule_id}: {e}")
                results[rule_id] = False
        return results
    async def trigger_alert(self, rule_id: str) -> Optional[Alert]:
        触发规则告警
        Trigger Rule Alert
        Args:
            rule_id: 规则ID / Rule ID
        Returns:
            Optional[Alert]: 创建的告警 / Created alert
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        # 生成告警ID
        alert_id = f"rule_{int(datetime.utcnow().timestamp())}_{hash(rule_id) % 10000}"
        # 创建告警
        alert = Alert(
            alert_id=alert_id,
            title=f"Rule Alert: {rule.name}",
            message=rule.description or f"Rule {rule.rule_id} was triggered",
            level=AlertLevel[rule.severity.upper()],
            source="rule_engine",
            labels={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "triggered_at": datetime.utcnow().isoformat()
            }
        )
        self.logger.info(f"Rule alert triggered: {alert_id} for rule {rule_id}")
        return alert
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        获取规则
        Get Rule
        Args:
            rule_id: 规则ID / Rule ID
        Returns:
            Optional[AlertRule]: 告警规则 / Alert rule
        return self.rules.get(rule_id)
    def get_all_rules(self) -> List[AlertRule]:
        获取所有规则
        Get All Rules
        Returns:
            List[AlertRule]: 规则列表 / List of rules
        return list(self.rules.values())
    def get_enabled_rules(self) -> List[AlertRule]:
        获取启用的规则
        Get Enabled Rules
        Returns:
            List[AlertRule]: 启用的规则列表 / List of enabled rules
        return [rule for rule in self.rules.values() if rule.enabled]
    def get_rule_history(self, rule_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        获取规则评估历史
        Get Rule Evaluation History
        Args:
            rule_id: 规则ID / Rule ID
            limit: 限制数量 / Limit
        Returns:
            List[Dict[str, Any]]: 历史记录 / History records
        history = self.rule_history.get(rule_id, [])
        return history[-limit:] if history else []
    def clear_history(self, rule_id: Optional[str] = None):
        清理规则历史
        Clear Rule History
        Args:
            rule_id: 规则ID，如果为None则清理所有 / Rule ID, None for all
        if rule_id:
            if rule_id in self.rule_history:
                self.rule_history[rule_id] = []
                self.logger.info(f"Cleared history for rule: {rule_id}")
        else:
            self.rule_history.clear()
            self.logger.info("Cleared all rule history")
    def get_statistics(self) -> Dict[str, Any]:
        获取规则引擎统计信息
        Get Rule Engine Statistics
        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        total_rules = len(self.rules)
        enabled_rules = len(self.get_enabled_rules())
        # 统计最近评估结果
        recent_evaluations = 0
        recent_triggers = 0
        for rule_id, history in self.rule_history.items():
            recent_history = history[-10:]  # 最近10次评估
            recent_evaluations += len(recent_history)
            recent_triggers += sum(1 for record in recent_history if record["result"])
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "recent_evaluations": recent_evaluations,
            "recent_triggers": recent_triggers,
            "trigger_rate": recent_triggers / recent_evaluations if recent_evaluations > 0 else 0,
            "rules_with_history": len(self.rule_history),
            "context_variables": len(self.context.variables),
            "context_functions": len(self.context.functions),
        }
    def get_all_statistics(self) -> Dict[str, Any]:
        获取所有统计信息（向后兼容）
        Get All Statistics (Backward Compatible)
        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        return self.get_statistics()