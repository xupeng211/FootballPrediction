#!/usr/bin/env python3
"""
✅ 代码质量检查器

自动执行代码格式化、静态分析、测试等质量检查，并尝试自动修复问题。
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 添加项目路径以便导入核心模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Logger  # noqa: E402


class QualityChecker:
    """代码质量检查器"""

    def __init__(self, project_root: str = ".", max_retries: int = 3):
        """
        初始化质量检查器

        Args:
            project_root: 项目根目录
            max_retries: 最大重试次数
        """
        self.project_root = Path(project_root).resolve()
        self.max_retries = max_retries
        self.results: Dict[str, Any] = {}
        self.iteration_log: List[Dict] = []
        # 设置日志器
        self.logger = Logger.setup_logger("quality_checker", "INFO")

    def run_all_checks(self) -> Dict[str, Any]:
        """
        运行所有质量检查

        Returns:
            检查结果字典
        """
        self.logger.info("🔍 开始代码质量检查...")

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "checks": {},
            "overall_status": "failed",
            "retry_count": 0,
        }

        # 定义检查步骤
        check_steps = [
            ("backup", "备份文件", self._backup_files),
            ("format", "代码格式化", self._run_black_format),
            ("lint", "代码风格检查", self._run_ruff_lint),
            ("type_check", "类型检查", self._run_mypy_check),
            ("test", "单元测试", self._run_pytest),
            ("coverage", "测试覆盖率", self._run_coverage),
            ("complexity", "复杂度分析", self._run_complexity_check),
        ]

        # 执行检查循环 - 多轮检查机制，自动修复问题并重试验证
        for retry in range(self.max_retries):
            self.results["retry_count"] = retry
            self.logger.info(f"\n🔄 第 {retry + 1} 轮检查...")

            all_passed = True

            for check_id, check_name, check_func in check_steps:
                self.logger.info(f"  ▶️ {check_name}...")

                try:
                    # 执行单项检查，获取结果状态和详细信息
                    success, message, details = check_func()

                    # 记录每项检查的详细结果，便于问题追踪和分析
                    self.results["checks"][check_id] = {
                        "name": check_name,
                        "success": success,
                        "message": message,
                        "details": details,
                        "retry": retry,
                    }

                    if success:
                        self.logger.info(f"    ✅ {check_name}成功: {message}")
                    else:
                        self.logger.warning(f"    ❌ {check_name}失败: {message}")
                        all_passed = False

                        # 尝试自动修复
                        if self._can_auto_fix(check_id):
                            self.logger.info("    🔧 尝试自动修复...")
                            fix_success = self._auto_fix(check_id, details)
                            if fix_success:
                                self.logger.info("    ✨ 自动修复成功")
                            else:
                                self.logger.warning("    ⚠️ 自动修复失败")

                except Exception as e:
                    self.logger.error(f"    💥 {check_name}异常: {e}")
                    self.results["checks"][check_id] = {
                        "name": check_name,
                        "success": False,
                        "message": f"检查异常: {e}",
                        "details": {"exception": str(e)},
                        "retry": retry,
                    }
                    all_passed = False

            # 记录迭代日志
            self._log_iteration(retry, all_passed)

            if all_passed:
                self.results["overall_status"] = "passed"
                self.logger.info("\n🎉 所有检查通过！")
                break
            else:
                self.logger.warning(f"\n⚠️ 第 {retry + 1} 轮检查未完全通过，准备重试...")

        # 最终状态
        if self.results["overall_status"] != "passed":
            self.logger.error("\n❌ 检查失败，已达到最大重试次数")

        return self.results

    def _backup_files(self) -> Tuple[bool, str, Dict]:
        """备份文件"""
        try:
            backup_dir = self.project_root / "backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 备份Python文件
            python_files = list(self.project_root.rglob("*.py"))
            backed_up = []

            for py_file in python_files:
                if self._should_backup(py_file):
                    relative_path = py_file.relative_to(self.project_root)
                    backup_file = backup_dir / relative_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)

                    import shutil

                    shutil.copy2(py_file, backup_file)
                    backed_up.append(str(relative_path))

            return (
                True,
                f"已备份 {len(backed_up)} 个文件",
                {"backup_directory": str(backup_dir), "files_backed_up": backed_up},
            )

        except Exception as e:
            return False, f"备份失败: {e}", {"exception": str(e)}

    def _should_backup(self, file_path: Path) -> bool:
        """判断文件是否需要备份"""
        # 排除一些不需要备份的目录
        exclude_dirs = {"__pycache__", ".git", ".pytest_cache", "venv", "env", "backup"}

        for parent in file_path.parents:
            if parent.name in exclude_dirs:
                return False

        return True

    def _run_black_format(self) -> Tuple[bool, str, Dict]:
        """运行black代码格式化"""
        try:
            # 首先检查是否安装了black
            check_result = subprocess.run(
                ["python", "-m", "black", "--version"], capture_output=True, text=True
            )

            if check_result.returncode != 0:
                return False, "black未安装", {"suggestion": "pip install black"}

            # 运行black格式化
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "black",
                    "src/core/",
                    "src/models/",
                    "src/services/",
                    "src/utils/",
                    "src/database/",
                    "src/api/",
                    "tests/",
                    "scripts/",
                    "--line-length=88",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            return (
                True,
                "代码格式化完成",
                {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                },
            )

        except Exception as e:
            return False, f"格式化失败: {e}", {"exception": str(e)}

    def _run_flake8_lint(self) -> Tuple[bool, str, Dict]:
        """运行flake8代码风格检查"""
        try:
            # 检查是否安装了flake8
            check_result = subprocess.run(
                ["python", "-m", "flake8", "--version"], capture_output=True, text=True
            )

            if check_result.returncode != 0:
                return False, "flake8未安装", {"suggestion": "pip install flake8"}

            # 运行flake8检查
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "flake8",
                    "src/core/",
                    "src/models/",
                    "src/services/",
                    "src/utils/",
                    "src/database/",
                    "src/api/",
                    "tests/",
                    "scripts/",
                    "--max-line-length=88",
                    "--extend-ignore=E203,W503",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return True, "代码风格检查通过", {"issues": []}
            else:
                issues = result.stdout.strip().split("\n") if result.stdout.strip() else []
                return (
                    False,
                    f"发现 {len(issues)} 个风格问题",
                    {
                        "issues": issues,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )

        except Exception as e:
            return False, f"风格检查失败: {e}", {"exception": str(e)}

    def _run_ruff_lint(self) -> Tuple[bool, str, Dict]:
        """运行ruff代码风格检查"""
        try:
            # 检查是否安装了ruff
            check_result = subprocess.run(
                ["python", "-m", "ruff", "--version"], capture_output=True, text=True
            )

            if check_result.returncode != 0:
                return False, "ruff未安装", {"suggestion": "pip install ruff"}

            # 运行ruff检查
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ruff",
                    "check",
                    "src/core/",
                    "src/models/",
                    "src/services/",
                    "src/utils/",
                    "src/database/",
                    "src/api/",
                    "tests/",
                    "scripts/",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return True, "代码风格检查通过", {"issues": []}
            else:
                issues = result.stdout.strip().split("\n") if result.stdout.strip() else []
                return (
                    False,
                    f"发现 {len(issues)} 个风格问题",
                    {
                        "issues": issues,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )

        except Exception as e:
            return False, f"风格检查失败: {e}", {"exception": str(e)}

    def _run_mypy_check(self) -> Tuple[bool, str, Dict]:
        """运行mypy类型检查"""
        try:
            # 检查是否安装了mypy
            check_result = subprocess.run(
                ["python", "-m", "mypy", "--version"], capture_output=True, text=True
            )

            if check_result.returncode != 0:
                return True, "mypy未安装，跳过类型检查", {"skipped": True}

            # 运行mypy检查
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "mypy",
                    "src/core/",
                    "src/models/",
                    "src/services/",
                    "src/utils/",
                    "src/database/",
                    "src/api/",
                    "--ignore-missing-imports",
                    "--explicit-package-bases",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return True, "类型检查通过", {"issues": []}
            else:
                issues = result.stdout.strip().split("\n") if result.stdout.strip() else []
                return (
                    False,
                    f"发现 {len(issues)} 个类型问题",
                    {
                        "issues": issues,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )

        except Exception as e:
            return False, f"类型检查失败: {e}", {"exception": str(e)}

    def _run_pytest(self) -> Tuple[bool, str, Dict]:
        """运行pytest单元测试"""
        try:
            # 检查是否有测试文件
            test_files = list(self.project_root.rglob("test_*.py"))
            if not test_files:
                return True, "未找到测试文件，跳过测试", {"skipped": True}

            # 检查是否安装了pytest
            check_result = subprocess.run(
                ["python", "-m", "pytest", "--version"], capture_output=True, text=True
            )

            if check_result.returncode != 0:
                return False, "pytest未安装", {"suggestion": "pip install pytest"}

            # 运行pytest
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return (
                    True,
                    "所有测试通过",
                    {"stdout": result.stdout, "test_files_count": len(test_files)},
                )
            else:
                return (
                    False,
                    "测试失败",
                    {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "return_code": result.returncode,
                    },
                )

        except Exception as e:
            return False, f"测试运行失败: {e}", {"exception": str(e)}

    def _run_coverage(self) -> Tuple[bool, str, Dict]:
        """运行测试覆盖率检查"""
        try:
            # 检查是否安装了coverage
            check_result = subprocess.run(
                ["python", "-m", "coverage", "--version"],
                capture_output=True,
                text=True,
            )

            if check_result.returncode != 0:
                return True, "coverage未安装，跳过覆盖率检查", {"skipped": True}

            # 运行覆盖率测试
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "coverage",
                    "run",
                    "--source=src/core,src/models,src/services,src/utils,src/database,src/api",
                    "-m",
                    "pytest",
                    "tests/",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return (
                    False,
                    "覆盖率测试失败",
                    {"stdout": result.stdout, "stderr": result.stderr},
                )

            # 获取覆盖率报告（JSON格式）
            report_result = subprocess.run(
                ["python", "-m", "coverage", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if report_result.returncode == 0:
                try:
                    # 读取生成的coverage.json文件
                    coverage_json_path = os.path.join(self.project_root, "coverage.json")
                    if os.path.exists(coverage_json_path):
                        with open(coverage_json_path, "r", encoding="utf-8") as f:
                            coverage_data = json.load(f)
                        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                    else:
                        return (
                            False,
                            "覆盖率JSON报告文件未生成",
                            {"error": "coverage.json not found"},
                        )

                    min_coverage = int(os.getenv("TEST_COVERAGE_MIN", "78"))

                    if total_coverage >= min_coverage:
                        return (
                            True,
                            f"测试覆盖率 {total_coverage:.1f}% >= {min_coverage}%",
                            {
                                "coverage": total_coverage,
                                "threshold": min_coverage,
                                "details": coverage_data,
                            },
                        )
                    else:
                        return (
                            False,
                            f"测试覆盖率 {total_coverage:.1f}% < {min_coverage}%",
                            {
                                "coverage": total_coverage,
                                "threshold": min_coverage,
                                "details": coverage_data,
                            },
                        )

                except json.JSONDecodeError:
                    return (
                        False,
                        "无法解析覆盖率报告",
                        {"raw_output": report_result.stdout},
                    )

            return (
                False,
                "获取覆盖率报告失败",
                {"stdout": report_result.stdout, "stderr": report_result.stderr},
            )

        except Exception as e:
            return False, f"覆盖率检查失败: {e}", {"exception": str(e)}

    def _run_complexity_check(self) -> Tuple[bool, str, Dict]:
        """运行复杂度分析"""
        try:
            # 检查是否安装了radon
            # 使用 `import` 语句检查radon是否安装，这比检查版本更可靠
            check_result = subprocess.run(
                ["python", "-c", "import radon"],
                capture_output=True,
                text=True,
            )

            if check_result.returncode != 0:
                return True, "radon未安装，跳过复杂度检查", {"skipped": True}

            # 运行复杂度检查
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "radon",
                    "cc",
                    "src/core/",
                    "src/models/",
                    "src/services/",
                    "src/utils/",
                    "src/database/",
                    "src/api/",
                    "--json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                try:
                    complexity_data = json.loads(result.stdout)
                    max_complexity = int(os.getenv("MAX_COMPLEXITY", "10"))

                    high_complexity_items = []
                    for file_path, items in complexity_data.items():
                        for item in items:
                            if item.get("complexity", 0) > max_complexity:
                                high_complexity_items.append(
                                    {
                                        "file": file_path,
                                        "name": item.get("name"),
                                        "complexity": item.get("complexity"),
                                        "line": item.get("lineno"),
                                    }
                                )

                    if not high_complexity_items:
                        return (
                            True,
                            f"所有函数复杂度 <= {max_complexity}",
                            {
                                "max_complexity": max_complexity,
                                "details": complexity_data,
                            },
                        )
                    else:
                        return (
                            False,
                            f"发现 {len(high_complexity_items)} 个高复杂度函数",
                            {
                                "max_complexity": max_complexity,
                                "high_complexity_items": high_complexity_items,
                                "details": complexity_data,
                            },
                        )

                except json.JSONDecodeError:
                    return False, "无法解析复杂度报告", {"raw_output": result.stdout}

            return (
                False,
                "复杂度检查失败",
                {"stdout": result.stdout, "stderr": result.stderr},
            )

        except Exception as e:
            return False, f"复杂度检查失败: {e}", {"exception": str(e)}

    def _can_auto_fix(self, check_id: str) -> bool:
        """判断是否可以自动修复"""
        auto_fixable = {"format", "lint"}
        return check_id in auto_fixable

    def _auto_fix(self, check_id: str, details: Dict) -> bool:
        """尝试自动修复问题"""
        try:
            if check_id == "format":
                # black格式化通常不需要额外修复
                return True

            elif check_id == "lint":
                # 对于某些flake8问题，可以尝试自动修复
                return self._auto_fix_lint_issues(details)

            return False

            except Exception:
            return False

    def _auto_fix_lint_issues(self, details: Dict) -> bool:
        """自动修复lint问题"""
        try:
            # 这里可以实现一些简单的自动修复逻辑
            # 例如删除多余的空行、修复import顺序等

            # 运行isort修复import顺序
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "isort",
                    "src/core/",
                    "src/models/",
                    "src/services/",
                    "src/utils/",
                    "src/database/",
                    "src/api/",
                    "tests/",
                    "scripts/",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            return result.returncode == 0

            except Exception:
            return False

    def _log_iteration(self, retry: int, passed: bool) -> None:
        """记录迭代日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "retry": retry,
            "passed": passed,
            "checks": self.results["checks"].copy(),
        }

        self.iteration_log.append(log_entry)

    def save_results(self, output_file: str = "logs/quality_check.json") -> None:
        """保存检查结果"""
        output_path = self.project_root / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        full_results = {**self.results, "iteration_log": self.iteration_log}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_results, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 检查结果已保存到: {output_path}")

    def save_iteration_log(self, log_file: str = "logs/iteration.log") -> None:
        """保存迭代日志"""
        log_path = self.project_root / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = (
            f"[{datetime.now().isoformat()}] 质量检查 - "
            f"状态: {self.results['overall_status']}, "
            f"重试次数: {self.results['retry_count']}\n"
        )

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def print_summary(self) -> None:
        """打印检查摘要"""
        self.logger.info("\n📊 质量检查摘要:")
        self.logger.info(f"   ⚡ 整体状态: {self.results['overall_status']}")
        self.logger.info(f"   🔄 重试次数: {self.results['retry_count']}")

        for check_id, check_result in self.results["checks"].items():
            status = "✅" if check_result["success"] else "❌"
            self.logger.info(f"   {status} {check_result['name']}: {check_result['message']}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="代码质量检查器")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数")
    parser.add_argument("--output", default="logs/quality_check.json", help="结果输出文件")
    parser.add_argument("--summary", action="store_true", help="显示摘要")

    args = parser.parse_args()

    checker = QualityChecker(args.project_root, args.max_retries)
    results = checker.run_all_checks()
    checker.save_results(args.output)
    checker.save_iteration_log()

    if args.summary:
        checker.print_summary()

    # 返回适当的退出代码
    sys.exit(0 if results["overall_status"] == "passed" else 1)


if __name__ == "__main__":
    main()
