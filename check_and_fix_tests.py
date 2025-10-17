#!/usr/bin/env python3
"""
简化的测试检查和修复脚本
专注于快速识别和修复常见问题
"""

import os
import subprocess
import sys
from pathlib import Path
import ast

def run_quick_test_check():
    """运行快速测试检查"""
    print("\n" + "="*80)
    print("🔍 快速测试状态检查")
    print("="*80)

    # 1. 检查pytest是否能正常工作
    print("\n1️⃣ 测试pytest配置...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ pytest已安装: {result.stdout.strip()}")
        else:
            print(f"❌ pytest未安装")
            return False
    except Exception as e:
        print(f"❌ pytest错误: {e}")
        return False

    # 2. 检查测试收集
    print("\n2️⃣ 检查测试收集...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            test_count = 0
            for line in lines:
                if 'tests/' in line and '.py::' in line:
                    test_count += 1
            print(f"✅ 收集到 {test_count} 个测试")
        else:
            print(f"⚠️ 测试收集有警告或错误")
            # 显示前几个错误
            errors = result.stderr.split('\n')[:5]
            for error in errors:
                if error.strip():
                    print(f"   - {error}")
    except subprocess.TimeoutExpired:
        print("⚠️ 测试收集超时")
    except Exception as e:
        print(f"❌ 测试收集错误: {e}")

    # 3. 运行一个快速单元测试
    print("\n3️⃣ 运行快速单元测试...")
    try:
        # 尝试运行一个简单的utils测试
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/unit/test_validators_optimized.py", "--tb=short", "-v"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ 单元测试运行成功")
            print(result.stdout)
        else:
            print(f"❌ 单元测试失败")
            print(result.stderr)
    except subprocess.TimeoutExpired:
        print("⚠️ 单元测试超时")
    except FileNotFoundError:
        print("⚠️ 测试文件不存在")
    except Exception as e:
        print(f"❌ 单元测试错误: {e}")

    # 4. 检查覆盖率
    print("\n4️⃣ 检查覆盖率...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/unit/test_validators_optimized.py", "--cov=src.utils.validators", "--cov-report=term-missing", "-q"],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode == 0:
            # 提取覆盖率信息
            output = result.stdout
            if "coverage:" in output.lower() or "覆盖" in output:
                print("✅ 覆盖率报告生成成功")
                for line in output.split('\n'):
                    if 'src/utils/validators.py' in line:
                        print(f"   覆盖率: {line}")
            else:
                print("⚠️ 未找到覆盖率信息")
        else:
            print(f"⚠️ 覆盖率检查失败")
    except subprocess.TimeoutExpired:
        print("⚠️ 覆盖率检查超时")
    except Exception as e:
        print(f"❌ 覆盖率检查错误: {e}")

    return True

def check_common_test_errors():
    """检查常见的测试错误"""
    print("\n" + "="*80)
    print("🐛 常见测试错误检查")
    print("="*80)

    # 检查的文件
    test_files = [
        "tests/conftest.py",
        "tests/unit/test_validators_optimized.py",
        "tests/unit/test_crypto_utils_optimized.py",
        "tests/unit/test_string_utils_optimized.py",
        "tests/unit/test_time_utils_optimized.py",
        "tests/unit/test_file_utils_optimized.py"
    ]

    errors_found = []

    for file_path in test_files:
        if not os.path.exists(file_path):
            errors_found.append(f"❌ 文件不存在: {file_path}")
            continue

        print(f"\n🔍 检查 {file_path}...")

        # 1. 语法检查
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            print(f"  ✅ 语法正确")
        except SyntaxError as e:
            errors_found.append(f"❌ 语法错误 {file_path}: 第{e.lineno}行 - {e.msg}")
            print(f"  ❌ 语法错误: 第{e.lineno}行 - {e.msg}")
        except Exception as e:
            errors_found.append(f"❌ 解析错误 {file_path}: {e}")
            print(f"  ❌ 解析错误: {e}")

        # 2. 常见问题检查
        common_issues = [
            ("@pytest.fixture", "fixture装饰器"),
            ("async def test_", "异步测试"),
            ("from unittest.mock", "mock导入"),
            ("pytest.mark", "pytest标记")
        ]

        for pattern, desc in common_issues:
            if pattern in content:
                print(f"  ✓ 包含{desc}")

    return errors_found

def create_test_diagnostic_report():
    """创建测试诊断报告"""
    print("\n" + "="*80)
    print("📊 创建测试诊断报告")
    print("="*80)

    report = []
    report.append("# 测试诊断报告\n")
    report.append(f"生成时间: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}\n")

    # 1. pytest版本
    result = subprocess.run(["python", "-m", "pytest", "--version"], capture_output=True, text=True)
    report.append("## pytest信息\n")
    report.append(f"```{result.stdout.strip()}```\n")

    # 2. Python环境
    report.append("## Python环境\n")
    report.append(f"- Python版本: {sys.version}\n")
    report.append(f"- 当前目录: {os.getcwd()}\n")

    # 3. 测试统计
    report.append("## 测试统计\n")
    test_dirs = ["tests/unit", "tests/integration", "tests/e2e"]
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            count = len([f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")])
            report.append(f"- {test_dir}: {count} 个测试文件\n")

    # 4. 常见问题
    report.append("## 常见问题及解决方案\n")
    report.append("""
### 1. 语法错误
- **问题**: IndentationError, SyntaxError
- **解决**: 检查缩进和语法格式

### 2. 导入错误
- **问题**: ImportError, ModuleNotFoundError
- **解决**: 检查模块路径和依赖

### 3. Fixture错误
- **问题**: fixture 'api_client' not found
- **解决**: 在conftest.py中定义fixture

### 4. 异步测试错误
- **问题**: async test without @pytest.mark.asyncio
- **解决**: 添加装饰器

### 5. 覆盖率低
- **问题**: 覆盖率不达标
- **解决**: 添加更多测试用例
""")

    # 写入报告
    with open("TEST_DIAGNOSTIC_REPORT.md", "w", encoding="utf-8") as f:
        f.writelines(report)

    print("✅ 测试诊断报告已生成: TEST_DIAGNOSTIC_REPORT.md")

def main():
    """主函数"""
    print("\n🚀 开始测试诊断和修复...")

    # 1. 运行快速测试检查
    if run_quick_test_check():
        print("\n✅ 测试环境基本正常")
    else:
        print("\n❌ 测试环境有问题")

    # 2. 检查常见错误
    errors = check_common_test_errors()
    if errors:
        print(f"\n⚠️ 发现 {len(errors)} 个问题")
        for error in errors[:5]:
            print(f"  {error}")
    else:
        print("\n✅ 未发现常见错误")

    # 3. 创建诊断报告
    create_test_diagnostic_report()

    # 4. 提供下一步建议
    print("\n" + "="*80)
    print("📋 下一步建议")
    print("="*80)
    print("\n1. 运行单个测试验证:")
    print("   pytest tests/unit/test_validators_optimized.py -v")
    print("\n2. 运行快速覆盖率:")
    print("   make coverage-fast")
    print("\n3. 运行完整测试:")
    print("   make test-quick")
    print("\n4. 查看诊断报告:")
    print("   cat TEST_DIAGNOSTIC_REPORT.md")

    print("\n✅ 诊断完成!")


if __name__ == "__main__":
    main()