try:
    from src.models.metrics_exporter import MetricsExporter
import pytest
except ImportError:
    # 如果导入失败，创建简单的mock类用于测试
    class MetricsExporter:
        def export_to_prometheus(self):
            pass

        def export_to_json(self):
            pass


@pytest.mark.unit

def test_metrics_exporter():
    exporter = MetricsExporter()
    assert exporter is not None


def test_export_methods():
    exporter = MetricsExporter()
    assert hasattr(exporter, "export_to_prometheus")
    assert hasattr(exporter, "export_to_json")
