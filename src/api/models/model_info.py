"""
模型信息
Model Information

提供模型基本信息和路由配置。
"""



# 创建路由器
router = APIRouter(prefix="/models", tags=["models"])

# 预测服务实例
prediction_service = PredictionService()


def get_model_info() -> dict:
    """
    获取模型基本信息

    Returns:
        包含模型基本信息的字典
    """
    return {
        "api": router,
        "prefix": "/models"}src.models.prediction_service import PredictionService

        "tags": ["models"],
        "prediction_service": prediction_service,
    }