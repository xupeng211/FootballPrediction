"""
API端点综合测试套件
Comprehensive API Endpoints Test Suite

测试所有API端点的HTTP功能，包括状态码、请求/响应验证、认证授权等。
"""

import pytest
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch

# FastAPI和相关组件
try:
    from fastapi import FastAPI, HTTPException, Depends, Security, status, Query, Path, Body
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.testclient import TestClient
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field, validator
    from starlette.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    pytest.skip("FastAPI not available", allow_module_level=True)

# 安全的Mock类
class SafeMock:
    """安全的Mock类，避免递归问题"""
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if not hasattr(self, 'id'):
            self.id = 1
        if not hasattr(self, 'name'):
            self.name = "Mock"

    def __call__(self, *args, **kwargs):
        return SafeMock(*args, **kwargs)

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return SafeMock(name=name)

    def __bool__(self):
        return True

    def __iter__(self):
        return iter([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Pydantic模型定义
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PredictionRequest(BaseModel):
    match_id: int = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    prediction_type: str = Field(..., description="预测类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="预测置信度")

    @validator('prediction_type')
    def validate_prediction_type(cls, v):
        allowed_types = ['win', 'draw', 'lose', 'over_2.5', 'under_2.5']
        if v not in allowed_types:
            raise ValueError(f'Prediction type must be one of: {allowed_types}')
        return v

class PredictionResponse(BaseModel):
    id: int
    match_id: int
    home_team: str
    away_team: str
    prediction_type: str
    confidence: float
    predicted_result: Optional[str]
    created_at: datetime
    status: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    components: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    timestamp: datetime

# Mock认证管理器
class MockAuthManager:
    """Mock认证管理器"""
    def __init__(self):
        self.users = {
            1: {"id": 1, "username": "admin", "email": "admin@test.com", "role": "admin", "is_active": True},
            2: {"id": 2, "username": "user", "email": "user@test.com", "role": "user", "is_active": True},
            3: {"id": 3, "username": "inactive", "email": "inactive@test.com", "role": "user", "is_active": False},
        }
        self.tokens = {
            "admin_token": 1,
            "user_token": 2,
            "inactive_token": 3,
        }

    def create_access_token(self, data: dict) -> str:
        return f"token_{data.get('sub', 'unknown')}"

    async def verify_token(self, token: str) -> Dict[str, Any]:
        if token in self.tokens:
            user_id = self.tokens[token]
            return self.users[user_id]
        raise HTTPException(status_code=401, detail="Invalid token")

# Mock数据服务
class MockDataService:
    """Mock数据服务"""
    def __init__(self):
        self.predictions = [
            {
                "id": 1,
                "match_id": 101,
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "prediction_type": "win",
                "confidence": 0.75,
                "predicted_result": "2-1",
                "created_at": datetime.now(),
                "status": "completed"
            },
            {
                "id": 2,
                "match_id": 102,
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "prediction_type": "draw",
                "confidence": 0.60,
                "predicted_result": "1-1",
                "created_at": datetime.now(),
                "status": "pending"
            },
        ]

    async def get_predictions(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        return self.predictions[skip:skip + limit]

    async def get_prediction_by_id(self, prediction_id: int) -> Optional[Dict[str, Any]]:
        for prediction in self.predictions:
            if prediction["id"] == prediction_id:
                return prediction
        return None

    async def create_prediction(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        new_prediction = {
            "id": max(p["id"] for p in self.predictions) + 1,
            **prediction_data,
            "created_at": datetime.now(),
            "status": "pending"
        }
        self.predictions.append(new_prediction)
        return new_prediction

# 创建FastAPI应用
def create_test_app() -> FastAPI:
    """创建测试用FastAPI应用"""
    app = FastAPI(
        title="Football Prediction API Test",
        description="足球预测API测试应用",
        version="1.0.0"
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 实例化Mock服务
    auth_manager = MockAuthManager()
    data_service = MockDataService()

    # 认证依赖
    security = HTTPBearer()

    async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
        try:
            return await auth_manager.verify_token(credentials.credentials)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    async def get_admin_user(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return current_user

    async def get_active_user(current_user: dict = Depends(get_current_user)):
        if not current_user.get("is_active"):
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

    # 健康检查端点
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """基础健康检查"""
        return HealthResponse(
            status="healthy",
            service="football-prediction-api",
            version="1.0.0",
            timestamp=datetime.now(),
            components={"database": "healthy", "cache": "healthy"}
        )

    @app.get("/health/detailed", response_model=HealthResponse, tags=["Health"])
    async def detailed_health_check():
        """详细健康检查"""
        return HealthResponse(
            status="healthy",
            service="football-prediction-api",
            version="1.0.0",
            timestamp=datetime.now(),
            components={
                "database": {"status": "healthy", "response_time_ms": 10},
                "cache": {"status": "healthy", "hit_rate": 0.85},
                "external_apis": {"status": "degraded", "response_time_ms": 500}
            }
        )

    # 用户管理端点
    @app.get("/api/users/me", response_model=UserResponse, tags=["Users"])
    async def get_current_user_info(current_user: dict = Depends(get_active_user)):
        """获取当前用户信息"""
        return UserResponse(**current_user, created_at=datetime.now())

    @app.get("/api/users/{user_id}", response_model=UserResponse, tags=["Users"])
    async def get_user_by_id(
        user_id: int = Path(..., description="用户ID"),
        current_user: dict = Depends(get_admin_user)
    ):
        """根据ID获取用户信息（管理员权限）"""
        if user_id in auth_manager.users:
            user_data = auth_manager.users[user_id]
            return UserResponse(**user_data, created_at=datetime.now())
        raise HTTPException(status_code=404, detail="User not found")

    @app.get("/api/users", response_model=List[UserResponse], tags=["Users"])
    async def list_users(
        skip: int = Query(0, ge=0, description="跳过的记录数"),
        limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
        current_user: dict = Depends(get_admin_user)
    ):
        """获取用户列表（管理员权限）"""
        users = list(auth_manager.users.values())[skip:skip + limit]
        return [UserResponse(**user, created_at=datetime.now()) for user in users]

    # 预测管理端点
    @app.get("/api/predictions", response_model=List[PredictionResponse], tags=["Predictions"])
    async def get_predictions(
        skip: int = Query(0, ge=0, description="跳过的记录数"),
        limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
        current_user: dict = Depends(get_active_user)
    ):
        """获取预测列表"""
        predictions = await data_service.get_predictions(skip=skip, limit=limit)
        return [PredictionResponse(**prediction) for prediction in predictions]

    @app.get("/api/predictions/{prediction_id}", response_model=PredictionResponse, tags=["Predictions"])
    async def get_prediction_by_id(
        prediction_id: int = Path(..., description="预测ID"),
        current_user: dict = Depends(get_active_user)
    ):
        """根据ID获取预测"""
        prediction = await data_service.get_prediction_by_id(prediction_id)
        if prediction:
            return PredictionResponse(**prediction)
        raise HTTPException(status_code=404, detail="Prediction not found")

    @app.post("/api/predictions", response_model=PredictionResponse, status_code=201, tags=["Predictions"])
    async def create_prediction(
        prediction_data: PredictionRequest,
        current_user: dict = Depends(get_active_user)
    ):
        """创建新预测"""
        try:
            new_prediction = await data_service.create_prediction(prediction_data.dict())
            return PredictionResponse(**new_prediction)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 错误处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """HTTP异常处理器"""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.detail,
                status_code=exc.status_code,
                timestamp=datetime.now()
            ).dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """通用异常处理器"""
        logging.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                detail="Internal server error",
                status_code=500,
                timestamp=datetime.now()
            ).dict()
        )

    return app

# 创建测试应用和客户端
app = create_test_app()
client = TestClient(app)

logger = logging.getLogger(__name__)

# ==================== 测试用例 ====================

class TestHealthEndpoints:
    """健康检查端点测试类"""

    def test_health_check_success(self):
        """测试健康检查成功响应"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "football-prediction-api"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_detailed_health_check_success(self):
        """测试详细健康检查成功响应"""
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "database" in data["components"]
        assert "cache" in data["components"]

    def test_health_check_response_headers(self):
        """测试健康检查响应头"""
        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"
        assert "x-request-id" not in response.headers  # 未启用请求ID中间件

class TestAuthentication:
    """认证功能测试类"""

    def test_no_authentication_required_for_health(self):
        """测试健康检查不需要认证"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_endpoint_without_token(self):
        """测试未认证访问受保护端点"""
        response = client.get("/api/users/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Not authenticated"

    def test_protected_endpoint_with_invalid_token(self):
        """测试使用无效令牌访问受保护端点"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_protected_endpoint_with_valid_user_token(self):
        """测试使用有效用户令牌访问受保护端点"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "user"
        assert data["role"] == "user"

    def test_protected_endpoint_with_admin_token(self):
        """测试使用管理员令牌访问受保护端点"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_protected_endpoint_with_inactive_user_token(self):
        """测试使用非活跃用户令牌访问受保护端点"""
        headers = {"Authorization": "Bearer inactive_token"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Inactive user" in data["detail"]

class TestAuthorization:
    """授权功能测试类"""

    def test_admin_endpoint_access_by_admin(self):
        """测试管理员访问管理员端点"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users/1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_admin_endpoint_access_by_regular_user(self):
        """测试普通用户访问管理员端点"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/users/1", headers=headers)
        assert response.status_code == 403
        data = response.json()
        assert "Admin access required" in data["detail"]

    def test_user_list_access_by_admin(self):
        """测试管理员访问用户列表"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_user_list_access_by_regular_user(self):
        """测试普通用户访问用户列表"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/users", headers=headers)
        assert response.status_code == 403

class TestUserManagementEndpoints:
    """用户管理端点测试类"""

    def test_get_current_user_info_success(self):
        """测试获取当前用户信息成功"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/users/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "user"
        assert data["email"] == "user@test.com"
        assert data["role"] == "user"
        assert data["is_active"] is True

    def test_get_user_by_id_success(self):
        """测试根据ID获取用户信息成功"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users/2", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "user"

    def test_get_user_by_id_not_found(self):
        """测试根据ID获取不存在的用户"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users/999", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]

    def test_get_users_with_pagination(self):
        """测试分页获取用户列表"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users?skip=0&limit=2", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 2

    def test_get_users_invalid_pagination(self):
        """测试无效分页参数"""
        headers = {"Authorization": "Bearer admin_token"}
        response = client.get("/api/users?skip=-1&limit=0", headers=headers)

        # 应该返回验证错误或使用默认值
        assert response.status_code in [422, 200]

class TestPredictionEndpoints:
    """预测端点测试类"""

    def test_get_predictions_success(self):
        """测试获取预测列表成功"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/predictions", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0]
            assert "match_id" in data[0]
            assert "home_team" in data[0]

    def test_get_predictions_with_pagination(self):
        """测试分页获取预测列表"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/predictions?skip=0&limit=1", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 1

    def test_get_prediction_by_id_success(self):
        """测试根据ID获取预测成功"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/predictions/1", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "match_id" in data
        assert "prediction_type" in data

    def test_get_prediction_by_id_not_found(self):
        """测试根据ID获取不存在的预测"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/predictions/999", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert "Prediction not found" in data["detail"]

    def test_create_prediction_success(self):
        """测试创建预测成功"""
        headers = {"Authorization": "Bearer user_token"}
        prediction_data = {
            "match_id": 103,
            "home_team": "Chelsea",
            "away_team": "Arsenal",
            "prediction_type": "win",
            "confidence": 0.80
        }

        response = client.post("/api/predictions", json=prediction_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["match_id"] == 103
        assert data["home_team"] == "Chelsea"
        assert data["away_team"] == "Arsenal"
        assert data["prediction_type"] == "win"
        assert data["confidence"] == 0.80
        assert "id" in data
        assert "created_at" in data

    def test_create_prediction_invalid_data(self):
        """测试创建预测时数据无效"""
        headers = {"Authorization": "Bearer user_token"}
        invalid_data = {
            "match_id": 103,
            "home_team": "Chelsea",
            "away_team": "Arsenal",
            "prediction_type": "invalid_type",  # 无效类型
            "confidence": 1.5  # 超出范围
        }

        response = client.post("/api/predictions", json=invalid_data, headers=headers)

        assert response.status_code == 422  # 验证错误

    def test_create_prediction_missing_data(self):
        """测试创建预测时缺少必要数据"""
        headers = {"Authorization": "Bearer user_token"}
        incomplete_data = {
            "home_team": "Chelsea",
            "away_team": "Arsenal"
            # 缺少必要字段
        }

        response = client.post("/api/predictions", json=incomplete_data, headers=headers)

        assert response.status_code == 422  # 验证错误

class TestErrorHandling:
    """错误处理测试类"""

    def test_404_error_handling(self):
        """测试404错误处理"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """测试方法不允许错误"""
        response = client.delete("/health")
        assert response.status_code == 405

    def test_invalid_json_data(self):
        """测试无效JSON数据"""
        headers = {"Authorization": "Bearer user_token", "Content-Type": "application/json"}
        response = client.post("/api/predictions", data="invalid json", headers=headers)
        assert response.status_code == 422

    def test_missing_authorization_header(self):
        """测试缺少授权头"""
        response = client.get("/api/predictions")
        assert response.status_code == 401

    def test_malformed_authorization_header(self):
        """测试格式错误的授权头"""
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/predictions", headers=headers)
        assert response.status_code == 401

class TestRequestValidation:
    """请求验证测试类"""

    def test_query_parameter_validation(self):
        """测试查询参数验证"""
        headers = {"Authorization": "Bearer admin_token"}

        # 测试负数skip值
        response = client.get("/api/users?skip=-1", headers=headers)
        assert response.status_code in [200, 422]  # 可能的响应

        # 测试超过限制的limit值
        response = client.get("/api/users?limit=200", headers=headers)
        assert response.status_code in [200, 422]

    def test_path_parameter_validation(self):
        """测试路径参数验证"""
        headers = {"Authorization": "Bearer admin_token"}

        # 测试非数字用户ID
        response = client.get("/api/users/abc", headers=headers)
        assert response.status_code == 422

    def test_request_body_validation(self):
        """测试请求体验证"""
        headers = {"Authorization": "Bearer user_token"}

        # 测试字段类型错误
        invalid_data = {
            "match_id": "not_a_number",
            "home_team": "Chelsea",
            "away_team": "Arsenal",
            "prediction_type": "win",
            "confidence": 0.80
        }

        response = client.post("/api/predictions", json=invalid_data, headers=headers)
        assert response.status_code == 422

class TestResponseValidation:
    """响应验证测试类"""

    def test_response_structure_validation(self):
        """测试响应结构验证"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/predictions", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # 验证响应结构
        assert isinstance(data, list)
        if data:  # 如果列表不为空
            prediction = data[0]
            required_fields = ["id", "match_id", "home_team", "away_team",
                             "prediction_type", "confidence", "created_at", "status"]
            for field in required_fields:
                assert field in prediction

    def test_response_data_types(self):
        """测试响应数据类型"""
        headers = {"Authorization": "Bearer user_token"}
        response = client.get("/api/predictions/1", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["id"], int)
        assert isinstance(data["match_id"], int)
        assert isinstance(data["home_team"], str)
        assert isinstance(data["away_team"], str)
        assert isinstance(data["prediction_type"], str)
        assert isinstance(data["confidence"], (int, float))
        assert isinstance(data["status"], str)

class TestPerformanceAndLoad:
    """性能和负载测试类"""

    def test_response_time_under_threshold(self):
        """测试响应时间在阈值内"""
        import time

        headers = {"Authorization": "Bearer user_token"}
        start_time = time.time()

        response = client.get("/api/predictions", headers=headers)

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 1.0, f"Response time too slow: {response_time}s"

    def test_concurrent_requests_handling(self):
        """测试并发请求处理"""
        import threading
        import time

        results = []

        def make_request():
            headers = {"Authorization": "Bearer user_token"}
            response = client.get("/health")
            results.append(response.status_code)

        # 创建多个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # 启动所有线程
        start_time = time.time()
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        end_time = time.time()

        # 验证所有请求都成功
        assert len(results) == 10
        assert all(status == 200 for status in results)
        assert (end_time - start_time) < 5.0  # 应该在5秒内完成

class TestCORSAndHeaders:
    """CORS和头信息测试类"""

    def test_cors_headers_present(self):
        """测试CORS头信息存在"""
        response = client.options("/health")

        # 检查CORS相关的头
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_content_type_headers(self):
        """测试内容类型头"""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]

    def test_preflight_request_handling(self):
        """测试预检请求处理"""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization"
        }

        response = client.options("/api/predictions", headers=headers)
        assert response.status_code in [200, 405]  # 根据实际配置

class TestIntegration:
    """集成测试类"""

    def test_full_prediction_workflow(self):
        """测试完整的预测工作流程"""
        headers = {"Authorization": "Bearer user_token"}

        # 1. 创建预测
        prediction_data = {
            "match_id": 104,
            "home_team": "Juventus",
            "away_team": "Inter Milan",
            "prediction_type": "draw",
            "confidence": 0.65
        }

        create_response = client.post("/api/predictions", json=prediction_data, headers=headers)
        assert create_response.status_code == 201
        created_prediction = create_response.json()
        prediction_id = created_prediction["id"]

        # 2. 获取预测详情
        get_response = client.get(f"/api/predictions/{prediction_id}", headers=headers)
        assert get_response.status_code == 200
        retrieved_prediction = get_response.json()

        # 3. 验证数据一致性
        assert retrieved_prediction["match_id"] == prediction_data["match_id"]
        assert retrieved_prediction["home_team"] == prediction_data["home_team"]
        assert retrieved_prediction["away_team"] == prediction_data["away_team"]
        assert retrieved_prediction["prediction_type"] == prediction_data["prediction_type"]
        assert retrieved_prediction["confidence"] == prediction_data["confidence"]

        # 4. 获取预测列表，确认新预测在列表中
        list_response = client.get("/api/predictions", headers=headers)
        assert list_response.status_code == 200
        predictions = list_response.json()

        prediction_ids = [p["id"] for p in predictions]
        assert prediction_id in prediction_ids

    def test_user_management_workflow(self):
        """测试用户管理工作流程"""
        admin_headers = {"Authorization": "Bearer admin_token"}
        user_headers = {"Authorization": "Bearer user_token"}

        # 1. 管理员获取用户列表
        list_response = client.get("/api/users", headers=admin_headers)
        assert list_response.status_code == 200
        users = list_response.json()
        assert len(users) > 0

        # 2. 管理员获取特定用户信息
        user_id = users[0]["id"]
        user_detail_response = client.get(f"/api/users/{user_id}", headers=admin_headers)
        assert user_detail_response.status_code == 200
        user_detail = user_detail_response.json()

        # 3. 普通用户尝试访问管理员功能（应该失败）
        admin_attempt_response = client.get("/api/users", headers=user_headers)
        assert admin_attempt_response.status_code == 403

        # 4. 普通用户获取自己的信息（应该成功）
        self_info_response = client.get("/api/users/me", headers=user_headers)
        assert self_info_response.status_code == 200
        self_info = self_info_response.json()
        assert self_info["role"] == "user"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])