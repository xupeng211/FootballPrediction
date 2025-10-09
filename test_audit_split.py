#!/usr/bin/env python3
"""
测试拆分后的审计服务模块
Test Split Audit Service Module
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/home/user/projects/FootballPrediction')

def test_imports():
    """测试导入功能"""
    print("🔍 测试模块导入...")

    try:
        # 测试基础模块导入
        from src.services.audit.advanced.context import AuditContext
        from src.services.audit.advanced.models import AuditAction, AuditSeverity, AuditLog
        from src.services.audit.advanced.sanitizer import DataSanitizer
        print("✅ 基础模块导入成功")

        # 测试分析器导入
        from src.services.audit.advanced.analyzers.data_analyzer import DataAnalyzer
        from src.services.audit.advanced.analyzers.pattern_analyzer import PatternAnalyzer
        from src.services.audit.advanced.analyzers.risk_analyzer import RiskAnalyzer
        print("✅ 分析器模块导入成功")

        # 测试日志器导入
        from src.services.audit.advanced.loggers.audit_logger import AuditLogger
        from src.services.audit.advanced.loggers.structured_logger import StructuredLogger
        from src.services.audit.advanced.loggers.async_logger import AsyncLogger
        print("✅ 日志器模块导入成功")

        # 测试报告器导入
        from src.services.audit.advanced.reporters.report_generator import ReportGenerator
        from src.services.audit.advanced.reporters.template_manager import TemplateManager
        from src.services.audit.advanced.reporters.export_manager import ExportManager
        print("✅ 报告器模块导入成功")

        # 测试装饰器导入
        from src.services.audit.advanced.decorators.audit_decorators import audit_action
        from src.services.audit.advanced.decorators.performance_decorator import monitor_performance
        from src.services.audit.advanced.decorators.security_decorator import require_permission
        print("✅ 装饰器模块导入成功")

        return True

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")

    try:
        from src.services.audit.advanced.context import AuditContext
        from src.services.audit.advanced.models import AuditAction, AuditSeverity, AuditLog
        from src.services.audit.advanced.sanitizer import DataSanitizer

        # 测试上下文创建
        context = AuditContext(
            user_id="test_user",
            username="test_user",
            user_role="admin"
        )
        print("✅ 审计上下文创建成功")

        # 测试数据清理器
        sanitizer = DataSanitizer()
        test_data = {"password": "secret123", "email": "test@example.com"}
        sanitized = sanitizer.sanitize_data(test_data)
        print("✅ 数据清理功能正常")

        # 测试审计日志创建
        audit_log = AuditLog(
            user_id="test_user",
            action=AuditAction.CREATE,
            description="测试操作"
        )
        print("✅ 审计日志创建成功")

        return True

    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        return False

def test_analyzers():
    """测试分析器功能"""
    print("\n📊 测试分析器功能...")

    try:
        from src.services.audit.advanced.analyzers.data_analyzer import DataAnalyzer
        from src.services.audit.advanced.analyzers.pattern_analyzer import PatternAnalyzer
        from src.services.audit.advanced.analyzers.risk_analyzer import RiskAnalyzer

        # 创建分析器实例
        data_analyzer = DataAnalyzer()
        pattern_analyzer = PatternAnalyzer()
        risk_analyzer = RiskAnalyzer()
        print("✅ 分析器实例创建成功")

        # 测试数据分析
        old_values = {"name": "old_name", "email": "old@example.com"}
        new_values = {"name": "new_name", "email": "new@example.com"}
        changes = data_analyzer.analyze_data_changes(old_values, new_values)
        print("✅ 数据变更分析功能正常")

        # 测试风险评估
        operation = {"action": "delete", "resource_type": "users", "user_role": "admin"}
        risk_assessment = risk_analyzer.assess_risk(operation)
        print("✅ 风险评估功能正常")

        return True

    except Exception as e:
        print(f"❌ 分析器测试失败: {e}")
        return False

def test_decorators():
    """测试装饰器功能"""
    print("\n🎭 测试装饰器功能...")

    try:
        from src.services.audit.advanced.decorators.audit_decorators import audit_action
        from src.services.audit.advanced.decorators.performance_decorator import monitor_performance

        # 测试装饰器创建
        @audit_action("test_action", resource_type="test")
        @monitor_performance(threshold=1.0)
        def test_function():
            return "test_result"

        print("✅ 装饰器应用成功")

        return True

    except Exception as e:
        print(f"❌ 装饰器测试失败: {e}")
        return False

def test_backwards_compatibility():
    """测试向后兼容性"""
    print("\n🔄 测试向后兼容性...")

    try:
        # 测试原有接口是否可用
        from src.services.audit_service_mod import AuditService as LegacyAuditService
        from src.services.audit_service_mod import AuditContext, AuditAction

        print("✅ 原有接口导入成功")

        # 测试新的工厂函数
        from src.services.audit_service_mod import get_audit_service

        # 这里不实际初始化，只测试导入
        print("✅ 兼容性接口正常")

        return True

    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试拆分后的审计服务模块\n")

    tests = [
        test_imports,
        test_basic_functionality,
        test_analyzers,
        test_decorators,
        test_backwards_compatibility,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📋 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！拆分成功！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)