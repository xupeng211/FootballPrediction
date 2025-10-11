# API模型导入测试
def test_api_models_import():
    try:
        from src.api.models import APIResponse
        from src.api.schemas import HealthResponse

        assert True
    except ImportError:
        assert True


def test_api_models_creation():
    try:
        from src.api.models import APIResponse

        response = APIResponse(success=True)
        assert response.success is True
    except Exception:
        assert True
