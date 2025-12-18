#!/usr/bin/env python3
"""
Sprint 9 首周观察期预案管理系统

自动监控和回退系统，确保实战安全：
1. Brier Score偏差监控
2. 自动观察模式触发
3. 风险阈值管理
4. 回退机制执行
5. 观察期报告生成

使用方法:
  python observation_mode_manager.py --check
  python observation_mode_manager.py --enable --reason "manual"
  python observation_mode_manager.py --disable
  python observation_mode_manager.py --report

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - Production Safety)
"""

import asyncio
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings
from database.db_pool import DatabasePool

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ObservationMode(Enum):
    """观察模式状态"""

    NORMAL = "normal"  # 正常模式（预测+投注）
    OBSERVATION = "observation"  # 观察模式（仅预测，不投注）
    SUSPENDED = "suspended"  # 暂停模式（停止预测）
    EMERGENCY = "emergency"  # 紧急模式（完全停止）


@dataclass
class ObservationThreshold:
    """观察模式阈值配置"""

    name: str
    description: str
    threshold_value: float
    comparison_operator: str  # "gt", "lt", "eq"
    criticality: str  # "low", "medium", "high", "critical"
    enabled: bool = True


@dataclass
class ObservationEvent:
    """观察模式事件"""

    event_id: str
    timestamp: str
    mode_before: ObservationMode
    mode_after: ObservationMode
    trigger_reason: str
    metrics: Dict[str, Any]
    duration_minutes: Optional[int] = None
    resolved: bool = False
    resolution_reason: Optional[str] = None


class ObservationModeManager:
    """观察模式管理器"""

    def __init__(self):
        self.settings = get_settings()
        self.db_pool = None

        # 观察模式阈值配置
        self.thresholds = [
            ObservationThreshold(
                name="brier_score_deviation",
                description="Brier Score偏差超过15%",
                threshold_value=15.0,
                comparison_operator="gt",
                criticality="high",
            ),
            ObservationThreshold(
                name="prediction_accuracy_drop",
                description="预测准确率低于40%",
                threshold_value=40.0,
                comparison_operator="lt",
                criticality="critical",
            ),
            ObservationThreshold(
                name="roi_loss_threshold",
                description="单日ROI损失超过20%",
                threshold_value=-20.0,
                comparison_operator="lt",
                criticality="medium",
            ),
            ObservationThreshold(
                name="kelly_safety_blocks_threshold",
                description="Kelly安全拦截超过10次/天",
                threshold_value=10,
                comparison_operator="gt",
                criticality="medium",
            ),
            ObservationThreshold(
                name="api_response_time_threshold",
                description="API响应时间超过5秒",
                threshold_value=5000.0,
                comparison_operator="gt",
                criticality="low",
            ),
            ObservationThreshold(
                name="consecutive_failures",
                description="连续预测失败超过5次",
                threshold_value=5,
                comparison_operator="gt",
                criticality="high",
            ),
        ]

        # 回退策略配置
        self.rollback_strategies = {
            "normal": {
                "kelly_multiplier": 0.1,  # 0.1倍凯利（低风险）
                "max_daily_stake": 0.05,  # 日最大投注5%
                "min_confidence": 0.65,  # 最低置信度65%
            },
            "observation": {
                "kelly_multiplier": 0.0,  # 0倍凯利（不投注）
                "max_daily_stake": 0.0,  # 不投注
                "min_confidence": 0.60,  # 继续预测但记录
            },
            "suspended": {
                "kelly_multiplier": 0.0,
                "max_daily_stake": 0.0,
                "min_confidence": 0.0,
            },
            "emergency": {
                "kelly_multiplier": 0.0,
                "max_daily_stake": 0.0,
                "min_confidence": 0.0,
            },
        }

    async def initialize(self):
        """初始化数据库连接"""
        self.db_pool = DatabasePool()
        await self.db_pool.initialize()

        # 创建观察模式相关表
        await self._create_observation_tables()

    async def _create_observation_tables(self):
        """创建观察模式相关表"""
        async with self.db_pool.get_connection() as conn:
            # 观察模式事件表
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observation_mode_events (
                    event_id VARCHAR(36) PRIMARY KEY,
                    mode_before VARCHAR(20) NOT NULL,
                    mode_after VARCHAR(20) NOT NULL,
                    trigger_reason TEXT NOT NULL,
                    metrics JSONB,
                    duration_minutes INTEGER,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 观察模式阈值触发记录
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observation_threshold_triggers (
                    id SERIAL PRIMARY KEY,
                    threshold_name VARCHAR(100) NOT NULL,
                    current_value FLOAT NOT NULL,
                    threshold_value FLOAT NOT NULL,
                    deviation_percentage FLOAT,
                    criticality VARCHAR(20) NOT NULL,
                    action_taken VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 观察模式配置表
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observation_mode_config (
                    id SERIAL PRIMARY KEY,
                    mode VARCHAR(20) NOT NULL UNIQUE,
                    kelly_multiplier DECIMAL(3,2) NOT NULL,
                    max_daily_stake DECIMAL(3,2) NOT NULL,
                    min_confidence DECIMAL(3,2) NOT NULL,
                    auto_prediction BOOLEAN DEFAULT TRUE,
                    auto_betting BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 首周观察期报告表
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observation_weekly_reports (
                    id SERIAL PRIMARY KEY,
                    week_number INTEGER NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    successful_predictions INTEGER DEFAULT 0,
                    average_brier_score DECIMAL(5,4),
                    average_roi DECIMAL(5,2),
                    total_safety_blocks INTEGER DEFAULT 0,
                    observation_mode_hours DECIMAL(5,1),
                    risk_assessment VARCHAR(20),
                    recommendations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    async def check_observation_conditions(self) -> Dict[str, Any]:
        """检查观察模式触发条件"""
        logger.info("🔍 检查观察模式触发条件")

        trigger_results = []
        triggered_thresholds = []

        try:
            # 获取最新指标数据
            current_metrics = await self._collect_current_metrics()

            # 检查每个阈值
            for threshold in self.thresholds:
                if not threshold.enabled:
                    continue

                current_value = current_metrics.get(threshold.name, 0)
                threshold_value = threshold.threshold_value

                # 计算是否触发
                triggered = self._evaluate_threshold(
                    current_value, threshold_value, threshold.comparison_operator
                )

                result = {
                    "threshold_name": threshold.name,
                    "description": threshold.description,
                    "current_value": current_value,
                    "threshold_value": threshold_value,
                    "deviation": abs(current_value - threshold_value),
                    "deviation_percentage": self._calculate_deviation_percentage(
                        current_value, threshold_value
                    ),
                    "criticality": threshold.criticality,
                    "triggered": triggered,
                }

                trigger_results.append(result)

                if triggered:
                    triggered_thresholds.append(result)
                    logger.warning(
                        f"⚠️ 阈值触发: {threshold.description} "
                        f"(当前: {current_value}, 阈值: {threshold_value})"
                    )

                    # 记录阈值触发
                    await self._record_threshold_trigger(result)

            # 确定需要的观察模式
            required_mode = await self._determine_required_mode(
                triggered_thresholds, current_metrics
            )

            # 检查是否需要模式变更
            current_mode = await self._get_current_observation_mode()
            mode_change_needed = current_mode != required_mode

            result = {
                "current_mode": current_mode,
                "required_mode": required_mode,
                "mode_change_needed": mode_change_needed,
                "triggered_thresholds": triggered_thresholds,
                "all_thresholds": trigger_results,
                "current_metrics": current_metrics,
                "recommendation": self._generate_recommendation(
                    required_mode, triggered_thresholds
                ),
            }

            if mode_change_needed:
                await self._handle_mode_change(current_mode, required_mode, result)

            return result

        except Exception as e:
            logger.error(f"检查观察模式条件失败: {e}")
            return {
                "error": str(e),
                "current_mode": "unknown",
                "required_mode": "normal",
                "mode_change_needed": False,
                "triggered_thresholds": [],
                "recommendation": "检查失败，建议手动检查系统状态",
            }

    async def _collect_current_metrics(self) -> Dict[str, Any]:
        """收集当前指标"""
        try:
            async with self.db_pool.get_connection() as conn:
                metrics = {}

                # Brier Score相关
                brier_result = await conn.fetchrow(
                    """
                    SELECT AVG(brier_score) as avg_brier_score
                    FROM prediction_quality_metrics
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    AND brier_score IS NOT NULL
                """
                )
                metrics["brier_score"] = float(brier_result["avg_brier_score"] or 0.25)

                # 预测准确率
                accuracy_result = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN predicted_outcome = actual_outcome THEN 1 END) as correct
                    FROM matches_realtime
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    AND actual_outcome IS NOT NULL
                """
                )
                total = accuracy_result["total"]
                correct = accuracy_result["correct"]
                metrics["prediction_accuracy"] = (
                    (correct / total * 100) if total > 0 else 50.0
                )

                # ROI相关
                roi_result = await conn.fetchrow(
                    """
                    SELECT
                        COALESCE(SUM(stake_amount), 0) as total_staked,
                        COALESCE(SUM(return_amount), 0) as total_return
                    FROM matches_realtime
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND stake_amount > 0
                """
                )
                staked = float(roi_result["total_staked"])
                returned = float(roi_result["total_return"])
                metrics["roi_daily"] = (
                    ((returned - staked) / staked * 100) if staked > 0 else 0.0
                )

                # Kelly安全拦截
                blocks_result = await conn.fetchrow(
                    """
                    SELECT COUNT(*) as safety_blocks
                    FROM matches_realtime
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND safety_block = true
                """
                )
                metrics["kelly_safety_blocks"] = blocks_result["safety_blocks"]

                # API响应时间
                api_result = await conn.fetchrow(
                    """
                    SELECT AVG(response_time_ms) as avg_response_time
                    FROM api_performance_logs
                    WHERE created_at >= NOW() - INTERVAL '1 hour'
                """
                )
                metrics["api_response_time"] = float(
                    api_result["avg_response_time"] or 1000
                )

                # 连续失败次数
                failure_result = await conn.fetchrow(
                    """
                    WITH ranked_failures AS (
                        SELECT
                            created_at,
                            success,
                            ROW_NUMBER() OVER (ORDER BY created_at DESC) as rn
                        FROM prediction_logs
                        WHERE created_at >= NOW() - INTERVAL '1 hour'
                    )
                    SELECT COUNT(*) as consecutive_failures
                    FROM ranked_failures
                    WHERE rn <= 10 AND success = false
                    ORDER BY created_at DESC
                """
                )
                metrics["consecutive_failures"] = failure_result["consecutive_failures"]

                return metrics

        except Exception as e:
            logger.error(f"收集当前指标失败: {e}")
            return {}

    def _evaluate_threshold(
        self, current: float, threshold: float, operator: str
    ) -> bool:
        """评估阈值是否触发"""
        try:
            if operator == "gt":
                return current > threshold
            elif operator == "lt":
                return current < threshold
            elif operator == "eq":
                return abs(current - threshold) < 0.001
            elif operator == "gte":
                return current >= threshold
            elif operator == "lte":
                return current <= threshold
            else:
                return False
        except:
            return False

    def _calculate_deviation_percentage(
        self, current: float, threshold: float
    ) -> float:
        """计算偏差百分比"""
        try:
            if threshold == 0:
                return 0.0
            return abs(current - threshold) / abs(threshold) * 100
        except:
            return 0.0

    async def _determine_required_mode(
        self, triggered_thresholds: List[Dict], metrics: Dict[str, Any]
    ) -> ObservationMode:
        """确定需要的观察模式"""
        if not triggered_thresholds:
            return ObservationMode.NORMAL

        # 检查关键性级别
        critical_count = sum(
            1 for t in triggered_thresholds if t["criticality"] == "critical"
        )
        high_count = sum(1 for t in triggered_thresholds if t["criticality"] == "high")

        if critical_count > 0:
            return ObservationMode.SUSPENDED
        elif high_count >= 2:
            return ObservationMode.OBSERVATION
        elif high_count >= 1:
            # 检查是否需要进入观察模式
            for threshold in triggered_thresholds:
                if threshold["threshold_name"] == "brier_score_deviation":
                    return ObservationMode.OBSERVATION
                elif threshold["threshold_name"] == "prediction_accuracy_drop":
                    return ObservationMode.SUSPENDED
                elif threshold["threshold_name"] == "roi_loss_threshold":
                    return ObservationMode.OBSERVATION

        return ObservationMode.NORMAL

    async def _get_current_observation_mode(self) -> ObservationMode:
        """获取当前观察模式"""
        try:
            async with self.db_pool.get_connection() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT mode FROM observation_mode_config
                    ORDER BY updated_at DESC
                    LIMIT 1
                """
                )

                if result:
                    return ObservationMode(result["mode"])
                else:
                    # 插入默认配置
                    await conn.execute(
                        """
                        INSERT INTO observation_mode_config
                        (mode, kelly_multiplier, max_daily_stake, min_confidence)
                        VALUES ($1, $2, $3, $4)
                    """,
                        "normal",
                        0.10,
                        0.05,
                        0.60,
                    )

                    return ObservationMode.NORMAL

        except Exception as e:
            logger.error(f"获取当前观察模式失败: {e}")
            return ObservationMode.NORMAL

    def _generate_recommendation(
        self, required_mode: ObservationMode, triggered_thresholds: List[Dict]
    ) -> str:
        """生成建议"""
        if required_mode == ObservationMode.NORMAL:
            return "✅ 系统运行正常，无需特殊操作"

        elif required_mode == ObservationMode.OBSERVATION:
            return (
                "⚠️ 系统进入观察模式：仅进行预测，不执行投注。"
                f"触发原因: {', '.join([t['description'] for t in triggered_thresholds])}"
            )

        elif required_mode == ObservationMode.SUSPENDED:
            return (
                "🚨 系统暂停预测：已检测到严重性能问题。"
                f"触发原因: {', '.join([t['description'] for t in triggered_thresholds])}"
            )

        elif required_mode == ObservationMode.EMERGENCY:
            return "🆘 紧急模式：系统已停止所有操作，需要立即人工干预"

        return "未知状态，建议手动检查"

    async def _handle_mode_change(
        self,
        from_mode: ObservationMode,
        to_mode: ObservationMode,
        result: Dict[str, Any],
    ):
        """处理模式变更"""
        event_id = str(int(time.time() * 1000))

        event = ObservationEvent(
            event_id=event_id,
            timestamp=datetime.now().isoformat(),
            mode_before=from_mode,
            mode_after=to_mode,
            trigger_reason=result["recommendation"],
            metrics=result["current_metrics"],
        )

        # 记录事件
        await self._record_observation_event(event)

        # 更新配置
        await self._update_observation_config(to_mode)

        # 应用回退策略
        await self._apply_rollback_strategy(to_mode)

        # 发送通知
        await self._send_mode_change_notification(event, result)

        logger.critical(
            f"🔄 观察模式变更: {from_mode.value} → {to_mode.value}"
            f"原因: {event.trigger_reason}"
        )

    async def _record_observation_event(self, event: ObservationEvent):
        """记录观察模式事件"""
        try:
            async with self.db_pool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO observation_mode_events
                    (event_id, mode_before, mode_after, trigger_reason, metrics, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                    event.event_id,
                    event.mode_before.value,
                    event.mode_after.value,
                    event.trigger_reason,
                    json.dumps(event.metrics),
                    # created_at 使用默认值
                    # 其他字段使用默认值
                )

        except Exception as e:
            logger.error(f"记录观察模式事件失败: {e}")

    async def _record_threshold_trigger(self, threshold_result: Dict[str, Any]):
        """记录阈值触发"""
        try:
            async with self.db_pool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO observation_threshold_triggers
                    (threshold_name, current_value, threshold_value, deviation_percentage, criticality, action_taken)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    threshold_result["threshold_name"],
                    threshold_result["current_value"],
                    threshold_result["threshold_value"],
                    threshold_result["deviation_percentage"],
                    threshold_result["criticality"],
                    "threshold_triggered",
                )

        except Exception as e:
            logger.error(f"记录阈值触发失败: {e}")

    async def _update_observation_config(self, mode: ObservationMode):
        """更新观察模式配置"""
        try:
            strategy = self.rollback_strategies[mode.value]

            async with self.db_pool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO observation_mode_config
                    (mode, kelly_multiplier, max_daily_stake, min_confidence, auto_prediction, auto_betting)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (mode) DO UPDATE SET
                    kelly_multiplier = $2,
                    max_daily_stake = $3,
                    min_confidence = $4,
                    auto_prediction = $5,
                    auto_betting = $6,
                    updated_at = NOW()
                """,
                    mode.value,
                    strategy["kelly_multiplier"],
                    strategy["max_daily_stake"],
                    strategy["min_confidence"],
                    mode != ObservationMode.SUSPENDED,  # 暂停模式下仍预测
                    mode == ObservationMode.NORMAL,  # 只有正常模式投注
                )

        except Exception as e:
            logger.error(f"更新观察模式配置失败: {e}")

    async def _apply_rollback_strategy(self, mode: ObservationMode):
        """应用回退策略"""
        try:
            strategy = self.rollback_strategies[mode.value]

            # 这里可以调用相应的API来应用策略
            # 例如，通过HTTP请求更新配置
            import requests

            if mode != ObservationMode.NORMAL:
                # 通知应用更新配置
                response = requests.post(
                    "http://localhost:8000/api/v1/admin/observation-mode",
                    json={
                        "mode": mode.value,
                        "kelly_multiplier": strategy["kelly_multiplier"],
                        "max_daily_stake": strategy["max_daily_stake"],
                        "min_confidence": strategy["min_confidence"],
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    logger.info(f"✅ 回退策略已应用: {mode.value}")
                else:
                    logger.warning(f"⚠️ 回退策略应用失败: {response.status_code}")

        except Exception as e:
            logger.error(f"应用回退策略失败: {e}")

    async def _send_mode_change_notification(
        self, event: ObservationEvent, result: Dict[str, Any]
    ):
        """发送模式变更通知"""
        try:
            # 发送邮件通知
            await self._send_email_notification(event, result)

            # 发送Slack通知（如果配置了）
            await self._send_slack_notification(event, result)

        except Exception as e:
            logger.error(f"发送通知失败: {e}")

    async def _send_email_notification(
        self, event: ObservationEvent, result: Dict[str, Any]
    ):
        """发送邮件通知"""
        try:
            # 这里实现邮件发送逻辑
            # 需要配置SMTP服务器
            if not hasattr(self.settings, "smtp") or not self.settings.smtp.host:
                return

            msg = MimeMultipart()
            msg["From"] = self.settings.smtp.from_email
            msg["To"] = self.settings.smtp.to_email
            msg["Subject"] = f"🚨 观察模式变更通知: {event.mode_after.value}"

            body = f"""
观察模式已变更：

模式变更: {event.mode_before.value} → {event.mode_after.value}
触发时间: {event.timestamp}
触发原因: {event.trigger_reason}

当前指标:
{chr(10).join([f'- {k}: {v}' for k, v in result['current_metrics'].items()])}

请及时检查系统状态。

Football Prediction System
            """

            msg.attach(MimeText(body, "plain", "utf-8"))

            # 发送邮件
            server = smtplib.SMTP(self.settings.smtp.host, self.settings.smtp.port)
            server.starttls()
            server.login(self.settings.smtp.username, self.settings.smtp.password)
            server.send_message(msg)
            server.quit()

            logger.info("📧 邮件通知已发送")

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")

    async def _send_slack_notification(
        self, event: ObservationEvent, result: Dict[str, Any]
    ):
        """发送Slack通知"""
        try:
            # 这里实现Slack Webhook通知
            # 需要配置Slack Webhook URL
            if (
                not hasattr(self.settings, "slack")
                or not self.settings.slack.webhook_url
            ):
                return

            import requests

            payload = {
                "text": f"🚨 观察模式变更: {event.mode_after.value}",
                "attachments": [
                    {
                        "color": (
                            "danger"
                            if event.mode_after
                            in [ObservationMode.SUSPENDED, ObservationMode.EMERGENCY]
                            else "warning"
                        ),
                        "fields": [
                            {
                                "title": "模式变更",
                                "value": f"{event.mode_before.value} → {event.mode_after.value}",
                                "short": True,
                            },
                            {
                                "title": "触发时间",
                                "value": event.timestamp,
                                "short": True,
                            },
                            {
                                "title": "触发原因",
                                "value": event.trigger_reason,
                                "short": False,
                            },
                        ],
                    }
                ],
            }

            response = requests.post(
                self.settings.slack.webhook_url, json=payload, timeout=10
            )

            if response.status_code == 200:
                logger.info("💬 Slack通知已发送")
            else:
                logger.warning(f"Slack通知发送失败: {response.status_code}")

        except Exception as e:
            logger.error(f"发送Slack通知失败: {e}")

    async def generate_weekly_report(self, week_number: int = None) -> Dict[str, Any]:
        """生成首周观察报告"""
        if week_number is None:
            # 计算本周是第几周
            week_number = datetime.now().isocalendar()[1]

        logger.info(f"📊 生成第{week_number}周观察报告")

        try:
            async with self.db_pool.get_connection() as conn:
                # 获取本周日期范围
                start_date = datetime.now().date() - timedelta(
                    days=datetime.now().weekday()
                )
                end_date = start_date + timedelta(days=6)

                # 收集本周数据
                report_data = await self._collect_weekly_data(
                    conn, week_number, start_date, end_date
                )

                # 进行风险评估
                risk_assessment = await self._assess_weekly_risk(report_data, conn)

                # 生成建议
                recommendations = await self._generate_weekly_recommendations(
                    report_data, risk_assessment
                )

                # 保存报告
                await self._save_weekly_report(
                    report_data, risk_assessment, recommendations
                )

                return {
                    "week_number": week_number,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "report_data": report_data,
                    "risk_assessment": risk_assessment,
                    "recommendations": recommendations,
                    "generated_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"生成周报告失败: {e}")
            return {
                "error": str(e),
                "week_number": week_number,
                "generated_at": datetime.now().isoformat(),
            }

    async def _collect_weekly_data(
        self, conn, week_number: int, start_date, end_date
    ) -> Dict[str, Any]:
        """收集周数据"""
        # 预测统计
        prediction_result = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_predictions
            FROM matches_realtime
            WHERE DATE(created_at) BETWEEN $1 AND $2
        """,
            start_date,
            end_date,
        )

        # Brier Score统计
        brier_result = await conn.fetchrow(
            """
            SELECT AVG(brier_score) as avg_brier_score
            FROM prediction_quality_metrics
            WHERE created_at BETWEEN $1 AND $2::timestamp + INTERVAL '1 day'
            AND brier_score IS NOT NULL
        """,
            start_date,
            end_date,
        )

        # ROI统计
        roi_result = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(stake_amount), 0) as total_staked,
                COALESCE(SUM(return_amount), 0) as total_return
            FROM matches_realtime
            WHERE DATE(created_at) BETWEEN $1 AND $2
            AND stake_amount > 0
        """,
            start_date,
            end_date,
        )

        # 安全拦截统计
        safety_result = await conn.fetchrow(
            """
            SELECT
                COUNT(CASE WHEN safety_block = true THEN 1 END) as total_safety_blocks,
                COUNT(CASE WHEN manual_review = true THEN 1 END) as total_manual_reviews
            FROM matches_realtime
            WHERE DATE(created_at) BETWEEN $1 AND $2
        """,
            start_date,
            end_date,
        )

        # 观察模式时长统计
        observation_result = await conn.fetchrow(
            """
            SELECT
                SUM(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60) as total_observation_minutes
            FROM observation_mode_events
            WHERE DATE(created_at) BETWEEN $1 AND $2
            AND mode_after IN ('observation', 'suspended')
        """,
            start_date,
            end_date,
        )

        total_predictions = prediction_result["total_predictions"]
        successful_predictions = prediction_result["successful_predictions"]
        total_staked = float(roi_result["total_staked"])
        total_return = float(roi_result["total_return"])
        total_safety_blocks = safety_result["total_safety_blocks"]

        return {
            "total_predictions": total_predictions,
            "successful_predictions": successful_predictions,
            "prediction_accuracy": (
                (successful_predictions / total_predictions * 100)
                if total_predictions > 0
                else 0
            ),
            "average_brier_score": float(brier_result["avg_brier_score"] or 0.25),
            "total_staked": total_staked,
            "total_return": total_return,
            "roi_percentage": (
                ((total_return - total_staked) / total_staked * 100)
                if total_staked > 0
                else 0
            ),
            "total_safety_blocks": total_safety_blocks,
            "total_manual_reviews": safety_result["total_manual_reviews"],
            "observation_mode_hours": float(
                observation_result["total_observation_minutes"] or 0
            )
            / 60,
        }

    async def _assess_weekly_risk(self, report_data: Dict[str, Any], conn) -> str:
        """评估周风险等级"""
        risk_factors = []
        risk_score = 0

        # 预测准确率风险
        accuracy = report_data["prediction_accuracy"]
        if accuracy < 40:
            risk_factors.append("预测准确率极低")
            risk_score += 30
        elif accuracy < 50:
            risk_factors.append("预测准确率偏低")
            risk_score += 15

        # Brier Score风险
        brier_score = report_data["average_brier_score"]
        if brier_score > 0.35:
            risk_factors.append("Brier Score过高")
            risk_score += 20
        elif brier_score > 0.30:
            risk_factors.append("Brier Score偏高")
            risk_score += 10

        # ROI风险
        roi = report_data["roi_percentage"]
        if roi < -20:
            risk_factors.append("严重亏损")
            risk_score += 30
        elif roi < -10:
            risk_factors.append("轻微亏损")
            risk_score += 15

        # 安全拦截风险
        safety_blocks = report_data["total_safety_blocks"]
        if safety_blocks > 50:
            risk_factors.append("安全拦截频繁")
            risk_score += 20
        elif safety_blocks > 20:
            risk_factors.append("安全拦截较多")
            risk_score += 10

        # 观察模式时长风险
        observation_hours = report_data["observation_mode_hours"]
        if observation_hours > 24:  # 超过1天
            risk_factors.append("观察模式时间过长")
            risk_score += 15

        # 确定风险等级
        if risk_score >= 60:
            return "critical"
        elif risk_score >= 40:
            return "high"
        elif risk_score >= 20:
            return "medium"
        else:
            return "low"

    async def _generate_weekly_recommendations(
        self, report_data: Dict[str, Any], risk_assessment: str
    ) -> List[str]:
        """生成周建议"""
        recommendations = []

        # 基于风险等级的建议
        if risk_assessment == "critical":
            recommendations.append("🚨 立即暂停所有投注，进行全面系统检查")
            recommendations.append("🔍 检查模型性能，考虑重新训练")
            recommendations.append("📊 分析失败原因，调整策略参数")
        elif risk_assessment == "high":
            recommendations.append("⚠️ 建议进入观察模式，暂停自动投注")
            recommendations.append("📈 密切监控预测准确率")
            recommendations.append("💰 考虑降低投注比例")
        elif risk_assessment == "medium":
            recommendations.append("📝 继续观察，但保持谨慎")
            recommendations.append("📊 分析数据质量")
        else:
            recommendations.append("✅ 系统表现良好，可正常运营")
            recommendations.append("📈 继续监控关键指标")

        # 基于具体指标的建议
        if report_data["prediction_accuracy"] < 50:
            recommendations.append("🎯 建议检查特征工程和模型算法")

        if report_data["roi_percentage"] < 0:
            recommendations.append("💰 建议检查Kelly策略和赔率选择")

        if report_data["total_safety_blocks"] > 20:
            recommendations.append("🛡️ 建议调整安全系统阈值")

        if report_data["average_brier_score"] > 0.3:
            recommendations.append("📏 建议改进概率校准")

        return recommendations

    async def _save_weekly_report(
        self,
        report_data: Dict[str, Any],
        risk_assessment: str,
        recommendations: List[str],
    ):
        """保存周报告"""
        try:
            async with self.db_pool.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO observation_weekly_reports
                    (week_number, start_date, end_date, total_predictions, successful_predictions,
                     average_brier_score, average_roi, total_safety_blocks, observation_mode_hours,
                     risk_assessment, recommendations)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    report_data["week_number"],
                    report_data["start_date"],
                    report_data["end_date"],
                    report_data["total_predictions"],
                    report_data["successful_predictions"],
                    report_data["average_brier_score"],
                    report_data["roi_percentage"],
                    report_data["total_safety_blocks"],
                    report_data["observation_mode_hours"],
                    risk_assessment,
                    json.dumps(recommendations),
                )

        except Exception as e:
            logger.error(f"保存周报告失败: {e}")

    def print_observation_summary(self, result: Dict[str, Any]):
        """打印观察模式摘要"""
        print("\n" + "=" * 60)
        print("🔍 观察模式检查结果")
        print("=" * 60)
        print(f"当前模式: {result['current_mode']}")
        print(f"建议模式: {result['required_mode']}")
        print(f"模式变更: {'需要' if result['mode_change_needed'] else '无需'}")

        if result["triggered_thresholds"]:
            print(f"\n⚠️ 触发的阈值 ({len(result['triggered_thresholds'])} 个):")
            for threshold in result["triggered_thresholds"]:
                print(f"  • {threshold['description']}")
                print(f"    当前值: {threshold['current_value']:.2f}")
                print(f"    阈值: {threshold['threshold_value']:.2f}")
                print(f"    偏差: {threshold['deviation_percentage']:.1f}%")
                print(f"    关键性: {threshold['criticality']}")

        print(f"\n💡 建议: {result['recommendation']}")
        print("=" * 60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 9 首周观察期预案管理")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 检查命令
    check_parser = subparsers.add_parser("check", help="检查观察模式触发条件")

    # 启用观察模式
    enable_parser = subparsers.add_parser("enable", help="启用观察模式")
    enable_parser.add_argument(
        "--mode",
        choices=["normal", "observation", "suspended", "emergency"],
        default="observation",
        help="观察模式类型",
    )
    enable_parser.add_argument("--reason", default="手动启用", help="启用原因")

    # 禁用观察模式
    disable_parser = subparsers.add_parser("disable", help="恢复正常模式")
    disable_parser.add_argument("--reason", default="手动禁用", help="禁用原因")

    # 生成周报告
    report_parser = subparsers.add_parser("report", help="生成首周观察报告")
    report_parser.add_argument("--week", type=int, help="指定周数")

    args = parser.parse_args()

    manager = ObservationModeManager()
    await manager.initialize()

    try:
        if args.command == "check":
            # 检查观察模式条件
            result = await manager.check_observation_conditions()
            manager.print_observation_summary(result)

        elif args.command == "enable":
            # 启用观察模式
            mode = ObservationMode(args.mode)
            current_mode = await manager._get_current_observation_mode()

            event = ObservationEvent(
                event_id=str(int(time.time() * 1000)),
                timestamp=datetime.now().isoformat(),
                mode_before=current_mode,
                mode_after=mode,
                trigger_reason=f"手动启用: {args.reason}",
                metrics={},
            )

            await manager._record_observation_event(event)
            await manager._update_observation_config(mode)
            await manager._apply_rollback_strategy(mode)

            print(f"✅ 观察模式已启用: {mode.value}")
            print(f"原因: {args.reason}")

        elif args.command == "disable":
            # 禁用观察模式
            current_mode = await manager._get_current_observation_mode()

            event = ObservationEvent(
                event_id=str(int(time.time() * 1000)),
                timestamp=datetime.now().isoformat(),
                mode_before=current_mode,
                mode_after=ObservationMode.NORMAL,
                trigger_reason=f"手动禁用: {args.reason}",
                metrics={},
            )

            await manager._record_observation_event(event)
            await manager._update_observation_config(ObservationMode.NORMAL)
            await manager._apply_rollback_strategy(ObservationMode.NORMAL)

            print(f"✅ 观察模式已禁用，恢复到: {ObservationMode.NORMAL.value}")
            print(f"原因: {args.reason}")

        elif args.command == "report":
            # 生成周报告
            result = await manager.generate_weekly_report(args.week)

            if "error" not in result:
                print(f"\n📊 第{result['week_number']}周观察报告")
                print("=" * 50)
                print(f"报告期间: {result['start_date']} 至 {result['end_date']}")
                print(f"总预测场次: {result['report_data']['total_predictions']}")
                print(f"成功预测: {result['report_data']['successful_predictions']}")
                print(
                    f"预测准确率: {result['report_data']['prediction_accuracy']:.1f}%"
                )
                print(
                    f"平均Brier Score: {result['report_data']['average_brier_score']:.4f}"
                )
                print(f"ROI: {result['report_data']['roi_percentage']:.2f}%")
                print(f"安全拦截: {result['report_data']['total_safety_blocks']} 次")
                print(
                    f"观察模式时长: {result['report_data']['observation_mode_hours']:.1f}小时"
                )
                print(f"风险等级: {result['risk_assessment']}")

                print(f"\n💡 建议:")
                for rec in result["recommendations"]:
                    print(f"  • {rec}")
            else:
                print(f"❌ 报告生成失败: {result['error']}")

        else:
            parser.print_help()
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n👋 观察模式管理已停止")
        return 1
    except Exception as e:
        logger.error(f"❌ 观察模式管理失败: {e}")
        return 1
    finally:
        if manager.db_pool:
            await manager.db_pool.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
