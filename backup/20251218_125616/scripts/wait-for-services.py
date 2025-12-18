#!/usr/bin/env python3
"""
Wait for services to be ready
模拟CI中的等待逻辑
"""

import time
import socket
import sys
import subprocess


def wait_for_postgres(
    host="localhost",
    port=5432,
    user="test_user",
    database="football_prediction_test",
    timeout=60,
):
    """等待PostgreSQL服务就绪"""
    # 从环境变量读取参数，支持CI环境
    db_host = os.getenv("DB_HOST", host)
    db_port = int(os.getenv("DB_PORT", port))
    db_user = os.getenv("DB_USER", user)
    db_database = os.getenv("DB_NAME", database)
    db_password = os.getenv("DB_PASSWORD", "")

    print(
        f"🔄 等待PostgreSQL服务启动 (host={db_host}, port={db_port}, user={db_user}, database={db_database})..."
    )

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # 尝试连接数据库
            import psycopg2

            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_database,
                connect_timeout=2,
            )
            conn.close()
            elapsed = time.time() - start_time
            print(f"✅ PostgreSQL已就绪 (耗时: {elapsed:.1f}秒)")
            return True
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"⏳ PostgreSQL未就绪，等待中... (耗时: {elapsed:.1f}秒) - {e}")
            time.sleep(2)

    print(f"❌ PostgreSQL启动超时 ({timeout}秒)")
    return False


def wait_for_redis(host="localhost", port=6379, timeout=30):
    """等待Redis服务就绪"""
    print(f"🔄 等待Redis服务启动 (host={host}, port={port})...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # 尝试连接Redis
            import redis

            r = redis.Redis(
                host=host, port=port, socket_connect_timeout=2, socket_timeout=2
            )
            r.ping()
            elapsed = time.time() - start_time
            print(f"✅ Redis已就绪 (耗时: {elapsed:.1f}秒)")
            return True
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"⏳ Redis未就绪，等待中... (耗时: {elapsed:.1f}秒) - {e}")
            time.sleep(1)

    print(f"❌ Redis启动超时 ({timeout}秒)")
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Football Prediction CI服务等待脚本")
    print("=" * 60)

    # 检查环境变量
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 5432))
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))

    print(f"🔍 环境变量检查:")
    print(f"  - DB_HOST: {db_host}")
    print(f"  - DB_PORT: {db_port}")
    print(f"  - REDIS_HOST: {redis_host}")
    print(f"  - REDIS_PORT: {redis_port}")

    success = True

    # 等待PostgreSQL
    if not wait_for_postgres(db_host, db_port):
        success = False

    # 等待Redis
    if not wait_for_redis(redis_host, redis_port):
        success = False

    print("\n" + "=" * 60)
    if success:
        print("🎉 所有服务已就绪！")
        return 0
    else:
        print("❌ 部分服务启动失败")
        return 1


if __name__ == "__main__":
    import os

    sys.exit(main())
