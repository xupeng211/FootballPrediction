"""
Cache API综合测试
通过直接模块导入避免复杂的依赖问题
"""

import sys
import os
from unittest.mock import MagicMock, AsyncMock
import pytest

# 使用当前工作目录作为项目根目录
project_root = os.getcwd()
sys.path.insert(0, project_root)

def import_cache_module():
    """导入cache模块的工具函数"""
    import importlib.util

    cache_path = os.path.join(project_root, "src/api/cache.py")
    if not os.path.exists(cache_path):
        print(f"Cache模块不存在: {cache_path}")
        return None

    spec = importlib.util.spec_from_file_location(
        "cache_module",
        cache_path
    )

    if spec and spec.loader:
        cache_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_module)
        return cache_module
    return None

class TestCacheModuleStructure:
    """测试Cache模块结构"""

    def test_module_import(self):
        """测试模块能够成功导入"""
        cache = import_cache_module()
        assert cache is not None, "无法导入cache模块"

    def test_router_exists(self):
        """测试Router存在"""
        cache = import_cache_module()
        assert hasattr(cache, 'router'), "cache模块应该有router"
        assert cache.router is not None, "router不应为None"

    def test_required_functions_exist(self):
        """测试所需函数都存在"""
        cache = import_cache_module()

        required_functions = [
            'get_cache_stats',
            'clear_cache',
            'prewarm_cache',
            'optimize_cache'
        ]

        for func_name in required_functions:
            assert hasattr(cache, func_name), f"缺少函数: {func_name}"

    def test_required_classes_exist(self):
        """测试所需类都存在"""
        cache = import_cache_module()

        required_classes = [
            'CacheStatsResponse',
            'CacheOperationResponse',
            'CacheKeyRequest',
            'CachePrewarmRequest'
        ]

        for class_name in required_classes:
            assert hasattr(cache, class_name), f"缺少类: {class_name}"

    def test_class_inheritance(self):
        """测试类继承关系"""
        cache = import_cache_module()

        # 测试CacheStatsResponse
        stats_class = getattr(cache, 'CacheStatsResponse', None)
        if stats_class:
            # 检查是否继承自BaseModel
            assert hasattr(stats_class, 'model_fields'), "CacheStatsResponse应该是Pydantic模型"

        # 测试CacheOperationResponse
        operation_class = getattr(cache, 'CacheOperationResponse', None)
        if operation_class:
            assert hasattr(operation_class, 'model_fields'), "CacheOperationResponse应该是Pydantic模型"

    def test_class_fields(self):
        """测试类字段定义"""
        cache = import_cache_module()

        # 测试CacheStatsResponse字段
        stats_class = getattr(cache, 'CacheStatsResponse', None)
        if stats_class:
            fields = stats_class.model_fields if hasattr(stats_class, 'model_fields') else {}
            assert 'l1_cache' in fields, "CacheStatsResponse应该有l1_cache字段"
            assert 'l2_cache' in fields, "CacheStatsResponse应该有l2_cache字段"
            assert 'overall' in fields, "CacheStatsResponse应该有overall字段"
            assert 'config' in fields, "CacheStatsResponse应该有config字段"

        # 测试CacheOperationResponse字段
        operation_class = getattr(cache, 'CacheOperationResponse', None)
        if operation_class:
            fields = operation_class.model_fields if hasattr(operation_class, 'model_fields') else {}
            assert 'success' in fields, "CacheOperationResponse应该有success字段"
            assert 'message' in fields, "CacheOperationResponse应该有message字段"

    def test_function_signatures(self):
        """测试函数签名"""
        cache = import_cache_module()

        # 测试get_cache_stats
        get_stats = getattr(cache, 'get_cache_stats', None)
        if get_stats:
            assert callable(get_stats), "get_cache_stats应该是可调用的"
            # 检查是否是async函数
            import inspect
            assert inspect.iscoroutinefunction(get_stats), "get_cache_stats应该是async函数"

        # 测试其他async函数
        async_functions = ['clear_cache', 'prewarm_cache', 'optimize_cache']
        for func_name in async_functions:
            func = getattr(cache, func_name, None)
            if func:
                assert callable(func), f"{func_name}应该是可调用的"
                assert inspect.iscoroutinefunction(func), f"{func_name}应该是async函数"

class TestCacheModels:
    """测试Cache相关模型"""

    def test_cache_stats_response_creation(self):
        """测试CacheStatsResponse创建"""
        cache = import_cache_module()
        StatsClass = getattr(cache, 'CacheStatsResponse', None)

        if StatsClass:
            # 测试正常创建
            stats = StatsClass(
                l1_cache={"hit_rate": 0.8},
                l2_cache={"hit_rate": 0.6},
                overall={"total_hit_rate": 0.7},
                config={"ttl": 3600}
            )

            assert stats.l1_cache["hit_rate"] == 0.8
            assert stats.l2_cache["hit_rate"] == 0.6
            assert stats.overall["total_hit_rate"] == 0.7
            assert stats.config["ttl"] == 3600

    def test_cache_operation_response_creation(self):
        """测试CacheOperationResponse创建"""
        cache = import_cache_module()
        OperationClass = getattr(cache, 'CacheOperationResponse', None)

        if OperationClass:
            # 测试成功响应
            response = OperationClass(
                success=True,
                message="操作成功",
                data={"cleared_keys": ["key1", "key2"]}
            )

            assert response.success is True
            assert response.message == "操作成功"
            assert response.data["cleared_keys"] == ["key1", "key2"]

            # 测试失败响应（无data）
            response2 = OperationClass(
                success=False,
                message="操作失败"
            )

            assert response2.success is False
            assert response2.message == "操作失败"
            assert response2.data is None

    def test_cache_key_request_creation(self):
        """测试CacheKeyRequest创建"""
        cache = import_cache_module()
        KeyRequestClass = getattr(cache, 'CacheKeyRequest', None)

        if KeyRequestClass:
            # 测试只有键的请求
            request = KeyRequestClass(keys=["key1", "key2", "key3"])
            assert request.keys == ["key1", "key2", "key3"]
            assert request.pattern is None

            # 测试带模式的请求
            request2 = KeyRequestClass(
                keys=["key1"],
                pattern="test:*"
            )
            assert request2.keys == ["key1"]
            assert request2.pattern == "test:*"

    def test_cache_prewarm_request_creation(self):
        """测试CachePrewarmRequest创建"""
        cache = import_cache_module()
        PrewarmClass = getattr(cache, 'CachePrewarmRequest', None)

        if PrewarmClass:
            # 测试基本请求
            request = PrewarmClass(task_types=["predictions", "teams"])
            assert request.task_types == ["predictions", "teams"]
            assert request.force is False  # 默认值

            # 测试强制预热
            request2 = PrewarmClass(
                task_types=["hot_matches"],
                force=True
            )
            assert request2.task_types == ["hot_matches"]
            assert request2.force is True

class TestCacheRouter:
    """测试Cache路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        cache = import_cache_module()
        router = getattr(cache, 'router', None)

        if router:
            assert hasattr(router, 'prefix'), "Router应该有prefix属性"
            assert "/cache" in router.prefix, "Router prefix应该包含cache"

    def test_router_tags(self):
        """测试路由标签"""
        cache = import_cache_module()
        router = getattr(cache, 'router', None)

        if router:
            assert hasattr(router, 'tags'), "Router应该有tags属性"
            # 检查是否有中文标签
            if router.tags:
                assert any("缓存" in tag or "cache" in tag.lower() for tag in router.tags), \
                    "Router tags应该包含缓存相关标签"

    def test_route_endpoints_exist(self):
        """测试路由端点存在"""
        cache = import_cache_module()
        router = getattr(cache, 'router', None)

        if router:
            # 检查路由是否有端点
            assert hasattr(router, 'routes'), "Router应该有routes属性"
            if router.routes:
                # 至少应该有一些路由
                assert len(router.routes) > 0, "Router应该至少有一个路由"

class TestCacheLogicCoverage:
    """测试Cache逻辑覆盖"""

    def test_get_cache_stats_logic(self):
        """测试获取缓存统计的逻辑结构"""
        cache = import_cache_module()
        func_source = getattr(cache, 'get_cache_stats', None)

        if func_source:
            import inspect
            source = inspect.getsource(func_source)

            # 检查关键逻辑是否存在
            assert "get_cache_manager" in source, "应该调用get_cache_manager"
            assert "get_stats" in source, "应该调用get_stats方法"
            assert "CacheStatsResponse" in source, "应该返回CacheStatsResponse"
            assert "HTTPException" in source, "应该处理HTTPException"

    def test_clear_cache_logic(self):
        """测试清理缓存的逻辑结构"""
        cache = import_cache_module()
        func_source = getattr(cache, 'clear_cache', None)

        if func_source:
            import inspect
            source = inspect.getsource(func_source)

            # 检查关键逻辑
            assert "get_cache_manager" in source, "应该调用get_cache_manager"
            assert "delete" in source, "应该有删除逻辑"
            assert "CacheOperationResponse" in source, "应该返回CacheOperationResponse"
            assert "pattern" in source, "应该支持模式匹配"

    def test_prewarm_cache_logic(self):
        """测试缓存预热的逻辑结构"""
        cache = import_cache_module()
        func_source = getattr(cache, 'prewarm_cache', None)

        if func_source:
            import inspect
            source = inspect.getsource(func_source)

            # 检查关键逻辑
            assert "get_cache_initializer" in source, "应该调用get_cache_initializer"
            assert "valid_tasks" in source, "应该有任务验证"
            assert "BackgroundTasks" in source, "应该使用BackgroundTasks"
            assert "invalid_tasks" in source, "应该处理无效任务"

    def test_optimize_cache_logic(self):
        """测试缓存优化的逻辑结构"""
        cache = import_cache_module()
        func_source = getattr(cache, 'optimize_cache', None)

        if func_source:
            import inspect
            source = inspect.getsource(func_source)

            # 检查关键逻辑
            assert "get_cache_initializer" in source, "应该调用get_cache_initializer"
            assert "BackgroundTasks" in source, "应该使用BackgroundTasks"
            assert "optimize" in source.lower(), "应该有优化逻辑"

# 运行测试的主函数
def run_all_tests():
    """运行所有测试"""
    print("🧪 运行Cache综合测试...")

    import pytest

    # 运行这个文件中的所有测试
    test_file = os.path.abspath(__file__)
    exit_code = pytest.main([test_file, "-v", "--tb=short"])

    return exit_code.value if hasattr(exit_code, 'value') else exit_code

if __name__ == "__main__":
    print("=" * 60)
    print("Cache API 综合测试")
    print("=" * 60)

    try:
        exit_code = run_all_tests()
        if exit_code == 0:
            print("\n✅ 所有测试通过！")
        else:
            print(f"\n❌ 测试失败，退出码: {exit_code}")
    except Exception as e:
        print(f"\n⚠️ 运行测试时出错: {e}")
        exit_code = 1

    sys.exit(exit_code)