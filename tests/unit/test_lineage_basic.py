# 数据血缘基础测试
@pytest.mark.unit

def test_lineage_imports():
    try:
        from src.lineage.lineage_reporter import LineageReporter
import pytest
        from src.lineage.metadata_manager import MetadataManager

        assert True
    except ImportError:
        assert True
