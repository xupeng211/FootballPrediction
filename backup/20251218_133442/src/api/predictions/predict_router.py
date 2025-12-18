#!/usr/bin/env python3
"""
M5模块: 预测API路由

实现高性能的足球比赛1X2预测API，严格遵循TDD设计。
提供RESTful接口，整合推理服务，支持低延迟预测。

核心功能:
1. GET /predict/match/{match_id} - 单场比赛预测
2. 完整的Pydantic Schema验证
3. 标准化的HTTP状态码和错误响应
4. API文档和请求/响应示例
5. 异常处理和降级策略

设计原则:
- TDD驱动: 先写测试，后写实现
- 类型安全: Pydantic模型验证所有输入输出
- RESTful设计: 符合REST API设计规范
- 错误处理: 完整的HTTP异常处理
- 性能优化: 低延迟响应和缓存支持

依赖关系:
- M5.1: src/services/inference_service.py - 推理服务
- 外部: FastAPI, Pydantic, httpx
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# 导入推理服务
from src.services.inference_service import InferenceService
from src.services.explainability_service import ExplainabilityService

logger = logging.getLogger(__name__)

# 创建API路由
router = APIRouter(
    prefix="/predict",
    tags=["predictions"],
    responses={
        404: {"description": "比赛不存在"},
        400: {"description": "请求参数错误或特征提取失败"},
        500: {"description": "服务器内部错误"},
        503: {"description": "服务不可用"},
    },
)


# Pydantic Schema定义
class PredictionRequest(BaseModel):
    """预测请求模型"""

    match_id: str = Field(
        ..., description="比赛唯一标识符", min_length=1, max_length=100
    )
    include_features: bool = Field(default=False, description="是否包含特征信息")
    include_metadata: bool = Field(default=True, description="是否包含元数据")

    class Config:
        schema_extra = {
            "example": {
                "match_id": "match_12345",
                "include_features": False,
                "include_metadata": True,
            }
        }


class PredictionResult(BaseModel):
    """预测结果模型"""

    match_id: str = Field(..., description="比赛ID")
    HOME_WIN_PROBA: float = Field(..., ge=0.0, le=1.0, description="主队获胜概率")
    DRAW_PROBA: float = Field(..., ge=0.0, le=1.0, description="平局概率")
    AWAY_WIN_PROBA: float = Field(..., ge=0.0, le=1.0, description="客队获胜概率")
    predicted_class: str = Field(..., description="预测结果类别")
    confidence: float = Field(..., ge=0.0, le=1.0, description="预测置信度")
    model_version: str = Field(..., description="模型版本")
    processed_at: str = Field(..., description="处理时间")

    @validator("HOME_WIN_PROBA", "DRAW_PROBA", "AWAY_WIN_PROBA")
    def validate_probabilities(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("概率值必须在0.0到1.0之间")
        return v

    @validator("predicted_class")
    def validate_predicted_class(cls, v):
        valid_classes = ["HOME_WIN", "DRAW", "AWAY_WIN"]
        if v not in valid_classes:
            raise ValueError(f"预测类别必须是以下之一: {valid_classes}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "match_id": "match_12345",
                "HOME_WIN_PROBA": 0.65,
                "DRAW_PROBA": 0.25,
                "AWAY_WIN_PROBA": 0.10,
                "predicted_class": "HOME_WIN",
                "confidence": 0.65,
                "model_version": "1.0.0",
                "processed_at": "2024-01-15T10:30:00Z",
            }
        }


class DetailedPredictionResult(PredictionResult):
    """详细预测结果模型"""

    feature_completeness: float = Field(
        ..., ge=0.0, le=1.0, description="特征完整性分数"
    )
    data_quality: str = Field(..., description="数据质量标记")
    feature_importance: Optional[Dict[str, float]] = Field(
        None, description="特征重要性"
    )
    processing_time_ms: Optional[float] = Field(None, description="处理时间（毫秒）")

    @validator("data_quality")
    def validate_data_quality(cls, v):
        valid_qualities = ["HIGH", "MEDIUM", "LOW", "FALLBACK"]
        if v not in valid_qualities:
            raise ValueError(f"数据质量必须是以下之一: {valid_qualities}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "match_id": "match_12345",
                "HOME_WIN_PROBA": 0.65,
                "DRAW_PROBA": 0.25,
                "AWAY_WIN_PROBA": 0.10,
                "predicted_class": "HOME_WIN",
                "confidence": 0.65,
                "model_version": "1.0.0",
                "processed_at": "2024-01-15T10:30:00Z",
                "feature_completeness": 0.95,
                "data_quality": "HIGH",
                "feature_importance": {
                    "home_form_score": 0.25,
                    "away_form_score": 0.20,
                    "h2h_home_win_rate": 0.15,
                },
                "processing_time_ms": 45.2,
            }
        }


class FeatureContribution(BaseModel):
    """特征贡献度模型"""

    feature: str = Field(..., description="特征名称")
    contribution: float = Field(..., description="SHAP贡献度值")

    class Config:
        schema_extra = {
            "example": {"feature": "home_form_score", "contribution": 0.142}
        }


class ExplainablePredictionResult(PredictionResult):
    """可解释预测结果模型"""

    feature_contributions: Dict[str, float] = Field(
        ..., description="特征SHAP贡献度字典"
    )
    top_positive_contributors: List[FeatureContribution] = Field(
        ..., description="正向贡献最大的特征"
    )
    top_negative_contributors: List[FeatureContribution] = Field(
        ..., description="负向贡献最大的特征"
    )
    feature_importance_ranking: Dict[str, float] = Field(
        ..., description="全局特征重要性排名"
    )
    explanation_metadata: Optional[Dict[str, Any]] = Field(
        None, description="解释元数据"
    )

    class Config:
        schema_extra = {
            "example": {
                "match_id": "match_12345",
                "HOME_WIN_PROBA": 0.65,
                "DRAW_PROBA": 0.25,
                "AWAY_WIN_PROBA": 0.10,
                "predicted_class": "HOME_WIN",
                "confidence": 0.65,
                "model_version": "1.0.0",
                "processed_at": "2024-01-15T10:30:00Z",
                "feature_contributions": {
                    "home_form_score": 0.142,
                    "away_form_score": -0.083,
                    "h2h_home_win_rate": 0.067,
                    "rolling_home_score_3": 0.045,
                },
                "top_positive_contributors": [
                    {"feature": "home_form_score", "contribution": 0.142},
                    {"feature": "h2h_home_win_rate", "contribution": 0.067},
                ],
                "top_negative_contributors": [
                    {"feature": "away_form_score", "contribution": -0.083},
                    {"feature": "rolling_away_score_3", "contribution": -0.025},
                ],
                "feature_importance_ranking": {
                    "home_form_score": 0.142,
                    "away_form_score": 0.121,
                    "h2h_home_win_rate": 0.105,
                },
                "explanation_metadata": {
                    "shap_computation_time_ms": 15.2,
                    "total_features": 12,
                    "base_value": 0.333,
                },
            }
        }


class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""

    match_ids: List[str] = Field(
        ..., description="比赛ID列表", min_items=1, max_items=100
    )
    include_features: bool = Field(default=False, description="是否包含特征信息")
    include_metadata: bool = Field(default=True, description="是否包含元数据")

    @validator("match_ids")
    def validate_match_ids(cls, v):
        if not v:
            raise ValueError("比赛ID列表不能为空")
        if len(v) > 100:
            raise ValueError("批量预测最多支持100场比赛")
        return v

    class Config:
        schema_extra = {
            "example": {
                "match_ids": ["match_12345", "match_67890", "match_11111"],
                "include_features": False,
                "include_metadata": True,
            }
        }


class BatchPredictionResult(BaseModel):
    """批量预测结果模型"""

    results: List[PredictionResult] = Field(..., description="预测结果列表")
    total_count: int = Field(..., description="总预测数量")
    successful_count: int = Field(..., description="成功预测数量")
    failed_count: int = Field(..., description="失败预测数量")
    errors: List[Dict[str, str]] = Field(default=[], description="错误信息列表")
    processed_at: str = Field(..., description="处理时间")

    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "match_id": "match_12345",
                        "HOME_WIN_PROBA": 0.65,
                        "DRAW_PROBA": 0.25,
                        "AWAY_WIN_PROBA": 0.10,
                        "predicted_class": "HOME_WIN",
                        "confidence": 0.65,
                        "model_version": "1.0.0",
                        "processed_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total_count": 3,
                "successful_count": 2,
                "failed_count": 1,
                "errors": [{"match_id": "match_11111", "error": "比赛不存在"}],
                "processed_at": "2024-01-15T10:30:05Z",
            }
        }


class HealthCheckResult(BaseModel):
    """健康检查结果模型"""

    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="检查时间")
    service: str = Field(..., description="服务名称")
    model_loaded: bool = Field(None, description="模型是否已加载")
    total_predictions: int = Field(None, description="总预测数量")
    avg_response_time_ms: float = Field(None, description="平均响应时间")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "service": "InferenceService",
                "model_loaded": True,
                "total_predictions": 1250,
                "avg_response_time_ms": 45.2,
            }
        }


# 依赖注入
async def get_inference_service_dependency() -> InferenceService:
    """获取推理服务依赖"""
    try:
        # 创建服务实例但不强制初始化数据库连接
        from src.services.inference_service import InferenceService, InferenceConfig

        config = InferenceConfig(enable_fallback=True)
        service = InferenceService(config)

        # 尝试加载模型，如果失败则使用降级策略
        try:
            await service._load_model()
            service.feature_extractor = None  # 暂时不初始化特征提取器
            service.db_pool = None  # 暂时不初始化数据库连接
            service.is_initialized = True
        except Exception as e:
            logger.warning(f"模型加载失败，将使用降级策略: {e}")
            service.is_initialized = True

        return service
    except Exception as e:
        logger.error(f"推理服务初始化失败: {e}")
        raise HTTPException(status_code=503, detail="预测服务不可用，请稍后重试")


async def get_explainability_service_dependency() -> ExplainabilityService:
    """获取可解释性服务依赖"""
    try:
        explainability_service = ExplainabilityService()
        return explainability_service
    except Exception as e:
        logger.error(f"可解释性服务初始化失败: {e}")
        raise HTTPException(status_code=503, detail="可解释性服务不可用，请稍后重试")


# API路由实现
@router.get(
    "/match/{match_id}",
    response_model=PredictionResult,
    summary="单场比赛预测",
    description="根据比赛ID预测1X2结果，返回各结果的概率和预测类别",
    responses={
        200: {
            "description": "预测成功",
            "content": {"application/json": {"schema": PredictionResult.schema()}},
        }
    },
)
async def predict_match(
    match_id: str = Path(..., description="比赛唯一标识符"),
    include_features: bool = Query(default=False, description="是否包含特征信息"),
    include_metadata: bool = Query(default=True, description="是否包含元数据"),
    inference_service: InferenceService = Depends(get_inference_service_dependency),
) -> PredictionResult:
    """
    单场比赛预测端点

    Args:
        match_id: 比赛ID
        include_features: 是否包含特征信息
        include_metadata: 是否包含元数据
        inference_service: 推理服务实例

    Returns:
        PredictionResult: 预测结果

    Raises:
        HTTPException: 当预测失败时
    """
    try:
        logger.info(f"收到预测请求: match_id={match_id}")

        # 调用推理服务进行预测
        result = await inference_service.predict(match_id)

        # 根据请求参数构建响应
        if include_features or include_metadata:
            # 如果需要详细信息，返回详细结果
            detailed_result = DetailedPredictionResult(**result)

            # 如果不需要特征信息，移除该字段
            if not include_features:
                detailed_result.feature_importance = None

            return detailed_result
        else:
            # 返回基础结果
            return PredictionResult(**result)

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"预测请求处理失败 {match_id}: {e}")
        raise HTTPException(status_code=500, detail=f"预测服务内部错误: {str(e)}")


@router.post(
    "/batch",
    response_model=BatchPredictionResult,
    summary="批量比赛预测",
    description="批量预测多场比赛的1X2结果",
    responses={
        200: {
            "description": "批量预测成功",
            "content": {"application/json": {"schema": BatchPredictionResult.schema()}},
        }
    },
)
async def predict_batch(
    request: BatchPredictionRequest,
    inference_service: InferenceService = Depends(get_inference_service_dependency),
) -> BatchPredictionResult:
    """
    批量比赛预测端点

    Args:
        request: 批量预测请求
        inference_service: 推理服务实例

    Returns:
        BatchPredictionResult: 批量预测结果

    Raises:
        HTTPException: 当批量预测失败时
    """
    try:
        logger.info(f"收到批量预测请求: {len(request.match_ids)} 场比赛")

        results = []
        errors = []
        successful_count = 0
        failed_count = 0

        # 并发处理批量请求
        import asyncio

        semaphore = asyncio.Semaphore(10)  # 限制并发数

        async def predict_single(match_id: str) -> tuple:
            async with semaphore:
                try:
                    result = await inference_service.predict(match_id)
                    return match_id, result, None
                except Exception as e:
                    return match_id, None, str(e)

        # 执行并发预测
        tasks = [predict_single(match_id) for match_id in request.match_ids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for match_id, result, error in responses:
            if isinstance(responses[0], Exception):
                errors.append({"match_id": match_id, "error": str(responses[0])})
                failed_count += 1
            elif error:
                errors.append({"match_id": match_id, "error": error})
                failed_count += 1
            else:
                # 根据请求参数构建响应
                if request.include_features or request.include_metadata:
                    detailed_result = DetailedPredictionResult(**result)
                    if not request.include_features:
                        detailed_result.feature_importance = None
                    results.append(detailed_result)
                else:
                    results.append(PredictionResult(**result))
                successful_count += 1

        batch_result = BatchPredictionResult(
            results=results,
            total_count=len(request.match_ids),
            successful_count=successful_count,
            failed_count=failed_count,
            errors=errors,
            processed_at=datetime.now().isoformat(),
        )

        logger.info(f"批量预测完成: 成功={successful_count}, 失败={failed_count}")
        return batch_result

    except Exception as e:
        logger.error(f"批量预测请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量预测服务内部错误: {str(e)}")


@router.get(
    "/health",
    response_model=HealthCheckResult,
    summary="服务健康检查",
    description="检查预测服务的健康状态",
    responses={
        200: {
            "description": "健康检查成功",
            "content": {"application/json": {"schema": HealthCheckResult.schema()}},
        }
    },
)
async def health_check(
    inference_service: InferenceService = Depends(get_inference_service_dependency),
) -> HealthCheckResult:
    """
    服务健康检查端点

    Args:
        inference_service: 推理服务实例

    Returns:
        HealthCheckResult: 健康检查结果
    """
    try:
        health_info = await inference_service.health_check()
        return HealthCheckResult(**health_info)
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthCheckResult(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            service="InferenceService",
            model_loaded=False,
        )


@router.get(
    "/stats",
    summary="服务统计信息",
    description="获取预测服务的统计信息",
    responses={
        200: {
            "description": "统计信息获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "total_requests": 1000,
                        "successful_predictions": 950,
                        "cache_hits": 200,
                        "fallback_used": 5,
                        "errors": 45,
                        "avg_response_time_ms": 42.5,
                        "cache_size": 150,
                        "is_initialized": True,
                    }
                }
            },
        }
    },
)
async def get_stats(
    inference_service: InferenceService = Depends(get_inference_service_dependency),
) -> Dict[str, Any]:
    """
    服务统计信息端点

    Args:
        inference_service: 推理服务实例

    Returns:
        Dict[str, Any]: 服务统计信息
    """
    try:
        stats = inference_service.get_service_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get(
    "/model/info",
    summary="模型信息",
    description="获取当前加载的模型信息",
    responses={
        200: {
            "description": "模型信息获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "model_name": "football_1x2_classifier",
                        "model_version": "1.0.0",
                        "is_trained": True,
                        "n_features": 13,
                        "classes": [0, 1, 2],
                        "config": {
                            "max_depth": 6,
                            "learning_rate": 0.1,
                            "n_estimators": 100,
                        },
                    }
                }
            },
        }
    },
)
async def get_model_info(
    inference_service: InferenceService = Depends(get_inference_service_dependency),
) -> Dict[str, Any]:
    """
    模型信息端点

    Args:
        inference_service: 推理服务实例

    Returns:
        Dict[str, Any]: 模型信息
    """
    try:
        model_info = inference_service.get_model_info()
        return JSONResponse(content=model_info)
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")


@router.post(
    "/model/reload",
    summary="重新加载模型",
    description="重新加载预测模型",
    responses={
        200: {
            "description": "模型重新加载成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "模型重新加载成功",
                        "model_path": "models/football_xgboost_classifier_v2.pkl",
                    }
                }
            },
        }
    },
)
async def reload_model(
    model_path: Optional[str] = Query(None, description="新的模型文件路径"),
    inference_service: InferenceService = Depends(get_inference_service_dependency),
) -> Dict[str, Any]:
    """
    模型重新加载端点

    Args:
        model_path: 新的模型文件路径
        inference_service: 推理服务实例

    Returns:
        Dict[str, Any]: 重新加载结果
    """
    try:
        success = await inference_service.reload_model(model_path)

        if success:
            logger.info(f"模型重新加载成功: {model_path or '使用默认路径'}")
            return {
                "success": True,
                "message": "模型重新加载成功",
                "model_path": model_path or "使用默认路径",
                "reloaded_at": datetime.now().isoformat(),
            }
        else:
            logger.error(f"模型重新加载失败: {model_path}")
            raise HTTPException(status_code=500, detail="模型重新加载失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模型重新加载异常: {e}")
        raise HTTPException(status_code=500, detail=f"模型重新加载异常: {str(e)}")


@router.get(
    "/match/{match_id}/explain",
    response_model=ExplainablePredictionResult,
    summary="单场比赛预测解释",
    description="根据比赛ID预测1X2结果并提供SHAP特征解释",
    responses={
        200: {
            "description": "预测解释成功",
            "content": {
                "application/json": {"schema": ExplainablePredictionResult.schema()}
            },
        }
    },
)
async def predict_match_with_explanation(
    match_id: str = Path(..., description="比赛唯一标识符"),
    inference_service: InferenceService = Depends(get_inference_service_dependency),
    explainability_service: ExplainabilityService = Depends(
        get_explainability_service_dependency
    ),
) -> ExplainablePredictionResult:
    """
    单场比赛预测解释端点

    提供完整的预测结果以及SHAP特征贡献度分析。

    Args:
        match_id: 比赛ID
        inference_service: 推理服务实例
        explainability_service: 可解释性服务实例

    Returns:
        ExplainablePredictionResult: 包含SHAP解释的预测结果

    Raises:
        HTTPException: 当预测或解释失败时
    """
    try:
        import time

        start_time = time.time()

        logger.info(f"收到预测解释请求: match_id={match_id}")

        # 获取预测结果
        prediction_result = await inference_service.predict(match_id)

        # 获取特征数据用于SHAP计算
        # 注意：这里需要根据实际的推理服务实现来获取特征
        features_data = await inference_service._get_features_for_match(match_id)

        if features_data is None:
            raise HTTPException(
                status_code=404, detail=f"无法获取比赛 {match_id} 的特征数据"
            )

        # 转换为DataFrame格式
        import pandas as pd

        features_df = pd.DataFrame([features_data])

        # 计算SHAP贡献度
        shap_start_time = time.time()
        contributions_list = await explainability_service.get_shap_contributions(
            features_df, inference_service.model
        )
        shap_computation_time = (time.time() - shap_start_time) * 1000

        if not contributions_list:
            raise HTTPException(status_code=500, detail="SHAP贡献度计算失败")

        contributions = contributions_list[0]

        # 获取特征重要性排名
        importance_ranking = explainability_service.get_feature_importance_ranking(
            [contributions]
        )

        # 提取正向和负向贡献最大的特征
        sorted_contributions = sorted(
            contributions.items(), key=lambda x: x[1], reverse=True
        )

        top_positive = [
            FeatureContribution(feature=k, contribution=v)
            for k, v in sorted_contributions[:5]
            if v > 0
        ]

        top_negative = [
            FeatureContribution(feature=k, contribution=v)
            for k, v in sorted_contributions[-5:]
            if v < 0
        ]

        # 构建解释元数据
        explanation_metadata = {
            "shap_computation_time_ms": round(shap_computation_time, 2),
            "total_features": len(contributions),
            "positive_contributions_count": len(top_positive),
            "negative_contributions_count": len(top_negative),
            "base_value": (
                getattr(
                    explainability_service._explainer_cache.get(
                        id(inference_service.model.model)
                    ),
                    "expected_value",
                    0.0,
                )
                if explainability_service._explainer_cache
                else 0.0
            ),
        }

        # 构建可解释预测结果
        total_time = (time.time() - start_time) * 1000

        explainable_result = ExplainablePredictionResult(
            match_id=prediction_result["match_id"],
            HOME_WIN_PROBA=prediction_result["HOME_WIN_PROBA"],
            DRAW_PROBA=prediction_result["DRAW_PROBA"],
            AWAY_WIN_PROBA=prediction_result["AWAY_WIN_PROBA"],
            predicted_class=prediction_result["predicted_class"],
            confidence=prediction_result["confidence"],
            model_version=prediction_result["model_version"],
            processed_at=prediction_result["processed_at"],
            feature_contributions=contributions,
            top_positive_contributors=top_positive,
            top_negative_contributors=top_negative,
            feature_importance_ranking=importance_ranking,
            explanation_metadata=explanation_metadata,
        )

        logger.info(f"预测解释完成: match_id={match_id}, 耗时={total_time:.2f}ms")
        return explainable_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预测解释失败 {match_id}: {e}")
        raise HTTPException(status_code=500, detail=f"预测解释服务内部错误: {str(e)}")


@router.post(
    "/batch/explain",
    summary="批量比赛预测解释",
    description="批量预测多场比赛的1X2结果并提供SHAP特征解释",
    response_model=Dict[str, Any],
)
async def predict_batch_with_explanation(
    match_ids: List[str] = Query(
        ..., description="比赛ID列表", min_items=1, max_items=10
    ),
    inference_service: InferenceService = Depends(get_inference_service_dependency),
    explainability_service: ExplainabilityService = Depends(
        get_explainability_service_dependency
    ),
) -> Dict[str, Any]:
    """
    批量比赛预测解释端点

    Args:
        match_ids: 比赛ID列表（限制最大10个以保证性能）
        inference_service: 推理服务实例
        explainability_service: 可解释性服务实例

    Returns:
        Dict[str, Any]: 批量预测解释结果
    """
    try:
        import time

        start_time = time.time()

        if len(match_ids) > 10:
            raise HTTPException(
                status_code=400, detail="批量解释最多支持10场比赛以保证性能"
            )

        logger.info(f"收到批量预测解释请求: {len(match_ids)} 场比赛")

        results = []
        errors = []
        successful_count = 0
        failed_count = 0

        # 并发处理批量请求（限制并发数以优化SHAP计算性能）
        import asyncio

        semaphore = asyncio.Semaphore(3)  # 限制并发数，SHAP计算资源密集

        async def explain_single(match_id: str) -> tuple:
            async with semaphore:
                try:
                    # 获取预测结果
                    prediction_result = await inference_service.predict(match_id)

                    # 获取特征数据
                    features_data = await inference_service._get_features_for_match(
                        match_id
                    )

                    if features_data is None:
                        return match_id, None, f"无法获取比赛 {match_id} 的特征数据"

                    # 计算SHAP贡献度
                    import pandas as pd

                    features_df = pd.DataFrame([features_data])
                    contributions_list = (
                        await explainability_service.get_shap_contributions(
                            features_df, inference_service.model
                        )
                    )

                    if not contributions_list:
                        return match_id, None, "SHAP贡献度计算失败"

                    contributions = contributions_list[0]
                    importance_ranking = (
                        explainability_service.get_feature_importance_ranking(
                            [contributions]
                        )
                    )

                    # 构建结果
                    result = {
                        "match_id": match_id,
                        "prediction": prediction_result,
                        "feature_contributions": contributions,
                        "feature_importance_ranking": importance_ranking,
                        "top_positive_contributors": [
                            {"feature": k, "contribution": v}
                            for k, v in sorted(
                                contributions.items(), key=lambda x: x[1], reverse=True
                            )[:5]
                            if v > 0
                        ],
                        "top_negative_contributors": [
                            {"feature": k, "contribution": v}
                            for k, v in sorted(
                                contributions.items(), key=lambda x: x[1]
                            )[:5]
                            if v < 0
                        ],
                    }

                    return match_id, result, None

                except Exception as e:
                    return match_id, None, str(e)

        # 执行并发解释
        tasks = [explain_single(match_id) for match_id in match_ids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for match_id, result, error in responses:
            if isinstance(responses[0], Exception):
                errors.append({"match_id": match_id, "error": str(responses[0])})
                failed_count += 1
            elif error:
                errors.append({"match_id": match_id, "error": error})
                failed_count += 1
            else:
                results.append(result)
                successful_count += 1

        total_time = (time.time() - start_time) * 1000

        batch_result = {
            "results": results,
            "total_count": len(match_ids),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "errors": errors,
            "processed_at": datetime.now().isoformat(),
            "processing_time_ms": round(total_time, 2),
            "avg_time_per_prediction": (
                round(total_time / len(match_ids), 2) if match_ids else 0
            ),
        }

        logger.info(
            f"批量预测解释完成: 成功={successful_count}, 失败={failed_count}, 耗时={total_time:.2f}ms"
        )
        return batch_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量预测解释失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"批量预测解释服务内部错误: {str(e)}"
        )


# 注意：异常处理器需要在主FastAPI应用中设置，而不是在APIRouter中
# 以下是异常处理器的示例代码，需要在主应用中使用：

# from fastapi import HTTPException, Request
# from fastapi.responses import JSONResponse
#
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request: Request, exc: HTTPException):
#     logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "error": exc.detail,
#             "status_code": exc.status_code,
#             "timestamp": datetime.now().isoformat(),
#             "path": str(request.url)
#         }
#     )
#
# @app.exception_handler(Exception)
# async def general_exception_handler(request: Request, exc: Exception):
#     logger.error(f"未处理的异常: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": "服务器内部错误",
#             "status_code": 500,
#             "timestamp": datetime.now().isoformat(),
#             "path": str(request.url)
#         }
#     )
