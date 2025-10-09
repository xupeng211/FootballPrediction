"""
实验管理端点
Experiments Endpoint

提供MLflow实验管理的API接口。
"""

import logging
from typing import Any, Dict

from fastapi import HTTPException, Query
from mlflow import MlflowClient

from src.utils.response import APIResponse

logger = logging.getLogger(__name__)


async def get_experiments(
    limit: int = Query(default=20, description="返回实验数量限制", ge=1, le=100),
    mlflow_client: MlflowClient = None,
) -> Dict[str, Any]:
    """
    获取MLflow实验列表

    Args:
        limit: 返回实验数量限制
        mlflow_client: MLflow客户端

    Returns:
        API响应，包含实验列表
    """
    try:
        logger.info("获取MLflow实验列表")

        # 获取实验列表
        experiments = mlflow_client.search_experiments(
            max_results=limit, order_by=["creation_time DESC"]
        )

        experiment_list = []
        for experiment in experiments:
            experiment_info = {
                "experiment_id": experiment.experiment_id,
                "name": experiment.name,
                "artifact_location": experiment.artifact_location,
                "lifecycle_stage": experiment.lifecycle_stage,
                "creation_time": experiment.creation_time,
                "last_update_time": experiment.last_update_time,
                "tags": experiment.tags,
            }
            experiment_list.append(experiment_info)

        return APIResponse.success(
            data={"experiments": experiment_list, "count": len(experiment_list)}
        )

    except Exception as e:
        logger.error(f"获取实验列表失败: {e}")
        raise HTTPException(status_code=500, detail={"error": "获取实验列表失败"})