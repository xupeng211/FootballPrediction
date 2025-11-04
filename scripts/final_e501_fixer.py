#!/usr/bin/env python3
"""
最终E501格式错误修复工具
处理剩余的顽固格式错误
"""

import os
import re
from pathlib import Path

def fix_specific_e501_errors(project_root: str = ".") -> int:
    """修复特定的E501错误"""
    total_fixed = 0

    # 修复notification_manager.py中的HTML/CSS格式问题
    notification_file = os.path.join(project_root,
    "src/alerting/notification_manager.py")
    if os.path.exists(notification_file):
        fixed = fix_notification_manager_file(notification_file)
        total_fixed += fixed

    # 修复其他关键文件的E501错误
    critical_files = [
        "src/api/adapters/router.py",
        "src/api/auth.py",
        "src/api/predictions.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/tenant_management.py",
        "src/app_enhanced.py",
        "src/bad_example.py",
        "src/cache/ttl_cache.py",
        "src/cache/ttl_cache_enhanced/ttl_cache.py",
        "src/collectors/collectors/scores_collector_improved_services.py",
        "src/collectors/data_sources.py",
        "src/collectors/football_data_collector.py",
        "src/collectors/league_collector.py",
        "src/collectors/match_collector.py",
        "src/collectors/oddsportal_integration.py",
        "src/collectors/team_collector.py",
        "src/config/fastapi_config.py",
        "src/core/di.py",
        "src/cqrs/handlers.py",
        "src/data/collectors/fixtures_collector.py",
        "src/data/quality/data_quality_monitor.py",
        "src/database/config.py",
        "src/database/connection.py",
        "src/domain/models/prediction.py",
        "src/domain/strategies/base.py",
        "src/domain/strategies/statistical.py",
        "src/domain_simple/odds.py",
        "src/domain_simple/prediction.py",
        "src/events/bus.py",
        "src/events/handlers.py",
        "src/lineage/lineage_reporter.py",
        "src/metrics/quality_integration.py",
        "src/ml/models/base_model.py",
        "src/ml/models/elo_model.py",
        "src/ml/models/poisson_model.py",
        "src/ml/prediction/prediction_service.py",
        "src/models/auth_user.py",
        "src/models/external/competition.py",
        "src/models/external/league.py",
        "src/models/external/match.py",
        "src/models/external/team.py",
        "src/monitoring/quality_monitor.py",
        "src/observers/observers.py",
        "src/patterns/decorator.py",
        "src/performance/api.py",
        "src/performance/integration.py",
        "src/realtime/quality_monitor_server.py",
        "src/realtime/subscriptions.py",
        "src/scheduler/tasks.py",
        "src/services/betting/betting_service.py",
        "src/services/betting/betting_service_fixed.py",
        "src/services/data_sync_service.py",
        "src/services/strategy_prediction_service.py",
        "src/services/user_profile.py",
        "src/streaming/stream_config.py",
        "src/tasks/backup_tasks.py",
        "src/tasks/maintenance_tasks.py",
        "src/tasks/monitoring.py",
        "src/tasks/utils.py",
        "src/utils/validators.py"
    ]

    for file_path in critical_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            fixed = fix_file_e501_errors(full_path)
            total_fixed += fixed

    return total_fixed

def _fix_notification_manager_file_manage_resource():
            content = f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0

def _fix_notification_manager_file_check_condition():
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)


def _fix_notification_manager_file_check_condition():
            fixed_count += 1
            content = new_content

    # 修复长字符串
    lines = content.split('\n')
    new_lines = []


def _fix_notification_manager_file_check_condition():
                    fixed_line = break_long_css_line(line)
                    new_lines.extend(fixed_line)
                    fixed_count += 1
                    continue

def _fix_notification_manager_file_check_condition():
                # 尝试分解长字符串
                fixed_line = break_long_string_line(line)

def _fix_notification_manager_file_check_condition():
                    new_lines.extend(fixed_line)
                    fixed_count += 1
                    continue

def _fix_notification_manager_file_manage_resource():
                f.write(content)
            print(f"修复 {file_path} 中的 {fixed_count} 个格式错误")
        except Exception as e:
            print(f"写入文件 {file_path} 失败: {e}")
            return 0

def fix_notification_manager_file(file_path: str) -> int:
    """修复notification_manager.py文件中的格式错误"""
    try:
        _fix_notification_manager_file_manage_resource()
            content = f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0

    original_content = content
    fixed_count = 0

    # 修复CSS样式长行
    css_fixes = [
        # 修复alert-info样式
        (r'\.alert-info \{ background: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; \}',
         '.alert-info {\n            background: #f8f9fa;\n            padding: 20px;\n            border-radius: 6px;\n            margin: 20px 0;\n        }'),

        # 修复severity-badge样式
        (r'\.severity-badge \{[^}]+\}',
         lambda m: reformat_css_block(m.group(0))),

        # 修复footer样式
        (r'\.footer \{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; \}',
         '.footer {\n            background: #f8f9fa;\n            padding: 20px;\n            text-align: center;\n            color: #666;\n            font-size: 12px;\n        }'),

        # 修复details样式
        (r'\.details \{ background: #fff1f0; border-left: 4px solid #ff4d4f; padding: 15px; margin: 15px 0; \}',
         '.details {\n            background: #fff1f0;\n            border-left: 4px solid #ff4d4f;\n            padding: 15px;\n            margin: 15px 0;\n        }'),

        # 修复metric样式
        (r'\.metric \{ display: flex; justify-content: space-between; margin: 8px 0; \}',
         '.metric {\n            display: flex;\n            justify-content: space-between;\n            margin: 8px 0;\n        }')
    ]

    for pattern, replacement in css_fixes:
        _fix_notification_manager_file_check_condition()
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        _fix_notification_manager_file_check_condition()
            fixed_count += 1
            content = new_content

    # 修复长字符串
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        if len(line) > 88:
            # 检查是否是CSS行
            if line.strip().startswith(('.',
    'body {',
    'container {',
    'header {',
    'content {',
    'alert-info {',
    'footer {',
    'details {',
    'metric {')):
                # 分解CSS属性
                _fix_notification_manager_file_check_condition()
                    fixed_line = break_long_css_line(line)
                    new_lines.extend(fixed_line)
                    fixed_count += 1
                    continue

            # 检查是否是长字符串
            _fix_notification_manager_file_check_condition()
                # 尝试分解长字符串
                fixed_line = break_long_string_line(line)
                _fix_notification_manager_file_check_condition()
                    new_lines.extend(fixed_line)
                    fixed_count += 1
                    continue

        new_lines.append(line)

    content = '\n'.join(new_lines)

    # 只有在有修复时才写回文件
    if content != original_content:
        try:
            _fix_notification_manager_file_manage_resource()
                f.write(content)
            print(f"修复 {file_path} 中的 {fixed_count} 个格式错误")
        except Exception as e:
            print(f"写入文件 {file_path} 失败: {e}")
            return 0

    return fixed_count

def reformat_css_block(css_block: str) -> str:
    """重新格式化CSS块"""
    # 提取选择器和属性
    match = re.match(r'(\.[^{]+)\{([^}]+)\}', css_block)
    if not match:
        return css_block

    selector = match.group(1).strip()
    properties = match.group(2).strip()

    # 分解属性为多行
    props_list = [prop.strip() for prop in properties.split(';') if prop.strip()]

    # 格式化为多行
    result_lines = [selector + '{']
    for prop in props_list:
        result_lines.append(f'    {prop};')
    result_lines.append('}')

    return '\n'.join(result_lines)

def break_long_css_line(line: str) -> list:
    """分解长CSS行"""
    # 提取缩进
    indent_match = re.match(r'^(\s*)', line)
    base_indent = indent_match.group(1) if indent_match else ''

    # 分解CSS属性
    if '{' in line and '}' in line:
        # 单行CSS块
        before_brace = line[:line.find('{')]
        after_brace = line[line.find('{')+1:line.find('}')]

        result_lines = [base_indent + before_brace + '{']
        properties = [prop.strip() for prop in after_brace.split(';') if prop.strip()]

        for prop in properties:
            result_lines.append(base_indent + '    ' + prop + ';')

        result_lines.append(base_indent + '}')
        return result_lines

    return [line]

def break_long_string_line(line: str) -> list:
    """分解长字符串行"""
    # 提取缩进
    indent_match = re.match(r'^(\s*)', line)
    base_indent = indent_match.group(1) if indent_match else ''

    # 检查是否是f-string
    if 'f"' in line:
        # 尝试在适当的空格处分行
        parts = re.split(r'(\s+and\s+|\s+\+\s+)', line)
        if len(parts) > 1:
            result_lines = []
            current_line = base_indent

            for part in parts:
                if len(current_line + part) <= 88:
                    current_line += part
                else:
                    if current_line.strip():
                        result_lines.append(current_line.rstrip())
                    current_line = base_indent + '    ' + part.strip()

            if current_line.strip():
                result_lines.append(current_line.rstrip())

            return result_lines

    return [line]

def fix_file_e501_errors(file_path: str) -> int:
    """修复单个文件中的E501错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0

    original_content = content
    fixed_count = 0

    # 修复长函数调用
    content = fix_long_function_calls(content)

    # 修复长导入语句
    content = fix_long_imports(content)

    # 修复长字符串
    content = fix_long_strings(content)

    # 只有在有修复时才写回文件
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"修复 {file_path} 中的格式错误")
            fixed_count = 1
        except Exception as e:
            print(f"写入文件 {file_path} 失败: {e}")
            return 0

    return fixed_count

def fix_long_function_calls(content: str) -> str:
    """修复长函数调用"""
    # 匹配长函数调用并分行
    pattern = r'(\w+\([^{]*?,[^{]*?,[^{]*?,[^{]*?,.*)'

    def fix_match(match):
        line = match.group(1)
        if len(line) > 88:
            # 在逗号处分行
            parts = line.split(',')
            if len(parts) > 1:
                result = parts[0] + ',\n'
                for part in parts[1:-1]:
                    result += '    ' + part.strip() + ',\n'
                result += '    ' + parts[-1].strip()
                return result
        return line

    return re.sub(pattern, fix_match, content, flags=re.MULTILINE)

def fix_long_imports(content: str) -> str:
    """修复长导入语句"""
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        if line.strip().startswith('import ') and len(line) > 88 and ',' in line:
            # 分解长导入语句
            parts = line.split(',')
            if len(parts) > 1:
                new_lines.append(parts[0] + ' (')
                for part in parts[1:-1]:
                    new_lines.append('    ' + part.strip() + ',')
                new_lines.append('    ' + parts[-1].strip() + ')')
                continue

        new_lines.append(line)

    return '\n'.join(new_lines)

def fix_long_strings(content: str) -> str:
    """修复长字符串"""
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        if len(line) > 88 and ('"' in line or "'" in line):
            # 尝试分解长字符串
            if 'f"' in line or 'f\'' in line:
                fixed_line = break_long_string_line(line)
                if len(fixed_line) > 1:
                    new_lines.extend(fixed_line)
                    continue

        new_lines.append(line)

    return '\n'.join(new_lines)

def main():
    """主函数"""
    print("开始修复剩余的E501格式错误...")

    total_fixed = fix_specific_e501_errors()

    print(f"\n总共修复了 {total_fixed} 个格式错误")

    # 验证修复结果
    print("\n验证修复结果...")
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=E501', '--output-format=concise', '.'],
            capture_output=True,
            text=True
        )
        remaining_errors = len([line for line in result.stdout.split('\n') if line.strip()])
        print(f"剩余 E501 错误: {remaining_errors}")

        if remaining_errors == 0:
            print("🎉 所有E501格式错误已修复！")
        else:
            print("⚠️  仍有部分格式错误需要手动处理")
            print("主要错误文件：")
            for line in result.stdout.split('\n')[:10]:
                if line.strip():
                    print(f"  {line.split(':')[0]}:{line.split(':')[1]}")
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    import subprocess
    main()