"""


"""





    """


    """

        """内部异步采集函数"""














    """赛程数据收集器（用于测试）"""


        """收集赛程数据"""


            from src.data.collectors.fixtures_collector import (

赛程数据采集任务
Fixtures Collection Task
负责采集足球赛程数据。
logger = logging.getLogger(__name__)
@app.task(base=DataCollectionTask, bind=True)
def collect_fixtures_task(
    self, leagues: Optional[List[str]] = None, days_ahead: int = 30
) -> Dict[str, Any]:
    赛程数据采集任务
    Args:
        leagues: 需要采集的联赛列表
        days_ahead: 采集未来N天的赛程
    Returns:
        采集结果字典
    async def _collect_fixtures():
        try:
            # 动态导入以避免循环导入问题
                FixturesCollector as RealFixturesCollector,
            )
            collector = RealFixturesCollector()
            # 设置时间范围
            date_from = datetime.now()
            date_to = date_from + timedelta(days=days_ahead)
            logger.info(
                f"开始采集赛程数据: 联赛={leagues}, "
                f"时间范围={date_from.strftime('%Y-%m-%d')} 到 {date_to.strftime('%Y-%m-%d')}"
            )
            # 执行采集
            result = await collector.collect_fixtures(
                leagues=leagues, date_from=date_from, date_to=date_to
            )
            return result
        except Exception as e:
            # 记录API失败
            await CollectionTaskMixin.log_api_failure(
                self, "collect_fixtures_task", "fixtures_api", e
            )
            raise e
    try:
        # 运行异步任务
        result = asyncio.run(_collect_fixtures())
        if isinstance(result, dict) and result.get("status") == "failed":
            raise Exception(
                f"赛程采集失败: {result.get(str('error_message'), '未知错误')}"
            )
        success_count = (
            result.get(str("success_count"), 0)
            if isinstance(result, dict)
            else getattr(result, "success_count", 0)
        )
        error_count = (
            result.get(str("error_count"), 0)
            if isinstance(result, dict)
            else getattr(result, "error_count", 0)
        )
        records_collected = (
            result.get(str("records_collected"), 0)
            if isinstance(result, dict)
            else getattr(result, "records_collected", 0)
        )
        logger.info(
            f"赛程采集完成: 成功={success_count}, "
            f"错误={error_count}, 总数={records_collected}"
        )
        status = (
            result.get(str("status"), "success")
            if isinstance(result, dict)
            else getattr(result, "status", "success")
        )
        return {
            "status": status,
            "records_collected": records_collected,
            "success_count": success_count,
            "error_count": error_count,
            "execution_time": datetime.now().isoformat(),
            "leagues": leagues,
            "days_ahead": days_ahead,
        }
    except Exception as exc:
        # 检查是否需要重试
        if not CollectionTaskMixin.handle_retry(self, exc, "collect_fixtures_task"):
            # 最终失败，记录到错误日志
            CollectionTaskMixin.log_data_collection_error(
                self,
                data_source="fixtures_api",
                collection_type="fixtures",
                error=exc,
            )
            raise exc
# 测试用的收集器类
class FixturesCollector:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FixturesCollector")
    def collect_fixtures(self, days_ahead: int = 30, **kwargs) -> Dict[str, Any]:
        self.logger.info(f"开始收集未来 {days_ahead} 天的赛程数据")
        return {
            "status": "success",
            "fixtures_collected": 0,
            "days_ahead": days_ahead,
            "timestamp": datetime.now().isoformat(),)
        }