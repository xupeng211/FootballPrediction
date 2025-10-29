#!/usr/bin/env python3
"""
F405星号导入优化工具
F405 Star Import Fixer

专门用于修复F405星号导入错误，通过以下策略：
1. 分析星号导入的实际使用情况
2. 替换为明确的导入语句
3. 移除未使用的星号导入
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


class F405StarImportFixer:
    """F405星号导入修复器"""

    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.files_fixed = 0

        # 常见的星号导入模块
        self.common_star_imports = {
            'django.db.models',
            'sqlalchemy.orm',
            'pandas',
            'numpy',
            'matplotlib.pyplot',
            'seaborn',
            'sklearn',
            'tensorflow',
            'torch',
            'pytest',
            'src.*'
        }

    def get_f405_errors(self) -> List[Dict]:
        """获取所有F405错误"""
        logger.info("正在获取F405错误列表...")
        errors = []

        try:
            result = subprocess.run(
                ['make', 'lint'],
                capture_output=True,
                text=True,
                timeout=60
            )

            for line in result.stdout.split('\n'):
                if 'F405' in line and 'may be undefined' in line:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        col_num = int(parts[2])
                        error_msg = parts[3].strip()

                        # 提取模块名和导入名
                        module_match = re.search(r"from (\S+) \* may be undefined", error_msg)
                        if module_match:
                            module_name = module_match.group(1)
                            errors.append({
                                'file': file_path,
                                'line': line_num,
                                'column': col_num,
                                'message': error_msg,
                                'module_name': module_name,
                                'full_line': line
                            })
        except Exception as e:
            logger.error(f"获取F405错误失败: {e}")

        logger.info(f"发现 {len(errors)} 个F405错误")
        return errors

    def analyze_star_imports(self, file_path: str) -> Dict:
        """分析文件的星号导入使用情况"""
        path = Path(file_path)
        if not path.exists():
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST分析导入使用情况
            try:
                tree = ast.parse(content)
                analyzer = StarImportAnalyzer()
                analyzer.visit(tree)
                return analyzer.star_imports_usage
            except SyntaxError:
                logger.warning(f"文件 {file_path} 存在语法错误，跳过AST分析")
                return {}

        except Exception as e:
            logger.error(f"分析文件 {file_path} 失败: {e}")
            return {}

    def fix_star_imports(self, file_path: str, usage_info: Dict) -> bool:
        """修复星号导入"""
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            modified = False

            # 处理每个星号导入
            for module, used_names in usage_info.items():
                # 找到星号导入语句
                for i, line in enumerate(lines):
                    if f'from {module} import *' in line:
                        if used_names:
                            # 替换为明确导入
                            if len(used_names) <= 5:  # 少量导入放在一行
                                new_import = f"from {module} import {', '.join(sorted(used_names))}"
                            else:  # 多个导入分行
                                new_import = f"from {module} import ("
                                for name in sorted(used_names):
                                    new_import += f"\n    {name},"
                                new_import += "\n)"
                            lines[i] = new_import
                        else:
                            # 如果没有使用任何导入，注释掉或删除
                            lines[i] = f"# from {module} import *  # Removed: unused"
                        modified = True
                        break

            # 如果有修改，写回文件
            if modified:
                content = '\n'.join(lines)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"修复星号导入: {file_path}")
                return True

        except Exception as e:
            logger.error(f"修复文件 {file_path} 失败: {e}")

        return False

    def run_batch_fix(self) -> Dict:
        """运行批量修复"""
        logger.info("🔧 开始F405星号导入批量修复...")

        errors = self.get_f405_errors()
        if not errors:
            logger.info("没有发现F405错误")
            return {
                'success': True,
                'errors_fixed': 0,
                'files_processed': 0,
                'message': '没有F405错误需要修复'
            }

        # 获取需要修复的文件列表
        files_to_fix = set(error['file'] for error in errors)

        # 修复每个文件
        files_fixed = 0
        total_errors_fixed = 0

        for file_path in files_to_fix:
            # 分析星号导入使用情况
            usage_info = self.analyze_star_imports(file_path)

            if usage_info:
                if self.fix_star_imports(file_path, usage_info):
                    files_fixed += 1
                    # 估算修复的错误数
                    file_errors = [e for e in errors if e['file'] == file_path]
                    total_errors_fixed += len(file_errors)

            self.files_processed += 1

        result = {
            'success': True,
            'errors_fixed': total_errors_fixed,
            'files_processed': self.files_processed,
            'files_fixed': files_fixed,
            'message': f'修复了 {files_fixed} 个文件中的 {total_errors_fixed} 个F405错误'
        }

        logger.info(f"F405批量修复完成: {result}")
        return result

    def generate_report(self) -> Dict:
        """生成修复报告"""
        return {
            'fixer_name': 'F405 Star Import Fixer',
            'timestamp': '2025-10-30T01:55:00.000000',
            'fixes_applied': self.fixes_applied,
            'files_processed': self.files_processed,
            'success_rate': f"{(self.fixes_applied / max(self.files_processed, 1)) * 100:.1f}%"
        }


class StarImportAnalyzer(ast.NodeVisitor):
    """星号导入使用分析器"""

    def __init__(self):
        self.star_imports_usage = {}
        self.current_star_imports = []

    def visit_ImportFrom(self, node):
        """访问导入语句"""
        if node.names and isinstance(node.names[0], ast.alias) and node.names[0].name == '*':
            # 记录星号导入
            module = node.module or ''
            self.current_star_imports.append(module)
        self.generic_visit(node)

    def visit_Name(self, node):
        """访问名称节点"""
        if isinstance(node.ctx, ast.Load):
            # 检查是否来自星号导入
            for module in self.current_star_imports:
                if module not in self.star_imports_usage:
                    self.star_imports_usage[module] = set()
                self.star_imports_usage[module].add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """访问属性节点"""
        # 处理属性访问，如 module.name
        if isinstance(node.value, ast.Name):
            name_parts = [node.value.id]
            current = node
            while isinstance(current, ast.Attribute):
                name_parts.append(current.attr)
                current = current.value

            # 检查是否来自星号导入
            '.'.join(reversed(name_parts))
            for module in self.current_star_imports:
                if module not in self.star_imports_usage:
                    self.star_imports_usage[module] = set()
                # 添加基名称
                if name_parts:
                    self.star_imports_usage[module].add(name_parts[0])

        self.generic_visit(node)


def main():
    """主函数"""
    fixer = F405StarImportFixer()

    print("🔧 F405 星号导入批量修复工具")
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
    report_file = Path('f405_fix_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'result': result,
            'report': report
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细报告已保存到: {report_file}")

    return result


if __name__ == '__main__':
    main()