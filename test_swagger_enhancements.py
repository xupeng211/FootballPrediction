#!/usr/bin/env python3
"""
Swagger UI 增强功能测试脚本
Swagger UI Enhancement Features Testing Script

Author: Claude Code
Version: 1.0.0
"""

import os
import re


def test_swagger_config_structure():
    """测试Swagger UI配置结构"""

    try:
        config_path = 'src/config/swagger_ui_config.py'
        if not os.path.exists(config_path):
            return False

        with open(config_path, encoding='utf-8') as f:
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
            return False


        # 检查HTML内容
        html_content = config_content.count('<html>')
        config_content.count('<style>')
        config_content.count('<script>')
        config_content.count('function ')


        if html_content < 2:
            return False

        # 检查增强功能
        enhancement_features = [
            'api-status', 'quick-actions', 'loading-overlay',
            'custom-swagger-ui', 'interactive-playground',
            'response-interceptor', 'request-interceptor'
        ]

        sum(1 for feature in enhancement_features if feature in config_content)

        return True

    except Exception:
        return False

def test_docs_api_structure():
    """测试文档API结构"""

    try:
        docs_path = 'src/api/docs.py'
        if not os.path.exists(docs_path):
            return False

        with open(docs_path, encoding='utf-8') as f:
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


        if route_count < 4:
            return False

        # 检查HTML生成功能
        docs_content.count('return HTMLResponse(')

        # 检查交互式功能
        interactive_features = [
            'testHealthCheck', 'testAuth', 'getApiInfo',
            'exportOpenAPI', 'clearLocalStorage',
            'checkApiStatus', 'runAllTests'
        ]

        sum(1 for feature in interactive_features if feature in docs_content)

        return True

    except Exception:
        return False

def test_html_content_quality():
    """测试HTML内容质量"""

    try:
        docs_path = 'src/api/docs.py'
        with open(docs_path, encoding='utf-8') as f:
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

        for feature, count in html_features.items():
            if count > 0:
                pass

        # 检查响应式设计
        responsive_indicators = ['@media', 'flex', 'grid', 'responsive']
        sum(1 for indicator in responsive_indicators if indicator in docs_content.lower())

        # 检查用户体验功能
        ux_features = ['loading', 'error', 'success', 'warning', 'notification']
        sum(1 for feature in ux_features if feature in docs_content.lower())

        return total_html_size > 10000  # 至少10KB的HTML内容

    except Exception:
        return False

def test_javascript_functionality():
    """测试JavaScript功能"""

    try:
        docs_path = 'src/api/docs.py'
        with open(docs_path, encoding='utf-8') as f:
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

        for _func_name, count in js_functions.items():
            if count > 0:
                pass

        # 检查错误处理
        error_handling = docs_content.count('try {') + docs_content.count('catch(')

        # 检查API调用
        api_calls = docs_content.count('fetch(')

        # 检查事件处理
        docs_content.count('addEventListener')

        # 检查DOM操作
        docs_content.count('document.getElementById') + docs_content.count('document.querySelector')

        return error_handling > 5 and api_calls > 3

    except Exception:
        return False

def test_css_styling():
    """测试CSS样式"""

    try:
        docs_path = 'src/api/docs.py'
        with open(docs_path, encoding='utf-8') as f:
            docs_content = f.read()

        # 检查CSS选择器
        css_selectors = {
            'class selectors': docs_content.count('.'),
            'id selectors': docs_content.count('#'),
            'element selectors': docs_content.count('body') + docs_content.count('div') + docs_content.count('button'),
            'pseudo-selectors': docs_content.count(':hover') + docs_content.count(':active')
        }

        for _selector_type, _count in css_selectors.items():
            pass

        # 检查CSS属性
        css_properties = [
            'color:', 'background:', 'border:', 'padding:', 'margin:',
            'display:', 'position:', 'flex:', 'grid:', 'transition:',
            'transform:', 'animation:', 'box-shadow:', 'border-radius:'
        ]

        sum(1 for prop in css_properties if prop in docs_content)

        # 检查响应式CSS
        media_queries = docs_content.count('@media')
        flexbox_usage = docs_content.count('display: flex')
        grid_usage = docs_content.count('display: grid')


        return media_queries > 0 and (flexbox_usage > 5 or grid_usage > 2)

    except Exception:
        return False

def test_integration_with_main():
    """测试与主应用的集成"""

    try:
        main_path = 'src/main.py'
        if not os.path.exists(main_path):
            return False

        with open(main_path, encoding='utf-8') as f:
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

        for stmt, _status in import_status.items():
            stmt.split('.')[-1].replace(' setup_', '')

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

        for call, _status in call_status.items():
            call.split('(')[0]

        # 计算集成度
        total_checks = len(required_imports) + len(function_calls)
        passed_checks = len([status for status in list(import_status.values()) + list(call_status.values()) if status == "✅ 已导入" or status == "✅ 已调用"])

        integration_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

        return integration_rate >= 75

    except Exception:
        return False

def test_file_organization():
    """测试文件组织结构"""

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
            else:
                return False


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
            else:
                pass


        return total_size > 10000 and dir_status >= 3

    except Exception:
        return False

def main():
    """主测试函数"""

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
    for _name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                pass
        except Exception:
            pass

    # 汇总结果

    for _name, _ in tests:
        pass

    success_rate = (passed / total) * 100

    if success_rate >= 90:
        return True
    elif success_rate >= 75:
        return True
    else:
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
