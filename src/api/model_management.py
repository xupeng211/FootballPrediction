"""
模型管理API路由

提供模型热重载、版本查询等MLOps功能
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.services.inference_service import InferenceService

logger = logging.getLogger(__name__)

# 创建API路由
router = APIRouter(
    prefix="/api/v1/models",
    tags=["模型管理"],
    responses={
        400: {"description": "请求参数错误"},
        404: {"description": "模型文件不存在"},
        500: {"description": "服务器内部错误"},
    },
)


# Pydantic模型定义
class ModelReloadRequest(BaseModel):
    """模型重载请求"""

    model_path: str | None = Field(None, description="新的模型文件路径，如果不提供则使用默认路径")
    backup_current: bool = Field(default=True, description="是否备份当前模型")

    class Config:
        schema_extra = {
            "example": {
                "model_path": "models/baseline_v1_retrained.pkl",
                "backup_current": True,
            }
        }


class ModelReloadResponse(BaseModel):
    """模型重载响应"""

    success: bool = Field(..., description="是否重载成功")
    message: str = Field(..., description="重载结果信息")
    previous_version: str | None = Field(None, description="重载前的模型版本")
    new_version: str | None = Field(None, description="重载后的模型版本")
    reload_time: str = Field(..., description="重载时间")
    model_path: str = Field(..., description="模型文件路径")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "模型重载成功",
                "previous_version": "baseline_v1_mock",
                "new_version": "baseline_v1_retrained",
                "reload_time": "2025-12-16T20:15:00.000Z",
                "model_path": "models/baseline_v1_retrained.pkl",
            }
        }


class ModelInfoResponse(BaseModel):
    """模型信息响应"""

    is_loaded: bool = Field(..., description="模型是否已加载")
    model_version: str = Field(..., description="当前模型版本")
    model_path: str = Field(..., description="模型文件路径")
    load_time: str | None = Field(None, description="模型加载时间")
    file_size_mb: float | None = Field(None, description="模型文件大小(MB)")
    last_modified: str | None = Field(None, description="模型文件最后修改时间")
    available_models: list[str] = Field(..., description="可用的模型文件列表")

    class Config:
        schema_extra = {
            "example": {
                "is_loaded": True,
                "model_version": "baseline_v1_retrained",
                "model_path": "models/baseline_v1_retrained.pkl",
                "load_time": "2025-12-16T20:15:00.000Z",
                "file_size_mb": 0.14,
                "last_modified": "2025-12-16T20:12:00.000Z",
                "available_models": [
                    "models/baseline_v1.pkl",
                    "models/baseline_v1_retrained.pkl",
                ],
            }
        }


# 全局推理服务实例（在实际应用中应该通过依赖注入）
_inference_service: InferenceService | None = None


def get_inference_service() -> InferenceService:
    """获取推理服务实例"""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service


def get_available_models() -> list[str]:
    """获取可用的模型文件列表"""
    models_dir = Path("models")
    if not models_dir.exists():
        return []

    model_files = []
    for file_path in models_dir.glob("*.pkl"):
        model_files.append(str(file_path))

    return sorted(model_files)


def get_model_metadata(model_path: str) -> dict[str, Any]:
    """获取模型元数据"""
    model_path_obj = Path(model_path)
    metadata_path = model_path_obj.with_suffix("._metadata.json")

    metadata = {}
    if metadata_path.exists():
        try:
            import json

            with open(metadata_path) as f:
                metadata = json.load(f)
        except Exception as e:
            logger.warning(f"读取模型元数据失败 {metadata_path}: {e}")

    return metadata


@router.post("/reload", response_model=ModelReloadResponse)
async def reload_model(request: ModelReloadRequest, background_tasks: BackgroundTasks):
    """
    重新加载模型

    支持模型热重载，可以在不重启服务的情况下更新模型。

    Args:
        request: 模型重载请求
        background_tasks: 后台任务（用于日志记录等）

    Returns:
        ModelReloadResponse: 重载结果
    """
    try:
        inference_service = get_inference_service()

        # 获取当前模型版本
        current_info = inference_service.get_model_info()
        previous_version = current_info.get("model_version", "unknown")

        # 确定模型路径
        target_model_path = request.model_path or "models/baseline_v1.pkl"

        # 备份当前模型
        if request.backup_current:
            backup_path = f"{target_model_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                import shutil

                current_model_path = current_info.get("model_path", target_model_path)
                if Path(current_model_path).exists():
                    shutil.copy2(current_model_path, backup_path)
                    logger.info(f"当前模型已备份到: {backup_path}")
            except Exception as e:
                logger.warning(f"模型备份失败: {e}")

        # 执行模型重载
        reload_success = await inference_service.reload_model(target_model_path)

        if reload_success:
            # 获取新模型信息
            new_info = inference_service.get_model_info()
            new_version = new_info.get("model_version", "unknown")

            # 后台任务：记录重载日志
            background_tasks.add_task(
                log_model_reload, previous_version, new_version, target_model_path, True
            )

            return ModelReloadResponse(
                success=True,
                message="模型重载成功",
                previous_version=previous_version,
                new_version=new_version,
                reload_time=datetime.now().isoformat(),
                model_path=target_model_path,
            )
        background_tasks.add_task(
            log_model_reload, previous_version, "unknown", target_model_path, False
        )

        raise HTTPException(status_code=500, detail="模型重载失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"模型重载异常: {e}")
        raise HTTPException(status_code=500, detail=f"模型重载异常: {e!s}")


@router.get("/info", response_model=ModelInfoResponse)
async def get_model_info():
    """
    获取当前模型信息

    Returns:
        ModelInfoResponse: 模型信息
    """
    try:
        inference_service = get_inference_service()
        model_info = inference_service.get_model_info()

        # 获取模型文件信息
        model_path = model_info.get("model_path", "")
        model_path_obj = Path(model_path)

        file_size_mb = None
        last_modified = None

        if model_path_obj.exists():
            file_size_mb = round(model_path_obj.stat().st_size / (1024 * 1024), 3)
            last_modified = datetime.fromtimestamp(model_path_obj.stat().st_mtime).isoformat()

        # 获取可用模型列表
        available_models = get_available_models()

        return ModelInfoResponse(
            is_loaded=model_info.get("is_trained", False),
            model_version=model_info.get("model_version", "unknown"),
            model_path=model_path,
            load_time=model_info.get("load_time"),
            file_size_mb=file_size_mb,
            last_modified=last_modified,
            available_models=available_models,
        )

    except Exception as e:
        logger.exception(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {e!s}")


@router.get("/list")
async def list_models():
    """
    列出所有可用模型

    Returns:
        Dict[str, Any]: 可用模型列表
    """
    try:
        models = []
        available_models = get_available_models()

        for model_path in available_models:
            model_path_obj = Path(model_path)
            metadata = get_model_metadata(model_path)

            model_info = {
                "path": model_path,
                "filename": model_path_obj.name,
                "size_mb": round(model_path_obj.stat().st_size / (1024 * 1024), 3),
                "last_modified": datetime.fromtimestamp(model_path_obj.stat().st_mtime).isoformat(),
                "version": metadata.get("model_version", "unknown"),
                "training_date": metadata.get("training_date"),
                "accuracy": metadata.get("metrics", {}).get("accuracy"),
                "is_metadata_available": bool(metadata),
            }
            models.append(model_info)

        return {"total_models": len(models), "models": models}

    except Exception as e:
        logger.exception(f"列出模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出模型失败: {e!s}")


async def log_model_reload(old_version: str, new_version: str, model_path: str, success: bool):
    """记录模型重载日志"""
    status = "成功" if success else "失败"
    logger.info(
        f"模型重载{status}: {old_version} -> {new_version} 模型路径: {model_path} 时间: {datetime.now()}"
    )
