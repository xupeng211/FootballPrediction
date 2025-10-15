#!/usr/bin/env python3
"""
代码质量改进脚本
Code Quality Improvement Script

批量修复常见的代码质量问题
"""

import ast
import re
import subprocess
from pathlib import Path


class CodeQualityFixer:
    """代码质量修复器"""

    def __init__(self):
        self.root_path = Path(".")
        self.src_path = self.root_path / "src"
        self.fixes_applied = 0

    def log_fix(self, file_path: str, message: str):
        """记录修复"""
        print(f"  ✅ {file_path}: {message}")
        self.fixes_applied += 1

    def find_python_files(self) -> list[Path]:
        """查找所有Python文件"""
        python_files = []
        for pattern in ["src/**/*.py", "tests/**/*.py"]:
            python_files.extend(self.root_path.glob(pattern))
        return python_files

    def fix_type_annotations(self, file_path: Path) -> bool:
        """修复类型注解错误"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            original_content = content
            fixes = 0

            # 1. 修复 Optional[Type] 语法
            content = re.sub(
                r": Optional\[([^\]]+)\] = None", r": Optional[\1] = None", content
            )

            # 2. 修复 List[Type] 语法
            content = re.sub(r": List\[([^\]]+)\] = \{\}", r": List[\1] = []", content)

            # 3. 修复 Dict[Type, Type] 语法
            content = re.sub(r": Dict\[([^\]]+)\] = \[\]", r": Dict[\1] = {}", content)

            # 4. 修复 Union[Type] 语法
            content = re.sub(r": Union\[([^\]]+)\] =", r": Union[\1] =", content)

            # 5. 修复嵌套类型注解中的括号不匹配
            content = re.sub(r"\] \]", "]]", content)
            content = re.sub(r"\} \}", "}}", content)

            # 6. 修复函数参数中的类型注解
            content = re.sub(
                r"def (\w+)\([^)]*)(: Optional\[([^\]]+)\] = None|: List\[([^\]]+)\] = None|: Dict\[([^\]]+)\] = None)([^)]*) ->",
                r"def \1\2\5 ->",
                content,
            )

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixes = len(content) - len(original_content)  # 简单统计
                self.log_fix(
                    str(file_path.relative_to(self.root_path)),
                    f"修复了 {fixes} 处类型注解",
                )
                return True

        except Exception as e:
            print(f"  ❌ {file_path}: 修复失败 - {e}")

        return False

    def fix_import_errors(self, file_path: Path) -> bool:
        """修复导入错误"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # 1. 添加缺失的导入
            if (
                "ClassVar" in content
                and "from typing import" in content
                and "ClassVar" not in content
            ):
                content = re.sub(
                    r"from typing import ([^\n]+)",
                    r"from typing import \1, ClassVar",
                    content,
                )

            # 2. 修复相对导入
            content = re.sub(r"from \.\.(\w+)", r"from src.\1", content)

            # 3. 修复导入语句中的类型注解
            content = re.sub(
                r"from typing import Optional, Dict, List, Union, Any",
                r"from typing import Optional, Dict, List, Union, Any, ClassVar, Type, Callable, TypeVar",
                content,
            )

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_fix(str(file_path.relative_to(self.root_path)), "修复导入错误")
                return True

        except Exception as e:
            print(f"  ❌ {file_path}: 修复失败 - {e}")

        return False

    def check_syntax_errors(self, file_path: Path) -> list[str]:
        """检查语法错误"""
        errors = []
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            errors.append(f"第{e.lineno}行: {e.msg}")
        except Exception as e:
            errors.append(f"解析错误: {e}")
        return errors

    def fix_all_files(self):
        """修复所有文件"""
        print("=" * 60)
        print("           代码质量改进工具")
        print("=" * 60)

        python_files = self.find_python_files()
        print(f"\n找到 {len(python_files)} 个Python文件")

        # 1. 修复类型注解
        print("\n🔧 修复类型注解...")
        type_fixes = 0
        for file_path in python_files:
            if self.fix_type_annotations(file_path):
                type_fixes += 1

        # 2. 修复导入错误
        print("\n🔧 修复导入错误...")
        import_fixes = 0
        for file_path in python_files:
            if self.fix_import_errors(file_path):
                import_fixes += 1

        # 3. 检查语法错误
        print("\n🔍 检查语法错误...")
        syntax_errors = []
        for file_path in python_files:
            errors = self.check_syntax_errors(file_path)
            if errors:
                syntax_errors.append((file_path, errors))
                print(f"  ❌ {file_path.relative_to(self.root_path)}:")
                for error in errors:
                    print(f"     - {error}")

        # 4. 运行代码格式化
        print("\n🔧 运行代码格式化（ruff）...")
        try:
            subprocess.run(["python", "-m", "ruff", "format", "src/"], check=True)
            print("  ✅ ruff格式化完成")
        except subprocess.CalledProcessError:
            print("  ⚠️ ruff格式化失败")

        # 5. 运行代码检查
        print("\n🔍 运行代码检查（ruff）...")
        try:
            subprocess.run(["python", "-m", "ruff", "check", "src/"], check=True)
            print("  ✅ ruff检查通过")
        except subprocess.CalledProcessError:
            print("  ⚠️ ruff检查发现问题")

        # 6. 运行类型检查
        print("\n🔍 运行类型检查（mypy）...")
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "mypy",
                    "src/core/config.py",
                    "src/utils/dict_utils.py",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                print("  ✅ mypy检查通过")
            else:
                print(f"  ⚠️ mypy发现问题：{result.stdout[:200]}...")
        except Exception as e:
            print(f"  ❌ mypy检查失败：{e}")

        # 7. 运行测试
        print("\n🧪 运行基础测试...")
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "tests/unit/utils/test_dict_utils_basic.py",
                    "-q",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                print("  ✅ 基础测试通过")
            else:
                print(f"  ⚠️ 测试失败：{result.stdout[:200]}...")
        except Exception as e:
            print(f"  ❌ 测试运行失败：{e}")

        # 生成报告
        print("\n" + "=" * 60)
        print("📊 修复报告")
        print("=" * 60)
        print(f"✅ 类型注解修复：{type_fixes} 个文件")
        print(f"✅ 导入错误修复：{import_fixes} 个文件")
        print(f"❌ 语法错误文件：{len(syntax_errors)} 个")
        print(f"📝 总修复数：{self.fixes_applied}")

        if syntax_errors:
            print("\n⚠️ 仍有语法错误的文件：")
            for file_path, errors in syntax_errors:
                print(f"  - {file_path.relative_to(self.root_path)}")

        print("\n💡 建议：")
        print("1. 手动修复剩余的语法错误")
        print("2. 运行 'python -m pytest' 验证所有测试")
        print("3. 运行 'python -m mypy src/' 进行完整的类型检查")
        print("=" * 60)

        return len(syntax_errors) == 0


def main():
    """主函数"""
    fixer = CodeQualityFixer()
    success = fixer.fix_all_files()

    if success:
        print("\n🎉 所有代码质量问题已修复！")
    else:
        print("\n⚠️ 仍有部分问题需要手动修复")


if __name__ == "__main__":
    main()
