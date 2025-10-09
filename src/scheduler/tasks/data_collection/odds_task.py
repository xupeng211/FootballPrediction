"""

"""





    """

    """



















赔率采集任务
负责从外部API采集足球赔率数据。
logger = logging.getLogger(__name__)
@app.task(base=BaseDataTask, bind=True)
def collect_odds(
    self,
    match_ids: Optional[List[str]] = None,
    leagues: Optional[List[str]] = None,
    hours_ahead: int = 48,
):
    采集赔率数据任务
    Args:
        match_ids: 指定比赛ID列表
        leagues: 指定联赛列表
        hours_ahead: 采集未来N小时内的赔率
    async def _collect_odds():
        # 初始化赔率采集器
        collector = OddsCollector()
        collected_count = 0
        if match_ids:
            # 采集指定比赛的赔率
            for match_id in match_ids:
                try:
                    result = await collector.collect_odds_for_match(match_id)
                    if result.get("status") == "success":
                        odds_count = result.get("odds_count", 0)
                        collected_count += odds_count
                        logger.info(f"采集比赛 {match_id} 的赔率: {odds_count} 条")
                    else:
                        logger.warning(f"采集比赛 {match_id} 赔率失败: {result.get('error')}")
                except Exception as e:
                    logger.error(f"采集比赛 {match_id} 赔率时出错: {str(e)}")
                    continue
        else:
            # 获取需要采集赔率的比赛列表
            cutoff_time = datetime.now() + timedelta(hours=hours_ahead)
            async with get_async_session() as session:
                # 查询即将开始的比赛
                query = select(Match).where(
                    Match.match_date <= cutoff_time,
                    Match.match_date >= datetime.now(),
                    Match.status == "scheduled"
                )
                if leagues:
                    query = query.where(Match.league_id.in_(leagues))
                result = await session.execute(query)
                matches = result.scalars().all()
                logger.info(f"找到 {len(matches)} 场需要采集赔率的比赛")
                # 为每场比赛采集赔率
                for match in matches:
                    try:
                        odds_result = await collector.collect_odds_for_match(match.id)
                        if odds_result.get("status") == "success":
                            odds_count = odds_result.get("odds_count", 0)
                            collected_count += odds_count
                            logger.info(f"采集比赛 {match.id} 赔率: {odds_count} 条")
                        else:
                            logger.warning(
                                f"采集比赛 {match.id} 赔率失败: {odds_result.get('error')}"
                            )
                    except Exception as e:
                        logger.error(f"采集比赛 {match.id} 赔率时出错: {str(e)}")
                        continue
        return collected_count
    try:
        # 运行异步采集任务
        total_odds = asyncio.run(_collect_odds())
        logger.info(f"赔率采集任务完成: 总计采集 {total_odds} 条赔率数据")
        return {
            "status": "success",
            "odds_collected": total_odds,
            "match_ids": match_ids or "auto",
            "leagues": leagues or "all",
            "hours_ahead": hours_ahead,
            "execution_time": datetime.now().isoformat(),
        }
            "execution_time": datetime.now().isoformat(),)
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("collect_odds", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get("retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY)
        if self.request.retries < max_retries:
            logger.warning(f"赔率采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"赔率采集任务最终失败: {str(exc)}")
            raise