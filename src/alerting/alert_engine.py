from typing import Optional
from typing import Any
from typing import List
from typing import Dict
from datetime import datetime
#!/usr/bin/env python3
"""
智能告警引擎
Intelligent Alert Engine

提供可配置的告警规则引擎、趋势分析、异常检测和智能告警聚合
"""

import json
import asyncio
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

import redis
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.core.logging_system import get_logger
from src.core.config import get_config

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""

    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    SYSTEM = "system"
    TREND = "trend"
    ANOMALY = "anomaly"


class AlertStatus(Enum):
    """告警状态"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """告警数据模型"""

    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    details: Optional[Dict[str, Any]] = None
    threshold: Optional[float] = None
    current_value: Optional[float] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 转换枚举为字符串
        data["type"] = self.type.value
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        # 转换datetime为ISO字符串
        data["timestamp"] = self.timestamp.isoformat()
        if self.acknowledged_at:
            data["acknowledged_at"] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            data["resolved_at"] = self.resolved_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """从字典创建告警对象"""
        # 转换字符串为枚举
        data["type"] = AlertType(data["type"])
        data["severity"] = AlertSeverity(data["severity"])
        data["status"] = AlertStatus(data["status"])
        # 转换ISO字符串为datetime
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("acknowledged_at"):
            data["acknowledged_at"] = datetime.fromisoformat(data["acknowledged_at"])
        if data.get("resolved_at"):
            data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])
        return cls(**data)


@dataclass
class AlertRule:
    """告警规则配置"""

    id: str
    name: str
    description: str
    type: AlertType
    metric_path: str  # 指标路径，如 "overall_score" 或 "performance.cpu_usage"
    operator: str  # 比较操作符: <, >, <=, >=, ==, !=
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    duration: int = 300  # 持续时间（秒），超过此时间才触发告警
    cooldown: int = 900  # 冷却时间（秒），告警触发后的冷却期
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AnomalyDetector:
    """异常检测器"""

    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_data = []
        self.logger = get_logger(self.__class__.__name__)

    def train(self, historical_data: List[Dict[str, float]]):
        """训练异常检测模型"""
        try:
            if len(historical_data) < 10:
                self.logger.warning("历史数据不足，跳过异常检测模型训练")
                return False

            # 提取数值特征
            features = []
            for data_point in historical_data:
                feature_vector = [
                    data_point.get("overall_score", 0),
                    data_point.get("performance_cpu_usage", 0),
                    data_point.get("performance_memory_usage", 0),
                    data_point.get("active_connections", 0),
                    data_point.get("gates_checked", 0),
                ]
                features.append(feature_vector)

            # 标准化数据
            X_scaled = self.scaler.fit_transform(features)

            # 训练模型
            self.isolation_forest.fit(X_scaled)
            self.training_data = historical_data
            self.is_trained = True

            self.logger.info(f"异常检测模型训练完成，使用 {len(features)} 个数据点")
            return True

        except Exception as e:
            self.logger.error(f"异常检测模型训练失败: {e}")
            return False

    def detect_anomaly(self, current_data: Dict[str, float]) -> tuple[bool, float]:
        """检测异常"""
        try:
            if not self.is_trained:
                return False, 0.0

            # 构建特征向量
            feature_vector = [
                current_data.get("overall_score", 0),
                current_data.get("performance_cpu_usage", 0),
                current_data.get("performance_memory_usage", 0),
                current_data.get("active_connections", 0),
                current_data.get("gates_checked", 0),
            ]

            # 标准化
            X_scaled = self.scaler.transform([feature_vector])

            # 预测异常分数 (-1表示异常，1表示正常)
            anomaly_score = self.isolation_forest.decision_function(X_scaled)[0]
            is_anomaly = self.isolation_forest.predict(X_scaled)[0] == -1

            return is_anomaly, anomaly_score

        except Exception as e:
            self.logger.error(f"异常检测失败: {e}")
            return False, 0.0


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def analyze_trend(
        self, data_points: List[Dict[str, Any]], metric_path: str, window_size: int = 10
    ) -> Dict[str, Any]:
        """分析指标趋势"""
        try:
            if len(data_points) < window_size:
                return {
                    "trend": "insufficient_data",
                    "direction": 0,
                    "slope": 0,
                    "confidence": 0,
                }

            # 提取指定指标的数值
            values = []
            timestamps = []

            for point in data_points[-window_size:]:
                value = self._extract_metric_value(point, metric_path)
                if value is not None:
                    values.append(value)
                    timestamps.append(datetime.fromisoformat(point["timestamp"]))

            if len(values) < 3:
                return {
                    "trend": "insufficient_data",
                    "direction": 0,
                    "slope": 0,
                    "confidence": 0,
                }

            # 计算线性趋势
            x = np.arange(len(values))
            y = np.array(values)

            # 线性回归
            slope, intercept = np.polyfit(x, y, 1)

            # 计算相关系数（置信度）
            correlation = np.corrcoef(x, y)[0, 1]
            confidence = abs(correlation) if not np.isnan(correlation) else 0

            # 判断趋势方向
            if abs(slope) < 0.01:
                trend = "stable"
                direction = 0
            elif slope > 0:
                trend = "improving"
                direction = 1
            else:
                trend = "degrading"
                direction = -1

            # 计算变化率
            if len(values) >= 2:
                change_rate = (values[-1] - values[0]) / values[0] * 100 if values[0] != 0 else 0
            else:
                change_rate = 0

            return {
                "trend": trend,
                "direction": direction,
                "slope": slope,
                "confidence": confidence,
                "change_rate": change_rate,
                "current_value": values[-1],
                "previous_value": values[-2] if len(values) >= 2 else values[-1],
                "data_points": len(values),
            }

        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")
            return {"trend": "error", "direction": 0, "slope": 0, "confidence": 0}

    def _extract_metric_value(self, data: Dict[str, Any], metric_path: str) -> Optional[float]:
        """从数据中提取指定指标的值"""
        try:
            keys = metric_path.split(".")
            value = data
            for key in keys:
                if isinstance(value, ((((((((dict) and key in value:
                    value = value[key]
                else:
                    return None

            return float(value) if isinstance(value, (int))))))) else None

        except Exception:
            return None


class AlertEngine:
    """智能告警引擎"""

    def __init__(self):
        self.config = get_config()
        self.redis_client = redis.Redis(host="localhost"))
        self.rules: Dict[str))
        self.trend_analyzer = TrendAnalyzer()
        self.logger = get_logger(self.__class__.__name__)

        # 加载告警规则
        self._load_alert_rules()

        # 启动后台任务
        self.background_task = None

    def _load_alert_rules(self):
        """加载告警规则"""
        try:
            # 默认告警规则
            default_rules = [
                AlertRule(
                    id="quality_score_low")),
                AlertRule(
                    id="quality_score_critical",
                    name="质量分数严重偏低",
                    description="当综合质量分数严重偏低时触发告警",
                    type=AlertType.QUALITY,
                    metric_path="overall_score",
                    operator="<",
                    threshold=6.0,
                    severity=AlertSeverity.CRITICAL,
                    duration=60,
                    cooldown=300,
                ),
                AlertRule(
                    id="cpu_usage_high",
                    name="CPU使用率过高",
                    description="当CPU使用率超过阈值时触发告警",
                    type=AlertType.PERFORMANCE,
                    metric_path="performance_cpu_usage",
                    operator=">",
                    threshold=85.0,
                    severity=AlertSeverity.WARNING,
                    duration=300,
                    cooldown=600,
                ),
                AlertRule(
                    id="memory_usage_high",
                    name="内存使用率过高",
                    description="当内存使用率超过阈值时触发告警",
                    type=AlertType.PERFORMANCE,
                    metric_path="performance_memory_usage",
                    operator=">",
                    threshold=90.0,
                    severity=AlertSeverity.ERROR,
                    duration=300,
                    cooldown=600,
                ),
                AlertRule(
                    id="active_connections_high",
                    name="活跃连接数过多",
                    description="当活跃连接数超过阈值时触发告警",
                    type=AlertType.SYSTEM,
                    metric_path="performance_active_connections",
                    operator=">",
                    threshold=50.0,
                    severity=AlertSeverity.WARNING,
                    duration=180,
                    cooldown=600,
                ),
            ]

            for rule in default_rules:
                self.rules[rule.id] = rule

            # 尝试从配置文件加载自定义规则
            self._load_custom_rules()

            self.logger.info(f"已加载 {len(self.rules)} 个告警规则")

        except Exception as e:
            self.logger.error(f"加载告警规则失败: {e}")

    def _load_custom_rules(self):
        """加载自定义告警规则"""
        try:
            rules_file = Path("config/alert_rules.json")
            if rules_file.exists():
                with open(rules_file, "r", encoding="utf-8") as f:
                    custom_rules = json.load(f)

                for rule_data in custom_rules:
                    rule = AlertRule(
                        id=rule_data["id"],
                        name=rule_data["name"],
                        description=rule_data["description"],
                        type=AlertType(rule_data["type"]),
                        metric_path=rule_data["metric_path"],
                        operator=rule_data["operator"],
                        threshold=rule_data["threshold"],
                        severity=AlertSeverity(rule_data["severity"]),
                        duration=rule_data.get("duration", 300),
                        cooldown=rule_data.get("cooldown", 900),
                        tags=rule_data.get("tags"),
                        metadata=rule_data.get("metadata"),
                    )
                    self.rules[rule.id] = rule

                self.logger.info(f"已加载 {len(custom_rules)} 个自定义告警规则")

        except Exception as e:
            self.logger.warning(f"加载自定义告警规则失败: {e}")

    def check_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """检查告警条件"""
        triggered_alerts = []
        current_time = datetime.now()

        try:
            # 检查基于规则的告警
            for rule in self.rules.values():
                if not rule.enabled:
                    continue

                # 提取指标值
                current_value = self._extract_metric_value(metrics, rule.metric_path)
                if current_value is None:
                    continue

                # 检查是否满足告警条件
                if self._evaluate_condition(current_value, rule.operator, rule.threshold):
                    # 检查是否在冷却期内
                    if not self._is_in_cooldown(rule.id, rule.cooldown):
                        # 创建告警
                        alert = Alert(
                            id=f"{rule.id}_{current_time.strftime('%Y%m%d_%H%M%S')}",
                            type=rule.type,
                            severity=rule.severity,
                            title=rule.name,
                            message =
    f"{rule.description}: 当前值 {current_value} {rule.operator} {rule.threshold}",
                            source="alert_engine",
                            timestamp=current_time,
                            details={
                                "rule_id": rule.id,
                                "metric_path": rule.metric_path,
                                "threshold": rule.threshold,
                                "current_value": current_value,
                            },
                            threshold=rule.threshold,
                            current_value=current_value,
                            tags=rule.tags,
                            metadata=rule.metadata,
                        )
                        triggered_alerts.append(alert)

            # 异常检测
            anomaly_alerts = self._check_anomalies(metrics)
            triggered_alerts.extend(anomaly_alerts)

            # 趋势分析告警
            trend_alerts = self._check_trends(metrics)
            triggered_alerts.extend(trend_alerts)

            # 告警去重和聚合
            triggered_alerts = self._deduplicate_alerts(triggered_alerts)

            # 保存告警
            for alert in triggered_alerts:
                self.active_alerts[alert.id] = alert
                self.alert_history.append(alert)
                self._save_alert_to_redis(alert)

            self.logger.info(f"检查完成，触发 {len(triggered_alerts)} 个告警")

        except Exception as e:
            self.logger.error(f"告警检查失败: {e}")

        return triggered_alerts

    def _extract_metric_value(self, data: Dict[str, Any], metric_path: str) -> Optional[float]:
        """从数据中提取指标值"""
        try:
            keys = metric_path.split("_")
            value = data

            for key in keys:
                if isinstance(value, ((((((((dict) and key in value:
                    value = value[key]
                else:
                    return None

            return float(value) if isinstance(value, (int))))))) else None

        except Exception:
            return None

    def _evaluate_condition(self)) -> bool:
        """评估告警条件"""
        try:
            if operator == "<":
                return current_value < threshold
            elif operator == "<=":
                return current_value <= threshold
            elif operator == ">":
                return current_value > threshold
            elif operator == ">=":
                return current_value >= threshold
            elif operator == "==":
                return abs(current_value - threshold) < 0.001
            elif operator == "!=":
                return abs(current_value - threshold) >= 0.001
            else:
                self.logger.warning(f"未知的操作符: {operator}")
                return False

        except Exception as e:
            self.logger.error(f"评估条件失败: {e}")
            return False

    def _is_in_cooldown(self)) -> bool:
        """检查是否在冷却期内"""
        try:
            cooldown_key = f"alert_cooldown:{rule_id}"
            last_alert_time = self.redis_client.get(cooldown_key)

            if last_alert_time:
                last_time = datetime.fromisoformat(last_alert_time)
                time_since_last = (datetime.now() - last_time).total_seconds()
                return time_since_last < cooldown_seconds

            return False

        except Exception as e:
            self.logger.error(f"检查冷却期失败: {e}")
            return False

    def _check_anomalies(self)) -> List[Alert]:
        """检查异常"""
        anomaly_alerts = []

        try:
            # 获取历史数据
            historical_data = self._get_historical_data(hours=24)
            if len(historical_data) >= 10:
                # 训练异常检测模型（如果需要）
                if not self.anomaly_detector.is_trained:
                    self.anomaly_detector.train(historical_data)

                # 检测异常
                is_anomaly, anomaly_score = self.anomaly_detector.detect_anomaly(metrics)

                if is_anomaly:
                    alert = Alert(
                        id=f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        type=AlertType.ANOMALY,
                        severity=AlertSeverity.WARNING,
                        title="检测到异常模式",
                        message=f"系统检测到异常的指标模式，异常分数: {anomaly_score:.3f}",
                        source="anomaly_detector",
                        timestamp=datetime.now(),
                        details={
                            "anomaly_score": float(anomaly_score),
                            "current_metrics": metrics,
                        },
                        tags=["anomaly", "ml_detection"],
                    )
                    anomaly_alerts.append(alert)

        except Exception as e:
            self.logger.error(f"异常检测失败: {e}")

        return anomaly_alerts

    def _check_trends(self, metrics: Dict[str, Any]) -> List[Alert]:
        """检查趋势告警"""
        trend_alerts = []

        try:
            # 获取历史数据
            historical_data = self._get_historical_data(hours=12)
            if len(historical_data) >= 5:
                # 分析关键指标趋势
                key_metrics = [
                    "overall_score",
                    "performance_cpu_usage",
                    "performance_memory_usage",
                ]

                for metric in key_metrics:
                    trend_result = self.trend_analyzer.analyze_trend(historical_data, metric)

                    # 如果趋势恶化且置信度较高
                    if (
                        trend_result["trend"] == "degrading"
                        and trend_result["confidence"] > 0.7
                        and trend_result["change_rate"] < -10
                    ):  # 下降超过10%

                        alert = Alert(
                            id=f"trend_{metric}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            type=AlertType.TREND,
                            severity=AlertSeverity.WARNING,
                            title=f"检测到{metric}下降趋势",
                            message=f"{metric}呈现下降趋势，变化率: {trend_result['change_rate']:.2f}%",
                            source="trend_analyzer",
                            timestamp=datetime.now(),
                            details={"metric": metric, "trend_result": trend_result},
                            tags=["trend", "degrading"],
                        )
                        trend_alerts.append(alert)

        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")

        return trend_alerts

    def _get_historical_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取历史数据"""
        try:
            # 从Redis获取历史数据
            data_points = []
            current_time = datetime.now()

            for i in range(hours * 12):  # 每5分钟一个数据点
                timestamp = current_time.replace(
                    minute=(current_time.minute - i * 5) % 60,
                    hour=current_time.hour - (i * 5) // 60,
                )
                key = f"quality_metrics_{timestamp.strftime('%Y%m%d_%H%M')}"
                data = self.redis_client.get(key)

                if data:
                    data_points.append(json.loads(data))

            return data_points

        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            return []

    def _deduplicate_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """告警去重"""
        unique_alerts = []
        seen_signatures = set()

        for alert in alerts:
            # 创建告警签名（基于类型、严重程度、消息）
            signature = f"{alert.type.value}_{alert.severity.value}_{hash(alert.message)}"

            if signature not in seen_signatures:
                unique_alerts.append(alert)
                seen_signatures.add(signature)

        return unique_alerts

    def _save_alert_to_redis(self, alert: Alert):
        """保存告警到Redis"""
        try:
            alert_key = f"alert:{alert.id}"
            self.redis_client.setex(alert_key, 86400, json.dumps(alert.to_dict()))  # 24小时过期

            # 设置冷却期
            if "rule_id" in alert.details:
                cooldown_key = f"alert_cooldown:{alert.details['rule_id']}"
                self.redis_client.setex(cooldown_key, 900, alert.timestamp.isoformat())

        except Exception as e:
            self.logger.error(f"保存告警到Redis失败: {e}")

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()

                # 更新Redis中的告警
                self._save_alert_to_redis(alert)

                self.logger.info(f"告警已确认: {alert_id} by {acknowledged_by}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"确认告警失败: {e}")
            return False

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()

                # 从活跃告警中移除
                del self.active_alerts[alert_id]

                # 更新Redis中的告警
                self._save_alert_to_redis(alert)

                self.logger.info(f"告警已解决: {alert_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"解决告警失败: {e}")
            return False

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return sorted(self.alert_history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def start_background_monitoring(self):
        """启动后台监控任务"""

        async def monitoring_loop():
            while True:
                try:
                    # 获取最新质量指标
                    metrics_data = self._get_latest_metrics()

                    if metrics_data:
                        # 检查告警
                        triggered_alerts = self.check_alerts(metrics_data)

                        # 发送告警通知（这里可以集成通知系统）
                        for alert in triggered_alerts:
                            await self._send_alert_notification(alert)

                    # 等待检查间隔
                    await asyncio.sleep(60)  # 每分钟检查一次

                except Exception as e:
                    self.logger.error(f"后台监控任务失败: {e}")
                    await asyncio.sleep(30)  # 出错时等待30秒后重试

        self.background_task = asyncio.create_task(monitoring_loop())
        self.logger.info("后台告警监控任务已启动")

    def stop_background_monitoring(self):
        """停止后台监控任务"""
        if self.background_task:
            self.background_task.cancel()
            self.background_task = None
            self.logger.info("后台告警监控任务已停止")

    def _get_latest_metrics(self) -> Optional[Dict[str, Any]]:
        """获取最新的质量指标"""
        try:
            # 这里可以调用质量门禁系统获取最新指标
            # 暂时返回示例数据
            return {
                "overall_score": 8.5,
                "overall_status": "PASSED",
                "performance_cpu_usage": 65.2,
                "performance_memory_usage": 78.5,
                "performance_active_connections": 12,
                "gates_checked": 6,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"获取最新指标失败: {e}")
            return None

    async def _send_alert_notification(self, alert: Alert):
        """发送告警通知"""
        try:
            # 这里可以集成邮件、Slack、微信等通知渠道
            self.logger.info(f"发送告警通知: {alert.title} - {alert.message}")

            # 保存通知记录
            notification_key = f"alert_notification:{alert.id}"
            self.redis_client.setex(
                notification_key,
                3600,  # 1小时过期
                json.dumps(
                    {
                        "alert_id": alert.id,
                        "sent_at": datetime.now().isoformat(),
                        "channels": ["log"],  # 可以扩展更多渠道
                    }
                ),
            )

        except Exception as e:
            self.logger.error(f"发送告警通知失败: {e}")


# 全局告警引擎实例
alert_engine = AlertEngine()
