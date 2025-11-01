#!/usr/bin/env python3
"""
针对性类型修复工具
专门处理高错误文件的优化修复
"""

import subprocess
import re
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any


class TargetedFixer:
    """针对性修复器"""

    def __init__(self, project_root: str = "/home/user/projects/FootballPrediction"):
        self.project_root = Path(project_root)
        self.reports_dir = self.project_root / "reports" / "quality"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def get_high_error_files(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取高错误文件列表"""
        try:
            result = subprocess.run(
                ["mypy", "src/", "--show-error-codes", "--no-error-summary"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            error_count = {}
            for line in result.stdout.strip().split("\n"):
                if ": error:" in line:
                    file_path = line.split(":")[0]
                    error_count[file_path] = error_count.get(file_path, 0) + 1

            # 过滤并排序
            filtered_files = []
            for file_path, count in error_count.items():
                # 只处理核心业务文件
                if any(
                    keyword in file_path
                    for keyword in [
                        "src/api/",
                        "src/core/",
                        "src/services/",
                        "src/utils/",
                        "src/repositories/",
                        "src/domain/",
                        "src/database/",
                    ]
                ):
                    # 避免错误过多或过少的文件
                    if 5 <= count <= 100:
                        filtered_files.append((file_path, count))

            # 按错误数量排序
            filtered_files.sort(key=lambda x: x[1], reverse=True)
            return filtered_files[:limit]

        except Exception as e:
            print(f"⚠️  分析失败: {e}")
            return []

    def fix_common_import_issues(self, content: str) -> Tuple[str, List[str]]:
        """修复常见的导入问题"""
        changes = []

        # 常见需要导入的类型
        needed_imports = {
            "Dict": "from typing import Dict",
            "List": "from typing import List",
            "Optional": "from typing import Optional",
            "Union": "from typing import Union",
            "Any": "from typing import Any",
            "Tuple": "from typing import Tuple",
            "Type": "from typing import Type",
            "TypeVar": "from typing import TypeVar",
            "Callable": "from typing import Callable",
            "TypeGuard": "from typing_extensions import TypeGuard",
        }

        # 检查内容中使用了哪些类型但没有导入
        missing_imports = set()
        for type_name, import_stmt in needed_imports.items():
            if type_name in content and import_stmt not in content:
                missing_imports.add(type_name)

        if missing_imports:
            # 检查是否已有typing导入
            if "from typing import" in content:
                # 扩展现有导入
                typing_import_match = re.search(r"from typing import ([^\n]+)", content)
                if typing_import_match:
                    current_imports = typing_import_match.group(1)
                    all_imports = set(name.strip() for name in current_imports.split(","))
                    all_imports.update(missing_imports)
                    new_import_line = f"from typing import {', '.join(sorted(all_imports))}"
                    content = content.replace(typing_import_match.group(0), new_import_line)
                    changes.append(f"扩展typing导入: {', '.join(missing_imports)}")
            else:
                # 添加新的导入行
                import_lines = []
                for type_name in sorted(missing_imports):
                    if needed_imports[type_name].startswith("from typing"):
                        import_lines.append(needed_imports[type_name])

                if import_lines:
                    # 在文件开头添加导入
                    lines = content.split("\n")
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.startswith("#") and not line.startswith('"""'):
                            insert_index = i
                            break

                    for import_line in reversed(import_lines):
                        lines.insert(insert_index, import_line)
                    content = "\n".join(lines)
                    changes.append(f"添加导入: {', '.join(missing_imports)}")

        return content, changes

    def fix_function_return_types(self, content: str) -> Tuple[str, List[str]]:
        """修复函数返回类型问题"""
        changes = []

        # 修复 "return None" 但返回类型不是Optional的情况
        return_none_pattern = r"(def\s+(\w+)\([^)]*\)\s*->\s*([^\n:]+):[\s\S]*?return\s+None)"
        matches = re.finditer(return_none_pattern, content, re.MULTILINE | re.DOTALL)

        for match in matches:
            func_name = match.group(2)
            return_type = match.group(3).strip()

            # 如果返回类型不包含Optional，添加Optional
            if "None" not in return_type and "Optional" not in return_type:
                fixed_type = f"Optional[{return_type}]"
                fixed_def = match.group(0).replace(f"-> {return_type}:", f"-> {fixed_type}:")
                content = content.replace(match.group(0), fixed_def)
                changes.append(f"修复 {func_name} 返回类型: {return_type} -> {fixed_type}")

        return content, changes

    def fix_dict_return_syntax(self, content: str) -> Tuple[str, List[str]]:
        """修复字典返回语法"""
        changes = []

        # 修复 "return Dict[str, Any]:" 语法错误
        wrong_dict_pattern = r"return\s+Dict\[str,\s*Any\]:\s*\n?\s*\{"
        matches = re.finditer(wrong_dict_pattern, content)

        for match in matches:
            fixed_return = match.group(0).replace("Dict[str, Any]:", "").replace("\n", "")
            content = content.replace(match.group(0), fixed_return)
            changes.append("修复字典返回语法")

        return content, changes

    def fix_attribute_errors(self, content: str) -> Tuple[str, List[str]]:
        """修复属性错误"""
        changes = []

        # 常见的属性错误修复
        common_fixes = {
            "self.config.get(": "self.config.get(",
            "self.settings.get(": "self.settings.get(",
            "response.json(": "response.json(",
            "result.json(": "result.json(",
        }

        for wrong, correct in common_fixes.items():
            if wrong in content and correct not in content:
                content = content.replace(wrong, correct)
                changes.append("修复常见属性访问")

        return content, changes

    def fix_variable_types(self, content: str) -> Tuple[str, List[str]]:
        """修复变量类型问题"""
        changes = []

        # 为未类型化的变量添加类型注解
        lines = content.split("\n")
        modified_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 查找简单的变量赋值
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^=]", stripped):
                # 跳过已经有类型注解的
                if ":" not in stripped.split("=")[0]:
                    # 跳过明显是简单类型的情况
                    if not any(x in stripped for x in ["True", "False", "None", '"', "'"]):
                        # 这里可以添加更智能的类型推断
                        # 目前先跳过，避免破坏性修改
                        pass

            modified_lines.append(line)

        return "\n".join(modified_lines), changes

    def fix_file(self, file_path: str) -> Tuple[bool, List[str], int]:
        """修复单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return False, [f"读取文件失败: {e}"], 0

        original_content = content
        all_changes = []

        # 应用各种修复策略
        content, changes = self.fix_common_import_issues(content)
        all_changes.extend(changes)

        content, changes = self.fix_function_return_types(content)
        all_changes.extend(changes)

        content, changes = self.fix_dict_return_syntax(content)
        all_changes.extend(changes)

        content, changes = self.fix_attribute_errors(content)
        all_changes.extend(changes)

        content, changes = self.fix_variable_types(content)
        all_changes.extend(changes)

        # 保存修复后的内容
        if content != original_content:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True, all_changes, len(all_changes)
            except Exception as e:
                return False, [f"保存文件失败: {e}"], 0
        else:
            return False, ["无需修复"], 0

    def run_targeted_fix(self) -> Dict[str, Any]:
        """运行针对性修复"""
        print("🎯 启动针对性类型修复...")
        print("=" * 50)

        # 获取高错误文件
        high_error_files = self.get_high_error_files()
        if not high_error_files:
            print("ℹ️  没有找到合适的高错误文件")
            return {"success": False, "message": "No suitable files found"}

        print(f"📋 目标文件 ({len(high_error_files)}个):")
        for i, (file_path, error_count) in enumerate(high_error_files, 1):
            short_path = file_path.replace("/home/user/projects/FootballPrediction/", "")
            print(f"  {i}. {short_path:<40} {error_count:3d} 个错误")

        print("\n🔄 开始针对性修复...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "files_processed": [],
            "total_files": len(high_error_files),
            "success_count": 0,
            "total_fixes": 0,
        }

        for file_path, original_errors in high_error_files:
            short_path = file_path.replace("/home/user/projects/FootballPrediction/", "")
            print(f"\n🔧 修复: {short_path} ({original_errors} 个错误)")

            success, changes, fix_count = self.fix_file(file_path)

            if success and fix_count > 0:
                # 验证修复效果
                new_errors = self._count_file_errors(file_path)
                improvement = original_errors - new_errors

                results["success_count"] += 1
                results["total_fixes"] += fix_count

                print(f"   ✅ 修复成功: {fix_count} 项")
                print(f"   📈 错误减少: {improvement} 个 ({original_errors} → {new_errors})")
                if changes:
                    print(f"   🔧 主要修复: {', '.join(changes[:3])}")

            elif changes:
                print(f"   ⚠️ 尝试修复但未改善: {'; '.join(changes[:2])}")
            else:
                print("   ℹ️ 无需修复")

            results["files_processed"].append(
                {
                    "file_path": file_path,
                    "original_errors": original_errors,
                    "fixes_applied": fix_count,
                    "changes": changes,
                    "success": success,
                }
            )

        # 保存报告
        report_file = (
            self.reports_dir
            / f"targeted_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("\n📊 针对性修复结果:")
        print(f"✅ 成功修复: {results['success_count']}/{results['total_files']} 个文件")
        print(f"🔧 总修复数: {results['total_fixes']} 项")
        print(f"💾 详细报告: {report_file}")

        return results

    def _count_file_errors(self, file_path: str) -> int:
        """统计文件错误数量"""
        try:
            result = subprocess.run(
                ["mypy", file_path, "--no-error-summary"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )
            error_lines = [line for line in result.stdout.split("\n") if ": error:" in line]
            return len(error_lines)
def main():
    """主函数"""
    fixer = TargetedFixer()
    results = fixer.run_targeted_fix()

    if results["success_count"] > 0:
        print("\n🎉 修复成功！建议运行质量检查验证效果")
        return 0
    else:
        print("\n💡 没有发现可自动修复的问题")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
