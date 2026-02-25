#!/usr/bin/env python3
"""
V39.1 坏账活体清零 - 重新搜索 4 场坏账

使用 V39.1 双重校验逻辑重新搜索这 4 场比赛：
1. 3610233 - Manchester United vs Leicester (2022-04-02)
2. 4193541 - Aston Villa vs West Ham (2023-10-22)
3. 3901018 - Liverpool vs Brighton (2022-10-01)
4. 3900954 - Everton vs Nottingham Forest (2022-08-20)

目的：证明是之前映射错了，还是页面真没赔率

Author: 首席数据采集官 & 算法专家
Version: V39.1 Bad Debt Rehunt
Date: 2026-01-12
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.scrapers.oddsportal import OddsPortalScraper


# ============================================================================
# 4 场坏账数据
# ============================================================================

BAD_DEBT_MATCHES = [
    {
        "match_id": "3610233",
        "home_team": "Manchester United",
        "away_team": "Leicester City",
        "league_name": "Premier League",
        "match_date": "2022-04-02",
        "previous_url": None,
        "previous_method": "manual"
    },
    {
        "match_id": "4193541",
        "home_team": "Aston Villa",
        "away_team": "West Ham United",
        "league_name": "Premier League",
        "match_date": "2023-10-22",
        "previous_url": None,
        "previous_method": "manual"
    },
    {
        "match_id": "3901018",
        "home_team": "Liverpool",
        "away_team": "Brighton & Hove Albion",
        "league_name": "Premier League",
        "match_date": "2022-10-01",
        "previous_url": None,
        "previous_method": "manual"
    },
    {
        "match_id": "3900954",
        "home_team": "Everton",
        "away_team": "Nottingham Forest",
        "league_name": "Premier League",
        "match_date": "2022-08-20",
        "previous_url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/nottingham-luton-tC3uVymm/",
        "previous_method": "levenshtein"
    },
]


# ============================================================================
# 重新搜索函数
# ============================================================================

async def rehunt_bad_debt_match(
    match_data: dict,
    scraper: OddsPortalScraper
) -> dict:
    """
    使用 V39.1 双重校验逻辑重新搜索单场坏账

    Args:
        match_data: 比赛数据
        scraper: OddsPortalScraper 实例

    Returns:
        搜索结果
    """
    from scripts.ops.hunt_league_hashes_v39 import multi_source_search

    home_team = match_data["home_team"]
    away_team = match_data["away_team"]
    league_name = match_data["league_name"]

    print(f"\n{'=' * 70}")
    print(f"重新搜索: {home_team} vs {away_team} ({league_name})")
    print(f"Match ID: {match_data['match_id']}")
    print(f"比赛日期: {match_data['match_date']}")
    print(f"之前 URL: {match_data['previous_url']}")
    print(f"之前方法: {match_data['previous_method']}")
    print(f"{'=' * 70}")

    # 使用 V39.1 多源搜索（包含双重校验）
    result = await multi_source_search(
        home_team=home_team,
        away_team=away_team,
        league_hint=league_name,
        scraper=scraper
    )

    return result


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('logs/v39_1_bad_debt_rehunt.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("V39.1 坏账活体清零 - 重新搜索 4 场坏账")
    logger.info("=" * 70)

    # 初始化 Scraper
    scraper = OddsPortalScraper()

    results = []

    for i, match in enumerate(BAD_DEBT_MATCHES, 1):
        logger.info(f"\n[{i}/4] 开始处理...")

        try:
            result = await rehunt_bad_debt_match(match, scraper)
            results.append({
                "match_id": match["match_id"],
                "match": match,
                "result": result
            })

            # 延迟（除了最后一场）
            if i < len(BAD_DEBT_MATCHES):
                logger.info("⏳ 等待 3.0s 后继续...")
                await asyncio.sleep(3.0)

        except Exception as e:
            logger.error(f"❌ 异常: {e}")
            results.append({
                "match_id": match["match_id"],
                "match": match,
                "result": {"success": False, "error": str(e)}
            })

    # 汇报结果
    logger.info("\n" + "=" * 70)
    logger.info("📊 V39.1 坏账活体清零结果报告")
    logger.info("=" * 70)

    success_count = 0
    failed_count = 0

    for i, item in enumerate(results, 1):
        match_id = item["match_id"]
        match = item["match"]
        result = item["result"]

        logger.info(f"\n[{i}] Match ID: {match_id}")
        logger.info(f"    对阵: {match['home_team']} vs {match['away_team']}")

        if result.get("success"):
            logger.info(f"    ✅ 搜索成功!")
            logger.info(f"    URL: {result.get('url')}")
            logger.info(f"    置信度: {result.get('confidence', 0):.1f}%")
            logger.info(f"    方法: {result.get('method')}")
            success_count += 1
        else:
            logger.info(f"    ❌ 搜索失败")
            logger.info(f"    原因: {result.get('error', '未知错误')}")
            failed_count += 1

    logger.info("\n" + "=" * 70)
    logger.info(f"总计: {len(results)} 场")
    logger.info(f"成功: {success_count} 场")
    logger.info(f"失败: {failed_count} 场")
    logger.info("=" * 70)

    # 返回状态码
    sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
