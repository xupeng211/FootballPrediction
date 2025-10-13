#!/usr/bin/env python3
"""
测试覆盖率分析和计划生成脚本
Test Coverage Analysis and Planning Script
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set
import re


def get_current_coverage():
    """获取当前测试覆盖率"""
    print("📊 获取当前测试覆盖率...")

    # 运行覆盖率测试
    result = subprocess.run(["make", "coverage-local"], capture_output=True, text=True)

    # 解析覆盖率结果
    if "TOTAL" in result.stdout:
        lines = result.stdout.split("\n")
        for line in lines:
            if "TOTAL" in line:
                parts = line.split()
                if len(parts) >= 3 and "%" in parts[-1]:
                    coverage = float(parts[-1].replace("%", ""))
                    return coverage

    return 0.0


def analyze_api_routes():
    """分析API路由"""
    print("\n🔍 分析API路由...")

    api_files = [
        "src/api/data_router.py",
        "src/api/features.py",
        "src/api/predictions.py",
        "src/api/monitoring.py",
        "src/api/events.py",
        "src/api/observers.py",
        "src/api/cqrs.py",
        "src/api/repositories.py",
        "src/api/decorators.py",
        "src/api/adapters.py",
        "src/api/facades.py",
    ]

    routes = []
    for file_path in api_files:
        if Path(file_path).exists():
            with open(file_path, "r") as f:
                content = f.read()

            # 查找路由定义
            router_matches = re.findall(
                r'@router\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']', content
            )
            app_matches = re.findall(
                r'@app\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']', content
            )

            for match in router_matches + app_matches:
                if match and match not in [r[1] for r in routes]:
                    routes.append((file_path, match))

    return routes


def get_tested_endpoints():
    """获取已测试的端点"""
    print("\n📝 分析已测试的端点...")

    # 查找所有测试文件
    test_files = list(Path("tests/unit/api").glob("test_*.py"))

    tested_endpoints = set()

    for test_file in test_files:
        with open(test_file, "r") as f:
            content = f.read()

        # 查找测试的端点
        endpoint_matches = re.findall(
            r'(?:client\.get|client\.post|client\.put|client\.delete|client\.patch)\(["\']([^"\']+)["\']',
            content,
        )
        for match in endpoint_matches:
            if match:
                tested_endpoints.add(match)

        # 查找测试函数名中的端点
        func_matches = re.findall(
            r"def test_(?:get_|post_|put_|delete_|patch_)(\w+)", content
        )
        for match in func_matches:
            if match:
                tested_endpoints.add(match)

    return tested_endpoints


def generate_test_plan():
    """生成测试计划"""
    print("\n📋 生成测试改进计划...")

    current_coverage = get_current_coverage()
    routes = analyze_api_routes()
    tested = get_tested_endpoints()

    # 找出未测试的端点
    untested = []
    for file_path, endpoint in routes:
        endpoint_clean = endpoint.lstrip("/")
        if endpoint_clean not in tested:
            untested.append((file_path, endpoint_clean))

    # 生成报告
    plan = {
        "current_coverage": current_coverage,
        "target_coverage": 55,
        "gap": 55 - current_coverage,
        "total_routes": len(routes),
        "tested_endpoints": len(tested),
        "untested_endpoints": len(untested),
        "untested_routes": untested[:10],  # 显示前10个
        "suggestions": [],
    }

    # 添加建议
    if len(untested) > 0:
        plan["suggestions"].append(f"需要为 {len(untested)} 个未测试的端点编写测试")
        plan["suggestions"].append("优先级：核心API端点（/api/v1/*）")

    if current_coverage < 55:
        plan["suggestions"].append("每日提升1-2%的覆盖率")
        plan["suggestions"].append("专注于API和业务逻辑的测试")

    return plan


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 API测试覆盖率分析")
    print("=" * 60)

    plan = generate_test_plan()

    print("\n📊 测试覆盖率分析结果")
    print("-" * 40)
    print(f"当前覆盖率: {plan['current_coverage']:.2f}%")
    print(f"目标覆盖率: {plan['target_coverage']}%")
    print(f"差距: {plan['gap']:.2f}%")
    print(f"API路由总数: {plan['total_routes']}")
    print(f"已测试端点: {plan['tested_endpoints']}")
    print(f"未测试端点: {plan['untested_endpoints']}")

    if plan["untested_routes"]:
        print("\n🎯 前10个未测试的端点:")
        for i, (file_path, endpoint) in enumerate(plan["untested_routes"][:10], 1):
            print(f"  {i}. {endpoint} (来自 {file_path})")

    print("\n💡 改进建议:")
    for suggestion in plan["suggestions"]:
        print(f"  • {suggestion}")

    # 保存计划
    with open("test_coverage_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print("\n📁 详细计划已保存到: test_coverage_plan.json")


if __name__ == "__main__":
    main()
