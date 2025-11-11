#!/usr/bin/env python3
"""
修复B024抽象基类错误的脚本
为空的ABC类添加抽象方法或移除ABC继承
"""

import os
import re

def fix_test_interface_classes(file_path):
    """修复测试文件中的TestInterface类"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 替换空的TestInterface类，添加一个抽象方法
        pattern = r'class (TestInterface|ITestService|IRepository|IService)\(ABC\):\s*\n\s*pass'
        replacement = r'class \1(ABC):\n            """测试接口"""\n            @abstractmethod\n            def test_method(self) -> None:\n                """测试方法"""\n                pass'
        
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            # 确保导入了abstractmethod
            if 'from abc import' not in content and 'import abc' not in content:
                lines = content.split('\n')
                import_pos = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')):
                        import_pos = i + 1
                lines.insert(import_pos, 'from abc import ABC, abstractmethod')
                content = '\n'.join(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的抽象基类")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_base_adapter(file_path):
    """修复BaseAdapter类"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复BaseAdapter类
        pattern = r'class BaseAdapter\(ABC\):\s*\n\s*"""基础适配器抽象类"""'
        replacement = r'class BaseAdapter(ABC):\n        """基础适配器抽象类"""\n        \n        @abstractmethod\n        def connect(self) -> bool:\n            """连接方法"""\n            pass'
        
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            # 确保导入了abstractmethod
            if 'from abc import' not in content and 'import abc' not in content:
                lines = content.split('\n')
                import_pos = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')):
                        import_pos = i + 1
                lines.insert(import_pos, 'from abc import ABC, abstractmethod')
                content = '\n'.join(lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的BaseAdapter抽象基类")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复B024抽象基类错误...")

    # 需要修复的文件
    files_to_fix = [
        "tests/unit/adapters/test_adapters_standalone.py",
        "tests/unit/test_auto_binding_comprehensive.py"
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if file_path.endswith("test_adapters_standalone.py"):
                if fix_base_adapter(file_path):
                    fixed_count += 1
            else:
                if fix_test_interface_classes(file_path):
                    fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"🎯 修复完成！共修复了 {fixed_count} 个抽象基类问题")

if __name__ == "__main__":
    main()
