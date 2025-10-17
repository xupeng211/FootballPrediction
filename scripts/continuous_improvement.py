#!/usr/bin/env python3
"""持续改进脚本 - 自动化测试覆盖率提升流程"""

import subprocess
import json
import time
from pathlib import Path

def check_environment():
    """检查环境"""
    print("🔍 检查环境...")

    # 检查虚拟环境
    result = subprocess.run(['python', '-c', 'import sys; print("Python:", sys.version)'], capture_output=True)
    if result.returncode != 0:
        print("❌ Python环境有问题")
        return False

    print("✅ 环境检查通过")
    return True

def quick_test_run():
    """快速测试运行"""
    print("\n🏃 快速测试运行...")

    cmd = [
        'pytest', '-m', 'not slow',
        '--maxfail=5',
        '--tb=no',
        '-q',
        'tests/unit/utils/',
        'tests/unit/services/'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 提取结果
    output = result.stdout + result.stderr
    if 'passed' in output:
        # 提取passed数量
        import re
        match = re.search(r'(\d+) passed', output)
        if match:
            passed = int(match.group(1))
            print(f"✅ 通过: {passed} 个测试")

    if 'failed' in output:
        match = re.search(r'(\d+) failed', output)
        if match:
            failed = int(match.group(1))
            print(f"❌ 失败: {failed} 个测试")

    return result.returncode == 0

def identify_next_action():
    """识别下一步行动"""
    print("\n🎯 识别下一步行动...")

    # 运行覆盖率检查
    cmd = [
        'pytest', '-m', 'not slow',
        '--maxfail=20',
        '--cov=src',
        '--cov-report=json',
        '--cov-report=term-missing',
        '-q'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 解析覆盖率
    output = result.stdout + result.stderr
    for line in output.split('\n'):
        if 'TOTAL' in line and '%' in line:
            parts = line.split()
            if len(parts) >= 6:
                coverage = float(parts[-1].strip('%'))
                break
    else:
        coverage = 0

    print(f"📊 当前覆盖率: {coverage:.1f}%")

    # 根据覆盖率给出建议
    if coverage < 25:
        print("\n📋 建议行动:")
        print("  1. 运行 `python scripts/quick_fix_failures.py` 修复导入错误")
        print("  2. 运行 `pytest tests/unit/utils/test_validators.py -v` 验证修复")
        print("  3. 运行 `python scripts/feedback_loop.py` 查看进度")
    elif coverage < 30:
        print("\n📋 建议行动:")
        print("  1. 创建更多的mock fixtures")
        print("  2. 修复剩余的测试失败")
        print("  3. 激活更多被跳过的测试")
    else:
        print("\n🎉 做得好！")
        print("  1. 可以开始处理0%覆盖的模块")
        print("  2. 优化测试性能")
        print("  3. 考虑将覆盖率门槛调整到30%")

    return coverage

def create_daily_report():
    """创建每日报告"""
    report_path = Path('docs/_reports/coverage/daily_report.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # 运行完整测试
    print("\n📝 生成每日报告...")

    cmd = [
        'pytest', '-m', 'not slow',
        '--maxfail=100',
        '--cov=src',
        '--cov-report=html',
        '--cov-report=json',
        '--cov-report=term-missing'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 读取JSON报告
    try:
        with open('coverage.json', 'r') as f:
            coverage_data = json.load(f)
    except:
        coverage_data = {'totals': {'covered_lines': 0, 'num_statements': 0}}

    # 生成报告
    report = f"""# 每日测试覆盖率报告

## 时间
{time.strftime('%Y-%m-%d %H:%M:%S')}

## 覆盖率统计
- 行覆盖率: {coverage_data.get('totals', {}).get('covered_lines', 0)} / {coverage_data.get('totals', {}).get('num_statements', 0)}
- 总体覆盖率: 待计算

## 最需要覆盖的模块
(需要从HTML报告中提取)

## 今日成就
- 完成的任务:
- 遇到的挑战:
- 下一步计划:

---
*此报告由 continuous_improvement.py 自动生成*
"""

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✅ 报告已生成: {report_path}")

def main():
    """主函数"""
    print("🚀 持续改进流程")
    print("="*50)

    # 环境检查
    if not check_environment():
        return

    # 快速测试
    quick_test_run()

    # 识别下一步
    coverage = identify_next_action()

    # 每小时提示
    print("\n⏰ 提醒:")
    print("  - 每小时运行一次 `python scripts/feedback_loop.py`")
    print("  - 每天运行一次 `python scripts/continuous_improvement.py`")
    print("  - 使用 `make test-quick` 进行快速验证")

    # 创建报告（如果需要）
    import sys
    if '--report' in sys.argv:
        create_daily_report()

if __name__ == '__main__':
    main()