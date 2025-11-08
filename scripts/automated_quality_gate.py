#!/usr/bin/env python3
"""
自动化质量门禁脚本 - 简化版本
"""

import subprocess
import sys


def run_syntax_check():
    """运行语法检查"""
    try:
        result = subprocess.run([
            'python3', '-m', 'py_compile', 'src/'
        ], capture_output=True, text=True)

        return {
            'status': 'pass' if result.returncode == 0 else 'fail',
            'errors_fixed': 0,
            'recommendations': [] if result.returncode == 0 else ['修复语法错误']
        }
    except Exception:
        return {
            'status': 'fail',
            'errors_fixed': 0,
            'recommendations': ['检查Python环境']
        }

def run_quality_check():
    """运行质量检查"""
    try:
        result = subprocess.run([
            'ruff', 'check', 'src/', 'tests/', '--format=json'
        ], capture_output=True, text=True)

        return {
            'status': 'pass' if result.returncode == 0 else 'fail',
            'issues_count': result.returncode,
            'metrics': {'overall_score': 85 if result.returncode == 0 else 70}
        }
    except Exception:
        return {
            'status': 'fail',
            'issues_count': 999,
            'metrics': {'overall_score': 0}
        }

if __name__ == '__main__':

    # 语法检查
    syntax_result = run_syntax_check()

    # 质量检查
    quality_result = run_quality_check()

    # 综合结果
    overall_status = 'pass' if (syntax_result['status'] == 'pass' and
                               quality_result['status'] == 'pass') else 'fail'

    sys.exit(0 if overall_status == 'pass' else 1)
