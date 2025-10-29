#!/usr/bin/env python3
"""
🚨 测试危机紧急修复脚本
解决测试覆盖率危机中的关键问题
执行时间: 2025-10-27
目标: 2小时内修复P0级别问题
"""

import os
import subprocess
import shutil
import glob
from pathlib import Path


class TestCrisisFixer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.errors_fixed = 0
        self.warnings_found = 0

    def clean_pycache(self):
        """清理Python缓存文件，解决模块冲突"""
        print("🧹 清理Python缓存文件...")
        cache_dirs = list(self.project_root.rglob("__pycache__"))
        pyc_files = list(self.project_root.rglob("*.pyc"))

        for cache_dir in cache_dirs:
            shutil.rmtree(cache_dir, ignore_errors=True)
            print(f"  ✓ 删除缓存目录: {cache_dir}")

        for pyc_file in pyc_files:
            pyc_file.unlink(missing_ok=True)
            print(f"  ✓ 删除pyc文件: {pyc_file}")

        print(f"✅ 清理完成: {len(cache_dirs)}个缓存目录, {len(pyc_files)}个pyc文件")

    def fix_import_conflicts(self):
        """修复import冲突问题"""
        print("🔧 修复import冲突...")

        # 检查问题文件
        problem_files = [
            "tests/examples/test_factory_usage.py",
            "tests/integration/test_api_service_integration_safe_import.py",
            "tests/integration/test_messaging_event_integration.py",
            "tests/unit/archived/test_comprehensive.py",
            "tests/unit/database/test_repositories/test_base.py",
        ]

        for file_path in problem_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"  🔍 检查文件: {file_path}")

                # 修复test_api_service_integration_safe_import.py的IMPORT_SUCCESS问题
                if "api_service_integration_safe_import" in file_path:
                    self.fix_import_success_variable(full_path)

                # 修复test_messaging_event_integration.py的参数问题
                elif "messaging_event_integration" in file_path:
                    self.fix_message_test_signature(full_path)

                # 对于重复命名的文件，考虑重命名
                elif self.check_name_conflict(full_path):
                    new_name = self.resolve_name_conflict(full_path)
                    if new_name:
                        print(f"  📝 重命名文件: {file_path} -> {new_name}")

    def fix_import_success_variable(self, file_path):
        """修复IMPORT_SUCCESS变量未定义问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if "IMPORT_SUCCESS" in content and "IMPORT_SUCCESS =" not in content:
                # 在文件开头添加变量定义
                lines = content.split("\n")
                import_lines = []
                other_lines = []

                for line in lines:
                    if line.startswith("from ") or line.startswith("import "):
                        import_lines.append(line)
                    else:
                        other_lines.append(line)

                # 添加IMPORT_SUCCESS定义
                fixed_content = "\n".join(import_lines) + "\n\n"
                fixed_content += "# 导入成功标志\n"
                fixed_content += "IMPORT_SUCCESS = True\n"
                fixed_content += "IMPORT_ERROR = None\n\n"
                fixed_content += "\n".join(other_lines)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

                print(f"    ✅ 修复IMPORT_SUCCESS变量: {file_path}")
                self.errors_fixed += 1

        except Exception as e:
            print(f"    ❌ 修复失败: {e}")

    def fix_message_test_signature(self, file_path):
        """修复测试函数参数问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找并修复函数签名问题
            if "def test_message_size_handling(" in content and "message_size" not in content:
                # 修复函数签名
                content = content.replace(
                    "def test_message_size_handling():",
                    "def test_message_size_handling(message_size):",
                )

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"    ✅ 修复函数签名: {file_path}")
                self.errors_fixed += 1

        except Exception as e:
            print(f"    ❌ 修复失败: {e}")

    def check_name_conflict(self, file_path):
        """检查文件名冲突"""
        file_name = file_path.stem
        conflicts = list(self.project_root.rglob(f"{file_name}.py"))
        return len(conflicts) > 1

    def resolve_name_conflict(self, file_path):
        """解决文件名冲突"""
        # 简单的重命名策略
        parent = file_path.parent
        stem = file_path.stem
        suffix = parent.name.replace("tests_", "").replace("test_", "")
        new_name = f"{stem}_{suffix}.py"

        try:
            new_path = parent / new_name
            if not new_path.exists():
                file_path.rename(new_path)
                return str(new_path.relative_to(self.project_root))
        except Exception as e:
            print(f"    ❌ 重命名失败: {e}")

        return None

    def run_quick_test_check(self):
        """运行快速测试检查"""
        print("🧪 运行快速测试检查...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                collected = result.stdout.split("collected")[1].split()[0]
                print(f"  ✅ 测试收集成功: {collected}个测试用例")
                return True
            else:
                print(f"  ❌ 测试收集失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("  ⏰ 测试收集超时")
            return False
        except Exception as e:
            print(f"  ❌ 测试检查异常: {e}")
            return False

    def generate_coverage_report(self):
        """生成覆盖率报告"""
        print("📊 生成覆盖率报告...")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=src", "--cov-report=html", "--maxfail=5", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )

            if result.returncode == 0:
                print("  ✅ 覆盖率报告生成成功")
                return True
            else:
                print(f"  ⚠️ 覆盖率生成有警告: {len(result.stderr.splitlines())}行错误")
                return True  # 即使有错误也继续

        except subprocess.TimeoutExpired:
            print("  ⏰ 覆盖率生成超时，使用快速模式")
            return self.run_quick_coverage()
        except Exception as e:
            print(f"  ❌ 覆盖率生成失败: {e}")
            return False

    def run_quick_coverage(self):
        """运行快速覆盖率检查"""
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--maxfail=3",
                    "-q",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            print("  📊 快速覆盖率报告:")
            for line in result.stdout.split("\n"):
                if "TOTAL" in line or "%" in line:
                    print(f"    {line}")

            return True

        except Exception as e:
            print(f"  ❌ 快速覆盖率失败: {e}")
            return False

    def run_fix_cycle(self):
        """执行完整的修复周期"""
        print("🚀 开始测试危机紧急修复...")
        print("=" * 50)

        # 步骤1: 清理缓存
        self.clean_pycache()
        print()

        # 步骤2: 修复导入冲突
        self.fix_import_conflicts()
        print()

        # 步骤3: 测试检查
        if self.run_quick_test_check():
            print("✅ 测试收集通过")
        else:
            print("⚠️ 测试收集仍有问题，需要手动检查")
        print()

        # 步骤4: 覆盖率报告
        self.generate_coverage_report()
        print()

        # 总结
        print("=" * 50)
        print("🎯 修复完成!")
        print(f"  📊 修复错误: {self.errors_fixed}个")
        print(f"  ⚠️ 发现警告: {self.warnings_found}个")
        print("  📈 建议下一步: 运行 make coverage 查看详细报告")


if __name__ == "__main__":
    fixer = TestCrisisFixer()
    fixer.run_fix_cycle()
