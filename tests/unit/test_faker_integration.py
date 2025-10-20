"""
Faker集成测试
Faker Integration Tests

测试Faker数据生成功能。
"""

import pytest
from datetime import datetime, timedelta
from tests.factories.fake_data import (
    FootballDataFactory,
    APIDataFactory,
    create_fake_match,
    create_fake_prediction,
    create_fake_user,
    create_batch_fake_data,
)


@pytest.mark.unit
@pytest.mark.fast
class TestFootballDataFactory:
    """测试足球数据工厂"""

    def test_create_match(self):
        """测试生成比赛数据"""
        match = FootballDataFactory.match()

        # 验证必需字段
        assert "match_id" in match
        assert "home_team" in match
        assert "away_team" in match
        assert "home_score" in match
        assert "away_score" in match
        assert "match_date" in match

        # 验证数据类型和范围
        assert isinstance(match["match_id"], int)
        assert isinstance(match["home_team"], str)
        assert isinstance(match["away_team"], str)
        assert isinstance(match["home_score"], int)
        assert isinstance(match["away_score"], int)
        assert isinstance(match["match_date"], datetime)

        # 验证分数范围
        assert 0 <= match["home_score"] <= 5
        assert 0 <= match["away_score"] <= 5

    def test_create_team(self):
        """测试生成球队数据"""
        team = FootballDataFactory.team()

        # 验证必需字段
        required_fields = ["team_id", "name", "league", "founded_year", "home_city"]
        for field in required_fields:
            assert field in team, f"Missing field: {field}"

        # 验证数据类型
        assert isinstance(team["team_id"], int)
        assert isinstance(team["name"], str)
        assert isinstance(team["founded_year"], int)
        assert 1900 <= team["founded_year"] <= 2020

    def test_create_player(self):
        """测试生成球员数据"""
        player = FootballDataFactory.player()

        # 验证必需字段
        required_fields = ["player_id", "name", "age", "position", "team"]
        for field in required_fields:
            assert field in player, f"Missing field: {field}"

        # 验证数据范围
        assert 18 <= player["age"] <= 40
        assert player["position"] in ["前锋", "中场", "后卫", "门将"]
        assert player["height"] >= 160
        assert player["weight"] >= 60

    def test_create_prediction(self):
        """测试生成预测数据"""
        prediction = FootballDataFactory.prediction()

        # 验证必需字段
        required_fields = [
            "match_id",
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "predicted_outcome",
            "confidence",
            "model_version",
            "predicted_at",
        ]
        for field in required_fields:
            assert field in prediction, f"Missing field: {field}"

        # 验证概率总和为1
        total_prob = (
            prediction["home_win_prob"]
            + prediction["draw_prob"]
            + prediction["away_win_prob"]
        )
        assert abs(total_prob - 1.0) < 0.02, f"Probabilities sum to {total_prob}"

        # 验证置信度范围
        assert 0.5 <= prediction["confidence"] <= 0.95

        # 验证预测结果
        assert prediction["predicted_outcome"] in ["home", "draw", "away"]

    def test_create_user(self):
        """测试生成用户数据"""
        user = FootballDataFactory.user()

        # 验证必需字段
        required_fields = [
            "user_id",
            "username",
            "email",
            "full_name",
            "phone",
            "date_of_birth",
            "country",
            "city",
        ]
        for field in required_fields:
            assert field in user, f"Missing field: {field}"

        # 验证数据格式
        assert "@" in user["email"]
        assert isinstance(user["date_of_birth"], datetime)
        assert isinstance(user["user_id"], str)  # UUID4

    def test_batch_predictions(self):
        """测试批量生成预测数据"""
        count = 5
        predictions = FootballDataFactory.batch_predictions(count)

        assert len(predictions) == count
        for prediction in predictions:
            assert isinstance(prediction, dict)
            assert "match_id" in prediction
            assert prediction["predicted_outcome"] in ["home", "draw", "away"]

    def test_batch_matches(self):
        """测试批量生成比赛数据"""
        count = 3
        matches = FootballDataFactory.batch_matches(count)

        assert len(matches) == count
        for match in matches:
            assert isinstance(match, dict)
            assert "match_id" in match
            assert "home_team" in match
            assert "away_team" in match

    def test_batch_teams(self):
        """测试批量生成球队数据"""
        count = 4
        teams = FootballDataFactory.batch_teams(count)

        assert len(teams) == count
        for team in teams:
            assert isinstance(team, dict)
            assert "team_id" in team
            assert "name" in team


@pytest.mark.unit
@pytest.mark.fast
class TestAPIDataFactory:
    """测试API数据工厂"""

    def test_prediction_request(self):
        """测试生成预测请求数据"""
        request = APIDataFactory.prediction_request()

        assert "match_id" in request
        assert "model_version" in request
        assert "include_details" in request

        assert isinstance(request["match_id"], int)
        assert isinstance(request["include_details"], bool)
        assert request["model_version"] in ["default", "v1.0", "v2.0", "advanced"]

    def test_batch_prediction_request(self):
        """测试生成批量预测请求数据"""
        request = APIDataFactory.batch_prediction_request(5)

        assert "match_ids" in request
        assert "model_version" in request

        assert len(request["match_ids"]) == 5
        assert all(isinstance(mid, int) for mid in request["match_ids"])
        assert request["model_version"] in ["default", "v1.0", "v2.0"]

    def test_verification_request(self):
        """测试生成验证请求数据"""
        request = APIDataFactory.verification_request()

        assert "match_id" in request
        assert "actual_result" in request

        assert isinstance(request["match_id"], int)
        assert request["actual_result"] in ["home", "draw", "away"]

    def test_health_check_response(self):
        """测试生成健康检查响应数据"""
        response = APIDataFactory.health_check_response()

        assert "status" in response
        assert "timestamp" in response
        assert "service" in response
        assert "checks" in response

        assert response["status"] == "healthy"
        assert response["service"] == "football-prediction-api"
        assert isinstance(response["checks"], dict)


@pytest.mark.unit
@pytest.mark.fast
class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_fake_match(self):
        """测试便捷函数创建比赛"""
        match = create_fake_match()
        assert isinstance(match, dict)
        assert "match_id" in match

    def test_create_fake_prediction(self):
        """测试便捷函数创建预测"""
        prediction = create_fake_prediction()
        assert isinstance(prediction, dict)
        assert "predicted_outcome" in prediction

    def test_create_fake_user(self):
        """测试便捷函数创建用户"""
        user = create_fake_user()
        assert isinstance(user, dict)
        assert "username" in user

    def test_create_batch_fake_data(self):
        """测试便捷函数批量创建数据"""
        # 测试匹配数据
        matches = create_batch_fake_data("matches", 3)
        assert len(matches) == 3
        assert all("match_id" in m for m in matches)

        # 测试预测数据
        predictions = create_batch_fake_data("predictions", 5)
        assert len(predictions) == 5
        assert all("predicted_outcome" in p for p in predictions)

        # 测试错误数据类型
        with pytest.raises(ValueError):
            create_batch_fake_data("invalid_type", 2)


@pytest.mark.unit
@pytest.mark.fast
class TestDataConsistency:
    """测试数据一致性"""

    def test_probability_sum(self):
        """测试概率总和始终为1"""
        for _ in range(10):
            prediction = FootballDataFactory.prediction()
            total = (
                prediction["home_win_prob"]
                + prediction["draw_prob"]
                + prediction["away_win_prob"]
            )
            assert abs(total - 1.0) < 0.01, f"Probabilities sum to {total}"

    def test_date_ranges(self):
        """测试日期在合理范围内"""
        match = FootballDataFactory.match()
        now = datetime.utcnow()

        # 比赛日期应该在前后30天内
        assert (
            (now - timedelta(days=31))
            < match["match_date"]
            < (now + timedelta(days=31))
        )

    def test_unique_ids(self):
        """测试生成的ID是唯一的"""
        ids = set()
        for _ in range(100):
            match = FootballDataFactory.match()
            assert match["match_id"] not in ids
            ids.add(match["match_id"])

        # Faker使用固定种子，所以ID是可重现的但也是唯一的
        assert len(ids) == 100
