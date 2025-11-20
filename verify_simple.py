#!/usr/bin/env python3
"""
简化的系统集成验证脚本
验证核心系统组件是否正常工作
"""

import sys
import os
import requests
import json
from datetime import datetime

def test_external_api():
    """测试外部API连接"""
    print("🔍 测试外部Football API...")
    try:
        api_key = "ed809154dc1f422da46a18d8961a98a0"
        url = "https://api.football-data.org/v4/matches"
        headers = {"X-Auth-Token": api_key}
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Football API连接成功")
            print(f"📊 响应状态: {response.status_code}")
            print(f"📊 返回数据: {len(data.get('matches', []))} 场比赛")
            return True
        else:
            print(f"⚠️ API响应状态码: {response.status_code}")
            print(f"📊 响应内容: {response.text[:200]}...")
            return False

    except Exception as e:
        print(f"❌ API连接失败: {e}")
        return False

def test_redis_connection():
    """测试Redis连接"""
    print("\n🔍 测试Redis连接...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()

        # 测试读写操作
        test_key = "test:verify:" + str(int(datetime.now().timestamp()))
        r.set(test_key, "test_value", ex=60)
        value = r.get(test_key)
        r.delete(test_key)

        print(f"✅ Redis连接成功")
        print(f"📊 测试读写操作成功: {value}")
        return True

    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

def test_database_connection():
    """测试数据库连接"""
    print("\n🔍 测试数据库连接...")
    try:
        # 尝试多种连接字符串
        connection_strings = [
            "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
            "postgresql://postgres:postgres@localhost:5432/football_prediction",
            "postgresql://postgres:@localhost:5432/football_prediction"
        ]

        import psycopg2
        conn = None
        working_connection = None

        for conn_str in connection_strings:
            try:
                conn = psycopg2.connect(conn_str)
                working_connection = conn_str
                print(f"✅ 数据库连接成功")
                print(f"📊 连接字符串: {conn_str}")

                # 测试基本查询
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                print(f"📊 PostgreSQL版本: {version[0][:50]}...")

                # 测试数据库是否存在
                cursor.execute("SELECT current_database();")
                db_name = cursor.fetchone()
                print(f"📊 当前数据库: {db_name[0]}")

                conn.close()
                return True

            except Exception as e:
                if conn:
                    conn.close()
                print(f"⚠️ 连接失败 ({conn_str}): {e}")
                continue

        print(f"❌ 所有数据库连接尝试均失败")
        return False

    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False

def test_basic_application():
    """测试基础应用功能"""
    print("\n🔍 测试基础应用功能...")
    try:
        sys.path.append('src')

        # 测试核心模块导入
        print("📊 测试核心模块导入...")

        try:
            import fastapi
            print("✅ FastAPI导入成功")
        except ImportError:
            print("❌ FastAPI未安装")
            return False

        try:
            import sqlalchemy
            print("✅ SQLAlchemy导入成功")
        except ImportError:
            print("❌ SQLAlchemy未安装")
            return False

        # 尝试导入应用
        try:
            from src.main import app
            print("✅ FastAPI应用导入成功")
            print(f"📊 应用标题: {app.title}")
            print(f"📊 应用版本: {app.version}")
            return True
        except Exception as e:
            print(f"⚠️ 应用导入失败: {e}")
            return False

    except Exception as e:
        print(f"❌ 应用测试失败: {e}")
        return False

def main():
    """主验证流程"""
    print("=" * 60)
    print("🚀 FootballPrediction 系统集成验证")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {
        "外部API": test_external_api(),
        "Redis": test_redis_connection(),
        "数据库": test_database_connection(),
        "基础应用": test_basic_application()
    }

    print("\n" + "=" * 60)
    print("📊 验证结果汇总:")
    print("=" * 60)

    success_count = 0
    total_count = len(results)

    for component, status in results.items():
        status_emoji = "✅" if status else "❌"
        print(f"{status_emoji} {component}: {'PASS' if status else 'FAIL'}")
        if status:
            success_count += 1

    print("\n" + "=" * 60)
    success_rate = (success_count / total_count) * 100
    print(f"🎯 总体成功率: {success_rate:.1f}% ({success_count}/{total_count})")

    if success_rate >= 75:
        print("🎉 系统集成验证: 通过")
        return 0
    elif success_rate >= 50:
        print("⚠️ 系统集成验证: 部分通过")
        return 1
    else:
        print("❌ 系统集成验证: 失败")
        return 2

if __name__ == "__main__":
    sys.exit(main())