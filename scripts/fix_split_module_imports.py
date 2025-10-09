#!/usr/bin/env python3
"""
修复拆分模块的导入问题

修复恢复的拆分模块中缺失的导入。
"""

import os
from pathlib import Path
from typing import Dict, List, Set

def fix_audit_service_imports():
    """修复audit_service_mod的导入问题"""
    print("修复audit_service_mod的导入问题...")

    service_file = Path("src/services/audit_service_mod/service.py")
    if not service_file.exists():
        print(f"文件不存在: {service_file}")
        return

    content = service_file.read_text(encoding='utf-8')

    # 检查并添加缺失的导入
    if "BaseService" in content and "BaseService" not in content.split("\n")[0]:
        # 在现有导入后添加BaseService导入
        import_lines = []
        for line in content.split("\n"):
            if line.startswith("from ") or line.startswith("import "):
                import_lines.append(line)
            elif line.strip() == "" and import_lines:
                break

        # 查找最后一个导入位置
        last_import = 0
        for i, line in enumerate(content.split("\n")):
            if line.startswith("from ") or line.startswith("import "):
                last_import = i

        # 插入BaseService导入
        lines = content.split("\n")
        lines.insert(last_import + 1, "from src.services.base_service import BaseService")
        content = "\n".join(lines)

        service_file.write_text(content, encoding='utf-8')
        print("✓ 添加了BaseService导入")

def fix_manager_imports():
    """修复manager_mod的导入问题"""
    print("\n修复manager_mod的导入问题...")

    manager_file = Path("src/services/manager_mod.py")
    if not manager_file.exists():
        print(f"文件不存在: {manager_file}")
        return

    # 检查是否已经有manager模块
    manager_dir = Path("src/services/manager")
    if not manager_dir.exists():
        print("✗ 找不到manager目录，manager_mod可能引用了不存在的模块")
        # 从原始manager.py复制
        original = Path("src/services/manager.py")
        if original.exists():
            manager_dir.mkdir(exist_ok=True)
            target = manager_dir / "manager.py"
            if not target.exists():
                target.write_text(original.read_text(encoding='utf-8'), encoding='utf-8')
                print("✓ 复制了原始manager.py到manager目录")

def fix_data_processing_imports():
    """修复data_processing_mod的导入问题"""
    print("\n修复data_processing_mod的导入问题...")

    service_file = Path("src/services/data_processing_mod/service.py")
    if not service_file.exists():
        print(f"文件不存在: {service_file}")
        return

    content = service_file.read_text(encoding='utf-8')

    # 添加BaseService导入
    if "BaseService" in content and "BaseService" not in content.split("\n")[0:10]:
        lines = content.split("\n")

        # 查找导入区域
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                last_import = i

        lines.insert(last_import + 1, "from src.services.base_service import BaseService")
        content = "\n".join(lines)

        service_file.write_text(content, encoding='utf-8')
        print("✓ 添加了BaseService导入")

def check_base_service():
    """检查BaseService是否存在"""
    base_service = Path("src/services/base_service.py")
    if not base_service.exists():
        print("\n⚠️  BaseService不存在，尝试从EnhancedBaseService创建...")

        # 尝试从enhanced_base_service导入
        enhanced = Path("src/services/enhanced_base_service.py")
        if enhanced.exists():
            content = enhanced.read_text(encoding='utf-8')
            # 替换类名
            content = content.replace("class EnhancedBaseService", "class BaseService")
            base_service.write_text(content, encoding='utf-8')
            print("✓ 创建了BaseService（基于EnhancedBaseService）")
        else:
            print("✗ 找不到EnhancedBaseService，需要手动创建BaseService")

def main():
    """主函数"""
    print("=" * 60)
    print("修复拆分模块的导入问题")
    print("=" * 60)

    # 首先检查BaseService
    check_base_service()

    # 修复各个模块
    fix_audit_service_imports()
    fix_manager_imports()
    fix_data_processing_imports()

    print("\n" + "=" * 60)
    print("导入修复完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()