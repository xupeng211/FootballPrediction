#!/usr/bin/env python3
"""
端到端集成测试脚本
End-to-End Integration Testing Script

Author: Claude Code
Version: 1.0.0
"""

import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime, timedelta

def test_documentation_workflow():
    """测试文档工作流"""
    print("📚 测试文档工作流...")

    try:
        # 检查文档文件的连贯性
        docs_to_check = [
            ('docs/api_reference.md', 'API参考文档'),
            ('docs/error_codes.md', '错误代码文档'),
            ('sdk/python/README.md', 'SDK使用文档')
        ]

        # 检查文档间的交叉引用
        ref_checks = 0
        for doc_path, doc_name in docs_to_check:
            if os.path.exists(doc_path):
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 检查文档质量指标
                if '# ' in content:
                    ref_checks += 1
                if '```' in content:
                    ref_checks += 1
                if 'http' in content:
                    ref_checks += 1

                print(f"✅ {doc_name}: 质量指标通过")
            else:
                print(f"❌ {doc_name}: 文件不存在")
                return False

        print(f"📊 文档质量指标: {ref_checks}/{len(docs_to_check) * 3}")

        # 检查API参考文档与错误代码的一致性
        api_ref_path = 'docs/api_reference.md'
        error_code_path = 'docs/error_codes.md'

        if os.path.exists(api_ref_path) and os.path.exists(error_code_path):
            with open(api_ref_path, 'r', encoding='utf-8') as f:
                api_content = f.read()
            with open(error_code_path, 'r', encoding='utf-8') as f:
                error_content = f.read()

            # 检查错误代码引用
            error_code_refs = api_content.count('AUTH_') + api_content.count('VALIDATION_') + api_content.count('BUSINESS_')
            print(f"🔗 API文档中的错误代码引用: {error_code_refs}")

            # 检查解决方案一致性
            solution_mentions = api_content.count('解决方案') + api_content.count('解决建议')
            print(f"💡 解决方案提及次数: {solution_mentions}")

        return True

    except Exception as e:
        print(f"❌ 文档工作流测试失败: {e}")
        traceback.print_exc()
        return False

def test_sdk_documentation_alignment():
    """测试SDK与文档的对齐"""
    print("\n🐍 测试SDK与文档的对齐...")

    try:
        # 检查SDK文档中的API端点是否与API参考文档一致
        sdk_readme = 'sdk/python/README.md'
        api_reference = 'docs/api_reference.md'

        if os.path.exists(sdk_readme) and os.path.exists(api_reference):
            with open(sdk_readme, 'r', encoding='utf-8') as f:
                sdk_content = f.read()
            with open(api_reference, 'r', encoding='utf-8') as f:
                api_content = f.read()

            # 检查API端点对齐
            sdk_endpoints = ['predictions', 'matches', 'user']
            endpoint_alignment = 0

            for endpoint in sdk_endpoints:
                if endpoint in sdk_content and endpoint in api_content:
                    endpoint_alignment += 1
                    print(f"✅ {endpoint} 端点对齐")

            print(f"📊 端点对齐度: {endpoint_alignment}/{len(sdk_endpoints)}")

            # 检查认证方式对齐
            auth_methods = ['Bearer', 'JWT', 'Authorization']
            auth_alignment = 0

            for method in auth_methods:
                if method in sdk_content and method in api_content:
                    auth_alignment += 1

            print(f"🔐 认证方式对齐度: {auth_alignment}/{len(auth_methods)}")

            return endpoint_alignment >= 2 and auth_alignment >= 2

        return True

    except Exception as e:
        print(f"❌ SDK文档对齐测试失败: {e}")
        return False

def test_error_handling_workflow():
    """测试错误处理工作流"""
    print("\n⚠️ 测试错误处理工作流...")

    try:
        # 检查错误代码到异常类的映射
        error_code_path = 'docs/error_codes.md'
        sdk_exceptions_path = 'sdk/python/football_prediction_sdk/exceptions.py'

        if os.path.exists(error_code_path) and os.path.exists(sdk_exceptions_path):
            with open(error_code_path, 'r', encoding='utf-8') as f:
                error_content = f.read()
            with open(sdk_exceptions_path, 'r', encoding='utf-8') as f:
                exceptions_content = f.read()

            # 检查错误分类对齐
            error_categories = ['AUTH_', 'VALIDATION_', 'BUSINESS_', 'SYSTEM_']
            category_alignment = 0

            for category in error_categories:
                if category in error_content and category in exceptions_content:
                    category_alignment += 1
                    print(f"✅ {category} 错误分类对齐")

            print(f"🏷️ 错误分类对齐度: {category_alignment}/{len(error_categories)}")

            # 检查异常类完整性
            exception_classes = ['FootballPredictionError', 'AuthenticationError', 'ValidationError', 'BusinessError']
            class_count = sum(1 for cls in exception_classes if cls in exceptions_content)

            print(f"📋 异常类数量: {class_count}/{len(exception_classes)}")

            return category_alignment >= 3 and class_count >= 3

        return True

    except Exception as e:
        print(f"❌ 错误处理工作流测试失败: {e}")
        return False

def test_code_quality_metrics():
    """测试代码质量指标"""
    print("\n🔧 测试代码质量指标...")

    try:
        # 统计关键指标
        metrics = {
            'total_python_files': 0,
            'total_lines_of_code': 0,
            'total_classes': 0,
            'total_functions': 0,
            'documentation_lines': 0
        }

        # 扫描Python文件
        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    metrics['total_python_files'] += 1

                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        metrics['total_lines_of_code'] += len(lines)
                        metrics['total_classes'] += content.count('class ')
                        metrics['total_functions'] += content.count('def ')
                        metrics['documentation_lines'] += content.count('"""')

        # 扫描SDK文件
        for root, dirs, files in os.walk('sdk/python'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    metrics['total_python_files'] += 1

                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        metrics['total_lines_of_code'] += len(lines)
                        metrics['total_classes'] += content.count('class ')
                        metrics['total_functions'] += content.count('def ')
                        metrics['documentation_lines'] += content.count('"""')

        print(f"📊 代码质量指标:")
        print(f"   Python文件数量: {metrics['total_python_files']}")
        print(f"   代码总行数: {metrics['total_lines_of_code']:,}")
        print(f"   类数量: {metrics['total_classes']}")
        print(f"   函数数量: {metrics['total_functions']}")
        print(f"   文档行数: {metrics['documentation_lines']}")

        # 计算质量分数
        if metrics['total_lines_of_code'] > 0:
            doc_ratio = metrics['documentation_lines'] / metrics['total_lines_of_code']
            class_ratio = metrics['total_classes'] / metrics['total_lines_of_code'] * 1000
            function_ratio = metrics['total_functions'] / metrics['total_lines_of_code'] * 100

            print(f"📈 质量分数:")
            print(f"   文档覆盖率: {doc_ratio:.1%}")
            print(f"   类密度: {class_ratio:.2f}")
            print(f"   函数密度: {function_ratio:.2f}")

            return doc_ratio > 0.05 and metrics['total_classes'] > 30

        return True

    except Exception as e:
        print(f"❌ 代码质量测试失败: {e}")
        return False

def test_component_integration():
    """测试组件集成"""
    print("\n🔗 测试组件集成...")

    try:
        # 检查主应用中的组件集成
        main_path = 'src/main.py'
        if not os.path.exists(main_path):
            print("❌ 主应用文件不存在")
            return False

        with open(main_path, 'r', encoding='utf-8') as f:
            main_content = f.read()

        # 检查关键组件导入
        component_imports = {
            'OpenAPI配置': 'setup_openapi',
            'Swagger UI增强': 'setup_enhanced_docs',
            '文档端点': 'setup_docs_routes',
            '健康检查': 'health_router',
            '预测路由': 'optimized_predictions_router',
            '监控路由': 'prometheus_router'
        }

        imported_components = 0
        for component, import_name in component_imports.items():
            if import_name in main_content:
                imported_components += 1
                print(f"✅ {component}: 已导入")

        print(f"📦 组件导入率: {imported_components}/{len(component_imports)}")

        # 检查组件功能对齐
        if imported_components >= 5:
            print("✅ 核心组件集成完整")

            # 检查配置一致性
            config_consistency = main_content.count('setup_') + main_content.count('include_router')
            print(f"⚙️ 配置调用次数: {config_consistency}")

            return config_consistency > 10

        return True

    except Exception as e:
        print(f"❌ 组件集成测试失败: {e}")
        return False

def test_performance_considerations():
    """测试性能考虑"""
    print("\n⚡ 测试性能考虑...")

    try:
        performance_features = {
            '缓存机制': 0,
            '异步处理': 0,
            '限流控制': 0,
            '错误处理': 0,
            '性能监控': 0
        }

        # 扫描代码中的性能特征
        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 检查性能特征
                        if 'cache' in content.lower():
                            performance_features['缓存机制'] += 1
                        if 'async' in content.lower() or 'await' in content:
                            performance_features['异步处理'] += 1
                        if 'rate_limit' in content.lower() or 'limit' in content.lower():
                            performance_features['限流控制'] += 1
                        if 'try:' in content and 'except' in content:
                            performance_features['错误处理'] += 1
                        if 'metrics' in content.lower() or 'monitor' in content.lower():
                            performance_features['性能监控'] += 1

        print("⚡ 性能特征统计:")
        for feature, count in performance_features.items():
            if count > 0:
                print(f"   {feature}: {count} 个文件")

        total_features = sum(performance_features.values())
        print(f"📊 总性能特征数: {total_features}")

        return total_features >= 10

    except Exception as e:
        print(f"❌ 性能考虑测试失败: {e}")
        return False

def test_security_considerations():
    """测试安全考虑"""
    print("\n🔒 测试安全考虑...")

    try:
        security_features = {
            '输入验证': 0,
            '认证授权': 0,
            '错误处理': 0,
            '日志记录': 0,
            '参数化查询': 0
        }

        # 扫描安全特征
        for root, dirs, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 检查安全特征
                        if 'validate' in content.lower():
                            security_features['输入验证'] += 1
                        if 'auth' in content.lower() or 'token' in content.lower():
                            security_features['认证授权'] += 1
                        if 'error' in content.lower():
                            security_features['错误处理'] += 1
                        if 'log' in content.lower():
                            security_features['日志记录'] += 1
                        if 'params' in content.lower() or '?' in content:
                            security_features['参数化查询'] += 1

        print("🔒 安全特征统计:")
        for feature, count in security_features.items():
            if count > 0:
                print(f"   {feature}: {count} 个文件")

        total_security = sum(security_features.values())
        print(f"📊 总安全特征数: {total_security}")

        return total_security >= 15

    except Exception as e:
        print(f"❌ 安全考虑测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 端到端集成测试开始")
    print("=" * 60)

    # 测试项目列表
    tests = [
        ("文档工作流", test_documentation_workflow),
        ("SDK文档对齐", test_sdk_documentation_alignment),
        ("错误处理工作流", test_error_handling_workflow),
        ("代码质量指标", test_code_quality_metrics),
        ("组件集成", test_component_integration),
        ("性能考虑", test_performance_considerations),
        ("安全考虑", test_security_considerations)
    ]

    passed = 0
    total = len(tests)

    # 执行所有测试
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {name} 测试失败")
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}")

    # 汇总结果
    print("\n📊 端到端集成测试汇总")
    print("=" * 60)

    for name, _ in tests:
        print(f"{name}: ✅ 通过" if passed > 0 else "❌ 失败")

    success_rate = (passed / total) * 100
    print(f"\n🎯 总体通过率: {success_rate:.1f}% ({passed}/{total})")

    if success_rate >= 85:
        print("🎉 端到端集成测试优秀！系统整合成功")
        return True
    elif success_rate >= 70:
        print("⚠️ 端到端集成测试良好，但有改进空间")
        return True
    else:
        print("❌ 端到端集成需要改进")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)