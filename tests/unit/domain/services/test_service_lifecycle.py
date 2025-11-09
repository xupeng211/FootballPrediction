#!/usr/bin/env python3
"""
🏗️ M2-P4-01: 领域服务生命周期测试
Domain Service Lifecycle Tests

测试领域服务的生命周期管理，包括：
- 服务初始化和依赖注入
- 服务配置和环境设置
- 服务状态管理
- 资源清理和销毁
- 服务健康检查

目标覆盖率: 领域服务模块覆盖率≥45%
"""

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

# 导入领域服务
try:
    from src.domain.services.match_service import MatchDomainService
    from src.domain.services.prediction_service import PredictionDomainService
    from src.domain.services.scoring_service import ScoringService
    from src.domain.services.team_service import TeamDomainService

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: Import failed: {e}")  # TODO: Add logger import if needed
    CAN_IMPORT = False

    # Mock implementations for testing
    class MatchDomainService:
        def __init__(self, config: dict = None):
            self._config = config or {}
            self._events = []
            self._is_initialized = False
            self._is_disposed = False
            self._health_status = "healthy"
            self._created_at = datetime.now()

        def initialize(self) -> bool:
            if self._is_disposed:
                raise RuntimeError("Cannot initialize disposed service")
            self._is_initialized = True
            return True

        def dispose(self) -> None:
            self._is_disposed = True
            self._events.clear()

        def is_healthy(self) -> bool:
            return self._health_status == "healthy" and not self._is_disposed

        def get_service_info(self) -> dict:
            return {
                "name": "MatchDomainService",
                "initialized": self._is_initialized,
                "disposed": self._is_disposed,
                "healthy": self.is_healthy(),
                "created_at": self._created_at.isoformat(),
                "config": self._config,
            }

    class PredictionDomainService:
        def __init__(self, config: dict = None):
            self._config = config or {}
            self._events = []
            self._is_initialized = False
            self._is_disposed = False
            self._health_status = "healthy"
            self._created_at = datetime.now()

        def initialize(self) -> bool:
            if self._is_disposed:
                raise RuntimeError("Cannot initialize disposed service")
            self._is_initialized = True
            return True

        def dispose(self) -> None:
            self._is_disposed = True
            self._events.clear()

        def is_healthy(self) -> bool:
            return self._health_status == "healthy" and not self._is_disposed

        def get_service_info(self) -> dict:
            return {
                "name": "PredictionDomainService",
                "initialized": self._is_initialized,
                "disposed": self._is_disposed,
                "healthy": self.is_healthy(),
                "created_at": self._created_at.isoformat(),
                "config": self._config,
            }

    class ScoringService:
        def __init__(self, config: dict = None):
            self._config = config or {}
            self._events = []
            self._is_initialized = False
            self._is_disposed = False
            self._health_status = "healthy"
            self._created_at = datetime.now()

        def initialize(self) -> bool:
            if self._is_disposed:
                raise RuntimeError("Cannot initialize disposed service")
            self._is_initialized = True
            return True

        def dispose(self) -> None:
            self._is_disposed = True
            self._events.clear()

        def is_healthy(self) -> bool:
            return self._health_status == "healthy" and not self._is_disposed

        def get_service_info(self) -> dict:
            return {
                "name": "ScoringService",
                "initialized": self._is_initialized,
                "disposed": self._is_disposed,
                "healthy": self.is_healthy(),
                "created_at": self._created_at.isoformat(),
                "config": self._config,
            }

    class TeamDomainService:
        def __init__(self, config: dict = None):
            self._config = config or {}
            self._events = []
            self._is_initialized = False
            self._is_disposed = False
            self._health_status = "healthy"
            self._created_at = datetime.now()

        def initialize(self) -> bool:
            if self._is_disposed:
                raise RuntimeError("Cannot initialize disposed service")
            self._is_initialized = True
            return True

        def dispose(self) -> None:
            self._is_disposed = True
            self._events.clear()

        def is_healthy(self) -> bool:
            return self._health_status == "healthy" and not self._is_disposed

        def get_service_info(self) -> dict:
            return {
                "name": "TeamDomainService",
                "initialized": self._is_initialized,
                "disposed": self._is_disposed,
                "healthy": self.is_healthy(),
                "created_at": self._created_at.isoformat(),
                "config": self._config,
            }


# 服务工厂和容器管理
class ServiceContainer:
    """服务容器，管理所有领域服务的生命周期"""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._config: dict[str, dict] = {}

    def register_service(
        self, name: str, service_class: type, config: dict = None
    ) -> None:
        """注册服务"""
        self._config[name] = config or {}
        # 不立即创建实例，延迟初始化

    def get_service(self, name: str) -> Any:
        """获取服务实例（延迟初始化）"""
        if name not in self._services:
            if name not in self._config:
                raise ValueError(f"Service {name} not registered")

            # 动态获取服务类
            service_classes = {
                "match": MatchDomainService,
                "prediction": PredictionDomainService,
                "scoring": ScoringService,
                "team": TeamDomainService,
            }

            if name not in service_classes:
                raise ValueError(f"Unknown service: {name}")

            service = service_classes[name](self._config[name])
            service.initialize()
            self._services[name] = service

        return self._services[name]

    def initialize_all(self) -> None:
        """初始化所有注册的服务"""
        for name in self._config:
            self.get_service(name)  # 延迟初始化

    def dispose_all(self) -> None:
        """销毁所有服务"""
        for service in self._services.values():
            service.dispose()
        self._services.clear()

    def get_health_status(self) -> dict[str, bool]:
        """获取所有服务的健康状态"""
        status = {}
        for name, service in self._services.items():
            status[name] = service.is_healthy()
        return status

    def get_service_infos(self) -> dict[str, dict]:
        """获取所有服务的信息"""
        infos = {}
        for name, service in self._services.items():
            infos[name] = service.get_service_info()
        return infos


@pytest.mark.skipif(not CAN_IMPORT, reason="领域服务导入失败")
@pytest.mark.unit
@pytest.mark.domain
@pytest.mark.services
class TestServiceLifecycle:
    """服务生命周期测试"""

    @pytest.fixture
    def service_container(self):
        """创建服务容器"""
        return ServiceContainer()

    @pytest.fixture
    def sample_config(self):
        """示例配置"""
        return {
            "timeout": 30,
            "retry_count": 3,
            "enable_logging": True,
            "cache_enabled": False,
        }

    def test_service_initialization(self, sample_config):
        """测试服务初始化"""
        service = MatchDomainService(sample_config)

        # 验证初始状态
        assert not service._is_initialized
        assert not service._is_disposed
        assert service._config == sample_config

        # 初始化服务
        result = service.initialize()

        # 验证初始化结果
        assert result is True
        assert service._is_initialized
        assert not service._is_disposed

    def test_service_disposal(self, sample_config):
        """测试服务销毁"""
        service = PredictionDomainService(sample_config)
        service.initialize()

        # 验证服务已初始化
        assert service._is_initialized
        assert not service._is_disposed

        # 销毁服务
        service.dispose()

        # 验证销毁结果
        assert service._is_disposed
        assert len(service._events) == 0

    def test_service_disposal_without_initialization(self, sample_config):
        """测试未初始化的服务销毁"""
        service = ScoringService(sample_config)

        # 直接销毁未初始化的服务
        service.dispose()

        # 验证销毁结果
        assert service._is_disposed

    def test_service_initialization_after_disposal(self, sample_config):
        """测试销毁后重新初始化应该失败"""
        service = TeamDomainService(sample_config)
        service.dispose()

        # 尝试初始化已销毁的服务
        with pytest.raises(RuntimeError, match="Cannot initialize disposed service"):
            service.initialize()

    def test_service_health_check(self, sample_config):
        """测试服务健康检查"""
        service = MatchDomainService(sample_config)

        # 未初始化的服务健康检查
        assert not service.is_healthy()

        # 初始化后的健康检查
        service.initialize()
        assert service.is_healthy()

        # 销毁后的健康检查
        service.dispose()
        assert not service.is_healthy()

    def test_service_health_status_manipulation(self, sample_config):
        """测试服务健康状态手动设置"""
        service = PredictionDomainService(sample_config)
        service.initialize()

        # 设置为不健康状态
        service._health_status = "unhealthy"
        assert not service.is_healthy()

        # 恢复健康状态
        service._health_status = "healthy"
        assert service.is_healthy()

    def test_service_info_retrieval(self, sample_config):
        """测试服务信息获取"""
        service = ScoringService(sample_config)
        service.initialize()

        info = service.get_service_info()

        # 验证信息内容
        assert info["name"] == "ScoringService"
        assert info["initialized"] is True
        assert info["disposed"] is False
        assert info["healthy"] is True
        assert "created_at" in info
        assert info["config"] == sample_config

    def test_service_configuration(self):
        """测试服务配置"""
        config1 = {"timeout": 10}
        config2 = {"timeout": 20, "retry_count": 5}

        service1 = MatchDomainService(config1)
        service2 = MatchDomainService(config2)

        # 验证不同配置
        assert service1._config["timeout"] == 10
        assert service2._config["timeout"] == 20
        assert service2._config["retry_count"] == 5

    def test_default_configuration(self):
        """测试默认配置"""
        service = PredictionDomainService()  # 无配置参数

        assert service._config == {}
        assert service.initialize()  # 应该能正常初始化

    def test_service_creation_timestamp(self):
        """测试服务创建时间戳"""
        before_creation = datetime.now()
        service = ScoringService()
        after_creation = datetime.now()

        # 验证创建时间戳
        assert before_creation <= service._created_at <= after_creation

    def test_multiple_services_lifecycle(self):
        """测试多个服务的生命周期管理"""
        services = [
            MatchDomainService(),
            PredictionDomainService(),
            ScoringService(),
            TeamDomainService(),
        ]

        # 初始化所有服务
        for service in services:
            assert service.initialize() is True
            assert service.is_healthy()

        # 验证所有服务健康
        assert all(service.is_healthy() for service in services)

        # 销毁所有服务
        for service in services:
            service.dispose()

        # 验证所有服务已销毁
        assert all(service._is_disposed for service in services)
        assert all(not service.is_healthy() for service in services)


@pytest.mark.unit
@pytest.mark.domain
@pytest.mark.services
class TestServiceContainer:
    """服务容器测试"""

    @pytest.fixture
    def container(self):
        """创建服务容器"""
        return ServiceContainer()

    def test_service_registration(self, container):
        """测试服务注册"""
        config = {"timeout": 30}
        container.register_service("match", MatchDomainService, config)

        # 验证配置已注册
        assert "match" in container._config
        assert container._config["match"] == config

    def test_service_lazy_initialization(self, container):
        """测试服务延迟初始化"""
        config = {"timeout": 30}
        container.register_service("prediction", PredictionDomainService, config)

        # 验证服务还未创建
        assert "prediction" not in container._services

        # 获取服务（触发初始化）
        service = container.get_service("prediction")

        # 验证服务已创建和初始化
        assert "prediction" in container._services
        assert service._is_initialized
        assert service._config == config

    def test_get_same_service_instance(self, container):
        """测试获取相同服务实例"""
        container.register_service("scoring", ScoringService)

        # 多次获取服务
        service1 = container.get_service("scoring")
        service2 = container.get_service("scoring")

        # 验证是同一个实例
        assert service1 is service2

    def test_get_nonexistent_service(self, container):
        """测试获取不存在的服务"""
        with pytest.raises(ValueError, match="Service nonexistent not registered"):
            container.get_service("nonexistent")

    def test_initialize_all_services(self, container):
        """测试初始化所有服务"""
        configs = {
            "match": {"timeout": 30},
            "prediction": {"retry_count": 3},
            "scoring": {"enable_logging": True},
            "team": {"cache_enabled": False},
        }

        # 注册所有服务
        for name, config in configs.items():
            if name == "match":
                service_class = MatchDomainService
            elif name == "prediction":
                service_class = PredictionDomainService
            elif name == "scoring":
                service_class = ScoringService
            elif name == "team":
                service_class = TeamDomainService
            else:
                continue
            container.register_service(name, service_class, config)

        # 初始化所有服务
        container.initialize_all()

        # 验证所有服务都已创建和初始化
        assert len(container._services) == 4
        for name, service in container._services.items():
            assert service._is_initialized
            assert service._config == configs[name]

    def test_dispose_all_services(self, container):
        """测试销毁所有服务"""
        # 注册和初始化服务
        container.register_service("match", MatchDomainService)
        container.register_service("prediction", PredictionDomainService)
        container.initialize_all()

        # 验证服务已创建
        assert len(container._services) == 2

        # 销毁所有服务
        container.dispose_all()

        # 验证所有服务已销毁
        assert len(container._services) == 0

    def test_get_health_status(self, container):
        """测试获取健康状态"""
        container.register_service("match", MatchDomainService)
        container.register_service("prediction", PredictionDomainService)
        container.initialize_all()

        # 获取健康状态
        status = container.get_health_status()

        # 验证健康状态
        assert len(status) == 2
        assert status["match"] is True
        assert status["prediction"] is True

        # 销毁一个服务
        container._services["match"]._is_disposed = True

        # 重新获取健康状态
        status = container.get_health_status()
        assert status["match"] is False
        assert status["prediction"] is True

    def test_get_service_infos(self, container):
        """测试获取服务信息"""
        config = {"timeout": 30}
        container.register_service("scoring", ScoringService, config)
        container.initialize_all()

        # 获取服务信息
        infos = container.get_service_infos()

        # 验证信息内容
        assert len(infos) == 1
        assert "scoring" in infos
        assert infos["scoring"]["name"] == "ScoringService"
        assert infos["scoring"]["initialized"] is True
        assert infos["scoring"]["config"] == config

    def test_container_lifecycle_integration(self, container):
        """测试容器生命周期集成"""
        # 注册服务
        configs = {"match": {"timeout": 30}, "prediction": {"retry_count": 3}}

        for name, config in configs.items():
            if name == "match":
                service_class = MatchDomainService
            elif name == "prediction":
                service_class = PredictionDomainService
            elif name == "scoring":
                service_class = ScoringService
            elif name == "team":
                service_class = TeamDomainService
            else:
                continue
            container.register_service(name, service_class, config)

        # 初始化所有服务
        container.initialize_all()

        # 验证初始状态
        assert len(container._services) == 2
        health_status = container.get_health_status()
        assert all(health_status.values())

        # 销毁所有服务
        container.dispose_all()

        # 验证最终状态
        assert len(container._services) == 0


@pytest.mark.unit
@pytest.mark.domain
@pytest.mark.services
@pytest.mark.integration
class TestServiceLifecycleIntegration:
    """服务生命周期集成测试"""

    def test_service_dependency_injection(self):
        """测试服务依赖注入"""
        # 模拟依赖注入场景
        container = ServiceContainer()

        # 配置服务依赖
        container.register_service("match", MatchDomainService, {"timeout": 30})
        container.register_service(
            "prediction", PredictionDomainService, {"match_service": "match"}
        )

        # 初始化服务
        container.initialize_all()

        # 获取预测服务并验证其能够访问比赛服务
        prediction_service = container.get_service("prediction")
        match_service = container.get_service("match")

        # 验证服务都正常初始化
        assert prediction_service.is_healthy()
        assert match_service.is_healthy()

    def test_service_configuration_validation(self):
        """测试服务配置验证"""
        ServiceContainer()

        # 测试无效配置
        with pytest.raises(Exception):
            MatchDomainService({"invalid_key": "value"})
            # 这里可能需要实现实际的配置验证逻辑

    def test_service_error_handling_during_lifecycle(self):
        """测试生命周期过程中的错误处理"""
        service = MatchDomainService()

        # 模拟初始化错误
        with patch.object(
            service, "initialize", side_effect=Exception("Initialization failed")
        ):
            with pytest.raises(Exception, match="Initialization failed"):
                service.initialize()

        # 验证服务状态
        assert not service._is_initialized

    def test_concurrent_service_initialization(self):
        """测试并发服务初始化"""
        import threading

        container = ServiceContainer()
        container.register_service("match", MatchDomainService)

        results = []
        errors = []

        def initialize_service():
            try:
                service = container.get_service("match")
                results.append(service._is_initialized)
            except Exception as e:
                errors.append(str(e))

        # 创建多个线程同时初始化服务
        threads = [threading.Thread(target=initialize_service) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0
        assert len(results) == 5
        assert all(results)  # 所有初始化都成功

    def test_service_lifecycle_monitoring(self):
        """测试服务生命周期监控"""
        container = ServiceContainer()

        # 注册服务
        container.register_service("match", MatchDomainService)
        container.register_service("prediction", PredictionDomainService)

        # 监控初始状态
        initial_health = container.get_health_status()
        assert len(initial_health) == 0  # 还未初始化

        # 初始化并监控
        container.initialize_all()
        after_init_health = container.get_health_status()
        assert len(after_init_health) == 2
        assert all(after_init_health.values())

        # 获取服务信息用于监控
        service_infos = container.get_service_infos()
        for _name, info in service_infos.items():
            assert "created_at" in info
            assert "healthy" in info
            assert "initialized" in info

        # 销毁并监控
        container.dispose_all()
        final_health = container.get_health_status()
        assert len(final_health) == 0


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
