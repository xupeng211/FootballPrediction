#!/usr/bin/env python3
"""
紧急代码质量修复工具
Emergency Code Quality Fixer

快速修复关键的未定义名称和导入错误，确保代码可正常运行。
"""

import re
import subprocess
from pathlib import Path


class EmergencyQualityFixer:
    """紧急代码质量修复器"""

    def __init__(self, source_dir: str = "src"):
        self.source_dir = Path(source_dir)
        self.fix_count = 0
        self.error_files = {}

    def find_files_with_errors(self) -> list[Path]:
        """查找有错误的文件"""
        try:
            # 使用ruff检查F821错误
            result = subprocess.run(
                ["ruff", "check", str(self.source_dir), "--select=F821", "--output-format=text"],
                capture_output=True,
                text=True,
                timeout=60
            )

            error_files = set()
            for line in result.stdout.split('\n'):
                if ':' in line and 'F821' in line:
                    file_path = line.split(':')[0]
                    if Path(file_path).exists():
                        error_files.add(Path(file_path))

            return list(error_files)

        except Exception as e:
            print(f"错误检查失败: {e}")
            return []

    def analyze_missing_imports(self, file_path: Path) -> set[str]:
        """分析缺失的导入"""
        try:
            result = subprocess.run(
                ["ruff", "check", str(file_path), "--select=F821", "--output-format=text"],
                capture_output=True,
                text=True,
                timeout=30
            )

            missing_names = set()
            for line in result.stdout.split('\n'):
                if 'F821' in line and 'Undefined name' in line:
                    # 提取未定义的名称
                    match = re.search(r'`([^`]+)`', line)
                    if match:
                        missing_names.add(match.group(1))

            return missing_names

        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")
            return set()

    def fix_file_imports(self, file_path: Path) -> bool:
        """修复文件的导入问题"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # 分析缺失的导入
            missing_names = self.analyze_missing_imports(file_path)
            if not missing_names:
                return True

            # 生成需要的导入语句
            imports_to_add = []
            for name in missing_names:
                if name in ['APIRouter', 'Depends', 'HTTPException', 'Query', 'BackgroundTasks']:
                    imports_to_add.append(f"from fastapi import {name}")
                elif name in ['Dict', 'List', 'Optional', 'Any', 'Union', 'Callable']:
                    imports_to_add.append(f"from typing import {name}")
                elif name in ['datetime', 'os', 'sys', 'json', 're', 'pathlib']:
                    imports_to_add.append(f"import {name}")
                elif name == 'e':
                    # 这是一个异常变量，需要检查上下文
                    continue
                else:
                    # 其他可能的导入
                    imports_to_add.append(f"# TODO: 需要导入 {name}")

            if not imports_to_add:
                return True

            # 找到插入位置（文件开头，在文档字符串之后）
            lines = content.split('\n')
            insert_index = 0

            # 跳过文件开头的注释和文档字符串
            for i, line in enumerate(lines):
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    # 找到文档字符串结束
                    quote_type = line.strip()[:3]
                    for j in range(i + 1, len(lines)):
                        if quote_type in lines[j]:
                            insert_index = j + 1
                            break
                    break
                elif line.strip().startswith('import') or line.strip().startswith('from'):
                    # 找到现有导入的结束位置
                    for j in range(i, len(lines)):
                        if not (lines[j].strip().startswith('import') or
                               lines[j].strip().startswith('from') or
                               lines[j].strip() == '' or
                               lines[j].strip().startswith('#')):
                            insert_index = j
                            break
                    break
            else:
                insert_index = 0

            # 插入新的导入语句
            for import_stmt in reversed(imports_to_add):
                lines.insert(insert_index, import_stmt)

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print(f"✅ 修复文件: {file_path} (添加了 {len(imports_to_add)} 个导入)")
            self.fix_count += 1
            return True

        except Exception as e:
            print(f"❌ 修复文件失败 {file_path}: {e}")
            return False

    def fix_fastapi_specific_issues(self, file_path: Path) -> bool:
        """修复FastAPI特定的导入问题"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 检查是否使用了FastAPI相关的类型但缺少导入
            fastapi_patterns = [
                (r'\bAPIRouter\b', 'from fastapi import APIRouter'),
                (r'\bDepends\b', 'from fastapi import Depends'),
                (r'\bHTTPException\b', 'from fastapi import HTTPException'),
                (r'\bQuery\b', 'from fastapi import Query'),
                (r'\bBackgroundTasks\b', 'from fastapi import BackgroundTasks'),
                (r'\bStatusCodes\b', 'from fastapi import status'),
                (r'\bRequest\b', 'from fastapi import Request'),
                (r'\bResponse\b', 'from fastapi import Response'),
            ]

            lines = content.split('\n')
            imports_needed = set()

            # 检查是否需要这些导入
            for pattern, import_stmt in fastapi_patterns:
                if re.search(pattern, content) and import_stmt not in content:
                    imports_needed.add(import_stmt)

            if imports_needed:
                # 找到合适的插入位置
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('from fastapi import'):
                        # 已有FastAPI导入，合并到同一行
                        fastapi_imports = line.strip()
                        for import_stmt in imports_needed:
                            if import_stmt not in fastapi_imports:
                                fastapi_imports += f", {import_stmt.split('import ')[1]}"
                        lines[i] = fastapi_imports
                        imports_needed.clear()
                        break
                    elif line.strip().startswith('import') and 'fastapi' not in line:
                        insert_index = i
                        break
                else:
                    # 在文件开头插入
                    insert_index = 0

                # 插入新的导入
                for import_stmt in sorted(imports_needed):
                    lines.insert(insert_index, import_stmt)
                    insert_index += 1

                content = '\n'.join(lines)

            # 检查是否需要typing导入
            typing_patterns = [
                (r'\bDict\b', 'from typing import Dict'),
                (r'\bList\b', 'from typing import List'),
                (r'\bOptional\b', 'from typing import Optional'),
                (r'\bAny\b', 'from typing import Any'),
                (r'\bUnion\b', 'from typing import Union'),
                (r'\bCallable\b', 'from typing import Callable'),
            ]

            for pattern, import_stmt in typing_patterns:
                if re.search(pattern, content) and import_stmt not in content:
                    if 'from typing import' in content:
                        # 合并到现有typing导入
                        for i, line in enumerate(lines):
                            if line.strip().startswith('from typing import'):
                                lines[i] = line.strip() + f", {import_stmt.split('import ')[1]}"
                                break
                    else:
                        # 添加新的typing导入
                        for i, line in enumerate(lines):
                            if line.strip().startswith('import') and 'typing' not in line:
                                lines.insert(i, import_stmt)
                                break
                        else:
                            lines.insert(0, import_stmt)

            content = '\n'.join(lines)

            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ 修复FastAPI导入: {file_path}")
                self.fix_count += 1
                return True

            return True

        except Exception as e:
            print(f"❌ 修复FastAPI导入失败 {file_path}: {e}")
            return False

    def run_emergency_fix(self) -> dict:
        """运行紧急修复"""
        print("🚨 开始紧急代码质量修复...")

        # 查找有错误的文件
        error_files = self.find_files_with_errors()
        print(f"📊 发现 {len(error_files)} 个文件有错误")

        if not error_files:
            print("✅ 没有发现需要修复的错误")
            return {"fixed_files": 0, "total_files": 0}

        # 逐个修复文件
        fixed_count = 0
        for file_path in error_files:
            print(f"\n🔧 修复文件: {file_path}")

            # 修复FastAPI特定问题
            if self.fix_fastapi_specific_issues(file_path):
                fixed_count += 1

        print("\n📊 修复完成:")
        print(f"  修复文件数: {fixed_count}/{len(error_files)}")
        print(f"  总修复操作: {self.fix_count}")

        return {
            "fixed_files": fixed_count,
            "total_files": len(error_files),
            "total_fixes": self.fix_count
        }

    def verify_fixes(self) -> bool:
        """验证修复结果"""
        print("\n🔍 验证修复结果...")

        try:
            result = subprocess.run(
                ["ruff", "check", str(self.source_dir), "--select=F821", "--output-format=text"],
                capture_output=True,
                text=True,
                timeout=60
            )

            remaining_errors = len([line for line in result.stdout.split('\n') if 'F821' in line])

            if remaining_errors == 0:
                print("✅ 所有F821错误已修复!")
                return True
            else:
                print(f"⚠️  还有 {remaining_errors} 个F821错误需要处理")
                return False

        except Exception as e:
            print(f"❌ 验证失败: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="紧急代码质量修复")
    parser.add_argument(
        "--source-dir",
        default="src",
        help="源代码目录 (默认: src)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证，不修复"
    )

    args = parser.parse_args()

    fixer = EmergencyQualityFixer(args.source_dir)

    if args.verify_only:
        fixer.verify_fixes()
    else:
        # 运行修复
        result = fixer.run_emergency_fix()

        # 验证结果
        success = fixer.verify_fixes()

        if success:
            print("\n🎉 紧急修复完成!")
            print("💡 建议运行: ruff check src/ --fix 来修复其他格式问题")
        else:
            print("\n⚠️ 部分问题未能自动修复，建议手动检查")


if __name__ == "__main__":
    main()
