#!/usr/bin/env python3
"""
持续覆盖率守护脚本
自动监控覆盖率并提供建议
"""

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import sys


def get_current_coverage():
    """获取当前覆盖率"""
    try:
        result = subprocess.run(
            ["coverage", "report", "--format=json"], capture_output=True, text=True
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        return data["totals"]["percent_covered"]
    except Exception as e:
        print(f"获取覆盖率失败: {e}")
        return None


def get_low_coverage_files(threshold=30):
    """获取低覆盖率的文件"""
    try:
        result = subprocess.run(["coverage", "report"], capture_output=True, text=True)

        low_files = []
        for line in result.stdout.split("\n"):
            if line.strip() and "src/" in line and not line.startswith("Name"):
                parts = re.split(r"\s+", line.strip())
                if len(parts) >= 4:
                    filename = parts[0]
                    coverage_str = parts[3].replace("%", "")

                    try:
                        coverage = int(coverage_str)
                        if coverage < threshold:
                            low_files.append({"file": filename, "coverage": coverage})
                    except ValueError:
                        continue

        return low_files
    except Exception as e:
        print(f"分析低覆盖率文件失败: {e}")
        return []


def generate_coverage_report():
    """生成覆盖率报告"""
    coverage = get_current_coverage()

    if coverage is None:
        print("❌ 无法获取覆盖率数据")
        return

    print(f"\n{'='*60}")
    print(f"📊 覆盖率守护报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    print(f"\n🎯 当前覆盖率: {coverage:.2f}%")

    # 覆盖率状态
    if coverage >= 50:
        print("✅ 优秀！覆盖率已达到50%以上")
    elif coverage >= 40:
        print("🟡 良好！覆盖率已达到40%以上")
    elif coverage >= 30:
        print("🟠 及格！覆盖率已达到30%以上")
    elif coverage >= 25:
        print("🔴 需改进：覆盖率刚过25%门槛")
    else:
        print("❌ 警告：覆盖率低于25%门槛")

    # 分析低覆盖率文件
    low_files = get_low_coverage_files()

    if low_files:
        print("\n📋 低覆盖率文件（<30%）:")
        print("   文件名                                      覆盖率")
        print("   ------------------------------------------------")

        for file_info in low_files[:10]:  # 只显示前10个
            filename = file_info["file"]
            coverage = file_info["coverage"]
            print(f"   {filename:<45} {coverage:>3}%")

        if len(low_files) > 10:
            print(f"   ... 还有 {len(low_files) - 10} 个文件")

    # 提供改进建议
    print("\n💡 改进建议:")

    if coverage < 25:
        print("   1. 优先为0%覆盖率文件创建基础测试")
        print("   2. 运行 python scripts/analyze_zero_coverage.py 分析")
        print("   3. 使用 python scripts/auto_generate_tests.py 生成测试")

    if 25 <= coverage < 30:
        print("   1. 覆盖率刚刚达标，继续提升")
        print("   2. 专注于核心业务逻辑测试")
        print("   3. 补充API端点测试")

    if 30 <= coverage < 40:
        print("   1. 覆盖率良好，向40%迈进")
        print("   2. 添加集成测试")
        print("   3. 补充边界条件测试")

    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "coverage": coverage,
        "low_coverage_files": low_files,
        "status": "good" if coverage >= 25 else "needs_improvement",
    }

    report_path = Path("docs/_reports/coverage/coverage_guardian_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_path}")

    return coverage


def check_ci_threshold():
    """检查CI门槛"""
    coverage = get_current_coverage()

    if coverage is None:
        return False

    ci_threshold = 25  # CI门槛

    if coverage < ci_threshold:
        print("\n❌ CI门槛检查失败")
        print(f"   当前覆盖率: {coverage:.2f}%")
        print(f"   CI门槛要求: {ci_threshold}%")
        print(f"   差距: {ci_threshold - coverage:.2f}%")
        return False
    else:
        print("\n✅ CI门槛检查通过")
        print(f"   当前覆盖率: {coverage:.2f}%")
        print(f"   CI门槛要求: {ci_threshold}%")
        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="覆盖率守护脚本")
    parser.add_argument("--check-ci", action="store_true", help="检查CI门槛")
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    args = parser.parse_args()

    if args.check_ci:
        # 只检查CI门槛
        success = check_ci_threshold()
        sys.exit(0 if success else 1)

    elif args.watch:
        # 持续监控模式
        print("🔄 开始持续监控覆盖率（按Ctrl+C停止）")
        try:
            while True:
                generate_coverage_report()
                print("\n⏰ 60秒后再次检查...")
                import time

                time.sleep(60)
        except KeyboardInterrupt:
            print("\n👋 监控已停止")

    else:
        # 默认生成报告
        coverage = generate_coverage_report()

        # 设置退出码
        if coverage and coverage < 25:
            print("\n⚠️ 覆盖率低于25%，建议继续改进")
            sys.exit(1)
        else:
            print("\n✅ 覆盖率检查完成")
            sys.exit(0)


if __name__ == "__main__":
    main()
