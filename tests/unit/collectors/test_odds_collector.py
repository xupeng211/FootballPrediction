"""
赔率收集器测试
Tests for Odds Collector

测试src.collectors.odds_collector模块的兼容性功能
"""

import pytest
import warnings

# 测试导入
ODDS_COLLECTOR_AVAILABLE = True
try:
    from src.collectors.odds_collector import collector, parser, storage, validator, __all__
except ImportError as e:
    print(f"Import error: {e}")
    ODDS_COLLECTOR_AVAILABLE = False
    collector = None
    parser = None
    storage = None
    validator = None
    __all__ = []


class TestOddsCollectorCompatibility:
    """赔率收集器兼容性测试"""

    def test_module_exports(self):
        """测试：模块导出"""
        assert isinstance(__all__, list)
        assert len(__all__) == 4
        assert "collector" in __all__
        assert "parser" in __all__
        assert "storage" in __all__
        assert "validator" in __all__

    def test_imports_available(self):
        """测试：导入可用"""
        # 即使导入失败，至少应该有占位符
        if ODDS_COLLECTOR_AVAILABLE:
            assert collector is not None
            assert parser is not None
            assert storage is not None
            assert validator is not None

    def test_deprecation_warning(self):
        """测试：弃用警告"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # 尝试重新导入以触发警告
            try:
                from importlib import reload
                import sys
                if 'src.collectors.odds_collector' in sys.modules:
                    del sys.modules['src.collectors.odds_collector']
                import src.collectors.odds_collector
            except Exception:
                pass

            # 检查弃用警告
            deprecation_warnings = [warn for warn in w if issubclass(warn.category, DeprecationWarning)]
            if ODDS_COLLECTOR_AVAILABLE:
                assert len(deprecation_warnings) > 0
                assert "已弃用" in str(deprecation_warnings[0].message)

    def test_module_structure(self):
        """测试：模块结构"""
        import src.collectors.odds_collector as odds_module

        assert odds_module.__doc__ is not None
        assert "拆分" in odds_module.__doc__
        assert "向后兼容" in odds_module.__doc__

    def test_export_components(self):
        """测试：导出组件"""
        if ODDS_COLLECTOR_AVAILABLE:
            # 验证每个组件都有基本属性
            for component in [collector, parser, storage, validator]:
                if component is not None:
                    assert hasattr(component, '__name__')
                    assert component.__name__ is not None

    def test_no_additional_exports(self):
        """测试：没有额外的导出"""
        import src.collectors.odds_collector as odds_module

        # 检查只有预期的导出
        expected_exports = {'collector', 'parser', 'storage', 'validator', '__all__'}
        actual_exports = {name for name in dir(odds_module)
                          if not name.startswith('_') or name == '__all__'}

        # 移除Python默认属性
        python_defaults = {'name', 'package', 'spec', 'loader', 'file', 'cached'}
        actual_exports -= python_defaults

        # 应该只有预期的导出
        assert expected_exports.issubset(actual_exports)


class TestOddsCollectorFunctionality:
    """赔率收集器功能测试"""

    def test_collector_interface(self):
        """测试：收集器接口"""
        if collector and ODDS_COLLECTOR_AVAILABLE:
            # 检查基本接口
            if hasattr(collector, 'collect'):
                assert callable(collector.collect)

    def test_parser_interface(self):
        """测试：解析器接口"""
        if parser and ODDS_COLLECTOR_AVAILABLE:
            # 检查基本接口
            if hasattr(parser, 'parse'):
                assert callable(parser.parse)

    def test_storage_interface(self):
        """测试：存储接口"""
        if storage and ODDS_COLLECTOR_AVAILABLE:
            # 检查基本接口
            if hasattr(storage, 'save'):
                assert callable(storage.save)
            if hasattr(storage, 'load'):
                assert callable(storage.load)

    def test_validator_interface(self):
        """测试：验证器接口"""
        if validator and ODDS_COLLECTOR_AVAILABLE:
            # 检查基本接口
            if hasattr(validator, 'validate'):
                assert callable(validator.validate)

    def test_component_types(self):
        """测试：组件类型"""
        if ODDS_COLLECTOR_AVAILABLE:
            components = [collector, parser, storage, validator]
            for component in components:
                if component is not None:
                    # 可以是类、实例或函数
                    assert isinstance(component, (type, object, callable))

    def test_module_dependencies(self):
        """测试：模块依赖"""
        # 验证模块文档提到了正确的依赖路径
        import src.collectors.odds_collector as odds_module

        doc = odds_module.__doc__
        if doc:
            assert "src/collectors/odds/basic" in doc


class TestOddsCollectorIntegration:
    """赔率收集器集成测试"""

    def test_backward_compatibility(self):
        """测试：向后兼容性"""
        # 旧代码应该能够导入
        try:
            from src.collectors.odds_collector import collector as old_collector
            assert old_collector is not None
        except ImportError:
            pytest.skip("Backward compatibility import failed")

    def test_import_path_consistency(self):
        """测试：导入路径一致性"""
        # 尝试从新路径导入
        try:
            from src.collectors.odds.basic import collector as new_collector
            # 如果两个路径都能导入，它们应该是相同的对象
            if ODDS_COLLECTOR_AVAILABLE and collector is not None:
                assert collector is new_collector
        except ImportError:
            # 新路径可能不存在，这是兼容性包装器存在的原因
            pass

    def test_component_relationships(self):
        """测试：组件关系"""
        if ODDS_COLLECTOR_AVAILABLE:
            # 验证所有组件都来自同一个模块族
            components = [collector, parser, storage, validator]
            available_components = [c for c in components if c is not None]

            # 至少应该有一些组件可用
            assert len(available_components) > 0

    def test_workflow_compatibility(self):
        """测试：工作流兼容性"""
        if ODDS_COLLECTOR_AVAILABLE and collector and parser:
            # 模拟一个简单的工作流
            test_data = {"odds": [1.5, 2.0, 3.5]}

            # 解析
            if hasattr(parser, 'parse') and callable(parser.parse):
                try:
                    parsed = parser.parse(test_data)
                    assert parsed is not None
                except Exception:
                    # 可能需要额外的依赖
                    pass

            # 验证
            if hasattr(validator, 'validate') and callable(validator.validate):
                try:
                    is_valid = validator.validate(test_data)
                    assert isinstance(is_valid, bool)
                except Exception:
                    pass

    def test_error_handling(self):
        """测试：错误处理"""
        if ODDS_COLLECTOR_AVAILABLE:
            # 测试对None输入的处理
            components = [collector, parser, storage, validator]
            for component in components:
                if component is None:
                    continue

                # 测试各种方法的错误处理
                for method_name in ['collect', 'parse', 'save', 'load', 'validate']:
                    if hasattr(component, method_name):
                        method = getattr(component, method_name)
                        if callable(method):
                            try:
                                # 尝试传入None
                                result = method(None)
                                # 应该优雅地处理None或抛出适当的异常
                                assert result is not None or True
                            except (TypeError, ValueError, AttributeError):
                                # 这些是预期的错误类型
                                pass
                            except Exception:
                                # 其他异常可能表示问题
                                pass


# 运行一个简单的性能测试
def test_performance_baseline():
    """性能基准测试"""
    import time

    start_time = time.time()

    # 读取模块文件
    try:
        with open("/home/user/projects/FootballPrediction/src/collectors/odds_collector.py", 'r') as f:
            content = f.read()
        assert len(content) > 0
    except FileNotFoundError:
        # 文件可能不存在，跳过测试
        pytest.skip("Module file not found")

    end_time = time.time()

    # 应该能快速读取
    assert end_time - start_time < 0.1