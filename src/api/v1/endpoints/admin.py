"""
管理 API 接口

提供模型管理和系统管理的接口，需要管理员权限访问。
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.services.mlops.retraining_service import RetrainingService
from src.ml.inference.model_loader import ModelLoader
from src.tasks.schedule import manual_retrain, emergency_rollback
from src.config_unified import get_settings

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/admin", tags=["管理接口"])

# 安全配置
security = HTTPBearer()
settings = get_settings()


def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """
    验证管理员权限

    Args:
        credentials: HTTP Bearer 认证凭据

    Returns:
        bool: 验证成功返回True

    Raises:
        HTTPException: 认证失败时抛出
    """
    # 在生产环境中，这里应该验证 JWT token 或检查用户权限
    # 目前简单地检查 token 是否存在
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 可以检查 JWT claims 中的角色或权限
    return True


@router.post("/retrain", summary="手动触发模型重训练")
async def trigger_manual_retrain(
    description: str = "Manual retraining trigger",
    admin_verified: bool = Depends(verify_admin),
) -> Dict[str, Any]:
    """
    手动触发模型重训练

    Args:
        description: 训练描述
        admin_verified: 管理员验证

    Returns:
        重训练任务结果
    """
    try:
        logger.info(f"管理员手动触发模型重训练: {description}")

        # 异步执行重训练任务
        task = manual_retrain.s(description).apply_async()

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": f"模型重训练任务已提交，任务ID: {task.id}",
            "description": description,
        }

    except Exception as e:
        logger.error(f"手动触发重训练失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发重训练失败: {str(e)}",
        )


@router.post("/model/switch", summary="切换模型版本")
async def switch_model_version(target_version: str, admin_verified: bool = Depends(verify_admin)) -> Dict[str, Any]:
    """
    切换到指定版本的模型

    Args:
        target_version: 目标模型版本
        admin_verified: 管理员验证

    Returns:
        切换结果
    """
    try:
        logger.info(f"管理员请求切换模型版本到: {target_version}")

        # 使用模型加载器切换版本
        model_loader = ModelLoader(model_cache_dir=settings.model_path, enable_hot_reload=True)

        success = model_loader.switch_model_version(target_version)

        if success:
            return {
                "status": "success",
                "message": f"成功切换到模型版本: {target_version}",
                "current_version": model_loader.get_current_version(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"切换模型版本失败: {target_version}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换模型版本失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切换模型版本失败: {str(e)}",
        )


@router.post("/model/rollback", summary="紧急回滚模型")
async def emergency_rollback_model(target_version: str, admin_verified: bool = Depends(verify_admin)) -> Dict[str, Any]:
    """
    紧急回滚到指定版本模型

    Args:
        target_version: 目标回滚版本
        admin_verified: 管理员验证

    Returns:
        回滚结果
    """
    try:
        logger.info(f"管理员紧急回滚到模型版本: {target_version}")

        # 异步执行回滚任务
        task = emergency_rollback.s(target_version).apply_async()

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": f"紧急回滚任务已提交，任务ID: {task.id}",
            "target_version": target_version,
        }

    except Exception as e:
        logger.error(f"紧急回滚失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"紧急回滚失败: {str(e)}",
        )


@router.get("/model/status", summary="获取模型状态")
async def get_model_status(
    admin_verified: bool = Depends(verify_admin),
) -> Dict[str, Any]:
    """
    获取当前模型状态和历史

    Args:
        admin_verified: 管理员验证

    Returns:
        模型状态信息
    """
    try:
        # 获取重训练服务状态
        retraining_service = RetrainingService()
        training_status = retraining_service.get_training_status()

        # 获取模型加载器状态
        model_loader = ModelLoader(
            model_cache_dir=settings.model_path,
            enable_hot_reload=False,  # 避免重复启动热更新
        )

        current_version = model_loader.get_current_version()
        loaded_models = model_loader.list_loaded_models()

        # 获取当前最佳模型信息
        current_best = retraining_service.registry.get_current_best()

        return {
            "training_status": training_status,
            "current_version": current_version,
            "loaded_models": loaded_models,
            "current_best": current_best.to_dict() if current_best else None,
            "hot_reload_enabled": model_loader.enable_hot_reload,
            "models_directory": str(model_loader.get_cache_directory()),
        }

    except Exception as e:
        logger.error(f"获取模型状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型状态失败: {str(e)}",
        )


@router.get("/models", summary="获取所有模型列表")
async def list_all_models(
    admin_verified: bool = Depends(verify_admin),
) -> Dict[str, Any]:
    """
    获取所有注册的模型列表

    Args:
        admin_verified: 管理员验证

    Returns:
        模型列表
    """
    try:
        retraining_service = RetrainingService()
        models = retraining_service.registry.list_models()

        # 按创建时间排序
        models.sort(key=lambda x: x.created_at, reverse=True)

        model_list = []
        for model in models:
            model_list.append(
                {
                    "version": model.version,
                    "accuracy": model.accuracy,
                    "log_loss": model.log_loss,
                    "training_samples": model.training_samples,
                    "feature_count": model.feature_count,
                    "training_time": model.training_time,
                    "model_path": model.model_path,
                    "created_at": model.created_at.isoformat(),
                    "description": model.description,
                }
            )

        return {"total_models": len(model_list), "models": model_list}

    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}",
        )


@router.get("/model/{version}", summary="获取指定版本模型详情")
async def get_model_details(version: str, admin_verified: bool = Depends(verify_admin)) -> Dict[str, Any]:
    """
    获取指定版本的模型详细信息

    Args:
        version: 模型版本
        admin_verified: 管理员验证

    Returns:
        模型详细信息
    """
    try:
        retraining_service = RetrainingService()
        metadata = retraining_service.registry.get_model_metadata(version)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型版本 {version} 不存在",
            )

        # 检查模型文件是否存在
        from pathlib import Path

        model_path = Path(metadata.model_path)
        file_exists = model_path.exists()
        file_size = model_path.stat().st_size if file_exists else 0

        return {
            "version": metadata.version,
            "accuracy": metadata.accuracy,
            "log_loss": metadata.log_loss,
            "training_samples": metadata.training_samples,
            "feature_count": metadata.feature_count,
            "training_time": metadata.training_time,
            "model_path": metadata.model_path,
            "file_exists": file_exists,
            "file_size": file_size,
            "created_at": metadata.created_at.isoformat(),
            "description": metadata.description,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型详情失败: {str(e)}",
        )


@router.post("/model/reload", summary="手动重新加载模型")
async def manual_reload_model(
    admin_verified: bool = Depends(verify_admin),
) -> Dict[str, Any]:
    """
    手动触发模型重新加载

    Args:
        admin_verified: 管理员验证

    Returns:
        重载结果
    """
    try:
        logger.info("管理员手动触发模型重新加载")

        model_loader = ModelLoader(model_cache_dir=settings.model_path, enable_hot_reload=False)  # 手动控制

        success = model_loader.trigger_model_reload()

        if success:
            return {
                "status": "success",
                "message": "模型重新加载已触发",
                "current_version": model_loader.get_current_version(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="触发模型重新加载失败",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动重新加载模型失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手动重新加载模型失败: {str(e)}",
        )


@router.delete("/model/{version}", summary="删除指定版本模型")
async def delete_model_version(
    version: str, force: bool = False, admin_verified: bool = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    删除指定版本的模型

    Args:
        version: 模型版本
        force: 是否强制删除（即使模型是当前最佳模型）
        admin_verified: 管理员验证

    Returns:
        删除结果
    """
    try:
        logger.info(f"管理员删除模型版本: {version}, force: {force}")

        retraining_service = RetrainingService()

        # 检查模型是否存在
        metadata = retraining_service.registry.get_model_metadata(version)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型版本 {version} 不存在",
            )

        # 检查是否是当前最佳模型
        current_best = retraining_service.registry.get_current_best()
        if current_best and current_best.version == version and not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法删除当前最佳模型 {version}，请先切换到其他版本或使用 force=true",
            )

        # 删除模型文件
        from pathlib import Path

        model_path = Path(metadata.model_path)
        deleted_files = []

        if model_path.exists():
            model_path.unlink()
            deleted_files.append(str(model_path))
            logger.info(f"已删除模型文件: {model_path}")

        # 当前版本只删除文件，注册表清理需要额外实现

        return {
            "status": "success",
            "message": f"模型版本 {version} 已删除",
            "deleted_files": deleted_files,
            "version": version,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型版本失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除模型版本失败: {str(e)}",
        )


@router.get("/system/health", summary="获取系统健康状态")
async def get_system_health(
    admin_verified: bool = Depends(verify_admin),
) -> Dict[str, Any]:
    """
    获取详细的系统健康状态

    Args:
        admin_verified: 管理员验证

    Returns:
        系统健康状态
    """
    try:
        from src.tasks.schedule import system_health_check

        # 执行系统健康检查
        health_status = system_health_check.apply()

        # 获取额外系统信息
        import psutil
        import os

        system_info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage("/").percent,
            "process_id": os.getpid(),
            "uptime": psutil.boot_time(),
        }

        return {
            "health_status": health_status.get(),
            "system_info": system_info,
            "timestamp": psutil.time.time(),
        }

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统健康状态失败: {str(e)}",
        )
