"""
比分数据采集任务
Scores Collection Task

负责采集足球比分数据。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..celery_app import app
from .base import DataCollectionTask, CollectionTaskMixin

logger = logging.getLogger(__name__)


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
            await CollectionTaskMixin.log_api_failure(
                self, "collect_scores_task", "scores_api", e
            )
            raise e

    try:
        # 根据live_only决定是否跳过
        if live_only:
            # 检查是否有进行中的比赛（简化版检查）
            from ..utils import should_collect_live_scores

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
        # 检查是否需要重试（比分采集重试次数较少，因为时效性要求高）
        if not CollectionTaskMixin.handle_retry(self, exc, "collect_scores_task"):
            # 最终失败，记录到错误日志
            CollectionTaskMixin.log_data_collection_error(
                self,
                data_source="scores_api",
                collection_type="scores",
                error=exc,
            )

            raise exc