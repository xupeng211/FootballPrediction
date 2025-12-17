#!/usr/bin/env python3
"""
推理服务 v2.0 - 重构版本 (Inference Service v2.0)

基于重构后的inference模块，提供简化的服务层接口。
专注于业务逻辑协调，底层实现委托给专业的组件。

主要职责：
1. 协调模型加载器和预测器的工作
2. 提供高级的预测业务接口
3. 管理预测请求的生命周期
4. 提供预测结果的业务解释
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

from .__init__ import BaseService
from src.ml.inference import ModelLoader, MatchPredictor
from src.ml.inference.cache_manager import PredictionCache
from src.ml.features.extractor import MatchFeatureExtractor

logger = logging.getLogger(__name__)


@dataclass
class PredictionRequest:
    """预测请求"""

    match_id: str
    home_team: str
    away_team: str
    match_date: Optional[datetime] = None
    features: Optional[List[float]] = None
    use_cache: bool = True
    model_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_date": self.match_date.isoformat() if self.match_date else None,
            "features": self.features,
            "use_cache": self.use_cache,
            "model_name": self.model_name,
        }


@dataclass
class PredictionResponse:
    """预测响应"""

    request: PredictionRequest
    prediction: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    cached: bool = False
    model_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "request": self.request.to_dict(),
            "prediction": self.prediction,
            "success": self.success,
            "error": self.error,
            "processing_time_ms": self.processing_time_ms,
            "cached": self.cached,
            "model_info": self.model_info,
            "timestamp": datetime.now().isoformat(),
        }


class InferenceServiceV2(BaseService):
    """
    推理服务 v2.0

    使用重构后的inference模块，提供简洁的服务层接口。
    专注于业务协调，底层实现委托给专业组件。
    """

    def __init__(self, model_path: Optional[str] = None):
        super().__init__("InferenceServiceV2")

        # 核心组件
        self.model_loader = ModelLoader()
        self.cache_manager = PredictionCache(enable_auto_cleanup=False)
        self.feature_extractor = MatchFeatureExtractor()

        # 默认配置
        self.default_model_path = model_path or "models/football_prediction_model.pkl"
        self.default_model_name = "football_model"

        # 业务统计
        self.request_stats = {
            "total_requests": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "errors": 0,
            "avg_processing_time_ms": 0.0,
        }

        self.is_initialized = False

    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            self.logger.info("正在初始化推理服务 v2.0...")

            # 尝试加载默认模型
            if Path(self.default_model_path).exists():
                success = await self._load_model_async(
                    self.default_model_name, self.default_model_path
                )
                if success:
                    self.logger.info(f"默认模型加载成功: {self.default_model_path}")
                else:
                    self.logger.warning(
                        f"默认模型加载失败，将使用降级模式: {self.default_model_path}"
                    )
            else:
                self.logger.info(
                    f"默认模型文件不存在，使用降级模式: {self.default_model_path}"
                )

            # 初始化特征提取器
            await self.feature_extractor.initialize()

            self.is_initialized = True
            self.logger.info("推理服务 v2.0 初始化成功")
            return True

        except Exception as e:
            self.logger.error(f"推理服务 v2.0 初始化失败: {e}")
            return False

    async def shutdown(self) -> None:
        """关闭服务"""
        try:
            self.logger.info("正在关闭推理服务 v2.0...")

            # 关闭缓存管理器
            await self.cache_manager.shutdown()

            # 关闭特征提取器
            if hasattr(self.feature_extractor, "shutdown"):
                await self.feature_extractor.shutdown()

            self.is_initialized = False
            self.logger.info("推理服务 v2.0 已关闭")

        except Exception as e:
            self.logger.error(f"推理服务 v2.0 关闭失败: {e}")

    async def _load_model_async(self, model_name: str, model_path: str) -> bool:
        """异步加载模型"""
        try:
            # 在线程池中执行同步的模型加载
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self.model_loader.load_model, model_name, model_path
            )
        except Exception as e:
            self.logger.error(f"模型加载异步执行失败: {e}")
            return False

    async def predict_match(self, request: PredictionRequest) -> PredictionResponse:
        """
        预测比赛结果

        Args:
            request: 预测请求

        Returns:
            PredictionResponse: 预测响应
        """
        if not self.is_initialized:
            return PredictionResponse(
                request=request, prediction={}, success=False, error="服务未初始化"
            )

        start_time = datetime.now()

        try:
            self.request_stats["total_requests"] += 1

            # 创建预测器实例
            predictor = MatchPredictor(
                model_loader=self.model_loader,
                cache_manager=self.cache_manager,
                default_model_name=request.model_name or self.default_model_name,
            )

            # 获取或生成特征
            features = await self._get_or_generate_features(request)

            # 执行预测
            prediction = await predictor.predict(
                features=features,
                model_name=request.model_name or self.default_model_name,
                use_cache=request.use_cache,
            )

            # 添加业务信息
            prediction.update(
                {
                    "match_id": request.match_id,
                    "home_team": request.home_team,
                    "away_team": request.away_team,
                    "requested_at": (
                        request.match_date.isoformat() if request.match_date else None
                    ),
                }
            )

            # 获取模型信息
            model_info = predictor.get_model_info()

            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_processing_stats(processing_time)

            # 检查是否使用缓存
            cached = prediction.get("from_cache", False)
            if cached:
                self.request_stats["cache_hits"] += 1

            self.request_stats["successful_predictions"] += 1

            return PredictionResponse(
                request=request,
                prediction=prediction,
                success=True,
                processing_time_ms=processing_time,
                cached=cached,
                model_info=model_info,
            )

        except Exception as e:
            self.request_stats["errors"] += 1
            error_msg = f"预测失败: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_processing_stats(processing_time)

            return PredictionResponse(
                request=request,
                prediction={},
                success=False,
                error=error_msg,
                processing_time_ms=processing_time,
            )

    async def _get_or_generate_features(
        self, request: PredictionRequest
    ) -> List[float]:
        """获取或生成特征数据"""
        if request.features is not None:
            # 使用提供的特征
            return request.features

        # 从数据库生成特征
        try:
            features = await self.feature_extractor.extract_features_from_match(
                match_id=request.match_id,
                home_team=request.home_team,
                away_team=request.away_team,
                match_date=request.match_date,
            )

            # 转换为列表格式
            if hasattr(features, "to_dict"):
                feature_dict = features.to_dict()
                feature_list = list(feature_dict.values())
            elif hasattr(features, "__iter__"):
                feature_list = list(features)
            else:
                feature_list = [features]

            return feature_list

        except Exception as e:
            self.logger.warning(f"特征生成失败，使用默认特征: {e}")
            # 返回默认特征向量（用于降级模式）
            return [1.0] * 12  # 假设12个特征

    def _update_processing_stats(self, processing_time_ms: float) -> None:
        """更新处理时间统计"""
        total_requests = self.request_stats["total_requests"]
        if total_requests == 1:
            self.request_stats["avg_processing_time_ms"] = processing_time_ms
        else:
            # 计算移动平均值
            current_avg = self.request_stats["avg_processing_time_ms"]
            self.request_stats["avg_processing_time_ms"] = (
                current_avg * (total_requests - 1) + processing_time_ms
            ) / total_requests

    async def predict_match_simple(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        match_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        简化的预测接口

        Args:
            match_id: 比赛ID
            home_team: 主队
            away_team: 客队
            match_date: 比赛日期

        Returns:
            Dict[str, Any]: 预测结果
        """
        request = PredictionRequest(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
        )

        response = await self.predict_match(request)
        return response.to_dict()

    async def batch_predict(
        self, requests: List[PredictionRequest]
    ) -> List[PredictionResponse]:
        """
        批量预测

        Args:
            requests: 预测请求列表

        Returns:
            List[PredictionResponse]: 预测响应列表
        """
        # 并发执行预测任务
        tasks = [self.predict_match(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        result = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                error_response = PredictionResponse(
                    request=requests[i],
                    prediction={},
                    success=False,
                    error=f"批量预测异常: {str(response)}",
                )
                result.append(error_response)
            else:
                result.append(response)

        return result

    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "service_name": self.name,
            "is_initialized": self.is_initialized,
            "model_status": {
                "loaded_models": self.model_loader.list_loaded_models(),
                "default_model": self.default_model_name,
            },
            "request_stats": self.request_stats.copy(),
            "cache_stats": (
                self.cache_manager.get_stats().__dict__
                if hasattr(self.cache_manager, "get_stats")
                else {}
            ),
            "components": {
                "model_loader": type(self.model_loader).__name__,
                "cache_manager": type(self.cache_manager).__name__,
                "feature_extractor": type(self.feature_extractor).__name__,
            },
        }

    def load_model(self, model_name: str, model_path: str) -> bool:
        """
        加载模型

        Args:
            model_name: 模型名称
            model_path: 模型文件路径

        Returns:
            bool: 加载是否成功
        """
        try:
            success = self.model_loader.load_model(model_name, model_path)
            if success:
                self.logger.info(f"模型加载成功: {model_name} from {model_path}")
            else:
                self.logger.error(f"模型加载失败: {model_name} from {model_path}")
            return success
        except Exception as e:
            self.logger.error(f"模型加载异常: {e}")
            return False

    def unload_model(self, model_name: str) -> bool:
        """
        卸载模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 卸载是否成功
        """
        try:
            success = self.model_loader.unload_model(model_name)
            if success:
                self.logger.info(f"模型卸载成功: {model_name}")
            else:
                self.logger.warning(f"模型卸载失败，可能未加载: {model_name}")
            return success
        except Exception as e:
            self.logger.error(f"模型卸载异常: {e}")
            return False

    def list_models(self) -> List[str]:
        """获取已加载的模型列表"""
        return self.model_loader.list_loaded_models()


# 创建全局服务实例
inference_service_v2 = InferenceServiceV2()

__all__ = [
    "InferenceServiceV2",
    "PredictionRequest",
    "PredictionResponse",
    "inference_service_v2",
]
