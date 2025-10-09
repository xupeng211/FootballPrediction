"""
恢复处理器主类
Recovery Handler Main Class

协调恢复处理的各个组件。
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict

from .alerting import AlertManager
from .classifiers import FailureClassifier
from .models import FailureType, RecoveryStrategy, TaskFailure
from .statistics import RecoveryStatistics
from .strategies import StrategyFactory

logger = logging.getLogger(__name__)


class RecoveryHandler:
    """
    恢复处理器主类

    负责处理任务失败和恢复，提供以下功能：
    - 失败分类和分析
    - 智能重试策略
    - 错误恢复机制
    - 告警通知
    - 失败统计和分析
    """

    def __init__(self):
        """初始化恢复处理器"""
        # 初始化组件
        self.classifier = FailureClassifier()
        self.alert_manager = AlertManager()
        self.statistics = RecoveryStatistics()

        # 初始化恢复配置
        self.recovery_configs = self._init_recovery_configs()

        logger.info("恢复处理器初始化完成")

    def _init_recovery_configs(self) -> Dict[FailureType, Dict[str, Any]]:
        """
        初始化恢复配置

        Returns:
            Dict[FailureType, Dict[str, Any]]: 失败类型对应的恢复配置
        """
        return {
            FailureType.TIMEOUT: {
                "strategy": RecoveryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 3,
                "base_delay": 60,  # 基础延迟（秒）
                "max_delay": 300,  # 最大延迟（秒）
                "backoff_factor": 2.0,
                "alert_threshold": 2,  # 重试几次后发送告警
            },
            FailureType.CONNECTION_ERROR: {
                "strategy": RecoveryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 5,
                "base_delay": 30,
                "max_delay": 600,
                "backoff_factor": 1.5,
                "alert_threshold": 3,
            },
            FailureType.DATA_ERROR: {
                "strategy": RecoveryStrategy.FIXED_DELAY,
                "max_retries": 2,
                "base_delay": 120,
                "alert_threshold": 1,
            },
            FailureType.RESOURCE_ERROR: {
                "strategy": RecoveryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 4,
                "base_delay": 180,
                "max_delay": 900,
                "backoff_factor": 2.0,
                "alert_threshold": 2,
            },
            FailureType.PERMISSION_ERROR: {
                "strategy": RecoveryStrategy.MANUAL_INTERVENTION,
                "max_retries": 0,
                "alert_threshold": 0,
            },
            FailureType.UNKNOWN_ERROR: {
                "strategy": RecoveryStrategy.FIXED_DELAY,
                "max_retries": 2,
                "base_delay": 300,
                "alert_threshold": 1,
            },
        }

    def handle_task_failure(self, task: Any, error_message: str) -> bool:
        """
        处理任务失败

        Args:
            task: 失败的任务对象
            error_message: 错误消息

        Returns:
            bool: 是否成功处理失败
        """
        try:
            # 分析失败类型
            failure_type = self.classifier.classify_failure(error_message)

            # 创建失败记录
            failure = TaskFailure(
                task_id=task.task_id,
                failure_time=datetime.now(),
                failure_type=failure_type,
                error_message=error_message,
                retry_count=getattr(task, "retry_count", 0),
                context={
                    "task_name": getattr(task, "name", "unknown"),
                    "cron_expression": getattr(task, "cron_expression", None),
                    "priority": getattr(task, "priority", "normal"),
                    "timeout": getattr(task, "timeout", None),
                },
            )

            # 添加到统计和历史记录
            self.statistics.add_failure(failure)
            self.statistics.update_failure_pattern(task.task_id, failure_type)

            # 执行恢复策略
            recovery_success = self._execute_recovery_strategy(task, failure)

            # 记录恢复结果
            self.statistics.record_recovery(recovery_success)

            # 检查并发送告警
            config = self.recovery_configs[failure_type]
            self.alert_manager.check_retry_threshold(task, failure, config)
            self.alert_manager.check_failure_patterns(
                task.task_id, self.statistics.failure_patterns
            )

            # 如果是人工干预策略，发送额外告警
            if config["strategy"] == RecoveryStrategy.MANUAL_INTERVENTION:
                self.alert_manager.request_manual_intervention(task, failure)

            logger.info(
                f"任务失败处理完成: {task.task_id}, 恢复{'成功' if recovery_success else '失败'}"
            )
            return recovery_success

        except Exception as e:
            logger.error(f"处理任务失败时发生异常: {task.task_id} - {e}")
            return False

    def _execute_recovery_strategy(
        self, task: Any, failure: TaskFailure
    ) -> bool:
        """
        执行恢复策略

        Args:
            task: 任务对象
            failure: 失败记录

        Returns:
            bool: 恢复是否成功
        """
        config = self.recovery_configs[failure.failure_type]
        strategy_type = config["strategy"]

        logger.info(f"执行恢复策略: {task.task_id}, 策略: {strategy_type.value}")

        try:
            # 获取策略实例
            strategy = StrategyFactory.get_strategy(strategy_type)

            # 执行策略
            success = strategy.execute(task, failure, config)

            # 记录恢复尝试
            failure.add_recovery_attempt(
                strategy_type,
                success,
                datetime.now(),
                f"策略执行{'成功' if success else '失败'}",
            )

            return success

        except Exception as e:
            logger.error(f"执行恢复策略失败: {task.task_id} - {e}")
            failure.add_recovery_attempt(
                strategy_type,
                False,
                datetime.now(),
                f"策略执行异常: {str(e)}",
            )
            return False

    def register_alert_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        注册告警处理器

        Args:
            handler: 告警处理函数
        """
        self.alert_manager.register_handler(handler)
        logger.info(f"告警处理器已注册: {handler.__name__}")

    def get_failure_statistics(self) -> Dict[str, Any]:
        """
        获取失败统计信息

        Returns:
            Dict[str, Any]: 失败统计信息
        """
        return self.statistics.get_statistics()

    def get_recent_failures(self, limit: int = 20) -> list[Dict[str, Any]]:
        """
        获取最近的失败记录

        Args:
            limit: 返回记录数量限制

        Returns:
            List[Dict[str, Any]]: 最近的失败记录
        """
        return self.statistics.get_recent_failures(limit)

    def get_failure_trend(
        self, hours: int = 24, interval_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        获取失败趋势

        Args:
            hours: 统计时间范围（小时）
            interval_minutes: 时间间隔（分钟）

        Returns:
            Dict[str, Any]: 趋势数据
        """
        return self.statistics.get_failure_trend(hours, interval_minutes)

    def get_alert_statistics(self) -> Dict[str, Any]:
        """
        获取告警统计信息

        Returns:
            Dict[str, Any]: 告警统计信息
        """
        return self.alert_manager.get_alert_statistics()

    def clear_old_failures(self, days_to_keep: int = 30) -> int:
        """
        清理旧的失败记录

        Args:
            days_to_keep: 保留天数

        Returns:
            int: 清理的记录数量
        """
        return self.statistics.clear_old_failures(days_to_keep)

    def add_custom_keywords(
        self, failure_type: FailureType, keywords: list[str]
    ) -> None:
        """
        添加自定义关键词到分类器

        Args:
            failure_type: 失败类型
            keywords: 关键词列表
        """
        self.classifier.add_custom_keywords(failure_type, keywords)

    def update_recovery_config(
        self, failure_type: FailureType, config: Dict[str, Any]
    ) -> None:
        """
        更新恢复配置

        Args:
            failure_type: 失败类型
            config: 新的配置
        """
        # 验证配置
        required_keys = ["strategy", "max_retries"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置缺少必需的键: {key}")

        # 更新配置
        self.recovery_configs[failure_type] = config
        logger.info(f"已更新 {failure_type.value} 的恢复配置")

    def add_alert_suppression_rule(
        self,
        name: str,
        pattern: str,
        duration_minutes: int = 60,
        max_alerts: int = 1,
    ) -> None:
        """
        添加告警抑制规则

        Args:
            name: 规则名称
            pattern: 匹配模式
            duration_minutes: 抑制持续时间（分钟）
            max_alerts: 最大告警次数
        """
        self.alert_manager.add_suppression_rule(
            name, pattern, duration_minutes, max_alerts
        )