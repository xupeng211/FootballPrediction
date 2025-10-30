#!/usr/bin/env python3
"""
🔧 isinstance语法错误专用修复工具
专门修复项目中大量存在的isinstance函数调用错误

问题：isinstance(x, (type1, type2, type3)) 在Python中应该是2个参数，但代码中传入了3个参数
"""

import os
import re
from pathlib import Path
from typing import List, Dict

class IsinstanceErrorFixer:
    """isinstance错误修复器"""

    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.fixes_applied = 0

    def fix_project_isinstance_errors(self, source_dir: str = "src") -> Dict:
        """修复项目中的isinstance语法错误"""
        print("🔧 开始修复isinstance语法错误...")

        source_path = Path(source_dir)
        python_files = list(source_path.rglob("*.py"))

        print(f"📂 发现 {len(python_files)} 个Python文件")

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            print(f"   🔍 修复: {py_file}")
            self._fix_file_isinstance_errors(py_file)

        summary = {
            'total_files': len(python_files),
            'fixed_files': len(self.fixed_files),
            'failed_files': len(self.failed_files),
            'fixes_applied': self.fixes_applied,
            'fixed_files_list': [str(f) for f in self.fixed_files],
            'failed_files_list': [str(f) for f in self.failed_files]
        }

        print("\n📊 isinstance修复结果:")
        print(f"   总文件数: {summary['total_files']}")
        print(f"   修复成功: {summary['fixed_files']}")
        print(f"   修复失败: {summary['failed_files']}")
        print(f"   修复应用: {summary['fixes_applied']}")

        return summary

    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__",
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "site-packages",
            ".git",
            "migrations"  # 跳过数据库迁移文件
        ]

        for pattern in skip_patterns:
            if pattern in str(file_path):
                return True

        return False

    def _fix_file_isinstance_errors(self, file_path: Path) -> bool:
        """修复单个文件的isinstance错误"""
        try:
            # 读取原始内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 应用isinstance修复
            fixed_content, fixes_count = self._apply_isinstance_fixes(original_content)

            if fixes_count == 0:
                print(f"      ✅ {file_path.name} 无需修复")
                return True

            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

            print(f"      ✅ {file_path.name} 修复了 {fixes_count} 处错误")
            self.fixed_files.append(file_path)
            self.fixes_applied += fixes_count
            return True

        except Exception as e:
            print(f"      ❌ {file_path.name} 修复失败: {e}")
            self.failed_files.append(file_path)
            return False

    def _apply_isinstance_fixes(self, content: str) -> tuple[str, int]:
        """应用isinstance修复"""
        fixed_content = content
        fixes_applied = 0

        # 修复模式1: isinstance(x, (type1, type2, type3)) -> isinstance(x, (type1, type2))
        # 这种模式通常是因为有3个类型参数，需要截断为2个
        pattern1 = r'\bisinstance\s*\(\s*([^,]+),\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)\s*\)'

        def fix_isinstance_triple(match):
            nonlocal fixes_applied
            obj = match.group(1).strip()
            type1 = match.group(2).strip()
            type2 = match.group(3).strip()
            match.group(4).strip()

            fixes_applied += 1
            return f"isinstance({obj}, ({type1}, {type2}))"

        fixed_content = re.sub(pattern1, fix_isinstance_triple, fixed_content, flags=re.MULTILINE)

        # 修复模式2: isinstance(x, type1, type2, type3) -> isinstance(x, (type1, type2))
        # 这种模式是直接传入了多个类型参数，需要包装为元组并截断
        pattern2 = r'\bisinstance\s*\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'

        def fix_isinstance_direct(match):
            nonlocal fixes_applied
            obj = match.group(1).strip()
            type1 = match.group(2).strip()
            type2 = match.group(3).strip()
            match.group(4).strip()

            fixes_applied += 1
            return f"isinstance({obj}, ({type1}, {type2}))"

        fixed_content = re.sub(pattern2, fix_isinstance_direct, fixed_content, flags=re.MULTILINE)

        # 修复模式3: isinstance(x, type1, type2) -> isinstance(x, (type1, type2))
        # 两个类型参数的情况
        pattern3 = r'\bisinstance\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'

        def fix_isinstance_double(match):
            nonlocal fixes_applied
            obj = match.group(1).strip()
            type1 = match.group(2).strip()
            type2 = match.group(3).strip()

            fixes_applied += 1
            return f"isinstance({obj}, ({type1}, {type2}))"

        fixed_content = re.sub(pattern3, fix_isinstance_double, fixed_content, flags=re.MULTILINE)

        return fixed_content, fixes_applied

def main():
    """主函数"""
    print("🚀 isinstance语法错误专用修复工具启动...")
    print("=" * 60)

    fixer = IsinstanceErrorFixer()

    # 修复src目录
    print("📁 修复 src/ 目录 isinstance 错误...")
    src_summary = fixer.fix_project_isinstance_errors("src")

    # 验证修复效果
    print("\n🧪 验证修复效果...")
    import ast

    test_files = list(Path("src").rglob("*.py"))[:20]  # 测试前20个文件
    success_count = 0

    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            success_count += 1
        except:
            pass

    print(f"   测试文件解析成功率: {success_count}/{len(test_files)} ({success_count/len(test_files)*100:.1f}%)")

    # 保存修复报告
    import json
    with open('isinstance_fix_report.json', 'w', encoding='utf-8') as f:
        json.dump(src_summary, f, indent=2, ensure_ascii=False)

    print("\n📄 详细报告: isinstance_fix_report.json")

    # 给出下一步建议
    print("\n🎯 下一步建议:")
    if src_summary['fixes_applied'] > 0:
        print("   ✅ isinstance错误修复完成")
        print("   📋 建议: 现在可以重新运行Phase G智能分析器")
        print("   📋 命令: python3 scripts/intelligent_test_gap_analyzer.py")
    else:
        print("   ⚠️ 未发现isinstance错误")
        print("   📋 建议: 检查其他类型的语法错误")

    return src_summary

if __name__ == "__main__":
    main()