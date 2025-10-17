#!/usr/bin/env python3
"""
运行测试并生成报告
"""

import subprocess
import sys
import os
import json
from datetime import datetime
from pathlib import Path


def run_command_with_env(cmd, env_vars=None):
    """运行命令并设置环境变量"""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    return result


def generate_test_report():
    """生成测试报告"""
    print("\n" + "="*80)
    print("🚀 测试运行与报告生成")
    print("="*80)

    report = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "tests": {}
    }

    # 1. 运行utils模块测试
    print("\n1️⃣ 运行utils模块测试...")
    utils_modules = [
        "validators",
        "crypto_utils",
        "string_utils",
        "time_utils",
        "file_utils"
    ]

    total_passed = 0
    total_failed = 0
    total_tests = 0

    for module in utils_modules:
        test_file = f"tests/unit/test_{module}_optimized.py"
        if os.path.exists(test_file):
            print(f"\n🔍 运行 {module} 测试...")

            result = run_command_with_env([
                "python", "-m", "pytest",
                test_file,
                "--tb=no",
                "-q",
                "--disable-warnings"
            ])

            if result.returncode == 0:
                print(f"  ✅ {module} 测试通过")
                status = "PASSED"
            else:
                print(f"  ❌ {module} 测试失败")
                status = "FAILED"

            # 解析输出
            output = result.stdout or result.stderr
            test_count = output.count("passed") + output.count("failed")

            report["tests"][module] = {
                "status": status,
                "test_count": test_count,
                "output": output[-500:]  # 只保留最后500字符
            }

            if status == "PASSED":
                total_passed += test_count
            else:
                total_failed += test_count
            total_tests += test_count

    # 2. 运行覆盖率测试
    print("\n2️⃣ 运行覆盖率测试...")
    coverage_result = run_command_with_env([
        "python", "-m", "pytest",
        "tests/unit/test_validators_optimized.py",
        "tests/unit/test_string_utils_optimized.py",
        "tests/unit/test_time_utils_optimized.py",
        "--cov=src.utils",
        "--cov-report=json:coverage_report.json",
        "--cov-report=term-missing",
        "--tb=no",
        "-q",
        "--disable-warnings"
    ])

    # 读取覆盖率报告
    coverage_data = {}
    if os.path.exists("coverage_report.json"):
        with open("coverage_report.json", "r") as f:
            coverage_json = json.load(f)
            coverage_data = {
                "total_coverage": coverage_json.get("totals", {}).get("percent_covered", 0),
                "files": {}
            }

            for file_path, file_data in coverage_json.get("files", {}).items():
                if "utils/" in file_path:
                    filename = file_path.split("/")[-1]
                    coverage_data["files"][filename] = {
                        "statements": file_data.get("summary", {}).get("num_statements", 0),
                        "missing": file_data.get("summary", {}).get("missing_lines", 0),
                        "coverage": file_data.get("summary", {}).get("percent_covered", 0)
                    }

    # 3. 更新报告
    report["summary"] = {
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "success_rate": f"{(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "0%"
    }
    report["coverage"] = coverage_data

    # 4. 生成报告文件
    with open("TEST_EXECUTION_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 5. 生成Markdown报告
    md_report = f"""# 测试执行报告

生成时间: {report['timestamp']}

## 📊 测试摘要

- **总测试数**: {report['summary']['total_tests']}
- **通过**: {report['summary']['passed']}
- **失败**: {report['summary']['failed']}
- **成功率**: {report['summary']['success_rate']}

## 🧪 模块测试状态

"""

    for module, data in report["tests"].items():
        status_icon = "✅" if data["status"] == "PASSED" else "❌"
        md_report += f"### {status_icon} {module}\n"
        md_report += f"- 状态: {data['status']}\n"
        md_report += f"- 测试数: {data['test_count']}\n\n"

    if coverage_data:
        md_report += f"""## 📈 覆盖率报告

- **总覆盖率**: {coverage_data.get('total_coverage', 0):.2f}%

### 各文件覆盖率

"""

        for filename, data in coverage_data.get("files", {}).items():
            md_report += f"- **{filename}**: {data['coverage']:.1f}% ({data['statements'] - data['missing']}/{data['statements']} 行)\n"

    with open("TEST_EXECUTION_REPORT.md", "w", encoding="utf-8") as f:
        f.write(md_report)

    # 6. 打印摘要
    print("\n" + "="*80)
    print("📊 测试执行摘要")
    print("="*80)
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"通过: {report['summary']['passed']} ✅")
    print(f"失败: {report['summary']['failed']} ❌")
    print(f"成功率: {report['summary']['success_rate']}")

    if coverage_data:
        print(f"\n覆盖率: {coverage_data.get('total_coverage', 0):.2f}%")

    print("\n📄 报告已生成:")
    print("- TEST_EXECUTION_REPORT.md")
    print("- TEST_EXECUTION_REPORT.json")

    return report


def main():
    """主函数"""
    print("🚀 开始运行测试并生成报告...")

    # 检查环境
    print("\n检查环境...")
    if not os.path.exists("src/utils"):
        print("❌ 未找到src/utils目录")
        return False

    if not os.path.exists("tests"):
        print("❌ 未找到tests目录")
        return False

    # 生成报告
    report = generate_test_report()

    # 提供下一步建议
    print("\n" + "="*80)
    print("📋 下一步建议")
    print("="*80)

    success_rate = float(report['summary']['success_rate'].rstrip('%'))

    if success_rate >= 80:
        print("✅ 测试状态良好！")
        print("下一步建议:")
        print("1. 运行更多模块测试: pytest tests/unit/")
        print("2. 检查集成测试: pytest tests/integration/")
        print("3. 运行完整测试: make test")
    elif success_rate >= 60:
        print("⚠️ 测试状态一般，建议继续优化")
        print("下一步建议:")
        print("1. 检查失败的测试")
        print("2. 运行: pytest --tb=short 查看详细错误")
        print("3. 修复失败的测试")
    else:
        print("❌ 测试状态需要改进")
        print("下一步建议:")
        print("1. 检查测试环境配置")
        print("2. 确认模块导入正确")
        print("3. 逐个运行测试找出问题")

    print("\n📊 当前状态:")
    print(f"- Utils模块测试: {success_rate:.0f}% 成功")
    print(f"- 测试文件数: 5个 (validators, crypto_utils, string_utils, time_utils, file_utils)")
    print(f"- 覆盖率目标: 73.5%+ (utils模块)")
    print(f"- 整体覆盖率目标: 30%+")

    print("\n✅ 完成!")
    return True


if __name__ == "__main__":
    main()