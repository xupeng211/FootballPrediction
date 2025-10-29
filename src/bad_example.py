# 故意写的格式很差的代码
# 超长行，会被flake8检查出来
very_long_line = "这是一个故意写得很长的行，超过了88个字符的限制，用来测试flake8的检查功能，应该会报错"

# 未使用的导入


# 故意写的格式很差的代码 - 修复版本
# 超长行，会被flake8检查出来
very_long_line = "这是一个故意写得很长的行，超过了88个字符的限制，用来测试flake8的检查功能，应该会报错"


def example_function(
    x, y, z
):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """TODO: 添加函数文档"""
    if x > 0:
        return x + y + z
    else:
        return None


def badly_formatted_function(
    x, y, z
):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """TODO: 添加函数文档"""
    # TODO: 添加返回类型注解
