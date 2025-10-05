"""测试失败演示"""

def test_intentional_failure():
    """故意失败的测试，用于演示失败保护机制"""
    assert False, "这是一个故意失败的测试，用于演示失败保护机制"

def test_normal_success():
    """正常的测试"""
    assert True
