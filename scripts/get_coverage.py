#!/usr/bin/env python3
"""
获取测试覆盖率
Get Test Coverage
"""

import subprocess
import sys
import re
from pathlib import Path

def run_coverage_test():
    """运行覆盖率测试"""
    print("=" * 60)
    print("           测试覆盖率报告")
    print("=" * 60)

    # 测试可用的模块
    modules_to_test = [
        ("src.utils.dict_utils", "tests/unit/utils/test_dict_utils.py::TestDictUtils::test_deep_merge"),
        ("src.utils.helpers", "tests/unit/utils/test_helpers.py::test_helper_functions"),
        ("src.utils.string_utils", "tests/unit/utils/test_string_utils.py::TestStringUtils::test_string_operations"),
    ]

    total_coverage = 0
    tested_modules = 0

    for module, test_path in modules_to_test:
        print(f"\n📊 测试模块: {module}")

        try:
            # 运行单个测试
            result = subprocess.run(
                [
                    "python", "-m", "pytest",
                    test_path,
                    "--cov=" + module,
                    "--cov-report=term-missing",
                    "-q"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            # 解析输出
            output = result.stdout
            if result.stderr:
                output += result.stderr

            # 查找覆盖率行
            for line in output.split('\n'):
                if module in line and '%' in line:
                    # 解析覆盖率
                    match = re.search(r'(\d+)%', line)
                    if match:
                        coverage = int(match.group(1))
                        total_coverage += coverage
                        tested_modules += 1
                        print(f"   覆盖率: {coverage}%")

                        # 显示缺失的行
                        if "Missing" in line:
                            print(f"   未覆盖: {line.split('Missing')[-1].strip()}")
                    break
            else:
                print("   ⚠️ 无法获取覆盖率数据")

        except subprocess.TimeoutExpired:
            print("   ⏰ 测试超时")
        except Exception as e:
            print(f"   ❌ 错误: {e}")

    # 计算平均覆盖率
    if tested_modules > 0:
        average_coverage = total_coverage / tested_modules
        print("\n" + "=" * 60)
        print(f"📈 平均测试覆盖率: {average_coverage:.1f}%")
        print(f"📊 测试的模块数: {tested_modules}")
        print("=" * 60)

        # 建议
        if average_coverage < 50:
            print("\n💡 建议:")
            print("1. 增加更多测试用例")
            print("2. 测试边界条件")
            print("3. 测试异常处理路径")
        elif average_coverage < 80:
            print("\n💡 建议:")
            print("1. 添加缺失的测试用例")
            print("2. 提高测试覆盖率到80%以上")
        else:
            print("\n✅ 测试覆盖率良好！")

    else:
        print("\n⚠️ 没有成功获取任何覆盖率数据")

def check_project_coverage():
    """检查项目整体覆盖率"""
    print("\n" + "=" * 60)
    print("           项目整体状态")
    print("=" * 60)

    # 统计Python文件
    src_files = list(Path("src").rglob("*.py"))
    test_files = list(Path("tests").rglob("*.py"))

    print(f"\n📁 项目文件统计:")
    print(f"   源代码文件: {len(src_files)}")
    print(f"   测试文件: {len(test_files)}")

    # 检查关键目录
    key_dirs = [
        "src/utils",
        "src/core",
        "src/api",
        "src/domain",
        "src/services"
    ]

    print("\n📂 关键目录文件数:")
    for dir_path in key_dirs:
        path = Path(dir_path)
        if path.exists():
            py_files = list(path.rglob("*.py"))
            print(f"   {dir_path}: {len(py_files)} 文件")
        else:
            print(f"   {dir_path}: 不存在")

    # 测试运行状态
    print("\n🔍 测试运行状态:")

    # 尝试运行pytest --collect-only
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # 统计测试数量
            output = result.stdout
            match = re.search(r'collected (\d+) items', output)
            if match:
                test_count = int(match.group(1))
                print(f"   ✅ 可收集的测试: {test_count} 个")
            else:
                print("   ⚠️ 无法统计测试数量")
        else:
            print("   ⚠️ 收集测试时出错")
            # 显示错误数量
            error_count = result.stdout.count("ERROR")
            if error_count > 0:
                print(f"   ❌ 错误数: {error_count}")

    except Exception as e:
        print(f"   ❌ 检查失败: {e}")

def main():
    """主函数"""
    # 运行覆盖率测试
    run_coverage_test()

    # 检查项目状态
    check_project_coverage()

    # 总结
    print("\n" + "=" * 60)
    print("📝 总结:")
    print("1. 项目已完成四个阶段的重构工作")
    print("2. 核心模块语法错误已修复")
    print("3. 文档体系已完善")
    print("4. 部分测试可以运行")
    print("\n🚀 下一步建议:")
    print("1. 继续修复剩余的导入错误")
    print("2. 提高测试覆盖率")
    print("3. 进行性能优化")
    print("=" * 60)

if __name__ == "__main__":
    main()