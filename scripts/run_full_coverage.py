#!/usr/bin/env python3
"""
运行全量单元测试覆盖率
"""

import subprocess
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def run_command(cmd, capture_output=True):
    """运行命令并返回结果"""
    print(f"🚀 运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=capture_output, text=True)

    if result.returncode != 0:
        print(f"❌ 命令失败，返回码: {result.returncode}")
        if result.stderr:
            print(f"错误输出: {result.stderr}")
        return None

    return result


def parse_coverage_from_xml(xml_file):
    """从 XML 文件解析覆盖率"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # 获取总体覆盖率
        line_rate = float(root.get("line-rate", 0)) * 100
        branch_rate = float(root.get("branch-rate", 0)) * 100

        return {
            "line_coverage": line_rate,
            "branch_coverage": branch_rate,
            "total_coverage": (line_rate + branch_rate) / 2,
        }
    except Exception as e:
        print(f"❌ 解析覆盖率 XML 失败: {e}")
        return None


def parse_coverage_from_json(json_file):
    """从 JSON 文件解析覆盖率"""
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        totals = data.get("totals", {})
        line_cov = totals.get("percent_covered", 0)

        return {
            "line_coverage": line_cov,
            "branch_coverage": 0,  # JSON 报告可能不包含分支覆盖率
            "total_coverage": line_cov,
        }
    except Exception as e:
        print(f"❌ 解析覆盖率 JSON 失败: {e}")
        return None


def generate_coverage_report(coverage_data, output_file):
    """生成覆盖率报告"""
    report = {
        "timestamp": subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"])
        .decode()
        .strip(),
        "coverage": coverage_data,
        "threshold": {"current": 40, "target": 80},
        "status": "PASS"
        if coverage_data and coverage_data["line_coverage"] >= 40
        else "FAIL",
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    return report


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 运行全量单元测试覆盖率检查")
    print("=" * 60)

    # 运行测试
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "--cov=src",
        "--cov-report=xml:coverage-full.xml",
        "--cov-report=json:coverage-full.json",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "-v",
        "--tb=short",
    ]

    result = run_command(cmd)

    if result is None:
        print("\n❌ 测试运行失败")
        sys.exit(1)

    # 解析覆盖率
    coverage_xml = Path("coverage-full.xml")
    coverage_json = Path("coverage-full.json")

    coverage_data = None

    if coverage_xml.exists():
        coverage_data = parse_coverage_from_xml(coverage_xml)
    elif coverage_json.exists():
        coverage_data = parse_coverage_from_json(coverage_json)

    if not coverage_data:
        print("\n❌ 无法获取覆盖率数据")
        sys.exit(1)

    # 打印覆盖率结果
    print("\n" + "=" * 60)
    print("📊 覆盖率报告")
    print("=" * 60)
    print(f"行覆盖率: {coverage_data['line_coverage']:.2f}%")
    if coverage_data["branch_coverage"] > 0:
        print(f"分支覆盖率: {coverage_data['branch_coverage']:.2f}%")
    print(f"总体覆盖率: {coverage_data['total_coverage']:.2f}%")

    # 检查阈值
    threshold = 40
    passed = coverage_data["line_coverage"] >= threshold

    print("\n" + "-" * 60)
    if passed:
        print(f"✅ 覆盖率 {coverage_data['line_coverage']:.2f}% >= {threshold}% - 通过")
    else:
        print(f"❌ 覆盖率 {coverage_data['line_coverage']:.2f}% < {threshold}% - 失败")
        print(f"   需要至少 {threshold}% 覆盖率")

    # 生成报告文件
    report_file = Path("docs/_reports/COVERAGE_REPORT.json")
    report_file.parent.mkdir(exist_ok=True, parents=True)
    generate_coverage_report(coverage_data, report_file)

    print(f"\n📄 覆盖率报告已保存到: {report_file}")

    if coverage_json.exists():
        print(f"📄 详细 JSON 报告: {coverage_json}")
    if coverage_xml.exists():
        print(f"📄 XML 报告: {coverage_xml}")

    print("📄 HTML 报告: htmlcov/index.html")

    # 按模块显示覆盖率
    if coverage_json.exists():
        print("\n📈 模块覆盖率详情:")
        print("-" * 60)

        with open(coverage_json, "r") as f:
            data = json.load(f)

        files = data.get("files", [])
        modules = {}

        for file_info in files:
            file_path = Path(file_info["relative_filename"])
            if "src/" in str(file_path):
                # 提取模块名
                parts = file_path.parts
                if len(parts) > 1 and parts[0] == "src":
                    module = parts[1]
                    if module not in modules:
                        modules[module] = []
                    modules[module].append(file_info)

        for module, module_files in sorted(modules.items()):
            total_lines = sum(f["summary"]["num_statements"] for f in module_files)
            total_missing = sum(f["summary"]["missing_lines"] for f in module_files)
            total_covered = total_lines - total_missing
            module_cov = (total_covered / total_lines * 100) if total_lines > 0 else 0

            print(
                f"{module:15} {module_cov:6.2f}% ({total_covered:4}/{total_lines:4} 行)"
            )

    print("\n" + "=" * 60)

    # 返回适当的退出码
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
