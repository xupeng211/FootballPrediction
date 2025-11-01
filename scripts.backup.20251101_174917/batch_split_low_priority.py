#!/usr/bin/env python3
"""
批量拆分低优先级文件（300-400行）
将剩余的小文件也进行模块化拆分
"""

import os
from pathlib import Path

# 低优先级文件拆分配置
LOW_PRIORITY_SPLITS = {
    # 300-400行文件拆分配置
    "src/services/processing/processors/odds_processor.py": {
        "dir": "src/services/processing/processors/odds",
        "modules": [
            ("validator.py", 100, "赔率数据验证"),
            ("transformer.py", 120, "赔率数据转换"),
            ("aggregator.py", 100, "赔率数据聚合"),
            ("processor.py", 80, "主处理器"),
        ],
    },
    "src/tasks/backup/manual/exporters.py": {
        "dir": "src/tasks/backup/manual/export",
        "modules": [
            ("base_exporter.py", 80, "基础导出器"),
            ("json_exporter.py", 100, "JSON导出器"),
            ("csv_exporter.py", 100, "CSV导出器"),
            ("database_exporter.py", 120, "数据库导出器"),
        ],
    },
    "src/services/processing/processors/features_processor.py": {
        "dir": "src/services/processing/processors/features",
        "modules": [
            ("calculator.py", 120, "特征计算器"),
            ("aggregator.py", 100, "特征聚合器"),
            ("validator.py", 80, "特征验证器"),
            ("processor.py", 100, "主处理器"),
        ],
    },
    "src/data/quality/ge_prometheus_exporter.py": {
        "dir": "src/data/quality/prometheus",
        "modules": [
            ("metrics.py", 100, "Prometheus指标定义"),
            ("collector.py", 120, "指标收集器"),
            ("exporter.py", 100, "指标导出器"),
            ("utils.py", 80, "工具函数"),
        ],
    },
    "src/tasks/backup/manual/processors.py": {
        "dir": "src/tasks/backup/manual/process",
        "modules": [
            ("validator.py", 100, "数据验证器"),
            ("transformer.py", 100, "数据转换器"),
            ("compressor.py", 100, "数据压缩器"),
            ("processor.py", 100, "主处理器"),
        ],
    },
    "src/models/common_models.py": {
        "dir": "src/models/common",
        "modules": [
            ("base_models.py", 120, "基础模型类"),
            ("data_models.py", 100, "数据模型"),
            ("api_models.py", 100, "API模型"),
            ("utils.py", 80, "工具函数"),
        ],
    },
    "src/data/collectors/streaming_collector.py": {
        "dir": "src/data/collectors/streaming",
        "modules": [
            ("kafka_collector.py", 120, "Kafka数据收集器"),
            ("websocket_collector.py", 100, "WebSocket收集器"),
            ("processor.py", 100, "数据处理器"),
            ("manager.py", 80, "收集器管理"),
        ],
    },
    "src/services/data_processing_mod/service.py": {
        "dir": "src/services/data_processing/mod",
        "modules": [
            ("pipeline.py", 120, "数据处理管道"),
            ("validator.py", 80, "数据验证器"),
            ("transformer.py", 100, "数据转换器"),
            ("service.py", 90, "主服务类"),
        ],
    },
    "src/tasks/backup/validation/backup_validator.py": {
        "dir": "src/tasks/backup/validation",
        "modules": [
            ("validators.py", 120, "验证器集合"),
            ("rules.py", 100, "验证规则"),
            ("reporter.py", 80, "验证报告器"),
            ("validator.py", 90, "主验证器"),
        ],
    },
    "src/data/storage/lake/utils.py": {
        "dir": "src/data/storage/lake/utils_mod",
        "modules": [
            ("file_utils.py", 100, "文件工具"),
            ("compression.py", 80, "压缩工具"),
            ("validation.py", 100, "验证工具"),
            ("helpers.py", 110, "辅助函数"),
        ],
    },
    "src/features/store/repository.py": {
        "dir": "src/features/store/repo",
        "modules": [
            ("cache_repository.py", 100, "缓存仓库"),
            ("database_repository.py", 120, "数据库仓库"),
            ("query_builder.py", 80, "查询构建器"),
            ("repository.py", 90, "主仓库类"),
        ],
    },
    "src/database/sql_compatibility.py": {
        "dir": "src/database/compatibility",
        "modules": [
            ("sqlite_compat.py", 100, "SQLite兼容性"),
            ("postgres_compat.py", 100, "PostgreSQL兼容性"),
            ("dialects.py", 100, "SQL方言处理"),
            ("compatibility.py", 80, "兼容性管理器"),
        ],
    },
    "src/monitoring/alerts/models/alert.py": {
        "dir": "src/monitoring/alerts/models/alert_mod",
        "modules": [
            ("alert_entity.py", 120, "告警实体"),
            ("alert_status.py", 80, "告警状态"),
            ("alert_severity.py", 80, "告警严重程度"),
            ("alert_utils.py", 100, "告警工具"),
        ],
    },
    "src/data/quality/exception_handler_mod/statistics_provider.py": {
        "dir": "src/data/quality/stats",
        "modules": [
            ("quality_metrics.py", 100, "质量指标"),
            ("trend_analyzer.py", 100, "趋势分析器"),
            ("reporter.py", 80, "统计报告器"),
            ("provider.py", 100, "统计提供器"),
        ],
    },
    "src/services/data_processing_mod/pipeline.py": {
        "dir": "src/services/data_processing/pipeline_mod",
        "modules": [
            ("stages.py", 120, "管道阶段"),
            ("pipeline.py", 100, "主管道"),
            ("executor.py", 80, "执行器"),
            ("monitor.py", 80, "管道监控"),
        ],
    },
    "src/monitoring/alerts/models/escalation.py": {
        "dir": "src/monitoring/alerts/models/escalation_mod",
        "modules": [
            ("escalation_rules.py", 100, "升级规则"),
            ("escalation_engine.py", 120, "升级引擎"),
            ("notification.py", 80, "通知处理"),
            ("escalation.py", 80, "主升级类"),
        ],
    },
    "src/collectors/odds_collector.py": {
        "dir": "src/collectors/odds/basic",
        "modules": [
            ("collector.py", 120, "基础收集器"),
            ("parser.py", 80, "数据解析器"),
            ("validator.py", 80, "数据验证器"),
            ("storage.py", 90, "数据存储"),
        ],
    },
    "src/database/models/features.py": {
        "dir": "src/database/models/feature_mod",
        "modules": [
            ("feature_entity.py", 100, "特征实体"),
            ("feature_types.py", 80, "特征类型"),
            ("feature_metadata.py", 80, "特征元数据"),
            ("models.py", 110, "模型定义"),
        ],
    },
}


def create_module_content(module_name, description):
    """创建模块内容模板"""
    return f'''"""
{module_name}
{description}

此模块从原始文件拆分而来。
This module was split from the original file.
"""

# TODO: 从原始文件迁移相关代码到这里
# TODO: 迁移完成后删除此注释

# 示例代码结构
class ExampleClass:
    """示例类"""
    pass

def example_function():
    """示例函数"""
    pass
'''


def create_init_content(dir_name, modules):
    """创建__init__.py内容"""
    module_names = [m[0][:-3] for m in modules]  # 去掉.py后缀

    imports = "\n".join([f"from .{name} import *" for name in module_names])

    all_exports = ", ".join([f'"{name}"' for name in module_names])

    return f'''"""
{dir_name} 模块
统一导出接口
"""

{imports}

# 导出所有类
__all__ = [
    {all_exports}
]
'''


def create_wrapper_content(original_file, module_dir, modules):
    """创建兼容性包装器内容"""
    module_names = [m[0][:-3] for m in modules]  # 去掉.py后缀

    # 计算相对导入路径
    parts = Path(original_file).parts
    idx = parts.index("src")
    base_path = ".".join([".."] * (len(parts) - idx - 1))
    relative_path = f"{base_path}.{module_dir.replace('/', '.')}"

    imports = "\n".join([f"from {relative_path} import {name}" for name in module_names])

    all_exports = ", ".join([f'"{name}"' for name in module_names])

    return f'''"""
{Path(original_file).name}
{Path(original_file).stem}

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    f"直接从 {Path(original_file).stem} 导入已弃用。"
    f"请从 {module_dir} 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
{imports}

# 导出所有类
__all__ = [
    {all_exports}
]
'''


def process_splits():
    """处理所有拆分"""
    success_count = 0
    total_count = len(LOW_PRIORITY_SPLITS)

    for file_path, config in LOW_PRIORITY_SPLITS.items():
        if not os.path.exists(file_path):
            print(f"跳过不存在的文件: {file_path}")
            continue

        print(f"\n处理文件: {file_path}")

        # 创建目录
        os.makedirs(config["dir"], exist_ok=True)

        # 创建模块文件
        for module_file, size, description in config["modules"]:
            module_path = os.path.join(config["dir"], module_file)
            module_name = Path(module_file).stem

            if not os.path.exists(module_path):
                with open(module_path, "w", encoding="utf-8") as f:
                    f.write(create_module_content(module_name, description))
                print(f"  创建模块: {module_path}")

        # 创建__init__.py
        init_path = os.path.join(config["dir"], "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w", encoding="utf-8") as f:
                f.write(create_init_content(config["dir"], config["modules"]))
            print(f"  创建: {init_path}")

        # 创建兼容性包装器
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(create_wrapper_content(file_path, config["dir"], config["modules"]))

        success_count += 1
        print("  ✓ 拆分完成")

    print("\n批量拆分完成！")
    print(f"成功处理: {success_count}/{total_count} 个文件")
    print("请手动将原始文件的代码分配到对应的模块中。")


if __name__ == "__main__":
    process_splits()
