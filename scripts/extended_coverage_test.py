#!/usr/bin/env python3
"""
扩展覆盖率测试工具
基于稳定基线，逐步扩展测试覆盖率
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime


def run_extended_coverage_test():
    """运行扩展覆盖率测试"""
    print("🚀 运行扩展覆盖率测试...")

    # 定义扩展测试套件（基线 + 新增）
    extended_tests = [
        # 基线测试
        "tests/unit/services/test_services_basic.py",
        "tests/unit/adapters/test_registry.py",
        # 新增预测算法测试（32个测试全部通过！）
        "tests/unit/domain/test_prediction_algorithms_comprehensive.py",
        # API基础设施测试（18个测试通过，1个失败）
        "tests/unit/api/test_app_infrastructure_fixed.py",
        # 标准库覆盖测试（23个测试通过）
        "tests/unit/test_final_coverage_push.py",
        # 额外的小型测试文件（15个测试全部通过）
        "tests/unit/test_observers.py",
        "tests/unit/test_checks.py",
        "tests/unit/test_schemas.py",
        "tests/unit/test_utils_complete.py",
        # 新增适配器测试文件（高质量测试）
        "tests/unit/adapters/test_factory.py",  # 29个测试通过
        "tests/unit/adapters/test_base.py",  # 26个测试通过
        # 新发现的高质量API测试文件
        "tests/unit/api/test_core_functionality.py",  # 17个测试通过，5个失败
        # 新发现的高质量工具测试文件
        "tests/unit/utils/test_crypto_utils_simple.py",  # 20个测试通过，2个失败
        # 新发现的高质量域服务测试文件
        "tests/unit/domain/services/test_team_service.py",  # 6个测试全部通过！
        "tests/unit/domain/services/test_scoring_service.py",  # 16个测试通过，部分失败
        # 高质量大型API测试文件
        "tests/unit/api/test_data_router_comprehensive.py",  # 41个测试通过，3个失败
        "tests/unit/api/test_predictions_router_comprehensive.py",  # 41个测试全部通过！
    ]

    print(f"📋 运行 {len(extended_tests)} 个扩展测试...")

    # 运行测试并生成覆盖率报告
    cmd = [
        "python",
        "-m",
        "pytest",
        *extended_tests,
        "--cov=src",
        "--cov-report=json",
        "--cov-report=term-missing",
        "--tb=short",
        "-q",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print("❌ 测试执行失败")
            print("错误输出:")
            print(result.stderr)
            return None

        # 读取覆盖率报告
        with open("coverage.json", "r") as f:
            coverage_data = json.load(f)

        totals = coverage_data.get("totals", {})
        coverage_percent = totals.get("percent_covered", 0)
        covered_lines = totals.get("covered_lines", 0)
        total_lines = totals.get("num_statements", 0)

        # 读取基线数据
        baseline_file = Path("reports/stable_coverage_baseline.json")
        baseline_data = {}
        if baseline_file.exists():
            with open(baseline_file, "r") as f:
                baseline_data = json.load(f)

        print("\n" + "=" * 60)
        print("📊 扩展覆盖率报告")
        print("=" * 60)
        print(f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 当前覆盖率: {coverage_percent:.2f}%")
        print(f"📝 覆盖行数: {covered_lines:,}")
        print(f"📄 总代码行数: {total_lines:,}")
        print(f"🧪 测试文件: {len(extended_tests)} 个")

        # 与基线比较
        if baseline_data:
            baseline_coverage = baseline_data["coverage_percent"]
            improvement = coverage_percent - baseline_coverage
            print(f"📊 基线覆盖率: {baseline_coverage:.2f}%")
            print(f"📈 改进幅度: {improvement:+.2f}%")

            if improvement > 0.5:
                print("✅ 覆盖率有显著提升")
            elif improvement > 0:
                print("➡️ 覆盖率小幅提升")
            elif improvement < -0.5:
                print("⚠️ 覆盖率有所下降")
            else:
                print("➡️ 覆盖率基本稳定")

        # 检查15%目标
        if coverage_percent >= 15.0:
            print("🎉 恭喜！已达到15%覆盖率目标！")
        elif coverage_percent >= 14.0:
            print("📈 接近15%目标，继续努力！")
        else:
            print("📊 需要继续改进以达到15%目标")

        # 显示关键模块覆盖率
        files = coverage_data.get("files", {})
        key_modules = {
            "src/utils/string_utils.py": "字符串工具",
            "src/services/": "服务模块",
            "src/adapters/": "适配器模块",
            "src/core/": "核心模块",
            "src/api/": "API模块",
        }

        print("\n🏆 关键模块覆盖率:")
        for module_path, desc in key_modules.items():
            matching_files = [
                (file_path, file_data["summary"]["percent_covered"])
                for file_path, file_data in files.items()
                if file_path.startswith(module_path)
            ]

            if matching_files:
                avg_coverage = sum(percent for _, percent in matching_files) / len(matching_files)
                print(f"  📁 {desc:<20} {avg_coverage:6.2f}% ({len(matching_files)} 个文件)")

        print("=" * 60)

        # 保存扩展测试数据
        extended_data = {
            "timestamp": datetime.now().isoformat(),
            "coverage_percent": coverage_percent,
            "covered_lines": covered_lines,
            "total_lines": total_lines,
            "test_files": extended_tests,
            "baseline_comparison": baseline_data,
        }

        extended_file = Path("reports/extended_coverage_test.json")
        extended_file.parent.mkdir(exist_ok=True)

        with open(extended_file, "w", encoding="utf-8") as f:
            json.dump(extended_data, f, indent=2, ensure_ascii=False)

        print(f"💾 扩展测试数据已保存: {extended_file}")
        return extended_data

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return None


def main():
    """主函数"""
    print("🚀 启动扩展覆盖率测试工具")

    data = run_extended_coverage_test()
    return data is not None


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
