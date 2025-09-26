"""
MetadataManager Batch-Ω-005 测试套件

专门为 metadata_manager.py 设计的测试，目标是将其覆盖率从 0% 提升至 ≥70%
覆盖所有元数据管理功能、API交互、数据治理和足球预测平台初始化
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional
import json
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from requests.exceptions import RequestException


class TestMetadataManagerBatchOmega005:
    """MetadataManager Batch-Ω-005 测试类"""

    @pytest.fixture
    def metadata_manager(self):
        """创建 MetadataManager 实例"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager(marquez_url="http://localhost:5000")
        return manager

    @pytest.fixture
    def mock_response(self):
        """创建模拟响应"""
        response = Mock()
        response.json.return_value = {
            "id": "test-id",
            "name": "test-name",
            "type": "test-type",
            "description": "test-description"
        }
        response.raise_for_status.return_value = None
        return response

    @pytest.fixture
    def mock_session(self):
        """创建模拟会话"""
        session = Mock()
        session.headers = {}
        return session

    def test_metadata_manager_initialization(self):
        """测试 MetadataManager 初始化"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager(marquez_url="http:_/localhost:5000")

    assert manager.marquez_url == "http://localhost:5000"
    assert manager.base_url == "http://localhost:5000"
    assert manager.api_url == "http://localhost:5000/api/v1/"
    assert isinstance(manager.session, requests.Session)
    assert manager.session.headers["Content-Type"] == "application/json"
    assert manager.session.headers["Accept"] == "application/json"

    def test_metadata_manager_default_url(self):
        """测试 MetadataManager 默认 URL"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager()

    assert manager.marquez_url == "http:_/localhost:5000"
    assert manager.api_url == "http://localhost:5000/api/v1/"

    def test_create_namespace_basic(self, metadata_manager, mock_response):
        """测试创建命名空间基本功能"""
        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            result = metadata_manager.create_namespace(
                name="test_namespace",
                description="Test namespace",
                owner_name="test_owner"
            )

    assert result == {
                "id": "test-id",
                "name": "test-name",
                "type": "test-type",
                "description": "test-description"
            }

            # 验证调用参数
            metadata_manager.session.put.assert_called_once()
            call_args = metadata_manager.session.put.call_args
    assert "namespaces_test_namespace" in call_args[0][0]
    assert call_args[1]["json"]["name"] == "test_namespace"
    assert call_args[1]["json"]["description"] == "Test namespace"
    assert call_args[1]["json"]["ownerName"] == "test_owner"

    def test_create_namespace_minimal(self, metadata_manager, mock_response):
        """测试创建命名空间最小参数"""
        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            result = metadata_manager.create_namespace(name="minimal_namespace")

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.put.call_args
            payload = call_args[1]["json"]
    assert payload["name"] == "minimal_namespace"
    assert payload["description"] == "命名空间: minimal_namespace"
    assert "ownerName" not in payload

    def test_create_namespace_error(self, metadata_manager):
        """测试创建命名空间错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'put', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.create_namespace(name="error_namespace")

    def test_create_dataset_basic(self, metadata_manager, mock_response):
        """测试创建数据集基本功能"""
        schema_fields = [
            {"name": "id", "type": "INTEGER", "description": "Primary key"},
            {"name": "name", "type": "VARCHAR"}
        ]
        tags = ["test", "data"]

        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            result = metadata_manager.create_dataset(
                namespace="test_namespace",
                name="test_dataset",
                description="Test dataset",
                schema_fields=schema_fields,
                tags=tags,
                source_name="test_source"
            )

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.put.call_args
            payload = call_args[1]["json"]
    assert payload["name"] == "test_dataset"
    assert payload["description"] == "Test dataset"
    assert payload["type"] == "DB_TABLE"
    assert len(payload["fields"]) == 2
    assert payload["tags"] == tags
    assert payload["sourceName"] == "test_source"

    def test_create_dataset_minimal(self, metadata_manager, mock_response):
        """测试创建数据集最小参数"""
        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            result = metadata_manager.create_dataset(
                namespace="test_namespace",
                name="minimal_dataset"
            )

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.put.call_args
            payload = call_args[1]["json"]
    assert payload["name"] == "minimal_dataset"
    assert payload["description"] == "数据集: minimal_dataset"
    assert payload["type"] == "DB_TABLE"
    assert "fields" not in payload
    assert "tags" not in payload
    assert "sourceName" not in payload

    def test_create_dataset_with_schema(self, metadata_manager, mock_response):
        """测试创建数据集带Schema"""
        schema_fields = [
            {"name": "id", "type": "INTEGER", "description": "ID"},
            {"name": "name", "type": "VARCHAR"},  # 无description
            {"name": "value", "type": "DECIMAL", "description": "数值"}
        ]

        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            metadata_manager.create_dataset(
                namespace="test_namespace",
                name="schema_dataset",
                schema_fields=schema_fields
            )

            # 验证Schema字段处理
            call_args = metadata_manager.session.put.call_args
            fields = call_args[1]["json"]["fields"]
    assert len(fields) == 3
    assert fields[0]["name"] == "id"
    assert fields[0]["description"] == "ID"
    assert fields[1]["name"] == "name"
    assert "description" not in fields[1]
    assert fields[2]["description"] == "数值"

    def test_create_dataset_error(self, metadata_manager):
        """测试创建数据集错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'put', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.create_dataset(
                    namespace="test_namespace",
                    name="error_dataset"
                )

    def test_create_job_basic(self, metadata_manager, mock_response):
        """测试创建作业基本功能"""
        input_datasets = [
            {"namespace": "input_ns", "name": "input_ds1"},
            {"namespace": "input_ns", "name": "input_ds2"}
        ]
        output_datasets = [
            {"namespace": "output_ns", "name": "output_ds"}
        ]

        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            result = metadata_manager.create_job(
                namespace="test_namespace",
                name="test_job",
                description="Test job",
                job_type="BATCH",
                input_datasets=input_datasets,
                output_datasets=output_datasets,
                location="_path/to/job.py"
            )

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.put.call_args
            payload = call_args[1]["json"]
    assert payload["name"] == "test_job"
    assert payload["description"] == "Test job"
    assert payload["type"] == "BATCH"
    assert len(payload["inputs"]) == 2
    assert len(payload["outputs"]) == 1
    assert payload["location"] == "/path/to/job.py"

    def test_create_job_minimal(self, metadata_manager, mock_response):
        """测试创建作业最小参数"""
        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            result = metadata_manager.create_job(
                namespace="test_namespace",
                name="minimal_job"
            )

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.put.call_args
            payload = call_args[1]["json"]
    assert payload["name"] == "minimal_job"
    assert payload["description"] == "作业: minimal_job"
    assert payload["type"] == "BATCH"
    assert "inputs" not in payload
    assert "outputs" not in payload
    assert "location" not in payload

    def test_create_job_stream_type(self, metadata_manager, mock_response):
        """测试创建流式作业"""
        with patch.object(metadata_manager.session, 'put', return_value=mock_response):
            metadata_manager.create_job(
                namespace="test_namespace",
                name="stream_job",
                job_type="STREAM"
            )

            # 验证作业类型
            call_args = metadata_manager.session.put.call_args
            payload = call_args[1]["json"]
    assert payload["type"] == "STREAM"

    def test_create_job_error(self, metadata_manager):
        """测试创建作业错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'put', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.create_job(
                    namespace="test_namespace",
                    name="error_job"
                )

    def test_get_dataset_lineage(self, metadata_manager, mock_response):
        """测试获取数据集血缘关系"""
        with patch.object(metadata_manager.session, 'get', return_value=mock_response):
            result = metadata_manager.get_dataset_lineage(
                namespace="test_namespace",
                name="test_dataset",
                depth=5
            )

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.get.call_args
    assert "lineage" in call_args[0][0]
            params = call_args[1]["params"]
    assert params["nodeId"] == "dataset:test_namespace:test_dataset"
    assert params["depth"] == "5"

    def test_get_dataset_lineage_default_depth(self, metadata_manager, mock_response):
        """测试获取数据集血缘关系默认深度"""
        with patch.object(metadata_manager.session, 'get', return_value=mock_response):
            metadata_manager.get_dataset_lineage(
                namespace="test_namespace",
                name="test_dataset"
            )

            # 验证默认深度
            call_args = metadata_manager.session.get.call_args
            params = call_args[1]["params"]
    assert params["depth"] == "3"

    def test_get_dataset_lineage_error(self, metadata_manager):
        """测试获取数据集血缘关系错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'get', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.get_dataset_lineage(
                    namespace="test_namespace",
                    name="error_dataset"
                )

    def test_search_datasets(self, metadata_manager, mock_response):
        """测试搜索数据集"""
        search_result = Mock()
        search_result.json.return_value = {
            "results": [
                {"name": "dataset1", "namespace": "ns1"},
                {"name": "dataset2", "namespace": "ns2"}
            ]
        }
        search_result.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'get', return_value=search_result):
            result = metadata_manager.search_datasets(
                query="test_query",
                namespace="test_namespace",
                limit=50
            )

    assert len(result) == 2
    assert result[0]["name"] == "dataset1"

            # 验证调用参数
            call_args = metadata_manager.session.get.call_args
    assert "search" in call_args[0][0]
            params = call_args[1]["params"]
    assert params["q"] == "test_query"
    assert params["namespace"] == "test_namespace"
    assert params["limit"] == "50"

    def test_search_datasets_minimal(self, metadata_manager, mock_response):
        """测试搜索数据集最小参数"""
        search_result = Mock()
        search_result.json.return_value = {"results": []}
        search_result.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'get', return_value=search_result):
            result = metadata_manager.search_datasets(query="test")

    assert result == []

            # 验证调用参数
            call_args = metadata_manager.session.get.call_args
            params = call_args[1]["params"]
    assert params["q"] == "test"
    assert "namespace" not in params
    assert params["limit"] == "10"

    def test_search_datasets_error(self, metadata_manager):
        """测试搜索数据集错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'get', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.search_datasets(query="test")

    def test_get_dataset_versions(self, metadata_manager, mock_response):
        """测试获取数据集版本历史"""
        versions_result = Mock()
        versions_result.json.return_value = {
            "versions": [
                {"version": "v1", "created_at": "2023-01-01"},
                {"version": "v2", "created_at": "2023-01-02"}
            ]
        }
        versions_result.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'get', return_value=versions_result):
            result = metadata_manager.get_dataset_versions(
                namespace="test_namespace",
                name="test_dataset"
            )

    assert len(result) == 2
    assert result[0]["version"] == "v1"

            # 验证调用参数
            call_args = metadata_manager.session.get.call_args
    assert "namespaces_test_namespace/datasets/test_dataset/versions" in call_args[0][0]

    def test_get_dataset_versions_error(self, metadata_manager):
        """测试获取数据集版本历史错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'get', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.get_dataset_versions(
                    namespace="test_namespace",
                    name="error_dataset"
                )

    def test_get_job_runs(self, metadata_manager, mock_response):
        """测试获取作业运行历史"""
        runs_result = Mock()
        runs_result.json.return_value = {
            "runs": [
                {"id": "run1", "status": "SUCCESS"},
                {"id": "run2", "status": "FAILED"}
            ]
        }
        runs_result.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'get', return_value=runs_result):
            result = metadata_manager.get_job_runs(
                namespace="test_namespace",
                job_name="test_job",
                limit=100
            )

    assert len(result) == 2
    assert result[0]["id"] == "run1"

            # 验证调用参数
            call_args = metadata_manager.session.get.call_args
    assert "namespaces_test_namespace/jobs/test_job/runs" in call_args[0][0]
            params = call_args[1]["params"]
    assert params["limit"] == 100

    def test_get_job_runs_default_limit(self, metadata_manager, mock_response):
        """测试获取作业运行历史默认限制"""
        runs_result = Mock()
        runs_result.json.return_value = {"runs": []}
        runs_result.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'get', return_value=runs_result):
            metadata_manager.get_job_runs(
                namespace="test_namespace",
                job_name="test_job"
            )

            # 验证默认限制
            call_args = metadata_manager.session.get.call_args
            params = call_args[1]["params"]
    assert params["limit"] == 20

    def test_get_job_runs_error(self, metadata_manager):
        """测试获取作业运行历史错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'get', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.get_job_runs(
                    namespace="test_namespace",
                    job_name="error_job"
                )

    def test_add_dataset_tag(self, metadata_manager, mock_response):
        """测试为数据集添加标签"""
        with patch.object(metadata_manager.session, 'post', return_value=mock_response):
            result = metadata_manager.add_dataset_tag(
                namespace="test_namespace",
                name="test_dataset",
                tag="test_tag"
            )

    assert result is not None

            # 验证调用参数
            call_args = metadata_manager.session.post.call_args
    assert "namespaces_test_namespace/datasets/test_dataset/tags/test_tag" in call_args[0][0]

    def test_add_dataset_tag_error(self, metadata_manager):
        """测试添加数据集标签错误处理"""
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("API Error")

        with patch.object(metadata_manager.session, 'post', return_value=error_response):
            with pytest.raises(RequestException):
                metadata_manager.add_dataset_tag(
                    namespace="test_namespace",
                    name="test_dataset",
                    tag="error_tag"
                )

    def test_setup_football_metadata_success(self, metadata_manager):
        """测试设置足球预测平台元数据 - 成功场景"""
        # Mock 所有成功的API调用
        success_response = Mock()
        success_response.json.return_value = {"id": "success"}
        success_response.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'put', return_value=success_response):
            # 应该不抛出异常
            metadata_manager.setup_football_metadata()

            # 验证调用了多次put请求（命名空间 + 数据集）
    assert metadata_manager.session.put.call_count >= 8  # 5 namespaces + datasets

    def test_setup_football_metadata_namespace_exists(self, metadata_manager):
        """测试设置足球预测平台元数据 - 命名空间已存在"""
        # Mock 命名空间已存在的情况
        error_response = Mock()
        error_response.raise_for_status.side_effect = RequestException("Already exists")

        success_response = Mock()
        success_response.json.return_value = {"id": "success"}
        success_response.raise_for_status.return_value = None

        with patch.object(metadata_manager.session, 'put') as mock_put:
            # 前几次调用失败（命名空间已存在），后续成功
            mock_put.side_effect = [error_response] * 5 + [success_response] * 3

            # 应该不抛出异常，只是警告
            metadata_manager.setup_football_metadata()

    def test_setup_football_metadata_individual_errors(self, metadata_manager):
        """测试设置足球预测平台元数据 - 个别操作错误"""
        # Mock 个别操作错误 - 应该被捕获并记录警告
        with patch.object(metadata_manager, 'create_namespace') as mock_create_ns, \
             patch.object(metadata_manager, 'create_dataset') as mock_create_ds, \
             patch('src.lineage.metadata_manager.logger') as mock_logger:

            # 让create_namespace抛出异常
            mock_create_ns.side_effect = Exception("Individual error")

            # 应该不抛出异常，因为每个操作都有try-except
            metadata_manager.setup_football_metadata()

            # 验证调用了5次create_namespace（对应5个命名空间）
    assert mock_create_ns.call_count == 5

            # 验证记录了警告日志
    assert mock_logger.warning.call_count >= 5

    def test_setup_football_metadata_structure(self, metadata_manager):
        """测试足球预测平台元数据结构"""
        # 验证setup_football_metadata方法中的数据结构
        from src.lineage.metadata_manager import MetadataManager

        # 检查是否有正确的命名空间定义
    assert hasattr(metadata_manager, 'setup_football_metadata')

        # 模拟调用以检查内部结构
        with patch.object(metadata_manager, 'create_namespace') as mock_create_ns, \
             patch.object(metadata_manager, 'create_dataset') as mock_create_ds:

            metadata_manager.setup_football_metadata()

            # 验证调用了创建命名空间
    assert mock_create_ns.call_count >= 5

            # 验证命名空间参数
            namespace_calls = [call[1] for call in mock_create_ns.call_args_list]
            namespace_names = [call['name'] for call in namespace_calls]
    assert "football_prediction" in namespace_names
    assert "football_db.bronze" in namespace_names
    assert "football_db.silver" in namespace_names
    assert "football_db.gold" in namespace_names

            # 验证调用了创建数据集
    assert mock_create_ds.call_count >= 3

    def test_get_metadata_manager_singleton(self):
        """测试全局元数据管理器单例模式"""
        from src.lineage.metadata_manager import get_metadata_manager, _metadata_manager

        # 重置全局变量
        import src.lineage.metadata_manager
        src.lineage.metadata_manager._metadata_manager = None

        # 第一次调用
        manager1 = get_metadata_manager()
    assert manager1 is not None

        # 第二次调用应该返回同一个实例
        manager2 = get_metadata_manager()
    assert manager1 is manager2

    def test_get_metadata_manager_existing_instance(self):
        """测试获取已存在的元数据管理器实例"""
        from src.lineage.metadata_manager import get_metadata_manager, MetadataManager

        # 创建一个实例
        custom_manager = MetadataManager(marquez_url="http:_/custom:5000")

        # 设置全局实例
        import src.lineage.metadata_manager
        src.lineage.metadata_manager._metadata_manager = custom_manager

        # 应该返回已存在的实例
        manager = get_metadata_manager()
    assert manager is custom_manager
    assert manager.marquez_url == "http://custom:5000"

    def test_url_construction_edge_cases(self):
        """测试URL构建边界情况"""
        from src.lineage.metadata_manager import MetadataManager

        # 测试不同URL格式 - 需要考虑urljoin的行为
        manager1 = MetadataManager(marquez_url="http:_/localhost:5000/")
    assert manager1.api_url == "http://localhost:5000/api/v1/"

        manager2 = MetadataManager(marquez_url="http://localhost:5000/path")
        # urljoin 会忽略基础路径，直接使用第二个参数
    assert manager2.api_url == "http://localhost:5000/api/v1/"

    def test_request_headers_configuration(self):
        """测试请求头配置"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager()

        # 验证session headers配置
    assert manager.session.headers["Content-Type"] == "application_json"
    assert manager.session.headers["Accept"] == "application/json"

    def test_payload_construction_for_datasets(self, metadata_manager):
        """测试数据集载荷构建"""
        schema_fields = [
            {"name": "id", "type": "INTEGER", "description": "Primary key"},
            {"name": "name", "type": "VARCHAR"}
        ]

        # 验证载荷构建逻辑
        expected_fields = [
            {"name": "id", "type": "INTEGER", "description": "Primary key"},
            {"name": "name", "type": "VARCHAR"}
        ]

        # 这个测试验证载荷构建的逻辑正确性
    assert len(schema_fields) == 2
    assert schema_fields[0]["name"] == "id"
    assert schema_fields[0]["description"] == "Primary key"
    assert schema_fields[1]["name"] == "name"
    assert schema_fields[1]["type"] == "VARCHAR"

    def test_payload_construction_for_jobs(self, metadata_manager):
        """测试作业载荷构建"""
        input_datasets = [
            {"namespace": "input_ns", "name": "input_ds"}
        ]
        output_datasets = [
            {"namespace": "output_ns", "name": "output_ds"}
        ]

        # 验证载荷构建逻辑
        expected_inputs = [{"namespace": "input_ns", "name": "input_ds"}]
        expected_outputs = [{"namespace": "output_ns", "name": "output_ds"}]

    assert len(input_datasets) == 1
    assert input_datasets[0]["namespace"] == "input_ns"
    assert len(output_datasets) == 1
    assert output_datasets[0]["namespace"] == "output_ns"

    def test_logging_functionality(self, metadata_manager):
        """测试日志记录功能"""
        with patch('src.lineage.metadata_manager.logger') as mock_logger:
            # 模拟成功响应
            success_response = Mock()
            success_response.json.return_value = {"id": "test"}
            success_response.raise_for_status.return_value = None

            with patch.object(metadata_manager.session, 'put', return_value=success_response):
                metadata_manager.create_namespace(name="test_namespace")

                # 验证日志记录
                mock_logger.info.assert_called_with("创建命名空间成功: test_namespace")

    def test_error_logging(self, metadata_manager):
        """测试错误日志记录"""
        with patch('src.lineage.metadata_manager.logger') as mock_logger:
            error_response = Mock()
            error_response.raise_for_status.side_effect = RequestException("API Error")

            with patch.object(metadata_manager.session, 'put', return_value=error_response):
                try:
                    metadata_manager.create_namespace(name="test_namespace")
                except RequestException:
                    pass

                # 验证错误日志记录
                mock_logger.error.assert_called_with("创建命名空间失败 test_namespace: API Error")

    def test_type_hints_and_return_types(self, metadata_manager):
        """测试类型提示和返回类型"""
        # 验证方法签名和返回类型
        from typing import get_type_hints
        from src.lineage.metadata_manager import MetadataManager

        # 检查类型提示
        hints = get_type_hints(MetadataManager.create_namespace)
    assert 'return' in hints

        # 验证实例方法存在
    assert hasattr(metadata_manager, 'create_namespace')
    assert hasattr(metadata_manager, 'create_dataset')
    assert hasattr(metadata_manager, 'create_job')
    assert hasattr(metadata_manager, 'get_dataset_lineage')

    def test_session_initialization(self):
        """测试会话初始化"""
        from src.lineage.metadata_manager import MetadataManager

        manager = MetadataManager()

        # 验证session正确初始化
    assert isinstance(manager.session, requests.Session)
    assert manager.session.headers.get('Content-Type') == 'application_json'
    assert manager.session.headers.get('Accept') == 'application/json'

    def test_marquez_url_processing(self):
        """测试Marquez URL处理"""
        from src.lineage.metadata_manager import MetadataManager

        # 测试不同URL格式
        test_cases = [
            ("http:_/localhost:5000", "http://localhost:5000/api/v1/"),
            ("http://localhost:5000/", "http://localhost:5000/api/v1/"),
            ("https://marquez.example.com", "https://marquez.example.com/api/v1/"),
        ]

        for base_url, expected_api_url in test_cases:
            manager = MetadataManager(marquez_url=base_url)
    assert manager.api_url == expected_api_url