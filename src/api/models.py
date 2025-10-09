"""


"""



    """

    """



模型API端点
Models API Endpoints
提供模型管理相关的API接口:
- 获取当前活跃模型
- 获取模型性能指标
- 模型版本管理
注意:此文件已重构为模块化结构,具体实现请查看 src/api/models/ 目录.
# 为了向后兼容,从新模块导入所有内容
def get_model_info() -> dict:
    获取模型基本信息
    Returns:
        包含模型基本信息的字典
    return {
        "api": router,
        "prefix": "/models"}src.api.models.mlflow_client import mlflow_client
        "tags": ["models"],
        "mlflow_client": mlflow_client,
        "prediction_service": prediction_service,
    }
# 导出所有符号以保持向后兼容
__all__ = [
    "router",
    "mlflow_client",
    "prediction_service",
    "get_model_info",
]