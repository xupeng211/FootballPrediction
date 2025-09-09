"""
测试services模块的功能
"""

import pytest

from src.models import AnalysisResult, Content, User
from src.services import (BaseService, ContentAnalysisService,
                          DataProcessingService, ServiceManager,
                          UserProfileService, service_manager)


class TestBaseService:
    """测试基础服务抽象类"""

    def test_base_service_creation(self):
        """测试基础服务创建"""

        # 由于BaseService是抽象类，需要创建具体实现来测试
        class TestService(BaseService):
            async def initialize(self) -> bool:
                return True

            async def shutdown(self) -> None:
                pass

        service = TestService("test_service")
        assert service.name == "test_service"
        assert service.logger is not None


class TestContentAnalysisService:
    """测试内容分析服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return ContentAnalysisService()

    @pytest.fixture
    def sample_content(self):
        """创建测试内容"""
        from src.models import ContentType

        return Content(
            id="test_content_1",
            title="测试内容",
            content_data="这是一个测试内容",
            author_id="user_1",
            content_type=ContentType.TEXT,
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """测试服务初始化"""
        assert not service._initialized
        result = await service.initialize()
        assert result is True
        assert service._initialized is True

    @pytest.mark.asyncio
    async def test_service_shutdown(self, service):
        """测试服务关闭"""
        await service.initialize()
        await service.shutdown()
        assert service._initialized is False

    @pytest.mark.asyncio
    async def test_analyze_content_success(self, service, sample_content):
        """测试内容分析成功"""
        await service.initialize()
        result = await service.analyze_content(sample_content)

        assert result is not None
        assert isinstance(result, AnalysisResult)
        assert result.content_id == sample_content.id
        assert result.analysis_type == "content_analysis"
        assert result.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_analyze_content_not_initialized(self, service, sample_content):
        """测试未初始化时分析内容"""
        with pytest.raises(RuntimeError, match="服务未初始化"):
            await service.analyze_content(sample_content)

    @pytest.mark.asyncio
    async def test_batch_analyze(self, service):
        """测试批量分析"""
        await service.initialize()

        from src.models import ContentType

        contents = [
            Content(
                id="1",
                title="内容1",
                content_data="测试内容1",
                author_id="user1",
                content_type=ContentType.TEXT,
            ),
            Content(
                id="2",
                title="内容2",
                content_data="测试内容2",
                author_id="user2",
                content_type=ContentType.TEXT,
            ),
        ]

        results = await service.batch_analyze(contents)
        assert len(results) == 2
        assert all(isinstance(r, AnalysisResult) for r in results)


class TestUserProfileService:
    """测试用户画像服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return UserProfileService()

    @pytest.fixture
    def sample_user(self):
        """创建测试用户"""
        return User(
            id="test_user_1",
            username="testuser",
            email="test@example.com",
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """测试服务初始化"""
        result = await service.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_service_shutdown(self, service):
        """测试服务关闭"""
        # 添加一些测试数据
        service._user_profiles["test"] = "data"
        await service.shutdown()
        assert len(service._user_profiles) == 0

    @pytest.mark.asyncio
    async def test_generate_profile(self, service, sample_user):
        """测试生成用户画像"""
        profile = await service.generate_profile(sample_user)

        assert profile.user_id == sample_user.id
        assert "文化" in profile.interests
        assert profile.preferences["language"] == "zh"
        assert sample_user.id in service._user_profiles

    @pytest.mark.asyncio
    async def test_get_profile_exists(self, service, sample_user):
        """测试获取存在的用户画像"""
        await service.generate_profile(sample_user)
        profile = await service.get_profile(sample_user.id)

        assert profile is not None
        assert profile.user_id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_profile_not_exists(self, service):
        """测试获取不存在的用户画像"""
        profile = await service.get_profile("nonexistent_user")
        assert profile is None

    @pytest.mark.asyncio
    async def test_update_profile_success(self, service, sample_user):
        """测试更新用户画像成功"""
        await service.generate_profile(sample_user)

        updates = {"interests": ["新兴趣"]}
        updated_profile = await service.update_profile(sample_user.id, updates)

        assert updated_profile is not None
        assert updated_profile.interests == ["新兴趣"]

    @pytest.mark.asyncio
    async def test_update_profile_not_exists(self, service):
        """测试更新不存在的用户画像"""
        updates = {"interests": ["新兴趣"]}
        result = await service.update_profile("nonexistent_user", updates)
        assert result is None


class TestDataProcessingService:
    """测试数据处理服务"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DataProcessingService()

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """测试服务初始化"""
        result = await service.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_service_shutdown(self, service):
        """测试服务关闭"""
        await service.shutdown()
        # 数据处理服务关闭时没有特殊逻辑，只要不抛异常即可

    @pytest.mark.asyncio
    async def test_process_text(self, service):
        """测试文本处理"""
        test_text = "  这是一个测试文本  "
        result = await service.process_text(test_text)

        assert "processed_text" in result
        assert result["processed_text"] == "这是一个测试文本"
        assert result["word_count"] == 1
        assert result["character_count"] == len(test_text)

    @pytest.mark.asyncio
    async def test_process_batch(self, service):
        """测试批量处理"""
        data_list = [
            "文本1",
            "文本2",
            123,  # 非字符串数据应该被跳过
        ]

        results = await service.process_batch(data_list)
        assert len(results) == 2  # 只处理了两个字符串
        assert all("processed_text" in r for r in results)


class TestServiceManager:
    """测试服务管理器"""

    @pytest.fixture
    def manager(self):
        """创建服务管理器实例"""
        return ServiceManager()

    @pytest.fixture
    def test_service(self):
        """创建测试服务"""

        class TestService(BaseService):
            def __init__(self):
                super().__init__("TestService")
                self.initialized = False

            async def initialize(self) -> bool:
                self.initialized = True
                return True

            async def shutdown(self) -> None:
                self.initialized = False

        return TestService()

    def test_register_service(self, manager, test_service):
        """测试注册服务"""
        manager.register_service(test_service)
        assert "TestService" in manager.services
        assert manager.services["TestService"] == test_service

    @pytest.mark.asyncio
    async def test_initialize_all_success(self, manager, test_service):
        """测试初始化所有服务成功"""
        manager.register_service(test_service)
        result = await manager.initialize_all()

        assert result is True
        assert test_service.initialized is True

    @pytest.mark.asyncio
    async def test_initialize_all_failure(self, manager):
        """测试初始化服务失败"""

        class FailingService(BaseService):
            async def initialize(self) -> bool:
                return False  # 初始化失败

            async def shutdown(self) -> None:
                pass

        failing_service = FailingService("FailingService")
        manager.register_service(failing_service)

        result = await manager.initialize_all()
        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_all_exception(self, manager):
        """测试初始化服务异常"""

        class ExceptionService(BaseService):
            async def initialize(self) -> bool:
                raise Exception("初始化异常")

            async def shutdown(self) -> None:
                pass

        exception_service = ExceptionService("ExceptionService")
        manager.register_service(exception_service)

        result = await manager.initialize_all()
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_all(self, manager, test_service):
        """测试关闭所有服务"""
        manager.register_service(test_service)
        await manager.initialize_all()
        await manager.shutdown_all()

        assert test_service.initialized is False

    @pytest.mark.asyncio
    async def test_shutdown_all_with_exception(self, manager):
        """测试关闭服务时发生异常"""

        class ExceptionService(BaseService):
            async def initialize(self) -> bool:
                return True

            async def shutdown(self) -> None:
                raise Exception("关闭异常")

        exception_service = ExceptionService("ExceptionService")
        manager.register_service(exception_service)

        # 应该不抛出异常，即使某个服务关闭失败
        await manager.shutdown_all()

    def test_get_service_exists(self, manager, test_service):
        """测试获取存在的服务"""
        manager.register_service(test_service)
        service = manager.get_service("TestService")
        assert service == test_service

    def test_get_service_not_exists(self, manager):
        """测试获取不存在的服务"""
        service = manager.get_service("NonExistentService")
        assert service is None


class TestGlobalServiceManager:
    """测试全局服务管理器"""

    def test_global_service_manager_exists(self):
        """测试全局服务管理器存在"""
        assert service_manager is not None
        assert isinstance(service_manager, ServiceManager)

    def test_default_services_registered(self):
        """测试默认服务已注册"""
        expected_services = [
            "ContentAnalysisService",
            "UserProfileService",
            "DataProcessingService",
        ]

        for service_name in expected_services:
            assert service_name in service_manager.services
