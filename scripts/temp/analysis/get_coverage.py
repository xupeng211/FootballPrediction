#!/usr/bin/env python3
"""简单的覆盖率提取脚本."""

import subprocess
import sys


def get_coverage():
    """获取测试覆盖率."""
    try:
        result = subprocess.run(
            [
                "pytest",
                "tests/unit/utils/test_string_utils.py",
                "--cov=src.utils.string_utils",
                "--cov-report=term",
            ],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction",
        )

        lines = result.stdout.split("\n")
        coverage_line = ""

        for line in lines:
            if "src/utils/string_utils.py" in line and "%" in line:
                coverage_line = line.strip()
                break
            elif "TOTAL" in line and "covered" in line.lower():
                coverage_line = line.strip()

        return coverage_line

    except Exception as e:
        print(f"Error running tests: {e}")
        return ""


if __name__ == "__main__":
    coverage = get_coverage()
    if coverage:
        print(f"Coverage: {coverage}")
    else:
        print("Could not extract coverage information")
