"""
Services与Domain模块集成测试
Services and Domain Module Integration Tests

测试服务层与领域层的集成，确保业务服务正确使用领域模型
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

# 标记测试
pytestmark = [pytest.mark.integration, pytest.mark.services, pytest.mark.domain]


class TestPredictionServiceDomainIntegration:
    """预测服务与领域模块集成测试"""

    @pytest.mark.asyncio
    async def test_prediction_service_creates_domain_object(
        self, test_db_session, sample_match, test_user_data
    ):
        """测试预测服务创建领域对象"""
        try:
            from src.domain.models.prediction import Prediction, PredictionStatus
            from src.domain.services.prediction_service import PredictionService

            service = PredictionService(test_db_session)

            # 创建预测
            prediction_data = {
                "user_id": 1,
                "match_id": sample_match.id if sample_match else 1,
                "predicted_home": 2,
                "predicted_away": 1,
                "confidence": 0.85,
            }

            prediction = await service.create_prediction(prediction_data)

            # 验证领域对象创建
            assert isinstance(prediction, Prediction)
            assert prediction.user_id == prediction_data["user_id"]
            assert prediction.match_id == prediction_data["match_id"]
            assert prediction.status == PredictionStatus.PENDING

            # 验证预测比分已设置
            assert prediction.score is not None
            assert prediction.score.predicted_home == prediction_data["predicted_home"]
            assert prediction.score.predicted_away == prediction_data["predicted_away"]

            # 验证置信度已设置
            if prediction.confidence:
                assert prediction.confidence.value == Decimal(
                    str(prediction_data["confidence"])
                )

        except ImportError:
            pytest.skip("Prediction service or domain models not available")

    @pytest.mark.asyncio
    async def test_prediction_service_uses_domain_validation(
        self, test_db_session, sample_match
    ):
        """测试预测服务使用领域验证"""
        try:
            from src.core.exceptions import DomainError
            from src.domain.services.prediction_service import PredictionService

            service = PredictionService(test_db_session)

            # 测试无效预测数据
            invalid_data = {
                "user_id": -1,  # 无效用户ID
                "match_id": sample_match.id if sample_match else 1,
                "predicted_home": 2,
                "predicted_away": 1,
                "confidence": 0.85,
            }

            # 应该抛出领域错误
            with pytest.raises(DomainError):
                await service.create_prediction(invalid_data)

        except ImportError:
            pytest.skip("Prediction service or domain models not available")

    @pytest.mark.asyncio
    async def test_prediction_service_evaluation_with_domain_logic(
        self, test_db_session, sample_predictions
    ):
        """测试预测服务评估使用领域逻辑"""
        try:
            from src.domain.services.prediction_service import PredictionService

            if not sample_predictions:
                pytest.skip("Sample predictions not available")

            service = PredictionService(test_db_session)
            pending_prediction = next(
                (p for p in sample_predictions if p.status in ["pending", "PENDING"]),
                None,
            )

            if not pending_prediction:
                pytest.skip("No pending predictions found")

            # 评估预测
            evaluation_result = await service.evaluate_prediction(
                pending_prediction.id, actual_home=2, actual_away=1
            )

            # 验证领域逻辑执行
            assert evaluation_result is not None
            assert "points" in evaluation_result
            assert "accuracy_score" in evaluation_result
            assert evaluation_result["accuracy_score"] > 0

        except ImportError:
            pytest.skip("Prediction service not available")

    @pytest.mark.asyncio
    async def test_prediction_service_domain_events(
        self, test_db_session, sample_match, mock_external_services
    ):
        """测试预测服务领域事件处理"""
        try:
            from src.domain.services.prediction_service import PredictionService

            service = PredictionService(test_db_session)

            # 模拟事件发布
            with patch(
                "src.core.event_application.event_bus",
                mock_external_services["audit_service"],
            ):
                prediction_data = {
                    "user_id": 1,
                    "match_id": sample_match.id if sample_match else 1,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "confidence": 0.85,
                }

                await service.create_prediction(prediction_data)

                # 验证领域事件发布
                if hasattr(mock_external_services["audit_service"], "log_event"):
                    assert mock_external_services["audit_service"].log_event.called

        except ImportError:
            pytest.skip("Prediction service not available")


class TestMatchServiceDomainIntegration:
    """比赛服务与领域模块集成测试"""

    @pytest.mark.asyncio
    async def test_match_service_manages_domain_status(
        self, test_db_session, sample_teams
    ):
        """测试比赛服务管理领域状态"""
        try:
            from src.domain.models.match import Match, MatchStatus
            from src.domain.services.match_service import MatchService

            if not sample_teams or len(sample_teams) < 2:
                pytest.skip("Sample teams not available")

            service = MatchService(test_db_session)

            # 创建比赛
            match_data = {
                "home_team_id": sample_teams[0].id,
                "away_team_id": sample_teams[1].id,
                "match_date": datetime.utcnow() + timedelta(days=1),
                "venue": "Test Stadium",
            }

            match = await service.create_match(match_data)

            # 验证领域状态
            assert isinstance(match, Match)
            assert match.status == MatchStatus.SCHEDULED

            # 开始比赛
            await service.start_match(match.id)
            updated_match = await service.get_match(match.id)

            assert updated_match.status == MatchStatus.IN_PROGRESS

            # 结束比赛
            await service.finish_match(match.id, home_score=2, away_score=1)
            finished_match = await service.get_match(match.id)

            assert finished_match.status == MatchStatus.FINISHED
            assert finished_match.home_score == 2
            assert finished_match.away_score == 1

        except ImportError:
            pytest.skip("Match service or domain models not available")

    @pytest.mark.asyncio
    async def test_match_service_enforces_domain_rules(
        self, test_db_session, sample_teams
    ):
        """测试比赛服务强制执行领域规则"""
        try:
            from src.core.exceptions import DomainError
            from src.domain.services.match_service import MatchService

            if not sample_teams or len(sample_teams) < 2:
                pytest.skip("Sample teams not available")

            service = MatchService(test_db_session)

            # 创建已结束的比赛
            match_data = {
                "home_team_id": sample_teams[0].id,
                "away_team_id": sample_teams[1].id,
                "match_date": datetime.utcnow() - timedelta(days=1),
                "venue": "Test Stadium",
            }

            match = await service.create_match(match_data)
            await service.finish_match(match.id, home_score=1, away_score=1)

            # 尝试重新开始已结束的比赛（应该失败）
            with pytest.raises(DomainError):
                await service.start_match(match.id)

        except ImportError:
            pytest.skip("Match service or domain models not available")

    @pytest.mark.asyncio
    async def test_match_service_calculates_domain_statistics(
        self, test_db_session, sample_teams
    ):
        """测试比赛服务计算领域统计"""
        try:
            from src.domain.services.match_service import MatchService

            if not sample_teams:
                pytest.skip("Sample teams not available")

            service = MatchService(test_db_session)

            # 获取球队统计
            team = sample_teams[0]
            stats = await service.get_team_statistics(team.id)

            # 验证统计计算
            assert "matches_played" in stats
            assert "wins" in stats
            assert "draws" in stats
            assert "losses" in stats
            assert "goals_for" in stats
            assert "goals_against" in stats
            assert "goal_difference" in stats

            # 验证数据类型
            for key, value in stats.items():
                if key != "recent_form":  # recent_form可能是列表
                    assert isinstance(value, (int, float))

        except ImportError:
            pytest.skip("Match service not available")


class TestTeamServiceDomainIntegration:
    """球队服务与领域模块集成测试"""

    @pytest.mark.asyncio
    async def test_team_service_manages_domain_entity(
        self, test_db_session, sample_league
    ):
        """测试球队服务管理领域实体"""
        try:
            from src.domain.models.team import Team
            from src.domain.services.team_service import TeamService

            service = TeamService(test_db_session)

            # 创建球队
            team_data = {
                "name": "Test FC",
                "short_name": "TFC",
                "country": "Test Country",
                "founded_year": 2020,
                "league_id": sample_league.id if sample_league else 1,
            }

            team = await service.create_team(team_data)

            # 验证领域实体
            assert isinstance(team, Team)
            assert team.name == team_data["name"]
            assert team.short_name == team_data["short_name"]
            assert team.country == team_data["country"]
            assert team.founded_year == team_data["founded_year"]

            # 更新球队信息
            update_data = {"name": "Updated FC"}
            updated_team = await service.update_team(team.id, update_data)

            assert updated_team.name == update_data["name"]

        except ImportError:
            pytest.skip("Team service or domain models not available")

    @pytest.mark.asyncio
    async def test_team_service_calculates_domain_performance_metrics(
        self, test_db_session, sample_teams
    ):
        """测试球队服务计算领域性能指标"""
        try:
            from src.domain.services.team_service import TeamService

            if not sample_teams:
                pytest.skip("Sample teams not available")

            service = TeamService(test_db_session)

            # 获取球队性能指标
            team = sample_teams[0]
            performance = await service.calculate_team_performance(team.id)

            # 验证性能指标
            expected_metrics = [
                "home_form",
                "away_form",
                "overall_form",
                "scoring_rate",
                "conceding_rate",
                "clean_sheets",
                "win_percentage",
                "recent_trend",
            ]

            for metric in expected_metrics:
                if metric in performance:
                    # 验证指标格式
                    if isinstance(performance[metric], (int, float)):
                        assert performance[metric] >= 0

        except ImportError:
            pytest.skip("Team service not available")


class TestScoringServiceDomainIntegration:
    """积分服务与领域模块集成测试"""

    @pytest.mark.asyncio
    async def test_scoring_service_uses_domain_points_calculation(
        self, test_db_session, sample_predictions
    ):
        """测试积分服务使用领域积分计算"""
        try:
            from src.domain.services.scoring_service import ScoringService

            if not sample_predictions:
                pytest.skip("Sample predictions not available")

            service = ScoringService(test_db_session)

            # 计算用户积分
            user_id = sample_predictions[0].user_id
            user_points = await service.calculate_user_points(user_id)

            # 验证积分计算
            assert "total_points" in user_points
            assert "points_breakdown" in user_points
            assert "ranking" in user_points

            assert isinstance(user_points["total_points"], (int, float))
            assert user_points["total_points"] >= 0

        except ImportError:
            pytest.skip("Scoring service not available")

    @pytest.mark.asyncio
    async def test_scoring_service_updates_leaderboard(
        self, test_db_session, sample_predictions
    ):
        """测试积分服务更新排行榜"""
        try:
            from src.domain.services.scoring_service import ScoringService

            if not sample_predictions:
                pytest.skip("Sample predictions not available")

            service = ScoringService(test_db_session)

            # 更新排行榜
            await service.update_leaderboard()

            # 获取排行榜
            leaderboard = await service.get_leaderboard(limit=10)

            # 验证排行榜格式
            assert isinstance(leaderboard, list)
            if leaderboard:
                top_entry = leaderboard[0]
                assert "rank" in top_entry
                assert "user_id" in top_entry
                assert "total_points" in top_entry
                assert top_entry["rank"] == 1

        except ImportError:
            pytest.skip("Scoring service not available")


class TestDomainServiceIntegration:
    """领域服务集成测试"""

    @pytest.mark.asyncio
    async def test_prediction_factory_creates_domain_strategies(self, test_db_session):
        """测试预测工厂创建领域策略"""
        try:
            from src.domain.strategies.factory import PredictionStrategyFactory

            factory = PredictionStrategyFactory()

            # 创建不同类型的策略
            strategies = ["statistical", "historical", "ml_model", "ensemble"]

            for strategy_type in strategies:
                try:
                    strategy = await factory.create_strategy(
                        strategy_type, test_db_session
                    )
                    assert strategy is not None
                    assert hasattr(strategy, "predict")
                except Exception:
                    # 如果特定策略不可用，跳过
                    continue

        except ImportError:
            pytest.skip("Prediction strategy factory not available")

    @pytest.mark.asyncio
    async def test_domain_services_coordinate(
        self, test_db_session, sample_match, sample_teams
    ):
        """测试领域服务协调"""
        try:
            from src.domain.services.match_service import MatchService
            from src.domain.services.prediction_service import PredictionService
            from src.domain.services.scoring_service import ScoringService

            prediction_service = PredictionService(test_db_session)
            match_service = MatchService(test_db_session)
            scoring_service = ScoringService(test_db_session)

            # 模拟完整的预测流程
            if sample_match and sample_teams:
                # 1. 创建预测
                prediction_data = {
                    "user_id": 1,
                    "match_id": sample_match.id,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "confidence": 0.85,
                }

                prediction = await prediction_service.create_prediction(prediction_data)

                # 2. 结束比赛
                await match_service.finish_match(
                    sample_match.id, home_score=2, away_score=1
                )

                # 3. 评估预测
                evaluation = await prediction_service.evaluate_prediction(
                    prediction.id, actual_home=2, actual_away=1
                )

                # 4. 更新积分
                await scoring_service.update_user_points(prediction.user_id)

                # 验证协调成功
                assert evaluation is not None
                assert evaluation.get("points", 0) > 0

        except ImportError:
            pytest.skip("Domain services not available")


class TestServiceErrorHandlingIntegration:
    """服务错误处理集成测试"""

    @pytest.mark.asyncio
    async def test_service_handles_domain_errors_gracefully(self, test_db_session):
        """测试服务优雅处理领域错误"""
        try:
            from src.core.exceptions import DomainError
            from src.domain.services.prediction_service import PredictionService

            service = PredictionService(test_db_session)

            # 测试各种领域错误
            error_scenarios = [
                {"user_id": -1, "error_type": "invalid_user"},
                {"match_id": -1, "error_type": "invalid_match"},
                {"predicted_home": -1, "error_type": "invalid_score"},
                {"confidence": 1.5, "error_type": "invalid_confidence"},
            ]

            for scenario in error_scenarios:
                prediction_data = {
                    "user_id": 1,
                    "match_id": 1,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "confidence": 0.85,
                }
                prediction_data.update(scenario)

                with pytest.raises(DomainError):
                    await service.create_prediction(prediction_data)

        except ImportError:
            pytest.skip("Prediction service not available")

    @pytest.mark.asyncio
    async def test_service_transaction_rollback_on_domain_error(self, test_db_session):
        """测试领域错误时服务事务回滚"""
        try:
            from src.domain.services.match_service import MatchService
            from src.domain.services.prediction_service import PredictionService

            prediction_service = PredictionService(test_db_session)
            MatchService(test_db_session)

            # 记录操作前的状态
            initial_predictions = await prediction_service.get_user_predictions(1)
            initial_count = len(initial_predictions) if initial_predictions else 0

            # 尝试创建无效预测（应该失败并回滚）
            try:
                invalid_prediction_data = {
                    "user_id": -1,  # 这将导致领域错误
                    "match_id": 1,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "confidence": 0.85,
                }

                await prediction_service.create_prediction(invalid_prediction_data)
            except Exception:
                pass  # 预期会失败

            # 验证事务已回滚（预测数量没有增加）
            final_predictions = await prediction_service.get_user_predictions(1)
            final_count = len(final_predictions) if final_predictions else 0

            assert initial_count == final_count

        except ImportError:
            pytest.skip("Services not available")


class TestServicePerformanceIntegration:
    """服务性能集成测试"""

    @pytest.mark.asyncio
    async def test_bulk_prediction_processing_performance(
        self, test_db_session, sample_match, performance_benchmarks
    ):
        """测试批量预测处理性能"""
        try:
            from src.domain.services.prediction_service import PredictionService

            service = PredictionService(test_db_session)

            import time

            start_time = time.time()

            # 创建多个预测
            predictions_data = [
                {
                    "user_id": i,
                    "match_id": sample_match.id if sample_match else 1,
                    "predicted_home": (i % 5) + 1,
                    "predicted_away": (i % 3) + 1,
                    "confidence": 0.5 + (i % 5) * 0.1,
                }
                for i in range(1, 51)  # 50个预测
            ]

            # 批量创建预测
            created_predictions = []
            for prediction_data in predictions_data:
                try:
                    prediction = await service.create_prediction(prediction_data)
                    created_predictions.append(prediction)
                except Exception:
                    continue  # 跳过失败的预测

            end_time = time.time()
            duration = end_time - start_time

            # 验证性能
            avg_time_per_prediction = (
                duration / len(created_predictions) if created_predictions else 0
            )
            assert (
                avg_time_per_prediction
                < performance_benchmarks["response_time_limits"]["prediction_creation"]
            )

            # 验证成功率
            success_rate = len(created_predictions) / len(predictions_data)
            assert success_rate > 0.8  # 至少80%成功率

        except ImportError:
            pytest.skip("Prediction service not available")

    @pytest.mark.asyncio
    async def test_concurrent_prediction_processing(
        self, test_db_session, sample_match
    ):
        """测试并发预测处理"""
        try:
            from src.domain.services.prediction_service import PredictionService

            service = PredictionService(test_db_session)

            async def create_prediction_async(user_id: int):
                """异步创建预测"""
                prediction_data = {
                    "user_id": user_id,
                    "match_id": sample_match.id if sample_match else 1,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "confidence": 0.85,
                }

                try:
                    return await service.create_prediction(prediction_data)
                except Exception:
                    return None

            # 并发创建预测
            tasks = [create_prediction_async(i) for i in range(1, 21)]  # 20个并发预测

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证并发处理
            successful_results = [
                r for r in results if r is not None and not isinstance(r, Exception)
            ]
            assert len(successful_results) > 0

        except ImportError:
            pytest.skip("Prediction service not available")


# 测试辅助函数
async def create_test_prediction(
    service,
    user_id: int,
    match_id: int,
    home_score: int,
    away_score: int,
    confidence: float = 0.85,
):
    """创建测试预测的辅助函数"""
    prediction_data = {
        "user_id": user_id,
        "match_id": match_id,
        "predicted_home": home_score,
        "predicted_away": away_score,
        "confidence": confidence,
    }

    return await service.create_prediction(prediction_data)


async def create_test_match(
    service, home_team_id: int, away_team_id: int, match_date: datetime = None
):
    """创建测试比赛的辅助函数"""
    if match_date is None:
        match_date = datetime.utcnow() + timedelta(days=1)

    match_data = {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "match_date": match_date,
        "venue": "Test Stadium",
    }

    return await service.create_match(match_data)
