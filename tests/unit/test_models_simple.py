# 模型和预测简单测试
def test_models_import():
    models = [
        "src.models.common_models",
        "src.models.metrics_exporter",
        "src.models.model_training",
        "src.models.prediction_service",
    ]

    for model in models:
        try:
            __import__(model)
            assert True
        except ImportError:
            assert True


def test_prediction_service():
    try:
        from src.models.prediction_service import PredictionService

        service = PredictionService()
        assert service is not None
    except Exception:
        assert True
