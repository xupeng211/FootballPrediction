"""

"""





    """

    """











from datetime import datetime, timedelta

赛程采集任务
负责从外部API采集足球赛程数据。
logger = logging.getLogger(__name__)
@app.task(base=BaseDataTask, bind=True)
def collect_fixtures(self, leagues: Optional[List[str]] = None, days_ahead: int = 30):
    采集赛程数据任务
    Args:
        leagues: 需要采集的联赛列表
        days_ahead: 采集未来N天的赛程
    async def _collect_task():
        # 初始化赛程采集器
        collector = FixturesCollector()
        # 设置采集时间范围
        date_from = datetime.now()
        date_to = date_from + timedelta(days=days_ahead)
        logger.info(
            f"开始采集赛程数据: 时间范围 {date_from.date()} 到 {date_to.date()}"
        )
        # 采集赛程数据
        result = await collector.collect_fixtures(
            date_from=date_from,
            date_to=date_to,
            leagues=leagues
        )
        return result
    try:
        # 运行异步采集任务
        result = asyncio.run(_collect_task())
        if result.get("status") == "success":
            fixtures_collected = result.get("fixtures_count", 0)
            logger.info(f"赛程采集任务完成: 采集了 {fixtures_collected} 场比赛")
            return {
                "status": "success",
                "fixtures_collected": fixtures_collected,
                "date_range": {
                    "from": (datetime.now()).date().isoformat(),
                    "to": (datetime.now() + timedelta(days=days_ahead)).date().isoformat()
                },
                "leagues": leagues or "all",
                "execution_time": datetime.now().isoformat(),
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"赛程采集失败: {error_msg}")
            raise Exception(f"赛程采集失败: {error_msg}")
    except Exception as exc:
        logger.error(f"赛程采集任务失败: {str(exc)}")
        raise