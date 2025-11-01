#!/usr/bin/env python3
"""
收集和分析 skipped 测试
"""

import subprocess
import re
import os
import sys
from pathlib import Path


def collect_skipped_from_file(test_file):
    """从单个测试文件收集 skipped 测试"""
    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    cmd = ["pytest", test_file, "-v", "--disable-warnings", "--tb=no"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        output = result.stdout + result.stderr

        skipped_tests = []
        lines = output.split("\n")

        for line in lines:
            if "SKIPPED" in line and "::" in line:
                # 提取测试名称
                parts = line.split("::")
                if len(parts) >= 2:
                    test_full_name = parts[1].split()[0]
                    class_name = parts[0].split("/")[-1].replace(".py", "")

                    skipped_tests.append(
                        {
                            "file": test_file,
                            "class": class_name,
                            "test": test_full_name,
                            "full_name": line.split("::")[1].split("SKIPPED")[0].strip(),
                        }
                    )

        return skipped_tests
def get_skip_reason(test_file, test_name):
    """从测试文件中获取跳过原因"""
    try:
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找测试函数或类
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if test_name in line and ("def " in line or "class " in line):
                # 查找前面的 skipif 或 skip 装饰器
                for j in range(max(0, i - 10), i):
                    if "pytest.mark.skip" in lines[j] or "pytest.skip" in lines[j]:
                        # 提取原因
                        reason_match = re.search(r'reason=["\']([^"\']+)["\']', lines[j])
                        if reason_match:
                            return reason_match.group(1)
                        if "pytest.skip(" in lines[j]:
                            skip_reason = re.search(r'pytest\.skip\(["\']([^"\']+)["\']', lines[j])
                            if skip_reason:
                                return skip_reason.group(1)

        return "未知原因"
def main():
    """主函数"""
    print("=" * 80)
    print("📊 Skipped 测试收集器")
    print("=" * 80)

    # 定义要测试的文件列表
    test_files = [
        "tests/unit/api/test_health.py",
        "tests/unit/core/test_logger.py",
        "tests/unit/services/test_audit_service.py",
        "tests/unit/database/test_models.py",
        "tests/unit/api/test_cqrs.py",
        "tests/unit/api/test_events.py",
        "tests/unit/core/test_di.py",
        "tests/unit/core/test_config.py",
        "tests/unit/services/test_base_unified.py",
        "tests/unit/database/test_connection.py",
    ]

    all_skipped = []

    print("\n🔍 收集 skipped 测试...")
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"  处理: {test_file}")
            skipped = collect_skipped_from_file(test_file)
            if skipped:
                print(f"    找到 {len(skipped)} 个 skipped 测试")
                all_skipped.extend(skipped)

    print(f"\n✅ 总共收集到 {len(all_skipped)} 个 skipped 测试")

    # 分类统计
    categories = {
        "健康检查相关": [],
        "模块不可用": [],
        "依赖缺失": [],
        "临时禁用": [],
        "其他": [],
    }

    # 分析每个 skipped 测试
    for skipped_test in all_skipped:
        reason = get_skip_reason(skipped_test["file"], skipped_test["test"])
        skipped_test["reason"] = reason

        # 分类
        if "health" in skipped_test["file"].lower() or "健康" in reason:
            categories["健康检查相关"].append(skipped_test)
        elif "not available" in reason.lower() or "不可用" in reason:
            categories["模块不可用"].append(skipped_test)
        elif "placeholder" in reason.lower() or "占位" in reason:
            categories["临时禁用"].append(skipped_test)
        else:
            categories["其他"].append(skipped_test)

    # 打印统计结果
    print("\n📈 分类统计:")
    for category, tests in categories.items():
        if tests:
            print(f"\n  {category}: {len(tests)} 个")
            for test in tests[:5]:  # 只显示前5个
                print(f"    - {test['test']}")
                print(f"      原因: {test['reason']}")
                print(f"      文件: {test['file']}")
                print()
            if len(tests) > 5:
                print(f"    ... 还有 {len(tests) - 5} 个")

    # 生成修复建议
    print("\n🔧 修复建议:")
    print(f"\n1. 健康检查相关 ({len(categories['健康检查相关'])} 个)")
    print("   - 这些测试需要 mock 外部依赖（数据库、Redis等）")
    print("   - 可以添加 fixture 来模拟服务状态")

    print(f"\n2. 模块不可用 ({len(categories['模块不可用'])} 个)")
    print("   - 这些测试在模块不可用时运行")
    print("   - 可以考虑移除或保留作为边缘情况测试")

    print(f"\n3. 临时禁用 ({len(categories['临时禁用'])} 个)")
    print("   - 需要实现测试逻辑或移除占位代码")

    # 保存结果到文件
    os.makedirs("docs/_reports", exist_ok=True)

    report_content = "# Skipped 测试分析报告\n\n"
    report_content += f"生成时间: {subprocess.check_output(['date'], text=True).strip()}\n\n"
    report_content += f"总计: {len(all_skipped)} 个 skipped 测试\n\n"

    for category, tests in categories.items():
        if tests:
            report_content += f"## {category} ({len(tests)} 个)\n\n"
            for test in tests:
                report_content += f"- `{test['test']}` - {test['reason']}\n"
                report_content += f"  文件: {test['file']}\n\n"

    with open("docs/_reports/SKIPPED_TESTS_ANALYSIS.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n📄 详细报告已保存到: docs/_reports/SKIPPED_TESTS_ANALYSIS.md")

    # 返回可以修复的数量
    fixable = len(categories["健康检查相关"]) + len(categories["临时禁用"])
    print(f"\n🎯 可修复测试数: {fixable}")
    print("📊 目标: 将 skipped 测试减少到 10 个以下")

    return all_skipped


if __name__ == "__main__":
    main()
