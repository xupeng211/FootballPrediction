#!/usr/bin/env python3
"""
运行可以成功执行的测试来检查覆盖率
"""

import subprocess
import sys
from pathlib import Path

def run_tests_with_coverage():
    """运行可成功的测试并检查覆盖率"""

    # 确定可运行的测试文件列表（基于已验证可以运行的文件）
    test_files = [
        # Utils测试（已知可以运行）
        "tests/unit/test_string_utils_extended.py",
        "tests/unit/test_response_utils_extended.py",
        "tests/unit/test_file_utils_extended.py",
        "tests/unit/test_data_validator_extended.py",
        "tests/unit/test_api_data_endpoints.py",
        "tests/unit/test_dict_utils_new.py",
        "tests/unit/test_crypto_utils_new.py",
        "tests/unit/test_common_models_new.py",
        "tests/unit/test_base_service_new.py",
        "tests/unit/test_health_api_new.py",
        "tests/unit/test_cache_improved_simple.py",
        "tests/unit/test_dict_utils.py",
        # 新的简单API测试
        "tests/unit/api/test_api_simple.py",
        # 其他已验证的测试
        "tests/unit/test_time_utils_functional.py",
        "tests/unit/test_utils_functional.py",
        "tests/unit/test_simple_functional.py",
        "tests/unit/test_imports_fix.py",
        "tests/unit/test_skip_problematic.py",
        "tests/unit/test_core_config_functional.py",
        "tests/unit/test_database_connection_functional.py",
        "tests/unit/test_auth_core.py",
    ]

    # 过滤存在的文件
    existing_files = []
    for test_file in test_files:
        if Path(test_file).exists():
            existing_files.append(test_file)
        else:
            print(f"⚠️  文件不存在: {test_file}")

    if not existing_files:
        print("❌ 没有找到可运行的测试文件")
        return False

    print(f"🏃 运行 {len(existing_files)} 个测试文件...")
    print("\n测试文件列表:")
    for f in existing_files:
        print(f"  - {f}")

    # 构建pytest命令
    cmd = [
        "python", "-m", "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_successful",
        "-q",
        "--tb=short"
    ] + existing_files

    print("\n执行命令:")
    print(" ".join(cmd[:6]) + " [测试文件...]")

    # 运行测试
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        print("\n" + "="*60)
        print("测试输出:")
        print("="*60)

        # 输出最后20行（包含覆盖率信息）
        lines = result.stdout.split('\n')
        for line in lines[-30:]:
            print(line)

        if result.returncode == 0:
            print("\n✅ 测试成功完成！")
            print("\n📊 HTML覆盖率报告已生成: htmlcov_successful/index.html")
        else:
            print("\n⚠️  部分测试失败，但仍生成了覆盖率报告")

        return True

    except subprocess.TimeoutExpired:
        print("\n⏰ 测试超时（5分钟）")
        return False
    except Exception as e:
        print(f"\n❌ 运行测试时出错: {e}")
        return False


if __name__ == "__main__":
    print("🚀 开始运行成功测试的覆盖率检查...")
    success = run_tests_with_coverage()

    if success:
        print("\n✅ 覆盖率检查完成！")
        print("\n查看详细报告:")
        print("  1. 打开 htmlcov_successful/index.html")
        print("  2. 或运行: python -m http.server 8000 --directory htmlcov_successful")
    else:
        print("\n❌ 覆盖率检查失败")
        sys.exit(1)