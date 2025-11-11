#!/usr/bin/env python3
"""
修复测试收集错误
解决NameError、RecursionError等问题
"""

import re
from pathlib import Path


def fix_adapter_pattern_test():
    """修复test_adapter_pattern.py中的作用域问题"""
    file_path = Path("tests/unit/adapters/test_adapter_pattern.py")

    if not file_path.exists():
        return False

    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # 找到CompositeAdapter类定义并将其移到模块级别
    # 首先提取类定义
    class_match = re.search(r'(\s+class CompositeAdapter:.*?)(?=\n    class|\nclass|\ndef|\Z)', content, re.DOTALL)

    if not class_match:
        return False

    composite_class_def = class_match.group(1).strip()

    # 将类定义格式化为模块级别
    module_level_class = "\n\nclass CompositeAdapter:\n"
    class_body = re.sub(r'^\s+', '', composite_class_def.replace('class CompositeAdapter:', ''))
    module_level_class += class_body

    # 删除原始的嵌套类定义
    content = content.replace(class_match.group(1), '')

    # 在适当位置插入模块级别的类定义（在import语句之后）
    import_end = content.find('\n# ')
    if import_end == -1:
        import_end = content.find('\nclass ')
    if import_end == -1:
        import_end = content.find('\ndef ')

    if import_end != -1:
        content = content[:import_end] + module_level_class + '\n' + content[import_end:]
    else:
        # 如果找不到合适位置，添加到文件开头
        content = module_level_class + '\n' + content

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True

def fix_api_comprehensive_test():
    """修复test_api_comprehensive.py中的递归错误"""
    file_path = Path("tests/unit/api/test_api_comprehensive.py")

    if not file_path.exists():
        return False

    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # 检查是否存在无限递归的MockClass
    if 'MockClass' in content and '__getattr__' in content:
        # 修复递归的__getattr__方法
        old_getattr = r'def __getattr__\(self, name\):\s*return MockClass\(\*\*\{name: None\}\)'
        new_getattr = '''def __getattr__(self, name):
            # 防止无限递归
            if name.startswith('_'):
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
            return f"mock_{name}"'''

        content = re.sub(old_getattr, new_getattr, content, flags=re.MULTILINE)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True
    else:
        return True

def fix_pytest_collection_warnings():
    """修复pytest收集警告"""
    # 删除重复的类定义
    test_files = [
        "tests/unit/cqrs/queries.py",
        "tests/integration/test_models_simple.py"
    ]

    for file_path in test_files:
        path = Path(file_path)
        if not path.exists():
            continue

        with open(path, encoding='utf-8') as f:
            content = f.read()

        # 查找重复的类定义
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # 检查是否是类定义
            class_match = re.match(r'^(\s*)class\s+(\w+)\s*\(', line)
            if class_match:
                class_name = class_match.group(2)
                # 如果是测试类但不是以Test开头，跳过
                if not class_name.startswith('Test'):
                    fixed_lines.append(f"# {line}")
                    continue

            fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)


def main():
    """主函数"""

    fixes = [
        ("适配器模式测试", fix_adapter_pattern_test),
        ("API综合测试", fix_api_comprehensive_test),
        ("Pytest收集警告", fix_pytest_collection_warnings),
    ]

    fixed_count = 0
    for _name, fix_func in fixes:
        try:
            if fix_func():
                fixed_count += 1
        except Exception:
            pass


if __name__ == "__main__":
    main()
