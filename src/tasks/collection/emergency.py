"""
紧急数据采集任务
Emergency Data Collection Tasks

提供紧急情况下的数据采集功能。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..celery_app import app
from .base import DataCollectionTask

logger = logging.getLogger(__name__)


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

        # 导入任务
        from .fixtures import collect_fixtures_task
        from .odds import collect_odds_task
        from .scores import collect_scores_task

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

        # 导入任务
        from .fixtures import collect_fixtures_task
        from .odds import collect_odds_task
        from .scores import collect_scores_task

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