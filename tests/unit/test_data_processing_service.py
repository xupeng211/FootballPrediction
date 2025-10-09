from src.services.data_processing_mod import DataProcessingService


def test_data_processing():
    service = DataProcessingService()
    assert service is not None


def test_processing_methods():
    service = DataProcessingService()
    assert hasattr(service, "process_data")
    assert hasattr(service, "clean_data")
