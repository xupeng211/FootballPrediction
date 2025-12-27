#!/usr/bin/env python3
"""
推理服务 - Sprint 3 依赖注入重构版本

实现企业级依赖注入模式，消除硬编码依赖。
支持构造函数注入、生命周期管理和配置注入。

Sprint 3 改进:
- 依赖注入重构 (P0-005) ✅
- 移除硬编码实例化 ✅
- 构造函数注入模式 ✅
- 服务生命周期管理 ✅

设计原则:
- Constructor Injection (构造函数注入)
- Dependency Inversion (依赖倒置)
- Single Responsibility (单一职责)
- Configuration Externalization (配置外部化)
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .dependency_injection import ServiceLifecycle, injectable

logger = logging.getLogger(__name__)


# 定义依赖接口协议
class ModelProtocol(Protocol):
    """模型协议接口"""

    async def predict(self, features: Any) -> Any:
        """预测方法"""
        ...

    async def predict_proba(self, features: Any) -> Any:
        """概率预测方法"""
        ...

    @property
    def is_trained(self) -> bool:
        """是否已训练"""
        ...

    def get_model_info(self) -> dict[str, Any]:
        """获取模型信息"""
        ...


class FeatureExtractorProtocol(Protocol):
    """特征提取器协议接口"""

    async def extract_features(self, match_id: str, historical_data: Any) -> Any:
        """提取特征方法"""
        ...


class DatabaseProtocol(Protocol):
    """数据库协议接口"""

    async def fetchrow(self, query: str, *args) -> dict[str, Any] | None:
        """查询单行数据"""
        ...

    async def fetch(self, query: str, *args) -> list[dict[str, Any]]:
        """查询多行数据"""
        ...


@dataclass
class InferenceServiceConfig:
    """推理服务配置类"""

    # 模型配置
    model_path: str = "models/football_xgboost_classifier.pkl"
    fallback_model_path: str | None = None

    # 缓存配置
    enable_cache: bool = True
    cache_ttl_seconds: int = 300  # 5分钟
    max_cache_size: int = 1000

    # 性能配置
    request_timeout_seconds: float = 10.0
    max_concurrent_requests: int = 100

    # 降级策略
    enable_fallback: bool = True
    default_probabilities: dict[str, float] = None

    # 监控配置
    enable_metrics: bool = True
    log_prediction_requests: bool = True

    def __post_init__(self):
        """初始化后处理"""
        if self.default_probabilities is None:
            self.default_probabilities = {
                "HOME_WIN_PROBA": 0.46,
                "DRAW_PROBA": 0.26,
                "AWAY_WIN_PROBA": 0.28,
            }

        # 确保概率总和为1.0
        total = sum(self.default_probabilities.values())
        if abs(total - 1.0) > 1e-6:
            for key in self.default_probabilities:
                self.default_probabilities[key] /= total


@injectable("inference_service", ["model_service", "feature_extractor", "database_service"])
class InferenceService(ServiceLifecycle):
    """
    推理服务 - Sprint 3 依赖注入版本

    通过构造函数注入所有依赖，实现松耦合架构。
    支持配置注入和生命周期管理。

    主要改进:
    - 移除硬编码依赖实例化
    - 使用构造函数注入模式
    - 实现服务生命周期管理
    - 支持配置外部化
    """

    def __init__(
        self,
        model_service: ModelProtocol,
        feature_extractor: FeatureExtractorProtocol,
        database_service: DatabaseProtocol,
        config: InferenceServiceConfig | None = None,
    ):
        """
        初始化推理服务 - 使用依赖注入

        Args:
            model_service: 模型服务实例
            feature_extractor: 特征提取器实例
            database_service: 数据库服务实例
            config: 推理服务配置
        """
        self.model_service = model_service
        self.feature_extractor = feature_extractor
        self.database_service = database_service
        self.config = config or InferenceServiceConfig()

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 缓存
        self._prediction_cache: dict[str, tuple[dict[str, Any], float]] = {}

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "fallback_used": 0,
            "errors": 0,
            "avg_response_time_ms": 0.0,
            "started_at": None,
            "last_prediction_time": None,
        }

        self._initialized = False

    async def initialize(self) -> None:
        """初始化服务"""
        try:
            # 验证依赖服务
            if not self.model_service:
                raise ValueError("model_service 不能为空")
            if not self.feature_extractor:
                raise ValueError("feature_extractor 不能为空")
            if not self.database_service:
                raise ValueError("database_service 不能为空")

            # 验证模型状态
            if not getattr(self.model_service, "is_trained", False):
                self.logger.warning("模型未训练，可能影响预测质量")

            # 记录初始化时间
            self.stats["started_at"] = datetime.now().isoformat()
            self._initialized = True

            self.logger.info("InferenceService 初始化完成")

        except Exception as e:
            self.logger.error(f"InferenceService 初始化失败: {e}")
            raise

    async def shutdown(self) -> None:
        """关闭服务"""
        # 清理缓存
        self._prediction_cache.clear()
        self._initialized = False
        self.logger.info("InferenceService 已关闭")

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    async def predict(self, match_id: str) -> dict[str, Any]:
        """
        进行比赛预测

        Args:
            match_id: 比赛ID

        Returns:
            Dict[str, Any]: 预测结果
        """
        if not self._initialized:
            raise RuntimeError("推理服务未初始化")

        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # 1. 检查缓存
            if self.config.enable_cache:
                cached_result = self._get_from_cache(match_id)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    return cached_result

            # 2. 获取比赛数据
            match_data = await self._fetch_match_data(match_id)

            # 3. 获取历史数据
            historical_data = await self._get_historical_data(match_data)

            # 4. 提取特征
            features = await self.feature_extractor.extract_features(match_id, historical_data)

            # 5. 进行推理
            prediction_result = await self._perform_inference(match_id, features)

            # 6. 缓存结果
            if self.config.enable_cache:
                self._add_to_cache(match_id, prediction_result)

            # 7. 更新统计
            response_time = (time.time() - start_time) * 1000
            self._update_stats(response_time, success=True)

            if self.config.log_prediction_requests:
                self.logger.info(
                    f"预测请求: {match_id} -> {prediction_result['predicted_class']} "
                    f"(置信度: {prediction_result['confidence']:.3f})"
                )

            return prediction_result

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"预测失败 {match_id}: {e}")

            # 使用降级策略
            if self.config.enable_fallback:
                self.stats["fallback_used"] += 1
                return self._create_fallback_result(match_id, str(e))
            else:
                raise RuntimeError(f"预测服务内部错误: {str(e)}")

    async def _fetch_match_data(self, match_id: str) -> dict[str, Any]:
        """从数据库获取比赛数据"""
        try:
            query = """
            SELECT
                match_id,
                home_team_id,
                away_team_id,
                match_date,
                home_score,
                away_score,
                status,
                venue,
                league_id
            FROM raw_match_data
            WHERE match_id = $1
            """

            record = await self.database_service.fetchrow(query, match_id)

            if not record:
                raise ValueError(f"比赛不存在: {match_id}")

            return dict(record)

        except Exception as e:
            self.logger.error(f"获取比赛数据失败 {match_id}: {e}")
            raise RuntimeError(f"数据库查询失败: {str(e)}")

    async def _get_historical_data(self, match_data: dict[str, Any]) -> Any:
        """获取历史数据用于特征提取"""
        try:
            match_date = match_data.get("match_date")
            league_id = match_data.get("league_id")

            if league_id:
                query = """
                SELECT
                    match_id,
                    home_team_id,
                    away_team_id,
                    match_date,
                    home_score,
                    away_score,
                    home_xg,
                    away_xg,
                    home_odds,
                    draw_odds,
                    away_odds,
                    status,
                    venue
                FROM raw_match_data
                WHERE league_id = $1
                    AND match_date < $2
                    AND status = 'FINISHED'
                ORDER BY match_date DESC
                LIMIT 200
                """
                records = await self.database_service.fetch(query, league_id, match_date)
            else:
                query = """
                SELECT
                    match_id,
                    home_team_id,
                    away_team_id,
                    match_date,
                    home_score,
                    away_score,
                    home_xg,
                    away_xg,
                    home_odds,
                    draw_odds,
                    away_odds,
                    status,
                    venue
                FROM raw_match_data
                WHERE match_date < $1
                    AND status = 'FINISHED'
                ORDER BY match_date DESC
                LIMIT 200
                """
                records = await self.database_service.fetch(query, match_date)

            if not records:
                self.logger.warning("未找到历史数据，返回空数据集")
                return []

            return records

        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            return []

    async def _perform_inference(self, match_id: str, features: Any) -> dict[str, Any]:
        """执行模型推理"""
        try:
            # 使用模型服务进行预测
            predicted_class = await self.model_service.predict(features)
            probabilities = await self.model_service.predict_proba(features)

            # 获取模型信息
            model_info = self.model_service.get_model_info()

            # 构建结果
            result = {
                "match_id": match_id,
                "HOME_WIN_PROBA": float(probabilities.get("HOME_WIN_PROBA", 0.0)),
                "DRAW_PROBA": float(probabilities.get("DRAW_PROBA", 0.0)),
                "AWAY_WIN_PROBA": float(probabilities.get("AWAY_WIN_PROBA", 0.0)),
                "predicted_class": str(predicted_class),
                "confidence": float(max(probabilities.values()) if probabilities else 0.0),
                "model_version": model_info.get("model_version", "1.0.0"),
                "processed_at": datetime.now().isoformat(),
            }

            self.stats["successful_predictions"] += 1
            return result

        except Exception as e:
            self.logger.error(f"推理执行失败 {match_id}: {e}")
            raise RuntimeError(f"模型推理失败: {str(e)}")

    def _get_from_cache(self, match_id: str) -> dict[str, Any] | None:
        """从缓存获取结果"""
        if not self.config.enable_cache:
            return None

        cached_item = self._prediction_cache.get(match_id)
        if cached_item:
            result, timestamp = cached_item
            age = time.time() - timestamp

            if age < self.config.cache_ttl_seconds:
                return result
            else:
                del self._prediction_cache[match_id]

        return None

    def _add_to_cache(self, match_id: str, result: dict[str, Any]) -> None:
        """添加结果到缓存"""
        if not self.config.enable_cache:
            return

        # 检查缓存大小
        if len(self._prediction_cache) >= self.config.max_cache_size:
            oldest_key = min(
                self._prediction_cache.keys(),
                key=lambda k: self._prediction_cache[k][1],
            )
            del self._prediction_cache[oldest_key]

        self._prediction_cache[match_id] = (result, time.time())

    def _create_fallback_result(self, match_id: str, error_message: str) -> dict[str, Any]:
        """创建降级结果"""
        return {
            "match_id": match_id,
            "HOME_WIN_PROBA": self.config.default_probabilities["HOME_WIN_PROBA"],
            "DRAW_PROBA": self.config.default_probabilities["DRAW_PROBA"],
            "AWAY_WIN_PROBA": self.config.default_probabilities["AWAY_WIN_PROBA"],
            "predicted_class": "HOME_WIN",
            "confidence": self.config.default_probabilities["HOME_WIN_PROBA"],
            "model_version": "fallback",
            "error_message": error_message,
            "processed_at": datetime.now().isoformat(),
        }

    def _update_stats(self, response_time_ms: float, success: bool) -> None:
        """更新统计信息"""
        # 更新平均响应时间
        current_avg = self.stats["avg_response_time_ms"]
        total_requests = self.stats["total_requests"]
        self.stats["avg_response_time_ms"] = (current_avg * (total_requests - 1) + response_time_ms) / total_requests

        # 更新最后预测时间
        self.stats["last_prediction_time"] = datetime.now().isoformat()

    def get_service_stats(self) -> dict[str, Any]:
        """获取服务统计信息"""
        return {
            **self.stats,
            "cache_size": len(self._prediction_cache),
            "is_initialized": self._initialized,
            "config": {
                "enable_cache": self.config.enable_cache,
                "cache_ttl_seconds": self.config.cache_ttl_seconds,
                "max_cache_size": self.config.max_cache_size,
                "enable_fallback": self.config.enable_fallback,
                "model_path": self.config.model_path,
            },
        }

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "model_loaded": self.model_service is not None,
            "feature_extractor_ready": self.feature_extractor is not None,
            "database_connected": self.database_service is not None,
            "cache_enabled": self.config.enable_cache,
            "total_predictions": self.stats["successful_predictions"],
            "avg_response_time_ms": self.stats["avg_response_time_ms"],
        }
