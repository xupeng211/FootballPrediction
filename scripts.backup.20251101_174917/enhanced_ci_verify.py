#!/usr/bin/env python3
"""
增强版CI验证脚本
针对Phase G Week 5优化的本地CI/CD验证工具
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple

class EnhancedCIVerifier:
    """增强版CI验证器"""

    def __init__(self):
        self.venv_path = Path(".venv")
        self.results = {
            "dependency_check": False,
            "syntax_check": False,
            "quality_check": False,
            "test_check": False,
            "docker_check": False,
            "overall_status": False
        }

    def print_status(self, status: str, message: str):
        """打印状态信息"""
        colors = {
            "success": "\033[0;32m✅",
            "error": "\033[0;31m❌",
            "info": "\033[0;34mℹ️ ",
            "warning": "\033[1;33m⚠️",
            "reset": "\033[0m"
        }

        icon = colors.get(status, "")
        reset = colors["reset"]
        print(f"{icon} {message}{reset}")

    def run_command(self, command: List[str], description: str, check: bool = True) -> Tuple[bool, str]:
        """运行命令并返回结果"""
        self.print_status("info", f"执行: {description}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                self.print_status("success", f"{description} - 成功")
                return True, result.stdout
            else:
                self.print_status("error", f"{description} - 失败")
                if result.stderr:
                    print(f"错误信息: {result.stderr[:500]}...")
                return False, result.stderr

        except subprocess.TimeoutExpired:
            self.print_status("error", f"{description} - 超时")
            return False, "Command timeout"
        except Exception as e:
            self.print_status("error", f"{description} - 异常: {e}")
            return False, str(e)

    def check_dependencies(self) -> bool:
        """检查依赖安装"""
        self.print_status("info", "步骤 1/5: 检查依赖安装")

        # 检查虚拟环境
        if not self.venv_path.exists():
            self.print_status("info", "创建虚拟环境...")
            success, _ = self.run_command([
                sys.executable, "-m", "venv", ".venv"
            ], "创建虚拟环境", check=False)

            if not success:
                return False

        # 激活虚拟环境并安装依赖
        pip_cmd = [str(self.venv_path / "bin" / "pip")]

        # 升级pip
        success, _ = self.run_command([
            *pip_cmd, "install", "--upgrade", "pip"
        ], "升级pip", check=False)

        # 安装锁定依赖
        requirements_lock = Path("requirements/requirements.lock")
        if requirements_lock.exists():
            success, _ = self.run_command([
                *pip_cmd, "install", "-r", str(requirements_lock)
            ], "安装锁定依赖", check=False)
            if not success:
                return False

        # 安装开发依赖
        requirements_dev = Path("requirements/dev.txt")
        if requirements_dev.exists():
            success, _ = self.run_command([
                *pip_cmd, "install", "-r", str(requirements_dev)
            ], "安装开发依赖", check=False)

        # 安装当前项目
        success, _ = self.run_command([
            *pip_cmd, "install", "-e", "."
        ], "安装当前项目", check=False)

        self.results["dependency_check"] = success
        return success

    def check_syntax(self) -> bool:
        """检查Python语法"""
        self.print_status("info", "步骤 2/5: 检查Python语法")

        python_cmd = [str(self.venv_path / "bin" / "python")]

        # 编译检查所有Python文件
        success, _ = self.run_command([
            *python_cmd, "-c",
            """
import ast
import os
import sys

errors = []
for root, dirs, files in os.walk('.'):
    # 跳过隐藏目录和虚拟环境
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content, filepath)
            except SyntaxError as e:
                errors.append(f"{filepath}:{e.lineno}: {e.msg}")
            except Exception as e:
                errors.append(f"{filepath}: {e}")

if errors:
    print(f"发现 {len(errors)} 个语法错误:")
    for error in errors[:10]:  # 只显示前10个
        print(f"  - {error}")
    if len(errors) > 10:
        print(f"  ... 还有 {len(errors) - 10} 个错误")
    sys.exit(1)
else:
    print("✅ 所有Python文件语法检查通过")
            """
        ], "Python语法检查", check=False)

        self.results["syntax_check"] = success
        return success

    def check_code_quality(self) -> bool:
        """检查代码质量"""
        self.print_status("info", "步骤 3/5: 检查代码质量")

        # Ruff检查
        ruff_cmd = [str(self.venv_path / "bin" / "ruff")]
        success, _ = self.run_command([
            *ruff_cmd, "check", ".", "--output-format=concise"
        ], "Ruff代码检查", check=False)

        # MyPy检查（可选）
        mypy_cmd = [str(self.venv_path / "bin" / "mypy")]
        self.run_command([
            *mypy_cmd, "src/", "--ignore-missing-imports"
        ], "MyPy类型检查", check=False)

        self.results["quality_check"] = success
        return success

    def check_tests(self) -> bool:
        """检查测试"""
        self.print_status("info", "步骤 4/5: 检查测试")

        pytest_cmd = [str(self.venv_path / "bin" / "pytest")]

        # 测试收集
        success, output = self.run_command([
            *pytest_cmd, "--collect-only", "-q"
        ], "测试收集", check=False)

        if not success:
            return False

        # 运行简单测试
        success, _ = self.run_command([
            *pytest_cmd,
            "tests/unit/utils/test_core_logger.py::TestLogger::test_setup_logger_all_levels",
            "-v", "--tb=short"
        ], "运行示例测试", check=False)

        self.results["test_check"] = success
        return success

    def check_docker(self) -> bool:
        """检查Docker环境"""
        self.print_status("info", "步骤 5/5: 检查Docker环境")

        # 检查Docker是否可用
        success, _ = self.run_command([
            "docker", "--version"
        ], "Docker版本检查", check=False)

        if not success:
            self.print_status("warning", "Docker不可用，跳过Docker检查")
            self.results["docker_check"] = True  # 跳过不算失败
            return True

        # 检查Docker Compose文件
        compose_files = [
            "docker-compose.yml",
            "docker-compose.prod.yml",
            "Dockerfile"
        ]

        all_exist = True
        for file in compose_files:
            if Path(file).exists():
                self.print_status("success", f"找到 {file}")
            else:
                self.print_status("warning", f"缺少 {file}")

        self.results["docker_check"] = all_exist
        return all_exist

    def generate_report(self):
        """生成验证报告"""
        self.print_status("info", "生成验证报告...")

        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results) - 1  # 排除overall_status

        self.results["overall_status"] = passed == total

        print("\n" + "="*60)
        print("📊 CI验证结果摘要")
        print("="*60)

        status_names = {
            "dependency_check": "依赖检查",
            "syntax_check": "语法检查",
            "quality_check": "质量检查",
            "test_check": "测试检查",
            "docker_check": "Docker检查"
        }

        for key, status in self.results.items():
            if key == "overall_status":
                continue

            name = status_names.get(key, key)
            icon = "✅" if status else "❌"
            print(f"{icon} {name}: {'通过' if status else '失败'}")

        print(f"\n📈 总体通过率: {passed}/{total} ({passed/total*100:.1f}%)")

        if self.results["overall_status"]:
            self.print_status("success", "🎉 CI验证完全通过！")
        else:
            self.print_status("error", "❌ CI验证失败，请检查上述问题")

        # 保存报告
        report_path = "ci_verification_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存: {report_path}")

        return self.results["overall_status"]

    def run_verification(self) -> bool:
        """运行完整验证"""
        self.print_status("info", "🚀 开始增强版CI验证...")
        print("="*60)

        steps = [
            self.check_dependencies,
            self.check_syntax,
            self.check_code_quality,
            self.check_tests,
            self.check_docker
        ]

        for step in steps:
            if not step():
                self.print_status("error", "验证步骤失败，停止执行")
                break

        return self.generate_report()

def main():
    """主函数"""
    verifier = EnhancedCIVerifier()
    success = verifier.run_verification()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()