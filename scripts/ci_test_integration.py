#!/usr/bin/env python3
"""
CI/CD测试集成脚本 - M2-P1-05
CI/CD Test Integration Script

功能:
1. 集成测试结果到GitHub Actions
2. 自动生成Pull Request评论
3. 测试质量门禁检查
4. 测试执行时间监控和告警
"""

import json
import subprocess
import sys
import os
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests


class CITestIntegration:
    """CI/CD测试集成管理器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.results_dir = self.project_root / "ci_results"
        self.results_dir.mkdir(exist_ok=True)

        # CI环境变量
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_repository = os.getenv("GITHUB_REPOSITORY", "xupeng211/FootballPrediction")
        self.github_sha = os.getenv("GITHUB_SHA", "unknown")
        self.github_ref = os.getenv("GITHUB_REF", "unknown")
        self.github_event_name = os.getenv("GITHUB_EVENT_NAME", "unknown")
        self.pull_request_number = os.getenv("PR_NUMBER")

    def is_ci_environment(self) -> bool:
        """检查是否在CI环境中"""
        return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))

    def run_ci_tests(self) -> Tuple[bool, Dict[str, Any]]:
        """运行CI测试套件"""
        print("🚀 开始CI测试执行...")

        start_time = time.time()
        results = {
            "timestamp": datetime.now().isoformat(),
            "github_sha": self.github_sha,
            "github_ref": self.github_ref,
            "github_event": self.github_event_name,
            "success": False,
            "execution_time": 0,
            "test_results": {},
            "coverage_results": {},
            "quality_results": {},
            "performance_results": {}
        }

        try:
            # 1. 运行单元测试
            print("📋 执行单元测试...")
            unit_test_result = self._run_command([
                "python", "-m", "pytest",
                "-m", "unit",
                "--junitxml=unit_test_results.xml",
                "--cov=src",
                "--cov-report=xml",
                "--cov-report=term-missing",
                "--tb=short"
            ], timeout=300)

            results["test_results"]["unit"] = {
                "success": unit_test_result.returncode == 0,
                "execution_time": unit_test_result.execution_time,
                "output": unit_test_result.stdout[-1000:] if unit_test_result.stdout else "",
                "error": unit_test_result.stderr[-500:] if unit_test_result.stderr else ""
            }

            if unit_test_result.returncode != 0:
                print("❌ 单元测试失败")
                results["success"] = False
                results["execution_time"] = time.time() - start_time
                return False, results

            # 2. 运行集成测试
            print("🔗 执行集成测试...")
            integration_test_result = self._run_command([
                "python", "-m", "pytest",
                "-m", "integration",
                "--junitxml=integration_test_results.xml",
                "--tb=short"
            ], timeout=600)

            results["test_results"]["integration"] = {
                "success": integration_test_result.returncode == 0,
                "execution_time": integration_test_result.execution_time,
                "output": integration_test_result.stdout[-1000:] if integration_test_result.stdout else "",
                "error": integration_test_result.stderr[-500:] if integration_test_result.stderr else ""
            }

            # 3. 覆盖率分析
            print("📊 分析覆盖率...")
            coverage_result = self._analyze_coverage()
            results["coverage_results"] = coverage_result

            # 4. 代码质量检查
            print("🛡️ 执行代码质量检查...")
            quality_result = self._run_quality_checks()
            results["quality_results"] = quality_result

            # 5. 性能测试
            print("⚡ 执行性能测试...")
            performance_result = self._run_performance_tests()
            results["performance_results"] = performance_result

            # 计算总执行时间
            results["execution_time"] = time.time() - start_time

            # 判断整体成功状态
            all_tests_passed = (
                results["test_results"]["unit"]["success"] and
                results["test_results"]["integration"]["success"]
            )

            results["success"] = all_tests_passed

            if all_tests_passed:
                print("✅ 所有CI测试通过")
            else:
                print("❌ 部分CI测试失败")

            return all_tests_passed, results

        except Exception as e:
            print(f"❌ CI测试执行失败: {e}")
            results["execution_time"] = time.time() - start_time
            results["error"] = str(e)
            return False, results

    def _run_command(self, cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """运行命令并返回结果"""
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            result.execution_time = time.time() - start_time
            return result
        except subprocess.TimeoutExpired:
            print(f"❌ 命令执行超时: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 1, "", "Timeout")

    def _analyze_coverage(self) -> Dict[str, Any]:
        """分析覆盖率数据"""
        coverage_file = self.project_root / "coverage.xml"
        if not coverage_file.exists():
            return {"error": "coverage.xml文件不存在"}

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(coverage_file)
            root = tree.getroot()

            # 获取总体覆盖率
            total_coverage = 0.0
            for coverage in root.findall(".//coverage"):
                line_rate = float(coverage.get("line-rate", 0))
                total_coverage = max(total_coverage, line_rate * 100)

            # 获取M2目标状态
            m2_target_met = total_coverage >= 50.0

            return {
                "total_coverage": round(total_coverage, 2),
                "m2_target_met": m2_target_met,
                "target": 50.0,
                "gap": max(0, 50.0 - total_coverage),
                "file_exists": True
            }

        except Exception as e:
            return {"error": f"解析覆盖率失败: {e}"}

    def _run_quality_checks(self) -> Dict[str, Any]:
        """运行代码质量检查"""
        results = {}

        # Ruff检查
        try:
            ruff_result = self._run_command(["ruff", "check", "src/", "tests/"], timeout=120)
            results["ruff"] = {
                "success": ruff_result.returncode == 0,
                "issues": ruff_result.stdout.count('\n') if ruff_result.stdout else 0,
                "execution_time": ruff_result.execution_time
            }
        except Exception as e:
            results["ruff"] = {"error": str(e)}

        # MyPy检查
        try:
            mypy_result = self._run_command(["mypy", "src/"], timeout=180)
            results["mypy"] = {
                "success": mypy_result.returncode == 0,
                "issues": mypy_result.stdout.count('\n') if mypy_result.stdout else 0,
                "execution_time": mypy_result.execution_time
            }
        except Exception as e:
            results["mypy"] = {"error": str(e)}

        # bandit安全检查
        try:
            bandit_result = self._run_command(["bandit", "-r", "src/"], timeout=120)
            results["bandit"] = {
                "success": bandit_result.returncode == 0,
                "issues": bandit_result.stdout.count('\n') if bandit_result.stdout else 0,
                "execution_time": bandit_result.execution_time
            }
        except Exception as e:
            results["bandit"] = {"error": str(e)}

        return results

    def _run_performance_tests(self) -> Dict[str, Any]:
        """运行性能测试"""
        results = {}

        # 测试导入性能
        try:
            start_time = time.time()
            import_result = self._run_command([
                "python", "-c", "import sys; sys.path.insert(0, 'src'); import core.di, core.config_di"
            ], timeout=30)
            import_time = time.time() - start_time

            results["import_performance"] = {
                "success": import_result.returncode == 0,
                "time": import_time
            }
        except Exception as e:
            results["import_performance"] = {"error": str(e)}

        # 测试测试套件启动性能
        try:
            start_time = time.time()
            pytest_collect = self._run_command([
                "python", "-m", "pytest", "--collect-only", "-q", "tests/"
            ], timeout=60)
            collect_time = time.time() - start_time

            results["test_collection"] = {
                "success": pytest_collect.returncode == 0,
                "time": collect_time
            }
        except Exception as e:
            results["test_collection"] = {"error": str(e)}

        return results

    def generate_ci_report(self, results: Dict[str, Any]) -> str:
        """生成CI报告"""
        report_lines = [
            "# 🚀 CI/CD 测试报告",
            f"",
            f"**时间**: {results['timestamp']}",
            f"**提交**: {results['github_sha'][:8]}",
            f"**分支**: {results['github_ref']}",
            f"**事件**: {results['github_event']}",
            f"",
            f"## 📊 测试结果",
            f""
        ]

        # 测试结果
        unit_success = results["test_results"].get("unit", {}).get("success", False)
        integration_success = results["test_results"].get("integration", {}).get("success", False)

        report_lines.extend([
            f"| 测试类型 | 状态 | 耗时 |",
            f"|----------|------|------|",
            f"| 单元测试 | {'✅ 通过' if unit_success else '❌ 失败'} | {results['test_results'].get('unit', {}).get('execution_time', 0):.2f}s |",
            f"| 集成测试 | {'✅ 通过' if integration_success else '❌ 失败'} | {results['test_results'].get('integration', {}).get('execution_time', 0):.2f}s |",
            f""
        ])

        # 覆盖率结果
        coverage = results.get("coverage_results", {})
        if "error" not in coverage:
            coverage_status = "✅ 达标" if coverage.get("m2_target_met", False) else "❌ 未达标"
            report_lines.extend([
                f"## 📈 覆盖率分析",
                f"",
                f"- **总体覆盖率**: {coverage.get('total_coverage', 0):.1f}%",
                f"- **M2目标**: {coverage.get('target', 50):.1f}%",
                f"- **状态**: {coverage_status}",
                f"- **差距**: {coverage.get('gap', 0):.1f}%",
                f""
            ])

        # 质量检查结果
        quality = results.get("quality_results", {})
        if quality:
            report_lines.extend([
                f"## 🛡️ 代码质量",
                f""
            ])

            for tool, result in quality.items():
                if "error" not in result:
                    status = "✅ 通过" if result.get("success", False) else "❌ 失败"
                    issues = result.get("issues", 0)
                    report_lines.append(f"- **{tool}**: {status} ({issues} 个问题)")

            report_lines.append("")

        # 性能结果
        performance = results.get("performance_results", {})
        if performance:
            report_lines.extend([
                f"## ⚡ 性能指标",
                f""
            ])

            for metric, result in performance.items():
                if "error" not in result:
                    time_taken = result.get("time", 0)
                    status = "✅ 正常" if time_taken < 5.0 else "⚠️ 较慢"
                    report_lines.append(f"- **{metric}**: {status} ({time_taken:.2f}s)")

            report_lines.append("")

        # 总体状态
        overall_status = "✅ 通过" if results.get("success", False) else "❌ 失败"
        total_time = results.get("execution_time", 0)

        report_lines.extend([
            f"## 🎯 总体状态",
            f"",
            f"- **状态**: {overall_status}",
            f"- **总耗时**: {total_time:.2f}s",
            f""
        ])

        return "\n".join(report_lines)

    def save_ci_results(self, results: Dict[str, Any]):
        """保存CI结果"""
        results_file = self.results_dir / f"ci_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"📊 CI结果已保存: {results_file}")
        return results_file

    def create_pr_comment(self, results: Dict[str, Any]) -> bool:
        """创建Pull Request评论"""
        if not self.github_token or not self.pull_request_number:
            print("⚠️ 缺少GitHub Token或PR编号，跳过PR评论创建")
            return False

        try:
            # 生成评论内容
            comment_body = self.generate_ci_report(results)

            # GitHub API请求
            url = f"https://api.github.com/repos/{self.github_repository}/issues/{self.pull_request_number}/comments"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {"body": comment_body}

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 201:
                print("✅ PR评论创建成功")
                return True
            else:
                print(f"❌ PR评论创建失败: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ 创建PR评论失败: {e}")
            return False

    def check_quality_gates(self, results: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """检查质量门禁"""
        gates_passed = True
        messages = []

        # 测试通过门禁
        unit_success = results["test_results"].get("unit", {}).get("success", False)
        integration_success = results["test_results"].get("integration", {}).get("success", False)

        if not unit_success:
            gates_passed = False
            messages.append("❌ 单元测试失败")

        if not integration_success:
            gates_passed = False
            messages.append("❌ 集成测试失败")

        # 覆盖率门禁
        coverage = results.get("coverage_results", {})
        if "error" not in coverage and not coverage.get("m2_target_met", False):
            gates_passed = False
            messages.append(f"❌ 覆盖率未达标: {coverage.get('total_coverage', 0):.1f}% < 50%")

        # 代码质量门禁
        quality = results.get("quality_results", {})
        for tool, result in quality.items():
            if "error" not in result and not result.get("success", False):
                gates_passed = False
                messages.append(f"❌ {tool}质量检查失败")

        # 性能门禁
        performance = results.get("performance_results", {})
        for metric, result in performance.items():
            if "error" not in result and result.get("time", 0) > 10.0:
                messages.append(f"⚠️ {metric}性能较慢: {result.get('time', 0):.2f}s")

        return gates_passed, messages

    def run_ci_pipeline(self) -> int:
        """运行完整的CI流水线"""
        print("🚀 开始CI/CD流水线...")

        if not self.is_ci_environment():
            print("⚠️ 不在CI环境中，将以开发模式运行")

        # 1. 运行测试
        success, results = self.run_ci_tests()

        # 2. 保存结果
        self.save_ci_results(results)

        # 3. 生成报告
        report_content = self.generate_ci_report(results)
        report_file = self.results_dir / "ci_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"📝 CI报告已生成: {report_file}")

        # 4. 检查质量门禁
        gates_passed, gate_messages = self.check_quality_gates(results)

        if not gates_passed:
            print("⚠️ 质量门禁检查失败:")
            for msg in gate_messages:
                print(f"  {msg}")

        # 5. 创建PR评论（如果在PR环境中）
        if self.github_event_name == "pull_request":
            self.create_pr_comment(results)

        # 6. 输出摘要
        print("\n" + "="*60)
        print("🚀 CI/CD流水线完成")
        print("="*60)
        print(f"📅 时间: {results['timestamp'][:19]}")
        print(f"🎯 总体状态: {'✅ 通过' if success else '❌ 失败'}")
        print(f"⏱️ 总耗时: {results.get('execution_time', 0):.2f}s")
        print(f"📊 覆盖率: {results.get('coverage_results', {}).get('total_coverage', 0):.1f}%")
        print("="*60)

        return 0 if (success and gates_passed) else 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CI/CD测试集成")
    parser.add_argument("--test", action="store_true", help="测试模式")
    parser.add_argument("--project-root", help="项目根目录")
    parser.add_argument("--results-dir", help="结果输出目录")

    args = parser.parse_args()

    if args.test:
        print("🧪 测试模式：验证CI集成功能")

        # 检查环境
        project_root = Path(args.project_root) if args.project_root else Path.cwd()
        ci = CITestIntegration(project_root)

        print(f"项目根目录: {project_root}")
        print(f"CI环境: {ci.is_ci_environment()}")
        print(f"GitHub Token: {'已设置' if ci.github_token else '未设置'}")
        print(f"GitHub仓库: {ci.github_repository}")
        print("✅ CI集成验证完成")
        return 0

    # 创建CI集成器
    project_root = Path(args.project_root) if args.project_root else None
    ci = CITestIntegration(project_root)

    # 设置自定义结果目录
    if args.results_dir:
        ci.results_dir = Path(args.results_dir)
        ci.results_dir.mkdir(exist_ok=True)

    # 运行CI流水线
    return ci.run_ci_pipeline()


if __name__ == "__main__":
    sys.exit(main())