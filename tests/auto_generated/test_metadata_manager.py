"""
 metadata_manager.py 测试文件
 测试 Marquez 元数据管理器的元数据操作和数据治理功能
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import sys
import os
from typing import Dict, Any, List, Optional

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lineage.metadata_manager import MetadataManager, get_metadata_manager


class TestMetadataManager:
    """测试 MetadataManager 元数据管理器"""

    def setup_method(self):
        """设置测试环境"""
        self.manager = MetadataManager(marquez_url="http://localhost:5000")

    def test_metadata_manager_initialization(self):
        """测试元数据管理器初始化"""
        assert self.manager.marquez_url == "http://localhost:5000"
        assert self.manager.base_url == "http://localhost:5000"
        assert self.manager.api_url == "http://localhost:5000/api/v1/"
        assert self.manager.session is not None
        assert "Content-Type" in self.manager.session.headers
        assert "Accept" in self.manager.session.headers

    def test_metadata_manager_default_initialization(self):
        """测试默认参数初始化"""
        manager = MetadataManager()
        assert manager.marquez_url == "http://localhost:5000"

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_namespace_success(self, mock_session_class):
        """测试成功创建命名空间"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟成功响应
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "name": "test_namespace",
            "description": "Test namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        mock_session.put.return_value = mock_response

        manager = MetadataManager()
        result = manager.create_namespace(
            name="test_namespace",
            description="Test namespace",
            owner_name="test_owner"
        )

        assert result["name"] == "test_namespace"
        assert result["description"] == "Test namespace"

        # 验证API调用
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        assert "namespaces/test_namespace" in call_args[0][0]

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_namespace_minimal(self, mock_session_class):
        """测试最小参数创建命名空间"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "name": "test_namespace",
            "description": "命名空间: test_namespace"
        }
        mock_session.put.return_value = mock_response

        manager = MetadataManager()
        result = manager.create_namespace(name="test_namespace")

        assert result["name"] == "test_namespace"
        assert result["description"] == "命名空间: test_namespace"

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_namespace_error_handling(self, mock_session_class):
        """测试命名空间创建错误处理"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟HTTP错误
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 409 Conflict")
        mock_session.put.return_value = mock_response

        manager = MetadataManager()

        with pytest.raises(Exception) as exc_info:
            manager.create_namespace(name="existing_namespace")

        assert "HTTP 409 Conflict" in str(exc_info.value)

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_dataset_success(self, mock_session_class):
        """测试成功创建数据集"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "name": "test_dataset",
            "namespace": "test_namespace",
            "type": "DB_TABLE",
            "description": "Test dataset"
        }
        mock_session.put.return_value = mock_response

        manager = MetadataManager()
        result = manager.create_dataset(
            namespace="test_namespace",
            name="test_dataset",
            description="Test dataset",
            schema_fields=[
                {"name": "id", "type": "INTEGER", "description": "Primary key"},
                {"name": "name", "type": "VARCHAR", "description": "Name field"}
            ],
            source_name="test_source",
            tags=["test", "dataset"]
        )

        assert result["name"] == "test_dataset"
        assert result["namespace"] == "test_namespace"
        assert result["type"] == "DB_TABLE"

        # 验证API调用
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        assert "namespaces/test_namespace/datasets/test_dataset" in call_args[0][0]

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_dataset_minimal(self, mock_session_class):
        """测试最小参数创建数据集"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "name": "test_dataset",
            "namespace": "test_namespace",
            "type": "DB_TABLE",
            "description": "数据集: test_dataset"
        }
        mock_session.put.return_value = mock_response

        manager = MetadataManager()
        result = manager.create_dataset(
            namespace="test_namespace",
            name="test_dataset"
        )

        assert result["name"] == "test_dataset"
        assert result["description"] == "数据集: test_dataset"

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_job_success(self, mock_session_class):
        """测试成功创建作业"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "name": "test_job",
            "namespace": "test_namespace",
            "type": "BATCH",
            "description": "Test job"
        }
        mock_session.put.return_value = mock_response

        manager = MetadataManager()
        result = manager.create_job(
            namespace="test_namespace",
            name="test_job",
            description="Test job",
            job_type="BATCH",
            input_datasets=[
                {"namespace": "input_ns", "name": "input_dataset"}
            ],
            output_datasets=[
                {"namespace": "output_ns", "name": "output_dataset"}
            ],
            location="https://github.com/test/repo"
        )

        assert result["name"] == "test_job"
        assert result["namespace"] == "test_namespace"
        assert result["type"] == "BATCH"

        # 验证API调用
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        assert "namespaces/test_namespace/jobs/test_job" in call_args[0][0]

    @patch('lineage.metadata_manager.requests.Session')
    def test_create_job_minimal(self, mock_session_class):
        """测试最小参数创建作业"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "name": "test_job",
            "namespace": "test_namespace",
            "type": "BATCH",
            "description": "作业: test_job"
        }
        mock_session.put.return_value = mock_response

        manager = MetadataManager()
        result = manager.create_job(
            namespace="test_namespace",
            name="test_job"
        )

        assert result["name"] == "test_job"
        assert result["description"] == "作业: test_job"

    @patch('lineage.metadata_manager.requests.Session')
    def test_get_dataset_lineage_success(self, mock_session_class):
        """测试成功获取数据集血缘"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "nodes": [
                {"id": "dataset:test_namespace:test_dataset", "type": "DATASET"},
                {"id": "job:test_namespace:test_job", "type": "JOB"}
            ],
            "edges": [
                {"source": "job:test_namespace:test_job", "target": "dataset:test_namespace:test_dataset"}
            ]
        }
        mock_session.get.return_value = mock_response

        manager = MetadataManager()
        result = manager.get_dataset_lineage(
            namespace="test_namespace",
            name="test_dataset",
            depth=3
        )

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

        # 验证API调用
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "lineage" in call_args[0][0]
        assert call_args[1]["params"]["nodeId"] == "dataset:test_namespace:test_dataset"
        assert call_args[1]["params"]["depth"] == "3"

    @patch('lineage.metadata_manager.requests.Session')
    def test_search_datasets_success(self, mock_session_class):
        """测试成功搜索数据集"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {
                    "name": "match_dataset",
                    "namespace": "test_namespace",
                    "type": "DB_TABLE"
                },
                {
                    "name": "team_dataset",
                    "namespace": "test_namespace",
                    "type": "DB_TABLE"
                }
            ]
        }
        mock_session.get.return_value = mock_response

        manager = MetadataManager()
        result = manager.search_datasets(
            query="match",
            namespace="test_namespace",
            limit=10
        )

        assert len(result) == 2
        assert result[0]["name"] == "match_dataset"
        assert result[1]["name"] == "team_dataset"

        # 验证API调用
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "search" in call_args[0][0]
        assert call_args[1]["params"]["q"] == "match"
        assert call_args[1]["params"]["namespace"] == "test_namespace"
        assert call_args[1]["params"]["limit"] == "10"

    @patch('lineage.metadata_manager.requests.Session')
    def test_search_datasets_no_namespace(self, mock_session_class):
        """测试不指定命名空间搜索数据集"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": []}
        mock_session.get.return_value = mock_response

        manager = MetadataManager()
        result = manager.search_datasets(query="test")

        assert result == []

        # 验证API调用
        call_args = mock_session.get.call_args
        assert "namespace" not in call_args[1]["params"]

    @patch('lineage.metadata_manager.requests.Session')
    def test_get_dataset_versions_success(self, mock_session_class):
        """测试成功获取数据集版本"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "versions": [
                {
                    "version": "1",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "description": "Initial version"
                },
                {
                    "version": "2",
                    "createdAt": "2023-01-02T00:00:00Z",
                    "description": "Updated schema"
                }
            ]
        }
        mock_session.get.return_value = mock_response

        manager = MetadataManager()
        result = manager.get_dataset_versions(
            namespace="test_namespace",
            name="test_dataset"
        )

        assert len(result) == 2
        assert result[0]["version"] == "1"
        assert result[1]["version"] == "2"

        # 验证API调用
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "namespaces/test_namespace/datasets/test_dataset/versions" in call_args[0][0]

    @patch('lineage.metadata_manager.requests.Session')
    def test_get_job_runs_success(self, mock_session_class):
        """测试成功获取作业运行历史"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "runs": [
                {
                    "id": "run_1",
                    "nominalStartTime": "2023-01-01T00:00:00Z",
                    "nominalEndTime": "2023-01-01T01:00:00Z",
                    "status": "COMPLETED"
                },
                {
                    "id": "run_2",
                    "nominalStartTime": "2023-01-02T00:00:00Z",
                    "nominalEndTime": "2023-01-02T01:00:00Z",
                    "status": "FAILED"
                }
            ]
        }
        mock_session.get.return_value = mock_response

        manager = MetadataManager()
        result = manager.get_job_runs(
            namespace="test_namespace",
            job_name="test_job",
            limit=20
        )

        assert len(result) == 2
        assert result[0]["id"] == "run_1"
        assert result[1]["id"] == "run_2"

        # 验证API调用
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "namespaces/test_namespace/jobs/test_job/runs" in call_args[0][0]
        assert call_args[1]["params"]["limit"] == 20

    @patch('lineage.metadata_manager.requests.Session')
    def test_add_dataset_tag_success(self, mock_session_class):
        """测试成功添加数据集标签"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "tag": "important",
            "dataset": "test_dataset",
            "namespace": "test_namespace"
        }
        mock_session.post.return_value = mock_response

        manager = MetadataManager()
        result = manager.add_dataset_tag(
            namespace="test_namespace",
            name="test_dataset",
            tag="important"
        )

        assert result["tag"] == "important"
        assert result["dataset"] == "test_dataset"

        # 验证API调用
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "namespaces/test_namespace/datasets/test_dataset/tags/important" in call_args[0][0]

    @patch('lineage.metadata_manager.requests.Session')
    def test_setup_football_metadata_success(self, mock_session_class):
        """测试成功设置足球元数据"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟成功响应
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"name": "test", "description": "test"}
        mock_session.put.return_value = mock_response
        mock_session.post.return_value = mock_response

        manager = MetadataManager()
        manager.setup_football_metadata()

        # 验证多个API调用
        assert mock_session.put.call_count >= 5  # 5个命名空间 + 3个数据集

    @patch('lineage.metadata_manager.requests.Session')
    def test_setup_football_metadata_partial_failure(self, mock_session_class):
        """测试足球元数据设置部分失败"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟部分失败
        call_count = 0
        def mock_put(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # 第3个调用失败
                raise Exception("Already exists")
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"name": "test"}
            return mock_response

        mock_session.put.side_effect = mock_put

        manager = MetadataManager()
        # 应该不会抛出异常，而是记录警告
        manager.setup_football_metadata()

        # 验证仍然进行了多个调用
        assert call_count >= 8  # 继续尝试其他操作

    @patch('lineage.metadata_manager.logger')
    def test_error_logging(self, mock_logger):
        """测试错误日志记录"""
        with patch('lineage.metadata_manager.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 模拟错误
            mock_session.put.side_effect = Exception("Connection failed")

            manager = MetadataManager()

            with pytest.raises(Exception):
                manager.create_namespace("test_namespace")

            # 验证错误被记录
            mock_logger.error.assert_called_once()

    def test_url_construction(self):
        """测试URL构造"""
        # 测试不同的marquez_url
        manager1 = MetadataManager(marquez_url="http://localhost:8080")
        assert manager1.api_url == "http://localhost:8080/api/v1/"

        manager2 = MetadataManager(marquez_url="https://marquez.example.com")
        assert manager2.api_url == "https://marquez.example.com/api/v1/"

        manager3 = MetadataManager(marquez_url="http://localhost:5000/marquez")
        assert manager3.api_url == "http://localhost:5000/marquez/api/v1/"


class TestGlobalMetadataManager:
    """测试全局元数据管理器"""

    def setup_method(self):
        """设置测试环境"""
        # 清理全局变量
        import lineage.metadata_manager
        lineage.metadata_manager._metadata_manager = None

    def test_get_metadata_manager_singleton(self):
        """测试获取全局元数据管理器单例"""
        manager1 = get_metadata_manager()
        manager2 = get_metadata_manager()

        assert manager1 is manager2  # 应该是同一个实例

    def test_get_metadata_manager_initialization(self):
        """测试全局元数据管理器初始化"""
        manager = get_metadata_manager()

        assert isinstance(manager, MetadataManager)
        assert manager.marquez_url == "http://localhost:5000"

    def test_global_manager_thread_safety(self):
        """测试全局管理器线程安全性"""
        import threading
        import time

        managers = []

        def get_manager():
            manager = get_metadata_manager()
            managers.append(manager)
            time.sleep(0.01)  # 短暂延迟

        # 创建多个线程同时获取管理器
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_manager)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有线程获取的是同一个实例
        assert len(set(managers)) == 1
        assert len(managers) == 10


class TestMetadataManagerIntegration:
    """测试 MetadataManager 集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.manager = MetadataManager(marquez_url="http://localhost:5000")

    @patch('lineage.metadata_manager.requests.Session')
    def test_complete_metadata_workflow(self, mock_session_class):
        """测试完整的元数据工作流"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟成功响应
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"name": "test", "description": "test"}
        mock_session.put.return_value = mock_response
        mock_session.get.return_value = mock_response
        mock_session.post.return_value = mock_response

        # 1. 创建命名空间
        self.manager.create_namespace(
            name="football_prediction",
            description="Football prediction platform",
            owner_name="data_team"
        )

        # 2. 创建数据集
        self.manager.create_dataset(
            namespace="football_prediction",
            name="matches",
            description="Football match data",
            schema_fields=[
                {"name": "id", "type": "INTEGER"},
                {"name": "home_team", "type": "VARCHAR"},
                {"name": "away_team", "type": "VARCHAR"}
            ],
            tags=["football", "matches"]
        )

        # 3. 创建作业
        self.manager.create_job(
            namespace="football_prediction",
            name="data_processing",
            description="Process football data",
            job_type="BATCH",
            input_datasets=[
                {"namespace": "football_prediction", "name": "raw_matches"}
            ],
            output_datasets=[
                {"namespace": "football_prediction", "name": "matches"}
            ]
        )

        # 4. 添加标签
        self.manager.add_dataset_tag(
            namespace="football_prediction",
            name="matches",
            tag="processed"
        )

        # 5. 获取血缘
        lineage = self.manager.get_dataset_lineage(
            namespace="football_prediction",
            name="matches"
        )

        # 6. 搜索数据集
        search_results = self.manager.search_datasets(
            query="football",
            namespace="football_prediction"
        )

        # 7. 获取版本历史
        versions = self.manager.get_dataset_versions(
            namespace="football_prediction",
            name="matches"
        )

        # 8. 获取作业运行历史
        runs = self.manager.get_job_runs(
            namespace="football_prediction",
            name="data_processing"
        )

        # 验证所有操作都成功
        assert mock_session.put.call_count >= 3  # 创建操作
        assert mock_session.get.call_count >= 3  # 查询操作
        assert mock_session.post.call_count >= 1  # 标签操作

    @patch('lineage.metadata_manager.requests.Session')
    def test_error_recovery_workflow(self, mock_session_class):
        """测试错误恢复工作流"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟部分失败
        call_count = 0
        def mock_put(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # 第一个调用失败
                raise Exception("Temporary failure")
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"name": "test"}
            return mock_response

        mock_session.put.side_effect = mock_put

        # 第一个操作失败
        with pytest.raises(Exception):
            self.manager.create_namespace("test_namespace")

        # 第二个操作成功
        result = self.manager.create_namespace("another_namespace")
        assert result is not None

        # 验证调用了两次
        assert call_count == 2

    @patch('lineage.metadata_manager.requests.Session')
    def test_concurrent_operations(self, mock_session_class):
        """测试并发操作"""
        import threading
        import time

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 模拟成功响应
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"name": "test", "description": "test"}
        mock_session.put.return_value = mock_response

        results = []

        def create_namespace(i):
            try:
                result = self.manager.create_namespace(f"namespace_{i}")
                results.append(result)
            except Exception as e:
                results.append(e)

        # 创建多个线程并发执行
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_namespace, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有操作都成功
        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)

        # 验证API调用次数
        assert mock_session.put.call_count == 5

    def test_performance_and_scalability(self):
        """测试性能和可扩展性"""
        import time

        # 测试多次初始化的性能
        start_time = time.time()

        for _ in range(100):
            manager = MetadataManager()
            assert manager is not None

        end_time = time.time()
        initialization_time = end_time - start_time

        # 验证初始化时间在合理范围内
        assert initialization_time < 5.0  # 100次初始化应该在5秒内完成


if __name__ == "__main__":
    pytest.main([__file__, "-v"])