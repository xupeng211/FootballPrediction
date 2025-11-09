#!/usr/bin/env python3
"""
导入语句修复工具
专门处理E402和I001导入问题
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

class ImportStatementFixer:
    def __init__(self):
        self.files_fixed = 0
        self.errors_fixed = 0

    def get_files_with_import_issues(self) -> List[Tuple[str, int]]:
        """获取有导入问题的文件列表"""
        try:
            result = subprocess.run([
                "ruff", "check", "src/",
                "--output-format=concise",
                "--select=E402,I001"
            ], capture_output=True, text=True, timeout=30)

            error_files = {}
            for line in result.stdout.split('\n'):
                if line and ':' in line:
                    file_path = line.split(':')[0]
                    error_files[file_path] = error_files.get(file_path, 0) + 1

            # 按错误数量排序
            sorted_files = sorted(error_files.items(), key=lambda x: x[1], reverse=True)
            return sorted_files

        except Exception as e:
            print(f"获取导入问题文件列表失败: {e}")
            return []

    def fix_import_statements(self, file_path: str) -> Dict[str, int]:
        """修复单个文件的导入语句"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 1. 修复E402 - 模块级别导入不在文件顶部
            content = self._fix_e402_imports(content)

            # 2. 修复I001 - 导入语句排序和格式
            content = self._fix_i001_imports(content)

            # 3. 清理多余的空行
            content = self._cleanup_empty_lines(content)

            fixes_count = 1 if content != original_content else 0

            # 写入修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  ✅ 修复 {file_path}: 导入语句问题")
                self.errors_fixed += 1

            return {"import_fixes": fixes_count}

        except Exception as e:
            print(f"  ❌ 处理文件 {file_path} 时出错: {e}")
            return {"import_fixes": 0}

    def _fix_e402_imports(self, content: str) -> str:
        """修复E402 - 模块级别导入不在文件顶部"""
        lines = content.split('\n')
        imports = []
        other_lines = []
        in_import_section = True
        docstring_ended = False

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳过文档字符串
            if not docstring_ended:
                if '"""' in stripped or "'''" in stripped:
                    docstring_ended = True
                imports.append(line)
                i += 1
                continue

            # 处理导入语句
            if stripped.startswith(('import ', 'from ')):
                # 如果导入语句不在文件顶部，移动到顶部
                if not in_import_section:
                    # 检查是否可以安全移动
                    if self._is_safe_to_move_import(line, lines, i):
                        imports.append(line)
                    else:
                        in_import_section = False
                        other_lines.append(line)
                else:
                    imports.append(line)
            else:
                # 遇到非导入语句，导入部分结束
                if stripped and not stripped.startswith('#') and in_import_section:
                    in_import_section = False
                    # 添加空行分隔
                    if imports and imports[-1] != '':
                        imports.append('')
                other_lines.append(line)

            i += 1

        # 重新组合内容
        return '\n'.join(imports + other_lines)

    def _is_safe_to_move_import(self, line: str, all_lines: List[str], current_index: int) -> bool:
        """检查导入语句是否可以安全移动到文件顶部"""
        # 简单的安全性检查
        stripped = line.strip()

        # 如果是相对导入，可能不安全
        if stripped.startswith('from .'):
            return False

        # 如果涉及动态导入，不安全
        if 'importlib' in stripped or 'dynamic' in stripped.lower():
            return False

        # 检查前面是否有条件语句或函数定义
        for i in range(max(0, current_index - 5), current_index):
            prev_line = all_lines[i].strip()
            if prev_line.startswith(('if ', 'def ', 'class ', 'try:', 'except', 'finally', 'with ')):
                return False

        return True

    def _fix_i001_imports(self, content: str) -> str:
        """修复I001 - 导入语句排序和格式"""
        lines = content.split('\n')
        imports = []
        other_lines = []
        in_import_section = True

        for line in lines:
            stripped = line.strip()

            if stripped.startswith(('import ', 'from ')):
                imports.append(line)
            elif stripped == '' and in_import_section:
                imports.append(line)
            else:
                if stripped and in_import_section:
                    in_import_section = False
                other_lines.append(line)

        # 排序导入语句
        sorted_imports = self._sort_imports(imports)

        return '\n'.join(sorted_imports + other_lines)

    def _sort_imports(self, imports: List[str]) -> List[str]:
        """排序导入语句"""
        # 分离不同类型的导入
        std_lib_imports = []
        third_party_imports = []
        local_imports = []

        for imp in imports:
            stripped = imp.strip()
            if not stripped or stripped.startswith('#'):
                # 保留空行和注释
                continue

            if stripped.startswith('from .') or stripped.startswith('from src'):
                local_imports.append(imp)
            elif self._is_standard_library_import(stripped):
                std_lib_imports.append(imp)
            else:
                third_party_imports.append(imp)

        # 排序每类导入
        std_lib_imports.sort()
        third_party_imports.sort()
        local_imports.sort()

        # 重新组合
        sorted_imports = []

        if std_lib_imports:
            sorted_imports.extend(std_lib_imports)
            sorted_imports.append('')

        if third_party_imports:
            sorted_imports.extend(third_party_imports)
            sorted_imports.append('')

        if local_imports:
            sorted_imports.extend(local_imports)
            sorted_imports.append('')

        return sorted_imports

    def _is_standard_library_import(self, import_line: str) -> bool:
        """检查是否是标准库导入"""
        std_lib_modules = {
            'os', 'sys', 'time', 'datetime', 'json', 're', 'pathlib',
            'typing', 'collections', 'itertools', 'functools', 'operator',
            'logging', 'threading', 'asyncio', 'subprocess', 'urllib',
            'http', 'email', 'xml', 'sqlite3', 'hashlib', 'hmac',
            'base64', 'uuid', 'random', 'math', 'statistics', 'decimal',
            'fractions', 'enum', 'dataclasses', 'contextlib', 'weakref',
            'copy', 'pickle', 'struct', 'array', 'bisect', 'heapq',
            'queue', 'multiprocessing', 'concurrent', 'socket',
            'ssl', 'select', 'selectors', 'signal', 'shutil', 'tempfile',
            'glob', 'fnmatch', 'linecache', 'shlex', 'platform',
            'errno', 'stat', 'filecmp', 'fileinput', 'io', 'stringio',
            'traceback', 'types', 'gc', 'inspect', 'importlib',
            'pkgutil', 'modulefinder', 'runpy', 'parser', 'token',
            'keyword', 'tokenize', 'tabnanny', 'pyclbr', 'py_compile',
            'compileall', 'dis', 'pickletools', 'zipapp', 'site',
            'user', 'this', 'antigravity', '__future__'
        }

        # 提取模块名
        if import_line.startswith('import '):
            module_name = import_line.replace('import ', '').split('.')[0].split(' as ')[0]
        elif import_line.startswith('from '):
            module_name = import_line.replace('from ', '').split(' import')[0].split('.')[0]
        else:
            return False

        return module_name in std_lib_modules

    def _cleanup_empty_lines(self, content: str) -> str:
        """清理多余的空行"""
        lines = content.split('\n')
        cleaned_lines = []
        empty_line_count = 0

        for line in lines:
            if line.strip() == '':
                empty_line_count += 1
                # 最多保留2个连续空行
                if empty_line_count <= 2:
                    cleaned_lines.append(line)
            else:
                empty_line_count = 0
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def batch_fix_import_statements(self, limit: int = 20):
        """批量修复导入语句"""
        print("🔧 导入语句修复工具")
        print("=" * 50)
        print("🎯 专门处理E402和I001导入问题")

        # 获取有导入问题的文件
        problem_files = self.get_files_with_import_issues()
        if not problem_files:
            print("📊 没有发现导入语句问题")
            return

        print(f"📋 发现 {len(problem_files)} 个有导入问题的文件")

        # 显示前10个问题最多的文件
        print(f"\n📊 导入问题最多的文件 (前10个):")
        for file_path, error_count in problem_files[:10]:
            print(f"  - {file_path}: {error_count} 个问题")

        # 获取当前的E402和I001错误数量
        initial_errors = self.get_current_import_errors()
        print(f"\n📊 当前导入错误数: {initial_errors}")

        # 处理文件
        files_to_process = problem_files[:limit]
        print(f"\n🔧 开始处理前 {len(files_to_process)} 个文件...")

        for file_path, error_count in files_to_process:
            if Path(file_path).exists():
                print(f"\n🔧 处理文件: {file_path} (预计 {error_count} 个问题)")
                result = self.fix_import_statements(file_path)
                self.files_fixed += 1
            else:
                print(f"  ⚠️ 文件不存在: {file_path}")

        # 验证修复效果
        final_errors = self.get_current_import_errors()
        improvement = initial_errors - final_errors

        print(f"\n📊 修复结果:")
        print(f"  🔧 处理文件数: {self.files_fixed}")
        print(f"  ✅ 导入错误改善: {improvement} 个")
        print(f"  📈 初始错误: {initial_errors}")
        print(f"  📉 修复后错误: {final_errors}")

        if improvement > 0:
            print(f"\n🎉 导入语句优化成功! 减少了 {improvement} 个导入错误")
        else:
            print(f"\n⚠️ 导入语句改善有限，可能需要手动处理")

    def get_current_import_errors(self) -> int:
        """获取当前导入错误数量"""
        try:
            result = subprocess.run([
                "ruff", "check", "src/",
                "--output-format=concise",
                "--select=E402,I001"
            ], capture_output=True, text=True, timeout=30)

            return len([line for line in result.stdout.split('\n') if line.strip()])
        except:
            return -1

def main():
    """主函数"""
    fixer = ImportStatementFixer()
    fixer.batch_fix_import_statements(20)

if __name__ == "__main__":
    main()