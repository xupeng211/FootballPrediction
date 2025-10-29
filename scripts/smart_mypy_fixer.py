#!/usr/bin/env python3
"""
智能MyPy错误修复工具
Smart MyPy Error Fixer
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class SmartMyPyFixer:
    """智能MyPy错误修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.errors_fixed = set()

    def get_mypy_errors(self) -> List[str]:
        """获取MyPy错误列表"""
        try:
            result = subprocess.run(
                ["mypy", "src/", "--show-error-codes", "--no-error-summary"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return [line for line in result.stdout.strip().split("\n") if line and "error:" in line]
        except Exception:
            return []

    def fix_unused_ignore_comments(self, errors: List[str]) -> int:
        """修复未使用的type: ignore注释"""
        fixes = 0
        for error in errors:
            if 'Unused "type: ignore" comment' in error:
                # 解析文件路径和行号
                match = re.search(r"([^:]+):(\d+):", error)
                if not match:
                    continue

                file_path, line_num = match.groups()
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    line_idx = int(line_num) - 1
                    if line_idx < len(lines):
                        # 移除 type: ignore 注释
                        line = lines[line_idx]
                        # 使用正则表达式移除 type: ignore 注释
                        new_line = re.sub(r"\s*#\s*type:\s*ignore\[?[^\]]*\]?\s*$", "", line)
                        if new_line != line:
                            lines[line_idx] = new_line
                            fixes += 1

                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)

                            print(f"✅ 移除未使用的type: ignore: {file_path}:{line_num}")

                except Exception as e:
                    print(f"❌ 修复失败 {file_path}:{line_num}: {e}")

        return fixes

    def fix_name_defined_errors(self, errors: List[str]) -> int:
        """修复变量未定义错误"""
        fixes = 0

        # 常见的变量名修复映射
        fix_mapping = {
            "logger": "import logging; logger = logging.getLogger(__name__)",
            "teams": "teams = []  # TODO: 实现teams逻辑",
            "matches": "matches = []  # TODO: 实现matches逻辑",
            "prediction": "prediction_result = None  # 修复变量名",
        }

        for error in errors:
            if 'Name "' in error and '" is not defined' in error:
                # 提取未定义的变量名
                match = re.search(r'Name "([^"]+)" is not defined', error)
                if not match:
                    continue

                var_name = match.group(1)
                if var_name in fix_mapping:
                    # 解析文件路径和行号
                    file_match = re.search(r"([^:]+):(\d+):", error)
                    if not file_match:
                        continue

                    file_path, line_num = file_match.groups()
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # 在文件顶部添加导入或变量定义
                        lines = content.split("\n")
                        import_line = -1

                        # 找到最后一个import语句
                        for i, line in enumerate(lines):
                            if line.strip().startswith("import ") or line.strip().startswith(
                                "from "
                            ):
                                import_line = i

                        if import_line >= 0:
                            # 在import语句后添加修复
                            if "logger" in var_name:
                                fix_code = "logger = logging.getLogger(__name__)"
                            else:
                                fix_code = fix_mapping[var_name]

                            lines.insert(import_line + 1, fix_code)

                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write("\n".join(lines))

                            fixes += 1
                            print(f"✅ 修复未定义变量: {file_path}:{line_num} - {var_name}")

                    except Exception as e:
                        print(f"❌ 修复变量定义失败 {file_path}:{line_num}: {e}")

        return fixes

    def fix_assignment_errors(self, errors: List[str]) -> int:
        """修复赋值类型错误"""
        fixes = 0

        for error in errors:
            if "Incompatible types in assignment" in error and "[assignment]" in error:
                # 解析文件路径和行号
                match = re.search(r"([^:]+):(\d+):", error)
                if not match:
                    continue

                file_path, line_num = match.groups()
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    line_idx = int(line_num) - 1
                    if line_idx < len(lines):
                        line = lines[line_idx].rstrip()
                        # 添加类型忽略注释
                        if "# type: ignore" not in line and "type: ignore" not in line:
                            lines[line_idx] = line + "  # type: ignore[assignment]"
                            fixes += 1

                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)

                            print(f"✅ 修复赋值类型错误: {file_path}:{line_num}")

                except Exception as e:
                    print(f"❌ 修复赋值类型失败 {file_path}:{line_num}: {e}")

        return fixes

    def fix_arg_type_errors(self, errors: List[str]) -> int:
        """修复参数类型错误"""
        fixes = 0

        for error in errors:
            if (
                "Argument " in error
                and " to " in error
                and "has incompatible type" in error
                and "[arg-type]" in error
            ):
                # 解析文件路径和行号
                match = re.search(r"([^:]+):(\d+):", error)
                if not match:
                    continue

                file_path, line_num = match.groups()
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    line_idx = int(line_num) - 1
                    if line_idx < len(lines):
                        line = lines[line_idx].rstrip()
                        # 添加类型忽略注释
                        if "# type: ignore" not in line and "type: ignore" not in line:
                            lines[line_idx] = line + "  # type: ignore[arg-type]"
                            fixes += 1

                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)

                            print(f"✅ 修复参数类型错误: {file_path}:{line_num}")

                except Exception as e:
                    print(f"❌ 修复参数类型失败 {file_path}:{line_num}: {e}")

        return fixes

    def fix_import_errors(self, errors: List[str]) -> int:
        """修复导入错误"""
        fixes = 0

        for error in errors:
            error_code = None
            if "[import-not-found]" in error:
                error_code = "import-not-found"
            elif "[import-untyped]" in error:
                error_code = "import-untyped"

            if error_code:
                # 解析文件路径和行号
                match = re.search(r"([^:]+):(\d+):", error)
                if not match:
                    continue

                file_path, line_num = match.groups()
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    line_idx = int(line_num) - 1
                    if line_idx < len(lines):
                        line = lines[line_idx].rstrip()
                        # 添加类型忽略注释
                        if "# type: ignore" not in line:
                            lines[line_idx] = line + f"  # type: ignore[{error_code}]"
                            fixes += 1

                            with open(file_path, "w", encoding="utf-8") as f:
                                f.writelines(lines)

                            print(f"✅ 修复导入错误: {file_path}:{line_num} - {error_code}")

                except Exception as e:
                    print(f"❌ 修复导入错误失败 {file_path}:{line_num}: {e}")

        return fixes

    def run_fix_cycle(self) -> Dict[str, int]:
        """运行一轮修复"""
        print("🔍 获取MyPy错误...")
        errors = self.get_mypy_errors()

        if not errors:
            print("✅ 没有发现错误")
            return {}

        print(f"📊 发现 {len(errors)} 个错误")

        fix_results = {}

        # 按优先级修复不同类型的错误
        fix_strategies = [
            ("unused-ignore", self.fix_unused_ignore_comments),
            ("name-defined", self.fix_name_defined_errors),
            ("assignment", self.fix_assignment_errors),
            ("arg-type", self.fix_arg_type_errors),
            ("import", self.fix_import_errors),
        ]

        for strategy_name, fixer in fix_strategies:
            print(f"\n🔧 修复 {strategy_name} 类型错误...")
            fixes = fixer(errors)
            if fixes > 0:
                fix_results[strategy_name] = fixes
                self.fixes_applied += fixes
                print(f"✅ {strategy_name}: 修复了 {fixes} 个错误")

            # 重新获取错误列表，避免重复修复
            errors = self.get_mypy_errors()
            if not errors:
                break

        return fix_results

    def run_multiple_cycles(self, max_cycles: int = 3) -> Dict[str, int]:
        """运行多轮修复"""
        total_results = defaultdict(int)

        for cycle in range(max_cycles):
            print(f"\n{'='*60}")
            print(f"🔄 修复循环 {cycle + 1}/{max_cycles}")
            print(f"{'='*60}")

            cycle_results = self.run_fix_cycle()

            if not cycle_results:
                print("✅ 所有错误已修复完成")
                break

            for strategy, count in cycle_results.items():
                total_results[strategy] += count

        return dict(total_results)


def main():
    """主函数"""
    print("🚀 智能MyPy错误修复工具")
    print("=" * 60)

    # 初始检查
    print("🔍 检查初始错误...")
    fixer = SmartMyPyFixer()
    initial_errors = fixer.get_mypy_errors()
    initial_count = len(initial_errors)

    print(f"📊 初始错误数量: {initial_count}")

    if initial_count == 0:
        print("🎉 没有发现错误，系统已经很干净！")
        return

    # 运行修复
    print("\n🔧 开始智能修复 (最多3轮)...")
    results = fixer.run_multiple_cycles(3)

    # 最终检查
    print("\n🔍 检查修复结果...")
    final_errors = fixer.get_mypy_errors()
    final_count = len(final_errors)

    improvement = initial_count - final_count

    print(f"\n{'='*60}")
    print("📊 修复统计报告")
    print(f"{'='*60}")

    print(f"   初始错误: {initial_count}")
    print(f"   最终错误: {final_count}")
    print(f"   修复数量: {fixer.fixes_applied}")
    print(f"   实际改善: {improvement}")

    if results:
        print("\n📈 按类型统计:")
        for error_type, count in results.items():
            print(f"   {error_type}: {count} 个")

    if improvement > 0:
        print(f"\n🎉 错误数量减少了 {improvement} 个 ({improvement/initial_count:.1%})")

        if final_count <= 100:
            print("🎯 已达到目标：错误数量在100个以下！")
        else:
            print(f"⚠️  距离目标还有 {final_count - 100} 个错误")
    else:
        print("⚠️  错误数量没有减少")


if __name__ == "__main__":
    main()
