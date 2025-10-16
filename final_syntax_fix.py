#!/usr/bin/env python3
"""
最终语法修复工具 - 处理所有剩余的语法错误
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Tuple, Dict

class FinalSyntaxFixer:
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.fixes_applied = 0

    def fix_file(self, file_path: str) -> bool:
        """修复单个文件的语法错误"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用各种修复规则
            content = self.fix_common_errors(content)
            content = self.fix_string_literals(content)
            content = self.fix_imports(content)
            content = self.fix_punctuation(content)

            # 写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✓ 已修复: {file_path}")
            else:
                print(f"○ 无需修复: {file_path}")

            # 验证语法
            try:
                ast.parse(content)
                self.fixed_files.append(file_path)
                return True
            except SyntaxError as e:
                print(f"✗ 修复失败: {file_path} - {e}")
                self.failed_files.append((file_path, str(e)))
                return False

        except Exception as e:
            print(f"✗ 处理失败: {file_path} - {e}")
            self.failed_files.append((file_path, str(e)))
            return False

    def fix_common_errors(self, content: str) -> str:
        """修复常见语法错误"""
        # 修复类定义后的多余字符
        content = re.sub(r'class\s+(\w+)\)\s*:', r'class \1:', content)
        content = re.sub(r'class\s+(\w+)\s*\]\s*:', r'class \1:', content)

        # 修复函数定义
        content = re.sub(r'def\s+(\w+)\)\s*:', r'def \1():', content)

        # 修复if/for/while语句
        content = re.sub(r'if\s+([^:]+)\)\s*:', r'if \1:', content)
        content = re.sub(r'for\s+([^:]+)\)\s*:', r'for \1:', content)

        return content

    def fix_string_literals(self, content: str) -> str:
        """修复字符串字面量"""
        # 修复未闭合的三引号字符串
        triple_quote_count = content.count('"""')
        if triple_quote_count % 2 != 0:
            content += '\n"""'

        # 修复断开的URL
        content = re.sub(r'http://localhos\s*\n\s*t:(\d+)', r'http://localhost:\1', content)

        # 修复未闭合的字符串（简单情况）
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.count('"') % 2 == 1 and not line.strip().endswith('"'):
                if not line.rstrip().endswith('\\'):
                    lines[i] = line + '"'
        content = '\n'.join(lines)

        return content

    def fix_imports(self, content: str) -> str:
        """修复import语句"""
        # 修复合并的import语句
        content = re.sub(r'import\s+(\w+)\s*import\s+', r'import \1\nimport ', content)
        content = re.sub(r'from\s+(\S+)\s*import\s+(\w+)\s*from\s+', r'from \1 import \2\nfrom ', content)

        # 修复from import语句中的错误
        content = re.sub(r'from\s+([^\s]+)\.\s*\.\s*([^\s]+)\s+import', r'from ..\2 import', content)

        return content

    def fix_punctuation(self, content: str) -> str:
        """修复标点符号"""
        # 替换中文标点为英文标点
        content = content.replace('，', ', ')
        content = content.replace('。', '. ')
        content = content.replace('：', ': ')
        content = content.replace('；', '; ')
        content = content.replace('（', '(')
        content = content.replace('）', ')')
        content = content.replace('【', '[')
        content = content.replace('】', ']')
        content = content.replace('、', ', ')

        return content

    def fix_specific_files(self):
        """修复特定的已知问题文件"""
        specific_fixes = {
            "src/core/service_lifecycle.py": self._fix_service_lifecycle,
            "src/api/facades.py": self._fix_api_facades,
            "src/api/features.py": self._fix_api_features,
            "src/api/decorators.py": self._fix_api_decorators,
            "src/database/config.py": self._fix_database_config,
            "src/utils/validators.py": self._fix_utils_validators,
            "src/adapters/registry.py": self._fix_adapters_registry,
            "src/domain/models/prediction.py": self._fix_domain_prediction,
            "src/domain/strategies/config.py": self._fix_domain_strategies_config,
        }

        for file_path, fix_func in specific_fixes.items():
            if os.path.exists(file_path):
                print(f"\n修复特定文件: {file_path}")
                if fix_func(file_path):
                    print(f"✓ 成功修复: {file_path}")
                else:
                    print(f"✗ 修复失败: {file_path}")

    def _fix_service_lifecycle(self, file_path: str) -> bool:
        """修复 service_lifecycle.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复文档字符串和import语句
            content = re.sub(r'""\s*服务生命周期管理', '"""\n服务生命周期管理', content)
            content = re.sub(r'import asyncioimport logging', 'import asyncio\nimport logging', content)
            content = re.sub(r'import threadingfrom abc', 'import threading\nfrom abc', content)
            content = re.sub(r'fieldfrom datetime', 'field\nfrom datetime', content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_api_facades(self, file_path: str) -> bool:
        """修复 api/facades.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复语法错误
            content = content.replace('、', ', ')
            content = re.sub(r'from\s+\.\s*\.\s*decorators', 'from ..decorators', content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_api_features(self, file_path: str) -> bool:
        """修复 api/features.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复未闭合的字符串
            if content.count('"') % 2 != 0:
                content += '"'

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_api_decorators(self, file_path: str) -> bool:
        """修复 api/decorators.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复中文标点
            content = content.replace('：', ': ')

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_database_config(self, file_path: str) -> bool:
        """修复 database/config.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复中文标点
            content = content.replace('。', '. ')

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_utils_validators(self, file_path: str) -> bool:
        """修复 utils/validators.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复类型注解错误
            content = re.sub(r'def\s+validate_data\([^)]+\)\s*->\s*[^:]+:', 'def validate_data(data):', content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_adapters_registry(self, file_path: str) -> bool:
        """修复 adapters/registry.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复import语句
            content = re.sub(r'from\s+\.base', 'from .base', content)
            content = re.sub(r'from\s+\.factory', 'from .factory', content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_domain_prediction(self, file_path: str) -> bool:
        """修复 domain/models/prediction.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复未闭合的字符串
            if content.count('"') % 2 != 0:
                content += '"'

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def _fix_domain_strategies_config(self, file_path: str) -> bool:
        """修复 domain/strategies/config.py"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复未闭合的字符串
            if content.count('"') % 2 != 0:
                content += '"'

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except:
            return False

    def fix_all_files(self, base_dir: str = "src") -> Dict[str, int]:
        """修复所有Python文件"""
        base_path = Path(base_dir)

        print("=" * 60)
        print("最终语法修复工具")
        print("=" * 60)

        # 首先修复特定文件
        print("\n1. 修复特定的已知问题文件...")
        self.fix_specific_files()

        # 查找所有Python文件
        python_files = list(base_path.rglob("*.py"))

        print(f"\n2. 批量修复所有 {len(python_files)} 个Python文件...")
        print()

        results = {
            "total": len(python_files),
            "fixed": 0,
            "failed": 0,
            "skipped": 0
        }

        for file_path in python_files:
            relative_path = file_path.relative_to(Path.cwd())
            print(f"处理: {relative_path}")

            if self.fix_file(str(file_path)):
                results["fixed"] += 1
            else:
                results["failed"] += 1

        return results

    def generate_report(self, results: Dict[str, int]):
        """生成修复报告"""
        print("\n" + "=" * 60)
        print("修复完成！")
        print("=" * 60)
        print(f"总文件数: {results['total']}")
        print(f"修复成功: {results['fixed']}")
        print(f"修复失败: {results['failed']}")
        print(f"总修复数: {self.fixes_applied}")

        if self.failed_files:
            print("\n失败的文件:")
            for file_path, error in self.failed_files[:10]:
                print(f"  - {file_path}: {error}")

        # 验证核心模块
        print("\n验证核心模块...")
        core_modules = [
            "src/core/config.py",
            "src/core/di.py",
            "src/core/service_lifecycle.py",
            "src/utils/string_utils.py",
            "src/utils/validators.py",
            "src/api/app.py",
            "src/database/base.py"
        ]

        success_count = 0
        for module in core_modules:
            if os.path.exists(module):
                try:
                    with open(module, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                    print(f"✓ {module}")
                    success_count += 1
                except:
                    print(f"✗ {module}")

        print(f"\n核心模块状态: {success_count}/{len(core_modules)} 文件语法正确")


def main():
    """主函数"""
    fixer = FinalSyntaxFixer()
    results = fixer.fix_all_files()
    fixer.generate_report(results)


if __name__ == "__main__":
    main()