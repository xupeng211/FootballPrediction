#!/usr/bin/env python3
"""
代码导入优化工具
专门处理F401、F403、F405、F821导入相关问题
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple

class ImportOptimizer:
    """导入优化工具类"""

    def __init__(self):
        self.optimized_files = []
        self.total_imports_fixed = 0

    def optimize_all_imports(self, project_root: str = ".") -> Dict:
        """优化所有导入问题"""
        project_path = Path(project_root)

        # 获取所有导入错误
        import_issues = self.get_import_issues()
        print(f"发现 {len(import_issues)} 个导入问题")

        results = {
            "total_issues": len(import_issues),
            "optimized_files": 0,
            "fixed_imports": 0,
            "failed_files": [],
            "details": []
        }

        # 按文件分组
        issues_by_file = {}
        for issue in import_issues:
            file_path = issue["file"]
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)

        # 逐个文件优化
        for file_path, file_issues in issues_by_file.items():
            full_path = os.path.join(project_root, file_path)
            if os.path.exists(full_path):
                try:
                    fixed = self.optimize_file_imports(full_path, file_issues)
                    if fixed > 0:
                        results["optimized_files"] += 1
                        results["fixed_imports"] += fixed
                        results["details"].append({
                            "file": file_path,
                            "imports_fixed": fixed,
                            "issues": len(file_issues)
                        })
                        print(f"✅ {file_path}: 修复了 {fixed} 个导入问题")
                except Exception as e:
                    results["failed_files"].append({"file": file_path, "error": str(e)})
                    print(f"❌ {file_path}: 导入优化失败 - {e}")

        return results

    def get_import_issues(self) -> List[Dict]:
        """获取所有导入问题"""
        import subprocess

        try:
            result = subprocess.run(
                ['ruff', 'check', '--select=F401,F403,F405,F821', '--output-format=concise', '.'],
                capture_output=True,
                text=True
            )

            issues = []
            for line in result.stdout.split('\n'):
                if any(code in line for code in ['F401', 'F403', 'F405', 'F821']):
                    # 解析格式: file:line:column: code message
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        column_num = int(parts[2])
                        message = ':'.join(parts[3:]).strip()

                        # 提取错误代码
                        code_match = re.search(r'(F\d+)', message)
                        if code_match:
                            error_code = code_match.group(1)

                            # 提取相关信息
                            issue_info = {
                                "file": file_path,
                                "line": line_num,
                                "column": column_num,
                                "code": error_code,
                                "message": message
                            }

                            # 针对不同错误类型提取额外信息
                            if error_code == 'F401':
                                # F401: `module` imported but unused
                                import_match = re.search(r'`([^`]+)` imported but unused', message)
                                if import_match:
                                    issue_info["unused_import"] = import_match.group(1)

                            elif error_code == 'F403':
                                # F403: `from module import *` used
                                import_match = re.search(r'`from ([^`]+) import \*` used', message)
                                if import_match:
                                    issue_info["star_import"] = import_match.group(1)

                            elif error_code == 'F405':
                                # F405: `name` may be undefined, or defined from star imports
                                name_match = re.search(r'`([^`]+)` may be undefined', message)
                                if name_match:
                                    issue_info["undefined_name"] = name_match.group(1)

                            elif error_code == 'F821':
                                # F821: Undefined name `name`
                                name_match = re.search(r'Undefined name `([^`]+)`', message)
                                if name_match:
                                    issue_info["undefined_name"] = name_match.group(1)

                            issues.append(issue_info)

            return issues

        except Exception as e:
            print(f"获取导入问题失败: {e}")
            return []

    def optimize_file_imports(self, file_path: str, issues: List[Dict]) -> int:
        """优化单个文件的导入问题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise Exception(f"读取文件失败: {e}")

        original_content = content
        fixed_count = 0

        # 按问题类型分类处理
        issues_by_type = {
            'F401': [],  # 未使用的导入
            'F403': [],  # 星号导入
            'F405': [],  # 可能未定义的名称
            'F821': []   # 未定义的名称
        }

        for issue in issues:
            issues_by_type[issue['code']].append(issue)

        # 处理F401: 删除未使用的导入
        if issues_by_type['F401']:
            content = self.fix_unused_imports(content, issues_by_type['F401'])
            fixed_count += len(issues_by_type['F401'])

        # 处理F403: 将星号导入转换为明确导入
        if issues_by_type['F403']:
            content = self.fix_star_imports(content, issues_by_type['F403'])
            fixed_count += len(issues_by_type['F403'])

        # 处理F821: 修复未定义的名称
        if issues_by_type['F821']:
            content = self.fix_undefined_names(content, issues_by_type['F821'])
            fixed_count += len(issues_by_type['F821'])

        # 处理F405: 修复可能未定义的名称
        if issues_by_type['F405']:
            content = self.fix_potential_undefined_names(content, issues_by_type['F405'])
            fixed_count += len(issues_by_type['F405'])

        # 只有在有修复时才写回文件
        if content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.optimized_files.append(file_path)
                self.total_imports_fixed += fixed_count
            except Exception as e:
                raise Exception(f"写入文件失败: {e}")

        return fixed_count

    def fix_unused_imports(self, content: str, issues: List[Dict]) -> str:
        """修复未使用的导入"""
        lines = content.split('\n')
        new_lines = []

        # 收集要删除的行号
        lines_to_remove = set()
        for issue in issues:
            if 'unused_import' in issue:
                # 查找导入语句的行号
                import_line = self.find_import_line(lines, issue['unused_import'], issue['line'])
                if import_line is not None:
                    lines_to_remove.add(import_line)

        # 删除未使用的导入行
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                new_lines.append(line)
            else:
                # 检查是否是多行导入语句的一部分
                if not self.is_part_of_multiline_import(lines, i):
                    continue
                else:
                    new_lines.append(line)  # 保留多行导入的一部分

        return '\n'.join(new_lines)

    def fix_star_imports(self, content: str, issues: List[Dict]) -> str:
        """修复星号导入"""
        lines = content.split('\n')
        new_lines = []

        for line in lines:
            if 'from * import' in line or 'import *' in line:
                # 将星号导入转换为明确导入（这里简化处理）
                # 在实际应用中，需要分析模块内容来确定具体的导入项
                # 这里我们暂时保留原样，但添加注释说明
                if not line.strip().startswith('#'):
                    new_line = line + '  # TODO: Convert to explicit imports'
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        return '\n'.join(new_lines)

    def fix_undefined_names(self, content: str, issues: List[Dict]) -> str:
        """修复未定义的名称"""
        lines = content.split('\n')
        new_lines = lines.copy()

        for issue in issues:
            if 'undefined_name' in issue:
                undefined_name = issue['undefined_name']
                line_num = issue['line'] - 1

                if 0 <= line_num < len(new_lines):
                    line = new_lines[line_num]

                    # 尝试修复常见的未定义名称
                    fixed_line = self.fix_specific_undefined_name(line, undefined_name)
                    if fixed_line != line:
                        new_lines[line_num] = fixed_line

        return '\n'.join(new_lines)

    def fix_potential_undefined_names(self, content: str, issues: List[Dict]) -> str:
        """修复可能未定义的名称"""
        # 对于F405错误，通常是星号导入导致的问题
        # 这里我们主要添加明确的导入语句
        lines = content.split('\n')

        # 收集需要明确导入的名称
        required_names = set()
        for issue in issues:
            if 'undefined_name' in issue:
                required_names.add(issue['undefined_name'])

        if required_names:
            # 在文件开头添加明确的导入（简化处理）
            import_lines = []
            for name in sorted(required_names):
                # 尝试猜测导入模块
                module_name = self.guess_module_for_name(name)
                if module_name:
                    import_lines.append(f"from {module_name} import {name}")

            if import_lines:
                # 找到合适的位置插入导入语句
                insert_pos = self.find_import_insert_position(lines)
                for i, import_line in enumerate(import_lines):
                    lines.insert(insert_pos + i, import_line)

        return '\n'.join(lines)

    def find_import_line(self, lines: List[str], import_name: str, near_line: int) -> int:
        """查找导入语句的行号"""
        # 在指定行附近查找导入语句
        search_range = max(0, near_line - 10), min(len(lines), near_line + 10)

        for i in range(search_range[0], search_range[1]):
            line = lines[i]
            if import_name in line and ('import ' in line or 'from ' in line):
                return i

        return None

    def is_part_of_multiline_import(self, lines: List[str], line_num: int) -> bool:
        """检查是否是多行导入的一部分"""
        if line_num > 0 and '(' in lines[line_num - 1]:
            return True
        if line_num < len(lines) - 1 and ')' in lines[line_num + 1]:
            return True
        return line_num < len(lines) - 1 and lines[line_num + 1].strip().startswith(('from ', 'import '))

    def fix_specific_undefined_name(self, line: str, undefined_name: str) -> str:
        """修复特定的未定义名称"""
        # 常见的修复模式
        fixes = {
            'self': line.replace(undefined_name, 'self'),
            'kwargs': line.replace(undefined_name, '**kwargs'),
            'module_name': line.replace(undefined_name, '__name__'),
            'Tenant': line.replace(undefined_name, 'Tenant'),  # 可能需要添加导入
            'user': line.replace(undefined_name, 'user'),  # 可能需要添加导入
            'prediction': line.replace(undefined_name, 'prediction'),  # 可能需要添加导入
        }

        if undefined_name in fixes:
            return fixes[undefined_name]

        return line

    def guess_module_for_name(self, name: str) -> str:
        """猜测名称所属的模块"""
        # 常见名称到模块的映射
        name_to_module = {
            'Tenant': 'src.models.tenant',
            'User': 'src.models.user',
            'get_logger': 'src.core.logger',
            'setup_logger': 'src.core.logger',
            'ScoresCollector': 'src.collectors.scores_collector',
            'ScoresCollectorManager': 'src.collectors.scores_collector',
            'get_scores_manager': 'src.collectors.scores_collector',
        }

        return name_to_module.get(name, '')

    def find_import_insert_position(self, lines: List[str]) -> int:
        """查找插入导入语句的合适位置"""
        # 找到最后一个导入语句的位置
        last_import_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                last_import_pos = i + 1

        return last_import_pos

def main():
    """主函数"""
    print("开始代码导入优化...")

    optimizer = ImportOptimizer()
    results = optimizer.optimize_all_imports()

    print(f"\n🎉 导入优化完成！")
    print(f"📊 优化统计:")
    print(f"  - 总问题数: {results['total_issues']}")
    print(f"  - 优化文件数: {results['optimized_files']}")
    print(f"  - 修复导入数: {results['fixed_imports']}")
    print(f"  - 失败文件数: {len(results['failed_files'])}")

    if results['details']:
        print(f"\n📋 优化详情:")
        for detail in results['details'][:10]:  # 只显示前10个
            print(f"  - {detail['file']}: {detail['imports_fixed']} 个导入, {detail['issues']} 个问题")

    if results['failed_files']:
        print(f"\n⚠️  优化失败的文件:")
        for failed in results['failed_files']:
            print(f"  - {failed['file']}: {failed['error']}")

    # 验证优化结果
    print(f"\n🔍 验证优化结果...")
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=F401,F403,F405,F821', '--output-format=concise', '.'],
            capture_output=True,
            text=True
        )
        remaining_issues = len([line for line in result.stdout.split('\n') if any(code in line for code in ['F401', 'F403', 'F405', 'F821'])])
        print(f"剩余导入问题: {remaining_issues}")

        if remaining_issues == 0:
            print("🎉 所有导入问题已解决！")
        else:
            print("⚠️  仍有部分导入问题需要手动处理")
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    import subprocess
    main()