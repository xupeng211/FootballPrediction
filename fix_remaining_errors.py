#!/usr/bin/env python3
"""
修复剩余的Python语法错误
"""

import re
from pathlib import Path


def fix_specific_errors(file_path):
    """修复特定文件的语法错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        changes = []

        # 修复常见的类型注解错误
        patterns = [
            # List[str]] -> List[str]
            (r"List\[(\w+)\]\]", r"List[\1]"),
            # Dict[str, Any]] -> Dict[str, Any]
            (r"Dict\[str,\s*Any\]\]", r"Dict[str, Any]"),
            # Optional[str]] -> Optional[str]
            (r"Optional\[(\w+)\]\]", r"Optional[\1]"),
            # Union[str, Path]] -> Union[str, Path]
            (r"Union\[[^\]]+\]\]", lambda m: m.group(0)[:-1]),
        ]

        for pattern, replacement in patterns:
            if hasattr(replacement, "__call__"):
                # 使用函数进行替换
                new_content = pattern.sub(replacement, content)
            else:
                # 使用字符串替换
                new_content = re.sub(pattern, replacement, content)

            if new_content != content:
                changes.append(f"Applied pattern: {pattern}")
                content = new_content

        # 特殊修复：处理特定的文件
        if "cors_config.py" in str(file_path):
            content = re.sub(r"origins: List\[str\]\]", "origins: List[str]", content)
            changes.append("Fixed cors_config.py origins type")

        # 写回文件
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return changes

        return []

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return []


def main():
    """主函数"""
    Path("src")
    fixed_files = []

    # 已知有问题的文件列表
    problem_files = [
        "src/config/cors_config.py",
        "src/utils/validators.py",
        "src/facades/base.py",
        "src/facades/facades.py",
        "src/facades/subsystems/database.py",
        "src/patterns/decorator.py",
        "src/patterns/facade.py",
        "src/patterns/facade_simple.py",
        "src/domain/strategies/base.py",
        "src/domain/strategies/historical.py",
        "src/domain/strategies/ensemble.py",
        "src/domain/strategies/statistical.py",
        "src/domain/strategies/ml_model.py",
        "src/cqrs/queries.py",
        "src/cqrs/commands.py",
        "src/cqrs/base.py",
        "src/streaming/kafka_consumer_simple.py",
        "src/streaming/stream_config.py",
        "src/streaming/kafka_producer_simple.py",
        "src/cache/ttl_cache_enhanced/async_cache.py",
        "src/cache/ttl_cache_enhanced/ttl_cache.py",
        "src/domain_simple/league.py",
        "src/domain_simple/user.py",
        "src/domain_simple/team.py",
        "src/domain_simple/rules.py",
        "src/observers/subjects.py",
        "src/observers/manager.py",
        "src/features/feature_store.py",
        "src/features/feature_calculator.py",
        "src/data/storage/lake.py",
        "src/data/processing/football_data_cleaner.py",
        "src/data/collectors/odds_collector.py",
        "src/lineage/lineage_reporter.py",
        "src/scheduler/job_manager.py",
    ]

    for file_path in problem_files:
        full_path = Path(file_path)
        if full_path.exists():
            changes = fix_specific_errors(full_path)
            if changes:
                fixed_files.append((file_path, changes))
                print(f"✓ Fixed {file_path}")
                for change in changes:
                    print(f"  - {change}")

    print(f"\n总计修复了 {len(fixed_files)} 个文件")

    # 测试关键导入
    print("\n测试关键导入...")
    try:
        from src.api.data_router import router

        print("✓ data_router 导入成功")
    except SyntaxError as e:
        print(f"✗ data_router 导入失败: {e}")

    try:
        from src import main as main_module

        print("✓ main 模块导入成功")
    except SyntaxError as e:
        print(f"✗ main 模块导入失败: {e}")


if __name__ == "__main__":
    main()
