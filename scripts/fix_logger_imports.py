#!/usr/bin/env python3
"""
批量修复测试文件中的logger导入问题
"""

import os
import re
from pathlib import Path

def fix_logger_imports(file_path):
    """修复单个文件中的logger导入问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 检查是否已经有logging导入
        has_logging_import = bool(re.search(r'import\s+logging|from\s+logging\s+import', content))

        # 检查是否已经定义了logger
        has_logger_defined = bool(re.search(r'logger\s*=\s*logging\.getLogger|logger\s*=\s*logging\.Logger', content))

        # 如果使用了logger但没有定义
        if 'logger.' in content and not has_logger_defined:
            # 添加logging导入
            if not has_logging_import:
                # 找到合适的位置添加import（在其他imports之后）
                import_pattern = r'(import\s+\w+.*\n)'
                imports_match = re.search(import_pattern, content)

                if imports_match:
                    # 在最后一个import后添加logging导入
                    last_import_pos = imports_match.end()
                    content = content[:last_import_pos] + 'import logging\n' + content[last_import_pos:]
                else:
                    # 在文件开头添加
                    lines = content.split('\n')
                    # 找到第一个非注释、非空行的位置
                    insert_pos = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                            insert_pos = i
                            break

                    lines.insert(insert_pos, 'import logging\n')
                    content = '\n'.join(lines)

            # 移除错误位置的logger定义（如果在import之前）
            lines = content.split('\n')
            content = '\n'.join(lines)  # 重新组合以便后续处理

            # 添加logger定义 - 确保在所有imports之后
            lines = content.split('\n')
            logger_line = 'logger = logging.getLogger(__name__)'
            added = False
            last_import_line = -1

            # 找到最后一个import语句的行号
            for i, line in enumerate(lines):
                if re.match(r'^\s*(import|from)\s+', line.strip()):
                    last_import_line = i

            if last_import_line >= 0:
                # 在最后一个import之后添加logger定义
                # 先找到import块结束的位置（跳过空行）
                insert_pos = last_import_line + 1
                while insert_pos < len(lines) and (lines[insert_pos].strip() == '' or lines[insert_pos].strip().startswith('#')):
                    insert_pos += 1

                lines.insert(insert_pos, logger_line)
                lines.insert(insert_pos + 1, '')  # 添加空行
                added = True
            else:
                # 如果没有找到import，在文档字符串后添加
                docstring_end = -1
                in_docstring = False

                for i, line in enumerate(lines):
                    if '"""' in line:
                        if not in_docstring:
                            in_docstring = True
                        else:
                            docstring_end = i
                            break

                if docstring_end >= 0:
                    insert_pos = docstring_end + 1
                    lines.insert(insert_pos, '')
                    lines.insert(insert_pos + 1, 'import logging')
                    lines.insert(insert_pos + 2, logger_line)
                    added = True
                else:
                    # 在文件开头添加
                    lines.insert(0, 'import logging')
                    lines.insert(1, '')
                    lines.insert(2, logger_line)
                    lines.insert(3, '')
                    added = True

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
    # 需要修复的文件列表
    files_to_fix = [
        'tests/unit/adapters/test_adapter_pattern.py',
        'tests/unit/adapters/test_adapters_basic.py',
        'tests/unit/api/test_api_endpoint.py',
        'tests/unit/api/test_auth_direct.py',
        'tests/unit/api/test_auth_simple.py',
        'tests/unit/api/test_predictions_simple.py',
        'tests/unit/database/test_database_operations.py',
        'tests/unit/database/test_models.py',
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
    total_count = len(files_to_fix)

    print(f"开始修复 {total_count} 个文件中的logger导入问题...")

    for file_path in files_to_fix:
        full_path = Path(file_path)
        if full_path.exists():
            if fix_logger_imports(full_path):
                print(f"✅ 修复了: {file_path}")
                fixed_count += 1
            else:
                print(f"⏭️  跳过（无需修复）: {file_path}")
        else:
            print(f"❌ 文件不存在: {file_path}")

    print(f"\n修复完成！")
    print(f"总共处理: {total_count} 个文件")
    print(f"成功修复: {fixed_count} 个文件")

if __name__ == "__main__":
    main()