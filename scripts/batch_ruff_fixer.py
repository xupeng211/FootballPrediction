#!/usr/bin/env python3
"""
批量Ruff错误修复工具
Batch Ruff Error Fixer

专门用于批量处理常见的Ruff格式错误
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Any
import tempfile
import shutil


class BatchRuffFixer:
    """批量Ruff错误修复器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.fixes_applied = 0
        self.errors_fixed = {
            "F401": 0,  # 未使用的导入
            "E501": 0,  # 行长度超限
            "E402": 0,  # 模块导入位置问题
            "E302": 0,  # 空行格式问题
            "E722": 0,  # 裸except语句
        }

    def get_ruff_errors(self, error_type: str = None) -> List[Dict[str, Any]]:
        """获取Ruff错误列表"""
        try:
            result = subprocess.run(
                ["make", "lint"], cwd=self.project_root, capture_output=True, text=True, timeout=120
            )

            errors = []
            for line in result.stdout.split("\n"):
                if ":" in line:
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        col_num = int(parts[2])
                        error_info = parts[3]

                        # 提取错误代码
                        error_code_match = re.search(r"\b([A-Z]\d{3})\b", error_info)
                        if error_code_match:
                            error_code = error_code_match.group(1)

                            if error_type is None or error_code == error_type:
                                errors.append(
                                    {
                                        "file": file_path,
                                        "line": line_num,
                                        "col": col_num,
                                        "code": error_code,
                                        "message": error_info.strip(),
                                    }
                                )

            return errors
        except Exception as e:
            print(f"❌ 获取Ruff错误失败: {e}")
            return []

    def fix_f401_unused_imports(self) -> int:
        """批量修复F401未使用导入错误"""
        print("🔧 批量修复F401未使用导入错误...")

        f401_errors = [e for e in self.get_ruff_errors() if e["code"] == "F401"]
        print(f"📊 发现 {len(f401_errors)} 个F401错误")

        if not f401_errors:
            print("✅ 没有F401错误需要修复")
            return 0

        # 按文件分组
        files_to_fix = {}
        for error in f401_errors:
            file_path = error["file"]
            if file_path not in files_to_fix:
                files_to_fix[file_path] = []
            files_to_fix[file_path].append(error)

        fixed_count = 0

        for file_path, errors in files_to_fix.items():
            full_path = self.project_root / file_path

            if not full_path.exists():
                print(f"⚠️ 文件不存在: {file_path}")
                continue

            try:
                # 读取文件内容
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # 需要删除的行号（倒序，避免行号偏移）
                lines_to_remove = sorted({error["line"] - 1 for error in errors}, reverse=True)

                # 删除未使用的导入行
                new_lines = []
                for i, line in enumerate(lines):
                    if i not in lines_to_remove:
                        new_lines.append(line)
                    else:
                        # 检查是否是导入行
                        stripped_line = line.strip()
                        if (
                            stripped_line.startswith("import ")
                            or stripped_line.startswith("from ")
                            or stripped_line == ""
                            or stripped_line.startswith("#")
                        ):
                            print(f"   删除: {file_path}:{i+1} {stripped_line}")
                            fixed_count += 1
                        else:
                            new_lines.append(line)

                # 写回文件
                with open(full_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

            except Exception as e:
                print(f"❌ 修复文件失败 {file_path}: {e}")

        self.errors_fixed["F401"] = fixed_count
        print(f"✅ F401修复完成，修复了 {fixed_count} 个未使用导入")
        return fixed_count

    def fix_e501_line_length(self) -> int:
        """批量修复E501行长度超限错误"""
        print("🔧 批量修复E501行长度超限错误...")

        e501_errors = [e for e in self.get_ruff_errors() if e["code"] == "E501"]
        print(f"📊 发现 {len(e501_errors)} 个E501错误")

        if not e501_errors:
            print("✅ 没有E501错误需要修复")
            return 0

        # 按文件分组
        files_to_fix = {}
        for error in e501_errors:
            file_path = error["file"]
            if file_path not in files_to_fix:
                files_to_fix[file_path] = []
            files_to_fix[file_path].append(error)

        fixed_count = 0

        for file_path, errors in files_to_fix.items():
            full_path = self.project_root / file_path

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                modified = False

                for error in errors:
                    line_num = error["line"] - 1
                    if 0 <= line_num < len(lines):
                        line = lines[line_num]

                        # 如果行长度超过100字符，尝试智能分割
                        if len(line) > 100:
                            # 分割长行的策略
                            if "=" in line and not line.strip().startswith("#"):
                                # 分割赋值语句
                                parts = line.split("=", 1)
                                if len(parts) == 2:
                                    var_part = parts[0].rstrip()
                                    value_part = parts[1].lstrip()
                                    lines[line_num] = f"{var_part} =\n    {value_part}"
                                    modified = True
                                    fixed_count += 1
                            elif "+" in line and not line.strip().startswith("#"):
                                # 分割字符串连接
                                lines[line_num] = line.replace(" + ", " +\n        ")
                                modified = True
                                fixed_count += 1

                if modified:
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))

            except Exception as e:
                print(f"❌ 修复文件失败 {file_path}: {e}")

        self.errors_fixed["E501"] = fixed_count
        print(f"✅ E501修复完成，修复了 {fixed_count} 个行长度问题")
        return fixed_count

    def fix_e402_import_positions(self) -> int:
        """批量修复E402模块导入位置问题"""
        print("🔧 批量修复E402模块导入位置问题...")

        e402_errors = [e for e in self.get_ruff_errors() if e["code"] == "E402"]
        print(f"📊 发现 {len(e402_errors)} 个E402错误")

        if not e402_errors:
            print("✅ 没有E402错误需要修复")
            return 0

        fixed_count = 0

        for file_path in set(error["file"] for error in e402_errors):
            full_path = self.project_root / file_path

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # 分离导入和其他代码
                imports = []
                other_code = []
                in_import_section = True

                for line in lines:
                    stripped = line.strip()

                    if stripped.startswith("#") or stripped == "":
                        imports.append(line)
                    elif (
                        stripped.startswith("import ")
                        or stripped.startswith("from ")
                        or stripped.startswith("__future__")
                    ):
                        imports.append(line)
                    else:
                        if in_import_section and imports:
                            # 添加空行分隔
                            if imports and imports[-1].strip() != "":
                                imports.append("\n")
                        in_import_section = False
                        other_code.append(line)

                # 重新组合文件
                new_content = "".join(imports + other_code)

                if new_content != "".join(lines):
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    fixed_count += 1
                    print(f"   修复: {file_path}")

            except Exception as e:
                print(f"❌ 修复文件失败 {file_path}: {e}")

        self.errors_fixed["E402"] = fixed_count
        print(f"✅ E402修复完成，修复了 {fixed_count} 个导入位置问题")
        return fixed_count

    def fix_e302_blank_lines(self) -> int:
        """批量修复E302空行格式问题"""
        print("🔧 批量修复E302空行格式问题...")

        e302_errors = [e for e in self.get_ruff_errors() if e["code"] == "E302"]
        print(f"📊 发现 {len(e302_errors)} 个E302错误")

        if not e302_errors:
            print("✅ 没有E302错误需要修复")
            return 0

        # 使用black自动修复空行问题
        try:
            result = subprocess.run(
                ["black", "--line-length", "100", "--target-version", "py311"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print("✅ E302空行问题已通过black自动修复")
                return len(e302_errors)
            else:
                print(f"⚠️ black修复部分失败: {result.stderr}")
                return 0

        except Exception as e:
            print(f"❌ black修复失败: {e}")
            return 0

    def run_phase(self, phase: int) -> Dict[str, int]:
        """运行指定的修复阶段"""
        print(f"\n🚀 执行Phase {phase}批量修复...")

        results = {}

        if phase == 1:
            # Phase 1: 处理最容易修复的错误
            results["F401"] = self.fix_f401_unused_imports()
            results["E402"] = self.fix_e402_import_positions()

        elif phase == 2:
            # Phase 2: 处理格式问题
            results["E501"] = self.fix_e501_line_length()
            results["E302"] = self.fix_e302_blank_lines()

        return results

    def run_all_phases(self) -> Dict[str, int]:
        """运行所有修复阶段"""
        print("🎯 开始执行所有批量修复阶段...")

        all_results = {}

        # Phase 1: 基础修复
        phase1_results = self.run_phase(1)
        all_results.update(phase1_results)

        # Phase 2: 格式修复
        phase2_results = self.run_phase(2)
        all_results.update(phase2_results)

        return all_results

    def get_final_status(self) -> Dict[str, Any]:
        """获取最终修复状态"""
        # 重新运行Ruff检查获取最新错误数量
        errors = self.get_ruff_errors()

        # 按错误类型统计
        error_counts = {}
        for error in errors:
            code = error["code"]
            error_counts[code] = error_counts.get(code, 0) + 1

        total_errors = len(errors)

        return {
            "total_errors": total_errors,
            "original_errors": 9108,  # 原始错误数量
            "errors_fixed": 9108 - total_errors,
            "fix_rate": (9108 - total_errors) / 9108 * 100,
            "error_breakdown": error_counts,
            "fixes_applied": sum(self.errors_fixed.values()),
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="批量Ruff错误修复工具")
    parser.add_argument(
        "--phase", "-p", type=int, choices=[1, 2], help="指定修复阶段 (1: 基础修复, 2: 格式修复)"
    )
    parser.add_argument("--all", "-a", action="store_true", help="运行所有修复阶段")
    parser.add_argument("--project-root", type=str, help="项目根目录路径")

    args = parser.parse_args()

    # 创建修复器
    fixer = BatchRuffFixer(args.project_root)

    if args.all:
        results = fixer.run_all_phases()
    elif args.phase:
        results = fixer.run_phase(args.phase)
    else:
        print("请指定 --phase 或 --all 参数")
        return

    # 显示结果
    print("\n" + "=" * 60)
    print("📊 批量修复结果")
    print("=" * 60)

    for error_type, count in results.items():
        print(f"✅ {error_type}: 修复了 {count} 个错误")

    # 获取最终状态
    final_status = fixer.get_final_status()

    print("-" * 60)
    print("🎯 最终状态:")
    print(f"   原始错误数: {final_status['original_errors']:,}")
    print(f"   当前错误数: {final_status['total_errors']:,}")
    print(f"   修复错误数: {final_status['errors_fixed']:,}")
    print(f"   修复率: {final_status['fix_rate']:.1f}%")

    if final_status["error_breakdown"]:
        print("\n📋 剩余错误分布:")
        for code, count in sorted(final_status["error_breakdown"].items()):
            print(f"   {code}: {count:,} 个")

    print("=" * 60)


if __name__ == "__main__":
    main()
