#!/usr/bin/env python3
"""
每日覆盖率检查脚本
自动运行测试并生成覆盖率报告
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=300,  # 5分钟超时
        )
        return result
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return None
    except Exception as e:
        print(f"命令执行错误: {e}")
        return None


def parse_coverage_output(output):
    """解析覆盖率输出"""
    lines = output.split("\n")
    total_line = None

    for line in lines:
        if "TOTAL" in line:
            total_line = line
            break

    if total_line:
        # 解析TOTAL行，例如: "TOTAL                              14554   11226   3456     44    19%"
        parts = total_line.split()
        if len(parts) >= 5:
            coverage = {
                "statements": int(parts[1]),
                "missing": int(parts[2]),
                "branches": int(parts[3]),
                "partial": int(parts[4]),
                "percent": float(parts[5].strip("%")),
            }
            return coverage

    return None


def generate_coverage_report():
    """生成覆盖率报告"""
    print("=" * 60)
    print(f"📊 测试覆盖率报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 运行整体覆盖率测试
    print("\n1️⃣ 运行整体覆盖率测试...")
    cmd = (
        "python -m pytest "
        "tests/unit/api/test_basic_imports.py "
        "tests/unit/api/test_health.py "
        "tests/unit/api/test_predictions.py "
        "tests/unit/services/test_services_fixed.py "
        "tests/unit/services/test_quick_wins.py "
        "--cov=src "
        "--cov-report=term-missing "
        "--tb=short"
    )

    result = run_command(cmd)
    if result and result.returncode == 0:
        print("✅ 测试通过")
        coverage = parse_coverage_output(result.stdout)
        if coverage:
            print(f"\n📈 整体覆盖率: {coverage['percent']}%")
            print(f"   - 总语句数: {coverage['statements']}")
            print(f"   - 未覆盖: {coverage['missing']}")
            print(f"   - 覆盖率变化: +{(coverage['percent'] - 19):.1f}%")  # 假设基准是19%
    else:
        print("❌ 测试失败")
        if result:
            print(result.stderr)

    # 2. 生成HTML报告
    print("\n2️⃣ 生成HTML覆盖率报告...")
    html_cmd = (
        "python -m pytest "
        "tests/unit/api/test_basic_imports.py "
        "tests/unit/services/test_services_fixed.py "
        "tests/unit/services/test_quick_wins.py "
        "--cov=src "
        "--cov-report=html "
        "--cov-report=json "
        "-q"
    )

    result = run_command(html_cmd)
    if result and result.returncode == 0:
        print("✅ HTML报告已生成: htmlcov/index.html")
        if Path("coverage.json").exists():
            with open("coverage.json") as f:
                _ = json.load(f)
                print("   JSON报告已生成: coverage.json")
    else:
        print("❌ HTML报告生成失败")

    # 3. 检查新增测试
    print("\n3️⃣ 检查测试文件数量...")
    test_files = list(Path("tests").rglob("test_*.py"))
    print(f"   当前测试文件数量: {len(test_files)}")

    # 4. 检查零覆盖率模块
    print("\n4️⃣ 零覆盖率模块检查...")
    zero_coverage_cmd = "coverage report --show-missing | grep ' 0%' | head -10"
    result = run_command(zero_coverage_cmd)
    if result and result.stdout.strip():
        print("   零覆盖率模块:")
        for line in result.stdout.strip().split("\n")[:5]:
            print(f"   - {line}")
    else:
        print("   ✅ 没有零覆盖率模块（或未安装coverage）")

    # 5. 建议和下一步
    print("\n5️⃣ 建议和下一步:")
    print("   📝 待办事项:")
    print("   - [ ] 修复 test_services_enhanced.py 中的失败测试")
    print("   - [ ] 为 odds_collector.py 添加功能测试")
    print("   - [ ] 为 scores_collector.py 添加功能测试")
    print("   - [ ] 优化 DataProcessingService 测试覆盖率")
    print("\n   💡 提示:")
    print("   - 使用 'pytest --collect-only' 查看可测试项")
    print("   - 使用 'pytest -k test_name' 运行特定测试")
    print("   - 使用 'pytest --cov=src/module --cov-report=html' 查看模块覆盖率")


def check_coverage_threshold(threshold=20.0):
    """检查覆盖率是否达到阈值"""
    cmd = "coverage json --fail-under=0"
    result = run_command(cmd)

    if result and result.returncode == 0:
        try:
            with open("coverage.json") as f:
                data = json.load(f)
                total_coverage = data["totals"]["percent_covered"]

                if total_coverage >= threshold:
                    print(f"\n✅ 覆盖率达标: {total_coverage:.1f}% >= {threshold}%")
                    return True
                else:
                    print(f"\n⚠️ 覆盖率未达标: {total_coverage:.1f}% < {threshold}%")
                    return False
        except Exception as e:
            print(f"解析覆盖率报告失败: {e}")
            return False

    return False


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # 只检查覆盖率
        success = check_coverage_threshold()
        sys.exit(0 if success else 1)
    else:
        # 生成完整报告
        generate_coverage_report()


if __name__ == "__main__":
    main()
