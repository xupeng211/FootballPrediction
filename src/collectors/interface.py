"""
统一采集器接口协议定义
Base Collector Protocol Definition

该模块定义了所有数据采集器必须实现的标准接口，确保：
1. 统一的方法签名和返回类型
2. 标准化的错误处理约定
3. 可插拔的采集器架构
4. 类型安全的异步操作

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class BaseCollectorProtocol(Protocol):
    """
    基础采集器协议接口

    所有数据采集器都必须实现此协议，确保统一的行为契约。
    使用 Python 的 Structural Subtyping (Protocol) 而非继承，
    提供更大的灵活性和 Pythonic 的实现方式。

    核心设计原则:
    1. 所有网络IO操作必须是异步的
    2. 统一的错误处理和重试策略
    3. 标准化的数据格式
    4. 资源管理和清理机制
    """

    @abstractmethod
    async def collect_fixtures(
        self, league_id: int, season_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        采集联赛赛程数据

        Args:
            league_id: 联赛ID (如: 47 for Premier League)
            season_id: 赛季ID (可选，如: "2024-2025")

        Returns:
            List[Dict[str, Any]]: 赛程数据列表，每个字典包含:
                - match_id: str - 比赛唯一标识
                - home_team: str - 主队名称
                - away_team: str - 客队名称
                - kickoff_time: str - 开赛时间 (ISO 8601)
                - venue: Optional[str] - 场地信息
                - status: str - 比赛状态

        Raises:
            CollectorError: 采集过程中的通用错误
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            NetworkError: 网络连接问题
        """
        ...

    @abstractmethod
    async def collect_match_details(self, match_id: str) -> dict[str, Any]:
        """
        采集比赛详情数据

        Args:
            match_id: 比赛唯一标识

        Returns:
            Dict[str, Any]: 比赛详情数据，包含:
                - match_id: str - 比赛ID
                - home_score: Optional[int] - 主队得分
                - away_score: Optional[int] - 客队得分
                - home_xg: Optional[float] - 主队期望进球数
                - away_xg: Optional[float] - 客队期望进球数
                - shots: Dict[str, int] - 射门数据
                - possession: Dict[str, float] - 控球率
                - events: List[Dict] - 比赛事件列表
                - lineups: Dict[str, List] - 阵容信息
                - odds: Optional[Dict] - 赔率数据

        Raises:
            CollectorError: 采集过程中的通用错误
            DataNotFoundError: 比赛数据不存在
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            NetworkError: 网络连接问题
        """
        ...

    @abstractmethod
    async def collect_team_info(self, team_id: str) -> dict[str, Any]:
        """
        采集球队信息

        Args:
            team_id: 球队唯一标识

        Returns:
            Dict[str, Any]: 球队信息，包含:
                - team_id: str - 球队ID
                - name: str - 球队名称
                - country: str - 国家
                - founded: Optional[int] - 成立年份
                - stadium: Optional[str] - 主场
                - logo_url: Optional[str] - 球队徽标URL

        Raises:
            CollectorError: 采集过程中的通用错误
            DataNotFoundError: 球队数据不存在
        """
        ...

    @abstractmethod
    async def check_health(self) -> dict[str, Any]:
        """
        检查采集器健康状态

        此方法用于：
        1. 代理池健康检查
        2. API连通性验证
        3. 认证状态检查
        4. 速率限制状态查询

        Returns:
            Dict[str, Any]: 健康状态信息，包含:
                - status: str - "healthy" | "degraded" | "unhealthy"
                - response_time_ms: float - 响应时间(毫秒)
                - last_check: str - 最后检查时间
                - error_count: int - 错误计数
                - details: Dict[str, Any] - 额外详情

        Example:
            >>> health = await collector.check_health()
            >>> if health["status"] == "healthy":
            ...     print("采集器运行正常")
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """
        清理资源并关闭采集器

        此方法负责：
        1. 关闭HTTP客户端连接
        2. 清理代理池资源
        3. 保存缓存数据
        4. 取消进行中的任务

        注意:
        - 必须在程序退出前调用
        - 支持多次调用而无副作用
        - 应该优雅地处理清理失败
        """
        ...


@runtime_checkable
class ExtendedCollectorProtocol(BaseCollectorProtocol, Protocol):
    """
    扩展采集器协议接口

    为高级采集器提供额外的功能，如：
    - 批量操作支持
    - 流式数据处理
    - 自定义配置管理
    """

    @abstractmethod
    async def collect_batch_fixtures(
        self, league_ids: list[int], season_id: Optional[str] = None
    ) -> dict[int, list[dict[str, Any]]]:
        """
        批量采集多个联赛的赛程数据

        Args:
            league_ids: 联赛ID列表
            season_id: 赛季ID

        Returns:
            Dict[int, List[Dict]]: 按联赛ID分组的赛程数据
        """
        ...

    @abstractmethod
    async def stream_fixtures(self, league_id: int, season_id: Optional[str] = None):
        """
        流式采集赛程数据

        Args:
            league_id: 联赛ID
            season_id: 赛季ID

        Yields:
            Dict[str, Any]: 单个赛程数据
        """
        ...


# 采集器异常类型定义
class CollectorError(Exception):
    """采集器基础异常类"""

    pass


class AuthenticationError(CollectorError):
    """认证失败异常"""

    pass


class RateLimitError(CollectorError):
    """速率限制异常"""

    pass


class NetworkError(CollectorError):
    """网络连接异常"""

    pass


class DataNotFoundError(CollectorError):
    """数据未找到异常"""

    pass


class ConfigurationError(CollectorError):
    """配置错误异常"""

    pass


# 类型别名，提高代码可读性
FixtureData = dict[str, Any]
MatchDetailData = dict[str, Any]
TeamInfoData = dict[str, Any]
HealthStatus = dict[str, Any]

# 导出的公共接口
__all__ = [
    "BaseCollectorProtocol",
    "ExtendedCollectorProtocol",
    "CollectorError",
    "AuthenticationError",
    "RateLimitError",
    "NetworkError",
    "DataNotFoundError",
    "ConfigurationError",
    "FixtureData",
    "MatchDetailData",
    "TeamInfoData",
    "HealthStatus",
]
