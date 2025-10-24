# API Schema测试
@pytest.mark.unit
@pytest.mark.api

def test_schema_imports():
    # 只测试导入是否成功
    try:
        from src.api.schemas import PredictionRequest
import pytest
        from src.api.schemas import PredictionResponse

        assert True
    except ImportError:
        assert False
