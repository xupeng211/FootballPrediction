"""
预测API端点
Prediction API Endpoints

提供完整的预测相关API接口，包括：
- 单场比赛预测
- 批量预测
- 预测历史
- 模型性能统计
- 实时预测流

Provides complete prediction-related API endpoints, including:
- Single match prediction
- Batch prediction
- Prediction history
- Model performance statistics
- Real-time prediction stream

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口。
建议使用：from src.api.predictions import router

"""

from .predictions import (

# 为了向后兼容性，从新的模块化结构中导入所有内容
    router,
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    UpcomingMatchesRequest,
    UpcomingMatchesResponse,
    ModelStatsResponse,
    PredictionHistoryResponse,
    PredictionOverviewResponse,
    VerificationResponse,
    CacheClearResponse,
    HealthCheckResponse,
)

# 重新导出以保持原始接口
__all__ = [
    "router",
    "PredictionRequest",
    "PredictionResponse",
    "BatchPredictionRequest",
    "BatchPredictionResponse",
    "UpcomingMatchesRequest",
    "UpcomingMatchesResponse",
    "ModelStatsResponse",
    "PredictionHistoryResponse",
    "PredictionOverviewResponse",
    "VerificationResponse",
    "CacheClearResponse",
    "HealthCheckResponse",
]

# 原始实现已移至 src/api/predictions/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有端点：
# - POST /predict
# - POST /predict/batch
# - POST /predict/upcoming
# - GET /match/{match_id}
# - GET /history/match/{match_id}
# - GET /stats/model/{model_name}
# - GET /stats/overview
# - POST /verify/{match_id}
# - GET /stream/matches/{match_id}
# - DELETE /cache
# - GET /health
