"""
比分采集任务

负责采集实时比分数据。
"""



logger = logging.getLogger(__name__)


@app.task(base=BaseDataTask, bind=True)
def collect_live_scores_conditional(self, match_ids: Optional[List[str]] = None):
    """
    条件性采集实时比分任务

    Args:
        match_ids: 指定比赛ID列表，如果为None则自动获取正在进行和即将开始的比赛
    """

    async def _collect_scores():
        # 检查是否应该采集实时比分
        if not should_collect_live_scores():
            logger.info("当前时间不在实时比分采集窗口内，跳过采集")
            return 0, 0

        # 初始化比分采集器
        collector = ScoresCollector()

        matches_updated = 0


        scores_collected = 0

        if match_ids:
            # 采集指定比赛的比分
            target_matches = match_ids
        else:
            # 获取正在进行和即将开始的比赛
            async with get_async_session() as session:

                # 查询最近1小时开始和未来2小时内的比赛
                cutoff_start = datetime.now() - timedelta(hours=1)
                cutoff_end = datetime.now() + timedelta(hours=2)

                query = select(Match).where(
                    Match.match_date >= cutoff_start,
                    Match.match_date <= cutoff_end,
                    Match.status.in_(["live", "scheduled", "halftime", "delayed"]),
                )

                result = await session.execute(query)
                matches = result.scalars().all()
                target_matches = [match.id for match in matches]

        logger.info(f"找到 {len(target_matches)} 场需要采集比分的比赛")

        # 采集每场比赛的比分
        for match_id in target_matches:
            try:
                result = await collector.collect_live_scores(match_id)
                if result.get("status") == "success":
                    matches_updated += 1
                    scores_count = result.get("scores_count", 0)
                    scores_collected += scores_count
                    logger.info(f"更新比赛 {match_id} 比分: {scores_count} 条数据")
                else:
                    logger.warning(
                        f"采集比赛 {match_id} 比分失败: {result.get('error')}"
                    )
            except Exception as e:
                logger.error(f"采集比赛 {match_id} 比分时出错: {str(e)}")
                continue

        return matches_updated, scores_collected

    try:
        # 运行异步采集任务
        matches_updated, scores_collected = asyncio.run(_collect_scores())

        logger.info(
            f"实时比分采集完成: 更新了 {matches_updated} 场比赛，"
            f"采集了 {scores_collected} 条比分数据"
        )

        return {
            "status": "success",
            "matches_updated": matches_updated,
            "scores_collected": scores_collected,
            "match_ids": match_ids or "auto",
            "execution_time": datetime.now().isoformat(),
        }

            "execution_time": datetime.now().isoformat(),)

        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("collect_live_scores", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get(
            "retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY
        )

        if self.request.retries < max_retries:
            logger.warning(f"实时比分采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"实时比分采集任务最终失败: {str(exc)}")
            raise