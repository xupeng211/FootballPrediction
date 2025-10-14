from typing import Any, Dict, List, Optional, Union
"""
依赖注入设置
Dependency Injection Setup

提供依赖注入的初始化和配置功能。
Provides initialization and configuration for dependency injection.
"""

import os
from pathlib import Path
import logging

from .di import DIContainer, ServiceCollection, ServiceLifetime
from .service_lifecycle import ServiceLifecycleManager, get_lifecycle_manager
from .config_di import ConfigurationBinder
from .auto_binding import AutoBinder
from ..database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DISetup:
    """依赖注入设置类"""

    def __init__(self, profile: Optional[str] ] = None) -> None:
        self.profile = profile or os.getenv("APP_PROFILE", "development")
        self.container: Optional[DIContainer] = None
        self.lifecycle_manager: Optional[ServiceLifecycleManager] = None
    def initialize(
        self,
        config_file: Optional[str] ] = None,
        auto_scan_modules: Optional[list] ] = None,
    ) -> DIContainer:
        """初始化依赖注入"""
        logger.info(f"初始化依赖注入，配置文件: {config_file}, 环境: {self.profile}")

        # 创建容器
        collection = ServiceCollection()

        # 加载配置文件
        if config_file and Path(config_file).exists():
            binder = ConfigurationBinder(DIContainer())
            binder.load_from_file(config_file)
            binder.set_active_profile(self.profile)  # type: ignore
            binder.apply_configuration()
            self.container = binder.container
        else:
            self.container = collection.build_container()

        # 自动扫描模块
        if auto_scan_modules:
            auto_binder = AutoBinder(self.container)
            for module in auto_scan_modules:
                auto_binder.bind_from_assembly(module)

        # 注册核心服务
        self._register_core_services()

        # 获取生命周期管理器
        self.lifecycle_manager = get_lifecycle_manager()

        logger.info("依赖注入初始化完成")
        return self.container

    def _register_core_services(self) -> None:
        """注册核心服务"""
        # 注册生命周期管理器
        self.container.register_singleton(  # type: ignore
            ServiceLifecycleManager, instance=self.lifecycle_manager
        )

        # 自动注册所有仓储
        self._auto_register_repositories()

        # 自动注册所有服务
        self._auto_register_services()

    def _auto_register_repositories(self) -> None:
        """自动注册仓储"""
        # 这里可以扫描并自动注册所有仓储类
        # 简化示例，手动注册主要仓储
        try:
            from ..database.repositories.match_repository import MatchRepository  # type: ignore
            from ..database.repositories.prediction_repository import (  # type: ignore
                PredictionRepository,
            )
            from ..database.repositories.user_repository import UserRepository  # type: ignore

            self.container.register_scoped(BaseRepository, MatchRepository)  # type: ignore
            self.container.register_scoped(BaseRepository, PredictionRepository)  # type: ignore
            self.container.register_scoped(BaseRepository, UserRepository)  # type: ignore

            logger.debug("注册仓储服务完成")
        except ImportError as e:
            logger.warning(f"无法导入仓储类: {e}")

    def _auto_register_services(self) -> None:
        """自动注册服务"""
        # 这里可以扫描并自动注册所有服务类
        try:
            from ..services.database import DatabaseService  # type: ignore
            from ..services.prediction import PredictionService  # type: ignore
            from ..services.cache import CacheService  # type: ignore

            self.container.register_singleton(DatabaseService)  # type: ignore
            self.container.register_scoped(PredictionService)  # type: ignore
            self.container.register_singleton(CacheService)  # type: ignore

            logger.debug("注册业务服务完成")
        except ImportError as e:
            logger.warning(f"无法导入服务类: {e}")

    async def start_services(self) -> None:
        """启动所有服务"""
        if self.lifecycle_manager:
            await self.lifecycle_manager.start_all_services()
            # 启动健康监控
            self.lifecycle_manager.start_monitoring(interval=30.0)

    async def stop_services(self) -> None:
        """停止所有服务"""
        if self.lifecycle_manager:
            await self.lifecycle_manager.shutdown()


# 全局DI设置实例
_di_setup: Optional[DISetup] = None
def get_di_setup() -> DISetup:
    """获取DI设置实例"""
    global _di_setup
    if _di_setup is None:
        _di_setup = DISetup()
    return _di_setup


def configure_di(
    config_file: Optional[str] ] = None,
    profile: Optional[str] ] = None,
    auto_scan_modules: Optional[list] ] = None,
) -> DIContainer:
    """配置依赖注入（便捷函数）"""
    setup = DISetup(profile)
    return setup.initialize(config_file, auto_scan_modules)


# 装饰器：自动注册服务
def register_service(
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    interface: Optional[type] ] = None,
    name: Optional[str] ] = None,
):
    """自动注册服务装饰器"""

    def decorator(cls) -> None:
        # 保存注册信息
        cls.__di_lifetime__ = lifetime
        cls.__di_interface__ = interface
        cls.__di_name__ = name or cls.__name__

        # 在类被导入时自动注册
        setup = get_di_setup()
        if setup.container:
            if interface:
                if lifetime == ServiceLifetime.SINGLETON:
                    setup.container.register_singleton(interface, cls)
                elif lifetime == ServiceLifetime.SCOPED:
                    setup.container.register_scoped(interface, cls)
                else:
                    setup.container.register_transient(interface, cls)
            else:
                if lifetime == ServiceLifetime.SINGLETON:
                    setup.container.register_singleton(cls)
                elif lifetime == ServiceLifetime.SCOPED:
                    setup.container.register_scoped(cls)
                else:
                    setup.container.register_transient(cls)

        return cls

    return decorator


# 示例：创建配置文件的便捷函数
def create_di_config(
    output_path: str = "configs/di-config.yaml", format: str = "yaml"
) -> None:
    """创建依赖注入配置文件"""
    from .config_di import generate_sample_config

    config_content = generate_sample_config(format)

    # 确保目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 写入配置文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    logger.info(f"创建配置文件: {output_path}")
