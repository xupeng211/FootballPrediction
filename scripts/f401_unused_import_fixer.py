#!/usr/bin/env python3
"""
F401未使用导入批量清理工具
F401 Unused Import Batch Cleaner

专门用于批量清理F401未使用导入错误，通过以下策略：
1. 直接删除未使用的导入语句
2. 智能分析导入使用情况
3. 批量处理多个文件
"""

import ast
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class F401ImportFixer:
    """F401未使用导入修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

        # 保留的重要导入（即使看起来未使用）
        self.preserve_imports = {
            'typing', 'datetime', 'pathlib', 'asyncio', 'logging',
            'sys', 'os', 'json', 're', 'uuid', 'time', 'math'
        }

    def get_f401_errors(self) -> List[Dict]:
        """获取所有F401错误"""
        logger.info("正在获取F401错误列表...")
        errors = []

        try:
            result = subprocess.run(
                ['make', 'lint'],
                capture_output=True,
                text=True,
                timeout=60
            )

            for line in result.stdout.split('\n'):
                if 'F401' in line and 'imported but never used' in line:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        col_num = int(parts[2])
                        error_msg = parts[3].strip()

                        # 提取导入名
                        import_match = re.search(r"'([^']+)' imported but never used", error_msg)
                        if import_match:
                            import_name = import_match.group(1)
                            errors.append({
                                'file': file_path,
                                'line': line_num,
                                'column': col_num,
                                'message': error_msg,
                                'import_name': import_name,
                                'full_line': line
                            })
        except Exception as e:
            logger.error(f"获取F401错误失败: {e}")

        logger.info(f"发现 {len(errors)} 个F401错误")
        return errors

    def analyze_import_usage(self, file_path: str) -> Dict[str, bool]:
        """分析文件中导入的使用情况"""
        path = Path(file_path)
        if not path.exists():
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST分析导入使用情况
            try:
                tree = ast.parse(content)
                analyzer = ImportUsageAnalyzer()
                analyzer.visit(tree)
                return analyzer.import_usage
            except SyntaxError:
                logger.warning(f"文件 {file_path} 存在语法错误，跳过AST分析")
                return {}

        except Exception as e:
            logger.error(f"分析文件 {file_path} 失败: {e}")
            return {}

    def fix_unused_imports(self, file_path: str, unused_imports: List[str], import_usage: Dict[str, bool]) -> bool:
        """修复未使用的导入"""
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            modified = False

            # 按行号倒序处理，避免行号偏移
            for unused_import in unused_imports:
                # 如果这个导入确实未被使用
                if not import_usage.get(unused_import, True):
                    # 查找并删除对应的导入语句
                    for i, line in enumerate(lines):
                        # 检查import语句
                        if f"import {unused_import}" in line or f"from {unused_import}" in line:
                            # 对于from语句，需要检查具体导入的内容
                            if ' from ' in line:
                                # 简单处理：如果from语句中有其他导入，保留；否则删除整行
                                imports_part = line.split(' from ')[1].split(' import ')[1]
                                imported_items = [item.strip() for item in imports_part.split(',')]

                                # 如果只有一个导入项且是未使用的，删除整行
                                if len(imported_items) == 1 and imported_items[0] == unused_import:
                                    lines[i] = f"# {line}  # Removed unused import"
                                    modified = True
                                    logger.info(f"删除导入: {file_path}:{i+1} - {line.strip()}")
                            else:
                                # 简单的import语句，直接删除
                                lines[i] = f"# {line}  # Removed unused import"
                                modified = True
                                logger.info(f"删除导入: {file_path}:{i+1} - {line.strip()}")

            # 如果有修改，写回文件
            if modified:
                content = '\n'.join(lines)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

        except Exception as e:
            logger.error(f"修复文件 {file_path} 失败: {e}")

        return False

    def run_batch_fix(self) -> Dict:
        """运行批量修复"""
        logger.info("🔧 开始F401未使用导入批量清理...")

        errors = self.get_f401_errors()
        if not errors:
            logger.info("没有发现F401错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'message': '没有F401错误需要修复'
            }

        # 按文件分组错误
        errors_by_file = {}
        for error in errors:
            file_path = error['file']
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error)

        # 修复每个文件
        files_fixed = 0
        total_errors_fixed = 0

        for file_path, file_errors in errors_by_file.items():
            # 分析导入使用情况
            import_usage = self.analyze_import_usage(file_path)
            unused_imports = [error['import_name'] for error in file_errors]

            # 过滤掉保留的导入
            unused_imports = [imp for imp in unused_imports if imp not in self.preserve_imports]

            if unused_imports:
                if self.fix_unused_imports(file_path, unused_imports, import_usage):
                    files_fixed += 1
                    total_errors_fixed += len(unused_imports)
                    self.fixes_applied += len(unused_imports)

            self.files_processed += 1

        result = {
            'success': True,
            'errors_fixed': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'message': f'修复了 {files_fixed} 个文件中的 {total_errors_fixed} 个F401错误'
        }

        logger.info(f"F401批量清理完成: {result}")
        return result

    def generate_report(self) -> Dict:
        """生成修复报告"""
        return {
            'fixer_name': 'F401 Unused Import Fixer',
            'timestamp': '2025-10-30T02:00:00.000000',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'success_rate': f"{(self.fixes_applied / max(self.files_processed, 1)) * 100:.1f}%"
        }


class ImportUsageAnalyzer(ast.NodeVisitor):
    """导入使用情况分析器"""

    def __init__(self):
        self.import_usage = {}
        self.current_imports = []

    def visit_Import(self, node):
        """访问import语句"""
        for alias in node.names:
            import_name = alias.asname if alias.asname else alias.name
            self.current_imports.append(import_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """访问from import语句"""
        for alias in node.names:
            import_name = alias.asname if alias.asname else alias.name
            # 记录具体的导入名称
            self.current_imports.append(import_name)
        self.generic_visit(node)

    def visit_Name(self, node):
        """访问名称节点"""
        if isinstance(node.ctx, ast.Load):
            # 检查是否是导入的名称
            for imported_name in self.current_imports:
                if node.id == imported_name:
                    self.import_usage[imported_name] = True
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """访问属性节点"""
        # 处理模块级别的属性访问，如 module.name
        if isinstance(node.value, ast.Name):
            module_name = node.value.id
            # 检查是否是导入的模块
            for imported_name in self.current_imports:
                if imported_name == module_name:
                    # 记录模块被使用
                    self.import_usage[imported_name] = True
        self.generic_visit(node)


def main():
    """主函数"""
    fixer = F401ImportFixer()

    print("🔧 F401 未使用导入批量清理工具")
    print("=" * 50)

    # 运行批量修复
    result = fixer.run_batch_fix()

    # 生成报告
    report = fixer.generate_report()

    print("\n📊 修复摘要:")
    print(f"   修复错误数: {result['errors_fixed']}")
    print(f"   处理文件数: {result['files_processed']}")
    print(f"   修复文件数: {result['files_fixed']}")
    print(f"   成功率: {report['success_rate']}")
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 失败'}")

    # 保存报告
    report_file = Path('f401_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_file}")

    return result


if __name__ == '__main__':
    main()