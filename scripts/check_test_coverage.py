#!/usr/bin/env python3
"""
测试覆盖率检查脚本
Check test coverage for all modules
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_coverage_report():
    """运行测试覆盖率报告"""
    print("=" * 80)
    print("🧪 运行测试覆盖率报告")
    print("=" * 80)

    # 创建覆盖率报告目录
    coverage_dir = project_root / "tests" / "coverage"
    coverage_dir.mkdir(exist_ok=True)

    # 运行pytest coverage
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:tests/coverage/html",
        "--cov-report=json:tests/coverage/coverage.json",
        "--cov-report=xml:tests/coverage/coverage.xml",
        "--tb=short",
        "-v"
    ]

    print(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        print("\n📊 测试输出:")
        print(result.stdout)

        if result.stderr:
            print("\n⚠️ 错误输出:")
            print(result.stderr)

        # 解析覆盖率JSON报告
        coverage_file = coverage_dir / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)

            print("\n📈 详细覆盖率报告:")
            print("-" * 60)

            total_coverage = coverage_data["totals"]["percent_covered"]
            print(f"总覆盖率: {total_coverage:.2f}%")

            # 按模块显示覆盖率
            print("\n模块覆盖率:")
            for file_path, file_data in coverage_data["files"].items():
                if "src/" in file_path:
                    module_name = file_path.split("src/")[1]
                    coverage = file_data["summary"]["percent_covered"]
                    missing = file_data["summary"]["missing_lines"]
                    print(f"  {module_name:<50} {coverage:>6.2f}%")
                    if missing and len(missing) < 10:
                        print(f"    缺失行: {', '.join(map(str, missing[:5]))}")

            return total_coverage
        else:
            print("\n❌ 无法生成覆盖率JSON报告")
            return 0

    except Exception as e:
        print(f"\n❌ 运行测试时出错: {e}")
        return 0

def check_module_coverage():
    """检查各模块的测试覆盖情况"""
    print("\n" + "=" * 80)
    print("🔍 模块测试覆盖情况检查")
    print("=" * 80)

    # 定义关键模块和对应的测试文件
    modules = {
        "API模块": {
            "path": "src/api",
            "test_path": "tests/unit/api",
            "files": [
                "predictions.py",
                "data.py",
                "health.py",
                "models.py"
            ]
        },
        "核心服务": {
            "path": "src/services",
            "test_path": "tests/unit/services",
            "files": [
                "audit_service.py",
                "data_processing.py",
                "prediction_service.py"
            ]
        },
        "数据层": {
            "path": "src/database",
            "test_path": "tests/unit/database",
            "files": [
                "connection.py",
                "models.py",
                "repositories.py"
            ]
        },
        "缓存层": {
            "path": "src/cache",
            "test_path": "tests/unit/cache",
            "files": [
                "redis_manager.py",
                "ttl_cache.py"
            ]
        },
        "配置层": {
            "path": "src/config",
            "test_path": "tests/unit/config",
            "files": [
                "settings.py",
                "database.py",
                "logging.py"
            ]
        },
        "监控层": {
            "path": "src/monitoring",
            "test_path": "tests/unit/monitoring",
            "files": [
                "system_monitor.py",
                "metrics_collector.py",
                "alert_manager.py"
            ]
        }
    }

    results = {}

    for module_name, module_info in modules.items():
        print(f"\n{module_name}:")
        print("-" * 60)

        module_path = project_root / module_info["path"]
        test_path = project_root / module_info["test_path"]

        covered_files = 0
        total_files = len(module_info["files"])

        for file_name in module_info["files"]:
            src_file = module_path / file_name
            test_file_pattern = test_path / f"test_{file_name.replace('.py', '*.py')}"

            if src_file.exists():
                # 查找测试文件
                test_files = list(test_path.glob(f"test_{file_name.replace('.py', '')}*.py"))

                if test_files:
                    print(f"  ✅ {file_name:<40} 已测试")
                    covered_files += 1
                else:
                    print(f"  ❌ {file_name:<40} 缺少测试")
            else:
                print(f"  ⚪ {file_name:<40} 文件不存在")

        coverage_percent = (covered_files / total_files) * 100 if total_files > 0 else 0
        results[module_name] = coverage_percent
        print(f"\n  覆盖率: {coverage_percent:.1f}% ({covered_files}/{total_files})")

    return results

def generate_coverage_report(total_coverage, module_coverage):
    """生成覆盖率报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_coverage": total_coverage,
        "module_coverage": module_coverage,
        "status": "PASS" if total_coverage >= 80 else "FAIL",
        "target": 80.0,
        "gap": max(0, 80.0 - total_coverage)
    }

    # 保存报告
    report_file = project_root / "tests" / "coverage" / "report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("📋 测试覆盖率总结")
    print("=" * 80)
    print(f"时间: {report['timestamp']}")
    print(f"总覆盖率: {total_coverage:.2f}%")
    print(f"目标: {report['target']:.2f}%")
    print(f"差距: {report['gap']:.2f}%")
    print(f"状态: {'✅ 通过' if report['status'] == 'PASS' else '❌ 未达标'}")

    if total_coverage < 80:
        print("\n🚨 需要改进的模块:")
        for module, coverage in module_coverage.items():
            if coverage < 80:
                print(f"  - {module}: {coverage:.1f}%")

    return report

def update_task_board(coverage):
    """更新任务看板"""
    task_board_file = project_root / "docs" / "_tasks" / "PRODUCTION_READINESS_BOARD.md"

    if task_board_file.exists():
        with open(task_board_file, "r") as f:
            content = f.read()

        # 更新测试覆盖率
        content = re.sub(
            r'"测试覆盖率" : \d+\.\d+%',
            f'"测试覆盖率" : {coverage:.2f}%',
            content
        )

        # 更新进度饼图
        content = re.sub(
            r'"测试覆盖率" : \d+\.\d+%',
            f'"测试覆盖率" : {coverage:.2f}%',
            content
        )

        with open(task_board_file, "w") as f:
            f.write(content)

        print(f"\n✅ 任务看板已更新，测试覆盖率: {coverage:.2f}%")

def main():
    """主函数"""
    print("🚀 开始测试覆盖率检查")
    print(f"项目目录: {project_root}")

    # 1. 运行覆盖率报告
    total_coverage = run_coverage_report()

    # 2. 检查模块覆盖情况
    module_coverage = check_module_coverage()

    # 3. 生成报告
    report = generate_coverage_report(total_coverage, module_coverage)

    # 4. 更新任务看板
    update_task_board(total_coverage)

    # 5. 返回退出码
    if total_coverage >= 80:
        print("\n🎉 测试覆盖率达标！")
        sys.exit(0)
    else:
        print(f"\n⚠️ 测试覆盖率未达标，还需 {report['gap']:.2f}%")
        sys.exit(1)

if __name__ == "__main__":
    main()