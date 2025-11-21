"""服务模块初始化文件
Services Module Initialization File.

提供各种业务服务：
- 推理服务
- 数据服务
- 缓存服务
"""

from .inference_service import InferenceService

__all__ = ["InferenceService"]
