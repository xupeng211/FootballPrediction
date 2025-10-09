"""
历史数据采集任务
Historical Data Collection Task

负责采集历史比赛数据。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..celery_app import app
from .base import DataCollectionTask, CollectionTaskMixin

logger = logging.getLogger(__name__)


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
            await CollectionTaskMixin.log_api_failure(
                self, "collect_historical_data_task", "historical_data_api", e
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
        # 检查是否需要重试（历史数据收集可以重试较多次数）
        if not CollectionTaskMixin.handle_retry(self, exc, "collect_historical_data_task"):
            # 最终失败，记录到错误日志
            CollectionTaskMixin.log_data_collection_error(
                self,
                data_source="historical_data_api",
                collection_type="historical_matches",
                error=exc,
                team_id=team_id,
                start_date=start_date,
                end_date=end_date,
            )

            raise exc