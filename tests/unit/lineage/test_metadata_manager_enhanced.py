"""
Enhanced test file for metadata_manager.py lineage module
Provides comprehensive coverage for the actual MetadataManager implementation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import json
import uuid

# Import from src directory
from src.lineage.metadata_manager import MetadataManager


class TestMetadataManager:
    """Test MetadataManager class methods and functionality"""

    @pytest.fixture
    def metadata_manager(self):
        """Create MetadataManager instance for testing"""
        with patch('src.lineage.metadata_manager.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            manager = MetadataManager()
            manager._session = mock_session
            manager.logger = Mock()
            return manager

    @pytest.fixture
    def mock_dataset(self):
        """Create mock Dataset object for testing"""
        dataset = Mock()
        dataset.id = "test_dataset_123"
        dataset.name = "test_dataset"
        dataset.namespace = "test_namespace"
        dataset.description = "Test dataset description"
        dataset.created_at = datetime.now()
        dataset.updated_at = datetime.now()
        return dataset

    @pytest.fixture
    def mock_job(self):
        """Create mock Job object for testing"""
        job = Mock()
        job.id = "test_job_123"
        job.name = "test_job"
        job.namespace = "test_namespace"
        job.description = "Test job description"
        job.input_datasets = []
        job.output_datasets = []
        job.created_at = datetime.now()
        job.updated_at = datetime.now()
        return job

    @pytest.fixture
    def mock_run(self):
        """Create mock Run object for testing"""
        run = Mock()
        run.id = "test_run_123"
        run.job_id = "test_job_123"
        run.namespace = "test_namespace"
        run.status = "RUNNING"
        run.start_time = datetime.now()
        run.end_time = None
        run.facets = {}
        return run

    def test_metadata_manager_init(self, metadata_manager):
        """Test MetadataManager initialization"""
        assert metadata_manager is not None
        assert metadata_manager.base_url == "http://localhost:5000"
        assert metadata_manager._session is not None

    def test_metadata_manager_init_with_custom_url(self):
        """Test MetadataManager initialization with custom URL"""
        with patch('src.lineage.metadata_manager.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            manager = MetadataManager(base_url="http://custom:8080/api/v1")

            assert manager.base_url == "http://custom:8080/api/v1"

    def test_create_namespace_success(self, metadata_manager):
        """Test successful namespace creation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_namespace("test_namespace", "Test namespace description")

        assert result is True
        metadata_manager._session.post.assert_called_once()
        assert "test_namespace" in metadata_manager._namespace_cache

    def test_create_namespace_already_exists(self, metadata_manager):
        """Test namespace creation when namespace already exists"""
        # Add namespace to cache
        metadata_manager._namespace_cache["test_namespace"] = {
            "name": "test_namespace",
            "description": "Existing namespace"
        }

        result = metadata_manager.create_namespace("test_namespace", "Test namespace description")

        assert result is True
        # Should not make API call since namespace is cached
        metadata_manager._session.post.assert_not_called()

    def test_create_namespace_api_error(self, metadata_manager):
        """Test namespace creation with API error"""
        mock_response = Mock()
        mock_response.status_code = 409  # Conflict
        mock_response.text = "Namespace already exists"
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_namespace("test_namespace", "Test namespace description")

        assert result is False
        metadata_manager.logger.error.assert_called_once()

    def test_create_source_success(self, metadata_manager):
        """Test successful source creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "test_source",
            "type": "POSTGRESQL",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_source("test_source", "POSTGRESQL", "Test source")

        assert result is True
        metadata_manager._session.post.assert_called_once()

    def test_create_source_api_error(self, metadata_manager):
        """Test source creation with API error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid source type"
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_source("test_source", "INVALID", "Test source")

        assert result is False
        metadata_manager.logger.error.assert_called_once()

    def test_create_dataset_success(self, metadata_manager):
        """Test successful dataset creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "test_dataset",
            "namespace": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_dataset(
            "test_namespace", "test_dataset", "test_source", "Test dataset"
        )

        assert result is True
        metadata_manager._session.post.assert_called_once()

    def test_create_dataset_auto_create_namespace(self, metadata_manager):
        """Test dataset creation with automatic namespace creation"""
        # Mock namespace creation success
        mock_namespace_response = Mock()
        mock_namespace_response.status_code = 201
        mock_namespace_response.json.return_value = {
            "name": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Mock dataset creation success
        mock_dataset_response = Mock()
        mock_dataset_response.status_code = 201
        mock_dataset_response.json.return_value = {
            "name": "test_dataset",
            "namespace": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        metadata_manager._session.post.side_effect = [mock_namespace_response, mock_dataset_response]

        result = metadata_manager.create_dataset(
            "test_namespace", "test_dataset", "test_source", "Test dataset"
        )

        assert result is True
        assert metadata_manager._session.post.call_count == 2
        assert "test_namespace" in metadata_manager._namespace_cache

    def test_create_dataset_namespace_creation_fails(self, metadata_manager):
        """Test dataset creation when namespace creation fails"""
        # Mock namespace creation failure
        mock_namespace_response = Mock()
        mock_namespace_response.status_code = 400
        mock_namespace_response.text = "Invalid namespace"
        metadata_manager._session.post.return_value = mock_namespace_response

        result = metadata_manager.create_dataset(
            "test_namespace", "test_dataset", "test_source", "Test dataset"
        )

        assert result is False
        metadata_manager.logger.error.assert_called_once()

    def test_create_job_success(self, metadata_manager):
        """Test successful job creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "test_job",
            "namespace": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_job(
            "test_namespace", "test_job", "Test job", ["input_dataset"], ["output_dataset"]
        )

        assert result is True
        metadata_manager._session.post.assert_called_once()

    def test_create_job_auto_create_namespace(self, metadata_manager):
        """Test job creation with automatic namespace creation"""
        # Mock namespace and job creation success
        mock_namespace_response = Mock()
        mock_namespace_response.status_code = 201
        mock_namespace_response.json.return_value = {
            "name": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        mock_job_response = Mock()
        mock_job_response.status_code = 201
        mock_job_response.json.return_value = {
            "name": "test_job",
            "namespace": "test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        metadata_manager._session.post.side_effect = [mock_namespace_response, mock_job_response]

        result = metadata_manager.create_job(
            "test_namespace", "test_job", "Test job", ["input_dataset"], ["output_dataset"]
        )

        assert result is True
        assert metadata_manager._session.post.call_count == 2

    def test_create_run_success(self, metadata_manager):
        """Test successful run creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "test_run_123",
            "nominalStartTime": "2023-01-01T00:00:00Z",
            "nominalEndTime": "2023-01-01T01:00:00Z"
        }
        metadata_manager._session.post.return_value = mock_response

        result = metadata_manager.create_run(
            "test_namespace", "test_job", "test_run_123",
            "2023-01-01T00:00:00Z", "2023-01-01T01:00:00Z"
        )

        assert result is True
        metadata_manager._session.post.assert_called_once()

    def test_update_run_success(self, metadata_manager):
        """Test successful run update"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_run_123",
            "status": "COMPLETED",
            "endedAt": "2023-01-01T01:00:00Z"
        }
        metadata_manager._session.put.return_value = mock_response

        facets = {"test_facet": {"value": "test_value"}}
        result = metadata_manager.update_run(
            "test_namespace", "test_job", "test_run_123",
            "COMPLETED", facets
        )

        assert result is True
        metadata_manager._session.put.assert_called_once()

    def test_get_dataset_success(self, metadata_manager):
        """Test successful dataset retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test_dataset",
            "namespace": "test_namespace",
            "description": "Test dataset",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.get_dataset("test_namespace", "test_dataset")

        assert result is not None
        assert result["name"] == "test_dataset"
        assert result["namespace"] == "test_namespace"
        metadata_manager._session.get.assert_called_once()

    def test_get_dataset_not_found(self, metadata_manager):
        """Test dataset retrieval when dataset not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Dataset not found"
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.get_dataset("test_namespace", "nonexistent_dataset")

        assert result is None
        metadata_manager.logger.warning.assert_called_once()

    def test_get_job_success(self, metadata_manager):
        """Test successful job retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test_job",
            "namespace": "test_namespace",
            "description": "Test job",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.get_job("test_namespace", "test_job")

        assert result is not None
        assert result["name"] == "test_job"
        assert result["namespace"] == "test_namespace"

    def test_get_job_not_found(self, metadata_manager):
        """Test job retrieval when job not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Job not found"
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.get_job("test_namespace", "nonexistent_job")

        assert result is None
        metadata_manager.logger.warning.assert_called_once()

    def test_get_run_success(self, metadata_manager):
        """Test successful run retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_run_123",
            "namespace": "test_namespace",
            "jobName": "test_job",
            "status": "COMPLETED",
            "startedAt": "2023-01-01T00:00:00Z",
            "endedAt": "2023-01-01T01:00:00Z"
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.get_run("test_namespace", "test_job", "test_run_123")

        assert result is not None
        assert result["id"] == "test_run_123"
        assert result["status"] == "COMPLETED"

    def test_get_run_not_found(self, metadata_manager):
        """Test run retrieval when run not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Run not found"
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.get_run("test_namespace", "test_job", "nonexistent_run")

        assert result is None
        metadata_manager.logger.warning.assert_called_once()

    def test_search_datasets_success(self, metadata_manager):
        """Test successful dataset search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "datasets": [
                {
                    "name": "dataset1",
                    "namespace": "test_namespace",
                    "description": "First dataset"
                },
                {
                    "name": "dataset2",
                    "namespace": "test_namespace",
                    "description": "Second dataset"
                }
            ]
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.search_datasets("test_namespace", "dataset")

        assert len(result) == 2
        assert result[0]["name"] == "dataset1"
        assert result[1]["name"] == "dataset2"

    def test_search_datasets_empty_result(self, metadata_manager):
        """Test dataset search with no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"datasets": []}
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.search_datasets("test_namespace", "nonexistent")

        assert result == []

    def test_search_jobs_success(self, metadata_manager):
        """Test successful job search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [
                {
                    "name": "job1",
                    "namespace": "test_namespace",
                    "description": "First job"
                },
                {
                    "name": "job2",
                    "namespace": "test_namespace",
                    "description": "Second job"
                }
            ]
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.search_jobs("test_namespace", "job")

        assert len(result) == 2
        assert result[0]["name"] == "job1"
        assert result[1]["name"] == "job2"

    def test_list_datasets_success(self, metadata_manager):
        """Test successful dataset listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "datasets": [
                {"name": "dataset1", "namespace": "test_namespace"},
                {"name": "dataset2", "namespace": "test_namespace"}
            ]
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.list_datasets("test_namespace")

        assert len(result) == 2
        assert result[0]["name"] == "dataset1"
        assert result[1]["name"] == "dataset2"

    def test_list_datasets_with_limit(self, metadata_manager):
        """Test dataset listing with limit"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "datasets": [{"name": "dataset1", "namespace": "test_namespace"}]
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.list_datasets("test_namespace", limit=1)

        assert len(result) == 1
        assert result[0]["name"] == "dataset1"
        # Verify limit parameter is passed
        call_args = metadata_manager._session.get.call_args[0][0]
        assert "limit=1" in call_args

    def test_list_jobs_success(self, metadata_manager):
        """Test successful job listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [
                {"name": "job1", "namespace": "test_namespace"},
                {"name": "job2", "namespace": "test_namespace"}
            ]
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.list_jobs("test_namespace")

        assert len(result) == 2
        assert result[0]["name"] == "job1"
        assert result[1]["name"] == "job2"

    def test_list_runs_success(self, metadata_manager):
        """Test successful run listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "runs": [
                {"id": "run1", "jobName": "test_job", "status": "COMPLETED"},
                {"id": "run2", "jobName": "test_job", "status": "FAILED"}
            ]
        }
        metadata_manager._session.get.return_value = mock_response

        result = metadata_manager.list_runs("test_namespace", "test_job")

        assert len(result) == 2
        assert result[0]["id"] == "run1"
        assert result[1]["id"] == "run2"

    def test_delete_dataset_success(self, metadata_manager):
        """Test successful dataset deletion"""
        mock_response = Mock()
        mock_response.status_code = 204
        metadata_manager._session.delete.return_value = mock_response

        result = metadata_manager.delete_dataset("test_namespace", "test_dataset")

        assert result is True
        metadata_manager._session.delete.assert_called_once()

    def test_delete_dataset_not_found(self, metadata_manager):
        """Test dataset deletion when dataset not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Dataset not found"
        metadata_manager._session.delete.return_value = mock_response

        result = metadata_manager.delete_dataset("test_namespace", "nonexistent_dataset")

        assert result is False
        metadata_manager.logger.warning.assert_called_once()

    def test_delete_job_success(self, metadata_manager):
        """Test successful job deletion"""
        mock_response = Mock()
        mock_response.status_code = 204
        metadata_manager._session.delete.return_value = mock_response

        result = metadata_manager.delete_job("test_namespace", "test_job")

        assert result is True

    def test_delete_namespace_success(self, metadata_manager):
        """Test successful namespace deletion"""
        mock_response = Mock()
        mock_response.status_code = 204
        metadata_manager._session.delete.return_value = mock_response

        result = metadata_manager.delete_namespace("test_namespace")

        assert result is True
        # Should remove from cache
        assert "test_namespace" not in metadata_manager._namespace_cache

    def test_delete_namespace_from_cache(self, metadata_manager):
        """Test namespace deletion removes from cache"""
        # Add namespace to cache
        metadata_manager._namespace_cache["test_namespace"] = {"name": "test_namespace"}

        mock_response = Mock()
        mock_response.status_code = 204
        metadata_manager._session.delete.return_value = mock_response

        result = metadata_manager.delete_namespace("test_namespace")

        assert result is True
        assert "test_namespace" not in metadata_manager._namespace_cache


class TestMetadataManagerEdgeCases:
    """Edge case tests for MetadataManager"""

    def test_create_namespace_empty_name(self, metadata_manager):
        """Test namespace creation with empty name"""
        with pytest.raises(ValueError):
            metadata_manager.create_namespace("", "Test description")

    def test_create_dataset_empty_namespace(self, metadata_manager):
        """Test dataset creation with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.create_dataset("", "test_dataset", "test_source", "Test dataset")

    def test_create_dataset_empty_name(self, metadata_manager):
        """Test dataset creation with empty name"""
        with pytest.raises(ValueError):
            metadata_manager.create_dataset("test_namespace", "", "test_source", "Test dataset")

    def test_create_job_empty_namespace(self, metadata_manager):
        """Test job creation with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.create_job("", "test_job", "Test job", [], [])

    def test_create_job_empty_name(self, metadata_manager):
        """Test job creation with empty name"""
        with pytest.raises(ValueError):
            metadata_manager.create_job("test_namespace", "", "Test job", [], [])

    def test_create_run_empty_namespace(self, metadata_manager):
        """Test run creation with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.create_run("", "test_job", "test_run", "2023-01-01T00:00:00Z")

    def test_update_run_invalid_status(self, metadata_manager):
        """Test run update with invalid status"""
        with pytest.raises(ValueError):
            metadata_manager.update_run(
                "test_namespace", "test_job", "test_run", "INVALID_STATUS"
            )

    def test_get_dataset_empty_namespace(self, metadata_manager):
        """Test dataset retrieval with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.get_dataset("", "test_dataset")

    def test_get_dataset_empty_name(self, metadata_manager):
        """Test dataset retrieval with empty name"""
        with pytest.raises(ValueError):
            metadata_manager.get_dataset("test_namespace", "")

    def test_search_datasets_empty_namespace(self, metadata_manager):
        """Test dataset search with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.search_datasets("", "query")

    def test_list_datasets_empty_namespace(self, metadata_manager):
        """Test dataset listing with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.list_datasets("")

    def test_list_datasets_invalid_limit(self, metadata_manager):
        """Test dataset listing with invalid limit"""
        with pytest.raises(ValueError):
            metadata_manager.list_datasets("test_namespace", limit=-1)

    def test_delete_dataset_empty_namespace(self, metadata_manager):
        """Test dataset deletion with empty namespace"""
        with pytest.raises(ValueError):
            metadata_manager.delete_dataset("", "test_dataset")

    def test_delete_dataset_empty_name(self, metadata_manager):
        """Test dataset deletion with empty name"""
        with pytest.raises(ValueError):
            metadata_manager.delete_dataset("test_namespace", "")

    def test_connection_error_handling(self, metadata_manager):
        """Test handling of connection errors"""
        import requests
        metadata_manager._session.post.side_effect = requests.ConnectionError("Connection failed")

        result = metadata_manager.create_namespace("test_namespace", "Test description")

        assert result is False
        metadata_manager.logger.error.assert_called_once()

    def test_timeout_error_handling(self, metadata_manager):
        """Test handling of timeout errors"""
        import requests
        metadata_manager._session.get.side_effect = requests.Timeout("Request timeout")

        result = metadata_manager.get_dataset("test_namespace", "test_dataset")

        assert result is None
        metadata_manager.logger.warning.assert_called_once()

    def test_request_exception_handling(self, metadata_manager):
        """Test handling of general request exceptions"""
        import requests
        metadata_manager._session.put.side_effect = requests.RequestException("Request failed")

        result = metadata_manager.update_run(
            "test_namespace", "test_job", "test_run", "COMPLETED"
        )

        assert result is False
        metadata_manager.logger.error.assert_called_once()


class TestMetadataManagerIntegration:
    """Integration tests for MetadataManager"""

    def test_full_namespace_lifecycle(self, metadata_manager):
        """Test complete namespace lifecycle"""
        # Create namespace
        mock_create_response = Mock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = {
            "name": "integration_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }
        metadata_manager._session.post.return_value = mock_create_response

        result = metadata_manager.create_namespace("integration_namespace", "Integration test namespace")
        assert result is True
        assert "integration_namespace" in metadata_manager._namespace_cache

        # Mock successful deletion
        mock_delete_response = Mock()
        mock_delete_response.status_code = 204
        metadata_manager._session.delete.return_value = mock_delete_response

        # Delete namespace
        result = metadata_manager.delete_namespace("integration_namespace")
        assert result is True
        assert "integration_namespace" not in metadata_manager._namespace_cache

    def test_full_dataset_lifecycle(self, metadata_manager):
        """Test complete dataset lifecycle"""
        # Create namespace
        mock_namespace_response = Mock()
        mock_namespace_response.status_code = 201
        mock_namespace_response.json.return_value = {
            "name": "dataset_test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create source
        mock_source_response = Mock()
        mock_source_response.status_code = 201
        mock_source_response.json.return_value = {
            "name": "test_source",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create dataset
        mock_dataset_response = Mock()
        mock_dataset_response.status_code = 201
        mock_dataset_response.json.return_value = {
            "name": "integration_dataset",
            "namespace": "dataset_test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Get dataset
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "name": "integration_dataset",
            "namespace": "dataset_test_namespace",
            "description": "Integration test dataset"
        }

        # Delete dataset
        mock_delete_response = Mock()
        mock_delete_response.status_code = 204

        metadata_manager._session.post.side_effect = [
            mock_namespace_response, mock_source_response, mock_dataset_response
        ]
        metadata_manager._session.get.return_value = mock_get_response
        metadata_manager._session.delete.return_value = mock_delete_response

        # Create dataset
        result = metadata_manager.create_dataset(
            "dataset_test_namespace", "integration_dataset",
            "test_source", "Integration test dataset"
        )
        assert result is True

        # Get dataset
        dataset = metadata_manager.get_dataset("dataset_test_namespace", "integration_dataset")
        assert dataset is not None
        assert dataset["name"] == "integration_dataset"

        # Delete dataset
        result = metadata_manager.delete_dataset("dataset_test_namespace", "integration_dataset")
        assert result is True

    def test_full_job_lifecycle(self, metadata_manager):
        """Test complete job lifecycle"""
        # Create namespace
        mock_namespace_response = Mock()
        mock_namespace_response.status_code = 201
        mock_namespace_response.json.return_value = {
            "name": "job_test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create job
        mock_job_response = Mock()
        mock_job_response.status_code = 201
        mock_job_response.json.return_value = {
            "name": "integration_job",
            "namespace": "job_test_namespace",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Get job
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "name": "integration_job",
            "namespace": "job_test_namespace",
            "description": "Integration test job"
        }

        metadata_manager._session.post.side_effect = [mock_namespace_response, mock_job_response]
        metadata_manager._session.get.return_value = mock_get_response

        # Create job
        result = metadata_manager.create_job(
            "job_test_namespace", "integration_job", "Integration test job",
            ["input_dataset"], ["output_dataset"]
        )
        assert result is True

        # Get job
        job = metadata_manager.get_job("job_test_namespace", "integration_job")
        assert job is not None
        assert job["name"] == "integration_job"

    def test_football_prediction_workflow(self, metadata_manager):
        """Test realistic football prediction workflow"""
        # Create namespace
        mock_namespace_response = Mock()
        mock_namespace_response.status_code = 201
        mock_namespace_response.json.return_value = {
            "name": "football_prediction",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create source
        mock_source_response = Mock()
        mock_source_response.status_code = 201
        mock_source_response.json.return_value = {
            "name": "postgres_source",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create datasets
        mock_dataset_response = Mock()
        mock_dataset_response.status_code = 201
        mock_dataset_response.json.return_value = {
            "name": "raw_matches",
            "namespace": "football_prediction",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create job
        mock_job_response = Mock()
        mock_job_response.status_code = 201
        mock_job_response.json.return_value = {
            "name": "match_prediction_job",
            "namespace": "football_prediction",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Create run
        mock_run_response = Mock()
        mock_run_response.status_code = 201
        mock_run_response.json.return_value = {
            "id": "prediction_run_123",
            "createdAt": "2023-01-01T00:00:00Z"
        }

        # Update run
        mock_update_response = Mock()
        mock_update_response.status_code = 200
        mock_update_response.json.return_value = {
            "id": "prediction_run_123",
            "status": "COMPLETED",
            "endedAt": "2023-01-01T01:00:00Z"
        }

        metadata_manager._session.post.side_effect = [
            mock_namespace_response, mock_source_response, mock_dataset_response,
            mock_job_response, mock_run_response
        ]
        metadata_manager._session.put.return_value = mock_update_response

        # Setup workflow
        result = metadata_manager.create_namespace("football_prediction", "Football prediction system")
        assert result is True

        result = metadata_manager.create_source("postgres_source", "POSTGRESQL", "PostgreSQL database")
        assert result is True

        result = metadata_manager.create_dataset(
            "football_prediction", "raw_matches", "postgres_source", "Raw match data"
        )
        assert result is True

        result = metadata_manager.create_job(
            "football_prediction", "match_prediction_job", "Match prediction ML job",
            ["raw_matches"], ["predictions"]
        )
        assert result is True

        result = metadata_manager.create_run(
            "football_prediction", "match_prediction_job", "prediction_run_123",
            "2023-01-01T00:00:00Z", "2023-01-01T01:00:00Z"
        )
        assert result is True

        result = metadata_manager.update_run(
            "football_prediction", "match_prediction_job", "prediction_run_123",
            "COMPLETED", {"accuracy": 0.85}
        )
        assert result is True

        # Verify workflow
        assert metadata_manager._session.post.call_count == 5
        assert metadata_manager._session.put.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])