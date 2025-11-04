"""
ServiceLifecycleManager 综合测试
目标覆盖率: 40%
当前覆盖率: 26%
新增测试: 15个测试用例
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.service_lifecycle import (ServiceInfo, ServiceLifecycleError,
                                        ServiceLifecycleManager, ServiceState,
                                        get_lifecycle_manager)


class TestServiceState:
    """ServiceState枚举测试"""

    def test_service_state_values(self):
        """测试服务状态枚举值"""
        assert ServiceState.INITIALIZED.value == "initialized"
        assert ServiceState.READY.value == "ready"
        assert ServiceState.STARTING.value == "starting"
        assert ServiceState.RUNNING.value == "running"
        assert ServiceState.STOPPING.value == "stopping"
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.ERROR.value == "error"

    def test_service_state_comparison(self):
        """测试服务状态比较"""
        state1 = ServiceState.RUNNING
        state2 = ServiceState.RUNNING
        state3 = ServiceState.STOPPED

        assert state1 == state2
        assert state1 != state3
        assert hash(state1) == hash(state2)


class TestServiceInfo:
    """ServiceInfo数据类测试"""

    def test_service_info_creation(self):
        """测试服务信息创建"""
        mock_service = Mock()
        service_info = ServiceInfo(
            name="test_service",
            service=mock_service,
            state=ServiceState.INITIALIZED,
            dependencies=["dep1", "dep2"],
            dependents=["dep3"],
            health_check=lambda s: True,
            startup_timeout=30.0,
            shutdown_timeout=10.0,
        )

        assert service_info.name == "test_service"
        assert service_info.service == mock_service
        assert service_info.state == ServiceState.INITIALIZED
        assert service_info.dependencies == ["dep1", "dep2"]
        assert service_info.dependents == ["dep3"]
        assert service_info.startup_timeout == 30.0
        assert service_info.shutdown_timeout == 10.0
        assert service_info.last_health_check is None

    def test_service_info_defaults(self):
        """测试服务信息默认值"""
        mock_service = Mock()
        service_info = ServiceInfo(
            name="test_service",
            service=mock_service,
            state=ServiceState.INITIALIZED,
            dependencies=[],
            dependents=[],
        )

        assert service_info.health_check is None
        assert service_info.startup_timeout == 30.0
        assert service_info.shutdown_timeout == 10.0
        assert service_info.last_health_check is None


class TestServiceLifecycleManager:
    """ServiceLifecycleManager核心功能测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.manager = ServiceLifecycleManager()

    def teardown_method(self):
        """每个测试方法后的清理"""
        try:
            self.manager.shutdown_all()
        except Exception:
            pass

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = ServiceLifecycleManager()

        assert isinstance(manager._services, dict)
        assert len(manager._services) == 0
        assert hasattr(manager, "_lock")
        assert hasattr(manager, "_shutdown_event")
        assert manager._monitoring_task is None
        assert manager._loop is None

    def test_register_service_success(self):
        """测试服务注册成功"""
        mock_service = Mock()
        health_check = Mock(return_value=True)

        self.manager.register_service(
            name="test_service",
            service=mock_service,
            dependencies=["dep1"],
            health_check=health_check,
            startup_timeout=45.0,
            shutdown_timeout=15.0,
        )

        service_info = self.manager.get_service_status("test_service")
        assert service_info is not None
        assert service_info.name == "test_service"
        assert service_info.service == mock_service
        assert service_info.state == ServiceState.INITIALIZED
        assert service_info.dependencies == ["dep1"]
        assert service_info.health_check == health_check
        assert service_info.startup_timeout == 45.0
        assert service_info.shutdown_timeout == 15.0

    def test_register_service_duplicate_warning(self):
        """测试重复注册服务的警告"""
        mock_service = Mock()

        # 第一次注册
        self.manager.register_service("test_service", mock_service)

        # 第二次注册应该产生警告但不抛出异常
        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.register_service("test_service", Mock())
            mock_logger.warning.assert_called_with("服务已存在: test_service")

    def test_register_service_with_dependencies(self):
        """测试带依赖关系的服务注册"""
        mock_service1 = Mock()
        mock_service2 = Mock()

        # 先注册依赖服务
        self.manager.register_service("dependency", mock_service1)

        # 注册依赖服务
        self.manager.register_service(
            "main_service", mock_service2, dependencies=["dependency"]
        )

        # 检查依赖关系
        main_service_info = self.manager.get_service_status("main_service")
        dependency_info = self.manager.get_service_status("dependency")

        assert "dependency" in main_service_info.dependencies
        assert "main_service" in dependency_info.dependents

    def test_unregister_service_success(self):
        """测试服务注销成功"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)

        # 注销服务
        self.manager.unregister_service("test_service")

        # 验证服务已移除
        assert self.manager.get_service_status("test_service") is None

    def test_unregister_service_not_found(self):
        """测试注销不存在的服务"""
        with pytest.raises(ServiceLifecycleError) as exc_info:
            self.manager.unregister_service("nonexistent_service")

        assert "服务未注册" in str(exc_info.value)

    def test_unregister_running_service(self):
        """测试注销正在运行的服务"""
        mock_service = Mock()
        mock_service.stop = Mock()

        self.manager.register_service("test_service", mock_service)

        # 手动设置状态为运行
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        # 注销服务应该停止它
        with patch.object(self.manager, "_stop_service_sync") as mock_stop:
            self.manager.unregister_service("test_service")
            mock_stop.assert_called_once_with("test_service")

    def test_start_service_success(self):
        """测试服务启动成功"""
        mock_service = Mock()
        mock_service.start = Mock()

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.READY

        self.manager.start_service("test_service")

        updated_service_info = self.manager.get_service_status("test_service")
        assert updated_service_info.state == ServiceState.RUNNING
        mock_service.start.assert_called_once()

    def test_start_service_with_dependencies(self):
        """测试启动带依赖的服务"""
        mock_dependency = Mock()
        mock_dependency.start = Mock()
        mock_main = Mock()
        mock_main.start = Mock()

        # 注册依赖服务
        self.manager.register_service("dependency", mock_dependency)
        dep_info = self.manager.get_service_status("dependency")
        dep_info.state = ServiceState.READY

        # 注册主服务
        self.manager.register_service(
            "main_service", mock_main, dependencies=["dependency"]
        )
        main_info = self.manager.get_service_status("main_service")
        main_info.state = ServiceState.READY

        # 启动主服务应该先启动依赖
        self.manager.start_service("main_service")

        # 验证两个服务都启动了
        updated_dep_info = self.manager.get_service_status("dependency")
        updated_main_info = self.manager.get_service_status("main_service")

        assert updated_dep_info.state == ServiceState.RUNNING
        assert updated_main_info.state == ServiceState.RUNNING
        mock_dependency.start.assert_called_once()
        mock_main.start.assert_called_once()

    def test_start_service_not_found(self):
        """测试启动不存在的服务"""
        with pytest.raises(ServiceLifecycleError) as exc_info:
            self.manager.start_service("nonexistent_service")

        assert "服务未注册" in str(exc_info.value)

    def test_start_service_already_running(self):
        """测试启动已在运行的服务"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        # 启动已运行的服务应该直接返回
        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.start_service("test_service")
            mock_logger.debug.assert_called_with("服务已在运行: test_service")

    def test_start_service_invalid_state(self):
        """测试从无效状态启动服务"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.ERROR

        with pytest.raises(ServiceLifecycleError) as exc_info:
            self.manager.start_service("test_service")

        assert "服务状态不允许启动" in str(exc_info.value)
        assert "ERROR" in str(exc_info.value)

    def test_start_service_with_exception(self):
        """测试服务启动时发生异常"""
        mock_service = Mock()
        mock_service.start.side_effect = Exception("启动失败")

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.READY

        with pytest.raises(ServiceLifecycleError) as exc_info:
            self.manager.start_service("test_service")

        assert "服务启动失败" in str(exc_info.value)
        # 验证状态被设置为ERROR
        updated_info = self.manager.get_service_status("test_service")
        assert updated_info.state == ServiceState.ERROR

    def test_stop_service_success(self):
        """测试服务停止成功"""
        mock_service = Mock()
        mock_service.stop = Mock()

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        self.manager.stop_service("test_service")

        updated_service_info = self.manager.get_service_status("test_service")
        assert updated_service_info.state == ServiceState.STOPPED
        mock_service.stop.assert_called_once()

    def test_stop_service_not_running(self):
        """测试停止未运行的服务"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.READY

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.stop_service("test_service")
            mock_logger.debug.assert_called_with("服务未运行: test_service")

    def test_stop_service_not_found(self):
        """测试停止不存在的服务"""
        with pytest.raises(ServiceLifecycleError) as exc_info:
            self.manager.stop_service("nonexistent_service")

        assert "服务未注册" in str(exc_info.value)

    def test_stop_service_with_dependents(self):
        """测试停止有依赖服务的服务"""
        mock_main = Mock()
        mock_main.stop = Mock()
        mock_dependent = Mock()
        mock_dependent.stop = Mock()

        # 注册主服务
        self.manager.register_service("main_service", mock_main)
        main_info = self.manager.get_service_status("main_service")
        main_info.state = ServiceState.RUNNING

        # 注册依赖服务
        self.manager.register_service(
            "dependent_service", mock_dependent, dependencies=["main_service"]
        )
        dependent_info = self.manager.get_service_status("dependent_service")
        dependent_info.state = ServiceState.RUNNING

        # 停止主服务应该先停止依赖服务
        with patch.object(self.manager, "_stop_service_sync") as mock_stop:
            self.manager.stop_service("main_service")
            # 验证依赖服务被停止
            assert mock_stop.call_count >= 1  # 至少调用了一次

    def test_get_service_status(self):
        """测试获取服务状态"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)

        service_info = self.manager.get_service_status("test_service")
        assert service_info is not None
        assert service_info.name == "test_service"

        # 测试不存在的服务
        nonexistent = self.manager.get_service_status("nonexistent")
        assert nonexistent is None

    def test_get_all_services(self):
        """测试获取所有服务"""
        mock_service1 = Mock()
        mock_service2 = Mock()

        self.manager.register_service("service1", mock_service1)
        self.manager.register_service("service2", mock_service2)

        all_services = self.manager.get_all_services()
        assert len(all_services) == 2
        assert "service1" in all_services
        assert "service2" in all_services

        # 验证返回的是副本
        all_services["new_service"] = Mock()
        assert "new_service" not in self.manager._services


class TestServiceLifecycleManagerAsync:
    """异步功能测试"""

    def setup_method(self):
        self.manager = ServiceLifecycleManager()

    def teardown_method(self):
        try:
            self.manager.shutdown_all()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """测试所有服务健康检查通过"""
        mock_service = Mock()
        health_check = Mock(return_value=True)

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        results = await self.manager.health_check()
        assert results["test_service"] is True
        health_check.assert_called_once_with(mock_service)

    @pytest.mark.asyncio
    async def test_health_check_async_healthy(self):
        """测试异步健康检查"""
        mock_service = Mock()
        health_check = AsyncMock(return_value=True)

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        results = await self.manager.health_check()
        assert results["test_service"] is True
        health_check.assert_called_once_with(mock_service)

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_service(self):
        """测试不健康服务检查"""
        mock_service = Mock()
        health_check = Mock(return_value=False)

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        results = await self.manager.health_check()
        assert results["test_service"] is False

    @pytest.mark.asyncio
    async def test_health_check_no_health_check_function(self):
        """测试没有健康检查函数的服务"""
        mock_service = Mock()

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        results = await self.manager.health_check()
        assert results["test_service"] is True  # 默认健康检查

    @pytest.mark.asyncio
    async def test_health_check_error_service(self):
        """测试错误状态的服务"""
        mock_service = Mock()

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.ERROR

        results = await self.manager.health_check()
        assert results["test_service"] is False

    @pytest.mark.asyncio
    async def test_health_check_exception_in_check(self):
        """测试健康检查函数抛出异常"""
        mock_service = Mock()
        health_check = Mock(side_effect=Exception("检查失败"))

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            results = await self.manager.health_check()
            assert results["test_service"] is False
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_updates_timestamp(self):
        """测试健康检查更新时间戳"""
        mock_service = Mock()
        health_check = Mock(return_value=True)

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING
        original_timestamp = service_info.last_health_check

        # 等待一小段时间确保时间戳不同
        await asyncio.sleep(0.001)

        await self.manager.health_check()

        updated_service_info = self.manager.get_service_status("test_service")
        assert updated_service_info.last_health_check > original_timestamp

    @pytest.mark.asyncio
    async def test_async_service_start(self):
        """测试异步服务启动"""
        mock_service = Mock()
        mock_service.start = AsyncMock()

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.READY

        with patch.object(self.manager, "_start_service_async") as mock_async_start:
            self.manager.start_service("test_service")
            mock_async_start.assert_called_once_with("test_service")

    @pytest.mark.asyncio
    async def test_async_service_stop(self):
        """测试异步服务停止"""
        mock_service = Mock()
        mock_service.stop = AsyncMock()

        self.manager.register_service("test_service", mock_service)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        with patch.object(self.manager, "_stop_service_async") as mock_async_stop:
            self.manager.stop_service("test_service")
            mock_async_stop.assert_called_once_with("test_service")

    @pytest.mark.asyncio
    async def test_start_service_async_timeout(self):
        """测试异步服务启动超时"""
        mock_service = Mock()
        mock_service.start = AsyncMock(side_effect=asyncio.sleep(1))

        self.manager.register_service("test_service", mock_service, startup_timeout=0.1)
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.READY

        with pytest.raises(ServiceLifecycleError) as exc_info:
            await self.manager._start_service_async("test_service")

        assert "服务启动超时" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_service_async_timeout(self):
        """测试异步服务停止超时"""
        mock_service = Mock()
        mock_service.stop = AsyncMock(side_effect=asyncio.sleep(1))

        self.manager.register_service(
            "test_service", mock_service, shutdown_timeout=0.1
        )

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            await self.manager._stop_service_async("test_service")
            mock_logger.warning.assert_called_with("服务停止超时: test_service")


class TestServiceLifecycleManagerMonitoring:
    """监控功能测试"""

    def setup_method(self):
        self.manager = ServiceLifecycleManager()

    def teardown_method(self):
        try:
            self.manager.stop_monitoring()
            self.manager.shutdown_all()
        except Exception:
            pass

    def test_start_monitoring_success(self):
        """测试启动监控成功"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.start_monitoring(interval=0.1)
            mock_logger.info.assert_called_with("启动服务监控")

        assert self.manager._monitoring_task is not None
        assert self.manager._loop is not None

    def test_start_monitoring_already_running(self):
        """测试重复启动监控"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)

        # 第一次启动
        self.manager.start_monitoring(interval=0.1)

        # 第二次启动应该产生警告
        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.start_monitoring(interval=0.1)
            mock_logger.warning.assert_called_with("监控已在运行")

    def test_stop_monitoring_success(self):
        """测试停止监控成功"""
        mock_service = Mock()
        self.manager.register_service("test_service", mock_service)

        # 启动监控
        self.manager.start_monitoring(interval=0.1)

        # 停止监控
        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.stop_monitoring()
            mock_logger.info.assert_called_with("停止服务监控")

        assert self.manager._monitoring_task is None
        assert self.manager._loop is None

    def test_stop_monitoring_not_running(self):
        """测试停止未运行的监控"""
        # 停止未运行的监控应该直接返回
        result = self.manager.stop_monitoring()
        assert result is None

    @pytest.mark.asyncio
    async def test_monitoring_loop_basic(self):
        """测试监控循环基本功能"""
        mock_service = Mock()
        health_check = Mock(return_value=True)

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        # 设置关闭事件让循环退出
        self.manager._shutdown_event.set()

        # 运行监控循环（应该立即退出）
        await self.manager._monitoring_loop(0.1)

    @pytest.mark.asyncio
    async def test_monitoring_loop_with_unhealthy_services(self):
        """测试监控循环处理不健康服务"""
        mock_service = Mock()
        health_check = Mock(return_value=False)

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            # 设置关闭事件让循环退出
            self.manager._shutdown_event.set()
            await self.manager._monitoring_loop(0.1)
            mock_logger.warning.assert_called_with("不健康的服务: ['test_service']")

    @pytest.mark.asyncio
    async def test_monitoring_loop_with_exception(self):
        """测试监控循环异常处理"""
        mock_service = Mock()
        health_check = Mock(side_effect=Exception("监控错误"))

        self.manager.register_service(
            "test_service", mock_service, health_check=health_check
        )
        service_info = self.manager.get_service_status("test_service")
        service_info.state = ServiceState.RUNNING

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            # 设置关闭事件让循环退出
            self.manager._shutdown_event.set()
            await self.manager._monitoring_loop(0.1)
            mock_logger.error.assert_called_with("监控循环错误: 监控错误")


class TestServiceLifecycleManagerShutdown:
    """关闭功能测试"""

    def setup_method(self):
        self.manager = ServiceLifecycleManager()

    def test_shutdown_all_success(self):
        """测试关闭所有服务成功"""
        mock_service1 = Mock()
        mock_service1.stop = Mock()
        mock_service2 = Mock()
        mock_service2.stop = Mock()

        # 注册并启动服务
        self.manager.register_service("service1", mock_service1)
        self.manager.register_service("service2", mock_service2)

        service1_info = self.manager.get_service_status("service1")
        service1_info.state = ServiceState.RUNNING
        service2_info = self.manager.get_service_status("service2")
        service2_info.state = ServiceState.RUNNING

        # 启动监控
        self.manager.start_monitoring(interval=0.1)

        with patch("src.core.service_lifecycle.logger") as mock_logger:
            self.manager.shutdown_all()
            mock_logger.info.assert_called_with("所有服务已关闭")

        # 验证监控已停止
        assert self.manager._monitoring_task is None


class TestGlobalLifecycleManager:
    """全局生命周期管理器测试"""

    def test_get_lifecycle_manager_singleton(self):
        """测试获取全局生命周期管理器单例"""
        manager1 = get_lifecycle_manager()
        manager2 = get_lifecycle_manager()

        assert manager1 is manager2
        assert isinstance(manager1, ServiceLifecycleManager)

    def test_global_manager_persistence(self):
        """测试全局管理器持久性"""
        manager = get_lifecycle_manager()
        mock_service = Mock()

        # 在全局管理器中注册服务
        manager.register_service("global_test_service", mock_service)

        # 再次获取全局管理器应该包含该服务
        new_manager = get_lifecycle_manager()
        service_info = new_manager.get_service_status("global_test_service")
        assert service_info is not None
        assert service_info.name == "global_test_service"


class TestServiceLifecycleError:
    """ServiceLifecycleError异常测试"""

    def test_service_lifecycle_error_creation(self):
        """测试服务生命周期异常创建"""
        error = ServiceLifecycleError("测试错误")
        assert str(error) == "测试错误"

    def test_service_lifecycle_error_inheritance(self):
        """测试服务生命周期异常继承"""
        error = ServiceLifecycleError("测试错误")
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)
