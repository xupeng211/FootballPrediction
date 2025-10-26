"""
    预测算法测试 - 第5部分
    从原文件 test_prediction_algorithms_comprehensive.py 拆分
    创建时间: 2025-10-26 18:19:15.123460
    """

    import pytest
    from unittest.mock import Mock, patch

def create_prediction_result(**overrides):
def create_prediction_result(**overrides):
    """创建预测结果"""
    default_result = {
    "match_id": 12345,
    "predicted_outcome": "home",
    "probabilities": {
    "home_win": 0.45,
    "draw": 0.30,
    "away_win": 0.25
    },
    "confidence": 0.75,
    "model_version": "v1.0"
    }
    default_result.update(overrides)
    return default_result

@staticmethod

def create_training_data(num_samples=100):
def create_training_data(num_samples=100):
    """创建训练数据"""
    import random

    training_data = []
    outcomes = ["home", "draw", "away"]

    for i in range(num_samples):

    features = {
    "home_form": random.uniform(0, 3),
    "away_form": random.uniform(0, 3),
    "home_advantage": random.uniform(-0.5, 0.5)
    }
    outcome = random.choice(outcomes)

    training_data.append({
    "features": features,
    "outcome": outcome
    })

    return training_data

    return PredictionDataFactory()


# ==================== 测试运行配置 ====================

if __name__ == "__main__":
        pass
    # 独立运行测试的配置
    pytest.main([__file__, "-v", "--tb=short"])
