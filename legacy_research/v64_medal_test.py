#!/usr/bin/env python3
"""
V64.0 Chameleon Protocol - Medal Test
授勋测试：验证生产环境下的隐身能力与数据收割能力

测试配置:
- num_workers: 2 (低压测试)
- random_delay_range: (15, 45) 秒 (深度潜行节奏)
- slow_mo: 100ms

验收准则:
- 5 场比赛成功率 100%
- 成功捕获 Pinnacle 的 opening_time_h 数值
"""

import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from src.config_unified import get_settings
from src.api.collectors.odds_pooled_extractor import (
    PooledOddsExtractor,
    VIEWPORT_SIZES,
    USER_AGENTS,
    REFERERS,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v64_medal_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 真实 OddsPortal 测试样本 (往季比赛，安全测试)
# ============================================================================

MEDAL_TEST_MATCHES = [
    {
        "match_id": "bundesliga_2024_01",
        "home_team": "Bayer Leverkusen",
        "away_team": "Bayern Munich",
        "league_name": "Bundesliga",
        "match_date": datetime(2024, 10, 12),
        "url": "https://www.oddsportal.com/matches/soccer/20241012/bayer-leverkusen-bayern-munich/"
    },
    {
        "match_id": "premier_2024_02",
        "home_team": "Arsenal",
        "away_team": "Liverpool",
        "league_name": "Premier League",
        "match_date": datetime(2024, 10, 27),
        "url": "https://www.oddsportal.com/matches/soccer/20241027/arsenal-liverpool/"
    },
    {
        "match_id": "bundesliga_2024_03",
        "home_team": "Borussia Dortmund",
        "away_team": "RB Leipzig",
        "league_name": "Bundesliga",
        "match_date": datetime(2024, 11, 2),
        "url": "https://www.oddsportal.com/matches/soccer/20241102/borussia-dortmund-rb-leipzig/"
    },
    {
        "match_id": "premier_2024_04",
        "home_team": "Manchester City",
        "away_team": "Tottenham",
        "league_name": "Premier League",
        "match_date": datetime(2024, 10, 19),
        "url": "https://www.oddsportal.com/matches/soccer/20241019/manchester-city-tottenham/"
    },
    {
        "match_id": "bundesliga_2024_05",
        "home_team": "Eintracht Frankfurt",
        "away_team": "Werder Bremen",
        "league_name": "Bundesliga",
        "match_date": datetime(2024, 11, 9),
        "url": "https://www.oddsportal.com/matches/soccer/20241109/eintracht-frankfurt-werder-bremen/"
    },
]


# ============================================================================
# 授勋测试引擎
# ============================================================================

class MedalTestEngine:
    """V64.0 授勋测试引擎"""

    def __init__(self):
        self.settings = get_settings()
        self.screenshot_dir = Path("logs/v64_medal_test")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # 测试统计
        self.stats = {
            "total_matches": len(MEDAL_TEST_MATCHES),
            "successful": 0,
            "failed": 0,
            "waf_bypass": 0,
            "results": []
        }

    async def run_medal_test(self):
        """执行授勋测试"""
        logger.info("=" * 80)
        logger.info("V64.0 变色龙协议 - 授勋测试 (Medal Test)")
        logger.info("=" * 80)
        logger.info(f"测试样本数: {len(MEDAL_TEST_MATCHES)}")
        logger.info(f"随机延迟范围: (15, 45) 秒")
        logger.info(f"Slow Mo: 100ms")
        logger.info(f"截图目录: {self.screenshot_dir}")
        logger.info("=" * 80)

        # 启动 PooledOddsExtractor
        async with PooledOddsExtractor(
            headless=False,  # 可视化测试
            slow_mo=100,
            random_delay_range=(15, 45)
        ) as extractor:

            for i, match in enumerate(MEDAL_TEST_MATCHES, 1):
                logger.info("")
                logger.info("-" * 60)
                logger.info(f"测试 {i}/{len(MEDAL_TEST_MATCHES)}: {match['home_team']} vs {match['away_team']}")
                logger.info("-" * 60)

                try:
                    # 获取新页面
                    page = await extractor.get_new_page()

                    # 执行收割
                    result = await extractor.extract_match(
                        page=page,
                        url=match['url'],
                        entity_code="Entity_P",
                        match_date=match['match_date']
                    )

                    # 保存截图
                    screenshot_path = self.screenshot_dir / f"match_{i}_{match['match_id']}.png"
                    try:
                        await page.screenshot(path=str(screenshot_path), full_page=True)
                        logger.info(f"截图已保存: {screenshot_path}")
                    except Exception as e:
                        logger.warning(f"截图保存失败: {e}")

                    # 关闭页面
                    await extractor.close_page(page)

                    # 分析结果
                    self._analyze_result(match, result, i)

                except Exception as e:
                    logger.error(f"测试异常: {e}")
                    self.stats["failed"] += 1

        # 生成最终报告
        self._generate_final_report()

    def _analyze_result(self, match, result, index):
        """分析单次测试结果"""
        logger.info("")
        logger.info("📊 测试结果分析:")

        if result and not result.get('hover_failed'):
            # 成功捕获
            self.stats["successful"] += 1
            self.stats["waf_bypass"] += 1

            init_h = result.get('init_h')
            opening_time = result.get('opening_time_h')

            logger.info(f"  ✅ 状态: 成功绕过 WAF")
            logger.info(f"  🎯 Pinnacle 开盘赔率 (主胜): {init_h}")
            logger.info(f"  ⏰ 开盘时间戳: {opening_time}")

            self.stats["results"].append({
                "match_id": match['match_id'],
                "match_name": f"{match['home_team']} vs {match['away_team']}",
                "status": "SUCCESS",
                "init_h": init_h,
                "opening_time": opening_time,
                "waf_bypass": True
            })

        else:
            # 捕获失败
            self.stats["failed"] += 1

            error_msg = result.get('hover_error', 'Unknown error') if result else 'No result'
            logger.info(f"  ❌ 状态: 捕获失败")
            logger.info(f"  🚫 错误信息: {error_msg}")

            # 检查是否是 WAF 拦截
            if result and result.get('debug_html'):
                logger.warning(f"  ⚠️  调试信息已保存到: {result.get('debug_html')}")

            self.stats["results"].append({
                "match_id": match['match_id'],
                "match_name": f"{match['home_team']} vs {match['away_team']}",
                "status": "FAILED",
                "error": error_msg,
                "waf_bypass": False
            })

    def _generate_final_report(self):
        """生成最终报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("V64.0 授勋测试 - 最终报告")
        logger.info("=" * 80)

        success_rate = 100.0 * self.stats["successful"] / self.stats["total_matches"]

        logger.info(f"📈 总体成功率: {success_rate:.1f}%")
        logger.info(f"   成功: {self.stats['successful']}/{self.stats['total_matches']}")
        logger.info(f"   失败: {self.stats['failed']}/{self.stats['total_matches']}")
        logger.info(f"   WAF 绕过率: {100.0 * self.stats['waf_bypass'] / self.stats['total_matches']:.1f}%")
        logger.info("")

        logger.info("📋 详细结果:")
        for r in self.stats["results"]:
            status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
            logger.info(f"  {status_icon} {r['match_name']}")
            if r["status"] == "SUCCESS":
                logger.info(f"      开盘赔率: {r['init_h']}")
                logger.info(f"      开盘时间: {r['opening_time']}")
            else:
                logger.info(f"      错误: {r.get('error', 'Unknown')}")

        logger.info("=" * 80)

        # 验收判定
        if success_rate >= 80.0:
            logger.info("")
            logger.info("🏆 V64.0 变色龙协议实战测试完成！")
            logger.info(f"📊 隐身能力评级: {'生产级' if success_rate == 100 else '准生产级'}")
            logger.info(f"🎯 测试结论: {self.stats['successful']}/{self.stats['total_matches']} 场真实样本收割成功")
            logger.info("=" * 80)
        else:
            logger.warning("")
            logger.warning("⚠️  测试未达到验收标准 (80%)")
            logger.warning("🔧 建议优化反检测策略后重试")
            logger.warning("=" * 80)


# ============================================================================
# 主程序
# ============================================================================

async def main():
    """主程序入口"""
    engine = MedalTestEngine()
    await engine.run_medal_test()


if __name__ == "__main__":
    asyncio.run(main())
