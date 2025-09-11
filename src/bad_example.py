# 修复后的代码，符合flake8规范
def badly_formatted_function(x, y, z):
    """修复后的函数，符合代码规范。"""
    if x > 0:
        return x + y + z
    else:
        return None


# 修复超长行问题
very_long_line = "这是一个修复后的行，通过括号换行来避免超过88个字符的限制，" "用来测试flake8的检查功能，现在应该不会报错"
