#!/usr/bin/env python3
"""
批量添加标准导入脚本
Add standard imports script
"""

import os
import re
import sys

def add_import_if_needed(file_path, import_line):
    """如果文件缺少特定导入，则添加"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已经包含该导入
        if import_line in content:
            return False

        # 找到合适的位置插入导入（在其他导入语句后面）
        lines = content.split('\n')

        # 找到最后一个导入语句的位置
        last_import_line = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import_line = i

        # 插入新的导入
        if last_import_line >= 0:
            lines.insert(last_import_line + 1, import_line)
        else:
            # 如果没有找到其他导入，在文件开头添加
            lines.insert(0, import_line)

        # 写回文件
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """主函数"""
    # 需要添加np导入的文件列表
    np_files = [
        'src/api/predictions_enhanced.py',
        'src/api/predictions_srs_simple.py',
        'src/data/processing/football_data_cleaner.py',
        'src/data/processing/missing_data_handler.py',
        'src/domain/strategies/enhanced_ml_model.py',
        'src/domain/strategies/ml_model.py',
        'src/domain/strategies/statistical.py',
        'src/ml/automl_pipeline.py',
        'src/ml/lstm_predictor.py',
        'src/ml/model_performance_monitor.py',
        'src/ml/models/base_model.py',
        'src/ml/models/elo_model.py',
        'src/ml/models/poisson_model.py',
        'src/models/prediction_model.py',
        'src/services/betting/enhanced_ev_calculator.py',
        'src/services/processing/processors/match_processor.py',
        'src/services/processing/processors/match_processor_fixed.py',
        'src/services/processing/validators/data_validator.py',
        'src/services/processing/validators/data_validator_fixed.py'
    ]

    # 需要添加pd导入的文件列表
    pd_files = [
        'src/data/processing/data_preprocessor.py',
        'src/data/processing/football_data_cleaner.py',
        'src/data/processing/missing_data_handler.py',
        'src/ml/automl_pipeline.py',
        'src/ml/lstm_predictor.py',
        'src/ml/model_performance_monitor.py',
        'src/ml/models/base_model.py',
        'src/ml/models/elo_model.py',
        'src/ml/models/poisson_model.py',
        'src/ml/model_training.py',
        'src/models/prediction_model.py',
        'src/services/processing/processors/match_processor.py',
        'src/services/processing/processors/match_processor_fixed.py',
        'src/services/processing/validators/data_validator.py',
        'src/services/processing/validators/data_validator_fixed.py'
    ]

    fixed_count = 0

    # 添加numpy导入
    for file_path in np_files:
        if os.path.exists(file_path):
            if add_import_if_needed(file_path, 'import numpy as np'):
                print(f"✅ Added numpy import to {file_path}")
                fixed_count += 1

    # 添加pandas导入
    for file_path in pd_files:
        if os.path.exists(file_path):
            if add_import_if_needed(file_path, 'import pandas as pd'):
                print(f"✅ Added pandas import to {file_path}")
                fixed_count += 1

    print(f"\n📊 总计修复了 {fixed_count} 个文件的导入问题")

if __name__ == '__main__':
    main()