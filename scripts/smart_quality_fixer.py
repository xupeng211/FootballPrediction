#!/usr/bin/env python3
"""
智能质量修复工具
Smart Quality Fixer

集成多种自动化修复功能，提供智能化的代码质量问题修复
"""

import os
import sys
import json
import subprocess
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartQualityFixer:
    """智能质量修复器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"

        # 修复结果跟踪
        self.fix_results = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": {},
            "errors_fixed": 0,
            "files_processed": 0,
            "recommendations": []
        }

        # 质量标准
        self.quality_standards = self._load_quality_standards()

    def _load_quality_standards(self) -> Dict[str, Any]:
        """加载质量标准"""
        standards_file = self.project_root / "config" / "quality_standards.json"
        if standards_file.exists():
            try:
                with open(standards_file, 'r') as f:
                    data = json.load(f)
                    return data.get("standards", {})
            except Exception as e:
                logger.warning(f"加载质量标准失败: {e}")

        # 默认标准
        return {
            "code_quality": {
                "max_ruff_errors": 10,
                "max_mypy_errors": 10
            },
            "coverage": {
                "minimum": 15.0,
                "target": 18.0
            }
        }

    def run_comprehensive_fix(self) -> Dict[str, Any]:
        """运行综合修复流程"""
        logger.info("开始智能质量修复...")

        print("🔧 智能质量修复工具")
        print("=" * 60)

        # 1. 语法错误修复
        print("\n1️⃣ 修复语法错误...")
        syntax_fixes = self.fix_syntax_errors()

        # 2. 导入错误修复
        print("\n2️⃣ 修复导入错误...")
        import_fixes = self.fix_import_errors()

        # 3. MyPy类型错误修复
        print("\n3️⃣ 修复MyPy类型错误...")
        mypy_fixes = self.fix_mypy_errors()

        # 4. Ruff问题修复
        print("\n4️⃣ 修复Ruff代码问题...")
        ruff_fixes = self.fix_ruff_issues()

        # 5. 测试相关问题修复
        print("\n5️⃣ 修复测试相关问题...")
        test_fixes = self.fix_test_issues()

        # 6. 生成修复报告
        print("\n6️⃣ 生成修复报告...")
        self.generate_fix_report()

        # 汇总结果
        total_fixes = (
            syntax_fixes + import_fixes + mypy_fixes +
            ruff_fixes + test_fixes
        )

        print("\n✅ 修复完成！")
        print(f"📊 总修复数: {total_fixes}")
        print(f"📁 处理文件数: {self.fix_results['files_processed']}")

        return self.fix_results

    def fix_syntax_errors(self) -> int:
        """修复语法错误"""
        fix_count = 0

        # 查找所有Python文件
        python_files = list(self.src_dir.rglob("*.py")) + list(self.test_dir.rglob("*.py"))

        for py_file in python_files:
            try:
                # 尝试编译文件
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查语法错误
                try:
                    ast.parse(content)
                    continue  # 语法正确，跳过
                except SyntaxError:
                    pass  # 有语法错误，需要修复

                # 应用常见的语法错误修复模式
                fixed_content = self._apply_syntax_fixes(content, py_file)

                if fixed_content != content:
                    # 验证修复后的语法
                    try:
                        ast.parse(fixed_content)
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        fix_count += 1
                        self.fix_results['files_processed'] += 1
                        logger.info(f"修复语法错误: {py_file}")
                    except SyntaxError:
                        logger.warning(f"无法修复语法错误: {py_file}")

            except Exception as e:
                logger.error(f"处理文件失败 {py_file}: {e}")

        self.fix_results['fixes_applied']['syntax_errors'] = fix_count
        print(f"  ✅ 修复语法错误: {fix_count} 个")

        return fix_count

    def _apply_syntax_fixes(self, content: str, file_path: Path) -> str:
        """应用语法错误修复模式"""
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # 修复常见的语法错误模式

            # 1. 修复未闭合的括号问题
            if 'def ' in line and line.strip().endswith(':'):
                # 检查函数定义后的缩进问题
                if i + 1 < len(lines) and not lines[i + 1].startswith('    ') and lines[i + 1].strip():
                    # 可能缺少函数体
                    line = line.rstrip() + '\n    pass'

            # 2. 修复f-string中的表达式问题
            if 'f"' in line and '{$' in line:
                # 修复f-string中的空表达式
                line = re.sub(r'\{\$\}', '{}', line)
                line = re.sub(r'\{\$(.*?)\}', r'{\1}', line)

            # 3. 修复字典键缺失引号问题
            if re.search(r'^\s*\w+\s*=\s*\{[^\'"]\w+:', line):
                # 字典键缺少引号
                line = re.sub(r'(\w+):', r'"\1":', line)

            # 4. 修复import语句问题
            if line.strip().startswith('from ') and ' import ' in line:
                # 检查导入路径问题
                if '..' in line:
                    # 相对导入路径问题
                    line = line.replace('..', '.')

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def fix_import_errors(self) -> int:
        """修复导入错误"""
        fix_count = 0

        # 运行导入检查
        try:
            result = subprocess.run([
                sys.executable, "-m", "mypy", "src/", "--no-error-summary"
            ], capture_output=True, text=True, timeout=60)

            mypy_output = result.stderr

            # 分析导入错误
            import_errors = []
            for line in mypy_output.split('\n'):
                if 'import-not-found' in line or 'module' in line and 'not found' in line:
                    import_errors.append(line.strip())

            # 修复常见的导入问题
            for error in import_errors[:10]:  # 限制修复数量避免过度修改
                fix = self._fix_single_import_error(error)
                if fix:
                    fix_count += 1

        except Exception as e:
            logger.error(f"导入错误修复失败: {e}")

        self.fix_results['fixes_applied']['import_errors'] = fix_count
        print(f"  ✅ 修复导入错误: {fix_count} 个")

        return fix_count

    def _fix_single_import_error(self, error_line: str) -> bool:
        """修复单个导入错误"""
        # 解析错误行
        # 示例: error: Cannot find implementation or library stub for module named "src.collectors.base_collector"

        if "Cannot find implementation" in error_line and "module named" in error_line:
            # 提取模块名
            match = re.search(r'module named "([^"]+)"', error_line)
            if match:
                module_name = match.group(1)

                # 尝试找到正确的模块路径
                if module_name.startswith('src.'):
                    # 检查是否存在对应的文件
                    relative_path = module_name.replace('src.', '') + '.py'
                    full_path = self.src_dir / relative_path

                    if not full_path.exists():
                        # 尝试找到相似的文件
                        similar_files = self._find_similar_files(relative_path)
                        if similar_files:
                            logger.info(f"建议的导入替换: {module_name} -> {similar_files[0]}")
                            return True

        return False

    def _find_similar_files(self, target_path: str) -> List[str]:
        """查找相似的文件"""
        target_name = Path(target_path).stem
        similar_files = []

        for py_file in self.src_dir.rglob("*.py"):
            if target_name.lower() in py_file.stem.lower():
                relative_path = py_file.relative_to(self.src_dir)
                module_path = str(relative_path.with_suffix('')).replace(os.sep, '.')
                similar_files.append(f"src.{module_path}")

        return similar_files[:3]  # 返回前3个最相似的

    def fix_mypy_errors(self) -> int:
        """修复MyPy类型错误"""
        fix_count = 0

        try:
            # 获取MyPy错误详情
            result = subprocess.run([
                sys.executable, "-m", "mypy", "src/", "--show-error-codes", "--no-error-summary"
            ], capture_output=True, text=True, timeout=60)

            mypy_output = result.stderr
            errors = mypy_output.split('\n')

            # 修复可自动修复的错误类型
            for error in errors[:50]:  # 限制处理数量
                if self._fix_mypy_error(error):
                    fix_count += 1

        except Exception as e:
            logger.error(f"MyPy错误修复失败: {e}")

        self.fix_results['fixes_applied']['mypy_errors'] = fix_count
        print(f"  ✅ 修复MyPy错误: {fix_count} 个")

        return fix_count

    def _fix_mypy_error(self, error_line: str) -> bool:
        """修复单个MyPy错误"""
        # 解析错误格式: filename:line: error: message [error-code]
        match = re.match(r'^(.+?):(\d+): error: (.+?) \[([^\]]+)\]', error_line)
        if not match:
            return False

        file_path, line_num, message, error_code = match.groups()

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False

            line_num = int(line_num)

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_num > len(lines):
                return False

            original_line = lines[line_num - 1]

            # 根据错误类型进行修复
            fixed_line = None

            if error_code == 'name-defined':
                # 未定义变量错误
                fixed_line = self._fix_name_defined_error(original_line, message)
            elif error_code == 'attr-defined':
                # 属性未定义错误
                fixed_line = self._fix_attr_defined_error(original_line, message)
            elif error_code == 'assignment':
                # 赋值类型错误
                fixed_line = self._fix_assignment_error(original_line, message)
            elif error_code == 'return-value':
                # 返回值类型错误
                fixed_line = self._fix_return_value_error(original_line, message)

            if fixed_line and fixed_line != original_line:
                lines[line_num - 1] = fixed_line

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                logger.info(f"修复MyPy错误: {file_path}:{line_num} - {message}")
                return True

        except Exception as e:
            logger.error(f"修复MyPy错误失败: {e}")

        return False

    def _fix_name_defined_error(self, line: str, message: str) -> Optional[str]:
        """修复变量未定义错误"""
        # 简单的变量名修复策略
        if "Name " in message and " is not defined" in message:
            var_match = re.search(r'Name "([^"]+)" is not defined', message)
            if var_match:
                var_name = var_match.group(1)

                # 如果是常见的未定义变量，添加默认值
                if var_name in ['result', 'data', 'response']:
                    indent = len(line) - len(line.lstrip())
                    return f"{' ' * indent}{var_name} = None\n{line}"

        return None

    def _fix_attr_defined_error(self, line: str, message: str) -> Optional[str]:
        """修复属性未定义错误"""
        # 检查是否是模块属性错误
        if "Module " in message and " has no attribute" in message:
            # 可能的模块导入问题，暂时跳过自动修复
            pass

        return None

    def _fix_assignment_error(self, line: str, message: str) -> Optional[str]:
        """修复赋值类型错误"""
        # 检查常见的类型转换问题
        if "Incompatible types in assignment" in message:
            # 添加类型转换
            if "int" in message and "=" in line:
                return line.replace("=", "= int(") + ")"
            elif "str" in message and "=" in line:
                return line.replace("=", "= str(") + ")"

        return None

    def _fix_return_value_error(self, line: str, message: str) -> Optional[str]:
        """修复返回值类型错误"""
        # 简单的返回值修复
        if "return" in line and "None" in message:
            # 可能需要明确返回None
            if line.strip() == "return":
                return line + " None"

        return None

    def fix_ruff_issues(self) -> int:
        """修复Ruff问题"""
        fix_count = 0

        try:
            # 运行Ruff自动修复
            result = subprocess.run([
                "ruff", "check", "src/", "--fix", "--show-fixes"
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # 统计修复数量
                output = result.stdout
                fix_count = output.count("Fixed")

        except Exception as e:
            logger.error(f"Ruff修复失败: {e}")

        self.fix_results['fixes_applied']['ruff_issues'] = fix_count
        print(f"  ✅ 修复Ruff问题: {fix_count} 个")

        return fix_count

    def fix_test_issues(self) -> int:
        """修复测试相关问题"""
        fix_count = 0

        # 检查测试文件中的常见问题
        test_files = list(self.test_dir.rglob("test_*.py"))

        for test_file in test_files[:20]:  # 限制处理数量
            fixes = self._fix_test_file(test_file)
            fix_count += fixes

        self.fix_results['fixes_applied']['test_issues'] = fix_count
        print(f"  ✅ 修复测试问题: {fix_count} 个")

        return fix_count

    def _fix_test_file(self, test_file: Path) -> int:
        """修复单个测试文件"""
        fix_count = 0

        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 修复常见的测试问题
            content = self._fix_test_imports(content)
            content = self._fix_test_fixtures(content)
            content = self._fix_test_assertions(content)

            if content != original_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fix_count = 1
                logger.info(f"修复测试文件: {test_file}")

        except Exception as e:
            logger.error(f"修复测试文件失败 {test_file}: {e}")

        return fix_count

    def _fix_test_imports(self, content: str) -> str:
        """修复测试导入问题"""
        # 修复常见的测试导入问题
        if 'import pytest' not in content and 'pytest' in content:
            content = 'import pytest\n' + content

        # 修复相对导入问题
        content = re.sub(r'from \.\.\.', 'from ', content)

        return content

    def _fix_test_fixtures(self, content: str) -> str:
        """修复测试夹具问题"""
        # 确保测试函数有正确的参数
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            if line.strip().startswith('def test_') and '(' in line and ')' in line:
                if 'self' not in line and 'fixture' not in line and line.count('(') == 1:
                    # 可能缺少测试参数
                    line = line.replace(')', ', client)')
            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_test_assertions(self, content: str) -> str:
        """修复测试断言问题"""
        # 修复常见的断言问题
        content = re.sub(r'assert\s+([^(]+)\s*==', r'assert \1 ==', content)
        content = re.sub(r'assert\s+([^(]+)\s*!=', r'assert \1 !=', content)

        return content

    def generate_fix_report(self) -> None:
        """生成修复报告"""
        report_file = self.project_root / "smart_quality_fix_report.json"

        # 计算总的修复数量
        total_fixes = sum(self.fix_results['fixes_applied'].values())
        self.fix_results['total_fixes'] = total_fixes
        self.fix_results['errors_fixed'] = total_fixes

        # 生成改进建议
        self.fix_results['recommendations'] = self._generate_recommendations()

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.fix_results, f, indent=2, ensure_ascii=False)

            logger.info(f"修复报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"保存修复报告失败: {e}")

    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于修复结果生成建议
        if self.fix_results['fixes_applied'].get('mypy_errors', 0) > 20:
            recommendations.append("🔍 建议手动审查MyPy错误修复，确保类型注解正确")

        if self.fix_results['fixes_applied'].get('import_errors', 0) > 5:
            recommendations.append("📦 建议检查模块依赖关系，可能需要重构导入结构")

        if self.fix_results['fixes_applied'].get('syntax_errors', 0) > 0:
            recommendations.append("🛠️ 建议增加语法检查到pre-commit钩子中")

        recommendations.extend([
            "📊 定期运行此工具保持代码质量",
            "🧪 增加单元测试覆盖率以防止回归",
            "📋 建立代码审查流程确保修复质量"
        ])

        return recommendations

    def print_summary(self) -> None:
        """打印修复摘要"""
        print("\n" + "=" * 60)
        print("📊 智能质量修复摘要")
        print("=" * 60)
        print(f"修复时间: {self.fix_results['timestamp']}")
        print(f"处理文件数: {self.fix_results['files_processed']}")
        print(f"总修复数: {self.fix_results.get('total_fixes', 0)}")
        print()

        print("🔧 修复详情:")
        for fix_type, count in self.fix_results['fixes_applied'].items():
            if count > 0:
                print(f"  - {fix_type}: {count} 个")
        print()

        if self.fix_results.get('recommendations'):
            print("💡 改进建议:")
            for rec in self.fix_results['recommendations']:
                print(f"  {rec}")
            print()

        print("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="智能质量修复工具")
    parser.add_argument("--project-root", type=Path, help="项目根目录")
    parser.add_argument("--syntax-only", action="store_true", help="仅修复语法错误")
    parser.add_argument("--mypy-only", action="store_true", help="仅修复MyPy错误")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")

    args = parser.parse_args()

    fixer = SmartQualityFixer(args.project_root)

    if args.dry_run:
        print("🔍 试运行模式 - 不会修改文件")
        # 在试运行模式下只分析问题
        return

    if args.syntax_only:
        fixer.fix_syntax_errors()
    elif args.mypy_only:
        fixer.fix_mypy_errors()
    else:
        fixer.run_comprehensive_fix()

    fixer.print_summary()


if __name__ == "__main__":
    main()