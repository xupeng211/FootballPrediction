#!/usr/bin/env python3
"""
防御机制验证系统 - 确保防御措施有效工作

这个模块负责：
1. 验证新生成的测试用例是否能正确运行
2. 检查lint规则是否能捕获预期的问题
3. 验证pre-commit钩子是否正常工作
4. 测试CI工作流是否按预期执行
5. 生成防御效果评估报告

作者：AI CI Guardian System
版本：v1.0.0
"""

import json
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click


class TestValidator:
    """测试验证器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"

    def validate_test_files(self, test_files: List[str]) -> Dict[str, Any]:
        """验证测试文件是否能正确运行"""
        results = {
            "total_tests": len(test_files),
            "passed_tests": 0,
            "failed_tests": 0,
            "test_results": {},
            "validation_time": 0,
        }

        start_time = time.time()

        for test_file in test_files:
            test_path = self.tests_dir / test_file
            if not test_path.exists():
                results["test_results"][test_file] = {
                    "status": "not_found",
                    "message": f"测试文件不存在: {test_path}",
                }
                results["failed_tests"] += 1
                continue

            # 运行单个测试文件
            test_result = self._run_single_test(test_path)
            results["test_results"][test_file] = test_result

            if test_result["status"] == "passed":
                results["passed_tests"] += 1
            else:
                results["failed_tests"] += 1

        results["validation_time"] = time.time() - start_time
        results["success_rate"] = (
            results["passed_tests"] / max(results["total_tests"], 1)
        ) * 100

        return results

    def _run_single_test(self, test_path: Path) -> Dict[str, Any]:
        """运行单个测试文件"""
        try:
            result = subprocess.run(
                ["pytest", str(test_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            if result.returncode == 0:
                return {
                    "status": "passed",
                    "message": "测试通过",
                    "output": result.stdout[-500:] if result.stdout else "",
                    "test_count": self._count_tests_in_output(result.stdout),
                }
            else:
                return {
                    "status": "failed",
                    "message": "测试失败",
                    "output": result.stdout[-500:] if result.stdout else "",
                    "error": result.stderr[-500:] if result.stderr else "",
                    "test_count": self._count_tests_in_output(result.stdout),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "测试超时",
                "output": "",
                "error": "测试运行超过60秒",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"测试运行错误: {e}",
                "output": "",
                "error": str(e),
            }

    def _count_tests_in_output(self, output: str) -> int:
        """从测试输出中统计测试数量"""
        if not output:
            return 0

        # 查找类似 "3 passed" 的模式
        import re

        match = re.search(r"(\d+) passed", output)
        if match:
            return int(match.group(1))

        # 或者计算 "test_" 出现的次数
        return output.count("::test_")

    def validate_test_coverage(self, test_files: List[str]) -> Dict[str, Any]:
        """验证测试覆盖率"""
        if not test_files:
            return {"status": "skipped", "message": "没有测试文件"}

        try:
            # 运行覆盖率测试
            result = subprocess.run(
                ["pytest"]
                + [f"tests/{tf}" for tf in test_files]
                + ["--cov=src", "--cov-report=json", "--cov-report=term-missing"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=120,
            )

            coverage_data = {}
            coverage_file = self.project_root / "coverage.json"

            if coverage_file.exists():
                with open(coverage_file, "r") as f:
                    coverage_data = json.load(f)

            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)

            return {
                "status": "completed",
                "total_coverage": total_coverage,
                "coverage_data": coverage_data.get("files", {}),
                "meets_threshold": total_coverage >= 80,
                "output": result.stdout[-500:] if result.stdout else "",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"覆盖率检查失败: {e}",
                "error": str(e),
            }


class LintValidator:
    """Lint配置验证器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def validate_lint_configs(self, config_files: List[str]) -> Dict[str, Any]:
        """验证lint配置是否有效"""
        results = {
            "total_configs": len(config_files),
            "valid_configs": 0,
            "invalid_configs": 0,
            "config_results": {},
        }

        for config_file in config_files:
            config_path = self.project_root / config_file

            if "pyproject.toml" in config_file or "ruff" in config_file:
                result = self._validate_ruff_config(config_path)
            elif "mypy" in config_file:
                result = self._validate_mypy_config(config_path)
            elif "bandit" in config_file:
                result = self._validate_bandit_config(config_path)
            else:
                result = self._validate_generic_config(config_path)

            results["config_results"][config_file] = result

            if result["status"] == "valid":
                results["valid_configs"] += 1
            else:
                results["invalid_configs"] += 1

        results["success_rate"] = (
            results["valid_configs"] / max(results["total_configs"], 1)
        ) * 100

        return results

    def _validate_ruff_config(self, config_path: Path) -> Dict[str, Any]:
        """验证ruff配置"""
        if not config_path.exists():
            return {"status": "not_found", "message": f"配置文件不存在: {config_path}"}

        try:
            # 测试ruff配置
            result = subprocess.run(
                ["ruff", "check", "--config", str(config_path), "src/", "--no-fix"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            # ruff返回码可能不为0（因为有lint问题），但配置有效
            return {
                "status": "valid",
                "message": "Ruff配置有效",
                "output": result.stdout[-200:] if result.stdout else "",
                "issues_found": result.returncode != 0,
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Ruff检查超时"}
        except FileNotFoundError:
            return {"status": "tool_not_found", "message": "Ruff工具未安装"}
        except Exception as e:
            return {"status": "error", "message": f"Ruff配置验证失败: {e}"}

    def _validate_mypy_config(self, config_path: Path) -> Dict[str, Any]:
        """验证mypy配置"""
        if not config_path.exists():
            return {"status": "not_found", "message": f"配置文件不存在: {config_path}"}

        try:
            # 测试mypy配置
            result = subprocess.run(
                ["mypy", "--config-file", str(config_path), "src/"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            return {
                "status": "valid",
                "message": "MyPy配置有效",
                "output": result.stdout[-200:] if result.stdout else "",
                "issues_found": result.returncode != 0,
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "MyPy检查超时"}
        except FileNotFoundError:
            return {"status": "tool_not_found", "message": "MyPy工具未安装"}
        except Exception as e:
            return {"status": "error", "message": f"MyPy配置验证失败: {e}"}

    def _validate_bandit_config(self, config_path: Path) -> Dict[str, Any]:
        """验证bandit配置"""
        if not config_path.exists():
            return {"status": "not_found", "message": f"配置文件不存在: {config_path}"}

        try:
            # 测试bandit配置
            result = subprocess.run(
                ["bandit", "-c", str(config_path), "-r", "src/", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            return {
                "status": "valid",
                "message": "Bandit配置有效",
                "output": result.stdout[-200:] if result.stdout else "",
                "issues_found": result.returncode != 0,
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Bandit检查超时"}
        except FileNotFoundError:
            return {"status": "tool_not_found", "message": "Bandit工具未安装"}
        except Exception as e:
            return {"status": "error", "message": f"Bandit配置验证失败: {e}"}

    def _validate_generic_config(self, config_path: Path) -> Dict[str, Any]:
        """验证通用配置文件"""
        if not config_path.exists():
            return {"status": "not_found", "message": f"配置文件不存在: {config_path}"}

        try:
            # 基础文件语法检查
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

            if config_path.suffix == ".toml":
                import tomllib

                tomllib.loads(content)
            elif config_path.suffix in [".yaml", ".yml"]:
                import yaml

                yaml.safe_load(content)
            elif config_path.suffix == ".json":
                json.loads(content)

            return {
                "status": "valid",
                "message": "配置文件语法正确",
                "size": len(content),
            }

        except Exception as e:
            return {"status": "invalid", "message": f"配置文件语法错误: {e}"}


class PreCommitValidator:
    """Pre-commit钩子验证器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def validate_precommit_hooks(self, precommit_files: List[str]) -> Dict[str, Any]:
        """验证pre-commit钩子配置"""
        if not precommit_files:
            return {"status": "skipped", "message": "没有pre-commit配置"}

        config_path = self.project_root / ".pre-commit-config.yaml"
        if not config_path.exists():
            return {"status": "not_found", "message": "pre-commit配置文件不存在"}

        try:
            # 验证配置文件语法
            with open(config_path, "r", encoding="utf-8") as f:
                import yaml

                config = yaml.safe_load(f)

            if not isinstance(config, dict) or "repos" not in config:
                return {"status": "invalid", "message": "pre-commit配置格式错误"}

            # 尝试安装和运行pre-commit
            install_result = self._install_precommit_hooks()
            if not install_result["success"]:
                return {
                    "status": "install_failed",
                    "message": "pre-commit钩子安装失败",
                    "error": install_result["error"],
                }

            # 运行pre-commit检查
            run_result = self._run_precommit_hooks()

            return {
                "status": "valid",
                "message": "pre-commit钩子配置有效",
                "hooks_count": len(self._count_hooks(config)),
                "install_result": install_result,
                "run_result": run_result,
            }

        except Exception as e:
            return {"status": "error", "message": f"pre-commit验证失败: {e}"}

    def _install_precommit_hooks(self) -> Dict[str, Any]:
        """安装pre-commit钩子"""
        try:
            result = subprocess.run(
                ["pre-commit", "install"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout[-200:] if result.stdout else "",
                "error": result.stderr[-200:] if result.stderr else "",
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "pre-commit安装超时"}
        except FileNotFoundError:
            return {"success": False, "error": "pre-commit工具未安装"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_precommit_hooks(self) -> Dict[str, Any]:
        """运行pre-commit钩子"""
        try:
            # 只运行快速检查，避免长时间运行
            result = subprocess.run(
                ["pre-commit", "run", "--all-files", "trailing-whitespace"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            return {
                "success": True,  # pre-commit可能会找到问题，但这是正常的
                "output": result.stdout[-200:] if result.stdout else "",
                "issues_found": result.returncode != 0,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "pre-commit运行超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _count_hooks(self, config: Dict) -> List[str]:
        """统计配置中的钩子数量"""
        hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hooks.append(hook.get("id", "unknown"))
        return hooks


class CIWorkflowValidator:
    """CI工作流验证器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.workflows_dir = project_root / ".github" / "workflows"

    def validate_ci_workflows(self, workflow_files: List[str]) -> Dict[str, Any]:
        """验证CI工作流文件"""
        results = {
            "total_workflows": len(workflow_files),
            "valid_workflows": 0,
            "invalid_workflows": 0,
            "workflow_results": {},
        }

        for workflow_file in workflow_files:
            workflow_path = self.workflows_dir / workflow_file
            result = self._validate_single_workflow(workflow_path)
            results["workflow_results"][workflow_file] = result

            if result["status"] == "valid":
                results["valid_workflows"] += 1
            else:
                results["invalid_workflows"] += 1

        results["success_rate"] = (
            results["valid_workflows"] / max(results["total_workflows"], 1)
        ) * 100

        return results

    def _validate_single_workflow(self, workflow_path: Path) -> Dict[str, Any]:
        """验证单个工作流文件"""
        if not workflow_path.exists():
            return {
                "status": "not_found",
                "message": f"工作流文件不存在: {workflow_path}",
            }

        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                import yaml

                workflow = yaml.safe_load(f)

            # 检查基本结构
            if not isinstance(workflow, dict):
                return {"status": "invalid", "message": "工作流文件格式错误"}

            required_fields = ["name", "on", "jobs"]
            missing_fields = [
                field for field in required_fields if field not in workflow
            ]
            if missing_fields:
                return {
                    "status": "invalid",
                    "message": f"缺少必需字段: {', '.join(missing_fields)}",
                }

            # 检查作业结构
            jobs = workflow.get("jobs", {})
            if not jobs:
                return {"status": "invalid", "message": "工作流没有定义作业"}

            job_count = len(jobs)
            step_count = sum(len(job.get("steps", [])) for job in jobs.values())

            # 检查是否包含防御验证步骤
            has_defense_steps = False
            for job in jobs.values():
                for step in job.get("steps", []):
                    step_name = step.get("name", "").lower()
                    if any(
                        keyword in step_name
                        for keyword in ["defense", "validation", "guardian"]
                    ):
                        has_defense_steps = True
                        break
                if has_defense_steps:
                    break

            return {
                "status": "valid",
                "message": "工作流文件有效",
                "job_count": job_count,
                "step_count": step_count,
                "has_defense_steps": has_defense_steps,
            }

        except yaml.YAMLError as e:
            return {"status": "invalid", "message": f"YAML语法错误: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"工作流验证失败: {e}"}


class EffectivenessValidator:
    """防御效果验证器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def validate_defense_effectiveness(
        self, original_issues: List[Dict], defenses: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """验证防御机制的有效性"""
        results = {
            "original_issues_count": len(original_issues),
            "defense_types": len([v for v in defenses.values() if v]),
            "test_reproduction": {},
            "issue_coverage": {},
            "effectiveness_score": 0,
        }

        # 尝试重现原始问题以验证防御措施
        results["test_reproduction"] = self._test_issue_reproduction(original_issues)

        # 分析问题覆盖率
        results["issue_coverage"] = self._analyze_issue_coverage(
            original_issues, defenses
        )

        # 计算效果评分
        results["effectiveness_score"] = self._calculate_effectiveness_score(results)

        return results

    def _test_issue_reproduction(self, issues: List[Dict]) -> Dict[str, Any]:
        """测试是否能重现原始问题"""
        reproduction_results = {
            "reproducible_issues": 0,
            "non_reproducible_issues": 0,
            "issue_details": {},
        }

        # 创建临时的"坏"代码来测试防御机制
        test_cases = self._create_test_cases_for_issues(issues)

        for issue_type, test_case in test_cases.items():
            result = self._run_defense_test(test_case)
            reproduction_results["issue_details"][issue_type] = result

            if result["detected"]:
                reproduction_results["reproducible_issues"] += 1
            else:
                reproduction_results["non_reproducible_issues"] += 1

        return reproduction_results

    def _create_test_cases_for_issues(self, issues: List[Dict]) -> Dict[str, Dict]:
        """为不同类型的问题创建测试用例"""
        test_cases = {}

        # 按问题类型分组
        issues_by_type = {}
        for issue in issues:
            issue_type = issue.get("category", "unknown")
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        # 为每种问题类型创建测试用例
        for issue_type, issue_list in issues_by_type.items():
            if issue_type == "import_error":
                test_cases[issue_type] = self._create_import_error_test()
            elif issue_type == "type_error":
                test_cases[issue_type] = self._create_type_error_test()
            elif issue_type == "style_error":
                test_cases[issue_type] = self._create_style_error_test()
            elif issue_type == "security_issue":
                test_cases[issue_type] = self._create_security_issue_test()

        return test_cases

    def _create_import_error_test(self) -> Dict[str, Any]:
        """创建导入错误测试用例"""
        bad_code = """
# 故意创建的错误代码来测试防御机制
import non_existent_module
from another_missing_module import something

def test_function():
    return non_existent_module.do_something()
"""

        return {
            "type": "import_error",
            "code": bad_code,
            "expected_tools": ["pytest", "mypy"],
            "description": "测试导入不存在的模块",
        }

    def _create_type_error_test(self) -> Dict[str, Any]:
        """创建类型错误测试用例"""
        bad_code = """
# 故意创建的类型错误来测试防御机制
def add_numbers(a: int, b: int) -> int:
    return a + b

# 类型错误：传递字符串给期望整数的函数
result = add_numbers("hello", "world")
"""

        return {
            "type": "type_error",
            "code": bad_code,
            "expected_tools": ["mypy"],
            "description": "测试类型不匹配错误",
        }

    def _create_style_error_test(self) -> Dict[str, Any]:
        """创建代码风格错误测试用例"""
        bad_code = """
# 故意创建的风格错误来测试防御机制
import os,sys,json
import numpy

def badly_formatted_function(   x,y   ):
    if True:
            return x+y


    # 多余的空行和糟糕的格式
"""

        return {
            "type": "style_error",
            "code": bad_code,
            "expected_tools": ["ruff", "black"],
            "description": "测试代码风格问题",
        }

    def _create_security_issue_test(self) -> Dict[str, Any]:
        """创建安全问题测试用例"""
        bad_code = """
# 故意创建的安全问题来测试防御机制
password = "hardcoded_password_123"

def vulnerable_function():
    import subprocess
    # 不安全的命令执行
    subprocess.call("rm -rf /", shell=True)

    # 不安全的eval使用
    user_input = "print('hello')"
    eval(user_input)
"""

        return {
            "type": "security_issue",
            "code": bad_code,
            "expected_tools": ["bandit"],
            "description": "测试安全漏洞检测",
        }

    def _run_defense_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行防御测试"""
        result = {"detected": False, "detection_tools": [], "output": "", "error": ""}

        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_case["code"])
            temp_file = Path(f.name)

        try:
            # 对每个预期工具运行测试
            for tool in test_case.get("expected_tools", []):
                tool_result = self._test_tool_detection(tool, temp_file)
                if tool_result["detected"]:
                    result["detected"] = True
                    result["detection_tools"].append(tool)
                    result["output"] += f"{tool}: {tool_result['output']}\n"

        finally:
            # 清理临时文件
            temp_file.unlink(missing_ok=True)

        return result

    def _test_tool_detection(self, tool: str, file_path: Path) -> Dict[str, Any]:
        """测试特定工具是否能检测问题"""
        try:
            if tool == "ruff":
                result = subprocess.run(
                    ["ruff", "check", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            elif tool == "mypy":
                result = subprocess.run(
                    ["mypy", str(file_path)], capture_output=True, text=True, timeout=10
                )
            elif tool == "bandit":
                result = subprocess.run(
                    ["bandit", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            elif tool == "pytest":
                result = subprocess.run(
                    ["python", "-m", "py_compile", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            else:
                return {"detected": False, "output": f"未知工具: {tool}"}

            # 如果工具返回非0退出码，说明检测到了问题
            detected = result.returncode != 0
            output = result.stdout + result.stderr

            return {
                "detected": detected,
                "output": output[-100:] if output else "",  # 只保留最后100字符
            }

        except Exception as e:
            return {"detected": False, "output": f"工具运行错误: {e}"}

    def _analyze_issue_coverage(
        self, issues: List[Dict], defenses: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """分析问题覆盖率"""
        issue_types = set(issue.get("category", "unknown") for issue in issues)

        coverage_analysis = {
            "total_issue_types": len(issue_types),
            "covered_types": 0,
            "uncovered_types": [],
            "coverage_details": {},
        }

        # 检查每种问题类型是否有对应的防御措施
        for issue_type in issue_types:
            has_coverage = False
            coverage_methods = []

            # 检查是否有相应的测试
            test_files = defenses.get("test_files", [])
            if any(issue_type in test_file for test_file in test_files):
                has_coverage = True
                coverage_methods.append("validation_tests")

            # 检查是否有相应的lint配置
            if issue_type in ["style_error", "type_error", "security_issue"]:
                lint_configs = defenses.get("lint_configs", [])
                if lint_configs:
                    has_coverage = True
                    coverage_methods.append("lint_configs")

            # 检查是否有pre-commit钩子
            if defenses.get("pre_commit_hooks"):
                has_coverage = True
                coverage_methods.append("pre_commit_hooks")

            coverage_analysis["coverage_details"][issue_type] = {
                "covered": has_coverage,
                "methods": coverage_methods,
            }

            if has_coverage:
                coverage_analysis["covered_types"] += 1
            else:
                coverage_analysis["uncovered_types"].append(issue_type)

        coverage_analysis["coverage_rate"] = (
            coverage_analysis["covered_types"]
            / max(coverage_analysis["total_issue_types"], 1)
        ) * 100

        return coverage_analysis

    def _calculate_effectiveness_score(self, results: Dict[str, Any]) -> float:
        """计算防御效果评分"""
        scores = []

        # 测试重现评分（30%）
        repro = results.get("test_reproduction", {})
        total_repro = repro.get("reproducible_issues", 0) + repro.get(
            "non_reproducible_issues", 0
        )
        if total_repro > 0:
            repro_score = (repro.get("reproducible_issues", 0) / total_repro) * 100
            scores.append(repro_score * 0.3)

        # 问题覆盖率评分（40%）
        coverage = results.get("issue_coverage", {})
        coverage_rate = coverage.get("coverage_rate", 0)
        scores.append(coverage_rate * 0.4)

        # 防御类型多样性评分（20%）
        defense_types = results.get("defense_types", 0)
        diversity_score = min(defense_types * 25, 100)  # 每种类型25分，最高100
        scores.append(diversity_score * 0.2)

        # 原始问题数量评分（10%）
        issue_count = results.get("original_issues_count", 0)
        issue_score = min(issue_count * 10, 100)  # 每个问题10分，最高100
        scores.append(issue_score * 0.1)

        return sum(scores)


class DefenseValidator:
    """防御机制验证器主控制器"""

    def __init__(self, project_root: Path = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()

        self.test_validator = TestValidator(self.project_root)
        self.lint_validator = LintValidator(self.project_root)
        self.precommit_validator = PreCommitValidator(self.project_root)
        self.workflow_validator = CIWorkflowValidator(self.project_root)
        self.effectiveness_validator = EffectivenessValidator(self.project_root)

    def validate_all_defenses(
        self, defenses: Dict[str, List[str]], original_issues: List[Dict] = None
    ) -> Dict[str, Any]:
        """验证所有防御机制"""
        start_time = time.time()

        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "validation_summary": {},
            "detailed_results": {},
            "overall_score": 0,
            "validation_time": 0,
        }

        click.echo("🔍 开始验证防御机制...")

        # 1. 验证测试文件
        if defenses.get("test_files"):
            click.echo("  📋 验证测试文件...")
            test_results = self.test_validator.validate_test_files(
                defenses["test_files"]
            )
            validation_results["detailed_results"]["tests"] = test_results

            # 验证测试覆盖率
            coverage_results = self.test_validator.validate_test_coverage(
                defenses["test_files"]
            )
            validation_results["detailed_results"]["coverage"] = coverage_results

        # 2. 验证lint配置
        if defenses.get("lint_configs"):
            click.echo("  🔧 验证lint配置...")
            lint_results = self.lint_validator.validate_lint_configs(
                defenses["lint_configs"]
            )
            validation_results["detailed_results"]["lint_configs"] = lint_results

        # 3. 验证pre-commit钩子
        if defenses.get("pre_commit_hooks"):
            click.echo("  🪝 验证pre-commit钩子...")
            precommit_results = self.precommit_validator.validate_precommit_hooks(
                defenses["pre_commit_hooks"]
            )
            validation_results["detailed_results"]["pre_commit"] = precommit_results

        # 4. 验证CI工作流
        if defenses.get("ci_workflows"):
            click.echo("  ⚙️ 验证CI工作流...")
            workflow_results = self.workflow_validator.validate_ci_workflows(
                defenses["ci_workflows"]
            )
            validation_results["detailed_results"]["workflows"] = workflow_results

        # 5. 验证防御效果
        if original_issues:
            click.echo("  🎯 验证防御效果...")
            effectiveness_results = (
                self.effectiveness_validator.validate_defense_effectiveness(
                    original_issues, defenses
                )
            )
            validation_results["detailed_results"][
                "effectiveness"
            ] = effectiveness_results

        # 计算总体评分
        validation_results["overall_score"] = self._calculate_overall_score(
            validation_results["detailed_results"]
        )
        validation_results["validation_time"] = time.time() - start_time

        # 生成验证摘要
        validation_results["validation_summary"] = self._generate_validation_summary(
            validation_results
        )

        return validation_results

    def _calculate_overall_score(self, detailed_results: Dict[str, Any]) -> float:
        """计算总体验证评分"""
        scores = []
        weights = {
            "tests": 0.25,
            "lint_configs": 0.25,
            "pre_commit": 0.15,
            "workflows": 0.15,
            "effectiveness": 0.20,
        }

        for category, weight in weights.items():
            if category in detailed_results:
                result = detailed_results[category]

                if category == "tests":
                    score = result.get("success_rate", 0)
                elif category == "lint_configs":
                    score = result.get("success_rate", 0)
                elif category == "pre_commit":
                    score = 100 if result.get("status") == "valid" else 0
                elif category == "workflows":
                    score = result.get("success_rate", 0)
                elif category == "effectiveness":
                    score = result.get("effectiveness_score", 0)
                else:
                    score = 0

                scores.append(score * weight)

        return sum(scores)

    def _generate_validation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成验证摘要"""
        summary = {
            "overall_status": "passed" if results["overall_score"] >= 80 else "failed",
            "total_score": results["overall_score"],
            "validation_time": results["validation_time"],
            "component_status": {},
        }

        detailed = results.get("detailed_results", {})

        # 测试状态
        if "tests" in detailed:
            test_result = detailed["tests"]
            summary["component_status"]["tests"] = {
                "status": (
                    "passed" if test_result.get("success_rate", 0) >= 80 else "failed"
                ),
                "passed": test_result.get("passed_tests", 0),
                "total": test_result.get("total_tests", 0),
                "success_rate": test_result.get("success_rate", 0),
            }

        # Lint配置状态
        if "lint_configs" in detailed:
            lint_result = detailed["lint_configs"]
            summary["component_status"]["lint_configs"] = {
                "status": (
                    "passed" if lint_result.get("success_rate", 0) >= 80 else "failed"
                ),
                "valid": lint_result.get("valid_configs", 0),
                "total": lint_result.get("total_configs", 0),
                "success_rate": lint_result.get("success_rate", 0),
            }

        # Pre-commit状态
        if "pre_commit" in detailed:
            precommit_result = detailed["pre_commit"]
            summary["component_status"]["pre_commit"] = {
                "status": precommit_result.get("status", "unknown"),
                "message": precommit_result.get("message", ""),
            }

        # 工作流状态
        if "workflows" in detailed:
            workflow_result = detailed["workflows"]
            summary["component_status"]["workflows"] = {
                "status": (
                    "passed"
                    if workflow_result.get("success_rate", 0) >= 80
                    else "failed"
                ),
                "valid": workflow_result.get("valid_workflows", 0),
                "total": workflow_result.get("total_workflows", 0),
                "success_rate": workflow_result.get("success_rate", 0),
            }

        # 效果验证状态
        if "effectiveness" in detailed:
            effectiveness_result = detailed["effectiveness"]
            summary["component_status"]["effectiveness"] = {
                "score": effectiveness_result.get("effectiveness_score", 0),
                "coverage_rate": effectiveness_result.get("issue_coverage", {}).get(
                    "coverage_rate", 0
                ),
                "reproducible_issues": effectiveness_result.get(
                    "test_reproduction", {}
                ).get("reproducible_issues", 0),
            }

        return summary


@click.command()
@click.option("--defenses-file", "-d", help="防御机制JSON文件路径")
@click.option("--issues-file", "-i", help="原始问题JSON文件路径")
@click.option("--project-root", "-p", help="项目根目录路径")
@click.option("--output", "-o", help="验证结果输出文件路径")
@click.option("--tests-only", "-t", is_flag=True, help="仅验证测试文件")
@click.option("--configs-only", "-c", is_flag=True, help="仅验证配置文件")
@click.option("--effectiveness-only", "-e", is_flag=True, help="仅验证防御效果")
@click.option("--summary", "-s", is_flag=True, help="显示验证摘要")
@click.option("--detailed", "-dt", is_flag=True, help="显示详细结果")
def main(
    defenses_file,
    issues_file,
    project_root,
    output,
    tests_only,
    configs_only,
    effectiveness_only,
    summary,
    detailed,
):
    """
    🔍 防御机制验证系统

    验证生成的防御机制是否能有效工作并捕获CI问题。

    Examples:
        defense_validator.py -d logs/defenses_generated.json -s
        defense_validator.py -d logs/defenses_generated.json -i logs/ci_issues.json -e
        defense_validator.py -t -c  # 仅验证测试和配置
    """

    project_path = Path(project_root) if project_root else Path.cwd()
    validator = DefenseValidator(project_path)

    click.echo("🔍 防御机制验证系统启动")

    # 读取防御机制文件
    if not defenses_file:
        defenses_file = project_path / "logs" / "defenses_generated.json"

    defenses_path = Path(defenses_file)
    if not defenses_path.exists():
        click.echo(f"❌ 防御机制文件不存在: {defenses_file}")
        return

    try:
        with open(defenses_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            defenses = data.get("defenses", {})
    except Exception as e:
        click.echo(f"❌ 读取防御机制文件失败: {e}")
        return

    # 读取原始问题文件（可选）
    original_issues = []
    if issues_file:
        issues_path = Path(issues_file)
        if issues_path.exists():
            try:
                with open(issues_path, "r", encoding="utf-8") as f:
                    original_issues = json.load(f)
            except Exception as e:
                click.echo(f"⚠️ 读取问题文件失败: {e}")

    click.echo(
        f"📋 验证 {sum(len(files) for files in defenses.values())} 个防御机制文件"
    )

    # 根据选项执行特定验证
    if tests_only:
        test_results = validator.test_validator.validate_test_files(
            defenses.get("test_files", [])
        )
        click.echo(
            f"📊 测试验证结果: {test_results.get('success_rate', 0):.1f}% 通过率"
        )
    elif configs_only:
        lint_results = validator.lint_validator.validate_lint_configs(
            defenses.get("lint_configs", [])
        )
        click.echo(
            f"📊 配置验证结果: {lint_results.get('success_rate', 0):.1f}% 有效率"
        )
    elif effectiveness_only:
        if original_issues:
            effectiveness_results = (
                validator.effectiveness_validator.validate_defense_effectiveness(
                    original_issues, defenses
                )
            )
            click.echo(
                f"📊 防御效果评分: {effectiveness_results.get('effectiveness_score', 0):.1f}"
            )
        else:
            click.echo("❌ 需要原始问题文件来验证防御效果")
    else:
        # 执行完整验证
        validation_results = validator.validate_all_defenses(defenses, original_issues)

        if summary:
            summary_data = validation_results["validation_summary"]
            click.echo("\n📊 验证摘要:")
            click.echo(f"  总体状态: {summary_data['overall_status']}")
            click.echo(f"  总体评分: {summary_data['total_score']:.1f}")
            click.echo(f"  验证用时: {summary_data['validation_time']:.2f}秒")

            for component, status in summary_data["component_status"].items():
                if isinstance(status, dict) and "status" in status:
                    click.echo(f"  {component}: {status['status']}")

        if detailed:
            click.echo("\n📋 详细结果:")
            for category, result in validation_results["detailed_results"].items():
                click.echo(f"  {category}:")
                if "success_rate" in result:
                    click.echo(f"    成功率: {result['success_rate']:.1f}%")
                if "message" in result:
                    click.echo(f"    信息: {result['message']}")

        # 保存验证结果
        if output:
            output_path = Path(output)
        else:
            output_path = project_path / "logs" / "validation_results.json"

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(validation_results, f, indent=2, ensure_ascii=False)
            click.echo(f"💾 验证结果已保存到: {output_path}")
        except Exception as e:
            click.echo(f"⚠️ 保存验证结果失败: {e}")

        # 显示最终状态
        overall_status = validation_results["validation_summary"]["overall_status"]
        if overall_status == "passed":
            click.echo("✅ 防御机制验证通过，可以有效防护CI问题")
        else:
            click.echo("❌ 防御机制验证失败，需要进一步完善")


if __name__ == "__main__":
    main()
