#!/usr/bin/env python3
"""
最终冲刺到100个错误以下的修复脚本
专注于最容易修复的问题类型
"""

import os
import re

def fix_unused_imports_targeted(file_path):
    """目标性修复未使用导入"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 具体修复未使用导入
        fixes = [
            # 测试文件中的常见未使用导入
            ('MatchStatus', 'from src.domain.models.match import Match, MatchStatus'),
            ('Config', 'from src.core.config import Config'),
            ('PredictionService', 'from src.services.prediction import PredictionService'),
            ('pydantic.Field', 'from pydantic import BaseModel, Field'),
            ('Decimal', 'from decimal import Decimal'),
            ('ConfidenceScore', 'from src.domain.models.prediction import'),
            ('PredictionScore', 'from src.domain.models.prediction import'),
        ]

        for import_name, line_pattern in fixes:
            if import_name in content and line_pattern in content:
                # 移除或注释掉这个导入
                if line_pattern in content:
                    content = content.replace(line_pattern, line_pattern.replace(import_name, f"# {import_name}"))
                    
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的未使用导入")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_type_comparisons(file_path):
    """修复类型比较"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复常见的类型比较模式
        fixes = [
            (r'type\((\w+)\) == type\((\w+)\)', r'type(\1) is type(\2)'),
            (r'type\((\w+)\) == (\w+)', r'isinstance(\1, \2)'),
            (r'assert type\((\w+)\) == (\w+)', r'assert isinstance(\1, \2)'),
            (r'assert (\w+)\["category"\] == (\w+)', r'assert \1["category"] is \2'),
        ]

        for pattern, replacement in fixes:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                break

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的类型比较")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def fix_loop_variables(file_path):
    """修复未使用循环变量"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复常见的未使用循环变量
        fixes = [
            (r'for (\w+) in (.+?):\s*pass\s*#', r'for _\1 in \2: pass  #'),
            (r'for (\w+) in (.+?):\s*pass  #', r'for _\1 in \2: pass  #'),
        ]

        for pattern, replacement in fixes:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                break

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复了 {file_path} 的循环变量")
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始最终冲刺到100个错误以下...")

    # 目标文件列表 - 专注于最容易修复的
    target_files = [
        "src/domain/events/__init__.py",
        "src/events/__init__.py", 
        "tests/integration/conftest.py",
        "tests/integration/test_api_domain_integration.py",
        "tests/performance/test_load.py",
        "tests/unit/api/test_health_endpoints_comprehensive.py",
        "tests/unit/test_core_auto_binding.py",
        "tests/unit/test_core_config_di.py",
        "tests/unit/test_core_di.py",
        "tests/unit/test_core_exceptions_enhanced.py",
        "tests/unit/test_core_exceptions_massive.py",
        "tests/unit/utils/test_crypto_utils_comprehensive.py",
        "tests/unit/utils/test_warning_filters_init.py",
        "tests/integration/test_imports_only.py",
        "tests/integration/test_prediction_api_integration.py",
        "tests/unit/data/test_processing_simple.py",
        "tests/unit/events/test_event_system.py"
    ]

    fixed_count = 0
    for file_path in target_files:
        if os.path.exists(file_path):
            if fix_unused_imports_targeted(file_path):
                fixed_count += 1
            elif fix_type_comparisons(file_path):
                fixed_count += 1
            elif fix_loop_variables(file_path):
                fixed_count += 1

    print(f"🎯 最终冲刺完成！共修复了 {fixed_count} 个错误")

if __name__ == "__main__":
    main()
