#!/usr/bin/env python3
"""
Base Harvest Engine - V1.0.0 [Genesis.UnifiedEngine]
====================================================================

基础引擎抽象类 - 定义所有收割引擎必须实现的统一接口。

Core Features:
- 统一的 HarvestResult 数据结构
- 抽象方法强制子类实现核心功能
- NetworkShield 集成接口
- 标准化错误处理
- 引擎统计信息收集

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class HarvestStatus(Enum):
    """收割状态枚举"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PROXY_ERROR = "proxy_error"
    DATA_ERROR = "data_error"


@dataclass
class HarvestResult:
    """
    统一的收割结果数据结构

    所有引擎必须返回此格式的结果, 确保:
    - 标准化的成功/失败标识
    - 一致的错误信息格式
    - 完整的元数据追踪
    - 代理使用信息(用于 NetworkShield 状态更新)

    Attributes:
        source: 数据源标识 (fotmob, oddsportal, etc.)
        match_id: 比赛 ID
        status: 收割状态 (HarvestStatus 枚举)
        success: 是否成功(向后兼容)
        data: 采集的数据
        errors: 错误信息列表
        latency_ms: 请求延迟(毫秒)
        proxy_port: 使用的代理端口
        fetched_at: 采集时间戳
        retry_count: 重试次数
        metadata: 额外元数据
    """
    source: str
    match_id: str
    status: HarvestStatus
    success: bool
    data: dict[str, Any] | None
    errors: list[str] = field(default_factory=list)
    latency_ms: int = 0
    proxy_port: int | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "source": self.source,
            "match_id": self.match_id,
            "status": self.status.value,
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "latency_ms": self.latency_ms,
            "proxy_port": self.proxy_port,
            "fetched_at": self.fetched_at,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    def is_complete_success(self) -> bool:
        """检查是否完全成功"""
        return self.status == HarvestStatus.SUCCESS

    def is_partial_success(self) -> bool:
        """检查是否部分成功"""
        return self.status == HarvestStatus.PARTIAL

    def is_proxy_related_failure(self) -> bool:
        """检查是否是代理相关的失败"""
        return self.status in {
            HarvestStatus.PROXY_ERROR,
            HarvestStatus.TIMEOUT,
            HarvestStatus.RATE_LIMITED
        }


@dataclass
class EngineConfig:
    """
    引擎配置基类

    Attributes:
        name: 引擎名称
        version: 引擎版本
        source: 数据源标识
        enabled: 是否启用
        max_retries: 最大重试次数
        timeout_seconds: 请求超时时间
        rate_limit_delay: 速率限制延迟（毫秒）
        enable_network_shield: 是否启用 NetworkShield
        session_timeout_minutes: 会话超时时间（分钟）
    """
    name: str = "BaseEngine"
    version: str = "1.0.0"
    source: str = "unknown"
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    rate_limit_delay: int = 2000  # 2 seconds
    enable_network_shield: bool = True
    session_timeout_minutes: int = 30


@dataclass
class EngineStatistics:
    """
    引擎统计信息

    Attributes:
        total_harvests: 总收割次数
        successful_harvests: 成功次数
        failed_harvests: 失败次数
        partial_harvests: 部分成功次数
        total_data_size: 总数据大小（字节）
        avg_latency_ms: 平均延迟（毫秒）
        last_harvest_time: 最后收割时间
        last_error: 最后错误信息
    """
    total_harvests: int = 0
    successful_harvests: int = 0
    failed_harvests: int = 0
    partial_harvests: int = 0
    total_data_size: int = 0
    avg_latency_ms: float = 0.0
    last_harvest_time: str | None = None
    last_error: str | None = None

    def update(self, result: HarvestResult) -> None:
        """更新统计信息"""
        self.total_harvests += 1
        self.last_harvest_time = result.fetched_at

        if result.success:
            self.successful_harvests += 1
        elif result.status == HarvestStatus.PARTIAL:
            self.partial_harvests += 1
        else:
            self.failed_harvests += 1
            if result.errors:
                self.last_error = result.errors[-1]

        # 更新平均延迟
        if self.total_harvests == 1:
            self.avg_latency_ms = float(result.latency_ms)
        else:
            self.avg_latency_ms = (
                (self.avg_latency_ms * (self.total_harvests - 1) + result.latency_ms)
                / self.total_harvests
            )

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_harvests == 0:
            return 0.0
        return self.successful_harvests / self.total_harvests

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_harvests": self.total_harvests,
            "successful_harvests": self.successful_harvests,
            "failed_harvests": self.failed_harvests,
            "partial_harvests": self.partial_harvests,
            "total_data_size": self.total_data_size,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "success_rate": round(self.get_success_rate(), 4),
            "last_harvest_time": self.last_harvest_time,
            "last_error": self.last_error
        }


class HarvestError(Exception):
    """
    收割异常基类

    用于所有收割引擎的异常处理，提供:
    - 标准化的错误信息
    - 错误分类
    - 上下文信息
    """

    def __init__(
        self,
        message: str,
        source: str = "unknown",
        match_id: str | None = None,
        proxy_port: int | None = None,
        original_error: Exception | None = None
    ):
        self.message = message
        self.source = source
        self.match_id = match_id
        self.proxy_port = proxy_port
        self.original_error = original_error
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "source": self.source,
            "match_id": self.match_id,
            "proxy_port": self.proxy_port,
            "original_error": str(self.original_error) if self.original_error else None
        }


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================


class BaseHarvestEngine(ABC):
    """
    基础收割引擎抽象类

    所有数据收割引擎必须继承此类并实现抽象方法。

    核心功能:
    1. 统一的初始化流程 (initialize)
    2. 强制的 NetworkShield 认证
    3. 标准化的单场收割 (harvest_match)
    4. 批量收割支持 (harvest_batch)
    5. 代理状态上报 (_report_success / _report_failure)
    6. 会话管理 (_get_proxy_for_session / _release_session)

    使用示例:
        >>> class MyEngine(BaseHarvestEngine):
        ...     async def initialize(self):
        ...         await super().initialize()
        ...         # 自定义初始化
        ...
        ...     async def harvest_match(self, match_id: str) -> HarvestResult:
        ...         # 1. 获取代理
        ...         proxy = await self._get_proxy_for_session(match_id)
        ...
        ...         # 2. 执行收割
        ...         try:
        ...             data = await self._fetch_data(match_id, proxy)
        ...             await self._report_success(proxy['port'], latency_ms=100)
        ...             return HarvestResult(...)
        ...         except Exception as e:
        ...             await self._report_failure(proxy['port'], str(e))
        ...             raise
    """

    def __init__(self, config: EngineConfig):
        """
        初始化引擎

        Args:
            config: 引擎配置
        """
        self.config = config
        self.statistics = EngineStatistics()
        self._network_guardian = None
        self._initialized = False
        self._sessions: Dict[str, str] = {}  # match_id -> session_id mapping

        # 初始化日志
        self.logger = logging.getLogger(f"HarvestEngine.{config.name}")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化引擎

        子类必须实现此方法，并:
        1. 调用 await super().initialize() 以启用 NetworkShield
        2. 执行引擎特定的初始化逻辑
        3. 验证连接和配置

        Raises:
            HarvestError: 初始化失败
        """
        # NetworkShield 初始化
        if self.config.enable_network_shield:
            from ..shared.network_guardian import NetworkGuardian

            self._network_guardian = NetworkGuardian(
                proxy_host="172.25.16.1",
                log_level="info"
            )

            try:
                await self._network_guardian.initialize()
                status = self._network_guardian.get_status()
                self.logger.info(
                    f"[{self.config.name}] NetworkShield initialized: "
                    f"{status.get('nodes', {}).get('active', 0)}/"
                    f"{status.get('nodes', {}).get('total', 0)} nodes available"
                )
            except Exception as e:
                raise HarvestError(
                    f"Failed to initialize NetworkShield: {e}",
                    source=self.config.source,
                    original_error=e
                )

        self._initialized = True
        self.logger.info(f"[{self.config.name}] Engine V{self.config.version} initialized")

    @abstractmethod
    async def shutdown(self) -> None:
        """
        关闭引擎

        子类必须实现此方法，并:
        1. 清理所有活跃会话
        2. 关闭网络连接
        3. 释放资源
        """
        # 释放所有会话
        if self._network_guardian:
            for match_id, session_id in self._sessions.items():
                self._network_guardian.release_session(session_id)
            self._sessions.clear()

        self._initialized = False
        self.logger.info(f"[{self.config.name}] Engine shutdown complete")

    # ========================================================================
    # CORE HARVEST METHODS (Must be implemented by subclasses)
    # ========================================================================

    @abstractmethod
    async def harvest_match(self, match_id: str) -> HarvestResult:
        """
        收割单场比赛数据

        子类必须实现此方法，返回标准化的 HarvestResult。

        Args:
            match_id: 比赛 ID

        Returns:
            HarvestResult: 收割结果

        Raises:
            HarvestError: 收割失败
        """
        pass

    @abstractmethod
    async def harvest_batch(self, match_ids: List[str]) -> List[HarvestResult]:
        """
        批量收割比赛数据

        默认实现为并发调用 harvest_match，子类可重写以优化批量处理。

        Args:
            match_ids: 比赛 ID 列表

        Returns:
            List[HarvestResult]: 收割结果列表
        """
        # 并发收割
        tasks = [self.harvest_match(mid) for mid in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(HarvestResult(
                    source=self.config.source,
                    match_id=match_ids[i],
                    status=HarvestStatus.FAILED,
                    success=False,
                    data=None,
                    errors=[str(result)]
                ))
            else:
                processed_results.append(result)

        return processed_results

    # ========================================================================
    # NETWORK SHIELD INTEGRATION (Protected methods)
    # ========================================================================

    async def _get_proxy_for_session(
        self,
        match_id: str,
        force_new: bool = False
    ) -> Dict[str, Any]:
        """
        通过 NetworkShield 获取会话绑定代理

        Args:
            match_id: 比赛 ID（用于会话绑定）
            force_new: 是否强制创建新会话

        Returns:
            Dict: { 'host': str, 'port': int, 'url': str, 'session_id': str }

        Raises:
            RuntimeError: NetworkShield 未初始化或无可用代理
        """
        if not self._network_guardian:
            raise RuntimeError(
                f"[{self.config.name}] NetworkShield not initialized. "
                "Set enable_network_shield=True in config."
            )

        # 检查是否已有会话绑定
        session_id = self._sessions.get(match_id)

        if session_id and not force_new:
            # 尝试复用现有会话
            proxy = await self._network_guardian.get_proxy(session_id)
            if proxy:
                self.logger.debug(
                    f"[{self.config.name}] Reusing session {session_id} for match {match_id}"
                )
                return {
                    "host": "172.25.16.1",
                    "port": proxy.port,
                    "url": proxy.url,
                    "session_id": session_id
                }

        # 创建新会话
        session_id = f"{self.config.source.upper()}-{match_id}"
        proxy = await self._network_guardian.get_next_healthy_proxy(session_id)

        if not proxy:
            raise RuntimeError(
                f"[{self.config.name}] No available proxies from NetworkShield"
            )

        # 记录会话绑定
        self._sessions[match_id] = session_id

        self.logger.debug(
            f"[{self.config.name}] Assigned proxy port {proxy.port} to match {match_id} "
            f"(session: {session_id})"
        )

        return {
            "host": "172.25.16.1",
            "port": proxy.port,
            "url": proxy.url,
            "session_id": session_id
        }

    async def _release_match_session(self, match_id: str) -> None:
        """
        释放比赛会话

        Args:
            match_id: 比赛 ID
        """
        session_id = self._sessions.get(match_id)
        if session_id and self._network_guardian:
            self._network_guardian.release_session(session_id)
            del self._sessions[match_id]
            self.logger.debug(f"[{self.config.name}] Released session {session_id}")

    async def _report_success(
        self,
        port: int,
        latency_ms: int = 0
    ) -> None:
        """
        上报代理成功到 NetworkShield

        Args:
            port: 代理端口
            latency_ms: 请求延迟（毫秒）
        """
        if self._network_guardian:
            await self._network_guardian.mark_proxy_success(port, latency_ms)
            self.logger.debug(f"[{self.config.name}] Reported success for port {port}")

    async def _report_failure(
        self,
        port: int,
        reason: str = "Unknown"
    ) -> None:
        """
        上报代理失败到 NetworkShield

        这对于跨语言状态同步至关重要！
        Python 端的失败会被记录到 active_registry.json，
        Node.js QuantHarvester 将能即时感知并避免使用失效 IP。

        Args:
            port: 代理端口
            reason: 失败原因
        """
        if self._network_guardian:
            await self._network_guardian.mark_proxy_failed(port, reason)
            self.logger.warning(
                f"[{self.config.name}] Reported failure for port {port}: {reason}"
            )

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取引擎统计信息

        Returns:
            Dict: 统计信息
        """
        stats = self.statistics.to_dict()
        stats["config"] = {
            "name": self.config.name,
            "version": self.config.version,
            "source": self.config.source,
            "enabled": self.config.enabled
        }
        return stats

    def is_initialized(self) -> bool:
        """检查引擎是否已初始化"""
        return self._initialized

    def get_active_sessions(self) -> List[str]:
        """获取活跃会话列表"""
        return list(self._sessions.keys())

    async def _execute_with_retry(
        self,
        func: Callable,
        match_id: str,
        *args,
        **kwargs
    ) -> Any:
        """
        带重试的执行器

        Args:
            func: 要执行的异步函数
            match_id: 比赛 ID（用于错误上下文）
            *args, **kwargs: 函数参数

        Returns:
            函数执行结果

        Raises:
            HarvestError: 重试次数用尽后仍失败
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"[{self.config.name}] Attempt {attempt + 1}/{self.config.max_retries} "
                    f"failed for match {match_id}: {e}"
                )

                if attempt < self.config.max_retries - 1:
                    # 指数退避
                    delay = self.config.rate_limit_delay * (2 ** attempt)
                    await asyncio.sleep(delay / 1000.0)

        # 重试用尽
        raise HarvestError(
            f"Failed after {self.config.max_retries} attempts: {last_error}",
            source=self.config.source,
            match_id=match_id,
            original_error=last_error
        )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_engine(
    engine_class: type,
    config: EngineConfig | None = None
) -> BaseHarvestEngine:
    """
    工厂函数：创建引擎实例

    Args:
        engine_class: 引擎类（必须继承 BaseHarvestEngine）
        config: 引擎配置（可选，使用默认配置如果为 None）

    Returns:
        BaseHarvestEngine: 引擎实例

    Raises:
        TypeError: engine_class 不是 BaseHarvestEngine 的子类
    """
    if not issubclass(engine_class, BaseHarvestEngine):
        raise TypeError(
            f"Engine class must inherit from BaseHarvestEngine, "
            f"got {engine_class.__name__}"
        )

    if config is None:
        config = EngineConfig()

    return engine_class(config)
