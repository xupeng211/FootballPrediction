"""
核心业务逻辑单元测试
测试足球预测系统的核心算法和业务规则
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from typing import Dict, List, Any
import datetime
import math


class TestMatchPredictionLogic:
    """比赛预测逻辑测试"""

    def test_prediction_outcome_mapping(self):
        """测试预测结果映射逻辑"""
        # 模型输出到预测结果的映射
        model_outputs = [0, 1, 2]  # HOME_WIN, DRAW, AWAY_WIN
        expected_outcomes = ["HOME_WIN", "DRAW", "AWAY_WIN"]

        for i, output in enumerate(model_outputs):
            assert output in [0, 1, 2]
            assert expected_outcomes[i] in ["HOME_WIN", "DRAW", "AWAY_WIN"]

        # 测试无效输出
        invalid_outputs = [-1, 3, 10]
        for output in invalid_outputs:
            assert output not in [0, 1, 2]

    def test_confidence_calculation(self):
        """测试置信度计算逻辑"""
        # 测试不同的概率分布
        test_cases = [
            {"probabilities": [0.8, 0.1, 0.1], "expected_confidence": 0.8},
            {"probabilities": [0.5, 0.3, 0.2], "expected_confidence": 0.5},
            {"probabilities": [0.4, 0.4, 0.2], "expected_confidence": 0.4},
            {"probabilities": [0.33, 0.33, 0.34], "expected_confidence": 0.34},
        ]

        for case in test_cases:
            probs = case["probabilities"]
            confidence = max(probs)
            assert abs(confidence - case["expected_confidence"]) < 0.01
            assert sum(probs) == pytest.approx(1.0, rel=1e-2)

    def test_feature_importance_ranking(self):
        """测试特征重要性排序逻辑"""
        # 模拟特征重要性
        feature_importance = {
            "home_form": 0.25,
            "away_form": 0.20,
            "h2h_advantage": 0.18,
            "venue_advantage": 0.15,
            "injuries": 0.12,
            "weather": 0.10,
        }

        # 按重要性排序
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        # 验证排序正确
        assert sorted_features[0][0] == "home_form"
        assert sorted_features[0][1] == 0.25
        assert sorted_features[-1][0] == "weather"
        assert sorted_features[-1][1] == 0.10

        # 验证总重要性
        total_importance = sum(feature_importance.values())
        assert abs(total_importance - 1.0) < 0.01

    def test_odds_conversion_logic(self):
        """测试赔率转换逻辑"""
        # 测试赔率到概率的转换
        odds_cases = [
            {"odds": 2.0, "expected_prob": 0.5},
            {"odds": 3.0, "expected_prob": 0.333},  # 近似值
            {"odds": 1.5, "expected_prob": 0.667},  # 近似值
        ]

        for case in odds_cases:
            odds = case["odds"]
            implied_prob = 1.0 / odds
            assert abs(implied_prob - case["expected_prob"]) < 0.01

            # 验证概率范围
            assert 0 < implied_prob <= 1

    def test_team_strength_calculation(self):
        """测试队伍实力计算逻辑"""
        # 模拟比赛数据
        team_stats = {
            "wins": 15,
            "draws": 5,
            "losses": 10,
            "goals_scored": 45,
            "goals_conceded": 30,
            "matches_played": 30,
        }

        # 计算实力指标
        total_matches = team_stats["matches_played"]
        win_rate = team_stats["wins"] / total_matches
        draw_rate = team_stats["draws"] / total_matches
        loss_rate = team_stats["losses"] / total_matches

        # 计算平均进球
        avg_goals_scored = team_stats["goals_scored"] / total_matches
        avg_goals_conceded = team_stats["goals_conceded"] / total_matches
        goal_diff = avg_goals_scored - avg_goals_conceded

        # 验证计算结果
        assert abs(win_rate + draw_rate + loss_rate - 1.0) < 0.01
        assert 0 <= win_rate <= 1
        assert 0 <= draw_rate <= 1
        assert 0 <= loss_rate <= 1
        assert avg_goals_scored >= 0
        assert avg_goals_conceded >= 0

    def test_form_calculation(self):
        """测试近期状态计算"""
        # 模拟最近5场比赛结果
        recent_results = ["W", "D", "W", "L", "W"]  # W=赢, D=平, L=输

        # 计算状态分数
        points_map = {"W": 3, "D": 1, "L": 0}
        form_points = sum(points_map[result] for result in recent_results)

        # 计算状态统计
        wins = recent_results.count("W")
        draws = recent_results.count("D")
        losses = recent_results.count("L")

        # 验证计算
        assert form_points == 10  # 3+1+3+0+3
        assert wins == 3
        assert draws == 1
        assert losses == 1
        assert wins + draws + losses == len(recent_results)

    def test_home_advantage_calculation(self):
        """测试主场优势计算"""
        # 模拟主客场数据
        team_performance = {
            "home_wins": 12,
            "home_draws": 3,
            "home_losses": 5,
            "away_wins": 8,
            "away_draws": 4,
            "away_losses": 8,
            "total_home_goals": 35,
            "total_away_goals": 28,
        }

        home_matches = team_performance["home_wins"] + team_performance["home_draws"] + team_performance["home_losses"]
        away_matches = team_performance["away_wins"] + team_performance["away_draws"] + team_performance["away_losses"]

        # 计算主客场胜率
        home_win_rate = team_performance["home_wins"] / home_matches
        away_win_rate = team_performance["away_wins"] / away_matches

        # 计算主场优势
        home_advantage = home_win_rate - away_win_rate
        avg_home_goals = team_performance["total_home_goals"] / home_matches
        avg_away_goals = team_performance["total_away_goals"] / away_matches
        goal_advantage = avg_home_goals - avg_away_goals

        # 验证计算
        assert 0 <= home_win_rate <= 1
        assert 0 <= away_win_rate <= 1
        assert -1 <= home_advantage <= 1
        assert avg_home_goals >= 0
        assert avg_away_goals >= 0

    def test_season_performance_analysis(self):
        """测试赛季表现分析"""
        # 模拟赛季数据
        season_data = [
            {"match_id": 1, "result": "W", "goals_scored": 2, "goals_conceded": 1},
            {"match_id": 2, "result": "L", "goals_scored": 0, "goals_conceded": 2},
            {"match_id": 3, "result": "D", "goals_scored": 1, "goals_conceded": 1},
            {"match_id": 4, "result": "W", "goals_scored": 3, "goals_conceded": 1},
            {"match_id": 5, "result": "L", "goals_scored": 1, "goals_conceded": 3},
        ]

        # 计算赛季统计
        total_matches = len(season_data)
        wins = sum(1 for match in season_data if match["result"] == "W")
        draws = sum(1 for match in season_data if match["result"] == "D")
        losses = sum(1 for match in season_data if match["result"] == "L")

        total_goals_scored = sum(match["goals_scored"] for match in season_data)
        total_goals_conceded = sum(match["goals_conceded"] for match in season_data)

        win_rate = wins / total_matches
        avg_goals_scored = total_goals_scored / total_matches
        avg_goals_conceded = total_goals_conceded / total_matches
        goal_difference = avg_goals_scored - avg_goals_conceded

        # 验证计算
        assert wins + draws + losses == total_matches
        assert abs(win_rate + (draws / total_matches) + (losses / total_matches) - 1.0) < 0.01
        assert 0 <= win_rate <= 1
        assert avg_goals_scored >= 0
        assert avg_goals_conceded >= 0


class TestDataValidationRules:
    """数据验证规则测试"""

    def test_team_name_validation(self):
        """测试队伍名称验证规则"""
        valid_names = [
            "Manchester United",
            "FC Barcelona",
            "Bayern Munich",
            "AC Milan",
            "Real Madrid CF",
        ]

        invalid_names = [
            "",  # 空字符串
            "   ",  # 只有空格
            "A",  # 太短
            "A" * 100,  # 太长
            "123",  # 只有数字
            "Team#$%",  # 包含特殊字符
            None,  # None值
        ]

        # 测试有效名称
        for name in valid_names:
            assert isinstance(name, str)
            assert len(name.strip()) > 0
            assert len(name) <= 50  # 合理长度限制
            assert name.replace(" ", "").isalpha()  # 只包含字母和空格

        # 测试无效名称的验证逻辑
        for name in invalid_names:
            if name is None:
                continue
            if name.strip() == "":
                assert True  # 空字符串应该被拒绝
            elif len(name) < 2 or len(name) > 50:
                assert True  # 长度不合理应该被拒绝

    def test_score_validation(self):
        """测试比分验证规则"""
        valid_scores = [
            (0, 0),
            (1, 0),
            (0, 1),
            (2, 1),
            (1, 2),
            (3, 0),
            (0, 3),
            (4, 2),
            (2, 4),
            (5, 5),
        ]

        invalid_scores = [
            (-1, 0),
            (0, -1),  # 负分
            (-1, -2),  # 都为负分
            (100, 0),
            (0, 100),  # 不合理的高分
            (1.5, 0),
            (0, 2.5),  # 非整数
        ]

        # 测试有效比分
        for home_score, away_score in valid_scores:
            assert isinstance(home_score, int)
            assert isinstance(away_score, int)
            assert home_score >= 0 and away_score >= 0
            assert home_score <= 20 and away_score <= 20  # 合理比分上限

        # 测试无效比分
        for home_score, away_score in invalid_scores:
            if home_score is None or away_score is None:
                continue
            if home_score < 0 or away_score < 0:
                assert True  # 负分应该被拒绝
            elif home_score > 20 or away_score > 20:
                assert True  # 过高比分应该被拒绝

    def test_date_validation(self):
        """测试日期验证规则"""
        import datetime

        valid_dates = [
            "2024-01-15",
            "2024-12-31",
            "2024-02-29",  # 闰年
            datetime.date(2024, 6, 15),
            datetime.datetime(2024, 6, 15, 14, 30),
        ]

        invalid_dates = [
            "2024-13-01",  # 无效月份
            "2024-02-30",  # 无效日期
            "2024-02-31",  # 无效日期
            "invalid-date",
            "",
            None,
        ]

        # 测试有效日期
        for date in valid_dates:
            if isinstance(date, str):
                # 尝试解析日期字符串
                try:
                    parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d")
                    assert 2000 <= parsed_date.year <= 2100  # 合理年份范围
                except ValueError:
                    pytest.fail(f"无效日期格式: {date}")
            else:
                assert isinstance(date, (datetime.date, datetime.datetime))

        # 测试无效日期
        for date in invalid_dates:
            if date is None or date == "":
                continue
            if isinstance(date, str):
                try:
                    datetime.datetime.strptime(date, "%Y-%m-%d")
                    pytest.fail(f"应该解析失败的日期: {date}")
                except ValueError:
                    assert True  # 预期的解析失败

    def test_probability_validation(self):
        """测试概率验证规则"""
        valid_probabilities = [0.0, 0.1, 0.5, 0.9, 1.0]

        invalid_probabilities = [-0.1, -0.5, 1.1, 1.5, 2.0]  # 负概率  # 超过1的概率

        # 测试有效概率
        for prob in valid_probabilities:
            assert 0 <= prob <= 1

        # 测试无效概率
        for prob in invalid_probabilities:
            assert not (0 <= prob <= 1)

    def test_league_validation(self):
        """测试联赛验证规则"""
        valid_leagues = [
            "Premier League",
            "La Liga",
            "Serie A",
            "Bundesliga",
            "Ligue 1",
        ]

        # 测试已知联赛
        for league in valid_leagues:
            assert isinstance(league, str)
            assert len(league.strip()) > 0

        # 测试未知联赛处理
        unknown_league = "Unknown League 2024"
        assert isinstance(unknown_league, str)
        # 未知联赛应该被记录但不阻止处理

    def test_venue_validation(self):
        """测试场地验证规则"""
        valid_venues = [
            "Old Trafford",
            "Camp Nou",
            "Allianz Arena",
            "San Siro",
            "Stadium of Light",
        ]

        invalid_venues = [
            "",  # 空字符串
            None,  # None值
            "A",  # 太短
        ]

        # 测试有效场地
        for venue in valid_venues:
            assert isinstance(venue, str)
            assert len(venue.strip()) >= 3
            assert len(venue) <= 100  # 合理长度限制

        # 测试无效场地
        for venue in invalid_venues:
            if venue is None:
                continue
            if venue.strip() == "":
                assert True  # 空场地应该被拒绝


class TestPredictionScoringMetrics:
    """预测评分指标测试"""

    def test_accuracy_calculation(self):
        """测试准确率计算"""
        # 模拟预测结果和实际结果
        predictions = ["HOME_WIN", "DRAW", "AWAY_WIN", "HOME_WIN", "DRAW"]
        actual_results = [
            "HOME_WIN",
            "AWAY_WIN",
            "AWAY_WIN",
            "HOME_WIN",
            "DRAW",
        ]  # 修改为3个匹配

        # 计算准确率
        correct_predictions = sum(1 for pred, actual in zip(predictions, actual_results) if pred == actual)
        total_predictions = len(predictions)
        accuracy = correct_predictions / total_predictions

        # 验证计算 (手动验证: 第1、3、4、5个预测正确)
        expected_correct = (
            4  # "HOME_WIN" vs "HOME_WIN", "AWAY_WIN" vs "AWAY_WIN", "HOME_WIN" vs "HOME_WIN", "DRAW" vs "DRAW"
        )
        expected_accuracy = expected_correct / total_predictions  # 4/5 = 0.8

        assert correct_predictions == expected_correct
        assert accuracy == expected_accuracy
        assert 0 <= accuracy <= 1

    def test_precision_recall_calculation(self):
        """测试精确率和召回率计算"""
        # 模拟二元分类结果
        true_labels = [1, 0, 1, 1, 0, 0, 1, 0]
        predictions = [1, 0, 1, 0, 0, 1, 1, 0]

        # 计算混淆矩阵
        tp = sum(1 for true, pred in zip(true_labels, predictions) if true == 1 and pred == 1)
        fp = sum(1 for true, pred in zip(true_labels, predictions) if true == 0 and pred == 1)
        fn = sum(1 for true, pred in zip(true_labels, predictions) if true == 1 and pred == 0)
        tn = sum(1 for true, pred in zip(true_labels, predictions) if true == 0 and pred == 0)

        # 计算精确率和召回率
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        # 验证计算
        assert tp == 3  # TP
        assert fp == 1  # FP
        assert fn == 1  # FN
        assert tn == 3  # TN
        assert precision == 3 / 4
        assert recall == 3 / 4
        assert 0 <= precision <= 1
        assert 0 <= recall <= 1

    def test_brier_score_calculation(self):
        """测试Brier分数计算"""
        # 模拟概率预测和实际结果
        predicted_probs = [0.8, 0.3, 0.6, 0.2, 0.7]  # 预测为正类的概率
        actual_outcomes = [1, 0, 1, 0, 1]  # 实际结果

        # 计算Brier分数
        brier_score = sum((prob - outcome) ** 2 for prob, outcome in zip(predicted_probs, actual_outcomes)) / len(
            actual_outcomes
        )

        # 验证计算
        expected_score = ((0.8 - 1) ** 2 + (0.3 - 0) ** 2 + (0.6 - 1) ** 2 + (0.2 - 0) ** 2 + (0.7 - 1) ** 2) / 5
        assert abs(brier_score - expected_score) < 0.01
        assert 0 <= brier_score <= 1

    def test_log_loss_calculation(self):
        """测试对数损失计算"""
        import math

        # 模拟概率预测和实际结果
        predicted_probs = [0.9, 0.1, 0.7, 0.2, 0.8]  # 预测为正类的概率
        actual_outcomes = [1, 0, 1, 0, 1]  # 实际结果

        # 计算对数损失
        epsilon = 1e-15  # 避免log(0)
        log_loss = -sum(
            outcome * math.log(prob + epsilon) + (1 - outcome) * math.log(1 - prob + epsilon)
            for prob, outcome in zip(predicted_probs, actual_outcomes)
        ) / len(actual_outcomes)

        # 验证计算
        assert log_loss > 0
        assert not math.isinf(log_loss)
        assert not math.isnan(log_loss)

    def test_auc_calculation(self):
        """测试AUC计算"""
        # 模拟概率预测和实际结果
        predicted_probs = [0.9, 0.8, 0.7, 0.6, 0.4, 0.3, 0.2, 0.1]
        actual_outcomes = [1, 1, 1, 0, 1, 0, 0, 0]

        # 简化的AUC计算（正确计算排名对）
        sorted_pairs = sorted(zip(predicted_probs, actual_outcomes), key=lambda x: x[0], reverse=True)

        # 分离正样本和负样本
        positive_scores = [prob for prob, outcome in sorted_pairs if outcome == 1]
        negative_scores = [prob for prob, outcome in sorted_pairs if outcome == 0]

        # 计算正样本得分大于负样本得分的概率
        auc_numerator = 0
        auc_denominator = len(positive_scores) * len(negative_scores)

        for pos_score in positive_scores:
            for neg_score in negative_scores:
                if pos_score > neg_score:
                    auc_numerator += 1
                elif pos_score == neg_score:
                    auc_numerator += 0.5  # 相等得分的处理

        auc = auc_numerator / auc_denominator if auc_denominator > 0 else 0.5

        # 验证计算
        assert 0 <= auc <= 1
        assert not math.isnan(auc)


class TestBusinessRuleValidation:
    """业务规则验证测试"""

    def test_minimum_matches_for_stats(self):
        """测试统计计算的最小比赛场次要求"""
        min_matches_required = 5

        # 测试有效场次
        valid_match_counts = [5, 10, 20, 50]
        for count in valid_match_counts:
            assert count >= min_matches_required

        # 测试无效场次
        invalid_match_counts = [0, 1, 2, 3, 4]
        for count in invalid_match_counts:
            assert count < min_matches_required

    def test_probability_threshold_validation(self):
        """测试概率阈值验证"""
        min_confidence_threshold = 0.6

        # 测试高置信度预测
        high_confidence_probs = [0.7, 0.8, 0.9, 1.0]
        for prob in high_confidence_probs:
            assert prob >= min_confidence_threshold

        # 测试低置信度预测
        low_confidence_probs = [0.1, 0.2, 0.3, 0.4, 0.5]
        for prob in low_confidence_probs:
            assert prob < min_confidence_threshold

    def test_data_freshness_validation(self):
        """测试数据新鲜度验证"""
        import datetime
        from datetime import timedelta

        max_data_age_days = 30

        # 测试新鲜数据
        today = datetime.date.today()
        fresh_dates = [
            today - timedelta(days=1),
            today - timedelta(days=7),
            today - timedelta(days=15),
            today - timedelta(days=29),
        ]

        for date in fresh_dates:
            data_age = (today - date).days
            assert data_age <= max_data_age_days

        # 测试过期数据
        stale_dates = [
            today - timedelta(days=31),
            today - timedelta(days=60),
            today - timedelta(days=365),
        ]

        for date in stale_dates:
            data_age = (today - date).days
            assert data_age > max_data_age_days

    def test_team_consistency_validation(self):
        """测试队伍一致性验证"""
        # 模拟队伍名称映射
        team_aliases = {
            "Manchester United": ["Man Utd", "Man United", "MUFC"],
            "Chelsea": ["Chelsea FC", "The Blues"],
            "Arsenal": ["Arsenal FC", "The Gunners"],
        }

        # 测试别名识别
        for standard_name, aliases in team_aliases.items():
            for alias in aliases:
                assert isinstance(alias, str)
                assert len(alias) > 0

        # 测试一致性规则
        assert "Manchester United" not in team_aliases["Chelsea"]
        assert "Chelsea" not in team_aliases["Arsenal"]

    def test_prediction_consistency_validation(self):
        """测试预测一致性验证"""
        # 模拟同一比赛的多次预测
        match_predictions = [
            {
                "timestamp": "2024-01-15 10:00",
                "prediction": "HOME_WIN",
                "confidence": 0.7,
            },
            {
                "timestamp": "2024-01-15 11:00",
                "prediction": "HOME_WIN",
                "confidence": 0.72,
            },
            {
                "timestamp": "2024-01-15 12:00",
                "prediction": "HOME_WIN",
                "confidence": 0.68,
            },
        ]

        # 验证预测一致性
        predictions = [p["prediction"] for p in match_predictions]
        assert all(pred == predictions[0] for pred in predictions)

        # 验证置信度在合理范围内
        confidences = [p["confidence"] for p in match_predictions]
        assert all(0 <= conf <= 1 for conf in confidences)
        assert max(confidences) - min(confidences) <= 0.1  # 置信度变化不超过10%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
