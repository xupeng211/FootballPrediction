"""
推理API模块
Phase 3: Inference Service

功能:
- 模型加载和管理
- FastAPI推理端点
- 请求/响应数据模型
- 错误处理和日志记录

作者: Backend Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Phase 3 Inference
"""

from .service import router, startup_load_model, shutdown_cleanup
from .model_loader import model_loader
from .schemas import (
    PredictionRequest,
    PredictionResponse,
    ModelInfoResponse,
    ErrorResponse,
)

__all__ = [
    "router",
    "model_loader",
    "startup_load_model",
    "shutdown_cleanup",
    "PredictionRequest",
    "PredictionResponse",
    "ModelInfoResponse",
    "ErrorResponse",
]
