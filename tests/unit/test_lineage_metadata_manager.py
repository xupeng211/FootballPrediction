"""
Test suite for metadata manager module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.lineage.metadata_manager import MetadataManager, get_metadata_manager


@pytest.fixture
def metadata_manager():
    """Create a metadata manager instance for testing"""
    return MetadataManager(marquez_url="http://test-marquez:5000")


def test_metadata_manager_initialization():
    """Test initialization of MetadataManager"""
    manager = MetadataManager()
    assert manager is not None
    assert manager.marquez_url == "http://localhost:5000"
    assert manager.api_url == "http://localhost:5000/api/v1/"
    assert manager.session is not None
    assert manager.session.headers["Content-Type"] == "application/json"


def test_create_namespace_success(metadata_manager):
    """Test successful namespace creation"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"name": "test_namespace", "description": "Test namespace"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    result = metadata_manager.create_namespace(
        name="test_namespace",
        description="Test namespace",
        owner_name="test_owner"
    )
    
    # Verify the session.put was called with correct parameters
    metadata_manager.session.put.assert_called_once()
    # Verify the result
    assert result["name"] == "test_namespace"


def test_create_namespace_with_exception(metadata_manager):
    """Test namespace creation with exception handling"""
    # Mock the session to raise an exception
    metadata_manager.session.put = Mock(side_effect=Exception("Network error"))
    
    with pytest.raises(Exception, match="Network error"):
        metadata_manager.create_namespace(name="test_namespace")


def test_create_dataset_success(metadata_manager):
    """Test successful dataset creation"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"name": "test_dataset", "description": "Test dataset"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    result = metadata_manager.create_dataset(
        namespace="test_namespace",
        name="test_dataset",
        description="Test dataset",
        schema_fields=[{"name": "id", "type": "INTEGER"}],
        source_name="test_source",
        tags=["test_tag"]
    )
    
    # Verify the session.put was called
    metadata_manager.session.put.assert_called_once()
    # Verify the result
    assert result["name"] == "test_dataset"


def test_create_job_success(metadata_manager):
    """Test successful job creation"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"name": "test_job", "type": "BATCH"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    result = metadata_manager.create_job(
        namespace="test_namespace",
        name="test_job",
        description="Test job",
        job_type="BATCH",
        input_datasets=[{"namespace": "ns1", "name": "ds1"}],
        output_datasets=[{"namespace": "ns2", "name": "ds2"}],
        location="test/location"
    )
    
    # Verify the session.put was called
    metadata_manager.session.put.assert_called_once()
    # Verify the result
    assert result["name"] == "test_job"


def test_get_dataset_lineage_success(metadata_manager):
    """Test successful dataset lineage retrieval"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"lineage": {"nodes": [], "edges": []}}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    result = metadata_manager.get_dataset_lineage(
        namespace="test_namespace",
        name="test_dataset",
        depth=3
    )
    
    # Verify the session.get was called
    metadata_manager.session.get.assert_called_once()
    # Verify the result
    assert "lineage" in result


def test_search_datasets_success(metadata_manager):
    """Test successful dataset search"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"results": [{"name": "test_dataset"}]}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    result = metadata_manager.search_datasets(
        query="test",
        namespace="test_namespace",
        limit=10
    )
    
    # Verify the session.get was called
    metadata_manager.session.get.assert_called_once()
    # Verify the result
    assert len(result) == 1
    assert result[0]["name"] == "test_dataset"


def test_get_dataset_versions_success(metadata_manager):
    """Test successful dataset versions retrieval"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"versions": [{"version": "v1.0"}]}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    result = metadata_manager.get_dataset_versions(
        namespace="test_namespace",
        name="test_dataset"
    )
    
    # Verify the session.get was called
    metadata_manager.session.get.assert_called_once()
    # Verify the result
    assert len(result) == 1
    assert result[0]["version"] == "v1.0"


def test_get_job_runs_success(metadata_manager):
    """Test successful job runs retrieval"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"runs": [{"id": "run1"}]}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    result = metadata_manager.get_job_runs(
        namespace="test_namespace",
        job_name="test_job",
        limit=20
    )
    
    # Verify the session.get was called
    metadata_manager.session.get.assert_called_once()
    # Verify the result
    assert len(result) == 1
    assert result[0]["id"] == "run1"


def test_add_dataset_tag_success(metadata_manager):
    """Test successful dataset tag addition"""
    # Mock the session response
    mock_response = Mock()
    mock_response.json.return_value = {"status": "success"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.post = Mock(return_value=mock_response)
    
    result = metadata_manager.add_dataset_tag(
        namespace="test_namespace",
        name="test_dataset",
        tag="test_tag"
    )
    
    # Verify the session.post was called
    metadata_manager.session.post.assert_called_once()
    # Verify the result contains status
    assert "status" in result


def test_create_namespace_request_exception(metadata_manager):
    """Test namespace creation with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.create_namespace(name="test_namespace")


def test_create_dataset_request_exception(metadata_manager):
    """Test dataset creation with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.create_dataset(
            namespace="test_namespace",
            name="test_dataset"
        )


def test_create_job_request_exception(metadata_manager):
    """Test job creation with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.create_job(
            namespace="test_namespace",
            name="test_job"
        )


def test_get_dataset_lineage_request_exception(metadata_manager):
    """Test dataset lineage retrieval with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.get_dataset_lineage(
            namespace="test_namespace",
            name="test_dataset"
        )


def test_search_datasets_request_exception(metadata_manager):
    """Test dataset search with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.search_datasets(query="test")


def test_get_dataset_versions_request_exception(metadata_manager):
    """Test dataset versions retrieval with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.get_dataset_versions(
            namespace="test_namespace",
            name="test_dataset"
        )


def test_get_job_runs_request_exception(metadata_manager):
    """Test job runs retrieval with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.get = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.get_job_runs(
            namespace="test_namespace",
            job_name="test_job"
        )


def test_add_dataset_tag_request_exception(metadata_manager):
    """Test dataset tag addition with HTTP request exception"""
    # Mock the session to raise a RequestException
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    metadata_manager.session.post = Mock(return_value=mock_response)
    
    with pytest.raises(Exception, match="HTTP Error"):
        metadata_manager.add_dataset_tag(
            namespace="test_namespace",
            name="test_dataset",
            tag="test_tag"
        )


def test_setup_football_metadata(metadata_manager):
    """Test setting up football metadata structure"""
    # Mock all the API calls that would be made
    mock_response = Mock()
    mock_response.json.return_value = {"status": "success"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    metadata_manager.session.post = Mock(return_value=mock_response)
    
    # This should not raise any exceptions
    metadata_manager.setup_football_metadata()


def test_global_metadata_manager():
    """Test getting the global metadata manager instance"""
    manager = get_metadata_manager()
    assert manager is not None
    assert isinstance(manager, MetadataManager)
    
    # Getting it again should return the same instance
    manager2 = get_metadata_manager()
    assert manager is manager2


def test_create_namespace_with_minimal_params(metadata_manager):
    """Test namespace creation with minimal parameters"""
    mock_response = Mock()
    mock_response.json.return_value = {"name": "minimal_namespace", "description": "minimal"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    result = metadata_manager.create_namespace(name="minimal_namespace")
    
    metadata_manager.session.put.assert_called_once()
    assert result["name"] == "minimal_namespace"


def test_create_dataset_with_minimal_params(metadata_manager):
    """Test dataset creation with minimal parameters"""
    mock_response = Mock()
    mock_response.json.return_value = {"name": "minimal_dataset", "description": "minimal"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    result = metadata_manager.create_dataset(
        namespace="test_namespace",
        name="minimal_dataset"
    )
    
    metadata_manager.session.put.assert_called_once()
    assert result["name"] == "minimal_dataset"


def test_create_job_with_minimal_params(metadata_manager):
    """Test job creation with minimal parameters"""
    mock_response = Mock()
    mock_response.json.return_value = {"name": "minimal_job", "type": "BATCH"}
    mock_response.raise_for_status.return_value = None
    metadata_manager.session.put = Mock(return_value=mock_response)
    
    result = metadata_manager.create_job(
        namespace="test_namespace",
        name="minimal_job"
    )
    
    metadata_manager.session.put.assert_called_once()
    assert result["name"] == "minimal_job"