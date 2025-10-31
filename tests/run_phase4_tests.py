#!/usr/bin/env python3
"""
Phase 4 测试运行器
不依赖pytest，使用Python标准库运行测试
"""

import unittest
import sys
import os
import time
from io import StringIO

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Phase4TestResult:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
        self.start_time = time.time()
        self.end_time = None

    def add_success(self, test_name):
        self.total_tests += 1
        self.passed_tests += 1
        print(f"✓ {test_name}")

    def add_failure(self, test_name, error):
        self.total_tests += 1
        self.failed_tests += 1
        self.errors.append((test_name, str(error)))
        print(f"✗ {test_name}")
        print(f"  错误: {error}")

    def finish(self):
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        print("\n" + "="*60)
        print("Phase 4 测试结果总结")
        print("="*60)
        print(f"总测试数: {self.total_tests}")
        print(f"通过: {self.passed_tests}")
        print(f"失败: {self.failed_tests}")
        print(f"成功率: {self.passed_tests/self.total_tests*100:.1f}%" if self.total_tests > 0 else "成功率: 0%")
        print(f"执行时间: {duration:.2f}秒")

        if self.errors:
            print("\n失败的测试:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")

        return self.failed_tests == 0

def run_test_function(test_func, test_name, result):
    """运行单个测试函数"""
    try:
        test_func()
        result.add_success(test_name)
    except Exception as e:
        result.add_failure(test_name, e)

def run_adapters_tests():
    """运行适配器模块测试"""
    print("\n" + "="*40)
    print("运行适配器模块测试")
    print("="*40)

    result = Phase4TestResult()

    # 导入测试函数
    try:
        from test_phase4_adapters_modules_comprehensive import (
            TestAdapterPattern, TestFactoryPattern, TestRegistryPattern, TestFootballAdapters
        )

        adapter_test = TestAdapterPattern()
        factory_test = TestFactoryPattern()
        registry_test = TestRegistryPattern()
        football_test = TestFootballAdapters()

        # 运行适配器模式测试
        run_test_function(adapter_test.test_adapter_interface, "适配器接口测试", result)
        run_test_function(adapter_test.test_base_adapter, "基础适配器测试", result)
        run_test_function(adapter_test.test_adapter_chain, "适配器链测试", result)
        run_test_function(adapter_test.test_data_transformation, "数据转换测试", result)
        run_test_function(adapter_test.test_error_handling, "错误处理测试", result)

        # 运行工厂模式测试
        run_test_function(factory_test.test_simple_factory, "简单工厂测试", result)
        run_test_function(factory_test.test_factory_with_config, "配置工厂测试", result)
        run_test_function(factory_test.test_factory_error_handling, "工厂错误处理测试", result)

        # 运行注册表模式测试
        run_test_function(registry_test.test_basic_registry, "基础注册表测试", result)
        run_test_function(registry_test.test_registry_with_validation, "注册表验证测试", result)
        run_test_function(registry_test.test_registry_lifecycle, "注册表生命周期测试", result)

        # 运行足球适配器测试
        run_test_function(football_test.test_team_adapter, "球队适配器测试", result)
        run_test_function(football_test.test_match_adapter, "比赛适配器测试", result)
        run_test_function(football_test.test_prediction_adapter, "预测适配器测试", result)

    except Exception as e:
        result.add_failure("模块导入", f"无法导入测试模块: {e}")

    return result.finish()

def run_monitoring_tests():
    """运行监控模块测试"""
    print("\n" + "="*40)
    print("运行监控模块测试")
    print("="*40)

    result = Phase4TestResult()

    try:
        from test_phase4_monitoring_modules_comprehensive import (
            TestHealthChecker, TestMetricsCollector, TestAlertHandler, TestSystemMonitor
        )

        health_test = TestHealthChecker()
        metrics_test = TestMetricsCollector()
        alert_test = TestAlertHandler()
        monitor_test = TestSystemMonitor()

        # 运行健康检查测试
        run_test_function(health_test.test_basic_health_check, "基础健康检查测试", result)
        run_test_function(health_test.test_timeout_handling, "超时处理测试", result)
        run_test_function(health_test.test_component_dependencies, "组件依赖测试", result)

        # 运行指标收集测试
        run_test_function(metrics_test.test_counter_metrics, "计数器指标测试", result)
        run_test_function(metrics_test.test_gauge_metrics, "仪表指标测试", result)
        run_test_function(metrics_test.test_histogram_metrics, "直方图指标测试", result)

        # 运行警报处理测试
        run_test_function(alert_test.test_alert_creation, "警报创建测试", result)
        run_test_function(alert_test.test_alert_filtering, "警报过滤测试", result)
        run_test_function(alert_test.test_alert_deduplication, "警报去重测试", result)

        # 运行系统监控测试
        run_test_function(monitor_test.test_cpu_monitoring, "CPU监控测试", result)
        run_test_function(monitor_test.test_memory_monitoring, "内存监控测试", result)
        run_test_function(monitor_test.test_disk_monitoring, "磁盘监控测试", result)

    except Exception as e:
        result.add_failure("模块导入", f"无法导入测试模块: {e}")

    return result.finish()

def run_patterns_tests():
    """运行设计模式测试"""
    print("\n" + "="*40)
    print("运行设计模式测试")
    print("="*40)

    result = Phase4TestResult()

    try:
        from test_phase4_patterns_modules_comprehensive import (
            TestStrategyPattern, TestFactoryPattern, TestObserverPattern,
            TestRepositoryPattern, TestBuilderPattern, TestCommandPattern,
            TestDecoratorPattern, TestProxyPattern, TestCompositePattern
        )

        strategy_test = TestStrategyPattern()
        factory_test = TestFactoryPattern()
        observer_test = TestObserverPattern()
        repository_test = TestRepositoryPattern()
        builder_test = TestBuilderPattern()
        command_test = TestCommandPattern()
        decorator_test = TestDecoratorPattern()
        proxy_test = TestProxyPattern()
        composite_test = TestCompositePattern()

        # 运行策略模式测试
        run_test_function(strategy_test.test_strategy_interface, "策略接口测试", result)
        run_test_function(strategy_test.test_strategy_context, "策略上下文测试", result)
        run_test_function(strategy_test.test_multiple_strategies, "多策略测试", result)

        # 运行工厂模式测试
        run_test_function(factory_test.test_simple_factory, "简单工厂测试", result)
        run_test_function(factory_test.test_abstract_factory, "抽象工厂测试", result)
        run_test_function(factory_test.test_factory_with_registration, "注册工厂测试", result)

        # 运行观察者模式测试
        run_test_function(observer_test.test_subject_observer, "主题观察者测试", result)
        run_test_function(observer_test.test_event_system, "事件系统测试", result)

        # 运行仓储模式测试
        run_test_function(repository_test.test_repository_interface, "仓储接口测试", result)
        run_test_function(repository_test.test_repository_with_criteria, "条件查询测试", result)

        # 运行建造者模式测试
        run_test_function(builder_test.test_prediction_builder, "预测建造者测试", result)

        # 运行命令模式测试
        run_test_function(command_test.test_command_execution, "命令执行测试", result)
        run_test_function(command_test.test_invoker, "调用者测试", result)

        # 运行装饰器模式测试
        run_test_function(decorator_test.test_function_decorator, "函数装饰器测试", result)
        run_test_function(decorator_test.test_class_decorator, "类装饰器测试", result)

        # 运行代理模式测试
        run_test_function(proxy_test.test_virtual_proxy, "虚拟代理测试", result)

        # 运行组合模式测试
        run_test_function(composite_test.test_team_composite, "团队组合测试", result)
        run_test_function(composite_test.test_nested_composite, "嵌套组合测试", result)

    except Exception as e:
        result.add_failure("模块导入", f"无法导入测试模块: {e}")

    return result.finish()

def run_domain_tests():
    """运行领域模块测试"""
    print("\n" + "="*40)
    print("运行领域模块测试")
    print("="*40)

    result = Phase4TestResult()

    try:
        from test_phase4_domain_modules_comprehensive import (
            TestDomainEntities, TestValueObjects, TestDomainServices,
            TestDomainEvents, TestAggregateRoots
        )

        entity_test = TestDomainEntities()
        value_test = TestValueObjects()
        service_test = TestDomainServices()
        event_test = TestDomainEvents()
        aggregate_test = TestAggregateRoots()

        # 运行实体测试
        run_test_function(entity_test.test_match_entity, "比赛实体测试", result)
        run_test_function(entity_test.test_team_entity, "球队实体测试", result)
        run_test_function(entity_test.test_prediction_entity, "预测实体测试", result)

        # 运行值对象测试
        run_test_function(value_test.test_score_value_object, "比分值对象测试", result)
        run_test_function(value_test.test_odds_value_object, "赔率值对象测试", result)
        run_test_function(value_test.test_money_value_object, "金额值对象测试", result)

        # 运行领域服务测试
        run_test_function(service_test.test_prediction_calculation_service, "预测计算服务测试", result)
        run_test_function(service_test.test_match_analytics_service, "比赛分析服务测试", result)

        # 运行领域事件测试
        run_test_function(event_test.test_domain_event_base, "领域事件基类测试", result)
        run_test_function(event_test.test_match_events, "比赛事件测试", result)
        run_test_function(event_test.test_prediction_events, "预测事件测试", result)
        run_test_function(event_test.test_event_aggregate, "事件聚合测试", result)

        # 运行聚合根测试
        run_test_function(aggregate_test.test_match_aggregate_root, "比赛聚合根测试", result)

    except Exception as e:
        result.add_failure("模块导入", f"无法导入测试模块: {e}")

    return result.finish()

def main():
    """主测试运行器"""
    print("🚀 Phase 4 综合测试运行器")
    print("="*60)
    print("测试模块: adapters, monitoring, patterns, domain")
    print("="*60)

    total_start_time = time.time()
    all_results = []

    try:
        # 运行各模块测试
        adapters_result = run_adapters_tests()
        all_results.append(("适配器模块", adapters_result))

        monitoring_result = run_monitoring_tests()
        all_results.append(("监控模块", monitoring_result))

        patterns_result = run_patterns_tests()
        all_results.append(("设计模式模块", patterns_result))

        domain_result = run_domain_tests()
        all_results.append(("领域模块", domain_result))

    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试运行器错误: {e}")
        return False

    # 总结报告
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time

    print("\n" + "="*80)
    print("🎯 Phase 4 综合测试最终报告")
    print("="*80)

    total_tests = sum(result.total_tests for _, result in all_results if isinstance(result, Phase4TestResult))
    total_passed = sum(result.passed_tests for _, result in all_results if isinstance(result, Phase4TestResult))
    total_failed = sum(result.failed_tests for _, result in all_results if isinstance(result, Phase4TestResult))

    print(f"总执行时间: {total_duration:.2f}秒")
    print(f"总测试数: {total_tests}")
    print(f"总通过数: {total_passed}")
    print(f"总失败数: {total_failed}")

    if total_tests > 0:
        overall_success_rate = (total_passed / total_tests) * 100
        print(f"总体成功率: {overall_success_rate:.1f}%")

    print("\n各模块详细结果:")
    for module_name, result in all_results:
        status = "✅ 通过" if result.failed_tests == 0 else "❌ 失败"
        print(f"  {module_name}: {result.passed_tests}/{result.total_tests} {status}")

    # 结论
    if total_failed == 0:
        print("\n🎉 所有测试通过！Phase 4 模块扩展成功完成！")
        print("✅ 新增测试用例已验证工作正常")
        print("✅ 代码覆盖率预期将有显著提升")
        return True
    else:
        print(f"\n⚠️ 有 {total_failed} 个测试失败")
        print("需要修复失败的测试用例")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)