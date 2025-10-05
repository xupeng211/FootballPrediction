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
            from src.data.collectors.fixtures_collector import (
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
    self,
    match_ids: Optional[List[str]] = None,
    live_only: bool = False,
    # 兼容性参数
    match_id: Optional[int] = None,
    live: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    比分数据采集任务

    Args:
        match_ids: 需要监控的比赛ID列表
        live_only: 是否只采集实时进行中的比赛
        match_id: 兼容性参数，单个比赛ID
        live: 兼容性参数，是否实时

    Returns:
        采集结果字典
    """

    # 处理兼容性参数
    if match_id is not None:
        match_ids = [str(match_id)]
    if live is not None:
        live_only = live

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
            "task_ids": {
                "fixtures": fixtures_result.id,
                "odds": odds_result.id,
                "scores": scores_result.id,
            },
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


@app.task(base=DataCollectionTask, bind=True)
def emergency_data_collection_task(
    self, match_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    紧急数据收集任务

    在发生异常情况时（如数据不一致、API失败等）触发的高优先级数据收集任务。
    立即收集指定比赛或全部关键数据，不等待定时任务。

    Args:
        match_id: 可选的特定比赛ID，如果不指定则收集所有关键数据

    Returns:
        Dict[str, Any]: 包含收集结果的字典

    Raises:
        Exception: 当数据收集过程中发生错误时
    """
    try:
        logger.warning(f"🚨 触发紧急数据收集任务 - Match ID: {match_id}")

        results = {}
        start_time = datetime.now()

        if match_id:
            # 针对特定比赛的紧急收集
            logger.info(f"针对比赛 {match_id} 进行紧急数据收集")

            # 高优先级收集该比赛的所有相关数据
            fixtures_task = collect_fixtures_task.apply_async(
                kwargs={"days_ahead": 1},
                priority=9,  # 最高优先级
            )
            odds_task = collect_odds_task.apply_async(priority=9)
            scores_task = collect_scores_task.apply_async(
                kwargs={"live_only": True}, priority=9
            )

            # 等待任务完成（较短超时时间）
            results["fixtures"] = fixtures_task.get(timeout=120)
            results["odds"] = odds_task.get(timeout=120)
            results["scores"] = scores_task.get(timeout=120)

        else:
            # 全量紧急收集
            logger.info("进行全量紧急数据收集")

            # 并行执行所有收集任务，使用高优先级
            fixtures_task = collect_fixtures_task.apply_async(
                kwargs={"days_ahead": 7}, priority=8
            )
            odds_task = collect_odds_task.apply_async(priority=8)
            scores_task = collect_scores_task.apply_async(priority=8)

            # 等待所有任务完成
            results["fixtures"] = fixtures_task.get(timeout=180)
            results["odds"] = odds_task.get(timeout=180)
            results["scores"] = scores_task.get(timeout=180)

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.warning(f"✅ 紧急数据收集任务完成 - 耗时: {execution_time:.2f}秒")

        return {
            "status": "success",
            "message": f"紧急数据收集任务完成 (Match ID: {match_id})",
            "results": results,
            "execution_time": execution_time,
            "priority": "emergency",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        error_msg = f"紧急数据收集任务失败: {str(exc)}"
        logger.error(error_msg)

        # 记录紧急任务失败（这是严重问题）
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.error_logger.log_task_error(
                    task_name="emergency_data_collection_task",
                    task_id=self.request.id,
                    error=exc,
                    context={
                        "match_id": match_id,
                        "emergency": True,
                        "severity": "critical",
                    },
                    retry_count=self.request.retries,
                )
            )
        except Exception as log_error:
            logger.critical(f"无法记录紧急任务失败日志: {str(log_error)}")

        return {
            "status": "failed",
            "error": error_msg,
            "match_id": match_id,
            "priority": "emergency",
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 数据收集器类（用于测试支持）
# =============================================================================


class FixturesCollector:
    """赛程数据收集器"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FixturesCollector")

    def collect_fixtures(self, days_ahead: int = 30, **kwargs) -> Dict[str, Any]:
        """收集赛程数据"""
        self.logger.info(f"开始收集未来 {days_ahead} 天的赛程数据")
        return {
            "status": "success",
            "fixtures_collected": 0,
            "days_ahead": days_ahead,
            "timestamp": datetime.now().isoformat(),
        }


@app.task(base=DataCollectionTask, bind=True)
def collect_historical_data_task(
    self,
    team_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    收集历史数据任务

    收集指定球队在指定时间段内的历史比赛数据，包括：
    - 比赛结果
    - 进球/失球统计
    - 赔率数据
    - 球员表现数据

    Args:
        team_id: 球队ID
        start_date: 开始日期 (YYYY-MM-DD格式)，默认为1年前
        end_date: 结束日期 (YYYY-MM-DD格式)，默认为当前日期
        data_types: 需要收集的数据类型列表，默认为所有类型

    Returns:
        Dict[str, Any]: 收集结果
            - status: 执行状态
            - team_id: 球队ID
            - matches: 收集的比赛数量
            - data_summary: 数据摘要（按类型统计）
            - execution_time: 执行时间
            - timestamp: 时间戳
    """
    logger.info(
        f"开始收集历史数据: team_id={team_id}, start_date={start_date}, end_date={end_date}"
    )

    # 设置默认日期范围
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if data_types is None:
        data_types = ["matches", "odds", "scores", "players"]

    async def _collect_historical_data():
        """内部异步收集函数"""
        try:
            # 动态导入以避免循环导入问题
            from src.data.collectors.scores_collector import ScoresCollector

            collector = ScoresCollector()

            logger.info(
                f"收集历史数据: 球队={team_id}, "
                f"时间范围={start_date} 到 {end_date}, "
                f"数据类型={data_types}"
            )

            # 执行收集
            result = await collector.collect_historical_matches(
                team_id=team_id,
                start_date=start_date,
                end_date=end_date,
                data_types=data_types,
            )

            return result

        except Exception as e:
            # 记录API失败
            if hasattr(self, "error_logger"):
                await self.error_logger.log_api_failure(
                    task_name="collect_historical_data_task",
                    api_endpoint="historical_data_api",
                    http_status=None,
                    error_message=str(e),
                    retry_count=self.request.retries if hasattr(self, "request") else 0,
                )
            raise e

    try:
        # 运行异步任务
        result = asyncio.run(_collect_historical_data())

        if isinstance(result, dict) and result.get("status") == "failed":
            raise Exception(
                f"历史数据收集失败: {result.get('error_message', '未知错误')}"
            )

        # 处理结果
        if isinstance(result, list):
            # 如果返回的是列表，转换为字典格式
            matches_collected = len(result)
            data_summary = {"matches": matches_collected}
        elif isinstance(result, dict):
            matches_collected = result.get("matches_collected", 0)
            data_summary = result.get("data_summary", {})
        else:
            matches_collected = getattr(result, "matches_collected", 0)
            data_summary = getattr(result, "data_summary", {})

        logger.info(
            f"历史数据收集完成: 球队={team_id}, "
            f"比赛数={matches_collected}, 数据摘要={data_summary}"
        )

        return {
            "status": "success",
            "team_id": team_id,
            "matches": matches_collected,
            "data_summary": data_summary,
            "start_date": start_date,
            "end_date": end_date,
            "data_types": data_types,
            "execution_time": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 获取重试配置（历史数据收集可以重试较多次数）
        retry_config = TaskRetryConfig.get_retry_config("collect_historical_data_task")
        max_retries = retry_config["max_retries"]
        retry_delay = retry_config["retry_delay"]

        # 检查是否需要重试
        if self.request.retries < max_retries:
            logger.warning(
                f"历史数据收集失败，将在{retry_delay}秒后重试 (第{self.request.retries + 1}次): {str(exc)}"
            )
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            # 最终失败，记录到错误日志
            logger.error(f"历史数据收集任务最终失败，已达最大重试次数: {str(exc)}")

            # 异步记录到数据采集日志
            asyncio.run(
                self.error_logger.log_data_collection_error(
                    data_source="historical_data_api",
                    collection_type="historical_matches",
                    error_message=str(exc),
                    error_count=1,
                    context={
                        "team_id": team_id,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
            )

            raise exc


# 为了向后兼容性，创建函数别名
collect_all_data_task = manual_collect_all_data


def validate_collected_data(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """
    验证收集的数据

    Args:
        data: 待验证的数据
        data_type: 数据类型

    Returns:
        Dict[str, Any]: 验证结果
    """
    result = {"is_valid": True, "errors": [], "warnings": []}

    try:
        if not data:
            result["is_valid"] = False
            result["errors"].append("数据为空")
            return result

        if data_type == "match":
            # 验证比赛数据
            required_fields = ["id", "home_team_id", "away_team_id", "start_time"]
            for field in required_fields:
                if field not in data:
                    result["errors"].append(f"缺少必填字段: {field}")
                    result["is_valid"] = False

        elif data_type == "team":
            # 验证球队数据
            required_fields = ["id", "name"]
            for field in required_fields:
                if field not in data:
                    result["errors"].append(f"缺少必填字段: {field}")
                    result["is_valid"] = False

        elif data_type == "odds":
            # 验证赔率数据
            required_fields = ["match_id", "home_win", "draw", "away_win"]
            for field in required_fields:
                if field not in data:
                    result["errors"].append(f"缺少必填字段: {field}")
                    result["is_valid"] = False
                else:
                    # 检查赔率值是否为正数
                    if field != "match_id" and data[field] <= 0:
                        result["errors"].append(f"赔率值必须为正数: {field}")
                        result["is_valid"] = False

    except Exception as e:
        result["is_valid"] = False
        result["errors"].append(f"验证过程出错: {str(e)}")

    return result
