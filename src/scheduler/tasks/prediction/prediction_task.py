"""

"""





    """

    """



















from datetime import datetime, timedelta

预测生成任务
负责为即将开始的比赛生成预测。
logger = logging.getLogger(__name__)
@app.task(base=BaseDataTask, bind=True)
def generate_predictions(self, match_ids: Optional[List[int]] = None):
    生成比赛预测
    Args:
        match_ids: 指定比赛ID列表，如果为None则自动获取即将开始的比赛
    async def _generate_predictions():
        # 初始化预测服务
        prediction_service = PredictionService()
        predictions_generated = 0
        predictions_failed = 0
        if match_ids:
            # 为指定比赛生成预测
            target_matches = match_ids
        else:
            # 获取即将开始的比赛（未来24小时内）
            async with get_async_session() as session:
                cutoff_time = datetime.now() + timedelta(hours=24)
                query = select(Match).where(
                    Match.match_date <= cutoff_time,
                    Match.match_date >= datetime.now(),
                    Match.status == "scheduled"
                ).order_by(Match.match_date)
                result = await session.execute(query)
                matches = result.scalars().all()
                target_matches = [match.id for match in matches]
        logger.info(f"找到 {len(target_matches)} 场需要生成预测的比赛")
        # 为每场比赛生成预测
        for match_id in target_matches:
            try:
                # 生成预测
                prediction_result = await prediction_service.generate_prediction(
                    match_id=match_id
                )
                if prediction_result.get("status") == "success":
                    predictions_generated += 1
                    prediction = prediction_result.get("prediction", {})
                    logger.info(
                        f"比赛 {match_id} 预测生成成功: "
                        f"主队胜率 {prediction.get('home_win_prob', 0):.2%}, "
                        f"平局概率 {prediction.get('draw_prob', 0):.2%}, "
                        f"客队胜率 {prediction.get('away_win_prob', 0):.2%}"
                    )
                else:
                    predictions_failed += 1
                    logger.warning(
                        f"比赛 {match_id} 预测生成失败: {prediction_result.get('error')}"
                    )
            except Exception as e:
                predictions_failed += 1
                logger.error(f"为比赛 {match_id} 生成预测时出错: {str(e)}")
                continue
        return predictions_generated, predictions_failed
    try:
        # 运行异步预测生成
        generated, failed = asyncio.run(_generate_predictions())
        logger.info(
            f"预测生成任务完成: 成功 {generated} 个，失败 {failed} 个"
        )
        return {
            "status": "success",
            "predictions_generated": generated,
            "predictions_failed": failed,
            "match_ids": match_ids or "auto",
            "execution_time": datetime.now().isoformat(),
        }
    except Exception as exc:
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("generate_predictions", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get("retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY)
        if self.request.retries < max_retries:
            logger.warning(f"预测生成失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"预测生成任务最终失败: {str(exc)}")
            raise