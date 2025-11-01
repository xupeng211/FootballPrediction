#!/usr/bin/env python3
"""
阶段3质量改进策略分析工具 - Issue #88
智能分析Ruff问题并制定最佳改进策略
"""

import os
import subprocess
import re
from pathlib import Path
from collections import defaultdict, Counter


def analyze_ruff_errors():
    """分析Ruff错误分布"""
    print("🔍 分析Ruff错误分布")
    print("=" * 50)

    # 运行ruff检查并获取详细输出
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=grouped"], capture_output=True, text=True, timeout=60
        )
        errors = result.stdout.split("\n")
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return {}

    # 统计错误类型
    error_stats = Counter()
    file_errors = defaultdict(list)

    for line in errors:
        if not line.strip():
            continue

        # 解析错误行格式: 文件路径:行号:列号: 错误代码 错误描述
        if "->" in line or ":" in line:
            parts = line.split(":", 3)
            if len(parts) >= 4:
                file_path = parts[0]
                error_code = parts[3].split()[0] if parts[3].strip() else "UNKNOWN"

                error_stats[error_code] += 1
                file_errors[file_path].append(error_code)

    return {
        "error_stats": dict(error_stats),
        "file_errors": dict(file_errors),
        "total_errors": sum(error_stats.values()),
    }


def categorize_errors_by_priority(error_stats):
    """按优先级分类错误"""
    high_priority = {
        # 语法错误 - 阻止运行
        "invalid-syntax": "critical",
        "E722": "high",  # bare-except
        "E401": "medium",  # multiple-imports-on-one-line
        "E713": "medium",  # not-in-test
        # 逻辑错误
        "F541": "medium",  # f-string-missing-placeholders
        "F841": "medium",  # unused-variable
        "F402": "low",  # import-shadowed-by-loop-var
    }

    categorized = defaultdict(list)
    for error_code, count in error_stats.items():
        priority = high_priority.get(error_code, "low")
        categorized[priority].append((error_code, count))

    return categorized


def identify_critical_files(file_errors):
    """识别关键文件"""
    # 关键源码文件优先级更高
    critical_patterns = [
        "src/",
        "tests/unit/",
        "tests/integration/",
    ]

    # 低优先级文件
    low_priority_patterns = [
        "scripts/",
        "config/",
        "docs/",
        "tests/e2e/",  # 端到端测试优先级较低
        "__pycache__",
        ".pytest_cache",
    ]

    critical_files = []
    low_priority_files = []

    for file_path, errors in file_errors.items():
        if any(pattern in file_path for pattern in critical_patterns):
            critical_files.append((file_path, len(errors)))
        elif any(pattern in file_path for pattern in low_priority_patterns):
            low_priority_files.append((file_path, len(errors)))
        else:
            critical_files.append((file_path, len(errors)))  # 默认为关键文件

    return {
        "critical": sorted(critical_files, key=lambda x: x[1], reverse=True),
        "low_priority": sorted(low_priority_files, key=lambda x: x[1], reverse=True),
    }


def create_smart_fix_strategy(error_stats, file_analysis):
    """创建智能修复策略"""
    print("🎯 制定智能修复策略")
    print("=" * 40)

    strategy = {"immediate_fixes": [], "auto_fixable": [], "manual_review": [], "skip_files": []}

    # 1. 立即修复的关键语法错误
    critical_files = file_analysis["critical"][:20]  # 前20个关键文件
    for file_path, error_count in critical_files:
        if "src/" in file_path and error_count > 0:
            strategy["immediate_fixes"].append(file_path)

    # 2. 可以自动修复的错误
    auto_fixable_codes = ["F541", "E401", "F402"]
    for code in auto_fixable_codes:
        if code in error_stats:
            strategy["auto_fixable"].append((code, error_stats[code]))

    # 3. 需要手动检查的错误
    manual_codes = ["invalid-syntax", "E722", "F841"]
    for code in manual_codes:
        if code in error_stats:
            strategy["manual_review"].append((code, error_stats[code]))

    # 4. 跳过的低优先级文件
    low_priority_files = file_analysis["low_priority"]
    for file_path, error_count in low_priority_files[:50]:  # 跳过前50个低优先级文件
        if "scripts/" in file_path or "config/" in file_path:
            strategy["skip_files"].append(file_path)

    return strategy


def execute_phase3_strategy(strategy):
    """执行阶段3策略"""
    print("🚀 执行阶段3质量改进策略")
    print("=" * 50)

    print("📋 策略概览:")
    print(f"  立即修复文件: {len(strategy['immediate_fixes'])} 个")
    print(f"  自动修复错误: {len(strategy['auto_fixable'])} 类")
    print(f"  手动检查错误: {len(strategy['manual_review'])} 类")
    print(f"  跳过文件: {len(strategy['skip_files'])} 个")

    # 1. 跳过低优先级文件
    print("\n第1步: 跳过低优先级文件")
    skip_count = 0
    for file_path in strategy["skip_files"]:
        # 创建.gitignore风格的排除，或者用ruff配置忽略
        skip_count += 1
        if skip_count <= 10:  # 只显示前10个
            print(f"  ⏭️  跳过: {file_path}")

    if skip_count > 10:
        print(f"  ⏭️  ...还有 {skip_count - 10} 个文件被跳过")

    # 2. 自动修复可修复的错误
    print("\n第2步: 自动修复可修复错误")
    for error_code, count in strategy["auto_fixable"]:
        print(f"  🔧 自动修复 {error_code}: {count} 个错误")
        try:
            # 使用ruff自动修复
            result = subprocess.run(
                ["ruff", "check", f"--select={error_code}", "--fix"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print(f"    ✅ {error_code} 修复成功")
            else:
                print(f"    ⚠️ {error_code} 修复遇到问题")
        except Exception as e:
            print(f"    ❌ {error_code} 修复失败: {e}")

    # 3. 修复关键文件
    print("\n第3步: 修复关键源码文件")
    fixed_files = 0
    for file_path in strategy["immediate_fixes"][:15]:  # 处理前15个关键文件
        if file_path.endswith(".py"):
            print(f"  🔧 处理关键文件: {file_path}")
            try:
                # 尝试自动修复该文件的所有可修复错误
                result = subprocess.run(
                    ["ruff", "check", file_path, "--fix"],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )

                if result.returncode == 0:
                    print(f"    ✅ {file_path} 修复成功")
                    fixed_files += 1
                else:
                    print(f"    ⚠️ {file_path} 部分修复")

            except Exception as e:
                print(f"    ❌ {file_path} 修复失败: {e}")

    print(f"\n📊 第3步总结: 成功处理 {fixed_files} 个关键文件")

    return True


def generate_improvement_report():
    """生成改进报告"""
    print("\n📊 生成阶段3改进报告")
    print("=" * 40)

    # 重新检查错误状态
    try:
        result = subprocess.run(
            ["ruff", "check", "--statistics"], capture_output=True, text=True, timeout=30
        )

        print("当前错误状态:")
        print(result.stdout)

        # 提取总错误数
        total_line = [
            line for line in result.stdout.split("\n") if "Found" in line and "errors" in line
        ]
        if total_line:
            print("\n🎯 阶段3改进效果:")
            print(f"  剩余错误数: {total_line[0]}")

    except Exception as e:
        print(f"❌ 生成报告失败: {e}")


def main():
    """主函数"""
    print("🚀 Issue #88 阶段3: 智能质量改进策略")
    print("=" * 60)

    # 1. 分析错误分布
    print("\n📊 第1步: 分析Ruff错误分布")
    analysis = analyze_ruff_errors()

    if not analysis:
        print("❌ 无法获取错误分析，退出")
        return False

    error_stats = analysis["error_stats"]
    file_errors = analysis["file_errors"]
    total_errors = analysis["total_errors"]

    print(f"发现 {total_errors} 个错误，涉及 {len(file_errors)} 个文件")
    print(f"错误类型分布: {len(error_stats)} 种")

    # 2. 按优先级分类
    print("\n🎯 第2步: 按优先级分类错误")
    categorized = categorize_errors_by_priority(error_stats)

    for priority, errors in categorized.items():
        print(f"{priority.upper()}: {len(errors)} 种错误类型")
        for error_code, count in errors[:3]:  # 显示前3个
            print(f"  {error_code}: {count} 个")

    # 3. 识别关键文件
    print("\n📂 第3步: 识别关键文件")
    file_analysis = identify_critical_files(file_errors)

    critical_count = len(file_analysis["critical"])
    low_priority_count = len(file_analysis["low_priority"])

    print(f"关键文件: {critical_count} 个")
    print(f"低优先级文件: {low_priority_count} 个")

    # 4. 制定策略
    print("\n🎯 第4步: 制定智能修复策略")
    strategy = create_smart_fix_strategy(error_stats, file_analysis)

    # 5. 执行策略
    print("\n🔧 第5步: 执行质量改进")
    success = execute_phase3_strategy(strategy)

    # 6. 生成报告
    generate_improvement_report()

    return success


if __name__ == "__main__":
    success = main()
    print(f"\n{'🎉 阶段3完成!' if success else '❌ 阶段3遇到问题'}")
