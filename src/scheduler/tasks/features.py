"""
        from sqlalchemy import text

特征计算任务
Feature Calculation Tasks

包含批量特征计算任务。
"""




logger = logging.getLogger(__name__)


@app.task(base=BaseDataTask, bind=True)
def calculate_features_batch(self, hours_ahead: int = 2):
    """
    批量计算特征数据任务

    Args:
        hours_ahead: 计算未来N小时内比赛的特征
    """
    try:
        logger.info(f"开始执行特征计算任务，计算未来{hours_ahead}小时内的比赛特征")


        async def _calculate_features():
            """异步计算特征"""
            async with get_async_session() as session:
                # 1. 查询未来N小时内的比赛
                result = await session.execute(
                    text(
                        """
                    SELECT id, home_team, away_team, match_date, league_id
                    FROM matches
                    WHERE match_date BETWEEN NOW() AND NOW() + INTERVAL :hours_ahead hours
                    AND status = 'scheduled'
                    ORDER BY match_date ASC
                    """
                    ),
                    {"hours_ahead": hours_ahead},
                )

                matches = result.fetchall()
                if not matches:
                    logger.info(f"未来{hours_ahead}小时内没有需要计算特征的比赛")
                    return 0, 0



                # 2. 初始化特征存储
                feature_store = FootballFeatureStore()

                matches_processed = 0
                features_calculated = 0

                # 3. 为每场比赛计算特征
                for match in matches:
                    try:
                        match_id = match.id
                        home_team = match.home_team
                        away_team = match.away_team
                        match_date = match.match_date
                        league_id = match.league_id

                        logger.info(
                            f"为比赛 {match_id} ({home_team} vs {away_team}) 计算特征"
                        )

                        # 计算比赛特征
                        feature_result = await feature_store.calculate_match_features(
                            match_id=match_id,
                            home_team=home_team,
                            away_team=away_team,
                            match_date=match_date,
                            league_id=league_id,
                        )

                        if feature_result.get("status") == "success":
                            matches_processed += 1
                            features_calculated += feature_result.get(
                                "features_count", 0
                            )
                            logger.info(
                                f"比赛 {match_id} 特征计算成功，生成了 {feature_result.get('features_count', 0)} 个特征"
                            )
                        else:
                            logger.warning(
                                f"比赛 {match_id} 特征计算失败: {feature_result.get('error', 'Unknown error')}"
                            )

                    except Exception as e:
                        logger.error(f"为比赛 {match.id} 计算特征时出错: {str(e)}")
                        continue

                return matches_processed, features_calculated

        # 运行异步特征计算
        matches_processed, features_calculated = asyncio.run(_calculate_features())

        logger.info(
            f"特征计算任务完成: 处理了 {matches_processed} 场比赛，计算了 {features_calculated} 个特征"
        )

        return {
            "status": "success",
            "matches_processed": matches_processed,
            "features_calculated": features_calculated,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        retry_config = self.get_retry_config("calculate_features")
        max_retries = retry_config.get("max_retries", 3)
        retry_delay = retry_config.get("retry_delay", 60)

        if self.request.retries < max_retries:
            logger.warning(f"特征计算失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"特征计算任务最终失败: {str(exc)}")
            raise