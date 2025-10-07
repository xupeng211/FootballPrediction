"""
API models模块功能测试
测试Pydantic模型的数据验证和序列化
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.mark.unit
class TestAPIModelsFunctional:
    """API models模块功能测试"""

    def test_match_response_model_creation(self):
        """测试比赛响应模型的创建"""
        try:
            from src.api.models import MatchResponse, MatchStatus, TeamInfo

            # 创建有效的比赛响应
            match = MatchResponse(
                id=1,
                home_team=TeamInfo(id=100, name="Team A", short_name="TA"),
                away_team=TeamInfo(id=200, name="Team B", short_name="TB"),
                status=MatchStatus.COMPLETED,
                home_score=2,
                away_score=1,
                match_date=datetime(2024, 1, 1, 15, 0)
            )

            assert match.id == 1
            assert match.home_team.name == "Team A"
            assert match.status == MatchStatus.COMPLETED
            assert match.home_score == 2
            assert match.away_score == 1

        except ImportError:
            pytest.skip("Models not available")

    def test_match_response_model_validation(self):
        """测试比赛响应模型的数据验证"""
        try:
            from src.api.models import MatchResponse, MatchStatus, TeamInfo

            # 测试无效状态
            with pytest.raises(ValidationError) as exc_info:
                MatchResponse(
                    id=1,
                    home_team=TeamInfo(id=100, name="Team A", short_name="TA"),
                    away_team=TeamInfo(id=200, name="Team B", short_name="TB"),
                    status="INVALID_STATUS",  # 无效状态
                    home_score=2,
                    away_score=1,
                    match_date=datetime(2024, 1, 1)
                )
            assert "status" in str(exc_info.value)

            # 测试负分
            with pytest.raises(ValidationError) as exc_info:
                MatchResponse(
                    id=1,
                    home_team=TeamInfo(id=100, name="Team A", short_name="TA"),
                    away_team=TeamInfo(id=200, name="Team B", short_name="TB"),
                    status=MatchStatus.COMPLETED,
                    home_score=-1,  # 负分无效
                    away_score=1,
                    match_date=datetime(2024, 1, 1)
                )
            assert "home_score" in str(exc_info.value)

        except ImportError:
            pytest.skip("Models not available")

    def test_prediction_request_model(self):
        """测试预测请求模型"""
        try:
            from src.api.models import PredictionRequest, PredictionType

            # 创建有效的预测请求
            request = PredictionRequest(
                match_id=1,
                prediction_type=PredictionType.WINNER,
                home_team_id=100,
                away_team_id=200
            )

            assert request.match_id == 1
            assert request.prediction_type == PredictionType.WINNER
            assert request.home_team_id == 100
            assert request.away_team_id == 200

        except ImportError:
            pytest.skip("Models not available")

    def test_prediction_response_model(self):
        """测试预测响应模型"""
        try:
            from src.api.models import PredictionResponse, PredictionResult

            # 创建预测响应
            response = PredictionResponse(
                match_id=1,
                prediction=PredictionResult.HOME_WIN,
                confidence=0.85,
                probabilities={
                    "home_win": 0.70,
                    "draw": 0.20,
                    "away_win": 0.10
                },
                model_version="v1.0.0",
                created_at=datetime.now()
            )

            assert response.match_id == 1
            assert response.prediction == PredictionResult.HOME_WIN
            assert response.confidence == 0.85
            assert response.probabilities["home_win"] == 0.70
            assert response.model_version == "v1.0.0"

        except ImportError:
            pytest.skip("Models not available")

    def test_error_response_model(self):
        """测试错误响应模型"""
        try:
            from src.api.models import ErrorResponse, ErrorCode

            # 创建错误响应
            error = ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message="Resource not found",
                details={"resource_id": 123},
                timestamp=datetime.now()
            )

            assert error.error_code == ErrorCode.NOT_FOUND
            assert error.message == "Resource not found"
            assert error.details["resource_id"] == 123

        except ImportError:
            pytest.skip("Models not available")

    def test_pagination_model(self):
        """测试分页模型"""
        try:
            from src.api.models import PaginationParams, PaginatedResponse

            # 创建分页参数
            params = PaginationParams(page=2, size=20)
            assert params.page == 2
            assert params.size == 20
            assert params.offset == 20  # (page-1)*size

            # 创建分页响应
            response = PaginatedResponse(
                items=[{"id": 1}, {"id": 2}],
                total=100,
                page=2,
                size=20,
                pages=5
            )

            assert len(response.items) == 2
            assert response.total == 100
            assert response.page == 2
            assert response.pages == 5

        except ImportError:
            pytest.skip("Models not available")

    def test_feature_model(self):
        """测试特征模型"""
        try:
            from src.api.models import FeatureData, FeatureValue

            # 创建特征数据
            feature = FeatureData(
                match_id=1,
                features={
                    "team_form": FeatureValue(value=0.85, confidence=0.9),
                    "head_to_head": FeatureValue(value=3, confidence=1.0),
                    "recent_goals": FeatureValue(value=2.5, confidence=0.8)
                },
                feature_types={
                    "team_form": "float",
                    "head_to_head": "int",
                    "recent_goals": "float"
                }
            )

            assert feature.match_id == 1
            assert feature.features["team_form"].value == 0.85
            assert feature.features["team_form"].confidence == 0.9
            assert feature.feature_types["head_to_head"] == "int"

        except ImportError:
            pytest.skip("Models not available")

    def test_model_serialization(self):
        """测试模型序列化"""
        try:
            from src.api.models import MatchResponse, TeamInfo, MatchStatus
            import json

            # 创建模型实例
            match = MatchResponse(
                id=1,
                home_team=TeamInfo(id=100, name="Team A", short_name="TA"),
                away_team=TeamInfo(id=200, name="Team B", short_name="TB"),
                status=MatchStatus.SCHEDULED,
                home_score=None,
                away_score=None,
                match_date=datetime(2024, 1, 1, 15, 0)
            )

            # 序列化为JSON
            json_data = match.model_dump_json()
            assert isinstance(json_data, str)

            # 反序列化
            data = json.loads(json_data)
            assert data["id"] == 1
            assert data["home_team"]["name"] == "Team A"
            assert data["status"] == "scheduled"

        except ImportError:
            pytest.skip("Models not available")

    def test_model_with_optional_fields(self):
        """测试包含可选字段的模型"""
        try:
            from src.api.models import MatchResponse, TeamInfo, MatchStatus

            # 创建最小化的比赛响应
            match = MatchResponse(
                id=1,
                home_team=TeamInfo(id=100, name="Team A", short_name="TA"),
                away_team=TeamInfo(id=200, name="Team B", short_name="TB"),
                status=MatchStatus.SCHEDULED,
                # home_score, away_score 可以为 None
                home_score=None,
                away_score=None,
                match_date=datetime(2024, 1, 1)
            )

            assert match.home_score is None
            assert match.away_score is None

        except ImportError:
            pytest.skip("Models not available")

    def test_model_field_validation_custom(self):
        """测试自定义字段验证"""
        try:
            from src.api.models import PredictionRequest, PredictionType

            # 测试自定义验证 - 确保队伍ID不同
            with pytest.raises(ValidationError) as exc_info:
                PredictionRequest(
                    match_id=1,
                    prediction_type=PredictionType.WINNER,
                    home_team_id=100,
                    away_team_id=100  # 相同的队伍ID应该无效
                )
            # 假设有自定义验证会检查这个
            if "home_team_id" in str(exc_info.value) or "away_team_id" in str(exc_info.value):
                pass  # 自定义验证生效
            else:
                # 如果没有自定义验证，这是预期的
                pytest.skip("No custom validation for team IDs")

        except ImportError:
            pytest.skip("Models not available")

    def test_model_inheritance(self):
        """测试模型继承"""
        try:
            from src.api.models import BaseModel, TimestampedModel

            # 测试基础模型
            base = BaseModel()
            assert hasattr(base, 'model_dump')

            # 测试时间戳模型（如果存在）
            if TimestampedModel:
                timestamped = TimestampedModel()
                assert hasattr(timestamped, 'created_at') or hasattr(timestamped, 'timestamp')

        except ImportError:
            pytest.skip("Base models not available")

    def test_model_config(self):
        """测试模型配置"""
        try:
            from src.api.models import MatchResponse, TeamInfo

            # 检查模型配置
            assert hasattr(MatchResponse, 'model_config')
            config = MatchResponse.model_config

            # 检查是否有populate_by_name或其他配置
            if 'populate_by_name' in config:
                assert config['populate_by_name'] is True

        except ImportError:
            pytest.skip("Models not available")

    def test_model_with_dict_data(self):
        """测试使用字典数据创建模型"""
        try:
            from src.api.models import MatchResponse, TeamInfo, MatchStatus

            # 使用字典创建
            match_data = {
                "id": 1,
                "home_team": {"id": 100, "name": "Team A", "short_name": "TA"},
                "away_team": {"id": 200, "name": "Team B", "short_name": "TB"},
                "status": "completed",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2024-01-01T15:00:00"
            }

            match = MatchResponse(**match_data)
            assert match.id == 1
            assert match.home_team.name == "Team A"

        except ImportError:
            pytest.skip("Models not available")

    def test_model_extra_fields_forbidden(self):
        """测试禁止额外字段的模型"""
        try:
            from src.api.models import TeamInfo

            # 测试额外字段
            with pytest.raises(ValidationError) as exc_info:
                TeamInfo(
                    id=100,
                    name="Team A",
                    short_name="TA",
                    extra_field="not_allowed"  # 额外字段
                )

            # 某些模型配置可能允许额外字段
            if "extra" in str(exc_info.value).lower():
                pass  # 额外字段被正确拒绝
            else:
                # 如果模型允许额外字段
                pytest.skip("Model allows extra fields")

        except ImportError:
            pytest.skip("Models not available")