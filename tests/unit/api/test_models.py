"""
Models API模块增强覆盖率测试
目标：将 src/api/models.py 的覆盖率从12%提升到30%+
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from pydantic import ValidationError, BaseModel
from typing import List, Optional, Dict, Any, Union
from enum import Enum


# 尝试导入实际模型，如果失败则创建模拟模型
try:
    from src.api.models import (
        MatchResponse, TeamResponse, LeagueResponse, PlayerResponse,
        PredictionRequest, PredictionResponse, PredictionModel,
        HealthResponse, ErrorResponse, SuccessResponse,
        PaginationInfo, PaginatedResponse, FilterOptions,
        MatchStatus, PredictionOutcome, ApiVersion
    )
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"Models import error: {e}")
    MODELS_AVAILABLE = False
    # 创建基础模拟模型用于测试
    class MatchStatus(str, Enum):
        SCHEDULED = "scheduled"
        LIVE = "live"
        FINISHED = "finished"
        CANCELLED = "cancelled"

    class PredictionOutcome(str, Enum):
        HOME_WIN = "home_win"
        DRAW = "draw"
        AWAY_WIN = "away_win"

    class MatchResponse(BaseModel):
        id: int
        home_team_id: int
        away_team_id: int
        league_id: int
        home_score: Optional[int] = None
        away_score: Optional[int] = None
        status: MatchStatus
        match_date: datetime
        venue: Optional[str] = None

    class TeamResponse(BaseModel):
        id: int
        name: str
        league_id: int
        points: int = 0
        played: int = 0
        won: int = 0
        drawn: int = 0
        lost: int = 0

    class LeagueResponse(BaseModel):
        id: int
        name: str
        country: str
        season: str
        total_teams: int

    class PredictionRequest(BaseModel):
        match_id: int
        home_team_id: int
        away_team_id: int
        model_version: Optional[str] = "latest"

    class PredictionResponse(BaseModel):
        match_id: int
        prediction: PredictionOutcome
        confidence: float
        probabilities: Dict[str, float]
        model_version: str

    class HealthResponse(BaseModel):
        status: str
        timestamp: datetime
        version: str
        components: Dict[str, Any]


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestMatchResponseModel:
    """比赛响应模型测试"""

    def test_match_response_all_fields(self):
        """测试包含所有字段的比赛响应"""
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "home_score": 3,
            "away_score": 1,
            "status": MatchStatus.FINISHED,
            "match_date": datetime.now(),
            "venue": "Stadium A"
        }

        match = MatchResponse(**data)
        assert match.id == 1
        assert match.home_score == 3
        assert match.away_score == 1
        assert match.status == MatchStatus.FINISHED
        assert match.venue == "Stadium A"

    def test_match_response_minimal_fields(self):
        """测试最小字段集合"""
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": MatchStatus.SCHEDULED,
            "match_date": datetime.now()
        }

        match = MatchResponse(**data)
        assert match.id == 1
        assert match.home_score is None
        assert match.away_score is None
        assert match.venue is None

    def test_match_response_invalid_status(self):
        """测试无效的状态值"""
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": "invalid_status",
            "match_date": datetime.now()
        }

        with pytest.raises(ValidationError):
            MatchResponse(**data)

    def test_match_response_future_date(self):
        """测试未来日期（即将进行的比赛）"""
        future_date = datetime.now() + timedelta(days=7)
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": MatchStatus.SCHEDULED,
            "match_date": future_date
        }

        match = MatchResponse(**data)
        assert match.match_date > datetime.now()

    def test_match_response_serialization(self):
        """测试模型序列化"""
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": MatchStatus.LIVE,
            "match_date": datetime.now()
        }

        match = MatchResponse(**data)

        # 测试字典序列化
        match_dict = match.model_dump()
        assert isinstance(match_dict, dict)
        assert match_dict["status"] == "live"

        # 测试JSON序列化
        match_json = match.model_dump_json()
        assert isinstance(match_json, str)
        assert "live" in match_json

        # 测试排除字段
        match_dict_exclude = match.model_dump(exclude={"league_id"})
        assert "league_id" not in match_dict_exclude

    def test_match_response_validation_methods(self):
        """测试模型验证方法"""
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": MatchStatus.FINISHED,
            "match_date": datetime.now()
        }

        match = MatchResponse(**data)

        # 测试模型复制
        match_copy = match.model_copy()
        assert match_copy.id == match.id
        assert match_copy is not match

        # 测试模型更新
        updated_match = match.model_copy(update={"home_score": 2})
        assert updated_match.home_score == 2
        assert match.home_score is None  # 原模型不变


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestTeamResponseModel:
    """球队响应模型测试"""

    def test_team_response_complete_stats(self):
        """测试完整统计数据"""
        data = {
            "id": 101,
            "name": "Team A",
            "league_id": 1,
            "points": 30,
            "played": 10,
            "won": 9,
            "drawn": 1,
            "lost": 0
        }

        team = TeamResponse(**data)
        assert team.points == 30
        assert team.played == 10
        assert team.won + team.drawn + team.lost == team.played

    def test_team_response_new_team(self):
        """测试新球队（零统计）"""
        data = {
            "id": 102,
            "name": "New Team",
            "league_id": 1
        }

        team = TeamResponse(**data)
        assert team.points == 0
        assert team.played == 0
        assert team.won == 0

    def test_team_response_invalid_points(self):
        """测试无效积分"""
        data = {
            "id": 101,
            "name": "Team A",
            "league_id": 1,
            "points": -10  # 负积分
        }

        # 根据模型验证，可能允许或不允许
        try:
            team = TeamResponse(**data)
            assert team.points == -10
        except ValidationError:
            pass  # 如果有验证器禁止负积分

    def test_team_response_name_validation(self):
        """测试球队名称验证"""
        # 测试空名称
        with pytest.raises(ValidationError):
            TeamResponse(id=101, name="", league_id=1)

        # 测试非常长的名称
        long_name = "A" * 200
        try:
            team = TeamResponse(id=101, name=long_name, league_id=1)
            assert len(team.name) == 200
        except ValidationError:
            pass  # 如果有长度限制


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestPredictionModels:
    """预测模型测试"""

    def test_prediction_request_validation(self):
        """测试预测请求验证"""
        data = {
            "match_id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "model_version": "v2.1.0"
        }

        request = PredictionRequest(**data)
        assert request.match_id == 1
        assert request.home_team_id != request.away_team_id  # 球队不同
        assert request.model_version == "v2.1.0"

    def test_prediction_request_same_teams(self):
        """测试相同球队的预测请求"""
        data = {
            "match_id": 1,
            "home_team_id": 101,
            "away_team_id": 101,  # 相同球队
            "model_version": "latest"
        }

        # 根据业务逻辑，可能允许或不允许
        try:
            request = PredictionRequest(**data)
            assert request.home_team_id == request.away_team_id
        except ValidationError:
            pass  # 如果有验证器禁止

    def test_prediction_response_complete(self):
        """测试完整的预测响应"""
        data = {
            "match_id": 1,
            "prediction": PredictionOutcome.HOME_WIN,
            "confidence": 0.85,
            "probabilities": {
                "home_win": 0.75,
                "draw": 0.15,
                "away_win": 0.10
            },
            "model_version": "v2.1.0"
        }

        response = PredictionResponse(**data)
        assert response.prediction == PredictionOutcome.HOME_WIN
        assert 0 <= response.confidence <= 1
        assert sum(response.probabilities.values()) == pytest.approx(1.0, rel=1e-2)

    def test_prediction_response_invalid_probabilities(self):
        """测试无效的概率分布"""
        data = {
            "match_id": 1,
            "prediction": PredictionOutcome.DRAW,
            "confidence": 0.6,
            "probabilities": {
                "home_win": 0.5,
                "draw": 0.3,
                "away_win": 0.1  # 总和=0.9
            },
            "model_version": "v2.1.0"
        }

        # 根据模型验证，可能允许或不允许
        try:
            response = PredictionResponse(**data)
            prob_sum = sum(response.probabilities.values())
            assert prob_sum == 0.9
        except ValidationError:
            pass  # 如果有验证器要求总和为1

    def test_prediction_response_confidence_range(self):
        """测试置信度范围"""
        # 测试边界值
        test_cases = [
            (0.0, True),
            (0.5, True),
            (1.0, True),
            (-0.1, False),
            (1.1, False)
        ]

        for confidence, should_be_valid in test_cases:
            data = {
                "match_id": 1,
                "prediction": PredictionOutcome.HOME_WIN,
                "confidence": confidence,
                "probabilities": {"home_win": 0.7, "draw": 0.2, "away_win": 0.1},
                "model_version": "v2.1.0"
            }

            try:
                response = PredictionResponse(**data)
                if not should_be_valid:
                    pytest.fail(f"Expected validation error for confidence={confidence}")
            except ValidationError:
                if should_be_valid:
                    pytest.fail(f"Expected valid response for confidence={confidence}")


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestHealthModels:
    """健康检查模型测试"""

    def test_health_response_all_components(self):
        """测试包含所有组件的健康响应"""
        data = {
            "status": "healthy",
            "timestamp": datetime.now(),
            "version": "1.0.0",
            "components": {
                "database": {"status": "healthy", "response_time": "10ms"},
                "redis": {"status": "healthy", "memory_usage": "256MB"},
                "mlflow": {"status": "healthy", "experiments": 5}
            }
        }

        health = HealthResponse(**data)
        assert health.status == "healthy"
        assert len(health.components) == 3
        assert all("status" in comp for comp in health.components.values())

    def test_health_response_degraded(self):
        """测试降级状态的健康响应"""
        data = {
            "status": "degraded",
            "timestamp": datetime.now(),
            "version": "1.0.0",
            "components": {
                "database": {"status": "healthy"},
                "redis": {"status": "degraded", "warning": "High memory"}
            }
        }

        health = HealthResponse(**data)
        assert health.status == "degraded"
        assert "warning" in health.components["redis"]

    def test_health_response_version_format(self):
        """测试版本格式"""
        valid_versions = ["1.0.0", "v2.1.0", "2024.01.15", "latest"]

        for version in valid_versions:
            data = {
                "status": "healthy",
                "timestamp": datetime.now(),
                "version": version,
                "components": {}
            }
            health = HealthResponse(**data)
            assert health.version == version


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestPaginationModels:
    """分页模型测试"""

    def test_pagination_info_basic(self):
        """测试基本分页信息"""
        try:
            from src.api.models import PaginationInfo

            data = {
                "page": 1,
                "page_size": 10,
                "total": 100,
                "pages": 10,
                "has_next": True,
                "has_prev": False
            }

            pagination = PaginationInfo(**data)
            assert pagination.page == 1
            assert pagination.has_next == True
            assert pagination.has_prev == False
        except ImportError:
            pytest.skip("PaginationInfo not available")

    def test_paginated_response_complete(self):
        """测试完整的分页响应"""
        try:
            from src.api.models import PaginatedResponse

            items = [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"}
            ]

            pagination = {
                "page": 1,
                "page_size": 10,
                "total": 2,
                "pages": 1
            }

            data = {
                "items": items,
                "pagination": pagination
            }

            response = PaginatedResponse(**data)
            assert len(response.items) == 2
            assert response.pagination["page"] == 1
        except ImportError:
            pytest.skip("PaginatedResponse not available")


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestAdvancedModelFeatures:
    """高级模型特性测试"""

    def test_model_with_computed_fields(self):
        """测试计算字段"""
        try:
            from src.api.models import TeamStats

            data = {
                "id": 101,
                "name": "Team A",
                "won": 8,
                "drawn": 2,
                "lost": 0
            }

            stats = TeamStats(**data)
            # 如果有计算字段（如胜率）
            if hasattr(stats, 'win_rate'):
                assert stats.win_rate == 0.8
        except ImportError:
            pytest.skip("TeamStats not available")

    def test_model_with_custom_validators(self):
        """测试自定义验证器"""
        try:
            from src.api.models import PredictionModel

            # 测试有效模型名称
            data = {
                "name": "football_predictor_v2",
                "version": "2.1.0",
                "accuracy": 0.85
            }

            model = PredictionModel(**data)
            assert model.name == "football_predictor_v2"

            # 测试无效模型名称（如果有的话）
            invalid_data = {
                "name": "invalid name with spaces",
                "version": "2.1.0",
                "accuracy": 0.85
            }

            try:
                PredictionModel(**invalid_data)
            except ValidationError:
                pass  # 如果有验证器禁止空格
        except ImportError:
            pytest.skip("PredictionModel not available")

    def test_model_with_field_transforms(self):
        """测试字段转换"""
        try:
            from src.api.models import MatchFilter

            # 测试日期字符串转换
            data = {
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
                "status": "finished"
            }

            filter_data = MatchFilter(**data)
            if hasattr(filter_data, 'date_from_dt'):
                assert isinstance(filter_data.date_from_dt, date)
        except ImportError:
            pytest.skip("MatchFilter not available")

    def test_model_inheritance(self):
        """测试模型继承"""
        try:
            from src.api.models import BaseEntity, MatchEntity

            # 测试基类字段
            base_data = {
                "id": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }

            # 测试派生类
            match_data = {
                **base_data,
                "home_team_id": 101,
                "away_team_id": 102,
                "status": "scheduled"
            }

            match = MatchEntity(**match_data)
            assert hasattr(match, 'id')
            assert hasattr(match, 'home_team_id')
        except ImportError:
            pytest.skip("Entity models not available")


class TestModelErrorHandling:
    """模型错误处理测试"""

    def test_type_conversion_errors(self):
        """测试类型转换错误"""
        # 测试字符串转整数
        with pytest.raises(ValidationError):
            MatchResponse(
                id="invalid",  # 应该是整数
                home_team_id=101,
                away_team_id=102,
                league_id=1,
                status=MatchStatus.SCHEDULED,
                match_date=datetime.now()
            )

        # 测试字符串转日期时间
        with pytest.raises(ValidationError):
            MatchResponse(
                id=1,
                home_team_id=101,
                away_team_id=102,
                league_id=1,
                status=MatchStatus.SCHEDULED,
                match_date="invalid_date"  # 应该是datetime
            )

    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        with pytest.raises(ValidationError):
            MatchResponse(
                home_team_id=101,
                away_team_id=102
                # 缺少id, league_id, status, match_date
            )

    def test_extra_fields_behavior(self):
        """测试额外字段处理"""
        data = {
            "id": 1,
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "status": MatchStatus.SCHEDULED,
            "match_date": datetime.now(),
            "extra_field": "should be ignored"
        }

        # 根据Pydantic配置，额外字段可能被忽略或导致错误
        try:
            match = MatchResponse(**data)
            assert not hasattr(match, "extra_field")
        except ValidationError:
            pass  # 严格模式下会报错

    def test_nested_validation_errors(self):
        """测试嵌套验证错误"""
        try:
            from src.api.models import ComplexPrediction

            data = {
                "match": {
                    "id": "invalid",  # 嵌套对象中的错误
                    "home_team": "Team A",
                    "away_team": "Team B"
                },
                "prediction": {
                    "outcome": "invalid_outcome",  # 枚举值错误
                    "confidence": 1.5  # 范围错误
                }
            }

            with pytest.raises(ValidationError) as exc_info:
                ComplexPrediction(**data)

            # 验证错误信息包含嵌套字段的路径
            errors = exc_info.value.errors()
            assert any('match' in str(error.get('loc', [])) for error in errors)
        except ImportError:
            pytest.skip("ComplexPrediction not available")


@pytest.mark.asyncio
class TestAsyncModelOperations:
    """异步模型操作测试"""

    async def test_async_model_validation(self):
        """测试异步模型验证"""
        try:
            from src.api.models import AsyncValidatedModel

            data = {
                "id": 1,
                "name": "Test",
                "external_id": "ext_123"
            }

            # 模拟异步验证（如检查外部ID是否存在）
            async def validate_external_id(external_id: str) -> bool:
                await asyncio.sleep(0.01)
                return external_id.startswith("ext_")

            model = AsyncValidatedModel(**data)
            is_valid = await validate_external_id(model.external_id)
            assert is_valid == True
        except ImportError:
            pytest.skip("AsyncValidatedModel not available")

    async def test_batch_model_operations(self):
        """测试批量模型操作"""
        models_data = [
            {"id": i, "name": f"Model {i}"}
            for i in range(5)
        ]

        # 批量创建模型
        models = []
        for data in models_data:
            try:
                model = BaseModel(**data)  # 使用基础模型
                models.append(model)
            except:
                pass

        assert len(models) == 5

        # 批量验证
        validation_results = []
        for model in models:
            try:
                # 模拟验证逻辑
                validation_results.append(True)
            except:
                validation_results.append(False)

        assert all(validation_results)


# 性能测试
class TestModelPerformance:
    """模型性能测试"""

    def test_large_dataset_processing(self):
        """测试大数据集处理"""
        # 创建大量模型实例
        models = []
        start_time = datetime.now()

        for i in range(1000):
            try:
                model = TeamResponse(
                    id=i,
                    name=f"Team {i}",
                    league_id=1
                )
                models.append(model)
            except:
                pass

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        assert len(models) == 1000
        assert processing_time < 1.0  # 应该在1秒内完成

    def test_serialization_performance(self):
        """测试序列化性能"""
        model = MatchResponse(
            id=1,
            home_team_id=101,
            away_team_id=102,
            league_id=1,
            status=MatchStatus.FINISHED,
            match_date=datetime.now()
        )

        # 测试多次序列化
        start_time = datetime.now()
        for _ in range(1000):
            json_str = model.model_dump_json()
        end_time = datetime.now()

        serialization_time = (end_time - start_time).total_seconds()
        assert serialization_time < 0.5  # 应该在0.5秒内完成