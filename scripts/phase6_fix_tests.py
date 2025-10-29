#!/usr/bin/env python3
"""
Phase 6: 修复剩余的失败测试，提升覆盖率
"""

import subprocess
import re
import sys
import os
import json
from pathlib import Path


def analyze_failed_tests():
    """分析失败的测试"""
    print("\n🔍 分析失败的测试...")
    print("-" * 60)

    # 运行测试并收集失败信息
    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    cmd = [
        "pytest",
        "-v",
        "--disable-warnings",
        "--tb=short",
        "--json-report",
        "--json-report-file=test_results.json",
    ]

    try:
        # 检查是否安装了 pytest-json-report
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    except Exception:
        # 如果没有安装，使用普通方式
        cmd = ["pytest", "-v", "--disable-warnings", "--tb=short"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)

    output = result.stdout + result.stderr

    # 解析失败和错误
    failed_tests = []
    error_tests = []

    lines = output.split("\n")
    for line in lines:
        if "FAILED" in line and "::" in line:
            failed_tests.append(line.strip())
        elif "ERROR" in line and "::" in line:
            error_tests.append(line.strip())

    print(f"\n发现失败的测试: {len(failed_tests)}")
    for test in failed_tests:
        print(f"  ❌ {test}")

    print(f"\n发现错误的测试: {len(error_tests)}")
    for test in error_tests:
        print(f"  💥 {test}")

    return failed_tests + error_tests


def analyze_skipped_tests():
    """分析 skipped 测试"""
    print("\n🔍 分析 skipped 测试...")
    print("-" * 60)

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    cmd = ["pytest", "-v", "--disable-warnings", "--rs", "-q"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
    output = result.stdout + result.stderr

    # 收集 skipped 测试及原因
    skipped_tests = []
    lines = output.split("\n")

    for i, line in enumerate(lines):
        if "SKIPPED" in line and "::" in line:
            # 尝试获取跳过原因
            skip_reason = "未知原因"
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith("[") and "skip" in next_line.lower():
                    skip_reason = next_line

            skipped_tests.append({"test": line.strip(), "reason": skip_reason})

    print(f"\n发现 {len(skipped_tests)} 个 skipped 测试:")

    # 分类
    placeholder_tests = []  # 占位测试
    dependency_tests = []  # 依赖缺失
    other_tests = []  # 其他原因

    for test in skipped_tests:
        if "placeholder" in test["reason"].lower() or "占位" in test["reason"]:
            placeholder_tests.append(test)
        elif "not available" in test["reason"].lower() or "不可用" in test["reason"]:
            dependency_tests.append(test)
        else:
            other_tests.append(test)

    print(f"\n  📌 占位测试（可保留）: {len(placeholder_tests)}")
    for test in placeholder_tests[:5]:  # 只显示前5个
        print(f"    - {test['test']}")

    print(f"\n  ⚠️  依赖缺失（可能修复）: {len(dependency_tests)}")
    for test in dependency_tests[:5]:
        print(f"    - {test['test']}")

    print(f"\n  ❓ 其他原因: {len(other_tests)}")
    for test in other_tests[:5]:
        print(f"    - {test['test']}")

    return {
        "total": len(skipped_tests),
        "placeholder": len(placeholder_tests),
        "dependency": len(dependency_tests),
        "other": len(other_tests),
        "details": skipped_tests,
    }


def generate_coverage_report():
    """生成覆盖率报告"""
    print("\n📊 生成覆盖率报告...")
    print("-" * 60)

    env = os.environ.copy()
    env["PYTHONPATH"] = "tests:src"
    env["TESTING"] = "true"

    # 创建覆盖率报告目录
    os.makedirs("htmlcov", exist_ok=True)
    os.makedirs("docs/_reports", exist_ok=True)

    cmd = [
        "pytest",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=json",
        "--disable-warnings",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)

        # 解析覆盖率数据
        if os.path.exists("coverage.json"):
            with open("coverage.json", "r") as f:
                coverage_data = json.load(f)

            # 找出覆盖率为0的模块
            zero_coverage_modules = []
            low_coverage_modules = []

            for file_path, file_data in coverage_data["files"].items():
                if file_path.startswith("src/"):
                    coverage_percent = file_data["summary"]["percent_covered"]
                    module_name = file_path.replace("src/", "").replace(".py", "")

                    if coverage_percent == 0:
                        zero_coverage_modules.append(
                            {
                                "module": module_name,
                                "path": file_path,
                                "statements": file_data["summary"]["num_statements"],
                            }
                        )
                    elif coverage_percent < 30:
                        low_coverage_modules.append(
                            {
                                "module": module_name,
                                "path": file_path,
                                "coverage": coverage_percent,
                                "statements": file_data["summary"]["num_statements"],
                            }
                        )

            # 提取总体覆盖率
            total_coverage = coverage_data["totals"]["percent_covered"]
            total_statements = coverage_data["totals"]["num_statements"]
            total_missing = coverage_data["totals"]["missing_lines"]

            print("\n覆盖率统计:")
            print(f"  总覆盖率: {total_coverage:.1f}%")
            print(f"  总语句数: {total_statements}")
            print(f"  未覆盖: {total_missing}")
            print(f"  0%覆盖率模块: {len(zero_coverage_modules)}")
            print(f"  低覆盖率模块(<30%): {len(low_coverage_modules)}")

            return {
                "total_coverage": total_coverage,
                "zero_coverage": zero_coverage_modules,
                "low_coverage": low_coverage_modules,
                "total_statements": total_statements,
            }

        else:
            print("❌ 无法生成覆盖率JSON文件")
            return None

    except subprocess.TimeoutExpired:
        print("❌ 覆盖率测试超时")
        return None


def create_improvement_plan(coverage_data, failed_tests, skipped_data):
    """创建覆盖率改进计划"""
    print("\n📋 创建覆盖率改进计划...")
    print("-" * 60)

    # 创建改进计划文档
    plan_content = f"""# 覆盖率改进计划

生成时间: {subprocess.check_output(['date'], text=True).strip()}

## 📊 当前状态

- 总覆盖率: {coverage_data['total_coverage']:.1f}%
- 总语句数: {coverage_data['total_statements']}
- 失败测试数: {len(failed_tests)}
- 跳过测试数: {skipped_data['total']}

## 🎯 改进目标

1. **短期目标**（1周内）
   - 修复所有失败的测试
   - 减少跳过测试到 10 个以下
   - 覆盖率提升到 {coverage_data['total_coverage'] + 10:.1f}%

2. **中期目标**（2周内）
   - 覆盖所有 0% 覆盖率的模块
   - 整体覆盖率达到 40%
   - 建立自动化测试生成流程

## 🔧 待修复的失败测试

"""

    # 添加失败测试详情
    for i, test in enumerate(failed_tests, 1):
        plan_content += f"{i}. `{test}`\n"

    plan_content += f"""
## 📌 跳过测试分析

- 占位测试: {skipped_data['placeholder']} 个（可保留）
- 依赖缺失: {skipped_data['dependency']} 个（需修复）
- 其他原因: {skipped_data['other']} 个

## 🎯 优先级：0% 覆盖率模块

以下模块完全没有测试覆盖，需要优先添加测试：

"""

    # 添加0%覆盖率模块
    for i, module in enumerate(coverage_data["zero_coverage"][:10], 1):
        plan_content += f"{i}. **{module['module']}** ({module['statements']} 语句)\n"
        plan_content += "   - 需要创建测试文件\n"
        plan_content += "   - 优先级: 高\n\n"

    # 添加低覆盖率模块
    if coverage_data["low_coverage"]:
        plan_content += "## 📈 低覆盖率模块 (<30%)\n\n"

        for i, module in enumerate(coverage_data["low_coverage"][:10], 1):
            plan_content += f"{i}. **{module['module']}** - {module['coverage']:.1f}%\n"
            plan_content += f"   - 路径: {module['path']}\n"
            plan_content += f"   - 语句数: {module['statements']}\n"
            plan_content += "   - 优先级: 中\n\n"

    plan_content += """
## ✅ 检查清单

### Phase 6.1: 修复失败测试
- [ ] 修复 `fixture 'self' not found` 错误
- [ ] 修复模块导入错误
- [ ] 确保所有测试可以运行

### Phase 6.2: 减少跳过测试
- [ ] 分析依赖缺失的测试
- [ ] 添加必要的 mock 或 fixture
- [ ] 目标: 跳过测试 < 10

### Phase 6.3: 提升 0% 覆盖率模块
- [ ] 为每个 0% 模块创建基础测试
- [ ] 至少覆盖主要函数
- [ ] 验证测试通过

### Phase 6.4: 验证改进
- [ ] 运行完整测试套件
- [ ] 生成新覆盖率报告
- [ ] 确认目标达成

## 🚀 执行命令

```bash
# 运行测试并查看覆盖率
pytest --cov=src --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html

# 运行特定模块测试
pytest tests/unit/path/to/test.py

# 生成详细报告
python scripts/phase6_fix_tests.py
```

## 📝 备注

- 优先修复失败的测试，确保测试套件稳定
- 然后逐步提升覆盖率
- 使用 Claude Code 自动生成测试
- 每次改进后更新此文档
"""

    # 写入文件
    os.makedirs("docs/_reports", exist_ok=True)
    with open("docs/_reports/COVERAGE_IMPROVEMENT_PLAN.md", "w", encoding="utf-8") as f:
        f.write(plan_content)

    print("✅ 覆盖率改进计划已生成: docs/_reports/COVERAGE_IMPROVEMENT_PLAN.md")
    print("\n📖 查看计划:")
    print("  cat docs/_reports/COVERAGE_IMPROVEMENT_PLAN.md")
    print("\n🌐 查看HTML覆盖率报告:")
    print("  open htmlcov/index.html")


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 Phase 6: 修复剩余的失败测试，提升覆盖率")
    print("=" * 80)
    print("目标：从'测试能跑'转向'测试覆盖率可度量、可提升'")
    print("-" * 80)

    # 1. 分析失败的测试
    failed_tests = analyze_failed_tests()

    # 2. 分析 skipped 测试
    skipped_data = analyze_skipped_tests()

    # 3. 生成覆盖率报告
    coverage_data = generate_coverage_report()

    if coverage_data:
        # 4. 创建改进计划
        create_improvement_plan(coverage_data, failed_tests, skipped_data)

        # 5. 总结
        print("\n" + "=" * 80)
        print("📋 Phase 6 分析完成")
        print("=" * 80)
        print(f"✅ 失败测试: {len(failed_tests)} 个")
        print(f"✅ 跳过测试: {skipped_data['total']} 个")
        print(f"✅ 当前覆盖率: {coverage_data['total_coverage']:.1f}%")
        print(f"✅ 0% 覆盖率模块: {len(coverage_data['zero_coverage'])} 个")
        print("\n📄 生成的文件:")
        print("  - docs/_reports/COVERAGE_IMPROVEMENT_PLAN.md")
        print("  - htmlcov/index.html")
        print("\n🎯 下一步:")
        print("  1. 查看改进计划")
        print("  2. 修复失败的测试")
        print("  3. 开始提升覆盖率")
    else:
        print("\n❌ 无法生成覆盖率报告，请检查环境")


if __name__ == "__main__":
    main()
