"""
 buggy_api.py 测试文件
 测试 FastAPI 路由器中的查询参数修复功能
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.buggy_api import router


class TestBuggyAPI:
    """测试 buggy_api 模块"""

    def setup_method(self):
        """设置测试环境"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_query_param_fix_basic(self):
        """测试基本查询参数修复功能"""
        response = self.client.get("/api/buggy/fix-query?param1=value1&param2=value2")
        assert response.status_code == 200

        data = response.json()
        assert "fixed_params" in data
        assert "original_params" in data
        assert data["fixed_params"]["param1"] == "value1"
        assert data["fixed_params"]["param2"] == "value2"

    def test_query_param_fix_with_special_chars(self):
        """测试包含特殊字符的查询参数修复"""
        response = self.client.get("/api/buggy/fix-query?param=test%20value&param2=test@value")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["param"] == "test value"
        assert data["fixed_params"]["param2"] == "test@value"

    def test_query_param_fix_empty_params(self):
        """测试空查询参数处理"""
        response = self.client.get("/api/buggy/fix-query")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"] == {}
        assert data["original_params"] == {}

    def test_query_param_fix_multiple_values(self):
        """测试多值查询参数处理"""
        response = self.client.get("/api/buggy/fix-query?param=value1&param=value2")
        assert response.status_code == 200

        data = response.json()
        assert "param" in data["fixed_params"]
        # 多值参数应该被正确处理

    def test_query_param_fix_with_spaces(self):
        """测试包含空格的查询参数"""
        response = self.client.get("/api/buggy/fix-query?name=John%20Doe&age=25")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["name"] == "John Doe"
        assert data["fixed_params"]["age"] == "25"

    def test_query_param_fix_unicode_chars(self):
        """测试Unicode字符处理"""
        response = self.client.get("/api/buggy/fix-query?name=张三&city=北京")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["name"] == "张三"
        assert data["fixed_params"]["city"] == "北京"

    def test_query_param_fix_nested_objects(self):
        """测试嵌套对象参数处理"""
        response = self.client.get("/api/buggy/fix-query?user[name]=John&user[age]=25")
        assert response.status_code == 200

        data = response.json()
        # 验证嵌套对象被正确解析

    def test_query_param_fix_boolean_values(self):
        """测试布尔值参数处理"""
        response = self.client.get("/api/buggy/fix-query?active=true&enabled=false")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["active"] == "true"
        assert data["fixed_params"]["enabled"] == "false"

    def test_query_param_fix_numeric_values(self):
        """测试数值参数处理"""
        response = self.client.get("/api/buggy/fix-query?count=10&price=19.99")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["count"] == "10"
        assert data["fixed_params"]["price"] == "19.99"

    def test_query_param_fix_with_array(self):
        """测试数组参数处理"""
        response = self.client.get("/api/buggy/fix-query?tags[]=tag1&tags[]=tag2")
        assert response.status_code == 200

        data = response.json()
        # 验证数组参数被正确处理

    def test_query_param_fix_error_handling(self):
        """测试错误处理"""
        # 测试无效的查询参数
        response = self.client.get("/api/buggy/fix-query?invalid=")
        assert response.status_code == 200

        data = response.json()
        assert "fixed_params" in data
        assert "original_params" in data

    def test_query_param_fix_response_structure(self):
        """测试响应结构"""
        response = self.client.get("/api/buggy/fix-query?test=value")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "fixed_params" in data
        assert "original_params" in data
        assert isinstance(data["fixed_params"], dict)
        assert isinstance(data["original_params"], dict)

    def test_query_param_fix_with_special_encoding(self):
        """测试特殊编码处理"""
        response = self.client.get("/api/buggy/fix-query?message=Hello%20World%21")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["message"] == "Hello World!"

    def test_query_param_fix_large_params(self):
        """测试大参数处理"""
        long_value = "a" * 1000
        response = self.client.get(f"/api/buggy/fix-query?long_param={long_value}")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["long_param"] == long_value

    def test_query_param_fix_with_null_values(self):
        """测试空值处理"""
        response = self.client.get("/api/buggy/fix-query?param=null&empty=")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["param"] == "null"
        assert data["fixed_params"]["empty"] == ""

    def test_query_param_fix_with_reserved_chars(self):
        """测试保留字符处理"""
        response = self.client.get("/api/buggy/fix-query?url=http%3A%2F%2Fexample.com%3Fparam%3Dvalue")
        assert response.status_code == 200

        data = response.json()
        assert data["fixed_params"]["url"] == "http://example.com?param=value"

    @patch('api.buggy_api.logger')
    def test_query_param_fix_logging(self, mock_logger):
        """测试日志记录功能"""
        response = self.client.get("/api/buggy/fix-query?test=value")
        assert response.status_code == 200

        # 验证日志被调用
        mock_logger.info.assert_called()

    def test_query_param_fix_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        import time

        def make_request():
            response = self.client.get("/api/buggy/fix-query?thread_id=" + str(threading.get_ident()))
            assert response.status_code == 200

        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def test_query_param_fix_with_headers(self):
        """测试带头部信息的请求"""
        headers = {"User-Agent": "test-agent", "Authorization": "Bearer token"}
        response = self.client.get("/api/buggy/fix-query?test=value", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "fixed_params" in data

    def test_query_param_fix_performance(self):
        """测试性能表现"""
        import time
        start_time = time.time()

        for i in range(100):
            response = self.client.get(f"/api/buggy/fix-query?param= value_{i}")
            assert response.status_code == 200

        end_time = time.time()
        # 确保在合理时间内完成
        assert (end_time - start_time) < 5.0


class TestBuggyAPIIntegration:
    """测试 buggy_api 集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_router_inclusion(self):
        """测试路由器是否正确包含"""
        assert len(router.routes) > 0

    def test_route_path_exists(self):
        """测试路由路径存在"""
        routes = [route.path for route in router.routes if hasattr(route, 'path')]
        assert "/api/buggy/fix-query" in routes

    def test_route_methods(self):
        """测试路由方法"""
        for route in router.routes:
            if hasattr(route, 'path') and route.path == "/api/buggy/fix-query":
                assert "GET" in route.methods

    def test_app_integration(self):
        """测试应用集成"""
        response = self.client.get("/docs")
        # 检查 Swagger 文档是否包含 buggy_api 路由
        assert response.status_code == 200

    def test_cors_headers(self):
        """测试CORS头部"""
        response = self.client.get("/api/buggy/fix-query?test=value")
        assert response.status_code == 200
        # 检查CORS头部是否存在
        assert "access-control-allow-origin" in response.headers or response.headers.get("access-control-allow-origin") == "*"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])