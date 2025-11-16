#!/usr/bin/env python3
"""
测试危机解决方案脚本
用于快速诊断和修复测试系统中的常见问题
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json


class TestCrisisSolver:
    """测试危机解决器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues_found = []
        self.fixes_applied = []

    def run_full_diagnosis(self) -> Dict[str, Any]:
        """运行完整的测试危机诊断"""
        print("🔍 开始测试危机诊断...")

        diagnosis = {
            "syntax_errors": self.check_syntax_errors(),
            "import_errors": self.check_import_errors(),
            "test_collection_errors": self.check_test_collection_errors(),
            "dependency_issues": self.check_dependency_issues(),
            "configuration_issues": self.check_configuration_issues(),
            "environment_issues": self.check_environment_issues()
        }

        return diagnosis

    def apply_automatic_fixes(self) -> None:
        """应用自动修复"""
        print("\n🔧 应用自动修复...")

        # 1. 修复语法错误
        self.fix_syntax_errors()

        # 2. 修复导入错误
        self.fix_import_errors()

        # 3. 修复测试收集错误
        self.fix_test_collection_errors()

        # 4. 修复依赖问题
        self.fix_dependency_issues()

    def check_syntax_errors(self) -> Dict[str, Any]:
        """检查语法错误"""
        print("  📝 检查语法错误...")

        syntax_errors = []

        # 使用Python的compile检查语法错误
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or ".git" in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                compile(source, str(py_file), 'exec')
            except SyntaxError as e:
                syntax_errors.append({
                    "file": str(py_file.relative_to(self.project_root)),
                    "line": e.lineno,
                    "error": str(e),
                    "type": "SyntaxError"
                })
            except Exception as e:
                # 其他编译错误
                if "invalid syntax" in str(e).lower():
                    syntax_errors.append({
                        "file": str(py_file.relative_to(self.project_root)),
                        "error": str(e),
                        "type": "CompilationError"
                    })

        self.issues_found.extend(syntax_errors)
        return {
            "count": len(syntax_errors),
            "errors": syntax_errors[:10]  # 只显示前10个
        }

    def check_import_errors(self) -> Dict[str, Any]:
        """检查导入错误"""
        print("  📦 检查导入错误...")

        # 运行pytest收集测试来检查导入错误
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            import_errors = []
            if result.returncode != 0:
                lines = result.stderr.split('\n')
                for line in lines:
                    if "ImportError" in line or "ModuleNotFoundError" in line:
                        import_errors.append(line.strip())

            self.issues_found.extend([{"type": "ImportError", "error": err} for err in import_errors])
            return {
                "pytest_returncode": result.returncode,
                "errors": import_errors[:10]
            }
        except Exception as e:
            return {"error": str(e)}

    def check_test_collection_errors(self) -> Dict[str, Any]:
        """检查测试收集错误"""
        print("  🧪 检查测试收集错误...")

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            collection_errors = []
            if result.returncode != 0:
                output = result.stderr + result.stdout
                lines = output.split('\n')

                for line in lines:
                    if "ERROR" in line and "collecting" in line:
                        collection_errors.append(line.strip())
                    elif "PytestCollectionWarning" in line:
                        collection_errors.append(line.strip())

            return {
                "returncode": result.returncode,
                "errors": collection_errors[:10]
            }
        except Exception as e:
            return {"error": str(e)}

    def check_dependency_issues(self) -> Dict[str, Any]:
        """检查依赖问题"""
        print("  🔗 检查依赖问题...")

        issues = []

        # 检查requirements.txt
        req_file = self.project_root / "requirements.txt"
        if not req_file.exists():
            issues.append("requirements.txt 文件不存在")

        # 检查关键依赖
        critical_packages = ["fastapi", "sqlalchemy", "pytest", "redis"]
        missing_packages = []

        for package in critical_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            issues.append(f"缺失关键依赖: {', '.join(missing_packages)}")

        return {
            "issues": issues,
            "missing_packages": missing_packages
        }

    def check_configuration_issues(self) -> Dict[str, Any]:
        """检查配置问题"""
        print("  ⚙️ 检查配置问题...")

        issues = []

        # 检查pytest.ini
        pytest_ini = self.project_root / "pytest.ini"
        if not pytest_ini.exists():
            issues.append("pytest.ini 配置文件不存在")

        # 检查.env.example
        env_example = self.project_root / ".env.example"
        if not env_example.exists():
            issues.append(".env.example 文件不存在")

        return {"issues": issues}

    def check_environment_issues(self) -> Dict[str, Any]:
        """检查环境问题"""
        print("  🌍 检查环境问题...")

        issues = []

        # 检查虚拟环境
        if "VIRTUAL_ENV" not in os.environ:
            issues.append("未检测到虚拟环境")

        # 检查Python版本
        if sys.version_info < (3, 8):
            issues.append(f"Python版本过低: {sys.version}")

        return {"issues": issues}

    def fix_syntax_errors(self) -> None:
        """修复语法错误"""
        print("  🔧 修复语法错误...")

        # 运行现有的语法修复脚本
        syntax_fixers = [
            "emergency_syntax_fixer.py",
            "comprehensive_syntax_fixer.py"
        ]

        for fixer in syntax_fixers:
            fixer_path = self.project_root / "scripts" / fixer
            if fixer_path.exists():
                try:
                    print(f"    运行: {fixer}")
                    result = subprocess.run(
                        ["python3", str(fixer_path)],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.fixes_applied.append(f"成功运行 {fixer}")
                    else:
                        self.fixes_applied.append(f"运行 {fixer} 失败: {result.stderr[:100]}")
                except Exception as e:
                    self.fixes_applied.append(f"运行 {fixer} 异常: {e}")

    def fix_import_errors(self) -> None:
        """修复导入错误"""
        print("  🔧 修复导入错误...")

        import_fixers = [
            "fix_common_imports.py",
            "fix_test_imports.py"
        ]

        for fixer in import_fixers:
            fixer_path = self.project_root / "scripts" / fixer
            if fixer_path.exists():
                try:
                    print(f"    运行: {fixer}")
                    result = subprocess.run(
                        ["python3", str(fixer_path)],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.fixes_applied.append(f"成功运行 {fixer}")
                except Exception as e:
                    self.fixes_applied.append(f"运行 {fixer} 异常: {e}")

    def fix_test_collection_errors(self) -> None:
        """修复测试收集错误"""
        print("  🔧 修复测试收集错误...")

        # 运行测试收集错误修复脚本
        fixers = [
            "fix_test_collection_errors.py",
            "quick_test_fix.py"
        ]

        for fixer in fixers:
            fixer_path = self.project_root / "scripts" / fixer
            if fixer_path.exists():
                try:
                    print(f"    运行: {fixer}")
                    result = subprocess.run(
                        ["python3", str(fixer_path)],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True
                    )
                    self.fixes_applied.append(f"运行 {fixer}: {'成功' if result.returncode == 0 else '失败'}")
                except Exception as e:
                    self.fixes_applied.append(f"运行 {fixer} 异常: {e}")

    def fix_dependency_issues(self) -> None:
        """修复依赖问题"""
        print("  🔧 修复依赖问题...")

        try:
            # 尝试安装依赖
            print("    安装依赖...")
            result = subprocess.run(
                ["make", "install"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.fixes_applied.append("依赖安装成功")
            else:
                self.fixes_applied.append(f"依赖安装失败: {result.stderr[:100]}")
        except Exception as e:
            self.fixes_applied.append(f"依赖安装异常: {e}")

    def run_verification_test(self) -> Dict[str, Any]:
        """运行验证测试"""
        print("\n🧪 运行验证测试...")

        try:
            # 运行一个简单的测试来验证修复效果
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/unit/utils/", "--maxfail=5", "-q", "--disable-warnings"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60  # 60秒超时
            )

            # 解析结果
            output_lines = result.stdout.split('\n')
            passed = 0
            failed = 0

            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # 解析类似 "5 failed, 440 passed in 18.94s" 的行
                    if "failed" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "failed" and i > 0:
                                failed = int(parts[i-1])
                            elif part == "passed" and i > 0:
                                passed = int(parts[i-1])
                                break
                    break
                elif line.strip().endswith("passed"):
                    passed += 1
                elif "FAILED" in line:
                    failed += 1

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "passed": passed,
                "failed": failed,
                "total": passed + failed,
                "output": result.stdout[:500],
                "error": result.stderr[:200] if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "测试超时（超过60秒）",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }

    def generate_report(self, diagnosis: Dict[str, Any], verification: Dict[str, Any]) -> str:
        """生成修复报告"""
        report = []
        report.append("# 测试危机解决方案报告")
        report.append(f"**生成时间**: {Path.cwd()}")
        report.append("")

        # 诊断结果
        report.append("## 🔍 诊断结果")
        report.append("")

        for category, results in diagnosis.items():
            report.append(f"### {category}")
            if isinstance(results, dict):
                if "count" in results:
                    report.append(f"- 发现问题数量: {results['count']}")
                if "issues" in results:
                    for issue in results["issues"]:
                        report.append(f"- {issue}")
                if "errors" in results:
                    for error in results.get("errors", []):
                        report.append(f"- {error}")
                if "missing_packages" in results:
                    if results["missing_packages"]:
                        report.append(f"- 缺失包: {', '.join(results['missing_packages'])}")
            report.append("")

        # 应用的修复
        report.append("## 🔧 应用的修复")
        report.append("")
        for fix in self.fixes_applied:
            report.append(f"- {fix}")
        report.append("")

        # 验证结果
        report.append("## 🧪 验证结果")
        report.append("")
        if verification.get("success", False):
            report.append("✅ **验证通过**")
            report.append(f"- 通过测试: {verification.get('passed', 0)}")
            report.append(f"- 失败测试: {verification.get('failed', 0)}")
            report.append(f"- 总计测试: {verification.get('total', 0)}")
        else:
            report.append("❌ **验证失败**")
            if verification.get("timeout"):
                report.append("- 测试超时")
            if verification.get("error"):
                report.append(f"- 错误: {verification['error']}")
        report.append("")

        # 建议
        report.append("## 💡 后续建议")
        report.append("")
        if not verification.get("success", False):
            report.append("1. 检查剩余的测试失败原因")
            report.append("2. 手动修复特定的测试问题")
            report.append("3. 考虑运行特定的测试模块")
        else:
            report.append("1. 运行完整的测试套件: `make test.unit`")
            report.append("2. 检查覆盖率: `make coverage`")
            report.append("3. 运行质量检查: `make ci-check`")

        return "\n".join(report)

    def solve_crisis(self, quick_fix: bool = False) -> None:
        """解决测试危机"""
        print("🚨 开始测试危机解决方案...")
        print("=" * 60)

        # 1. 诊断问题
        diagnosis = self.run_full_diagnosis()

        # 2. 应用修复
        self.apply_automatic_fixes()

        # 3. 验证修复效果
        verification = self.run_verification_test()

        # 4. 生成报告
        report = self.generate_report(diagnosis, verification)

        # 保存报告
        report_file = self.project_root / "test_crisis_solution_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 显示摘要
        print("\n" + "=" * 60)
        print("🎯 测试危机解决方案摘要")
        print("=" * 60)
        print(f"📋 发现问题: {len(self.issues_found)}个")
        print(f"🔧 应用修复: {len(self.fixes_applied)}个")

        if verification.get("success", False):
            print("✅ 验证通过")
            print(f"   通过测试: {verification.get('passed', 0)}")
            print(f"   失败测试: {verification.get('failed', 0)}")
        else:
            print("❌ 验证失败，需要进一步检查")

        print(f"📄 详细报告: {report_file}")
        print("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试危机解决方案")
    parser.add_argument("--quick-fix", action="store_true", help="快速修复模式")
    parser.add_argument("--diagnose-only", action="store_true", help="仅诊断，不修复")

    args = parser.parse_args()

    solver = TestCrisisSolver()

    if args.diagnose_only:
        # 仅运行诊断
        diagnosis = solver.run_full_diagnosis()
        print("\n诊断结果:")
        print(json.dumps(diagnosis, indent=2, ensure_ascii=False))
    else:
        # 运行完整的解决方案
        solver.solve_crisis(args.quick_fix)


if __name__ == "__main__":
    main()
