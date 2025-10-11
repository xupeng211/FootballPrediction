"""
测试数据处理组件

验证拆分后的各个数据处理组件的功能。
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

from src.services.processing import (
    DataProcessingService,
    MatchProcessor,
    OddsProcessor,
    FeaturesProcessor,
    DataValidator,
    ProcessingCache,
)


class TestMatchProcessor:
    """测试比赛数据处理器"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        return MatchProcessor()

    @pytest.mark.asyncio
    async def test_process_raw_match_data_dict(self, processor):
        """测试处理字典格式的比赛数据"""
        raw_data = {
            "match_id": "123",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2024-01-01",
            "home_score": 2,
            "away_score": 1,
        }

        result = await processor.process_raw_match_data(raw_data)

        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["match_id"] == "123"
        assert "processed_at" in result.columns

    @pytest.mark.asyncio
    async def test_process_raw_match_data_list(self, processor):
        """测试处理列表格式的比赛数据"""
        raw_data = [
            {
                "match_id": "123",
                "home_team": "Team A",
                "away_team": "Team B",
                "match_date": "2024-01-01",
            },
            {
                "match_id": "456",
                "home_team": "Team C",
                "away_team": "Team D",
                "match_date": "2024-01-02",
            },
        ]

        result = await processor.process_raw_match_data(raw_data)

        assert result is not None
        assert len(result) == 2
        assert "processed_at" in result.columns

    @pytest.mark.asyncio
    async def test_process_empty_data(self, processor):
        """测试处理空数据"""
        result = await processor.process_raw_match_data([])
        assert result is None

    @pytest.mark.asyncio
    async def test_standardize_team_names(self, processor):
        """测试队名标准化"""
        # 创建测试数据
        df = pd.DataFrame([{"home_team": "  MANCHESTER UNITED  "}])

        # 调用私有方法
        standardized = await processor._standardize_team_names(df)

        assert standardized.iloc[0]["home_team"] == "Manchester United"


class TestOddsProcessor:
    """测试赔率数据处理器"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        return OddsProcessor()

    @pytest.mark.asyncio
    async def test_process_raw_odds_data(self, processor):
        """测试处理原始赔率数据"""
        raw_data = {
            "match_id": "123",
            "bookmaker": "BookmakerA",
            "home_win": 2.5,
            "draw": 3.2,
            "away_win": 2.8,
        }

        result = await processor.process_raw_odds_data(raw_data)

        assert result is not None
        assert len(result) == 1
        assert "implied_probability" in result.columns
        assert "bookmaker_margin" in result.columns

    @pytest.mark.asyncio
    async def test_detect_arbitrage_opportunities(self, processor):
        """测试套利机会检测"""
        # 创建包含套利机会的数据
        df = pd.DataFrame(
            [
                {
                    "match_id": "123",
                    "bookmaker": "BookmakerA",
                    "home_win": 2.1,
                    "draw": 3.4,
                    "away_win": 4.0,
                },
                {
                    "match_id": "123",
                    "bookmaker": "BookmakerB",
                    "home_win": 2.0,
                    "draw": 3.3,
                    "away_win": 4.2,
                },
            ]
        )

        opportunities = await processor.detect_arbitrage_opportunities(df)

        assert isinstance(opportunities, list)


class TestFeaturesProcessor:
    """测试特征数据处理器"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        return FeaturesProcessor()

    @pytest.mark.asyncio
    async def test_process_features_data(self, processor):
        """测试特征数据生成"""
        match_data = {
            "match_id": "123",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2024-01-01",
        }

        result = await processor.process_features_data(match_data)

        assert result is not None
        assert len(result) == 1
        # 检查是否包含生成的特征
        feature_cols = [col for col in result.columns if "form" in col]
        assert len(feature_cols) > 0

    @pytest.mark.asyncio
    async def test_get_feature_importance(self, processor):
        """测试特征重要性计算"""
        feature_names = ["feature1", "feature2", "feature3"]

        importance = await processor.get_feature_importance(feature_names)

        assert isinstance(importance, dict)
        assert len(importance) == len(feature_names)
        # 检查是否已归一化
        assert abs(sum(importance.values()) - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_select_top_features(self, processor):
        """测试选择重要特征"""
        # 创建测试数据
        df = pd.DataFrame(
            {
                "match_id": ["1", "2", "3"],
                "feature1": [0.1, 0.2, 0.3],
                "feature2": [0.4, 0.5, 0.6],
                "feature3": [0.7, 0.8, 0.9],
                "target": [1, 0, 1],
            }
        )

        top_features = await processor.select_top_features(df, "target", k=2)

        assert isinstance(top_features, list)
        assert len(top_features) == 2


class TestDataValidator:
    """测试数据验证器"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return DataValidator()

    @pytest.mark.asyncio
    async def test_validate_match_data_valid(self, validator):
        """测试有效比赛数据验证"""
        valid_data = {
            "match_id": "123",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2024-01-01",
            "home_score": 2,
            "away_score": 1,
        }

        result = await validator.validate_data_quality(valid_data, "match_data")

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_match_data_missing_fields(self, validator):
        """测试缺失字段的比赛数据验证"""
        invalid_data = {
            "match_id": "123",
            # 缺少必需字段
        }

        result = await validator.validate_data_quality(invalid_data, "match_data")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("缺少必需字段" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_odds_data_invalid_odds(self, validator):
        """测试无效赔率数据验证"""
        invalid_odds = {
            "match_id": "123",
            "bookmaker": "TestBookmaker",
            "home_win": 0.5,  # 小于1，无效
            "draw": 3.2,
            "away_win": 2.8,
        }

        result = await validator.validate_data_quality(invalid_odds, "odds_data")

        assert result["valid"] is False
        assert any("不能小于等于1" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_batch_consistency(self, validator):
        """测试批次数据一致性验证"""
        # 创建一致的批次数据
        batch1 = pd.DataFrame(
            {
                "match_id": ["1", "2"],
                "home_team": ["A", "B"],
                "away_team": ["C", "D"],
            }
        )

        batch2 = pd.DataFrame(
            {
                "match_id": ["3", "4"],
                "home_team": ["E", "F"],
                "away_team": ["G", "H"],
            }
        )

        result = await validator.validate_batch_consistency([batch1, batch2])

        assert result["consistent"] is True
        assert len(result["issues"]) == 0


class TestProcessingCache:
    """测试处理缓存"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return ProcessingCache()

    @pytest.mark.asyncio
    async def test_cache_result_and_get_cached_result(self, cache):
        """测试缓存存储和获取"""
        # 模拟 Redis 管理器
        cache.redis_manager = AsyncMock()
        cache.redis_manager.get.return_value = None
        cache.redis_manager.set.return_value = True

        # 缓存结果
        success = await cache.cache_result(
            operation="test",
            data={"key": "value"},
            result={"result": "success"},
        )

        assert success is True
        cache.redis_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled(self, cache):
        """测试缓存禁用时的行为"""
        cache.cache_enabled = False

        result = await cache.get_cached_result("test", {"data": "value"})

        assert result is None
        assert cache.stats["misses"] == 1

    def test_calculate_data_hash(self, cache):
        """测试数据哈希计算"""
        data1 = {"key": "value"}
        data2 = {"key": "value"}
        data3 = {"key": "different"}

        hash1 = cache._calculate_data_hash(data1)
        hash2 = cache._calculate_data_hash(data2)
        hash3 = cache._calculate_data_hash(data3)

        # 相同数据应有相同哈希
        assert hash1 == hash2
        # 不同数据应有不同哈希
        assert hash1 != hash3


class TestDataProcessingService:
    """测试主数据处理服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DataProcessingService()

    @pytest.mark.asyncio
    async def test_initialize_service(self, service):
        """测试服务初始化"""
        with patch.object(
            service.processing_cache, "initialize", new_callable=AsyncMock
        ) as mock_init:
            await service.initialize()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_match_data_flow(self, service):
        """测试比赛数据处理流程"""
        # 模拟组件行为
        service.processing_cache.get_cached_result = AsyncMock(return_value=None)
        service.match_processor.process_raw_match_data = AsyncMock(
            return_value=pd.DataFrame([{"match_id": "123"}])
        )
        service.data_validator.validate_data_quality = AsyncMock(
            return_value={"valid": True, "errors": [], "warnings": []}
        )
        service.processing_cache.cache_result = AsyncMock(return_value=True)

        raw_data = {"match_id": "123", "home_team": "A", "away_team": "B"}

        result = await service.process_match_data(raw_data)

        assert result is not None
        assert len(result) == 1
        assert service.processing_stats["matches_processed"] == 1

    @pytest.mark.asyncio
    async def test_process_batch_data(self, service):
        """测试批量数据处理"""
        # 模拟单个处理
        service.process_match_data = AsyncMock(
            return_value=pd.DataFrame([{"match_id": "123"}])
        )

        batches = [
            {"match_id": "123", "home_team": "A", "away_team": "B"},
            {"match_id": "456", "home_team": "C", "away_team": "D"},
        ]

        results = await service.process_batch_data(batches, data_type="match")

        assert len(results) == 2
        service.process_match_data.assert_called()

    @pytest.mark.asyncio
    async def test_get_processing_statistics(self, service):
        """测试获取处理统计"""
        # 模拟缓存统计
        service.processing_cache.get_cache_stats = AsyncMock(
            return_value={"hit_rate": 85.5, "cache_enabled": True}
        )

        stats = await service.get_processing_statistics()

        assert "processing_stats" in stats
        assert "cache_stats" in stats
        assert "service_health" in stats

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """测试健康检查"""
        service.processing_cache.get_cache_stats = AsyncMock(
            return_value={"cache_enabled": True, "hit_rate": 80.0}
        )

        health = await service.health_check()

        assert health["status"] == "healthy"
        assert "components" in health
        assert "cache" in health["components"]
        assert "match_processor" in health["components"]

    @pytest.mark.asyncio
    async def test_clear_cache(self, service):
        """测试清理缓存"""
        service.processing_cache.invalidate_cache = AsyncMock(return_value=5)

        cleared_count = await service.clear_cache("match_processing")

        assert cleared_count == 5
        service.processing_cache.invalidate_cache.assert_called_with("match_processing")

    def test_reset_statistics(self, service):
        """测试重置统计"""
        # 设置一些统计
        service.processing_stats["matches_processed"] = 100

        service.reset_statistics()

        assert service.processing_stats["matches_processed"] == 0
        assert all(v == 0 for v in service.processing_stats.values())
