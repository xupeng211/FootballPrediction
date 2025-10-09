"""
活跃模型端点
Active Models Endpoint

提供获取当前活跃模型信息的API接口。
"""

import logging
from typing import Any, Dict

from fastapi import HTTPException
from mlflow import MlflowClient

from src.utils.response import APIResponse

logger = logging.getLogger(__name__)


async def get_active_models(mlflow_client: MlflowClient) -> Dict[str, Any]:
    """
    获取当前生产环境使用的模型版本

    Args:
        mlflow_client: MLflow客户端

    Returns:
        API响应，包含活跃模型信息
    """
    try:
        logger.info("获取当前活跃模型信息")

        # 获取所有注册模型
        try:
            registered_models = mlflow_client.search_registered_models()
        except Exception as e:
            logger.error(f"无法连接到MLflow服务: {e}")
            raise HTTPException(status_code=500, detail={"error": "获取活跃模型失败"})

        active_models = []

        # 验证MLflow服务状态
        try:
            mlflow_client.get_latest_versions(
                name="__health_check__", stages=["Production"]
            )
        except RuntimeError as e:
            logger.error(f"MLflow服务不可用: {e}")
            raise HTTPException(
                status_code=500, detail={"error": f"MLflow服务错误: {str(e)}"}
            )
        except Exception:
            # 其他异常（如模型不存在）是正常的，忽略
            pass

        for registered_model in registered_models:
            model_name = registered_model.name

            # 获取生产阶段的最新版本
            try:
                production_versions = mlflow_client.get_latest_versions(
                    name=model_name, stages=["Production"]
                )

                # 如果没有生产版本，检查Staging版本
                if not production_versions:
                    staging_versions = mlflow_client.get_latest_versions(
                        name=model_name, stages=["Staging"]
                    )
                    if staging_versions:
                        production_versions = staging_versions
                        logger.warning(
                            f"模型 {model_name} 没有生产版本，使用Staging版本"
                        )

                # 如果还是没有，获取最新版本
                if not production_versions:
                    all_versions = mlflow_client.get_latest_versions(name=model_name)
                    if all_versions:
                        production_versions = all_versions
                        logger.warning(
                            f"模型 {model_name} 没有指定阶段版本，使用最新版本"
                        )

                for version in production_versions:
                    # 获取模型详细信息
                    model_details = mlflow_client.get_model_version(
                        name=model_name, version=version.version
                    )

                    # 获取模型运行信息
                    run_info = None
                    if model_details.run_id:
                        try:
                            run = mlflow_client.get_run(model_details.run_id)
                            run_info = {
                                "run_id": run.info.run_id,
                                "experiment_id": run.info.experiment_id,
                                "status": run.info.status,
                                "start_time": run.info.start_time,
                                "end_time": run.info.end_time,
                                "metrics": run.data.metrics,
                                "params": run.data.params,
                            }
                        except Exception as e:
                            logger.warning(
                                f"无法获取运行信息 {model_details.run_id}: {e}"
                            )

                    model_info = {
                        "name": model_name,
                        "version": version.version,
                        "stage": version.current_stage,
                        "creation_timestamp": version.creation_timestamp,
                        "last_updated_timestamp": version.last_updated_timestamp,
                        "description": version.description,
                        "tags": version.tags,
                        "status": version.status,
                        "user_id": version.user_id,
                        "run_info": run_info,
                    }

                    active_models.append(model_info)

            except RuntimeError as e:
                logger.error(f"MLflow服务错误: {e}")
                raise HTTPException(
                    status_code=500, detail={"error": f"MLflow服务错误: {str(e)}"}
                )
            except Exception as e:
                logger.error(f"获取模型 {model_name} 版本信息失败: {e}")
                continue

        return APIResponse.success(
            data={
                "models": active_models,
                "active_models": active_models,
                "count": len(active_models),
                "mlflow_tracking_uri": "http://localhost:5002",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取活跃模型失败: {e}")
        raise HTTPException(status_code=500, detail={"error": "获取活跃模型失败"})