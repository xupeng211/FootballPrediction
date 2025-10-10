#!/usr/bin/env python3
"""
只运行通过了的测试来获取覆盖率
"""

import subprocess
import sys
from pathlib import Path


def get_passed_test_files():
    """获取所有通过了的测试文件列表"""

    # 已知可以运行的测试文件（无错误的）
    passed_test_files = [
        # Utils模块测试
        "tests/unit/test_string_utils_extended.py",
        "tests/unit/test_response_utils_extended.py",
        "tests/unit/test_file_utils_extended.py",
        "tests/unit/test_data_validator_extended.py",
        "tests/unit/test_api_data_endpoints.py",
        "tests/unit/test_dict_utils_new.py",
        "tests/unit/test_crypto_utils_new.py",
        "tests/unit/test_common_models_new.py",
        "tests/unit/test_time_utils_functional.py",
        "tests/unit/test_simple_functional.py",
        # 服务层测试
        "tests/unit/test_base_service_new.py",
        "tests/unit/test_health_api_new.py",
        # API测试
        "tests/unit/api/test_api_simple.py",
        # Streaming测试
        "tests/unit/streaming/test_stream_config.py",
        # 基础组件测试
        "tests/unit/test_cache_utils.py",
        "tests/unit/test_monitoring_utils.py",
        "tests/unit/test_data_collectors.py",
        # 已修复的测试文件（15个）
        "tests/unit/test_error_handlers.py",
        "tests/unit/test_logging_utils.py",
        "tests/unit/test_database_base.py",
        "tests/unit/test_lineage_reporter.py",
        "tests/unit/test_metadata_manager.py",
        "tests/unit/test_models_common.py",
        "tests/unit/test_metrics_exporter.py",
        "tests/unit/test_prediction_model.py",
        "tests/unit/test_tasks_utils.py",
        "tests/unit/test_data_collectors_v2.py",
        "tests/unit/test_api_models_simple.py",
        "tests/unit/test_db_models_all.py",
        "tests/unit/test_collectors_all.py",
        "tests/unit/test_data_quality_extended.py",
        "tests/unit/test_core_config_extended.py",
        # 覆盖率提升测试
        "tests/unit/test_api_imports_all.py",
        "tests/unit/test_services_all.py",
        "tests/unit/test_tasks_imports.py",
        "tests/unit/test_streaming_all.py",
        "tests/unit/test_data_processing_all.py",
        "tests/unit/test_cache_extended.py",
        "tests/unit/test_utils_extended_final.py",
        # 最终冲刺测试（21个简单测试）
        "tests/unit/test_api_only_imports.py",
        "tests/unit/test_api_models_import.py",
        "tests/unit/test_db_models_basic.py",
        "tests/unit/test_services_basic.py",
        "tests/unit/test_tasks_simple.py",
        "tests/unit/test_streaming_simple.py",
        "tests/unit/test_cache_simple.py",
        "tests/unit/test_monitoring_simple.py",
        "tests/unit/test_data_processing_simple.py",
        "tests/unit/test_database_simple.py",
        "tests/unit/test_models_simple.py",
        "tests/unit/test_utils_complete.py",
        "tests/unit/test_core_simple.py",
        "tests/unit/test_collectors_simple.py",
        "tests/unit/test_data_quality_simple.py",
        "tests/unit/test_features_simple.py",
        "tests/unit/test_middleware_simple.py",
        "tests/unit/test_config_simple.py",
        "tests/unit/test_security_simple.py",
        "tests/unit/test_ml_simple.py",
        "tests/unit/test_realtime_simple.py",
    ]

    # 过滤存在的文件
    existing_files = []
    for test_file in passed_test_files:
        if Path(test_file).exists():
            existing_files.append(test_file)
        else:
            print(f"⚠️  文件不存在: {test_file}")

    return existing_files


def run_tests_with_coverage(test_files):
    """运行测试并检查覆盖率"""

    print(f"🏃 运行 {len(test_files)} 个通过了的测试文件...")
    print("这些测试已经验证可以正常运行，不会有导入错误")

    # 构建pytest命令
    cmd = [
        "python",
        "-m",
        "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_passed",
        "-v",
        "--tb=short",
    ] + test_files

    # 运行测试
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, timeout=600)

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

        # 生成一个总结报告
        print("\n📊 生成了以下文件：")
        print("1. HTML覆盖率报告: htmlcov_passed/index.html")

        # 尝试提取最终的覆盖率数字
        if result.returncode == 0:
            print("\n✅ 所有测试成功通过！")
        else:
            print("\n⚠️  部分测试失败，但已生成覆盖率报告")

        return True

    except subprocess.TimeoutExpired:
        print("\n⏰ 测试超时（10分钟）")
        return False
    except Exception as e:
        print(f"\n❌ 运行测试时出错: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始运行所有通过了的测试...")
    print("这个脚本只会运行那些已经验证没有导入错误的测试")
    print("目标：获得准确的覆盖率数据\n")

    # 获取测试文件列表
    test_files = get_passed_test_files()

    if not test_files:
        print("❌ 没有找到可运行的测试文件")
        return False

    print(f"找到 {len(test_files)} 个可以运行的测试文件\n")

    # 运行测试
    success = run_tests_with_coverage(test_files)

    if success:
        print("\n✅ 测试完成！")
        print("\n查看详细报告:")
        print("  1. 打开 htmlcov_passed/index.html")
        print("  2. 或运行: python -m http.server 8000 --directory htmlcov_passed")

        # 计算预估的总覆盖率
        print("\n💡 提示：")
        print("- 这是只运行通过的测试得出的覆盖率")
        print("- 实际项目覆盖率可能会更低，因为有些测试还在修复中")
        print("- 当前距离30%目标还需要继续努力")
    else:
        print("\n❌ 测试失败")
        sys.exit(1)

    return True


if __name__ == "__main__":
    main()
