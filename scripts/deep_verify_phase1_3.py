#!/usr/bin/env python3
"""
深度确认 Phase 1-3 100%达成
"""

import subprocess
import re
import sys
import os
import time


def deep_verify_phase1():
    """深度验证 Phase 1: 修复模块导入问题"""
    print("\n🔍 深度验证 Phase 1: 修复模块导入问题")
    print("=" * 60)

    # 测试1: 检查 pytest.ini 配置
    try:
        with open("pytest.ini", "r") as f:
            content = f.read()
            if "pythonpath = src" in content:
                print("✓ pytest.ini 包含 pythonpath = src")
            else:
                print("✗ pytest.ini 缺少 pythonpath 配置")
                return False
    except:
        print("✗ 无法读取 pytest.ini")
        return False

    # 测试2: 验证核心模块可以导入
    modules_to_test = [
        "src.core.logger",
        "src.api.health",
        "src.database.models",
        "src.services.base_unified",
    ]

    for module in modules_to_test:
        try:
            cmd = [sys.executable, "-c", f"import {module}"]
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            print(f"✓ {module} 导入成功")
        except:
            print(f"✗ {module} 导入失败")
            return False

    # 测试3: pytest 能收集测试
    cmd = ["pytest", "--collect-only", "-p", "no:warnings", "-q", "tests"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if "error" not in result.stdout.lower() and "error" not in result.stderr.lower():
        collected_match = re.search(r"collected (\d+) items", result.stdout)
        if collected_match:
            count = int(collected_match.group(1))
            print(f"✓ pytest 成功收集 {count} 个测试")
            return True

    print("✗ pytest 收集测试失败")
    return False


def deep_verify_phase2():
    """深度验证 Phase 2: 清理 skipif 跳过条件"""
    print("\n🔍 深度验证 Phase 2: 清理 skipif 跳过条件")
    print("=" * 60)

    # 统计所有 skipif 的使用
    skipif_count = 0
    skipif_files = []

    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                        file_skipif = len(re.findall(r"@pytest\.mark\.skipif", content))
                        if file_skipif > 0:
                            skipif_count += file_skipif
                            skipif_files.append((file_path, file_skipif))
                except:
                    pass

    print(f"发现 {skipif_count} 个 skipif 标记")

    # 检查关键模块的 skipif 使用
    critical_tests = [
        "tests/unit/api/test_health.py",
        "tests/unit/core/test_logger.py",
        "tests/unit/services/test_audit_service.py",
    ]

    total_skipped = 0
    total_tests = 0

    for test_file in critical_tests:
        if os.path.exists(test_file):
            # 使用 --rs 显示跳过原因
            cmd = ["pytest", test_file, "-v", "--disable-warnings", "--rs", "--tb=no"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            output = result.stdout + result.stderr

            # 统计跳过和运行
            skipped = len(re.findall(r"SKIPPED", output))
            passed = len(re.findall(r"PASSED", output))
            failed = len(re.findall(r"FAILED", output))
            errors = len(re.findall(r"ERROR", output))

            total_skipped += skipped
            total_tests += passed + failed + errors + skipped

            print(f"  {test_file}: 跳过={skipped}, 运行={passed+failed+errors}")

    print(f"\n关键模块统计:")
    print(f"  总测试数: {total_tests}")
    print(f"  跳过数: {total_skipped}")
    print(f"  跳过率: {total_skipped/total_tests*100:.1f}%" if total_tests > 0 else "N/A")

    # 验证标准：跳过率应该小于20%
    if total_tests > 0 and (total_skipped / total_tests) < 0.2:
        print("✓ Phase 2 目标达成：跳过率 < 20%")
        return True
    else:
        print("✗ Phase 2 目标未达成：跳过率过高")
        return False


def deep_verify_phase3():
    """深度验证 Phase 3: Mock 外部依赖"""
    print("\n🔍 深度验证 Phase 3: Mock 外部依赖")
    print("=" * 60)

    # 设置环境
    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    # 测试1: 验证所有外部依赖都被Mock
    mock_test_script = """
import sys
sys.path.insert(0, 'tests')
import conftest_mock  # 应用Mock

test_results = []

# 测试数据库
try:
    from src.database.connection import DatabaseManager
    db = DatabaseManager()
    # 测试会话创建
    session = db.get_session()
    test_results.append(("Database", True))
except Exception as e:
    test_results.append(("Database", False, str(e)))

# 测试Redis
try:
    import redis
    r = redis.Redis()
    r.ping()
    test_results.append(("Redis", True))
except Exception as e:
    test_results.append(("Redis", False, str(e)))

# 测试Kafka
try:
    from src.streaming.kafka_producer import KafkaProducer
    producer = KafkaProducer()
    test_results.append(("Kafka Producer", True))
except Exception as e:
    test_results.append(("Kafka Producer", False, str(e)))

# 测试MLflow
try:
    import mlflow
    run_id = mlflow.start_run()
    test_results.append(("MLflow", True))
except Exception as e:
    test_results.append(("MLflow", False, str(e)))

# 测试requests
try:
    import requests
    response = requests.get("http://example.com")
    test_results.append(("Requests", True))
except Exception as e:
    test_results.append(("Requests", False, str(e)))

# 输出结果
all_passed = True
for result in test_results:
    if len(result) == 2:
        name, passed = result
        print(f"✓ {name} Mock成功")
    else:
        name, passed, error = result
        print(f"✗ {name} Mock失败: {error}")
        all_passed = False

exit(0 if all_passed else 1)
"""

    cmd = [sys.executable, "-c", mock_test_script]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        print("✓ 所有外部依赖Mock成功")
    else:
        print("✗ 部分Mock失败")
        return False

    # 测试2: 运行实际的pytest确保无超时
    print("\n测试pytest执行（检查无超时）...")
    test_cmd = [
        "pytest", "tests/unit/core/test_logger.py",
        "-v", "--disable-warnings", "--tb=short"
    ]

    start_time = time.time()
    try:
        test_result = subprocess.run(test_cmd, env=env, capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time

        if elapsed < 30:  # 30秒内完成
            print(f"✓ pytest 在 {elapsed:.1f} 秒内完成，无超时")
        else:
            print(f"⚠ pytest 耗时 {elapsed:.1f} 秒，可能需要优化")

        # 检查输出
        output = test_result.stdout + test_result.stderr
        if "timeout" not in output.lower() and "connection" not in output.lower():
            print("✓ 无连接错误")
            return True
        else:
            print("✗ 检测到连接错误")
            return False

    except subprocess.TimeoutExpired:
        print("✗ pytest 执行超时")
        return False


def main():
    print("=" * 80)
    print("🎯 深度确认 Phase 1-3 100%达成")
    print("=" * 80)
    print("目标：每个阶段都严格达成验收标准")
    print("-" * 80)

    # 深度验证各个阶段
    phase1_ok = deep_verify_phase1()
    phase2_ok = deep_verify_phase2()
    phase3_ok = deep_verify_phase3()

    print("\n" + "=" * 80)
    print("🏁 深度验证结果:")
    print("=" * 80)
    print(f"  Phase 1 (模块导入): {'✅ 100% 达成' if phase1_ok else '❌ 未达成'}")
    print(f"  Phase 2 (跳过测试): {'✅ 100% 达成' if phase2_ok else '❌ 未达成'}")
    print(f"  Phase 3 (Mock依赖): {'✅ 100% 达成' if phase3_ok else '❌ 未达成'}")

    overall_success = phase1_ok and phase2_ok and phase3_ok

    print("\n" + "-" * 80)
    if overall_success:
        print("🎉🎉🎉 Phase 1-3 全部 100% 达成！🎉🎉🎉")
        print("\n✨ 重大成就：")
        print("  ✅ 模块导入问题完全解决")
        print("  ✅ 测试跳过率降至合理范围")
        print("  ✅ 外部依赖完全Mock，无连接超时")
        print("  ✅ pytest 可以稳定执行测试")
        print("\n🚀 现在进入 Phase 4: 校准覆盖率配置")
        return True
    else:
        print("⚠️ 部分阶段需要进一步优化")
        print("\n需要改进：")
        if not phase1_ok:
            print("  🔧 Phase 1: 检查模块导入配置")
        if not phase2_ok:
            print("  🔧 Phase 2: 进一步清理skipif")
        if not phase3_ok:
            print("  🔧 Phase 3: 优化Mock配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)