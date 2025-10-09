"""
数据分析器
Data Analyzer

负责审计数据的分析和处理。
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging import get_logger

logger = get_logger(__name__)


class DataAnalyzer:
    """
    数据分析器 / Data Analyzer

    提供审计数据的深度分析功能。
    Provides deep analysis capabilities for audit data.
    """

    def __init__(self):
        """初始化数据分析器 / Initialize Data Analyzer"""
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 合规类别映射
        self.compliance_mapping = {
            "users": "user_management",
            "permissions": "access_control",
            "tokens": "authentication",
            "payment": "financial",
            "personal_data": "privacy",
            "health_records": "healthcare",
            "financial_data": "financial",
            "contact_information": "privacy",
            "audit_logs": "audit",
            "system_logs": "system",
        }

        # 动作类别映射
        self.action_categories = {
            "create": "data_modification",
            "update": "data_modification",
            "delete": "data_modification",
            "read": "data_access",
            "login": "authentication",
            "logout": "authentication",
            "export": "data_transfer",
            "import": "data_transfer",
            "access": "data_access",
            "execute": "system_operation",
        }

        # 数据敏感度级别
        self.sensitivity_levels = {
            "high": ["users", "permissions", "payment_info", "personal_data"],
            "medium": ["tokens", "audit_logs", "financial_data"],
            "low": ["logs", "cache", "temporary_data"],
        }

    def determine_compliance_category(
        self,
        table_name: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        """
        确定合规类别 / Determine Compliance Category

        Args:
            table_name: 表名 / Table name
            action: 动作 / Action

        Returns:
            Optional[str]: 合规类别 / Compliance category
        """
        if table_name and table_name in self.compliance_mapping:
            return self.compliance_mapping[table_name]

        if action and action in ["login", "logout", "access"]:
            return "authentication"

        return None

    def get_action_category(self, action: str) -> str:
        """
        获取动作类别 / Get Action Category

        Args:
            action: 动作 / Action

        Returns:
            str: 动作类别 / Action category
        """
        return self.action_categories.get(action, "unknown")

    def get_data_sensitivity_level(self, table_name: str) -> str:
        """
        获取数据敏感度级别 / Get Data Sensitivity Level

        Args:
            table_name: 表名 / Table name

        Returns:
            str: 敏感度级别 / Sensitivity level
        """
        for level, tables in self.sensitivity_levels.items():
            if table_name in tables:
                return level
        return "unknown"

    def analyze_data_changes(
        self,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        分析数据变更 / Analyze Data Changes

        Args:
            old_values: 旧值 / Old values
            new_values: 新值 / New values

        Returns:
            Dict[str, Any]: 变更分析结果 / Change analysis result
        """
        if not old_values and not new_values:
            return {
                "change_type": "none",
                "changed_fields": [],
                "added_fields": [],
                "removed_fields": [],
                "change_count": 0,
            }

        old_values = old_values or {}
        new_values = new_values or {}

        changed_fields = []
        added_fields = []
        removed_fields = []

        # 查找变更的字段
        for key in set(old_values.keys()) | set(new_values.keys()):
            old_val = old_values.get(key)
            new_val = new_values.get(key)

            if key in old_values and key not in new_values:
                removed_fields.append(key)
            elif key not in old_values and key in new_values:
                added_fields.append(key)
            elif old_val != new_val:
                changed_fields.append({
                    "field": key,
                    "old_value": old_val,
                    "new_value": new_val,
                    "value_type": type(old_val).__name__ if old_val else type(new_val).__name__,
                })

        # 确定变更类型
        if changed_fields or added_fields or removed_fields:
            change_type = "update"
        elif new_values and not old_values:
            change_type = "create"
        elif old_values and not new_values:
            change_type = "delete"
        else:
            change_type = "none"

        return {
            "change_type": change_type,
            "changed_fields": changed_fields,
            "added_fields": added_fields,
            "removed_fields": removed_fields,
            "change_count": len(changed_fields) + len(added_fields) + len(removed_fields),
        }

    def analyze_user_behavior(
        self,
        user_logs: List[Dict[str, Any]],
        time_window: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """
        分析用户行为 / Analyze User Behavior

        Args:
            user_logs: 用户日志列表 / User logs list
            time_window: 时间窗口 / Time window

        Returns:
            Dict[str, Any]: 行为分析结果 / Behavior analysis result
        """
        if not user_logs:
            return {
                "total_actions": 0,
                "unique_resources": 0,
                "action_frequency": {},
                "resource_access": {},
                "time_patterns": {},
                "risk_indicators": [],
            }

        # 统计动作频率
        action_frequency = {}
        resource_access = {}
        time_patterns = {}
        risk_indicators = []

        current_time = datetime.now()
        time_window = time_window or timedelta(hours=24)

        for log in user_logs:
            # 动作频率
            action = log.get("action", "unknown")
            action_frequency[action] = action_frequency.get(action, 0) + 1

            # 资源访问
            resource = log.get("resource_type", "unknown")
            resource_access[resource] = resource_access.get(resource, 0) + 1

            # 时间模式分析
            timestamp_str = log.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    hour = timestamp.hour
                    time_patterns[hour] = time_patterns.get(hour, 0) + 1
                except:
                    pass

            # 风险指标检测
            self._check_risk_indicators(log, risk_indicators, current_time, time_window)

        # 计算行为分数
        behavior_score = self._calculate_behavior_score(
            action_frequency, resource_access, risk_indicators
        )

        return {
            "total_actions": len(user_logs),
            "unique_resources": len(resource_access),
            "action_frequency": action_frequency,
            "resource_access": resource_access,
            "time_patterns": time_patterns,
            "risk_indicators": risk_indicators,
            "behavior_score": behavior_score,
            "analysis_timestamp": current_time.isoformat(),
        }

    def _check_risk_indicators(
        self,
        log: Dict[str, Any],
        risk_indicators: List[Dict[str, Any]],
        current_time: datetime,
        time_window: timedelta,
    ) -> None:
        """
        检查风险指标 / Check Risk Indicators

        Args:
            log: 日志条目 / Log entry
            risk_indicators: 风险指标列表 / Risk indicators list
            current_time: 当前时间 / Current time
            time_window: 时间窗口 / Time window
        """
        action = log.get("action", "")
        resource_type = log.get("resource_type", "")
        severity = log.get("severity", "")

        # 检查高风险动作
        high_risk_actions = ["delete", "export", "admin", "reset_password"]
        if action in high_risk_actions:
            risk_indicators.append({
                "type": "high_risk_action",
                "action": action,
                "resource": resource_type,
                "severity": severity,
                "timestamp": log.get("timestamp"),
            })

        # 检查异常访问模式
        if resource_type in ["users", "permissions", "admin"]:
            risk_indicators.append({
                "type": "sensitive_resource_access",
                "action": action,
                "resource": resource_type,
                "severity": severity,
                "timestamp": log.get("timestamp"),
            })

        # 检查错误频率
        if severity == "critical" or (log.get("metadata") and log.get("metadata", {}).get("error")):
            risk_indicators.append({
                "type": "error_occurrence",
                "action": action,
                "error": log.get("metadata", {}).get("error"),
                "timestamp": log.get("timestamp"),
            })

    def _calculate_behavior_score(
        self,
        action_frequency: Dict[str, int],
        resource_access: Dict[str, int],
        risk_indicators: List[Dict[str, Any]],
    ) -> float:
        """
        计算行为分数 / Calculate Behavior Score

        Args:
            action_frequency: 动作频率 / Action frequency
            resource_access: 资源访问 / Resource access
            risk_indicators: 风险指标 / Risk indicators

        Returns:
            float: 行为分数 / Behavior score
        """
        score = 100.0  # 基础分数

        # 根据高风险动作扣分
        high_risk_actions = ["delete", "export", "admin", "reset_password"]
        for action in high_risk_actions:
            if action in action_frequency:
                score -= action_frequency[action] * 10

        # 根据敏感资源访问扣分
        sensitive_resources = ["users", "permissions", "admin", "payment_info"]
        for resource in sensitive_resources:
            if resource in resource_access:
                score -= resource_access[resource] * 5

        # 根据风险指标扣分
        score -= len(risk_indicators) * 15

        # 确保分数不为负
        return max(0.0, score)

    def analyze_data_integrity(
        self,
        audit_logs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        分析数据完整性 / Analyze Data Integrity

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            Dict[str, Any]: 完整性分析结果 / Integrity analysis result
        """
        if not audit_logs:
            return {
                "total_logs": 0,
                "integrity_score": 0.0,
                "missing_fields": [],
                "invalid_formats": [],
                "duplicates": [],
                "anomalies": [],
            }

        missing_fields = []
        invalid_formats = []
        duplicates = []
        anomalies = []

        # 检查必填字段
        required_fields = ["user_id", "action", "timestamp", "severity"]
        for i, log in enumerate(audit_logs):
            for field in required_fields:
                if field not in log or log[field] is None:
                    missing_fields.append({
                        "log_index": i,
                        "missing_field": field,
                        "log_id": log.get("id"),
                    })

            # 检查时间戳格式
            timestamp = log.get("timestamp")
            if timestamp:
                try:
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    invalid_formats.append({
                        "log_index": i,
                        "field": "timestamp",
                        "value": timestamp,
                        "error": "Invalid timestamp format",
                    })

        # 检查重复条目
        seen_logs = set()
        for i, log in enumerate(audit_logs):
            log_key = (
                log.get("user_id"),
                log.get("action"),
                log.get("timestamp"),
                log.get("resource_type"),
                log.get("resource_id"),
            )
            if log_key in seen_logs:
                duplicates.append({
                    "log_index": i,
                    "duplicate_key": log_key,
                    "log_id": log.get("id"),
                })
            seen_logs.add(log_key)

        # 检查异常
        anomalies = self._detect_data_anomalies(audit_logs)

        # 计算完整性分数
        total_issues = len(missing_fields) + len(invalid_formats) + len(duplicates) + len(anomalies)
        integrity_score = max(0.0, 100.0 - (total_issues / len(audit_logs)) * 100)

        return {
            "total_logs": len(audit_logs),
            "integrity_score": integrity_score,
            "missing_fields": missing_fields,
            "invalid_formats": invalid_formats,
            "duplicates": duplicates,
            "anomalies": anomalies,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def _detect_data_anomalies(self, audit_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测数据异常 / Detect Data Anomalies

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            List[Dict[str, Any]]: 异常列表 / Anomalies list
        """
        anomalies = []

        # 检查时间异常
        timestamps = []
        for log in audit_logs:
            timestamp = log.get("timestamp")
            if timestamp:
                try:
                    timestamps.append(datetime.fromisoformat(timestamp.replace('Z', '+00:00')))
                except:
                    pass

        if len(timestamps) > 1:
            timestamps.sort()
            time_gaps = []
            for i in range(1, len(timestamps)):
                gap = (timestamps[i] - timestamps[i-1]).total_seconds()
                time_gaps.append(gap)

            if time_gaps:
                avg_gap = sum(time_gaps) / len(time_gaps)
                for i, gap in enumerate(time_gaps):
                    if gap > avg_gap * 10:  # 异常大的时间间隔
                        anomalies.append({
                            "type": "time_gap_anomaly",
                            "log_index": i + 1,
                            "gap_seconds": gap,
                            "average_gap": avg_gap,
                        })

        # 检查用户行为异常
        user_actions = {}
        for log in audit_logs:
            user_id = log.get("user_id")
            action = log.get("action")
            if user_id and action:
                if user_id not in user_actions:
                    user_actions[user_id] = {}
                user_actions[user_id][action] = user_actions[user_id].get(action, 0) + 1

        # 检查异常高频操作
        for user_id, actions in user_actions.items():
            for action, count in actions.items():
                if count > 100:  # 超过100次可能异常
                    anomalies.append({
                        "type": "high_frequency_action",
                        "user_id": user_id,
                        "action": action,
                        "count": count,
                    })

        return anomalies

    def generate_insights(
        self,
        audit_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        生成洞察 / Generate Insights

        Args:
            audit_data: 审计数据 / Audit data

        Returns:
            Dict[str, Any]: 洞察结果 / Insights result
        """
        insights = {
            "summary": {},
            "trends": {},
            "recommendations": [],
            "compliance_status": {},
        }

        # 摘要信息
        total_logs = audit_data.get("total_logs", 0)
        unique_users = audit_data.get("unique_users", 0)
        unique_actions = audit_data.get("unique_actions", 0)

        insights["summary"] = {
            "total_logs": total_logs,
            "unique_users": unique_users,
            "unique_actions": unique_actions,
            "avg_logs_per_user": total_logs / unique_users if unique_users > 0 else 0,
        }

        # 趋势分析
        action_counts = audit_data.get("action_counts", {})
        severity_counts = audit_data.get("severity_counts", {})

        insights["trends"] = {
            "most_common_action": max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None,
            "highest_severity": max(severity_counts.items(), key=lambda x: x[1])[0] if severity_counts else None,
            "action_diversity": len(action_counts),
            "severity_distribution": severity_counts,
        }

        # 生成建议
        recommendations = []

        if severity_counts.get("critical", 0) > 0:
            recommendations.append({
                "type": "security",
                "priority": "high",
                "message": f"发现 {severity_counts['critical']} 个严重错误，需要立即处理",
            })

        if action_counts.get("delete", 0) > total_logs * 0.1:
            recommendations.append({
                "type": "data_protection",
                "priority": "medium",
                "message": "删除操作比例较高，建议检查数据保护策略",
            })

        insights["recommendations"] = recommendations

        # 合规状态
        insights["compliance_status"] = {
            "data_logging": "active",
            "retention_policy": "compliant",
            "privacy_protection": "enabled",
            "audit_trail": "complete",
        }

        return insights