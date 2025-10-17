#!/usr/bin/env python3
"""最后冲刺到30%覆盖率的脚本"""

import subprocess
import sys

def run_boost():
    """运行最后冲刺"""

    # 专门针对低覆盖率但重要的模块
    test_modules = [
        "config_loader",  # 18%
        "crypto_utils",   # 25%
        "validators",     # 28-30%
        "dict_utils",     # 27%
        "file_utils",     # 31%
        "helpers",        # 56%
        "response",       # 49%
        "string_utils",   # 48%
        "time_utils",     # 72%
    ]

    # 构建测试命令
    cmd = [
        "python", "-m", "pytest",
        "tests/unit/utils/",
        "--cov=src",
        "--cov-report=term-missing",
        "--tb=no",
        "-q",
        "--maxfail=5",
        "-k"
    ]

    # 添加过滤器
    filter_expr = " or ".join([
        "test_config_loader",
        "test_crypto_utils",
        "test_validators",
        "test_dict_utils",
        "test_file_utils",
        "test_helpers",
        "test_response",
        "test_string_utils",
        "test_time_utils"
    ])

    cmd.append(filter_expr)

    print("🚀 最后冲刺到30%覆盖率")
    print("=" * 50)
    print(f"运行命令: {' '.join(cmd[:6])} -k '{filter_expr}'")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        print("\n" + result.stdout)

        # 检查覆盖率
        if "TOTAL" in result.stdout:
            for line in result.stdout.split('\n'):
                if line.startswith('TOTAL'):
                    parts = line.split()
                    coverage = float(parts[3].rstrip('%'))
                    print(f"\n📊 最终覆盖率: {coverage}%")

                    if coverage >= 30:
                        print("🎉 成功达到30%覆盖率目标！")
                        return True
                    else:
                        print(f"⚠️  覆盖率未达到30%，当前为: {coverage}%")
                        print(f"距离目标还差: {30 - coverage:.2f}%")
                        return False

        return False

    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    success = run_boost()
    sys.exit(0 if success else 1)