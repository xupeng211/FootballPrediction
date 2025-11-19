"""预测API端点 / Prediction API Endpoints.

提供比赛预测相关的API接口:

常量定义:
    DEFAULT_API_PORT = 8000
    DEFAULT_API_HOST = "localhost"
"""
- 获取比赛预测结果
- 实时生成预测
- 批量预测接口

Provides API endpoints for match prediction:
    - Get match prediction results
- Generate real-time predictions
- Batch prediction interface

主要端点 / Main Endpoints:
    GET /predictions/{match_id}: 获取指定比赛的预测结果 / Get prediction for specified match
    POST /predictions/{match_id}/predict: 实时预测比赛结果 / Predict match result in real-time
    POST /predictions/batch: 批量预测比赛 / Batch predict matches
    GET /predictions/history/{match_id}: 获取比赛历史预测 / Get match prediction history
    GET /predictions/recent: 获取最近的预测 / Get recent predictions
    POST /predictions/{match_id}/verify: 验证预测结果 / Verify prediction result

使用示例 / Usage Example:
    ```python
    import requests

    # 获取比赛预测
    response = None
    base_url = f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}"
    requests.get(f"{base_url}/api/v1/predictions/12345")
    _prediction = response.json()

    # 实时预测
    response = None
    requests.post(f"{base_url}/api/v1/predictions/12345/predict")
    result = response.json()
    ```

错误处理 / Error Handling:
    - 404: 比赛不存在 / Match not found  # ISSUE: 魔法数字 404 应该提取为命名常量以提高代码可维护性
    - 400: 请求参数错误 / Bad request parameters  # ISSUE: 魔法数字 400 应该提取为命名常量以提高代码可维护性
    - 500: 服务器内部错误 / Internal server error  # ISSUE: 魔法数字 500 应该提取为命名常量以提高代码可维护性

该文件已重构为模块化架构,原始功能现在通过以下模块提供:
- rate_limiter: 速率限制配置
- prediction_handlers: 单个预测处理逻辑
- batch_handlers: 批量预测处理
- history_handlers: 历史预测处理
- schemas: API响应模式定义
- predictions_router: 主路由器

基于 API_DESIGN.md 第3.1节设计.
"""

# 为了向后兼容,从新的模块化实现重新导出路由器
from .predictions.router import router

# 保持原有的导出
__all__ = [
    "router",
]
