"""通用模型测试"""

import pytest
from datetime import datetime
from src.models.common_models import (
    ContentType,
    UserRole,
    AnalysisResult,
    Content,
    UserProfile,
    User,
    DataValidationResult,
    FeatureVector,
    MatchData,
    ModelMetrics,
    PredictionRequest,
    PredictionResponse,
)


class TestContentType:
    """内容类型枚举测试"""

    def test_content_type_values(self):
        """测试内容类型枚举值"""
        assert ContentType.TEXT.value == "text"
        assert ContentType.IMAGE.value == "image"
        assert ContentType.VIDEO.value == "video"
        assert ContentType.AUDIO.value == "audio"
        assert ContentType.DOCUMENT.value == "document"


class TestUserRole:
    """用户角色枚举测试"""

    def test_user_role_values(self):
        """测试用户角色枚举值"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.GUEST.value == "guest"
        assert UserRole.MODERATOR.value == "moderator"


class TestUserProfile:
    """用户配置文件测试"""

    def test_user_profile_creation(self):
        """测试用户配置文件创建"""
        created_at = datetime.now()
        profile = UserProfile(
            user_id="user123",
            display_name="测试用户",
            email="test@example.com",
            preferences={"theme": "dark", "lang": "zh"},
            created_at=created_at,
        )

        assert profile.user_id == "user123"
        assert profile.display_name == "测试用户"
        assert profile.email == "test@example.com"
        assert profile.preferences["theme"] == "dark"

        dict_result = profile.to_dict()
        assert dict_result["user_id"] == "user123"
        assert dict_result["display_name"] == "测试用户"


class TestUser:
    """用户模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        created_at = datetime.now()
        profile = UserProfile(
            user_id="user123",
            display_name="测试用户",
            email="test@example.com",
            preferences={},
            created_at=created_at,
        )

        user = User(
            id="user123", username="testuser", role=UserRole.USER, profile=profile
        )

        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.created_at is not None

        # 测试权限检查
        assert user.has_permission("read") is True
        assert user.has_permission("write") is True
        assert user.has_permission("admin") is False

    def test_admin_permissions(self):
        """测试管理员权限"""
        profile = UserProfile(
            user_id="admin123",
            display_name="管理员",
            email="admin@example.com",
            preferences={},
            created_at=datetime.now(),
        )

        admin = User(
            id="admin123", username="admin", role=UserRole.ADMIN, profile=profile
        )

        assert admin.has_permission("admin") is True
        assert admin.has_permission("any_permission") is True


class TestMatchData:
    """比赛数据测试"""

    def test_match_data_creation(self):
        """测试比赛数据创建"""
        match = MatchData(
            match_id="match123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-15",
            home_score=2,
            away_score=1,
            league="Premier League",
        )

        assert match.home_team == "Team A"
        assert match.away_team == "Team B"
        assert match.get_result() == "home_win"

        # 测试平局
        match.home_score = 1
        match.away_score = 1
        assert match.get_result() == "draw"

        # 测试客胜
        match.home_score = 0
        match.away_score = 2
        assert match.get_result() == "away_win"

    def test_match_validation(self):
        """测试比赛数据验证"""
        valid_match = MatchData(
            match_id="match123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-15",
        )

        assert valid_match.is_valid() is True

        # 测试无效数据
        invalid_match = MatchData(
            match_id="", home_team="", away_team="", match_date=""
        )

        assert invalid_match.is_valid() is False


class TestPredictionRequest:
    """预测请求测试"""

    def test_prediction_request_creation(self):
        """测试预测请求创建"""
        request = PredictionRequest(
            match_id="match123",
            home_team="Team A",
            away_team="Team B",
            features={"home_form": 0.8, "away_form": 0.6},
        )

        assert request.match_id == "match123"
        assert request.is_valid() is True

        dict_result = request.to_dict()
        assert dict_result["home_team"] == "Team A"
        assert "features" in dict_result


class TestFeatureVector:
    """特征向量测试"""

    def test_feature_vector_creation(self):
        """测试特征向量创建"""
        features = [1.0, 0.5, 0.8, 0.3]
        vector = FeatureVector(
            match_id="match123",
            features=features,
            feature_names=["f1", "f2", "f3", "f4"],
        )

        assert len(vector.features) == 4
        assert vector.features[0] == 1.0
        assert vector.is_empty() is False

        # 测试归一化
        normalized = vector.normalize()
        assert len(normalized) == 4
        assert max(normalized) <= 1.0
        assert min(normalized) >= 0.0

        # 测试统计信息
        stats = vector.get_statistics()
        assert "mean" in stats
        assert "std" in stats


class TestDataValidationResult:
    """数据验证结果测试"""

    def test_validation_result_creation(self):
        """测试验证结果创建"""
        result = DataValidationResult(is_valid=True, errors=[], warnings=["警告1"])

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1

        # 测试添加错误
        result.add_error("严重错误")
        assert result.is_valid is False
        assert len(result.errors) == 1

        # 测试添加警告
        result.add_warning("警告2")
        assert len(result.warnings) == 2

        # 测试摘要
        summary = result.get_summary()
        assert "无效" in summary
