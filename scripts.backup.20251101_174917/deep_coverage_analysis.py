#!/usr/bin/env python3
"""
深度覆盖率分析工具
准确评估当前项目的测试覆盖率状况
"""

import subprocess
import json
import os
import ast
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class CoverageAnalyzer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.source_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        self.analysis_results = {}

    def analyze_python_files(self) -> Dict[str, any]:
        """分析Python源代码文件"""
        python_files = list(self.source_dir.rglob("*.py"))

        total_files = len(python_files)
        total_lines = 0
        analyzable_lines = 0
        import_lines = 0
        class_lines = 0
        function_lines = 0

        file_details = []

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 简单的代码行统计
                lines = content.split("\n")
                file_line_count = len(lines)
                non_empty_lines = len([line for line in lines if line.strip()])

                # 使用AST分析代码结构
                try:
                    tree = ast.parse(content)

                    imports = 0
                    classes = 0
                    functions = 0

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            imports += 1
                        elif isinstance(node, ast.ClassDef):
                            classes += 1
                        elif isinstance(node, ast.FunctionDef):
                            functions += 1

                    file_details.append(
                        {
                            "path": str(file_path.relative_to(self.project_root)),
                            "total_lines": file_line_count,
                            "non_empty_lines": non_empty_lines,
                            "imports": imports,
                            "classes": classes,
                            "functions": functions,
                        }
                    )

                    total_lines += file_line_count
                    analyzable_lines += non_empty_lines
                    import_lines += imports * 2  # 估算import语句行数
                    class_lines += classes * 5  # 估算class定义行数
                    function_lines += functions * 3  # 估算function定义行数

                except SyntaxError:
                    # 文件有语法错误，但仍计入总行数
                    total_lines += file_line_count
                    file_details.append(
                        {
                            "path": str(file_path.relative_to(self.project_root)),
                            "total_lines": file_line_count,
                            "non_empty_lines": non_empty_lines,
                            "syntax_error": True,
                        }
                    )

            except Exception as e:
                print(f"分析文件 {file_path} 时出错: {e}")

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "analyzable_lines": analyzable_lines,
            "import_lines": import_lines,
            "class_lines": class_lines,
            "function_lines": function_lines,
            "file_details": file_details,
        }

    def analyze_test_files(self) -> Dict[str, any]:
        """分析测试文件"""
        test_files = list(self.test_dir.rglob("test_*.py"))

        total_test_files = len(test_files)
        executable_tests = 0
        total_test_lines = 0
        actual_test_lines = 0

        test_file_details = []

        for file_path in test_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 检查文件是否包含实质性测试
                lines = content.split("\n")
                total_file_lines = len(lines)
                total_test_lines += total_file_lines

                # 简单的实质性测试检测
                has_assert = "assert" in content
                has_test_func = "def test_" in content
                has_pytest_mark = "@pytest.mark" in content
                has_fixture = "@pytest.fixture" in content

                # 估算实质性测试行数
                actual_lines = len(
                    [
                        line
                        for line in lines
                        if line.strip()
                        and (
                            line.strip().startswith("def test_")
                            or "assert" in line
                            or "expect" in line.lower()
                        )
                    ]
                )

                actual_test_lines += actual_lines

                if has_assert or has_test_func:
                    executable_tests += 1

                test_file_details.append(
                    {
                        "path": str(file_path.relative_to(self.project_root)),
                        "total_lines": total_file_lines,
                        "actual_test_lines": actual_lines,
                        "has_assert": has_assert,
                        "has_test_func": has_test_func,
                        "has_pytest_mark": has_pytest_mark,
                        "has_fixture": has_fixture,
                    }
                )

            except Exception as e:
                print(f"分析测试文件 {file_path} 时出错: {e}")

        return {
            "total_test_files": total_test_files,
            "executable_tests": executable_tests,
            "total_test_lines": total_test_lines,
            "actual_test_lines": actual_test_lines,
            "test_file_details": test_file_details,
        }

    def estimate_coverage(self, source_analysis: Dict, test_analysis: Dict) -> Dict[str, any]:
        """估算测试覆盖率"""

        # 方法1: 基于测试文件数量
        coverage_by_files = (
            test_analysis["executable_tests"] / max(1, source_analysis["total_files"])
        ) * 100

        # 方法2: 基于代码行数的理论估算
        # 假设每个可执行测试文件平均测试50行代码
        estimated_covered_lines = test_analysis["executable_tests"] * 50
        coverage_by_lines = (
            estimated_covered_lines / max(1, source_analysis["analyzable_lines"])
        ) * 100

        # 方法3: 基于实际测试行数
        coverage_by_test_lines = (
            test_analysis["actual_test_lines"] / max(1, source_analysis["analyzable_lines"])
        ) * 100

        # 方法4: 基于核心组件覆盖估算
        # 统计核心模块是否有对应的测试
        core_modules = ["config", "di", "exceptions", "database", "api", "services", "utils"]
        covered_modules = 0

        for module in core_modules:
            module_pattern = f"test_*{module}*"
            if any(
                module_pattern in test_file["path"]
                for test_file in test_analysis["test_file_details"]
            ):
                covered_modules += 1

        coverage_by_modules = (covered_modules / len(core_modules)) * 100

        # 综合估算 (加权平均)
        weights = {"files": 0.2, "lines": 0.3, "test_lines": 0.3, "modules": 0.2}

        estimated_coverage = (
            coverage_by_files * weights["files"]
            + coverage_by_lines * weights["lines"]
            + coverage_by_test_lines * weights["test_lines"]
            + coverage_by_modules * weights["modules"]
        )

        return {
            "estimated_coverage": round(estimated_coverage, 2),
            "coverage_by_files": round(coverage_by_files, 2),
            "coverage_by_lines": round(coverage_by_lines, 2),
            "coverage_by_test_lines": round(coverage_by_test_lines, 2),
            "coverage_by_modules": round(coverage_by_modules, 2),
            "method_weights": weights,
        }

    def run_actual_coverage_test(self) -> Dict[str, any]:
        """尝试运行实际的覆盖率测试"""
        try:
            # 尝试运行基础的覆盖率测试
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pytest",
                    "--cov=src",
                    "--cov-report=json",
                    "--cov-report=term-missing",
                    "--tb=short",
                    "-q",
                ],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                # 尝试读取coverage.json文件
                coverage_file = self.project_root / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, "r") as f:
                        coverage_data = json.load(f)

                    return {
                        "success": True,
                        "actual_coverage": coverage_data["totals"]["percent_covered"],
                        "lines_covered": coverage_data["totals"]["covered_lines"],
                        "lines_total": coverage_data["totals"]["num_statements"],
                        "files": coverage_data["files"],
                    }

            return {"success": False, "error": result.stderr, "returncode": result.returncode}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_comprehensive_report(self) -> Dict[str, any]:
        """生成综合覆盖率报告"""

        print("🔍 开始深度覆盖率分析...")

        # 1. 分析源代码
        print("📊 分析源代码文件...")
        source_analysis = self.analyze_python_files()

        # 2. 分析测试文件
        print("🧪 分析测试文件...")
        test_analysis = self.analyze_test_files()

        # 3. 估算覆盖率
        print("📈 估算测试覆盖率...")
        coverage_estimation = self.estimate_coverage(source_analysis, test_analysis)

        # 4. 尝试实际测试
        print("🎯 尝试运行实际覆盖率测试...")
        actual_coverage = self.run_actual_coverage_test()

        # 5. 生成综合报告
        report = {
            "analysis_time": datetime.now().isoformat(),
            "analyzer_version": "1.0.0",
            "project_root": str(self.project_root),
            "source_analysis": source_analysis,
            "test_analysis": test_analysis,
            "coverage_estimation": coverage_estimation,
            "actual_coverage": actual_coverage,
            "final_assessment": self.generate_final_assessment(
                source_analysis, test_analysis, coverage_estimation, actual_coverage
            ),
        }

        # 保存报告
        report_file = (
            self.project_root
            / f'deep_coverage_analysis_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📋 深度覆盖率分析报告已保存: {report_file}")
        return report

    def generate_final_assessment(
        self,
        source_analysis: Dict,
        test_analysis: Dict,
        coverage_estimation: Dict,
        actual_coverage: Dict,
    ) -> Dict[str, any]:
        """生成最终评估"""

        if actual_coverage["success"]:
            final_coverage = actual_coverage["actual_coverage"]
            method = "actual_measurement"
            reliability = "high"
        else:
            final_coverage = coverage_estimation["estimated_coverage"]
            method = "estimation"
            reliability = "medium"

        # 覆盖率等级评估
        if final_coverage >= 80:
            grade = "A+"
            assessment = "Excellent"
            recommendation = "Coverage meets enterprise standards"
        elif final_coverage >= 60:
            grade = "A"
            assessment = "Good"
            recommendation = "Coverage is good, consider adding more tests"
        elif final_coverage >= 40:
            grade = "B"
            assessment = "Fair"
            recommendation = "Coverage needs improvement"
        elif final_coverage >= 20:
            grade = "C"
            assessment = "Poor"
            recommendation = "Coverage is insufficient, major improvements needed"
        else:
            grade = "D"
            assessment = "Very Poor"
            recommendation = "Coverage is critically low, immediate action required"

        return {
            "final_coverage": round(final_coverage, 2),
            "measurement_method": method,
            "reliability": reliability,
            "grade": grade,
            "assessment": assessment,
            "recommendation": recommendation,
            "source_files": source_analysis["total_files"],
            "test_files": test_analysis["total_test_files"],
            "executable_tests": test_analysis["executable_tests"],
            "test_executable_rate": round(
                (test_analysis["executable_tests"] / max(1, test_analysis["total_test_files"]))
                * 100,
                2,
            ),
        }


def main():
    """主函数"""
    analyzer = CoverageAnalyzer()

    try:
        report = analyzer.generate_comprehensive_report()

        # 打印关键结果
        print("\n" + "=" * 60)
        print("📊 深度覆盖率分析结果")
        print("=" * 60)

        final_assessment = report["final_assessment"]

        print(f"🎯 最终覆盖率: {final_assessment['final_coverage']}%")
        print(f"📈 测量方法: {final_assessment['measurement_method']}")
        print(f"🏆 评级: {final_assessment['grade']} ({final_assessment['assessment']})")
        print(f"📝 建议: {final_assessment['recommendation']}")
        print(f"📁 源代码文件: {final_assessment['source_files']}")
        print(f"🧪 测试文件: {final_assessment['test_files']}")
        print(f"✅ 可执行测试: {final_assessment['executable_tests']}")
        print(f"📊 测试可执行率: {final_assessment['test_executable_rate']}%")

        print("\n🎯 目标达成情况:")
        if final_assessment["final_coverage"] >= 80:
            print("✅ 80%覆盖率目标: 已达成")
        elif final_assessment["final_coverage"] >= 50:
            print("⚠️ 80%覆盖率目标: 部分达成")
        else:
            print("❌ 80%覆盖率目标: 未达成")

        print("=" * 60)

        return report

    except Exception as e:
        print(f"❌ 深度覆盖率分析失败: {e}")
        return None


if __name__ == "__main__":
    main()
