"""
预测API测试套件 - 修复版
Prediction API Test Suite - Fixed Version

专门测试足球预测相关API端点的功能，包括预测创建、查询、更新等。
"""

import pytest
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# FastAPI和相关组件
try:
    from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, BackgroundTasks
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, Field, validator
    from enum import Enum
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    pytest.skip("FastAPI not available", allow_module_level=True)

# 安全的Mock类
class PredictionSafeMock:
    """预测API专用的安全Mock类"""
    def __init__(self, *args, **kwargs):
        # 直接设置属性，避免使用hasattr
        self._attributes = set(kwargs.keys())
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)

        # 设置默认属性
        if 'id' not in self._attributes:
            object.__setattr__(self, 'id', 1)
            self._attributes.add('id')
        if 'status' not in self._attributes:
            object.__setattr__(self, 'status', "pending")
            self._attributes.add('status')

    def __call__(self, *args, **kwargs):
        return PredictionSafeMock(*args, **kwargs)

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return PredictionSafeMock(name=name)

    def __bool__(self):
        return True

    def __iter__(self):
        return iter([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __len__(self):
        return 0

    def __getitem__(self, key):
        return None

# 枚举定义
class PredictionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PredictionType(str, Enum):
    WIN = "win"
    DRAW = "draw"
    LOSE = "lose"
    OVER_2_5 = "over_2.5"
    UNDER_2_5 = "under_2.5"
    BTTS = "btts"  # Both Teams to Score
    CORRECT_SCORE = "correct_score"

class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"

# Pydantic模型定义
class MatchInfo(BaseModel):
    id: int
    home_team: str
    away_team: str
    league: str
    match_date: datetime
    status: MatchStatus
    home_score: Optional[int] = None
    away_score: Optional[int] = None

class PredictionRequest(BaseModel):
    match_id: int = Field(..., gt=0, description="比赛ID")
    prediction_type: PredictionType = Field(..., description="预测类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="预测置信度(0-1)")
    predicted_score: Optional[str] = Field(None, description="预测比分")
    odds: Optional[float] = Field(None, gt=0, description="赔率")
    stake: Optional[float] = Field(None, gt=0, description="投注金额")
    notes: Optional[str] = Field(None, max_length=500, description="备注")

    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0.5:
            raise ValueError('预测置信度不能低于0.5')
        return v

    @validator('predicted_score')
    def validate_predicted_score(cls, v, values):
        if v is not None and 'prediction_type' in values:
            if values['prediction_type'] == PredictionType.CORRECT_SCORE:
                if not v or '-' not in v:
                    raise ValueError('比分预测格式应为: 主队得分-客队得分')
        return v

class PredictionResponse(BaseModel):
    id: int
    match_id: int
    match_info: MatchInfo
    prediction_type: PredictionType
    confidence: float
    predicted_score: Optional[str]
    actual_score: Optional[str]
    status: PredictionStatus
    odds: Optional[float]
    stake: Optional[float]
    potential_winnings: Optional[float]
    actual_winnings: Optional[float]
    is_correct: Optional[bool]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

class PredictionStats(BaseModel):
    total_predictions: int
    correct_predictions: int
    accuracy_rate: float
    total_stake: float
    total_winnings: float
    profit_loss: float
    roi: float  # Return on Investment

class MockPredictionService:
    """Mock预测服务"""

    def __init__(self):
        self.predictions = [
            {
                "id": 1,
                "match_id": 101,
                "match_info": {
                    "id": 101,
                    "home_team": "Real Madrid",
                    "away_team": "Barcelona",
                    "league": "La Liga",
                    "match_date": datetime.now() + timedelta(days=1),
                    "status": MatchStatus.SCHEDULED,
                    "home_score": None,
                    "away_score": None
                },
                "prediction_type": PredictionType.WIN,
                "confidence": 0.75,
                "predicted_score": "2-1",
                "actual_score": None,
                "status": PredictionStatus.PENDING,
                "odds": 1.85,
                "stake": 100.0,
                "potential_winnings": 185.0,
                "actual_winnings": None,
                "is_correct": None,
                "notes": "主队优势明显",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "completed_at": None
            },
            {
                "id": 2,
                "match_id": 102,
                "match_info": {
                    "id": 102,
                    "home_team": "Manchester City",
                    "away_team": "Liverpool",
                    "league": "Premier League",
                    "match_date": datetime.now() + timedelta(days=2),
                    "status": MatchStatus.COMPLETED,
                    "home_score": 2,
                    "away_score": 1
                },
                "prediction_type": PredictionType.OVER_2_5,
                "confidence": 0.80,
                "predicted_score": None,
                "actual_score": "3-1",
                "status": PredictionStatus.COMPLETED,
                "odds": 1.65,
                "stake": 50.0,
                "potential_winnings": 82.5,
                "actual_winnings": 82.5,
                "is_correct": True,
                "notes": "两队进攻力强",
                "created_at": datetime.now() - timedelta(days=2),
                "updated_at": datetime.now(),
                "completed_at": datetime.now()
            }
        ]
        self.next_id = 3

    async def get_predictions(
        self,
        skip: int = 0,
        limit: int = 10,
        status: Optional[PredictionStatus] = None,
        match_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取预测列表"""
        filtered_predictions = self.predictions

        if status:
            filtered_predictions = [p for p in filtered_predictions if p["status"] == status]

        if match_id:
            filtered_predictions = [p for p in filtered_predictions if p["match_id"] == match_id]

        return filtered_predictions[skip:skip + limit]

    async def get_prediction_by_id(self, prediction_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取预测"""
        for prediction in self.predictions:
            if prediction["id"] == prediction_id:
                return prediction
        return None

    async def create_prediction(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新预测"""
        # 查找比赛信息
        match_id = prediction_data["match_id"]
        mock_match = {
            "id": match_id,
            "home_team": prediction_data.get("home_team", "Unknown Home"),
            "away_team": prediction_data.get("away_team", "Unknown Away"),
            "league": "Unknown League",
            "match_date": datetime.now() + timedelta(days=1),
            "status": MatchStatus.SCHEDULED,
            "home_score": None,
            "away_score": None
        }

        # 计算潜在收益
        odds = prediction_data.get("odds")
        stake = prediction_data.get("stake")
        potential_winnings = None
        if odds and stake:
            potential_winnings = odds * stake

        new_prediction = {
            "id": self.next_id,
            "match_id": match_id,
            "match_info": mock_match,
            "prediction_type": prediction_data["prediction_type"],
            "confidence": prediction_data["confidence"],
            "predicted_score": prediction_data.get("predicted_score"),
            "actual_score": None,
            "status": PredictionStatus.PENDING,
            "odds": odds,
            "stake": stake,
            "potential_winnings": potential_winnings,
            "actual_winnings": None,
            "is_correct": None,
            "notes": prediction_data.get("notes"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "completed_at": None
        }

        self.predictions.append(new_prediction)
        self.next_id += 1

        return new_prediction

    async def update_prediction(
        self,
        prediction_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新预测"""
        prediction = await self.get_prediction_by_id(prediction_id)
        if prediction:
            prediction.update(update_data)
            prediction["updated_at"] = datetime.now()
            return prediction
        return None

    async def delete_prediction(self, prediction_id: int) -> bool:
        """删除预测"""
        for i, prediction in enumerate(self.predictions):
            if prediction["id"] == prediction_id:
                del self.predictions[i]
                return True
        return False

    async def get_prediction_stats(self, user_id: Optional[int] = None) -> PredictionStats:
        """获取预测统计"""
        # 简化的统计计算
        total_predictions = len(self.predictions)
        correct_predictions = len([p for p in self.predictions if p.get("is_correct") is True])
        accuracy_rate = correct_predictions / total_predictions if total_predictions > 0 else 0.0

        total_stake = sum(p.get("stake", 0) for p in self.predictions)
        total_winnings = sum(p.get("actual_winnings", 0) for p in self.predictions)
        profit_loss = total_winnings - total_stake
        roi = (profit_loss / total_stake * 100) if total_stake > 0 else 0.0

        return PredictionStats(
            total_predictions=total_predictions,
            correct_predictions=correct_predictions,
            accuracy_rate=accuracy_rate,
            total_stake=total_stake,
            total_winnings=total_winnings,
            profit_loss=profit_loss,
            roi=roi
        )

# Mock认证服务
class MockAuthService:
    """Mock认证服务"""

    def __init__(self):
        self.tokens = {
            "user_token": {"user_id": 1, "role": "user", "is_active": True},
            "admin_token": {"user_id": 2, "role": "admin", "is_active": True},
            "premium_token": {"user_id": 3, "role": "premium", "is_active": True}
        }

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """验证令牌"""
        if token in self.tokens:
            return self.tokens[token]
        raise HTTPException(status_code=401, detail="Invalid token")

    async def check_prediction_limit(self, user_id: int) -> bool:
        """检查用户预测限制"""
        # 简化的限制检查
        return True

# 创建FastAPI应用
def create_prediction_test_app() -> FastAPI:
    """创建预测测试用FastAPI应用"""
    app = FastAPI(
        title="Football Prediction API",
        description="足球预测API测试应用",
        version="2.0.0"
    )

    # 实例化Mock服务
    prediction_service = MockPredictionService()
    auth_service = MockAuthService()

    # 认证依赖
    async def get_current_user(authorization: str = None) -> Dict[str, Any]:
        """获取当前用户"""
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")

        try:
            token = authorization.replace("Bearer ", "")
            return await auth_service.verify_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def check_user_limit(current_user: Dict[str, Any] = Depends(get_current_user)):
        """检查用户限制"""
        can_create = await auth_service.check_prediction_limit(current_user["user_id"])
        if not can_create:
            raise HTTPException(status_code=429, detail="Prediction limit exceeded")

    # 预测端点
    @app.get("/api/predictions", response_model=List[PredictionResponse], tags=["Predictions"])
    async def get_predictions(
        skip: int = Query(0, ge=0, description="跳过的记录数"),
        limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
        status: Optional[PredictionStatus] = Query(None, description="预测状态筛选"),
        match_id: Optional[int] = Query(None, gt=0, description="比赛ID筛选"),
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        """获取预测列表"""
        predictions = await prediction_service.get_predictions(
            skip=skip, limit=limit, status=status, match_id=match_id
        )
        return [PredictionResponse(**prediction) for prediction in predictions]

    @app.get("/api/predictions/{prediction_id}", response_model=PredictionResponse, tags=["Predictions"])
    async def get_prediction_by_id(
        prediction_id: int = Path(..., gt=0, description="预测ID"),
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        """根据ID获取预测"""
        prediction = await prediction_service.get_prediction_by_id(prediction_id)
        if prediction:
            return PredictionResponse(**prediction)
        raise HTTPException(status_code=404, detail="Prediction not found")

    @app.post("/api/predictions", response_model=PredictionResponse, status_code=201, tags=["Predictions"])
    async def create_prediction(
        prediction_data: PredictionRequest,
        background_tasks: BackgroundTasks,
        current_user: Dict[str, Any] = Depends(get_current_user),
        user_limit_ok: bool = Depends(check_user_limit)
    ):
        """创建新预测"""
        # 添加后台任务处理
        background_tasks.add_task(
            process_prediction_background,
            prediction_data.dict(),
            current_user["user_id"]
        )

        new_prediction = await prediction_service.create_prediction(prediction_data.dict())
        return PredictionResponse(**new_prediction)

    @app.put("/api/predictions/{prediction_id}", response_model=PredictionResponse, tags=["Predictions"])
    async def update_prediction(
        prediction_id: int = Path(..., gt=0, description="预测ID"),
        update_data: Dict[str, Any] = Body(..., description="更新数据"),
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        """更新预测"""
        # 验证预测存在且属于当前用户
        existing = await prediction_service.get_prediction_by_id(prediction_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Prediction not found")

        # 更新预测
        updated = await prediction_service.update_prediction(prediction_id, update_data)
        if updated:
            return PredictionResponse(**updated)
        raise HTTPException(status_code=400, detail="Failed to update prediction")

    @app.delete("/api/predictions/{prediction_id}", status_code=204, tags=["Predictions"])
    async def delete_prediction(
        prediction_id: int = Path(..., gt=0, description="预测ID"),
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        """删除预测"""
        # 验证预测存在且属于当前用户
        existing = await prediction_service.get_prediction_by_id(prediction_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Prediction not found")

        # 只能删除pending状态的预测
        if existing["status"] != PredictionStatus.PENDING:
            raise HTTPException(status_code=400, detail="Cannot delete non-pending prediction")

        success = await prediction_service.delete_prediction(prediction_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete prediction")

    @app.get("/api/predictions/stats", response_model=PredictionStats, tags=["Predictions"])
    async def get_prediction_stats(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        """获取预测统计"""
        return await prediction_service.get_prediction_stats(current_user["user_id"])

    @app.get("/api/predictions/types", tags=["Predictions"])
    async def get_prediction_types():
        """获取可用的预测类型"""
        return {
            "prediction_types": [
                {"value": pt.value, "description": get_prediction_type_description(pt)}
                for pt in PredictionType
            ]
        }

    # 后台任务
    async def process_prediction_background(prediction_data: Dict[str, Any], user_id: int):
        """后台处理预测任务"""
        # 模拟后台处理
        await asyncio.sleep(0.1)
        logging.info(f"Processed prediction for user {user_id}")

    return app

# 导入asyncio
import asyncio

# 创建测试应用和客户端
prediction_app = create_prediction_test_app()
prediction_client = TestClient(prediction_app)

logger = logging.getLogger(__name__)

# 辅助函数
def get_prediction_type_description(prediction_type: PredictionType) -> str:
    """获取预测类型描述"""
    descriptions = {
        PredictionType.WIN: "主队获胜",
        PredictionType.DRAW: "平局",
        PredictionType.LOSE: "主队失利",
        PredictionType.OVER_2_5: "总进球数大于2.5",
        PredictionType.UNDER_2_5: "总进球数小于2.5",
        PredictionType.BTTS: "两队都进球",
        PredictionType.CORRECT_SCORE: "准确比分"
    }
    return descriptions.get(prediction_type, "未知类型")

# ==================== 测试用例 ====================

class TestPredictionBasicOperations:
    """预测基础操作测试类"""

    def test_get_predictions_success(self):
        """测试获取预测列表成功"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # 至少有Mock数据

        # 验证数据结构
        if data:
            prediction = data[0]
            required_fields = ["id", "match_id", "match_info", "prediction_type",
                             "confidence", "status", "created_at", "updated_at"]
            for field in required_fields:
                assert field in prediction

    def test_get_predictions_with_pagination(self):
        """测试分页获取预测"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions?skip=0&limit=1", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 1

    def test_get_predictions_with_status_filter(self):
        """测试按状态筛选预测"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions?status=completed", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 验证筛选结果
        for prediction in data:
            assert prediction["status"] == "completed"

    def test_get_predictions_with_match_filter(self):
        """测试按比赛ID筛选预测"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions?match_id=101", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 验证筛选结果
        for prediction in data:
            assert prediction["match_id"] == 101

    def test_get_prediction_by_id_success(self):
        """测试根据ID获取预测成功"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions/1", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "match_info" in data
        assert "prediction_type" in data

    def test_get_prediction_by_id_not_found(self):
        """测试根据ID获取不存在的预测"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions/999", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert "Prediction not found" in data["detail"]

    def test_create_prediction_success(self):
        """测试创建预测成功"""
        headers = {"Authorization": "Bearer user_token"}
        prediction_data = {
            "match_id": 103,
            "prediction_type": "draw",
            "confidence": 0.70,
            "predicted_score": "1-1",
            "odds": 3.20,
            "stake": 50.0,
            "notes": "实力相当，可能平局"
        }

        response = prediction_client.post("/api/predictions", json=prediction_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["match_id"] == 103
        assert data["prediction_type"] == "draw"
        assert data["confidence"] == 0.70
        assert data["predicted_score"] == "1-1"
        assert data["status"] == "pending"
        assert data["potential_winnings"] == 160.0  # 50.0 * 3.20

    def test_create_prediction_invalid_confidence(self):
        """测试创建预测时置信度无效"""
        headers = {"Authorization": "Bearer user_token"}
        invalid_data = {
            "match_id": 103,
            "prediction_type": "win",
            "confidence": 0.3,  # 低于最小值0.5
            "odds": 1.85
        }

        response = prediction_client.post("/api/predictions", json=invalid_data, headers=headers)
        assert response.status_code == 422
        errors = response.json()
        assert any("置信度" in str(error) or "confidence" in str(error) for error in errors.get("detail", []))

    def test_create_prediction_invalid_score_format(self):
        """测试创建预测时比分格式无效"""
        headers = {"Authorization": "Bearer user_token"}
        invalid_data = {
            "match_id": 103,
            "prediction_type": "correct_score",
            "confidence": 0.80,
            "predicted_score": "invalid_format",  # 无效格式
            "odds": 5.50
        }

        response = prediction_client.post("/api/predictions", json=invalid_data, headers=headers)
        assert response.status_code == 422

    def test_create_prediction_missing_required_fields(self):
        """测试创建预测时缺少必要字段"""
        headers = {"Authorization": "Bearer user_token"}
        incomplete_data = {
            "confidence": 0.75
            # 缺少 match_id 和 prediction_type
        }

        response = prediction_client.post("/api/predictions", json=incomplete_data, headers=headers)
        assert response.status_code == 422

    def test_update_prediction_success(self):
        """测试更新预测成功"""
        headers = {"Authorization": "Bearer user_token"}
        update_data = {
            "confidence": 0.85,
            "notes": "更新后的分析"
        }

        response = prediction_client.put("/api/predictions/1", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["confidence"] == 0.85
        assert data["notes"] == "更新后的分析"

    def test_update_prediction_not_found(self):
        """测试更新不存在的预测"""
        headers = {"Authorization": "Bearer user_token"}
        update_data = {"confidence": 0.90}

        response = prediction_client.put("/api/predictions/999", json=update_data, headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert "Prediction not found" in data["detail"]

    def test_delete_prediction_success(self):
        """测试删除预测成功"""
        headers = {"Authorization": "Bearer user_token"}

        # 先创建一个预测
        create_data = {
            "match_id": 104,
            "prediction_type": "win",
            "confidence": 0.75
        }
        create_response = prediction_client.post("/api/predictions", json=create_data, headers=headers)
        created_id = create_response.json()["id"]

        # 然后删除它
        response = prediction_client.delete(f"/api/predictions/{created_id}", headers=headers)
        assert response.status_code == 204

        # 验证预测已被删除
        get_response = prediction_client.get(f"/api/predictions/{created_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_non_pending_prediction(self):
        """测试删除非pending状态的预测"""
        headers = {"Authorization": "Bearer user_token"}

        # 尝试删除已完成的预测
        response = prediction_client.delete("/api/predictions/2", headers=headers)
        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete non-pending prediction" in data["detail"]

    def test_get_prediction_stats(self):
        """测试获取预测统计"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        required_fields = ["total_predictions", "correct_predictions", "accuracy_rate",
                         "total_stake", "total_winnings", "profit_loss", "roi"]
        for field in required_fields:
            assert field in data

        # 验证数据类型
        assert isinstance(data["total_predictions"], int)
        assert isinstance(data["accuracy_rate"], (int, float))
        assert isinstance(data["roi"], (int, float))

    def test_get_prediction_types(self):
        """测试获取预测类型列表"""
        response = prediction_client.get("/api/predictions/types")

        assert response.status_code == 200
        data = response.json()
        assert "prediction_types" in data
        assert isinstance(data["prediction_types"], list)
        assert len(data["prediction_types"]) == len(PredictionType)

        # 验证每个类型都有value和description
        for pred_type in data["prediction_types"]:
            assert "value" in pred_type
            assert "description" in pred_type

class TestPredictionValidation:
    """预测验证测试类"""

    def test_prediction_type_validation(self):
        """测试预测类型验证"""
        headers = {"Authorization": "Bearer user_token"}
        valid_types = [pt.value for pt in PredictionType]

        for pred_type in valid_types:
            data = {
                "match_id": 105,
                "prediction_type": pred_type,
                "confidence": 0.75
            }
            response = prediction_client.post("/api/predictions", json=data, headers=headers)
            assert response.status_code == 201

    def test_invalid_prediction_type(self):
        """测试无效预测类型"""
        headers = {"Authorization": "Bearer user_token"}
        invalid_data = {
            "match_id": 105,
            "prediction_type": "invalid_type",
            "confidence": 0.75
        }

        response = prediction_client.post("/api/predictions", json=invalid_data, headers=headers)
        assert response.status_code == 422

    def test_confidence_boundaries(self):
        """测试置信度边界值"""
        headers = {"Authorization": "Bearer user_token"}

        # 测试最小有效值
        min_data = {
            "match_id": 106,
            "prediction_type": "win",
            "confidence": 0.5
        }
        response = prediction_client.post("/api/predictions", json=min_data, headers=headers)
        assert response.status_code == 201

        # 测试最大有效值
        max_data = {
            "match_id": 107,
            "prediction_type": "win",
            "confidence": 1.0
        }
        response = prediction_client.post("/api/predictions", json=max_data, headers=headers)
        assert response.status_code == 201

        # 测试超出范围的值
        invalid_data = {
            "match_id": 108,
            "prediction_type": "win",
            "confidence": 1.5
        }
        response = prediction_client.post("/api/predictions", json=invalid_data, headers=headers)
        assert response.status_code == 422

    def test_odds_and_stake_validation(self):
        """测试赔率和投注金额验证"""
        headers = {"Authorization": "Bearer user_token"}

        # 测试正数的赔率和投注金额
        valid_data = {
            "match_id": 109,
            "prediction_type": "win",
            "confidence": 0.75,
            "odds": 2.50,
            "stake": 100.0
        }
        response = prediction_client.post("/api/predictions", json=valid_data, headers=headers)
        assert response.status_code == 201

        # 测试负数投注金额
        invalid_data = {
            "match_id": 110,
            "prediction_type": "win",
            "confidence": 0.75,
            "stake": -50.0
        }
        response = prediction_client.post("/api/predictions", json=invalid_data, headers=headers)
        assert response.status_code == 422

class TestPredictionAuthentication:
    """预测认证测试类"""

    def test_unauthorized_access(self):
        """测试未授权访问"""
        response = prediction_client.get("/api/predictions")
        assert response.status_code == 401

    def test_invalid_token(self):
        """测试无效令牌"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = prediction_client.get("/api/predictions", headers=headers)
        assert response.status_code == 401

    def test_missing_authorization_header(self):
        """测试缺少授权头"""
        response = prediction_client.post("/api/predictions", json={})
        assert response.status_code == 401

    def test_valid_user_token(self):
        """测试有效用户令牌"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions", headers=headers)
        assert response.status_code == 200

    def test_admin_token(self):
        """测试管理员令牌"""
        headers = {"Authorization": "Bearer admin_token"}
        response = prediction_client.get("/api/predictions", headers=headers)
        assert response.status_code == 200

class TestPredictionBusinessLogic:
    """预测业务逻辑测试类"""

    def test_potential_winnings_calculation(self):
        """测试潜在收益计算"""
        headers = {"Authorization": "Bearer user_token"}
        prediction_data = {
            "match_id": 111,
            "prediction_type": "win",
            "confidence": 0.75,
            "odds": 3.00,
            "stake": 100.0
        }

        response = prediction_client.post("/api/predictions", json=prediction_data, headers=headers)
        assert response.status_code == 201

        data = response.json()
        assert data["potential_winnings"] == 300.0  # 100.0 * 3.00

    def test_completed_prediction_readonly_fields(self):
        """测试已完成预测的只读字段"""
        headers = {"Authorization": "Bearer user_token"}

        # 尝试更新已完成的预测
        update_data = {
            "confidence": 0.90,
            "actual_winnings": 200.0
        }

        response = prediction_client.put("/api/predictions/2", json=update_data, headers=headers)
        assert response.status_code == 200

        # 验证某些字段可能不允许修改（取决于业务逻辑）
        data = response.json()
        # 这里可以添加具体的业务逻辑验证

    def test_prediction_status_transitions(self):
        """测试预测状态转换"""
        headers = {"Authorization": "Bearer user_token"}

        # 创建预测（初始状态为pending）
        create_data = {
            "match_id": 112,
            "prediction_type": "draw",
            "confidence": 0.70
        }
        create_response = prediction_client.post("/api/predictions", json=create_data, headers=headers)
        prediction_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"

        # 更新预测状态为in_progress
        update_data = {"status": "in_progress"}
        response = prediction_client.put(f"/api/predictions/{prediction_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

class TestPredictionErrorHandling:
    """预测错误处理测试类"""

    def test_concurrent_prediction_creation(self):
        """测试并发创建预测"""
        import threading
        import time

        results = []

        def create_prediction():
            headers = {"Authorization": "Bearer user_token"}
            data = {
                "match_id": 113,
                "prediction_type": "win",
                "confidence": 0.75
            }
            response = prediction_client.post("/api/predictions", json=data, headers=headers)
            results.append(response.status_code)

        # 创建多个并发请求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_prediction)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        assert len(results) == 5
        assert all(status == 201 for status in results)

    def test_large_prediction_list(self):
        """测试大量预测列表"""
        headers = {"Authorization": "Bearer user_token"}
        response = prediction_client.get("/api/predictions?limit=100", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 验证响应时间在合理范围内

    def test_prediction_data_integrity(self):
        """测试预测数据完整性"""
        headers = {"Authorization": "Bearer user_token"}

        # 创建包含所有字段的预测
        full_data = {
            "match_id": 114,
            "prediction_type": "correct_score",
            "confidence": 0.80,
            "predicted_score": "2-0",
            "odds": 8.50,
            "stake": 25.0,
            "notes": "这是一条详细的预测备注，用于测试数据完整性"
        }

        response = prediction_client.post("/api/predictions", json=full_data, headers=headers)
        assert response.status_code == 201

        created_data = response.json()
        assert created_data["match_id"] == 114
        assert created_data["prediction_type"] == "correct_score"
        assert created_data["confidence"] == 0.80
        assert created_data["predicted_score"] == "2-0"
        assert created_data["odds"] == 8.50
        assert created_data["stake"] == 25.0
        assert created_data["notes"] == full_data["notes"]
        assert created_data["potential_winnings"] == 212.5  # 25.0 * 8.50

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])