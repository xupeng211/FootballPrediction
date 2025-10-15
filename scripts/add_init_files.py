#!/usr/bin/env python3
"""
批量添加缺失的__init__.py文件
"""

from pathlib import Path
import os

def add_missing_init_files():
    """批量添加缺失的__init__.py文件"""

    src_path = Path('src')
    missing_inits = []
    added_count = 0

    print("扫描缺失的__init__.py文件...")

    # 扫描所有目录（不包括src本身）
    for dir_path in sorted(src_path.rglob('*/')):
        # 跳过__pycache__目录
        if '__pycache__' in dir_path.parts:
            continue

        init_file = dir_path / '__init__.py'

        if not init_file.exists():
            missing_inits.append(dir_path)
            # 创建__init__.py文件
            init_file.write_text('"""初始化模块"""\n')
            added_count += 1
            print(f"  ✅ {init_file.relative_to(src_path)}")

    print(f"\n统计结果:")
    print(f"  - 找到 {len(missing_inits)} 个缺失__init__.py的目录")
    print(f"  - 已添加 {added_count} 个__init__.py文件")

    return added_count

def verify_init_files():
    """验证__init__.py文件"""
    print("\n验证__init__.py文件...")

    src_path = Path('src')
    error_count = 0
    total_dirs = 0

    for dir_path in src_path.rglob('*/'):
        if '__pycache__' in dir_path.parts:
            continue

        total_dirs += 1
        init_file = dir_path / '__init__.py'

        if not init_file.exists():
            print(f"  ❌ {init_file.relative_to(src_path)}")
            error_count += 1

    if error_count == 0:
        print(f"  ✅ 所有 {total_dirs} 个目录都有__init__.py")
    else:
        print(f"  ⚠️ 仍有 {error_count} 个目录缺少__init__.py")

    return error_count

def main():
    """主函数"""
    print("=" * 60)
    print("           批量添加__init__.py文件")
    print("=" * 60)

    # 添加缺失的__init__.py文件
    added_count = add_missing_init_files()

    # 验证结果
    error_count = verify_init_files()

    # 清理.pyc文件
    print("\n清理Python缓存文件...")
    for pyc_file in Path('src').rglob('*.pyc'):
        pyc_file.unlink()
    print(f"  ✅ 清理了 {list(Path('src').rglob('*.pyc'))} 个.pyc文件")

    # 清理__pycache__目录
    for cache_dir in Path('src').rglob('__pycache__'):
        if cache_dir.is_dir():
            import shutil
            shutil.rmtree(cache_dir)
    print(f"  ✅ 清理了__pycache__目录")

    print("\n" + "=" * 60)
    if error_count == 0:
        print("🎉 包结构修复完成！")
    else:
        print("⚠️ 部分目录仍有问题需要手动处理")
    print("=" * 60)

if __name__ == "__main__":
    main()