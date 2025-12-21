"""
Inference Service 隔离单元测试套件

验证推理服务的核心逻辑，包括模型加载、预测流程、缓存机制等
使用模拟对象避免依赖问题，专注测试业务逻辑
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd
import numpy as np
import tempfile
import json


class MockInferenceConfig:
    """模拟InferenceConfig类"""

    def __init__(self):
        # 模型配置
        self.model_path = "models/test_xgboost_classifier.pkl"
        self.fallback_model_path = None

        # 缓存配置
        self.enable_cache = True
        self.cache_ttl_seconds = 300
        self.max_cache_size = 1000

        # 性能配置
        self.request_timeout_seconds = 10.0
        self.max_concurrent_requests = 100

        # 降级策略
        self.enable_fallback = True
        self.default_probabilities = {
            "HOME_WIN_PROBA": 0.46,
            "DRAW_PROBA": 0.26,
            "AWAY_WIN_PROBA": 0.28,
        }

        # 监控配置
        self.enable_metrics = True
        self.log_prediction_requests = True

    def __post_init__(self):
        """确保概率总和为1.0"""
        total = sum(self.default_probabilities.values())
        if abs(total - 1.0) > 1e-6:
            for key in self.default_probabilities:
                self.default_probabilities[key] /= total


class MockModel:
    """模拟XGBoost模型"""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.is_loaded = False
        self.load_time = 0.0

    async def load_model(self, model_path: str) -> bool:
        """模拟模型加载"""
        if self.should_fail:
            raise Exception("模型加载失败")

        # 模拟加载时间
        await asyncio.sleep(0.01)
        self.load_time = time.time()
        self.is_loaded = True
        return True

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """模拟预测概率"""
        if not self.is_loaded:
            raise RuntimeError("模型未加载")

        # 生成随机概率，确保和为1
        batch_size = len(features)
        probabilities = np.random.dirichlet([1, 1, 1], batch_size)
        return probabilities

    def predict(self, features: np.ndarray) -> np.ndarray:
        """模拟预测类别"""
        proba = self.predict_proba(features)
        return np.argmax(proba, axis=1)


class MockFeatureExtractor:
    """模拟特征提取器"""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.extraction_time = 0.001

    async def extract_features(self, match_data: Dict[str, Any]) -> np.ndarray:
        """模拟特征提取"""
        if self.should_fail:
            raise Exception("特征提取失败")

        # 模拟提取时间
        await asyncio.sleep(self.extraction_time)

        # 返回模拟特征向量 (假设15个特征)
        return np.random.randn(15)


class MockCache:
    """模拟缓存系统"""

    def __init__(self, ttl_seconds=300, max_size=1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存值"""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        current_time = time.time()

        # 检查TTL
        if current_time - entry["timestamp"] > self.ttl_seconds:
            del self.cache[key]
            return None

        return entry["data"]

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """设置缓存值"""
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]

        self.cache[key] = {"data": data, "timestamp": time.time()}

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()

    def size(self) -> int:
        """返回缓存大小"""
        return len(self.cache)


class MockInferenceService:
    """模拟推理服务核心逻辑"""

    def __init__(self, config: Optional[MockInferenceConfig] = None):
        self.config = config or MockInferenceConfig()
        self.logger = Mock()

        # 组件
        self.model: Optional[MockModel] = None
        self.feature_extractor: Optional[MockFeatureExtractor] = None
        self.cache = (
            MockCache(
                ttl_seconds=self.config.cache_ttl_seconds,
                max_size=self.config.max_cache_size,
            )
            if self.config.enable_cache
            else None
        )

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "fallback_used": 0,
            "errors": 0,
            "avg_response_time_ms": 0.0,
            "model_load_time_ms": 0.0,
            "started_at": None,
            "last_prediction_time": None,
        }

        self.is_initialized = False

    async def initialize(self, model_should_fail=False, feature_should_fail=False) -> bool:
        """初始化服务"""
        start_time = time.time()

        try:
            # 初始化模型
            self.model = MockModel(should_fail=model_should_fail)
            if not await self.model.load_model(self.config.model_path):
                raise Exception("模型加载失败")

            # 初始化特征提取器
            self.feature_extractor = MockFeatureExtractor(should_fail=feature_should_fail)

            self.is_initialized = True
            self.stats["started_at"] = datetime.now(timezone.utc)
            self.stats["model_load_time_ms"] = (time.time() - start_time) * 1000

            return True

        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False

    async def predict_match(self, home_team: str, away_team: str, match_date: Optional[str] = None) -> Dict[str, Any]:
        """预测比赛结果"""
        if not self.is_initialized:
            raise RuntimeError("服务未初始化")

        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # 生成缓存键
            cache_key = f"{home_team}_{away_team}_{match_date or 'default'}"

            # 检查缓存
            if self.cache:
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    cached_result["from_cache"] = True
                    return cached_result

            # 构建比赛数据
            match_data = {
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date or datetime.now(timezone.utc).isoformat(),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }

            # 提取特征
            features = await self.feature_extractor.extract_features(match_data)
            features = features.reshape(1, -1)  # 确保是二维数组

            # 模型预测
            probabilities = self.model.predict_proba(features)[0]
            predicted_class_idx = np.argmax(probabilities)

            # 映射到类别名称
            class_names = ["HOME_WIN", "DRAW", "AWAY_WIN"]
            predicted_class = class_names[predicted_class_idx]

            # 构建结果
            result = {
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date,
                "HOME_WIN_PROBA": float(probabilities[0]),
                "DRAW_PROBA": float(probabilities[1]),
                "AWAY_WIN_PROBA": float(probabilities[2]),
                "predicted_class": predicted_class,
                "confidence": float(np.max(probabilities)),
                "model_version": "test_model_v1.0",
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "from_cache": False,
                "extraction_time_ms": 0.1,
                "prediction_time_ms": 0.05,
            }

            # 缓存结果
            if self.cache:
                self.cache.set(cache_key, result)

            # 更新统计
            self.stats["successful_predictions"] += 1
            self.stats["last_prediction_time"] = datetime.now(timezone.utc)

            # 更新平均响应时间
            response_time = (time.time() - start_time) * 1000
            current_avg = self.stats["avg_response_time_ms"]
            total_requests = self.stats["total_requests"]
            self.stats["avg_response_time_ms"] = (current_avg * (total_requests - 1) + response_time) / total_requests

            return result

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"预测失败: {e}")

            # 降级策略
            if self.config.enable_fallback:
                self.stats["fallback_used"] += 1
                return self._get_fallback_prediction(home_team, away_team, match_date)
            else:
                raise e

    def _get_fallback_prediction(self, home_team: str, away_team: str, match_date: Optional[str]) -> Dict[str, Any]:
        """获取降级预测结果"""
        return {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": match_date,
            "HOME_WIN_PROBA": self.config.default_probabilities["HOME_WIN_PROBA"],
            "DRAW_PROBA": self.config.default_probabilities["DRAW_PROBA"],
            "AWAY_WIN_PROBA": self.config.default_probabilities["AWAY_WIN_PROBA"],
            "predicted_class": "HOME_WIN",  # 默认预测
            "confidence": self.config.default_probabilities["HOME_WIN_PROBA"],
            "model_version": "fallback_v1.0",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "from_cache": False,
            "fallback_used": True,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            **self.stats,
            "cache_size": self.cache.size() if self.cache else 0,
            "is_initialized": self.is_initialized,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - self.stats["started_at"]).total_seconds()
                if self.stats["started_at"]
                else 0
            ),
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()


class TestInferenceConfig:
    """InferenceConfig测试"""

    def test_config_initialization(self):
        """测试配置初始化"""
        config = MockInferenceConfig()

        assert config.enable_cache is True
        assert config.cache_ttl_seconds == 300
        assert config.max_cache_size == 1000
        assert config.enable_fallback is True
        assert "HOME_WIN_PROBA" in config.default_probabilities

    def test_config_probability_normalization(self):
        """测试概率标准化"""
        config = MockInferenceConfig()
        config.default_probabilities = {
            "HOME_WIN_PROBA": 0.5,
            "DRAW_PROBA": 0.3,
            "AWAY_WIN_PROBA": 0.4,  # 总和为1.2
        }

        config.__post_init__()

        total = sum(config.default_probabilities.values())
        assert abs(total - 1.0) < 1e-6


class TestMockModel:
    """MockModel测试"""

    @pytest.mark.asyncio
    async def test_model_loading_success(self):
        """测试模型加载成功"""
        model = MockModel(should_fail=False)
        result = await model.load_model("test_model.pkl")

        assert result is True
        assert model.is_loaded is True
        assert model.load_time > 0

    @pytest.mark.asyncio
    async def test_model_loading_failure(self):
        """测试模型加载失败"""
        model = MockModel(should_fail=True)

        with pytest.raises(Exception, match="模型加载失败"):
            await model.load_model("test_model.pkl")

        assert model.is_loaded is False

    def test_model_prediction(self):
        """测试模型预测"""
        model = MockModel()
        model.is_loaded = True

        # 创建测试特征
        features = np.random.randn(10, 15)

        # 测试预测概率
        proba = model.predict_proba(features)
        assert proba.shape == (10, 3)
        assert np.allclose(proba.sum(axis=1), 1.0)  # 每行概率和为1

        # 测试预测类别
        pred = model.predict(features)
        assert pred.shape == (10,)
        assert all(0 <= p <= 2 for p in pred)

    def test_model_prediction_not_loaded(self):
        """测试未加载模型的预测"""
        model = MockModel()
        features = np.random.randn(1, 15)

        with pytest.raises(RuntimeError, match="模型未加载"):
            model.predict_proba(features)


class TestMockCache:
    """MockCache测试"""

    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        cache = MockCache(ttl_seconds=60, max_size=2)

        # 测试设置和获取
        data = {"test": "data", "timestamp": time.time()}
        cache.set("key1", data)
        retrieved = cache.get("key1")

        assert retrieved == data
        assert cache.size() == 1

    def test_cache_ttl_expiration(self):
        """测试缓存TTL过期"""
        cache = MockCache(ttl_seconds=0.1, max_size=10)  # 0.1秒过期

        data = {"test": "data"}
        cache.set("key1", data)

        # 立即获取应该成功
        assert cache.get("key1") == data

        # 等待过期后获取应该失败
        time.sleep(0.2)
        assert cache.get("key1") is None

    def test_cache_max_size_eviction(self):
        """测试缓存最大容量淘汰"""
        cache = MockCache(ttl_seconds=3600, max_size=2)

        cache.set("key1", {"data": "1", "timestamp": time.time()})
        cache.set("key2", {"data": "2", "timestamp": time.time()})
        cache.set("key3", {"data": "3", "timestamp": time.time() + 1})

        # 应该淘汰最旧的key1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
        assert cache.size() == 2


class TestInferenceService:
    """InferenceService核心测试"""

    @pytest.mark.asyncio
    async def test_service_initialization_success(self):
        """测试服务初始化成功"""
        service = MockInferenceService()
        result = await service.initialize()

        assert result is True
        assert service.is_initialized is True
        assert service.model is not None
        assert service.feature_extractor is not None
        assert service.stats["started_at"] is not None

    @pytest.mark.asyncio
    async def test_service_initialization_model_failure(self):
        """测试服务初始化时模型加载失败"""
        service = MockInferenceService()
        result = await service.initialize(model_should_fail=True)

        assert result is False
        assert service.is_initialized is False

    @pytest.mark.asyncio
    async def test_prediction_success(self):
        """测试预测成功"""
        service = MockInferenceService()
        await service.initialize()

        result = await service.predict_match("Manchester United", "Arsenal")

        assert result["home_team"] == "Manchester United"
        assert result["away_team"] == "Arsenal"
        assert "HOME_WIN_PROBA" in result
        assert "DRAW_PROBA" in result
        assert "AWAY_WIN_PROBA" in result
        assert result["predicted_class"] in ["HOME_WIN", "DRAW", "AWAY_WIN"]
        assert 0 <= result["confidence"] <= 1
        assert result["from_cache"] is False

    @pytest.mark.asyncio
    async def test_prediction_caching(self):
        """测试预测缓存"""
        config = MockInferenceConfig()
        config.enable_cache = True
        config.cache_ttl_seconds = 3600

        service = MockInferenceService(config)
        await service.initialize()

        # 第一次预测
        result1 = await service.predict_match("Team A", "Team B")
        assert result1["from_cache"] is False

        # 第二次相同预测应该从缓存获取
        result2 = await service.predict_match("Team A", "Team B")
        assert result2["from_cache"] is True
        assert result1["HOME_WIN_PROBA"] == result2["HOME_WIN_PROBA"]

        # 验证缓存统计
        stats = service.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_size"] == 1

    @pytest.mark.asyncio
    async def test_prediction_fallback(self):
        """测试预测降级策略"""
        config = MockInferenceConfig()
        config.enable_fallback = True
        config.default_probabilities = {
            "HOME_WIN_PROBA": 0.5,
            "DRAW_PROBA": 0.3,
            "AWAY_WIN_PROBA": 0.2,
        }

        service = MockInferenceService(config)
        await service.initialize()

        # 模拟特征提取失败
        service.feature_extractor.should_fail = True

        result = await service.predict_match("Team A", "Team B")

        assert result["fallback_used"] is True
        assert result["HOME_WIN_PROBA"] == 0.5
        assert result["DRAW_PROBA"] == 0.3
        assert result["AWAY_WIN_PROBA"] == 0.2
        assert result["model_version"] == "fallback_v1.0"

        # 验证降级统计
        stats = service.get_stats()
        assert stats["fallback_used"] == 1
        assert stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_prediction_without_fallback(self):
        """测试无降级策略的预测失败"""
        config = MockInferenceConfig()
        config.enable_fallback = False

        service = MockInferenceService(config)
        await service.initialize()

        # 模拟特征提取失败
        service.feature_extractor.should_fail = True

        with pytest.raises(Exception, match="特征提取失败"):
            await service.predict_match("Team A", "Team B")

    @pytest.mark.asyncio
    async def test_service_not_initialized(self):
        """测试未初始化服务的预测"""
        service = MockInferenceService()
        # 不调用initialize()

        with pytest.raises(RuntimeError, match="服务未初始化"):
            await service.predict_match("Team A", "Team B")

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """测试统计信息跟踪"""
        service = MockInferenceService()
        await service.initialize()

        # 执行多次预测
        await service.predict_match("Team A", "Team B")
        await service.predict_match("Team C", "Team D")
        await service.predict_match("Team A", "Team B")  # 缓存命中

        stats = service.get_stats()

        assert stats["total_requests"] == 3
        assert stats["successful_predictions"] >= 2
        assert stats["cache_hits"] == 1
        assert stats["errors"] == 0
        assert stats["avg_response_time_ms"] > 0
        assert stats["uptime_seconds"] > 0
        assert stats["is_initialized"] is True

    def test_cache_management(self):
        """测试缓存管理"""
        service = MockInferenceService()

        # 初始缓存为空
        if service.cache:
            assert service.cache.size() == 0

            # 清空缓存
            service.clear_cache()
            assert service.cache.size() == 0

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self):
        """测试并发预测"""
        service = MockInferenceService()
        await service.initialize()

        # 创建并发预测任务
        tasks = [service.predict_match(f"Team {i}", f"Opponent {i}") for i in range(10)]

        # 执行并发预测
        results = await asyncio.gather(*tasks)

        # 验证所有预测都成功
        assert len(results) == 10
        for result in results:
            assert "HOME_WIN_PROBA" in result
            assert result["from_cache"] is False  # 第一次都是未命中缓存

        # 验证统计
        stats = service.get_stats()
        assert stats["total_requests"] == 10
        assert stats["successful_predictions"] == 10


class TestInferenceServiceIntegration:
    """推理服务集成测试"""

    @pytest.mark.asyncio
    async def test_full_prediction_workflow(self):
        """测试完整预测工作流"""
        config = MockInferenceConfig()
        config.enable_cache = True
        config.cache_ttl_seconds = 60

        service = MockInferenceService(config)
        await service.initialize()

        # 执行预测
        result = await service.predict_match("Liverpool", "Manchester City", "2024-01-15T20:00:00Z")

        # 验证结果结构
        required_fields = [
            "home_team",
            "away_team",
            "match_date",
            "HOME_WIN_PROBA",
            "DRAW_PROBA",
            "AWAY_WIN_PROBA",
            "predicted_class",
            "confidence",
            "model_version",
            "processed_at",
            "from_cache",
        ]

        for field in required_fields:
            assert field in result

        # 验证数据类型和值
        assert isinstance(result["HOME_WIN_PROBA"], float)
        assert isinstance(result["DRAW_PROBA"], float)
        assert isinstance(result["AWAY_WIN_PROBA"], float)
        assert result["predicted_class"] in ["HOME_WIN", "DRAW", "AWAY_WIN"]
        assert 0 <= result["confidence"] <= 1

        # 验证概率和为1（允许小的浮点误差）
        prob_sum = result["HOME_WIN_PROBA"] + result["DRAW_PROBA"] + result["AWAY_WIN_PROBA"]
        assert abs(prob_sum - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """测试性能指标"""
        service = MockInferenceService()
        await service.initialize()

        # 执行一系列预测
        for i in range(5):
            await service.predict_match(f"Team {i}", f"Opponent {i}")

        stats = service.get_stats()

        # 验证性能指标
        assert stats["model_load_time_ms"] > 0
        assert stats["avg_response_time_ms"] > 0
        assert stats["successful_predictions"] == 5

        # 平均响应时间应该在合理范围内（< 100ms for mock）
        assert stats["avg_response_time_ms"] < 100

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试错误恢复"""
        service = MockInferenceService()
        await service.initialize()

        # 第一次预测成功
        result1 = await service.predict_match("Team A", "Team B")
        assert result1.get("fallback_used", False) is False

        # 模拟失败，启用降级
        service.feature_extractor.should_fail = True
        result2 = await service.predict_match("Team C", "Team D")
        assert result2["fallback_used"] is True

        # 恢复正常
        service.feature_extractor.should_fail = False
        result3 = await service.predict_match("Team E", "Team F")
        assert result3.get("fallback_used", False) is False

        # 验证统计
        stats = service.get_stats()
        assert stats["fallback_used"] == 1
        assert stats["successful_predictions"] == 2  # 只有成功的预测计入
        assert stats["errors"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
