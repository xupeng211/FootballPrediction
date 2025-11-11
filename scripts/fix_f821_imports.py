#!/usr/bin/env python3
"""
批量修复F821未定义名称错误 - 专注sa/np/pd导入
Batch fix F821 undefined name errors - focus on sa/np/pd imports
"""

import re
from pathlib import Path
from typing import Set, Dict, List

class F821Importer:
    """F821导入错误修复器"""

    def __init__(self):
        self.import_patterns = {
            'sa': {
                'pattern': r'\bsa\.',
                'import_stmt': 'from sqlalchemy import text as sa_text\nfrom sqlalchemy.orm import Session as sa_Session\n',
                'alias_mapping': {
                    'sa.text': 'sa_text',
                    'sa.Session': 'sa_Session'
                }
            },
            'np': {
                'pattern': r'\bnp\.',
                'import_stmt': 'import numpy as np\n',
                'alias_mapping': {}
            },
            'pd': {
                'pattern': r'\bpd\.',
                'import_stmt': 'import pandas as pd\n',
                'alias_mapping': {}
            }
        }

    def find_f821_errors_in_file(self, file_path: Path) -> List[str]:
        """查找文件中的F821错误"""
        try:
            import subprocess
            result = subprocess.run(
                ['ruff', 'check', str(file_path), '--output-format=json'],
                capture_output=True, text=True
            )
            undefined_names = []

            for line in result.stdout.split('\n'):
                if '"F821"' in line:
                    # 提取未定义的名称
                    match = re.search(r'Undefined name `([^`]+)`', line)
                    if match:
                        undefined_names.append(match.group(1))

            return list(set(undefined_names))
        except:
            return []

    def fix_file_imports(self, file_path: Path) -> bool:
        """修复单个文件的导入错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            modifications = []

            # 查找F821错误
            undefined_names = self.find_f821_errors_in_file(file_path)

            if not undefined_names:
                return False

            # 检查每种类型的错误
            for alias in ['sa', 'np', 'pd']:
                if alias in undefined_names and self.import_patterns[alias]['pattern'] in content:
                    # 需要添加导入
                    import_info = self.import_patterns[alias]

                    # 找到插入位置（在docstring之后）
                    insert_pos = self._find_insert_position(content)

                    # 添加导入语句
                    content = content[:insert_pos] + import_info['import_stmt'] + content[insert_pos:]
                    modifications.append(f"添加 {alias} 导入")

                    # 处理特殊的别名映射（主要针对sa）
                    if alias == 'sa':
                        content = self._handle_sa_aliases(content)

            # 写回修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"✅ 修复文件: {file_path}")
                print(f"   修改: {', '.join(modifications)}")
                return True

            return False

        except Exception as e:
            print(f"❌ 修复文件 {file_path} 时出错: {e}")
            return False

    def _find_insert_position(self, content: str) -> int:
        """找到导入语句的插入位置"""
        lines = content.split('\n')

        # 查找docstring结束位置
        docstring_end = -1
        in_docstring = False

        for i, line in enumerate(lines):
            if line.strip().startswith('"""') and not in_docstring:
                if line.strip().count('"""') == 2:
                    # 单行docstring
                    docstring_end = i + 1
                    break
                else:
                    # 多行docstring开始
                    in_docstring = True
            elif line.strip().endswith('"""') and in_docstring:
                docstring_end = i + 1
                break

        # 如果找到docstring结束位置，在其后插入
        if docstring_end != -1 and docstring_end < len(lines):
            # 找到下一个非空行
            for i in range(docstring_end, len(lines)):
                if lines[i].strip():
                    return '\n'.join(lines[:i]) + '\n\n' + '\n'.join(lines[i:])

        # 如果没有找到docstring，在文件开头插入
        if content.startswith('"""'):
            doc_end = content.find('"""', 3)
            if doc_end != -1:
                insert_pos = content.find('\n', doc_end) + 1
                return insert_pos

        return 0

    def _handle_sa_aliases(self, content: str) -> str:
        """处理SQLAlchemy的特殊别名"""
        # 替换 sa.text 为 sa_text
        content = re.sub(r'\bsa\.text\(', 'sa_text(', content)

        # 替换 sa.Session 为 sa_Session
        content = re.sub(r'\bsa\.Session\b', 'sa_Session', content)

        # 其他sa的使用保持不变（如果有的话）
        return content

    def batch_fix_directory(self, directory: Path) -> Dict[str, int]:
        """批量修复目录中的文件"""
        print(f"🔧 开始批量修复F821错误: {directory}")

        fixed_files = []
        error_files = []
        total_f821_before = 0
        total_f821_after = 0

        # 遍历所有Python文件
        for py_file in directory.rglob("*.py"):
            # 跳过__init__.py和测试文件
            if py_file.name == "__init__.py" or py_file.name.startswith("test_"):
                continue

            # 统计修复前的F821错误
            f821_before = len([name for name in self.find_f821_errors_in_file(py_file)])
            total_f821_before += f821_before

            # 尝试修复
            if self.fix_file_imports(py_file):
                fixed_files.append(py_file)

                # 统计修复后的F821错误
                f821_after = len([name for name in self.find_f821_errors_in_file(py_file)])
                total_f821_after += f821_after
            elif f821_before > 0:
                error_files.append(py_file)
                total_f821_after += f821_before

        return {
            'fixed_files': len(fixed_files),
            'error_files': len(error_files),
            'f821_before': total_f821_before,
            'f821_after': total_f821_after,
            'f821_fixed': total_f821_before - total_f821_after
        }

def main():
    """主函数"""
    print("🚀 启动F821未定义名称错误批量修复...")

    fixer = F821Importer()
    src_path = Path("src")

    if not src_path.exists():
        print(f"❌ 源码目录不存在: {src_path}")
        return

    # 执行批量修复
    results = fixer.batch_fix_directory(src_path)

    # 输出结果
    print(f"\n📊 修复结果统计:")
    print(f"✅ 成功修复文件: {results['fixed_files']} 个")
    print(f"❌ 修复失败文件: {results['error_files']} 个")
    print(f"🎯 F821错误修复: {results['f821_before']} → {results['f821_after']} (减少 {results['f821_fixed']} 个)")

    if results['f821_fixed'] > 0:
        fix_rate = (results['f821_fixed'] / results['f821_before']) * 100 if results['f821_before'] > 0 else 0
        print(f"📈 修复成功率: {fix_rate:.1f}%")

    print(f"\n🎉 F821批量修复完成！")

if __name__ == "__main__":
    main()