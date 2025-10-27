"""
观察者系统API端点
Observer System API Endpoints

提供观察者系统的管理和监控接口。
Provides management and monitoring interfaces for the observer system.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from ..observers import get_observer_manager
from ..observers.base import ObservableEventType

# mypy: ignore-errors
# 类型检查已忽略 - 这些文件包含复杂的动态类型逻辑


router = APIRouter(prefix="/observers", tags=["观察者系统"])


class AlertRequest(BaseModel):
    """告警请求模型"""

    alert_type: str
    severity: str
    message: str
    source: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class MetricUpdateRequest(BaseModel):
    """指标更新请求模型"""

    metric_name: str
    metric_value: float
    metric_type: str = "gauge"


@router.get("/status", summary="获取观察者系统状态")
async def get_observer_status() -> Dict[str, Any]:
    """获取观察者系统的整体状态"""
    manager = get_observer_manager()
    return manager.get_system_status()


@router.get("/metrics", summary="获取所有指标")
async def get_all_metrics() -> Dict[str, Any]:
    """获取所有观察者收集的指标"""
    manager = get_observer_manager()
    return manager.get_all_metrics()


@router.get("/observers", summary="获取所有观察者")
async def get_observers() -> Dict[str, Any]:
    """获取所有观察者的信息"""
    manager = get_observer_manager()
    observers = {}

    for name, observer in manager._observers.items():
        stats = observer.get_stats()
        stats["observed_event_types"] = [
            et.value for et in observer.get_observed_event_types()
        ]
        observers[name] = stats

    return {
        "observers": observers,
        "total_count": len(observers),
    }


@router.get("/subjects", summary="获取所有被观察者")
async def get_subjects() -> Dict[str, Any]:
    """获取所有被观察者的信息"""
    manager = get_observer_manager()
    subjects = {}

    for name, subject in manager._subjects.items():
        stats = subject.get_stats()
        subjects[name] = stats

    return {
        "subjects": subjects,
        "total_count": len(subjects),
    }


@router.get("/alerts", summary="获取告警历史")
async def get_alerts(
    severity: Optional[str] = Query(None, description="告警严重性过滤"),
    hours: int = Query(24, ge=1, le=168, description="查询时间范围（小时）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
) -> Dict[str, Any]:
    """获取告警历史记录"""
    manager = get_observer_manager()
    alerting_observer = manager.get_alerting_observer()

    if not alerting_observer:
        raise HTTPException(status_code=404, detail="告警观察者未找到")

    since = datetime.utcnow() - timedelta(hours=hours)
    alerts = alerting_observer.get_alert_history(
        severity=severity, since=since, limit=limit
    )

    return {
        "alerts": alerts,
        "total_count": len(alerts),
        "filters": {
            "severity": severity,
            "since": since.isoformat(),
            "limit": limit,
        },
    }


@router.post("/alerts", summary="手动触发告警")
async def trigger_alert(
    request: AlertRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """手动触发一个告警"""
    manager = get_observer_manager()

    # 后台任务触发告警
    background_tasks.add_task(
        manager.trigger_alert,
        alert_type=request.alert_type,
        severity=request.severity,
        message=request.message,
        source=request.source,
        data=request.data,
    )

    return {"message": "告警已触发", "alert_type": request.alert_type}


@router.get("/alerts/rules", summary="获取告警规则")
async def get_alert_rules() -> Dict[str, Any]:
    """获取所有告警规则"""
    manager = get_observer_manager()
    alerting_observer = manager.get_alerting_observer()

    if not alerting_observer:
        raise HTTPException(status_code=404, detail="告警观察者未找到")

    return {
        "rules": alerting_observer.get_alert_rules(),
        "total_count": len(alerting_observer._alert_rules),
    }


@router.post("/metrics/update", summary="更新指标")
async def update_metric(
    request: MetricUpdateRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """手动更新一个指标值"""
    manager = get_observer_manager()
    system_subject = manager.get_system_metrics_subject()

    if not system_subject:
        raise HTTPException(status_code=404, detail="系统指标被观察者未找到")

    # 更新指标
    system_subject.set_metric(request.metric_name, request.metric_value)

    return {
        "message": "指标已更新",
        "metric_name": request.metric_name,
        "metric_value": request.metric_value,
    }


@router.get("/predictions", summary="获取预测统计")
async def get_prediction_metrics() -> Dict[str, Any]:
    """获取预测相关的统计信息"""
    manager = get_observer_manager()
    prediction_subject = manager.get_prediction_metrics_subject()

    if not prediction_subject:
        raise HTTPException(status_code=404, detail="预测指标被观察者未找到")

    return prediction_subject.get_prediction_metrics()


@router.post("/predictions/record", summary="记录预测事件")
async def record_prediction(
    strategy_name: str,
    response_time_ms: float,
    success: bool = True,
    confidence: Optional[float] = None,
    background_tasks: BackgroundTasks = None,
) -> Dict[str, str]:
    """记录一个预测事件"""
    manager = get_observer_manager()

    # 后台任务记录预测
    if background_tasks:
        background_tasks.add_task(
            manager.record_prediction,
            strategy_name=strategy_name,
            response_time_ms=response_time_ms,
            success=success,
            confidence=confidence,
        )
    else:
        await manager.record_prediction(
            strategy_name=strategy_name,
            response_time_ms=response_time_ms,
            success=success,
            confidence=confidence,
        )

    return {
        "message": "预测事件已记录",
        "strategy_name": strategy_name,
        "response_time_ms": response_time_ms,
    }


@router.get("/cache", summary="获取缓存统计")
async def get_cache_statistics() -> Dict[str, Any]:
    """获取缓存统计信息"""
    manager = get_observer_manager()
    cache_subject = manager.get_cache_subject()

    if not cache_subject:
        raise HTTPException(status_code=404, detail="缓存被观察者未找到")

    return cache_subject.get_cache_statistics()


@router.post("/cache/hit", summary="记录缓存命中")
async def record_cache_hit(
    cache_name: str, key: str, background_tasks: BackgroundTasks = None
) -> Dict[str, str]:
    """记录缓存命中事件"""
    manager = get_observer_manager()

    if background_tasks:
        background_tasks.add_task(
            manager.record_cache_hit,
            cache_name=cache_name,
            key=key,
        )
    else:
        await manager.record_cache_hit(cache_name, key)

    return {
        "message": "缓存命中已记录",
        "cache_name": cache_name,
        "key": key,
    }


@router.post("/cache/miss", summary="记录缓存未命中")
async def record_cache_miss(
    cache_name: str, key: str, background_tasks: BackgroundTasks = None
) -> Dict[str, str]:
    """记录缓存未命中事件"""
    manager = get_observer_manager()

    if background_tasks:
        background_tasks.add_task(
            manager.record_cache_miss,
            cache_name=cache_name,
            key=key,
        )
    else:
        await manager.record_cache_miss(cache_name, key)

    return {
        "message": "缓存未命中已记录",
        "cache_name": cache_name,
        "key": key,
    }


@router.get("/performance", summary="获取性能指标")
async def get_performance_metrics() -> Dict[str, Any]:
    """获取性能指标"""
    manager = get_observer_manager()
    performance_observer = manager._observers.get("performance")

    if not performance_observer:
        raise HTTPException(status_code=404, detail="性能观察者未找到")

    return performance_observer.get_performance_metrics()


@router.post("/system/collect", summary="触发系统指标收集")
async def trigger_system_metrics_collection(
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """手动触发系统指标收集"""
    manager = get_observer_manager()
    system_subject = manager.get_system_metrics_subject()

    if not system_subject:
        raise HTTPException(status_code=404, detail="系统指标被观察者未找到")

    # 后台任务收集指标
    background_tasks.add_task(system_subject.collect_metrics)

    return {"message": "系统指标收集已触发"}


@router.post("/system/check", summary="触发性能检查")
async def trigger_performance_check(
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """手动触发性能检查"""
    manager = get_observer_manager()
    prediction_subject = manager.get_prediction_metrics_subject()

    if not prediction_subject:
        raise HTTPException(status_code=404, detail="预测指标被观察者未找到")

    # 后台任务检查性能
    background_tasks.add_task(prediction_subject.check_performance_degradation)

    return {"message": "性能检查已触发"}


@router.get("/event-types", summary="获取所有事件类型")
async def get_event_types() -> List[str]:
    """获取所有可用的事件类型"""
    return [et.value for et in ObservableEventType]


@router.post("/observer/{observer_name}/enable", summary="启用观察者")
async def enable_observer(observer_name: str) -> Dict[str, str]:
    """启用指定的观察者"""
    manager = get_observer_manager()
    observer = manager.get_observer(observer_name)

    if not observer:
        raise HTTPException(status_code=404, detail=f"观察者 {observer_name} 未找到")

    observer.enable()
    return {"message": f"观察者 {observer_name} 已启用"}


@router.post("/observer/{observer_name}/disable", summary="禁用观察者")
async def disable_observer(observer_name: str) -> Dict[str, str]:
    """禁用指定的观察者"""
    manager = get_observer_manager()
    observer = manager.get_observer(observer_name)

    if not observer:
        raise HTTPException(status_code=404, detail=f"观察者 {observer_name} 未找到")

    observer.disable()
    return {"message": f"观察者 {observer_name} 已禁用"}


@router.post("/subject/{subject_name}/clear-history", summary="清空事件历史")
async def clear_subject_history(subject_name: str) -> Dict[str, str]:
    """清空指定被观察者的事件历史"""
    manager = get_observer_manager()
    subject = manager.get_subject(subject_name)

    if not subject:
        raise HTTPException(status_code=404, detail=f"被观察者 {subject_name} 未找到")

    subject.clear_history()
    return {"message": f"被观察者 {subject_name} 的事件历史已清空"}
