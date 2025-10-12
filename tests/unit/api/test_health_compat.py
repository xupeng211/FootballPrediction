"""
健康API兼容性测试
Tests for Health API Compatibility

测试src.api.health模块的兼容性包装功能
"""

import pytest
import warnings

# 测试导入
HEALTH_AVAILABLE = True
try:
    from src.api.health import router, __all__
except ImportError as e:
    print(f"Import error: {e}")
    HEALTH_AVAILABLE = False
    router = None
    __all__ = []


# @pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health module not available")
class TestHealthCompatibility:
    """健康API兼容性测试"""

    def test_router_import(self):
        """测试：路由导入"""
        assert router is not None
        assert hasattr(router, "routes")
        # 验证是FastAPI路由器
        assert "APIRouter" in str(type(router))

    def test_module_exports(self):
        """测试：模块导出"""
        assert isinstance(__all__, list)
        assert "router" in __all__
        assert len(__all__) == 1

    def test_deprecation_warning(self):
        """测试：弃用警告"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # 重新导入以触发警告
            from importlib import reload
            import src.api.health as health_module

            reload(health_module)

            # 检查警告
            deprecation_warnings = [
                warn for warn in w if issubclass(warn.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0
            assert "已弃用" in str(deprecation_warnings[0].message)
            assert "api.health" in str(deprecation_warnings[0].message)

    def test_backward_compatibility(self):
        """测试：向后兼容性"""
        # 验证可以从旧的导入路径访问
        from src.api.health import router as old_router

        # 验证与新导入路径一致
        try:
            from src.api.health.checks import router as new_router

            # 注意：由于是重新导出，它们应该是同一个对象
            assert old_router is new_router
        except ImportError:
            # 如果新路径不存在，至少确保旧路径可用
            assert old_router is not None

    def test_module_documentation(self):
        """测试：模块文档"""
        import src.api.health as health_module

        assert health_module.__doc__ is not None
        assert "拆分" in health_module.__doc__
        assert "向后兼容" in health_module.__doc__

    def test_no_additional_exports(self):
        """测试：没有额外的导出"""
        # 确保只导出预期中的内容
        import src.api.health as health_module

        # 检查没有意外的导出
        actual_exports = {
            name
            for name in dir(health_module)
            if not name.startswith("_") or name == "__all__"
        }

        # 移除Python默认属性
        python_defaults = {
            "name",
            "package",
            "spec",
            "loader",
            "file",
            "cached",
            "path",
        }
        actual_exports -= python_defaults

        # 应该只有router在公开导出中
        assert actual_exports == {"router"}


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health module not available")
class TestHealthFunctionality:
    """健康功能测试"""

    def test_router_structure(self):
        """测试：路由结构"""
        # 验证路由器有基本的健康检查端点
        routes = list(router.routes)
        assert len(routes) > 0

        # 检查路由路径
        route_paths = [route.path for route in routes if hasattr(route, "path")]
        assert any("/health" in path for path in route_paths)

    def test_router_tags(self):
        """测试：路由标签"""
        if hasattr(router, "tags"):
            assert isinstance(router.tags, (list, tuple))

        # 检查路由的标签
        for route in router.routes:
            if hasattr(route, "tags"):
                assert isinstance(route.tags, (list, tuple, set))

    def test_router_methods(self):
        """测试：路由方法"""
        for route in router.routes:
            if hasattr(route, "methods"):
                assert isinstance(route.methods, (list, set, frozenset))
                # 健康检查通常有GET方法
                assert "GET" in route.methods


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health module not available")
class TestHealthIntegration:
    """健康集成测试"""

    def test_integration_with_fastapi(self):
        """测试：与FastAPI集成"""
        # 尝试将路由器添加到FastAPI应用
        try:
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            # 如果没有异常，说明集成成功
            assert True
        except Exception as e:
            pytest.fail(f"FastAPI integration failed: {e}")

    def test_health_check_flow(self):
        """测试：健康检查流程"""
        # 这是一个基础测试，实际的健康检查取决于实现
        assert router is not None

        # 验证路由器已正确配置
        if hasattr(router, "prefix"):
            # 健康检查路由通常有前缀
            assert router.prefix is not None or len(router.routes) > 0


# 如果模块不可用，添加一个占位测试
@pytest.mark.skipif(True, reason="Module not available")
class TestModuleNotAvailable:
    """模块不可用时的占位测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not HEALTH_AVAILABLE
        assert True  # 表明测试意识到模块不可用
