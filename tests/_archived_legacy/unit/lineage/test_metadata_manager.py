from src.lineage.metadata_manager import MetadataManager
from unittest.mock import Mock, patch
import pytest

"""
Unit tests for metadata manager module.:

Tests for src/lineage/metadata_manager.py module functions and classes.
"""

@pytest.fixture
def mock_session():
    """Mock requests session."""
    session = Mock()
    session.headers = {"Content-Type[: "application/json"", "Accept[" "]application/json]}": return session["""
@pytest.fixture
def metadata_manager():
    "]""Create a MetadataManager instance for testing."""
    with patch("requests.Session[") as mock_session_class:": mock_session_instance = Mock()": mock_session_instance.headers = {""
            "]Content-Type[: "application/json[","]"""
            "]Accept[: "application/json["}"]": mock_session_class.return_value = mock_session_instance[": manager = MetadataManager(marquez_url="]]http://test5000[")": manager.session = mock_session_instance[": return manager[": class TestMetadataManagerInitialization:"
    "]]]""Test cases for MetadataManager initialization."""
    def test_init_default_url(self):
        """Test initialization with default URL."""
        with patch("requests.Session[") as mock_session_class:": mock_session_instance = Mock()": mock_session_instance.headers = {}": mock_session_class.return_value = mock_session_instance"
            manager = MetadataManager()
            assert manager.marquez_url =="]http//localhost5000[" assert manager.base_url =="]http//localhost5000[" assert manager.api_url =="]http//localhost5000/api/v1/" assert manager.session ==mock_session_instance[""""
    def test_init_custom_url(self):
        "]""Test initialization with custom URL."""
        with patch("requests.Session[") as mock_session_class:": mock_session_instance = Mock()": mock_session_instance.headers = {}": mock_session_class.return_value = mock_session_instance"
            manager = MetadataManager(marquez_url="]http://custom8080[")": assert manager.marquez_url =="]http//custom8080[" assert manager.base_url =="]http//custom8080[" assert manager.api_url =="]http//custom8080/api/v1/" def test_session_headers("
    """"
        """Test that session headers are properly set."""
        with patch("requests.Session[") as mock_session_class:": mock_session_instance = Mock()": mock_session_class.return_value = mock_session_instance[": MetadataManager()"
            expected_headers = {
                "]]Content-Type[: "application/json[","]"""
                "]Accept[: "application/json["}"]": mock_session_instance.headers.update.assert_called_once_with(": expected_headers"
            )
class TestCreateNamespace:
    "]""Test cases for create_namespace method."""
    def test_create_namespace_success(self, metadata_manager):
        """Test successful namespace creation."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name[": ["]test_namespace[",""""
            "]description[: "Test namespace[","]"""
            "]ownerName[": ["]test_owner[",""""
            "]createdAt[: "2024-01-01T00:00:00Z["}"]": metadata_manager.session.post.return_value = mock_response[": result = metadata_manager.create_namespace("
            name="]]test_namespace[", description="]Test namespace[", owner_name="]test_owner["""""
        )
        # Verify the call
        expected_url = "]http://test5000/api/v1/namespaces[": expected_data = {""""
            "]name[": ["]test_namespace[",""""
            "]description[: "Test namespace[","]"""
            "]ownerName[": ["]test_owner["}": metadata_manager.session.post.assert_called_once_with(": expected_url, json=expected_data[""
        )
        # Verify result
        assert result["]]name["] =="]test_namespace[" assert result["]description["] =="]Test namespace[" assert result["]ownerName["] =="]test_owner[" def test_create_namespace_minimal("
    """"
        "]""Test namespace creation with minimal parameters."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name[": ["]minimal_namespace["}": metadata_manager.session.post.return_value = mock_response[": result = metadata_manager.create_namespace(name="]]minimal_namespace[")": expected_data = {"]name[": ["]minimal_namespace["}": metadata_manager.session.post.assert_called_once_with("""
            "]http://test:5000/api/v1/namespaces[", json=expected_data[""""
        )
        assert result["]]name["] =="]minimal_namespace[" def test_create_namespace_http_error("
    """"
        "]""Test namespace creation with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.raise_for_status.side_effect = Exception(
            "Namespace already exists["""""
        )
        metadata_manager.session.post.return_value = mock_response
        with pytest.raises(Exception, match = "]Namespace already exists[")": metadata_manager.create_namespace(name="]existing_namespace[")": def test_create_namespace_connection_error(self, metadata_manager):"""
        "]""Test namespace creation with connection error."""
        metadata_manager.session.post.side_effect = Exception("Connection failed[")": with pytest.raises(Exception, match = "]Connection failed[")": metadata_manager.create_namespace(name="]test_namespace[")": class TestGetNamespace:"""
    "]""Test cases for get_namespace method."""
    def test_get_namespace_success(self, metadata_manager):
        """Test successful namespace retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name[": ["]test_namespace[",""""
            "]description[: "Test namespace[","]"""
            "]ownerName[": ["]test_owner["}": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_namespace("]]test_namespace[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert result["]name["] =="]test_namespace[" def test_get_namespace_not_found("
    """"
        "]""Test namespace retrieval when not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found[")": metadata_manager.session.get.return_value = mock_response[": with pytest.raises(Exception, match = "]]Not found[")": metadata_manager.get_namespace("]nonexistent_namespace[")": class TestListNamespaces:"""
    "]""Test cases for list_namespaces method."""
    def test_list_namespaces_success(self, metadata_manager):
        """Test successful namespace listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "namespaces[": [""""
                {"]name[: "ns1"", "description]},""""
                {"name[: "ns2"", "description]}]""""
        }
        metadata_manager.session.get.return_value = mock_response
        result = metadata_manager.list_namespaces()
        expected_url = "http://test5000/api/v1/namespaces[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert len(result["]namespaces["]) ==2[" assert result["]]namespaces["][0]["]name["] =="]ns1[" def test_list_namespaces_empty("
    """"
        "]""Test namespace listing when no namespaces exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"namespaces[" []}": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.list_namespaces()": assert len(result["]]namespaces["]) ==0[" class TestCreateDataset:"""
    "]]""Test cases for create_dataset method."""
    def test_create_dataset_success(self, metadata_manager):
        """Test successful dataset creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name[": ["]test_dataset[",""""
            "]namespace[": ["]test_namespace[",""""
            "]description[: "Test dataset["}"]": metadata_manager.session.post.return_value = mock_response[": result = metadata_manager.create_dataset("
            namespace="]]test_namespace[", name="]test_dataset[", description="]Test dataset["""""
        )
        expected_url = "]http://test5000/api/v1/namespaces/test_namespace/datasets[": expected_data = {"]name[: "test_dataset"", "description]}": metadata_manager.session.post.assert_called_once_with(": expected_url, json=expected_data[""
        )
        assert result["]name["] =="]test_dataset[" def test_create_dataset_with_fields("
    """"
        "]""Test dataset creation with schema fields."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name[": ["]test_dataset["}": metadata_manager.session.post.return_value = mock_response[": fields = [{"]]name[: "id"", "type]}]": metadata_manager.create_dataset(": namespace="test_namespace[", name="]test_dataset[", fields=fields[""""
        )
        expected_data = {"]]name[: "test_dataset"", "fields] fields}": metadata_manager.session.post.assert_called_once_with("""
            "http://test:5000/api/v1/namespaces/test_namespace/datasets[",": json=expected_data)": class TestGetDataset:""
    "]""Test cases for get_dataset method."""
    def test_get_dataset_success(self, metadata_manager):
        """Test successful dataset retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name[": ["]test_dataset[",""""
            "]namespace[": ["]test_namespace[",""""
            "]description[: "Test dataset["}"]": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_dataset("]]test_namespace[", "]test_dataset[")": expected_url = ("""
            "]http://test:5000/api/v1/namespaces/test_namespace/datasets/test_dataset["""""
        )
        metadata_manager.session.get.assert_called_once_with(expected_url)
        assert result["]name["] =="]test_dataset[" class TestListDatasets:""""
    "]""Test cases for list_datasets method."""
    def test_list_datasets_success(self, metadata_manager):
        """Test successful dataset listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "datasets[": [""""
                {"]name[: "dataset1"", "namespace]},""""
                {"name[: "dataset2"", "namespace]}]""""
        }
        metadata_manager.session.get.return_value = mock_response
        result = metadata_manager.list_datasets("test_namespace[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace/datasets[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert len(result["]datasets["]) ==2[" class TestCreateJob:"""
    "]]""Test cases for create_job method."""
    def test_create_job_success(self, metadata_manager):
        """Test successful job creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name[": ["]test_job[",""""
            "]namespace[": ["]test_namespace[",""""
            "]description[: "Test job[","]"""
            "]type[": ["]BATCH["}": metadata_manager.session.post.return_value = mock_response[": result = metadata_manager.create_job(": namespace="]]test_namespace[",": name="]test_job[",": description="]Test job[",": job_type="]BATCH[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs[": expected_data = {"]name[: "test_job"", "description]}": metadata_manager.session.post.assert_called_once_with(": expected_url, json=expected_data[""
        )
        assert result["]name["] =="]test_job[" class TestGetJob:""""
    "]""Test cases for get_job method."""
    def test_get_job_success(self, metadata_manager):
        """Test successful job retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name[": ["]test_job[",""""
            "]namespace[": ["]test_namespace[",""""
            "]type[": ["]BATCH["}": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_job("]]test_namespace[", "]test_job[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs/test_job[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert result["]name["] =="]test_job[" class TestListJobs:""""
    "]""Test cases for list_jobs method."""
    def test_list_jobs_success(self, metadata_manager):
        """Test successful job listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs[": [""""
                {"]name[: "job1"", "namespace]},""""
                {"name[: "job2"", "namespace]}]""""
        }
        metadata_manager.session.get.return_value = mock_response
        result = metadata_manager.list_jobs("test_namespace[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert len(result["]jobs["]) ==2[" class TestCreateRun:"""
    "]]""Test cases for create_run method."""
    def test_create_run_success(self, metadata_manager):
        """Test successful run creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id[": ["]test_run_id[",""""
            "]nominalStartTime[: "2024-01-01T00:00:00Z[","]"""
            "]nominalEndTime[: "2024-01-01T01:00:00Z["}"]": metadata_manager.session.post.return_value = mock_response[": result = metadata_manager.create_run("
            namespace="]]test_namespace[",": job_name="]test_job[",": nominal_start_time = "]2024-01-01T00:0000Z[",": nominal_end_time = "]2024-01-01T01:0000Z[")": expected_url = ("""
            "]http://test:5000/api/v1/namespaces/test_namespace/jobs/test_job/runs["""""
        )
        expected_data = {
            "]nominalStartTime[: "2024-01-01T00:00:00Z[","]"""
            "]nominalEndTime[: "2024-01-01T01:00:00Z["}"]": metadata_manager.session.post.assert_called_once_with(": expected_url, json=expected_data"
        )
        assert result["]id["] =="]test_run_id[" class TestGetRun:""""
    "]""Test cases for get_run method."""
    def test_get_run_success(self, metadata_manager):
        """Test successful run retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id[": ["]test_run_id[",""""
            "]nominalStartTime[: "2024-01-01T00:00:00Z["}"]": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_run("]]test_namespace[", "]test_job[", "]test_run_id[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs/test_job/runs/test_run_id[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert result["]id["] =="]test_run_id[" class TestListRuns:""""
    "]""Test cases for list_runs method."""
    def test_list_runs_success(self, metadata_manager):
        """Test successful run listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "runs[": [""""
                {"]id[: "run1"", "nominalStartTime]},""""
                {"id[: "run2"", "nominalStartTime]}]""""
        }
        metadata_manager.session.get.return_value = mock_response
        result = metadata_manager.list_runs("test_namespace[", "]test_job[")": expected_url = ("""
            "]http://test:5000/api/v1/namespaces/test_namespace/jobs/test_job/runs["""""
        )
        metadata_manager.session.get.assert_called_once_with(expected_url)
        assert len(result["]runs["]) ==2[" class TestGetLatestRun:"""
    "]]""Test cases for get_latest_run method."""
    def test_get_latest_run_success(self, metadata_manager):
        """Test successful latest run retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id[": ["]latest_run_id[",""""
            "]nominalStartTime[: "2024-01-01T00:00:00Z["}"]": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_latest_run("]]test_namespace[", "]test_job[")": expected_url = "]http://test5000/api/v1/namespaces/test_namespace/jobs/test_job/runs/latest[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert result["]id["] =="]latest_run_id[" class TestSearchMetadata:""""
    "]""Test cases for search_metadata method."""
    def test_search_metadata_success(self, metadata_manager):
        """Test successful metadata search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results[": [""""
                {"]name[: "dataset1"", "type]},""""
                {"name[: "job1"", "type]}]""""
        }
        metadata_manager.session.get.return_value = mock_response
        result = metadata_manager.search_metadata("test_query[")": expected_url = "]http://test5000/api/v1/search[": expected_params = {"]q[": ["]test_query["}": metadata_manager.session.get.assert_called_once_with(": expected_url, params=expected_params[""
        )
        assert len(result["]]results["]) ==2[" def test_search_metadata_with_filters(self, metadata_manager):"""
        "]]""Test metadata search with filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results[" []}": metadata_manager.session.get.return_value = mock_response[": filters = {"]]namespace[: "test_namespace"", "type]}": metadata_manager.search_metadata("test_query[", filters=filters)": expected_params = {"""
            "]q[": ["]test_query[",""""
            "]namespace[": ["]test_namespace[",""""
            "]type[": ["]dataset["}": metadata_manager.session.get.assert_called_once_with("""
            "]http://test:5000/api/v1/search[", params=expected_params[""""
        )
class TestHealthCheck:
    "]]""Test cases for health_check method."""
    def test_health_check_success(self, metadata_manager):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status[: "healthy"", "version]}": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.health_check()": expected_url = "]http://test5000/api/v1/health[": metadata_manager.session.get.assert_called_once_with(expected_url)": assert result["]status["] =="]healthy[" def test_health_check_unhealthy("
    """"
        "]""Test health check when service is unhealthy."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"status[": ["]unhealthy["}": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.health_check()": assert result["]]status["] =="]unhealthy[" class TestMetadataManagerErrorHandling:""""
    "]""Test cases for error handling in MetadataManager."""
    def test_http_error_handling(self, metadata_manager):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal server error[")": metadata_manager.session.get.return_value = mock_response[": with pytest.raises(Exception, match = "]]Internal server error[")": metadata_manager.get_namespace("]test_namespace[")": def test_connection_error_handling(self, metadata_manager):"""
        "]""Test connection error handling."""
        metadata_manager.session.get.side_effect = Exception("Connection refused[")": with pytest.raises(Exception, match = "]Connection refused[")": metadata_manager.get_namespace("]test_namespace[")": def test_timeout_error_handling(self, metadata_manager):"""
        "]""Test timeout error handling."""
        metadata_manager.session.get.side_effect = Exception("Request timeout[")": with pytest.raises(Exception, match = "]Request timeout[")": metadata_manager.get_namespace("]test_namespace[")": class TestMetadataManagerEdgeCases:"""
    "]""Test cases for edge cases in MetadataManager."""
    def test_empty_string_parameters(self, metadata_manager):
        """Test handling of empty string parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name[" "]"}": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_namespace("]test_namespace[")""""
        # Should handle empty results gracefully
        assert result is not None
    def test_none_parameters(self, metadata_manager):
        "]""Test handling of None parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        metadata_manager.session.get.return_value = mock_response
        result = metadata_manager.get_namespace(None)
        # Should handle None parameters gracefully
        assert result is not None
    def test_special_characters_in_parameters(self, metadata_manager):
        """Test handling of special characters in parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name[: "test@namespace["}"]": metadata_manager.session.get.return_value = mock_response[": result = metadata_manager.get_namespace("]]test@namespace[")": assert result["]name["] =="]test@namespace[" class TestMetadataManagerModule:""""
    "]""Test cases for metadata manager module imports and functionality."""
    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        from src.lineage import metadata_manager
        assert hasattr(metadata_manager, "MetadataManager[")" def test_class_methods_exist(self):"""
        "]""Test that all expected methods exist on the class."""
        methods = [
            "create_namespace[",""""
            "]get_namespace[",""""
            "]list_namespaces[",""""
            "]create_dataset[",""""
            "]get_dataset[",""""
            "]list_datasets[",""""
            "]create_job[",""""
            "]get_job[",""""
            "]list_jobs[",""""
            "]create_run[",""""
            "]get_run[",""""
            "]list_runs[",""""
            "]get_latest_run[",""""
            "]search_metadata[",""""
            "]health_check["]"]": for method in methods:": assert hasattr(MetadataManager, method)"
        from src.lineage import metadata_manager