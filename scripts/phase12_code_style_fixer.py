#!/usr/bin/env python3
"""
Phase 12 代码风格错误修复工具
专门处理E402导入顺序和I001导入格式问题
"""

import os
import re
import subprocess
from pathlib import Path


class CodeStyleFixer:
    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.errors_fixed = 0

    def fix_import_order_issues(self, file_path: str) -> dict[str, int]:
        """修复导入顺序问题 (E402)"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 备份原文件
            backup_path = file_path + '.style_backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            lines = content.split('\n')
            imports_section = []
            other_code = []
            in_imports_section = False

            # 分离导入语句和其他代码
            for line in lines:
                stripped = line.strip()

                # 检测是否是导入语句
                if (stripped.startswith('import ') or
                    stripped.startswith('from ') or
                    stripped.startswith('#') or
                    stripped == '' or
                    stripped.startswith('"""') or
                    stripped.startswith("'''")):

                    if stripped.startswith('import ') or stripped.startswith('from '):
                        in_imports_section = True

                    imports_section.append(line)
                else:
                    if in_imports_section and not stripped.startswith('#'):
                        # 导入部分结束，开始其他代码
                        in_imports_section = False
                        other_code.append(line)
                    else:
                        other_code.append(line)

            # 处理导入部分：移动import语句到顶部
            imports_only = []
            other_imports = []

            for line in imports_section:
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    imports_only.append(line)
                else:
                    other_imports.append(line)

            # 合并：标准导入 + 其他导入 + 其他代码
            final_lines = imports_only + other_imports + other_code

            # 写入修复后的内容
            fixed_content = '\n'.join(final_lines)

            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                fixes_count = len([line for line in imports_only if line.strip()])

            return {"import_fixes": fixes_count}

        except Exception:
            return {"import_fixes": 0}

    def fix_import_format_issues(self, file_path: str) -> dict[str, int]:
        """修复导入格式问题 (I001)"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 备份原文件
            backup_path = file_path + '.format_backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            lines = content.split('\n')
            fixed_lines = []

            for line in lines:
                # 修复导入格式
                fixed_line = line

                # 规范化空格
                if line.strip().startswith('import '):
                    # import os, sys -> import os, sys
                    fixed_line = re.sub(r'import\s+', 'import ', line)

                elif line.strip().startswith('from '):
                    # from module import item -> from module import item
                    fixed_line = re.sub(r'from\s+', 'from ', line)

                # 修复多余的分号
                fixed_line = re.sub(r';\s*$', '', fixed_line)

                # 修复尾随空格
                fixed_line = fixed_line.rstrip()

                if fixed_line != line:
                    fixes_count += 1

                fixed_lines.append(fixed_line)

            # 写入修复后的内容
            fixed_content = '\n'.join(fixed_lines)

            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)


            return {"format_fixes": fixes_count}

        except Exception:
            return {"format_fixes": 0}

    def fix_naming_conventions(self, file_path: str) -> dict[str, int]:
        """修复命名约定问题"""
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            original_content = content
            fixes_count = 0

            # 备份原文件
            backup_path = file_path + '.naming_backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            lines = content.split('\n')
            fixed_lines = []

            for line in lines:
                # 修复类名 (应该是CapWords)
                fixed_line = re.sub(r'class\s+([a-z][a-zA-Z0-9_]*)_', r'class \1', line)

                # 修复变量名 (应该是snake_case)
                fixed_line = re.sub(r'(\s+)([A-Z][a-zA-Z0-9_]*)\s*=', r'\1' + self._to_snake_case(r'\2') + ' =', fixed_line)

                # 修复函数名 (应该是snake_case)
                fixed_line = re.sub(r'def\s+([A-Z][a-zA-Z0-9_]*)\(', r'def ' + self._to_snake_case(r'\1') + '(', fixed_line)

                # 修复常量名 (应该是UPPER_CASE)
                if '=' in line and not line.strip().startswith(('def', 'class', 'import', 'from')):
                    # 检查是否是常量赋值
                    parts = line.split('=')
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        if var_name.isupper() or '_' in var_name:
                            # 可能是常量，检查是否需要修改
                            if var_name != var_name.upper():
                                fixed_line = line.replace(var_name, var_name.upper(), 1)
                                fixes_count += 1

                if fixed_line != line:
                    fixes_count += 1

                fixed_lines.append(fixed_line)

            # 写入修复后的内容
            fixed_content = '\n'.join(fixed_lines)

            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)


            return {"naming_fixes": fixes_count}

        except Exception:
            return {"naming_fixes": 0}

    def _to_snake_case(self, name: str) -> str:
        """转换为snake_case"""
        # 简单的转换：CamelCase -> snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def fix_file(self, file_path: str) -> dict[str, int]:
        """修复单个文件的所有代码风格问题"""

        total_fixes = 0
        fix_details = {}

        # 1. 修复导入顺序问题
        import_result = self.fix_import_order_issues(file_path)
        total_fixes += import_result.get("import_fixes", 0)
        fix_details.update(import_result)

        # 2. 修复导入格式问题
        format_result = self.fix_import_format_issues(file_path)
        total_fixes += format_result.get("format_fixes", 0)
        fix_details.update(format_result)

        # 3. 修复命名约定问题
        naming_result = self.fix_naming_conventions(file_path)
        total_fixes += naming_result.get("naming_fixes", 0)
        fix_details.update(naming_result)

        self.files_processed += 1
        self.errors_fixed += total_fixes

        return {
            "total_fixes": total_fixes,
            "details": fix_details
        }

    def analyze_current_errors(self) -> dict[str, int]:
        """分析当前的代码风格错误"""

        error_counts = {}

        # 使用ruff检查错误类型
        try:
            result = subprocess.run([
                "ruff", "check", "src/",
                "--output-format=concise"
            ], capture_output=True, text=True, timeout=30)

            for line in result.stdout.split('\n'):
                if line.strip():
                    error_code = line.split(':')[-1].strip()
                    if error_code in error_counts:
                        error_counts[error_code] += 1
                    else:
                        error_counts[error_code] = 1

        except Exception:
            pass

        return error_counts

def main():
    """主函数"""

    fixer = CodeStyleFixer()

    # 分析当前错误状态
    current_errors = fixer.analyze_current_errors()
    for error_code, count in current_errors.items():
        pass

    # 重点关注E402和I001错误
    high_priority_files = [
        "src/api/predictions_enhanced.py",
        "src/api/realtime_streaming.py",
        "src/streaming/kafka_producer.py",
        "src/streaming/kafka_components.py",
        "src/utils/crypto_utils.py",
        "src/cache/cache/decorators_functions.py",
        "src/cache/mock_redis.py"
    ]

    total_fixes = 0

    for file_path in high_priority_files:
        if Path(file_path).exists():
            result = fixer.fix_file(file_path)
            total_fixes += result["total_fixes"]
        else:
            pass

    # 修复其他文件中的导入问题

    # 查找所有Python文件
    python_files = []
    for root, _dirs, files in os.walk("src"):
        for file in files:
            if file.endswith('.py') and not file.startswith('.') and 'test' not in file:
                python_files.append(os.path.join(root, file))

    # 处理其他文件（避免重复处理）
    processed_files = set(high_priority_files)
    remaining_files = [f for f in python_files if f not in processed_files]

    for file_path in remaining_files[:20]:  # 限制处理数量以避免超时
        try:
            result = fixer.fix_file(file_path)
            total_fixes += result["total_fixes"]
        except Exception:
            pass


    # 验证修复效果
    final_errors = fixer.analyze_current_errors()

    for error_code, count in final_errors.items():
        reduction = current_errors.get(error_code, 0) - count
        if reduction > 0:
            pass
        else:
            pass

    sum(current_errors.values()) - sum(final_errors.values())

if __name__ == "__main__":
    main()
