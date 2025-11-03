"""
泊松分布预测模型
Poisson Distribution Model for Football Match Prediction
"""

import logging
import os
import pickle
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .base_model import BaseModel, PredictionResult, TrainingResult

logger = logging.getLogger(__name__)


class PoissonModel(BaseModel):
    """泊松分布预测模型"""

    def __init__(self, version: str = "1.0"):
        super().__init__("PoissonModel", version)

        # 泊松分布参数 (λ: 进球期望值)
        self.home_advantage = 0.3  # 主场优势
        self.team_attack_strength = {}  # 球队进攻强度
        self.team_defense_strength = {}  # 球队防守强度
        self.average_goals_home = 1.5  # 主队平均进球
        self.average_goals_away = 1.1  # 客队平均进球

        # 训练统计数据
        self.total_matches = 0
        self.team_stats = {}

        # 默认超参数
        self.hyperparameters = {
            "home_advantage": 0.3,
            "min_matches_per_team": 10,
            "decay_factor": 0.9,  # 历史数据衰减因子
            "max_goals": 10,  # 最大考虑进球数
        }

    def prepare_features(self, match_data: dict[str, Any]) -> np.ndarray:
        """
        准备特征 - 泊松模型主要依赖历史统计数据

        Args:
            match_data: 比赛数据，需要包含历史统计

        Returns:
            特征向量 [home_attack, home_defense, away_attack, away_defense]
        """
        home_team = match_data.get("home_team")
        away_team = match_data.get("away_team")

        # 获取球队强度
        home_attack = self.team_attack_strength.get(home_team, 1.0)
        home_defense = self.team_defense_strength.get(home_team, 1.0)
        away_attack = self.team_attack_strength.get(away_team, 1.0)
        away_defense = self.team_defense_strength.get(away_team, 1.0)

        return np.array([home_attack, home_defense, away_attack, away_defense])

    def train(
        self,
        training_data: pd.DataFrame,
        validation_data: pd.DataFrame | None = None,
    ) -> TrainingResult:
        """
        训练泊松分布模型

        Args:
            training_data: 训练数据，必须包含 'home_team', 'away_team', 'home_score', 'away_score'
            validation_data: 验证数据

        Returns:
            训练结果
        """
        start_time = datetime.now()

        if not self.validate_training_data(training_data):
            raise ValueError("Invalid training data")

        # 更新超参数
        self.update_hyperparameters(**self.hyperparameters)

        # 计算基础统计
        self._calculate_team_strengths(training_data)

        # 先设置为已训练状态
        self.is_trained = True

        # 评估模型
        if validation_data is not None:
            metrics = self.evaluate(validation_data)
        else:
            # 使用交叉验证
            metrics = self._cross_validate(training_data)

        self.last_training_time = start_time

        training_time = (datetime.now() - start_time).total_seconds()

        result = TrainingResult(
            model_name=self.model_name,
            model_version=self.model_version,
            accuracy=metrics.get("accuracy", 0.0),
            precision=metrics.get("precision", 0.0),
            recall=metrics.get("recall", 0.0),
            f1_score=metrics.get("f1_score", 0.0),
            confusion_matrix=metrics.get("confusion_matrix", []),
            training_samples=len(training_data),
            validation_samples=len(validation_data)
            if validation_data is not None
            else 0,
            training_time=training_time,
            features_used=[
                "home_attack_strength",
                "home_defense_strength",
                "away_attack_strength",
                "away_defense_strength",
            ],
            hyperparameters=self.hyperparameters.copy(),
            created_at=datetime.now(),
        )

        logger.info(
            f"PoissonModel training completed in {training_time:.2f}s. Accuracy: {result.accuracy:.3f}"
        )

        return result

    def _calculate_team_strengths(self, training_data: pd.DataFrame):
        """
        计算球队攻防强度

        Args:
            training_data: 训练数据
        """
        logger.info("Calculating team strengths from training data")

        # 计算总体平均进球
        total_home_goals = training_data["home_score"].sum()
        total_away_goals = training_data["away_score"].sum()
        total_matches = len(training_data)

        self.average_goals_home = total_home_goals / total_matches
        self.average_goals_away = total_away_goals / total_matches

        # 初始化球队统计
        team_goals_scored = {}
        team_goals_conceded = {}
        team_matches = {}

        # 统计每个球队的进球和失球
        for _, match in training_data.iterrows():
            home_team = match["home_team"]
            away_team = match["away_team"]
            home_score = match["home_score"]
            away_score = match["away_score"]

            # 主队统计
            team_goals_scored[home_team] = (
                team_goals_scored.get(home_team, 0) + home_score
            )
            team_goals_conceded[home_team] = (
                team_goals_conceded.get(home_team, 0) + away_score
            )
            team_matches[home_team] = team_matches.get(home_team, 0) + 1

            # 客队统计
            team_goals_scored[away_team] = (
                team_goals_scored.get(away_team, 0) + away_score
            )
            team_goals_conceded[away_team] = (
                team_goals_conceded.get(away_team, 0) + home_score
            )
            team_matches[away_team] = team_matches.get(away_team, 0) + 1

        # 计算球队攻防强度
        min_matches = self.hyperparameters["min_matches_per_team"]

        for team in team_matches:
            if team_matches[team] >= min_matches:
                matches = team_matches[team]

                # 进攻强度 = 球队平均进球 / 联赛平均进球
                avg_goals_scored = team_goals_scored[team] / matches
                avg_goals_conceded = team_goals_conceded[team] / matches

                # 主客场分别计算
                home_matches = training_data[training_data["home_team"] == team]
                away_matches = training_data[training_data["away_team"] == team]

                if len(home_matches) > 0:
                    home_attack = (
                        home_matches["home_score"].sum() / len(home_matches)
                    ) / self.average_goals_home
                    home_defense = (
                        home_matches["away_score"].sum() / len(home_matches)
                    ) / self.average_goals_away
                else:
                    home_attack = avg_goals_scored / self.average_goals_home
                    home_defense = avg_goals_conceded / self.average_goals_away

                if len(away_matches) > 0:
                    away_attack = (
                        away_matches["away_score"].sum() / len(away_matches)
                    ) / self.average_goals_away
                    away_defense = (
                        away_matches["home_score"].sum() / len(away_matches)
                    ) / self.average_goals_home
                else:
                    away_attack = avg_goals_scored / self.average_goals_away
                    away_defense = avg_goals_conceded / self.average_goals_home

                # 使用加权平均
                self.team_attack_strength[team] = home_attack * 0.6 + away_attack * 0.4
                self.team_defense_strength[team] = (
                    home_defense * 0.6 + away_defense * 0.4
                )

                # 限制在合理范围内
                self.team_attack_strength[team] = np.clip(
                    self.team_attack_strength[team], 0.2, 3.0
                )
                self.team_defense_strength[team] = np.clip(
                    self.team_defense_strength[team], 0.2, 3.0
                )
            else:
                # 数据不足的球队使用默认值
                self.team_attack_strength[team] = 1.0
                self.team_defense_strength[team] = 1.0

        self.total_matches = total_matches
        logger.info(f"Calculated strengths for {len(self.team_attack_strength)} teams")

    def predict(self, match_data: dict[str, Any]) -> PredictionResult:
        """
        预测比赛结果

        Args:
            match_data: 比赛数据

        Returns:
            预测结果
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")

        if not self.validate_prediction_input(match_data):
            raise ValueError("Invalid prediction input")

        home_team = match_data["home_team"]
        away_team = match_data["away_team"]
        match_id = match_data.get("match_id", f"{home_team}_vs_{away_team}")

        # 计算期望进球数
        home_expected_goals = self._calculate_expected_goals(
            home_team, away_team, is_home=True
        )
        away_expected_goals = self._calculate_expected_goals(
            away_team, home_team, is_home=False
        )

        # 计算概率分布
        home_win_prob, draw_prob, away_win_prob = self._calculate_match_probabilities(
            home_expected_goals, away_expected_goals
        )

        # 确定预测结果
        probabilities = (home_win_prob, draw_prob, away_win_prob)
        predicted_outcome = self.get_outcome_from_probabilities(probabilities)
        confidence = self.calculate_confidence(probabilities)

        result = PredictionResult(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            predicted_outcome=predicted_outcome,
            confidence=confidence,
            model_name=self.model_name,
            model_version=self.model_version,
            created_at=datetime.now(),
        )

        logger.debug(
            f"Prediction for {home_team} vs {away_team}: {predicted_outcome} (confidence: {confidence:.3f})"
        )

        return result

    def _calculate_expected_goals(
        self, team: str, opponent: str, is_home: bool
    ) -> float:
        """
        计算期望进球数

        Args:
            team: 球队
            opponent: 对手
            is_home: 是否主场

        Returns:
            期望进球数
        """
        team_attack = self.team_attack_strength.get(team, 1.0)
        opponent_defense = self.team_defense_strength.get(opponent, 1.0)

        if is_home:
            base_avg = self.average_goals_home
            home_advantage = self.hyperparameters["home_advantage"]
        else:
            base_avg = self.average_goals_away
            home_advantage = 0

        expected_goals = (
            base_avg * team_attack * opponent_defense * (1 + home_advantage)
        )

        return max(expected_goals, 0.1)  # 确保至少0.1

    def _calculate_match_probabilities(
        self, home_expected: float, away_expected: float
    ) -> tuple[float, float, float]:
        """
        计算比赛结果概率

        Args:
            home_expected: 主队期望进球
            away_expected: 客队期望进球

        Returns:
            (主胜概率, 平局概率, 客胜概率)
        """
        max_goals = self.hyperparameters["max_goals"]

        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0

        # 计算所有可能的比分组合的概率
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                # 使用泊松分布计算概率
                home_prob = stats.poisson.pmf(home_goals, home_expected)
                away_prob = stats.poisson.pmf(away_goals, away_expected)
                combined_prob = home_prob * away_prob

                if home_goals > away_goals:
                    home_win_prob += combined_prob
                elif home_goals == away_goals:
                    draw_prob += combined_prob
                else:
                    away_win_prob += combined_prob

        # 确保概率总和为1
        total_prob = home_win_prob + draw_prob + away_win_prob
        if total_prob > 0:
            home_win_prob /= total_prob
            draw_prob /= total_prob
            away_win_prob /= total_prob

        return home_win_prob, draw_prob, away_win_prob

    def predict_proba(self, match_data: dict[str, Any]) -> tuple[float, float, float]:
        """
        预测概率分布

        Args:
            match_data: 比赛数据

        Returns:
            (主胜概率, 平局概率, 客胜概率)
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")

        home_team = match_data["home_team"]
        away_team = match_data["away_team"]

        home_expected_goals = self._calculate_expected_goals(
            home_team, away_team, is_home=True
        )
        away_expected_goals = self._calculate_expected_goals(
            away_team, home_team, is_home=False
        )

        return self._calculate_match_probabilities(
            home_expected_goals, away_expected_goals
        )

    def evaluate(self, test_data: pd.DataFrame) -> dict[str, float]:
        """
        评估模型性能

        Args:
            test_data: 测试数据

        Returns:
            评估指标
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before evaluation")

        predictions = []
        actuals = []

        for _, match in test_data.iterrows():
            match_data = {
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "match_id": f"{match['home_team']}_vs_{match['away_team']}",
            }

            try:
                prediction = self.predict(match_data)
                predictions.append(prediction.predicted_outcome)
                actuals.append(match["result"])
            except Exception as e:
                logger.warning(f"Failed to predict match {match_data['match_id']}: {e}")
                continue

        if not predictions:
            logger.error("No valid predictions made")
            return {}

        # 计算评估指标
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
        )

        accuracy = accuracy_score(actuals, predictions)
        precision = precision_score(
            actuals, predictions, average="weighted", zero_division=0
        )
        recall = recall_score(actuals, predictions, average="weighted", zero_division=0)
        f1 = f1_score(actuals, predictions, average="weighted", zero_division=0)

        cm = confusion_matrix(actuals, predictions).tolist()

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "confusion_matrix": cm,
            "total_predictions": len(predictions),
        }

        logger.info(f"Model evaluation: accuracy={accuracy:.3f}, f1={f1:.3f}")

        return metrics

    def _cross_validate(
        self, training_data: pd.DataFrame, folds: int = 5
    ) -> dict[str, float]:
        """
        交叉验证

        Args:
            training_data: 训练数据
            folds: 折数

        Returns:
            平均评估指标
        """
        from sklearn.model_selection import KFold

        kf = KFold(n_splits=folds, shuffle=True, random_state=42)
        fold_metrics = []

        for fold, (train_idx, val_idx) in enumerate(kf.split(training_data)):
            train_fold = training_data.iloc[train_idx]
            val_fold = training_data.iloc[val_idx]

            # 临时保存当前状态
            temp_strengths = self.team_attack_strength.copy()
            temp_defense = self.team_defense_strength.copy()
            temp_trained = self.is_trained

            # 训练和评估
            self._calculate_team_strengths(train_fold)
            self.is_trained = True
            metrics = self.evaluate(val_fold)
            fold_metrics.append(metrics)

            # 恢复状态
            self.team_attack_strength = temp_strengths
            self.team_defense_strength = temp_defense
            self.is_trained = temp_trained

            logger.info(f"Fold {fold + 1}: accuracy={metrics.get('accuracy', 0):.3f}")

        # 计算平均指标
        avg_metrics = {}
        if fold_metrics:
            for key in ["accuracy", "precision", "recall", "f1_score"]:
                values = [m.get(key, 0) for m in fold_metrics]
                avg_metrics[key] = np.mean(values)
                avg_metrics[f"{key}_std"] = np.std(values)

        return avg_metrics

    def save_model(self, file_path: str) -> bool:
        """
        保存模型

        Args:
            file_path: 模型文件路径

        Returns:
            是否保存成功
        """
        try:
            model_data = {
                "model_name": self.model_name,
                "model_version": self.model_version,
                "is_trained": self.is_trained,
                "home_advantage": self.home_advantage,
                "team_attack_strength": self.team_attack_strength,
                "team_defense_strength": self.team_defense_strength,
                "average_goals_home": self.average_goals_home,
                "average_goals_away": self.average_goals_away,
                "total_matches": self.total_matches,
                "hyperparameters": self.hyperparameters,
                "training_history": self.training_history,
                "last_training_time": self.last_training_time,
            }

            with open(file_path, "wb") as f:
                pickle.dump(model_data, f)

            logger.info(f"Model saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, file_path: str) -> bool:
        """
        加载模型

        Args:
            file_path: 模型文件路径

        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Model file not found: {file_path}")
                return False

            with open(file_path, "rb") as f:
                model_data = pickle.load(f)

            # 恢复模型状态
            self.model_name = model_data["model_name"]
            self.model_version = model_data["model_version"]
            self.is_trained = model_data["is_trained"]
            self.home_advantage = model_data["home_advantage"]
            self.team_attack_strength = model_data["team_attack_strength"]
            self.team_defense_strength = model_data["team_defense_strength"]
            self.average_goals_home = model_data["average_goals_home"]
            self.average_goals_away = model_data["average_goals_away"]
            self.total_matches = model_data["total_matches"]
            self.hyperparameters = model_data["hyperparameters"]
            self.training_history = model_data["training_history"]
            self.last_training_time = model_data["last_training_time"]

            logger.info(f"Model loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
