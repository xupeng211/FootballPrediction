"""
metadata_manager模块的扩展测试
补充对数据查询、错误处理和边界场景的测试覆盖
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.lineage.metadata_manager import MetadataManager, get_metadata_manager


@pytest.fixture
def manager():
    """提供一个MetadataManager实例"""
    return MetadataManager(marquez_url="http://fake-marquez:5000")


class TestMetadataManagerExtended:
    """测试MetadataManager的扩展功能和错误处理"""

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_get_dataset_lineage_success(self, mock_get, manager: MetadataManager):
        """测试成功获取数据集血缘"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"graph": []}
        mock_get.return_value = mock_response

        result = manager.get_dataset_lineage("test_ns", "test_ds")

        assert result == {"graph": []}
        mock_get.assert_called_once_with(
            "http://fake-marquez:5000/api/v1/lineage",
            params={"nodeId": "dataset:test_ns:test_ds", "depth": "3"},
        )

    @patch("src.lineage.metadata_manager.requests.Session.put")
    def test_create_namespace_failure(self, mock_put, manager: MetadataManager):
        """测试创建命名空间时HTTP失败"""
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Conflict"
        )
        mock_put.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            manager.create_namespace("existing_namespace")

    @patch("src.lineage.metadata_manager.requests.Session.put")
    def test_create_dataset_failure(self, mock_put, manager: MetadataManager):
        """测试创建数据集时HTTP失败"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_put.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            manager.create_dataset("test_ns", "test_ds")

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_get_dataset_lineage_failure(self, mock_get, manager: MetadataManager):
        """测试获取数据集血缘时请求失败"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        with pytest.raises(requests.exceptions.RequestException):
            manager.get_dataset_lineage("test_ns", "test_ds")

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_search_datasets_success(self, mock_get, manager: MetadataManager):
        """测试成功搜索数据集"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"name": "dataset1"}]}
        mock_get.return_value = mock_response

        results = manager.search_datasets("query", namespace="test_ns")

        assert len(results) == 1
        assert results[0]["name"] == "dataset1"
        mock_get.assert_called_once_with(
            "http://fake-marquez:5000/api/v1/search",
            params={"q": "query", "limit": "10", "namespace": "test_ns"},
        )

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_search_datasets_failure(self, mock_get, manager: MetadataManager):
        """测试搜索数据集时请求失败"""
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            manager.search_datasets("query")

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_get_dataset_versions_success(self, mock_get, manager: MetadataManager):
        """测试成功获取数据集版本"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"versions": [{"version": "1"}]}
        mock_get.return_value = mock_response

        versions = manager.get_dataset_versions("test_ns", "test_ds")

        assert len(versions) == 1
        assert versions[0]["version"] == "1"
        mock_get.assert_called_once_with(
            "http://fake-marquez:5000/api/v1/namespaces/test_ns/datasets/test_ds/versions"
        )

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_get_dataset_versions_failure(self, mock_get, manager: MetadataManager):
        """测试获取数据集版本时请求失败"""
        mock_get.side_effect = requests.exceptions.RequestException("Timeout")

        with pytest.raises(requests.exceptions.RequestException):
            manager.get_dataset_versions("test_ns", "test_ds")

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_get_job_runs_success(self, mock_get, manager: MetadataManager):
        """测试成功获取作业运行历史"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"runs": [{"runId": "123"}]}
        mock_get.return_value = mock_response

        runs = manager.get_job_runs("test_ns", "test_job")

        assert len(runs) == 1
        assert runs[0]["runId"] == "123"
        mock_get.assert_called_once_with(
            "http://fake-marquez:5000/api/v1/namespaces/test_ns/jobs/test_job/runs",
            params={"limit": 20},
        )

    @patch("src.lineage.metadata_manager.requests.Session.post")
    def test_add_dataset_tag_success(self, mock_post, manager: MetadataManager):
        """测试成功为数据集添加标签"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag": "test_tag"}
        mock_post.return_value = mock_response

        result = manager.add_dataset_tag("test_ns", "test_ds", "test_tag")

        assert result["tag"] == "test_tag"
        mock_post.assert_called_once_with(
            "http://fake-marquez:5000/api/v1/namespaces/test_ns/datasets/test_ds/tags/test_tag"
        )

    @patch("src.lineage.metadata_manager.requests.Session.post")
    def test_add_dataset_tag_failure(self, mock_post, manager: MetadataManager):
        """测试添加数据集标签时HTTP失败"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "Internal Server Error"
        )
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            manager.add_dataset_tag("test_ns", "test_ds", "test_tag")

    @patch.object(MetadataManager, "create_namespace")
    @patch.object(MetadataManager, "create_dataset")
    def test_setup_football_metadata_success(
        self, mock_create_dataset, mock_create_namespace, manager: MetadataManager
    ):
        """测试元数据初始化流程"""
        manager.setup_football_metadata()

        assert mock_create_namespace.call_count == 5
        assert mock_create_dataset.call_count == 3
        mock_create_namespace.assert_any_call(
            name="football_prediction",
            description="足球预测平台核心数据",
            owner_name="data_team",
        )
        mock_create_dataset.assert_any_call(
            namespace="football_db.bronze",
            name="raw_match_data",
            description="原始比赛数据",
            schema_fields=[
                {"name": "id", "type": "INTEGER", "description": "主键"},
                {"name": "data_source", "type": "VARCHAR", "description": "数据源"},
                {"name": "raw_data", "type": "JSONB", "description": "原始数据"},
                {
                    "name": "collected_at",
                    "type": "TIMESTAMP",
                    "description": "采集时间",
                },
            ],
            tags=["bronze", "raw", "matches"],
        )

    @patch.object(
        MetadataManager, "create_namespace", side_effect=Exception("Already Exists")
    )
    def test_setup_football_metadata_handles_existing(
        self, mock_create_namespace, manager: MetadataManager
    ):
        """测试元数据初始化时处理已存在项的警告"""
        with patch("src.lineage.metadata_manager.logger") as mock_logger:
            manager.setup_football_metadata()
            assert mock_create_namespace.call_count > 0
            mock_logger.warning.assert_called()

    def test_get_metadata_manager_singleton(self):
        """测试get_metadata_manager返回单例"""
        # 重置全局变量以进行干净的测试
        from src.lineage import metadata_manager

        metadata_manager._metadata_manager = None

        manager1 = get_metadata_manager()
        manager2 = get_metadata_manager()
        assert manager1 is manager2

    @patch("src.lineage.metadata_manager.requests.Session.put")
    def test_create_namespace_with_owner(self, mock_put, manager: MetadataManager):
        """测试创建命名空间时提供所有者"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "test_namespace",
            "ownerName": "test_owner",
        }
        mock_put.return_value = mock_response

        manager.create_namespace("test_namespace", owner_name="test_owner")

        # 验证请求体中是否包含 ownerName
        sent_payload = mock_put.call_args.kwargs["json"]
        assert sent_payload["ownerName"] == "test_owner"

    @patch("src.lineage.metadata_manager.requests.Session.put")
    def test_create_job_with_all_fields(self, mock_put, manager: MetadataManager):
        """测试使用所有可选字段创建作业"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "full_job"}
        mock_put.return_value = mock_response

        manager.create_job(
            namespace="test_ns",
            name="full_job",
            job_type="STREAM",
            input_datasets=[{"namespace": "ns1", "name": "ds1"}],
            output_datasets=[{"namespace": "ns2", "name": "ds2"}],
            location="file:///tmp/job.py",
        )

        sent_payload = mock_put.call_args.kwargs["json"]
        assert len(sent_payload["inputs"]) == 1
        assert len(sent_payload["outputs"]) == 1
        assert sent_payload["location"] == "file:///tmp/job.py"
        assert sent_payload["type"] == "STREAM"

    @patch("src.lineage.metadata_manager.requests.Session.put")
    def test_create_job_failure(self, mock_put, manager: MetadataManager):
        """测试创建作业时请求失败"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_put.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            manager.create_job("test_ns", "failing_job")

    @patch("src.lineage.metadata_manager.requests.Session.get")
    def test_get_job_runs_failure(self, mock_get, manager: MetadataManager):
        """测试获取作业运行历史时请求失败"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        with pytest.raises(requests.exceptions.RequestException):
            manager.get_job_runs("test_ns", "test_job")
