#!/usr/bin/env python3
"""
预测服务层 - Sprint 3 核心组件

实现业务逻辑与API路由的解耦，作为API层和推理服务之间的中转层。
负责请求验证、业务协调、响应构建和错误处理。

设计原则:
- Separation of Concerns (关注点分离)
- Business Logic Orchestration (业务逻辑编排)
- Request/Response Transformation (请求响应转换)
- Error Handling and Validation (错误处理和验证)
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .dependency_injection import injectable, ServiceLifecycle

logger = logging.getLogger(__name__)


@dataclass
class PredictionRequest:
    """预测请求模型"""

    match_id: str
    include_features: bool = False
    include_metadata: bool = True
    include_explanation: bool = False
    batch_mode: bool = False
    match_ids: Optional[List[str]] = None

    def __post_init__(self):
        """初始化后验证"""
        if not self.match_id:
            raise ValueError("match_id 不能为空")

        if self.batch_mode and not self.match_ids:
            raise ValueError("批量模式必须提供 match_ids")


@dataclass
class PredictionResponse:
    """预测响应模型"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: Optional[str] = None


@injectable("prediction_service", ["inference_service", "explainability_service"])
class PredictionService(ServiceLifecycle):
    """
    预测服务层

    职责:
    1. 预测请求的验证和预处理
    2. 业务逻辑编排和协调
    3. 推理服务调用
    4. 响应数据的构建和后处理
    5. 错误处理和降级策略
    """

    def __init__(
        self, inference_service: Any = None, explainability_service: Any = None
    ):
        """
        初始化预测服务

        Args:
            inference_service: 推理服务实例
            explainability_service: 可解释性服务实例
        """
        self.inference_service = inference_service
        self.explainability_service = explainability_service
        self._initialized = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self) -> None:
        """初始化服务"""
        try:
            # 验证依赖服务
            if not self.inference_service:
                raise ValueError("inference_service 不能为空")

            # 如果需要可解释性功能，验证可解释性服务
            # 注意：可解释性服务为可选依赖

            self._initialized = True
            self.logger.info("PredictionService 初始化完成")

        except Exception as e:
            self.logger.error(f"PredictionService 初始化失败: {e}")
            raise

    async def shutdown(self) -> None:
        """关闭服务"""
        self._initialized = False
        self.logger.info("PredictionService 已关闭")

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    async def predict_single_match(
        self,
        match_id: str,
        include_features: bool = False,
        include_metadata: bool = True,
        include_explanation: bool = False,
    ) -> PredictionResponse:
        """
        单场比赛预测

        Args:
            match_id: 比赛ID
            include_features: 是否包含特征信息
            include_metadata: 是否包含元数据
            include_explanation: 是否包含解释信息

        Returns:
            PredictionResponse: 预测响应
        """
        start_time = datetime.now()
        request_id = f"single_{match_id}_{int(start_time.timestamp())}"

        try:
            # 1. 验证请求参数
            self._validate_single_request(match_id)

            # 2. 调用推理服务
            prediction_result = await self.inference_service.predict(match_id)

            # 3. 构建响应数据
            response_data = await self._build_single_response(
                prediction_result,
                include_features,
                include_metadata,
                include_explanation,
            )

            # 4. 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            response = PredictionResponse(
                success=True,
                data=response_data,
                processing_time_ms=processing_time,
                request_id=request_id,
            )

            self.logger.info(
                f"单场比赛预测完成: match_id={match_id}, "
                f"processing_time={processing_time:.2f}ms"
            )

            return response

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_message = str(e)

            self.logger.error(
                f"单场比赛预测失败: match_id={match_id}, error={error_message}"
            )

            return PredictionResponse(
                success=False,
                error=error_message,
                processing_time_ms=processing_time,
                request_id=request_id,
            )

    async def predict_batch_matches(
        self,
        match_ids: List[str],
        include_features: bool = False,
        include_metadata: bool = True,
        include_explanation: bool = False,
        max_concurrent: int = 10,
    ) -> PredictionResponse:
        """
        批量比赛预测

        Args:
            match_ids: 比赛ID列表
            include_features: 是否包含特征信息
            include_metadata: 是否包含元数据
            include_explanation: 是否包含解释信息
            max_concurrent: 最大并发数

        Returns:
            PredictionResponse: 批量预测响应
        """
        start_time = datetime.now()
        request_id = f"batch_{len(match_ids)}_{int(start_time.timestamp())}"

        try:
            # 1. 验证批量请求
            self._validate_batch_request(match_ids)

            # 2. 并发预测
            results = await self._predict_batch_concurrent(
                match_ids,
                include_features,
                include_metadata,
                include_explanation,
                max_concurrent,
            )

            # 3. 构建批量响应
            batch_response = await self._build_batch_response(results)

            # 4. 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            response = PredictionResponse(
                success=True,
                data=batch_response,
                processing_time_ms=processing_time,
                request_id=request_id,
            )

            successful_count = sum(1 for r in results if r.success)
            self.logger.info(
                f"批量比赛预测完成: total={len(match_ids)}, "
                f"success={successful_count}, "
                f"processing_time={processing_time:.2f}ms"
            )

            return response

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_message = str(e)

            self.logger.error(
                f"批量比赛预测失败: match_ids={match_ids}, error={error_message}"
            )

            return PredictionResponse(
                success=False,
                error=error_message,
                processing_time_ms=processing_time,
                request_id=request_id,
            )

    async def explain_prediction(self, match_id: str) -> PredictionResponse:
        """
        预测解释

        Args:
            match_id: 比赛ID

        Returns:
            PredictionResponse: 解释响应
        """
        start_time = datetime.now()
        request_id = f"explain_{match_id}_{int(start_time.timestamp())}"

        try:
            # 1. 验证请求
            self._validate_single_request(match_id)

            # 2. 检查可解释性服务
            if not self.explainability_service:
                raise ValueError("可解释性服务未配置")

            # 3. 获取预测结果
            prediction_result = await self.inference_service.predict(match_id)

            # 4. 获取特征数据
            features_data = await self.inference_service._get_features_for_match(
                match_id
            )

            if not features_data:
                raise ValueError(f"无法获取比赛 {match_id} 的特征数据")

            # 5. 计算SHAP贡献度
            import pandas as pd

            features_df = pd.DataFrame([features_data])

            contributions_list = (
                await self.explainability_service.get_shap_contributions(
                    features_df, self.inference_service.model
                )
            )

            if not contributions_list:
                raise ValueError("SHAP贡献度计算失败")

            contributions = contributions_list[0]

            # 6. 构建解释响应
            explanation_data = {
                "prediction": prediction_result,
                "feature_contributions": contributions,
                "top_positive_contributors": [
                    {"feature": k, "contribution": v}
                    for k, v in sorted(
                        contributions.items(), key=lambda x: x[1], reverse=True
                    )[:5]
                    if v > 0
                ],
                "top_negative_contributors": [
                    {"feature": k, "contribution": v}
                    for k, v in sorted(contributions.items(), key=lambda x: x[1])[:5]
                    if v < 0
                ],
            }

            # 7. 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            response = PredictionResponse(
                success=True,
                data=explanation_data,
                processing_time_ms=processing_time,
                request_id=request_id,
            )

            self.logger.info(
                f"预测解释完成: match_id={match_id}, processing_time={processing_time:.2f}ms"
            )
            return response

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_message = str(e)

            self.logger.error(
                f"预测解释失败: match_id={match_id}, error={error_message}"
            )

            return PredictionResponse(
                success=False,
                error=error_message,
                processing_time_ms=processing_time,
                request_id=request_id,
            )

    async def get_service_health(self) -> PredictionResponse:
        """获取服务健康状态"""
        try:
            # 检查推理服务健康状态
            inference_health = await self.inference_service.health_check()

            health_data = {
                "prediction_service": {
                    "status": "healthy",
                    "initialized": self._initialized,
                },
                "inference_service": inference_health,
                "explainability_service": {
                    "available": self.explainability_service is not None,
                    "status": "healthy" if self.explainability_service else "disabled",
                },
            }

            response = PredictionResponse(
                success=True, data=health_data, request_id="health_check"
            )

            return response

        except Exception as e:
            self.logger.error(f"服务健康检查失败: {e}")
            return PredictionResponse(
                success=False, error=str(e), request_id="health_check"
            )

    # 私有方法
    def _validate_single_request(self, match_id: str) -> None:
        """验证单场比赛请求"""
        if not match_id or not isinstance(match_id, str):
            raise ValueError("无效的 match_id")

        if len(match_id) > 100:  # 防止过长的ID
            raise ValueError("match_id 过长")

    def _validate_batch_request(self, match_ids: List[str]) -> None:
        """验证批量请求"""
        if not match_ids or not isinstance(match_ids, list):
            raise ValueError("无效的 match_ids")

        if len(match_ids) == 0:
            raise ValueError("match_ids 不能为空")

        if len(match_ids) > 100:  # 限制批量大小
            raise ValueError("批量请求最多支持100场比赛")

        for match_id in match_ids:
            self._validate_single_request(match_id)

    async def _build_single_response(
        self,
        prediction_result: Dict[str, Any],
        include_features: bool,
        include_metadata: bool,
        include_explanation: bool,
    ) -> Dict[str, Any]:
        """构建单场比赛响应数据"""
        response_data = prediction_result.copy()

        # 根据请求参数过滤数据
        if not include_features:
            # 移除特征相关字段
            response_data = {
                k: v for k, v in response_data.items() if not k.startswith("feature_")
            }

        if not include_metadata:
            # 移除元数据字段
            metadata_fields = ["model_version", "processed_at", "data_quality"]
            response_data = {
                k: v for k, v in response_data.items() if k not in metadata_fields
            }

        return response_data

    async def _predict_batch_concurrent(
        self,
        match_ids: List[str],
        include_features: bool,
        include_metadata: bool,
        include_explanation: bool,
        max_concurrent: int,
    ) -> List[PredictionResponse]:
        """并发执行批量预测"""
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def predict_single(match_id: str) -> PredictionResponse:
            async with semaphore:
                return await self.predict_single_match(
                    match_id, include_features, include_metadata, include_explanation
                )

        # 创建并发任务
        tasks = [predict_single(match_id) for match_id in match_ids]

        # 执行并发任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results: List[PredictionResponse] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_response = PredictionResponse(
                    success=False,
                    error=f"预测异常: {str(result)}",
                    request_id=f"batch_item_{match_ids[i]}",
                )
                processed_results.append(error_response)
            else:
                # result已经是一个PredictionResponse对象
                processed_results.append(result)  # type: ignore

        return processed_results

    async def _build_batch_response(
        self, results: List[PredictionResponse]
    ) -> Dict[str, Any]:
        """构建批量响应数据"""
        successful_results = [r.data for r in results if r.success]
        failed_results = [
            {"match_id": r.request_id, "error": r.error}
            for r in results
            if not r.success
        ]

        # 转换为标准格式
        if successful_results:
            # 如果包含详细预测结果，转换为批量格式
            if all(isinstance(r, dict) for r in successful_results):
                batch_data = {
                    "results": successful_results,
                    "total_count": len(results),
                    "successful_count": len(successful_results),
                    "failed_count": len(failed_results),
                    "errors": failed_results,
                    "processed_at": datetime.now().isoformat(),
                }
            else:
                # 如果是简单格式，保持原样
                batch_data = {
                    "results": successful_results,
                    "total_count": len(results),
                    "successful_count": len(successful_results),
                    "failed_count": len(failed_results),
                    "errors": failed_results,
                    "processed_at": datetime.now().isoformat(),
                }
        else:
            batch_data = {
                "results": [],
                "total_count": len(results),
                "successful_count": 0,
                "failed_count": len(failed_results),
                "errors": failed_results,
                "processed_at": datetime.now().isoformat(),
            }

        return batch_data
