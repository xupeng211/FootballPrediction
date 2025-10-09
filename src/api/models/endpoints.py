"""

"""







    """获取当前活跃模型列表"""


    """获取指定模型的指标"""


    """获取指定模型的版本列表"""


    """获取指定模型的详细性能分析"""


    """推广模型版本到指定阶段"""


    """获取MLflow实验列表"""




from src.api.models.active import get_active_models
from src.api.models.experiments import get_experiments
from src.api.models.metrics import get_model_metrics
from src.api.models.mlflow_client import mlflow_client
from src.api.models.performance import get_model_performance
from src.api.models.versions import get_model_versions, promote_model_version

模型管理API端点
Models API Endpoints
整合所有模型管理相关的API端点。
# 获取模型信息
model_info = get_model_info()
router = model_info["api"]
# 依赖注入
AsyncSession = Annotated[object, Depends(get_async_db_session)]
MLflowClient = Annotated[object, lambda: mlflow_client]
@router.get("/active", summary="获取当前活跃模型")
async def get_active_models_endpoint(
    client: MLflowClient,
) -> dict:
    return await get_active_models(client)
@router.get("/{model_name}/metrics", summary="获取模型指标")
async def get_model_metrics_endpoint(
    model_name: str = Path(..., description="模型名称"),
    client: MLflowClient = None,
) -> dict:
    return await get_model_metrics(model_name, client)
@router.get("/{model_name}/versions", summary="获取模型版本列表")
async def get_model_versions_endpoint(
    model_name: str = Path(..., description="模型名称"),
    limit: int = Query(default=20, description="返回版本数量限制", ge=1, le=100),
    client: MLflowClient = None,
) -> dict:
    return await get_model_versions(model_name, limit, client)
@router.get("/{model_name}/performance", summary="获取模型性能分析")
async def get_model_performance_endpoint(
    model_name: str = Path(..., description="模型名称"),
    version: str = Query(default=None, description="模型版本"),
    session: AsyncSession = None,
    client: MLflowClient = None,
) -> dict:
    return await get_model_performance(model_name, version, session, client)
@router.post("/{model_name}/versions/{version}/promote", summary="推广模型版本")
async def promote_model_version_endpoint(
    model_name: str = Path(..., description="模型名称"),
    version: str = Path(..., description="模型版本"),
    target_stage: str = Query(default="Production", description="目标阶段"),
    client: MLflowClient = None,
) -> dict:
    return await promote_model_version(model_name, version, target_stage, client)
@router.get("/experiments", summary="获取实验列表")
async def get_experiments_endpoint(
    limit: int = Query(default=20, description="返回实验数量限制", ge=1, le=100),
    client: MLflowClient = None,
) -> dict:
    return await get_experiments(limit, client)