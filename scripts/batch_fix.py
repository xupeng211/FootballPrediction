#!/usr/bin/env python3
"""批量语法修复脚本
自动修复常见的语法错误
"""

import os
import re

def fix_illegal_targets():
    """修复类型注解中的引号错误"""
    files = [
        "src/adapters/factory.py",
        "src/adapters/registry.py",
        "src/adapters/football.py",
        "src/api/schemas.py",
        "src/api/cqrs.py",
        "src/api/data_router.py",
        "src/api/observers.py",
        "src/api/monitoring.py",
        "src/api/predictions/models.py",
        "src/api/predictions/router.py",
        "src/api/data/models/odds_models.py",
        "src/api/data/models/match_models.py",
        "src/api/data/models/league_models.py",
        "src/api/data/models/team_models.py",
        "src/utils/response.py",
        "src/repositories/base.py",
        "src/patterns/adapter.py",
        "src/performance/api.py",
        "src/models/prediction.py",
        "src/models/base_models.py",
    ]

    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()

            # 移除参数名中的引号
            import re
            content = re.sub(r'^(\s+)"([^"]+)":', r'\1\2:', content, flags=re.MULTILINE)

            with open(file_path, 'w') as f:
                f.write(content)
            print(f"修复: {file_path}")

def fix_unterminated_strings():
    """修复未闭合的字符串"""
    files = [
        "src/domain/events/base.py",
        "src/database/config.py",
        "src/core/logging/advanced_filters.py",
        "src/data/quality/data_quality_monitor.py",
        "src/data/features/feature_store.py",
        "src/data/features/feature_definitions.py",
        "src/lineage/lineage_reporter.py",
        "src/scheduler/job_manager.py",
    ]

    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if line.count('"') % 2 == 1:
                    if line.rstrip().endswith(','):
                        lines[i] = line[:-1] + '",\n'
                    else:
                        lines[i] = line + '"\n'

            with open(file_path, 'w') as f:
                f.writelines(lines)
            print(f"修复: {file_path}")

def main():
    print("批量修复脚本")
    print("=" * 40)

    print("1. 修复类型注解错误...")
    fix_illegal_targets()

    print("\n2. 修复未闭合字符串...")
    fix_unterminated_strings()

    print("\n修复完成!")

if __name__ == "__main__":
    main()
