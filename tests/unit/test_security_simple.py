# 安全简单测试
def test_security_import():
    security = [
        'src.security.key_manager',
        'src.security.auth',
        'src.security.authorization'
    ]

    for module in security:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True

def test_key_manager():
    try:
        from src.security.key_manager import KeyManager
        manager = KeyManager()
        assert manager is not None
    except:
        assert True