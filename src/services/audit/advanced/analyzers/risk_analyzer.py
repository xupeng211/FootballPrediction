"""
风险分析器
Risk Analyzer

负责分析审计操作的风险级别和威胁评估。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from src.core.logging import get_logger

logger = get_logger(__name__)


class RiskAnalyzer:
    """
    风险分析器 / Risk Analyzer

    评估审计操作的风险级别并提供威胁分析。
    Evaluates risk levels of audit operations and provides threat analysis.
    """

    def __init__(self):
        """初始化风险分析器 / Initialize Risk Analyzer"""
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 高风险动作
        self.high_risk_actions = {
            "delete",
            "export",
            "import",
            "admin",
            "reset_password",
            "change_role",
            "bulk_delete",
            "system_config",
            "database_backup",
            "user_deletion",
            "permission_grant",
            "data_restore",
        }

        # 高风险表
        self.high_risk_tables = {
            "users",
            "permissions",
            "tokens",
            "payment_info",
            "personal_data",
            "financial_data",
            "health_records",
            "system_config",
            "audit_logs",
            "security_settings",
            "encryption_keys",
            "api_keys",
        }

        # 高风险角色
        self.high_risk_roles = {
            "admin",
            "superadmin",
            "root",
            "system",
            "administrator",
            "db_admin",
            "security_admin",
            "audit_admin",
        }

        # 风险权重配置
        self.risk_weights = {
            "action": 0.3,
            "resource": 0.2,
            "user_role": 0.2,
            "time_pattern": 0.1,
            "frequency": 0.1,
            "error_rate": 0.1,
        }

        # 威胁类型
        self.threat_types = {
            "unauthorized_access": "未经授权访问",
            "data_exfiltration": "数据泄露",
            "privilege_escalation": "权限提升",
            "data_destruction": "数据破坏",
            "system_compromise": "系统损害",
            "insider_threat": "内部威胁",
            "malicious_activity": "恶意活动",
        }

        # 风险级别阈值
        self.risk_thresholds = {
            "critical": 90,
            "high": 70,
            "medium": 40,
            "low": 20,
        }

    def determine_severity(
        self,
        action: str,
        table_name: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        确定严重性级别 / Determine Severity Level

        Args:
            action: 动作 / Action
            table_name: 表名 / Table name
            error: 错误信息 / Error message

        Returns:
            str: 严重性级别 / Severity level
        """
        if error:
            return "critical"

        # 基于动作确定
        if action.lower() in self.high_risk_actions:
            return "high"

        # 基于表名确定
        if table_name and table_name.lower() in self.high_risk_tables:
            return "high"

        # 基于组合判断
        if action.lower() in ["update", "create"]:
            if table_name and table_name.lower() in self.high_risk_tables:
                return "high"
            else:
                return "medium"

        return "low"

    def assess_risk(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估操作风险 / Assess Operation Risk

        Args:
            operation: 操作信息 / Operation information

        Returns:
            Dict[str, Any]: 风险评估结果 / Risk assessment result
        """
        # 提取操作信息
        action = operation.get("action", "")
        resource_type = operation.get("resource_type", "")
        user_role = operation.get("user_role", "")
        user_id = operation.get("user_id", "")
        timestamp_str = operation.get("timestamp", "")

        # 计算各个风险因子
        action_risk = self._calculate_action_risk(action)
        resource_risk = self._calculate_resource_risk(resource_type)
        role_risk = self._calculate_role_risk(user_role)
        time_risk = self._calculate_time_risk(timestamp_str)
        frequency_risk = self._calculate_frequency_risk(user_id, timestamp_str)
        error_risk = self._calculate_error_risk(operation)

        # 计算综合风险分数
        total_risk = (
            action_risk * self.risk_weights["action"]
            + resource_risk * self.risk_weights["resource"]
            + role_risk * self.risk_weights["user_role"]
            + time_risk * self.risk_weights["time_pattern"]
            + frequency_risk * self.risk_weights["frequency"]
            + error_risk * self.risk_weights["error_rate"]
        )

        # 确定风险级别
        risk_level = self._determine_risk_level(total_risk)

        # 识别威胁类型
        threat_types = self._identify_threat_types(operation, total_risk)

        # 生成建议
        recommendations = self._generate_recommendations(operation, total_risk)

        return {
            "risk_score": round(total_risk, 2),
            "risk_level": risk_level,
            "risk_factors": {
                "action_risk": round(action_risk, 2),
                "resource_risk": round(resource_risk, 2),
                "role_risk": round(role_risk, 2),
                "time_risk": round(time_risk, 2),
                "frequency_risk": round(frequency_risk, 2),
                "error_risk": round(error_risk, 2),
            },
            "threat_types": threat_types,
            "recommendations": recommendations,
            "assessment_timestamp": datetime.now().isoformat(),
        }

    def _calculate_action_risk(self, action: str) -> float:
        """
        计算动作风险 / Calculate Action Risk

        Args:
            action: 动作 / Action

        Returns:
            float: 动作风险分数 / Action risk score
        """
        if not action:
            return 0.0

        action_lower = action.lower()

        if action_lower in self.high_risk_actions:
            return 80.0
        elif action_lower in ["update", "create"]:
            return 50.0
        elif action_lower in ["read", "access", "view"]:
            return 20.0
        elif action_lower in ["login", "logout"]:
            return 10.0
        else:
            return 30.0

    def _calculate_resource_risk(self, resource_type: str) -> float:
        """
        计算资源风险 / Calculate Resource Risk

        Args:
            resource_type: 资源类型 / Resource type

        Returns:
            float: 资源风险分数 / Resource risk score
        """
        if not resource_type:
            return 0.0

        resource_lower = resource_type.lower()

        if resource_lower in self.high_risk_tables:
            return 80.0
        elif resource_lower in ["config", "settings", "logs", "cache"]:
            return 50.0
        elif resource_lower in ["data", "records", "information"]:
            return 30.0
        else:
            return 20.0

    def _calculate_role_risk(self, user_role: str) -> float:
        """
        计算角色风险 / Calculate Role Risk

        Args:
            user_role: 用户角色 / User role

        Returns:
            float: 角色风险分数 / Role risk score
        """
        if not user_role:
            return 0.0

        role_lower = user_role.lower()

        if role_lower in self.high_risk_roles:
            return 70.0
        elif role_lower in ["manager", "supervisor", "lead"]:
            return 40.0
        elif role_lower in ["user", "member", "guest"]:
            return 20.0
        else:
            return 30.0

    def _calculate_time_risk(self, timestamp_str: str) -> float:
        """
        计算时间风险 / Calculate Time Risk

        Args:
            timestamp_str: 时间戳字符串 / Timestamp string

        Returns:
            float: 时间风险分数 / Time risk score
        """
        if not timestamp_str:
            return 50.0  # 无时间信息视为中等风险

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            hour = timestamp.hour
            weekday = timestamp.weekday()

            # 夜间时间风险更高
            if 0 <= hour < 6:  # 凌晨0-6点
                time_risk = 60.0
            elif 22 <= hour < 24 or 6 <= hour < 9:  # 晚上10-12点，早上6-9点
                time_risk = 40.0
            else:  # 正常工作时间
                time_risk = 20.0

            # 周末风险更高
            if weekday >= 5:  # 周末
                time_risk += 20.0

            return min(100.0, time_risk)

        except Exception:
            return 50.0

    def _calculate_frequency_risk(self, user_id: str, timestamp_str: str) -> float:
        """
        计算频率风险 / Calculate Frequency Risk

        Args:
            user_id: 用户ID / User ID
            timestamp_str: 时间戳字符串 / Timestamp string

        Returns:
            float: 频率风险分数 / Frequency risk score
        """
        # 这里简化处理，实际应该基于历史数据计算
        # 返回默认值
        return 30.0

    def _calculate_error_risk(self, operation: Dict[str, Any]) -> float:
        """
        计算错误风险 / Calculate Error Risk

        Args:
            operation: 操作信息 / Operation information

        Returns:
            float: 错误风险分数 / Error risk score
        """
        error_risk = 0.0

        # 检查是否有错误
        metadata = operation.get("metadata", {})
        if metadata and metadata.get("error"):
            error_risk += 50.0

        # 检查严重性
        severity = operation.get("severity", "")
        if severity == "critical":
            error_risk += 30.0
        elif severity == "high":
            error_risk += 20.0

        return min(100.0, error_risk)

    def _determine_risk_level(self, risk_score: float) -> str:
        """
        确定风险级别 / Determine Risk Level

        Args:
            risk_score: 风险分数 / Risk score

        Returns:
            str: 风险级别 / Risk level
        """
        if risk_score >= self.risk_thresholds["critical"]:
            return "critical"
        elif risk_score >= self.risk_thresholds["high"]:
            return "high"
        elif risk_score >= self.risk_thresholds["medium"]:
            return "medium"
        else:
            return "low"

    def _identify_threat_types(
        self, operation: Dict[str, Any], risk_score: float
    ) -> List[str]:
        """
        识别威胁类型 / Identify Threat Types

        Args:
            operation: 操作信息 / Operation information
            risk_score: 风险分数 / Risk score

        Returns:
            List[str]: 威胁类型列表 / Threat types list
        """
        threat_types = []

        action = operation.get("action", "")
        resource_type = operation.get("resource_type", "")
        user_role = operation.get("user_role", "")
        operation.get("user_id", "")

        # 基于动作识别威胁
        if action in ["delete", "bulk_delete"]:
            threat_types.append("data_destruction")
        elif action == "export":
            threat_types.append("data_exfiltration")
        elif action in ["change_role", "permission_grant"]:
            threat_types.append("privilege_escalation")

        # 基于资源类型识别威胁
        if resource_type in ["users", "permissions", "admin"]:
            threat_types.append("unauthorized_access")

        # 基于用户角色识别威胁
        if user_role in self.high_risk_roles and risk_score > 70:
            threat_types.append("insider_threat")

        # 高风险操作可能是恶意活动
        if risk_score > 80:
            threat_types.append("malicious_activity")

        return list(set(threat_types))

    def _generate_recommendations(
        self, operation: Dict[str, Any], risk_score: float
    ) -> List[str]:
        """
        生成建议 / Generate Recommendations

        Args:
            operation: 操作信息 / Operation information
            risk_score: 风险分数 / Risk score

        Returns:
            List[str]: 建议列表 / Recommendations list
        """
        recommendations = []

        if risk_score > 80:
            recommendations.extend(
                [
                    "立即审查此操作",
                    "通知安全团队",
                    "考虑临时限制用户访问",
                    "进行详细的行为分析",
                ]
            )
        elif risk_score > 60:
            recommendations.extend(
                ["密切监控用户后续操作", "验证操作合法性", "考虑加强身份验证"]
            )
        elif risk_score > 40:
            recommendations.extend(["记录此操作以备后续审查", "定期检查相关活动"])

        action = operation.get("action", "")
        if action in ["export", "delete"]:
            recommendations.append("确保操作符合数据保护政策")

        resource_type = operation.get("resource_type", "")
        if resource_type in ["users", "permissions"]:
            recommendations.append("验证权限变更的必要性")

        return recommendations

    def analyze_risk_trends(
        self, operations: List[Dict[str, Any]], time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        分析风险趋势 / Analyze Risk Trends

        Args:
            operations: 操作列表 / Operations list
            time_window: 时间窗口 / Time window

        Returns:
            Dict[str, Any]: 风险趋势分析 / Risk trend analysis
        """
        if not operations:
            return {
                "overall_risk_trend": "stable",
                "risk_distribution": {},
                "high_risk_periods": [],
                "top_risky_users": [],
                "risk_evolution": [],
            }

        # 计算每个操作的风险
        risk_scores = []
        user_risks = defaultdict(list)
        time_risks = defaultdict(list)

        for operation in operations:
            risk_assessment = self.assess_risk(operation)
            risk_score = risk_assessment["risk_score"]
            risk_scores.append(risk_score)

            user_id = operation.get("user_id", "unknown")
            user_risks[user_id].append(risk_score)

            timestamp_str = operation.get("timestamp", "")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    date_key = timestamp.date().isoformat()
                    time_risks[date_key].append(risk_score)
                except Exception:
                    pass

        # 分析风险分布
        risk_distribution = {
            "critical": sum(1 for score in risk_scores if score >= 90),
            "high": sum(1 for score in risk_scores if 70 <= score < 90),
            "medium": sum(1 for score in risk_scores if 40 <= score < 70),
            "low": sum(1 for score in risk_scores if score < 40),
        }

        # 识别高风险用户
        user_avg_risks = {
            user_id: sum(risks) / len(risks) for user_id, risks in user_risks.items()
        }
        top_risky_users = sorted(
            user_avg_risks.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # 分析风险趋势
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        if avg_risk > 60:
            overall_trend = "increasing"
        elif avg_risk < 30:
            overall_trend = "decreasing"
        else:
            overall_trend = "stable"

        return {
            "overall_risk_trend": overall_trend,
            "average_risk_score": round(avg_risk, 2),
            "risk_distribution": risk_distribution,
            "high_risk_users": top_risky_users,
            "daily_risk_averages": {
                date: sum(risks) / len(risks) for date, risks in time_risks.items()
            },
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def get_risk_alert_thresholds(self) -> Dict[str, float]:
        """
        获取风险警报阈值 / Get Risk Alert Thresholds

        Returns:
            Dict[str, float]: 风险警报阈值 / Risk alert thresholds
        """
        return {
            "critical_alert": 90.0,
            "high_alert": 70.0,
            "medium_alert": 50.0,
            "daily_risk_limit": 1000.0,
            "user_risk_limit": 500.0,
        }

    def should_trigger_alert(self, risk_assessment: Dict[str, Any]) -> bool:
        """
        是否应该触发警报 / Should Trigger Alert

        Args:
            risk_assessment: 风险评估结果 / Risk assessment result

        Returns:
            bool: 是否触发警报 / Whether to trigger alert
        """
        risk_score = risk_assessment.get("risk_score", 0)
        risk_level = risk_assessment.get("risk_level", "low")
        threat_types = risk_assessment.get("threat_types", [])

        # 高分数或高级别触发警报
        if risk_score >= 80 or risk_level in ["critical", "high"]:
            return True

        # 特定威胁类型触发警报
        critical_threats = [
            "unauthorized_access",
            "data_exfiltration",
            "privilege_escalation",
            "malicious_activity",
        ]

        if any(threat in critical_threats for threat in threat_types):
            return True

        return False
