import os
"""
预测结果数据模型

存储机器学习模型的预测结果，包括胜负概率、比分预测等。
"""

import json
import math
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import DECIMAL, JSON, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel


class PredictedResult(Enum):
    """预测结果枚举"""

    HOME_WIN = os.getenv("PREDICTIONS_HOME_WIN_25")  # 主队胜
    DRAW = "draw"  # 平局
    AWAY_WIN = os.getenv("PREDICTIONS_AWAY_WIN_26")  # 客队胜


class Predictions(BaseModel):
    """
    预测模型表

    存储各种机器学习模型的预测结果
    """

    __tablename__ = os.getenv("PREDICTIONS___TABLENAME___31")

    # 关联信息
    match_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete = os.getenv("PREDICTIONS_ONDELETE_40")),
        nullable=False,
        comment="比赛ID",
    )

    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="模型名称"
    )

    model_version: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="模型版本"
    )

    # 预测结果
    predicted_result: Mapped[PredictedResult] = mapped_column(
        SQLEnum(PredictedResult), nullable=False, comment="预测结果"
    )

    home_win_probability: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4), nullable=False, comment = os.getenv("PREDICTIONS_COMMENT_57")
    )

    draw_probability: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4), nullable=False, comment="平局概率"
    )

    away_win_probability: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4), nullable=False, comment = os.getenv("PREDICTIONS_COMMENT_65")
    )

    # 置信度和比分
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 4), nullable=True, comment="预测置信度"
    )

    predicted_home_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(4, 2), nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_74")
    )

    predicted_away_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(4, 2), nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_78")
    )

    over_under_prediction: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(4, 2), nullable=True, comment="大小球预测"
    )

    btts_probability: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 4), nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_85")
    )

    # 特征重要性
    feature_importance: Mapped[Optional[JSON]] = mapped_column(
        JSON, nullable=True, comment="特征重要性"
    )

    # 预测时间
    predicted_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, comment="预测时间"
    )

    # 验证相关字段
    actual_result: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_95")
    )

    is_correct: Mapped[Optional[bool]] = mapped_column(
        nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_100")
    )

    verified_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime, nullable=True, comment="验证时间"
    )

    # 特征数据（用于存储预测时使用的特征）
    features_used: Mapped[Optional[JSON]] = mapped_column(
        JSON, nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_108")
    )

    # 预测元数据
    prediction_metadata: Mapped[Optional[JSON]] = mapped_column(
        JSON, nullable=True, comment = os.getenv("PREDICTIONS_COMMENT_112")
    )

    # 关系定义
    match = relationship("Match", back_populates = os.getenv("PREDICTIONS_BACK_POPULATES_116"))

    # 兼容性别名 - 使用方法而不是属性来避免与基类冲突
    def get_created_at(self) -> datetime:
        """兼容性方法：获取预测创建时间"""
        return self.predicted_at

    # 索引定义
    __table_args__ = (
        Index("idx_predictions_match_model", "match_id", "model_name"),
        Index("idx_predictions_predicted_at", "predicted_at"),
        Index("idx_predictions_model_version", "model_name", "model_version"),
    )

    def __repr__(self) -> str:
        return (
            f"<Predictions(id={self.id}, match_id={self.match_id}, "
            f"model = os.getenv("PREDICTIONS_MODEL_132"), result = os.getenv("PREDICTIONS_RESULT_135"))>"
        )

    @property
    def prediction_summary(self) -> str:
        """返回预测摘要"""
        probabilities = [
            ("主队获胜", float(self.home_win_probability)),
            ("平局", float(self.draw_probability)),
            ("客队获胜", float(self.away_win_probability)),
        ]

        # 按概率排序
        probabilities.sort(key=lambda x: x[1], reverse=True)

        return f"{probabilities[0][0]} ({probabilities[0][1]:.1%})"

    @property
    def max_probability(self) -> float:
        """返回最高概率"""
        return max(
            float(self.home_win_probability),
            float(self.draw_probability),
            float(self.away_win_probability),
        )

    @property
    def prediction_confidence_level(self) -> str:
        """返回预测信心等级"""
        max_prob = self.max_probability

        if max_prob >= 0.7:
            return "High"
        elif max_prob >= 0.5:
            return "Medium"
        else:
            return "Low"

    def get_probabilities_dict(self) -> Dict[str, float]:
        """获取概率字典"""
        return {
            "home_win": float(self.home_win_probability),
            "draw": float(self.draw_probability),
            "away_win": float(self.away_win_probability),
        }

    def get_predicted_score(self) -> Optional[str]:
        """获取预测比分"""
        if (
            self.predicted_home_score is not None
            and self.predicted_away_score is not None
        ):
            return f"{self.predicted_home_score:.1f}-{self.predicted_away_score:.1f}"
        return None

    def get_feature_importance_dict(self) -> Optional[Dict[str, float]]:
        """获取特征重要性字典"""
        if self.feature_importance:
            if isinstance(self.feature_importance, str):
                return json.loads(self.feature_importance)
            # 如果是JSON类型，直接返回
            return (
                self.feature_importance
                if isinstance(self.feature_importance, dict)
                else None
            )
        return None

    def get_top_features(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取最重要的特征

        Args:
            top_n: 返回前N个重要特征

        Returns:
            List[Dict[str, Any]]: 特征列表，按重要性降序排列
        """
        feature_importance = self.get_feature_importance_dict()
        if not feature_importance:
            return []

        # 按重要性排序
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )

        return [
            {
                "feature": feature,
                "importance": importance,
                "percentage": f"{importance * 100:.1f}%",
            }
            for feature, importance in sorted_features[:top_n]
        ]

    def calculate_accuracy(self, actual_result: str) -> Dict[str, Any]:
        """
        计算预测准确性

        Args:
            actual_result: 实际比赛结果 ('home_win', 'draw', 'away_win')

        Returns:
            Dict[str, Any]: 准确性分析结果
        """
        # 预测是否正确
        prediction_correct = self.predicted_result.value == actual_result

        # 预测的概率
        actual_predicted_prob = self.get_probabilities_dict()[actual_result]

        # 计算对数损失
        log_loss = -1 * math.log(actual_predicted_prob + 1e-15)

        # 计算布里尔评分 (Brier Score)
        brier_score = 0.0
        probabilities = self.get_probabilities_dict()

        for outcome in ["home_win", "draw", "away_win"]:
            actual_outcome = 1.0 if outcome == actual_result else 0.0
            outcome_prob = probabilities[outcome]
            brier_score += (outcome_prob - actual_outcome) ** 2

        return {
            "prediction_correct": prediction_correct,
            "predicted_probability": actual_predicted_prob,
            "log_loss": log_loss,
            "brier_score": brier_score,
            "confidence_level": self.prediction_confidence_level,
        }

    def get_betting_recommendations(
        self, odds_data: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        基于预测概率和赔率给出投注建议

        Args:
            odds_data: 赔率数据，格式如 {'home_win': 2.1, 'draw': 3.2, 'away_win': 3.8}

        Returns:
            List[Dict[str, Any]]: 投注建议列表
        """
        recommendations = []
        probabilities = self.get_probabilities_dict()

        for outcome, predicted_prob in probabilities.items():
            if outcome in odds_data:
                odds = odds_data[outcome]

                # 计算期望价值
                expected_value = (odds * predicted_prob) - 1.0

                # 计算凯利准则建议的投注比例
                if odds > 1:
                    kelly_fraction = (predicted_prob * odds - 1) / (odds - 1)
                    kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制最大25%
                else:
                    kelly_fraction = 0

                recommendation = {
                    "outcome": outcome,
                    "predicted_probability": predicted_prob,
                    "odds": odds,
                    "expected_value": expected_value,
                    "kelly_fraction": kelly_fraction,
                    "recommendation": (
                        "BET"
                        if expected_value > 0.05
                        else "CONSIDER" if expected_value > 0 else "AVOID"
                    ),
                }

                recommendations.append(recommendation)

        # 按期望价值排序
        recommendations.sort(key=lambda x: float(x["expected_value"]), reverse=True)  # type: ignore

        return recommendations

    def generate_explanation(self) -> Dict[str, Any]:
        """生成预测解释"""
        top_features = self.get_top_features()
        probabilities = self.get_probabilities_dict()

        explanation = {
            "prediction_summary": self.prediction_summary,
            "confidence_level": self.prediction_confidence_level,
            "model_info": {
                "model_name": self.model_name,
                "model_version": self.model_version,
                "predicted_at": str(self.predicted_at) if self.predicted_at else None,
            },
            "probabilities": probabilities,
            "predicted_score": self.get_predicted_score(),
            "key_factors": top_features,
            "additional_predictions": {
                "over_2_5_goals": (
                    float(self.over_under_prediction)
                    if self.over_under_prediction
                    else None
                ),
                "both_teams_score": (
                    float(self.btts_probability) if self.btts_probability else None
                ),
            },
        }

        return explanation

    @classmethod
    def get_match_predictions(cls, session, match_id: int):
        """获取比赛的所有预测"""
        return (
            session.query(cls)
            .filter(cls.match_id == match_id)
            .order_by(cls.predicted_at.desc())
            .all()
        )  # type: ignore

    @classmethod
    def get_latest_prediction(
        cls, session, match_id: int, model_name: Optional[str] = None
    ) -> Optional["Predictions"]:
        """获取最新预测"""
        query = session.query(cls).filter(cls.match_id == match_id)
        if model_name:
            query = query.filter(cls.model_name == model_name)
        return query.order_by(cls.predicted_at.desc()).first()  # type: ignore

    @classmethod
    def get_model_predictions(cls, session, model_name: str, limit: int = 100):
        """获取指定模型的预测历史"""
        return (
            session.query(cls)
            .filter(cls.model_name == model_name)
            .order_by(cls.predicted_at.desc())
            .limit(limit)
            .all()
        )  # type: ignore

    @classmethod
    def calculate_model_accuracy(cls, session, model_name: str, days: int = 30):
        """
        计算模型在指定天数内的准确率

        Args:
            session: 数据库会话
            model_name: 模型名称
            days: 天数

        Returns:
            Dict[str, Any]: 准确性统计
        """

        from sqlalchemy import and_

        from .match import Match

        # 获取指定天数内已结束比赛的预测
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        predictions = (
            session.query(cls)
            .join(Match)
            .filter(
                and_(  # type: ignore
                    cls.model_name == model_name,
                    cls.predicted_at >= cutoff_date,
                    Match.match_status == "finished",
                )
            )
            .all()
        )

        if not predictions:
            return {"total_predictions": 0}

        total_predictions = len(predictions)
        correct_predictions = 0
        total_brier_score = 0.0
        total_log_loss = 0.0

        for prediction in predictions:
            match = prediction.match
            actual_result = match.get_result()

            if actual_result:
                accuracy = prediction.calculate_accuracy(actual_result)
                if accuracy["prediction_correct"]:
                    correct_predictions += 1

                total_brier_score += accuracy["brier_score"]
                total_log_loss += accuracy["log_loss"]

        accuracy_rate = correct_predictions / total_predictions
        avg_brier_score = total_brier_score / total_predictions
        avg_log_loss = total_log_loss / total_predictions

        return {
            "total_predictions": total_predictions,
            "correct_predictions": correct_predictions,
            "accuracy_rate": accuracy_rate,
            "accuracy_percentage": f"{accuracy_rate:.1%}",
            "average_brier_score": avg_brier_score,
            "average_log_loss": avg_log_loss,
            "model_name": model_name,
            "evaluation_period_days": days,
        }
