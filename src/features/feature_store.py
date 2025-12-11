"""
Football Prediction FeatureStore 实现.

基于 async_manager.py 的异步特征存储实现，支持高并发特征访问。
这个实现遵循 FeatureStoreProtocol 接口，提供生产就绪的特征管理功能。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.database.async_manager import get_db_session
from src.features.feature_store_interface import (
    DEFAULT_FEATURE_VERSION,
    FeatureData,
    FeatureStoreProtocol,
    FeatureQueryResult,
    FeatureStats,
    FeatureValidationError,
    StorageError,
)

# 导入缓存装饰器
from src.core.cache import cached

logger = logging.getLogger(__name__)


class FootballFeatureStore(FeatureStoreProtocol):
    """
    足球预测特征存储实现.

    基于 PostgreSQL + JSONB 的特征存储，支持:
    - 异步高并发读写
    - 版本管理
    - 批量操作
    - 自动重试
    - 性能监控
    - 数据完整性检查
    """

    def __init__(
        self,
        max_batch_size: int = 1000,
        retry_attempts: int = 3,
        enable_logging: bool = True,
    ):
        """
        初始化 FeatureStore.

        Args:
            max_batch_size: 批量操作的最大大小
            retry_attempts: 重试次数
            enable_logging: 是否启用详细日志
        """
        self.max_batch_size = max_batch_size
        self.retry_attempts = retry_attempts
        self.enable_logging = enable_logging
        self._initialized = False

    async def initialize(self) -> None:
        """初始化存储后端，确保表结构存在."""
        if self._initialized:
            return

        try:
            async with get_db_session() as session:
                # 创建表结构（通过执行迁移）
                await session.execute(
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
                await session.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_featurestore_match_id
                    ON feature_store(match_id)
                """
                )

                await session.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_featurestore_features_gin
                    ON feature_store USING GIN(features)
                """
                )

                await session.commit()
                self._initialized = True

                if self.enable_logging:
                    logger.info("FeatureStore initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize FeatureStore: {e}")
            raise StorageError(f"Initialization failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((StorageError,)),
        reraise=True,
    )
    async def save_features(
        self,
        match_id: int,
        features: dict[str, Any],
        version: str = DEFAULT_FEATURE_VERSION,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        保存特征数据到存储.

        Args:
            match_id: 比赛ID
            features: 特征数据字典
            version: 特征版本
            metadata: 可选的元数据

        Raises:
            FeatureValidationError: 当输入数据无效时
            StorageError: 当存储操作失败时
        """
        await self._ensure_initialized()

        # 输入验证
        self._validate_match_id(match_id)
        self._validate_features(features)
        self._validate_version(version)

        try:
            async with get_db_session() as session:
                # 使用 UPSERT 操作 (ON CONFLICT UPDATE)
                query = """
                    INSERT INTO feature_store (match_id, version, features, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (match_id, version)
                    DO UPDATE SET
                        features = EXCLUDED.features,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """

                await session.execute(
                    query,
                    (
                        match_id,
                        version,
                        json.dumps(features),
                        json.dumps(metadata) if metadata else None,
                    ),
                )

                await session.commit()

                if self.enable_logging:
                    logger.debug(
                        f"Saved features for match {match_id}, version {version}"
                    )

        except Exception as e:
            logger.error(f"Failed to save features for match {match_id}: {e}")
            raise StorageError(f"Save operation failed: {e}") from e

    @cached(
        ttl=300,  # 5分钟缓存
        namespace="features",
        stampede_protection=True,
        key_builder=lambda match_id,
        version=DEFAULT_FEATURE_VERSION: f"feature:{match_id}:{version}",
    )
    async def load_features(
        self, match_id: int, version: str = DEFAULT_FEATURE_VERSION
    ) -> Optional[FeatureData]:
        """
        加载单个比赛的特征数据.

        Args:
            match_id: 比赛ID
            version: 特征版本

        Returns:
            FeatureData 对象，如果不存在则返回 None
        """
        await self._ensure_initialized()
        self._validate_match_id(match_id)
        self._validate_version(version)

        try:
            async with get_db_session() as session:
                query = """
                    SELECT match_id, features, version, metadata, created_at, updated_at
                    FROM feature_store
                    WHERE match_id = %s AND version = %s
                """

                result = await session.execute(query, (match_id, version))
                row = result.fetchone()

                if row:
                    return FeatureData(
                        match_id=row[0],
                        features=(
                            json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        ),
                        version=row[2],
                        metadata=json.loads(row[3]) if row[3] else None,
                        created_at=row[4],
                        updated_at=row[5],
                    )
                return None

        except Exception as e:
            logger.error(f"Failed to load features for match {match_id}: {e}")
            raise StorageError(f"Load operation failed: {e}") from e

    async def load_batch(
        self, match_ids: list[int], version: str = DEFAULT_FEATURE_VERSION
    ) -> dict[int, FeatureData]:
        """
        批量加载多个比赛的特征数据.

        Args:
            match_ids: 比赛ID列表
            version: 特征版本

        Returns:
            字典，key为match_id，value为FeatureData
        """
        await self._ensure_initialized()

        if not match_ids:
            return {}

        if len(match_ids) > self.max_batch_size:
            raise FeatureValidationError(
                f"Batch size {len(match_ids)} exceeds maximum {self.max_batch_size}"
            )

        self._validate_version(version)

        try:
            async with get_db_session() as session:
                # 使用 IN 查询批量加载
                placeholders = ",".join(["%s"] * len(match_ids))
                query = f"""
                    SELECT match_id, features, version, metadata, created_at, updated_at
                    FROM feature_store
                    WHERE match_id IN ({placeholders}) AND version = %s
                """

                result = await session.execute(query, match_ids + [version])
                rows = result.fetchall()

                # 构建结果字典
                batch_data = {}
                for row in rows:
                    batch_data[row[0]] = FeatureData(
                        match_id=row[0],
                        features=(
                            json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        ),
                        version=row[2],
                        metadata=json.loads(row[3]) if row[3] else None,
                        created_at=row[4],
                        updated_at=row[5],
                    )

                if self.enable_logging:
                    logger.debug(
                        f"Loaded {len(batch_data)} feature sets from {len(match_ids)} requests"
                    )

                return batch_data

        except Exception as e:
            logger.error(f"Failed to load batch features: {e}")
            raise StorageError(f"Batch load operation failed: {e}") from e

    async def query_features(
        self,
        match_ids: list[int],
        feature_names: Optional[list[str]] = None,
        version: str = DEFAULT_FEATURE_VERSION,
    ) -> list[FeatureQueryResult]:
        """
        查询特定的特征字段.

        Args:
            match_ids: 比赛ID列表
            feature_names: 需要查询的特征名列表，None表示查询所有
            version: 特征版本

        Returns:
            查询结果列表
        """
        await self._ensure_initialized()

        if not match_ids:
            return []

        if len(match_ids) > self.max_batch_size:
            raise FeatureValidationError(
                f"Batch size {len(match_ids)} exceeds maximum {self.max_batch_size}"
            )

        try:
            async with get_db_session() as session:
                if feature_names:
                    # 查询特定特征字段
                    placeholders = ",".join(["%s"] * len(match_ids))

                    query = f"""
                        SELECT match_id, features, version, updated_at
                        FROM feature_store
                        WHERE match_id IN ({placeholders}) AND version = %s
                    """

                    result = await session.execute(query, match_ids + [version])
                    rows = result.fetchall()

                    results = []
                    for row in rows:
                        features = (
                            json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        )
                        # 只返回请求的特征
                        filtered_features = {
                            k: v for k, v in features.items() if k in feature_names
                        }

                        results.append(
                            FeatureQueryResult(
                                match_id=row[0],
                                features=filtered_features,
                                version=row[2],
                                timestamp=row[3],
                                is_complete=len(filtered_features)
                                == len(feature_names),
                            )
                        )

                    return results
                else:
                    # 查询所有特征
                    batch_data = await self.load_batch(match_ids, version)
                    return [
                        FeatureQueryResult(
                            match_id=match_id,
                            features=data["features"],
                            version=data["version"],
                            timestamp=data["updated_at"],
                            is_complete=True,
                        )
                        for match_id, data in batch_data.items()
                    ]

        except Exception as e:
            logger.error(f"Failed to query features: {e}")
            raise StorageError(f"Query operation failed: {e}") from e

    async def latest_feature_timestamp(
        self, version: str = DEFAULT_FEATURE_VERSION
    ) -> Optional[datetime]:
        """
        获取最新特征的时间戳.

        Args:
            version: 特征版本

        Returns:
            最新特征的创建时间，如果没有特征则返回 None
        """
        await self._ensure_initialized()
        self._validate_version(version)

        try:
            async with get_db_session() as session:
                query = """
                    SELECT MAX(created_at) as latest_timestamp
                    FROM feature_store
                    WHERE version = %s
                """

                result = await session.execute(query, (version,))
                row = result.fetchone()

                return row[0] if row and row[0] else None

        except Exception as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            raise StorageError(f"Timestamp query failed: {e}") from e

    async def stats(self) -> FeatureStats:
        """
        获取特征存储的统计信息.

        Returns:
            包含各种统计指标的字典
        """
        await self._ensure_initialized()

        try:
            async with get_db_session() as session:
                query = """
                    SELECT
                        COUNT(DISTINCT match_id) as total_matches,
                        COUNT(*) as total_features,
                        COUNT(DISTINCT version) as feature_versions,
                        MAX(created_at) as latest_timestamp,
                        pg_size_pretty(pg_total_relation_size('feature_store')) as storage_size
                    FROM feature_store
                """

                result = await session.execute(query)
                row = result.fetchone()

                return FeatureStats(
                    total_features=row[1] if row else 0,
                    total_matches=row[0] if row else 0,
                    feature_versions=list(row[2].split(",")) if row and row[2] else [],
                    latest_timestamp=row[3] if row and row[3] else None,
                    storage_size_mb=(
                        self._parse_storage_size(row[4]) if row and row[4] else None
                    ),
                )

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise StorageError(f"Stats query failed: {e}") from e

    async def delete_features(
        self, match_id: int, version: Optional[str] = None
    ) -> bool:
        """
        删除指定的特征数据.

        Args:
            match_id: 比赛ID
            version: 特征版本号，None表示删除所有版本

        Returns:
            删除是否成功
        """
        await self._ensure_initialized()
        self._validate_match_id(match_id)

        try:
            async with get_db_session() as session:
                if version:
                    # 删除特定版本
                    query = (
                        "DELETE FROM feature_store WHERE match_id = %s AND version = %s"
                    )
                    await session.execute(query, (match_id, version))
                else:
                    # 删除所有版本
                    query = "DELETE FROM feature_store WHERE match_id = %s"
                    await session.execute(query, (match_id,))

                await session.commit()

                if self.enable_logging:
                    logger.info(
                        f"Deleted features for match {match_id}, version: {version or 'all'}"
                    )

                return True

        except Exception as e:
            logger.error(f"Failed to delete features for match {match_id}: {e}")
            raise StorageError(f"Delete operation failed: {e}") from e

    async def list_feature_versions(self, match_id: int) -> list[str]:
        """
        列出指定比赛的所有特征版本.

        Args:
            match_id: 比赛ID

        Returns:
            版本号列表
        """
        await self._ensure_initialized()
        self._validate_match_id(match_id)

        try:
            async with get_db_session() as session:
                query = """
                    SELECT DISTINCT version
                    FROM feature_store
                    WHERE match_id = %s
                    ORDER BY version
                """

                result = await session.execute(query, (match_id,))
                rows = result.fetchall()

                return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to list versions for match {match_id}: {e}")
            raise StorageError(f"Version listing failed: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """
        健康检查接口.

        Returns:
            健康状态信息
        """
        try:
            stats = await self.stats()
            latest_timestamp = await self.latest_feature_timestamp()

            # 计算数据新鲜度（秒）
            data_age = None
            if latest_timestamp:
                data_age = (
                    datetime.now(timezone.utc) - latest_timestamp
                ).total_seconds()

            return {
                "status": "healthy" if self._initialized else "uninitialized",
                "initialized": self._initialized,
                "total_matches": stats["total_matches"],
                "total_features": stats["total_features"],
                "latest_timestamp": (
                    latest_timestamp.isoformat() if latest_timestamp else None
                ),
                "data_age_seconds": data_age,
                "storage_size": stats["storage_size_mb"],
                "max_batch_size": self.max_batch_size,
                "retry_attempts": self.retry_attempts,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "initialized": self._initialized,
            }

    async def close(self) -> None:
        """关闭连接，清理资源."""
        self._initialized = False
        if self.enable_logging:
            logger.info("FeatureStore closed")

    # 私有辅助方法

    async def _ensure_initialized(self) -> None:
        """确保FeatureStore已初始化."""
        if not self._initialized:
            await self.initialize()

    def _validate_match_id(self, match_id: int) -> None:
        """验证match_id的有效性."""
        if not isinstance(match_id, int) or match_id <= 0:
            raise FeatureValidationError(
                f"Invalid match_id: {match_id}. Must be a positive integer."
            )

    def _validate_features(self, features: dict[str, Any]) -> None:
        """验证features字典的有效性."""
        if not isinstance(features, dict):
            raise FeatureValidationError(
                f"Features must be a dictionary, got {type(features)}"
            )

        if not features:
            raise FeatureValidationError("Features dictionary cannot be empty")

        # 验证特征名的有效性
        for key in features.keys():
            if not isinstance(key, str) or not key.strip():
                raise FeatureValidationError(
                    f"Invalid feature name: {key}. Must be a non-empty string."
                )

    def _validate_version(self, version: str) -> None:
        """验证version的有效性."""
        if not isinstance(version, str) or not version.strip():
            raise FeatureValidationError(
                f"Invalid version: {version}. Must be a non-empty string."
            )

    def _parse_storage_size(self, size_str: Optional[str]) -> Optional[float]:
        """解析PostgreSQL的存储大小字符串为MB."""
        if not size_str:
            return None

        try:
            size_str = size_str.strip().upper()
            if size_str.endswith("KB"):
                return float(size_str[:-2]) / 1024
            elif size_str.endswith("MB"):
                return float(size_str[:-2])
            elif size_str.endswith("GB"):
                return float(size_str[:-2]) * 1024
            else:
                return float(size_str)
        except (ValueError, AttributeError):
            return None


# 创建全局实例（惰性初始化）
_global_feature_store: Optional[FootballFeatureStore] = None


async def get_feature_store() -> FootballFeatureStore:
    """
    获取全局FeatureStore实例（单例模式）.

    Returns:
        FootballFeatureStore 实例
    """
    global _global_feature_store
    if _global_feature_store is None:
        _global_feature_store = FootballFeatureStore()
        await _global_feature_store.initialize()
    return _global_feature_store


def reset_feature_store() -> None:
    """
    重置全局FeatureStore实例（主要用于测试）.
    """
    global _global_feature_store
    _global_feature_store = None


# 为了向后兼容，保留旧的导入别名
FootballFeatureStoreClass = FootballFeatureStore
