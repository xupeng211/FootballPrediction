#!/usr/bin/env python3
"""
P8.1 简化的失败测试聚类分析
直接分析失败测试列表
"""

import re
from collections import defaultdict, Counter
from pathlib import Path

def parse_failed_tests():
    """解析失败测试列表"""
    failed_tests = []

    with open('/tmp/failed_tests_list.txt', 'r') as f:
        for line in f:
            # 解析格式: tests/module/file.py::Class::test_name FAILED [ x%]
            match = re.match(r'(tests/.+?)::(.+?)\s+FAILED', line.strip())
            if match:
                test_path, test_full_name = match.groups()

                # 分离类名和测试方法名
                if '::' in test_full_name:
                    class_name, test_method = test_full_name.split('::', 1)
                else:
                    class_name = test_full_name
                    test_method = test_full_name

                failed_tests.append({
                    'full_path': line.strip(),
                    'test_path': test_path,
                    'class_name': class_name,
                    'test_method': test_method,
                    'module': extract_module(test_path),
                    'test_type': extract_test_type(test_path),
                    'functional_area': extract_functional_area(test_full_name),
                    'error_pattern': identify_error_pattern(test_method)
                })

    return failed_tests

def extract_module(test_path):
    """从测试路径提取模块"""
    if '/api/' in test_path:
        return 'API'
    elif '/integration/' in test_path:
        return 'INTEGRATION'
    elif '/unit/' in test_path:
        return 'UNIT'
    else:
        return 'OTHER'

def extract_test_type(test_path):
    """提取测试类型"""
    if 'auth' in test_path:
        return 'AUTH'
    elif 'cache' in test_path:
        return 'CACHE'
    elif 'api' in test_path:
        return 'API'
    elif 'database' in test_path or 'db' in test_path:
        return 'DATABASE'
    elif 'ml' in test_path:
        return 'ML'
    elif 'services' in test_path:
        return 'SERVICES'
    elif 'core' in test_path:
        return 'CORE'
    else:
        return 'GENERAL'

def extract_functional_area(test_full_name):
    """提取功能区域"""
    test_lower = test_full_name.lower()
    if 'health' in test_lower:
        return 'HEALTH_CHECK'
    elif 'auth' in test_lower:
        return 'AUTHENTICATION'
    elif 'cache' in test_lower:
        return 'CACHE_OPERATION'
    elif 'prediction' in test_lower:
        return 'PREDICTION_LOGIC'
    elif 'match' in test_lower:
        return 'MATCH_MANAGEMENT'
    elif 'team' in test_lower:
        return 'TEAM_MANAGEMENT'
    elif 'user' in test_lower:
        return 'USER_MANAGEMENT'
    elif 'adapter' in test_lower:
        return 'ADAPTER_INTEGRATION'
    elif 'performance' in test_lower:
        return 'PERFORMANCE'
    elif 'error' in test_lower:
        return 'ERROR_HANDLING'
    else:
        return 'GENERAL'

def identify_error_pattern(test_method):
    """识别可能的错误模式"""
    test_lower = test_method.lower()
    if 'system_info' in test_lower or 'health' in test_lower:
        return 'HTTP_500_ERROR'
    elif 'basic_operations' in test_lower or 'set' in test_lower:
        return 'CACHE_ATTR_ERROR'
    elif 'password' in test_lower or 'hash' in test_lower:
        return 'AUTH_SERVICE_ERROR'
    elif 'list' in test_lower or 'get' in test_lower:
        return 'API_RESPONSE_ERROR'
    elif 'create' in test_lower or 'update' in test_lower:
        return 'DATA_VALIDATION_ERROR'
    elif 'integration' in test_lower:
        return 'INTEGRATION_ERROR'
    else:
        return 'UNKNOWN_ERROR'

def perform_clustering(failed_tests):
    """执行聚类分析"""
    # 按模块聚类
    module_clusters = defaultdict(list)
    for test in failed_tests:
        module_clusters[test['module']].append(test)

    # 按测试类型聚类
    test_type_clusters = defaultdict(list)
    for test in failed_tests:
        test_type_clusters[test['test_type']].append(test)

    # 按功能区域聚类
    functional_clusters = defaultdict(list)
    for test in failed_tests:
        functional_clusters[test['functional_area']].append(test)

    # 按错误模式聚类
    error_clusters = defaultdict(list)
    for test in failed_tests:
        error_clusters[test['error_pattern']].append(test)

    return {
        'module_clusters': dict(module_clusters),
        'test_type_clusters': dict(test_type_clusters),
        'functional_clusters': dict(functional_clusters),
        'error_clusters': dict(error_clusters)
    }

def calculate_impact(cluster, cluster_type):
    """计算集群影响分数"""
    base_score = len(cluster)

    # 根据集群类型调整权重
    weights = {
        'module': {
            'API': 10,
            'INTEGRATION': 8,
            'UNIT': 5,
            'OTHER': 3
        },
        'test_type': {
            'AUTH': 9,
            'CACHE': 8,
            'API': 8,
            'DATABASE': 7,
            'SERVICES': 7,
            'ML': 6,
            'CORE': 6,
            'GENERAL': 4
        },
        'functional': {
            'HEALTH_CHECK': 7,
            'AUTHENTICATION': 9,
            'CACHE_OPERATION': 8,
            'PREDICTION_LOGIC': 8,
            'API_RESPONSE_ERROR': 7,
            'INTEGRATION': 8,
            'PERFORMANCE': 5
        },
        'error': {
            'HTTP_500_ERROR': 10,
            'CACHE_ATTR_ERROR': 9,
            'AUTH_SERVICE_ERROR': 9,
            'INTEGRATION_ERROR': 8,
            'API_RESPONSE_ERROR': 7,
            'DATA_VALIDATION_ERROR': 6,
            'UNKNOWN_ERROR': 4
        }
    }

    # 根据集群名称获取权重
    weight = 5  # 默认权重
    if cluster_type in weights:
        for cluster_name, w in weights[cluster_type].items():
            if cluster_name in str(cluster[0] if cluster else ''):
                weight = w
                break

    return int(base_score * weight)

def generate_triage_report(failed_tests, clusters):
    """生成分诊报告"""
    total_failures = len(failed_tests)

    # 计算各种统计
    module_stats = {k: len(v) for k, v in clusters['module_clusters'].items()}
    test_type_stats = {k: len(v) for k, v in clusters['test_type_clusters'].items()}
    functional_stats = {k: len(v) for k, v in clusters['functional_clusters'].items()}
    error_stats = {k: len(v) for k, v in clusters['error_clusters'].items()}

    # 识别高价值集群
    high_value_clusters = []

    # 模块集群
    for module, tests in clusters['module_clusters'].items():
        impact = calculate_impact(tests, 'module')
        high_value_clusters.append({
            'type': 'MODULE',
            'name': module,
            'size': len(tests),
            'impact': impact,
            'examples': [t['full_path'] for t in tests[:3]]
        })

    # 错误模式集群
    for error_pattern, tests in clusters['error_clusters'].items():
        impact = calculate_impact(tests, 'error')
        high_value_clusters.append({
            'type': 'ERROR_PATTERN',
            'name': error_pattern,
            'size': len(tests),
            'impact': impact,
            'examples': [t['full_path'] for t in tests[:3]]
        })

    # 功能区域集群
    for functional_area, tests in clusters['functional_clusters'].items():
        impact = calculate_impact(tests, 'functional')
        high_value_clusters.append({
            'type': 'FUNCTIONAL_AREA',
            'name': functional_area,
            'size': len(tests),
            'impact': impact,
            'examples': [t['full_path'] for t in tests[:3]]
        })

    # 按影响分数排序
    high_value_clusters.sort(key=lambda x: x['impact'], reverse=True)

    # 生成报告内容
    report = f"""# P8.1 Failed Tests Triage Report

## 📊 执行摘要

- **总失败测试数**: {total_failures}
- **分析时间**: 2025-11-14 11:15:00
- **分析范围**: 完整测试套件

## 🎯 关键统计数据

### 按模块分布
"""

    for module, count in sorted(module_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_failures) * 100
        report += f"- **{module}**: {count} 个测试 ({percentage:.1f}%)\n"

    report += "\n### 按测试类型分布\n"

    for test_type, count in sorted(test_type_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_failures) * 100
        report += f"- **{test_type}**: {count} 个测试 ({percentage:.1f}%)\n"

    report += "\n### 按功能区域分布\n"

    for functional_area, count in sorted(functional_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_failures) * 100
        report += f"- **{functional_area}**: {count} 个测试 ({percentage:.1f}%)\n"

    report += "\n### 按错误模式分布\n"

    for error_pattern, count in sorted(error_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_failures) * 100
        report += f"- **{error_pattern}**: {count} 个测试 ({percentage:.1f}%)\n"

    report += "\n## 🔥 高价值集群分析\n\n"

    # 优先级1: 影响分数 > 1000
    priority_1 = [c for c in high_value_clusters if c['impact'] > 1000]
    if priority_1:
        report += "### 优先级1: 立即修复 (影响 > 1000)\n\n"
        for i, cluster in enumerate(priority_1[:5], 1):
            report += f"""#### {i}. {cluster['name']} ({cluster['type']})
- **影响分数**: {cluster['impact']}
- **涉及测试**: {cluster['size']} 个
- **修复建议**: {get_fix_suggestion(cluster)}
- **示例测试**:
"""
            for example in cluster['examples']:
                report += f"  - `{example}`\n"
            report += "\n"

    # 优先级2: 影响分数 500-1000
    priority_2 = [c for c in high_value_clusters if 500 <= c['impact'] <= 1000]
    if priority_2:
        report += "### 优先级2: 高优先级 (影响 500-1000)\n\n"
        for i, cluster in enumerate(priority_2[:5], 1):
            report += f"""#### {i}. {cluster['name']} ({cluster['type']})
- **影响分数**: {cluster['impact']}
- **涉及测试**: {cluster['size']} 个
- **修复建议**: {get_fix_suggestion(cluster)}
"""

    report += f"""
## 🛠️ P8.2 修复策略建议

### 立即行动计划
1. **API系统修复** - 重点关注HTTP 500错误和端点响应问题
2. **缓存系统修复** - 解决AttributeError和异步装饰器问题
3. **认证系统修复** - 修复bcrypt和密码哈希依赖问题
4. **集成测试修复** - 解决模块间依赖和服务注入问题

### 渐进式修复方法
1. **阶段1**: 修复基础设施问题（依赖注入、装饰器、配置）
2. **阶段2**: 修复核心业务逻辑（API端点、认证、缓存）
3. **阶段3**: 优化集成测试和性能测试

### 质量保证措施
- 使用 `make solve-test-crisis` 自动修复常见问题
- 运行 `python3 scripts/smart_quality_fixer.py` 智能质量修复
- 执行 `make test.smart` 验证修复效果

## 📈 成功指标

- **目标**: 将失败测试数量从{total_failures}降至100以下
- **关键指标**:
  - API端点通过率 > 90%
  - 缓存系统测试通过率 > 85%
  - 认证系统测试通过率 > 90%
  - 集成测试通过率 > 80%

---
*报告生成时间: 2025-11-14 11:15:00*
*分析工具: P8.1 Simple Triage Analyzer*
"""

    return report

def get_fix_suggestion(cluster):
    """获取修复建议"""
    suggestions = {
        'HTTP_500_ERROR': '检查API端点实现，修复服务器内部错误',
        'CACHE_ATTR_ERROR': '解决异步装饰器问题，修复缓存管理器',
        'AUTH_SERVICE_ERROR': '修复认证服务依赖，检查密码哈希库',
        'API_RESPONSE_ERROR': '验证API响应格式，修复序列化问题',
        'INTEGRATION_ERROR': '解决模块间依赖，修复服务注入',
        'HEALTH_CHECK': '修复健康检查端点和系统监控',
        'AUTHENTICATION': '检查JWT令牌和用户认证逻辑',
        'CACHE_OPERATION': '解决缓存操作和Redis集成',
        'PREDICTION_LOGIC': '修复预测服务和数据模型',
        'API': '重点修复FastAPI路由和依赖注入',
        'INTEGRATION': '解决跨模块集成问题',
        'AUTH': '解决密码哈希和认证流程',
        'UNIT': '修复单元测试的模拟和依赖'
    }

    for key, suggestion in suggestions.items():
        if key.lower() in cluster['name'].lower():
            return suggestion

    return '需要详细分析具体错误原因'

def main():
    """主函数"""
    print("🚀 启动P8.1简化聚类分析...")

    # 解析失败测试
    failed_tests = parse_failed_tests()
    print(f"✅ 解析完成: 找到 {len(failed_tests)} 个失败测试")

    # 执行聚类分析
    clusters = perform_clustering(failed_tests)
    print("🔄 聚类分析完成")

    # 生成报告
    report = generate_triage_report(failed_tests, clusters)

    # 保存报告
    with open('P8.1_Triage_Report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print("✅ 报告已保存到: P8.1_Triage_Report.md")

    # 显示摘要
    print("\n📋 分析摘要:")
    print(f"- 总失败测试: {len(failed_tests)}")
    print(f"- 模块集群: {len(clusters['module_clusters'])}")
    print(f"- 测试类型集群: {len(clusters['test_type_clusters'])}")
    print(f"- 功能区域集群: {len(clusters['functional_clusters'])}")
    print(f"- 错误模式集群: {len(clusters['error_clusters'])}")

if __name__ == "__main__":
    main()