"""
ELO评分预测模型
ELO Rating Model for Football Match Prediction
"""

import logging
import os
import pickle
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from .base_model import BaseModel, PredictionResult, TrainingResult

logger = logging.getLogger(__name__)


class EloModel(BaseModel):
    """ELO评分预测模型"""

    def __init__(self, version: str = "1.0"):
        super().__init__("EloModel", version)

        # ELO评分系统参数
        self.initial_elo = 1500.0  # 初始ELO评分
        self.k_factor = 32.0  # K因子
        self.home_advantage = 100.0  # 主场优势（ELO分数）
        self.team_elos = {}  # 球队ELO评分
        self.team_matches = {}  # 球队比赛场次

        # 历史记录
        self.elo_history = {}  # ELO变化历史

        # 默认超参数
        self.hyperparameters = {
            "initial_elo": 1500.0,
            "k_factor": 32.0,
            "home_advantage": 100.0,
            "min_matches_per_team": 10,
            "elo_decay_factor": 0.95,  # ELO衰减因子（用于长期不活跃的球队）
            "max_elo_difference": 400.0,  # 最大ELO差异限制
        }

    def prepare_features(self,
    match_data: dict[str,
    Any]) -> np.ndarray:
        """
        准备ELO特征

        Args:
            match_data: 比赛数据

        Returns:
            特征向量 [home_elo,
    away_elo,
    elo_difference,
    home_advantage_adjusted]
        """
        home_team = match_data.get("home_team")
        away_team = match_data.get("away_team")

        home_elo = self.team_elos.get(home_team,
    self.initial_elo)
        away_elo = self.team_elos.get(away_team,
    self.initial_elo)
        elo_diff = home_elo - away_elo
        home_advantage_adj = self.hyperparameters["home_advantage"]

        return np.array([home_elo,
    away_elo,
    elo_diff,
    home_advantage_adj])

    def train(
        self,
    training_data: pd.DataFrame,
    validation_data: pd.DataFrame | None = None,
    ) -> TrainingResult:
        """
        训练ELO模型（计算历史ELO评分）

        Args:
            training_data: 训练数据，必须包含 'home_team',
    'away_team',
    'home_score',
    'away_score',
    'result'
            validation_data: 验证数据

        Returns:
            训练结果
        """
        start_time = datetime.now()

        if not self.validate_training_data(training_data):
            raise ValueError("Invalid training data")

        # 更新超参数
        self.update_hyperparameters(**self.hyperparameters)

        # 初始化所有球队的ELO评分
        self._initialize_team_elos(training_data)

        # 按时间顺序处理比赛（如果有日期信息）
        if "date" in training_data.columns:
            training_data = training_data.sort_values("date")

        # 逐场比赛更新ELO评分
        for _,
    match in training_data.iterrows():
            self._update_elo_after_match(match)

        # 评估模型
        if validation_data is not None:
            metrics = self.evaluate(validation_data)
        else:
            # 使用交叉验证
            metrics = self._cross_validate(training_data)

        self.is_trained = True
        self.last_training_time = start_time

        training_time = (datetime.now() - start_time).total_seconds()

        result = TrainingResult(
            model_name=self.model_name,
    model_version=self.model_version,
    accuracy=metrics.get("accuracy",
    0.0),
    
            precision=metrics.get("precision", 0.0),
            recall=metrics.get("recall", 0.0),
            f1_score=metrics.get("f1_score", 0.0),
            confusion_matrix=metrics.get("confusion_matrix", []),
            training_samples=len(training_data),
    validation_samples=(
                len(validation_data) if validation_data is not None else 0
            ),
    training_time=training_time,
    features_used=["home_elo",
    "away_elo",
    "elo_difference",
    "home_advantage"],
    
            hyperparameters=self.hyperparameters.copy(),
            created_at=datetime.now(),
        )

        logger.info(
            f"EloModel training completed in {training_time:.2f}s. Accuracy: {result.accuracy:.3f}"
        )

        return result

    def _initialize_team_elos(self, training_data: pd.DataFrame):
        """
        初始化所有球队的ELO评分

        Args:
            training_data: 训练数据
        """
        # 获取所有独特的球队
        all_teams = set(training_data["home_team"].unique()) | set(
            training_data["away_team"].unique()
        )

        # 初始化ELO评分
        for team in all_teams:
            self.team_elos[team] = self.hyperparameters["initial_elo"]
            self.team_matches[team] = 0
            self.elo_history[team] = [self.hyperparameters["initial_elo"]]

        logger.info(f"Initialized ELO ratings for {len(all_teams)} teams")

    def _update_elo_after_match(self,
    match: pd.Series):
        """
        根据比赛结果更新ELO评分

        Args:
            match: 比赛数据
        """
        home_team = match["home_team"]
        away_team = match["away_team"]
        home_score = match["home_score"]
        away_score = match["away_score"]

        # 获取当前ELO评分
        home_elo = self.team_elos[home_team]
        away_elo = self.team_elos[away_team]

        # 计算期望得分
        home_expected = self._calculate_expected_score(home_elo,
    away_elo,
    is_home=True)
        away_expected = self._calculate_expected_score(
            away_elo,
    home_elo,
    is_home=False
        )

        # 计算实际得分
        home_actual, away_actual = self._get_actual_scores(home_score,
    away_score)

        # 更新ELO评分
        k_factor = self.hyperparameters["k_factor"]
        new_home_elo = home_elo + k_factor * (home_actual - home_expected)
        new_away_elo = away_elo + k_factor * (away_actual - away_expected)

        # 限制ELO变化
        max_change = self.hyperparameters["k_factor"] * 1.5
        new_home_elo = np.clip(
            new_home_elo,
    home_elo - max_change,
    home_elo + max_change
        )
        new_away_elo = np.clip(
            new_away_elo,
    away_elo - max_change,
    away_elo + max_change
        )

        # 更新评分
        self.team_elos[home_team] = new_home_elo
        self.team_elos[away_team] = new_away_elo

        # 更新比赛场次
        self.team_matches[home_team] += 1
        self.team_matches[away_team] += 1

        # 记录历史
        self.elo_history[home_team].append(new_home_elo)
        self.elo_history[away_team].append(new_away_elo)

        logger.debug(
            f"ELO update: {home_team} {home_elo:.0f} -> {new_home_elo:.0f}, "
            f"{away_team} {away_elo:.0f} -> {new_away_elo:.0f}"
        )

    def _calculate_expected_score(
        self,
    team_elo: float,
    opponent_elo: float,
    is_home: bool
    ) -> float:
        """
        计算期望得分

        Args:
            team_elo: 球队ELO评分
            opponent_elo: 对手ELO评分
            is_home: 是否主场

        Returns:
            期望得分 (0-1)
        """
        home_advantage = self.hyperparameters["home_advantage"] if is_home else 0
        elo_difference = team_elo + home_advantage - opponent_elo

        # 限制ELO差异
        max_diff = self.hyperparameters["max_elo_difference"]
        elo_difference = np.clip(elo_difference,
    -max_diff,
    max_diff)

        # ELO公式：期望得分 = 1 / (1 + 10^((对手ELO - 己方ELO) / 400))
        expected_score = 1.0 / (1.0 + pow(10.0,
    -elo_difference / 400.0))

        return expected_score

    def _get_actual_scores(
        self,
    home_score: int,
    away_score: int
    ) -> tuple[float,
    float]:
        """
        获取实际得分

        Args:
            home_score: 主队进球
            away_score: 客队进球

        Returns:
            (主队得分, 客队得分)
        """
        if home_score > away_score:
            return 1.0, 0.0  # 主胜
        elif home_score < away_score:
            return 0.0, 1.0  # 客胜
        else:
            return 0.5, 0.5  # 平局

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

        # 获取ELO评分
        home_elo = self.team_elos.get(home_team,
    self.initial_elo)
        away_elo = self.team_elos.get(away_team,
    self.initial_elo)

        # 计算期望得分
        home_expected = self._calculate_expected_score(home_elo,
    away_elo,
    is_home=True)
        away_expected = self._calculate_expected_score(
            away_elo,
    home_elo,
    is_home=False
        )

        # 转换为胜平负概率
        home_win_prob,
    draw_prob,
    away_win_prob = (
            self._convert_expected_scores_to_probabilities(
                home_expected,
    away_expected,
    home_elo - away_elo
            )
        )

        # 确定预测结果
        probabilities = (home_win_prob,
    draw_prob,
    away_win_prob)
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
            f"ELO prediction for {home_team}({home_elo:.0f}) vs {away_team}({away_elo:.0f}): "
            f"{predicted_outcome} (confidence: {confidence:.3f})"
        )

        return result

    def _convert_expected_scores_to_probabilities(
        self,
    home_expected: float,
    away_expected: float,
    elo_difference: float
    ) -> tuple[float,
    float,
    float]:
        """
        将期望得分转换为胜平负概率

        Args:
            home_expected: 主队期望得分
            away_expected: 客队期望得分
            elo_difference: ELO差异

        Returns:
            (主胜概率, 平局概率, 客胜概率)
        """
        # 基础概率（从期望得分）
        home_win_prob = home_expected
        away_win_prob = away_expected

        # 根据ELO差异调整平局概率
        # ELO差异越小，平局概率越高
        draw_factor = 1.0 - min(abs(elo_difference) / 400.0,
    0.8)
        base_draw_prob = 0.25 * draw_factor

        # 调整胜负概率，为平局概率留出空间
        total_win_prob = home_win_prob + away_win_prob
        if total_win_prob > 0:
            scaling_factor = (1.0 - base_draw_prob) / total_win_prob
            home_win_prob *= scaling_factor
            away_win_prob *= scaling_factor

        # 确保概率合理
        home_win_prob = np.clip(home_win_prob,
    0.05,
    0.9)
        draw_prob = np.clip(base_draw_prob,
    0.05,
    0.5)
        away_win_prob = np.clip(away_win_prob,
    0.05,
    0.9)

        # 归一化
        total_prob = home_win_prob + draw_prob + away_win_prob
        if total_prob > 0:
            home_win_prob /= total_prob
            draw_prob /= total_prob
            away_win_prob /= total_prob

        return home_win_prob,
    draw_prob,
    away_win_prob

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

        home_elo = self.team_elos.get(home_team,
    self.initial_elo)
        away_elo = self.team_elos.get(away_team,
    self.initial_elo)

        home_expected = self._calculate_expected_score(home_elo,
    away_elo,
    is_home=True)
        away_expected = self._calculate_expected_score(
            away_elo,
    home_elo,
    is_home=False
        )

        return self._convert_expected_scores_to_probabilities(
            home_expected,
    away_expected,
    home_elo - away_elo
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

        accuracy = accuracy_score(actuals,
    predictions)
        precision = precision_score(
            actuals,
    predictions,
    average="weighted",
    zero_division=0
        )
        recall = recall_score(actuals,
    predictions,
    average="weighted",
    zero_division=0)
        f1 = f1_score(actuals,
    predictions,
    average="weighted",
    zero_division=0)

        cm = confusion_matrix(actuals, predictions).tolist()

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "confusion_matrix": cm,
            "total_predictions": len(predictions),
        }

        logger.info(f"ELO model evaluation: accuracy={accuracy:.3f}, f1={f1:.3f}")

        return metrics

    def _cross_validate(
        self,
    training_data: pd.DataFrame,
    folds: int = 5
    ) -> dict[str,
    float]:
        """
        交叉验证

        Args:
            training_data: 训练数据
            folds: 折数

        Returns:
            平均评估指标
        """
        from sklearn.model_selection import KFold

        kf = KFold(n_splits=folds,
    shuffle=True,
    random_state=42)
        fold_metrics = []

        for fold, (train_idx, val_idx) in enumerate(kf.split(training_data)):
            train_fold = training_data.iloc[train_idx]
            val_fold = training_data.iloc[val_idx]

            # 临时保存当前状态
            temp_elos = self.team_elos.copy()
            temp_matches = self.team_matches.copy()
            temp_history = self.elo_history.copy()
            temp_trained = self.is_trained

            # 训练和评估
            self._initialize_team_elos(train_fold)
            for _, match in train_fold.iterrows():
                self._update_elo_after_match(match)
            self.is_trained = True
            metrics = self.evaluate(val_fold)
            fold_metrics.append(metrics)

            # 恢复状态
            self.team_elos = temp_elos
            self.team_matches = temp_matches
            self.elo_history = temp_history
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

    def get_team_elo(self,
    team: str) -> float:
        """
        获取球队ELO评分

        Args:
            team: 球队名称

        Returns:
            ELO评分
        """
        return self.team_elos.get(team,
    self.initial_elo)

    def get_team_elo_history(self,
    team: str) -> list[float]:
        """
        获取球队ELO历史

        Args:
            team: 球队名称

        Returns:
            ELO历史列表
        """
        return self.elo_history.get(team,
    [self.initial_elo])

    def get_top_teams(self,
    limit: int = 20) -> list[tuple[str,
    float]]:
        """
        获取ELO评分最高的球队

        Args:
            limit: 返回数量

        Returns:
            (球队名称,
    ELO评分) 列表，按评分降序排列
        """
        sorted_teams = sorted(self.team_elos.items(),
    key=lambda x: x[1],
    reverse=True)
        return sorted_teams[:limit]

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
                "initial_elo": self.initial_elo,
                "team_elos": self.team_elos,
                "team_matches": self.team_matches,
                "elo_history": self.elo_history,
                "hyperparameters": self.hyperparameters,
                "training_history": self.training_history,
                "last_training_time": self.last_training_time,
            }

            with open(file_path, "wb") as f:
                pickle.dump(model_data, f)

            logger.info(f"ELO model saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save ELO model: {e}")
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
            self.initial_elo = model_data["initial_elo"]
            self.team_elos = model_data["team_elos"]
            self.team_matches = model_data["team_matches"]
            self.elo_history = model_data["elo_history"]
            self.hyperparameters = model_data["hyperparameters"]
            self.training_history = model_data["training_history"]
            self.last_training_time = model_data["last_training_time"]

            logger.info(f"ELO model loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load ELO model: {e}")
            return False

    def validate_training_data(self,
    training_data: pd.DataFrame) -> bool:
        """
        验证训练数据

        Args:
            training_data: 训练数据

        Returns:
            是否有效
        """
        if training_data.empty:
            logger.error("Training data is empty")
            return False

        required_columns = [
            "home_team",
    "away_team",
    "home_score",
    
            "away_score",
            "result",
        ]
        for col in required_columns:
            if col not in training_data.columns:
                logger.error(f"Missing required column: {col}")
                return False

        # 检查数据质量
        if training_data.isnull().any().any():
            logger.warning("Training data contains null values")

        # 检查样本数量
        min_samples = 50  # ELO模型需要的最小样本数
        if len(training_data) < min_samples:
            logger.warning(
                f"Training data has only {len(training_data)} samples,
    which may be insufficient"
            )

        # 检查比分数据
        if (training_data["home_score"] < 0).any() or (
            training_data["away_score"] < 0
        ).any():
            logger.error("Negative goals found in training data")
            return False

        return True
