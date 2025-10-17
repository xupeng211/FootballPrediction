#!/usr/bin/env python3
"""识别高价值的失败测试"""

import subprocess
import re
from pathlib import Path

def run_failing_tests():
    """运行测试并收集失败信息"""
    # 运行测试，只收集失败信息
    cmd = [
        'pytest', '-m', 'not slow',
        '--tb=no',  # 不显示详细错误信息
        '--maxfail=50',  # 最多收集50个失败
        '-q',  # 安静模式
        '--co',  # 只收集，不运行
    ]

    # 先收集测试
    collect_result = subprocess.run(cmd + ['--collect-only'], capture_output=True, text=True)

    # 运行一个快速测试看实际的失败情况
    run_cmd = [
        'pytest', '-m', 'not slow',
        '--tb=short',  # 简短的错误信息
        '--maxfail=20',  # 最多20个失败
        '-x',  # 第一个失败就停止
        'tests/unit/utils/',  # 优先处理utils模块
        'tests/unit/services/',  # 然后是services
    ]

    print("🔍 正在收集失败测试信息...")
    result = subprocess.run(run_cmd, capture_output=True, text=True)

    return result.stdout, result.stderr

def analyze_failures(output, error):
    """分析失败原因"""
    failures = []

    # 提取失败的测试
    lines = output.split('\n')
    for line in lines:
        if 'FAILED' in line:
            # 提取测试名
            test_match = re.search(r'(tests/unit/[^:]+::[^:]+::[^:]+)', line)
            if test_match:
                test_name = test_match.group(1)
                failures.append(test_name)

    # 提取错误类型
    error_types = {}
    if error:
        # 常见错误模式
        if 'ImportError' in error:
            error_types['ImportError'] = error.count('ImportError')
        if 'AttributeError' in error:
            error_types['AttributeError'] = error.count('AttributeError')
        if 'TypeError' in error:
            error_types['TypeError'] = error.count('TypeError')
        if 'AssertionError' in error:
            error_types['AssertionError'] = error.count('AssertionError')

    return failures, error_types

def prioritize_failures(failures):
    """为失败测试排序优先级"""
    prioritized = {
        'high': [],      # 核心utils模块
        'medium': [],    # services模块
        'low': [],       # 其他模块
    }

    for test in failures[:20]:  # 只处理前20个
        if 'tests/unit/utils/' in test:
            prioritized['high'].append(test)
        elif 'tests/unit/services/' in test:
            prioritized['medium'].append(test)
        else:
            prioritized['low'].append(test)

    return prioritized

def generate_fix_plan(prioritized, error_types):
    """生成修复计划"""
    plan = []

    # 添加错误类型统计
    if error_types:
        plan.append("## 错误类型统计")
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            plan.append(f"- {error_type}: {count} 个")
        plan.append("")

    # 添加高优先级修复
    if prioritized['high']:
        plan.append("## 🔥 高优先级修复（核心 utils 模块）")
        for i, test in enumerate(prioritized['high'][:10]):
            plan.append(f"{i+1}. {test}")
        plan.append("")

    # 添加中优先级修复
    if prioritized['medium']:
        plan.append("## 📋 中优先级修复（services 模块）")
        for i, test in enumerate(prioritized['medium'][:5]):
            plan.append(f"{i+1}. {test}")
        plan.append("")

    return "\n".join(plan)

def main():
    print("🚀 识别高价值失败测试...")

    # 运行测试收集失败信息
    output, error = run_failing_tests()

    # 分析失败
    failures, error_types = analyze_failures(output, error)

    # 排序优先级
    prioritized = prioritize_failures(failures)

    # 生成修复计划
    plan = generate_fix_plan(prioritized, error_types)

    # 保存报告
    output_dir = Path('docs/_reports/coverage')
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / 'high_value_failures.md', 'w', encoding='utf-8') as f:
        f.write("# 高价值失败测试修复计划\n\n")
        f.write(f"发现 {len(failures)} 个失败测试\n\n")
        f.write(plan)

    print(f"\n✅ 分析完成！")
    print(f"发现 {len(failures)} 个失败测试")
    print(f"高优先级：{len(prioritized['high'])} 个")
    print(f"中优先级：{len(prioritized['medium'])} 个")
    print(f"\n修复计划已保存到：docs/_reports/coverage/high_value_failures.md")

    # 返回前5个高优先级测试
    return prioritized['high'][:5]

if __name__ == '__main__':
    high_priority = main()
    print("\n🎯 立即修复的测试（前5个）：")
    for test in high_priority:
        print(f"  - {test}")