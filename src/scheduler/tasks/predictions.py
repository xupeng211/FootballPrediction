"""
        from sqlalchemy import text

预测任务
Prediction Tasks

包含预测生成任务。
"""




logger = logging.getLogger(__name__)


@app.task(base=BaseDataTask, bind=True)
def generate_predictions(self, match_ids: Optional[List[int]] = None):
    """
    生成预测任务

    Args:
        match_ids: 需要生成预测的比赛ID列表
    """
    try:
        logger.info("开始执行预测生成任务")


        async def _generate_predictions():
            """异步生成预测"""
            async with get_async_session() as session:
                # 1. 获取待预测的比赛
                if match_ids:
                    # 指定比赛ID
                    result = await session.execute(
                        text(
                            """
                        SELECT id, home_team, away_team, match_date, league_id
                        FROM matches
                        WHERE id = ANY(:match_ids)
                        AND match_date > NOW()
                        AND status = 'scheduled'
                        """
                        ),
                        {"match_ids": match_ids},
                    )
                else:
                    # 获取未来24小时内待预测的比赛
                    result = await session.execute(
                        text(
                            """
                        SELECT id, home_team, away_team, match_date, league_id
                        FROM matches
                        WHERE match_date BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                        AND status = 'scheduled'
                        ORDER BY match_date ASC
                        """
                        )
                    )

                matches = result.fetchall()
                if not matches:
                    logger.info("没有找到需要预测的比赛")
                    return 0



                # 2. 初始化预测服务
                prediction_service = PredictionService()

                predictions_generated = 0

                # 3. 为每场比赛生成预测
                for match in matches:
                    try:
                        match_id = match.id
                        home_team = match.home_team
                        away_team = match.away_team
                        match_date = match.match_date
                        league_id = match.league_id

                        logger.info(
                            f"为比赛 {match_id} ({home_team} vs {away_team}) 生成预测"
                        )

                        # 生成预测
                        prediction_result = (
                            await prediction_service.generate_match_prediction(
                                match_id=match_id,
                                home_team=home_team,
                                away_team=away_team,
                                match_date=match_date,
                                league_id=league_id,
                            )
                        )

                        if prediction_result.get("status") == "success":
                            predictions_generated += 1
                            logger.info(f"比赛 {match_id} 预测生成成功")
                        else:
                            logger.warning(
                                f"比赛 {match_id} 预测生成失败: {prediction_result.get('error', 'Unknown error')}"
                            )

                    except Exception as e:
                        logger.error(f"为比赛 {match.id} 生成预测时出错: {str(e)}")
                        continue

                return predictions_generated

        # 运行异步预测生成
        predictions_generated = asyncio.run(_generate_predictions())

        logger.info(f"预测生成任务完成: 生成了 {predictions_generated} 个预测")

        return {
            "status": "success",
            "predictions_generated": predictions_generated,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"预测生成任务失败: {str(exc)}")
        raise