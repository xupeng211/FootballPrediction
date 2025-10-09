"""
流式预测端点
Streaming Prediction Endpoints

处理实时流式预测相关的API端点。
"""




logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


@router.get("/stream/matches/{match_id}")
async def stream_match_predictions(
    match_id: int = Path(..., description="比赛ID", gt=0),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    实时流式获取比赛预测更新

    Args:
        match_id: 比赛ID
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        StreamingResponse: 实时预测更新流
    """

    async def generate():
        """生成实时数据流"""
        try:
            # 初始预测
            prediction = await engine.predict_match(match_id)
            yield f"data: {prediction}\n\n"

            # 监听更新
            last_time = datetime.now()
            while True:



                # 检查是否有更新
                current_prediction = await engine.predict_match(match_id)
                current_time = datetime.now()

                # 如果预测时间更新了，发送新数据
                if current_time - last_time > timedelta(minutes=5):
                    yield f"data: {current_prediction}\n\n"
                    last_time = current_time

                # 等待5秒
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"流式预测失败: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )