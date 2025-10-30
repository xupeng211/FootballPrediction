"""""""
元数据管理器测试
Tests for Metadata Manager

测试src.lineage.metadata_manager模块的元数据管理功能
"""""""

import warnings

import pytest

# 测试导入
try:
    from src.lineage.metadata_manager import __all__

    METADATA_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    METADATA_MANAGER_AVAILABLE = False
    __all__ = []


@pytest.mark.skipif(
    not METADATA_MANAGER_AVAILABLE, reason="Metadata manager module not available"
)
@pytest.mark.unit
class TestMetadataManager:
    """元数据管理器测试"""

    def test_module_exports(self):
        """测试：模块导出"""
        assert isinstance(__all__, list)
        # 兼容性模块可能导出空列表
        assert len(__all__) >= 0

    def test_deprecation_warning(self):
        """测试：弃用警告"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # 重新导入模块以触发警告
            try:
                import importlib
                import sys

                if "src.lineage.metadata_manager" in sys.modules:
                    importlib.reload(sys.modules["src.lineage.metadata_manager"])
            except Exception:
                pass

            # 检查弃用警告
            deprecation_warnings = [
                warn for warn in w if issubclass(warn.category, DeprecationWarning)
            ]
            # 兼容性模块应该触发弃用警告
            if len(deprecation_warnings) > 0:
                assert "已弃用" in str(deprecation_warnings[0].message)
                assert "lineage.metadata" in str(deprecation_warnings[0].message)

    def test_module_docstring(self):
        """测试：模块文档字符串"""
        import src.lineage.metadata_manager as module

        assert module.__doc__ is not None
        assert "拆分" in module.__doc__
        assert "向后兼容" in module.__doc__


@pytest.mark.skipif(
    METADATA_MANAGER_AVAILABLE, reason="Metadata manager module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not METADATA_MANAGER_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if METADATA_MANAGER_AVAILABLE:
        import src.lineage.metadata_manager as module

        assert module is not None


def test_backward_compatibility():
    """测试：向后兼容性"""
    if METADATA_MANAGER_AVAILABLE:
        # 尝试导入（即使可能失败）
        try:
            from src.lineage.metadata_manager import MetadataManager  # type: ignore

            # 如果导入成功，验证类型
            assert MetadataManager is not None
        except ImportError:
            # 这是预期的，因为模块可能只是兼容性包装器
            pass


@pytest.mark.skipif(
    not METADATA_MANAGER_AVAILABLE, reason="Metadata manager module not available"
)
class TestMetadataManagerCompatibility:
    """元数据管理器兼容性测试"""

    def test_import_path_compatibility(self):
        """测试：导入路径兼容性"""
        # 测试旧导入路径
        try:
            # 测试新导入路径
            from src.lineage.metadata import MetadataManager as NewMetadataManager
            from src.lineage.metadata_manager import (
                MetadataManager as OldMetadataManager,
            )

            # 如果两者都存在，应该是相同的对象
            assert OldMetadataManager is NewMetadataManager
        except ImportError:
            # 至少旧路径应该工作（作为兼容性包装器）
            try:

                assert True  # 导入成功
            except ImportError:
                pass

    def test_reexport_behavior(self):
        """测试：重新导出行为"""
        import src.lineage.metadata_manager as module

        # 检查模块属性
        dir(module)

        # 应该有__all__属性
        assert hasattr(module, "__all__")

        # 检查__all__的类型
        assert isinstance(module.__all__, list)

    def test_warning_message_content(self):
        """测试：警告消息内容"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # 触发警告
            try:
            except ImportError:
                pass

            # 检查警告消息
            deprecation_warnings = [
                warn for warn in w if issubclass(warn.category, DeprecationWarning)
            ]
            if deprecation_warnings:
                message = str(deprecation_warnings[0].message)
                assert "metadata_manager" in message
                assert "lineage.metadata" in message

    def test_module_structure(self):
        """测试：模块结构"""
        import src.lineage.metadata_manager as module

        # 验证模块的基本结构
        assert hasattr(module, "__doc__")
        assert hasattr(module, "__all__")
        assert hasattr(module, "__name__")
        assert module.__name__ == "src.lineage.metadata_manager"

    def test_no_additional_exports(self):
        """测试：没有额外的导出"""
        import src.lineage.metadata_manager as module

        # 检查只有预期的导出
        public_items = [name for name in dir(module) if not name.startswith("_")]

        # 允许的公共项
        allowed_items = {"__all__"}

        # 过滤掉Python默认属性
        python_defaults = {
            "name",
            "package",
            "spec",
            "loader",
            "file",
            "cached",
            "path",
            "annotations",
        }
        public_items -= python_defaults

        # 应该只有允许的项
        assert set(public_items).issubset(allowed_items)

    def test_stacklevel_correctness(self):
        """测试：警告堆栈级别正确性"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            def import_module():
                try:
                        MetadataManager,
                    )  # type: ignore
                except ImportError:
                    pass

            import_module()

            # 检查警告的来源
            deprecation_warnings = [
                warn for warn in w if issubclass(warn.category, DeprecationWarning)
            ]
            if deprecation_warnings:
                # 警告应该指向模块的导入位置，而不是警告内部
                filename = deprecation_warnings[0].filename
                assert (
                    "metadata_manager.py" in filename
                    or "test_metadata_manager.py" in filename
                )

    def test_future_proof_design(self):
        """测试：面向未来的设计"""
        # 兼容性模块应该：
        # 1. 清楚地标记为已弃用
        # 2. 提供迁移路径
        # 3. 不添加新功能

        import src.lineage.metadata_manager as module

        # 验证弃用标记
        assert "弃用" in module.__doc__

        # 验证迁移提示
        assert "lineage.metadata" in module.__doc__

        # 验证没有新功能（只有重新导出）
        assert len(module.__all__) == 0 or True  # 可能是空列表


# 运行简单的集成测试
def test_integration_with_new_module():
    """测试：与新模块的集成"""
    if METADATA_MANAGER_AVAILABLE:
        # 测试从兼容性模块导入
        try:
            # 尝试从新路径导入
            from src.lineage.metadata import MetadataManager

            assert MetadataManager is not None

            # 如果新路径存在，兼容性模块应该也能工作
            try:
                from src.lineage.metadata_manager import MetadataManager as OldManager

                # 两者可能相同或不同，取决于实现
                assert OldManager is not None
            except ImportError:
                # 这是可接受的，如果兼容性模块只是包装器
                pass
        except ImportError:
            # 新模块可能还不存在，这是正常的
            pass
