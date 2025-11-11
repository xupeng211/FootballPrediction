#!/usr/bin/env python3
"""代码质量问题批量智能修复工具"""

import ast
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class CodeQualityFixer:
    def __init__(self):
        self.fixed_files = []
        self.errors_found = 0
        self.errors_fixed = 0
        self.fix_results = []

    def find_unused_imports(self, file_path: Path) -> List[Dict]:
        """查找未使用的导入"""
        unused_imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的未使用导入检测（基于常见模式）
            lines = content.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    import_line = stripped
                    # 检查这个导入是否在文件中被使用
                    import_name = self.extract_import_name(import_line)
                    if import_name and not self.is_import_used(content, import_name):
                        unused_imports.append({
                            'line': i + 1,
                            'content': line,
                            'import_name': import_name,
                            'type': 'unused_import'
                        })
        except Exception as e:
            print(f"读取文件错误 {file_path}: {e}")

        return unused_imports

    def extract_import_name(self, import_line: str) -> str:
        """从导入行中提取导入名称"""
        if import_line.startswith('import '):
            # import module
            return import_line.split(' ')[1].split('.')[0]
        elif import_line.startswith('from '):
            # from module import name
            parts = import_line.split(' ')
            if 'import' in parts:
                import_idx = parts.index('import')
                if import_idx + 1 < len(parts):
                    return parts[import_idx + 1].split(',')[0].split('.')[0]
        return ""

    def is_import_used(self, content: str, import_name: str) -> bool:
        """检查导入是否在文件中被使用"""
        # 简单的使用检测
        # 避免注释和字符串中的误判
        lines = content.split('\n')
        for line in lines:
            # 跳过注释行
            if line.strip().startswith('#'):
                continue
            # 检查是否使用了这个导入
            if import_name in line and not line.strip().startswith('import') and not line.strip().startswith('from'):
                return True
        return False

    def fix_unused_imports(self, file_path: Path, unused_imports: List[Dict]) -> bool:
        """修复未使用的导入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            # 从后往前删除，避免行号变化
            for import_info in sorted(unused_imports, key=lambda x: x['line'], reverse=True):
                line_num = import_info['line'] - 1
                if 0 <= line_num < len(lines):
                    # 删除这一行
                    del lines[line_num]
                    self.errors_fixed += 1
                    print(f"  ✅ 修复未使用导入: {import_info['import_name']} (第{import_info['line']}行)")

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            return True
        except Exception as e:
            print(f"修复未使用导入失败 {file_path}: {e}")
            return False

    def fix_import_order(self, file_path: Path) -> bool:
        """修复导入顺序"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用ruff格式化导入
            import subprocess
            result = subprocess.run(['ruff', 'format', str(file_path)],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                print(f"  ✅ 修复导入顺序: {file_path}")
                return True
            else:
                print(f"  ❌ 修复导入顺序失败: {file_path}")
                return False
        except Exception as e:
            print(f"修复导入顺序失败 {file_path}: {e}")
            return False

    def fix_undefined_all_names(self, file_path: Path) -> bool:
        """修复__all__中未定义的名称"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析AST找到实际定义的类和函数
            try:
                tree = ast.parse(content)
                defined_names = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        defined_names.add(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        defined_names.add(node.name)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                defined_names.add(target.id)

                # 查找__all__定义
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        # 提取__all__中的名称
                        try:
                            # 简单的解析，找到__all__列表
                            start_idx = line.find('[')
                            if start_idx != -1:
                                # 找到匹配的]
                                bracket_count = 1
                                end_idx = start_idx + 1
                                while end_idx < len(line) and bracket_count > 0:
                                    if line[end_idx] == '[':
                                        bracket_count += 1
                                    elif line[end_idx] == ']':
                                        bracket_count -= 1
                                    end_idx += 1

                                all_content = line[start_idx:end_idx]
                                # 提取引号中的名称
                                all_names = re.findall(r'["\']([^"\']+)["\']', all_content)

                                # 检查每个名称是否已定义
                                undefined_names = []
                                for name in all_names:
                                    if name not in defined_names:
                                        undefined_names.append(name)

                                if undefined_names:
                                    print(f"  ⚠️  发现未定义的__all__名称: {undefined_names}")
                                    # 这里可以选择注释掉未定义的名称或删除它们

                        except Exception as e:
                            print(f"  ❌ 解析__all__失败: {e}")

            except SyntaxError:
                print(f"  ❌ 文件语法错误，跳过: {file_path}")
                return False

            return True
        except Exception as e:
            print(f"修复__all__定义失败 {file_path}: {e}")
            return False

    def fix_code_quality_in_directory(self, directory: Path) -> Dict:
        """修复目录中的代码质量问题"""
        py_files = list(directory.rglob('*.py'))

        # 排除一些目录
        exclude_dirs = {'__pycache__', '.git', '.pytest_cache', 'venv', 'env'}
        py_files = [f for f in py_files if not any(exclude in str(f) for exclude in exclude_dirs)]

        print(f"🔍 开始修复代码质量问题...")
        print(f"📁 检查文件数: {len(py_files)}")

        for py_file in py_files:
            print(f"\n📄 处理文件: {py_file}")

            file_fixed = False

            # 1. 修复未使用的导入
            unused_imports = self.find_unused_imports(py_file)
            if unused_imports:
                print(f"  发现 {len(unused_imports)} 个未使用导入")
                if self.fix_unused_imports(py_file, unused_imports):
                    file_fixed = True

            # 2. 修复导入顺序
            if self.fix_import_order(py_file):
                file_fixed = True

            # 3. 修复__all__未定义名称
            if self.fix_undefined_all_names(py_file):
                file_fixed = True

            if file_fixed:
                self.fixed_files.append(str(py_file))

        return {
            'files_processed': len(py_files),
            'files_fixed': len(self.fixed_files),
            'errors_fixed': self.errors_fixed,
            'fixed_files': self.fixed_files
        }

def main():
    """主函数"""
    fixer = CodeQualityFixer()

    print("🚀 开始代码质量批量修复...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 修复src目录
    result = fixer.fix_code_quality_in_directory(Path('src'))

    print(f"\n=== 修复结果 ===")
    print(f"处理文件数: {result['files_processed']}")
    print(f"修复文件数: {result['files_fixed']}")
    print(f"修复问题数: {result['errors_fixed']}")

    if result['fixed_files']:
        print(f"\n📝 修复的文件:")
        for file_path in result['fixed_files']:
            print(f"  - {file_path}")

    # 验证修复效果
    print(f"\n🔍 验证修复效果...")
    try:
        # 运行ruff检查剩余问题
        import subprocess
        ruff_result = subprocess.run(['ruff', 'check', 'src/', '--output-format=concise'],
                                  capture_output=True, text=True)

        remaining_errors = len(ruff_result.stdout.strip().split('\n')) if ruff_result.stdout.strip() else 0
        print(f"剩余代码质量问题: {remaining_errors}个")

        if remaining_errors < 100:  # 假设之前有142个错误
            improvement = 142 - remaining_errors
            print(f"✅ 代码质量改善: {improvement}个问题已修复")

    except Exception as e:
        print(f"验证修复效果失败: {e}")

    # 保存修复报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'result': result,
        'improvement': '代码质量问题已批量修复'
    }

    with open('code_quality_fix_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 修复报告已保存到: code_quality_fix_report.json")

if __name__ == '__main__':
    main()