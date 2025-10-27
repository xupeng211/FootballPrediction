# 原始数据模型测试
import pytest

from src.database.models.raw_data import RawData


@pytest.mark.unit
def test_raw_data_model():
    data = RawData(source="api", data_type="fixtures")
    assert data.source == "api"
    assert data.data_type == "fixtures"
