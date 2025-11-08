#!/usr/bin/env python3
"""批量修复类命名规范问题"""

import re

# 定义类名映射
class_mappings = {
    'Alert_Manager': 'AlertManager',
    'Apm_Integration': 'ApmIntegration', 
    'Api_Optimizations': 'ApiOptimizations',
    'Database_Optimizations': 'DatabaseOptimizations',
    'Facade_Simple': 'FacadeSimple',
    'Match_Service': 'MatchService',
    'Prediction_Api': 'PredictionApi',
    'Prediction_Service': 'PredictionService',
    'Job_Manager': 'JobManager',
    'Role_BasedAccessControl': 'RoleBasedAccessControl',
    'Kafka_Components': 'KafkaComponents',
    'Kafka_Components_Simple': 'KafkaComponentsSimple',
    'Kafka_Consumer_Simple': 'KafkaConsumerSimple',
    'Kafka_Producer': 'KafkaProducer',
    'Kafka_Producer_Simple': 'KafkaProducerSimple',
    'Stream_Config_Simple': 'StreamConfigSimple',
    'Confluent_Kafka': 'ConfluentKafka',
    'Data_Collection_Core': 'DataCollectionCore',
    'Influxdb_Client': 'InfluxdbClient',
}

import os
import sys

def fix_class_names_in_file(file_path):
    """修复单个文件中的类名"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_name, new_name in class_mappings.items():
            # 使用正则表达式精确匹配类定义
            pattern = rf'class {old_name}:'
            replacement = f'class {new_name}:'
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复了 {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"✗ 处理 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python fix_class_names.py <文件路径>")
        return
    
    file_path = sys.argv[1]
    if os.path.exists(file_path):
        fix_class_names_in_file(file_path)
    else:
        print(f"文件不存在: {file_path}")

if __name__ == "__main__":
    main()
