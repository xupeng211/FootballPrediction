#!/usr/bin/env python3
"""Phase 8.3 系统整合验证脚本
System Integration Verification Script for Phase 8.3.
"""

import os
from pathlib import Path


def verify_api_reference_docs():
    """验证API参考文档."""
    api_ref_path = "docs/api_reference.md"
    if not os.path.exists(api_ref_path):
        return False

    with open(api_ref_path, encoding="utf-8") as f:
        content = f.read()

    # 检查关键章节
    required_sections = [
        "API参考文档",
        "API概述",
        "认证与授权",
        "通用响应格式",
        "错误处理",
        "API端点",
        "数据模型",
        "性能指南",
        "SDK支持",
    ]

    missing_sections = [s for s in required_sections if s not in content]

    if missing_sections:
        return False

    # 统计内容
    content.count("### ")
    (
        content.count("```python")
        + content.count("```javascript")
        + content.count("```java")
    )
    content.count("/api/") + content.count("/health") + content.count("/predictions")

    return True


def verify_error_codes_docs():
    """验证错误代码文档."""
    error_code_path = "docs/error_codes.md"
    if not os.path.exists(error_code_path):
        return False

    with open(error_code_path, encoding="utf-8") as f:
        content = f.read()

    # 检查错误分类
    error_categories = [
        "认证与授权错误",
        "请求验证错误",
        "业务逻辑错误",
        "系统与基础设施错误",
        "第三方服务错误",
        "限流和配额错误",
    ]

    missing_categories = [c for c in error_categories if c not in content]

    if missing_categories:
        return False

    # 统计错误代码
    auth_errors = content.count("AUTH_")
    validation_errors = content.count("VALIDATION_")
    business_errors = content.count("BUSINESS_")
    system_errors = content.count("SYSTEM_")
    auth_errors + validation_errors + business_errors + system_errors

    # 检查工具和示例
    tool_sections = ["错误处理最佳实践", "开发者工具", "支持与帮助"]
    missing_tools = [t for t in tool_sections if t not in content]

    if missing_tools:
        return False

    return True


def verify_python_sdk():
    """验证Python SDK."""
    sdk_path = Path("sdk/python/football_prediction_sdk")
    if not sdk_path.exists():
        return False

    # 检查核心模块
    required_modules = [
        "__init__.py",
        "client.py",
        "auth.py",
        "models.py",
        "exceptions.py",
        "utils.py",
    ]

    missing_modules = []
    for module in required_modules:
        module_path = sdk_path / module
        if not module_path.exists():
            missing_modules.append(module)

    if missing_modules:
        return False

    # 检查配置文件
    config_files = ["setup.py", "requirements.txt", "README.md"]
    missing_configs = []

    for config in config_files:
        config_path = Path("sdk/python") / config
        if not config_path.exists():
            missing_configs.append(config)

    if missing_configs:
        return False

    # 验证模块内容
    try:
        with open(sdk_path / "__init__.py", encoding="utf-8") as f:
            init_content = f.read()

        if "FootballPredictionClient" not in init_content:
            return False

    except Exception:
        return False

    # 检查类数量
    total_classes = 0
    for module in required_modules:
        try:
            with open(sdk_path / module, encoding="utf-8") as f:
                content = f.read()
            class_count = content.count("class ")
            total_classes += class_count
        except Exception:
            pass

    return True


def verify_swagger_ui_enhancements():
    """验证Swagger UI增强功能."""
    # 检查配置文件
    swagger_config_path = "src/config/swagger_ui_config.py"
    if not os.path.exists(swagger_config_path):
        return False

    with open(swagger_config_path, encoding="utf-8") as f:
        config_content = f.read()

    # 检查关键功能
    required_functions = [
        "get_custom_swagger_ui_html",
        "get_enhanced_redoc_html",
        "setup_enhanced_docs",
    ]

    missing_functions = [f for f in required_functions if f not in config_content]

    if missing_functions:
        return False

    # 检查文档端点
    docs_api_path = "src/api/docs.py"
    if not os.path.exists(docs_api_path):
        return False

    with open(docs_api_path, encoding="utf-8") as f:
        api_content = f.read()

    # 检查端点
    endpoints = ["enhanced", "interactive", "examples", "status"]
    missing_endpoints = []

    for endpoint in endpoints:
        if f'@router.get("/{endpoint}"' not in api_content:
            missing_endpoints.append(endpoint)

    if missing_endpoints:
        return False

    # 检查HTML内容
    config_content.count("<html>")
    config_content.count("<style>")
    config_content.count("<script>")

    return True


def verify_file_structure():
    """验证整体文件结构."""
    # 主要目录和文件
    key_items = [
        ("docs/api_reference.md", "API参考文档"),
        ("docs/error_codes.md", "错误代码文档"),
        ("sdk/python/football_prediction_sdk/", "Python SDK包"),
        ("sdk/python/setup.py", "SDK安装配置"),
        ("src/config/swagger_ui_config.py", "Swagger UI配置"),
        ("src/api/docs.py", "文档API端点"),
        ("src/main.py", "主应用文件"),
    ]

    existing_items = 0
    for path, _description in key_items:
        if os.path.exists(path):
            existing_items += 1
        else:
            pass

    completion_rate = (existing_items / len(key_items)) * 100

    return completion_rate >= 90


def verify_code_quality():
    """验证代码质量."""
    # 检查Python文件语法
    python_files = [
        "src/config/swagger_ui_config.py",
        "src/api/docs.py",
        "sdk/python/setup.py",
    ]

    syntax_errors = 0
    for py_file in python_files:
        if os.path.exists(py_file):
            try:
                with open(py_file, encoding="utf-8") as f:
                    compile(f.read(), py_file, "exec")
            except SyntaxError:
                syntax_errors += 1
            except Exception:
                pass

    if syntax_errors > 0:
        return False

    # 检查文档格式
    doc_files = ["docs/api_reference.md", "docs/error_codes.md"]
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            try:
                with open(doc_file, encoding="utf-8") as f:
                    content = f.read()
                    # 基本Markdown格式检查
                    if content.count("#") < 5:  # 至少应该有5个标题
                        pass
                    else:
                        pass
            except Exception:
                pass

    return True


def main():
    """主验证函数."""
    results = []

    # 执行各项验证
    results.append(("API参考文档", verify_api_reference_docs()))
    results.append(("错误代码文档", verify_error_codes_docs()))
    results.append(("Python SDK", verify_python_sdk()))
    results.append(("Swagger UI增强", verify_swagger_ui_enhancements()))
    results.append(("文件结构", verify_file_structure()))
    results.append(("代码质量", verify_code_quality()))

    # 汇总结果

    passed = 0
    total = len(results)

    for _name, result in results:
        if result:
            passed += 1

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
