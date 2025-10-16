# TDD快速入门指南

## 5分钟TDD入门

### 第1步：理解TDD
TDD = Test-Driven Development（测试驱动开发）
- **先写测试**，再写代码
- **测试失败** → **代码通过** → **重构优化**

### 第2步：看一个例子

```python
# 1. 写测试（Red阶段）
def test_calculator_add():
    calc = Calculator()
    assert calc.add(2, 3) == 5

# 2. 运行测试（会失败）
# pytest test_calculator.py  # 失败：Calculator不存在

# 3. 写代码（Green阶段）
class Calculator:
    def add(self, a, b):
        return a + b  # 刚好让测试通过

# 4. 运行测试（会通过）
# pytest test_calculator.py  # 成功！

# 5. 重构（Refactor阶段）
class Calculator:
    """改进后的计算器"""
    def add(self, a: int, b: int) -> int:
        """两个整数相加"""
        return a + b
```

### 第3步：实践规则

1. **三定律**
   - 不能写生产代码，除非先写失败的测试
   - 不能写超过一个失败的测试
   - 不能写超过让测试通过的生产代码

2. **红绿重构循环**
   - Red：写一个失败的测试
   - Green：写最少的代码让它通过
   - Refactor：在测试保护下清理代码

## 常见问题

### Q1：测试写什么？
A：写用户需要的功能。从用户故事开始：
```
用户：我要看比赛预测
测试：test_get_match_prediction()
```

### Q2：什么时候停止写测试？
A：当覆盖所有重要功能时：
- 正常路径
- 边界条件
- 错误情况

### Q3：测试失败怎么办？
A：检查：
1. 测试是否合理
2. 实现是否正确
3. 边界条件是否考虑

## 实践任务

### 任务1：创建你的第一个TDD测试

选择一个简单功能，比如：
- 字符串处理
- 数据验证
- 简单计算

按照上面的例子完成TDD循环。

### 任务2：重构现有代码

找一个没有测试的函数：
1. 先写测试覆盖它
2. 重构改进它
3. 确保测试通过

## 检查清单

完成TDD后，确认：
- [ ] 测试描述清晰
- [ ] 测试先于代码
- [ ] 代码简单有效
- [ ] 所有测试通过
- [ ] 覆盖率达标

## 需要帮助？

- 查看完整指南：[TDD_GUIDE.md](TDD_GUIDE.md)
- 学习最佳实践：[TDD_CULTURE_GUIDE.md](TDD_CULTURE_GUIDE.md)
- 获取模板：运行 `python scripts/tdd_template_generator.py`

记住：**小步前进，持续改进！**
