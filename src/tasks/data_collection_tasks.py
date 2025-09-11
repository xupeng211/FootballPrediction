"""
数据采集任务

实现定时数据采集任务，包括：
- 赛程数据采集
- 赔率数据采集
- 实时比分数据采集

支持自动重试机制，API失败时自动重试3次，失败记录写入error_logs。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from celery import Task

from .celery_app import TaskRetryConfig, app
from .error_logger import TaskErrorLogger

logger = logging.getLogger(__name__)


class DataCollectionTask(Task):
    """数据采集任务基类"""

    def __init__(self):
        super().__init__()
        self.error_logger = TaskErrorLogger()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理"""
        task_name = self.name.split(".")[-1] if self.name else "unknown_task"

        # 异步记录错误日志
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.error_logger.log_task_error(
                    task_name=task_name,
                    task_id=task_id,
                    error=exc,
                    context={"args": args, "kwargs": kwargs, "einfo": str(einfo)},
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
                )
            )
        except Exception as log_error:
            logger.error(f"记录任务失败日志时出错: {str(log_error)}")

        logger.error(f"数据采集任务失败: {task_name} - {str(exc)}")

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的处理"""
        task_name = self.name.split(".")[-1] if self.name else "unknown_task"
        logger.info(f"数据采集任务成功: {task_name}")


@app.task(base=DataCollectionTask, bind=True)
def collect_fixtures_task(
    self, leagues: Optional[List[str]] = None, days_ahead: int = 30
) -> Dict[str, Any]:
    """
    赛程数据采集任务

    Args:
        leagues: 需要采集的联赛列表
        days_ahead: 采集未来N天的赛程

    Returns:
        采集结果字典
    """

    async def _collect_fixtures():
        """内部异步采集函数"""
        try:
            # 动态导入以避免循环导入问题
            from src.data.collectors.fixtures_collector import \
                FixturesCollector

            collector = FixturesCollector()

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
            if hasattr(self, "error_logger"):
                await self.error_logger.log_api_failure(
                    task_name="collect_fixtures_task",
                    api_endpoint="fixtures_api",
                    http_status=None,
                    error_message=str(e),
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
                )
            raise e

    try:
        # 运行异步任务
        result = asyncio.run(_collect_fixtures())

        if result.status == "failed":
            raise Exception(f"赛程采集失败: {result.error_message}")

        logger.info(
            f"赛程采集完成: 成功={result.success_count}, "
            f"错误={result.error_count}, 总数={result.records_collected}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
            "leagues": leagues,
            "days_ahead": days_ahead,
        }

    except Exception as exc:
        # 获取重试配置
        retry_config = TaskRetryConfig.get_retry_config("collect_fixtures_task")
        max_retries = retry_config["max_retries"]
        retry_delay = retry_config["retry_delay"]

        # 检查是否需要重试
        if self.request.retries < max_retries:
            logger.warning(
                f"赛程采集失败，将在{retry_delay}秒后重试 (第{self.request.retries + 1}次): {str(exc)}"
            )
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            # 最终失败，记录到错误日志
            logger.error(f"赛程采集任务最终失败，已达最大重试次数: {str(exc)}")

            # 异步记录到数据采集日志
            asyncio.run(
                self.error_logger.log_data_collection_error(
                    data_source="fixtures_api",
                    collection_type="fixtures",
                    error_message=str(exc),
                    error_count=1,
                )
            )

            raise exc


@app.task(base=DataCollectionTask, bind=True)
def collect_odds_task(
    self, match_ids: Optional[List[str]] = None, bookmakers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    赔率数据采集任务

    Args:
        match_ids: 需要采集的比赛ID列表
        bookmakers: 博彩公司列表

    Returns:
        采集结果字典
    """

    async def _collect_odds():
        """内部异步采集函数"""
        try:
            # 动态导入以避免循环导入问题
            from src.data.collectors.odds_collector import OddsCollector

            collector = OddsCollector()

            logger.info(f"开始采集赔率数据: 比赛={match_ids}, 博彩商={bookmakers}")

            # 执行采集
            result = await collector.collect_odds(
                match_ids=match_ids, bookmakers=bookmakers
            )

            return result

        except Exception as e:
            # 记录API失败
            if hasattr(self, "error_logger"):
                await self.error_logger.log_api_failure(
                    task_name="collect_odds_task",
                    api_endpoint="odds_api",
                    http_status=None,
                    error_message=str(e),
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
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
        # 获取重试配置
        retry_config = TaskRetryConfig.get_retry_config("collect_odds_task")
        max_retries = retry_config["max_retries"]
        retry_delay = retry_config["retry_delay"]

        # 检查是否需要重试
        if self.request.retries < max_retries:
            logger.warning(
                f"赔率采集失败，将在{retry_delay}秒后重试 (第{self.request.retries + 1}次): {str(exc)}"
            )
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            # 最终失败，记录到错误日志
            logger.error(f"赔率采集任务最终失败，已达最大重试次数: {str(exc)}")

            # 异步记录到数据采集日志
            asyncio.run(
                self.error_logger.log_data_collection_error(
                    data_source="odds_api",
                    collection_type="odds",
                    error_message=str(exc),
                    error_count=1,
                )
            )

            raise exc


@app.task(base=DataCollectionTask, bind=True)
def collect_scores_task(
    self, match_ids: Optional[List[str]] = None, live_only: bool = False
) -> Dict[str, Any]:
    """
    比分数据采集任务

    Args:
        match_ids: 需要监控的比赛ID列表
        live_only: 是否只采集实时进行中的比赛

    Returns:
        采集结果字典
    """

    async def _collect_scores():
        """内部异步采集函数"""
        try:
            # 动态导入以避免循环导入问题
            from src.data.collectors.scores_collector import ScoresCollector

            collector = ScoresCollector()

            logger.info(f"开始采集比分数据: 比赛={match_ids}, 仅实时={live_only}")

            # 根据是否仅实时采集选择不同的采集方法
            if live_only:
                result = await collector.collect_live_scores(
                    match_ids=match_ids, use_websocket=True
                )
            else:
                # 采集所有比分数据（包括已结束的比赛）
                result = await collector.collect_live_scores(
                    match_ids=match_ids, use_websocket=False
                )

            return result

        except Exception as e:
            # 记录API失败
            if hasattr(self, "error_logger"):
                await self.error_logger.log_api_failure(
                    task_name="collect_scores_task",
                    api_endpoint="scores_api",
                    http_status=None,
                    error_message=str(e),
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
                )
            raise e

    try:
        # 根据live_only决定是否跳过
        if live_only:
            # 检查是否有进行中的比赛（简化版检查）
            from .utils import should_collect_live_scores

            if not should_collect_live_scores():
                logger.info("当前无进行中的比赛，跳过实时比分采集")
                return {
                    "status": "skipped",
                    "reason": "no_live_matches",
                    "execution_time": datetime.now().isoformat(),
                }

        # 运行异步任务
        result = asyncio.run(_collect_scores())

        if result.status == "failed":
            raise Exception(f"比分采集失败: {result.error_message}")

        logger.info(
            f"比分采集完成: 成功={result.success_count}, "
            f"错误={result.error_count}, 总数={result.records_collected}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
            "match_ids": match_ids,
            "live_only": live_only,
        }

    except Exception as exc:
        # 获取重试配置（比分采集重试次数较少，因为时效性要求高）
        retry_config = TaskRetryConfig.get_retry_config("collect_scores_task")
        max_retries = retry_config["max_retries"]
        retry_delay = retry_config["retry_delay"]

        # 检查是否需要重试
        if self.request.retries < max_retries:
            logger.warning(
                f"比分采集失败，将在{retry_delay}秒后重试 (第{self.request.retries + 1}次): {str(exc)}"
            )
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            # 最终失败，记录到错误日志
            logger.error(f"比分采集任务最终失败，已达最大重试次数: {str(exc)}")

            # 异步记录到数据采集日志
            asyncio.run(
                self.error_logger.log_data_collection_error(
                    data_source="scores_api",
                    collection_type="scores",
                    error_message=str(exc),
                    error_count=1,
                )
            )

            raise exc


# 手动触发的任务（用于测试和调试）
@app.task(base=DataCollectionTask)
def manual_collect_all_data() -> Dict[str, Any]:
    """
    手动触发所有数据采集任务

    用于测试和调试，或者在需要时手动触发完整的数据采集
    """
    results = {}

    try:
        # 依次执行三个采集任务
        logger.info("开始手动执行所有数据采集任务")

        # 1. 赛程采集
        fixtures_result = collect_fixtures_task.delay(days_ahead=7)
        results["fixtures"] = fixtures_result.get(timeout=300)  # 5分钟超时

        # 2. 赔率采集
        odds_result = collect_odds_task.delay()
        results["odds"] = odds_result.get(timeout=300)

        # 3. 比分采集
        scores_result = collect_scores_task.delay(live_only=False)
        results["scores"] = scores_result.get(timeout=300)

        logger.info("手动数据采集任务全部完成")

        return {
            "status": "success",
            "message": "所有数据采集任务已完成",
            "results": results,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"手动数据采集任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "partial_results": results,
            "execution_time": datetime.now().isoformat(),
        }
