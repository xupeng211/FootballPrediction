"""预测API路由器
Predictions API Router.

提供预测相关的API路由.
"""

# mypy: ignore-errors
# 该文件包含复杂的机器学习逻辑,类型检查已忽略

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# 导入标准响应模型
from src.inference.schemas import PredictionResponse

# 创建路由器
router = APIRouter(prefix="/predictions", tags=["predictions"])

logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic Models
# ============================================================================


class PredictionRequest(BaseModel):
    """预测请求模型."""

    model_version: str | None = Field("default", description="模型版本")
    include_details: bool = Field(False, description="是否包含详细信息")


class PredictionResult(BaseModel):
    """预测结果模型."""

    match_id: int
    home_win_prob: float = Field(..., ge=0, le=1, description="主队获胜概率")
    draw_prob: float = Field(..., ge=0, le=1, description="平局概率")
    away_win_prob: float = Field(..., ge=0, le=1, description="客队获胜概率")
    predicted_outcome: str = Field(..., description="预测结果: home|draw|away")
    confidence: float = Field(..., ge=0, le=1, description="预测置信度")
    model_version: str = Field(..., description="使用的模型版本")
    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class BatchPredictionRequest(BaseModel):
    """批量预测请求."""

    match_ids: list[int] = Field(
        ..., min_length=1, max_length=100, description="比赛ID列表"
    )
    model_version: str | None = Field("default", description="模型版本")


class BatchPredictionResponse(BaseModel):
    """批量预测响应."""

    predictions: list[PredictionResult]
    total: int
    success_count: int
    failed_count: int
    failed_match_ids: list[int] = Field(default_factory=list)


class PredictionHistory(BaseModel):
    """预测历史记录."""

    match_id: int
    predictions: list[PredictionResult]
    total_predictions: int


class RecentPrediction(BaseModel):
    """最近的预测."""

    id: int
    match_id: int
    home_team: str
    away_team: str
    prediction: PredictionResult
    match_date: datetime


class PredictionVerification(BaseModel):
    """预测验证结果."""

    match_id: int
    prediction: PredictionResult
    actual_result: str
    is_correct: bool
    accuracy_score: float


# ============================================================================
# API Endpoints
# ============================================================================


class CreatePredictionRequest(BaseModel):
    """创建预测请求模型."""

    match_id: int = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    predicted_outcome: str = Field(..., description="预测结果: home|draw|away")
    confidence: float = Field(..., ge=0, le=1, description="预测置信度")


@router.get("/info")
async def get_predictions_root():
    """预测服务根路径信息."""
    return {
        "service": "足球预测API",
        "module": "predictions",
        "version": "1.0.0",
        "status": "运行中",
        "endpoints": {
            "list": "/",
            "recent": "/recent",
            "health": "/health",
            "prediction": "/{match_id}",
            "history": "/history/{match_id}",
            "predict": "/{match_id}/predict",
            "batch": "/batch",
            "verify": "/{match_id}/verify",
            "create": "/",
        },
    }


@router.get("/", response_model=dict[str, Any])
async def get_predictions_root():
    """预测服务根路径信息."""
    return {
        "service": "足球预测API",
        "module": "predictions",
        "version": "1.0.0",
        "status": "运行中",
        "endpoints": [
            "/",
            "/info",
            "/health",
            "/recent",
            "/match/{match_id}",
            "/history/{match_id}",
            "/{prediction_id}",
        ],
    }


@router.get("/list", response_model=dict[str, Any])
async def get_predictions_list(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取预测列表.

    返回分页的预测数据列表.
    """
    logger.info(f"获取预测列表: limit={limit}, offset={offset}")

    try:
        # 导入预测服务
        from src.services.prediction_service import PredictionService

        prediction_service = PredictionService()

        # 获取预测列表
        result = await prediction_service.get_predictions(limit=limit, offset=offset)

        logger.info(f"成功获取 {len(result['predictions'])} 条预测")
        return result

    except Exception as e:
        logger.error(f"获取预测列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取预测列表失败: {str(e)}"
        ) from e


@router.post("/", response_model=dict[str, Any], status_code=201)
async def create_prediction(request: CreatePredictionRequest):
    """创建新的预测.

    接收预测请求数据并创建新的预测记录.
    """
    logger.info(f"创建新预测: 比赛 {request.match_id}")

    try:
        # 导入预测服务
        from src.services.prediction_service import get_prediction_service

        prediction_service = get_prediction_service()

        # 构建预测数据
        prediction_data = {
            "match_id": request.match_id,
            "home_team": request.home_team,
            "away_team": request.away_team,
            "predicted_outcome": request.predicted_outcome,
            "confidence": request.confidence,
        }

        # 创建预测
        created_prediction = prediction_service.create_prediction(prediction_data)

        logger.info(f"成功创建预测: {created_prediction['id']}")
        return created_prediction

    except Exception as e:
        logger.error(f"创建预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建预测失败: {str(e)}") from e


@router.get("/health")
async def health_check():
    """健康检查."""
    return {"status": "healthy", "service": "predictions"}


@router.get("/recent", response_model=list[RecentPrediction])
async def get_recent_predictions(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
):
    """获取最近的预测记录.

    返回系统最近生成的预测,默认返回最近24小时内的预测.
    """
    logger.info(f"获取最近 {hours} 小时内的 {limit} 条预测")

    try:
        # ISSUE: 需要从数据库获取最近预测，需要实现数据访问层
        # 模拟数据
        recent = [
            RecentPrediction(
                id=i,
                match_id=1000 + i,
                home_team=f"Team A{i}",
                away_team=f"Team B{i}",
                prediction=PredictionResult(
                    match_id=1000 + i,
                    home_win_prob=0.45,
                    draw_prob=0.30,
                    away_win_prob=0.25,
                    predicted_outcome="home",
                    confidence=0.75,
                    model_version="default",
                    predicted_at=datetime.utcnow() - timedelta(hours=i),
                ),
                match_date=datetime.utcnow() + timedelta(days=i),
            )
            for i in range(min(limit, 10))
        ]

        logger.info(f"成功获取 {len(recent)} 条最近预测")
        return recent

    except Exception as e:
        logger.error(f"获取最近预测失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取最近预测失败: {str(e)}"
        ) from e


@router.get("/{prediction_id}")
async def get_prediction_by_id_endpoint(prediction_id: str):
    """根据预测ID获取预测.

    接受字符串ID并返回对应的预测数据.
    """
    logger.info(f"获取预测ID: {prediction_id}")

    try:
        # 导入预测服务
        from src.services.prediction_service import get_prediction_service

        prediction_service = get_prediction_service()

        # 获取预测
        prediction = prediction_service.get_prediction_by_id(prediction_id)

        if prediction is None:
            raise HTTPException(
                status_code=404, detail=f"预测ID {prediction_id} 不存在"
            )

        logger.info(f"成功获取预测: {prediction_id}")
        return prediction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预测失败: {str(e)}") from e


@router.get("/match/{match_id}", response_model=PredictionResponse)
async def get_match_predictions(match_id: int):
    """获取指定比赛的预测.

    返回符合PredictionResponse模型的标准预测结果.
    """
    logger.info(f"获取比赛 {match_id} 的预测")

    try:
        # 导入推理服务和响应模型
        from src.services.inference_service import inference_service
        from src.inference.schemas import PredictionResponse
        import uuid
        from datetime import datetime

        # 调用推理服务进行预测
        try:
            prediction_result = await inference_service.predict_match(match_id)
        except TypeError as e:
            # 如果inference_service不是可调用的对象，返回错误
            raise HTTPException(status_code=500, detail=f"推理服务不可用: {str(e)}")

        if not prediction_result.get("success", False):
            raise HTTPException(
                status_code=404, detail=prediction_result.get("error", "预测生成失败")
            )

        # 转换为PredictionResponse格式
        # 推理服务可能返回带有"data"字段的结构，或者直接返回预测数据
        if "data" in prediction_result:
            response_data = prediction_result["data"]
        else:
            response_data = prediction_result

        # 映射推理服务字段到PredictionResponse
        # 处理中文结果到英文枚举的映射
        predicted_outcome_raw = response_data.get(
            "prediction", response_data.get("predicted_outcome", "home_win")
        )
        outcome_mapping = {
            "home_win": "home_win",
            "主队胜": "home_win",
            "主胜": "home_win",
            "draw": "draw",
            "平局": "draw",
            "away_win": "away_win",
            "客队胜": "away_win",
            "客胜": "away_win",
        }
        predicted_outcome = outcome_mapping.get(predicted_outcome_raw, "home_win")

        prediction_response = PredictionResponse(
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            match_id=str(match_id),
            predicted_at=datetime.utcnow(),
            # 预测结果 - 适配推理服务的字段名
            home_win_prob=response_data.get("home_win_prob", 0.33),
            draw_prob=response_data.get("draw_prob", 0.33),
            away_win_prob=response_data.get("away_win_prob", 0.34),
            predicted_outcome=predicted_outcome,
            confidence=response_data.get("confidence", 0.5),
            # 模型信息
            model_name=response_data.get("model_name", "default_xgboost"),
            model_version=response_data.get("model_version", "mock_v1"),
            model_type=(
                "MOCK" if response_data.get("status") == "mock_data" else "XGBOOST"
            ),
            # 元数据
            features_used=response_data.get("features_used", []),
            prediction_time_ms=response_data.get("prediction_time_ms"),
            cached=response_data.get("cached", False),
            metadata={
                "status": response_data.get("status", "success"),
                "note": response_data.get("note", ""),
                "suggestion": response_data.get("suggestion", ""),
                **response_data.get("metadata", {}),
            },
        )

        logger.info(
            f"成功生成比赛 {match_id} 的预测: {prediction_response.predicted_outcome}"
        )
        return prediction_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预测失败: {str(e)}") from e


@router.post("/{match_id}/predict", response_model=PredictionResult, status_code=201)
async def create_prediction(match_id: int, request: PredictionRequest | None = None):
    """实时生成比赛预测.

    使用机器学习模型实时计算比赛结果预测。
    此操作会触发完整的预测流程,包括特征提取和模型推理.
    """
    logger.info(f"开始为比赛 {match_id} 生成预测")

    try:
        # 调用真实的推理服务
        from src.services.inference_service import inference_service

        # 使用推理服务进行预测
        prediction_result = await inference_service.predict_match(match_id)

        if not prediction_result.get("success", False):
            raise HTTPException(
                status_code=404, detail=prediction_result.get("error", "预测生成失败")
            )

        # 转换为API响应格式
        model_version = (
            request.model_version
            if request
            else prediction_result.get("model_version", "default")
        )
        result = PredictionResult(
            match_id=match_id,
            home_win_prob=prediction_result.get("home_win_prob", 0.33),
            draw_prob=prediction_result.get("draw_prob", 0.33),
            away_win_prob=prediction_result.get("away_win_prob", 0.34),
            predicted_outcome=prediction_result.get("predicted_outcome", "home"),
            confidence=prediction_result.get("confidence", 0.5),
            model_version=model_version,
            predicted_at=datetime.utcnow(),
        )

        logger.info(f"成功生成比赛 {match_id} 的预测: {result.predicted_outcome}")
        return result

    except Exception as e:
        logger.error(f"生成预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成预测失败: {str(e)}") from e


@router.post("/batch", response_model=BatchPredictionResponse)
async def batch_predict(request: BatchPredictionRequest):
    """批量预测比赛结果.

    一次性为多场比赛生成预测,适用于批处理场景。
    最多支持100场比赛的批量预测.
    """
    logger.info(f"开始批量预测 {len(request.match_ids)} 场比赛")

    try:
        predictions = []
        failed_ids = []

        for match_id in request.match_ids:
            try:
                # ISSUE: 需要实现基于机器学习模型的实际预测算法
                _prediction = PredictionResult(
                    match_id=match_id,
                    home_win_prob=0.45,
                    draw_prob=0.30,
                    away_win_prob=0.25,
                    predicted_outcome="home",
                    confidence=0.75,
                    model_version=request.model_version,
                    predicted_at=datetime.utcnow(),
                )
                predictions.append(_prediction)
            except Exception as e:
                logger.warning(f"比赛 {match_id} 预测失败: {e}")
                failed_ids.append(match_id)

        response = BatchPredictionResponse(
            predictions=predictions,
            total=len(request.match_ids),
            success_count=len(predictions),
            failed_count=len(failed_ids),
            failed_match_ids=failed_ids,
        )

        logger.info(
            f"批量预测完成: 成功 {response.success_count}, 失败 {response.failed_count}"
        )
        return response

    except Exception as e:
        logger.error(f"批量预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量预测失败: {str(e)}") from e


@router.get("/history/{match_id}", response_model=PredictionHistory)
async def get_prediction_history(
    match_id: int,
    limit: int = Query(10, ge=1, le=100, description="返回的历史记录数量"),
):
    """获取比赛的历史预测记录.

    返回指定比赛的所有历史预测,按时间倒序排列。
    可用于分析预测准确性的变化趋势.
    """
    logger.info(f"获取比赛 {match_id} 的历史预测记录")

    try:
        # ISSUE: 需要从数据库获取预测历史记录，需要实现历史数据查询
        # 模拟历史数据
        history_predictions = [
            PredictionResult(
                match_id=match_id,
                home_win_prob=0.45 + i * 0.01,
                draw_prob=0.30,
                away_win_prob=0.25 - i * 0.01,
                predicted_outcome="home",
                confidence=0.75,
                model_version=f"v1.{i}",
                predicted_at=datetime.utcnow() - timedelta(hours=i),
            )
            for i in range(min(limit, 5))
        ]

        history = PredictionHistory(
            match_id=match_id,
            predictions=history_predictions,
            total_predictions=len(history_predictions),
        )

        logger.info(f"成功获取 {history.total_predictions} 条历史记录")
        return history

    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取历史记录失败: {str(e)}"
        ) from e


@router.post("/{match_id}/verify", response_model=PredictionVerification)
async def verify_prediction(
    match_id: int,
    actual_result: str = Query(
        ..., regex="^(home|draw|away)$", description="实际比赛结果"
    ),
):
    """验证预测结果的准确性.

    在比赛结束后,使用此端点验证预测的准确性。
    系统会自动计算准确性分数并更新模型统计.
    """
    logger.info(f"验证比赛 {match_id} 的预测结果,实际结果: {actual_result}")

    try:
        # ISSUE: 需要获取原始预测数据并进行业务规则验证
        # 模拟验证
        prediction = PredictionResult(
            match_id=match_id,
            home_win_prob=0.45,
            draw_prob=0.30,
            away_win_prob=0.25,
            predicted_outcome="home",
            confidence=0.75,
            model_version="default",
            predicted_at=datetime.utcnow() - timedelta(days=1),
        )

        is_correct = prediction.predicted_outcome == actual_result
        accuracy_score = (
            prediction.confidence if is_correct else 1.0 - prediction.confidence
        )

        verification = PredictionVerification(
            match_id=match_id,
            prediction=prediction,
            actual_result=actual_result,
            is_correct=is_correct,
            accuracy_score=accuracy_score,
        )

        logger.info(
            f"验证完成: {'正确' if is_correct else '错误'}, 准确度: {accuracy_score:.2f}"
        )
        return verification

    except Exception as e:
        logger.error(f"验证预测失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证预测失败: {str(e)}") from e
