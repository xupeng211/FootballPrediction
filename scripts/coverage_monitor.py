#!/usr/bin/env python3
"""
测试覆盖率监控脚本
Test Coverage Monitor Script
"""

import json
import subprocess
import sys
from pathlib import Path

def check_coverage(threshold: float = 70.0):
    """检查测试覆盖率"""
    try:
        # 运行覆盖率测试
        result = subprocess.run([
            'python3', '-m', 'pytest',
            '--cov=src',
            '--cov-report=json',
            '--tb=no'
        ], capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print("❌ 测试执行失败")
            return False

        # 读取覆盖率报告
        with open('coverage.json', 'r') as f:
            coverage_data = json.load(f)

        total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)

        print(f"📊 当前覆盖率: {total_coverage:.1f}%")
        print(f"🎯 目标覆盖率: {threshold:.1f}%")

        if total_coverage >= threshold:
            print("✅ 覆盖率达标")
            return True
        else:
            print(f"⚠️ 覆盖率未达标，需要提升 {(threshold - total_coverage):.1f}%")
            return False

    except Exception as e:
        print(f"❌ 覆盖率检查失败: {e}")
        return False

if __name__ == '__main__':
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 70.0
    success = check_coverage(threshold)
    sys.exit(0 if success else 1)
