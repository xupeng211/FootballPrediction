#!/usr/bin/env python3
"""
批量拆分文件脚本
Batch File Splitting Script
"""

from pathlib import Path
from typing import Dict, List, Tuple

# 定义要拆分的文件和它们的模块结构
SPLIT_CONFIGS = {
    "src/api/data.py": {
        "dir": "src/api/data/endpoints",
        "modules": [
            ("matches.py", 180, "比赛API端点"),
            ("teams.py", 120, "球队API端点"),
            ("leagues.py", 100, "联赛API端点"),
            ("odds.py", 90, "赔率API端点"),
            ("statistics.py", 150, "统计API端点"),
            ("dependencies.py", 80, "依赖注入"),
        ],
    },
    "src/core/error_handler.py": {
        "dir": "src/core/error_handling",
        "modules": [
            ("error_handler.py", 200, "主错误处理器"),
            ("exceptions.py", 150, "异常定义"),
            ("serializers.py", 100, "错误序列化"),
            ("middleware.py", 120, "中间件"),
            ("handlers.py", 80, "处理器集合"),
        ],
    },
    "src/api/health.py": {
        "dir": "src/api/health",
        "modules": [
            ("health_checker.py", 200, "健康检查器"),
            ("checks.py", 180, "检查项目"),
            ("models.py", 100, "响应模型"),
            ("utils.py", 80, "工具函数"),
        ],
    },
    "src/scheduler/task_scheduler.py": {
        "dir": "src/scheduler/core",
        "modules": [
            ("task_scheduler.py", 250, "主调度器"),
            ("executor.py", 150, "执行器"),
            ("queue.py", 100, "队列管理"),
            ("monitor.py", 80, "监控器"),
        ],
    },
    "src/lineage/metadata_manager.py": {
        "dir": "src/lineage/metadata",
        "modules": [
            ("metadata_manager.py", 200, "主管理器"),
            ("storage.py", 150, "存储管理"),
            ("query.py", 100, "查询器"),
            ("serializer.py", 80, "序列化器"),
        ],
    },
    "src/streaming/kafka_producer.py": {
        "dir": "src/streaming/producer",
        "modules": [
            ("kafka_producer.py", 250, "主生产者"),
            ("message_builder.py", 150, "消息构建器"),
            ("partitioner.py", 100, "分区器"),
            ("retry_handler.py", 80, "重试处理"),
        ],
    },
    "src/api/features.py": {
        "dir": "src/api/features",
        "modules": [
            ("features_api.py", 200, "特征API主类"),
            ("endpoints.py", 150, "端点定义"),
            ("models.py", 100, "数据模型"),
            ("services.py", 80, "服务层"),
        ],
    },
    "src/models/prediction_service_refactored.py": {
        "dir": "src/models/prediction/refactored",
        "modules": [
            ("prediction_service.py", 200, "主服务"),
            ("predictors.py", 150, "预测器"),
            ("validators.py", 100, "验证器"),
            ("cache.py", 80, "缓存管理"),
        ],
    },
    "src/monitoring/alert_manager_mod/aggregator.py": {
        "dir": "src/monitoring/alerts/aggregation",
        "modules": [
            ("aggregator.py", 200, "聚合器"),
            ("deduplicator.py", 150, "去重器"),
            ("grouping.py", 120, "分组器"),
            ("silence.py", 100, "静默管理"),
        ],
    },
    "src/services/audit_service_mod/storage.py": {
        "dir": "src/services/audit/storage",
        "modules": [
            ("storage.py", 200, "存储接口"),
            ("database.py", 150, "数据库存储"),
            ("file_storage.py", 120, "文件存储"),
            ("cache.py", 100, "缓存管理"),
        ],
    },
    "src/monitoring/alert_manager_mod/rules.py": {
        "dir": "src/monitoring/alerts/rules",
        "modules": [
            ("rules.py", 200, "规则管理"),
            ("conditions.py", 150, "条件评估"),
            ("actions.py", 100, "动作执行"),
            ("evaluation.py", 100, "评估引擎"),
        ],
    },
    "src/monitoring/system_monitor_mod/health_checks.py": {
        "dir": "src/monitoring/system/health",
        "modules": [
            ("health_checker.py", 200, "健康检查器"),
            ("checks.py", 180, "检查项"),
            ("reporters.py", 100, "报告器"),
            ("utils.py", 80, "工具函数"),
        ],
    },
    "src/scheduler/dependency_resolver.py": {
        "dir": "src/scheduler/dependency",
        "modules": [
            ("resolver.py", 200, "依赖解析器"),
            ("graph.py", 150, "依赖图"),
            ("analyzer.py", 100, "分析器"),
            ("validator.py", 80, "验证器"),
        ],
    },
}


def create_module_template(module_name: str, description: str) -> str:
    """创建模块模板"""
    return f'''"""
{description}
{module_name}
"""

from typing import Any, Dict, List, Optional

# TODO: 从原始文件中提取相关代码并放在这里


'''


def create_init_file(modules: List[Tuple[str, int, str]]) -> str:
    """创建__init__.py文件"""
    imports = []
    exports = []

    for module_name, _, description in modules:
        class_name = module_name.replace(".py", "").title().replace("_", "")
        imports.append(f"from .{module_name.replace('.py', '')} import *")
        exports.append(f'"{class_name}"')

    return f'''"""
模块导出
Module Exports
"""

{chr(10).join(imports)}

__all__ = [
{chr(10).join(f"    {export}" for export in exports)}
]
'''


def create_compatibility_file(
    original_file: str, new_dir: str, modules: List[Tuple[str, int, str]]
) -> str:
    """创建向后兼容文件"""
    module_path = new_dir.replace("src/", "").replace("/", ".")

    imports = []
    exports = []

    for module_name, _, _ in modules:
        base_name = module_name.replace(".py", "")
        # 尝试猜测可能的类名
        class_name = base_name.title().replace("_", "")
        if "Api" in base_name:
            class_name = class_name.replace("Api", "API")
        imports.append(f"from .{module_path}.{base_name} import *")
        exports.append(f'"{class_name}"')

    return f'''"""
{Path(original_file).name}
{Path(original_file).stem.title()}

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    f"直接从 {Path(original_file).stem} 导入已弃用。"
    f"请从 {module_path} 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
{chr(10).join(imports)}

# 导出所有类
__all__ = [
{chr(10).join(f"    {export}" for export in exports)}
]
'''


def split_file(file_path: str, config: Dict):
    """拆分单个文件"""
    print(f"\n处理文件: {file_path}")

    # 创建目录
    dir_path = Path(config["dir"])
    dir_path.mkdir(parents=True, exist_ok=True)

    # 创建__init__.py
    init_content = create_init_file(config["modules"])
    (dir_path / "__init__.py").write_text(init_content, encoding="utf-8")

    # 创建模块文件
    for module_name, _, description in config["modules"]:
        module_path = dir_path / module_name
        template = create_module_template(module_name, description)
        module_path.write_text(template, encoding="utf-8")
        print(f"  创建模块: {module_path}")

    # 创建向后兼容文件
    compat_content = create_compatibility_file(file_path, config["dir"], config["modules"])
    Path(file_path).write_text(compat_content, encoding="utf-8")
    print(f"  更新兼容文件: {file_path}")


def main():
    """主函数"""
    print("开始批量拆分文件...")

    for file_path, config in SPLIT_CONFIGS.items():
        if Path(file_path).exists():
            split_file(file_path, config)
        else:
            print(f"文件不存在: {file_path}")

    print("\n批量拆分完成！")
    print("请手动将原始文件的代码分配到对应的模块中。")


if __name__ == "__main__":
    main()
