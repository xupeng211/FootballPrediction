#!/usr/bin/env python3
"""
天网计划 (SkyNet) 核心监控面板 - 稳健版本
基于已确认存在的核心金指标进行监控
"""

import asyncio
import os
import asyncpg
from datetime import datetime

async def show_dashboard():
    """显示实时监控面板"""

    # 1. 连接数据库
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/football_prediction')
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    # 2. 清屏
    os.system('cls' if os.name == 'nt' else 'clear')

    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n🕸️  天网计划 (SkyNet) 核心监控面板 - {now}")
    print("=" * 60)

    try:
        # 3. 获取数据
        # 总任务量
        total = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE status = 'FT'")

        # 有效完成量 (只检查 home_big_chances_created，这是L2数据入库的金标准)
        completed = await conn.fetchval("""
            SELECT COUNT(*) FROM matches
            WHERE status = 'FT'
            AND home_big_chances_created IS NOT NULL
        """)

        # 4. 计算指标
        remaining = total - completed
        percent = (completed / total * 100) if total > 0 else 0

        # 5. 绘制进度条
        bar_length = 30
        filled_length = int(bar_length * completed // total) if total > 0 else 0
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        print(f"📊 总体进度: [{bar}] {percent:.2f}%")
        print("-" * 60)
        print(f"✅ 已完工 (79维度):  {completed:6} 场")
        print(f"⏳ 剩余任务:         {remaining:6} 场")
        print(f"🏁 总场次:           {total:6} 场")
        print("-" * 60)

        # 6. 估算时间 (假设 2.5s/场)
        avg_speed = 2.5
        eta_seconds = remaining * avg_speed
        eta_hours = eta_seconds / 3600
        eta_minutes = (eta_seconds % 3600) / 60

        print(f"🚀 预估剩余时间:    {int(eta_hours)} 小时 {int(eta_minutes)} 分钟")
        print("=" * 60)

        # 7. 检查进程
        print("🔍 后台回补进程状态:")
        os.system("ps aux | grep backfill_l2_batch | grep -v grep")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(show_dashboard())