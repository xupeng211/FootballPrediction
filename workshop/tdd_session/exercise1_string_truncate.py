
"""
练习1：字符串截断功能
时间：15分钟 | 难度：⭐⭐

要求：
实现一个字符串截断函数，如果字符串超过指定长度，
截断并添加省略号。

步骤：
1. 先写失败的测试
2. 实现最小代码
3. 重构改进
"""

# Step 1: Red - 写测试
def test_truncate_string():
    """测试字符串截断"""
    from string_utils import truncate_string

    # 测试1：短字符串不截断
    assert truncate_string("hello", 10) == "hello"

    # 测试2：长字符串需要截断
    assert truncate_string("hello world", 5) == "hello..."

    # 测试3：边界值
    assert truncate_string("hello", 5) == "hello"

    print("✅ 所有测试通过！")

# Step 2: Green - 实现功能
def truncate_string(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

# Step 3: Refactor - 改进代码
def truncate_string_refactored(text: str, max_length: int, suffix="...") -> str:
    """
    截断字符串

    Args:
        text: 要截断的文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text

    # 计算保留的文本长度
    keep_length = max_length - len(suffix)
    if keep_length < 0:
        keep_length = 0

    return text[:keep_length] + suffix

# 运行测试
if __name__ == "__main__":
    test_truncate_string()
    print("\n🎉 练习1完成！")
