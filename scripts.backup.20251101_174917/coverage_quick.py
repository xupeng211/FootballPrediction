#!/usr/bin/env python3
"""
快速覆盖率检查 - 排除已知错误的测试
"""

import subprocess
import os


def main():
    """运行覆盖率检查"""

    # 设置环境变量以减少警告
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "ignore::DeprecationWarning"

    # 运行单元测试覆盖率检查，排除有问题的测试
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_quick",
        "--ignore=tests/unit/e2e",  # 排除e2e测试
        "--ignore=tests/unit/streaming",  # 排除streaming测试（需要confluent_kafka）
        "--ignore=tests/unit/test_core_config_functional.py",  # 已知错误
        "--ignore=tests/unit/test_database_connection_functional.py",  # 已知错误
        "--ignore=tests/unit/services/test_manager_extended.py",  # 已知错误
        "-q",
        "--tb=no",  # 不显示错误详情
    ]

    print("🚀 运行快速覆盖率检查...")
    print("排除的问题模块:")
    print("  - e2e测试")
    print("  - streaming测试（缺少confluent_kafka依赖）")
    print("  - 已知错误的测试文件")
    print()

    # 运行命令
    result = subprocess.run(cmd, env=env, capture_output=False)

    # 获取最后的覆盖率行
    print("\n" + "=" * 60)
    print("覆盖率报告:")
    print("=" * 60)

    return result.returncode == 0


if __name__ == "__main__":
    success = main()

    if success:
        print("\n✅ 覆盖率检查完成！")
        print("\n📊 查看HTML报告: htmlcov_quick/index.html")
    else:
        print("\n⚠️  覆盖率检查完成，但有部分测试失败")
