#!/usr/bin/env python3
"""
V64.0 授勋测试二测 - 使用真实的 OddsPortal URL

从日志中提取的真实 URL:
1. https://www.oddsportal.com/football/germany/bundesliga-2024-2025/mainz-bayern-munich-pOYHWCAL/
2. https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.config_unified import get_settings
from src.api.collectors.odds_pooled_extractor import PooledOddsExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v64_medal_test_round2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 真实的 OddsPortal URL（从日志中提取）
# ============================================================================

REAL_GOLDEN_URLS = [
    {
        "match_id": "bundeslia_2024_mainz_bayern",
        "home_team": "Mainz",
        "away_team": "Bayern Munich",
        "league_name": "Bundesliga 2024/2025",
        "match_date": datetime(2024, 10, 26),  # 根据实际比赛日期估算
        "url": "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/mainz-bayern-munich-pOYHWCAL/"
    },
    {
        "match_id": "premier_2024_chelsea_arsenal",
        "home_team": "Chelsea",
        "away_team": "Arsenal",
        "league_name": "Premier League 2024/2025",
        "match_date": datetime(2024, 11, 10),  # 根据实际比赛日期估算
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/"
    },
]


class MedalTestRound2:
    """授勋测试二测 - 真实 URL"""

    def __init__(self):
        self.screenshot_dir = Path("logs/v64_medal_test_round2")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "total_matches": len(REAL_GOLDEN_URLS),
            "successful": 0,
            "failed": 0,
            "results": []
        }

    async def run_test(self):
        """执行授勋测试二测"""
        logger.info("=" * 80)
        logger.info("V64.0 授勋测试二测 - 真实 OddsPortal URL")
        logger.info("=" * 80)
        logger.info(f"测试样本数: {len(REAL_GOLDEN_URLS)}")
        logger.info(f"配置: V64.0 变色龙协议 (15-45s 延迟, 100ms slow_mo)")
        logger.info("=" * 80)

        async with PooledOddsExtractor(
            headless=False,
            slow_mo=100,
            random_delay_range=(15, 45)
        ) as extractor:

            for i, match in enumerate(REAL_GOLDEN_URLS, 1):
                logger.info("")
                logger.info("-" * 60)
                logger.info(f"测试 {i}/{len(REAL_GOLDEN_URLS)}: {match['home_team']} vs {match['away_team']}")
                logger.info(f"URL: {match['url']}")
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

            init_h = result.get('init_h')
            opening_time = result.get('opening_time_h')

            logger.info(f"  ✅ 状态: 成功!")
            logger.info(f"  🎯 Pinnacle 开盘赔率 (主胜): {init_h}")
            logger.info(f"  ⏰ 开盘时间戳: {opening_time}")

            self.stats["results"].append({
                "match_id": match['match_id'],
                "match_name": f"{match['home_team']} vs {match['away_team']}",
                "status": "SUCCESS",
                "init_h": init_h,
                "opening_time": opening_time,
            })

        else:
            # 捕获失败
            self.stats["failed"] += 1

            error_msg = result.get('hover_error', 'Unknown error') if result else 'No result'
            logger.info(f"  ❌ 状态: 捕获失败")
            logger.info(f"  🚫 错误信息: {error_msg}")

            self.stats["results"].append({
                "match_id": match['match_id'],
                "match_name": f"{match['home_team']} vs {match['away_team']}",
                "status": "FAILED",
                "error": error_msg,
            })

    def _generate_final_report(self):
        """生成最终报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("V64.0 授勋测试二测 - 最终报告")
        logger.info("=" * 80)

        success_rate = 100.0 * self.stats["successful"] / self.stats["total_matches"]

        logger.info(f"📈 总体成功率: {success_rate:.1f}%")
        logger.info(f"   成功: {self.stats['successful']}/{self.stats['total_matches']}")
        logger.info(f"   失败: {self.stats['failed']}/{self.stats['total_matches']}")
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
        if success_rate >= 60.0:  # 2场比赛中至少1场成功
            logger.info("")
            logger.info("🏆 授勋测试二测完成！")
            logger.info("📊 隐身能力评级: 生产级")
            logger.info(f"🎯 测试结论: {self.stats['successful']}/{self.stats['total_matches']} 场真实样本收割成功")
            logger.info("=" * 80)
        else:
            logger.warning("")
            logger.warning("⚠️  测试未达到验收标准 (60%)")
            logger.warning("🔧 建议检查 URL 有效性或优化反检测策略")
            logger.warning("=" * 80)


async def main():
    """主程序入口"""
    engine = MedalTestRound2()
    await engine.run_test()


if __name__ == "__main__":
    asyncio.run(main())
