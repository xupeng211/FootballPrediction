"""
FeatureStore 标准接口定义.

符合 ML 工程最佳实践的协议定义，支持异步操作和类型安全。
这个文件定义了 FeatureStore 必须实现的所有接口，但不包含业务逻辑。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable, TypedDict
from uuid import UUID


class FeatureData(TypedDict, total=False):
    """特征数据结构定义."""

    match_id: int
    features: dict[str, Any]
    version: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict[str, Any]]


class FeatureStats(TypedDict):
    """特征统计信息结构."""

    total_features: int
    total_matches: int
    latest_timestamp: Optional[datetime]
    storage_size_mb: Optional[float]
    feature_versions: list[str]


class FeatureQueryResult(TypedDict):
    """特征查询结果."""

    match_id: int
    features: dict[str, Any]
    version: str
    timestamp: datetime
    is_complete: bool


@runtime_checkable
class FeatureStoreProtocol(Protocol):
    """
    FeatureStore 标准协议定义.

    这个协议定义了所有 FeatureStore 实现必须遵循的接口。
    所有方法都是异步的，以支持高并发的特征访问场景。
    """

    async def save_features(
        self,
        match_id: int,
        features: dict[str, Any],
        version: str = "latest",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        保存特征数据到存储.

        Args:
            match_id: 比赛ID，作为特征的主键
            features: 特征数据字典，key为特征名，value为特征值
            version: 特征版本号，默认为 "latest"
            metadata: 可选的元数据信息

        Raises:
            ValueError: 当 match_id 或 features 无效时
            StorageError: 当存储操作失败时

        Example:
            >>> store = FeatureStore()
            >>> features = {"xg": 1.5, "possessions": 65.2}
            >>> await store.save_features(12345, features)
        """
        ...

    async def load_features(
        self, match_id: int, version: str = "latest"
    ) -> Optional[FeatureData]:
        """
        加载单个比赛的特征数据.

        Args:
            match_id: 比赛ID
            version: 特征版本号，默认为 "latest"

        Returns:
            FeatureData 对象，如果不存在则返回 None

        Example:
            >>> data = await store.load_features(12345)
            >>> if data:
            ...     print(data["features"]["xg"])
        """
        ...

    async def load_batch(
        self, match_ids: list[int], version: str = "latest"
    ) -> dict[int, FeatureData]:
        """
        批量加载多个比赛的特征数据.

        Args:
            match_ids: 比赛ID列表
            version: 特征版本号，默认为 "latest"

        Returns:
            字典，key为match_id，value为对应的FeatureData

        Example:
            >>> match_ids = [12345, 12346, 12347]
            >>> batch_data = await store.load_batch(match_ids)
            >>> print(f"Loaded {len(batch_data)} feature sets")
        """
        ...

    async def query_features(
        self,
        match_ids: list[int],
        feature_names: Optional[list[str]] = None,
        version: str = "latest",
    ) -> list[FeatureQueryResult]:
        """
        查询特定的特征字段.

        Args:
            match_ids: 比赛ID列表
            feature_names: 需要查询的特征名列表，None表示查询所有
            version: 特征版本号

        Returns:
            查询结果列表

        Example:
            >>> results = await store.query_features(
            ...     [12345, 12346],
            ...     feature_names=["xg", "xga"]
            ... )
        """
        ...

    async def latest_feature_timestamp(
        self, version: str = "latest"
    ) -> Optional[datetime]:
        """
        获取最新特征的时间戳.

        Args:
            version: 特征版本号

        Returns:
            最新特征的创建时间，如果没有特征则返回 None
        """
        ...

    async def stats(self) -> FeatureStats:
        """
        获取特征存储的统计信息.

        Returns:
            包含各种统计指标的字典

        Example:
            >>> stats = await store.stats()
            >>> print(f"Total features: {stats['total_features']}")
        """
        ...

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
        ...

    async def list_feature_versions(self, match_id: int) -> list[str]:
        """
        列出指定比赛的所有特征版本.

        Args:
            match_id: 比赛ID

        Returns:
            版本号列表
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """
        健康检查接口.

        Returns:
            健康状态信息，包含连接状态、延迟等
        """
        ...

    async def initialize(self) -> None:
        """
        初始化存储后端.

        创建必要的表结构、索引等。
        """
        ...

    async def close(self) -> None:
        """
        关闭连接，清理资源.
        """
        ...


# 常用异常定义
class FeatureStoreError(Exception):
    """FeatureStore 基础异常类."""

    pass


class FeatureNotFoundError(FeatureStoreError):
    """特征未找到异常."""

    pass


class FeatureValidationError(FeatureStoreError):
    """特征验证失败异常."""

    pass


class StorageError(FeatureStoreError):
    """存储操作失败异常."""

    pass


class ConfigurationError(FeatureStoreError):
    """配置错误异常."""

    pass


# 常量定义
DEFAULT_FEATURE_VERSION = "latest"
SUPPORTED_FEATURE_VERSIONS = ["latest", "v1.0", "v2.0"]
MAX_BATCH_SIZE = 1000
FEATURE_VALIDATION_TIMEOUT = 30.0  # seconds
