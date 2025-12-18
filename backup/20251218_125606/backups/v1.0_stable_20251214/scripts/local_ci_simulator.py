#!/usr/bin/env python3
"""
本地CI模拟器
Local CI Simulator

通过模拟GitHub Actions CI环境来本地检测和修复问题
Simulates GitHub Actions CI environment locally to detect and fix issues

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-12-12
"""

import os
import sys
import subprocess
import json
import time
import signal
from pathlib import Path
from typing import Dict, List, Tuple, Any

class LocalCISimulator:
    """本地CI环境模拟器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.ci_env_vars = {
            'FOOTBALL_PREDICTION_ML_MODE': 'mock',
            'SKIP_ML_MODEL_LOADING': 'true',
            'INFERENCE_SERVICE_MOCK': 'true',
            'PYTHONPATH': str(self.project_root),
            'CI': 'true',
            'GITHUB_ACTIONS': 'true'
        }
        self.setup_commands = []
        self.test_commands = []
        self.lint_commands = []

    def setup_ci_environment(self):
        """设置CI环境变量"""
        print("🔧 设置CI环境变量...")
        for key, value in self.ci_env_vars.items():
            os.environ[key] = value
            print(f"   {key}={value}")

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """检查CI依赖是否满足"""
        print("📦 检查CI依赖...")

        required_packages = [
            'pytest', 'pytest-asyncio', 'pytest-cov', 'pytest-mock',
            'ruff', 'black', 'mypy', 'bandit',
            'fastapi', 'sqlalchemy', 'pydantic',
            'prometheus-fastapi-instrumentator', 'loguru'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ❌ {package}")
                missing_packages.append(package)

        return len(missing_packages) == 0, missing_packages

    def run_command(self, cmd: str, timeout: int = 300) -> Tuple[int, str, str]:
        """运行命令并返回结果"""
        print(f"🏃 运行命令: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            print(f"   ⏰ 命令超时 ({timeout}秒)")
            return -1, "", "Command timeout"
        except Exception as e:
            print(f"   ❌ 命令执行异常: {e}")
            return -1, "", str(e)

    def lint_check(self) -> Dict[str, Any]:
        """代码质量检查"""
        print("🔍 代码质量检查...")
        results = {
            'ruff': self.run_command("ruff check src/ --output-format=concise", 60),
            'ruff_format': self.run_command("ruff format --check src/", 30),
            'mypy': self.run_command("mypy src/ --ignore-missing-imports --exclude 'src/api/data/models/data_quality.py'", 60),
            'bandit': self.run_command("bandit -r src/ -f json", 30)
        }
        return results

    def test_execution(self) -> Dict[str, Any]:
        """测试执行"""
        print("🧪 执行测试...")

        test_configs = [
            # 快速测试 - 仅核心模块
            ("快速测试", "pytest tests/unit/test_core_di_extended.py -v --tb=short", 60),
            # 收集测试 - 不实际运行
            ("收集测试", "pytest --collect-only tests/unit/", 120),
            # 单个文件测试
            ("单个文件", "python -c 'import src.main; print(\"Main模块导入成功\")'", 30),
        ]

        results = {}
        for test_name, test_cmd, timeout in test_configs:
            print(f"   执行{test_name}: {test_cmd}")
            results[test_name] = self.run_command(test_cmd, timeout)

        return results

    def application_startup_test(self) -> Dict[str, Any]:
        """应用启动测试"""
        print("🚀 应用启动测试...")

        startup_tests = [
            ("主应用导入", "python -c 'import src.main; print(\"✅ 主应用导入成功\")'", 30),
            ("配置加载", "python -c 'from src.config.config_manager import ConfigManager; print(\"✅ 配置加载成功\")'", 30),
            ("日志系统", "python -c 'from src.core.logging_config import LoggingConfig; print(\"✅ 日志系统加载成功\")'", 30),
            ("监控模块", "python -c 'from src.monitoring.prometheus_instrumentator import create_instrumentator; print(\"✅ 监控模块加载成功\")'", 30),
        ]

        results = {}
        for test_name, test_cmd, timeout in startup_tests:
            results[test_name] = self.run_command(test_cmd, timeout)

        return results

    def analyze_failure(self, results: Dict[str, Any]) -> List[str]:
        """分析失败原因并提供建议"""
        issues = []
        suggestions = []

        # 分析启动测试结果
        startup_results = results.get('startup', {})
        for test_name, (returncode, stdout, stderr) in startup_results.items():
            if returncode != 0:
                issues.append(f"❌ {test_name}失败")

                # 基于错误信息提供具体建议
                if "prometheus" in stderr.lower():
                    suggestions.append("🔧 修复Prometheus相关错误: 检查prometheus-fastapi-instrumentator版本兼容性")
                if "loguru" in stderr.lower() or "color" in stderr.lower():
                    suggestions.append("🔧 修复Loguru颜色标签配置: 检查日志格式设置")
                if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
                    suggestions.append("📦 修复导入错误: 检查缺失的依赖和模块路径")
                if "SyntaxError" in stderr:
                    suggestions.append("🔤 修复语法错误: 检查代码语法问题")

        # 分析代码质量检查结果
        lint_results = results.get('lint', {})
        for tool_name, (returncode, stdout, stderr) in lint_results.items():
            if returncode != 0:
                issues.append(f"❌ {tool_name}检查失败")
                if tool_name == 'ruff':
                    error_count = stdout.count('error') + stderr.count('error')
                    suggestions.append(f"🔧 修复Ruff发现的 {error_count} 个错误")

        # 分析测试结果
        test_results = results.get('test', {})
        for test_name, (returncode, stdout, stderr) in test_results.items():
            if returncode != 0:
                issues.append(f"❌ {test_name}失败")
                if "FAILED" in stdout or "FAILED" in stderr:
                    failed_tests = stdout.count("FAILED") + stderr.count("FAILED")
                    suggestions.append(f"🧪 修复 {failed_tests} 个失败的测试")

        if not issues:
            issues.append("✅ 所有检查通过")

        return issues, suggestions

    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成详细报告"""
        report = []
        report.append("="*80)
        report.append("🏥 本地CI模拟诊断报告")
        report.append("="*80)
        report.append(f"📅 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📁 项目根目录: {self.project_root}")
        report.append("")

        # 环境变量
        report.append("🔧 CI环境变量:")
        for key, value in self.ci_env_vars.items():
            report.append(f"   {key}={value}")
        report.append("")

        # 依赖检查
        deps_ok, missing = self.check_dependencies()
        if deps_ok:
            report.append("📦 ✅ 所有依赖满足")
        else:
            report.append(f"📦 ❌ 缺失依赖: {', '.join(missing)}")
        report.append("")

        # 启动测试结果
        report.append("🚀 应用启动测试:")
        startup_results = results.get('startup', {})
        for test_name, (returncode, stdout, stderr) in startup_results.items():
            status = "✅" if returncode == 0 else "❌"
            report.append(f"   {status} {test_name}")
            if returncode != 0 and stderr:
                # 显示关键错误信息
                error_lines = stderr.strip().split('\n')[:3]
                for line in error_lines:
                    if line.strip():
                        report.append(f"      💥 {line.strip()}")
        report.append("")

        # 代码质量检查结果
        report.append("🔍 代码质量检查:")
        lint_results = results.get('lint', {})
        for tool_name, (returncode, stdout, stderr) in lint_results.items():
            status = "✅" if returncode == 0 else "❌"
            report.append(f"   {status} {tool_name}")
            if returncode != 0:
                # 显示错误数量
                error_count = stdout.count('error') + stderr.count('error')
                warning_count = stdout.count('warning') + stderr.count('warning')
                if error_count > 0:
                    report.append(f"      🔴 {error_count} 个错误")
                if warning_count > 0:
                    report.append(f"      🟡 {warning_count} 个警告")
        report.append("")

        # 分析和建议
        issues, suggestions = self.analyze_failure(results)

        report.append("🎯 问题总结:")
        for issue in issues:
            report.append(f"   {issue}")
        report.append("")

        if suggestions:
            report.append("💡 修复建议:")
            for suggestion in suggestions:
                report.append(f"   {suggestion}")
            report.append("")

        report.append("="*80)

        return '\n'.join(report)

    def run_full_ci_simulation(self) -> bool:
        """运行完整的CI模拟"""
        print("🚀 开始本地CI模拟...")
        print("="*60)

        # 设置环境
        self.setup_ci_environment()

        # 检查依赖
        deps_ok, missing = self.check_dependencies()
        if not deps_ok:
            print(f"❌ 缺失依赖: {missing}")
            return False

        results = {}

        # 1. 应用启动测试
        results['startup'] = self.application_startup_test()

        # 2. 代码质量检查
        results['lint'] = self.lint_check()

        # 3. 测试执行
        results['test'] = self.test_execution()

        # 生成报告
        report = self.generate_report(results)
        print(report)

        # 保存报告
        report_file = self.project_root / "ci_simulation_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 详细报告已保存到: {report_file}")

        # 返回是否成功
        issues, _ = self.analyze_failure(results)
        all_passed = all(issue.startswith("✅") for issue in issues if issue.startswith("✅") or issue.startswith("❌"))

        return all_passed and len([i for i in issues if i.startswith("❌")]) == 0


def main():
    """主函数"""
    simulator = LocalCISimulator()

    try:
        success = simulator.run_full_ci_simulation()
        if success:
            print("🎉 CI模拟成功 - 所有检查通过!")
            sys.exit(0)
        else:
            print("❌ CI模拟失败 - 发现问题需要修复")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ CI模拟异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()