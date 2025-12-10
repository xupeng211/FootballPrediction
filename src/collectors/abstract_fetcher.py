"""
抽象数据源获取器接口
Abstract Data Source Fetcher Interface

该模块定义了通用的、与具体数据源无关的抽象数据源接口，
为 Service 层提供统一的数据获取契约。

核心设计原则:
1. 数据源无关性 - 不依赖任何具体的数据源实现
2. 通用性 - 支持多种类型的资源获取
3. 可扩展性 - 便于添加新的数据源适配器
4. 类型安全 - 提供完整的类型注解

作者: Data Architecture Team
创建时间: 2025-12-07
版本: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, , , Optional, Union
from enum import Enum

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """资源类型枚举"""
    FIXTURES = "fixtures"          # 赛程数据
    MATCH_DETAILS = "match_details"  # 比赛详情
    TEAM_INFO = "team_info"        # 球队信息
    ODDS = "odds"                 # 赔率数据
    LEAGUE_INFO = "league_info"   # 联赛信息
    PLAYER_STATS = "player_stats" # 球员统计
    RAW_DATA = "raw_data"         # 原始数据


@dataclass
class FetchMetadata:
    """获取操作元数据"""
    source: str                           # 数据源标识
    fetched_at: datetime                  # 获取时间
    resource_type: ResourceType           # 资源类型
    resource_id: str                      # 资源ID
    processing_time_ms: Optional[float]   # 处理时间(毫秒)
    success: bool                         # 是否成功
    error_message: Optional[str]          # 错误信息(如有)
    record_count: Optional[int]           # 记录数量


class OddsData(BaseModel):
    """通用赔率数据模型

    该模型定义了赔率数据的标准化格式，作为所有数据源适配器的统一输出标准。
    """

    # 基础信息
    match_id: str = Field(..., description="比赛唯一标识")
    source: str = Field(..., description="数据源标识")
    timestamp: datetime = Field(default_factory=datetime.now, description="数据时间戳")

    # 赔率信息
    home_win: Optional[float] = Field(None, description="主胜赔率")
    draw: Optional[float] = Field(None, description="平局赔率")
    away_win: Optional[float] = Field(None, description="客胜赔率")

    # 亚洲盘口
    asian_handicap_home: Optional[float] = Field(None, description="亚洲盘口主队赔率")
    asian_handicap_away: Optional[float] = Field(None, description="亚洲盘口客队赔率")
    asian_handicap_line: Optional[float] = Field(None, description="亚洲盘口让球数")

    # 大小球
    over_under_line: Optional[float] = Field(None, description="大小球盘口")
    over_odds: Optional[float] = Field(None, description="大球赔率")
    under_odds: Optional[float] = Field(None, description="小球赔率")

    # 扩展信息
    bookmaker: Optional[str] = Field(None, description="博彩公司名称")
    market_type: Optional[str] = Field(None, description="市场类型")
    liquidity: Optional[float] = Field(None, description="市场流动性")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")

    # 原始数据(保留完整数据源信息)
    raw_data: Optional[dict[str, Any]] = Field(None, description="原始数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AbstractFetcher(ABC):
    """
    抽象数据源获取器基类

    定义了所有数据源适配器必须实现的标准接口，确保：
    1. 统一的方法签名和返回类型
    2. 标准化的错误处理
    3. 一致的数据格式
    4. 资源管理约定
    """

    def __init__(self, source_name: str, config: Optional[dict[str, Any]] = None):
        """
        初始化获取器

        Args:
            source_name: 数据源名称标识
            config: 可选的配置参数
        """
        self.source_name = source_name
        self.config = config or {}
        self._metadata: dict[str, FetchMetadata] = {}

    @abstractmethod
    async def fetch_data(
        self,
        resource_id: str,
        resource_type: Optional[ResourceType] = None,
        **kwargs
    ) -> list[dict[str, Any]]:
        """
        获取数据的核心抽象方法

        Args:
            resource_id: 资源标识符 (如: league_id, match_id, team_id)
            resource_type: 资源类型 (可选)
            **kwargs: 其他查询参数

        Returns:
            list[dict[str, Any]]: 返回数据记录列表

        Raises:
            NotImplementedError: 子类必须实现此方法
            ConnectionError: 网络连接错误
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            DataNotFoundError: 数据未找到
        """
        pass

    @abstractmethod
    async def fetch_odds(
        self,
        match_id: str,
        **kwargs
    ) -> list[OddsData]:
        """
        获取赔率数据的专用方法

        Args:
            match_id: 比赛ID
            **kwargs: 其他查询参数

        Returns:
            list[OddsData]: 赔率数据列表
        """
        pass

    async def fetch_single(
        self,
        resource_id: str,
        resource_type: Optional[ResourceType] = None,
        **kwargs
    ) -> Optional[dict[str, Any]]:
        """
        获取单条记录的便捷方法

        Args:
            resource_id: 资源标识符
            resource_type: 资源类型
            **kwargs: 其他查询参数

        Returns:
            Optional[dict[str, Any]]: 单条记录或None
        """
        results = await self.fetch_data(resource_id, resource_type, **kwargs)
        return results[0] if results else None

    async def validate_connection(self) -> bool:
        """
        验证数据源连接是否正常

        Returns:
            bool: 连接是否正常
        """
        try:
            # 默认实现: 尝试获取一个简单的资源
            await self.fetch_data("health_check")
            return True
        except Exception:
            return False

    def get_metadata(self, resource_id: str) -> Optional[FetchMetadata]:
        """
        获取指定资源的元数据

        Args:
            resource_id: 资源ID

        Returns:
            Optional[FetchMetadata]: 元数据信息
        """
        return self._metadata.get(resource_id)

    def get_source_name(self) -> str:
        """获取数据源名称"""
        return self.source_name

    def get_config(self) -> dict[str, Any]:
        """获取配置信息"""
        return self.config.copy()

    async def close(self) -> None:
        """
        清理资源

        默认实现为空，子类可重写以实现资源清理
        """
        pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()


class FetcherFactory:
    """
    获取器工厂类

    提供统一的获取器创建和管理接口
    """

    _fetchers: dict[str, type[AbstractFetcher]] = {}

    @classmethod
    def register(cls, name: str, fetcher_class: type[AbstractFetcher]) -> None:
        """
        注册获取器类

        Args:
            name: 获取器名称
            fetcher_class: 获取器类
        """
        if not issubclass(fetcher_class, AbstractFetcher):
            raise ValueError(f"{fetcher_class} must inherit from AbstractFetcher")

        cls._fetchers[name] = fetcher_class

    @classmethod
    def create(cls, name: str, config: Optional[dict[str, Any]] = None) -> AbstractFetcher:
        """
        创建获取器实例

        Args:
            name: 获取器名称
            config: 配置参数

        Returns:
            AbstractFetcher: 获取器实例
        """
        if name not in cls._fetchers:
            raise ValueError(f"Unknown fetcher: {name}. Available: {list(cls._fetchers.keys())}")

        fetcher_class = cls._fetchers[name]
        return fetcher_class(source_name=name, config=config or {})

    @classmethod
    def list_available(cls) -> list[str]:
        """获取所有可用的获取器名称"""
        return list(cls._fetchers.keys())


# 异常类型定义
class FetcherError(Exception):
    """获取器基础异常"""
    pass


class ConnectionError(FetcherError):
    """连接错误"""
    pass


class AuthenticationError(FetcherError):
    """认证错误"""
    pass


class RateLimitError(FetcherError):
    """速率限制错误"""
    pass


class DataNotFoundError(FetcherError):
    """数据未找到错误"""
    pass


class ConfigurationError(FetcherError):
    """配置错误"""
    pass


# 导出的公共接口
__all__ = [
    "AbstractFetcher",
    "OddsData",
    "FetchMetadata",
    "ResourceType",
    "FetcherFactory",
    "FetcherError",
    "ConnectionError",
    "AuthenticationError",
    "RateLimitError",
    "DataNotFoundError",
    "ConfigurationError",
]
