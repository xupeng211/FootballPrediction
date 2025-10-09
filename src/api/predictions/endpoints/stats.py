"""
统计相关端点
Statistics Endpoints

处理模型统计和性能相关的API端点。
"""




from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query

from src.api.dependencies import get_current_user, get_prediction_engine
from src.core.logging_system import get_logger
from src.models.common_models import     ModelStatsResponse,
    PredictionOverviewResponse,
    VerificationResponse,
)

logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


@router.get("/stats/model/{model_name}", response_model=ModelStatsResponse)
async def get_model_statistics(
    model_name: str = Path(..., description="模型名称"),
    days: int = Query(7, description="统计天数", ge=1, le=365),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取模型性能统计

    Args:
        model_name: 模型名称
        days: 统计天数
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        ModelStatsResponse: 模型统计信息
    """
    try:
        # 获取准确率
        accuracy_info = await engine.get_prediction_accuracy(model_name, days)
        _ = accuracy_info  # Mark as used for now

        # 获取详细统计
        detailed_stats = await engine.prediction_service.get_prediction_statistics(days)

        # 查找指定模型的统计
        model_stats = None
        for stat in detailed_stats.get("statistics", []):
            if stat["model_version"] == model_name:
                model_stats = stat
                break

        if not model_stats:
            raise HTTPException(
                status_code=404, detail=f"模型 {model_name} 没有统计数据"
            )

        return ModelStatsResponse(
            model_name=model_name,
            period_days=days,
            total_predictions=model_stats["total_predictions"],
            verified_predictions=model_stats["verified_predictions"],
            accuracy=model_stats["accuracy"],
            avg_confidence=model_stats["avg_confidence"],
            predictions_by_result=model_stats["predictions_by_result"],
            last_updated=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型 {model_name} 统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型统计失败")


@router.get("/stats/overview", response_model=PredictionOverviewResponse)
async def get_prediction_overview(
    days: int = Query(30, description="统计天数", ge=1, le=365),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取预测概览统计

    Args:
        days: 统计天数
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        PredictionOverviewResponse: 概览统计信息
    """
    try:
        # 获取引擎性能统计
        engine_stats = engine.get_performance_stats()

        # 获取所有模型统计
        detailed_stats = await engine.prediction_service.get_prediction_statistics(days)

        # 计算总体统计
        total_predictions = sum(
            s["total_predictions"] for s in detailed_stats["statistics"]
        )
        total_verified = sum(
            s["verified_predictions"] for s in detailed_stats["statistics"]
        )
        total_correct = sum(
            s["correct_predictions"] for s in detailed_stats["statistics"]
        )

        overall_accuracy = (
            total_correct / total_verified if total_verified > 0 else None
        )

        return PredictionOverviewResponse(
            period_days=days,
            engine_performance=engine_stats,
            overall_stats={
                "total_predictions": total_predictions,
                "verified_predictions": total_verified,
                "correct_predictions": total_correct,
                "overall_accuracy": overall_accuracy,
            },
            models=detailed_stats["statistics"],
            last_updated=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"获取预测概览失败: {e}")
        raise HTTPException(status_code=500, detail="获取预测概览失败")


@router.post("/verify/{match_id}", response_model=VerificationResponse)
async def verify_match_prediction(
    match_id: int = Path(..., description="比赛ID", gt=0),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    验证比赛预测结果

    Args:
        match_id: 比赛ID
        background_tasks: 后台任务
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        VerificationResponse: 验证结果
    """
    try:
        logger.info(f"用户 {current_user.get('id')} 请求验证比赛 {match_id} 预测")

        # 执行验证
        stats = await engine.verify_predictions([match_id])

        # 记录验证日志（后台任务）
        background_tasks.add_task(
            _log_verification,
            user_id=current_user.get("id"),
            match_id=match_id,
            stats=stats,
        )

        return VerificationResponse(
            match_id=match_id,
            verified=stats["verified"] > 0,
            correct=stats["correct"],
            accuracy=stats["accuracy"],
            message="验证完成" if stats["verified"] > 0 else "无可验证的预测",
        )

    except Exception as e:
        logger.error(f"验证比赛 {match_id} 预测失败: {e}")
        raise HTTPException(status_code=500, detail="验证预测失败")


async def _log_verification(
    user_id: int,
    match_id: int,
    stats: Dict[str, Any],
):
    """记录验证日志"""
    logger.info(
        f"用户 {user_id} 验证比赛 {match_id}: "
        f"验证={stats['verified']}, "
        f"正确={stats['correct']}, "
        f"准确率={stats['accuracy']:.2%}"
    )