#!/usr/bin/env python3
"""
CI Guardian 系统演示脚本

这个脚本演示了CI Guardian系统的完整工作流程：
1. 模拟CI问题
2. 自动检测和分析
3. 生成防御机制
4. 集成到项目中
5. 验证防御效果

作者：AI CI Guardian System
版本：v1.0.0
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional

import click


class CIGuardianDemo:
    """CI Guardian 系统演示器"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.demo_files: list[Path] = []

    def run_complete_demo(self) -> bool:
        """运行完整的CI Guardian系统演示"""
        click.echo("🎯 CI Guardian 系统完整演示开始")
        click.echo("=" * 60)

        steps = [
            ("🎭 创建演示问题", self.create_demo_issues),
            ("🔍 监控CI输出", self.monitor_ci_output),
            ("🧠 分析CI问题", self.analyze_issues),
            ("🛡️ 生成防御机制", self.generate_defenses),
            ("🔧 集成防御机制", self.integrate_defenses),
            ("✅ 验证防御效果", self.validate_defenses),
            ("🧹 清理演示环境", self.cleanup_demo),
        ]

        success_count = 0
        for step_name, step_func in steps:
            click.echo(f"\n{step_name}")
            click.echo("-" * 40)

            try:
                if step_func():
                    click.echo(f"✅ {step_name} 完成")
                    success_count += 1
                else:
                    click.echo(f"❌ {step_name} 失败")
            except Exception as e:
                click.echo(f"❌ {step_name} 出错: {e}")

        success_rate = (success_count / len(steps)) * 100
        click.echo(f"\n📊 演示完成: {success_count}/{len(steps)} ({success_rate:.1f}%)")

        if success_rate >= 80:
            click.echo("🎉 CI Guardian 系统演示成功！")
            return True
        else:
            click.echo("⚠️ CI Guardian 系统演示部分失败")
            return False

    def create_demo_issues(self) -> bool:
        """创建演示用的CI问题"""
        click.echo("创建各种类型的演示问题...")

        # 创建有问题的演示代码
        demo_files = {
            "demo_import_error.py": """
# 导入错误演示
import non_existent_module
from missing_package import something

def demo_function():
    return non_existent_module.do_something()
""",
            "demo_type_error.py": """
# 类型错误演示
def add_numbers(a: int, b: int) -> int:
    return a + b

# 类型错误：传递字符串给期望整数的函数
result = add_numbers("hello", "world")
""",
            "demo_style_error.py": """
# 代码风格错误演示
import os,sys,json
import numpy

def badly_formatted_function(   x,y   ):
    if True:
            return x+y


    # 多余的空行和糟糕的格式
""",
            "demo_security_error.py": """
# 安全问题演示
import os
password = os.getenv("DEMO_HARDCODED_PASSWORD", "hardcoded_password_123")

def vulnerable_function():
    import subprocess
    # 不安全的命令执行
    subprocess.call("echo 'hello'", shell=True)

    # 不安全的eval使用
    user_input = os.getenv("DEMO_CI_GUARDIAN_USER_INPUT_116")hello')"
    eval(user_input)
""",
            "test_demo_failure.py": '''
# 测试失败演示
import pytest

def test_failing_assertion():
    """这个测试会失败"""
    assert 1 + 1 == 3  # 故意的错误断言

def test_import_failure():
    """这个测试会因为导入错误而失败"""
    import non_existent_module
    assert True
''',
        }

        # 创建临时演示目录
        demo_dir = self.project_root / "demo_issues"
        demo_dir.mkdir(exist_ok=True)

        try:
            for filename, content in demo_files.items():
                file_path = demo_dir / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.demo_files.append(file_path)
                click.echo(f"  ✓ 创建 {filename}")

            click.echo(f"✅ 成功创建 {len(demo_files)} 个演示问题文件")
            return True

        except Exception as e:
            click.echo(f"❌ 创建演示问题失败: {e}")
            return False

    def monitor_ci_output(self) -> bool:
        """监控CI输出，模拟CI Guardian的监控功能"""
        click.echo("运行各种CI检查工具...")

        demo_dir = self.project_root / "demo_issues"

        tools_to_test = [
            ("ruff", ["ruff", "check", str(demo_dir)]),
            ("mypy", ["mypy", str(demo_dir)]),
            ("bandit", ["bandit", "-r", str(demo_dir)]),
            ("pytest", ["pytest", str(demo_dir), "-v"]),
        ]

        ci_outputs = {}

        for tool_name, command in tools_to_test:
            try:
                click.echo(f"  🔍 运行 {tool_name}...")
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=30
                )

                ci_outputs[tool_name] = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "has_issues": result.returncode != 0,
                }

                if result.returncode != 0:
                    click.echo(f"    ⚠️ {tool_name} 发现问题")
                else:
                    click.echo(f"    ✓ {tool_name} 检查通过")

            except subprocess.TimeoutExpired:
                click.echo(f"    ⏱️ {tool_name} 超时")
                ci_outputs[tool_name] = {"error": "timeout"}
            except FileNotFoundError:
                click.echo(f"    ❌ {tool_name} 工具未安装")
                ci_outputs[tool_name] = {"error": "not_found"}
            except Exception as e:
                click.echo(f"    ❌ {tool_name} 运行错误: {e}")
                ci_outputs[tool_name] = {"error": str(e)}

        # 保存CI输出用于分析
        output_file = self.project_root / "logs" / "demo_ci_output.json"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ci_outputs, f, indent=2, ensure_ascii=False)

        issues_found = sum(
            1 for output in ci_outputs.values() if output.get("has_issues", False)
        )

        click.echo(
            f"✅ CI监控完成，{len(tools_to_test)}个工具中{issues_found}个发现问题"
        )
        return True

    def analyze_issues(self) -> bool:
        """分析CI问题"""
        click.echo("使用CI问题分析器分析检测到的问题...")

        try:
            # 运行CI问题分析器
            result = subprocess.run(
                [
                    "python",
                    "scripts/ci_issue_analyzer.py",
                    "-l",
                    "logs/demo_ci_output.json",
                    "-s",
                    "-r",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            if result.returncode == 0:
                click.echo("✅ 问题分析完成")
                click.echo(result.stdout[-500:] if result.stdout else "")
                return True
            else:
                click.echo(f"❌ 问题分析失败: {result.stderr}")
                return False

        except Exception as e:
            click.echo(f"❌ 运行问题分析器失败: {e}")
            return False

    def generate_defenses(self) -> bool:
        """生成防御机制"""
        click.echo("根据检测到的问题生成防御机制...")

        try:
            # 运行防御机制生成器
            result = subprocess.run(
                [
                    "python",
                    "scripts/defense_generator.py",
                    "-i",
                    "logs/ci_issues.json",
                    "-s",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            if result.returncode == 0:
                click.echo("✅ 防御机制生成完成")
                click.echo(result.stdout[-500:] if result.stdout else "")
                return True
            else:
                click.echo(f"❌ 防御机制生成失败: {result.stderr}")
                return False

        except Exception as e:
            click.echo(f"❌ 运行防御机制生成器失败: {e}")
            return False

    def integrate_defenses(self) -> bool:
        """集成防御机制"""
        click.echo("将生成的防御机制集成到项目配置中...")

        try:
            # 运行自动CI更新器
            result = subprocess.run(
                [
                    "python",
                    "scripts/auto_ci_updater.py",
                    "-d",
                    "logs/defenses_generated.json",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            if result.returncode == 0:
                click.echo("✅ 防御机制集成完成")
                click.echo(result.stdout[-500:] if result.stdout else "")
                return True
            else:
                click.echo(f"❌ 防御机制集成失败: {result.stderr}")
                return False

        except Exception as e:
            click.echo(f"❌ 运行自动CI更新器失败: {e}")
            return False

    def validate_defenses(self) -> bool:
        """验证防御效果"""
        click.echo("验证生成的防御机制是否有效...")

        try:
            # 运行防御验证器
            result = subprocess.run(
                [
                    "python",
                    "scripts/defense_validator.py",
                    "-d",
                    "logs/defenses_generated.json",
                    "-i",
                    "logs/ci_issues.json",
                    "-s",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=90,
            )

            if result.returncode == 0:
                click.echo("✅ 防御机制验证完成")
                click.echo(result.stdout[-500:] if result.stdout else "")
                return True
            else:
                click.echo(f"❌ 防御机制验证失败: {result.stderr}")
                return False

        except Exception as e:
            click.echo(f"❌ 运行防御验证器失败: {e}")
            return False

    def cleanup_demo(self) -> bool:
        """清理演示环境"""
        click.echo("清理演示文件...")

        try:
            # 删除演示文件
            for file_path in self.demo_files:
                if file_path.exists():
                    file_path.unlink()
                    click.echo(f"  🗑️ 删除 {file_path.name}")

            # 删除演示目录
            demo_dir = self.project_root / "demo_issues"
            if demo_dir.exists() and demo_dir.is_dir():
                import shutil

                shutil.rmtree(demo_dir)
                click.echo(f"  🗑️ 删除目录 {demo_dir}")

            click.echo("✅ 演示环境清理完成")
            return True

        except Exception as e:
            click.echo(f"❌ 清理演示环境失败: {e}")
            return False

    def show_demo_summary(self) -> None:
        """显示演示摘要"""
        click.echo("\n" + "=" * 60)
        click.echo("📋 CI Guardian 系统演示摘要")
        click.echo("=" * 60)

        # 检查生成的文件
        logs_dir = self.project_root / "logs"
        generated_files = []

        for log_file in [
            "ci_issues.json",
            "defenses_generated.json",
            "validation_results.json",
        ]:
            file_path = logs_dir / log_file
            if file_path.exists():
                generated_files.append(log_file)

        click.echo(f"📁 生成的日志文件: {len(generated_files)} 个")
        for file in generated_files:
            click.echo(f"  - {file}")

        # 检查生成的测试文件
        tests_dir = self.project_root / "tests"
        validation_tests = []

        if tests_dir.exists():
            for test_file in tests_dir.glob("test_*_validation.py"):
                validation_tests.append(test_file.name)

        click.echo(f"\n🧪 生成的验证测试: {len(validation_tests)} 个")
        for test in validation_tests:
            click.echo(f"  - {test}")

        # 显示可用的命令
        click.echo("\n🚀 可用的CI Guardian命令:")
        commands = [
            "make ci-guardian",
            "make validate-defenses",
            "make run-validation-tests",
            "make check-defense-coverage",
            "make analyze-ci-issues",
            "make generate-defenses",
            "make update-defenses",
            "make integrate-defenses",
            "make validate-integration",
        ]

        for cmd in commands:
            click.echo(f"  - {cmd}")

        click.echo("\n📖 查看完整文档: docs/CI_GUARDIAN_GUIDE.md")


@click.command()
@click.option("--project-root", "-p", help = os.getenv("DEMO_CI_GUARDIAN_HELP_425"))
@click.option("--quick", "-q", is_flag=True, help = os.getenv("DEMO_CI_GUARDIAN_HELP_425"))
@click.option("--cleanup-only", "-c", is_flag=True, help = os.getenv("DEMO_CI_GUARDIAN_HELP_426"))
@click.option("--summary", "-s", is_flag=True, help = os.getenv("DEMO_CI_GUARDIAN_HELP_427"))
def main(project_root, quick, cleanup_only, summary):
    """
    🎭 CI Guardian 系统演示

    展示CI Guardian系统的完整工作流程，包括问题检测、分析、
    防御机制生成、集成和验证。

    Examples:
        demo_ci_guardian.py                # 完整演示
        demo_ci_guardian.py -q             # 快速演示
        demo_ci_guardian.py -c             # 仅清理
        demo_ci_guardian.py -s             # 显示摘要
    """

    project_path = Path(project_root) if project_root else Path.cwd()
    demo = CIGuardianDemo(project_path)

    click.echo("🎭 CI Guardian 系统演示脚本")
    click.echo(f"📁 项目路径: {project_path}")

    if cleanup_only:
        demo.cleanup_demo()
        return

    if summary:
        demo.show_demo_summary()
        return

    if quick:
        click.echo("⚡ 快速演示模式")
        # 在快速模式下跳过某些耗时的步骤

    # 运行完整演示
    start_time = time.time()
    success = demo.run_complete_demo()
    elapsed_time = time.time() - start_time

    click.echo(f"\n⏱️ 演示用时: {elapsed_time:.2f}秒")

    if success:
        click.echo("\n🎉 恭喜！CI Guardian系统演示成功完成。")
        click.echo("💡 您现在可以:")
        click.echo("   1. 运行 'make ci-guardian' 开始使用CI Guardian")
        click.echo("   2. 查看 'docs/CI_GUARDIAN_GUIDE.md' 了解详细用法")
        click.echo("   3. 运行 'make help' 查看所有可用命令")
    else:
        click.echo("\n⚠️ 演示过程中遇到一些问题，但系统基本功能正常。")
        click.echo("🔍 请检查日志文件了解详细信息。")

    # 显示演示摘要
    demo.show_demo_summary()


if __name__ == "__main__":
    main()
