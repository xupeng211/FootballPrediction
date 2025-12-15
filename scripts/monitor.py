#!/usr/bin/env python3
"""
天网计划 (Operation Skynet) 实时监控面板
提供L2数据回补进度可视化监控
"""

import asyncio
import os
import asyncpg
import sys
from datetime import datetime

async def show_dashboard():
    """显示实时监控面板"""

    # 数据库连接
    db_url = 'postgresql://postgres:postgres@localhost:5432/football_prediction'
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    # 清屏
    os.system('cls' if os.name == 'nt' else 'clear')

    print("\n🕸️  天网计划 (Operation Skynet) 实时监控面板")
    print("=" * 60)
    print(f"📅 监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        # 1. 获取总任务量 (已完赛)
        total = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE status = 'FT'")

        # 2. 获取已完成量 (以核心字段 home_big_chances_created 有值为准)
        completed = await conn.fetchval("""
            SELECT COUNT(*) FROM matches
            WHERE status = 'FT'
            AND home_big_chances_created IS NOT NULL
        """)

        # 3. 计算进度
        remaining = total - completed
        percent = (completed / total * 100) if total > 0 else 0

        # 4. 进度条绘制
        bar_length = 40
        filled_length = int(bar_length * completed // total) if total > 0 else 0
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        print(f"📊 总体进度: [{bar}] {percent:.2f}%")
        print("-" * 60)
        print(f"✅ 已采集 (79维度):  {completed:6} 场")
        print(f"⏳ 剩余待采集:      {remaining:6} 场")
        print(f"🏁 总目标场次:      {total:6} 场")
        print("-" * 60)

        # 5. 估算剩余时间 (按平均 2.5秒/场 估算)
        eta_hours = (remaining * 2.5) / 3600
        if eta_hours < 1:
            eta_minutes = eta_hours * 60
            print(f"🚀 预估剩余耗时:    {eta_minutes:.1f} 分钟")
        else:
            print(f"🚀 预估剩余耗时:    {eta_hours:.1f} 小时")

        # 6. 额外统计信息
        print("-" * 60)

        # 检查关键字段覆盖
        key_fields_stats = {}
        key_fields = [
            ('home_big_chances_created', '绝佳机会'),
            ('home_accurate_crosses', '精准传中'),
            ('home_accurate_long_balls', '精准长传'),
            ('home_blocked_shots', '被封堵射门')
        ]

        print("🎯 关键字段覆盖:")
        for field, desc in key_fields:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM matches WHERE status = 'FT' AND {field} IS NOT NULL")
                field_percent = (count / completed * 100) if completed > 0 else 0
                print(f"   - {desc:12}: {count:4} 场 ({field_percent:5.1f}%)")
            except Exception:
                print(f"   - {desc:12}: 字段不存在")

        # 7. 最近处理状态检查
        print("-" * 60)

        # 检查最近更新的记录
        recent = await conn.fetchrow("""
            SELECT match_date, home_team_name, away_team_name, home_possession, home_big_chances_created
            FROM matches
            WHERE status = 'FT' AND home_big_chances_created IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 1
        """)

        if recent:
            print("🔄 最近处理:")
            print(f"   比赛: {recent['home_team_name']} vs {recent['away_team_name']}")
            print(f"   日期: {recent['match_date'].date() if recent['match_date'] else 'N/A'}")
            print(f"   控球率: {recent['home_possession']}%")
            print(f"   绝佳机会: {recent['home_big_chances_created']}")

        print("=" * 60)
        print("💡 提示: 使用 'watch -n 30 python scripts/monitor.py' 实时监控")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(show_dashboard())