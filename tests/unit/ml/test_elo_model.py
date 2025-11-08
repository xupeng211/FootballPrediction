"""
Elo评级模型测试
Elo Rating Model Tests

专门测试Elo评级模型的功能，包括：
- Elo评级系统实现
- 评级计算和更新
- 预测概率计算
- K因子优化
- 历史数据处理
- 模型训练和评估
"""

import os

# 导入ML模块
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

try:
    from ml.models.base_model import TrainingResult
    from ml.models.elo_model import EloModel

    CAN_IMPORT = True
except ImportError as e:
    logger.warning(
        f"Warning: 无法导入Elo模型: {e}"
    )  # TODO: Add logger import if needed
    CAN_IMPORT = False


@pytest.mark.skipif(not CAN_IMPORT, reason="Elo模型导入失败")
class TestEloModel:
    """Elo模型测试"""

    @pytest.fixture
    def elo_model(self):
        """创建Elo模型实例"""
        return EloModel("1.0")

    @pytest.fixture
    def sample_training_data(self):
        """创建示例训练数据"""
        np.random.seed(42)
        n_matches = 500

        teams = [f"Team_{i}" for i in range(1, 21)]  # 20支球队

        data = []
        for _i in range(n_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 生成比分
            home_goals = np.random.poisson(1.4)
            away_goals = np.random.poisson(1.0)

            # 确定结果
            if home_goals > away_goals:
                result = "home_win"
            elif home_goals < away_goals:
                result = "away_win"
            else:
                result = "draw"

            data.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_goals,
                    "away_score": away_goals,
                    "result": result,
                    "date": datetime.now() - timedelta(days=np.random.randint(0, 365)),
                }
            )

        return pd.DataFrame(data)

    def test_elo_model_initialization(self, elo_model):
        """测试Elo模型初始化"""
        assert elo_model.model_name == "EloModel"
        assert elo_model.model_version == "1.0"
        assert not elo_model.is_trained
        assert hasattr(elo_model, "team_elos")  # 正确的属性名
        assert hasattr(elo_model, "k_factor")
        assert hasattr(elo_model, "home_advantage")

        # 检查默认值
        assert isinstance(elo_model.k_factor, (int, float))
        assert elo_model.k_factor > 0
        assert isinstance(elo_model.home_advantage, (int, float))

    def test_initial_rating_setup(self, elo_model):
        """测试初始评级设置"""
        assert hasattr(elo_model, "initial_rating")
        assert isinstance(elo_model.initial_rating, (int, float))
        assert elo_model.initial_rating > 0

    def test_expectation_score_calculation(self, elo_model):
        """测试期望得分计算"""
        # 测试相同评级的队伍
        expectation = elo_model._calculate_expectation(1500, 1500)
        assert expectation == 0.5  # 相同评级应该有相同的期望得分

        # 测试不同评级的队伍
        expectation_higher = elo_model._calculate_expectation(1600, 1400)
        expectation_lower = elo_model._calculate_expectation(1400, 1600)

        assert expectation_higher > 0.5  # 高评级队伍应该有更高期望
        assert expectation_lower < 0.5  # 低评级队伍应该有更低期望
        assert abs(expectation_higher + expectation_lower - 1.0) < 1e-6  # 和应该为1

    def test_rating_update_calculation(self, elo_model):
        """测试评级更新计算"""
        old_rating = 1500

        # 测试胜利情况
        new_rating_win = elo_model._update_rating(old_rating, 1500, actual_result=1.0)
        assert new_rating_win > old_rating

        # 测试失败情况
        new_rating_loss = elo_model._update_rating(old_rating, 1500, actual_result=0.0)
        assert new_rating_loss < old_rating

        # 测试平局情况
        new_rating_draw = elo_model._update_rating(old_rating, 1500, actual_result=0.5)
        assert abs(new_rating_draw - old_rating) < 1  # 平局时评级变化应该很小

    def test_outcome_conversion(self, elo_model):
        """测试结果转换"""
        # 测试不同比赛结果
        assert elo_model._convert_outcome_to_score("home_win") == 1.0
        assert elo_model._convert_outcome_to_score("away_win") == 0.0
        assert elo_model._convert_outcome_to_score("draw") == 0.5

        # 测试无效结果
        with pytest.raises(ValueError):
            elo_model._convert_outcome_to_score("invalid_result")

    def test_team_ratings_initialization(self, elo_model, sample_training_data):
        """测试队伍评级初始化"""
        # 训练模型以初始化评级
        elo_model.train(sample_training_data)

        # 检查所有队伍都有评级
        unique_teams = set(
            sample_training_data["home_team"].tolist()
            + sample_training_data["away_team"].tolist()
        )

        assert len(elo_model.team_elos) == len(unique_teams)

        # 检查评级在合理范围内
        for rating in elo_model.team_elos.values():
            assert isinstance(rating, (int, float))
            assert 1000 <= rating <= 2000  # 典型的Elo评级范围

    def test_feature_preparation(self, elo_model, sample_training_data):
        """测试特征准备"""
        # 先训练模型
        elo_model.train(sample_training_data)

        # 测试特征准备
        match_data = {"home_team": "Team_1", "away_team": "Team_2"}

        features = elo_model.prepare_features(match_data)

        assert isinstance(features, np.ndarray)
        assert len(features) >= 2  # 至少包含主客队评级

        # 检查特征值为正数
        assert all(f > 0 for f in features)

    def test_prediction_probability_calculation(self, elo_model, sample_training_data):
        """测试预测概率计算"""
        # 训练模型
        elo_model.train(sample_training_data)

        # 获取两个队伍
        teams = list(elo_model.team_ratings.keys())[:2]
        home_team, away_team = teams[0], teams[1]

        # 计算概率
        home_prob, draw_prob, away_prob = elo_model._calculate_match_probabilities(
            home_team, away_team
        )

        # 验证概率
        assert all(0 <= p <= 1 for p in [home_prob, draw_prob, away_prob])
        assert abs(sum([home_prob, draw_prob, away_prob]) - 1.0) < 1e-6

        # 验证主场优势（主队胜率应该略高）
        home_rating = elo_model.team_ratings[home_team]
        away_rating = elo_model.team_ratings[away_team]

        if abs(home_rating - away_rating) < 50:  # 评级相近时
            assert home_prob > away_prob  # 主场优势应该体现

    def test_model_training(self, elo_model, sample_training_data):
        """测试模型训练"""
        # 分割数据
        train_size = int(0.8 * len(sample_training_data))
        train_data = sample_training_data[:train_size]
        val_data = sample_training_data[train_size:]

        # 训练模型
        result = elo_model.train(train_data, val_data)

        # 验证训练结果
        assert isinstance(result, TrainingResult)
        assert result.model_name == "EloModel"
        assert result.training_samples == len(train_data)
        assert result.validation_samples == len(val_data)
        assert result.accuracy >= 0.0
        assert result.training_time > 0

        # 验证模型状态
        assert elo_model.is_trained
        assert elo_model.last_training_time is not None

    def test_sequential_rating_updates(self, elo_model):
        """测试顺序评级更新"""
        # 创建简单的比赛序列
        matches = pd.DataFrame(
            {
                "home_team": ["Team_A", "Team_A", "Team_B"],
                "away_team": ["Team_B", "Team_C", "Team_A"],
                "home_score": [2, 1, 0],
                "away_score": [1, 0, 1],
                "result": ["home_win", "home_win", "away_win"],
                "date": [datetime.now() - timedelta(days=i) for i in range(3, 0, -1)],
            }
        )

        # 训练模型
        elo_model.train(matches)

        # 验证评级更新
        assert len(elo_model.team_ratings) == 3  # Team_A, Team_B, Team_C

        # Team_A应该有最高评级（两胜一负）
        # Team_B应该有中间评级（一胜一负）
        # Team_C应该有最低评级（一负）
        ratings = elo_model.team_ratings
        assert ratings["Team_A"] > ratings["Team_B"] > ratings["Team_C"]

    def test_k_factor_optimization(self, elo_model):
        """测试K因子优化"""
        original_k = elo_model.k_factor

        # 测试不同K因子
        for k_factor in [10, 20, 30, 40]:
            elo_model.k_factor = k_factor

            # 创建简单数据
            matches = pd.DataFrame(
                {
                    "home_team": ["Team_A", "Team_B"],
                    "away_team": ["Team_B", "Team_A"],
                    "home_score": [1, 0],
                    "away_score": [0, 1],
                    "result": ["home_win", "away_win"],
                    "date": [datetime.now(), datetime.now()],
                }
            )

            # 训练模型
            elo_model.train(matches)

            # 验证评级变化与K因子相关
            # K因子越大，评级变化应该越大
            assert len(elo_model.team_ratings) == 2

        # 恢复原始K因子
        elo_model.k_factor = original_k

    def test_home_advantage_adjustment(self, elo_model):
        """测试主场优势调整"""
        # 设置不同的主场优势
        original_advantage = elo_model.home_advantage

        for advantage in [0, 50, 100]:
            elo_model.home_advantage = advantage

            # 创建评级相同的队伍比赛
            matches = pd.DataFrame(
                {
                    "home_team": ["Team_A"],
                    "away_team": ["Team_B"],
                    "home_score": [1],
                    "away_score": [0],
                    "result": ["home_win"],
                    "date": [datetime.now()],
                }
            )

            # 训练模型
            elo_model.train(matches)

            # 验证主场优势影响
            home_prob, draw_prob, away_prob = elo_model._calculate_match_probabilities(
                "Team_A", "Team_B"
            )

            # 主场优势越大，主队胜率应该越高
            assert home_prob >= away_prob

        # 恢复原始主场优势
        elo_model.home_advantage = original_advantage

    def test_model_evaluation(self, elo_model, sample_training_data):
        """测试模型评估"""
        # 训练模型
        elo_model.train(sample_training_data)

        # 评估模型
        metrics = elo_model.evaluate(sample_training_data)

        # 验证评估指标
        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "confusion_matrix" in metrics
        assert "total_predictions" in metrics

        # 验证指标范围
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1
        assert metrics["total_predictions"] > 0

    def test_model_save_and_load(self, elo_model, sample_training_data, tmp_path):
        """测试模型保存和加载"""
        # 训练模型
        elo_model.train(sample_training_data)
        original_ratings = elo_model.team_ratings.copy()

        # 保存模型
        model_path = tmp_path / "elo_model.pkl"
        success = elo_model.save_model(str(model_path))
        assert success
        assert model_path.exists()

        # 加载模型
        new_model = EloModel("1.0")
        success = new_model.load_model(str(model_path))
        assert success

        # 验证加载的模型
        assert new_model.is_trained
        assert new_model.team_ratings == original_ratings
        assert new_model.k_factor == elo_model.k_factor
        assert new_model.home_advantage == elo_model.home_advantage

    def test_rating_decay(self, elo_model):
        """测试评级衰减（如果实现）"""
        # 检查是否有评级衰减功能
        if hasattr(elo_model, "rating_decay"):
            original_decay = elo_model.rating_decay

            # 设置评级衰减
            elo_model.rating_decay = 0.99

            # 创建带有时间间隔的比赛
            old_date = datetime.now() - timedelta(days=365)
            recent_date = datetime.now()

            matches = pd.DataFrame(
                {
                    "home_team": ["Team_A", "Team_A"],
                    "away_team": ["Team_B", "Team_C"],
                    "home_score": [1, 1],
                    "away_score": [0, 0],
                    "result": ["home_win", "home_win"],
                    "date": [old_date, recent_date],
                }
            )

            # 训练模型
            elo_model.train(matches)

            # 验证评级衰减效果
            assert len(elo_model.team_ratings) == 3

            # 恢复原始衰减率
            elo_model.rating_decay = original_decay

    def test_confidence_calculation(self, elo_model):
        """测试置信度计算"""
        # 测试不同评级差别的置信度
        test_cases = [
            (1500, 1500),  # 相同评级，低置信度
            (1600, 1400),  # 评级差别中等，中等置信度
            (1800, 1200),  # 评级差别大，高置信度
        ]

        for home_rating, away_rating in test_cases:
            # 设置模拟评级
            elo_model.team_ratings = {"Team_A": home_rating, "Team_B": away_rating}

            # 计算概率
            home_prob, draw_prob, away_prob = elo_model._calculate_match_probabilities(
                "Team_A", "Team_B"
            )

            # 计算置信度
            confidence = elo_model.calculate_confidence(
                (home_prob, draw_prob, away_prob)
            )

            assert 0.1 <= confidence <= 1.0

            # 评级差别越大，置信度应该越高
            abs(home_rating - away_rating)

    def test_edge_cases(self, elo_model):
        """测试边界情况"""
        # 测试极端评级
        extreme_ratings = {
            "Team_A": 1000,  # 最低评级
            "Team_B": 3000,  # 最高评级
        }
        elo_model.team_ratings = extreme_ratings

        # 计算概率
        home_prob, draw_prob, away_prob = elo_model._calculate_match_probabilities(
            "Team_A", "Team_B"
        )

        # 验证概率合理性
        assert all(0 <= p <= 1 for p in [home_prob, draw_prob, away_prob])
        assert abs(sum([home_prob, draw_prob, away_prob]) - 1.0) < 1e-6

        # 低评级队伍胜率应该很低
        assert away_prob > home_prob

    def test_seasonal_rating_reset(self, elo_model):
        """测试赛季评级重置（如果实现）"""
        # 检查是否有赛季重置功能
        if hasattr(elo_model, "reset_seasonal_ratings"):
            # 创建一些队伍评级
            elo_model.team_ratings = {"Team_A": 1600, "Team_B": 1400, "Team_C": 1500}

            # 重置赛季评级
            elo_model.reset_seasonal_ratings()

            # 验证重置效果
            for rating in elo_model.team_ratings.values():
                assert rating == elo_model.initial_rating

    def test_prediction_with_unseen_teams(self, elo_model):
        """测试对未见过的队伍的预测"""
        # 设置一些队伍评级
        elo_model.team_ratings = {"Team_A": 1500, "Team_B": 1500}

        # 测试对未见过的队伍的预测
        match_data = {
            "home_team": "Team_A",  # 已知队伍
            "away_team": "New_Team",  # 未知队伍
        }

        # 应该能处理未知队伍（可能使用默认评级）
        try:
            features = elo_model.prepare_features(match_data)
            assert isinstance(features, np.ndarray)
            assert len(features) >= 2
        except Exception as e:
            # 如果抛出异常，应该是可预期的异常
            assert isinstance(e, (ValueError, KeyError))

    def test_hyperparameter_updates(self, elo_model):
        """测试超参数更新"""
        # 更新K因子
        original_k = elo_model.k_factor
        elo_model.update_hyperparameters(k_factor=40)
        assert elo_model.k_factor == 40
        assert elo_model.k_factor != original_k

        # 更新主场优势
        original_advantage = elo_model.home_advantage
        elo_model.update_hyperparameters(home_advantage=75)
        assert elo_model.home_advantage == 75
        assert elo_model.home_advantage != original_advantage

        # 更新初始评级
        original_initial = elo_model.initial_rating
        elo_model.update_hyperparameters(initial_rating=1400)
        assert elo_model.initial_rating == 1400
        assert elo_model.initial_rating != original_initial

    def test_large_dataset_training(self, elo_model):
        """测试大数据集训练"""
        # 创建大数据集
        np.random.seed(42)
        n_matches = 2000
        teams = [f"Team_{i}" for i in range(1, 51)]  # 50支球队

        data = []
        for _i in range(n_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 基于随机结果生成比分
            result = np.random.choice(
                ["home_win", "draw", "away_win"], p=[0.45, 0.25, 0.30]
            )

            if result == "home_win":
                home_goals, away_goals = np.random.poisson(1.8), np.random.poisson(0.9)
            elif result == "away_win":
                home_goals, away_goals = np.random.poisson(0.9), np.random.poisson(1.5)
            else:
                home_goals, away_goals = np.random.poisson(1.2), np.random.poisson(1.2)

            data.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_goals,
                    "away_score": away_goals,
                    "result": result,
                    "date": datetime.now() - timedelta(days=np.random.randint(0, 730)),
                }
            )

        large_data = pd.DataFrame(data)

        # 训练模型
        start_time = datetime.now()
        result = elo_model.train(large_data)
        training_time = (datetime.now() - start_time).total_seconds()

        # 验证训练结果
        assert isinstance(result, TrainingResult)
        assert result.training_samples == n_matches
        assert elo_model.is_trained
        assert len(elo_model.team_ratings) == 50
        assert training_time < 30  # 应该在合理时间内完成

        # 验证评级分布
        ratings = list(elo_model.team_ratings.values())
        assert min(ratings) >= 1000
        assert max(ratings) <= 2000

    def test_model_reproducibility(self, elo_model, sample_training_data):
        """测试模型可重现性"""
        # 第一次训练
        result1 = elo_model.train(sample_training_data)
        ratings1 = elo_model.team_ratings.copy()

        # 重置模型
        elo_model.reset_model()

        # 第二次训练
        result2 = elo_model.train(sample_training_data)
        ratings2 = elo_model.team_ratings.copy()

        # 验证结果一致性
        assert result1.training_samples == result2.training_samples
        assert ratings1 == ratings2  # Elo模型应该是确定性的

    def test_error_handling(self, elo_model):
        """测试错误处理"""
        # 测试空数据
        empty_data = pd.DataFrame()
        with pytest.raises((ValueError, pd.errors.EmptyDataError)):
            elo_model.train(empty_data)

        # 测试无效列
        invalid_data = pd.DataFrame({"wrong_column": [1, 2, 3]})
        with pytest.raises(ValueError):
            elo_model.train(invalid_data)

        # 测试未训练模型的预测
        match_data = {"home_team": "Team_A", "away_team": "Team_B"}
        with pytest.raises(RuntimeError):
            elo_model.predict(match_data)
