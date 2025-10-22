# 预测模型测试
from src.database.models.predictions import Prediction

def test_prediction_model():
    pred = Prediction(match_id=1, predicted_home_win=0.5)
    assert pred.match_id == 1
    assert pred.predicted_home_win == 0.5

def test_prediction_repr():
    pred = Prediction(match_id=1)
    assert "Prediction" in repr(pred)