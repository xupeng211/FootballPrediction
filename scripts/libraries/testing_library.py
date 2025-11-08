#!/usr/bin/env python3
"""
统一测试工具库
"""

import re
import subprocess


class QuickTestRunner:
    """快速测试运行器"""

    def run_tests(self, test_path=None, coverage=False):
        """运行测试"""
        cmd = ["python3", "-m", "pytest"]

        if test_path:
            cmd.append(test_path)

        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])

        cmd.extend(["-q", "--tb=short"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # 解析结果
            passed = self._extract_count(result.stdout + result.stderr, r"(\d+) passed")
            failed = self._extract_count(result.stdout + result.stderr, r"(\d+) failed")

            return {
                "success": result.returncode == 0,
                "passed": passed,
                "failed": failed,
                "output": result.stdout + result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_count(self, text, pattern):
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0

def quick_test(test_path=None):
    """快速测试"""
    runner = QuickTestRunner()
    return runner.run_tests(test_path)

def quick_coverage_test(test_path=None):
    """快速覆盖率测试"""
    runner = QuickTestRunner()
    return runner.run_tests(test_path, coverage=True)
