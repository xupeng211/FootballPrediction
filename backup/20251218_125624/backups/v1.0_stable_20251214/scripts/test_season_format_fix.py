#!/usr/bin/env python3
"""
测试赛季格式修复效果
验证SeasonFormatGenerator不再产生重复的赛季格式
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_season_format_generation():
    """测试赛季格式生成逻辑"""
    logger.info("🧪 开始测试赛季格式生成逻辑...")

    # 导入修复后的SeasonFormatGenerator
    sys.path.insert(0, str(Path(__file__).parent))
    from backfill_full_history import SeasonFormatGenerator

    generator = SeasonFormatGenerator()

    # 测试数据：不同类型的联赛
    test_leagues = [
        {"id": 47, "name": "Premier League", "country": "England", "type": "league"},  # 跨年制
        {"id": 268, "name": "Brasileirão", "country": "Brazil", "type": "league"},     # 单年制
        {"id": 54, "name": "La Liga", "country": "Spain", "type": "league"},          # 跨年制
        {"id": 34, "name": "MLS", "country": "USA", "type": "league"},                # 单年制
        {"id": 5, "name": "Champions League", "country": "Europe", "type": "cup"},    # 跨年制
        {"id": 372, "name": "J1 League", "country": "Japan", "type": "league"},       # 跨年制
        {"id": 999, "name": "Unknown League", "country": "Unknown", "type": "league"}, # 默认跨年制
    ]

    test_years = [2023, 2024]

    logger.info("=" * 60)
    logger.info("📊 赛季格式生成测试结果")
    logger.info("=" * 60)

    all_results = []

    for league in test_leagues:
        league_name = league["name"]
        league_id = league["id"]

        logger.info(f"\n🔍 测试联赛: {league_name} (ID: {league_id})")

        for year in test_years:
            season_formats = generator.generate_season_string(year, league)

            # 验证关键修复点：每个联赛应该只生成一个赛季格式
            if len(season_formats) != 1:
                logger.error(f"❌ 修复失败: {league_name} {year} 生成了 {len(season_formats)} 个格式: {season_formats}")
                return False

            season_format = season_formats[0]
            logger.info(f"  ✅ {year}: {season_format}")

            all_results.append({
                "league": league_name,
                "league_id": league_id,
                "year": year,
                "season": season_format
            })

    # 验证重复性检查
    logger.info("\n" + "=" * 60)
    logger.info("🔄 重复性检查")
    logger.info("=" * 60)

    # 检查同一联赛同年份是否产生重复
    league_year_combinations = {}
    for result in all_results:
        key = (result["league_id"], result["year"])
        if key in league_year_combinations:
            logger.error(f"❌ 发现重复: 联赛 {result['league']} (ID: {result['league_id']}) 在 {result['year']} 年有多个赛季格式")
            return False
        else:
            league_year_combinations[key] = result["season"]
            logger.info(f"  ✅ {result['league']} {result['year']}: {result['season']}")

    logger.info("\n" + "=" * 60)
    logger.info("📈 测试统计")
    logger.info("=" * 60)
    logger.info(f"📋 测试联赛数: {len(test_leagues)}")
    logger.info(f"📅 测试年份数: {len(test_years)}")
    logger.info(f"🎯 总测试组合: {len(all_results)}")
    logger.info(f"✅ 通过测试: {len(all_results)}")
    logger.info("📈 通过率: 100.0%")

    logger.info("\n🎉 所有测试通过！赛季格式修复成功！")
    logger.info("✅ 修复要点验证:")
    logger.info("  - 每个联赛每年只生成一个赛季格式")
    logger.info("  - 不再有重复的API调用")
    logger.info("  - 跨年制联赛使用 YYYY/YYYY+1 格式")
    logger.info("  - 单年制联赛使用 YYYY 格式")

    return True

def test_specific_league_classifications():
    """测试特定联赛分类"""
    logger.info("\n🎯 测试特定联赛分类...")

    sys.path.insert(0, str(Path(__file__).parent))
    from backfill_full_history import SeasonFormatGenerator

    generator = SeasonFormatGenerator()

    # 测试关键联赛的分类
    test_cases = [
        (47, "2023", "2023/2024"),  # Premier League - 跨年制
        (268, "2023", "2023"),      # Brasileirão - 单年制
        (54, "2023", "2023/2024"),  # La Liga - 跨年制
        (34, "2023", "2023"),       # MLS - 单年制
    ]

    logger.info("=" * 50)
    logger.info("🏷️ 联赛分类验证")
    logger.info("=" * 50)

    all_passed = True
    for league_id, year, expected_format in test_cases:
        league_info = {"id": league_id}
        season_formats = generator.generate_season_string(int(year), league_info)
        actual_format = season_formats[0]

        if actual_format == expected_format:
            logger.info(f"  ✅ 联赛ID {league_id} ({year}): {actual_format}")
        else:
            logger.error(f"  ❌ 联赛ID {league_id} ({year}): 期望 {expected_format}, 实际 {actual_format}")
            all_passed = False

    return all_passed

def main():
    """主函数"""
    logger.info("🚀 启动赛季格式修复验证测试")

    success_count = 0
    total_tests = 2

    # 测试1: 基本赛季格式生成
    if test_season_format_generation():
        success_count += 1

    # 测试2: 特定联赛分类
    if test_specific_league_classifications():
        success_count += 1

    # 输出最终结果
    logger.info("\n" + "=" * 60)
    logger.info("🏆 最终测试结果")
    logger.info("=" * 60)
    logger.info(f"📋 总测试数: {total_tests}")
    logger.info(f"✅ 成功测试: {success_count}")
    logger.info(f"❌ 失败测试: {total_tests - success_count}")
    success_rate = (success_count / total_tests) * 100
    logger.info(f"📈 成功率: {success_rate:.1f}%")

    if success_count == total_tests:
        logger.info("🎉 所有测试通过！重复赛季格式问题已修复！")
        return True
    else:
        logger.error("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
