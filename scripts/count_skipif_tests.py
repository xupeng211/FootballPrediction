#!/usr/bin/env python3
"""
统计 @pytest.mark.skipif 跳过的测试脚本
"""

import subprocess
import re
import os


def get_test_modules():
    """获取所有测试模块"""
    test_modules = []
    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file))
                test_modules.append(rel_path)
    return test_modules


def count_skipif_in_file(filepath):
    """统计文件中的 skipif 数量"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 统计 @pytest.mark.skipif
        skipif_count = len(re.findall(r'@pytest\.mark\.skipif', content))

        # 统计 pytest.mark.skipif(True) - 这些是永久跳过的
        always_skip_count = len(re.findall(r'@pytest\.mark\.skipif\(True', content))

        return skipif_count, always_skip_count
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0, 0


def analyze_skipif_reasons():
    """分析跳过原因"""
    reasons = {}

    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 查找所有 skipif 及其原因
                    matches = re.findall(r'@pytest\.mark\.skipif\([^)]+, reason="([^"]+)"\)', content)
                    for reason in matches:
                        reasons[reason] = reasons.get(reason, 0) + 1
                except:
                    pass

    return reasons


def main():
    print("=" * 60)
    print("Phase 2 - @pytest.mark.skipif 统计分析")
    print("=" * 60)

    # 统计所有 skipif
    total_skipif = 0
    total_always_skip = 0
    test_files = 0

    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                filepath = os.path.join(root, file)
                skipif, always_skip = count_skipif_in_file(filepath)
                if skipif > 0:
                    print(f"{filepath}: {skipif} skipif (其中 {always_skip} 永久跳过)")
                total_skipif += skipif
                total_always_skip += always_skip
                test_files += 1

    print("\n" + "=" * 60)
    print("统计结果:")
    print(f"  测试文件总数: {test_files}")
    print(f"  总 skipif 数量: {total_skipif}")
    print(f"  永久跳过 (skipif=True): {total_always_skip}")
    print(f"  条件跳过: {total_skipif - total_always_skip}")

    # 分析跳过原因
    print("\n跳过原因分析:")
    reasons = analyze_skipif_reasons()
    sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)

    for reason, count in sorted_reasons[:10]:  # 显示前10个
        print(f"  {count}: {reason}")

    # 运行一个实际测试来验证
    print("\n" + "=" * 60)
    print("运行实际测试验证...")

    # 选择一些代表性模块
    sample_modules = [
        "tests/unit/api/test_health.py",
        "tests/unit/api/test_features.py",
        "tests/unit/cache/test_ttl_cache_enhanced.py",
        "tests/unit/core/test_logger.py"
    ]

    actual_skipped = 0
    actual_run = 0

    for module in sample_modules:
        if os.path.exists(module):
            print(f"\n检查: {module}")
            result = subprocess.run(
                ["pytest", module, "-v", "--disable-warnings", "--tb=no"],
                capture_output=True,
                text=True
            )

            skipped = len(re.findall(r"SKIPPED", result.stdout))
            passed = len(re.findall(r"PASSED", result.stdout))
            failed = len(re.findall(r"FAILED", result.stdout))
            errors = len(re.findall(r"ERROR", result.stdout))

            run = passed + failed + errors
            actual_skipped += skipped
            actual_run += run

            print(f"  跳过: {skipped}, 运行: {run}")

    if actual_run > 0:
        skip_percentage = (actual_skipped / (actual_skipped + actual_run)) * 100
        print(f"\n实际跳过率: {skip_percentage:.2f}%")

    print("\n" + "=" * 60)
    print("结论:")
    if total_skipif < 100:
        print("✅ Phase 2 目标达成：skipif 数量 < 100")
    else:
        print(f"⚠️  Phase 2 需要继续优化：当前 skipif 数量 {total_skipif} >= 100")

    print("=" * 60)


if __name__ == "__main__":
    main()