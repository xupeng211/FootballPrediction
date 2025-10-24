# API Schema测试
def test_schema_imports():
    # 只测试导入是否成功
    try:
        from src.api.schemas import PredictionRequest
        from src.api.schemas import PredictionResponse

        assert True
    except ImportError:
        assert False
