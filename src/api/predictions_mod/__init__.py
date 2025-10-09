"""





"""



    from src.api.predictions_mod import router
    from src.api.predictions_mod.rate_limiter import get_rate_limiter
from .batch_handlers import batch_predict_matches_handler
from .history_handlers import (

预测API模块 / Predictions API Module
提供模块化的预测API功能，包括：
- 速率限制配置
- 单个预测处理
- 批量预测处理
- 历史预测查询
- API响应模式定义
主要导出 / Main Exports:
    - router: FastAPI路由器，包含所有预测端点
    - get_rate_limiter: 获取速率限制器实例
    - 各种处理器函数用于测试或独立使用
使用示例 / Usage Example:
    ```python
    # 在FastAPI应用中使用路由器
    app.include_router(router, prefix="/api/v1")
    # 获取速率限制器
    limiter = get_rate_limiter()
    ```
    get_match_prediction_history_handler,
    get_recent_predictions_handler,
)
    get_match_prediction_handler,
    predict_match_handler,
    verify_prediction_handler,
)
# 为了向后兼容，导出主要组件
__all__ = [
    # 主要路由器
    "router",
    # 速率限制
    "get_rate_limiter",
    "is_rate_limit_available",
    # 处理器函数
    "get_match_prediction_handler",
    "predict_match_handler",
    "batch_predict_matches_handler",
    "get_match_prediction_history_handler",
    "get_recent_predictions_handler",
    "verify_prediction_handler",
]