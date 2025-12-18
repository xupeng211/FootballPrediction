"""
Titan007 自动化调度工作流
Titan007 Automated Scheduling Flow

实现智能调度策略：
- 常规模式：每天 08:00 运行，获取初盘数据
- 临场模式：筛选未来 2 小时内开赛的比赛，每 10 分钟运行一次采集
- 智能重试和错误处理
- 完整的日志记录和监控

使用示例:
    # 运行常规模式
    python scripts/deploy_flow.py --run

    # 运行临场模式
    python scripts/deploy_flow.py --run --live
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from prefect import flow
from prefect.server.schemas.schedules import CronSchedule

from src.tasks.titan_tasks import (
    fetch_fixtures,
    align_ids,
    batch_collect_odds,
    cleanup_history_data,
)
from src.config.titan_settings import get_titan_settings

# 设置日志
import logging

logger = logging.getLogger(__name__)


def _filter_upcoming_matches(
    fixtures: List[Dict[str, Any]], hours_ahead: int = 2
) -> List[Dict[str, Any]]:
    """
    筛选未来指定小时内开赛的比赛

    Args:
        fixtures: 比赛列表
        hours_ahead: 小时数（默认2小时）

    Returns:
        List[Dict[str, Any]]: 即将开始的比赛列表
    """
    try:
        now = datetime.now()
        cutoff_time = now + timedelta(hours=hours_ahead)

        upcoming_matches = []
        for fixture in fixtures:
            match_date = fixture.get("match_date")
            if match_date:
                # 解析比赛日期
                if isinstance(match_date, str):
                    match_datetime = datetime.fromisoformat(
                        match_date.replace("Z", "+00:00")
                    )
                else:
                    match_datetime = match_date

                # 筛选即将开始的比赛
                if now <= match_datetime <= cutoff_time:
                    upcoming_matches.append(fixture)

        logger.info(
            "筛选即将开始的比赛",
            extra={
                "total_fixtures": len(fixtures),
                "upcoming_matches": len(upcoming_matches),
                "hours_ahead": hours_ahead,
                "cutoff_time": cutoff_time.isoformat(),
            },
        )

        return upcoming_matches

    except Exception as e:
        logger.error(
            "筛选即将开始的比赛失败",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        return []


@flow(
    name="Titan007 常规数据采集",
    description="每天运行一次，获取当天比赛的初盘数据",
    retries=1,
    retry_delay_seconds=300,
)
async def titan_regular_flow(
    start_date: Optional[str] = None,
    days_ahead: int = 1,
    batch_size: int = 20,
    max_concurrency: int = 15,
) -> Dict[str, Any]:
    """
    Titan007 常规数据采集工作流

    流程：
    1. 获取当天赛程
    2. ID 对齐
    3. 批量采集赔率数据
    4. （可选）清理历史数据

    Args:
        start_date: 开始日期，格式 "YYYY-MM-DD"，默认为今天
        days_ahead: 提前多少天的比赛
        batch_size: ID对齐的批处理大小
        max_concurrency: 并发采集比赛数

    Returns:
        Dict[str, Any]: 执行结果统计
    """
    run_logger = flow.get_run_logger()
    settings = get_titan_settings()

    run_logger.info(
        "🚀 开始 Titan007 常规数据采集工作流",
        extra={
            "start_date": start_date,
            "days_ahead": days_ahead,
            "batch_size": batch_size,
            "max_concurrency": max_concurrency,
            "flow_run_id": flow.id,
        },
    )

    try:
        flow_start_time = datetime.now()
        results = {
            "flow_type": "regular",
            "start_time": flow_start_time.isoformat(),
            "fixtures": 0,
            "aligned": 0,
            "collected": 0,
            "errors": 0,
            "total_odds": 0,
        }

        # Step 1: 获取赛程
        run_logger.info("📋 Step 1: 获取当天赛程")
        fixtures = await fetch_fixtures(start_date=start_date, days_ahead=days_ahead)
        results["fixtures"] = len(fixtures)

        if not fixtures:
            run_logger.warning("⚠️ 没有找到比赛数据，流程结束")
            return results

        # Step 2: ID 对齐
        run_logger.info("🔗 Step 2: 执行 ID 对齐")
        aligned_matches = await align_ids(fixtures, batch_size=batch_size)
        results["aligned"] = len(aligned_matches)

        if not aligned_matches:
            run_logger.warning("⚠️ 没有对齐成功的比赛，流程结束")
            return results

        # Step 3: 批量采集赔率
        run_logger.info("📊 Step 3: 批量采集赔率数据")
        collection_results = await batch_collect_odds(
            matches=aligned_matches, max_concurrency=max_concurrency
        )
        results["collected"] = len(collection_results)

        # 统计赔率采集结果
        total_odds = sum(r.get("success_count", 0) for r in collection_results)
        results["total_odds"] = total_odds
        results["errors"] = sum(r.get("error_count", 0) for r in collection_results)

        # Step 4: 清理历史数据（可选）
        try:
            run_logger.info("🧹 Step 4: 清理历史数据")
            cleanup_result = await cleanup_history_data(
                days_to_keep=settings.db_pool.pool_recycle // 3600
            )  # 转换为天数
            results["cleanup"] = cleanup_result
        except Exception as e:
            run_logger.warning(
                "历史数据清理失败，但流程继续",
                extra={"error_type": type(e).__name__, "error_message": str(e)},
            )

        # 计算执行时间
        flow_end_time = datetime.now()
        execution_time = (flow_end_time - flow_start_time).total_seconds()

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "execution_time_seconds": execution_time,
                "success_rate": results["total_odds"] / (results["collected"] * 3)
                if results["collected"] > 0
                else 0,
            }
        )

        run_logger.info(
            "✅ Titan007 常规数据采集工作流完成",
            extra={
                "fixtures": results["fixtures"],
                "aligned": results["aligned"],
                "collected": results["collected"],
                "total_odds": results["total_odds"],
                "errors": results["errors"],
                "execution_time_seconds": results["execution_time_seconds"],
                "success_rate": results["success_rate"],
            },
        )

        return results

    except Exception as e:
        run_logger.error(
            "❌ Titan007 常规数据采集工作流失败",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


@flow(
    name="Titan007 临场数据采集",
    description="每10分钟运行一次，采集即将开赛比赛的最新赔率",
    retries=2,
    retry_delay_seconds=60,
)
async def titan_live_flow(
    hours_ahead: int = 2, batch_size: int = 10, max_concurrency: int = 8
) -> Dict[str, Any]:
    """
    Titan007 临场数据采集工作流

    流程：
    1. 获取未来几小时内的比赛
    2. ID 对齐
    3. 批量采集赔率数据
    4. 专注最新数据（不清理历史数据）

    Args:
        hours_ahead: 提前多少小时筛选比赛
        batch_size: ID对齐的批处理大小
        max_concurrency: 并发采集比赛数

    Returns:
        Dict[str, Any]: 执行结果统计
    """
    run_logger = flow.get_run_logger()

    run_logger.info(
        "🚀 开始 Titan007 临场数据采集工作流",
        extra={
            "hours_ahead": hours_ahead,
            "batch_size": batch_size,
            "max_concurrency": max_concurrency,
            "flow_run_id": flow.id,
        },
    )

    try:
        flow_start_time = datetime.now()
        results = {
            "flow_type": "live",
            "start_time": flow_start_time.isoformat(),
            "total_fixtures": 0,
            "upcoming_fixtures": 0,
            "aligned": 0,
            "collected": 0,
            "errors": 0,
            "total_odds": 0,
        }

        # Step 1: 获取当天赛程
        run_logger.info("📋 Step 1: 获取当天赛程")
        fixtures = await fetch_fixtures(days_ahead=hours_ahead)
        results["total_fixtures"] = len(fixtures)

        if not fixtures:
            run_logger.warning("⚠️ 没有找到比赛数据，流程结束")
            return results

        # Step 1.5: 筛选即将开始的比赛
        run_logger.info("⏰ Step 1.5: 筛选即将开始的比赛")
        upcoming_fixtures = _filter_upcoming_matches(fixtures, hours_ahead)
        results["upcoming_fixtures"] = len(upcoming_fixtures)

        if not upcoming_fixtures:
            run_logger.info("✅ 没有即将开始的比赛，流程结束")
            return results

        # Step 2: ID 对齐
        run_logger.info("🔗 Step 2: 执行 ID 对齐")
        aligned_matches = await align_ids(upcoming_fixtures, batch_size=batch_size)
        results["aligned"] = len(aligned_matches)

        if not aligned_matches:
            run_logger.warning("⚠️ 没有对齐成功的比赛，流程结束")
            return results

        # Step 3: 批量采集赔率
        run_logger.info("📊 Step 3: 批量采集最新赔率数据")
        collection_results = await batch_collect_odds(
            matches=aligned_matches, max_concurrency=max_concurrency
        )
        results["collected"] = len(collection_results)

        # 统计赔率采集结果
        total_odds = sum(r.get("success_count", 0) for r in collection_results)
        results["total_odds"] = total_odds
        results["errors"] = sum(r.get("error_count", 0) for r in collection_results)

        # 计算执行时间
        flow_end_time = datetime.now()
        execution_time = (flow_end_time - flow_start_time).total_seconds()

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "execution_time_seconds": execution_time,
                "success_rate": results["total_odds"] / (results["collected"] * 3)
                if results["collected"] > 0
                else 0,
                "odds_per_second": results["total_odds"] / execution_time
                if execution_time > 0
                else 0,
            }
        )

        run_logger.info(
            "✅ Titan007 临场数据采集工作流完成",
            extra={
                "total_fixtures": results["total_fixtures"],
                "upcoming_fixtures": results["upcoming_fixtures"],
                "aligned": results["aligned"],
                "collected": results["collected"],
                "total_odds": results["total_odds"],
                "errors": results["errors"],
                "execution_time_seconds": results["execution_time_seconds"],
                "success_rate": results["success_rate"],
                "odds_per_second": results["odds_per_second"],
            },
        )

        return results

    except Exception as e:
        run_logger.error(
            "❌ Titan007 临场数据采集工作流失败",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


@flow(
    name="Titan007 混合数据采集",
    description="结合常规模式和临场模式的混合调度",
    retries=1,
    retry_delay_seconds=300,
)
async def titan_hybrid_flow(
    regular_hours_ahead: int = 1,
    live_hours_ahead: int = 2,
    enable_live: bool = True,
    cleanup_days: int = 7,
) -> Dict[str, Any]:
    """
    Titan007 混合数据采集工作流

    先执行常规模式获取全天数据，然后启动临场模式进行实时更新。

    Args:
        regular_hours_ahead: 常规模式的提前天数
        live_hours_ahead: 临场模式的提前小时数
        enable_live: 是否启用临场模式
        cleanup_days: 历史数据保留天数

    Returns:
        Dict[str, Any]: 执行结果统计
    """
    run_logger = flow.get_run_logger()

    run_logger.info(
        "🚀 开始 Titan007 混合数据采集工作流",
        extra={
            "regular_hours_ahead": regular_hours_ahead,
            "live_hours_ahead": live_hours_ahead,
            "enable_live": enable_live,
            "cleanup_days": cleanup_days,
            "flow_run_id": flow.id,
        },
    )

    try:
        flow_start_time = datetime.now()
        results = {
            "flow_type": "hybrid",
            "start_time": flow_start_time.isoformat(),
            "regular_results": {},
            "live_results": {},
            "cleanup_results": {},
            "total_odds": 0,
        }

        # 执行常规模式
        run_logger.info("📋 执行常规数据采集模式")
        regular_results = await titan_regular_flow(days_ahead=regular_hours_ahead)
        results["regular_results"] = regular_results
        results["total_odds"] += regular_results.get("total_odds", 0)

        # 启动临场模式
        if enable_live:
            run_logger.info("⚡ 启动临场数据采集模式")
            live_results = await titan_live_flow(hours_ahead=live_hours_ahead)
            results["live_results"] = live_results
            results["total_odds"] += live_results.get("total_odds", 0)

        # 清理历史数据
        if cleanup_days > 0:
            run_logger.info("🧹 清理历史数据")
            cleanup_results = await cleanup_history_data(days_to_keep=cleanup_days)
            results["cleanup_results"] = cleanup_results

        # 计算总体统计
        flow_end_time = datetime.now()
        execution_time = (flow_end_time - flow_start_time).total_seconds()

        results.update(
            {
                "end_time": flow_end_time.isoformat(),
                "execution_time_seconds": execution_time,
                "total_odds": results["total_odds"],
                "regular_odds": regular_results.get("total_odds", 0),
                "live_odds": live_results.get("total_odds", 0) if enable_live else 0,
            }
        )

        run_logger.info(
            "✅ Titan007 混合数据采集工作流完成",
            extra={
                "regular_odds": results["regular_odds"],
                "live_odds": results["live_odds"],
                "total_odds": results["total_odds"],
                "execution_time_seconds": results["execution_time_seconds"],
                "cleanup_days": cleanup_days,
            },
        )

        return results

    except Exception as e:
        run_logger.error(
            "❌ Titan007 混合数据采集工作流失败",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


# 调度配置
titan_regular_schedule = CronSchedule(
    cron="0 8 * * *",  # 每天早上8点
    timezone="Asia/Shanghai",
)

titan_live_schedule = CronSchedule(
    cron="*/10 * * * *",  # 每10分钟
    timezone="Asia/Shanghai",
)

# 增强型调度配置
titan_weekend_schedule = CronSchedule(
    cron="0 9 * * 6",  # 周六早上9点
    timezone="Asia/Shanghai",
)

# 智能调度策略 - 基于比赛密度的动态调度
titan_smart_schedule = CronSchedule(
    cron="0 */2 * * *",  # 每2小时检查一次
    timezone="Asia/Shanghai",
)

# 赛季高峰期调度 - 重要比赛窗口期
titan_peak_season_schedule = CronSchedule(
    cron="30 7,12,18 * * 1,5",  # 周一和周五的7:30, 12:30, 18:30
    timezone="Asia/Shanghai",
)

# 清理任务调度 - 每周日凌晨2点运行
titan_cleanup_schedule = CronSchedule(
    cron="0 2 * * 0",  # 每周日凌晨2点
    timezone="Asia/Shanghai",
)
