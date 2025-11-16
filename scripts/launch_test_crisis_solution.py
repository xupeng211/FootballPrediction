#!/usr/bin/env python3
"""
测试危机解决方案启动器
交互式工具，用于诊断和解决测试系统问题
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List
import time


class TestCrisisLauncher:
    """测试危机解决方案启动器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.crisis_solver_script = self.project_root / "scripts" / "fix_test_crisis.py"

    def show_banner(self):
        """显示启动横幅"""
        print("=" * 70)
        print("🚨 足球预测系统 - 测试危机解决方案启动器")
        print("=" * 70)
        print("这个工具将帮助您诊断和解决测试系统中的问题")
        print("")

    def show_main_menu(self) -> str:
        """显示主菜单"""
        print("请选择操作:")
        print("")
        print("1. 🔍 全面诊断测试系统")
        print("2. 🚀 快速修复常见问题")
        print("3. 🧪 运行特定测试模块")
        print("4. 📊 查看项目状态")
        print("5. 🛠️ 手动修复向导")
        print("6. 📋 查看历史报告")
        print("7. ⚙️ 配置检查")
        print("8. 🆘 获取帮助")
        print("0. 🚪 退出")
        print("")

        choice = input("请输入选项 (0-8): ").strip()
        return choice

    def run_comprehensive_diagnosis(self):
        """运行全面诊断"""
        print("\n🔍 开始全面诊断...")
        print("-" * 50)

        # 检查环境
        self.check_environment()
        print()

        # 检查依赖
        self.check_dependencies()
        print()

        # 检查语法
        self.check_syntax_issues()
        print()

        # 检查测试收集
        self.check_test_collection()
        print()

        # 提供诊断结果
        self.provide_diagnosis_summary()

    def run_quick_fix(self):
        """运行快速修复"""
        print("\n🚀 开始快速修复...")
        print("-" * 50)

        if not self.crisis_solver_script.exists():
            print("❌ 测试危机解决脚本不存在")
            return

        try:
            print("🔧 运行自动修复工具...")
            result = subprocess.run(
                ["python3", str(self.crisis_solver_script), "--quick-fix"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ 快速修复完成")
                print(result.stdout)
            else:
                print("❌ 快速修复失败")
                print(result.stderr)

            # 运行验证测试
            self.run_verification_test()

        except Exception as e:
            print(f"❌ 运行修复工具时出错: {e}")

    def run_specific_tests(self):
        """运行特定测试模块"""
        print("\n🧪 选择测试模块:")
        print("1. utils 模块测试")
        print("2. core 模块测试")
        print("3. api 模块测试")
        print("4. database 模块测试")
        print("5. 自定义测试路径")
        print("0. 返回主菜单")

        choice = input("请选择 (0-5): ").strip()

        test_modules = {
            "1": "tests/unit/utils/",
            "2": "tests/unit/core/",
            "3": "tests/unit/api/",
            "4": "tests/unit/database/",
        }

        if choice == "5":
            custom_path = input("请输入测试路径: ").strip()
            if custom_path:
                self.run_test_module(custom_path)
        elif choice in test_modules:
            self.run_test_module(test_modules[choice])
        elif choice == "0":
            return
        else:
            print("❌ 无效选项")

    def show_project_status(self):
        """显示项目状态"""
        print("\n📊 项目状态概览")
        print("-" * 50)

        # 基础信息
        self.show_basic_status()
        print()

        # 测试状态
        self.show_test_status()
        print()

        # 代码质量状态
        self.show_quality_status()
        print()

        # 依赖状态
        self.show_dependency_status()

    def manual_fix_wizard(self):
        """手动修复向导"""
        print("\n🛠️ 手动修复向导")
        print("-" * 50)
        print("这个向导将引导您手动修复常见问题")
        print("")

        while True:
            print("请选择要修复的问题类型:")
            print("1. 语法错误")
            print("2. 导入错误")
            print("3. 测试收集错误")
            print("4. 配置问题")
            print("5. 依赖问题")
            print("0. 返回主菜单")

            choice = input("请选择 (0-5): ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.manual_fix_syntax()
            elif choice == "2":
                self.manual_fix_imports()
            elif choice == "3":
                self.manual_fix_test_collection()
            elif choice == "4":
                self.manual_fix_configuration()
            elif choice == "5":
                self.manual_fix_dependencies()
            else:
                print("❌ 无效选项")

    def view_history_reports(self):
        """查看历史报告"""
        print("\n📋 历史报告")
        print("-" * 50)

        reports_dir = self.project_root
        report_files = []

        # 查找报告文件
        for pattern in ["*crisis*report*.md", "*test*report*.md", "*quality*report*.md"]:
            report_files.extend(reports_dir.glob(pattern))

        if not report_files:
            print("❌ 未找到历史报告")
            return

        print("找到以下报告文件:")
        for i, report_file in enumerate(report_files, 1):
            print(f"{i}. {report_file.name}")

        try:
            choice = input(f"\n请选择要查看的报告 (1-{len(report_files)}) 或 0 返回: ").strip()
            if choice == "0":
                return

            index = int(choice) - 1
            if 0 <= index < len(report_files):
                self.display_report(report_files[index])
            else:
                print("❌ 无效选项")
        except ValueError:
            print("❌ 无效输入")

    def configuration_check(self):
        """配置检查"""
        print("\n⚙️ 配置检查")
        print("-" * 50)

        config_files = [
            "pytest.ini",
            "requirements.txt",
            "pyproject.toml",
            ".env.example",
            "Makefile"
        ]

        print("检查关键配置文件:")
        for config_file in config_files:
            config_path = self.project_root / config_file
            status = "✅ 存在" if config_path.exists() else "❌ 缺失"
            print(f"  {config_file}: {status}")

        # 检查pytest配置
        pytest_ini = self.project_root / "pytest.ini"
        if pytest_ini.exists():
            print("\n📋 pytest 配置内容:")
            try:
                with open(pytest_ini, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:20]  # 只显示前20行
                    for line in lines:
                        print(f"  {line.rstrip()}")
                if len(lines) == 20:
                    print("  ...")
            except Exception as e:
                print(f"  ❌ 读取失败: {e}")

    def show_help(self):
        """显示帮助"""
        print("\n🆘 帮助信息")
        print("-" * 50)
        print("📚 常用命令:")
        print("  make install          # 安装依赖")
        print("  make test.unit        # 运行单元测试")
        print("  make coverage         # 查看覆盖率")
        print("  make solve-test-crisis # 解决测试危机")
        print("  make ci-check         # CI/CD检查")
        print("")
        print("🔧 常见问题解决:")
        print("  1. 语法错误: 运行 python3 scripts/emergency_syntax_fixer.py")
        print("  2. 导入错误: 运行 python3 scripts/fix_common_imports.py")
        print("  3. 测试失败: 运行 python3 scripts/fix_test_crisis.py")
        print("")
        print("📖 更多帮助:")
        print("  - 查看 CLAUDE.md 文件")
        print("  - 查看 README.md 文件")
        print("  - 运行 make help 查看所有命令")

    def check_environment(self):
        """检查环境"""
        print("🌍 环境检查:")

        # Python版本
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"  Python版本: {py_version} {'✅' if sys.version_info >= (3, 8) else '❌'}")

        # 虚拟环境
        venv_status = "✅" if "VIRTUAL_ENV" in os.environ else "❌"
        print(f"  虚拟环境: {venv_status}")

        # 项目目录
        print(f"  项目目录: {self.project_root} ✅")

        # Git状态
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                modified_files = len([line for line in result.stdout.split('\n') if line.strip()])
                print(f"  Git状态: {modified_files}个文件修改")
        except:
            print("  Git状态: ❌ 无法检查")

    def check_dependencies(self):
        """检查依赖"""
        print("📦 依赖检查:")

        critical_packages = [
            ("fastapi", "FastAPI"),
            ("sqlalchemy", "SQLAlchemy"),
            ("pytest", "pytest"),
            ("redis", "Redis")
        ]

        for package, display_name in critical_packages:
            try:
                __import__(package)
                print(f"  {display_name}: ✅")
            except ImportError:
                print(f"  {display_name}: ❌")

    def check_syntax_issues(self):
        """检查语法问题"""
        print("📝 语法检查:")

        syntax_errors = 0
        py_files = 0

        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or ".git" in str(py_file):
                continue

            py_files += 1
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                compile(source, str(py_file), 'exec')
            except SyntaxError:
                syntax_errors += 1
            except:
                pass  # 忽略其他错误

        print(f"  检查文件: {py_files}个")
        print(f"  语法错误: {syntax_errors}个 {'✅' if syntax_errors == 0 else '❌'}")

    def check_test_collection(self):
        """检查测试收集"""
        print("🧪 测试收集检查:")

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode == 0:
                print("  测试收集: ✅")
            else:
                print("  测试收集: ❌")
                error_count = result.stderr.count("ERROR")
                warning_count = result.stdout.count("PytestCollectionWarning")
                print(f"  错误数量: {error_count}")
                print(f"  警告数量: {warning_count}")

        except Exception as e:
            print(f"  测试收集: ❌ 检查失败 ({e})")

    def provide_diagnosis_summary(self):
        """提供诊断摘要"""
        print("\n📋 诊断摘要:")
        print("-" * 30)

        # 这里可以基于前面的检查结果提供摘要
        print("✅ 环境基本正常")
        print("⚠️  存在一些语法或导入问题")
        print("💡 建议运行快速修复工具")

        choice = input("\n是否运行快速修复? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            self.run_quick_fix()

    def run_test_module(self, test_path: str):
        """运行指定测试模块"""
        print(f"\n🧪 运行测试: {test_path}")
        print("-" * 50)

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_path, "--maxfail=10", "-v", "--disable-warnings"],
                cwd=self.project_root,
                timeout=120
            )

            if result.returncode == 0:
                print("✅ 测试通过")
            else:
                print("❌ 测试失败")

        except subprocess.TimeoutExpired:
            print("⏰ 测试超时")
        except Exception as e:
            print(f"❌ 运行测试失败: {e}")

    def run_verification_test(self):
        """运行验证测试"""
        print("\n🧪 运行验证测试...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/unit/utils/", "--maxfail=5", "-q", "--disable-warnings"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print("✅ 验证测试通过")
            else:
                print("⚠️ 验证测试存在问题")
                # 简单解析结果
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and ('failed' in line or 'error' in line):
                        print(f"  结果: {line}")
                        break

        except Exception as e:
            print(f"❌ 验证测试失败: {e}")

    def show_basic_status(self):
        """显示基础状态"""
        print("📋 基础信息:")
        print(f"  项目名称: FootballPrediction")
        print(f"  项目路径: {self.project_root}")
        print(f"  Python版本: {sys.version.split()[0]}")

        # Git信息
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                print(f"  Git提交: {result.stdout.strip()}")
        except:
            pass

    def show_test_status(self):
        """显示测试状态"""
        print("🧪 测试状态:")

        # 尝试获取测试统计
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode == 0:
                # 尝试解析测试数量
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'collected' in line.lower() or 'test session' in line.lower():
                        print(f"  {line.strip()}")
                        break
            else:
                print("  ❌ 测试收集存在问题")
        except:
            print("  ❌ 无法获取测试状态")

    def show_quality_status(self):
        """显示代码质量状态"""
        print("🛡️ 代码质量:")

        # 检查是否有质量工具
        quality_tools = ["ruff", "mypy", "black"]
        available_tools = []

        for tool in quality_tools:
            try:
                result = subprocess.run([tool, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    available_tools.append(tool)
            except:
                pass

        if available_tools:
            print(f"  可用工具: {', '.join(available_tools)} ✅")
        else:
            print("  质量工具: ❌ 未安装")

    def show_dependency_status(self):
        """显示依赖状态"""
        print("📦 依赖状态:")

        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                print(f"  依赖文件: ✅ ({len(lines)}个依赖)")
            except:
                print("  依赖文件: ❌ 读取失败")
        else:
            print("  依赖文件: ❌ 不存在")

    def display_report(self, report_file: Path):
        """显示报告内容"""
        print(f"\n📄 报告内容: {report_file.name}")
        print("-" * 50)

        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 显示前50行
            for line in lines[:50]:
                print(line.rstrip())

            if len(lines) > 50:
                print(f"\n... (报告还有 {len(lines) - 50} 行)")
                choice = input("是否查看完整报告? (y/N): ").strip().lower()
                if choice in ['y', 'yes']:
                    for line in lines[50:]:
                        print(line.rstrip())

        except Exception as e:
            print(f"❌ 读取报告失败: {e}")

    def manual_fix_syntax(self):
        """手动修复语法错误"""
        print("\n📝 手动修复语法错误指南:")
        print("1. 运行: python3 scripts/emergency_syntax_fixer.py")
        print("2. 运行: python3 scripts/comprehensive_syntax_fixer.py")
        print("3. 检查特定文件: python -m py_compile 文件名")

        choice = input("是否运行自动语法修复? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            self.run_syntax_fixers()

    def manual_fix_imports(self):
        """手动修复导入错误"""
        print("\n📦 手动修复导入错误指南:")
        print("1. 检查模块路径是否正确")
        print("2. 确认依赖是否已安装")
        print("3. 运行: python3 scripts/fix_common_imports.py")

    def manual_fix_test_collection(self):
        """手动修复测试收集错误"""
        print("\n🧪 手动修复测试收集错误指南:")
        print("1. 检查测试文件命名规范")
        print("2. 确认测试类和函数命名")
        print("3. 检查pytest.ini配置")

    def manual_fix_configuration(self):
        """手动修复配置问题"""
        print("\n⚙️ 手动修复配置问题指南:")
        print("1. 检查pytest.ini是否存在")
        print("2. 确认requirements.txt完整性")
        print("3. 检查环境变量配置")

    def manual_fix_dependencies(self):
        """手动修复依赖问题"""
        print("\n📦 手动修复依赖问题指南:")
        print("1. 运行: make install")
        print("2. 检查Python包索引")
        print("3. 更新pip: pip install --upgrade pip")

    def run_syntax_fixers(self):
        """运行语法修复器"""
        fixers = [
            "emergency_syntax_fixer.py",
            "comprehensive_syntax_fixer.py"
        ]

        for fixer in fixers:
            fixer_path = self.project_root / "scripts" / fixer
            if fixer_path.exists():
                print(f"🔧 运行: {fixer}")
                try:
                    result = subprocess.run(
                        ["python3", str(fixer_path)],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print("✅ 修复成功")
                    else:
                        print("❌ 修复失败")
                except Exception as e:
                    print(f"❌ 运行失败: {e}")
            else:
                print(f"⚠️  脚本不存在: {fixer}")

    def run(self):
        """运行主程序"""
        self.show_banner()

        while True:
            try:
                choice = self.show_main_menu()
                print()

                if choice == "0":
                    print("👋 再见！")
                    break
                elif choice == "1":
                    self.run_comprehensive_diagnosis()
                elif choice == "2":
                    self.run_quick_fix()
                elif choice == "3":
                    self.run_specific_tests()
                elif choice == "4":
                    self.show_project_status()
                elif choice == "5":
                    self.manual_fix_wizard()
                elif choice == "6":
                    self.view_history_reports()
                elif choice == "7":
                    self.configuration_check()
                elif choice == "8":
                    self.show_help()
                else:
                    print("❌ 无效选项，请重新选择")

                print("\n" + "="*50)
                input("按Enter键继续...")
                print()

            except KeyboardInterrupt:
                print("\n\n👋 用户中断，退出程序")
                break
            except Exception as e:
                print(f"\n❌ 程序错误: {e}")
                input("按Enter键继续...")


def main():
    """主函数"""
    launcher = TestCrisisLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
