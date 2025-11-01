#!/usr/bin/env python3
"""
清理重复的基础服务类
"""

import os
import shutil
from pathlib import Path


def main():
    """主函数"""
    print("🧹 清理重复的基础服务类...\n")

    # 检查是否还有文件使用废弃的导入
    print("1. 检查是否还有文件使用废弃的导入...")

    # 搜索使用废弃导入的文件
    deprecated_imports = [
        "from src.services.base import",
        "from src.services.base_service import",
    ]

    files_to_update = []

    for root, dirs, files in os.walk("src"):
        # 跳过 .venv 和其他目录
        dirs[:] = [d for d in dirs if d not in [".venv", "__pycache__", ".git"]]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    for deprecated in deprecated_imports:
                        if deprecated in content:
                            files_to_update.append(file_path)
                            print(f"   ⚠️ 需要更新: {file_path}")
                            break
                    pass

    if not files_to_update:
        print("   ✅ 没有文件使用废弃的导入")
    else:
        print(f"\n   需要更新 {len(files_to_update)} 个文件")
        # 这里可以添加自动更新逻辑

    print("\n2. 创建备份目录...")
    backup_dir = Path("backup/deprecated_services")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 要移动到备份的文件列表
    deprecated_files = ["src/services/base.py", "src/services/base_service.py"]

    print("\n3. 移动废弃文件到备份目录...")
    moved_count = 0

    for file_path in deprecated_files:
        if os.path.exists(file_path):
            # 获取文件名
            file_name = os.path.basename(file_path)
            backup_path = backup_dir / file_name

            # 备份文件
            shutil.move(file_path, backup_path)
            print(f"   ✅ 移动 {file_path} -> {backup_path}")
            moved_count += 1
        else:
            print(f"   ⚠️ 文件不存在: {file_path}")

    print(f"\n✅ 完成！共移动 {moved_count} 个文件到备份目录")

    print("\n4. 验证系统仍然正常...")
    # 运行一个简单的测试验证
    os.system(
        "python -c \"from src.services.base_unified import BaseService; print('✅ 基础服务导入正常')\""
    )

    print("\n5. 建议后续操作:")
    print("   - 确保所有文件都使用 from src.services.base_unified import")
    print("   - 可以在 1-2 周后删除 backup/deprecated_services 目录")
    print("   - 更新相关文档中的导入说明")


if __name__ == "__main__":
    main()
