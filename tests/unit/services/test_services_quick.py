import pytest

from tests.base import ServiceTestCase


@pytest.mark.unit
class TestServicesQuick(ServiceTestCase):
    """服务层快速测试"""

    def test_base_service_init(self):
        """测试基础服务初始化"""
from src.services.base import BaseService

        service = BaseService()
        assert service is not None

    def test_data_processing_service(self):
        """测试数据处理服务"""
        try:
            from src.data.processing import DataProcessingService

            service = DataProcessingService()
            assert service is not None
        except ImportError:
            pytest.skip("DataProcessingService not available")

    def test_audit_service_import(self):
        """测试审计服务导入"""
        try:
            from src.audit.service import audit_operation

            assert callable(audit_operation)
        except ImportError:
            pytest.skip("audit_service not available")
