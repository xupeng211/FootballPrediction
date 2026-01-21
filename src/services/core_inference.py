#!/usr/bin/env python3
"""
核心推理服务 - 工业级纯净架构

合并inference_service.py和prediction_service.py的核心功能，
提供统一、高效的推理接口。

设计原则:
- Single Source of Truth (单一数据源)
- Type Safety First (类型安全优先)
- Performance Optimized (性能优化)
- Error Resilient (错误恢复)

架构层级:
1. Core Inference Engine (核心推理引擎)
2. Prediction Business Logic (预测业务逻辑)
3. Request/Response Models (请求响应模型)
4. Type Safety Layer (类型安全层)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import time
from typing import Any, Protocol

from .dependency_injection import ServiceLifecycle, injectable

logger = logging.getLogger(__name__)


class PredictionStatus(str, Enum):
    """预测状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelProtocol(Protocol):
    """模型协议接口 - 类型安全"""

    async def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """预测方法"""
        ...

    async def predict_proba(self, features: dict[str, Any]) -> dict[str, float]:
        """概率预测方法"""
        ...

    @property
    def is_trained(self) -> bool:
        """是否已训练"""
        ...

    def get_model_info(self) -> dict[str, Any]:
        """获取模型信息"""
        ...


@dataclass
class PredictionRequest:
    """预测请求模型 - 严格类型安全"""

    match_id: str
    home_team: str
    away_team: str
    include_features: bool = False
    include_metadata: bool = True
    include_explanation: bool = False
    batch_mode: bool = False
    match_ids: list[str] | None = None

    def __post_init__(self) -> None:
        """严格验证"""
        if not self.match_id or not self.match_id.strip():
            raise ValueError("match_id 不能为空")

        if not self.home_team or not self.home_team.strip():
            raise ValueError("home_team 不能为空")

        if not self.away_team or not self.away_team.strip():
            raise ValueError("away_team 不能为空")

        if self.batch_mode and not self.match_ids:
            raise ValueError("批量模式必须提供 match_ids")


@dataclass
class PredictionResponse:
    """预测响应模型 - 完整类型安全"""

    success: bool
    match_id: str | None = None
    prediction: str | None = None
    probabilities: dict[str, float] | None = None
    confidence: float | None = None
    features: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None
    request_id: str | None = None
    processing_time_ms: float | None = None

    def __post_init__(self) -> None:
        """响应验证"""
        if self.success and not self.match_id:
            raise ValueError("成功响应必须包含 match_id")

        if self.confidence is not None and (self.confidence < 0 or self.confidence > 1):
            raise ValueError("置信度必须在0-1之间")

        if self.probabilities:
            total = sum(self.probabilities.values())
            if abs(total - 1.0) > 0.01:
                logger.warning(f"概率总和不等于1: {total}")


@dataclass
class BatchPredictionRequest:
    """批量预测请求"""

    requests: list[PredictionRequest]
    batch_id: str | None = None

    def __post_init__(self) -> None:
        """批量请求验证"""
        if not self.requests:
            raise ValueError("批量请求不能为空")

        if len(self.requests) > 100:
            raise ValueError("单次批量请求不能超过100个")


@dataclass
class BatchPredictionResponse:
    """批量预测响应"""

    batch_id: str
    responses: list[PredictionResponse]
    total_count: int
    success_count: int
    failed_count: int
    processing_time_ms: float
    errors: list[str] = field(default_factory=list)


@injectable("core_inference", ["model_service", "cache_service"])
class CoreInferenceService(ServiceLifecycle):
    """核心推理服务 - 工业级纯净实现"""

    def __init__(self, model_service: ModelProtocol, cache_service: Any | None = None) -> None:
        self.model_service = model_service
        self.cache_service = cache_service
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
        self._performance_stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "avg_processing_time_ms": 0.0,
            "cache_hits": 0,
        }

    async def initialize(self) -> None:
        """初始化推理服务"""
        try:
            if not self.model_service:
                raise ValueError("model_service 不能为空")

            if not self.model_service.is_trained:
                raise RuntimeError("模型未训练，无法初始化推理服务")

            self._initialized = True
            self.logger.info("✅ 核心推理服务初始化完成")

        except Exception as e:
            self.logger.exception(f"❌ 核心推理服务初始化失败: {e}")
            raise

    async def shutdown(self) -> None:
        """关闭推理服务"""
        self._initialized = False
        self.logger.info("✅ 核心推理服务已关闭")

    @property
    def is_initialized(self) -> bool:
        """检查初始化状态"""
        return self._initialized

    async def predict_single_match(self, request: PredictionRequest) -> PredictionResponse:
        """单场比赛预测 - 核心业务逻辑"""
        if not self._initialized:
            raise RuntimeError("推理服务未初始化")

        start_time = time.time()

        try:
            # 1. 构建缓存键
            cache_key = f"prediction:{request.match_id}"

            # 2. 检查缓存
            if self.cache_service:
                try:
                    cached_result = await self.cache_service.get(cache_key)
                    if cached_result:
                        self._performance_stats["cache_hits"] += 1
                        return PredictionResponse(
                            success=True, match_id=request.match_id, **cached_result
                        )
                except Exception as e:
                    self.logger.warning(f"缓存读取失败: {e}")

            # 3. 提取特征
            features = self._extract_features(request)

            # 4. 执行预测
            prediction_result = await self.model_service.predict(features)

            # 5. 构建响应
            response = self._build_response(request, prediction_result, start_time)

            # 6. 缓存结果
            if self.cache_service and response.success:
                try:
                    cache_data = {
                        "prediction": response.prediction,
                        "probabilities": response.probabilities,
                        "confidence": response.confidence,
                        "features": response.features if request.include_features else None,
                        "metadata": response.metadata,
                    }
                    await self.cache_service.set(cache_key, cache_data, ttl=300)
                except Exception as e:
                    self.logger.warning(f"缓存写入失败: {e}")

            # 7. 更新统计
            self._update_performance_stats(response.success, time.time() - start_time)

            return response

        except Exception as e:
            self.logger.exception(f"单场比赛预测失败: {request.match_id}, 错误: {e}")
            self._update_performance_stats(False, time.time() - start_time)

            return PredictionResponse(
                success=False,
                match_id=request.match_id,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def predict_batch_matches(
        self, batch_request: BatchPredictionRequest
    ) -> BatchPredictionResponse:
        """批量比赛预测 - 高并发优化"""
        if not self._initialized:
            raise RuntimeError("推理服务未初始化")

        start_time = time.time()
        responses = []
        errors = []

        # 并发预测（避免过度并发导致资源耗尽）
        import asyncio

        semaphore = asyncio.Semaphore(10)  # 限制并发数

        async def predict_with_semaphore(request: PredictionRequest) -> PredictionResponse:
            async with semaphore:
                return await self.predict_single_match(request)

        # 执行并发预测
        tasks = [predict_with_semaphore(req) for req in batch_request.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_response = PredictionResponse(
                    success=False, match_id=batch_request.requests[i].match_id, error=str(result)
                )
                responses.append(error_response)
                errors.append(f"预测{i + 1}失败: {result}")
            else:
                responses.append(result)

        # 统计结果
        success_count = sum(1 for r in responses if r.success)
        failed_count = len(responses) - success_count

        return BatchPredictionResponse(
            batch_id=batch_request.batch_id or f"batch_{int(time.time())}",
            responses=responses,
            total_count=len(responses),
            success_count=success_count,
            failed_count=failed_count,
            processing_time_ms=(time.time() - start_time) * 1000,
            errors=errors,
        )

    def _extract_features(self, request: PredictionRequest) -> dict[str, Any]:
        """特征提取 - 类型安全实现"""
        # 简化的特征提取逻辑
        # 实际实现应该调用专业的特征工程服务

        # 基础特征
        features = {
            "home_team": request.home_team,
            "away_team": request.away_team,
            "match_id": request.match_id,
        }

        # 模拟更复杂的特征（实际应该从特征工程服务获取）
        features.update(
            {
                "elo_difference": 0,  # 从历史数据计算
                "home_form_avg": 1.0,  # 从历史数据计算
                "away_form_avg": 0.8,  # 从历史数据计算
                "h2h_advantage": 0.1,  # 从历史数据计算
                "venue_advantage": 0.05,  # 从场地数据计算
            }
        )

        return features

    def _build_response(
        self, request: PredictionRequest, prediction_result: dict[str, Any], start_time: float
    ) -> PredictionResponse:
        """构建预测响应 - 完整类型安全"""

        # 提取预测结果
        prediction = prediction_result.get("prediction", "UNKNOWN")
        probabilities = prediction_result.get("probabilities", {})
        confidence = prediction_result.get("confidence", 0.5)
        features = prediction_result.get("features", {})
        metadata = prediction_result.get("metadata", {})

        # 构建响应
        return PredictionResponse(
            success=True,
            match_id=request.match_id,
            prediction=prediction,
            probabilities=probabilities,
            confidence=confidence,
            features=features if request.include_features else None,
            metadata=(
                {
                    **metadata,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "model_version": "core_inference_v1",
                    "request_timestamp": datetime.now().isoformat(),
                }
                if request.include_metadata
                else None
            ),
            processing_time_ms=(time.time() - start_time) * 1000,
        )


    def _update_performance_stats(self, success: bool, processing_time: float) -> None:
        """更新性能统计"""
        self._performance_stats["total_predictions"] += 1
        if success:
            self._performance_stats["successful_predictions"] += 1
        else:
            self._performance_stats["failed_predictions"] += 1

        # 更新平均处理时间
        total = self._performance_stats["total_predictions"]
        current_avg = self._performance_stats["avg_processing_time_ms"]
        new_avg = ((current_avg * (total - 1)) + (processing_time * 1000)) / total
        self._performance_stats["avg_processing_time_ms"] = new_avg

    def get_performance_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        stats = self._performance_stats.copy()

        # 计算成功率
        if stats["total_predictions"] > 0:
            stats["success_rate"] = stats["successful_predictions"] / stats["total_predictions"]
        else:
            stats["success_rate"] = 0.0

        # 计算缓存命中率
        if stats["total_predictions"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_predictions"]
        else:
            stats["cache_hit_rate"] = 0.0

        return stats

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        return {
            "service": "core_inference",
            "status": "healthy" if self._initialized else "unhealthy",
            "model_ready": self.model_service.is_trained if self.model_service else False,
            "performance_stats": self.get_performance_stats(),
            "timestamp": datetime.now().isoformat(),
        }


# 便捷函数
async def create_core_inference_service(
    model_service: ModelProtocol, cache_service: Any | None = None
) -> CoreInferenceService:
    """创建核心推理服务实例"""
    service = CoreInferenceService(model_service, cache_service)
    await service.initialize()
    return service


# 类型安全的工厂函数
def create_prediction_request(
    match_id: str, home_team: str, away_team: str, **kwargs
) -> PredictionRequest:
    """创建预测请求 - 类型安全"""
    return PredictionRequest(match_id=match_id, home_team=home_team, away_team=away_team, **kwargs)


def create_batch_request(
    requests: list[PredictionRequest], batch_id: str | None = None
) -> BatchPredictionRequest:
    """创建批量预测请求 - 类型安全"""
    return BatchPredictionRequest(requests=requests, batch_id=batch_id)
