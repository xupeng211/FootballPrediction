"""
TDD实践：预测工具测试
遵循 TDD 原则：先写测试，再实现功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

# Step 1: Red - 写失败的测试
def test_prediction_validator_valid_probabilities():
    """测试验证有效的概率值"""
    from src.utils.predictions import PredictionValidator

    # 测试正常的概率分布
    assert PredictionValidator.validate_probabilities(0.5, 0.3, 0.2) == True
    assert PredictionValidator.validate_probabilities(1.0, 0.0, 0.0) == True


def test_prediction_validator_invalid_probabilities():
    """测试验证无效的概率值"""
    from src.utils.predictions import PredictionValidator

    # 测试超出范围的值
    assert PredictionValidator.validate_probabilities(-0.1, 0.5, 0.6) == False
    assert PredictionValidator.validate_probabilities(0.5, 0.6, 0.0) == False

    # 测试总和不等于1
    assert PredictionValidator.validate_probabilities(0.5, 0.3, 0.3) == False  # 总和1.1
    assert PredictionValidator.validate_probabilities(0.4, 0.2, 0.2) == False  # 总和0.8


def test_prediction_validator_confidence():
    """测试置信度验证"""
    from src.utils.predictions import PredictionValidator

    assert PredictionValidator.validate_confidence(0.0) == True
    assert PredictionValidator.validate_confidence(0.5) == True
    assert PredictionValidator.validate_confidence(1.0) == True
    assert PredictionValidator.validate_confidence(-0.1) == False
    assert PredictionValidator.validate_confidence(1.1) == False


def test_prediction_analyzer_add_and_get_accuracy():
    """测试添加预测和计算准确率"""
    from src.utils.predictions import PredictionAnalyzer

    analyzer = PredictionAnalyzer()

    # 添加正确预测
    analyzer.add_prediction({
        'match_id': 1,
        'predicted': 'home_win',
        'actual': 'home_win'
    })

    # 添加错误预测
    analyzer.add_prediction({
        'match_id': 2,
        'predicted': 'home_win',
        'actual': 'away_win'
    })

    # 准确率应该是 50%
    assert analyzer.get_accuracy() == 0.5


def test_prediction_analyzer_empty():
    """测试空的分析器"""
    from src.utils.predictions import PredictionAnalyzer

    analyzer = PredictionAnalyzer()
    assert analyzer.get_accuracy() is None
    assert analyzer.get_most_predicted() is None


def test_prediction_analyzer_most_predicted():
    """测试获取最常预测的结果"""
    from src.utils.predictions import PredictionAnalyzer

    analyzer = PredictionAnalyzer()

    # 添加多个预测
    analyzer.add_prediction({'match_id': 1, 'predicted': 'home_win'})
    analyzer.add_prediction({'match_id': 2, 'predicted': 'home_win'})
    analyzer.add_prediction({'match_id': 3, 'predicted': 'draw'})
    analyzer.add_prediction({'match_id': 4, 'predicted': 'home_win'})

    # 最常预测的应该是 home_win
    assert analyzer.get_most_predicted() == 'home_win'


def test_prediction_formatter_probability():
    """测试概率格式化"""
    from src.utils.predictions import PredictionFormatter

    # 百分比格式
    assert PredictionFormatter.format_probability(0.75) == "75.0%"
    assert PredictionFormatter.format_probability(0.333) == "33.3%"

    # 小数格式
    assert PredictionFormatter.format_probability(0.75, False) == "0.750"
    assert PredictionFormatter.format_probability(0.333, False) == "0.333"


def test_prediction_formatter_summary():
    """测试预测摘要格式化"""
    from src.utils.predictions import PredictionFormatter

    prediction = {
        'match_id': 123,
        'probabilities': {
            'home_win': 0.6,
            'draw': 0.25,
            'away_win': 0.15
        },
        'predicted': 'home_win',
        'confidence': 0.85
    }

    summary = PredictionFormatter.format_prediction_summary(prediction)

    assert "比赛ID: 123" in summary
    assert "主胜: 60.0%" in summary
    assert "平局: 25.0%" in summary
    assert "客胜: 15.0%" in summary
    assert "预测结果: home_win" in summary
    assert "置信度: 85.0%" in summary


# Step 2: 边界条件测试
def test_probability_sum_edge_case():
    """测试概率和的边界情况"""
    from src.utils.predictions import PredictionValidator

    # 测试允许的误差范围
    assert PredictionValidator.validate_probabilities(0.333, 0.333, 0.334) == True  # 总和1.000
    assert PredictionValidator.validate_probabilities(0.333, 0.333, 0.333) == True  # 总和0.999
    assert PredictionValidator.validate_probabilities(0.334, 0.333, 0.333) == True  # 总和1.000


# Step 3: 集成测试
def test_full_prediction_workflow():
    """测试完整的预测工作流"""
    from src.utils.predictions import PredictionValidator, PredictionAnalyzer, PredictionFormatter

    # 1. 创建预测数据
    prediction = {
        'match_id': 456,
        'probabilities': {
            'home_win': 0.5,
            'draw': 0.3,
            'away_win': 0.2
        },
        'predicted': 'home_win',
        'confidence': 0.8
    }

    # 2. 验证概率
    validator = PredictionValidator()
    assert validator.validate_probabilities(
        prediction['probabilities']['home_win'],
        prediction['probabilities']['draw'],
        prediction['probabilities']['away_win']
    )

    assert validator.validate_confidence(prediction['confidence'])

    # 3. 添加到分析器
    analyzer = PredictionAnalyzer()
    analyzer.add_prediction(prediction)

    # 4. 格式化输出
    summary = PredictionFormatter.format_prediction_summary(prediction)
    assert "比赛ID: 456" in summary

    # 5. 验证历史记录
    assert len(analyzer.predictions_history) == 1
    assert analyzer.predictions_history[0]['match_id'] == 456


# Step 4: 性能测试
def test_prediction_analyzer_performance():
    """测试大量预测的性能"""
    from src.utils.predictions import PredictionAnalyzer

    analyzer = PredictionAnalyzer()

    # 添加1000个预测
    for i in range(1000):
        analyzer.add_prediction({
            'match_id': i,
            'predicted': 'home_win' if i % 2 == 0 else 'away_win',
            'actual': 'home_win' if i % 3 == 0 else 'away_win'
        })

    # 验证性能
    accuracy = analyzer.get_accuracy()
    assert 0 <= accuracy <= 1
    assert len(analyzer.predictions_history) == 1000


# Step 5: 错误处理测试
def test_invalid_prediction_data():
    """测试无效预测数据的处理"""
    from src.utils.predictions import PredictionAnalyzer

    analyzer = PredictionAnalyzer()

    # 测试缺少必要字段的预测
    invalid_prediction = {'predicted': 'home_win'}  # 缺少 match_id
    analyzer.add_prediction(invalid_prediction)

    # 应该没有添加到历史记录
    assert len(analyzer.predictions_history) == 0


def test_format_probability_edge_cases():
    """测试概率格式化的边界情况"""
    from src.utils.predictions import PredictionFormatter

    # 测试0和1
    assert PredictionFormatter.format_probability(0.0) == "0.0%"
    assert PredictionFormatter.format_probability(1.0) == "100.0%"

    # 测试小概率
    assert PredictionFormatter.format_probability(0.001) == "0.1%"
    assert PredictionFormatter.format_probability(0.999) == "99.9%"
