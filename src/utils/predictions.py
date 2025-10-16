"""
预测工具模块
用于处理和验证足球预测数据
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import statistics


class PredictionValidator:
    """预测数据验证器"""

    @staticmethod
    def validate_probabilities(home_win: float, draw: float, away_win: float) -> bool:
        """
        验证概率值是否有效

        Args:
    "home_win": 主胜概率
    "draw": 平局概率
    "away_win": 客胜概率

        Returns:
            验证结果
        """
        # 概率值必须在0-1之间
        if not all(0 <= p <= 1 for p in [home_win, draw, away_win]):
            return False

        # 概率总和应该等于1（允许小的误差）
        total = home_win + draw + away_win
        return abs(total - 1.0) < 0.001  # 允许0.1%的误差

    @staticmethod
    def validate_confidence(confidence: float) -> bool:
        """
        验证置信度

        Args:
    "confidence": 置信度值

        Returns:
            验证结果
        """
        return 0 <= confidence <= 1


class PredictionAnalyzer:
    """预测分析器"""

    def __init__(self):
        self.predictions_history: List[Dict] = []

    def add_prediction(self, prediction: Dict) -> None:
        """
        添加预测记录

        Args:
    "prediction": 预测数据
        """
        # 验证预测数据
        if self._validate_prediction(prediction):
            prediction['timestamp'] = datetime.now()
            self.predictions_history.append(prediction)

    def get_accuracy(self) -> Optional[float]:
        """
        计算预测准确率

        Returns:
            准确率（0-1之间）
        """
        if not self.predictions_history:
            return None

        correct = 0
        total = 0

        for pred in self.predictions_history:
            if 'predicted' in pred and 'actual' in pred:
                total += 1
                if pred['predicted'] == pred['actual']:
                    correct += 1

        return correct / total if total > 0 else 0

    def get_most_predicted(self) -> Optional[str]:
        """
        获取最常预测的结果

        Returns:
            最常预测的结果
        """
        if not self.predictions_history:
            return None

        outcomes = [p.get('predicted') for p in self.predictions_history if 'predicted' in p]
        if not outcomes:
            return None

        return statistics.mode(outcomes)

    def _validate_prediction(self, prediction: Dict) -> bool:
        """验证预测数据格式"""
        required_fields = ['match_id', 'predicted']
        return all(field in prediction for field in required_fields)


class PredictionFormatter:
    """预测数据格式化器"""

    @staticmethod
    def format_probability(probability: float, percentage: bool = True) -> str:
        """
        格式化概率显示

        Args:
    "probability": 概率值
    "percentage": 是否显示为百分比

        Returns:
            格式化后的字符串
        """
        if percentage:
            return f"{probability * 100:.1f}%"
        else:
            return f"{probability:.3f}"

    @staticmethod
    def format_prediction_summary(prediction: Dict) -> str:
        """
        格式化预测摘要

        Args:
    "prediction": 预测数据

        Returns:
            格式化后的摘要
        """
        lines = []
        lines.append(f"比赛ID: {prediction.get('match_id', 'N/A')}")

        if 'probabilities' in prediction:
            probs = prediction['probabilities']
            lines.append("概率分布:")
            lines.append(f"  主胜: {PredictionFormatter.format_probability(probs.get('home_win', 0))}")
            lines.append(f"  平局: {PredictionFormatter.format_probability(probs.get('draw', 0))}")
            lines.append(f"  客胜: {PredictionFormatter.format_probability(probs.get('away_win', 0))}")

        if 'predicted' in prediction:
            lines.append(f"预测结果: {prediction['predicted']}")

        if 'confidence' in prediction:
            lines.append(f"置信度: {PredictionFormatter.format_probability(prediction['confidence'])}")

        return "\n".join(lines)
