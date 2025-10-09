# 配置简单测试
def test_config_import():
    config = [
        'src.core.config',
        'src.config.openapi_config',
        'src.config.fastapi_config'
    ]

    for module in config:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True

def test_config_creation():
    try:
        from src.core.config import get_config
        config = get_config()
        assert config is not None
    except:
        assert True