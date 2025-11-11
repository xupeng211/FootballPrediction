#!/usr/bin/env python3
"""
修复重复定义问题的脚本
"""

from pathlib import Path


def fix_redefinitions():
    """修复重复定义"""

    # 修复cqrs/queries.py中的重复定义
    queries_file = Path("/home/user/projects/FootballPrediction/src/cqrs/queries.py")
    if queries_file.exists():
        with open(queries_file, encoding='utf-8') as f:
            content = f.read()

        # 注释掉第102行及之后的重复定义
        lines = content.split('\n')
        redefinition_lines = [102, 149, 196, 243, 300, 354, 410]

        for line_num in redefinition_lines:
            if line_num <= len(lines):
                if lines[line_num-1].strip().startswith('class GetUserByIdQuery'):
                    # 注释这行
                    lines[line_num-1] = '# ' + lines[line_num-1]
                    # 注释下一行的文档字符串
                    if line_num < len(lines) and '"""' in lines[line_num]:
                        lines[line_num] = '# ' + lines[line_num]

        with open(queries_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


    # 修复其他文件的重复定义
    other_files = [
        ("/home/user/projects/FootballPrediction/src/api/tenant_management.py", 408, "check_resource_quota"),
        ("/home/user/projects/FootballPrediction/src/domain/events/match_events.py", 50, "MatchStartedEvent"),
        ("/home/user/projects/FootballPrediction/src/domain/services/match_service.py", 95, "get_service_info"),
        ("/home/user/projects/FootballPrediction/src/database/dependencies.py", 123, "get_db_session"),
        ("/home/user/projects/FootballPrediction/src/patterns/observer.py", 644, "create_observer_system"),
        ("/home/user/projects/FootballPrediction/src/database/models/data_collection_log.py", 6, "Enum")
    ]

    for file_path, line_num, name in other_files:
        file = Path(file_path)
        if file.exists():
            with open(file, encoding='utf-8') as f:
                lines = f.readlines()

            if line_num <= len(lines):
                # 注释重复定义
                for i in range(line_num-1, min(line_num+2, len(lines))):
                    if name in lines[i] or ('def' in lines[i] or 'class' in lines[i]):
                        lines[i] = '# ' + lines[i]

                with open(file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)


if __name__ == "__main__":
    fix_redefinitions()
