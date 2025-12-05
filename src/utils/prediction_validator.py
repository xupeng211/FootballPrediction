"""预测结果验证器.

使用 TDD 方法开发的足球预测结果验证器.
用于验证预测的足球比赛结果是否与实际结果一致.
"""

import re
from typing import Dict, Any, Literal

# 常量定义，避免魔法值
VALID_PREDICTIONS = {"home_win", "away_win", "draw"}
HOME_WIN = "home_win"
AWAY_WIN = "away_win"
DRAW = "draw"

# 比分正则表达式模式
SCORE_PATTERN = r'^(\d+)-(\d+)$'


class ValidationError(Exception):
    """验证错误异常类.

    当输入参数格式无效或不符合预期时抛出此异常.
    """
    pass


class PredictionResultValidator:
    """预测结果验证器类.

    用于验证足球预测结果与实际比赛结果的一致性.
    支持多种预测结果格式和比分格式的验证.
    提供统计功能以跟踪验证准确率.
    """

    def __init__(self) -> None:
        """初始化验证器."""
        self._total_validations: int = 0
        self._correct_predictions: int = 0

    def validate_prediction(self, predicted_result: str, actual_result: str) -> bool:
        """验证预测结果是否正确.

        Args:
            predicted_result: 预测的结果，格式如 "home_win", "away_win", "draw"
            actual_result: 实际的比赛结果，格式如 "2-1", "1-1", "0-2"

        Returns:
            bool: 预测是否正确

        Raises:
            ValidationError: 当输入格式无效时
        """
        # 更新统计计数
        self._total_validations += 1

        # 验证输入有效性
        self._validate_inputs(predicted_result, actual_result)

        # 解析实际比分并确定结果类型
        actual_outcome = self._parse_score_to_outcome(actual_result)

        # 比较预测结果与实际结果
        is_correct = predicted_result == actual_outcome

        # 更新正确预测计数
        if is_correct:
            self._correct_predictions += 1

        return is_correct

    def _validate_inputs(self, predicted_result: str, actual_result: str) -> None:
        """验证输入参数的有效性.

        Args:
            predicted_result: 预测结果字符串
            actual_result: 实际结果字符串

        Raises:
            ValidationError: 当输入无效时抛出
        """
        if not predicted_result or not isinstance(predicted_result, str):
            raise ValidationError(
                f"预测结果不能为空且必须是字符串，但得到: {type(predicted_result).__name__}"
            )

        if not actual_result or not isinstance(actual_result, str):
            raise ValidationError(
                f"实际结果不能为空且必须是字符串，但得到: {type(actual_result).__name__}"
            )

        if predicted_result not in VALID_PREDICTIONS:
            raise ValidationError(
                f"无效的预测结果格式: '{predicted_result}'. "
                f"支持的格式: {sorted(VALID_PREDICTIONS)}"
            )

    def _parse_score_to_outcome(self, score: str) -> Literal["home_win", "away_win", "draw"]:
        """将比分字符串转换为结果类型.

        Args:
            score: 比分字符串，如 "2-1", "1-1", "0-2"

        Returns:
            str: 结果类型 "home_win", "away_win", "draw"

        Raises:
            ValidationError: 当比分格式无效时
        """
        cleaned_score = score.strip()
        match = re.match(SCORE_PATTERN, cleaned_score)

        if not match:
            raise ValidationError(
                f"无效的比分格式: '{cleaned_score}'. "
                f"期望格式为 '主队得分-客队得分'，例如 '2-1', '1-1', '0-2'"
            )

        home_score = int(match.group(1))
        away_score = int(match.group(2))

        if home_score > away_score:
            return HOME_WIN
        elif away_score > home_score:
            return AWAY_WIN
        else:
            return DRAW

    def get_statistics(self) -> dict[str, Any]:
        """获取验证统计信息.

        Returns:
            Dict[str, Any]: 包含以下字段的字典:
                - total_validations: 总验证次数
                - correct_predictions: 正确预测次数
                - accuracy: 预测准确率 (0.0 到 1.0)
        """
        accuracy: float = 0.0
        if self._total_validations > 0:
            accuracy = self._correct_predictions / self._total_validations

        return {
            "total_validations": self._total_validations,
            "correct_predictions": self._correct_predictions,
            "accuracy": accuracy
        }

    def reset_statistics(self) -> None:
        """重置验证统计信息."""
        self._total_validations = 0
        self._correct_predictions = 0
