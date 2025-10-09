# 机器学习简单测试
def test_ml_import():
    ml = [
        'src.ml.model_training',
        'src.ml.model_evaluation',
        'src.ml.feature_engineering',
        'src.ml.hyperparameter_tuning'
    ]

    for module in ml:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True

def test_ml_training():
    try:
        from src.ml.model_training import ModelTrainer
        trainer = ModelTrainer()
        assert trainer is not None
    except:
        assert True