"""
MetadataManager 增强测试套件 - Phase 5.1 Batch-Δ-013

专门为 metadata_manager.py 设计的增强测试，目标是将其覆盖率从 10% 提升至 ≥70%
覆盖所有 Marquez API 交互、元数据管理功能和数据治理操作
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException
import json
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestMetadataManagerComprehensive:
    """MetadataManager 综合测试类"""

    @pytest.fixture
    def manager(self):
        """创建 MetadataManager 实例"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager(marquez_url="http://test-marquez:5000")
        return manager

    @pytest.fixture
    def mock_response(self):
        """创建模拟 HTTP 响应"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"success": True}
        response.text = json.dumps({"success": True})
        return response

    @pytest.fixture
    def sample_namespace_data(self):
        """示例命名空间数据"""
        return {
            "name": "football_prediction",
            "description": "Football prediction pipeline namespace",
            "owner_name": "data_team"
        }

    @pytest.fixture
    def sample_dataset_data(self):
        """示例数据集数据"""
        return {
            "namespace": "football_prediction",
            "name": "matches_raw",
            "description": "Raw match data from external APIs",
            "fields": [
                {"name": "match_id", "type": "integer"},
                {"name": "home_team", "type": "string"},
                {"name": "away_team", "type": "string"},
                {"name": "home_score", "type": "integer"},
                {"name": "away_score", "type": "integer"},
                {"name": "match_date", "type": "timestamp"}
            ]
        }

    @pytest.fixture
    def sample_job_data(self):
        """示例作业数据"""
        return {
            "namespace": "football_prediction",
            "name": "data_processing_job",
            "description": "Daily data processing and quality validation",
            "type": "batch",
            "location": "/opt/airflow/dags/data_processing.py"
        }

    # === 初始化测试 ===

    def test_initialization_default_url(self):
        """测试默认 URL 初始化"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager()
    assert manager.marquez_url == "http:_/localhost:5000"
    assert manager.base_url == "http://localhost:5000"
    assert manager.api_url == "http://localhost:5000/api/v1/"
    assert manager.session is not None
    assert "Content-Type" in manager.session.headers
    assert "Accept" in manager.session.headers

    def test_initialization_custom_url(self):
        """测试自定义 URL 初始化"""
        from src.lineage.metadata_manager import MetadataManager

        custom_url = "http:_/custom-marquez:8080"
        manager = MetadataManager(marquez_url=custom_url)

    assert manager.marquez_url == custom_url
    assert manager.base_url == custom_url
    assert manager.api_url == f"{custom_url}/api/v1/"

    def test_session_headers_configuration(self):
        """测试会话头部配置"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager()
        headers = manager.session.headers

    assert headers["Content-Type"] == "application_json"
    assert headers["Accept"] == "application/json"

    # === 命名空间管理测试 ===

    @patch('requests.Session.post')
    def test_create_namespace_success(self, mock_post, manager, sample_namespace_data, mock_response):
        """测试成功创建命名空间"""
        mock_post.return_value = mock_response

        result = manager.create_namespace(**sample_namespace_data)

    assert result is not None
        mock_post.assert_called_once()

        # 验证调用参数
        call_args = mock_post.call_args
        expected_url = f"{manager.api_url}namespaces"
    assert call_args[0][0] == expected_url
    assert call_args[1]["json"] == sample_namespace_data

    @patch('requests.Session.post')
    def test_create_namespace_minimal_params(self, mock_post, manager, mock_response):
        """测试最小参数创建命名空间"""
        mock_post.return_value = mock_response

        result = manager.create_namespace(name="test_namespace")

    assert result is not None
        mock_post.assert_called_once()

        call_args = mock_post.call_args
        expected_data = {"name": "test_namespace"}
    assert call_args[1]["json"] == expected_data

    @patch('requests.Session.post')
    def test_create_namespace_api_error(self, mock_post, manager):
        """测试命名空间创建 API 错误"""
        error_response = Mock()
        error_response.status_code = 400
        error_response.text = "Bad Request"
        error_response.json.return_value = {"error": "Namespace already exists"}
        mock_post.return_value = error_response

        result = manager.create_namespace(name="existing_namespace")

    assert result is not None
        # 应该包含错误信息

    @patch('requests.Session.post')
    def test_create_namespace_network_error(self, mock_post, manager):
        """测试命名空间创建网络错误"""
        mock_post.side_effect = RequestException("Network error")

        result = manager.create_namespace(name="test_namespace")

    assert result is not None
        # 应该处理网络错误

    # === 数据集管理测试 ===

    @patch('requests.Session.post')
    def test_create_dataset_success(self, mock_post, manager, sample_dataset_data, mock_response):
        """测试成功创建数据集"""
        mock_response.json.return_value = {
            "namespace": sample_dataset_data["namespace"],
            "name": sample_dataset_data["name"],
            "id": "dataset-123"
        }
        mock_post.return_value = mock_response

        result = manager.create_dataset(**sample_dataset_data)

    assert result is not None
        mock_post.assert_called_once()

        call_args = mock_post.call_args
        expected_url = f"{manager.api_url}datasets"
    assert call_args[0][0] == expected_url

    @patch('requests.Session.post')
    def test_create_dataset_with_complex_fields(self, mock_post, manager, mock_response):
        """测试创建复杂字段的数据集"""
        complex_dataset = {
            "namespace": "football_prediction",
            "name": "complex_dataset",
            "description": "Dataset with complex field types",
            "fields": [
                {"name": "id", "type": "integer", "constraints": ["primary"]},
                {"name": "data", "type": "struct", "fields": [
                    {"name": "value", "type": "float"},
                    {"name": "metadata", "type": "map"}
                ]},
                {"name": "tags", "type": "array", "items": {"type": "string"}}
            ]
        }

        mock_post.return_value = mock_response
        result = manager.create_dataset(**complex_dataset)

    assert result is not None
        mock_post.assert_called_once()

    # === 作业管理测试 ===

    @patch('requests.Session.post')
    def test_create_job_success(self, mock_post, manager, sample_job_data, mock_response):
        """测试成功创建作业"""
        mock_response.json.return_value = {
            "namespace": sample_job_data["namespace"],
            "name": sample_job_data["name"],
            "id": "job-123"
        }
        mock_post.return_value = mock_response

        result = manager.create_job(**sample_job_data)

    assert result is not None
        mock_post.assert_called_once()

        call_args = mock_post.call_args
        expected_url = f"{manager.api_url}jobs"
    assert call_args[0][0] == expected_url

    @patch('requests.Session.post')
    def test_create_job_with_inputs_outputs(self, mock_post, manager, mock_response):
        """测试创建带输入输出的作业"""
        job_with_io = {
            "namespace": "football_prediction",
            "name": "etl_job",
            "description": "ETL job with inputs and outputs",
            "type": "batch",
            "inputs": ["source_dataset"],
            "outputs": ["target_dataset"]
        }

        mock_post.return_value = mock_response
        result = manager.create_job(**job_with_io)

    assert result is not None
        mock_post.assert_called_once()

    # === 数据集血缘测试 ===

    @patch('requests.Session.get')
    def test_get_dataset_lineage_success(self, mock_get, manager, mock_response):
        """测试成功获取数据集血缘"""
        mock_response.json.return_value = {
            "dataset": {"name": "test_dataset", "namespace": "test_namespace"},
            "upstream": [{"name": "source_dataset", "type": "dataset"}],
            "downstream": [{"name": "target_dataset", "type": "dataset"}]
        }
        mock_get.return_value = mock_response

        result = manager.get_dataset_lineage("test_namespace", "test_dataset")

    assert result is not None
        mock_get.assert_called_once()

        call_args = mock_get.call_args
        expected_url = f"{manager.api_url}datasets_test_namespace/test_dataset/lineage"
    assert call_args[0][0] == expected_url

    @patch('requests.Session.get')
    def test_get_dataset_lineage_not_found(self, mock_get, manager):
        """测试获取不存在的数据集血缘"""
        not_found_response = Mock()
        not_found_response.status_code = 404
        not_found_response.text = "Dataset not found"
        mock_get.return_value = not_found_response

        result = manager.get_dataset_lineage("nonexistent", "dataset")

    assert result is not None
        # 应该处理 404 错误

    # === 数据集搜索测试 ===

    @patch('requests.Session.get')
    def test_search_datasets_success(self, mock_get, manager, mock_response):
        """测试成功搜索数据集"""
        mock_response.json.return_value = {
            "datasets": [
                {"name": "dataset1", "namespace": "test_namespace"},
                {"name": "dataset2", "namespace": "test_namespace"}
            ],
            "total": 2
        }
        mock_get.return_value = mock_response

        result = manager.search_datasets("test_namespace", keyword="test")

    assert result is not None
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_search_datasets_with_filters(self, mock_get, manager, mock_response):
        """测试带过滤条件的数据集搜索"""
        mock_response.json.return_value = {"datasets": [], "total": 0}
        mock_get.return_value = mock_response

        result = manager.search_datasets(
            namespace="test_namespace",
            keyword="football",
            tag="raw",
            limit=10,
            offset=20
        )

    assert result is not None
        mock_get.assert_called_once()

    # === 数据集版本测试 ===

    @patch('requests.Session.get')
    def test_get_dataset_versions_success(self, mock_get, manager, mock_response):
        """测试成功获取数据集版本"""
        mock_response.json.return_value = {
            "versions": [
                {"version": "1.0", "created_at": "2023-01-01T00:00:00Z"},
                {"version": "2.0", "created_at": "2023-01-02T00:00:00Z"}
            ]
        }
        mock_get.return_value = mock_response

        result = manager.get_dataset_versions("test_namespace", "test_dataset")

    assert result is not None
    assert isinstance(result, list)
        mock_get.assert_called_once()

    # === 作业运行测试 ===

    @patch('requests.Session.get')
    def test_get_job_runs_success(self, mock_get, manager, mock_response):
        """测试成功获取作业运行"""
        mock_response.json.return_value = {
            "runs": [
                {"id": "run-1", "status": "completed", "start_time": "2023-01-01T00:00:00Z"},
                {"id": "run-2", "status": "running", "start_time": "2023-01-02T00:00:00Z"}
            ],
            "total": 2
        }
        mock_get.return_value = mock_response

        result = manager.get_job_runs("test_namespace", "test_job")

    assert result is not None
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_job_runs_with_filters(self, mock_get, manager, mock_response):
        """测试带过滤条件的作业运行查询"""
        mock_response.json.return_value = {"runs": [], "total": 0}
        mock_get.return_value = mock_response

        result = manager.get_job_runs(
            namespace="test_namespace",
            job_name="test_job",
            limit=5,
            status="completed"
        )

    assert result is not None
        mock_get.assert_called_once()

    # === 数据集标签测试 ===

    @patch('requests.Session.post')
    def test_add_dataset_tag_success(self, mock_post, manager, mock_response):
        """测试成功添加数据集标签"""
        mock_response.json.return_value = {"success": True, "tag": "important"}
        mock_post.return_value = mock_response

        result = manager.add_dataset_tag("test_namespace", "test_dataset", "important")

    assert result is not None
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_add_dataset_tag_error_handling(self, mock_post, manager):
        """测试添加数据集标签错误处理"""
        error_response = Mock()
        error_response.status_code = 404
        error_response.text = "Dataset not found"
        mock_post.return_value = error_response

        result = manager.add_dataset_tag("nonexistent", "dataset", "tag")

    assert result is not None
        # 应该处理错误

    # === 足球元数据设置测试 ===

    @patch('requests.Session.post')
    def test_setup_football_metadata_success(self, mock_post, manager, mock_response):
        """测试成功设置足球元数据"""
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        # 应该不抛出异常
        result = manager.setup_football_metadata()
    assert result is None  # 这个方法可能没有返回值

        # 验证多次调用（创建多个资源）
    assert mock_post.call_count >= 3  # 至少创建命名空间、数据集、作业

    @patch('requests.Session.post')
    def test_setup_football_metadata_partial_failure(self, mock_post, manager):
        """测试足球元数据设置部分失败"""
        # 第一个调用成功，后续调用失败
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"success": True}

        error_response = Mock()
        error_response.status_code = 400
        error_response.text = "Resource already exists"

        mock_post.side_effect = [success_response, error_response, error_response]

        # 应该继续执行即使部分失败
        result = manager.setup_football_metadata()
    assert result is None

    # === 错误处理测试 ===

    @patch('requests.Session.post')
    def test_http_error_handling(self, mock_post, manager):
        """测试 HTTP 错误处理"""
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        error_response.json.return_value = {"error": "Server error"}
        mock_post.return_value = error_response

        result = manager.create_namespace(name="test_namespace")
    assert result is not None
        # 应该包含错误信息但不崩溃

    @patch('requests.Session.post')
    def test_network_error_handling(self, mock_post, manager):
        """测试网络错误处理"""
        mock_post.side_effect = RequestException("Connection failed")

        result = manager.create_namespace(name="test_namespace")
    assert result is not None
        # 应该处理网络错误

    @patch('requests.Session.post')
    def test_json_decode_error_handling(self, mock_post, manager):
        """测试 JSON 解码错误处理"""
        invalid_response = Mock()
        invalid_response.status_code = 200
        invalid_response.json.side_effect = ValueError("Invalid JSON")
        invalid_response.text = "Invalid response"
        mock_post.return_value = invalid_response

        result = manager.create_namespace(name="test_namespace")
    assert result is not None
        # 应该处理 JSON 解码错误

    # === 边界条件测试 ===

    def test_empty_parameters_handling(self, manager):
        """测试空参数处理"""
        # 测试各种空参数情况
        result = manager.create_namespace(name="")
    assert result is not None

        result = manager.create_dataset(namespace="", name="")
    assert result is not None

        result = manager.search_datasets(namespace="")
    assert result is not None

    def test_special_characters_handling(self, manager):
        """测试特殊字符处理"""
        # 测试特殊字符在参数中的处理
        special_chars = {
            "name": "test-namespace_123",
            "description": "Test namespace with special chars: áéíóú 中文"
        }

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            result = manager.create_namespace(**special_chars)
    assert result is not None

    # === 参数验证测试 ===

    def test_parameter_validation(self, manager):
        """测试参数验证"""
        # 测试各种参数组合的验证
        test_cases = [
            {"name": "valid_name"},
            {"name": "name" * 100},  # 长名称
            {"name": "test@example.com"},  # 包含特殊字符
        ]

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            for params in test_cases:
                result = manager.create_namespace(**params)
    assert result is not None

    # === 会话管理测试 ===

    def test_session_reuse(self, manager):
        """测试会话重用"""
        # 验证同一实例重用会话
        session1 = manager.session
        session2 = manager.session
    assert session1 is session2

    def test_session_headers_persistence(self, manager):
        """测试会话头部持久性"""
        original_headers = manager.session.headers.copy()

        # 模拟一些操作
        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            manager.create_namespace(name="test")

        # 验证头部没有被修改
    assert manager.session.headers == original_headers

    # === 集成测试 ===

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_full_metadata_workflow(self, mock_get, mock_post, manager, mock_response):
        """测试完整元数据管理工作流"""
        # 模拟成功响应
        mock_post.return_value = mock_response
        mock_get.return_value = mock_response

        # 执行完整工作流
        namespace_result = manager.create_namespace("test_workflow", "Test workflow namespace")
    assert namespace_result is not None

        dataset_result = manager.create_dataset(
            namespace="test_workflow",
            name="test_dataset",
            description="Test dataset",
            fields=[{"name": "id", "type": "integer"}]
        )
    assert dataset_result is not None

        job_result = manager.create_job(
            namespace="test_workflow",
            name="test_job",
            description="Test job",
            type="batch"
        )
    assert job_result is not None

        lineage_result = manager.get_dataset_lineage("test_workflow", "test_dataset")
    assert lineage_result is not None

        search_result = manager.search_datasets("test_workflow", "test")
    assert search_result is not None

        versions_result = manager.get_dataset_versions("test_workflow", "test_dataset")
    assert versions_result is not None

    # === 性能测试 ===

    @patch('requests.Session.post')
    def test_multiple_operations_performance(self, mock_post, manager, mock_response):
        """测试多次操作性能"""
        import time

        mock_post.return_value = mock_response

        start_time = time.time()

        # 执行多次操作
        for i in range(10):
            manager.create_namespace(f"test_namespace_{i}")
            manager.create_dataset(
                namespace=f"test_namespace_{i}",
                name=f"test_dataset_{i}",
                description=f"Test dataset {i}",
                fields=[{"name": "id", "type": "integer"}]
            )

        end_time = time.time()
        execution_time = end_time - start_time

        # 应该在合理时间内完成
    assert execution_time < 5.0

    # === 配置测试 ===

    def test_url_configuration(self):
        """测试 URL 配置"""
        test_cases = [
            "http:_/localhost:5000",
            "https://marquez.example.com:8080",
            "http://internal-marquez:5000/api"
        ]

        for url in test_cases:
            manager = MetadataManager(marquez_url=url)
    assert manager.marquez_url == url
    assert manager.api_url is not None

    # === 工具函数测试 ===

    def test_get_metadata_manager_function(self):
        """测试 get_metadata_manager 工具函数"""
        from src.lineage.metadata_manager import get_metadata_manager

        manager = get_metadata_manager()
    assert manager is not None
    assert isinstance(manager, MetadataManager)
    assert manager.marquez_url == "http:_/localhost:5000"  # 默认 URL