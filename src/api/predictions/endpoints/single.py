"""
from src.database.connection import get_async_session
from src.database.models import Predictions

单个预测端点
Single Prediction Endpoints

处理单场比赛预测相关的API端点。
"""




    PredictionRequest,
    PredictionResponse,
    PredictionHistoryResponse,
)

logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_match(
    request: PredictionRequest,
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    预测单场比赛结果

    Args:
        request: 预测请求
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        PredictionResponse: 预测结果
    """
    try:
        logger.info(f"用户 {current_user.get('id')} 请求预测比赛 {request.match_id}")

        # 执行预测
        result = await engine.predict_match(
            match_id=request.match_id,
            force_refresh=request.force_refresh,
            include_features=request.include_features,
        )

        return PredictionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"预测比赛 {request.match_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="预测服务暂时不可用")


@router.get("/match/{match_id}", response_model=PredictionResponse)
async def get_match_prediction(
    match_id: int = Path(..., description="比赛ID", gt=0),
    include_features: bool = Query(False, description="是否包含特征信息"),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛预测结果

    Args:
        match_id: 比赛ID
        include_features: 是否包含特征信息
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        PredictionResponse: 预测结果
    """
    try:
        # 获取缓存中的预测结果
        result = await engine.predict_match(
            match_id=match_id,
            force_refresh=False,
            include_features=include_features,
        )

        return PredictionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测失败: {e}")
        raise HTTPException(status_code=500, detail="获取预测失败")


@router.get("/history/match/{match_id}", response_model=PredictionHistoryResponse)
async def get_match_prediction_history(
    match_id: int = Path(..., description="比赛ID", gt=0),
    limit: int = Query(10, description="返回记录数限制", ge=1, le=100),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛预测历史

    Args:
        match_id: 比赛ID
        limit: 返回记录数限制
        current_user: 当前用户

    Returns:
        PredictionHistoryResponse: 预测历史记录
    """
    try:
        async with get_async_session() as session:
            query = (
                select(Predictions)
                .where(Predictions.match_id == match_id)
                .order_by(Predictions.created_at.desc())
                .limit(limit)
            )




            result = await session.execute(query)
            predictions = result.scalars().all()

            history = []
            for pred in predictions:
                history.append(
                    {
                        "id": pred.id,
                        "model_version": pred.model_version,
                        "model_name": pred.model_name,
                        "predicted_result": pred.predicted_result,
                        "probabilities": {
                            "home_win": pred.home_win_probability,
                            "draw": pred.draw_probability,
                            "away_win": pred.away_win_probability,
                        },
                        "confidence": pred.confidence_score,
                        "created_at": pred.created_at.isoformat(),
                        "actual_result": pred.actual_result,
                        "is_correct": pred.is_correct,
                        "verified_at": pred.verified_at.isoformat()
                        if pred.verified_at
                        else None,
                    }
                )

            return PredictionHistoryResponse(
                match_id=match_id,
                total_records=len(history),
                history=history,
            )

    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取预测历史失败")