#!/usr/bin/env python3
"""
迁移到模块化结构

将代码中的导入路径更新为新的模块化路径。
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set

# 导入路径映射表
IMPORT_MAPPINGS = {
    # 服务模块
    "src.services.audit_service": "src.services.audit_service_mod",
    "src.services.manager": "src.services.manager_mod",
    "src.services.data_processing": "src.services.data_processing_mod",
    # 数据库模块
    "src.database.connection": "src.database.connection_mod",
    # 缓存模块
    "src.cache.ttl_cache_improved": "src.cache.ttl_cache_improved_mod",
    # 数据处理模块
    "src.data.processing.football_data_cleaner": "src.data.processing.football_data_cleaner_mod",
    "src.data.quality.exception_handler": "src.data.quality.exception_handler_mod",
    # 监控模块
    "src.monitoring.system_monitor": "src.monitoring.system_monitor_mod",
    "src.monitoring.metrics_collector_enhanced": "src.monitoring.metrics_collector_enhanced_mod",
    # 其他模块
    "src.features.feature_calculator": "src.features.feature_calculator_mod",
    "src.models.prediction_service": "src.models.prediction_service_mod",
}


def get_python_files(root_dir: str = ".") -> List[Path]:
    """获取所有Python文件"""
    python_files = []
    for path in Path(root_dir).rglob("*.py"):
        # 跳过某些目录
        if any(
            skip in str(path)
            for skip in [
                ".git",
                "__pycache__",
                ".venv",
                "venv",
                "node_modules",
                ".pytest_cache",
                "backup",
                "scripts",
                "tests",  # 暂时不修改测试文件
            ]
        ):
            continue
        python_files.append(path)
    return python_files


def update_imports_in_file(file_path: Path) -> Dict[str, int]:
    """更新单个文件中的导入"""
    stats = {"files_updated": 0, "imports_updated": 0, "errors": 0}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        content_updated = False

        # 查找并更新导入语句
        for old_path, new_path in IMPORT_MAPPINGS.items():
            # 匹配 from 语句
            pattern = rf"from\s+{re.escape(old_path)}\s+import"
            if re.search(pattern, content):
                content = re.sub(pattern, f"from {new_path} import", content)
                content_updated = True
                stats["imports_updated"] += 1

        # 如果内容有更新，写回文件
        if content_updated:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            stats["files_updated"] = 1
            print(f"✓ 更新: {file_path.relative_to('.')}")

    except Exception as e:
        print(f"✗ 错误: {file_path} - {e}")
        stats["errors"] += 1

    return stats


def main():
    """主函数"""
    print("=" * 60)
    print("迁移到模块化结构")
    print("=" * 60)

    print("\n检查需要更新的文件...")
    python_files = get_python_files()
    print(f"找到 {len(python_files)} 个Python文件")

    print("\n开始更新导入路径...")
    total_stats = {"files_updated": 0, "imports_updated": 0, "errors": 0}

    # 逐个文件更新
    for file_path in python_files:
        stats = update_imports_in_file(file_path)
        total_stats["files_updated"] += stats["files_updated"]
        total_stats["imports_updated"] += stats["imports_updated"]
        total_stats["errors"] += stats["errors"]

    # 打印统计信息
    print("\n" + "=" * 60)
    print("迁移统计")
    print("=" * 60)
    print(f"更新的文件数: {total_stats['files_updated']}")
    print(f"更新的导入数: {total_stats['imports_updated']}")
    print(f"错误数: {total_stats['errors']}")

    if total_stats["errors"] == 0:
        print("\n✅ 迁移完成！")
        print("\n下一步:")
        print("1. 运行 'make test-quick' 验证功能")
        print("2. 运行 'make lint' 检查代码质量")
        print("3. 提交更改")
    else:
        print(f"\n⚠️  有 {total_stats['errors']} 个错误需要处理")


if __name__ == "__main__":
    main()
