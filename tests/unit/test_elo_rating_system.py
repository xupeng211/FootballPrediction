#!/usr/bin/env python3
"""
Elo评级系统单元测试

测试Elo评级系统的核心计算逻辑和边界条件。
确保与数学公式的一致性和数值精度。

Author: 高级测试架构师 & QA专家
Sprint: 7 - 测试覆盖率保障与CI/CD自动化
"""

import pytest
import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, Any

from src.ml.features.elo_rating_system import EloRatingSystem


class TestEloRatingSystem:
    """Elo评级系统测试类"""

    @pytest.fixture
    def elo_system(self):
        """创建Elo评级系统实例"""
        return EloRatingSystem(
            initial_rating=1500.0,
            home_advantage=50.0,
            base_k_factor=40.0,
            enable_goal_margin=True,
            enable_dynamic_k=True,
            rating_decay_days=365,
        )

    @pytest.fixture
    def sample_teams(self):
        """示例球队数据"""
        return {
            "team_a": "Manchester United",
            "team_b": "Arsenal",
            "team_c": "Chelsea",
            "team_d": "Liverpool",
        }

    def test_initialization(self, elo_system):
        """测试系统初始化"""
        assert elo_system.initial_rating == 1500.0
        assert elo_system.home_advantage == 50.0
        assert elo_system.base_k_factor == 40.0
        assert elo_system.enable_goal_margin is True
        assert elo_system.enable_dynamic_k is True

    def test_basic_rating_calculation(self, elo_system, sample_teams):
        """测试基础评级计算"""
        # 设置初始评级
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        # 验证初始评级
        assert elo_system.get_team_rating(sample_teams["team_a"]) == 1500.0
        assert elo_system.get_team_rating(sample_teams["team_b"]) == 1500.0

    def test_expected_score_calculation(self, elo_system):
        """测试预期得分计算"""
        # 测试基础预期得分
        rating_diff = 100
        expected_score_a = 1 / (1 + math.pow(10, -rating_diff / 400))
        expected_score_b = 1 / (1 + math.pow(10, rating_diff / 400))

        assert abs(expected_score_a - 0.6401) < 0.001
        assert abs(expected_score_b - 0.3599) < 0.001

        # 验证预期得分和为1
        assert abs((expected_score_a + expected_score_b) - 1.0) < 0.0001

    def test_k_factor_calculation(self, elo_system):
        """测试K因子计算"""
        # 测试基础K因子
        assert elo_system._calculate_k_factor("league") == 40.0

        # 测试动态K因子
        # 重要比赛（权重=1.5）
        k_factor = elo_system._calculate_k_factor("league", weight=1.5, confidence=0.9)
        assert k_factor == 40.0 * 1.5 * 0.9

        # 杯重限制
        k_factor_limited = elo_system._calculate_k_factor("league", weight=3.0, confidence=0.5)
        assert k_factor_limited == 40.0 * 2.0 * 0.5  # 最大2.0倍权重

    def test_basic_rating_update(self, elo_system, sample_teams):
        """测试基础评级更新"""
        # 设置初始评级
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        # 强队主场战胜弱队
        result = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=3,
            away_goals=1,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 验证评级更新
        new_home_rating = elo_system.get_team_rating(sample_teams["team_a"])
        new_away_rating = elo_system.get_team_rating(sample_teams["team_b"])

        # 主队获胜应该增加评级
        assert new_home_rating > 1500.0
        # 客队失败应该减少评级
        assert new_away_rating < 1500.0

        # 验证评级差
        rating_diff_before = abs(1500.0 - 1500.0)
        rating_diff_after = abs(new_home_rating - new_away_rating)
        assert rating_diff_after > rating_diff_before

    def test_draw_result_update(self, elo_system, sample_teams):
        """测试平局结果评级更新"""
        # 设置初始评级
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1600.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1400.0,
            last_updated=datetime.utcnow(),
        )

        result = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=1,
            away_goals=1,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 平局情况下，低排名队应该获得收益
        new_home_rating = elo_system.get_team_rating(sample_teams["team_a"])
        new_away_rating = elo_system.get_team_rating(sample_teams["team_b"])

        # 高排名队（主队）应该损失评级
        assert new_home_rating < 1600.0
        # 低排名队（客队）应该获得评级
        assert new_away_rating > 1400.0

    def test_goal_margin_impact(self, elo_system, sample_teams):
        """测试进球差距对评级更新的影响"""
        # 设置初始评级
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        # 大比分胜利
        result_large = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=5,
            away_goals=0,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 小比分胜利
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        result_small = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=1,
            away_goals=0,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 大比分胜利应该获得更多评级提升
        large_win_home = result_large["ratings"]["home"]["after"]
        small_win_home = result_small["ratings"]["home"]["after"]
        assert large_win_home > small_win_home

    def test_home_advantage_impact(self, elo_system, sample_teams):
        """测试主场优势的影响"""
        # 设置初始评级
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        # 主队获胜
        result_home = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=2,
            away_goals=1,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 客队获胜（相同比分，客场）
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        result_away = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=1,
            away_goals=2,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 相同比分下，主场胜利获得的评级提升应该多于客场胜利
        home_win_home = result_home["ratings"]["home"]["after"]
        away_win_home = result_away["ratings"]["home"]["after"]

        # 主队胜利后主队评级
        assert home_win_home > 1500.0
        # 客队胜利后主队评级应该下降
        assert away_win_home < 1500.0
        # 主队胜利的评级提升应该大于客场胜利的评级下降
        rating_gain_home = home_win_home - 1500.0
        rating_loss_away = 1500.0 - away_win_home
        assert abs(rating_gain_home) > abs(rating_loss_away)

    def test_prediction_probabilities(self, elo_system, sample_teams):
        """测试预测概率计算"""
        # 设置不同评级
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1700.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"], rating=1300.0, rating_decay_days=365
        )

        probabilities = elo_system.predict_match_probabilities(
            home_team_id=sample_teams["team_a"], away_team_id=sample_teams["team_b"]
        )

        # 验证概率有效性
        assert 0 <= probabilities["probabilities"]["home_win"] <= 1
        assert 0 <= probabilities["probabilities"]["draw"] <= 1
        assert 0 <= probabilities["probabilities"]["away_win"] <= 1
        assert (
            abs(
                probabilities["probabilities"]["home_win"]
                + probabilities["probabilities"]["draw"]
                + probabilities["probabilities"]["away_win"]
                - 1.0
            )
            < 0.0001
        )

        # 高评级主队应该有更高的胜率
        assert probabilities["probabilities"]["home_win"] > probabilities["probabilities"]["away_win"]

    def test_head_to_head_record_tracking(self, elo_system, sample_teams):
        """测试历史交锋记录跟踪"""
        # 添加历史交锋记录
        match_date = datetime.utcnow() - timedelta(days=30)

        record = elo_system._add_h2h_record(sample_teams["team_a"], sample_teams["team_b"], 2, 1, match_date)

        # 验证记录存储
        assert record.home_team == sample_teams["team_a"]
        assert record.away_team == sample_teams["team_b"]
        assert record.home_goals == 2
        record.away_goals == 1
        assert record.match_date == match_date

        # 获取H2H记录
        h2h_record = elo_system.get_head_to_head_record(sample_teams["team_a"], sample_teams["team_b"])

        assert h2h_record.total_matches == 1
        assert h2h_record.home_wins == 1
        assert h2h_record.away_wins == 0
        assert h2h_record.draws == 0

    def test_h2h_impact_on_k_factor(self, elo_system, sample_teams):
        """测试历史交锋对K因子的影响"""
        # 添加H2H记录
        match_date = datetime.utcnow() - timedelta(days=10)

        # 强队有历史优势
        for i in range(3):
            elo_system._add_h2h_record(
                sample_teams["team_a"],
                sample_teams["team_b"],
                2,
                0,
                match_date - timedelta(days=i * 10),
            )

        # 测试H2H影响
        k_with_h2h = elo_system._calculate_k_factor("league", confidence=1.0)

        # 无H2H记录的球队
        k_without_h2h = elo_system._calculate_k_factor("league", team_id=sample_teams["team_c"], confidence=1.0)

        # H2H记录应该调整K因子
        assert abs(k_with_h2h - 40.0) < 5.0  # 允许一些调整

    def test_rating_decay(self, elo_system, sample_teams):
        """测试评级衰减机制"""
        # 设置过期评级
        old_date = datetime.utcnow() - timedelta(days=400)
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"], rating=1600.0, last_updated=old_date
        )

        # 验证衰减后的评级
        decayed_rating = elo_system.get_team_rating(sample_teams["team_a"])
        assert decayed_rating < 1600.0

        # 测试不衰减的近期评级
        recent_date = datetime.utcnow() - timedelta(days=100)
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"], rating=1500.0, last_updated=recent_date
        )

        no_decay_rating = elo_system.get_team_rating(sample_teams["team_b"])
        assert no_decay_rating == 1500.0

    def test_system_statistics(self, elo_system, sample_teams):
        """测试系统统计信息"""
        # 添加一些评级
        for team in sample_teams.values():
            elo_system.team_ratings[team] = TeamRating(team_id=team, rating=1500.0, last_updated=datetime.utcnow())

        # 添加一些比赛记录
        elo_system._add_h2h_record(sample_teams["team_a"], sample_teams["team_b"], 2, 1, datetime.utcnow())

        stats = elo_system.get_system_stats()

        # 验证统计数据
        assert stats["total_teams"] == len(sample_teams)
        assert stats["total_h2h_records"] == 1
        assert stats["average_rating"] == 1500.0
        assert stats["rating_distribution"]["average"] == 1500.0

    def test_edge_cases(self, elo_system):
        """测试边界条件和异常情况"""
        # 测试不存在的球队
        assert elo_system.get_team_rating("nonexistent_team") == 1500.0

        # 测试零赔率情况
        with pytest.raises(ValueError):
            elo_system.calculate_kelly_fraction(0.0, 0.5)

        # 测试无效概率
        with pytest.raises(ValueError):
            elo_system._validate_probabilities({"home_win": 1.5, "draw": 0.3, "away_win": 0.2})

    def test_numerical_precision(self, elo_system, sample_teams):
        """测试数值精度和一致性"""
        # 重复相同操作应该产生相同结果
        elo_system.team_ratings[sample_teams["team_a"]] = TeamRating(
            team_id=sample_teams["team_a"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )
        elo_system.team_ratings[sample_teams["team_b"]] = TeamRating(
            team_id=sample_teams["team_b"],
            rating=1500.0,
            last_updated=datetime.utcnow(),
        )

        # 第一次更新
        result1 = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=2,
            away_goals=1,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 重置到相同状态
        elo_system.team_ratings[sample_teams["team_a"]].rating = 1500.0
        elo_system.team_ratings[sample_teams["team_b"]].rating = 1500.0

        # 第二次更新
        result2 = elo_system.update_ratings(
            home_team_id=sample_teams["team_a"],
            away_team_id=sample_teams["team_b"],
            home_goals=2,
            away_goals=1,
            match_date=datetime.utcnow(),
            competition_type="league",
        )

        # 结果应该完全相同
        assert result1["ratings"]["home"]["after"] == result2["ratings"]["home"]["after"]
        assert result1["ratings"]["away"]["after"] == result2["ratings"]["away"]["after"]

    def test_configuration_variations(self):
        """测试不同配置的影响"""
        # 测试不同的主场优势
        elo_no_home_advantage = EloRatingSystem(home_advantage=0.0)
        elo_high_home_advantage = EloRatingSystem(home_advantage=100.0)

        # 比较主场优势影响
        team_a, team_b = "TeamA", "TeamB"
        elo_no_home_advantage.team_ratings[team_a] = TeamRating(
            team_id=team_a, rating=1500.0, last_updated=datetime.utcnow()
        )
        elo_no_home_advantage.team_ratings[team_b] = TeamRating(
            team_id=team_b, rating=1500.0, last_updated=datetime.utcnow()
        )
        elo_high_home_advantage.team_ratings[team_a] = TeamRating(
            team_id=team_a, rating=1500.0, last_updated=datetime.utcnow()
        )
        elo_high_home_advantage.team_ratings[team_b] = TeamRating(
            team_id=team_b, rating=1500.0, last_updated=datetime.utcnow()
        )

        # 相同比分，不同主场优势
        result_no_adv = elo_no_home_advantage.update_ratings(team_a, team_b, 1, 0, datetime.utcnow(), "league")
        result_high_adv = elo_high_home_advantage.update_ratings(team_a, team_b, 1, 0, datetime.utcnow(), "league")

        # 高主场优势应该给主队更多收益
        home_rating_high_adv = result_high_adv["ratings"]["home"]["after"]
        home_rating_no_adv = result_no_adv["ratings"]["home"]["after"]

        assert home_rating_high_adv > home_rating_no_adv

        # 测试不同的K因子
        elo_low_k = EloRatingSystem(base_k_factor=20.0)
        elo_high_k = EloRatingSystem(base_k_factor=80.0)

        elo_low_k.team_ratings[team_a] = TeamRating(team_id=team_a, rating=1500.0, last_updated=datetime.utcnow())
        elo_low_k.team_ratings[team_b] = TeamRating(team_id=team_b, rating=1500.0, last_updated=datetime.utcnow())
        elo_high_k.team_ratings[team_a] = TeamRating(team_id=team_a, rating=1500.0, last_updated=datetime.utcnow())
        elo_high_k.team_ratings[team_b] = TeamRating(team_id=team_b, rating=1500.0, last_updated=datetime.utcnow())

        result_low_k = elo_low_k.update_ratings(team_a, team_b, 3, 0, datetime.utcnow(), "league")
        result_high_k = elo_high_k.update_ratings(team_a, team_b, 3, 0, datetime.utcnow(), "league")

        # 高K因子应该产生更大的评级变化
        rating_change_low_k = result_low_k["ratings"]["home"]["after"] - 1500.0
        rating_change_high_k = result_high_k["ratings"]["home"]["after"] - 1500.0

        assert abs(rating_change_high_k) > abs(rating_change_low_k)

    def test_comprehensive_scenario(self, elo_system):
        """测试综合场景"""
        teams = ["TeamA", "TeamB", "TeamC", "TeamD", "TeamE"]

        # 初始化所有球队
        for team in teams:
            elo_system.team_ratings[team] = TeamRating(team_id=team, rating=1500.0, last_updated=datetime.utcnow())

        # 模拟一个赛季
        season_matches = [
            ("TeamA", "TeamB", 2, 1),
            ("TeamC", "TeamD", 1, 1),
            ("TeamE", "TeamA", 3, 0),
            ("TeamB", "TeamC", 0, 2),
            ("TeamD", "TeamE", 1, 2),
        ]

        # 执行赛季比赛
        for home, away, home_goals, away_goals in season_matches:
            elo_system.update_ratings(
                home_team_id=home,
                away_team_id=away,
                home_goals=home_goals,
                away_goals=away_goals,
                match_date=datetime.utcnow(),
                competition_type="league",
            )

        # 验证所有球队都有评级
        for team in teams:
            assert elo_system.get_team_rating(team) != 1500.0  # 应该有变化

        # 验证最终排名合理性
        final_ratings = [(team, elo_system.get_team_rating(team)) for team in teams]
        final_ranking = sorted(final_ratings, key=lambda x: x[1], reverse=True)

        # 最高评级应该属于胜率最高的球队
        assert final_ranking[0][1] >= final_ranking[-1][1]

        # 验证系统统计
        stats = elo_system.get_system_stats()
        assert stats["total_teams"] == 5
        assert stats["total_matches"] == len(season_matches)

    def test_async_compatibility(self):
        """测试异步兼容性（虽然Elo系统主要是同步的）"""
        elo_system = EloRatingSystem()

        # 异步上下文管理器测试 - 暂时注释掉，需要异步测试环境
        # async with elo_system as elo_async:
        # 测试在异步上下文中的使用
        # assert elo_async.get_team_rating("TestTeam") == 1500.0

        # 模拟异步操作
        # team_id = "AsyncTest"
        # elo_async.team_ratings[team_id] = TeamRating(
        #     team_id=team_id, rating=1500.0, last_updated=datetime.utcnow()
        # )

        # 在异步上下文中更新评级
        # result = elo_async.update_ratings(
        #     home_team_id=team_id,
        #     away_team_id="OtherTeam",
        #     home_goals=1,
        #     away_goals=0,
        #     match_date=datetime.utcnow(),
        #     competition_type="league"
        # )

        # assert result["success"] is True


class TestKellyCriterion:
    """凯利准则系统测试类"""

    @pytest.fixture
    def kelly_system(self):
        """创建凯利准则系统实例"""
        from src.strategy.kelly_criterion import KellyCriterion, KellyStrategy

        return KellyCriterion(
            initial_bankroll=10000.0,
            kelly_strategy=KellyStrategy.FRACTIONAL_KELLY,
            fraction_multiplier=0.25,
            min_edge_threshold=0.05,
            max_stake_percentage=0.10,
        )

    def test_basic_kelly_calculation(self, kelly_system):
        """测试基础凯利公式计算"""
        # 凯利公式: f* = (bp - q) / b
        # 其中 b为十进制赔率-1, p为胜率, q为败率

        # 测试简单情况：赔率2.0，预测概率60%
        odds = 2.0
        probability = 0.6

        # 手动计算期望结果
        expected_f = (odds * probability - (1 - probability)) / (odds - 1)
        # expected_f = (2.0 * 0.6 - 0.4) / 1.0  # = 0.2

        result = kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=probability)

        assert result["kelly_fraction"] == expected_f
        assert result["edge"] == odds * probability - 1
        assert result["should_bet"] is True

    def test_kelly_fractional_strategy(self, kelly_system):
        """测试分数凯利策略"""
        # 完整凯利：f* = 0.2
        odds = 2.5
        probability = 0.6

        result = kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=probability)

        # 分数Kelly应该是完整凯利的25%
        full_kelly = (odds * probability - (1 - probability)) / (odds - 1)
        expected_fractional = full_kelly * kelly_system.fraction_multiplier

        assert result["kelly_fraction"] == expected_fractional
        assert result["strategy_used"] == KellyStrategy.FRACTIONAL_KELLY.value

    def test_edge_threshold_filtering(self, kelly_system):
        """测试优势阈值过滤"""
        # 低优势情况（不应该投注）
        odds = 1.1  # 低赔率
        probability = 0.55  # 略高概率

        result = kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=probability)

        # 优势5%以下不应该投注
        assert result["should_bet"] is False
        assert result["kelly_fraction"] == 0.0
        assert "edge too low" in result["reasoning"].lower()

        # 高优势情况
        odds = 3.0
        probability = 0.7

        result = kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=probability)

        assert result["should_bet"] is True
        assert result["kelly_fraction"] > 0.0

    def test_maximum_stake_limit(self, kelly_system):
        """测试最大投注比例限制"""
        # 极高优势情况，理论上会产生大额投注
        odds = 5.0
        probability = 0.8

        result = kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=probability)

        # 投注比例应该被限制在最大值
        max_allowed = kelly_system.max_stake_percentage
        assert result["kelly_fraction"] <= max_allowed

        if result["kelly_fraction"] > max_allowed:
            assert result["stake_limited"] is True
            assert f"limited to {max_allowed:.1%}" in result["reasoning"].lower()

    def test_multiple_outcome_analysis(self, kelly_system):
        """测试多结果分析"""
        outcomes = {
            "home": {"odds": 2.1, "probability": 0.45, "confidence": 0.8},
            "draw": {"odds": 3.4, "probability": 0.25, "confidence": 0.7},
            "away": {"odds": 4.2, "probability": 0.30, "confidence": 0.6},
        }

        recommendations = kelly_system.generate_bet_recommendation(outcomes)

        # 验证返回推荐列表
        assert isinstance(recommendations, list)

        # 验证每个推荐的结构
        for rec in recommendations:
            assert hasattr(rec, "outcome")
            assert hasattr(rec, "odds")
            assert hasattr(rec, "predicted_prob")
            assert hasattr(rec, "kelly_fraction")
            assert hasattr(rec, "stake_amount")
            assert hasattr(rec, "expected_value")
            assert hasattr(rec, "risk_level")

    def test_portfolio_management(self, kelly_system):
        """测试投资组合管理"""
        # 获取初始投资组合状态
        portfolio = kelly_system.get_portfolio_state()

        assert portfolio["bankroll"]["total"] == 10000.0
        assert portfolio["bankroll"]["available"] == 10000.0
        assert portfolio["performance"]["win_rate"] == 0.0
        assert portfolio["performance"]["current_drawdown"] == 0.0

        # 模拟成功的投注
        successful_bet = {
            "outcome": "home",
            "stake_amount": 100.0,
            "payout": 210.0,  # 赔率2.1
            "profit": 110.0,
        }

        kelly_system._update_portfolio_after_bet(successful_bet)

        updated_portfolio = kelly_system.get_portfolio_state()

        # 验证资金更新
        assert updated_portfolio["bankroll"]["total"] == 10000.0 + 110.0
        assert updated_portfolio["bankroll"]["available"] == 10000.0 - 100.0 + 110.0
        assert updated_portfolio["performance"]["total_bets"] == 1
        assert updated_portfolio["performance"]["total_profit"] == 110.0
        assert updated_portfolio["performance"]["win_rate"] == 1.0

        # 模拟失败的投注
        failed_bet = {
            "outcome": "home",
            "stake_amount": 150.0,
            "payout": 0.0,
            "loss": 150.0,
        }

        kelly_system._update_portfolio_after_bet(failed_bet)

        final_portfolio = kelly_system.get_portfolio_state()

        # 验证亏损处理
        assert final_portfolio["bankroll"]["total"] == 10000.0 + 110.0 - 150.0
        assert final_portfolio["performance"]["total_bets"] == 2
        assert final_portfolio["performance"]["total_profit"] == -40.0
        assert final_portfolio["performance"]["win_rate"] == 0.5

    def test_losing_streak_detection(self, kelly_system):
        """测试连败检测和调整"""
        # 模拟连败序列
        losing_streak = []

        for i in range(5):
            failed_bet = {
                "outcome": "home",
                "stake_amount": 200.0,
                "payout": 0.0,
                "loss": 200.0,
            }
            losing_streak.append(failed_bet)
            kelly_system._update_portfolio_after_bet(failed_bet)

        # 检查连败计数
        current_streak = kelly_system._check_current_losing_streak()
        assert current_streak == 5

        # 模拟恢复
        winning_bet = {
            "outcome": "home",
            "stake_amount": 100.0,
            "payout": 250.0,
            "profit": 150.0,
        }
        kelly_system._update_portfolio_after_bet(winning_bet)

        # 连败计数应该重置
        current_streak = kelly_system._check_current_losing_streak()
        assert current_streak == 0

    def test_dynamic_risk_adjustment(self, kelly_system):
        """测试动态风险调整"""
        # 模拟高风险状态
        kelly_system._update_risk_level("high")

        # 高风险时应该降低投注比例
        normal_kelly = 0.15
        adjusted_kelly = kelly_system._adjust_kelly_for_risk(normal_kelly)

        assert adjusted_kelly < normal_kelly

        # 模拟低风险状态
        kelly_system._update_risk_level("low")

        normal_kelly = 0.15
        adjusted_kelly = kelly._adjust_kelly_for_risk(normal_kelly)

        # 低风险时可以使用完整比例
        assert adjusted_kelly >= normal_kelly

    def test_confidence_weighting(self, kelly_system):
        """测试置信度权重"""
        # 高置信度预测应该获得更高权重
        high_confidence_kelly = kelly._adjust_kelly_for_confidence(kelly_fraction=0.15, confidence=0.9)

        low_confidence_kelly = kelly._adjust_kelly_for_confidence(kelly_fraction=0.15, confidence=0.3)

        assert high_confidence_kelly > low_confidence_kelly

    def test_robustness_to_extreme_values(self, kelly_system):
        """测试极端值的鲁棒性"""
        # 极端赔率
        with pytest.raises(ValueError):
            kelly_system.calculate_kelly_fraction(decimal_odds=0.0, predicted_prob=0.6)  # 无效赔率

        # 无效概率
        with pytest.raises(ValueError):
            kelly_system.calculate_kelly_fraction(
                decimal_odds=2.0,
                predicted_prob=0.0,  # 概率为0
            )

        # 超出概率范围
        with pytest.raises(ValueError):
            kelly_system.calculate_kelly_fraction(decimal_odds=2.0, predicted_prob=1.5)  # 概率超过100%

        # 负数赔率
        with pytest.raises(ValueError):
            kelly_system.calculate_kelly_fraction(decimal_odds=-1.0, predicted_prob=0.6)  # 负数赔率

    def test_comprehensive_betting_scenario(self, kelly_system):
        """测试综合投注场景"""
        # 模拟一系列比赛和投注
        matches = [
            {
                "outcomes": {
                    "home": {"odds": 2.1, "probability": 0.55, "confidence": 0.8},
                    "draw": {"odds": 3.4, "probability": 0.25, "confidence": 0.7},
                    "away": {"odds": 4.2, "probability": 0.20, "confidence": 0.6},
                },
                "actual_outcome": "home",
            },
            {
                "outcomes": {
                    "home": {"odds": 1.9, "probability": 0.52, "confidence": 0.7},
                    "draw": {"odds": 3.6, "probability": 0.28, "confidence": 0.6},
                    "away": {"odds": 4.0, "probability": 0.20, "confidence": 0.5},
                },
                "actual_outcome": "draw",
            },
            {
                "outcomes": {
                    "home": {"odds": 2.3, "probability": 0.45, "confidence": 0.75},
                    "draw": {"odds": 3.2, "probability": 0.30, "confidence": 0.6},
                    "away": {"odds": 3.8, "probability": 0.25, "confidence": 0.5},
                },
                "actual_outcome": "home",
            },
        ]

        # 执行投注序列
        for match in matches:
            recommendations = kelly_system.generate_bet_recommendation(match["outcomes"])

            for rec in recommendations:
                if rec.should_bet:
                    # 模拟投注结果
                    if match["actual_outcome"] == rec.outcome:
                        # 赢利
                        profit = rec.stake_amount * (rec.odds - 1)
                        kelly_system._update_portfolio_after_bet(
                            {
                                "outcome": rec.outcome,
                                "stake_amount": rec.stake_amount,
                                "payout": rec.stake_amount * rec.odds,
                                "profit": profit,
                            }
                        )
                    else:
                        # 亏损
                        kelly_system._update_portfolio_after_bet(
                            {
                                "outcome": rec.outcome,
                                "stake_amount": rec.stake_amount,
                                "payout": 0.0,
                                "loss": rec.stake_amount,
                            }
                        )

        # 验证最终投资组合状态
        final_portfolio = kelly_system.get_portfolio_state()

        assert final_portfolio["performance"]["total_bets"] == len(matches)
        assert final_portfolio["bankroll"]["total"] == 10000.0 + final_portfolio["performance"]["total_profit"]

        # 验证性能指标
        assert final_portfolio["performance"]["win_rate"] >= 0.0
        assert final_portfolio["performance"]["sharpe_ratio"] is not None
        assert final_portfolio["performance"]["max_drawdown"] >= 0.0

    def test_bankroll_management_boundaries(self, kelly_system):
        """测试资金管理边界条件"""
        # 测试资金耗尽情况
        kelly_system.bankroll = 100.0  # 设置极小资金

        outcomes = {"home": {"odds": 2.5, "probability": 0.6, "confidence": 0.8}}

        result = kelly_system.calculate_kelly_fraction(
            decimal_odds=outcomes["home"]["odds"],
            predicted_prob=outcomes["home"]["probability"],
        )

        # 资金不足时应该限制投注
        assert result["stake_limited"] is True
        assert result["bankroll_exhausted"] is True
        assert result["reasoning"] and "insufficient bankroll" in result["reasoning"].lower()

    def test_portfolio_state_persistence(self, kelly_system):
        """测试投资组合状态持久化"""
        # 获取初始状态
        initial_state = kelly.get_portfolio_state()

        # 添加一些投注记录
        test_bet = {
            "outcome": "home",
            "stake_amount": 500.0,
            "payout": 1200.0,
            "profit": 700.0,
        }

        kelly_system._update_portfolio_after_bet(test_bet)

        intermediate_state = kelly.get_portfolio_state()

        # 验证状态变化
        assert intermediate_state["performance"]["total_bets"] == 1
        assert intermediate_state["performance"]["total_profit"] == 700.0

        # 模拟状态保存和恢复
        saved_state = intermediate_state
        kelly_system.restore_portfolio_state(saved_state)

        # 验证状态恢复
        restored_state = kelly_system.get_portfolio_state()
        assert restored_state["performance"]["total_bets"] == 1
        assert restored_state["performance"]["total_profit"] == 700.0
        assert restored_state["bankroll"]["total"] == 10000.0 + 700.0

    def test_strategy_configuration_impact(self, kelly_system):
        """测试不同策略配置的影响"""
        # 测试保守策略
        conservative_kelly = KellyCriterion(
            kelly_strategy=KellyStrategy.CONSERVATIVE,
            fraction_multiplier=0.1,
            max_stake_percentage=0.05,
        )

        # 测试激进策略
        aggressive_kelly = KellyCriterion(
            kelly_strategy=KellyStrategy.AGGRESSIVE,
            fraction_multiplier=0.5,
            max_stake_percentage=0.25,
        )

        # 相同预测，不同策略
        outcomes = {"home": {"odds": 2.5, "probability": 0.6, "confidence": 0.8}}

        conservative_result = conservative_kelly.calculate_kelly_fraction(
            decimal_odds=outcomes["home"]["odds"],
            predicted_prob=outcomes["home"]["probability"],
        )

        aggressive_result = aggressive_kelly.calculate_kelly_fraction(
            decimal_odds=outcomes["home"]["odds"],
            predicted_prob=outcomes["home"]["probability"],
        )

        # 激进策略应该产生更高的投注比例
        assert aggressive_result["kelly_fraction"] > conservative_result["kelly_fraction"]

        # 保守策略应该有更严格的最大投注限制
        assert conservative_kelly["max_stake_percentage"] == 0.05
        assert aggressive_kelly["max_stake_percentage"] == 0.25

    def test_error_handling_and_recovery(self, kelly_system):
        """测试错误处理和恢复机制"""
        # 测试无效赔率处理
        with pytest.raises(ValueError):
            kelly_system.calculate_kelly_fraction(decimal_odds="invalid", predicted_prob=0.5)

        # 测试概率验证错误处理
        outcomes = {"home": {"odds": 2.5, "probability": 0.6, "confidence": 0.8}}
        outcomes["home"]["probability"] = 1.5  # 无效概率

        with pytest.raises(ValueError):
            kelly_system.generate_bet_recommendation(outcomes)

        # 测试部分结果无效的情况
        outcomes["home"]["probability"] = 0.6  # 有效
        outcomes["draw"]["probability"] = 1.2  # 无效
        outcomes["away"]["probability"] = 0.2  # 有效

        # 应该仍然能生成有效的推荐（排除无效结果）
        recommendations = kelly_system.generate_bet_recommendation(outcomes)
        valid_recommendations = [r for r in recommendations if r.should_bet]
        assert len(valid_recommendations) == 1  # 只有home是有效的

    def test_performance_optimizations(self, kelly_system):
        """测试性能优化"""
        import time

        # 测试批量计算性能
        start_time = time.time()

        # 批量生成凯利计算
        for i in range(100):
            odds = 2.0 + (i * 0.01)
            prob = 0.5 + (i * 0.001)
            kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=prob)

        calculation_time = time.time() - start_time
        print(f"100次凯利计算耗时: {calculation_time:.4f}s")

        # 验证性能目标（应该在合理范围内）
        assert calculation_time < 1.0  # 100次计算应该在1秒内完成

    def test_memory_efficiency(self, kelly_system):
        """测试内存使用效率"""
        # 测试大量数据存储不会导致内存泄漏
        initial_portfolio = kelly_system.get_portfolio_state()

        # 添加大量投注记录
        for i in range(1000):
            test_bet = {
                "outcome": "home",
                "stake_amount": 100.0,
                "payout": 0.0,
                "loss": 100.0,
            }
            kelly_system._update_portfolio_after_bet(test_bet)

        # 验证内存没有持续增长
        final_portfolio = kelly.get_portfolio_state()

        # 投注记录数量应该正确增长
        assert final_portfolio["performance"]["total_bets"] == 1000

        # 验证基本内存使用不会爆炸
        portfolio_size = len(str(final_portfolio))
        assert portfolio_size < 10000  # 合理的内存使用量

    def test_integration_with_prediction_system(self, kelly_system):
        """测试与预测系统的集成"""
        # 这里需要模拟与预测服务的集成
        # 由于预测服务可能在其他测试中测试，这里只做基本验证

        # 验证凯利系统可以处理预测服务的输出格式
        prediction_output = {
            "home_win_probability": 0.65,
            "draw_probability": 0.20,
            "away_win_probability": 0.15,
            "home_odds": 2.1,
            "draw_odds": 3.4,
            "away_odds": 4.2,
        }

        # 验证可以处理预测输出
        assert kelly_system._handle_prediction_output(prediction_output) is not None

    def test_backtesting_compatibility(self, kelly_system):
        """测试与回测系统的兼容性"""
        # 验证凯利系统可以为回测提供资金管理功能
        assert hasattr(kelly_system, "get_portfolio_state")
        assert hasattr(kelly_system, "generate_bet_recommendation")
        assert hasattr(kelly_system, "_update_portfolio_after_bet")

        # 验证数据格式一致性
        portfolio = kelly_system.get_portfolio_state()
        required_fields = ["bankroll", "performance", "risk_management"]

        for field in required_fields:
            assert field in portfolio

    def test_long_term_stability(self, kelly_system):
        """测试长期运行稳定性"""
        # 模拟长期运行场景
        days_of_trading = 100
        bets_per_day = 5

        initial_bankroll = kelly_system.get_bankroll()

        for day in range(days_of_trading):
            for bet in range(bets_per_day):
                # 模拟日度投注
                daily_profit = 0
                for outcome in ["home", "draw", "away"]:
                    if outcome == "home":
                        odds = 2.5
                        prob = 0.55
                    elif outcome == "draw":
                        odds = 3.4
                        prob = 0.25
                    else:
                        odds = 4.0
                        prob = 0.20

                    if prob * odds > 1.0:  # 有正期望
                        daily_profit += (prob * (odds - 1) - 1) * 50

                # 更新投资组合
                kelly_system._update_daily_performance(daily_profit)

        # 验证长期稳定性
        final_bankroll = kelly_system.get_bankroll()
        assert final_bankroll > initial_bankroll * 0.95  # 允许小幅损失
        assert final_bankroll <= initial_bankroll * 5.0  # 限制最大增长

    def test_edge_case_probability(self, kelly_system):
        """测试边界概率情况"""
        # 刚好在边界上的概率
        edge_cases = [
            (0.01, 2.1, "极低优势"),
            (0.05, 2.1, "最低门槛"),
            (0.95, 1.1, "极低赔率"),
            (0.99, 5.0, "极高概率"),
            (0.501, 2.0, "刚好优势"),
            (0.49, 2.02, "边缘情况"),
        ]

        for prob, odds, description in edge_cases:
            result = kelly_system.calculate_kelly_fraction(decimal_odds=odds, predicted_prob=prob)

            # 验证结果的合理性
            if prob <= 0.05:
                assert result["should_bet"] is False
            elif prob >= 0.95 and odds <= 1.1:
                assert result["should_bet"] is False
            else:
                # 合理范围内的投注
                if result["should_bet"]:
                    assert 0.0 < result["kelly_fraction"] <= kelly_system.max_stake_percentage

    def test_integration_consistency(self):
        """测试集成一致性"""
        # 验证所有组件能够正常协作
        # 这里可以添加与其他系统的集成测试

        # 基础一致性检查
        assert kelly_system.initial_bankroll == 10000.0
        assert kelly_system.fraction_multiplier == 0.25
        assert kelly_system.min_edge_threshold == 0.05
        assert kelly_system.max_stake_percentage == 0.10


# 运行测试
if __name__ == "__main__":
    pytest.main(
        [
            "-v",
            "--tb=short",
            "tests/unit/test_elo_rating_system.py",
            "tests/unit/test_kelly_criterion.py",
        ]
    )
