#!/usr/bin/env python3
"""
清理src目录的垃圾文件
删除.pyc、__pycache__和其他临时文件
"""

import os
import shutil
from pathlib import Path
import re


def clean_src_directory():
    """清理src目录"""
    src_path = Path("src")

    if not src_path.exists():
        print("❌ src目录不存在")
        return

    print("🧹 开始清理src目录...")

    # 1. 删除所有__pycache__目录
    print("\n1️⃣ 清理__pycache__目录...")
    pycache_dirs = list(src_path.rglob("__pycache__"))

    removed_pycache = 0
    for cache_dir in pycache_dirs:
        if cache_dir.is_dir():
            print(f"   删除: {cache_dir.relative_to(src_path)}")
            shutil.rmtree(cache_dir)
            removed_pycache += 1

    print(f"   ✅ 删除了 {removed_pycache} 个__pycache__目录")

    # 2. 删除所有.pyc文件
    print("\n2️⃣ 清理.pyc文件...")
    pyc_files = list(src_path.rglob("*.pyc"))

    removed_pyc = 0
    for pyc_file in pyc_files:
        if pyc_file.is_file():
            print(f"   删除: {pyc_file.relative_to(src_path)}")
            pyc_file.unlink()
            removed_pyc += 1

    print(f"   ✅ 删除了 {removed_pyc} 个.pyc文件")

    # 3. 删除.pyo文件（优化后的字节码）
    print("\n3️⃣ 清理.pyo文件...")
    pyo_files = list(src_path.rglob("*.pyo"))

    removed_pyo = 0
    for pyo_file in pyo_files:
        if pyo_file.is_file():
            print(f"   删除: {pyo_file.relative_to(src_path)}")
            pyo_file.unlink()
            removed_pyo += 1

    print(f"   ✅ 删除了 {removed_pyo} 个.pyo文件")

    # 4. 删除pytest缓存
    print("\n4️⃣ 清理pytest缓存...")
    pytest_cache = src_path / ".pytest_cache"
    if pytest_cache.exists():
        print("   删除: .pytest_cache")
        shutil.rmtree(pytest_cache)

    # 5. 判断是否有mypy缓存
    mypy_cache = src_path / ".mypy_cache"
    if mypy_cache.exists():
        print("   删除: .mypy_cache")
        shutil.rmtree(mypy_cache)

    # 6. 查找并报告调试代码
    print("\n5️⃣ 检查调试代码...")
    debug_patterns = {
        "print(": "print语句",
        "import pdb": "pdb调试",
        "import ipdb": "ipdb调试",
        "breakpoint()": "断点调试",
        "TODO:": "待办事项",
        "FIXME:": "需要修复",
        "XXX:": "警告标记",
        "HACK:": "临时方案",
    }

    files_with_debug = {}
    for pattern, description in debug_patterns.items():
        files = []
        for py_file in src_path.rglob("*.py"):
            if py_file.is_file():
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if pattern in content:
                        files.append(py_file.relative_to(src_path))
                except Exception:
                    pass
        if files:
            files_with_debug[description] = files

    if files_with_debug:
        print("\n   ⚠️  发现以下调试代码：")
        for desc, files in files_with_debug.items():
            print(f"   - {desc}: {len(files)} 个文件")
            for file in files[:3]:  # 只显示前3个
                print(f"     • {file}")
            if len(files) > 3:
                print(f"     • ... 还有 {len(files) - 3} 个文件")

    # 7. 查找空的__init__.py文件
    print("\n6️⃣ 检查空的__init__.py文件...")
    empty_inits = []
    for init_file in src_path.rglob("__init__.py"):
        if init_file.is_file():
            content = init_file.read_text(encoding="utf-8").strip()
            if not content or content == '""""""':
                empty_inits.append(init_file.relative_to(src_path))

    if empty_inits:
        print(f"   ⚠️  发现 {len(empty_inits)} 个空的__init__.py文件")
        for init in empty_inits[:5]:
            print(f"     • {init}")
        if len(empty_inits) > 5:
            print(f"     • ... 还有 {len(empty_inits) - 5} 个")

    # 8. 检查测试文件是否混在src中
    print("\n7️⃣ 检查测试文件...")
    test_files_in_src = list(src_path.rglob("*test*.py"))
    test_files_in_src.extend(src_path.rglob("test_*.py"))

    if test_files_in_src:
        print(f"   ⚠️  发现 {len(test_files_in_src)} 个测试文件在src目录中：")
        for test_file in test_files_in_src[:5]:
            print(f"     • {test_file.relative_to(src_path)}")
        if len(test_files_in_src) > 5:
            print(f"     • ... 还有 {len(test_files_in_src) - 5} 个")

    # 9. 统计结果
    print("\n📊 清理结果：")

    total_py_files = len(list(src_path.rglob("*.py")))
    total_dirs = len([d for d in src_path.rglob("*") if d.is_dir()])
    total_size_mb = sum(
        f.stat().st_size for f in src_path.rglob("*") if f.is_file()
    ) / (1024 * 1024)

    print(f"   - Python文件数: {total_py_files}")
    print(f"   - 目录数: {total_dirs}")
    print(f"   - 总大小: {total_size_mb:.2f}MB")
    print(f"   - 删除__pycache__: {removed_pycache}")
    print(f"   - 删除.pyc文件: {removed_pyc}")
    print(f"   - 删除.pyo文件: {removed_pyo}")

    # 10. 创建.gitignore建议
    print("\n💡 建议：确保.gitignore包含以下内容：")
    gitignore_content = """
# Python缓存
__pycache__/
*.py[cod]
*$py.class

# 测试覆盖率
.coverage
htmlcov/

# pytest缓存
.pytest_cache/

# mypy缓存
.mypy_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 环境变量
.env
.env.local
.env.*.local
"""
    print(gitignore_content)

    print("\n✅ src目录清理完成！")


if __name__ == "__main__":
    clean_src_directory()
