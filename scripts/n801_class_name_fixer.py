#!/usr/bin/env python3
"""
N801类名规范修复工具
将使用下划线的类名改为CapWords格式
"""

import re
from pathlib import Path


def fix_n801_in_file(file_path: Path) -> tuple[int, bool]:
    """修复单个文件中的N801错误"""
    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content
        fix_count = 0

        # 常见的类名转换映射
        class_mappings = {
            'Real_timeDataStreamingAPIRequest': 'RealtimeDataStreamingAPIRequest',
            'Real_timeDataStreamingAPIResponse': 'RealtimeDataStreamingAPIResponse',
            'Odds_Collector': 'OddsCollector',
            'Scores_Collector': 'ScoresCollector',
            'Feature_Store': 'FeatureStore',
            'Football_Data_Cleaner': 'FootballDataCleaner',
            'Missing_Data_Handler': 'MissingDataHandler',
            'Anomaly_Detector': 'AnomalyDetector',
            'Exception_Handler': 'ExceptionHandler',
            'Data_Validator': 'DataValidator',
            'API_Manager': 'APIManager',
            'Kafka_Consumer': 'KafkaConsumer',
            'Kafka_Producer': 'KafkaProducer',
            'Stream_Config': 'StreamConfig',
            'Influxdb_Client': 'InfluxdbClient',
            'Confluent_Kafka': 'ConfluentKafka',
            'Data_Collection_Core': 'DataCollectionCore',
        }

        # 通用模式匹配：将_连接的单词转为CapWords
        def convert_to_capwords(class_name):
            if class_name in class_mappings:
                return class_mappings[class_name]

            # 转换下划线分隔的类名
            if '_' in class_name:
                parts = class_name.split('_')
                return ''.join(part.capitalize() for part in parts)

            return class_name

        # 匹配类定义
        class_pattern = r'class\s+([A-Za-z_][A-Za-z0-9_]*)\s*:'

        def replace_class_name(match):
            nonlocal fix_count
            old_name = match.group(1)

            # 检查是否需要修复
            if '_' in old_name or old_name in class_mappings:
                new_name = convert_to_capwords(old_name)
                if new_name != old_name:
                    fix_count += 1
                    # 替换整个文件中的类名
                    content = content.replace(f'class {old_name}', f'class {new_name}')
                    # 也替换实例化和引用
                    content = content.replace(f'({old_name})', f'({new_name})')
                    content = content.replace(f' {old_name}(', f' {new_name}(')
                    content = content.replace(f': {old_name}\n', f': {new_name}\n')
                    content = content.replace(f': {old_name} ', f': {new_name} ')

            return match.group(0)

        content = re.sub(class_pattern, replace_class_name, content)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fix_count, True
        else:
            return 0, False

    except Exception as e:
        print(f"❌ 修复文件失败 {file_path}: {e}")
        return 0, False

def find_n801_files() -> list[Path]:
    """查找包含N801错误的Python文件"""
    import subprocess
    try:
        result = subprocess.run(
            ['ruff', 'check', '--select=N801', '--output-format=text'],
            capture_output=True,
            text=True,
            cwd='.'
        )

        files = set()
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip() and 'N801' in line:
                    file_path = line.split(':')[0]
                    if file_path and file_path.endswith('.py'):
                        files.add(Path(file_path))

        return sorted(list(files))

    except Exception as e:
        print(f"❌ 查找N801文件失败: {e}")
        return []

def main():
    """主函数"""
    print("🔧 N801类名规范修复工具")
    print("=" * 50)

    # 查找需要修复的文件
    files_to_fix = find_n801_files()

    if not files_to_fix:
        print("✅ 没有发现N801错误")
        return

    print(f"📁 发现 {len(files_to_fix)} 个文件需要修复:")
    for file_path in files_to_fix:
        print(f"   - {file_path}")

    print()
    total_fixes = 0
    success_count = 0

    for file_path in files_to_fix:
        print(f"🔧 修复文件: {file_path}")
        fixes, success = fix_n801_in_file(file_path)
        total_fixes += fixes
        if success:
            success_count += 1
            if fixes > 0:
                print(f"   ✅ 修复了 {fixes} 个类名规范问题")
            else:
                print("   ℹ️  没有发现可修复的问题")
        else:
            print("   ❌ 修复失败")
        print()

    print("=" * 50)
    print("📊 修复总结:")
    print(f"   处理文件: {len(files_to_fix)} 个")
    print(f"   成功修复: {success_count} 个")
    print(f"   修复错误: {total_fixes} 个")

    # 验证修复效果
    print()
    print("🔍 验证修复效果...")
    try:
        import subprocess
        result = subprocess.run(
            ['ruff', 'check', '--select=N801', '--output-format=concise'],
            capture_output=True,
            text=True
        )
        remaining = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        print(f"   剩余N801错误: {remaining}个")

        if remaining == 0:
            print("🎉 所有N801错误已修复完成！")
        else:
            print(f"⚠️  还有 {remaining} 个N801错误需要手动处理")

    except Exception as e:
        print(f"❌ 验证失败: {e}")

if __name__ == "__main__":
    main()
