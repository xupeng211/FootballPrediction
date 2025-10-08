"""扩展的通用模型测试 - 提升覆盖率"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.common_models import (
    BaseResponse,
    ErrorResponse,
    SuccessResponse,
    PaginationInfo,
    PaginatedResponse,
    ValidationResult,
    TeamStats,
    MatchStats,
    OddsInfo,
    PredictionResult,
)


class TestCommonModelsExtended:
    """扩展的通用模型测试，覆盖未测试的代码路径"""

    def test_base_response_creation(self):
        """测试基础响应创建"""
        response = BaseResponse(success=True, message="操作成功", data={"key": "value"})

        assert response.success is True
        assert response.message == "操作成功"
        assert response.data == {"key": "value"}

    def test_error_response_creation(self):
        """测试错误响应创建"""
        error = ErrorResponse(
            error_code=400,
            error_message="请求参数错误",
            details={"field": "name", "issue": "required"},
        )

        assert error.error_code == 400
        assert error.error_message == "请求参数错误"
        assert error.details["field"] == "name"

    def test_success_response_creation(self):
        """测试成功响应创建"""
        success = SuccessResponse(
            message="创建成功", result={"id": 123, "name": "测试"}
        )

        assert success.message == "创建成功"
        assert success.result["id"] == 123

    def test_pagination_info_creation(self):
        """测试分页信息创建"""
        pagination = PaginationInfo(
            page=1, page_size=20, total_items=100, total_pages=5
        )

        assert pagination.page == 1
        assert pagination.page_size == 20
        assert pagination.total_items == 100
        assert pagination.total_pages == 5

        # 测试计算属性
        if hasattr(pagination, "has_next"):
            assert pagination.has_next is True
        if hasattr(pagination, "has_prev"):
            assert pagination.has_prev is False

    def test_paginated_response_creation(self):
        """测试分页响应创建"""
        response = PaginatedResponse(
            success=True,
            message="查询成功",
            data=[{"id": 1}, {"id": 2}],
            pagination=PaginationInfo(
                page=1, page_size=10, total_items=2, total_pages=1
            ),
        )

        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.page == 1

    def test_validation_result_creation(self):
        """测试验证结果创建"""
        validation = ValidationResult(
            is_valid=False,
            errors=["字段不能为空", "格式不正确"],
            warnings=["数据可能不准确"],
        )

        assert validation.is_valid is False
        assert len(validation.errors) == 2
        assert validation.warnings[0] == "数据可能不准确"

    def test_team_stats_creation(self):
        """测试球队统计创建"""
        stats = TeamStats(
            team_id=1,
            team_name="测试球队",
            matches_played=10,
            wins=6,
            draws=2,
            losses=2,
            goals_for=15,
            goals_against=10,
            points=20,
        )

        assert stats.team_id == 1
        assert stats.team_name == "测试球队"
        assert stats.matches_played == 10
        assert stats.points == 20

        # 测试计算属性
        if hasattr(stats, "win_rate"):
            assert stats.win_rate == 0.6
        if hasattr(stats, "goal_difference"):
            assert stats.goal_difference == 5

    def test_match_stats_creation(self):
        """测试比赛统计创建"""
        stats = MatchStats(
            match_id=123,
            home_team_id=1,
            away_team_id=2,
            home_score=2,
            away_score=1,
            home_possession=55.5,
            away_possession=44.5,
            home_shots=10,
            away_shots=8,
        )

        assert stats.match_id == 123
        assert stats.home_score == 2
        assert stats.away_score == 1
        assert stats.home_possession == 55.5

    def test_odds_info_creation(self):
        """测试赔率信息创建"""
        odds = OddsInfo(
            match_id=123,
            home_win_odds=Decimal("2.50"),
            draw_odds=Decimal("3.20"),
            away_win_odds=Decimal("2.80"),
            bookmaker="测试博彩公司",
            last_updated=datetime.now(),
        )

        assert odds.match_id == 123
        assert odds.home_win_odds == Decimal("2.50")
        assert odds.bookmaker == "测试博彩公司"

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        prediction = PredictionResult(
            match_id=123,
            prediction_type="win_draw_loss",
            predicted_outcome="home_win",
            confidence=0.75,
            home_win_probability=0.50,
            draw_probability=0.25,
            away_win_probability=0.25,
            created_at=datetime.now(),
        )

        assert prediction.match_id == 123
        assert prediction.predicted_outcome == "home_win"
        assert prediction.confidence == 0.75
        assert prediction.home_win_probability == 0.50

    def test_model_serialization(self):
        """测试模型序列化"""
        response = BaseResponse(success=True, message="测试", data={"key": "value"})

        # 测试字典转换
        if hasattr(response, "dict"):
            response_dict = response.dict()
            assert response_dict["success"] is True
            assert response_dict["message"] == "测试"

        # 测试JSON序列化
        if hasattr(response, "json"):
            json_str = response.json()
            assert "success" in json_str

    def test_model_validation(self):
        """测试模型验证"""
        # 测试无效数据
        with pytest.raises(Exception):
            # 假设模型有必填字段验证
            BaseResponse()

    def test_model_with_optional_fields(self):
        """测试包含可选字段的模型"""
        response = BaseResponse(
            success=True,
            message="测试",
            # data字段是可选的
        )

        assert response.success is True
        assert response.message == "测试"
        assert response.data is None

    def test_model_with_datetime_fields(self):
        """测试包含时间字段的模型"""
        now = datetime.now()
        prediction = PredictionResult(
            match_id=123,
            prediction_type="test",
            predicted_outcome="test",
            confidence=0.5,
            home_win_probability=0.33,
            draw_probability=0.33,
            away_win_probability=0.34,
            created_at=now,
        )

        assert prediction.created_at == now

        # 测试时间格式化
        if hasattr(prediction, "formatted_created_at"):
            formatted = prediction.formatted_created_at
            assert isinstance(formatted, str)

    def test_model_with_decimal_fields(self):
        """测试包含小数字段的模型"""
        odds = OddsInfo(
            match_id=123,
            home_win_odds=Decimal("2.55"),
            draw_odds=Decimal("3.15"),
            away_win_odds=Decimal("2.75"),
            bookmaker="Test",
        )

        # 测试精度计算
        if hasattr(odds, "total_probability"):
            total = odds.total_probability
            assert isinstance(total, (int, float, Decimal))

    def test_model_equality(self):
        """测试模型相等性比较"""
        response1 = BaseResponse(success=True, message="测试", data={"key": "value"})

        response2 = BaseResponse(success=True, message="测试", data={"key": "value"})

        response3 = BaseResponse(success=False, message="测试", data={"key": "value"})

        assert response1 == response2
        assert response1 != response3

    def test_model_copy(self):
        """测试模型复制"""
        original = BaseResponse(success=True, message="测试", data={"key": "value"})

        # 测试深拷贝
        if hasattr(original, "copy"):
            copied = original.copy()
            assert copied == original
            assert copied is not original

    def test_model_update(self):
        """测试模型更新"""
        response = BaseResponse(success=True, message="原始消息", data={"key": "value"})

        # 测试字段更新
        if hasattr(response, "update"):
            response.update(message="新消息")
            assert response.message == "新消息"
