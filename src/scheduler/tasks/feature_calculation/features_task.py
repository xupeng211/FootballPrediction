"""
            from sqlalchemy import select

特征计算任务

负责为即将开始的比赛计算特征。
"""



logger = logging.getLogger(__name__)


@app.task(base=BaseDataTask, bind=True)
def calculate_features_batch(self, hours_ahead: int = 2):
    """
    批量计算比赛特征

    Args:
        hours_ahead: 计算未来N小时内比赛的特征
    """

    async def _calculate_features():
        # 1. 获取需要计算特征的比赛
        cutoff_time = datetime.now() + timedelta(hours=hours_ahead)

        async with get_async_session() as session:

            # 查询即将开始的比赛
            query = select(Match).where(


                Match.match_date <= cutoff_time,
                Match.match_date >= datetime.now(),
                Match.status == "scheduled"
            ).order_by(Match.match_date)

            result = await session.execute(query)
            matches = result.scalars().all()

            logger.info(f"找到 {len(matches)} 场需要计算特征的比赛")

            # 2. 初始化特征存储
            feature_store = FeatureStore()

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

    try:
        # 运行异步特征计算
        matches_processed, features_calculated = asyncio.run(_calculate_features())

        logger.info(
            f"特征计算任务完成: 处理了 {matches_processed} 场比赛，"
            f"计算了 {features_calculated} 个特征"
        )

        return {
            "status": "success",
            "matches_processed": matches_processed,
            "features_calculated": features_calculated,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("calculate_features", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get(
            "retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY
        )

        if self.request.retries < max_retries:
            logger.warning(f"特征计算失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"特征计算任务最终失败: {str(exc)}")
            raise