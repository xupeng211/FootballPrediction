#!/usr/bin/env python3
"""
快速修复logger位置问题的脚本
"""

import re
from pathlib import Path

def fix_logger_position(file_path):
    """修复单个文件中logger的位置问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 移除文件开头的logger定义（在import之前的）
        lines = content.split('\n')
        new_lines = []
        removed_logger = None

        for line in lines:
            if re.match(r'^logger\s*=\s*logging\.getLogger', line.strip()):
                # 暂时保存logger定义
                removed_logger = line
            else:
                new_lines.append(line)

        content = '\n'.join(new_lines)

        # 如果有被移除的logger定义，重新添加到正确位置
        if removed_logger and 'logger.' in content:
            # 找到所有import语句
            lines = content.split('\n')
            last_import_line = -1

            for i, line in enumerate(lines):
                if re.match(r'^\s*(import|from)\s+', line.strip()):
                    last_import_line = i

            if last_import_line >= 0:
                # 确保有import logging
                has_logging_import = False
                for i in range(last_import_line + 1):
                    if 'import logging' in lines[i]:
                        has_logging_import = True
                        break

                if not has_logging_import:
                    # 在最后一个import后添加logging导入
                    insert_pos = last_import_line + 1
                    while insert_pos < len(lines) and (lines[insert_pos].strip() == '' or lines[insert_pos].strip().startswith('#')):
                        insert_pos += 1
                    lines.insert(insert_pos, 'import logging')
                    lines.insert(insert_pos + 1, '')
                    last_import_line += 2

                # 在最后一个import后添加logger定义
                insert_pos = last_import_line + 1
                while insert_pos < len(lines) and (lines[insert_pos].strip() == '' or lines[insert_pos].strip().startswith('#')):
                    insert_pos += 1

                lines.insert(insert_pos, removed_logger)
                lines.insert(insert_pos + 1, '')

            content = '\n'.join(lines)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 仍然有logger问题的文件
    problem_files = [
        'tests/unit/adapters/test_adapters_basic.py',
        'tests/unit/api/test_api_endpoint.py',
        'tests/unit/api/test_auth_direct.py',
        'tests/unit/api/test_auth_simple.py',
        'tests/unit/api/test_predictions_simple.py',
        'tests/unit/database/test_database_operations.py',
        'tests/unit/database/test_repositories.py',
        'tests/unit/domain/services/test_match_service.py',
        'tests/unit/domain/services/test_prediction_service.py',
        'tests/unit/domain/services/test_service_lifecycle.py',
        'tests/unit/domain/test_business_rules.py',
        'tests/unit/ml/test_elo_model.py',
        'tests/unit/ml/test_elo_model_simple.py',
        'tests/unit/ml/test_ml_integration.py',
        'tests/unit/ml/test_ml_models_comprehensive.py',
        'tests/unit/ml/test_ml_models_simple.py',
        'tests/unit/ml/test_ml_model_training.py',
        'tests/unit/ml/test_ml_performance.py',
        'tests/unit/ml/test_ml_prediction_evaluation.py',
        'tests/unit/ml/test_ml_prediction_service.py',
        'tests/unit/scripts/test_coverage_improvement_integration.py',
        'tests/unit/services/test_audit_service_new.py',
        'tests/unit/test_auto_binding_comprehensive.py',
        'tests/unit/test_core_logger_enhanced.py',
        'tests/unit/test_core_logger_massive.py',
        'tests/unit/test_core_logger.py',
        'tests/unit/test_health_check.py',
        'tests/unit/test_service_lifecycle_comprehensive.py',
        'tests/unit/utils/test_warning_filters_complete.py',
        'tests/unit/utils/test_warning_filters_final_coverage.py',
    ]

    fixed_count = 0

    for file_path in problem_files:
        path = Path(file_path)
        if path.exists():
            if fix_logger_position(path):
                print(f"✅ 修复了: {file_path}")
                fixed_count += 1

    print(f"修复完成！成功修复 {fixed_count} 个文件")

if __name__ == "__main__":
    main()