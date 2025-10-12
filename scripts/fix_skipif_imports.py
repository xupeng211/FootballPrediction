#!/usr/bin/env python3
"""
修复错误的 skipif 导入检查
"""

import os
import re


def fix_module_imports(filepath, module_name, actual_import):
    """修复文件中的模块导入检查"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 查找并替换导入检查
        pattern = rf'(# 测试导入\s+try:\s+from {module_name} import.*?except ImportError as e:.*?{module_name.upper()}_AVAILABLE = False)'

        # 替换为正确的导入
        replacement = f'''# 测试导入
try:
    {actual_import}
    {module_name.upper()}_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {{e}}")
    {module_name.upper()}_AVAILABLE = False'''

        # 使用更精确的替换
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if '# 测试导入' in line and i + 10 < len(lines):
                # 检查是否是目标模块
                import_block = '\n'.join(lines[i:i+10])
                if module_name in import_block:
                    # 找到 try 块
                    j = i
                    while j < len(lines) and 'except ImportError' not in lines[j]:
                        j += 1
                    if j < len(lines):
                        # 替换整个 try-except 块
                        new_lines.append(f'# 测试导入')
                        new_lines.append(f'try:')
                        new_lines.append(f'    {actual_import}')
                        new_lines.append(f'    {module_name.upper()}_AVAILABLE = True')
                        new_lines.append(f'except ImportError as e:')
                        new_lines.append(f'    print(f"Import error: {{e}}")')
                        new_lines.append(f'    {module_name.upper()}_AVAILABLE = False')

                        # 跳过原始的 try-except 块
                        i = j + 1
                        while i < len(lines) and not lines[i].strip().startswith('@'):
                            i += 1
                        i -= 1
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
            i += 1

        new_content = '\n'.join(new_lines)

        if new_content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ 修复了 {filepath}")
            return True

    except Exception as e:
        print(f"✗ 修复 {filepath} 失败: {e}")

    return False


def main():
    print("修复 skipif 导入检查...")
    print("-" * 60)

    # 已知可用的模块映射
    modules_to_fix = [
        ('tests/unit/api/test_features.py', 'src.api.features', 'router, get_feature_store, validate_match_id, check_feature_store_availability, get_match_info, get_features_data, build_response_data, feature_store'),
        ('tests/unit/api/test_monitoring.py', 'src.monitoring', 'SystemMonitor, MetricsCollector, HealthChecker'),
        ('tests/unit/services/test_audit_service.py', 'src.services.audit', 'AuditService, AuditLogger, AuditQuery'),
        ('tests/unit/utils/test_helpers_new.py', 'src.utils.helpers', 'validate_email, format_phone, generate_uuid'),
    ]

    fixed_count = 0
    for filepath, module_name, actual_import in modules_to_fix:
        if os.path.exists(filepath):
            if fix_module_imports(filepath, module_name, actual_import):
                fixed_count += 1

    print("-" * 60)
    print(f"修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()