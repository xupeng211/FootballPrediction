from src.core.prediction_engine import PredictionEngine

def test_engine_creation():
    engine = PredictionEngine()
    assert engine is not None

def test_engine_methods():
    engine = PredictionEngine()
    # 测试方法是否存在
    assert hasattr(engine, 'predict')
    assert hasattr(engine, 'train')
    assert hasattr(engine, 'evaluate')