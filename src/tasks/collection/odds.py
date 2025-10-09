"""
            from src.data.collectors.odds_collector import OddsCollector

赔率数据采集任务
Odds Collection Task

负责采集足球赔率数据。
"""



logger = logging.getLogger(__name__)


@app.task(base=DataCollectionTask, bind=True)
def collect_odds_task(
    self,
    match_ids: Optional[List[str]] = None,
    bookmakers: Optional[List[str]] = None,
    # 兼容性参数
    match_id: Optional[int] = None,
    bookmaker: Optional[str] = None,
) -> Dict[str, Any]:
    """
    赔率数据采集任务

    Args:
        match_ids: 需要采集的比赛ID列表
        bookmakers: 博彩公司列表
        match_id: 兼容性参数，单个比赛ID
        bookmaker: 兼容性参数，单个博彩公司

    Returns:
        采集结果字典
    """

    # 处理兼容性参数
    if match_id is not None:
        match_ids = [str(match_id)]
    if bookmaker is not None:
        bookmakers = [bookmaker]

    async def _collect_odds():
        """内部异步采集函数"""
        try:
            # 动态导入以避免循环导入问题

            collector = OddsCollector()



            logger.info(f"开始采集赔率数据: 比赛={match_ids}, 博彩商={bookmakers}")

            # 执行采集
            result = await collector.collect_odds(
                match_ids=match_ids, bookmakers=bookmakers
            )

            return result

        except Exception as e:
            # 记录API失败
            await CollectionTaskMixin.log_api_failure(
                self, "collect_odds_task", "odds_api", e
            )
            raise e

    try:
        # 运行异步任务
        result = asyncio.run(_collect_odds())

        if result.status == "failed":
            raise Exception(f"赔率采集失败: {result.error_message}")

        logger.info(
            f"赔率采集完成: 成功={result.success_count}, "
            f"错误={result.error_count}, 总数={result.records_collected}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
            "match_ids": match_ids,
            "bookmakers": bookmakers,
        }

    except Exception as exc:
        # 检查是否需要重试
        if not CollectionTaskMixin.handle_retry(self, exc, "collect_odds_task"):
            # 最终失败，记录到错误日志
            CollectionTaskMixin.log_data_collection_error(
                self,
                data_source="odds_api",
                collection_type="odds",
                error=exc,
            )

            raise exc