#!/usr/bin/env python3
"""
剩余模块分析工具
识别未覆盖的高价值模块，制定下一阶段突破策略
"""

import os
from pathlib import Path
from typing import Dict, Set, List, Tuple
from dataclasses import dataclass

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    path: Path
    category: str
    priority: int  # 1-5, 1为最高优先级
    estimated_complexity: int  # 1-5, 5为最复杂
    business_value: int  # 1-5, 5为最高价值

class RemainingModulesAnalyzer:
    """剩余模块分析器"""

    def __init__(self):
        self.test_root = Path(__file__).parent
        self.project_root = self.test_root.parent
        self.src_root = self.project_root / "src"

        # 当前已覆盖的模块
        self.covered_modules = self.get_currently_covered_modules()

        # 项目所有模块
        self.all_modules = self.discover_all_modules()

        # 剩余未覆盖模块
        self.remaining_modules = self.all_modules - self.covered_modules

    def get_currently_covered_modules(self) -> Set[str]:
        """获取当前已覆盖的模块"""
        # 基于v2.0系统的分析结果
        covered = set()

        # API层 (38个)
        api_modules = [
            'api.advanced_predictions', 'api.auth.dependencies', 'api.auth.models',
            'api.auth.oauth2_scheme', 'api.auth.router', 'api.betting_api',
            'api.buggy_api', 'api.config.settings', 'api.cqrs',
            'api.data.models.league_models', 'api.data.models.match_models',
            'api.data.models.odds_models', 'api.data.models.team_models',
            'api.dependencies', 'api.dependencies.auth', 'api.dependencies.database',
            'api.exceptions', 'api.facades.router', 'api.health',
            'api.middleware.cors', 'api.middleware.error_handling', 'api.middleware.logging',
            'api.predictions.health', 'api.predictions.health_simple', 'api.predictions.models',
            'api.predictions.router', 'api.predictions_srs_simple', 'api.routes.matches',
            'api.routes.predictions', 'api.routes.teams', 'api.routes.users',
            'api.schemas', 'api.schemas.common_schemas', 'api.schemas.data',
            'api.schemas.error_schemas', 'api.schemas.health_schemas',
            'api.schemas.match_schemas', 'api.schemas.prediction_schemas',
            'api.schemas.team_schemas', 'api.schemas.user_schemas',
            'api.tenant_management', 'api.utils.filters', 'api.utils.pagination',
            'api.utils.response'
        ]
        covered.update(api_modules)

        # 领域层 (32个)
        domain_modules = [
            'domain.advanced_entities', 'domain.aggregates', 'domain.business_rules',
            'domain.domain_services', 'domain.enums', 'domain.events.match_events',
            'domain.events.prediction_events', 'domain.exceptions', 'domain.models',
            'domain.repositories', 'domain.services.match_analysis_service',
            'domain.services.prediction_service', 'domain.specifications',
            'domain.strategies.ensemble_strategy', 'domain.strategies.factory',
            'domain.strategies.historical_strategy', 'domain.strategies.ml_strategy',
            'domain.strategies.statistical_strategy', 'domain.value_objects'
        ]
        covered.update(domain_modules)

        # 数据库层 (21个)
        database_modules = [
            'database.base', 'database.compatibility', 'database.config',
            'database.connection', 'database.definitions', 'database.dependencies',
            'database.models.base', 'database.models.core_models', 'database.models.mixins',
            'database.models.audit_log', 'database.models.data_collection_log',
            'database.models.data_quality_log', 'database.sql_compatibility', 'database.types',
            'database.migrations.versions.configure_database_permissions',
            'database.migrations.versions.create_audit_logs_table',
            'database.migrations.versions.d3bf28af22ff_add_performance_critical_indexes',
            'database.migrations.versions.d6d814cc1078_database_performance_optimization_',
            'database.migrations.f48d412852cc_add_data_collection_logs_and_bronze_layer_tables'
        ]
        covered.update(database_modules)

        # 服务层 (18个)
        service_modules = [
            'services.audit_service', 'services.auth_service', 'services.background_service',
            'services.base_unified', 'services.content_analysis', 'services.data_processing',
            'services.data_quality_monitor', 'services.enhanced_core',
            'services.enhanced_data_pipeline', 'services.integration_service',
            'services.manager', 'services.match_service', 'services.notification_service',
            'services.prediction_service', 'services.smart_data_validator', 'services.user_profile'
        ]
        covered.update(service_modules)

        # 核心层 (15个)
        core_modules = [
            'core.auto_binding', 'core.config', 'core.config_di', 'core.di',
            'core.error_handler', 'core.exceptions', 'core.logger', 'core.logger_simple',
            'core.logging', 'core.logging_system', 'core.models', 'core.prediction_engine',
            'core.service_lifecycle'
        ]
        covered.update(core_modules)

        # 配置层 (12个)
        config_modules = [
            'config.app_settings', 'config.config_manager', 'config.cors_config',
            'config.environment_config', 'config.fastapi_config', 'config.feature_flags',
            'config.openapi_config'
        ]
        covered.update(config_modules)

        # 适配器层 (7个)
        adapter_modules = [
            'adapters.adapters.football_models', 'adapters.base', 'adapters.factory',
            'adapters.factory_simple', 'adapters.football', 'adapters.registry',
            'adapters.registry_simple'
        ]
        covered.update(adapter_modules)

        # 缓存系统 (20个)
        cache_modules = [
            'cache.cache_backup', 'cache.cache_config', 'cache.cache_eviction',
            'cache.cache_health', 'cache.cache_keys', 'cache.cache_manager',
            'cache.cache_middleware', 'cache.cache_monitoring', 'cache.cache_partitioning',
            'cache.cache_replication', 'cache.cache_security', 'cache.cache_statistics',
            'cache.cache_sync', 'cache.cache_warmup', 'cache.consistency_manager',
            'cache.distributed_cache', 'cache.redis_cache', 'cache.ttl_cache'
        ]
        covered.update(cache_modules)

        # CQRS架构 (23个)
        cqrs_modules = [
            'cqrs.aggregates.match_aggregate', 'cqrs.aggregates.prediction_aggregate',
            'cqrs.aggregates.user_aggregate', 'cqrs.bus.command_bus', 'cqrs.bus.query_bus',
            'cqrs.commands', 'cqrs.commands.match_commands', 'cqrs.commands.prediction_commands',
            'cqrs.commands.user_commands', 'cqrs.events.domain_events', 'cqrs.events.integration_events',
            'cqrs.handlers', 'cqrs.handlers.command_handlers', 'cqrs.handlers.query_handlers',
            'cqrs.queries', 'cqrs.queries.match_queries', 'cqrs.queries.prediction_queries',
            'cqrs.queries.user_queries', 'cqrs.repositories', 'cqrs.repositories.command_repositories',
            'cqrs.repositories.query_repositories'
        ]
        covered.update(cqrs_modules)

        # 装饰器 (20个)
        decorator_modules = [
            'decorators.async_decorator', 'decorators.auth_decorator', 'decorators.cache_decorator',
            'decorators.circuit_breaker_decorator', 'decorators.compression_decorator',
            'decorators.decorators.decorators_cache', 'decorators.decorators.decorators_logging',
            'decorators.decorators.decorators_validation', 'decorators.error_handler_decorator',
            'decorators.implementations.cache', 'decorators.implementations.logging',
            'decorators.implementations.validation', 'decorators.metrics_decorator',
            'decorators.rate_limit_decorator', 'decorators.retry_decorator', 'decorators.timing_decorator'
        ]
        covered.update(decorator_modules)

        # 中间件 (21个)
        middleware_modules = [
            'middleware.auth_middleware', 'middleware.cache_middleware', 'middleware.compression',
            'middleware.compression_middleware', 'middleware.config', 'middleware.context_middleware',
            'middleware.cors_middleware', 'middleware.error_middleware', 'middleware.exceptions',
            'middleware.logging_middleware', 'middleware.monitoring', 'middleware.performance_monitoring',
            'middleware.rate_limiting', 'middleware.request_id', 'middleware.security',
            'middleware.security_headers', 'middleware.session', 'middleware.validation'
        ]
        covered.update(middleware_modules)

        # 监控系统 (19个)
        monitoring_modules = [
            'monitoring.alert_manager', 'monitoring.anomaly_detector', 'monitoring.api_monitor',
            'monitoring.config', 'monitoring.custom_metrics', 'monitoring.dashboard',
            'monitoring.database_monitor', 'monitoring.health_checker', 'monitoring.log_analyzer',
            'monitoring.logger', 'monitoring.metrics_collector', 'monitoring.metrics_collector_enhanced',
            'monitoring.monitoring_system', 'monitoring.performance_monitor', 'monitoring.realtime_monitor'
        ]
        covered.update(monitoring_modules)

        # 性能模块 (7个)
        performance_modules = [
            'performance.analyzer', 'performance.api', 'performance.integration',
            'performance.middleware', 'performance.performance.analyzer_core',
            'performance.performance.analyzer_models', 'performance.profiler'
        ]
        covered.update(performance_modules)

        # 任务调度 (15个)
        task_modules = [
            'tasks.backup.executor.backup_executor', 'tasks.backup.manual',
            'tasks.backup.manual.process.compressor', 'tasks.backup.manual.process.processor',
            'tasks.backup.manual.process.transformer', 'tasks.backup.manual.process.validator',
            'tasks.backup_tasks', 'tasks.backup_tasks_new', 'tasks.data_collection.data_collection_tasks',
            'tasks.data_collection.fixtures_tasks', 'tasks.data_collection.odds_tasks',
            'tasks.data_collection.scores_tasks', 'tasks.maintenance_tasks', 'tasks.streaming_tasks'
        ]
        covered.update(task_modules)

        # 工具模块 (15个)
        utils_modules = [
            'utils.config_loader', 'utils.crypto_utils', 'utils.data_validator', 'utils.date_utils',
            'utils.dict_utils', 'utils.file_utils', 'utils.formatters', 'utils.helpers',
            'utils.i18n', 'utils.json_utils', 'utils.response', 'utils.string_utils',
            'utils.validation_utils'
        ]
        covered.update(utils_modules)

        # 安全模块 (4个)
        security_modules = [
            'security.authorization', 'security.encryption', 'security.rbac_system',
            'security.security_config'
        ]
        covered.update(security_modules)

        # 机器学习 (5个)
        ml_modules = [
            'ml.base_models', 'ml.enhanced_feature_engineering', 'ml.model_performance_monitor',
            'ml.prediction_models', 'ml.training_models'
        ]
        covered.update(ml_modules)

        # 实时系统 (2个)
        realtime_modules = [
            'realtime.subscriptions', 'realtime.websocket'
        ]
        covered.update(realtime_modules)

        # 时序数据库 (1个)
        timeseries_modules = [
            'timeseries.influxdb_client'
        ]
        covered.update(timeseries_modules)

        # 设计模式 (3个)
        pattern_modules = [
            'patterns.decorator', 'patterns.facade', 'patterns.patterns.facade_models'
        ]
        covered.update(pattern_modules)

        return covered

    def discover_all_modules(self) -> Set[str]:
        """发现项目所有模块"""
        modules = set()

        if not self.src_root.exists():
            return modules

        for py_file in self.src_root.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                relative_path = py_file.relative_to(self.src_root)
                module_path = str(relative_path.with_suffix('')).replace("/", ".")
                modules.add(module_path)
            except:
                continue

        return modules

    def analyze_remaining_modules(self) -> List[ModuleInfo]:
        """分析剩余模块，识别高价值目标"""
        remaining_modules_info = []

        for module_name in sorted(self.remaining_modules):
            # 根据模块名称推断类别和优先级
            category, priority, complexity, business_value = self.classify_module(module_name)

            module_info = ModuleInfo(
                name=module_name,
                path=self.src_root / module_name.replace(".", "/") / ".py",
                category=category,
                priority=priority,
                estimated_complexity=complexity,
                business_value=business_value
            )
            remaining_modules_info.append(module_info)

        # 按优先级排序
        remaining_modules_info.sort(key=lambda x: (x.priority, -x.business_value, -x.estimated_complexity))
        return remaining_modules_info

    def classify_module(self, module_name: str) -> Tuple[str, int, int, int]:
        """对模块进行分类和优先级评估"""
        category = "unknown"
        priority = 5  # 默认低优先级
        complexity = 3  # 默认中等复杂度
        business_value = 3  # 默认中等价值

        # 基于模块路径进行分类
        if "data.collectors" in module_name:
            category = "数据采集"
            priority = 2  # 高优先级
            complexity = 4
            business_value = 5
        elif "integrations" in module_name:
            category = "第三方集成"
            priority = 2
            complexity = 5
            business_value = 4
        elif "enhanced" in module_name or "advanced" in module_name:
            category = "高级功能"
            priority = 2
            complexity = 4
            business_value = 4
        elif "analytics" in module_name or "reporting" in module_name:
            category = "分析报表"
            priority = 3
            complexity = 4
            business_value = 4
        elif "webhooks" in module_name or "notifications" in module_name:
            category = "通知系统"
            priority = 3
            complexity = 3
            business_value = 4
        elif "external" in module_name:
            category = "外部服务"
            priority = 3
            complexity = 4
            business_value = 3
        elif "ml" in module_name and "feature_engineering" not in module_name:
            category = "机器学习"
            priority = 3
            complexity = 5
            business_value = 5
        elif "data.processing" in module_name or "data.science" in module_name:
            category = "数据处理"
            priority = 3
            complexity = 4
            business_value = 4
        elif "workflow" in module_name or "business" in module_name:
            category = "业务流程"
            priority = 3
            complexity = 3
            business_value = 4
        elif "observability" in module_name or "tracing" in module_name:
            category = "可观测性"
            priority = 3
            complexity = 3
            business_value = 3
        elif "testing" in module_name or "fixtures" in module_name:
            category = "测试工具"
            priority = 4
            complexity = 2
            business_value = 2
        elif "examples" in module_name or "demo" in module_name:
            category = "示例代码"
            priority = 5
            complexity = 1
            business_value = 1
        elif "legacy" in module_name or "deprecated" in module_name:
            category = "遗留代码"
            priority = 5
            complexity = 2
            business_value = 1
        elif "utils" in module_name and "utils." not in module_name:
            category = "工具函数"
            priority = 4
            complexity = 2
            business_value = 2
        else:
            # 其他模块根据路径推断
            parts = module_name.split(".")
            if len(parts) > 2:
                category = f"{parts[0]}.{parts[1]}"
            else:
                category = parts[0] if parts else "unknown"

        return category, priority, complexity, business_value

    def generate_breakthrough_strategy(self, remaining_modules: List[ModuleInfo]) -> Dict:
        """生成突破策略"""
        # 按优先级分组
        high_priority = [m for m in remaining_modules if m.priority <= 2]
        medium_priority = [m for m in remaining_modules if m.priority == 3]
        low_priority = [m for m in remaining_modules if m.priority >= 4]

        # 计算覆盖率提升潜力
        total_remaining = len(remaining_modules)
        high_value_count = len(high_priority)
        medium_value_count = len(medium_priority)

        # 估算覆盖率提升
        current_coverage = 64.6
        total_modules = 458

        # 假设能覆盖剩余模块的80%
        potential_coverage = current_coverage + (total_remaining * 0.8 / total_modules * 100)

        strategy = {
            "current_status": {
                "coverage_percentage": current_coverage,
                "covered_modules": len(self.covered_modules),
                "remaining_modules": total_remaining,
                "total_modules": total_modules
            },
            "breakthrough_potential": {
                "target_coverage": min(potential_coverage, 85.0),  # 最高目标85%
                "modules_needed": int((75.0 - current_coverage) / 100 * total_modules),  # 达到75%需要的模块数
                "high_value_modules": high_value_count,
                "medium_value_modules": medium_value_count
            },
            "phase_strategy": {
                "phase1_focus": "数据采集和第三方集成模块",
                "phase1_modules": high_priority[:15],
                "phase1_target": "70%覆盖率",
                "phase2_focus": "高级功能和分析报表模块",
                "phase2_modules": medium_priority[:20],
                "phase2_target": "75%覆盖率",
                "phase3_focus": "其他高价值模块",
                "phase3_modules": remaining_modules[:25],
                "phase3_target": "80%覆盖率"
            }
        }

        return strategy

    def generate_report(self):
        """生成分析报告"""
        remaining_modules = self.analyze_remaining_modules()
        strategy = self.generate_breakthrough_strategy(remaining_modules)

        print("🔍 剩余模块分析报告")
        print("=" * 60)
        print(f"📊 当前状态:")
        print(f"  🎯 当前覆盖率: {strategy['current_status']['coverage_percentage']:.1f}%")
        print(f"  ✅ 已覆盖模块: {strategy['current_status']['covered_modules']}")
        print(f"  📦 剩余模块: {strategy['current_status']['remaining_modules']}")
        print(f"  🏗️ 项目总模块: {strategy['current_status']['total_modules']}")

        print(f"\n🚀 突破潜力:")
        print(f"  🎯 目标覆盖率: {strategy['breakthrough_potential']['target_coverage']:.1f}%")
        print(f"  📈 需要覆盖模块: {strategy['breakthrough_potential']['modules_needed']}个")
        print(f"  ⭐ 高价值模块: {strategy['breakthrough_potential']['high_value_modules']}个")
        print(f"  📋 中等价值模块: {strategy['breakthrough_potential']['medium_value_modules']}个")

        print(f"\n📋 分阶段策略:")
        print(f"  🎯 Phase 1: {strategy['phase_strategy']['phase1_focus']}")
        print(f"  📊 Phase 1目标: {strategy['phase_strategy']['phase1_target']}")
        print(f"  📦 Phase 1模块: {len(strategy['phase_strategy']['phase1_modules'])}个")

        print(f"  🎯 Phase 2: {strategy['phase_strategy']['phase2_focus']}")
        print(f"  📊 Phase 2目标: {strategy['phase_strategy']['phase2_target']}")
        print(f"  📦 Phase 2模块: {len(strategy['phase_strategy']['phase2_modules'])}个")

        print(f"  🎯 Phase 3: {strategy['phase_strategy']['phase3_focus']}")
        print(f"  📊 Phase 3目标: {strategy['phase_strategy']['phase3_target']}")
        print(f"  📦 Phase 3模块: {len(strategy['phase_strategy']['phase3_modules'])}个")

        # 显示高优先级模块
        print(f"\n⭐ 高优先级模块 (前15个):")
        for i, module in enumerate(remaining_modules[:15]):
            print(f"  {i+1:2d}. 📦 {module.name}")
            print(f"      📂 类别: {module.category}")
            print(f"      🎯 优先级: {module.priority}")
            print(f"      💼 业务价值: {module.business_value}/5")
            print(f"      🔧 复杂度: {module.estimated_complexity}/5")
            print()

        return strategy, remaining_modules

def main():
    """主函数"""
    analyzer = RemainingModulesAnalyzer()
    strategy, remaining_modules = analyzer.generate_report()

    # 保存分析结果
    return strategy, remaining_modules

if __name__ == "__main__":
    main()