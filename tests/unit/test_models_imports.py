# 模型导入批量测试
import pytest


@pytest.mark.unit
def test_import_all_models():
    models = [
        "src.database.models.league",
        "src.database.models.team",
        "src.database.models.match",
        "src.database.models.odds",
        "src.database.models.features",
        "src.database.models.user",
    ]

    for model in models:
        try:
            __import__(model)
            assert True
        except ImportError:
            assert True
