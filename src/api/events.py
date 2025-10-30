import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from requests.exceptions import HTTPError


from ..core.event_application import get_event_application
from ..events import get_event_bus
from ..events.handlers import AnalyticsEventHandler, MetricsEventHandler


# 获取各处理器的指标

# 添加指标收集器的数据

# 添加分析处理器的数据


# 获取特定事件的订阅者
# 获取所有事件的订阅者信息


# 获取指标收集器数据

# 获取分析数据

# 添加系统统计


# 过滤指定天数的数据


# 计算总计


# 按预测数量排序

# 返回前N个用户


# 辅助函数
"""
事件系统API端点
Event System API Endpoints
提供事件系统的管理和监控接口.
Provides management and monitoring interfaces for the event system.
"""
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["事件系统"])


@router.get("/health", summary="事件系统健康检查")
async def event_health_check() -> Dict[str, Any]:
    """检查事件系统的健康状态"""
    app = get_event_application()
    return await app.health_check()


@router.get("/stats", summary="获取事件统计")
async def get_event_statistics() -> Dict[str, Any]:
    """获取事件系统统计信息"""
    bus = get_event_bus()
    stats = bus.get_stats()
    detailed_stats = stats.copy()
    metrics_handler = _find_handler(MetricsEventHandler)
    if metrics_handler:
        detailed_stats["metrics"] = metrics_handler.get_metrics()
    analytics_handler = _find_handler(AnalyticsEventHandler)
    if analytics_handler:
        detailed_stats["analytics"] = analytics_handler.get_analytics_data()
    return detailed_stats


@router.get("/types", summary="获取所有事件类型")
async def get_event_types() -> List[str]:
    """获取所有已注册的事件类型"""
    bus = get_event_bus()
    return bus.get_all_event_types()


@router.get("/subscribers", summary="获取订阅者信息")
async def get_subscribers_info(
    event_type: Optional[str] = Query(None, description="特定事件类型"),
) -> Dict[str, Any]:
    """获取事件订阅者信息"""
    bus = get_event_bus()
    if event_type:
        count = bus.get_subscribers_count(event_type)
        return {
            "event_type": event_type,
            "subscribers_count": count,
        }
    else:
        all_types = bus.get_all_event_types()
        subscriber_info = {}
        for et in all_types:
            subscriber_info[et] = bus.get_subscribers_count(et)
        return {
            "total_event_types": len(all_types),
            "subscribers": subscriber_info,
        }


@router.post("/restart", summary="重启事件系统")
async def restart_event_system() -> Dict[str, str]:
    """重启事件系统（谨慎使用）"""
    try:
        app = get_event_application()
        await app.shutdown()
        await app.initialize()
        return {"message": "事件系统已成功重启"}
    except (ValueError, KeyError, AttributeError, HTTPError) as e:
        raise HTTPException(status_code=500, detail=f"重启失败: {str(e)}")


@router.get("/metrics", summary="获取详细指标")
async def get_detailed_metrics() -> Dict[str, Any]:
    """获取事件系统的详细指标"""
    metrics = {}
    metrics_handler = _find_handler(MetricsEventHandler)
    if metrics_handler:
        metrics["event_counts"] = metrics_handler.get_metrics().get("event_counts", {})
        metrics["total_events"] = metrics_handler.get_metrics().get(
            "events_processed", 0
        )
        metrics["last_event_time"] = metrics_handler.get_metrics().get(
            "last_event_time"
        )
    analytics_handler = _find_handler(AnalyticsEventHandler)
    if analytics_handler:
        analytics_data = analytics_handler.get_analytics_data()
        metrics["daily_predictions"] = analytics_data.get("daily_predictions", {})
        metrics["user_activity"] = analytics_data.get("user_activity", {})
        metrics["match_predictions"] = analytics_data.get("match_predictions", {})
    bus = get_event_bus()
    metrics["system_stats"] = bus.get_stats()
    return metrics


@router.get("/predictions/recent", summary="获取最近的预测统计")
async def get_recent_prediction_stats(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
) -> Dict[str, Any]:
    """获取最近的预测统计信息"""
    analytics_handler = _find_handler(AnalyticsEventHandler)
    if not analytics_handler:
        raise HTTPException(status_code=404, detail="分析处理器未找到")
    analytics_data = analytics_handler.get_analytics_data()
    daily_predictions = analytics_data.get("daily_predictions", {})
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()
    recent_stats = {}
    for date_str, count in daily_predictions.items():
        try:
            date = datetime.fromisoformat(date_str).date()
            if date >= cutoff_date:
                recent_stats[date_str] = count
        except (ValueError, KeyError, AttributeError, HTTPError) as e:
            logger.error(f"解析日期时出错: {e}")
            continue
    total_predictions = sum(recent_stats.values())
    return {
        "days": days,
        "total_predictions": total_predictions,
        "daily_breakdown": recent_stats,
        "average_per_day": total_predictions / days if days > 0 else 0,
    }


@router.get("/users/activity", summary="获取用户活动统计")
async def get_user_activity_stats(
    limit: int = Query(10, ge=1, le=100, description="返回用户数量限制"),
) -> Dict[str, Any]:
    """获取用户活动统计"""
    analytics_handler = _find_handler(AnalyticsEventHandler)
    if not analytics_handler:
        raise HTTPException(status_code=404, detail="分析处理器未找到")
    analytics_data = analytics_handler.get_analytics_data()
    user_activity = analytics_data.get("user_activity", {})
    sorted_users = sorted(
        user_activity.items(),
        key=lambda x: x[1].get("predictions_count", 0),
        reverse=True,
    )
    top_users = sorted_users[:limit]
    return {
        "total_active_users": len(user_activity),
        "top_users": [
            {
                "user_id": user_id,
                "predictions_count": data.get("predictions_count", 0),
                "last_prediction": data.get("last_prediction"),
            }
            for user_id, data in top_users
        ],
    }


def _find_handler(handler_type):
    """函数文档字符串"""
    pass  # 添加pass语句
    """查找特定类型的处理器"""
    bus = get_event_bus()
    for handlers in bus._subscribers.values():
        for handler in handlers:
            if isinstance(handler, handler_type):
                return handler
    return None
