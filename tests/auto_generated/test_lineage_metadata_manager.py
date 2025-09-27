"""
Auto-generated tests for src.lineage.metadata_manager module
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Optional
import requests

from src.lineage.metadata_manager import MetadataManager, get_metadata_manager


class TestMetadataManager:
    """测试元数据管理器"""

    def test_metadata_manager_initialization(self):
        """测试元数据管理器初始化"""
        manager = MetadataManager(
            marquez_url="http://localhost:8080"
        )

        assert manager.marquez_url == "http://localhost:8080"
        assert manager.base_url == "http://localhost:8080"
        assert manager.api_url == "http://localhost:8080/api/v1/"
        assert manager.session is not None
        assert manager.session.headers["Content-Type"] == "application/json"
        assert manager.session.headers["Accept"] == "application/json"

    def test_metadata_manager_initialization_defaults(self):
        """测试元数据管理器默认初始化"""
        manager = MetadataManager()

        assert manager.marquez_url == "http://localhost:5000"
        assert manager.api_url == "http://localhost:5000/api/v1/"

    def test_create_namespace_basic(self):
        """测试创建命名空间基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "test_namespace",
            "description": "Test namespace description",
            "ownerName": "test_owner"
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'put', return_value=mock_response) as mock_put:
            result = manager.create_namespace(
                name="test_namespace",
                description="Test namespace description",
                owner_name="test_owner"
            )

            assert result["name"] == "test_namespace"
            assert result["description"] == "Test namespace description"
            assert result["ownerName"] == "test_owner"

            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert "namespaces/test_namespace" in call_args[0][0]
            assert call_args[1]["json"]["name"] == "test_namespace"
            assert call_args[1]["json"]["description"] == "Test namespace description"
            assert call_args[1]["json"]["ownerName"] == "test_owner"

    def test_create_namespace_without_owner(self):
        """测试创建无所有者的命名空间"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "test_namespace"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'put', return_value=mock_response):
            result = manager.create_namespace(
                name="test_namespace",
                description="Test namespace"
            )

            assert result["name"] == "test_namespace"
            assert result["description"] == "Test namespace description"

            call_args = manager.session.put.call_args[1]
            assert "ownerName" not in call_args["json"]

    def test_create_namespace_with_request_exception(self):
        """测试创建命名空间请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'put') as mock_put:
            mock_put.side_effect = requests.exceptions.RequestException("Connection failed")

            with pytest.raises(requests.exceptions.RequestException, match="Connection failed"):
                manager.create_namespace(
                    name="test_namespace",
                    description="Test description"
                )

    def test_create_dataset_basic(self):
        """测试创建数据集基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "test_dataset",
            "description": "Test dataset description",
            "type": "DB_TABLE"
        }
        mock_response.raise_for_status = MagicMock()

        schema_fields = [
            {"name": "id", "type": "integer", "description": "Primary key"},
            {"name": "name", "type": "string", "description": "Entity name"}
        ]

        with patch.object(manager.session, 'put', return_value=mock_response) as mock_put:
            result = manager.create_dataset(
                namespace="test_namespace",
                name="test_dataset",
                description="Test dataset description",
                schema_fields=schema_fields,
                source_name="test_source",
                tags=["test", "dataset"]
            )

            assert result["name"] == "test_dataset"
            assert result["description"] == "Test dataset description"
            assert result["type"] == "DB_TABLE"

            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert "namespaces/test_namespace/datasets/test_dataset" in call_args[0][0]

            json_payload = call_args[1]["json"]
            assert json_payload["name"] == "test_dataset"
            assert json_payload["description"] == "Test dataset description"
            assert len(json_payload["fields"]) == 2
            assert json_payload["fields"][0]["name"] == "id"
            assert json_payload["fields"][0]["type"] == "integer"
            assert json_payload["fields"][0]["description"] == "Primary key"
            assert json_payload["tags"] == ["test", "dataset"]
            assert json_payload["sourceName"] == "test_source"

    def test_create_dataset_minimal(self):
        """测试创建最小数据集"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "minimal_dataset"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'put', return_value=mock_response):
            result = manager.create_dataset(
                namespace="test_namespace",
                name="minimal_dataset"
            )

            assert result["name"] == "minimal_dataset"

            call_args = manager.session.put.call_args[1]
            json_payload = call_args["json"]
            assert json_payload["name"] == "minimal_dataset"
            assert json_payload["description"] == "数据集: minimal_dataset"
            assert "fields" not in json_payload
            assert "tags" not in json_payload
            assert "sourceName" not in json_payload

    def test_create_dataset_with_request_exception(self):
        """测试创建数据集请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'put') as mock_put:
            mock_put.side_effect = requests.exceptions.RequestException("API error")

            with pytest.raises(requests.exceptions.RequestException, match="API error"):
                manager.create_dataset(
                    namespace="test_namespace",
                    name="test_dataset"
                )

    def test_create_job_basic(self):
        """测试创建作业基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "test_job",
            "description": "Test job description",
            "type": "BATCH"
        }
        mock_response.raise_for_status = MagicMock()

        input_datasets = [
            {"namespace": "input_namespace", "name": "input_dataset1"},
            {"namespace": "input_namespace", "name": "input_dataset2"}
        ]
        output_datasets = [
            {"namespace": "output_namespace", "name": "output_dataset"}
        ]

        with patch.object(manager.session, 'put', return_value=mock_response) as mock_put:
            result = manager.create_job(
                namespace="test_namespace",
                name="test_job",
                description="Test job description",
                job_type="BATCH",
                input_datasets=input_datasets,
                output_datasets=output_datasets,
                location="https://github.com/test/job.py"
            )

            assert result["name"] == "test_job"
            assert result["description"] == "Test job description"
            assert result["type"] == "BATCH"

            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert "namespaces/test_namespace/jobs/test_job" in call_args[0][0]

            json_payload = call_args[1]["json"]
            assert json_payload["name"] == "test_job"
            assert json_payload["description"] == "Test job description"
            assert json_payload["type"] == "BATCH"
            assert len(json_payload["inputs"]) == 2
            assert len(json_payload["outputs"]) == 1
            assert json_payload["location"] == "https://github.com/test/job.py"

    def test_create_job_minimal(self):
        """测试创建最小作业"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "minimal_job"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'put', return_value=mock_response):
            result = manager.create_job(
                namespace="test_namespace",
                name="minimal_job"
            )

            assert result["name"] == "minimal_job"

            call_args = manager.session.put.call_args[1]
            json_payload = call_args["json"]
            assert json_payload["name"] == "minimal_job"
            assert json_payload["description"] == "作业: minimal_job"
            assert json_payload["type"] == "BATCH"
            assert "inputs" not in json_payload
            assert "outputs" not in json_payload
            assert "location" not in json_payload

    def test_create_job_with_request_exception(self):
        """测试创建作业请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'put') as mock_put:
            mock_put.side_effect = requests.exceptions.RequestException("Job creation failed")

            with pytest.raises(requests.exceptions.RequestException, match="Job creation failed"):
                manager.create_job(
                    namespace="test_namespace",
                    name="test_job"
                )

    def test_get_dataset_lineage_basic(self):
        """测试获取数据集血缘基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nodes": [
                {"id": "dataset:test_namespace:source_table", "type": "dataset"},
                {"id": "dataset:test_namespace:target_table", "type": "dataset"}
            ],
            "edges": [
                {"source": "dataset:test_namespace:source_table", "target": "dataset:test_namespace:target_table"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response) as mock_get:
            result = manager.get_dataset_lineage(
                namespace="test_namespace",
                name="target_table",
                depth=3
            )

            assert len(result["nodes"]) == 2
            assert len(result["edges"]) == 1

            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["nodeId"] == "dataset:test_namespace:target_table"
            assert call_args[1]["params"]["depth"] == "3"

    def test_get_dataset_lineage_default_depth(self):
        """测试获取数据集血缘默认深度"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"nodes": [], "edges": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response):
            result = manager.get_dataset_lineage(
                namespace="test_namespace",
                name="target_table"
            )

            call_args = manager.session.get.call_args[1]
            assert call_args[1]["params"]["depth"] == "3"  # 默认深度

    def test_get_dataset_lineage_with_request_exception(self):
        """测试获取数据集血缘请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Lineage query failed")

            with pytest.raises(requests.exceptions.RequestException, match="Lineage query failed"):
                manager.get_dataset_lineage(
                    namespace="test_namespace",
                    name="target_table"
                )

    def test_search_datasets_basic(self):
        """测试搜索数据集基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"name": "dataset1", "namespace": "test_namespace"},
                {"name": "dataset2", "namespace": "test_namespace"},
                {"name": "other_dataset", "namespace": "other_namespace"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response) as mock_get:
            result = manager.search_datasets(
                query="test",
                namespace="test_namespace",
                limit=10
            )

            assert len(result) == 2  # 应该只返回匹配命名空间的2个结果
            assert result[0]["name"] == "dataset1"
            assert result[1]["name"] == "dataset2"

            mock_get.assert_called_once()
            call_args = mock_get.call_args[1]
            assert call_args[1]["params"]["q"] == "test"
            assert call_args[1]["params"]["namespace"] == "test_namespace"
            assert call_args[1]["params"]["limit"] == "10"

    def test_search_datasets_without_namespace(self):
        """测试无命名空间限制的数据集搜索"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response):
            result = manager.search_datasets(
                query="test",
                limit=5
            )

            call_args = manager.session.get.call_args[1]
            assert "namespace" not in call_args[1]["params"]
            assert call_args[1]["params"]["limit"] == "5"

    def test_search_datasets_with_request_exception(self):
        """测试搜索数据集请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Search failed")

            with pytest.raises(requests.exceptions.RequestException, match="Search failed"):
                manager.search_datasets(query="test")

    def test_get_dataset_versions_basic(self):
        """测试获取数据集版本历史基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "versions": [
                {"version": "1", "createdAt": "2025-09-28T10:00:00Z"},
                {"version": "2", "createdAt": "2025-09-28T12:00:00Z"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response) as mock_get:
            result = manager.get_dataset_versions(
                namespace="test_namespace",
                name="test_dataset"
            )

            assert len(result) == 2
            assert result[0]["version"] == "1"
            assert result[1]["version"] == "2"

            mock_get.assert_called_once()
            call_args = mock_get.call_args[0][0]
            assert "namespaces/test_namespace/datasets/test_dataset/versions" in call_args

    def test_get_dataset_versions_with_request_exception(self):
        """测试获取数据集版本历史请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Version query failed")

            with pytest.raises(requests.exceptions.RequestException, match="Version query failed"):
                manager.get_dataset_versions(
                    namespace="test_namespace",
                    name="test_dataset"
                )

    def test_get_job_runs_basic(self):
        """测试获取作业运行历史基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "runs": [
                {"id": "run1", "startTime": "2025-09-28T10:00:00Z", "endTime": "2025-09-28T10:05:00Z"},
                {"id": "run2", "startTime": "2025-09-28T11:00:00Z", "endTime": "2025-09-28T11:03:00Z"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response) as mock_get:
            result = manager.get_job_runs(
                namespace="test_namespace",
                job_name="test_job",
                limit=15
            )

            assert len(result) == 2
            assert result[0]["id"] == "run1"
            assert result[1]["id"] == "run2"

            mock_get.assert_called_once()
            call_args = mock_get.call_args[1]
            assert call_args[1]["params"]["limit"] == 15
            assert "namespaces/test_namespace/jobs/test_job/runs" in mock_get.call_args[0][0]

    def test_get_job_runs_default_limit(self):
        """测试获取作业运行历史默认限制"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"runs": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'get', return_value=mock_response):
            result = manager.get_job_runs(
                namespace="test_namespace",
                job_name="test_job"
            )

            call_args = manager.session.get.call_args[1]
            assert call_args[1]["params"]["limit"] == 20  # 默认限制

    def test_get_job_runs_with_request_exception(self):
        """测试获取作业运行历史请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Run query failed")

            with pytest.raises(requests.exceptions.RequestException, match="Run query failed"):
                manager.get_job_runs(
                    namespace="test_namespace",
                    job_name="test_job"
                )

    def test_add_dataset_tag_basic(self):
        """测试为数据集添加标签基本功能"""
        manager = MetadataManager()
        mock_response = MagicMock()
        mock_response.json.return_value = {"tag": "test_tag", "dataset": "test_dataset"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(manager.session, 'post', return_value=mock_response) as mock_post:
            result = manager.add_dataset_tag(
                namespace="test_namespace",
                name="test_dataset",
                tag="test_tag"
            )

            assert result["tag"] == "test_tag"
            assert result["dataset"] == "test_dataset"

            mock_post.assert_called_once()
            call_args = mock_post.call_args[0][0]
            assert "namespaces/test_namespace/datasets/test_dataset/tags/test_tag" in call_args

    def test_add_dataset_tag_with_request_exception(self):
        """测试为数据集添加标签请求异常"""
        manager = MetadataManager()

        with patch.object(manager.session, 'post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("Tag addition failed")

            with pytest.raises(requests.exceptions.RequestException, match="Tag addition failed"):
                manager.add_dataset_tag(
                    namespace="test_namespace",
                    name="test_dataset",
                    tag="test_tag"
                )

    def test_setup_football_metadata_basic(self):
        """测试设置足球预测平台元数据基本功能"""
        manager = MetadataManager()

        # 模拟创建命名空间的成功响应
        mock_namespace_response = MagicMock()
        mock_namespace_response.raise_for_status = MagicMock()

        # 模拟创建数据集的成功响应
        mock_dataset_response = MagicMock()
        mock_dataset_response.raise_for_status = MagicMock()

        with patch.object(manager, 'create_namespace', return_value={"name": "test"}) as mock_create_namespace:
            with patch.object(manager, 'create_dataset', return_value={"name": "test_dataset"}) as mock_create_dataset:
                # 应该不抛出异常
                manager.setup_football_metadata()

                # 验证命名空间创建调用
                assert mock_create_namespace.call_count == 5  # 应该创建5个命名空间

                # 验证数据集创建调用
                assert mock_create_dataset.call_count == 3  # 应该创建3个数据集

    def test_setup_football_metadata_with_namespace_exception(self):
        """测试设置足球预测平台元数据命名空间异常处理"""
        manager = MetadataManager()

        with patch.object(manager, 'create_namespace') as mock_create_namespace:
            with patch.object(manager, 'create_dataset') as mock_create_dataset:
                # 模拟命名空间已存在异常
                mock_create_namespace.side_effect = [Exception("Already exists")] * 5

                # 应该不抛出异常，继续处理
                manager.setup_football_metadata()

    def test_setup_football_metadata_with_dataset_exception(self):
        """测试设置足球预测平台元数据数据集异常处理"""
        manager = MetadataManager()

        with patch.object(manager, 'create_namespace') as mock_create_namespace:
            with patch.object(manager, 'create_dataset') as mock_create_dataset:
                # 模拟数据集已存在异常
                mock_create_dataset.side_effect = [Exception("Already exists")] * 3

                # 应该不抛出异常
                manager.setup_football_metadata()

    def test_setup_football_metadata_with_general_exception(self):
        """测试设置足球预测平台元数据一般异常处理"""
        manager = MetadataManager()

        with patch.object(manager, 'create_namespace') as mock_create_namespace:
            with patch.object(manager, 'create_dataset') as mock_create_dataset:
                mock_create_namespace.side_effect = Exception("Setup failed")

                with pytest.raises(Exception, match="Setup failed"):
                    manager.setup_football_metadata()


class TestGetMetadataManager:
    """测试获取元数据管理器全局实例"""

    def test_get_metadata_manager_singleton(self):
        """测试获取元数据管理器单例"""
        # 清除全局实例
        import src.lineage.metadata_manager
        src.lineage.metadata_manager._metadata_manager = None

        # 第一次获取应该创建新实例
        manager1 = get_metadata_manager()
        assert isinstance(manager1, MetadataManager)

        # 第二次获取应该返回相同实例
        manager2 = get_metadata_manager()
        assert manager1 is manager2

    def test_get_metadata_manager_with_existing_instance(self):
        """测试获取已存在的元数据管理器实例"""
        import src.lineage.metadata_manager

        # 设置自定义实例
        custom_manager = MetadataManager(marquez_url="http://custom:8080")
        src.lineage.metadata_manager._metadata_manager = custom_manager

        # 应该返回自定义实例
        manager = get_metadata_manager()
        assert manager is custom_manager
        assert manager.marquez_url == "http://custom:8080"


@pytest.fixture
def sample_metadata_manager():
    """示例元数据管理器fixture"""
    return MetadataManager(
        marquez_url="http://test-marquez:8080"
    )


@pytest.fixture
def mock_response():
    """模拟HTTP响应fixture"""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def sample_schema_fields():
    """示例Schema字段fixture"""
    return [
        {"name": "id", "type": "integer", "description": "Primary key"},
        {"name": "name", "type": "string", "description": "Entity name"},
        {"name": "created_at", "type": "timestamp", "description": "Creation timestamp"}
    ]


@pytest.fixture
def sample_input_datasets():
    """示例输入数据集fixture"""
    return [
        {"namespace": "bronze", "name": "raw_data"},
        {"namespace": "silver", "name": "processed_data"}
    ]


@pytest.fixture
def sample_output_datasets():
    """示例输出数据集fixture"""
    return [
        {"namespace": "gold", "name": "features"}
    ]


@pytest.mark.parametrize("owner_name,expected_in_payload", [
    ("test_owner", True),
    (None, False),
    ("", False),
])
def test_create_namespace_owner_handling(owner_name, expected_in_payload):
    """参数化测试命名空间所有者处理"""
    manager = MetadataManager()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch.object(manager.session, 'put', return_value=mock_response):
        if owner_name is None:
            manager.create_namespace(
                name="test_namespace",
                description="Test description"
            )
        else:
            manager.create_namespace(
                name="test_namespace",
                description="Test description",
                owner_name=owner_name
            )

        call_args = manager.session.put.call_args[1]
        has_owner = "ownerName" in call_args["json"]
        assert has_owner == expected_in_payload


@pytest.mark.parametrize("job_type,expected_type", [
    ("BATCH", "BATCH"),
    ("STREAM", "STREAM"),
    ("batch", "batch"),
    ("stream", "stream"),
])
def test_create_job_type_handling(job_type, expected_type):
    """参数化测试作业类型处理"""
    manager = MetadataManager()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch.object(manager.session, 'put', return_value=mock_response):
        manager.create_job(
            namespace="test_namespace",
            name="test_job",
            job_type=job_type
        )

        call_args = manager.session.put.call_args[1]
        assert call_args["json"]["type"] == expected_type


@pytest.mark.parametrize("depth,expected_depth", [
    (1, "1"),
    (3, "3"),
    (5, "5"),
    (10, "10"),
])
def test_get_dataset_lineage_depth(depth, expected_depth):
    """参数化测试数据集血缘深度"""
    manager = MetadataManager()
    mock_response = MagicMock()
    mock_response.json.return_value = {"nodes": [], "edges": []}
    mock_response.raise_for_status = MagicMock()

    with patch.object(manager.session, 'get', return_value=mock_response):
        manager.get_dataset_lineage(
            namespace="test_namespace",
            name="test_dataset",
            depth=depth
        )

        call_args = manager.session.get.call_args[1]
        assert call_args[1]["params"]["depth"] == expected_depth