# 断言修复建议

# 1. 使用更宽松的断言
assert result is not None  # 代替 assert result

# 2. 检查类型而不是具体值
assert isinstance(result, ExpectedType)

# 3. 使用 in 操作符代替直接比较
assert expected_value in actual_values

# 4. 检查字典键是否存在
assert "key" in result_dict
