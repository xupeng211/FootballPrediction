"""
数据采集任务
Data Collection Tasks

包含赛程采集、赔率采集和实时比分采集任务。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from celery import Task

from src.data.collectors.fixtures_collector import FixturesCollector
from src.data.collectors.odds_collector import OddsCollector
from src.data.collectors.scores_collector import ScoresCollector

from .base import BaseDataTask
from ..celery_config import app, should_collect_live_scores

logger = logging.getLogger(__name__)


@app.task(base=BaseDataTask, bind=True)
def collect_fixtures(self, leagues: Optional[List[str]] = None, days_ahead: int = 30):
    """
    采集赛程数据任务

    Args:
        leagues: 需要采集的联赛列表
        days_ahead: 采集未来N天的赛程
    """
    async def _collect_task():
        # 初始化赛程采集器
        collector = FixturesCollector()

        # 设置采集时间范围
        date_from = datetime.now()
        date_to = date_from + timedelta(days=days_ahead)

        # 执行采集
        result = await collector.collect_fixtures(
            leagues=leagues, date_from=date_from, date_to=date_to
        )
        return result

    try:
        logger.info("开始执行赛程采集任务")
        result = asyncio.run(_collect_task())

        if result.status == "failed":
            raise Exception(f"赛程采集失败: {result.error_message}")

        logger.info(
            f"赛程采集完成: 成功={result.success_count}, 错误={result.error_count}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 重试逻辑
        retry_config = self.get_retry_config("collect_fixtures")
        max_retries = retry_config.get("max_retries", 3)
        retry_delay = retry_config.get("retry_delay", 60)

        if self.request.retries < max_retries:
            logger.warning(f"赛程采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"赛程采集任务最终失败: {str(exc)}")
            raise


@app.task(base=BaseDataTask, bind=True)
def collect_odds(
    self, match_ids: Optional[List[str]] = None, bookmakers: Optional[List[str]] = None
):
    """
    采集赔率数据任务

    Args:
        match_ids: 需要采集的比赛ID列表
        bookmakers: 博彩公司列表
    """
    async def _collect_task():
        # 初始化赔率采集器
        collector = OddsCollector()

        # 执行采集
        result = await collector.collect_odds(
            match_ids=match_ids, bookmakers=bookmakers
        )
        return result

    try:
        logger.info("开始执行赔率采集任务")
        result = asyncio.run(_collect_task())

        if result.status == "failed":
            raise Exception(f"赔率采集失败: {result.error_message}")

        logger.info(
            f"赔率采集完成: 成功={result.success_count}, 错误={result.error_count}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 重试逻辑
        retry_config = self.get_retry_config("collect_odds")
        max_retries = retry_config.get("max_retries", 3)
        retry_delay = retry_config.get("retry_delay", 60)

        if self.request.retries < max_retries:
            logger.warning(f"赔率采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"赔率采集任务最终失败: {str(exc)}")
            raise


@app.task(base=BaseDataTask, bind=True)
def collect_live_scores_conditional(self, match_ids: Optional[List[str]] = None):
    """
    条件性实时比分采集任务（仅在有比赛时执行）

    Args:
        match_ids: 需要监控的比赛ID列表
    """
    async def _collect_task():
        # 初始化比分采集器
        collector = ScoresCollector()

        # 执行采集
        result = await collector.collect_live_scores(
            match_ids=match_ids, use_websocket=True
        )
        return result

    try:
        # 检查是否需要采集实时比分
        if not should_collect_live_scores():
            logger.info("当前无进行中的比赛，跳过实时比分采集")
            return {
                "status": "skipped",
                "reason": "no_active_matches",
                "execution_time": datetime.now().isoformat(),
            }

        logger.info("开始执行实时比分采集任务")
        result = asyncio.run(_collect_task())

        if result.status == "failed":
            raise Exception(f"实时比分采集失败: {result.error_message}")

        logger.info(
            f"实时比分采集完成: 成功={result.success_count}, 错误={result.error_count}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 实时比分采集重试次数较少，因为时效性要求高
        retry_config = self.get_retry_config("collect_live_scores")
        max_retries = retry_config.get("max_retries", 1)
        retry_delay = retry_config.get("retry_delay", 30)

        if self.request.retries < max_retries:
            logger.warning(f"实时比分采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"实时比分采集任务最终失败: {str(exc)}")
            raise