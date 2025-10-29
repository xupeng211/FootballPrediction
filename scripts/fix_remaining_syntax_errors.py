#!/usr/bin/env python3
"""
修复剩余语法错误脚本 - Issue #84完成
专门处理深层缩进问题和语法错误
"""

import os
import ast
import sys
from pathlib import Path
from typing import List, Tuple


class SyntaxErrorFixer:
    def __init__(self):
        self.fixed_files = []
        self.errors_files = []

    def find_syntax_error_files(self) -> List[Path]:
        """查找所有有语法错误的测试文件"""
        error_files = []
        tests_dir = Path("tests")

        if not tests_dir.exists():
            print("❌ tests目录不存在")
            return error_files

        print("🔍 检查语法错误...")

        for test_file in tests_dir.rglob("*.py"):
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 尝试编译AST
                ast.parse(content)
            except SyntaxError as e:
                error_files.append((test_file, str(e)))
                self.errors_files.append((test_file, str(e)))
            except Exception as e:
                print(f"⚠️ 文件 {test_file} 读取失败: {e}")

        print(f"📊 发现 {len(error_files)} 个语法错误文件")
        return error_files

    def fix_indentation_errors(self) -> int:
        """修复缩进错误"""
        fixed_count = 0

        for file_path, error_msg in self.errors_files:
            if "IndentationError" in error_msg or "unexpected indent" in error_msg:
                print(f"🔧 修复缩进错误: {file_path}")

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    lines = content.split("\n")
                    fixed_lines = []

                    for i, line in enumerate(lines):
                        # 检测并修复常见的缩进问题
                        if line.strip() and not line.startswith("#"):
                            # 计算当前缩进
                            current_indent = len(line) - len(line.lstrip())

                            # 修复第10行附近的问题
                            if i == 9:  # 第10行（0-based index）
                                if current_indent >= 8 and not line.strip().startswith("def "):
                                    # 可能是过大的缩进，减少到4个空格
                                    fixed_line = "    " + line.lstrip()
                                    fixed_lines.append(fixed_line)
                                else:
                                    fixed_lines.append(line)
                            else:
                                fixed_lines.append(line)
                        else:
                            fixed_lines.append(line)

                    # 写回文件
                    fixed_content = "\n".join(fixed_lines)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

                    self.fixed_files.append(file_path)
                    fixed_count += 1
                    print(f"  ✅ 已修复: {file_path}")

                except Exception as e:
                    print(f"  ❌ 修复失败: {file_path} - {e}")

        return fixed_count

    def fix_prediction_algorithm_tests(self) -> int:
        """修复预测算法测试文件的缩进问题"""
        fixed_count = 0

        # 查找特定的预测算法测试文件
        pattern_files = [
            "tests/unit/test_prediction_algorithms_part_2.py",
            "tests/unit/test_prediction_algorithms_part_3.py",
            "tests/unit/test_prediction_algorithms_part_4.py",
            "tests/unit/test_prediction_algorithms_part_5.py",
        ]

        for file_pattern in pattern_files:
            file_path = Path(file_pattern)
            if file_path.exists():
                print(f"🔧 修复预测算法测试: {file_path}")

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    lines = content.split("\n")
                    fixed_lines = []

                    for i, line in enumerate(lines):
                        # 修复第7行附近的缩进问题
                        if i == 6:  # 第7行（0-based index）
                            if line.strip() and not line.startswith("#"):
                                # 确保正确的缩进
                                if line.strip().startswith("def ") or line.strip().startswith(
                                    "class "
                                ):
                                    fixed_line = line  # 保持原缩进
                                else:
                                    # 其他内容减少缩进
                                    fixed_line = "    " + line.lstrip()
                                fixed_lines.append(fixed_line)
                            else:
                                fixed_lines.append(line)
                        else:
                            fixed_lines.append(line)

                    # 写回文件
                    fixed_content = "\n".join(fixed_lines)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

                    self.fixed_files.append(file_path)
                    fixed_count += 1
                    print(f"  ✅ 已修复: {file_path}")

                except Exception as e:
                    print(f"  ❌ 修复失败: {file_path} - {e}")

        return fixed_count

    def fix_phase3_tests(self) -> int:
        """修复phase3测试文件的缩进问题"""
        fixed_count = 0

        # 查找所有phase3测试文件
        for file_path, error_msg in self.errors_files:
            if "phase3" in str(file_path).lower():
                print(f"🔧 修复Phase3测试: {file_path}")

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    lines = content.split("\n")
                    fixed_lines = []

                    for i, line in enumerate(lines):
                        # 修复第10行附近的缩进问题
                        if i == 9:  # 第10行（0-based index）
                            if line.strip() and not line.startswith("#"):
                                # 确保正确的缩进级别
                                stripped = line.lstrip()
                                if stripped.startswith(("def ", "class ", "@")):
                                    fixed_line = "    " + stripped  # 4空格缩进
                                else:
                                    fixed_line = "        " + stripped  # 8空格缩进
                                fixed_lines.append(fixed_line)
                            else:
                                fixed_lines.append(line)
                        else:
                            fixed_lines.append(line)

                    # 写回文件
                    fixed_content = "\n".join(fixed_lines)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

                    self.fixed_files.append(file_path)
                    fixed_count += 1
                    print(f"  ✅ 已修复: {file_path}")

                except Exception as e:
                    print(f"  ❌ 修复失败: {file_path} - {e}")

        return fixed_count

    def validate_fixes(self) -> bool:
        """验证修复结果"""
        print("\n🧪 验证修复结果...")

        remaining_errors = 0
        total_files = 0

        for root, dirs, files in os.walk("tests"):
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    total_files += 1

                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        ast.parse(content)
                    except SyntaxError:
                        remaining_errors += 1
                        print(f"  ❌ 仍有语法错误: {file_path}")
                    except Exception:
                        pass

        success_rate = (
            ((total_files - remaining_errors) / total_files * 100) if total_files > 0 else 0
        )

        print("\n📊 修复验证结果:")
        print(f"  总文件数: {total_files}")
        print(f"  成功修复: {len(self.fixed_files)}")
        print(f"  剩余错误: {remaining_errors}")
        print(f"  成功率: {success_rate:.2f}%")

        return remaining_errors == 0

    def generate_report(self):
        """生成修复报告"""
        report = {
            "fix_time": "2025-10-26",
            "issue_number": 84,
            "fixed_files": [str(f) for f in self.fixed_files],
            "error_files": [(str(f), e) for f, e in self.errors_files],
            "total_fixed": len(self.fixed_files),
            "total_errors": len(self.errors_files),
        }

        report_file = Path("syntax_error_fix_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            import json

            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📋 修复报告已保存: {report_file}")
        return report

    def run_complete_fix(self):
        """运行完整的修复流程"""
        print("🚀 开始修复剩余语法错误...")
        print("=" * 60)

        # 1. 查找语法错误文件
        error_files = self.find_syntax_error_files()

        if not error_files:
            print("✅ 没有发现语法错误文件")
            return True

        # 2. 执行不同类型的修复
        print(f"\n🔧 开始修复 {len(error_files)} 个文件...")

        fixed_indent = self.fix_indentation_errors()
        fixed_prediction = self.fix_prediction_algorithm_tests()
        fixed_phase3 = self.fix_phase3_tests()

        total_fixed = fixed_indent + fixed_prediction + fixed_phase3

        print("\n📊 修复统计:")
        print(f"  缩进错误修复: {fixed_indent} 个")
        print(f"  预测算法测试修复: {fixed_prediction} 个")
        print(f"  Phase3测试修复: {fixed_phase3} 个")
        print(f"  总计修复: {total_fixed} 个")

        # 3. 验证修复结果
        success = self.validate_fixes()

        # 4. 生成报告
        self.generate_report()

        print("\n🎉 语法错误修复完成!")
        print(f"{'✅ 全部成功' if success else '⚠️ 部分成功'}")
        print(f"修复文件数: {total_fixed}")
        print(f"验证结果: {'通过' if success else '需要进一步处理'}")

        return success


def main():
    """主函数"""
    fixer = SyntaxErrorFixer()
    success = fixer.run_complete_fix()

    if success:
        print("\n🎯 Issue #84 可以标记为完成!")
        print("建议更新GitHub issue状态。")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
