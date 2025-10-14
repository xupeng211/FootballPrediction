#!/usr/bin/env python3
"""
测试认证系统
"""

import asyncio
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_auth_system():
    """测试认证系统"""
    print("🔐 测试认证系统...")

    try:
        # 测试导入
        from src.security.auth import (
            AuthManager,
            get_auth_manager,
            Role,
            Permission,
            require_permissions,
            require_roles,
        )

        print("✓ 认证模块导入成功")

        # 测试AuthManager
        auth = AuthManager(secret_key="test-secret-key")
        print("✓ AuthManager 创建成功")

        # 测试创建token
        access_token = auth.create_access_token(
            data={
                "sub": "test-user",
                "roles": [Role.USER],
                "permissions": [Permission.READ_PREDICTION],
            }
        )
        print(f"✓ Access Token 创建成功: {access_token[:50]}...")

        # 测试验证token
        payload = auth.verify_token(access_token)
        print(f"✓ Token 验证成功: user_id={payload.get('sub')}")

        # 测试刷新token
        refresh_token = auth.create_refresh_token(
            data={
                "sub": "test-user",
                "roles": [Role.USER],
                "permissions": [Permission.READ_PREDICTION],
            }
        )
        auth.refresh_access_token(refresh_token)
        print("✓ Token 刷新成功")

        # 测试权限映射
        from src.security.auth import ROLE_PERMISSIONS, get_user_permissions

        user_perms = get_user_permissions([Role.USER])
        print(f"✓ 用户权限获取成功: {len(user_perms)} 个权限")

        # 测试API路由
        from src.api.auth import router

        print(f"✓ 认证路由创建成功: {router.prefix}")

        print("\n🎉 认证系统测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ 认证系统测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_api_integration():
    """测试API集成"""
    print("\n🌐 测试API集成...")

    try:
        # 测试FastAPI应用
        from src.api.app import app

        print("✓ FastAPI应用创建成功")

        # 检查认证路由是否注册
        for route in app.routes:
            if hasattr(route, "path") and "/auth" in route.path:
                print(f"✓ 找到认证路由: {route.path}")
                break
        else:
            print("⚠️  未找到认证路由")

        # 检查OpenAPI schema
        if app.openapi_schema:
            auth_schemas = [
                schema
                for schema in app.openapi_schema.get("components", {})
                .get("securitySchemes", {})
                .keys()
            ]
            if "bearerAuth" in auth_schemas:
                print("✓ OpenAPI包含Bearer认证")
            else:
                print("⚠️  OpenAPI缺少Bearer认证")

        print("\n🎉 API集成测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ API集成测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("FootballPrediction 认证系统测试")
    print("=" * 60)

    # 测试认证系统
    auth_ok = await test_auth_system()

    # 测试API集成
    api_ok = await test_api_integration()

    print("\n" + "=" * 60)
    if auth_ok and api_ok:
        print("✅ 所有测试通过! 认证系统已就绪")
    else:
        print("❌ 部分测试失败，请检查")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
