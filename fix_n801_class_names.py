#!/usr/bin/env python3
"""
修复N801类命名错误 - 将下划线命名改为CapWords格式
Fix N801 class naming errors - Convert underscore naming to CapWords format
"""

import re
from pathlib import Path

def fix_n801_in_file(file_path: Path) -> int:
    """修复单个文件中的N801错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes = 0

        # 常见的类名映射
        name_mappings = {
            'Real_timeDataStreamingAPIRequest': 'RealTimeDataStreamingAPIRequest',
            'Real_timeDataStreamingAPIResponse': 'RealTimeDataStreamingAPIResponse',
            'Feature_Store': 'FeatureStore',
            'Anomaly_Detector': 'AnomalyDetector',
            'Exception_Handler': 'ExceptionHandler',
            'Great_Expectations_Config': 'GreatExpectationsConfig',
            'Advanced_Analyzer': 'AdvancedAnalyzer',
            'Cors_Config': 'CorsConfig',
            'Real_timeDataStreamingAPI': 'RealTimeDataStreamingAPI',
            'Data_Validator': 'DataValidator',
            'Feature_Calculator': 'FeatureCalculator',
            'Performance_Monitor': 'PerformanceMonitor',
            'Alert_System': 'AlertSystem',
            'Log_Aggregator': 'LogAggregator',
            'Cache_Manager': 'CacheManager',
            'Role_BasedAccessControl': 'RoleBasedAccessControl',
            '__Init__': '__Init__'  # 这个保持不变，特殊处理
        }

        # 处理类定义
        lines = content.split('\n')
        new_lines = []

        for line in lines:
            if 'class ' in line and ('_' in line or line.strip().startswith('class __Init__')):
                # 提取类名
                match = re.search(r'class\s+([A-Za-z_][A-Za-z0-9_]*)', line)
                if match:
                    class_name = match.group(1)

                    # 检查是否需要替换
                    if class_name in name_mappings and class_name != '__Init__':
                        new_class_name = name_mappings[class_name]
                        line = line.replace(f'class {class_name}', f'class {new_class_name}')
                        changes += 1
                        print(f"  {class_name} -> {new_class_name}")
                    elif class_name != '__Init__' and '_' in class_name:
                        # 通用转换：将下划线命名转换为CapWords
                        parts = class_name.split('_')
                        new_class_name = ''.join(part.capitalize() for part in parts)
                        if class_name != new_class_name:
                            line = line.replace(f'class {class_name}', f'class {new_class_name}')
                            changes += 1
                            print(f"  {class_name} -> {new_class_name}")

            new_lines.append(line)

        # 如果有更改，写回文件
        if changes > 0:
            new_content = '\n'.join(new_lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return changes

        return 0

    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return 0

def main():
    """主函数"""
    base_path = Path("src")

    # 获取所有包含N801错误的文件
    import subprocess
    result = subprocess.run(
        ["ruff", "check", str(base_path), "--select=N801", "--output-format=concise"],
        capture_output=True, text=True
    )

    if result.returncode != 0 and result.stdout.strip():
        # 解析文件路径
        files_to_fix = set()
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                file_path = line.split(':')[0]
                if Path(file_path).exists():
                    files_to_fix.add(file_path)

        print(f"找到 {len(files_to_fix)} 个文件需要修复N801错误")

        total_changes = 0
        for file_path_str in sorted(files_to_fix):
            file_path = Path(file_path_str)
            print(f"\n正在修复: {file_path}")
            changes = fix_n801_in_file(file_path)
            if changes > 0:
                print(f"✓ 修复了 {changes} 个类名")
                total_changes += changes
            else:
                print(f"- 无需修复或修复失败")

        print(f"\n总共修复了 {total_changes} 个类名")
    else:
        print("没有发现N801错误")

if __name__ == "__main__":
    main()