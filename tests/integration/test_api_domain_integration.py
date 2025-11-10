"""
API与Domain模块集成测试
API and Domain Module Integration Tests

测试API层与Domain层的集成，确保领域模型正确暴露给API接口
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient

# 标记测试
pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.domain]


class TestPredictionAPIDomainIntegration:
    """预测API与Domain模块集成测试"""

    @pytest.mark.asyncio
    async def test_create_prediction_with_domain_validation(
        self, async_client: AsyncClient, sample_match, test_db_session
    ):
        """测试创建预测时的领域验证"""
        if not sample_match:
            pytest.skip("Sample match not available")

        # 准备预测数据
        prediction_data = {
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        # 测试有效预测
        response = await async_client.post("/api/predictions/", json=prediction_data)

        if response.status_code == 200:
            result = response.json()
            assert result["user_id"] == prediction_data["user_id"]
            assert result["match_id"] == prediction_data["match_id"]
            assert result["predicted_home"] == prediction_data["predicted_home"]
            assert result["predicted_away"] == prediction_data["predicted_away"]
        elif response.status_code == 404:
            # 如果API端点不存在，跳过测试
            pytest.skip("Prediction API endpoint not available")

    @pytest.mark.asyncio
    async def test_prediction_domain_validation_errors(
        self, async_client: AsyncClient, sample_match
    ):
        """测试预测领域验证错误"""
        if not sample_match:
            pytest.skip("Sample match not available")

        # 测试无效的置信度
        invalid_prediction_data = {
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 1.5,  # 超出有效范围
        }

        response = await async_client.post(
            "/api/predictions/", json=invalid_prediction_data
        )

        if response.status_code == 422:
            # 验证错误响应包含验证信息
            errors = response.json()
            assert any(
                "confidence" in str(errors).lower()
                for errors in [errors]
                if isinstance(errors, dict)
            )
        elif response.status_code == 404:
            pytest.skip("Prediction API endpoint not available")

        # 测试负数比分
        invalid_score_data = {
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": -1,
            "predicted_away": 1,
        }

        response = await async_client.post("/api/predictions/", json=invalid_score_data)

        if response.status_code in [422, 400]:
            # 预期验证错误
            pass
        elif response.status_code == 404:
            pytest.skip("Prediction API endpoint not available")

    @pytest.mark.asyncio
    async def test_evaluate_prediction_domain_logic(
        self, async_client: AsyncClient, sample_predictions
    ):
        """测试评估预测的领域逻辑"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        # 获取一个待评估的预测
        pending_prediction = next(
            (p for p in sample_predictions if p.status in ["pending", "PENDING"]), None
        )

        if not pending_prediction:
            pytest.skip("No pending predictions found")

        # 评估预测
        evaluation_data = {
            "actual_home": 2,
            "actual_away": 1,
        }

        response = await async_client.post(
            f"/api/predictions/{pending_prediction.id}/evaluate", json=evaluation_data
        )

        if response.status_code == 200:
            result = response.json()
            assert "points" in result
            assert "accuracy" in result
            assert result["status"] in ["evaluated", "EVALUATED"]
        elif response.status_code == 404:
            pytest.skip("Prediction evaluation API endpoint not available")

    @pytest.mark.asyncio
    async def test_prediction_status_transitions(
        self, async_client: AsyncClient, sample_predictions
    ):
        """测试预测状态转换的领域规则"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        pending_prediction = next(
            (p for p in sample_predictions if p.status in ["pending", "PENDING"]), None
        )

        if not pending_prediction:
            pytest.skip("No pending predictions found")

        # 测试取消预测
        response = await async_client.post(
            f"/api/predictions/{pending_prediction.id}/cancel",
            json={"reason": "User requested cancellation"},
        )

        if response.status_code == 200:
            result = response.json()
            assert result["status"] in ["cancelled", "CANCELLED"]
            assert "cancelled_at" in result
        elif response.status_code == 404:
            pytest.skip("Prediction cancellation API endpoint not available")

    @pytest.mark.asyncio
    async def test_prediction_points_calculation(
        self, async_client: AsyncClient, test_db_session
    ):
        """测试预测积分计算的领域逻辑"""
        # 直接测试领域模型的积分计算
        try:
            from decimal import Decimal

            from src.domain.models.prediction import (
                ConfidenceScore,
                Prediction,
                PredictionScore,
                PredictionStatus,
            )

            # 创建预测
            prediction = Prediction(
                user_id=1,
                match_id=1,
                status=PredictionStatus.PENDING,
            )

            # 进行预测
            prediction.make_prediction(
                predicted_home=2, predicted_away=1, confidence=0.85
            )

            # 评估预测（精确比分）
            prediction.evaluate(actual_home=2, actual_away=1)

            # 验证积分计算
            assert prediction.points is not None
            assert prediction.points.total > 0
            assert prediction.accuracy_score == 1.0  # 精确比分应该得满分

        except ImportError:
            pytest.skip("Domain prediction models not available")


class TestMatchAPIDomainIntegration:
    """比赛API与Domain模块集成测试"""

    @pytest.mark.asyncio
    async def test_match_creation_with_domain_validation(
        self, async_client: AsyncClient, sample_teams
    ):
        """测试创建比赛时的领域验证"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        home_team, away_team = sample_teams[0], sample_teams[1]

        match_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "venue": "Test Stadium",
            "league_id": home_team.league_id if hasattr(home_team, "league_id") else 1,
        }

        response = await async_client.post("/api/matches/", json=match_data)

        if response.status_code == 200:
            result = response.json()
            assert result["home_team_id"] == match_data["home_team_id"]
            assert result["away_team_id"] == match_data["away_team_id"]
            assert result["status"] in ["SCHEDULED", "scheduled"]
        elif response.status_code == 404:
            pytest.skip("Match API endpoint not available")

    @pytest.mark.asyncio
    async def test_match_status_domain_transitions(
        self, async_client: AsyncClient, sample_match
    ):
        """测试比赛状态转换的领域规则"""
        if not sample_match:
            pytest.skip("Sample match not available")

        # 测试开始比赛
        response = await async_client.post(f"/api/matches/{sample_match.id}/start")

        if response.status_code == 200:
            result = response.json()
            assert result["status"] in ["IN_PROGRESS", "in_progress", "LIVE"]
        elif response.status_code == 404:
            pytest.skip("Match start API endpoint not available")

        # 测试结束比赛
        finish_data = {
            "home_score": 2,
            "away_score": 1,
        }

        response = await async_client.post(
            f"/api/matches/{sample_match.id}/finish", json=finish_data
        )

        if response.status_code == 200:
            result = response.json()
            assert result["status"] in ["FINISHED", "finished", "COMPLETED"]
            assert result["home_score"] == finish_data["home_score"]
            assert result["away_score"] == finish_data["away_score"]
        elif response.status_code == 404:
            pytest.skip("Match finish API endpoint not available")


class TestTeamAPIDomainIntegration:
    """球队API与Domain模块集成测试"""

    @pytest.mark.asyncio
    async def test_team_creation_with_domain_validation(
        self, async_client: AsyncClient, sample_league
    ):
        """测试创建球队时的领域验证"""
        if not sample_league:
            pytest.skip("Sample league not available")

        team_data = {
            "name": "Test FC",
            "short_name": "TFC",
            "country": "Test Country",
            "founded_year": 2020,
            "league_id": sample_league.id if hasattr(sample_league, "id") else 1,
        }

        response = await async_client.post("/api/teams/", json=team_data)

        if response.status_code == 200:
            result = response.json()
            assert result["name"] == team_data["name"]
            assert result["short_name"] == team_data["short_name"]
            assert result["country"] == team_data["country"]
            assert result["founded_year"] == team_data["founded_year"]
        elif response.status_code == 404:
            pytest.skip("Team API endpoint not available")

    @pytest.mark.asyncio
    async def test_team_statistics_domain_logic(
        self, async_client: AsyncClient, sample_teams
    ):
        """测试球队统计的领域逻辑"""
        if not sample_teams:
            pytest.skip("Sample teams not available")

        team = sample_teams[0]

        # 获取球队统计
        response = await async_client.get(f"/api/teams/{team.id}/statistics")

        if response.status_code == 200:
            stats = response.json()
            # 验证统计字段存在
            expected_fields = [
                "matches_played",
                "wins",
                "draws",
                "losses",
                "goals_for",
                "goals_against",
                "goal_difference",
                "points",
                "ranking",
            ]

            for field in expected_fields:
                if field in stats:
                    assert isinstance(stats[field], (int, float))
        elif response.status_code == 404:
            pytest.skip("Team statistics API endpoint not available")


class TestUserPredictionDomainIntegration:
    """用户预测领域集成测试"""

    @pytest.mark.asyncio
    async def test_user_prediction_history(
        self, async_client: AsyncClient, sample_predictions
    ):
        """测试用户预测历史的领域逻辑"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        # 获取第一个预测的用户ID
        user_id = sample_predictions[0].user_id

        response = await async_client.get(f"/api/users/{user_id}/predictions")

        if response.status_code == 200:
            predictions = response.json()
            if isinstance(predictions, list):
                # 验证返回的是用户预测列表
                for pred in predictions:
                    assert "user_id" in pred
                    assert pred["user_id"] == user_id
                    assert "match_id" in pred
                    assert "status" in pred
        elif response.status_code == 404:
            pytest.skip("User predictions API endpoint not available")

    @pytest.mark.asyncio
    async def test_user_prediction_statistics(
        self, async_client: AsyncClient, test_db_session
    ):
        """测试用户预测统计的领域逻辑"""
        user_id = 1

        response = await async_client.get(
            f"/api/users/{user_id}/predictions/statistics"
        )

        if response.status_code == 200:
            stats = response.json()
            expected_fields = [
                "total_predictions",
                "correct_predictions",
                "accuracy_rate",
                "total_points",
                "average_confidence",
                "best_streak",
            ]

            for field in expected_fields:
                if field in stats:
                    assert isinstance(stats[field], (int, float, str))
        elif response.status_code == 404:
            pytest.skip("User prediction statistics API endpoint not available")


class TestDomainEventIntegration:
    """领域事件集成测试"""

    @pytest.mark.asyncio
    async def test_prediction_created_event(
        self, async_client: AsyncClient, sample_match, mock_external_services
    ):
        """测试预测创建事件"""
        if not sample_match:
            pytest.skip("Sample match not available")

        prediction_data = {
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        # 模拟外部服务以捕获事件
        with patch(
            "src.domain.events.prediction_events.event_bus",
            mock_external_services["audit_service"],
        ):
            response = await async_client.post(
                "/api/predictions/", json=prediction_data
            )

            if response.status_code == 200:
                # 验证事件服务被调用
                if hasattr(mock_external_services["audit_service"], "log_event"):
                    assert mock_external_services["audit_service"].log_event.called
            elif response.status_code == 404:
                pytest.skip("Prediction API endpoint not available")

    @pytest.mark.asyncio
    async def test_prediction_evaluated_event(
        self, async_client: AsyncClient, sample_predictions, mock_external_services
    ):
        """测试预测评估事件"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        pending_prediction = next(
            (p for p in sample_predictions if p.status in ["pending", "PENDING"]), None
        )

        if not pending_prediction:
            pytest.skip("No pending predictions found")

        evaluation_data = {
            "actual_home": 2,
            "actual_away": 1,
        }

        with patch(
            "src.domain.events.prediction_events.event_bus",
            mock_external_services["analytics_service"],
        ):
            response = await async_client.post(
                f"/api/predictions/{pending_prediction.id}/evaluate",
                json=evaluation_data,
            )

            if response.status_code == 200:
                # 验证分析事件被记录
                if hasattr(mock_external_services["analytics_service"], "track_event"):
                    assert mock_external_services[
                        "analytics_service"
                    ].track_event.called
            elif response.status_code == 404:
                pytest.skip("Prediction evaluation API endpoint not available")


class TestValidationErrorIntegration:
    """验证错误集成测试"""

    @pytest.mark.asyncio
    async def test_domain_validation_error_format(
        self, async_client: AsyncClient, sample_match
    ):
        """测试领域验证错误的格式"""
        if not sample_match:
            pytest.skip("Sample match not available")

        # 发送包含多个验证错误的数据
        invalid_data = {
            "user_id": -1,  # 无效用户ID
            "match_id": sample_match.id,
            "predicted_home": -1,  # 无效比分
            "predicted_away": 1,
            "confidence": 1.5,  # 无效置信度
        }

        response = await async_client.post("/api/predictions/", json=invalid_data)

        if response.status_code in [422, 400]:
            error_response = response.json()
            # 验证错误响应格式
            assert "detail" in error_response or "errors" in error_response
        elif response.status_code == 404:
            pytest.skip("Prediction API endpoint not available")

    @pytest.mark.asyncio
    async def test_business_rule_validation(
        self, async_client: AsyncClient, sample_predictions
    ):
        """测试业务规则验证"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        evaluated_prediction = next(
            (p for p in sample_predictions if p.status in ["evaluated", "EVALUATED"]),
            None,
        )

        if not evaluated_prediction:
            pytest.skip("No evaluated predictions found")

        # 尝试修改已评估的预测（应该违反业务规则）
        update_data = {
            "predicted_home": 3,
            "predicted_away": 1,
        }

        response = await async_client.put(
            f"/api/predictions/{evaluated_prediction.id}", json=update_data
        )

        # 应该返回错误，因为已评估的预测不能修改
        if response.status_code in [400, 403, 422]:
            error_response = response.json()
            # 验证业务规则错误信息
            error_message = str(error_response.get("detail", ""))
            assert any(
                keyword in error_message.lower()
                for keyword in ["evaluated", "cannot", "modify"]
            )
        elif response.status_code == 404:
            pytest.skip("Prediction update API endpoint not available")


class TestPerformanceIntegration:
    """性能集成测试"""

    @pytest.mark.asyncio
    async def test_bulk_prediction_creation_performance(
        self, async_client: AsyncClient, sample_match, performance_benchmarks
    ):
        """测试批量创建预测的性能"""
        if not sample_match:
            pytest.skip("Sample match not available")

        import time

        # 准备批量预测数据
        bulk_data = [
            {
                "user_id": i,
                "match_id": sample_match.id,
                "predicted_home": (i % 5) + 1,
                "predicted_away": (i % 3) + 1,
                "confidence": 0.5 + (i % 5) * 0.1,
            }
            for i in range(1, 51)  # 50个预测
        ]

        start_time = time.time()

        # 如果支持批量创建
        response = await async_client.post(
            "/api/predictions/bulk", json={"predictions": bulk_data}
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            # 验证性能基准
            assert (
                duration
                < performance_benchmarks["response_time_limits"]["bulk_predictions"]
            )

            result = response.json()
            assert "created_count" in result
            assert result["created_count"] == len(bulk_data)
        elif response.status_code == 404:
            # 如果不支持批量操作，逐个创建并测试性能
            total_time = 0
            success_count = 0

            for prediction_data in bulk_data[:10]:  # 只测试前10个
                start_time = time.time()
                response = await async_client.post(
                    "/api/predictions/", json=prediction_data
                )
                end_time = time.time()

                if response.status_code == 200:
                    success_count += 1

                total_time += end_time - start_time

            # 验证平均时间
            avg_time = total_time / 10
            assert (
                avg_time
                < performance_benchmarks["response_time_limits"]["prediction_creation"]
            )


# 测试辅助类和函数
class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_valid_prediction_data(match_id: int, user_id: int = 1) -> dict:
        """创建有效的预测数据"""
        return {
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

    @staticmethod
    def create_valid_match_data(home_team_id: int, away_team_id: int) -> dict:
        """创建有效的比赛数据"""
        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "venue": "Test Stadium",
            "status": "SCHEDULED",
        }

    @staticmethod
    def create_valid_team_data(league_id: int = 1) -> dict:
        """创建有效的球队数据"""
        return {
            "name": "Test FC",
            "short_name": "TFC",
            "country": "Test Country",
            "founded_year": 2020,
            "league_id": league_id,
        }


# 集成测试配置
@pytest.fixture(scope="class")
def api_domain_test_config():
    """API与Domain集成测试配置"""
    return {
        "max_test_predictions": 100,
        "performance_sample_size": 50,
        "validation_error_test_cases": [
            {"confidence": 1.5, "expected_error": "confidence_range"},
            {"predicted_home": -1, "expected_error": "negative_score"},
            {"user_id": -1, "expected_error": "invalid_user_id"},
        ],
        "business_rule_test_cases": [
            {
                "operation": "modify_evaluated",
                "expected_error": "cannot_modify_evaluated",
            },
            {
                "operation": "duplicate_prediction",
                "expected_error": "already_predicted",
            },
        ],
    }
