#!/usr/bin/env python3
"""手动语法修复脚本
按照优先级修复语法错误
"""

import os

# 错误修复计划
ERRORS_TO_FIX = [
    ("src/domain/events/base.py", 56, "unterminated_string"),
    ("src/core/logging/advanced_filters.py", 7, "unterminated_string"),
    ("src/data/features/feature_store.py", 26, "unterminated_string"),
    ("src/data/features/feature_definitions.py", 21, "unterminated_string"),
    ("src/scheduler/job_manager.py", 65, "unterminated_string"),
    ("src/decorators/factory.py", 24, "illegal_target"),
    ("src/cqrs/bus.py", 139, "illegal_target"),
    ("src/streaming/stream_config.py", 22, "illegal_target"),
    ("src/database/config.py", 12, "illegal_target"),
    ("src/database/base.py", 62, "illegal_target"),
    ("src/database/query_optimizer.py", 23, "illegal_target"),
    ("src/database/models/features.py", 60, "illegal_target"),
    ("src/database/models/predictions.py", 64, "illegal_target"),
    ("src/database/models/raw_data.py", 32, "illegal_target"),
    ("src/database/models/odds.py", 79, "illegal_target"),
    ("src/adapters/factory_simple.py", 93, "invalid_syntax"),
    ("src/api/dependencies.py", 37, "invalid_syntax"),
    ("src/api/decorators.py", 61, "invalid_syntax"),
    ("src/utils/validators.py", 29, "invalid_syntax"),
    ("src/utils/dict_utils.py", 61, "invalid_syntax"),
    ("src/utils/data_validator.py", 38, "invalid_syntax"),
    ("src/utils/redis_cache.py", 19, "invalid_syntax"),
    ("src/utils/_retry/__init__.py", 21, "invalid_syntax"),
    ("src/facades/factory.py", 4, "invalid_syntax"),
    ("src/monitoring/anomaly_detector.py", 52, "invalid_syntax"),
]

def fix_unterminated_string(file_path, line_num):
    """修复未闭合的字符串"""
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    if line_num <= len(lines):
        line = lines[line_num - 1]
        if line.count('"') % 2 == 1:
            if line.rstrip().endswith(','):
                lines[line_num - 1] = line[:-1] + '",\n'
            else:
                lines[line_num - 1] = line + '"\n'
            
            with open(file_path, "w") as f:
                f.writelines(lines)
            print(f"  ✓ 修复: {file_path}:{line_num}")
            return True
    return False

def fix_illegal_target(file_path, line_num):
    """修复类型注解错误"""
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    if line_num <= len(lines):
        line = lines[line_num - 1]
        # 移除参数名中的引号
        import re
        fixed_line = re.sub(r'"(\w+)":', r'\1:', line)
        if fixed_line != line:
            lines[line_num - 1] = fixed_line
            with open(file_path, "w") as f:
                f.writelines(lines)
            print(f"  ✓ 修复: {file_path}:{line_num}")
            return True
    return False

def main():
    """主修复函数"""
    print("开始手动修复...")
    
    for file_path, line_num, error_type in ERRORS_TO_FIX:
        print(f"\n处理: {file_path}")
        print(f"  第{line_num}行: {error_type}")
        
        if error_type == "unterminated_string":
            fix_unterminated_string(file_path, line_num)
        elif error_type == "illegal_target":
            fix_illegal_target(file_path, line_num)
        else:
            print(f"  跳过: 需要手动修复")
            print(f"  命令: vim {file_path} +{line_num}")

if __name__ == "__main__":
    main()
