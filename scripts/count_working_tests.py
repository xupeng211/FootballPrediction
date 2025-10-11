#!/usr/bin/env python3
"""
统计可以运行的测试数量
"""

import subprocess
from pathlib import Path


def run_test(test_file):
    """运行单个测试文件并返回结果"""
    try:
        # 运行测试，不显示详细输出
        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # 解析输出
        output = result.stdout + result.stderr

        if "passed" in output:
            # 提取通过数
            import re

            passed_match = re.search(r"(\d+) passed", output)
            failed_match = re.search(r"(\d+) failed", output)
            error_match = re.search(r"(\d+) error", output)

            passed = int(passed_match.group(1)) if passed_match else 0
            failed = int(failed_match.group(1)) if failed_match else 0
            errors = int(error_match.group(1)) if error_match else 0

            return {
                "file": test_file,
                "status": "success" if failed == 0 and errors == 0 else "partial",
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": passed + failed + errors,
            }
        else:
            return {"file": test_file, "status": "error", "output": output[:200]}
    except subprocess.TimeoutExpired:
        return {"file": test_file, "status": "timeout", "output": "Test timed out"}
    except Exception as e:
        return {"file": test_file, "status": "exception", "output": str(e)[:200]}


def main():
    """主函数"""
    print("🔍 统计可运行的测试文件...\n")

    test_dir = Path("tests/unit")
    list(test_dir.glob("test_*.py"))

    # 核心测试文件列表
    priority_tests = [
        "test_api_simple.py",
        "test_adapters_base.py",
        "test_adapters_factory.py",
        "test_adapters_registry.py",
        "test_api_dependencies.py",
        "test_api_middleware.py",
        "test_data_validator.py",
        "test_prediction_model.py",
        "test_facade.py",
        "test_api_endpoints.py",
        "test_api_events.py",
    ]

    results = []
    total_passed = 0
    total_failed = 0
    total_errors = 0
    successful_files = 0

    print("测试核心文件...\n")

    # 先测试核心文件
    for test_file in priority_tests:
        file_path = test_dir / test_file
        if file_path.exists():
            print(f"测试 {test_file}...", end=" ")
            result = run_test(str(file_path))
            results.append(result)

            if result["status"] == "success":
                print(f"✅ {result['passed']} passed")
                successful_files += 1
                total_passed += result["passed"]
            elif result["status"] == "partial":
                print(f"⚠️ {result['passed']}/{result['total']} passed")
                successful_files += 1
                total_passed += result["passed"]
                total_failed += result["failed"]
                total_errors += result["errors"]
            else:
                print(f"❌ {result['status']}")
                print(f"   错误: {result.get('output', '')[:100]}...")
        else:
            print(f"⚠️ 文件不存在: {test_file}")

    print("\n" + "=" * 50)
    print("📊 测试统计")
    print("=" * 50)
    print(f"测试文件数: {len(results)}")
    print(f"成功运行的文件: {successful_files}")
    print(f"通过的测试: {total_passed}")
    print(f"失败的测试: {total_failed}")
    print(f"错误的测试: {total_errors}")
    print(f"总计测试: {total_passed + total_failed + total_errors}")

    if total_passed + total_failed + total_errors > 0:
        success_rate = (
            total_passed / (total_passed + total_failed + total_errors)
        ) * 100
        print(f"通过率: {success_rate:.1f}%")

    print("\n🎯 任务 1.3 目标：至少20个测试能够运行")
    if total_passed >= 20:
        print(f"✅ 已达成！当前有 {total_passed} 个测试通过")
    else:
        print(f"⚠️ 还需 {20 - total_passed} 个测试通过")

    # 显示成功测试的文件
    print("\n✅ 成功的测试文件:")
    for result in results:
        if result["status"] in ["success", "partial"]:
            print(f"   - {result['file']}: {result['passed']} passed")


if __name__ == "__main__":
    main()
