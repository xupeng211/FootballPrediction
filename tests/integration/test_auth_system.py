#!/usr/bin/env python3
"""
用户认证系统测试脚本

测试用户注册、登录、令牌验证等功能
"""

import asyncio
from datetime import datetime

import httpx
from passlib.context import CryptContext

# 测试配置
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_USER = {
    "username": "test_auth_user",
    "email": "testauth@example.com",
    "password": "testpassword123",
    "first_name": "认证",
    "last_name": "测试用户",
}

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def print_test_header(test_name: str):
    """打印测试标题"""
    print(f"\n{'='*60}")  # TODO: Add logger import if needed
    print(f"🧪 测试: {test_name}")  # TODO: Add logger import if needed
    print(f"{'='*60}")  # TODO: Add logger import if needed


def print_success(message: str):
    """打印成功消息"""
    print(f"✅ {message}")  # TODO: Add logger import if needed


def print_error(message: str):
    """打印错误消息"""
    print(f"❌ {message}")  # TODO: Add logger import if needed


def print_info(message: str):
    """打印信息消息"""
    print(f"ℹ️  {message}")  # TODO: Add logger import if needed


async def test_api_health():
    """测试API健康状态"""
    print_test_header("API健康检查")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/health/")
            if response.status_code == 200:
                health_data = response.json()
                print_success(f"API健康状态: {health_data.get('status')}")
                print_info(
                    f"数据库延迟: {health_data.get('checks', {}).get('database', {}).get('latency_ms')}ms"
                )
                return True
            else:
                print_error(f"API健康检查失败: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"API连接失败: {e}")
        return False


async def test_user_registration():
    """测试用户注册"""
    print_test_header("用户注册测试")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/auth/register", json=TEST_USER
            )

            if response.status_code == 201:
                user_data = response.json()
                print_success("用户注册成功")
                print_info(f"用户ID: {user_data.get('id')}")
                print_info(f"用户名: {user_data.get('username')}")
                print_info(f"邮箱: {user_data.get('email')}")
                print_info(f"角色: {user_data.get('role')}")
                return True
            else:
                error_data = response.json()
                print_error(f"用户注册失败: {error_data.get('detail')}")
                return False
    except Exception as e:
        print_error(f"注册请求失败: {e}")
        return False


async def test_user_login():
    """测试用户登录"""
    print_test_header("用户登录测试")

    try:
        async with httpx.AsyncClient() as client:
            login_data = {
                "username": TEST_USER["username"],
                "password": TEST_USER["password"],
            }

            response = await client.post(f"{API_BASE_URL}/auth/login", data=login_data)

            if response.status_code == 200:
                token_data = response.json()
                print_success("用户登录成功")
                print_info(f"令牌类型: {token_data.get('token_type')}")
                print_info(f"访问令牌: {token_data.get('access_token')[:50]}...")
                print_info(f"刷新令牌: {token_data.get('refresh_token')[:50]}...")
                print_info(f"过期时间: {token_data.get('expires_in')}秒")
                return token_data.get("access_token")
            else:
                error_data = response.json()
                print_error(f"用户登录失败: {error_data.get('detail')}")
                return None
    except Exception as e:
        print_error(f"登录请求失败: {e}")
        return None


async def test_get_current_user(access_token: str):
    """测试获取当前用户信息"""
    print_test_header("获取当前用户信息")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/auth/me", headers=headers)

            if response.status_code == 200:
                user_data = response.json()
                print_success("获取用户信息成功")
                print_info(f"用户ID: {user_data.get('id')}")
                print_info(f"用户名: {user_data.get('username')}")
                print_info(f"全名: {user_data.get('full_name')}")
                print_info(f"邮箱: {user_data.get('email')}")
                print_info(f"角色: {user_data.get('role')}")
                print_info(f"是否激活: {user_data.get('is_active')}")
                print_info(f"是否已验证: {user_data.get('is_verified')}")
                return True
            else:
                error_data = response.json()
                print_error(f"获取用户信息失败: {error_data.get('detail')}")
                return False
    except Exception as e:
        print_error(f"获取用户信息请求失败: {e}")
        return False


async def test_existing_users():
    """测试现有用户登录"""
    print_test_header("现有用户登录测试")

    existing_users = [
        {"username": "admin", "password": "admin123"},
        {"username": "testuser", "password": "test123"},
    ]

    for user in existing_users:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{API_BASE_URL}/auth/login", data=user)

                if response.status_code == 200:
                    token_data = response.json()
                    print_success(f"用户 {user['username']} 登录成功")
                    print_info(f"角色: {token_data.get('user', {}).get('role')}")
                else:
                    error_data = response.json()
                    print_error(
                        f"用户 {user['username']} 登录失败: {error_data.get('detail')}"
                    )
        except Exception as e:
            print_error(f"用户 {user['username']} 登录请求失败: {e}")


async def main():
    """主测试函数"""
    print("🚀 开始用户认证系统测试")  # TODO: Add logger import if needed
    print(
        f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )  # TODO: Add logger import if needed
    print(f"🔗 API地址: {API_BASE_URL}")  # TODO: Add logger import if needed

    # 测试API健康状态
    if not await test_api_health():
        print("\n❌ API服务不可用，测试终止")  # TODO: Add logger import if needed
        return

    # 测试现有用户
    await test_existing_users()

    # 测试用户注册
    registration_success = await test_user_registration()

    if registration_success:
        # 测试用户登录
        access_token = await test_user_login()

        if access_token:
            # 测试获取当前用户信息
            await test_get_current_user(access_token)

    print(f"\n{'='*60}")  # TODO: Add logger import if needed
    print("🎉 用户认证系统测试完成")  # TODO: Add logger import if needed
    print(f"{'='*60}")  # TODO: Add logger import if needed


if __name__ == "__main__":
    asyncio.run(main())
