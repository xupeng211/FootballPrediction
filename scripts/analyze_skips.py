#!/usr/bin/env python3
"""分析测试跳过情况"""

import subprocess
import re
import json
from collections import defaultdict
from pathlib import Path

def run_pytest_collect():
    """运行pytest收集跳过的测试"""
    cmd = [
        'pytest', '-m', 'not slow', '-v', '--tb=no',
        '-r', 's', '--maxfail=1000'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr

def parse_skips(output):
    """解析跳过的测试"""
    skips = []
    lines = output.split('\n')

    for line in lines:
        # 匹配跳过的测试行
        if 'SKIPPED' in line:
            # 提取测试名和原因
            parts = line.split('SKIPPED')
            test_name = parts[0].strip()

            # 查找跳过原因
            reason = ''
            if len(parts) > 1:
                # 提取括号中的原因
                match = re.search(r'\[(.*?)\]', parts[1])
                if match:
                    reason = match.group(1)

            if test_name and '::' in test_name:
                skips.append({
                    'test': test_name,
                    'reason': reason or '未指定原因',
                    'file': test_name.split('::')[0]
                })

    return skips

def analyze_reasons(skips):
    """分析跳过原因"""
    reasons = defaultdict(list)
    file_skips = defaultdict(list)

    for skip in skips:
        reason = skip['reason']
        file_path = skip['file']

        reasons[reason].append(skip['test'])
        file_skips[file_path].append(skip)

    # 统计最常见的跳过原因
    top_reasons = sorted(
        [(reason, len(tests)) for reason, tests in reasons.items()],
        key=lambda x: x[1],
        reverse=True
    )

    # 统计跳过最多的文件
    top_files = sorted(
        [(file, len(tests)) for file, tests in file_skips.items()],
        key=lambda x: x[1],
        reverse=True
    )

    return {
        'reasons': dict(reasons),
        'file_skips': dict(file_skips),
        'top_reasons': top_reasons[:10],
        'top_files': top_files[:20]
    }

def main():
    print("🔍 分析测试跳过情况...")

    # 运行pytest收集
    print("收集测试信息...")
    stdout, stderr = run_pytest_collect()

    # 解析跳过的测试
    skips = parse_skips(stdout)

    # 分析原因
    analysis = analyze_reasons(skips)

    # 生成报告
    report = {
        'total_collected': stdout.count('collected') if 'collected' in stdout else 0,
        'total_skipped': len(skips),
        'skip_rate': f"{len(skips) / max(1, stdout.count('collected')) * 100:.1f}%",
        'analysis': analysis
    }

    # 保存报告
    output_dir = Path('docs/_reports/coverage')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存JSON
    with open(output_dir / 'skip_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 生成摘要报告
    with open(output_dir / 'skip_summary.md', 'w', encoding='utf-8') as f:
        f.write("# 测试跳过情况分析报告\n\n")
        f.write(f"## 概览\n")
        f.write(f"- 总测试数：{report['total_collected']}\n")
        f.write(f"- 跳过测试数：{report['total_skipped']}\n")
        f.write(f"- 跳过率：{report['skip_rate']}\n\n")

        f.write("## 主要跳过原因（Top 10）\n\n")
        for reason, count in report['analysis']['top_reasons']:
            f.write(f"- **{reason}**：{count} 个测试\n")

        f.write("\n## 跳过最多的文件（Top 20）\n\n")
        for file_path, count in report['analysis']['top_files']:
            f.write(f"- `{file_path}`：{count} 个测试\n")

    print(f"\n✅ 分析完成！")
    print(f"发现 {len(skips)} 个跳过的测试")
    print(f"报告已保存到：docs/_reports/coverage/skip_summary.md")

if __name__ == '__main__':
    main()