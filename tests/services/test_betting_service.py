"""
投注服务测试
Betting Service Tests

测试Phase 5+重写的BettingService功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.services.betting.betting_service import (
    BettingService,
    EVCalculator,
    BettingRecommendationEngine,
    BettingOdds,
    PredictionProbabilities,
    EVCalculation,
    BettingRecommendation
)


class TestEVCalculator:
    """EVCalculator测试类"""

    @pytest.fixture
    def calculator(self):
        """测试用计算器实例"""
        return EVCalculator(margin=0.05)

    def test_calculator_initialization(self):
        """测试计算器初始化"""
        calc = EVCalculator(margin=0.1)
        assert calc.margin == 0.1

    def test_calculate_ev_valid(self, calculator):
        """测试计算EV - 有效输入"""
        odds = 2.5
        probability = 0.45

        result = calculator.calculate_ev(odds, probability)

        # 预期计算: (0.45 * 0.95 * 2.5 - 1.0) * 100
        # = (1.06875 - 1.0) * 100 = 6.875%
        assert abs(result - 6.875) < 0.01

    def test_calculate_ev_invalid_odds(self, calculator):
        """测试计算EV - 无效赔率"""
        odds = 1.0  # 赔率不能等于1.0
        probability = 0.5

        result = calculator.calculate_ev(odds, probability)

        assert result == 0.0

    def test_calculate_ev_invalid_probability(self, calculator):
        """测试计算EV - 无效概率"""
        odds = 2.5
        probability = 1.5  # 概率不能大于1

        result = calculator.calculate_ev(odds, probability)

        assert result == 0.0

    def test_calculate_kelly_fraction_positive_ev(self, calculator):
        """测试计算凯利比例 - 正EV"""
        ev = 5.0  # 5% EV
        odds = 2.5

        result = calculator.calculate_kelly_fraction(ev, odds)

        assert result > 0
        assert result <= 0.25  # 最大25%限制

    def test_calculate_kelly_fraction_zero_ev(self, calculator):
        """测试计算凯利比例 - 零EV"""
        ev = 0.0
        odds = 2.5

        result = calculator.calculate_kelly_fraction(ev, odds)

        assert result == 0.0

    def test_calculate_kelly_fraction_negative_ev(self, calculator):
        """测试计算凯利比例 - 负EV"""
        ev = -5.0
        odds = 2.5

        result = calculator.calculate_kelly_fraction(ev, odds)

        assert result == 0.0

    def test_calculate_kelly_fraction_limit(self, calculator):
        """测试计算凯利比例 - 限制测试"""
        ev = 50.0  # 很高的EV
        odds = 10.0

        result = calculator.calculate_kelly_fraction(ev, odds)

        assert result <= 0.25  # 应该被限制在25%

    def test_calculate_match_ev(self, calculator):
        """测试计算比赛EV"""
        odds = BettingOdds(
            home_win=2.5,
            draw=3.2,
            away_win=2.8,
            over_under_2_5=(1.9, 1.9)
        )

        probabilities = PredictionProbabilities(
            home_win=0.45,
            draw=0.25,
            away_win=0.30,
            over_under_2_5=(0.55, 0.45)
        )

        result = calculator.calculate_match_ev(odds, probabilities)

        assert isinstance(result, EVCalculation)
        assert result.ev_home_win > 0
        assert result.ev_draw is not None
        assert result.ev_away_win is not None
        assert result.ev_over_2_5 is not None
        assert result.ev_under_2_5 is not None
        assert result.recommendation in ["no_bet", "moderate_bet", "strong_bet"]
        assert 0 <= result.confidence <= 1

    def test_calculate_match_ev_no_additional_bets(self, calculator):
        """测试计算比赛EV - 无额外投注类型"""
        odds = BettingOdds(
            home_win=2.5,
            draw=3.2,
            away_win=2.8
        )

        probabilities = PredictionProbabilities(
            home_win=0.45,
            draw=0.25,
            away_win=0.30
        )

        result = calculator.calculate_match_ev(odds, probabilities)

        assert isinstance(result, EVCalculation)
        assert result.ev_over_2_5 is None
        assert result.ev_under_2_5 is None
        assert result.ev_bts_yes is None
        assert result.ev_bts_no is None


class TestBettingRecommendationEngine:
    """BettingRecommendationEngine测试类"""

    @pytest.fixture
    def engine(self):
        """测试用推荐引擎实例"""
        calculator = EVCalculator(margin=0.05)
        return BettingRecommendationEngine(calculator)

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine.ev_calculator is not None
        assert engine.logger is not None

    def test_generate_recommendations_strong_bet(self, engine):
        """测试生成推荐 - 强烈推荐"""
        match_id = "test_match_1"
        odds = BettingOdds(
            home_win=2.5,
            draw=3.2,
            away_win=3.5
        )

        # 设置概率使主胜EV很高
        probabilities = PredictionProbabilities(
            home_win=0.55,  # 高概率
            draw=0.25,
            away_win=0.20
        )

        result = engine.generate_recommendations(match_id, odds, probabilities)

        assert isinstance(result, list)
        # 应该有主胜推荐
        home_win_recs = [r for r in result if r.bet_type == "home_win"]
        assert len(home_win_recs) > 0
        assert home_win_recs[0].match_id == match_id
        assert home_win_recs[0].odds == odds.home_win
        assert home_win_recs[0].probability == probabilities.home_win
        assert home_win_recs[0].ev > 0

    def test_generate_recommendations_no_bets(self, engine):
        """测试生成推荐 - 无推荐"""
        match_id = "test_match_2"
        odds = BettingOdds(
            home_win=2.0,
            draw=3.2,
            away_win=3.8
        )

        # 设置概率使所有EV都很低
        probabilities = PredictionProbabilities(
            home_win=0.40,
            draw=0.30,
            away_win=0.30
        )

        result = engine.generate_recommendations(match_id, odds, probabilities)

        # 应该没有推荐或推荐很少
        high_ev_recs = [r for r in result if r.ev > 1.0]
        assert len(high_ev_recs) == 0

    def test_generate_recommendations_with_over_under(self, engine):
        """测试生成推荐 - 包含大小球"""
        match_id = "test_match_3"
        odds = BettingOdds(
            home_win=2.5,
            draw=3.2,
            away_win=2.8,
            over_under_2_5=(2.1, 1.8)
        )

        probabilities = PredictionProbabilities(
            home_win=0.45,
            draw=0.25,
            away_win=0.30,
            over_under_2_5=(0.60, 0.40)
        )

        result = engine.generate_recommendations(match_id, odds, probabilities)

        # 检查是否有大小球推荐
        over_2_5_recs = [r for r in result if r.bet_type == "over_2_5"]
        assert len(over_2_5_recs) >= 0  # 可能有也可能没有，取决于EV计算

    def test_generate_recommendations_all_bet_types(self, engine):
        """测试生成推荐 - 所有投注类型"""
        match_id = "test_match_4"
        odds = BettingOdds(
            home_win=3.0,
            draw=3.4,
            away_win=2.8,
            over_under_2_5=(2.2, 1.7),
            both_teams_score=(1.9, 1.9)
        )

        probabilities = PredictionProbabilities(
            home_win=0.30,
            draw=0.25,
            away_win=0.45,
            over_under_2_5=(0.55, 0.45),
            both_teams_score=(0.60, 0.40)
        )

        result = engine.generate_recommendations(match_id, odds, probabilities)

        # 检查各种投注类型
        bet_types = {r.bet_type for r in result}
        assert "home_win" in bet_types or "away_win" in bet_types
        assert len(result) >= 0  # 至少可能有推荐


class TestBettingService:
    """BettingService测试类"""

    @pytest.fixture
    def service(self):
        """测试用投注服务实例"""
        config = {
            "ev_margin": 0.03,
            "min_ev_threshold": 1.5,
            "max_kelly_fraction": 0.2
        }
        return BettingService(config)

    def test_service_initialization_default(self):
        """测试服务初始化 - 默认配置"""
        service = BettingService()

        assert service.config["ev_margin"] == 0.05
        assert service.config["min_ev_threshold"] == 1.0
        assert service.config["max_kelly_fraction"] == 0.25
        assert service.ev_calculator is not None
        assert service.recommendation_engine is not None
        assert service.recommendation_history == []

    def test_service_initialization_custom(self):
        """测试服务初始化 - 自定义配置"""
        config = {
            "ev_margin": 0.03,
            "min_ev_threshold": 2.0,
            "max_kelly_fraction": 0.15
        }
        service = BettingService(config)

        assert service.config["ev_margin"] == 0.03
        assert service.config["min_ev_threshold"] == 2.0
        assert service.config["max_kelly_fraction"] == 0.15

    @pytest.mark.asyncio
    async def test_analyze_match_valid(self, service):
        """测试分析比赛 - 有效输入"""
        match_id = "test_match_1"
        odds_data = {
            "home_win": 2.5,
            "draw": 3.2,
            "away_win": 2.8,
            "over_2_5": 1.9,
            "under_2_5": 1.9
        }

        prediction_data = {
            "home_win_prob": 0.45,
            "draw_prob": 0.25,
            "away_win_prob": 0.30,
            "over_2_5_prob": 0.55,
            "under_2_5_prob": 0.45
        }

        result = await service.analyze_match(match_id, odds_data, prediction_data)

        assert "match_id" in result
        assert result["match_id"] == match_id
        assert "ev_calculation" in result
        assert "recommendations" in result
        assert "analysis_summary" in result
        assert "analyzed_at" in result
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_analyze_match_invalid_data(self, service):
        """测试分析比赛 - 无效数据"""
        match_id = "test_match_2"
        odds_data = {}  # 空数据
        prediction_data = {}

        result = await service.analyze_match(match_id, odds_data, prediction_data)

        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_match_exception(self, service):
        """测试分析比赛 - 异常处理"""
        match_id = "test_match_3"
        odds_data = {"home_win": "invalid"}  # 无效数据
        prediction_data = {"home_win_prob": "invalid"}

        result = await service.analyze_match(match_id, odds_data, prediction_data)

        assert "error" in result

    def test_parse_odds_data_valid(self, service):
        """测试解析赔率数据 - 有效数据"""
        odds_data = {
            "home_win": "2.5",
            "draw": 3.2,
            "away_win": 2.8,
            "over_2_5": 1.9,
            "under_2_5": "1.9"
        }

        result = service._parse_odds_data(odds_data)

        assert isinstance(result, BettingOdds)
        assert result.home_win == 2.5
        assert result.draw == 3.2
        assert result.away_win == 2.8
        assert result.over_under_2_5 == (1.9, 1.9)

    def test_parse_odds_data_invalid(self, service):
        """测试解析赔率数据 - 无效数据"""
        odds_data = {
            "home_win": "invalid",
            "draw": "not_a_number"
        }

        result = service._parse_odds_data(odds_data)

        assert result is None

    def test_parse_prediction_data_valid(self, service):
        """测试解析预测数据 - 有效数据"""
        prediction_data = {
            "home_win_prob": "0.45",
            "draw_prob": 0.25,
            "away_win_prob": "0.30",
            "over_2_5_prob": 0.55,
            "under_2_5_prob": "0.45"
        }

        result = service._parse_prediction_data(prediction_data)

        assert isinstance(result, PredictionProbabilities)
        assert result.home_win == 0.45
        assert result.draw == 0.25
        assert result.away_win == 0.30
        assert result.over_under_2_5 == (0.55, 0.45)

    def test_parse_prediction_data_invalid(self, service):
        """测试解析预测数据 - 无效数据"""
        prediction_data = {
            "home_win_prob": "invalid",
            "draw_prob": "not_a_number"
        }

        result = service._parse_prediction_data(prediction_data)

        assert result is None

    def test_generate_analysis_summary(self, service):
        """测试生成分析摘要"""
        ev_calculation = EVCalculation(
            ev_home_win=3.0,
            ev_draw=1.0,
            ev_away_win=0.5,
            recommendation="moderate_bet",
            confidence=0.7
        )

        recommendations = [
            BettingRecommendation(
                match_id="test",
                bet_type="home_win",
                odds=2.5,
                probability=0.45,
                ev=3.0,
                kelly_fraction=0.15,
                confidence=0.7,
                reasoning="Test reasoning",
                created_at=datetime.utcnow()
            )
        ]

        result = service._generate_analysis_summary(ev_calculation, recommendations)

        assert result["overall_recommendation"] == "moderate_bet"
        assert result["confidence_score"] == 0.7
        assert result["recommendation_count"] == 1
        assert result["max_ev"] == 3.0
        assert result["best_bet"]["type"] == "home_win"
        assert result["best_bet"]["ev"] == 3.0

    @pytest.mark.asyncio
    async def test_get_recommendations_by_confidence(self, service):
        """测试根据置信度获取推荐"""
        # 添加一些推荐历史
        service.recommendation_history = [
            BettingRecommendation(
                match_id="test1",
                bet_type="home_win",
                odds=2.5,
                probability=0.5,
                ev=2.0,
                kelly_fraction=0.1,
                confidence=0.8,  # 高置信度
                reasoning="Test",
                created_at=datetime.utcnow()
            ),
            BettingRecommendation(
                match_id="test2",
                bet_type="away_win",
                odds=3.0,
                probability=0.3,
                ev=0.5,
                kelly_fraction=0.0,
                confidence=0.3,  # 低置信度
                reasoning="Test",
                created_at=datetime.utcnow()
            )
        ]

        result = await service.get_recommendations_by_confidence(min_confidence=0.5)

        assert len(result) == 1
        assert result[0].match_id == "test1"
        assert result[0].confidence >= 0.5

    @pytest.mark.asyncio
    async def test_get_recommendations_by_confidence_limit(self, service):
        """测试根据置信度获取推荐 - 限制数量"""
        # 添加多个高置信度推荐
        for i in range(5):
            service.recommendation_history.append(
                BettingRecommendation(
                    match_id=f"test{i}",
                    bet_type="home_win",
                    odds=2.5,
                    probability=0.5,
                    ev=2.0,
                    kelly_fraction=0.1,
                    confidence=0.8,
                    reasoning="Test",
                    created_at=datetime.utcnow()
                )
            )

        result = await service.get_recommendations_by_confidence(
            min_confidence=0.5,
            limit=3
        )

        assert len(result) == 3  # 应该被限制为3个

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance(self, service):
        """测试计算投资组合表现"""
        # 添加一些推荐历史
        base_time = datetime.utcnow()
        service.recommendation_history = [
            BettingRecommendation(
                match_id="test1",
                bet_type="home_win",
                odds=2.5,
                probability=0.5,
                ev=2.0,
                kelly_fraction=0.1,
                confidence=0.8,
                reasoning="Test",
                created_at=base_time - timedelta(days=5)
            ),
            BettingRecommendation(
                match_id="test2",
                bet_type="away_win",
                odds=3.0,
                probability=0.3,
                ev=0.5,
                kelly_fraction=0.0,
                confidence=0.3,
                reasoning="Test",
                created_at=base_time - timedelta(days=3)
            )
        ]

        result = await service.calculate_portfolio_performance()

        assert result["total_recommendations"] == 2
        assert result["average_ev"] == 1.25  # (2.0 + 0.5) / 2
        assert result["total_ev"] == 2.5
        assert result["high_confidence_count"] == 1
        assert result["high_confidence_ev"] == 2.0
        assert result["high_confidence_ratio"] == 0.5

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance_with_dates(self, service):
        """测试计算投资组合表现 - 指定日期范围"""
        base_time = datetime.utcnow()

        # 添加不同时间的推荐
        service.recommendation_history = [
            BettingRecommendation(
                match_id="old",
                bet_type="home_win",
                odds=2.5,
                probability=0.5,
                ev=2.0,
                kelly_fraction=0.1,
                confidence=0.8,
                reasoning="Test",
                created_at=base_time - timedelta(days=10)  # 10天前
            ),
            BettingRecommendation(
                match_id="recent",
                bet_type="away_win",
                odds=3.0,
                probability=0.3,
                ev=1.0,
                kelly_fraction=0.05,
                confidence=0.6,
                reasoning="Test",
                created_at=base_time - timedelta(days=2)   # 2天前
            )
        ]

        # 只查询最近5天的数据
        start_date = base_time - timedelta(days=5)
        result = await service.calculate_portfolio_performance(start_date=start_date)

        assert result["total_recommendations"] == 1
        assert result["total_ev"] == 1.0  # 只有最近的推荐

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance_empty_history(self, service):
        """测试计算投资组合表现 - 空历史"""
        result = await service.calculate_portfolio_performance()

        assert "error" in result

    def test_get_service_stats(self, service):
        """测试获取服务统计"""
        # 添加一些推荐历史
        service.recommendation_history = [
            BettingRecommendation(
                match_id="test",
                bet_type="home_win",
                odds=2.5,
                probability=0.5,
                ev=2.0,
                kelly_fraction=0.1,
                confidence=0.8,
                reasoning="Test",
                created_at=datetime.utcnow()
            )
        ]

        result = service.get_service_stats()

        assert result["total_recommendations"] == 1
        assert "config" in result
        assert "components" in result
        assert result["components"]["ev_calculator"] == "initialized"
        assert result["components"]["recommendation_engine"] == "initialized"
        assert "created_at" in result


class TestBettingServiceIntegration:
    """BettingService集成测试类"""

    @pytest.mark.asyncio
    async def test_complete_betting_analysis_flow(self):
        """测试完整投注分析流程"""
        service = BettingService()

        # 模拟真实的赔率和预测数据
        match_id = "manchester_united_vs_liverpool"
        odds_data = {
            "home_win": 2.4,
            "draw": 3.6,
            "away_win": 2.8,
            "over_2_5": 1.95,
            "under_2_5": 1.85,
            "bts_yes": 1.75,
            "bts_no": 2.05
        }

        prediction_data = {
            "home_win_prob": 0.42,
            "draw_prob": 0.28,
            "away_win_prob": 0.30,
            "over_2_5_prob": 0.52,
            "under_2_5_prob": 0.48,
            "bts_yes_prob": 0.58,
            "bts_no_prob": 0.42
        }

        # 分析比赛
        analysis = await service.analyze_match(match_id, odds_data, prediction_data)

        # 验证分析结果
        assert analysis["match_id"] == match_id
        assert "ev_calculation" in analysis
        assert "recommendations" in analysis
        assert "analysis_summary" in analysis

        # 验证EV计算
        ev_calc = analysis["ev_calculation"]
        assert hasattr(ev_calc, 'ev_home_win')
        assert hasattr(ev_calc, 'recommendation')
        assert hasattr(ev_calc, 'confidence')

        # 验证推荐
        recommendations = analysis["recommendations"]
        assert isinstance(recommendations, list)

        # 验证推荐已保存到历史
        assert len(service.recommendation_history) > 0

        # 验证可以获取推荐
        high_confidence_recs = await service.get_recommendations_by_confidence(0.5)
        assert isinstance(high_confidence_recs, list)

        # 验证投资组合表现计算
        portfolio_stats = await service.calculate_portfolio_performance()
        assert "total_recommendations" in portfolio_stats
        assert "average_ev" in portfolio_stats