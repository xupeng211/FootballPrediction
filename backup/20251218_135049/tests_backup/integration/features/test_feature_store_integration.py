"""
FeatureStore 集成测试.

使用真实的 PostgreSQL 数据库测试 FeatureStore 的完整功能。
这些测试运行较慢，但提供真实的集成验证。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from testcontainers.postgres import PostgresContainer
import asyncpg

from src.features.feature_store import FootballFeatureStore


class TestFeatureStoreIntegration:
    """FeatureStore 集成测试类。"""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """创建 PostgreSQL 容器用于测试。"""
        with PostgresContainer("postgres:15") as postgres:
            yield postgres

    @pytest.fixture(scope="class")
    def database_url(self, postgres_container):
        """获取数据库连接 URL。"""
        return postgres_container.get_connection_url()

    @pytest.fixture(scope="class")
    async def db_connection(self, database_url):
        """创建数据库连接。"""
        conn = await asyncpg.connect(database_url)
        try:
            # 创建测试表
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_store (
                    match_id BIGINT NOT NULL,
                    version VARCHAR(50) NOT NULL DEFAULT 'latest',
                    features JSONB NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (match_id, version)
                )
            """
            )

            # 创建索引
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_featurestore_match_id
                ON feature_store(match_id)
            """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_featurestore_features_gin
                ON feature_store USING GIN(features)
            """
            )

            yield conn
        finally:
            await conn.close()

    @pytest.fixture
    async def feature_store(self, database_url):
        """创建 FeatureStore 实例。"""
        # 临时设置数据库 URL
        import os

        original_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = database_url

        try:
            store = FootballFeatureStore(enable_logging=False)
            await store.initialize()
            yield store
            await store.close()
        finally:
            # 恢复原始数据库 URL
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    @pytest.fixture
    def sample_features(self) -> dict[str, Any]:
        """示例特征数据。"""
        return {
            "home_recent_5_wins": 3,
            "home_recent_5_win_rate": 0.6,
            "away_recent_5_wins": 2,
            "away_recent_5_win_rate": 0.4,
            "h2h_total_matches": 10,
            "h2h_home_win_rate": 0.7,
            "home_xg": 1.5,
            "away_xg": 1.2,
            "home_win_odds": 2.1,
            "home_implied_probability": 0.476,
            "home_possession": 55.5,
            "away_possession": 44.5,
        }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_and_load_features(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试保存和加载特征。"""
        match_id = 12345

        # 保存特征
        await feature_store.save_features(match_id, sample_features)

        # 加载特征
        loaded_data = await feature_store.load_features(match_id)

        # 验证结果
        assert loaded_data is not None
        assert loaded_data["match_id"] == match_id
        assert loaded_data["version"] == "latest"
        assert loaded_data["features"] == sample_features
        assert loaded_data["created_at"] is not None
        assert loaded_data["updated_at"] is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_and_load_with_version(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试带版本的特征保存和加载。"""
        match_id = 12346
        version = "v1.0"

        # 保存带版本的特征
        await feature_store.save_features(match_id, sample_features, version=version)

        # 加载特定版本
        loaded_data = await feature_store.load_features(match_id, version=version)

        # 验证结果
        assert loaded_data is not None
        assert loaded_data["match_id"] == match_id
        assert loaded_data["version"] == version
        assert loaded_data["features"] == sample_features

        # 验证不同版本的数据
        latest_data = await feature_store.load_features(match_id, version="latest")
        assert latest_data is None  # 没有 latest 版本

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_nonexistent_features(self, feature_store: FootballFeatureStore):
        """测试加载不存在的特征。"""
        result = await feature_store.load_features(99999)
        assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_batch_features(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试批量加载特征。"""
        match_ids = [12347, 12348, 12349]

        # 保存多个特征
        for i, match_id in enumerate(match_ids):
            features = {**sample_features, "batch_index": i}
            await feature_store.save_features(match_id, features)

        # 批量加载
        batch_data = await feature_store.load_batch(match_ids)

        # 验证结果
        assert len(batch_data) == 3
        for i, match_id in enumerate(match_ids):
            assert match_id in batch_data
            assert batch_data[match_id]["match_id"] == match_id
            assert batch_data[match_id]["features"]["batch_index"] == i
            assert (
                batch_data[match_id]["features"]["home_recent_5_wins"]
                == sample_features["home_recent_5_wins"]
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_batch_partial_match(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试批量加载部分匹配的情况。"""
        match_ids = [12350, 12351, 12352]

        # 只保存部分特征
        await feature_store.save_features(12350, sample_features)
        await feature_store.save_features(12352, sample_features)

        # 批量加载
        batch_data = await feature_store.load_batch(match_ids)

        # 验证结果
        assert len(batch_data) == 2
        assert 12350 in batch_data
        assert 12351 not in batch_data
        assert 12352 in batch_data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_features(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试查询特定特征字段。"""
        match_ids = [12353, 12354]
        feature_names = ["home_recent_5_wins", "away_recent_5_wins", "home_xg"]

        # 保存特征
        for match_id in match_ids:
            await feature_store.save_features(match_id, sample_features)

        # 查询特定特征
        results = await feature_store.query_features(match_ids, feature_names)

        # 验证结果
        assert len(results) == 2
        for result in results:
            assert len(result["features"]) == 3  # 只返回请求的特征
            assert "home_recent_5_wins" in result["features"]
            assert "away_recent_5_wins" in result["features"]
            assert "home_xg" in result["features"]
            assert "h2h_total_matches" not in result["features"]  # 未请求的特征

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upsert_features(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试更新现有特征（UPSERT）。"""
        match_id = 12355

        # 第一次保存
        await feature_store.save_features(match_id, sample_features)

        # 更新特征
        updated_features = {
            **sample_features,
            "home_recent_5_wins": 4,
            "updated_flag": True,
        }
        await feature_store.save_features(match_id, updated_features)

        # 加载并验证更新
        loaded_data = await feature_store.load_features(match_id)

        assert loaded_data is not None
        assert loaded_data["features"]["home_recent_5_wins"] == 4  # 已更新
        assert loaded_data["features"]["updated_flag"] is True  # 新增字段
        assert (
            loaded_data["features"]["away_recent_5_wins"]
            == sample_features["away_recent_5_wins"]
        )  # 保持不变

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_features(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试删除特征。"""
        match_id = 12356

        # 保存特征
        await feature_store.save_features(match_id, sample_features)

        # 验证存在
        loaded_data = await feature_store.load_features(match_id)
        assert loaded_data is not None

        # 删除特征
        result = await feature_store.delete_features(match_id)
        assert result is True

        # 验证已删除
        loaded_data = await feature_store.load_features(match_id)
        assert loaded_data is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_features_version_specific(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试删除特定版本的特征。"""
        match_id = 12357
        version_v1 = "v1.0"
        version_v2 = "v2.0"

        # 保存不同版本的特征
        await feature_store.save_features(match_id, sample_features, version=version_v1)
        await feature_store.save_features(
            match_id, {**sample_features, "version_2_flag": True}, version=version_v2
        )

        # 验证两个版本都存在
        v1_data = await feature_store.load_features(match_id, version=version_v1)
        v2_data = await feature_store.load_features(match_id, version=version_v2)
        assert v1_data is not None
        assert v2_data is not None

        # 删除特定版本
        result = await feature_store.delete_features(match_id, version=version_v1)
        assert result is True

        # 验证特定版本已删除，其他版本仍存在
        v1_data = await feature_store.load_features(match_id, version=version_v1)
        v2_data = await feature_store.load_features(match_id, version=version_v2)
        assert v1_data is None
        assert v2_data is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_feature_versions(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试列出特征版本。"""
        match_id = 12358
        versions = ["v1.0", "v2.0", "v3.0", "latest"]

        # 保存多个版本
        for version in versions:
            await feature_store.save_features(
                match_id, {**sample_features, "version": version}, version=version
            )

        # 列出版本
        version_list = await feature_store.list_feature_versions(match_id)

        # 验证结果
        assert len(version_list) == 4
        for version in versions:
            assert version in version_list

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_latest_feature_timestamp(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试获取最新特征时间戳。"""
        match_id = 12359

        # 保存特征
        before_save = datetime.now(timezone.utc)
        await feature_store.save_features(match_id, sample_features)

        # 获取时间戳
        timestamp = await feature_store.latest_feature_timestamp()

        # 验证时间戳
        assert timestamp is not None
        assert timestamp >= before_save

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stats(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试获取统计信息。"""
        # 保存多个特征
        match_ids = [12360, 12361, 12362]
        for match_id in match_ids:
            await feature_store.save_features(match_id, sample_features)

        # 获取统计信息
        stats = await feature_store.stats()

        # 验证结果
        assert stats["total_features"] >= 3
        assert stats["total_matches"] >= 3
        assert stats["latest_timestamp"] is not None
        # storage_size_mb 可能为 None，取决于数据库实现

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_check(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试健康检查。"""
        # 保存一些特征
        await feature_store.save_features(12363, sample_features)

        # 健康检查
        health = await feature_store.health_check()

        # 验证结果
        assert health["status"] == "healthy"
        assert health["initialized"] is True
        assert health["total_features"] >= 1
        assert health["total_matches"] >= 1
        assert health["latest_timestamp"] is not None
        assert "data_age_seconds" in health
        assert "max_batch_size" in health
        assert "retry_attempts" in health

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_batch_operations(
        self, feature_store: FootballFeatureStore, sample_features: dict[str, Any]
    ):
        """测试批量操作的性能。"""
        import time

        batch_size = 100
        match_ids = list(range(20000, 20000 + batch_size))

        # 测试批量保存性能
        start_time = time.time()
        for i, match_id in enumerate(match_ids):
            features = {**sample_features, "index": i}
            await feature_store.save_features(match_id, features)
        save_time = time.time() - start_time

        # 测试批量加载性能
        start_time = time.time()
        batch_data = await feature_store.load_batch(match_ids)
        load_time = time.time() - start_time

        # 验证结果
        assert len(batch_data) == batch_size
        assert save_time < 5.0  # 保存应在5秒内完成
        assert load_time < 1.0  # 加载应在1秒内完成

        print(f"保存 {batch_size} 个特征耗时: {save_time:.3f} 秒")
        print(f"加载 {batch_size} 个特征耗时: {load_time:.3f} 秒")

        # 计算平均性能
        avg_save_time = save_time / batch_size * 1000  # 毫秒
        avg_load_time = load_time / batch_size * 1000  # 毫秒

        print(f"平均保存时间: {avg_save_time:.2f} 毫秒/特征")
        print(f"平均加载时间: {avg_load_time:.2f} 毫秒/特征")

        # 性能断言
        assert avg_save_time < 50  # 每个特征保存时间应小于50毫秒
        assert avg_load_time < 10  # 每个特征加载时间应小于10毫秒

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_jsonb_feature_queries(
        self, feature_store: FootballFeatureStore, db_connection
    ):
        """测试 JSONB 特征查询功能。"""
        match_id = 12364
        features = {
            "nested": {"level1": {"level2": "deep_value"}},
            "array": [1, 2, 3, 4, 5],
            "mixed_types": {
                "string": "test",
                "number": 42,
                "boolean": True,
                "null": None,
            },
        }

        # 保存复杂特征
        await feature_store.save_features(match_id, features)

        # 直接查询数据库验证 JSONB 存储
        row = await db_connection.fetchrow(
            "SELECT features FROM feature_store WHERE match_id = $1", match_id
        )

        assert row is not None
        stored_features = row["features"]
        assert stored_features["nested"]["level1"]["level2"] == "deep_value"
        assert stored_features["array"] == [1, 2, 3, 4, 5]
        assert stored_features["mixed_types"]["string"] == "test"
        assert stored_features["mixed_types"]["number"] == 42
        assert stored_features["mixed_types"]["boolean"] is True
        assert stored_features["mixed_types"]["null"] is None

        # 使用 FeatureStore 加载并验证
        loaded_data = await feature_store.load_features(match_id)
        assert loaded_data["features"] == features
