#!/usr/bin/env python3
"""
建立覆盖率追踪基线
解析现有覆盖率数据并建立趋势追踪基线
"""

import json
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_coverage_from_xml(xml_file: Path) -> dict:
    """从XML文件提取覆盖率数据"""
    if not xml_file.exists():
        return {"error": "Coverage XML file not found"}

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # 总体覆盖率
        total_lines_valid = int(root.get("lines-valid", 0))
        total_lines_covered = int(root.get("lines-covered", 0))
        overall_coverage = (
            (total_lines_covered / total_lines_valid * 100)
            if total_lines_valid > 0
            else 0
        )

        coverage_data = {
            "total": overall_coverage,
            "lines_covered": total_lines_covered,
            "lines_valid": total_lines_valid,
        }

        # 查找关键模块覆盖率
        for package in root.findall(".//package"):
            for classes in package.findall("classes"):
                for class_elem in classes.findall("class"):
                    class_name = class_elem.get("name", "")
                    filename = class_elem.get("filename", "")

                    # 推理服务v2
                    if "inference_service_v2.py" in filename:
                        lines_valid = int(class_elem.get("lines-valid", 0))
                        lines_covered = int(class_elem.get("lines-covered", 0))
                        if lines_valid > 0:
                            coverage_data["inference_service_v2"] = (
                                lines_covered / lines_valid
                            ) * 100

                    # 配置模块
                    elif "config.py" in filename:
                        lines_valid = int(class_elem.get("lines-valid", 0))
                        lines_covered = int(class_elem.get("lines-covered", 0))
                        if lines_valid > 0:
                            coverage_data["config"] = (
                                lines_covered / lines_valid
                            ) * 100

                    # 数据库相关
                    elif "database" in filename:
                        lines_valid = int(class_elem.get("lines-valid", 0))
                        lines_covered = int(class_elem.get("lines-covered", 0))
                        if lines_valid > 0:
                            coverage_data["database"] = (
                                lines_covered / lines_valid
                            ) * 100

        return coverage_data

    except Exception as e:
        return {"error": str(e)}


def main():
    """主函数"""
    project_root = Path.cwd()
    coverage_xml = project_root / "coverage.xml"
    data_file = project_root / ".coverage_trends.json"

    # 提取覆盖率数据
    coverage_data = extract_coverage_from_xml(coverage_xml)

    if "error" in coverage_data:
        print(f"❌ 提取覆盖率数据失败: {coverage_data['error']}")
        return

    # 创建基线数据
    timestamp = datetime.datetime.now().isoformat()
    baseline_data = {
        "history": [
            {
                "timestamp": timestamp,
                "overall_coverage": coverage_data.get("total", 0),
                "module_coverage": {
                    k: v
                    for k, v in coverage_data.items()
                    if k not in ["total", "lines_covered", "lines_valid", "error"]
                },
                "raw_data": coverage_data,
            }
        ],
        "module_trends": {},
        "targets": {
            "overall": 25.0,
            "inference_service_v2": 90.0,
            "config": 70.0,
            "database": 50.0,
        },
    }

    # 初始化模块趋势
    for module, coverage in baseline_data["history"][0]["module_coverage"].items():
        baseline_data["module_trends"][module] = [
            {"timestamp": timestamp, "coverage": coverage}
        ]

    # 保存数据
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2, ensure_ascii=False)

    print("✅ 覆盖率基线已建立")
    print(f"   总体覆盖率: {baseline_data['history'][0]['overall_coverage']:.1f}%")
    print(f"   推理服务覆盖率: {coverage_data.get('inference_service_v2', 0):.1f}%")
    print(f"   配置模块覆盖率: {coverage_data.get('config', 0):.1f}%")
    print(f"   数据库覆盖率: {coverage_data.get('database', 0):.1f}%")

    print(f"\n📊 数据已保存到: {data_file}")


if __name__ == "__main__":
    main()
