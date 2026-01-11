#!/usr/bin/env python3
"""
物理删除 football_prediction_dev 数据库
⚠️ 警告：此操作不可逆！

执行方式：python -m scripts.ops.drop_dev_database
"""

import sys
from pathlib import Path

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from src.config_unified import get_settings

def drop_dev_database():
    """删除 football_prediction_dev 数据库"""

    print("=" * 80)
    print("⚠️  物理删除 football_prediction_dev 数据库")
    print("=" * 80)

    try:
        settings = get_settings()

        # 连接到 postgres 数据库（不能连接到要删除的数据库）
        print("\n📡 连接到 postgres 系统数据库...")
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database="postgres",  # 连接到系统数据库
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )

        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor() as cur:
            # 1. 检查数据库是否存在
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_database
                    WHERE datname = 'football_prediction_dev'
                );
            """)
            exists = cur.fetchone()[0]

            if not exists:
                print("❌ 数据库 football_prediction_dev 不存在")
                return False

            # 2. 终止所有连接到该数据库的会话
            print("\n🔌 终止所有连接到 football_prediction_dev 的会话...")
            cur.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = 'football_prediction_dev'
                AND pid != pg_backend_pid();
            """)
            terminated = cur.rowcount
            if terminated > 0:
                print(f"   终止了 {terminated} 个活动连接")
            else:
                print("   没有活动连接")

            # 3. 删除数据库
            print("\n💥 执行终极指令：DROP DATABASE football_prediction_dev;")
            cur.execute("DROP DATABASE football_prediction_dev;")
            print("✅ 数据库已成功删除")

        conn.close()

        # 4. 验证删除
        print("\n🔍 验证删除结果...")
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database="postgres",
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )

        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datname = 'football_prediction_dev';")
            result = cur.fetchall()

            if len(result) == 0:
                print("✅ 验证成功：football_prediction_dev 已不存在")
                print("\n🎉 垃圾库清理完成！Single Source of Truth 确认：football_db")
                return True
            else:
                print("❌ 验证失败：数据库仍然存在")
                return False

        conn.close()

    except Exception as e:
        print(f"\n❌ 删除失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = drop_dev_database()
    sys.exit(0 if success else 1)
