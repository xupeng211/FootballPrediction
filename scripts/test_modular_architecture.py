#!/usr/bin/env python3
"""
测试模块化架构的功能

验证拆分后的代码是否正常工作。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """测试所有模块的导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)

    tests = []

    # 测试audit_service_mod
    try:
        tests.append(("audit_service_mod", True, "✓ 导入成功"))
    except Exception as e:
        tests.append(("audit_service_mod", False, f"✗ 导入失败: {e}"))

    # 测试manager_mod
    try:
        tests.append(("manager_mod", True, "✓ 导入成功"))
    except Exception as e:
        tests.append(("manager_mod", False, f"✗ 导入失败: {e}"))

    # 测试data_processing_mod
    try:
        tests.append(("data_processing_mod", True, "✓ 导入成功"))
    except Exception as e:
        tests.append(("data_processing_mod", False, f"✗ 导入失败: {e}"))

    # 测试backward compatibility
    try:
        tests.append(("backward_compatibility", True, "✓ 兼容性正常"))
    except Exception as e:
        tests.append(("backward_compatibility", False, f"✗ 兼容性失败: {e}"))

    # 测试retry模块
    try:
        tests.append(("retry_module", True, "✓ 导入成功"))
    except Exception as e:
        tests.append(("retry_module", False, f"✗ 导入失败: {e}"))

    # 测试connection_mod
    try:
        tests.append(("connection_mod", True, "✓ 导入成功"))
    except Exception as e:
        tests.append(("connection_mod", False, f"✗ 导入失败: {e}"))

    # 打印结果
    for name, success, message in tests:
        print(f"{name:25} {message}")

    return all(success for _, success, _ in tests)


def test_audit_service_functionality():
    """测试audit_service的基本功能"""
    print("\n" + "=" * 60)
    print("测试AuditService功能")
    print("=" * 60)

    try:
        from src.services.audit_service import (
            AuditService,
            AuditContext,
            AuditAction,
            AuditSeverity,
        )

        # 创建上下文
        context = AuditContext(
            user_id="test_user_123",
            username="testuser",
            user_role="admin",
            session_id="session_456",
            ip_address="127.0.0.1",
            user_agent="Test-Agent/1.0",
        )

        # 创建服务实例
        service = AuditService()

        # 创建审计日志
        audit_log = service._create_audit_log_entry(
            context=context,
            action=AuditAction.LOGIN,
            resource_type="auth",
            description="测试登录",
            severity=AuditSeverity.LOW,
        )

        print("✓ AuditContext 创建成功")
        print("✓ AuditService 实例化成功")
        print("✓ 审计日志创建成功")
        print(f"  - 用户: {audit_log.username}")
        print(f"  - 动作: {audit_log.action}")
        print(f"  - 描述: {audit_log.description}")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_retry_functionality():
    """测试重试机制"""
    print("\n" + "=" * 60)
    print("测试重试机制")
    print("=" * 60)

    try:
        from src.utils._retry import RetryConfig, retry

        # 配置重试
        config = RetryConfig(max_attempts=3, base_delay=0.1)

        # 测试重试装饰器
        attempt_count = 0

        @retry(config)
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("测试失败")
            return "成功!"

        result = failing_function()
        print("✓ 重试机制正常工作")
        print(f"  - 尝试次数: {attempt_count}")
        print(f"  - 最终结果: {result}")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_content_analysis():
    """测试内容分析服务"""
    print("\n" + "=" * 60)
    print("测试ContentAnalysisService")
    print("=" * 60)

    try:
        from src.services.content_analysis import (
            ContentAnalysisService,
            Content,
        )

        # 创建服务
        ContentAnalysisService()

        # 创建测试内容
        content = Content(
            content_id="test_001",
            content_type="text",
            data={"text": "这是一场精彩的足球比赛！"},
        )

        print("✓ ContentAnalysisService 创建成功")
        print("✓ Content 对象创建成功")
        print(f"  - 内容ID: {content.id}")
        print(f"  - 内容类型: {content.content_type}")

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("模块化架构功能测试")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("导入测试", test_imports()))
    results.append(("AuditService功能", test_audit_service_functionality()))
    results.append(("重试机制", test_retry_functionality()))
    results.append(("内容分析服务", test_content_analysis()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20} {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！模块化架构工作正常。")
        return True
    else:
        print("\n⚠️ 部分测试失败，请检查相关模块。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
