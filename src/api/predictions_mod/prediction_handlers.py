"""


"""






    """获取预测服务实例（懒加载）"""


    """



    """











    """


    """







    """


    """





    """格式化缓存的预测结果"""


    """格式化实时预测结果"""



from src.utils.response import APIResponse

预测处理器 / Prediction Handlers
处理单个比赛的预测相关请求。
logger = logging.getLogger(__name__)
# 懒加载prediction服务
_prediction_service = None
def get_prediction_service():
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service
async def get_match_prediction_handler(
    request: Request,
    match_id: int,
    force_predict: bool = False,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    获取比赛预测结果的处理器
    Args:
        request: FastAPI请求对象
        match_id: 比赛ID
        force_predict: 是否强制重新预测
        session: 数据库会话
    Returns:
        API响应字典
    Raises:
        HTTPException: 当比赛不存在或预测失败时
    try:
        logger.info(f"获取比赛 {match_id} 的预测结果")
        # 查询比赛信息
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()
        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")
        # 查询现有预测结果
        prediction = None
        if not force_predict:
            prediction_query = (
                select(Prediction)
                .where(Prediction.match_id == match_id)
                .order_by(Prediction.created_at.desc())
            )
            prediction_result = await session.execute(prediction_query)
            prediction = prediction_result.scalar_one_or_none()
        if prediction and not force_predict:
            # 返回缓存的预测结果
            logger.info(f"返回缓存的预测结果：比赛 {match_id}")
            return _format_cached_prediction(match, prediction)
        else:
            # 实时生成预测
            logger.info(f"实时生成预测：比赛 {match_id}")
            # 检查比赛状态，如果已结束则不允许实时预测
            if match.match_status == MatchStatus.FINISHED:
                logger.warning(f"尝试为已结束的比赛 {match_id} 生成预测")
                raise HTTPException(
                    status_code=400, detail=f"比赛 {match_id} 已结束，无法生成预测"
                )
            prediction_service = get_prediction_service()
            prediction_result_data = await prediction_service.predict_match(match_id)
            return _format_realtime_prediction(match, prediction_result_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取预测结果失败: {e}")
async def predict_match_handler(
    match_id: int,
    session: AsyncSession,
) -> Dict[str, Any]:
    实时预测比赛结果的处理器
    Args:
        match_id: 比赛ID
        session: 数据库会话
    Returns:
        API响应字典
    try:
        logger.info(f"开始预测比赛 {match_id}")
        # 验证比赛存在
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()
        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")
        # 进行预测
        prediction_service = get_prediction_service()
        prediction_result_data = await prediction_service.predict_match(match_id)
        return APIResponse.success(
            data=prediction_result_data.to_dict(),
            message=f"比赛 {match_id} 预测完成"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预测比赛 {match_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="预测失败")
async def verify_prediction_handler(
    match_id: int,
    session: AsyncSession,
) -> Dict[str, Any]:
    验证预测结果的处理器
    Args:
        match_id: 比赛ID
        session: 数据库会话
    Returns:
        API响应字典
    try:
        logger.info(f"验证比赛 {match_id} 的预测结果")
        # 验证预测结果
        prediction_service = get_prediction_service()
        success = await prediction_service.verify_prediction(match_id)
        if success:
            return APIResponse.success(
                data={"match_id": match_id, "verified": True},
                message="预测结果验证完成",
            )
        else:
            return APIResponse.error(
                message="预测结果验证失败",
                data={"match_id": match_id, "verified": False},
            )
    except Exception as e:
        logger.error(f"验证预测结果失败: {e}")
        raise HTTPException(status_code=500, detail="验证预测结果失败")
def _format_cached_prediction(match: Match, prediction: Prediction) -> Dict[str, Any]:
    return APIResponse.success(
        data={
            "match_id": match.id,
            "match_info": {
                "match_id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "league_id": match.league_id,
                "match_time": match.match_time.isoformat(),
                "match_status": match.match_status,
                "season": match.season,
            },
            "prediction": {
                "id": prediction.id,
                "model_version": prediction.model_version,
                "model_name": prediction.model_name,
                "home_win_probability": (
                    float(prediction.home_win_probability)
                    if prediction.home_win_probability is not None
                    else 0.0
                ),
                "draw_probability": (
                    float(prediction.draw_probability)
                    if prediction.draw_probability is not None
                    else 0.0
                ),
                "away_win_probability": (
                    float(prediction.away_win_probability)
                    if prediction.away_win_probability is not None
                    else 0.0
                ),
                "predicted_result": prediction.predicted_result,
                "confidence_score": (
                    float(prediction.confidence_score)
                    if prediction.confidence_score is not None
                    else 0.0
                ),
                "created_at": prediction.created_at.isoformat(),
                "is_correct": prediction.is_correct,
                "actual_result": prediction.actual_result,
            },
            "source": "cached",
        }
    )
def _format_realtime_prediction(match: Match, prediction_result_data) -> Dict[str, Any]:
    return APIResponse.success(
        data={
            "match_id": match.id,
            "match_info": {
                "match_id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "league_id": match.league_id,
                "match_time": match.match_time.isoformat(),)
                "match_status": match.match_status,
                "season": match.season,
            },
            "prediction": prediction_result_data.to_dict(),
            "source": "real_time",
        }
    )