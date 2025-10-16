#!/usr/bin/env python3
"""TDD培训会话脚本
用于快速演示TDD实践"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(cmd, description=""):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"命令: {cmd}")
    print('='*60)

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("错误信息:")
        print(result.stderr[:500])

    return result.returncode == 0

def create_tdd_workshop():
    """创建TDD工作坊材料"""

    print("🎓 TDD培训会话")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建工作坊目录
    workshop_dir = Path("workshop/tdd_session")
    workshop_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 创建工作坊目录: {workshop_dir}")

    # 练习1：字符串工具（15分钟）
    exercise1 = '''
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
    print("\\n🎉 练习1完成！")
'''

    with open(workshop_dir / "exercise1_string_truncate.py", "w") as f:
        f.write(exercise1)

    # 练习2：数据验证（20分钟）
    exercise2 = '''
"""
练习2：邮箱验证器
时间：20分钟 | 难度：⭐⭐⭐

要求：
实现一个邮箱验证器，检查邮箱格式是否正确。

提示：
- 检查 @ 符号存在
- 检查域名格式
- 考虑边界情况

测试用例：
✅ "user@example.com" -> True
✅ "test.email+tag@domain.co.uk" -> True
❌ "invalid-email" -> False
❌ "@domain.com" -> False
❌ "user@" -> False
"""

# TODO: 在这里实现你的TDD流程
# 1. 先写失败的测试
# 2. 实现最小功能
# 3. 重构改进

print("开始练习2...")
'''

    with open(workshop_dir / "exercise2_email_validator.py", "w") as f:
        f.write(exercise2)

    # 练习3：列表处理（25分钟）
    exercise3 = '''
"""
练习3：统计数字
时间：25分钟 | 难度：⭐⭐⭐⭐

要求：
实现一个函数，统计数字列表中的：
- 最大值
- 最小值
- 平均值
- 中位数

示例：
input: [1, 5, 3, 2, 4]
output: {"max": 5, "min": 1, "average": 3, "median": 3}

挑战：
处理空列表、单元素列表、重复值等边界情况。
"""

# TODO: 实现你的TDD流程
print("开始练习3...")
'''

    with open(workshop_dir / "exercise3_number_stats.py", "w") as f:
        f.write(exercise3)

    print("\n📚 创建练习文件:")
    print("  ✓ exercise1_string_truncate.py - 字符串截断")
    print("  ✓ exercise2_email_validator.py - 邮箱验证")
    print("  ✓ exercise3_number_stats.py - 数字统计")

    return workshop_dir

def run_tdd_demo():
    """运行TDD演示"""

    print("\n🎬 TDD演示：计算器功能")
    print("=" * 60)

    # 创建演示目录
    demo_dir = Path("demo/tdd_calculator")
    demo_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Red - 失败的测试
    test_file = demo_dir / "test_calculator.py"
    with open(test_file, "w") as f:
        f.write('''import pytest

def test_calculator_add():
    """测试计算器加法"""
    from calculator import Calculator

    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5

def test_calculator_add_negative():
    """测试负数加法"""
    from calculator import Calculator

    calc = Calculator()
    result = calc.add(-2, -3)
    assert result == -5

def test_calculator_add_zero():
    """测试零值加法"""
    from calculator import Calculator

    calc = Calculator()
    result = calc.add(0, 5)
    assert result == 5
''')

    print("\n1️⃣ Step 1: Red - 写测试")
    print(f"   创建测试文件: {test_file}")

    # Step 2: 运行测试（失败）
    print("\n2️⃣ Step 2: 运行测试（预期失败）")
    run_command(f"cd {demo_dir} && python -m pytest test_calculator.py -v",
                "运行测试 - 应该失败")

    # Step 3: Green - 最小实现
    calc_file = demo_dir / "calculator.py"
    with open(calc_file, "w") as f:
        f.write('''class Calculator:
    """简单计算器"""

    def add(self, a, b):
        return a + b
''')

    print(f"\n3️⃣ Step 3: Green - 最小实现")
    print(f"   创建实现文件: {calc_file}")

    # Step 4: 运行测试（通过）
    print("\n4️⃣ Step 4: 运行测试（应该通过）")
    run_command(f"cd {demo_dir} && python -m pytest test_calculator.py -v",
                "运行测试 - 应该通过")

    # Step 5: Refactor - 改进代码
    with open(calc_file, "w") as f:
        f.write('''from typing import Union

class Calculator:
    """增强版计算器"""

    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相加

        Args:
            a: 第一个数
            b: 第二个数

        Returns:
            相加结果
        """
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相减"""
        return a - b

    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两数相乘"""
        return a * b
''')

    print("\n5️⃣ Step 5: Refactor - 重构代码")
    print("   添加类型注解和文档")
    print("   增加更多功能")

    # Step 6: 再次运行测试
    print("\n6️⃣ Step 6: 验证重构后测试")
    run_command(f"cd {demo_dir} && python -m pytest test_calculator.py -v --cov=calculator",
                "运行测试并查看覆盖率")

    print("\n✨ TDD演示完成！")
    return demo_dir

def main():
    """主函数"""

    # 1. 创建工作坊材料
    workshop_dir = create_tdd_workshop()

    # 2. 运行TDD演示
    demo_dir = run_tdd_demo()

    # 3. 生成培训总结
    summary = f"""
# TDD培训总结

## 培训内容
1. TDD快速入门指南
2. 三个练习任务
3. 完整的TDD演示

## 练习进度
- 练习1：字符串截断（15分钟）✅
- 练习2：邮箱验证（20分钟）⏳
- 练习3：数字统计（25分钟）⏳

## 关键收获
- TDD = Red → Green → Refactor
- 先写测试，后写代码
- 小步前进，持续改进

## 下一步
1. 完成剩余练习
2. 在实际项目中应用TDD
3. 定期分享TDD经验

## 资源
- 快速入门: docs/TDD_QUICK_START.md
- 完整指南: docs/TDD_GUIDE.md
- 文化指南: docs/TDD_CULTURE_GUIDE.md

培训时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open("TDD_TRAINING_SUMMARY.md", "w") as f:
        f.write(summary)

    print("\n📝 生成培训总结: TDD_TRAINING_SUMMARY.md")

    print("\n" + "=" * 60)
    print("🎉 TDD培训材料准备完成！")
    print("=" * 60)
    print("\n📂 创建的文件:")
    print(f"  📁 工作坊: {workshop_dir}")
    print(f"  📁 演示: {demo_dir}")
    print("\n📋 培训流程:")
    print("  1. 分发快速入门指南")
    print("  2. 讲解TDD概念（10分钟）")
    print("  3. 演示TDD流程（15分钟）")
    print("  4. 分组练习（60分钟）")
    print("  5. 分享和总结（15分钟）")
    print("\n✨ 培训准备就绪！")

if __name__ == "__main__":
    main()
