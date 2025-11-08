"""
告警系统API路由
Alert System API Routes

提供告警管理的REST API接口。
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .alert_system import (
    Alert,
    AlertLevel,
    AlertRule,
    AlertStatus,
    NotificationChannel,
    alert_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

# ============================================================================
# Pydantic模型
# ============================================================================


class AlertRuleCreate(BaseModel):
    """创建告警规则请求"""

    name: str = Field(..., description="规则名称")
    description: str = Field(..., description="规则描述")
    condition: str = Field(..., description="条件表达式")
    level: AlertLevel = Field(..., description="告警级别")
    enabled: bool = Field(True, description="是否启用")
    cooldown: int = Field(300, description="冷却时间（秒）")
    labels: dict[str, str] = Field(default_factory=dict, description="标签")
    annotations: dict[str, str] = Field(default_factory=dict, description="注解")


class AlertRuleResponse(BaseModel):
    """告警规则响应"""

    id: str
    name: str
    description: str
    condition: str
    level: AlertLevel
    enabled: bool
    cooldown: int
    labels: dict[str, str]
    annotations: dict[str, str]
    last_triggered: datetime | None = None
    trigger_count: int = 0


class NotificationChannelCreate(BaseModel):
    """创建通知渠道请求"""

    name: str = Field(..., description="渠道名称")
    type: str = Field(..., description="渠道类型")
    config: dict[str, str] = Field(..., description="渠道配置")
    enabled: bool = Field(True, description="是否启用")
    filters: dict[str, str] = Field(default_factory=dict, description="过滤条件")


class NotificationChannelResponse(BaseModel):
    """通知渠道响应"""

    id: str
    name: str
    type: str
    config: dict[str, str]
    enabled: bool
    filters: dict[str, str]


class AlertResponse(BaseModel):
    """告警响应"""

    id: str
    title: str
    description: str
    level: AlertLevel
    status: AlertStatus
    source: str
    timestamp: datetime
    metadata: dict[str, str]
    labels: dict[str, str]
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class AlertAcknowledge(BaseModel):
    """告警确认请求"""

    acknowledged_by: str = Field(..., description="确认人")


class AlertResolve(BaseModel):
    """告警解决请求"""

    resolved_by: str = Field(..., description="解决人")


# ============================================================================
# 告警规则管理
# ============================================================================


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(rule_data: AlertRuleCreate):
    """创建告警规则"""
    try:
        import uuid

        rule_id = f"rule_{uuid.uuid4().hex[:8]}"

        rule = AlertRule(
            id=rule_id,
            name=rule_data.name,
            description=rule_data.description,
            condition=rule_data.condition,
            level=rule_data.level,
            enabled=rule_data.enabled,
            cooldown=rule_data.cooldown,
            labels=rule_data.labels,
            annotations=rule_data.annotations,
        )

        await alert_manager.add_rule(rule)

        return AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            condition=rule.condition,
            level=rule.level,
            enabled=rule.enabled,
            cooldown=rule.cooldown,
            labels=rule.labels,
            annotations=rule.annotations,
            last_triggered=rule.last_triggered,
            trigger_count=rule.trigger_count,
        )

    except Exception as e:
        logger.error(f"创建告警规则失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"创建告警规则失败: {str(e)}"
        ) from e


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules():
    """获取告警规则列表"""
    try:
        rules = []
        for rule in alert_manager.rules.values():
            rules.append(
                AlertRuleResponse(
                    id=rule.id,
                    name=rule.name,
                    description=rule.description,
                    condition=rule.condition,
                    level=rule.level,
                    enabled=rule.enabled,
                    cooldown=rule.cooldown,
                    labels=rule.labels,
                    annotations=rule.annotations,
                    last_triggered=rule.last_triggered,
                    trigger_count=rule.trigger_count,
                )
            )
        return rules

    except Exception as e:
        logger.error(f"获取告警规则列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取告警规则列表失败: {str(e)}"
        ) from e


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(rule_id: str):
    """获取告警规则详情"""
    try:
        rule = alert_manager.rules.get(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        return AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            condition=rule.condition,
            level=rule.level,
            enabled=rule.enabled,
            cooldown=rule.cooldown,
            labels=rule.labels,
            annotations=rule.annotations,
            last_triggered=rule.last_triggered,
            trigger_count=rule.trigger_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警规则详情失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取告警规则详情失败: {str(e)}"
        ) from e


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: str, rule_data: AlertRuleCreate):
    """更新告警规则"""
    try:
        if rule_id not in alert_manager.rules:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        rule = AlertRule(
            id=rule_id,
            name=rule_data.name,
            description=rule_data.description,
            condition=rule_data.condition,
            level=rule_data.level,
            enabled=rule_data.enabled,
            cooldown=rule_data.cooldown,
            labels=rule_data.labels,
            annotations=rule_data.annotations,
            # 保留原有触发信息
            last_triggered=alert_manager.rules[rule_id].last_triggered,
            trigger_count=alert_manager.rules[rule_id].trigger_count,
        )

        await alert_manager.remove_rule(rule_id)
        await alert_manager.add_rule(rule)

        return AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            condition=rule.condition,
            level=rule.level,
            enabled=rule.enabled,
            cooldown=rule.cooldown,
            labels=rule.labels,
            annotations=rule.annotations,
            last_triggered=rule.last_triggered,
            trigger_count=rule.trigger_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"更新告警规则失败: {str(e)}"
        ) from e


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """删除告警规则"""
    try:
        if rule_id not in alert_manager.rules:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        await alert_manager.remove_rule(rule_id)
        return {"message": "告警规则已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警规则失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"删除告警规则失败: {str(e)}"
        ) from e


# ============================================================================
# 通知渠道管理
# ============================================================================


@router.post("/channels", response_model=NotificationChannelResponse)
async def create_notification_channel(channel_data: NotificationChannelCreate):
    """创建通知渠道"""
    try:
        import uuid

        channel_id = f"channel_{uuid.uuid4().hex[:8]}"

        channel = NotificationChannel(
            id=channel_id,
            name=channel_data.name,
            type=channel_data.type,
            config=channel_data.config,
            enabled=channel_data.enabled,
            filters=channel_data.filters,
        )

        await alert_manager.add_channel(channel)

        return NotificationChannelResponse(
            id=channel.id,
            name=channel.name,
            type=channel.type,
            config=channel.config,
            enabled=channel.enabled,
            filters=channel.filters,
        )

    except Exception as e:
        logger.error(f"创建通知渠道失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"创建通知渠道失败: {str(e)}"
        ) from e


@router.get("/channels", response_model=list[NotificationChannelResponse])
async def list_notification_channels():
    """获取通知渠道列表"""
    try:
        channels = []
        for channel in alert_manager.channels.values():
            channels.append(
                NotificationChannelResponse(
                    id=channel.id,
                    name=channel.name,
                    type=channel.type,
                    config=channel.config,
                    enabled=channel.enabled,
                    filters=channel.filters,
                )
            )
        return channels

    except Exception as e:
        logger.error(f"获取通知渠道列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取通知渠道列表失败: {str(e)}"
        ) from e


@router.delete("/channels/{channel_id}")
async def delete_notification_channel(channel_id: str):
    """删除通知渠道"""
    try:
        if channel_id not in alert_manager.channels:
            raise HTTPException(status_code=404, detail="通知渠道不存在")

        await alert_manager.remove_channel(channel_id)
        return {"message": "通知渠道已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除通知渠道失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"删除通知渠道失败: {str(e)}"
        ) from e


# ============================================================================
# 告警管理
# ============================================================================


@router.get("/active", response_model=list[AlertResponse])
async def list_active_alerts():
    """获取活跃告警列表"""
    try:
        alerts = []
        for alert in alert_manager.get_active_alerts():
            alerts.append(
                AlertResponse(
                    id=alert.id,
                    title=alert.title,
                    description=alert.description,
                    level=alert.level,
                    status=alert.status,
                    source=alert.source,
                    timestamp=alert.timestamp,
                    metadata=alert.metadata,
                    labels=alert.labels,
                    acknowledged_by=alert.acknowledged_by,
                    acknowledged_at=alert.acknowledged_at,
                    resolved_at=alert.resolved_at,
                    resolved_by=alert.resolved_by,
                )
            )
        return alerts

    except Exception as e:
        logger.error(f"获取活跃告警列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取活跃告警列表失败: {str(e)}"
        ) from e


@router.get("/history", response_model=list[AlertResponse])
async def get_alert_history(
    hours: int = Query(24, ge=1, le=168, description="历史时间范围（小时）"),
):
    """获取告警历史"""
    try:
        alerts = []
        for alert in alert_manager.get_alert_history(hours):
            alerts.append(
                AlertResponse(
                    id=alert.id,
                    title=alert.title,
                    description=alert.description,
                    level=alert.level,
                    status=alert.status,
                    source=alert.source,
                    timestamp=alert.timestamp,
                    metadata=alert.metadata,
                    labels=alert.labels,
                    acknowledged_by=alert.acknowledged_by,
                    acknowledged_at=alert.acknowledged_at,
                    resolved_at=alert.resolved_at,
                    resolved_by=alert.resolved_by,
                )
            )
        return alerts

    except Exception as e:
        logger.error(f"获取告警历史失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取告警历史失败: {str(e)}"
        ) from e


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, ack_data: AlertAcknowledge):
    """确认告警"""
    try:
        success = await alert_manager.acknowledge_alert(
            alert_id, ack_data.acknowledged_by
        )
        if not success:
            raise HTTPException(status_code=404, detail="告警不存在或已解决")

        return {"message": "告警已确认"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认告警失败: {e}")
        raise HTTPException(status_code=500, detail=f"确认告警失败: {str(e)}") from e


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolve_data: AlertResolve):
    """解决告警"""
    try:
        success = await alert_manager.resolve_alert(alert_id, resolve_data.resolved_by)
        if not success:
            raise HTTPException(status_code=404, detail="告警不存在")

        return {"message": "告警已解决"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决告警失败: {e}")
        raise HTTPException(status_code=500, detail=f"解决告警失败: {str(e)}") from e


# ============================================================================
# 统计和监控
# ============================================================================


@router.get("/statistics")
async def get_alert_statistics():
    """获取告警统计信息"""
    try:
        stats = alert_manager.get_alert_statistics()
        return {"status": "success", "data": stats}

    except Exception as e:
        logger.error(f"获取告警统计失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取告警统计失败: {str(e)}"
        ) from e


@router.post("/test")
async def test_alert_system():
    """测试告警系统"""
    try:
        import uuid

        # 创建测试告警
        test_alert = Alert(
            id=f"test_{uuid.uuid4().hex[:8]}",
            title="测试告警",
            description="这是一个测试告警，用于验证告警系统功能",
            level=AlertLevel.INFO,
            status=AlertStatus.ACTIVE,
            source="test_system",
            timestamp=datetime.now(),
            labels={"test": "true"},
            metadata={"test": True},
        )

        # 添加到活跃告警
        alert_manager.active_alerts[test_alert.id] = test_alert
        alert_manager.alert_history.append(test_alert)

        # 发送通知
        await alert_manager._send_notifications(test_alert)

        return {
            "status": "success",
            "message": "测试告警已创建并发送",
            "alert_id": test_alert.id,
        }

    except Exception as e:
        logger.error(f"测试告警系统失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"测试告警系统失败: {str(e)}"
        ) from e


# ============================================================================
# 预设配置
# ============================================================================


@router.post("/setup-default-rules")
async def setup_default_rules():
    """设置默认告警规则"""
    try:
        default_rules = [
            AlertRule(
                id="default_response_time",
                name="响应时间过高",
                description="API平均响应时间超过阈值",
                condition="metrics.get('system', {}).get('avg_response_time', 0) > 1.0",
                level=AlertLevel.WARNING,
                cooldown=300,
                labels={"component": "api", "metric": "response_time"},
            ),
            AlertRule(
                id="default_error_rate",
                name="错误率过高",
                description="API错误率超过阈值",
                condition="metrics.get('system', {}).get('error_rate', 0) > 5.0",
                level=AlertLevel.ERROR,
                cooldown=600,
                labels={"component": "api", "metric": "error_rate"},
            ),
            AlertRule(
                id="default_cpu_usage",
                name="CPU使用率过高",
                description="系统CPU使用率超过阈值",
                condition="metrics.get('system_info', {}).get('cpu_percent', 0) > 80.0",
                level=AlertLevel.WARNING,
                cooldown=300,
                labels={"component": "system", "metric": "cpu"},
            ),
            AlertRule(
                id="default_memory_usage",
                name="内存使用率过高",
                description="系统内存使用率超过阈值",
                condition="metrics.get('system_info', {}).get('memory_percent', 0) > 85.0",
                level=AlertLevel.WARNING,
                cooldown=300,
                labels={"component": "system", "metric": "memory"},
            ),
            AlertRule(
                id="default_cache_hit_rate",
                name="缓存命中率过低",
                description="Redis缓存命中率低于阈值",
                condition="metrics.get('cache', {}).get('hit_rate', 100) < 70.0",
                level=AlertLevel.WARNING,
                cooldown=600,
                labels={"component": "cache", "metric": "hit_rate"},
            ),
        ]

        # 添加默认规则
        for rule in default_rules:
            await alert_manager.add_rule(rule)

        return {
            "status": "success",
            "message": f"已添加 {len(default_rules)} 个默认告警规则",
            "rules": [rule.id for rule in default_rules],
        }

    except Exception as e:
        logger.error(f"设置默认告警规则失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"设置默认告警规则失败: {str(e)}"
        ) from e


def setup_alert_routes(app):
    """设置告警路由"""
    app.include_router(router)
    logger.info("告警路由已注册")
