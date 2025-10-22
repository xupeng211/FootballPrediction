#!/usr/bin/env python3
"""
小批量类型安全改进工具
每次处理5-10个核心业务文件
"""

import re
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

def analyze_file_errors(file_path: str) -> List[str]:
    """分析文件的类型错误"""
    try:
        result = subprocess.run([
            'mypy', file_path, '--show-error-codes', '--no-error-summary'
        ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

        errors = []
        for line in result.stdout.strip().split('\n'):
            if ': error:' in line:
                errors.append(line)
        return errors
    except Exception as e:
        return [f"Error analyzing file: {e}"]

def fix_common_type_issues(content: str, file_path: str) -> Tuple[str, List[str]]:
    """修复常见的类型问题"""
    original_content = content
    changes_made = []

    # 修复1: 缺失的导入
    if 'Optional' in content and 'from typing import Optional' not in content:
        if 'from typing import' in content:
            content = re.sub(r'(from typing import [^\n]+)', r'\1, Optional', content)
            changes_made.append("Added Optional import")
        else:
            content = f"from typing import Optional\n\n{content}"
            changes_made.append("Added typing imports")

    # 修复2: 简单的函数签名问题
    def fix_function_signatures(text):
        patterns = [
            # def method() -> str: return None
            (r'(def\s+(\w+)\([^)]*\)\s*->\s*str[^:]*)\s*:\s*(\w+)\s*return\s+None',
             lambda m: f"{m.group(1)}{m.group(2)} -> Optional[str]:\n    {m.group(3)}return None"),

            # def method() -> int: return None
            (r'(def\s+(\w+)\([^)]*\)\s*->\s*int[^:]*)\s*:\s*(\w+)\s*return\s+None',
             lambda m: f"{m.group(1)}{m.group(2)} -> Optional[int]:\n    {m.group(3)}return None"),

            # def method() -> dict: return None
            (r'(def\s+(\w+)\([^)]*\)\s*->\s*dict[^:]*)\s*:\s*(\w+)\s*return\s+None',
             lambda m: f"{m.group(1)}{m.group(2)} -> Optional[dict]:\n    {m.group(3)}return None"),
        ]

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text

    content = fix_function_signatures(content)
    if content != original_content:
        changes_made.append("Fixed function signatures")

    # 修复3: 字典类型注解
    def fix_dict_annotations(text):
        patterns = [
            # return {"key": value} -> return Dict[str, Any]
            (r'return\s*\{([^}]+)\}\s*$', lambda m: "return Dict[str, Any]:\n        {{{}}}".format(m.group(1))),
        ]

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        return text

    content = fix_dict_annotations(content)
    if content != original_content:
        changes_made.append("Fixed dictionary return types")

    # 修复4: 列表类型注解
    def fix_list_annotations(text):
        patterns = [
            # return [item] -> return List[str]
            (r'return\s*\[([^\]]+)\]\s*$', lambda m: "return List[str]:\n        [{}]".format(m.group(1))),
        ]

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        return text

    content = fix_list_annotations(content)
    if content != original_content:
        changes_made.append("Fixed list return types")

    return content, changes_made

def select_high_priority_files() -> List[str]:
    """选择第三批高优先级的文件进行修复"""
    # 第三批优先级：API层完整覆盖和关键服务
    third_batch_files = [
        # API基础设施
        'src/api/middleware.py',
        'src/api/monitoring.py',
        'src/api/adapters.py',
        'src/api/cqrs.py',

        # 关键服务层
        'src/services/event_prediction_service.py',
        'src/services/data_processing.py',
        'src/services/audit_service.py',

        # 数据收集器
        'src/collectors/odds_collector.py',
        'src/collectors/scores_collector_improved.py',

        # 数据库相关
        'src/database/config.py',
        'src/database/session.py',
        'src/api/dependencies.py',  # 重新检查修复效果
    ]

    # 只返回存在的文件
    existing_files = []
    for file_path in third_batch_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)

    return existing_files[:8]  # 限制为8个文件

def main():
    """主函数"""
    print("🔧 开始第三批小批量类型安全改进...")

    # 选择高优先级文件
    target_files = select_high_priority_files()
    print(f"\n📋 目标文件 ({len(target_files)}个):")
    for i, file_path in enumerate(target_files, 1):
        print(f"  {i}. {os.path.relpath(file_path, '/home/user/projects/FootballPrediction')}")

    print(f"\n🔄 开始处理...")

    fixed_count = 0
    failed_count = 0

    for file_path in target_files:
        print(f"\n🔧 处理: {os.path.relpath(file_path, '/home/user/projects/FootballPrediction')}")

        # 分析错误
        errors = analyze_file_errors(file_path)
        print(f"   📊 发现 {len(errors)} 个错误")

        if errors:
            for i, error in enumerate(errors[:3]):  # 只显示前3个
                print(f"   {i+1}. {error}")
            if len(errors) > 3:
                print(f"   ... 还有 {len(errors) - 3} 个错误")

        # 修复文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"   ❌ 读取失败: {e}")
            failed_count += 1
            continue

        fixed_content, changes = fix_common_type_issues(content, file_path)

        if changes:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                fixed_count += 1
                print(f"   ✅ 修复成功: {'; '.join(changes)}")

                # 验证修复效果
                new_errors = analyze_file_errors(file_path)
                improvement = len(errors) - len(new_errors)
                print(f"   📈 错误减少: {improvement} 个")

            except Exception as e:
                print(f"   ❌ 保存失败: {e}")
                failed_count += 1
        else:
            print(f"   ⚠️ 无需修复")

    print(f"\n📊 批量修复结果:")
    print(f"✅ 成功修复: {fixed_count} 个文件")
    print(f"❌ 修复失败: {failed_count} 个文件")

    print(f"\n🎯 下一步建议:")
    if fixed_count > 0:
        print("1. 运行质量检查验证修复效果")
        print("2. 测试核心功能确保正常运行")
        print("3. 提交修复成果")
    else:
        print("1. 选择其他高优先级文件")
        print("2. 考虑更复杂的类型问题")

if __name__ == '__main__':
    main()