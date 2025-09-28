#!/usr/bin/env python3
"""
AI 修复验证器 - 验证修复效果并提供反馈
"""

import json
import logging
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import ast

logger = logging.getLogger(__name__)

@dataclass
class FixValidationConfig:
    """修复验证配置"""
    # 验证控制
    timeout_per_test: int = 30  # 秒
    max_validation_time: int = 300  # 总验证时间
    non_blocking_mode: bool = True

    # 验证项目
    run_pytest: bool = True
    run_linting: bool = True
    run_type_check: bool = True
    run_coverage: bool = False  # 可选，耗时较长

    # 质量阈值
    min_test_pass_rate: float = 0.8  # 80%测试通过率
    max_lint_errors: int = 5
    max_type_errors: int = 3

    # 重试机制
    max_retry_attempts: int = 2
    enable_auto_improvement: bool = True

class FixValidator:
    """修复验证器"""

    def __init__(self, config: Optional[FixValidationConfig] = None):
        self.config = config or FixValidationConfig()
        self.reports_dir = Path("docs/_reports/validation")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def validate_fix(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证修复效果

        Args:
            fix_info: 修复信息，包含文件路径、修改内容等

        Returns:
            验证结果
        """
        start_time = time.time()

        try:
            logger.info(f"Validating fix for {fix_info.get('file_path', 'unknown')}")

            validation_results = {
                "fix_info": fix_info,
                "validation_time": 0,
                "overall_result": "unknown",
                "test_results": None,
                "lint_results": None,
                "type_check_results": None,
                "coverage_results": None,
                "quality_score": 0,
                "recommendations": [],
                "improvement_suggestions": [],
                "retry_attempts": 0
            }

            # 1. 运行测试验证
            if self.config.run_pytest:
                test_results = self._run_test_validation(fix_info)
                validation_results["test_results"] = test_results

                # 检查是否需要重试
                if test_results.get("pass_rate", 0) < self.config.min_test_pass_rate:
                    if validation_results["retry_attempts"] < self.config.max_retry_attempts:
                        improvement = self._generate_improvement_suggestions(fix_info, test_results)
                        validation_results["improvement_suggestions"].append(improvement)
                        validation_results["retry_attempts"] += 1

            # 2. 运行代码质量检查
            if self.config.run_linting:
                lint_results = self._run_lint_validation(fix_info)
                validation_results["lint_results"] = lint_results

            # 3. 运行类型检查
            if self.config.run_type_check:
                type_results = self._run_type_validation(fix_info)
                validation_results["type_check_results"] = type_results

            # 4. 运行覆盖率检查（可选）
            if self.config.run_coverage:
                coverage_results = self._run_coverage_validation(fix_info)
                validation_results["coverage_results"] = coverage_results

            # 计算综合评分
            quality_score = self._calculate_quality_score(validation_results)
            validation_results["quality_score"] = quality_score

            # 生成整体评估和建议
            overall_result = self._evaluate_overall_result(validation_results)
            validation_results["overall_result"] = overall_result

            # 生成改进建议
            recommendations = self._generate_recommendations(validation_results)
            validation_results["recommendations"] = recommendations

            validation_results["validation_time"] = time.time() - start_time

            # 保存验证结果
            self._save_validation_results(validation_results)

            return validation_results

        except Exception as e:
            logger.error(f"Failed to validate fix: {e}")
            return {
                "fix_info": fix_info,
                "error": str(e),
                "validation_time": time.time() - start_time,
                "overall_result": "error"
            }

    def _run_test_validation(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行测试验证"""
        file_path = fix_info.get("file_path")
        if not file_path:
            return {"error": "No file path provided"}

        try:
            # 确定要运行的测试
            test_file = self._get_corresponding_test_file(file_path)

            if test_file and Path(test_file).exists():
                # 运行特定测试文件
                cmd = [
                    "python", "-m", "pytest",
                    test_file,
                    "--tb=short",
                    "-v",
                    "--maxfail=10"
                ]
            else:
                # 运行所有测试，但过滤相关文件
                cmd = [
                    "python", "-m", "pytest",
                    "--tb=short",
                    "-v",
                    "--maxfail=10"
                ]

            logger.info(f"Running test validation: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_per_test
            )

            # 解析测试结果
            test_results = self._parse_test_output(result.stdout, result.stderr)

            return {
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "execution_time": None,  # TODO: 计算执行时间
                "test_results": test_results,
                "raw_output": result.stdout,
                "raw_error": result.stderr
            }

        except subprocess.TimeoutExpired:
            return {"error": "Test validation timed out", "timeout": True}
        except Exception as e:
            return {"error": f"Test validation failed: {e}"}

    def _get_corresponding_test_file(self, file_path: str) -> Optional[str]:
        """获取对应的测试文件"""
        if file_path.startswith("src/"):
            # src/module/file.py -> tests/test_module_file.py
            relative_path = file_path[4:]  # 移除src/
            test_name = f"tests/test_{relative_path.replace('/', '_')[:-3]}"  # 移除.py
            return test_name
        return None

    def _parse_test_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """解析pytest输出"""
        lines = stdout.split('\n') + stderr.split('\n')

        results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "skipped_tests": 0,
            "pass_rate": 0.0,
            "failed_test_names": [],
            "error_messages": []
        }

        for line in lines:
            # 解析测试结果行
            if "collected" in line and "items" in line:
                match = re.search(r'(\d+)\s+items?', line)
                if match:
                    results["total_tests"] = int(match.group(1))

            elif "passed" in line and "failed" in line:
                # 解析类似 "3 passed, 1 failed in 0.12s" 的行
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        match = re.search(r'(\d+)\s+passed', part)
                        if match:
                            results["passed_tests"] = int(match.group(1))
                    elif "failed" in part:
                        match = re.search(r'(\d+)\s+failed', part)
                        if match:
                            results["failed_tests"] = int(match.group(1))
                    elif "error" in part:
                        match = re.search(r'(\d+)\s+error', part)
                        if match:
                            results["error_tests"] = int(match.group(1))
                    elif "skipped" in part:
                        match = re.search(r'(\d+)\s+skipped', part)
                        if match:
                            results["skipped_tests"] = int(match.group(1))

            # 解析失败测试名称
            elif line.startswith("FAILED "):
                test_name = line.replace("FAILED ", "").strip()
                results["failed_test_names"].append(test_name)

            # 解析错误信息
            elif line.startswith("ERROR "):
                test_name = line.replace("ERROR ", "").strip()
                results["failed_test_names"].append(test_name)

        # 计算通过率
        if results["total_tests"] > 0:
            passed = results["passed_tests"]
            total = results["total_tests"]
            results["pass_rate"] = passed / total

        return results

    def _run_lint_validation(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行代码风格检查"""
        file_path = fix_info.get("file_path")
        if not file_path:
            return {"error": "No file path provided"}

        try:
            # 运行flake8
            cmd = ["python", "-m", "flake8", file_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # 解析flake8输出
            lint_errors = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        lint_errors.append(line)

            return {
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "error_count": len(lint_errors),
                "errors": lint_errors[:10],  # 只保留前10个错误
                "within_threshold": len(lint_errors) <= self.config.max_lint_errors
            }

        except subprocess.TimeoutExpired:
            return {"error": "Lint validation timed out", "timeout": True}
        except Exception as e:
            return {"error": f"Lint validation failed: {e}"}

    def _run_type_validation(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行类型检查"""
        file_path = fix_info.get("file_path")
        if not file_path:
            return {"error": "No file path provided"}

        try:
            # 运行mypy
            cmd = ["python", "-m", "mypy", file_path, "--ignore-missing-imports"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            # 解析mypy输出
            type_errors = []
            if result.stdout or result.stderr:
                output = result.stdout + result.stderr
                for line in output.split('\n'):
                    if "error:" in line.lower():
                        type_errors.append(line.strip())

            return {
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "error_count": len(type_errors),
                "errors": type_errors[:10],  # 只保留前10个错误
                "within_threshold": len(type_errors) <= self.config.max_type_errors
            }

        except subprocess.TimeoutExpired:
            return {"error": "Type validation timed out", "timeout": True}
        except Exception as e:
            return {"error": f"Type validation failed: {e}"}

    def _run_coverage_validation(self, fix_info: Dict[str, Any]) -> Dict[str, Any]:
        """运行覆盖率检查"""
        file_path = fix_info.get("file_path")
        if not file_path:
            return {"error": "No file path provided"}

        try:
            test_file = self._get_corresponding_test_file(file_path)
            if not test_file or not Path(test_file).exists():
                return {"error": "No corresponding test file found", "skipped": True}

            # 运行覆盖率测试
            cmd = [
                "python", "-m", "pytest",
                test_file,
                f"--cov={file_path.rsplit('/', 1)[0].replace('.py', '')}",
                "--cov-report=term-missing",
                "--cov-report=json:coverage_temp.json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            # 解析覆盖率报告
            coverage_data = {}
            if Path("coverage_temp.json").exists():
                try:
                    with open("coverage_temp.json", 'r') as f:
                        coverage_json = json.load(f)
                        coverage_data = coverage_json.get("files", {}).get(file_path, {})
                except Exception as e:
                    logger.warning(f"Failed to parse coverage data: {e}")
                finally:
                    # 清理临时文件
                    try:
                        Path("coverage_temp.json").unlink()
                    except:
                        pass

            return {
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "coverage_data": coverage_data,
                "line_coverage": coverage_data.get("summary", {}).get("percent_covered", 0),
                "raw_output": result.stdout
            }

        except subprocess.TimeoutExpired:
            return {"error": "Coverage validation timed out", "timeout": True}
        except Exception as e:
            return {"error": f"Coverage validation failed: {e}"}

    def _calculate_quality_score(self, validation_results: Dict[str, Any]) -> float:
        """计算综合质量评分"""
        score = 0.0
        max_score = 0.0

        # 测试通过率评分 (0-40分)
        if validation_results.get("test_results"):
            test_results = validation_results["test_results"]
            pass_rate = test_results.get("pass_rate", 0)
            score += min(pass_rate * 40, 40)
            max_score += 40

        # 代码质量评分 (0-30分)
        if validation_results.get("lint_results"):
            lint_results = validation_results["lint_results"]
            if lint_results.get("within_threshold", False):
                score += 30
            else:
                error_count = lint_results.get("error_count", 0)
                score += max(0, 30 - error_count * 2)
            max_score += 30

        # 类型检查评分 (0-20分)
        if validation_results.get("type_check_results"):
            type_results = validation_results["type_check_results"]
            if type_results.get("within_threshold", False):
                score += 20
            else:
                error_count = type_results.get("error_count", 0)
                score += max(0, 20 - error_count * 5)
            max_score += 20

        # 覆盖率评分 (0-10分)
        if validation_results.get("coverage_results"):
            coverage_results = validation_results["coverage_results"]
            line_coverage = coverage_results.get("line_coverage", 0)
            score += min(line_coverage * 0.1, 10)
            max_score += 10

        return score / max_score if max_score > 0 else 0

    def _evaluate_overall_result(self, validation_results: Dict[str, Any]) -> str:
        """评估整体验证结果"""
        quality_score = validation_results.get("quality_score", 0)

        if quality_score >= 0.9:
            return "excellent"
        elif quality_score >= 0.8:
            return "good"
        elif quality_score >= 0.6:
            return "acceptable"
        elif quality_score >= 0.4:
            return "needs_improvement"
        else:
            return "poor"

    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 测试相关建议
        test_results = validation_results.get("test_results")
        if test_results:
            pass_rate = test_results.get("pass_rate", 0)
            if pass_rate < self.config.min_test_pass_rate:
                recommendations.append(f"测试通过率过低 ({pass_rate:.1%} < {self.config.min_test_pass_rate:.1%})，建议检查测试逻辑")

            failed_tests = test_results.get("failed_test_names", [])
            if failed_tests:
                recommendations.append(f"有 {len(failed_tests)} 个测试失败，建议优先修复")

        # 代码质量建议
        lint_results = validation_results.get("lint_results")
        if lint_results and not lint_results.get("within_threshold", True):
            error_count = lint_results.get("error_count", 0)
            recommendations.append(f"代码风格问题较多 ({error_count} 个)，建议运行 black 和 isort 格式化")

        # 类型检查建议
        type_results = validation_results.get("type_check_results")
        if type_results and not type_results.get("within_threshold", True):
            error_count = type_results.get("error_count", 0)
            recommendations.append(f"类型错误较多 ({error_count} 个)，建议添加类型注解")

        # 整体建议
        quality_score = validation_results.get("quality_score", 0)
        if quality_score >= 0.9:
            recommendations.append("修复质量优秀，建议提交")
        elif quality_score >= 0.8:
            recommendations.append("修复质量良好，可考虑提交")
        elif quality_score >= 0.6:
            recommendations.append("修复质量可接受，建议进一步优化")
        else:
            recommendations.append("修复质量较差，建议重新修改")

        return recommendations

    def _generate_improvement_suggestions(self, fix_info: Dict[str, Any], test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成改进建议（用于重试）"""
        failed_tests = test_results.get("failed_test_names", [])

        return {
            "type": "improvement_suggestion",
            "failed_tests": failed_tests,
            "suggestion": f"检测到 {len(failed_tests)} 个测试失败，建议检查修复逻辑并重新生成",
            "auto_improvement_enabled": self.config.enable_auto_improvement,
            "timestamp": datetime.now().isoformat()
        }

    def _save_validation_results(self, results: Dict[str, Any]):
        """保存验证结果"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = self.reports_dir / f"validation_{timestamp}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Validation results saved to {result_file}")

    def batch_validate_fixes(self, fix_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量验证多个修复"""
        start_time = time.time()
        batch_results = []

        for fix_info in fix_list:
            # 检查超时
            if time.time() - start_time > self.config.max_validation_time:
                logger.warning("Batch validation timed out")
                break

            try:
                result = self.validate_fix(fix_info)
                batch_results.append(result)
            except Exception as e:
                logger.error(f"Failed to validate fix for {fix_info.get('file_path', 'unknown')}: {e}")
                batch_results.append({
                    "fix_info": fix_info,
                    "error": str(e),
                    "overall_result": "error"
                })

        execution_time = time.time() - start_time

        return {
            "batch_size": len(fix_list),
            "validated_count": len(batch_results),
            "execution_time": execution_time,
            "results": batch_results,
            "timestamp": datetime.now().isoformat()
        }

    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证历史摘要"""
        try:
            validation_files = list(self.reports_dir.glob("validation_*.json"))
            summary = {
                "total_validations": len(validation_files),
                "excellent_count": 0,
                "good_count": 0,
                "acceptable_count": 0,
                "needs_improvement_count": 0,
                "poor_count": 0,
                "error_count": 0,
                "average_quality_score": 0
            }

            quality_scores = []

            for file_path in validation_files[:50]:  # 只分析最近50个文件
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        result = data.get("overall_result", "unknown")
                        quality_score = data.get("quality_score", 0)

                        if result == "excellent":
                            summary["excellent_count"] += 1
                        elif result == "good":
                            summary["good_count"] += 1
                        elif result == "acceptable":
                            summary["acceptable_count"] += 1
                        elif result == "needs_improvement":
                            summary["needs_improvement_count"] += 1
                        elif result == "poor":
                            summary["poor_count"] += 1
                        elif result == "error":
                            summary["error_count"] += 1

                        quality_scores.append(quality_score)

                except Exception as e:
                    logger.warning(f"Failed to read validation file {file_path}: {e}")

            if quality_scores:
                summary["average_quality_score"] = sum(quality_scores) / len(quality_scores)

            return summary

        except Exception as e:
            logger.error(f"Failed to get validation summary: {e}")
            return {"error": str(e)}


def main():
    """主函数 - 用于测试"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix Validator")
    parser.add_argument("--file", type=str, help="Validate fix for specific file")
    parser.add_argument("--summary", action="store_true", help="Show validation summary")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")

    args = parser.parse_args()

    validator = FixValidator()

    if args.summary:
        summary = validator.get_validation_summary()
        print(json.dumps(summary, indent=2))
        return

    if args.test_mode:
        # 测试模式：使用示例数据
        test_fix = {
            "file_path": "src/utils/example.py",
            "description": "Test fix validation",
            "changes": ["Fixed function xyz"]
        }
        result = validator.validate_fix(test_fix)
        print(json.dumps(result, indent=2))
        return

    if args.file:
        fix_info = {
            "file_path": args.file,
            "description": "Manual validation",
            "timestamp": datetime.now().isoformat()
        }
        result = validator.validate_fix(fix_info)
        print(json.dumps(result, indent=2))
    else:
        print("Please specify a file to validate or use --summary")


if __name__ == "__main__":
    main()