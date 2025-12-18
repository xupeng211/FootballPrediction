"""预测结果验证器的单元测试.

使用 TDD 方法开发 PredictionResultValidator 类.
测试驱动开发：先写测试，再写实现代码.
"""

import pytest

# 假设我们要开发的类将在以下位置
from src.utils.prediction_validator import PredictionResultValidator, ValidationError


class TestPredictionResultValidator:
    """预测结果验证器测试类."""

    def setup_method(self):
        """每个测试方法执行前的设置."""
        self.validator = PredictionResultValidator()

    def test_validate_correct_home_win_prediction(self):
        """测试场景: 预测主队获胜，实际也是主队获胜.

        业务需求: 能够正确识别准确的主队获胜预测.
        """
        # Given: 预测结果为主队获胜，实际比赛结果为2-1主队获胜
        predicted_result = "home_win"
        actual_result = "2-1"

        # When: 执行验证
        is_correct = self.validator.validate_prediction(predicted_result, actual_result)

        # Then: 预测应该是正确的
        assert is_correct is True

    def test_validate_incorrect_home_win_prediction(self):
        """测试场景: 预测主队获胜，但是实际是客队获胜.

        业务需求: 能够正确识别错误的主队获胜预测.
        """
        # Given: 预测结果为主队获胜，实际比赛结果为1-2客队获胜
        predicted_result = "home_win"
        actual_result = "1-2"

        # When: 执行验证
        is_correct = self.validator.validate_prediction(predicted_result, actual_result)

        # Then: 预测应该是错误的
        assert is_correct is False

    def test_validate_correct_draw_prediction(self):
        """测试场景: 预测平局，实际也是平局.

        业务需求: 能够正确识别准确的平局预测.
        """
        # Given: 预测结果为平局，实际比赛结果为1-1平局
        predicted_result = "draw"
        actual_result = "1-1"

        # When: 执行验证
        is_correct = self.validator.validate_prediction(predicted_result, actual_result)

        # Then: 预测应该是正确的
        assert is_correct is True

    def test_validate_incorrect_draw_prediction(self):
        """测试场景: 预测平局，但是实际有胜负结果.

        业务需求: 能够正确识别错误的平局预测.
        """
        # Given: 预测结果为平局，实际比赛结果为2-0主队获胜
        predicted_result = "draw"
        actual_result = "2-0"

        # When: 执行验证
        is_correct = self.validator.validate_prediction(predicted_result, actual_result)

        # Then: 预测应该是错误的
        assert is_correct is False

    def test_validate_away_win_with_score_format(self):
        """测试场景: 使用比分格式进行客队获胜预测验证.

        业务需求: 支持比分格式的实际结果输入.
        """
        # Given: 预测结果为客队获胜，实际比赛结果为0-2客队获胜
        predicted_result = "away_win"
        actual_result = "0-2"

        # When: 执行验证
        is_correct = self.validator.validate_prediction(predicted_result, actual_result)

        # Then: 预测应该是正确的
        assert is_correct is True

    def test_validate_with_invalid_score_format(self):
        """测试场景: 使用无效的比分格式.

        业务需求: 对无效输入格式应该抛出ValidationError异常.
        """
        # Given: 无效的比分格式
        predicted_result = "home_win"
        actual_result = "invalid-score"

        # When & Then: 应该抛出ValidationError
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate_prediction(predicted_result, actual_result)

        assert "无效的比分格式" in str(exc_info.value)

    def test_validate_with_empty_inputs(self):
        """测试场景: 空输入验证.

        业务需求: 对空输入应该进行适当的验证处理.
        """
        # Given: 空的预测结果
        predicted_result = ""
        actual_result = "2-1"

        # When & Then: 应该抛出ValidationError
        with pytest.raises(ValidationError):
            self.validator.validate_prediction(predicted_result, actual_result)

    def test_get_validation_statistics(self):
        """测试场景: 获取验证统计信息.

        业务需求: 能够跟踪验证统计信息，包括总验证次数和准确率.
        """
        # Given: 执行几次验证
        self.validator.validate_prediction("home_win", "2-1")  # 正确
        self.validator.validate_prediction("away_win", "1-2")  # 正确
        self.validator.validate_prediction("draw", "2-1")  # 错误

        # When: 获取统计信息
        stats = self.validator.get_statistics()

        # Then: 统计信息应该正确
        assert stats["total_validations"] == 3
        assert stats["correct_predictions"] == 2
        assert stats["accuracy"] == 2 / 3

    def test_reset_statistics(self):
        """测试场景: 重置验证统计信息.

        业务需求: 能够重置统计计数器.
        """
        # Given: 执行一些验证操作
        self.validator.validate_prediction("home_win", "2-1")

        # When: 重置统计
        self.validator.reset_statistics()

        # Then: 统计信息应该被重置
        stats = self.validator.get_statistics()
        assert stats["total_validations"] == 0
        assert stats["correct_predictions"] == 0
        assert stats["accuracy"] == 0.0
