#!/usr/bin/env python3
"""
查找循环导入和意外的导入链
"""
import ast
import os
from pathlib import Path

def find_imports_in_file(file_path):
    """查找文件中的所有导入"""
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
    except Exception as e:
        print(f"解析文件失败 {file_path}: {e}")

    return imports

def main():
    """查找导致src.core被导入的地方"""
    project_root = Path("/home/user/projects/FootballPrediction/src")

    # 首先查找哪些文件直接导入了src.core
    core_importers = []

    for py_file in project_root.rglob("*.py"):
        if py_file.name.startswith("__init__"):
            continue

        imports = find_imports_in_file(py_file)

        for imp in imports:
            if imp.startswith('src.core') or imp == 'src.core':
                rel_path = py_file.relative_to(project_root)
                core_importers.append(str(rel_path))
                break

    print("以下文件直接导入了src.core:")
    for importer in sorted(core_importers):
        print(f"  - {importer}")

    # 查找football_data_cleaner的导入
    print("\n检查football_data_cleaner的导入:")
    fdc_path = project_root / "data/processing/football_data_cleaner.py"
    if fdc_path.exists():
        imports = find_imports_in_file(fdc_path)
        for imp in sorted(imports):
            print(f"  - {imp}")

    # 检查feature_store的导入
    print("\n检查feature_store的导入:")
    fs_path = project_root / "features/feature_store.py"
    if fs_path.exists():
        imports = find_imports_in_file(fs_path)
        for imp in sorted(imports):
            print(f"  - {imp}")

if __name__ == "__main__":
    main()