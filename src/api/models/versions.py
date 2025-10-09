"""
模型版本管理端点
Model Versions Endpoint

提供模型版本相关的API接口。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, Query
from mlflow import MlflowClient

from src.utils.response import APIResponse

logger = logging.getLogger(__name__)


async def get_model_versions(
    model_name: str,
    limit: int = Query(default=20, description="返回版本数量限制", ge=1, le=100),
    mlflow_client: MlflowClient = None,
) -> Dict[str, Any]:
    """
    获取模型版本列表

    Args:
        model_name: 模型名称
        limit: 返回版本数量限制
        mlflow_client: MLflow客户端

    Returns:
        API响应，包含模型版本信息
    """
    try:
        logger.info(f"获取模型 {model_name} 的版本列表")

        # 获取模型版本
        model_versions = mlflow_client.search_model_versions(
            filter_string=f"name='{model_name}'",
            max_results=limit,
            order_by=["version_number DESC"],
        )

        versions_info = []
        for version in model_versions:
            # 获取运行信息
            run_info = None
            if version.run_id:
                try:
                    run = mlflow_client.get_run(version.run_id)
                    run_info = {
                        "run_id": run.info.run_id,
                        "start_time": run.info.start_time,
                        "end_time": run.info.end_time,
                        "status": run.info.status,
                        "metrics": run.data.metrics,
                    }
                except Exception as e:
                    logger.warning(f"无法获取版本 {version.version} 的运行信息: {e}")

            version_info = {
                "version": version.version,
                "creation_timestamp": version.creation_timestamp,
                "created_at": version.creation_timestamp,
                "last_updated_timestamp": version.last_updated_timestamp,
                "description": version.description,
                "user_id": version.user_id,
                "current_stage": version.current_stage,
                "stage": version.current_stage,
                "source": version.source,
                "tags": version.tags,
                "status": version.status,
                "run_info": run_info,
            }
            versions_info.append(version_info)

        return APIResponse.success(
            data={
                "model_name": model_name,
                "total_versions": len(versions_info),
                "versions": versions_info,
            }
        )

    except Exception as e:
        logger.error(f"获取模型版本失败: {e}")
        raise HTTPException(status_code=500, detail={"error": "获取模型版本失败"})


async def promote_model_version(
    model_name: str,
    version: str,
    target_stage: str = Query(
        "Production", description="目标阶段：Staging, Production"
    ),
    mlflow_client: MlflowClient = None,
) -> Dict[str, Any]:
    """
    推广模型版本到指定阶段

    Args:
        model_name: 模型名称
        version: 版本号
        target_stage: 目标阶段
        mlflow_client: MLflow客户端

    Returns:
        API响应，包含推广结果
    """
    try:
        logger.info(f"推广模型 {model_name} 版本 {version} 到 {target_stage} 阶段")

        if target_stage not in ["Staging", "Production"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "目标阶段必须是 Staging 或 Production"},
            )

        # 验证版本存在
        try:
            model_version = mlflow_client.get_model_version(
                name=model_name, version=version
            )
        except Exception:
            raise HTTPException(
                status_code=404,
                detail={"error": f"模型版本 {model_name}:{version} 不存在"},
            )

        # 推广模型版本
        mlflow_client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=target_stage,
            archive_existing_versions=(
                target_stage == "Production"
            ),  # 生产环境时归档现有版本
        )

        # 获取更新后的版本信息
        updated_version = mlflow_client.get_model_version(
            name=model_name, version=version
        )

        return APIResponse.success(
            data={
                "model_name": model_name,
                "version": version,
                "previous_stage": model_version.current_stage,
                "current_stage": updated_version.current_stage,
                "promoted_at": datetime.now().isoformat(),
            },
            message=f"模型版本已成功推广到 {target_stage} 阶段",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推广模型版本失败: {e}")
        raise HTTPException(status_code=500, detail={"error": "推广模型版本失败"})