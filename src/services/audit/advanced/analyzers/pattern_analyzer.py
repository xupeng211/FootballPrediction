"""
模式分析器
Pattern Analyzer

负责分析审计日志中的行为模式和趋势。
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging import get_logger

logger = get_logger(__name__)


class PatternAnalyzer:
    """
    模式分析器 / Pattern Analyzer

    识别和分析审计日志中的行为模式和异常。
    Identifies and analyzes behavior patterns and anomalies in audit logs.
    """

    def __init__(self):
        """初始化模式分析器 / Initialize Pattern Analyzer"""
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 可疑模式配置
        self.suspicious_patterns = {
            "rapid_login_attempts": {
                "pattern": "multiple_logins_short_time",
                "threshold": 5,
                "time_window": timedelta(minutes=5),
                "severity": "high",
            },
            "bulk_data_export": {
                "pattern": "multiple_exports_short_time",
                "threshold": 3,
                "time_window": timedelta(minutes=10),
                "severity": "high",
            },
            "permission_changes": {
                "pattern": "multiple_permission_changes",
                "threshold": 2,
                "time_window": timedelta(hours=1),
                "severity": "medium",
            },
            "failed_operations": {
                "pattern": "multiple_failures",
                "threshold": 10,
                "time_window": timedelta(minutes=15),
                "severity": "medium",
            },
        }

        # 时间模式配置
        self.time_patterns = {
            "business_hours": (9, 17),
            "off_hours": (17, 24),
            "night_hours": (0, 6),
            "weekend": ["saturday", "sunday"],
        }

        # 行为模式配置
        self.behavior_patterns = {
            "normal_user": {
                "actions_per_hour": 10,
                "resources_per_session": 5,
                "session_duration": timedelta(hours=2),
            },
            "power_user": {
                "actions_per_hour": 50,
                "resources_per_session": 20,
                "session_duration": timedelta(hours=4),
            },
            "admin_user": {
                "actions_per_hour": 100,
                "resources_per_session": 50,
                "session_duration": timedelta(hours=8),
            },
        }

    def analyze_patterns(
        self,
        audit_logs: List[Dict[str, Any]],
        time_window: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """
        分析模式 / Analyze Patterns

        Args:
            audit_logs: 审计日志列表 / Audit logs list
            time_window: 时间窗口 / Time window

        Returns:
            Dict[str, Any]: 模式分析结果 / Pattern analysis result
        """
        if not audit_logs:
            return {
                "patterns_detected": [],
                "anomalies": [],
                "trends": {},
                "behavior_profiles": {},
                "risk_score": 0.0,
            }

        # 分析基本模式
        basic_patterns = self._analyze_basic_patterns(audit_logs)

        # 检测可疑模式
        suspicious_patterns = self._detect_suspicious_patterns(audit_logs, time_window)

        # 分析时间模式
        time_patterns = self._analyze_time_patterns(audit_logs)

        # 分析用户行为模式
        behavior_profiles = self._analyze_behavior_patterns(audit_logs)

        # 检测异常
        anomalies = self._detect_anomalies(audit_logs)

        # 计算风险分数
        risk_score = self._calculate_pattern_risk_score(suspicious_patterns, anomalies)

        return {
            "basic_patterns": basic_patterns,
            "suspicious_patterns": suspicious_patterns,
            "time_patterns": time_patterns,
            "behavior_profiles": behavior_profiles,
            "anomalies": anomalies,
            "risk_score": risk_score,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def _analyze_basic_patterns(
        self, audit_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析基本模式 / Analyze Basic Patterns

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            Dict[str, Any]: 基本模式 / Basic patterns
        """
        # 统计动作频率
        actions = [log.get("action", "unknown") for log in audit_logs]
        action_counts = Counter(actions)

        # 统计资源类型
        resources = [log.get("resource_type", "unknown") for log in audit_logs]
        resource_counts = Counter(resources)

        # 统计用户
        users = [log.get("user_id", "unknown") for log in audit_logs]
        user_counts = Counter(users)

        # 统计严重性
        severities = [log.get("severity", "medium") for log in audit_logs]
        severity_counts = Counter(severities)

        return {
            "action_distribution": dict(action_counts),
            "resource_distribution": dict(resource_counts),
            "user_distribution": dict(user_counts),
            "severity_distribution": dict(severity_counts),
            "most_common_action": action_counts.most_common(1)[0]
            if action_counts
            else None,
            "most_active_user": user_counts.most_common(1)[0] if user_counts else None,
            "most_accessed_resource": resource_counts.most_common(1)[0]
            if resource_counts
            else None,
        }

    def _detect_suspicious_patterns(
        self,
        audit_logs: List[Dict[str, Any]],
        time_window: Optional[timedelta] = None,
    ) -> List[Dict[str, Any]]:
        """
        检测可疑模式 / Detect Suspicious Patterns

        Args:
            audit_logs: 审计日志列表 / Audit logs list
            time_window: 时间窗口 / Time window

        Returns:
            List[Dict[str, Any]]: 可疑模式列表 / Suspicious patterns list
        """
        suspicious_patterns = []
        time_window = time_window or timedelta(hours=1)

        # 按用户分组
        user_logs = defaultdict(list)
        for log in audit_logs:
            user_id = log.get("user_id", "unknown")
            user_logs[user_id].append(log)

        # 检查每个用户的可疑模式
        for user_id, logs in user_logs.items():
            # 快速登录尝试
            login_attempts = [log for log in logs if log.get("action") == "login"]
            if self._check_rapid_attempts(login_attempts, 5, timedelta(minutes=5)):
                suspicious_patterns.append(
                    {
                        "type": "rapid_login_attempts",
                        "user_id": user_id,
                        "count": len(login_attempts),
                        "severity": "high",
                        "detected_at": datetime.now().isoformat(),
                    }
                )

            # 批量数据导出
            export_attempts = [log for log in logs if log.get("action") == "export"]
            if self._check_rapid_attempts(export_attempts, 3, timedelta(minutes=10)):
                suspicious_patterns.append(
                    {
                        "type": "bulk_data_export",
                        "user_id": user_id,
                        "count": len(export_attempts),
                        "severity": "high",
                        "detected_at": datetime.now().isoformat(),
                    }
                )

            # 权限变更
            permission_changes = [
                log for log in logs if log.get("resource_type") == "permissions"
            ]
            if len(permission_changes) > 2:
                suspicious_patterns.append(
                    {
                        "type": "multiple_permission_changes",
                        "user_id": user_id,
                        "count": len(permission_changes),
                        "severity": "medium",
                        "detected_at": datetime.now().isoformat(),
                    }
                )

            # 失败操作
            failed_operations = [
                log for log in logs if log.get("metadata", {}).get("error")
            ]
            if len(failed_operations) > 10:
                suspicious_patterns.append(
                    {
                        "type": "multiple_failures",
                        "user_id": user_id,
                        "count": len(failed_operations),
                        "severity": "medium",
                        "detected_at": datetime.now().isoformat(),
                    }
                )

        return suspicious_patterns

    def _check_rapid_attempts(
        self,
        attempts: List[Dict[str, Any]],
        threshold: int,
        time_window: timedelta,
    ) -> bool:
        """
        检查快速尝试 / Check Rapid Attempts

        Args:
            attempts: 尝试列表 / Attempts list
            threshold: 阈值 / Threshold
            time_window: 时间窗口 / Time window

        Returns:
            bool: 是否超过阈值 / Whether exceeds threshold
        """
        if len(attempts) < threshold:
            return False

        # 解析时间戳
        timestamps = []
        for attempt in attempts:
            timestamp_str = attempt.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    timestamps.append(timestamp)
                except Exception:
                    continue

        if len(timestamps) < threshold:
            return False

        timestamps.sort()

        # 检查是否有超过阈值的快速尝试
        for i in range(len(timestamps) - threshold + 1):
            if timestamps[i + threshold - 1] - timestamps[i] <= time_window:
                return True

        return False

    def _analyze_time_patterns(
        self, audit_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析时间模式 / Analyze Time Patterns

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            Dict[str, Any]: 时间模式 / Time patterns
        """
        hourly_activity = [0] * 24
        daily_activity = defaultdict(int)
        weekend_activity = 0
        weekday_activity = 0

        for log in audit_logs:
            timestamp_str = log.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    hour = timestamp.hour
                    day = timestamp.strftime("%A").lower()

                    hourly_activity[hour] += 1
                    daily_activity[day] += 1

                    if day in ["saturday", "sunday"]:
                        weekend_activity += 1
                    else:
                        weekday_activity += 1
                except Exception:
                    continue

        # 计算峰值时间
        peak_hour = hourly_activity.index(max(hourly_activity))
        peak_day = (
            max(daily_activity.items(), key=lambda x: x[1])[0]
            if daily_activity
            else "unknown"
        )

        return {
            "hourly_distribution": hourly_activity,
            "daily_distribution": dict(daily_activity),
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "weekend_ratio": weekend_activity / (weekend_activity + weekday_activity)
            if (weekend_activity + weekday_activity) > 0
            else 0,
            "business_hours_activity": sum(hourly_activity[9:18]) / sum(hourly_activity)
            if sum(hourly_activity) > 0
            else 0,
        }

    def _analyze_behavior_patterns(
        self, audit_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析行为模式 / Analyze Behavior Patterns

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            Dict[str, Any]: 行为模式 / Behavior patterns
        """
        user_profiles = defaultdict(
            lambda: {
                "total_actions": 0,
                "unique_resources": set(),
                "unique_actions": set(),
                "session_count": 0,
                "first_action": None,
                "last_action": None,
            }
        )

        for log in audit_logs:
            user_id = log.get("user_id", "unknown")
            profile = user_profiles[user_id]

            profile["total_actions"] += 1
            profile["unique_resources"].add(log.get("resource_type", "unknown"))
            profile["unique_actions"].add(log.get("action", "unknown"))

            timestamp_str = log.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    if (
                        not profile["first_action"]
                        or timestamp < profile["first_action"]
                    ):
                        profile["first_action"] = timestamp
                    if not profile["last_action"] or timestamp > profile["last_action"]:
                        profile["last_action"] = timestamp
                except Exception:
                    continue

        # 分类用户行为
        behavior_profiles = {}
        for user_id, profile in user_profiles.items():
            # 计算行为特征
            total_actions = profile["total_actions"]
            unique_resources = len(profile["unique_resources"])
            unique_actions = len(profile["unique_actions"])

            # 根据特征分类
            if total_actions > 100 and unique_resources > 20:
                user_type = "power_user"
            elif total_actions > 50 and unique_resources > 10:
                user_type = "normal_user"
            else:
                user_type = "casual_user"

            behavior_profiles[user_id] = {
                "user_type": user_type,
                "total_actions": total_actions,
                "unique_resources": unique_resources,
                "unique_actions": unique_actions,
                "resource_diversity": unique_resources / total_actions
                if total_actions > 0
                else 0,
                "action_diversity": unique_actions / total_actions
                if total_actions > 0
                else 0,
            }

        return behavior_profiles

    def _detect_anomalies(
        self, audit_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        检测异常 / Detect Anomalies

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            List[Dict[str, Any]]: 异常列表 / Anomalies list
        """
        anomalies = []

        # 检测异常时间模式
        time_anomalies = self._detect_time_anomalies(audit_logs)
        anomalies.extend(time_anomalies)

        # 检测异常用户行为
        user_anomalies = self._detect_user_anomalies(audit_logs)
        anomalies.extend(user_anomalies)

        # 检测异常资源访问
        resource_anomalies = self._detect_resource_anomalies(audit_logs)
        anomalies.extend(resource_anomalies)

        return anomalies

    def _detect_time_anomalies(
        self, audit_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        检测时间异常 / Detect Time Anomalies

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            List[Dict[str, Any]]: 时间异常列表 / Time anomalies list
        """
        anomalies = []

        # 检查夜间活动
        night_logs = [
            log for log in audit_logs if self._is_night_hour(log.get("timestamp"))
        ]

        if len(night_logs) > len(audit_logs) * 0.2:  # 超过20%的夜间活动
            anomalies.append(
                {
                    "type": "high_night_activity",
                    "count": len(night_logs),
                    "percentage": len(night_logs) / len(audit_logs) * 100,
                    "severity": "medium",
                }
            )

        # 检查周末活动
        weekend_logs = [
            log for log in audit_logs if self._is_weekend(log.get("timestamp"))
        ]

        if len(weekend_logs) > len(audit_logs) * 0.3:  # 超过30%的周末活动
            anomalies.append(
                {
                    "type": "high_weekend_activity",
                    "count": len(weekend_logs),
                    "percentage": len(weekend_logs) / len(audit_logs) * 100,
                    "severity": "low",
                }
            )

        return anomalies

    def _detect_user_anomalies(
        self, audit_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        检测用户异常 / Detect User Anomalies

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            List[Dict[str, Any]]: 用户异常列表 / User anomalies list
        """
        anomalies = []

        # 统计用户活动
        user_activity = defaultdict(int)
        for log in audit_logs:
            user_id = log.get("user_id", "unknown")
            user_activity[user_id] += 1

        # 检查异常活跃用户
        if user_activity:
            avg_activity = sum(user_activity.values()) / len(user_activity)
            for user_id, activity in user_activity.items():
                if activity > avg_activity * 5:  # 超过平均5倍
                    anomalies.append(
                        {
                            "type": "hyperactive_user",
                            "user_id": user_id,
                            "activity_count": activity,
                            "average_activity": avg_activity,
                            "severity": "medium",
                        }
                    )

        return anomalies

    def _detect_resource_anomalies(
        self, audit_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        检测资源异常 / Detect Resource Anomalies

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            List[Dict[str, Any]]: 资源异常列表 / Resource anomalies list
        """
        anomalies = []

        # 统计资源访问
        resource_access = defaultdict(int)
        for log in audit_logs:
            resource = log.get("resource_type", "unknown")
            resource_access[resource] += 1

        # 检查异常热门资源
        if resource_access:
            avg_access = sum(resource_access.values()) / len(resource_access)
            for resource, access_count in resource_access.items():
                if access_count > avg_access * 10:  # 超过平均10倍
                    anomalies.append(
                        {
                            "type": "high_access_resource",
                            "resource": resource,
                            "access_count": access_count,
                            "average_access": avg_access,
                            "severity": "low",
                        }
                    )

        return anomalies

    def _calculate_pattern_risk_score(
        self,
        suspicious_patterns: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]],
    ) -> float:
        """
        计算模式风险分数 / Calculate Pattern Risk Score

        Args:
            suspicious_patterns: 可疑模式列表 / Suspicious patterns list
            anomalies: 异常列表 / Anomalies list

        Returns:
            float: 风险分数 / Risk score
        """
        score = 0.0

        # 根据可疑模式计算风险
        for pattern in suspicious_patterns:
            severity = pattern.get("severity", "low")
            if severity == "high":
                score += 20
            elif severity == "medium":
                score += 10
            elif severity == "low":
                score += 5

        # 根据异常计算风险
        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            if severity == "high":
                score += 15
            elif severity == "medium":
                score += 8
            elif severity == "low":
                score += 3

        # 归一化分数到0-100范围
        return min(100.0, score)

    def _is_night_hour(self, timestamp_str: Optional[str]) -> bool:
        """
        检查是否为夜间时间 / Check if Night Hour

        Args:
            timestamp_str: 时间戳字符串 / Timestamp string

        Returns:
            bool: 是否为夜间 / Whether night time
        """
        if not timestamp_str:
            return False

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return 0 <= timestamp.hour < 6
        except Exception:
            return False

    def _is_weekend(self, timestamp_str: Optional[str]) -> bool:
        """
        检查是否为周末 / Check if Weekend

        Args:
            timestamp_str: 时间戳字符串 / Timestamp string

        Returns:
            bool: 是否为周末 / Whether weekend
        """
        if not timestamp_str:
            return False

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return timestamp.weekday() >= 5  # 5=Saturday, 6=Sunday
        except Exception:
            return False

    def get_pattern_summary(self, patterns: Dict[str, Any]) -> str:
        """
        获取模式摘要 / Get Pattern Summary

        Args:
            patterns: 模式分析结果 / Pattern analysis result

        Returns:
            str: 模式摘要 / Pattern summary
        """
        suspicious_count = len(patterns.get("suspicious_patterns", []))
        anomaly_count = len(patterns.get("anomalies", []))
        risk_score = patterns.get("risk_score", 0.0)

        summary = f"检测到 {suspicious_count} 个可疑模式和 {anomaly_count} 个异常，风险分数为 {risk_score:.1f}"

        if risk_score > 70:
            summary += " (高风险)"
        elif risk_score > 40:
            summary += " (中等风险)"
        else:
            summary += " (低风险)"

        return summary
