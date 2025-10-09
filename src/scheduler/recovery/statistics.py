"""
统计分析
Statistics

负责收集和分析恢复相关的统计数据。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .models import FailureType, TaskFailure

logger = logging.getLogger(__name__)


class RecoveryStatistics:
    """恢复统计器"""

    def __init__(self):
        """初始化统计器"""
        self.failure_history: List[TaskFailure] = []
        self.failure_patterns: Dict[str, List[FailureType]] = {}

        # 统计计数器
        self.total_failures = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0

    def add_failure(self, failure: TaskFailure) -> None:
        """
        添加失败记录

        Args:
            failure: 失败记录
        """
        self.failure_history.append(failure)
        self.total_failures += 1

    def record_recovery(self, success: bool) -> None:
        """
        记录恢复结果

        Args:
            success: 是否成功
        """
        if success:
            self.successful_recoveries += 1
        else:
            self.failed_recoveries += 1

    def update_failure_pattern(
        self, task_id: str, failure_type: FailureType
    ) -> None:
        """
        更新失败模式

        Args:
            task_id: 任务ID
            failure_type: 失败类型
        """
        if task_id not in self.failure_patterns:
            self.failure_patterns[task_id] = []

        self.failure_patterns[task_id].append(failure_type)

        # 保留最近10次失败记录
        if len(self.failure_patterns[task_id]) > 10:
            self.failure_patterns[task_id] = self.failure_patterns[task_id][-10:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        # 按失败类型统计
        failure_by_type = self._group_by_type()

        # 按任务统计
        failure_by_task = self._group_by_task()

        # 最近24小时统计
        recent_failures = self._get_recent_failures(hours=24)

        # 最近7天统计
        weekly_failures = self._get_recent_failures(hours=168)

        # 计算恢复率
        recovery_rate = (
            self.successful_recoveries / max(self.total_failures, 1) * 100
        )

        # 失败模式分析
        pattern_analysis = self._analyze_patterns()

        return {
            # 基本统计
            "total_failures": self.total_failures,
            "successful_recoveries": self.successful_recoveries,
            "failed_recoveries": self.failed_recoveries,
            "recovery_success_rate": round(recovery_rate, 2),

            # 分布统计
            "failure_by_type": failure_by_type,
            "failure_by_task": failure_by_task,
            "failure_patterns": {
                task_id: [ft.value for ft in failures]
                for task_id, failures in self.failure_patterns.items()
            },

            # 时间统计
            "recent_24h": {
                "total": len(recent_failures),
                "by_type": self._group_failures_by_type(recent_failures),
            },
            "recent_7d": {
                "total": len(weekly_failures),
                "by_type": self._group_failures_by_type(weekly_failures),
            },

            # 模式分析
            "pattern_analysis": pattern_analysis,

            # 趋势分析
            "trend_analysis": self._analyze_trends(),
        }

    def get_recent_failures(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的失败记录

        Args:
            limit: 返回记录数量限制

        Returns:
            List[Dict[str, Any]]: 最近的失败记录
        """
        recent_failures = sorted(
            self.failure_history, key=lambda f: f.failure_time, reverse=True
        )[:limit]

        return [failure.to_dict() for failure in recent_failures]

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
        now = datetime.now()
        start_time = now - timedelta(hours=hours)
        interval_delta = timedelta(minutes=interval_minutes)

        # 生成时间序列
        time_series = []
        current_time = start_time

        while current_time < now:
            next_time = current_time + interval_delta
            count = sum(
                1
                for failure in self.failure_history
                if current_time <= failure.failure_time < next_time
            )
            time_series.append({
                "timestamp": current_time.isoformat(),
                "count": count,
            })
            current_time = next_time

        return {
            "interval_minutes": interval_minutes,
            "time_series": time_series,
            "peak_time": self._find_peak_time(time_series),
            "average_failures": sum(t["count"] for t in time_series) / len(time_series),
        }

    def clear_old_failures(self, days_to_keep: int = 30) -> int:
        """
        清理旧的失败记录

        Args:
            days_to_keep: 保留天数

        Returns:
            int: 清理的记录数量
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        old_count = len(self.failure_history)

        self.failure_history = [
            f for f in self.failure_history if f.failure_time > cutoff_time
        ]

        # 同时清理失败模式中的旧记录
        for task_id in list(self.failure_patterns.keys()):
            # 检查该任务是否还有近期的失败记录
            task_has_recent_failure = any(
                f.task_id == task_id and f.failure_time > cutoff_time
                for f in self.failure_history
            )
            if not task_has_recent_failure:
                del self.failure_patterns[task_id]

        cleared_count = old_count - len(self.failure_history)
        logger.info(f"清理了 {cleared_count} 条旧失败记录")

        return cleared_count

    def _group_by_type(self) -> Dict[str, int]:
        """按类型分组统计"""
        failure_by_type = {}
        for failure in self.failure_history:
            failure_type = failure.failure_type.value
            failure_by_type[failure_type] = failure_by_type.get(failure_type, 0) + 1
        return failure_by_type

    def _group_by_task(self) -> Dict[str, int]:
        """按任务分组统计"""
        failure_by_task = {}
        for failure in self.failure_history:
            task_id = failure.task_id
            failure_by_task[task_id] = failure_by_task.get(task_id, 0) + 1
        return failure_by_task

    def _get_recent_failures(self, hours: int) -> List[TaskFailure]:
        """获取最近的失败记录"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            f for f in self.failure_history
            if f.failure_time > cutoff_time
        ]

    def _group_failures_by_type(self, failures: List[TaskFailure]) -> Dict[str, int]:
        """将失败记录按类型分组"""
        by_type = {}
        for failure in failures:
            failure_type = failure.failure_type.value
            by_type[failure_type] = by_type.get(failure_type, 0) + 1
        return by_type

    def _analyze_patterns(self) -> Dict[str, Any]:
        """分析失败模式"""
        if not self.failure_patterns:
            return {"repeated_failures": [], "common_sequences": []}

        # 找出重复失败的任务
        repeated_failures = [
            {
                "task_id": task_id,
                "count": len(failures),
                "types": list(set(ft.value for ft in failures)),
            }
            for task_id, failures in self.failure_patterns.items()
            if len(failures) >= 3
        ]

        # 找出常见的失败序列
        common_sequences = []
        for task_id, failures in self.failure_patterns.items():
            if len(failures) >= 2:
                sequence = [ft.value for ft in failures[-3:]]  # 最近3次
                common_sequences.append({
                    "task_id": task_id,
                    "sequence": sequence,
                })

        return {
            "repeated_failures": sorted(
                repeated_failures, key=lambda x: x["count"], reverse=True
            )[:10],
            "common_sequences": common_sequences[:10],
        }

    def _analyze_trends(self) -> Dict[str, Any]:
        """分析趋势"""
        # 比较最近24小时和前24小时
        recent_24h = self._get_recent_failures(hours=24)
        previous_24h = [
            f for f in self.failure_history
            if datetime.now() - timedelta(hours=48) < f.failure_time <= datetime.now() - timedelta(hours=24)
        ]

        recent_count = len(recent_24h)
        previous_count = len(previous_24h)

        trend = "stable"
        if recent_count > previous_count * 1.2:
            trend = "increasing"
        elif recent_count < previous_count * 0.8:
            trend = "decreasing"

        return {
            "trend": trend,
            "recent_24h": recent_count,
            "previous_24h": previous_count,
            "change_percent": round(
                ((recent_count - previous_count) / max(previous_count, 1)) * 100, 2
            ),
        }

    def _find_peak_time(self, time_series: List[Dict[str, Any]]) -> str | None:
        """找出峰值时间"""
        if not time_series:
            return None

        peak = max(time_series, key=lambda x: x["count"])
        return peak["timestamp"] if peak["count"] > 0 else None