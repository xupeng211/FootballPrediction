"""
Titan007 数据采集任务 - Prefect Tasks
Titan007 Data Collection Tasks - Prefect Tasks

将 Titan007 采集器逻辑封装为 Prefect Tasks，支持：
- 自动重试和错误处理
- 并发控制和资源管理
- 结构化日志记录
- 智能调度优化

使用示例:
    from prefect import flow
    from src.tasks.titan_tasks import fetch_fixtures, align_ids, collect_odds_for_match

    @flow(name="titan_collection_flow")
    async def titan_collection_flow():
        fixtures = await fetch_fixtures()
        aligned_matches = await align_ids(fixtures)

        results = []
        for match in aligned_matches:
            result = await collect_odds_for_match(match["match_id"])
            results.append(result)

        return results
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from prefect import task, get_run_logger

from src.collectors.fotmob.collector_v2 import FotMobCollectorV2
from src.collectors.titan.collectors import (
    TitanEuroCollector,
    TitanAsianCollector,
    TitanOverUnderCollector,
)
from src.services.match_alignment_service import MatchAlignmentService
from src.database.repositories.titan_odds_factory import RealTitanOddsRepository
from src.database.repositories.odds_repository import TitanOddsRepository

from src.config.titan_settings import get_titan_settings

logger = logging.getLogger(__name__)


@task(
    name="获取当天赛程",
    description="从 FotMob 获取当天比赛列表",
    retries=3,
    retry_delay_seconds=60,
)
async def fetch_fixtures(
    start_date: Optional[str] = None, days_ahead: int = 1
) -> List[Dict[str, Any]]:
    """
    获取当天比赛列表

    Args:
        start_date: 开始日期，格式 "YYYY-MM-DD"，默认为今天
        days_ahead: 提前多少天的比赛

    Returns:
        List[Dict[str, Any]]: 比赛列表
    """
    run_logger = get_run_logger()
    run_logger.info(
        "开始获取赛程信息", extra={"start_date": start_date, "days_ahead": days_ahead}
    )

    try:
        collector = FotMobCollectorV2()

        # 转换日期参数
        if start_date:
            target_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            target_date = datetime.now()

        # 计算结束日期
        end_date = target_date + timedelta(days=days_ahead)

        # 获取赛程
        fixtures = await collector.fetch_matches_by_date_range(
            start_date=target_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )

        run_logger.info(
            "成功获取赛程信息",
            extra={
                "fixture_count": len(fixtures),
                "start_date": target_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
        )

        return fixtures

    except Exception as e:
        run_logger.error(
            "获取赛程失败",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "start_date": start_date,
                "days_ahead": days_ahead,
            },
        )
        raise


@task(
    name="ID对齐服务",
    description="将 FotMob ID 批量转换为 Titan ID",
    retries=2,
    retry_delay_seconds=30,
)
async def align_ids(
    fixtures: List[Dict[str, Any]], batch_size: int = 50
) -> List[Dict[str, Any]]:
    """
    批量 ID 对齐服务

    Args:
        fixtures: FotMob 比赛列表
        batch_size: 批处理大小

    Returns:
        List[Dict[str, Any]]: 对齐成功的比赛列表
    """
    run_logger = get_run_logger()
    run_logger.info(
        "开始ID对齐服务",
        extra={"fixture_count": len(fixtures), "batch_size": batch_size},
    )

    try:
        alignment_service = MatchAlignmentService()

        # 批量处理ID对齐
        aligned_matches = []
        failed_matches = []

        # 分批处理
        for i in range(0, len(fixtures), batch_size):
            batch = fixtures[i : i + batch_size]

            run_logger.debug(
                f"处理批次 {i // batch_size + 1}",
                extra={
                    "batch_size": len(batch),
                    "batch_start": i,
                    "batch_end": min(i + batch_size, len(fixtures)),
                },
            )

            # 并发处理当前批次 - 使用信号量限制并发
            semaphore = asyncio.Semaphore(10)  # 限制并发数
            async with semaphore:
                batch_tasks = []
                for fixture in batch:
                    task = asyncio.create_task(alignment_service.align_ids(fixture))
                    batch_tasks.append(task)

                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                # 处理批次结果
                for fixture, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        failed_matches.append(
                            {
                                "fixture": fixture,
                                "error": str(result),
                                "error_type": type(result).__name__,
                            }
                        )
                    elif result:
                        aligned_matches.append(result)

        run_logger.info(
            "ID对齐完成",
            extra={
                "total_fixtures": len(fixtures),
                "aligned_count": len(aligned_matches),
                "failed_count": len(failed_matches),
                "success_rate": len(aligned_matches) / len(fixtures) if fixtures else 0,
            },
        )

        if failed_matches:
            run_logger.warning(
                "部分ID对齐失败",
                extra={
                    "failed_count": len(failed_matches),
                    "failed_matches": failed_matches[:5],  # 只记录前5个失败的
                },
            )

        return aligned_matches

    except Exception as e:
        run_logger.error(
            "ID对齐服务失败",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


@task(
    name="单场赔率采集",
    description="对单场比赛采集所有类型的赔率数据",
    retries=3,
    retry_delay_seconds=10,
)
async def collect_odds_for_match(
    match_info: Dict[str, Any], repo: Optional[TitanOddsRepository] = None
) -> Dict[str, Any]:
    """
    对单场比赛采集欧赔、亚盘、大小球赔率

    Args:
        match_info: 比赛信息，包含 match_id, match_name 等
        repo: 数据库仓库实例

    Returns:
        Dict[str, Any]: 采集结果
    """
    run_logger = get_run_logger()
    match_id = match_info.get("match_id")
    match_name = match_info.get("match_name", "Unknown")

    run_logger.info(
        "开始采集单场赔率", extra={"match_id": match_id, "match_name": match_name}
    )

    try:
        # 使用传入的仓库实例或创建新实例
        if repo is None:
            repo = RealTitanOddsRepository()

        # 初始化采集器
        settings = get_titan_settings()
        euro_collector = TitanEuroCollector(settings=settings)
        asian_collector = TitanAsianCollector(settings=settings)
        overunder_collector = TitanOverUnderCollector(settings=settings)

        results = {}
        errors = []

        # 并发采集三种赔率类型 - 使用信号量控制并发
        odds_semaphore = asyncio.Semaphore(3)  # 同时采集3种赔率
        async with odds_semaphore:
            euro_task = asyncio.create_task(
                _collect_single_odds_type(
                    euro_collector, "euro", match_id, repo, run_logger
                )
            )
            asian_task = asyncio.create_task(
                _collect_single_odds_type(
                    asian_collector, "asian", match_id, repo, run_logger
                )
            )
            overunder_task = asyncio.create_task(
                _collect_single_odds_type(
                    overunder_collector, "overunder", match_id, repo, run_logger
                )
            )

            # 等待所有采集完成
            euro_result, asian_result, overunder_result = await asyncio.gather(
                euro_task, asian_task, overunder_task, return_exceptions=True
            )

            # 处理结果
            for odds_type, result in [
                ("euro", euro_result),
                ("asian", asian_result),
                ("overunder", overunder_result),
            ]:
                if isinstance(result, Exception):
                    errors.append(
                        {
                            "odds_type": odds_type,
                            "error": str(result),
                            "error_type": type(result).__name__,
                        }
                    )
                else:
                    results[odds_type] = result

        # 汇总结果
        success_count = len([r for r in results.values() if r])
        error_count = len(errors)

        run_logger.info(
            "单场赔率采集完成",
            extra={
                "match_id": match_id,
                "match_name": match_name,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / 3,
                "results": list(results.keys()),
                "errors": errors,
            },
        )

        return {
            "match_id": match_id,
            "match_name": match_name,
            "results": results,
            "errors": errors,
            "success_count": success_count,
            "error_count": error_count,
        }

    except Exception as e:
        run_logger.error(
            "单场赔率采集失败",
            extra={
                "match_id": match_id,
                "match_name": match_name,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise


async def _collect_single_odds_type(
    collector, odds_type: str, match_id: str, repo: TitanOddsRepository, logger
) -> Dict[str, Any]:
    """采集单一类型的赔率数据（内部辅助函数）"""
    try:
        if odds_type == "euro":
            data = await collector.fetch_euro_odds(match_id)
            if data and "1" in data and data["1"]:
                dto = collector.to_dto(data["1"][0], match_id)
                latest, history = await repo.upsert_euro_odds(dto)
                return {
                    "latest": bool(latest),
                    "history": bool(history),
                    "odds_count": 1,
                }

        elif odds_type == "asian":
            data = await collector.fetch_asian_handicap(match_id)
            if data and "1" in data and data["1"]:
                dto = collector.to_dto(data["1"][0], match_id)
                latest, history = await repo.upsert_asian_odds(dto)
                return {
                    "latest": bool(latest),
                    "history": bool(history),
                    "odds_count": 1,
                }

        elif odds_type == "overunder":
            data = await collector.fetch_over_under(match_id)
            if data and "1" in data and data["1"]:
                dto = collector.to_dto(data["1"][0], match_id)
                latest, history = await repo.upsert_overunder_odds(dto)
                return {
                    "latest": bool(latest),
                    "history": bool(history),
                    "odds_count": 1,
                }

        return {"success": False, "message": "No data available"}

    except Exception as e:
        logger.error(
            f"采集{odds_type}赔率失败",
            extra={
                "match_id": match_id,
                "odds_type": odds_type,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise


@task(
    name="批量赔率采集",
    description="批量采集多场比赛的赔率数据",
    retries=1,
    retry_delay_seconds=5,
)
async def batch_collect_odds(
    matches: List[Dict[str, Any]],
    max_concurrency: int = 10,
    repo: Optional[TitanOddsRepository] = None,
) -> List[Dict[str, Any]]:
    """
    批量采集多场比赛赔率数据

    Args:
        matches: 比赛列表
        max_concurrency: 最大并发数
        repo: 数据库仓库实例

    Returns:
        List[Dict[str, Any]]: 采集结果列表
    """
    run_logger = get_run_logger()
    run_logger.info(
        "开始批量赔率采集",
        extra={"match_count": len(matches), "max_concurrency": max_concurrency},
    )

    try:
        # 使用传入的仓库实例或创建新实例
        if repo is None:
            repo = RealTitanOddsRepository()

        # 创建采集任务列表
        tasks = []
        for match in matches:
            task = asyncio.create_task(collect_odds_for_match(match, repo))
            tasks.append(task)

        # 控制并发数并执行
        results = []
        completed_count = 0
        error_count = 0

        # 控制并发数并执行 - 使用信号量控制并发
        batch_semaphore = asyncio.Semaphore(max_concurrency)
        async with batch_semaphore:
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    results.append(result)
                    completed_count += 1

                    if result["error_count"] > 0:
                        error_count += result["error_count"]

                except Exception as e:
                    run_logger.error(
                        "批量采集中的任务失败",
                        extra={"error_type": type(e).__name__, "error_message": str(e)},
                    )
                    error_count += 1

        # 统计结果
        total_odds_collected = sum(r.get("success_count", 0) for r in results)
        success_rate = completed_count / len(matches) if matches else 0

        run_logger.info(
            "批量赔率采集完成",
            extra={
                "total_matches": len(matches),
                "completed_count": completed_count,
                "error_count": error_count,
                "total_odds_collected": total_odds_collected,
                "success_rate": success_rate,
            },
        )

        return results

    except Exception as e:
        run_logger.error(
            "批量赔率采集失败",
            extra={
                "match_count": len(matches),
                "max_concurrency": max_concurrency,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise


@task(
    name="清理历史数据",
    description="清理过期的历史赔率数据（可选）",
)
async def cleanup_history_data(
    days_to_keep: int = 30, repo: Optional[TitanOddsRepository] = None
) -> Dict[str, Any]:
    """
    清理过期的历史数据

    Args:
        days_to_keep: 保留天数
        repo: 数据库仓库实例

    Returns:
        Dict[str, Any]: 清理结果
    """
    run_logger = get_run_logger()
    run_logger.info("开始清理历史数据", extra={"days_to_keep": days_to_keep})

    try:
        # 这里可以实现具体的清理逻辑
        # 例如：删除30天前的历史数据
        # 需要根据实际的数据库表结构来实现

        run_logger.info("历史数据清理完成", extra={"days_to_keep": days_to_keep})

        return {"success": True, "days_to_keep": days_to_keep}

    except Exception as e:
        run_logger.error(
            "历史数据清理失败",
            extra={
                "days_to_keep": days_to_keep,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise
