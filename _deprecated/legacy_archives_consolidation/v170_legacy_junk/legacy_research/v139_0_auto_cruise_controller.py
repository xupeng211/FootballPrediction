#!/usr/bin/env python3
"""
V139.0 24 小时全自动联动控制器 - 24h Auto Cruise Controller
================================================================

V138.2 + V136.1 联动流水线核心组件：

功能：
    1. 智能收割 - V138.2 全量模式扫描 PENDING 队列
    2. 生产级赔率解析 - V136.1 实时提取 Pinnacle 终盘
    3. 系统鲁棒性 - 4 并发 + 10 分钟冷却 + 自动重启
    4. 实时监控 - 每小时汇总报告

设计原则：
- 全自动运行 - 无人值守 24 小时巡航
- 智能联动 - URL 入库后自动触发赔率提取
- 健康监控 - 内存泄漏防护，浏览器自动重启
- 质量红线 - 100% 完整性评分合规

Author: Data Logistics Architect
Version: V139.0
Date: 2026-01-05
"""

import asyncio
import logging
import random
import signal
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v139_0_auto_cruise.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局运行标志
running = True


def signal_handler(signum, frame):
    """信号处理器 - 优雅关闭"""
    global running
    logger.info("🛑 收到关闭信号，正在优雅关闭...")
    running = False


class AutoCruiseController:
    """V139.0 全自动联动控制器"""

    def __init__(self):
        self.settings = get_settings()
        self.start_time = datetime.now()

        # 统计
        self.total_links_harvested = 0
        self.total_reversed_matches = 0
        self.total_odds_extracted = 0
        self.total_quality_passed = 0
        self.last_report_time = datetime.now()

    def print_hourly_report(self):
        """打印小时汇总报告"""
        now = datetime.now()
        elapsed = (now - self.last_report_time).total_seconds() / 3600
        total_elapsed = (now - self.start_time).total_seconds() / 3600

        if elapsed < 1.0:
            return

        logger.info("")
        logger.info("="*80)
        logger.info(f"🕰️ [小时报告] 运行时长: {total_elapsed:.1f} 小时")
        logger.info("="*80)

        # 获取实时统计
        import psycopg2
        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value()
        )
        cur = conn.cursor()

        # PENDING 队列
        cur.execute("""
            SELECT COUNT(*) FROM match_search_queue WHERE status = 'PENDING'
        """)
        pending_count = cur.fetchone()[0]

        # 新格式 URL
        cur.execute("""
            SELECT COUNT(*) FROM matches WHERE oddsportal_url LIKE '%/football/%'
        """)
        new_format_count = cur.fetchone()[0]

        # Pinnacle 赔率
        cur.execute("""
            SELECT COUNT(*) FROM metrics_multi_source_data
            WHERE source_name = 'Entity_P'
            AND integrity_score BETWEEN 1.02 AND 1.08
            AND data_timestamp::date = CURRENT_DATE
        """)
        today_odds = cur.fetchone()[0]

        cur.close()
        conn.close()

        logger.info(f"📊 [当前进度]")
        logger.info(f"  PENDING 队列剩余: {pending_count}")
        logger.info(f"  新格式链接总数: {new_format_count}")
        logger.info(f"  今日新增赔率: {today_odds} (100% 合规)")
        logger.info("")

        # 计算清理进度
        initial_pending = 2446
        cleared = initial_pending - pending_count
        progress_pct = (cleared / initial_pending * 100) if initial_pending > 0 else 0

        logger.info(f"🎯 [清理进度]")
        logger.info(f"  已清理: {cleared} 场 ({progress_pct:.2f}%)")
        logger.info(f"  剩余: {pending_count} 场")

        # 目标验收
        if cleared >= 1500:
            logger.info("✅ [验收达成] PENDING 队列下降 1,500+ 场！")
        elif cleared >= 1000:
            logger.info("🟡 [进度良好] PENDING 队列下降 1,000+ 场")
        elif cleared >= 500:
            logger.info("🟢 [正常推进] PENDING 队列下降 500+ 场")

        logger.info("="*80)
        logger.info("")

        self.last_report_time = now

    async def run_v1382_harvester(self, max_leagues: int = None):
        """运行 V138.2 智能收割器

        Args:
            max_leagues: 最大处理联赛数（None = 全量）
        """
        logger.info("🚀 启动 V138.2 智能收割器...")

        # 动态导入 V138.2
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "v138_2_smart_matcher",
            "scripts/v138_2_smart_matcher.py"
        )
        v1382_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v1382_module)

        # 创建实例并运行
        matcher = v1382_module.SmartBiDirectionalMatcher(max_concurrent_pages=4)
        await matcher.run(limit=max_leagues)

    async def run_v1361_extractor(self, limit: int = 50):
        """运行 V136.1 RPA 提取器

        Args:
            limit: 最大处理数量
        """
        logger.info("⚗️ 启动 V136.1 RPA 赔率提取器...")

        # 动态导入 V136.1
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "v136_1_rpa_enhanced_extractor",
            "scripts/v136_1_rpa_enhanced_extractor.py"
        )
        v1361_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v1361_module)

        # 创建实例并运行
        extractor = v1361_module.EnhancedOddsExtractor(
            target_league=None,  # 全联赛
            target_season=None
        )
        await extractor.run_batch(limit=limit)

    async def run_auto_cruise_cycle(self):
        """运行单次巡航周期

        流程：
        1. V138.2 智能收割（处理 5 个联赛）
        2. V136.1 赔率提取（处理 50 场）
        3. 打印小时报告
        """
        cycle_count = 0

        while running:
            cycle_count += 1
            logger.info("")
            logger.info("🔄" * 40)
            logger.info(f"🚁 巡航周期 #{cycle_count}")
            logger.info("🔄" * 40)
            logger.info("")

            try:
                # 阶段 1: 智能收割
                logger.info("📦 [阶段 1/3] 智能收割 - V138.2 全量模式")
                await self.run_v1382_harvester(max_leagues=5)

                # 阶段 2: 赔率提取
                logger.info("⚗️ [阶段 2/3] 生产级赔率解析 - V136.1 RPA 引擎")
                await self.run_v1361_extractor(limit=50)

                # 阶段 3: 打印报告
                logger.info("📊 [阶段 3/3] 实时监控 - 汇总报告")
                self.print_hourly_report()

                # 冷却时间（避免 IP 封禁）
                cooldown = random.randint(300, 600)  # 5-10 分钟
                logger.info(f"⏱️ 冷却: {cooldown/60:.1f} 分钟，避免 IP 封禁...")
                await asyncio.sleep(cooldown)

            except Exception as e:
                logger.error(f"❌ 周期执行异常: {e}")
                logger.info("⏳ 等待 5 分钟后重试...")
                await asyncio.sleep(300)

    def start_background_cruise(self):
        """启动后台巡航模式"""
        logger.info("="*80)
        logger.info("V139.0 24 小时全自动联动模式启动")
        logger.info("="*80)
        logger.info("⚙️ 运行配置:")
        logger.info("  - V138.2 智能收割: 5 联赛/周期")
        logger.info("  - V136.1 RPA 提取: 50 场/周期")
        logger.info("  - 并发数: 4 (安全模式)")
        logger.info("  - 冷却时间: 5-10 分钟")
        logger.info("  - 浏览器重启: 每 3 联赛")
        logger.info("  - 汇总报告: 每小时")
        logger.info("")

        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 运行异步巡航
        try:
            asyncio.run(self.run_auto_cruise_cycle())
        except KeyboardInterrupt:
            logger.info("🛑 键盘中断，正在关闭...")
            running = False

        logger.info("")
        logger.info("="*80)
        logger.info("🏁 24 小时全自动联动模式已关闭")
        logger.info("="*80)


def main():
    """主函数"""
    controller = AutoCruiseController()
    controller.start_background_cruise()


if __name__ == "__main__":
    main()
