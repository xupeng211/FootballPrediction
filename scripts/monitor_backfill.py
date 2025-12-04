#!/usr/bin/env python3
"""
大规模回填实时监控仪表板
Chief Data Engineer: 实时监控数据收集进度
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackfillMonitor:
    """大规模回填实时监控器"""

    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@db:5432/football_prediction")

        # 监控统计
        self.start_time = datetime.utcnow()
        self.last_count = 0
        self.last_check_time = datetime.utcnow()
        self.peak_rate = 0

    async def get_current_stats(self):
        """获取当前数据库统计"""
        try:
            conn = await asyncpg.connect(self.database_url)

            # 获取总体统计
            total_matches = await conn.fetchval(
                "SELECT COUNT(*) FROM matches WHERE data_source LIKE '%fotmob%'"
            )

            # 按联赛统计
            league_stats = await conn.fetch("""
                SELECT l.name, COUNT(m.id) as match_count
                FROM leagues l
                LEFT JOIN matches m ON l.id = m.league_id AND m.data_source LIKE '%fotmob%'
                WHERE l.fotmob_id IS NOT NULL
                GROUP BY l.name, l.fotmob_id
                ORDER BY match_count DESC
                LIMIT 10
            """)

            # 按赛季统计
            season_stats = await conn.fetch("""
                SELECT season, COUNT(*) as match_count
                FROM matches
                WHERE data_source LIKE '%fotmob%'
                GROUP BY season
                ORDER BY season DESC
            """)

            # 最近数据收集
            recent_activity = await conn.fetch("""
                SELECT created_at, data_source, COUNT(*) as batch_size
                FROM matches
                WHERE data_source LIKE '%fotmob%'
                GROUP BY created_at, data_source
                ORDER BY created_at DESC
                LIMIT 5
            """)

            await conn.close()

            return {
                'total_matches': total_matches,
                'league_stats': league_stats,
                'season_stats': season_stats,
                'recent_activity': recent_activity
            }

        except Exception as e:
            logger.error(f"❌ 获取统计数据失败: {e}")
            return None

    def calculate_performance_metrics(self, current_count):
        """计算性能指标"""
        now = datetime.utcnow()
        elapsed_total = (now - self.start_time).total_seconds()
        elapsed_since_last = (now - self.last_check_time).total_seconds()

        # 计算速率
        avg_rate = current_count / max(elapsed_total, 1)
        current_rate = (current_count - self.last_count) / max(elapsed_since_last, 1)

        # 更新峰值速率
        if current_rate > self.peak_rate:
            self.peak_rate = current_rate

        # 计算预计完成时间（假设目标是5000场比赛）
        target_matches = 5000
        remaining = target_matches - current_count
        eta_seconds = remaining / max(current_rate, 0.1) if current_rate > 0 else float('inf')

        return {
            'avg_rate': avg_rate,
            'current_rate': current_rate,
            'peak_rate': self.peak_rate,
            'eta_hours': eta_seconds / 3600 if eta_seconds != float('inf') else None,
            'elapsed_total_hours': elapsed_total / 3600,
            'progress_percent': min((current_count / target_matches) * 100, 100)
        }

    def format_output(self, stats, metrics):
        """格式化输出显示"""
        print("\n" + "=" * 80)
        print(f"📊 大规模FotMob回填实时监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        print(f"\n🎯 核心指标:")
        print(f"   总比赛数: {stats['total_matches']:,} 场")
        print(f"   平均速率: {metrics['avg_rate']:.1f} 场/秒")
        print(f"   当前速率: {metrics['current_rate']:.1f} 场/秒")
        print(f"   峰值速率: {metrics['peak_rate']:.1f} 场/秒")
        print(f"   进度: {metrics['progress_percent']:.1f}%")

        if metrics['eta_hours']:
            eta_str = f"{metrics['eta_hours']:.1f} 小时" if metrics['eta_hours'] < 24 else f"{metrics['eta_hours']/24:.1f} 天"
            print(f"   预计完成: {eta_str}")

        print(f"\n📈 联赛数据分布:")
        for league_stat in stats['league_stats'][:5]:
            league_name = league_stat['name']
            match_count = league_stat['match_count']
            print(f"   {league_name:<20} {match_count:>6,} 场")

        if stats['season_stats']:
            print(f"\n📅 赛季覆盖:")
            for season_stat in stats['season_stats']:
                season = season_stat['season'] or '未知'
                count = season_stat['match_count']
                print(f"   {season:<15} {count:>6,} 场")

        if stats['recent_activity']:
            print(f"\n⏰ 最近活动:")
            for activity in stats['recent_activity']:
                created_at = activity['created_at']
                source = activity['data_source']
                batch_size = activity['batch_size']
                print(f"   {created_at.strftime('%H:%M:%S')} - {source:<25} +{batch_size:,}")

        print("\n" + "-" * 80)

    async def run_monitoring(self):
        """运行监控循环"""
        logger.info("🔍 启动大规模回填实时监控")
        logger.info(f"⏱️ 检查间隔: {self.check_interval} 秒")

        try:
            while True:
                # 获取统计数据
                stats = await self.get_current_stats()

                if stats:
                    # 计算性能指标
                    metrics = self.calculate_performance_metrics(stats['total_matches'])

                    # 显示输出
                    self.format_output(stats, metrics)

                    # 更新上次检查数据
                    self.last_count = stats['total_matches']
                    self.last_check_time = datetime.utcnow()

                    # 检查是否达到目标
                    if stats['total_matches'] >= 5000:
                        logger.info("🎉 已达到目标5000场比赛!")
                        break

                # 等待下次检查
                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("\n⏹️ 用户中断监控")
        except Exception as e:
            logger.error(f"💥 监控异常: {e}")


async def main():
    """主函数"""
    # 解析参数
    interval = 30  # 默认30秒

    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith("--interval="):
                interval = int(arg.split("=")[1])

    logger.info("🏭 首席数据工程师 - 实时监控仪表板")
    logger.info(f"⏱️ 监控间隔: {interval} 秒")

    # 启动监控
    monitor = BackfillMonitor(check_interval=interval)
    await monitor.run_monitoring()


if __name__ == "__main__":
    asyncio.run(main())