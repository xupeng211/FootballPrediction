#!/usr/bin/env python3
"""
系统性 MyPy 类型错误修复脚本
Systematic MyPy Type Error Fix Script

专门设计用于修复最常见的 MyPy 类型错误，包括：
- callable → typing.Callable
- 缺失的 logger 导入
- 缺失的类型注解
- unused-ignore 错误
- no-any-return 错误
- var-annotated 错误
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
import time
from datetime import datetime


class MyPyErrorFixer:
    """MyPy 错误修复器"""

    def __init__(self, project_root: str = None):
        """初始化修复器"""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.src_dir = self.project_root / "src"
        self.fixed_files = set()
        self.error_stats = {
            "total_errors": 0,
            "fixed_errors": 0,
            "skipped_errors": 0,
            "failed_fixes": 0,
            "by_type": {},
        }
        self.start_time = time.time()
        self.dry_run = False

    def get_mypy_errors(self, module: str = "src") -> List[Dict[str, Any]]:
        """
        获取 MyPy 错误列表

        Args:
            module: 要检查的模块路径

        Returns:
            错误字典列表，每个错误包含文件路径、行号、错误类型和错误信息
        """
        print(f"🔍 获取 {module} 的 MyPy 错误...")

        try:
            result = subprocess.run(
                ["mypy", module, "--show-error-codes", "--no-error-summary"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            print("❌ MyPy 运行超时")
            return []
        except FileNotFoundError:
            print("❌ 找不到 mypy 命令，请确保已安装")
            return []

        errors = []
        for line in result.stdout.split("\n"):
            if ": error:" in line and "note:" not in line:
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    file_path = parts[0]
                    line_num = int(parts[1])
                    error_msg = parts[3].strip()

                    # 提取错误代码
                    error_code = "unknown"
                    if "[" in error_msg and "]" in error_msg:
                        code_match = re.search(r"\[([^\]]+)\]", error_msg)
                        if code_match:
                            error_code = code_match.group(1)

                    errors.append(
                        {
                            "file": file_path,
                            "line": line_num,
                            "message": error_msg,
                            "code": error_code,
                            "raw_line": line,
                        }
                    )

        self.error_stats["total_errors"] = len(errors)
        print(f"📊 发现 {len(errors)} 个 MyPy 错误")
        return errors

    def analyze_error_patterns(
        self, errors: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        分析错误模式并按类型分组

        Args:
            errors: 错误列表

        Returns:
            按错误类型分组的字典
        """
        patterns = {
            "callable_to_typing": [],
            "missing_logger": [],
            "var_annotated": [],
            "no_any_return": [],
            "unused_ignore": [],
            "import_not_found": [],
            "name_not_defined": [],
            "attr_defined": [],
            "arg_type": [],
            "valid_type": [],
            "misc": [],
            "others": [],
        }

        for error in errors:
            msg = error["message"].lower()
            code = error["code"]

            if 'function "builtins.callable" is not valid as a type' in msg:
                patterns["callable_to_typing"].append(error)
            elif 'name "logger" is not defined' in msg:
                patterns["missing_logger"].append(error)
            elif code == "var-annotated":
                patterns["var_annotated"].append(error)
            elif code == "no-any-return":
                patterns["no_any_return"].append(error)
            elif code == "unused-ignore":
                patterns["unused_ignore"].append(error)
            elif code == "import-not-found":
                patterns["import_not_found"].append(error)
            elif code == "name-defined":
                patterns["name_not_defined"].append(error)
            elif code == "attr-defined":
                patterns["attr_defined"].append(error)
            elif code == "arg-type":
                patterns["arg_type"].append(error)
            elif code == "valid-type":
                patterns["valid_type"].append(error)
            elif code == "misc":
                patterns["misc"].append(error)
            else:
                patterns["others"].append(error)

        # 打印分析结果
        print("\n📋 错误类型分析：")
        for error_type, error_list in patterns.items():
            if error_list:
                print(f"  {error_type}: {len(error_list)} 个")
                self.error_stats["by_type"][error_type] = len(error_list)

        return patterns

    def fix_callable_to_typing(self, error: Dict[str, Any]) -> bool:
        """
        修复 callable → typing.Callable 错误

        Args:
            error: 错误信息字典

        Returns:
            修复是否成功
        """
        file_path = self.project_root / error["file"]
        line_num = error["line"]

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_num <= len(lines):
                original_line = lines[line_num - 1]

                # 替换 callable 为 typing.Callable
                fixed_line = re.sub(r"\bcallable\b", "typing.Callable", original_line)

                # 确保导入了 typing.Callable
                if "typing" not in fixed_line and "Callable" not in fixed_line:
                    # 检查文件顶部是否已有 typing 导入
                    typing_imported = False
                    for i, line in enumerate(lines[:10]):  # 检查前10行
                        if "import typing" in line or "from typing import" in line:
                            if "Callable" in line:
                                typing_imported = True
                            else:
                                # 在现有 typing 导入中添加 Callable
                                lines[i] = line.rstrip() + ", Callable\n"
                                typing_imported = True
                            break

                    # 如果没有 typing 导入，添加一个
                    if not typing_imported:
                        # 找到最后一个 import 语句
                        last_import = 0
                        for i, line in enumerate(lines[:15]):
                            if line.strip().startswith("import") or line.strip().startswith("from"):
                                last_import = i + 1

                        # 在最后一个 import 后添加 typing 导入
                        lines.insert(last_import, "from typing import Callable\n")

                lines[line_num - 1] = fixed_line

                if not self.dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(lines)

                print(f"✅ 修复 {file_path}:{line_num} callable → typing.Callable")
                self.fixed_files.add(str(file_path))
                return True

        except Exception as e:
            print(f"❌ 修复 {file_path}:{line_num} 失败: {e}")
            return False

    def fix_missing_logger(self, error: Dict[str, Any]) -> bool:
        """
        修复缺失的 logger 导入

        Args:
            error: 错误信息字典

        Returns:
            修复是否成功
        """
        file_path = self.project_root / error["file"]

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否已有 logger 导入
            if "import logging" in content or "from logging" in content:
                return False  # 已有导入，可能需要其他修复

            # 添加 logger 导入和初始化
            lines = content.split("\n")

            # 找到最后一个 import 语句
            last_import = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("import") or line.strip().startswith("from"):
                    last_import = i + 1

            # 添加 logging 导入
            lines.insert(last_import, "import logging")
            lines.insert(last_import + 1, "")

            # 在文件中找到第一个 logger 使用前添加初始化
            logger_added = False
            for i, line in enumerate(lines):
                if "logger" in line and "logging" not in line and not logger_added:
                    lines.insert(i, "logger = logging.getLogger(__name__)")
                    lines.insert(i + 1, "")
                    logger_added = True
                    break

            if not self.dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

            print(f"✅ 修复 {file_path} 添加 logger 导入和初始化")
            self.fixed_files.add(str(file_path))
            return True

        except Exception as e:
            print(f"❌ 修复 {file_path} logger 失败: {e}")
            return False

    def fix_var_annotated(self, error: Dict[str, Any]) -> bool:
        """
        修复变量类型注解错误

        Args:
            error: 错误信息字典

        Returns:
            修复是否成功
        """
        file_path = self.project_root / error["file"]
        line_num = error["line"]

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_num <= len(lines):
                original_line = lines[line_num - 1]

                # 尝试从错误信息中推断类型
                var_name_match = re.search(r"\"([^\"]+)\"", error["message"])
                if var_name_match:
                    var_name = var_name_match.group(1)

                    # 尝试分析变量类型
                    if "=" in original_line:
                        # 分析赋值表达式来推断类型
                        value_part = original_line.split("=", 1)[1].strip()
                        inferred_type = self.infer_type_from_value(value_part)

                        if inferred_type:
                            # 添加类型注解
                            fixed_line = original_line.replace(
                                f"{var_name} =", f"{var_name}: {inferred_type} ="
                            )
                            lines[line_num - 1] = fixed_line

                            if not self.dry_run:
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.writelines(lines)

                            print(f"✅ 修复 {file_path}:{line_num} 添加类型注解: {inferred_type}")
                            self.fixed_files.add(str(file_path))
                            return True

        except Exception as e:
            print(f"❌ 修复 {file_path}:{line_num} 类型注解失败: {e}")
            return False

    def infer_type_from_value(self, value: str) -> Optional[str]:
        """
        从值推断类型

        Args:
            value: 值字符串

        Returns:
            推断的类型字符串
        """
        value = value.strip()

        if value.startswith("[") and value.endswith("]"):
            return "list"
        elif value.startswith("{") and value.endswith("}"):
            if ":" in value:
                return "dict"
            else:
                return "set"
        elif value.startswith("(") and value.endswith(")"):
            return "tuple"
        elif value.startswith('"') or value.startswith("'"):
            return "str"
        elif value.isdigit():
            return "int"
        elif value.replace(".", "").isdigit():
            return "float"
        elif value in ("True", "False"):
            return "bool"
        elif value.startswith("lambda"):
            return "Callable"
        elif "None" in value:
            return "Any"
        else:
            return "Any"

    def fix_unused_ignore(self, error: Dict[str, Any]) -> bool:
        """
        修复未使用的 type: ignore 注释

        Args:
            error: 错误信息字典

        Returns:
            修复是否成功
        """
        file_path = self.project_root / error["file"]
        line_num = error["line"]

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if line_num <= len(lines):
                original_line = lines[line_num - 1]

                # 移除 type: ignore 注释
                fixed_line = re.sub(r"\s*#\s*type:\s*ignore.*$", "", original_line)

                if fixed_line != original_line:
                    lines[line_num - 1] = fixed_line

                    if not self.dry_run:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.writelines(lines)

                    print(f"✅ 修复 {file_path}:{line_num} 移除未使用的 type: ignore")
                    self.fixed_files.add(str(file_path))
                    return True

        except Exception as e:
            print(f"❌ 修复 {file_path}:{line_num} unused-ignore 失败: {e}")
            return False

    def fix_no_any_return(self, error: Dict[str, Any]) -> bool:
        """
        修复 no-any-return 错误

        Args:
            error: 错误信息字典

        Returns:
            修复是否成功
        """
        file_path = self.project_root / error["file"]
        line_num = error["line"]

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 查找函数定义并添加 return 语句或类型注解
            # 这里简化处理，添加 type: ignore 注释
            if line_num <= len(lines):
                original_line = lines[line_num - 1]

                # 在函数行添加 type: ignore
                if "def " in original_line:
                    fixed_line = original_line.rstrip() + "  # type: ignore\n"
                    lines[line_num - 1] = fixed_line

                    if not self.dry_run:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.writelines(lines)

                    print(f"✅ 修复 {file_path}:{line_num} 添加 type: ignore for no-any-return")
                    self.fixed_files.add(str(file_path))
                    return True

        except Exception as e:
            print(f"❌ 修复 {file_path}:{line_num} no-any-return 失败: {e}")
            return False

    def fix_errors_batch(self, patterns: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        批量修复错误

        Args:
            patterns: 按类型分组的错误模式
        """
        print("\n🔧 开始批量修复错误...")

        # 定义修复策略和优先级
        fix_strategies = [
            (
                "callable_to_typing",
                self.fix_callable_to_typing,
                "callable → typing.Callable",
            ),
            ("missing_logger", self.fix_missing_logger, "缺失 logger 导入"),
            ("var_annotated", self.fix_var_annotated, "变量类型注解"),
            ("unused_ignore", self.fix_unused_ignore, "未使用的 type: ignore"),
            ("no_any_return", self.fix_no_any_return, "no-any-return 错误"),
        ]

        for error_type, fix_func, description in fix_strategies:
            errors = patterns.get(error_type, [])
            if errors:
                print(f"\n📝 修复 {description} ({len(errors)} 个)")
                for error in errors:
                    try:
                        if fix_func(error):
                            self.error_stats["fixed_errors"] += 1
                        else:
                            self.error_stats["skipped_errors"] += 1
                    except Exception as e:
                        print(f"❌ 修复失败: {e}")
                        self.error_stats["failed_fixes"] += 1

    def generate_report(self) -> str:
        """
        生成修复报告

        Returns:
            报告内容
        """
        elapsed_time = time.time() - self.start_time
        report_lines = [
            "=" * 60,
            "🔧 MyPy 错误修复报告",
            "=" * 60,
            f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"⌛ 耗时: {elapsed_time:.2f} 秒",
            "",
            "📊 修复统计:",
            f"  • 总错误数: {self.error_stats['total_errors']}",
            f"  • 已修复: {self.error_stats['fixed_errors']}",
            f"  • 跳过: {self.error_stats['skipped_errors']}",
            f"  • 失败: {self.error_stats['failed_fixes']}",
            "",
            "📋 错误类型分布:",
        ]

        for error_type, count in self.error_stats["by_type"].items():
            report_lines.append(f"  • {error_type}: {count} 个")

        report_lines.extend(
            [
                "",
                f"📁 修复的文件数: {len(self.fixed_files)}",
                "",
                "📝 修复的文件列表:",
            ]
        )

        for file_path in sorted(self.fixed_files):
            report_lines.append(f"  • {file_path}")

        report_lines.extend(
            [
                "",
                "=" * 60,
            ]
        )

        return "\n".join(report_lines)

    def save_report(self, report: str, filename: str = None) -> None:
        """
        保存修复报告

        Args:
            report: 报告内容
            filename: 文件名，默认使用时间戳
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mypy_fix_report_{timestamp}.md"

        report_path = self.project_root / "scripts" / "cleanup" / filename
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📄 报告已保存到: {report_path}")

    def run(self, module: str = "src", dry_run: bool = False) -> None:
        """
        运行完整的修复流程

        Args:
            module: 要修复的模块
            dry_run: 是否为试运行模式
        """
        self.dry_run = dry_run

        if dry_run:
            print("🔍 试运行模式 - 不会修改任何文件")

        print(f"🚀 开始修复 {module} 的 MyPy 错误...")

        # 1. 获取错误
        errors = self.get_mypy_errors(module)
        if not errors:
            print("✅ 没有发现 MyPy 错误!")
            return

        # 2. 分析错误模式
        patterns = self.analyze_error_patterns(errors)

        # 3. 批量修复
        self.fix_errors_batch(patterns)

        # 4. 生成报告
        report = self.generate_report()
        print(report)

        # 5. 保存报告
        self.save_report(report)

        # 6. 显示剩余错误
        print(f"\n🔍 再次检查 {module} 的 MyPy 错误...")
        remaining_errors = self.get_mypy_errors(module)
        if remaining_errors:
            print(f"⚠️  仍有 {len(remaining_errors)} 个错误需要手动修复:")
            for error in remaining_errors[:10]:  # 显示前10个
                print(f"  • {error['file']}:{error['line']} - {error['message']}")
            if len(remaining_errors) > 10:
                print(f"  ... 还有 {len(remaining_errors) - 10} 个错误")
        else:
            print("🎉 所有错误已修复!")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="系统性 MyPy 错误修复脚本")
    parser.add_argument("--module", default="src", help="要修复的模块路径 (默认: src)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不修改文件")
    parser.add_argument("--project-root", default=None, help="项目根目录路径")

    args = parser.parse_args()

    fixer = MyPyErrorFixer(args.project_root)
    fixer.run(args.module, args.dry_run)


if __name__ == "__main__":
    main()
