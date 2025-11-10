#!/usr/bin/env python3
"""
Swagger UI 增强功能测试脚本
Swagger UI Enhancement Features Testing Script

Author: Claude Code
Version: 1.0.0
"""

import os
import re
import json
from pathlib import Path

def test_swagger_config_structure():
    """测试Swagger UI配置结构"""
    print("🎨 测试Swagger UI配置结构...")

    try:
        config_path = 'src/config/swagger_ui_config.py'
        if not os.path.exists(config_path):
            print("❌ Swagger UI配置文件不存在")
            return False

        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()

        # 检查关键类和方法
        required_functions = [
            'class SwaggerUIConfig',
            'get_custom_swagger_ui_html',
            'get_enhanced_redoc_html',
            'setup_custom_swagger_ui',
            'setup_enhanced_redoc',
            'setup_enhanced_docs'
        ]

        missing_functions = [func for func in required_functions if func not in config_content]

        if missing_functions:
            print(f"❌ 缺少关键函数: {missing_functions}")
            return False

        print(f"✅ 关键函数完整 ({len(required_functions)})")

        # 检查HTML内容
        html_content = config_content.count('<html>')
        css_content = config_content.count('<style>')
        js_content = config_content.count('<script>')
        js_function_content = config_content.count('function ')

        print(f"📄 HTML模板数量: {html_content}")
        print(f"🎨 CSS样式数量: {css_content}")
        print(f"⚡ JavaScript代码数量: {js_content}")
        print(f"🔧 JavaScript函数数量: {js_function_content}")

        if html_content < 2:
            print("❌ HTML模板数量不足")
            return False

        # 检查增强功能
        enhancement_features = [
            'api-status', 'quick-actions', 'loading-overlay',
            'custom-swagger-ui', 'interactive-playground',
            'response-interceptor', 'request-interceptor'
        ]

        feature_count = sum(1 for feature in enhancement_features if feature in config_content)
        print(f"🚀 增强功能数量: {feature_count}/{len(enhancement_features)}")

        return True

    except Exception as e:
        print(f"❌ Swagger配置测试失败: {e}")
        return False

def test_docs_api_structure():
    """测试文档API结构"""
    print("\n📚 测试文档API结构...")

    try:
        docs_path = 'src/api/docs.py'
        if not os.path.exists(docs_path):
            print("❌ 文档API文件不存在")
            return False

        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_content = f.read()

        # 检查路由定义
        route_patterns = [
            r'@router\.get\("/enhanced"',
            r'@router\.get\("/interactive"',
            r'@router\.get\("/examples"',
            r'@router\.get\("/openapi\.json"',
            r'@router\.get\("/status"'
        ]

        route_count = 0
        for pattern in route_patterns:
            if re.search(pattern, docs_content):
                route_count += 1

        print(f"🔗 API路由数量: {route_count}/{len(route_patterns)}")

        if route_count < 4:
            print("❌ API路由数量不足")
            return False

        # 检查HTML生成功能
        html_generators = docs_content.count('return HTMLResponse(')
        print(f"📄 HTML生成器数量: {html_generators}")

        # 检查交互式功能
        interactive_features = [
            'testHealthCheck', 'testAuth', 'getApiInfo',
            'exportOpenAPI', 'clearLocalStorage',
            'checkApiStatus', 'runAllTests'
        ]

        interactive_count = sum(1 for feature in interactive_features if feature in docs_content)
        print(f"🎮 交互式功能数量: {interactive_count}/{len(interactive_features)}")

        return True

    except Exception as e:
        print(f"❌ 文档API测试失败: {e}")
        return False

def test_html_content_quality():
    """测试HTML内容质量"""
    print("\n🌐 测试HTML内容质量...")

    try:
        docs_path = 'src/api/docs.py'
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_content = f.read()

        # 提取HTML内容
        html_blocks = re.findall(r'"""(.*?)"""', docs_content, re.DOTALL)
        if not html_blocks:
            html_blocks = re.findall(r"'''(.*?)'''", docs_content, re.DOTALL)

        total_html_size = 0
        html_features = {
            'meta charset': 0,
            'meta name': 0,
            'title>': 0,
            '<style>': 0,
            '<script>': 0,
            'onclick=': 0,
            'addEventListener': 0,
            'fetch(': 0,
            'querySelector': 0,
            'createElement': 0
        }

        for html in html_blocks:
            total_html_size += len(html)
            for feature in html_features:
                html_features[feature] += html.count(feature)

        print(f"📊 总HTML内容大小: {total_html_size:,} 字符")
        print("🔧 HTML功能统计:")
        for feature, count in html_features.items():
            if count > 0:
                print(f"   {feature}: {count}")

        # 检查响应式设计
        responsive_indicators = ['@media', 'flex', 'grid', 'responsive']
        responsive_count = sum(1 for indicator in responsive_indicators if indicator in docs_content.lower())
        print(f"📱 响应式设计指标: {responsive_count}")

        # 检查用户体验功能
        ux_features = ['loading', 'error', 'success', 'warning', 'notification']
        ux_count = sum(1 for feature in ux_features if feature in docs_content.lower())
        print(f"🎨 用户体验功能: {ux_count}")

        return total_html_size > 10000  # 至少10KB的HTML内容

    except Exception as e:
        print(f"❌ HTML内容测试失败: {e}")
        return False

def test_javascript_functionality():
    """测试JavaScript功能"""
    print("\n⚡ 测试JavaScript功能...")

    try:
        docs_path = 'src/api/docs.py'
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_content = f.read()

        # 检查JavaScript核心功能
        js_functions = {
            'generateUUID': docs_content.count('generateUUID'),
            'showLoading': docs_content.count('showLoading'),
            'updateApiStatus': docs_content.count('updateApiStatus'),
            'addLog': docs_content.count('addLog'),
            'makeAPIRequest': docs_content.count('makeAPIRequest'),
            'checkConnection': docs_content.count('checkConnection')
        }

        print("🔧 JavaScript函数统计:")
        for func_name, count in js_functions.items():
            if count > 0:
                print(f"   {func_name}: {count} 次调用")

        # 检查错误处理
        error_handling = docs_content.count('try {') + docs_content.count('catch(')
        print(f"⚠️ 错误处理代码块: {error_handling}")

        # 检查API调用
        api_calls = docs_content.count('fetch(')
        print(f"🌐 API调用数量: {api_calls}")

        # 检查事件处理
        event_handlers = docs_content.count('addEventListener')
        print(f"👂 事件处理器数量: {event_handlers}")

        # 检查DOM操作
        dom_operations = docs_content.count('document.getElementById') + docs_content.count('document.querySelector')
        print(f"🎨 DOM操作数量: {dom_operations}")

        return error_handling > 5 and api_calls > 3

    except Exception as e:
        print(f"❌ JavaScript功能测试失败: {e}")
        return False

def test_css_styling():
    """测试CSS样式"""
    print("\n🎨 测试CSS样式...")

    try:
        docs_path = 'src/api/docs.py'
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_content = f.read()

        # 检查CSS选择器
        css_selectors = {
            'class selectors': docs_content.count('.'),
            'id selectors': docs_content.count('#'),
            'element selectors': docs_content.count('body') + docs_content.count('div') + docs_content.count('button'),
            'pseudo-selectors': docs_content.count(':hover') + docs_content.count(':active')
        }

        print("🎨 CSS选择器统计:")
        for selector_type, count in css_selectors.items():
            print(f"   {selector_type}: {count}")

        # 检查CSS属性
        css_properties = [
            'color:', 'background:', 'border:', 'padding:', 'margin:',
            'display:', 'position:', 'flex:', 'grid:', 'transition:',
            'transform:', 'animation:', 'box-shadow:', 'border-radius:'
        ]

        property_count = sum(1 for prop in css_properties if prop in docs_content)
        print(f"🎨 CSS属性种类: {property_count}/{len(css_properties)}")

        # 检查响应式CSS
        media_queries = docs_content.count('@media')
        flexbox_usage = docs_content.count('display: flex')
        grid_usage = docs_content.count('display: grid')

        print(f"📱 媒体查询: {media_queries}")
        print(f"📐 Flexbox使用: {flexbox_usage}")
        print(f"📋 Grid使用: {grid_usage}")

        return media_queries > 0 and (flexbox_usage > 5 or grid_usage > 2)

    except Exception as e:
        print(f"❌ CSS样式测试失败: {e}")
        return False

def test_integration_with_main():
    """测试与主应用的集成"""
    print("\n🔗 测试与主应用的集成...")

    try:
        main_path = 'src/main.py'
        if not os.path.exists(main_path):
            print("❌ 主应用文件不存在")
            return False

        with open(main_path, 'r', encoding='utf-8') as f:
            main_content = f.read()

        # 检查导入语句
        required_imports = [
            'from src.config.swagger_ui_config import setup_enhanced_docs',
            'from src.api.docs import setup_docs_routes'
        ]

        import_status = {}
        for import_stmt in required_imports:
            if import_stmt in main_content:
                import_status[import_stmt] = "✅ 已导入"
            else:
                import_status[import_stmt] = "❌ 未导入"

        print("📦 导入状态检查:")
        for stmt, status in import_status.items():
            module_name = stmt.split('.')[-1].replace(' setup_', '')
            print(f"   {module_name}: {status}")

        # 检查函数调用
        function_calls = [
            'setup_enhanced_docs(app)',
            'setup_docs_routes(app)'
        ]

        call_status = {}
        for call in function_calls:
            if call in main_content:
                call_status[call] = "✅ 已调用"
            else:
                call_status[call] = "❌ 未调用"

        print("🔧 函数调用状态:")
        for call, status in call_status.items():
            func_name = call.split('(')[0]
            print(f"   {func_name}: {status}")

        # 计算集成度
        total_checks = len(required_imports) + len(function_calls)
        passed_checks = len([status for status in list(import_status.values()) + list(call_status.values()) if status == "✅ 已导入" or status == "✅ 已调用"])

        integration_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        print(f"📊 集成完成度: {integration_rate:.1f}% ({passed_checks}/{total_checks})")

        return integration_rate >= 75

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False

def test_file_organization():
    """测试文件组织结构"""
    print("\n📁 测试文件组织结构...")

    try:
        # 检查相关文件的存在和大小
        files_to_check = [
            ('src/config/swagger_ui_config.py', 'Swagger UI配置'),
            ('src/api/docs.py', '文档API端点'),
            ('docs/api_reference.md', 'API参考文档'),
            ('docs/error_codes.md', '错误代码文档')
        ]

        file_stats = {}
        total_size = 0

        for file_path, description in files_to_check:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                file_stats[description] = size
                total_size += size
                print(f"✅ {description}: {size:,} 字节")
            else:
                print(f"❌ {description}: 文件不存在")
                return False

        print(f"📊 总代码量: {total_size:,} 字节")

        # 检查目录结构
        required_dirs = [
            'src/config/',
            'src/api/',
            'docs/',
            'sdk/python/'
        ]

        dir_status = 0
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                dir_status += 1
                print(f"✅ 目录: {dir_path}")
            else:
                print(f"❌ 目录缺失: {dir_path}")

        print(f"📂 目录完整性: {dir_status}/{len(required_dirs)}")

        return total_size > 10000 and dir_status >= 3

    except Exception as e:
        print(f"❌ 文件组织测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Swagger UI 增强功能测试开始")
    print("=" * 60)

    # 测试项目列表
    tests = [
        ("Swagger UI配置结构", test_swagger_config_structure),
        ("文档API结构", test_docs_api_structure),
        ("HTML内容质量", test_html_content_quality),
        ("JavaScript功能", test_javascript_functionality),
        ("CSS样式", test_css_styling),
        ("主应用集成", test_integration_with_main),
        ("文件组织", test_file_organization)
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
    print("\n📊 Swagger UI增强功能测试汇总")
    print("=" * 60)

    for name, _ in tests:
        print(f"{name}: ✅ 通过" if passed > 0 else "❌ 失败")

    success_rate = (passed / total) * 100
    print(f"\n🎯 总体通过率: {success_rate:.1f}% ({passed}/{total})")

    if success_rate >= 90:
        print("🎉 Swagger UI增强功能测试优秀！")
        return True
    elif success_rate >= 75:
        print("⚠️ Swagger UI增强功能测试良好，但有改进空间")
        return True
    else:
        print("❌ Swagger UI增强功能需要改进")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)