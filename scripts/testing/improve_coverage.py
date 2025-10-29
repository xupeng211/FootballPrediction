#!/usr/bin/env python3
"""
测试覆盖率提升自动化脚本
自动执行覆盖率提升任务
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class CoverageImprover:
    """覆盖率提升管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.reports_dir = self.project_root / "docs" / "_reports"
        self.reports_dir.mkdir(exist_ok=True, parents=True)

    def run_command(
        self, cmd: List[str], capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """运行命令"""
        print(f"🚀 运行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, cwd=self.project_root
        )

        if not capture_output and result.returncode != 0:
            print(f"❌ 命令失败，返回码: {result.returncode}")

        return result

    def install_dependencies(self):
        """安装必要的依赖"""
        print("\n📦 检查并安装依赖...")

        # 检查虚拟环境
        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            print("❌ 未找到虚拟环境，请先运行: make setup")
            return False

        # 激活虚拟环境并安装测试依赖
        requirements_files = ["requirements-test.txt", "requirements.txt"]

        for req_file in requirements_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                cmd = [f"{venv_path}/bin/pip", "install", "-r", str(req_path)]
                result = self.run_command(cmd)
                if result.returncode != 0:
                    print(f"❌ 安装依赖失败: {req_file}")
                    return False

        print("✅ 依赖安装完成")
        return True

    def generate_test_templates(self):
        """生成测试模板"""
        print("\n📝 生成测试模板...")

        script_path = self.project_root / "scripts" / "generate_test_templates.py"
        if not script_path.exists():
            print("❌ 测试模板生成脚本不存在")
            return False

        cmd = [sys.executable, str(script_path)]
        result = self.run_command(cmd)

        if result.returncode == 0:
            print("✅ 测试模板生成完成")
            return True
        else:
            print("❌ 测试模板生成失败")
            return False

    def run_tests_with_coverage(self) -> Optional[float]:
        """运行测试并获取覆盖率"""
        print("\n🧪 运行测试并生成覆盖率报告...")

        # 运行pytest生成覆盖率
        cmd = [
            f"{self.project_root}/.venv/bin/python",
            "-m",
            "pytest",
            "tests/unit",
            "--cov=src",
            "--cov-report=json:coverage.json",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "-v",
        ]

        result = self.run_command(cmd, capture_output=True)

        if result.returncode != 0:
            print("❌ 测试运行失败")
            print(result.stderr)
            return None

        # 读取覆盖率数据
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file, "r") as f:
                coverage_data = json.load(f)

            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            print(f"✅ 当前覆盖率: {total_coverage:.1f}%")

            # 移动覆盖率报告到reports目录
            report_file = (
                self.reports_dir
                / f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            coverage_file.rename(report_file)

            return total_coverage

        return None

    def analyze_uncovered_code(self) -> Dict:
        """分析未覆盖的代码"""
        print("\n🔍 分析未覆盖的代码...")

        # 使用coverage工具分析
        cmd = [
            f"{self.project_root}/.venv/bin/python",
            "-m",
            "coverage",
            "report",
            "--show-missing",
            "--format=json",
        ]

        self.run_command(cmd)

        # 简化的分析结果
        analysis = {"uncovered_files": [], "uncovered_lines": {}, "suggestions": []}

        # 生成改进建议
        coverage = self.run_tests_with_coverage()
        if coverage:
            if coverage < 30:
                analysis["suggestions"].append("覆盖率过低，建议优先为核心模块编写测试")
            elif coverage < 50:
                analysis["suggestions"].append("继续为工具函数和API端点编写测试")
            elif coverage < 70:
                analysis["suggestions"].append("关注边界情况和异常处理测试")
            else:
                analysis["suggestions"].append("完善集成测试和端到端测试")

        return analysis

    def generate_improvement_plan(self, current_coverage: float) -> Dict:
        """生成改进计划"""
        print("\n📋 生成覆盖率改进计划...")

        plan = {
            "current_coverage": current_coverage,
            "target_coverage": 50,
            "phase": "4A",
            "tasks": [],
        }

        # 根据当前覆盖率生成任务
        if current_coverage < 40:
            plan["tasks"] = [
                {
                    "module": "utils",
                    "priority": "high",
                    "description": "为字符串、字典、时间等工具模块编写测试",
                    "expected_coverage": 10,
                },
                {
                    "module": "api/health",
                    "priority": "high",
                    "description": "完善健康检查API的测试",
                    "expected_coverage": 5,
                },
                {
                    "module": "api/schemas",
                    "priority": "medium",
                    "description": "测试API数据模型",
                    "expected_coverage": 5,
                },
            ]
        elif current_coverage < 50:
            plan["target_coverage"] = 60
            plan["phase"] = "4B"
            plan["tasks"] = [
                {
                    "module": "database",
                    "priority": "high",
                    "description": "测试数据库模型和连接",
                    "expected_coverage": 5,
                },
                {
                    "module": "services",
                    "priority": "high",
                    "description": "测试核心业务服务",
                    "expected_coverage": 5,
                },
            ]

        return plan

    def create_coverage_badge(self, coverage: float):
        """创建覆盖率徽章"""
        # 简单的文本徽章
        color = "red" if coverage < 30 else "yellow" if coverage < 70 else "brightgreen"
        badge = f"![Coverage](https://img.shields.io/badge/coverage-{coverage:.1f}%25-{color})"

        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 更新或添加徽章
            if "![Coverage]" in content:
                import re

                content = re.sub(r"!\[Coverage\].*$", badge, content, flags=re.MULTILINE)
            else:
                # 在标题后添加徽章
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("# "):
                        lines.insert(i + 1, badge)
                        break
                content = "\n".join(lines)

            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"✅ 更新README.md中的覆盖率徽章: {coverage:.1f}%")

    def save_report(self, report: Dict):
        """保存改进报告"""
        report_file = (
            self.reports_dir
            / f"coverage_improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 报告已保存到: {report_file}")

    def run(self):
        """执行覆盖率提升流程"""
        print("=" * 60)
        print("🚀 测试覆盖率提升自动化工具")
        print("=" * 60)

        # 1. 安装依赖
        if not self.install_dependencies():
            return

        # 2. 生成测试模板
        self.generate_test_templates()

        # 3. 运行测试获取当前覆盖率
        current_coverage = self.run_tests_with_coverage()
        if current_coverage is None:
            print("❌ 无法获取覆盖率，终止流程")
            return

        # 4. 分析未覆盖代码
        analysis = self.analyze_uncovered_code()

        # 5. 生成改进计划
        plan = self.generate_improvement_plan(current_coverage)

        # 6. 创建覆盖率徽章
        self.create_coverage_badge(current_coverage)

        # 7. 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "current_coverage": current_coverage,
            "analysis": analysis,
            "plan": plan,
            "next_steps": [
                "1. 查看生成的测试模板",
                "2. 完善 TODO 部分的测试逻辑",
                "3. 运行 pytest tests/unit -v 验证测试",
                "4. 查看htmlcov/index.html了解详细覆盖率",
                "5. 重复执行此脚本追踪进度",
            ],
        }

        self.save_report(report)

        # 打印摘要
        print("\n" + "=" * 60)
        print("📊 覆盖率提升摘要")
        print("=" * 60)
        print(f"✅ 当前覆盖率: {current_coverage:.1f}%")
        print(f"🎯 目标覆盖率: {plan['target_coverage']}%")
        print(f"📋 当前阶段: {plan['phase']}")
        print(f"📝 需要完成的任务数: {len(plan['tasks'])}")

        if plan["tasks"]:
            print("\n🎯 优先任务:")
            for task in plan["tasks"][:3]:
                print(f"  - {task['module']}: {task['description']}")

        print("\n📈 下一步操作:")
        for step in report["next_steps"]:
            print(f"  {step}")

        print("\n" + "=" * 60)
        print("✨ 覆盖率提升流程完成！")
        print("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试覆盖率提升工具")
    parser.add_argument("--project-root", type=Path, help="项目根目录")

    args = parser.parse_args()

    improver = CoverageImprover(args.project_root)
    improver.run()


if __name__ == "__main__":
    main()
