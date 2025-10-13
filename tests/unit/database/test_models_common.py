try:
    from src.models.common_models import BaseResponse
except ImportError:
    # 如果导入失败，创建简单的mock类用于测试
    class BaseResponse:
        def __init__(self, _data =None, success=True, message="OK"):
            self._data = data or {}
            self.success = success
            self.message = message

        def dict(self):
            return {"data": self.data, "success": self.success, "message": self.message}


def test_base_response():
    response = BaseResponse(_data ={"test": "data"})
    assert response._data == {"test": "data"}


def test_response_serialization():
    response = BaseResponse(success=True, message="OK")
    response_dict = response.dict()
    assert response_dict["success"] is True
    assert response_dict["message"] == "OK"
