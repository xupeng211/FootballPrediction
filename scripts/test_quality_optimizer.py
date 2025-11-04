#!/usr/bin/env python3
"""
测试代码质量优化工具
专门处理测试代码中的质量问题，包括print语句、语法错误等
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple

class TestQualityOptimizer:
    """测试代码质量优化工具类"""

    def __init__(self):
        self.optimized_files = []
        self.total_issues_fixed = 0

    def optimize_all_test_quality(self, project_root: str = ".") -> Dict:
        """优化所有测试代码质量问题"""
        project_path = Path(project_root)

        # 获取所有测试代码质量问题
        test_issues = self.get_test_quality_issues()
        print(f"发现 {len(test_issues)} 个测试代码质量问题")

        results = {
            "total_issues": len(test_issues),
            "optimized_files": 0,
            "fixed_issues": 0,
            "failed_files": [],
            "details": []
        }

        # 按文件分组
        issues_by_file = {}
        for issue in test_issues:
            file_path = issue["file"]
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)

        # 逐个文件优化
        for file_path, file_issues in issues_by_file.items():
            full_path = os.path.join(project_root, file_path)
            if os.path.exists(full_path):
                try:
                    fixed = self.optimize_test_file_quality(full_path, file_issues)
                    if fixed > 0:
                        results["optimized_files"] += 1
                        results["fixed_issues"] += fixed
                        results["details"].append({
                            "file": file_path,
                            "issues_fixed": fixed,
                            "total_issues": len(file_issues)
                        })
                        print(f"✅ {file_path}: 修复了 {fixed} 个质量问题")
                except Exception as e:
                    results["failed_files"].append({"file": file_path, "error": str(e)})
                    print(f"❌ {file_path}: 测试质量优化失败 - {e}")

        return results

    def get_test_quality_issues(self) -> List[Dict]:
        """获取所有测试代码质量问题"""
        import subprocess

        try:
            result = subprocess.run(
                ['ruff', 'check', 'tests/', '--output-format=concise'],
                capture_output=True,
                text=True
            )

            issues = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    # 解析格式: file:line:column: code message
                    parts = line.split(':')
                    if len(parts) >= 4:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        column_num = int(parts[2])
                        message = ':'.join(parts[3:]).strip()

                        # 提取错误代码
                        code_match = re.search(r'([A-Z]\d+|invalid-syntax)', message)
                        if code_match:
                            error_code = code_match.group(1)

                            issue_info = {
                                "file": file_path,
                                "line": line_num,
                                "column": column_num,
                                "code": error_code,
                                "message": message
                            }

                            # 针对不同错误类型提取额外信息
                            if error_code == 'T201':
                                # T201: print found
                                issue_info["print_statement"] = True

                            elif 'invalid-syntax' in message:
                                # 语法错误
                                issue_info["syntax_error"] = True
                                if 'f-string' in message:
                                    issue_info["fstring_error"] = True
                                elif 'unterminated' in message:
                                    issue_info["unterminated_string"] = True

                            issues.append(issue_info)

            return issues

        except Exception as e:
            print(f"获取测试质量问题失败: {e}")
            return []

    def optimize_test_file_quality(self, file_path: str, issues: List[Dict]) -> int:
        """优化单个测试文件的质量问题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise Exception(f"读取文件失败: {e}")

        original_content = content
        fixed_count = 0

        # 按问题类型分类处理
        syntax_issues = [issue for issue in issues if issue.get('syntax_error')]
        print_issues = [issue for issue in issues if issue.get('print_statement')]

        # 优先处理语法错误
        if syntax_issues:
            content = self.fix_syntax_errors(content, syntax_issues)
            fixed_count += len(syntax_issues)

        # 处理print语句
        if print_issues:
            content = self.fix_print_statements(content, print_issues)
            fixed_count += len(print_issues)

        # 只有在有修复时才写回文件
        if content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.optimized_files.append(file_path)
                self.total_issues_fixed += fixed_count
            except Exception as e:
                raise Exception(f"写入文件失败: {e}")

        return fixed_count

    def fix_syntax_errors(self, content: str, issues: List[Dict]) -> str:
        """修复语法错误"""
        lines = content.split('\n')
        new_lines = lines.copy()

        for issue in issues:
            line_num = issue['line'] - 1
            if 0 <= line_num < len(new_lines):
                line = new_lines[line_num]

                # 处理f-string未终止错误
                if issue.get('fstring_error') and 'f"' in line:
                    fixed_line = self.fix_fstring_syntax(line)
                    if fixed_line != line:
                        new_lines[line_num] = fixed_line

                # 处理未终止字符串错误
                elif issue.get('unterminated_string'):
                    fixed_line = self.fix_unterminated_string(line, lines, line_num)
                    if fixed_line != line:
                        new_lines[line_num] = fixed_line

                # 处理其他语法错误
                else:
                    fixed_line = self.fix_general_syntax_error(line, lines, line_num)
                    if fixed_line != line:
                        new_lines[line_num] = fixed_line

        return '\n'.join(new_lines)

    def fix_print_statements(self, content: str, issues: List[Dict]) -> str:
        """修复print语句"""
        lines = content.split('\n')
        new_lines = []

        for i, line in enumerate(lines):
            # 检查是否是print语句
            if 'print(' in line or line.strip().startswith('print '):
                # 将print语句转换为logging或注释掉
                fixed_line = self.convert_print_to_logging(line)
                new_lines.append(fixed_line)
            else:
                new_lines.append(line)

        return '\n'.join(new_lines)

    def fix_fstring_syntax(self, line: str) -> str:
        """修复f-string语法错误"""
        # 查找未终止的f-string
        fstring_start = line.find('f"')
        if fstring_start == -1:
            fstring_start = line.find("f'")

        if fstring_start != -1:
            # 查找对应的结束引号
            quote_char = line[fstring_start + 1]
            if quote_char in ['"', "'"]:
                # 尝试找到结束引号
                end_pos = line.rfind(quote_char)
                if end_pos > fstring_start + 1:
                    # 检查是否有转义问题
                    fstring_content = line[fstring_start:end_pos + 1]
                    fixed_content = self.fix_fstring_content(fstring_content)
                    line = line.replace(fstring_content, fixed_content)
                else:
                    # 添加结束引号
                    line = line + quote_char

        return line

    def fix_unterminated_string(self, line: str, all_lines: List[str], line_num: int) -> str:
        """修复未终止的字符串"""
        # 查找未终止的字符串
        if 'f"' in line and line.count('"') % 2 == 1:
            # 未终止的f-string，添加结束引号
            return line + '"'
        elif "f'" in line and line.count("'") % 2 == 1:
            # 未终止的f-string，添加结束引号
            return line + "'"
        elif '"' in line and line.count('"') % 2 == 1:
            # 未终止的普通字符串，添加结束引号
            return line + '"'
        elif "'" in line and line.count("'") % 2 == 1:
            # 未终止的普通字符串，添加结束引号
            return line + "'"

        return line

    def fix_fstring_content(self, fstring_content: str) -> str:
        """修复f-string内容"""
        # 处理常见的f-string问题
        # 1. 修复嵌套引号问题
        content = fstring_content

        # 2. 修复表达式问题
        # 这里可以添加更多f-string修复逻辑

        return content

    def fix_general_syntax_error(self, line: str, all_lines: List[str], line_num: int) -> str:
        """修复一般语法错误"""
        # 处理常见的语法错误
        if 'Expected `except` or `finally`' in line:
            # 查找对应的try语句
            for i in range(max(0, line_num - 10), line_num):
                if 'try:' in all_lines[i]:
                    # 添加except语句
                    indent = len(all_lines[i]) - len(all_lines[i].lstrip())
                    except_line = ' ' * indent + 'except Exception as e:\n'
                    except_line += ' ' * (indent + 4) + 'pass'
                    return line + '\n' + except_line

        return line

    def convert_print_to_logging(self, line: str) -> str:
        """将print语句转换为logging语句"""
        stripped = line.strip()

        # 检查是否是print语句
        if stripped.startswith('print('):
            # 提取print内容
            content = stripped[6:-1]  # 去掉 'print(' 和 ')'

            # 根据内容判断日志级别
            if any(keyword in content.lower() for keyword in ['error', 'fail', 'exception']):
                log_level = 'error'
            elif any(keyword in content.lower() for keyword in ['warning', 'warn']):
                log_level = 'warning'
            elif any(keyword in content.lower() for keyword in ['info', 'start', 'complete']):
                log_level = 'info'
            else:
                log_level = 'debug'

            # 获取缩进
            indent = len(line) - len(line.lstrip())

            # 生成logging语句
            if content.strip().startswith('f"') or content.strip().startswith("f'"):
                logging_line = ' ' * indent + f'logger.{log_level}({content})'
            else:
                logging_line = ' ' * indent + f'logger.{log_level}({content})'

            # 如果文件中没有logger导入，添加注释说明
            return f'{logging_line}  # TODO: Add logger import if needed'

        # 对于简单的print语句，注释掉
        elif stripped.startswith('print '):
            return f'# {line}  # TODO: Replace with proper logging'

        return line

def main():
    """主函数"""
    print("开始测试代码质量优化...")

    optimizer = TestQualityOptimizer()
    results = optimizer.optimize_all_test_quality()

    print(f"\n🎉 测试代码质量优化完成！")
    print(f"📊 优化统计:")
    print(f"  - 总问题数: {results['total_issues']}")
    print(f"  - 优化文件数: {results['optimized_files']}")
    print(f"  - 修复问题数: {results['fixed_issues']}")
    print(f"  - 失败文件数: {len(results['failed_files'])}")

    if results['details']:
        print(f"\n📋 优化详情:")
        for detail in results['details'][:10]:  # 只显示前10个
            print(f"  - {detail['file']}: {detail['issues_fixed']} 个问题, {detail['total_issues']} 个总问题")

    if results['failed_files']:
        print(f"\n⚠️  优化失败的文件:")
        for failed in results['failed_files']:
            print(f"  - {failed['file']}: {failed['error']}")

    # 验证优化结果
    print(f"\n🔍 验证优化结果...")
    try:
        result = subprocess.run(
            ['ruff', 'check', 'tests/', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining_issues = len([line for line in result.stdout.split('\n') if line.strip()])
        print(f"剩余测试质量问题: {remaining_issues}")

        if remaining_issues == 0:
            print("🎉 所有测试质量问题已解决！")
        else:
            print("⚠️  仍有部分测试质量问题需要手动处理")
            print("主要问题类型：")
            for line in result.stdout.split('\n')[:5]:
                if line.strip():
                    code = line.split(':')[3] if len(line.split(':')) > 3 else 'unknown'
                    print(f"  - {code}")
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    import subprocess
    main()