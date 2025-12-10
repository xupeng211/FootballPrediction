"""
数据获取器工厂
Data Fetcher Factory

提供统一的获取器创建和管理接口，支持动态注册和创建不同类型的数据获取器实例。

工厂模式实现，允许：
1. 动态注册新的获取器类型
2. 通过名称字符串创建获取器实例
3. 查询所有可用的获取器类型
4. 配置获取器实例的参数

作者: Data Integration Team
创建时间: 2025-12-07
版本: 1.0.0
"""

import logging
from typing import Dict, List, Optional, Type, Any

from src.collectors.abstract_fetcher import AbstractFetcher, FetcherError
from .oddsportal_fetcher import OddsPortalFetcher

logger = logging.getLogger(__name__)


class FetcherFactory:
    """
    数据获取器工厂类

    采用注册表模式，允许运行时动态注册和创建获取器实例。
    提供类型安全的实例创建和配置管理功能。
    """

    # 注册表：存储获取器类和元数据
    _registry: dict[str, type[AbstractFetcher]] = {}
    _metadata: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        fetcher_class: type[AbstractFetcher],
        description: Optional[str] = None,
        version: str = "1.0.0",
        **metadata
    ) -> None:
        """
        注册获取器类

        Args:
            name: 获取器名称 (用于标识和创建)
            fetcher_class: 获取器类，必须继承自AbstractFetcher
            description: 获取器描述
            version: 获取器版本
            **metadata: 额外的元数据

        Raises:
            TypeError: 当fetcher_class不继承AbstractFetcher时
            ValueError: 当name已存在时
        """
        # 验证获取器类
        if not issubclass(fetcher_class, AbstractFetcher):
            raise TypeError(
                f"获取器类 {fetcher_class.__name__} 必须继承自 AbstractFetcher"
            )

        # 检查名称冲突
        if name in cls._registry:
            logger.warning(f"覆盖已存在的获取器: {name}")

        # 注册获取器
        cls._registry[name] = fetcher_class

        # 注册元数据
        cls._metadata[name] = {
            "name": name,
            "class_name": fetcher_class.__name__,
            "description": description or f"{fetcher_class.__name__} 数据获取器",
            "version": version,
            "module": fetcher_class.__module__,
            **metadata
        }

        logger.info(f"成功注册获取器: {name} ({fetcher_class.__name__})")

    @classmethod
    def create(
        cls,
        name: str,
        config: Optional[dict[str, Any]] = None,
        **kwargs
    ) -> AbstractFetcher:
        """
        创建获取器实例

        Args:
            name: 获取器名称
            config: 配置参数字典
            **kwargs: 额外的配置参数

        Returns:
            AbstractFetcher: 获取器实例

        Raises:
            FetcherError: 当获取器不存在时
            Exception: 创建实例时的其他异常
        """
        if name not in cls._registry:
            available = ", ".join(cls.list_available())
            raise FetcherError(f"未知的获取器: {name}。可用获取器: {available}")

        try:
            # 获取获取器类
            fetcher_class = cls._registry[name]

            # 合并配置参数
            final_config = config or {}
            final_config.update(kwargs)

            # 创建实例
            instance = fetcher_class(source_name=name, config=final_config)

            logger.info(f"成功创建获取器实例: {name}")
            return instance

        except Exception as e:
            logger.error(f"创建获取器实例失败: {name}, 错误: {e}")
            raise FetcherError(f"创建获取器 {name} 失败: {e}")

    @classmethod
    def list_available(cls) -> list[str]:
        """
        获取所有已注册的获取器名称列表

        Returns:
            List[str]: 获取器名称列表
        """
        return list(cls._registry.keys())

    @classmethod
    def get_metadata(cls, name: str) -> Optional[dict[str, Any]]:
        """
        获取指定获取器的元数据

        Args:
            name: 获取器名称

        Returns:
            Optional[Dict[str, Any]]: 元数据字典，如果不存在则返回None
        """
        return cls._metadata.get(name)

    @classmethod
    def list_metadata(cls) -> dict[str, dict[str, Any]]:
        """
        获取所有获取器的元数据

        Returns:
            Dict[str, Dict[str, Any]]: 所有获取器的元数据字典
        """
        return cls._metadata.copy()

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        注销获取器

        Args:
            name: 获取器名称

        Returns:
            bool: 是否成功注销
        """
        if name in cls._registry:
            del cls._registry[name]
            if name in cls._metadata:
                del cls._metadata[name]
            logger.info(f"成功注销获取器: {name}")
            return True
        return False

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        检查获取器是否已注册

        Args:
            name: 获取器名称

        Returns:
            bool: 是否已注册
        """
        return name in cls._registry

    @classmethod
    def get_registry_info(cls) -> dict[str, Any]:
        """
        获取注册表信息统计

        Returns:
            Dict[str, Any]: 注册表统计信息
        """
        return {
            "total_registered": len(cls._registry),
            "available_fetchers": cls.list_available(),
            "metadata_count": len(cls._metadata),
            "registry": cls._registry.copy(),
            "metadata": cls._metadata.copy()
        }


# 自动注册内置获取器
def _register_builtin_fetchers():
    """
    自动注册内置的获取器

    该函数在模块导入时自动调用，确保所有内置获取器都可用。
    """
    try:
        # 注册OddsPortal获取器
        FetcherFactory.register(
            name="oddsportal",
            fetcher_class=OddsPortalFetcher,
            description="OddsPortal 网站数据获取器，提供多种市场类型的赔率数据",
            version="1.0.0",
            supported_markets=["1X2", "Asian Handicap", "Over/Under", "Both Teams to Score", "Correct Score"],
            supported_bookmakers=["Bet365", "William Hill", "Betfair", "Paddy Power", "Ladbrokes"],
            data_type="odds",
            refresh_rate="实时",
            requires_auth=False
        )

        logger.info("内置获取器自动注册完成")

    except Exception as e:
        logger.error(f"自动注册内置获取器失败: {e}")


# 模块导入时自动注册
_register_builtin_fetchers()


# 导出公共接口
__all__ = [
    "FetcherFactory",
    "OddsPortalFetcher",
]
