#!/usr/bin/env python3
"""
Smoke Test for Data Backfill System
验证数据流是否真正打通的实战测试
"""
import asyncio
import sys
import time
import psycopg2
from datetime import datetime
import os

def get_db_connection():
    """获取数据库连接"""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction")
    # 转换URL格式用于psycopg2
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("postgresql://"):
        pass  # 已经是正确格式
    else:
        db_url = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"

    return psycopg2.connect(db_url)

def get_matches_count():
    """获取当前比赛数量"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM matches")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

async def main():
    """主测试函数"""
    print("🔥 SRE SMOKE TEST - 数据流验证开始...")
    print(f"⏰ 测试时间: {datetime.now()}")

    # Step 1: 获取起始数据量
    print("📊 Step 1: 获取起始数据量...")
    count_start = get_matches_count()
    if count_start is None:
        print("❌ 无法连接数据库，测试失败")
        return False

    print(f"✅ 起始数据量: {count_start} 条记录")

    # Step 2: 等待60秒观察数据变化
    print("⏳ Step 2: 等待60秒观察数据变化...")
    for i in range(60, 0, -1):
        if i % 10 == 0:
            print(f"   剩余 {i} 秒...")
        await asyncio.sleep(1)

    # Step 3: 获取结束数据量
    print("📊 Step 3: 获取结束数据量...")
    count_end = get_matches_count()
    if count_end is None:
        print("❌ 最终数据检查失败")
        return False

    print(f"✅ 结束数据量: {count_end} 条记录")

    # Step 4: 数据流断言
    print("🔍 Step 4: 数据流断言...")
    print(f"   起始: {count_start}")
    print(f"   结束: {count_end}")
    print(f"   变化: {count_end - count_start:+d}")

    if count_end > count_start:
        print("🎉 SMOKE TEST PASSED: Data is flowing!")
        print(f"📈 新增数据: {count_end - count_start} 条记录")
        print("✅ 数据采集系统正常工作!")
        return True
    elif count_end == count_start:
        print("⚠️ SMOKE TEST WARNING: No data change detected")
        print("🔍 可能原因: 数据采集正常但保存失败，或API限流")
        return False
    else:
        print("❌ SMOKE TEST FAILED: Data decreased!")
        print("🚨 系统异常，需要立即干预!")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        sys.exit(1)