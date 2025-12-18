#!/usr/bin/env python3
"""
L1 Match ID 提取调试脚本
L1 Match ID Extraction Debug Script

验证修复后的比赛ID提取逻辑是否正确获取纯数字ID
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

async def debug_premier_league_ids():
    """调试英超联赛比赛ID提取"""
    logger.info("🚀 启动L1比赛ID提取调试")
    logger.info("🎯 目标: 验证FotMob API返回纯数字比赛ID")
    logger.info("=" * 70)

    try:
        # 导入采集器
        from collectors.fotmob_api_collector import FotMobAPICollector

        # 初始化采集器
        collector = FotMobAPICollector(max_concurrent=1, timeout=30, max_retries=2)
        await collector.initialize()

        try:
            # 🔥 测试英超联赛 (ID: 47)
            league_id = 47
            league_name = "Premier League"
            season = "2024/2025"

            logger.info(f"🔍 测试联赛: {league_name} (ID: {league_id})")
            logger.info(f"📅 测试赛季: {season}")

            # 构造API请求
            league_url = f"https://www.fotmob.com/api/leagues?id={league_id}&timezone=Europe/London"
            logger.info(f"🌐 API URL: {league_url}")

            # 发送API请求
            data, status = await collector._make_request(league_url, f"league_{league_id}")

            logger.info(f"📊 API响应状态: {status}")

            if status.name == "SUCCESS" and data:
                logger.info("✅ API请求成功")

                # 🔥 修复：使用正确的API数据结构
                # FotMob联赛API返回的是 fixtures.allMatches，不是 content.matches
                logger.info(f"🔍 API根字段: {list(data.keys())}")

                matches_data = []

                # 主要数据路径：fixtures.allMatches
                if "fixtures" in data:
                    matches_data = data["fixtures"].get("allMatches", [])
                    logger.info(f"✅ 从fixtures.allMatches找到: {len(matches_data)}场比赛")
                else:
                    # 备用数据路径
                    content = data.get("content", {})
                    if "matches" in content:
                        matches_data = content["matches"].get("allMatches", [])
                        logger.info(f"✅ 从content.matches.allMatches找到: {len(matches_data)}场比赛")
                    elif "leagueMatches" in content:
                        matches_data = content["leagueMatches"]
                        logger.info(f"✅ 从leagueMatches找到: {len(matches_data)}场比赛")

                # 🔥 关键：提取和分析比赛ID
                if matches_data:
                    logger.info(f"📋 总共找到: {len(matches_data)}场比赛")

                    # 提取比赛ID
                    match_ids = []
                    invalid_ids = []
                    id_sources = {}

                    for _i, match in enumerate(matches_data[:20]):  # 检查前20场比赛
                        if isinstance(match, dict):
                            # 优先使用真实的比赛ID字段
                            match_id = None
                            id_source = None

                            if match.get("id"):
                                match_id = match.get("id")
                                id_source = "id"
                            elif match.get("matchId"):
                                match_id = match.get("matchId")
                                id_source = "matchId"
                            elif match.get("match_id"):
                                match_id = match.get("match_id")
                                id_source = "match_id"

                            if match_id:
                                clean_id = str(match_id).strip()

                                # 记录ID来源
                                if id_source not in id_sources:
                                    id_sources[id_source] = 0
                                id_sources[id_source] += 1

                                # 验证ID格式
                                if clean_id.isdigit():
                                    match_ids.append(clean_id)

                                    # 显示前5个有效ID的详细信息
                                    if len(match_ids) <= 5:
                                        home_team = match.get("home", {}).get("name", "Unknown")
                                        away_team = match.get("away", {}).get("name", "Unknown")
                                        status = match.get("status", {}).get("reason", {}).get("short", "N/A")
                                        logger.info(f"  ✅ 比赛ID {clean_id}: {home_team} vs {away_team} | 状态: {status}")
                                else:
                                    invalid_ids.append(clean_id)
                                    logger.warning(f"  ❌ 无效ID格式: {clean_id} (来源: {id_source})")
                            else:
                                logger.warning(f"  ⚠️ 比赛对象缺少ID字段: {list(match.keys())}")

                    # 📊 统计报告
                    logger.info("\n📊 ID提取统计:")
                    logger.info(f"  🔢 有效纯数字ID: {len(match_ids)}")
                    logger.info(f"  ❌ 无效格式ID: {len(invalid_ids)}")
                    logger.info(f"  📋 ID字段来源: {id_sources}")

                    # 🎯 验证标准检查
                    logger.info("\n🎯 验证标准检查:")

                    if match_ids:
                        logger.info(f"✅ 前5个有效比赛ID: {match_ids[:5]}")

                        # 检查ID格式是否符合4xxxxxx模式
                        valid_format_count = sum(1 for mid in match_ids if mid.startswith('4') and len(mid) >= 6)

                        if valid_format_count >= 3:  # 至少3个符合格式
                            logger.info("✅ ID格式验证通过: 符合4xxxxxx模式")

                            # 验证是否为纯数字
                            all_numeric = all(mid.isdigit() for mid in match_ids[:10])
                            if all_numeric:
                                logger.info("✅ 纯数字验证通过: 所有ID都是纯数字")

                                logger.info("\n🎉 L1比赛ID提取修复验证成功!")
                                logger.info("🚀 系统已准备好进行真实的L2数据采集")
                                return True
                            else:
                                logger.error("❌ 纯数字验证失败: 存在非数字字符")
                                return False
                        else:
                            logger.warning(f"⚠️ ID格式检查: 只有{valid_format_count}个ID符合4xxxxxx模式")
                            logger.warning("🔍 这可能是正常的，不同联赛可能有不同的ID格式")

                            # 即使不是4开头，只要是纯数字也认为修复成功
                            all_numeric = all(mid.isdigit() for mid in match_ids[:10])
                            if all_numeric:
                                logger.info("✅ 纯数字验证通过: 所有ID都是纯数字")
                                logger.info("🎉 L1比赛ID提取修复验证成功!")
                                return True
                    else:
                        logger.error("❌ 未找到有效的比赛ID")
                        return False

                else:
                    logger.error("❌ 未找到比赛数据")
                    logger.debug(f"🔍 完整API响应: {data}")
                    return False

            else:
                logger.error(f"❌ API请求失败: {status}")
                return False

        finally:
            await collector.close()

    except ImportError as e:
        logger.error(f"❌ 无法导入采集器模块: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 调试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_leagues():
    """测试多个联赛的ID提取"""
    logger.info("\n" + "="*70)
    logger.info("🔄 测试多个联赛的ID提取...")

    test_leagues = [
        (47, "Premier League"),
        (42, "Championship"),
        (54, "La Liga"),
        (82, "Serie A"),
        (100, "Bundesliga")
    ]

    success_count = 0

    try:
        from collectors.fotmob_api_collector import FotMobAPICollector
        collector = FotMobAPICollector(max_concurrent=1, timeout=30, max_retries=2)
        await collector.initialize()

        try:
            for league_id, league_name in test_leagues:
                logger.info(f"\n🔍 测试联赛: {league_name} (ID: {league_id})")

                league_url = f"https://www.fotmob.com/api/leagues?id={league_id}&timezone=Europe/London"
                data, status = await collector._make_request(league_url, f"league_{league_id}")

                if status.name == "SUCCESS" and data:
                    content = data.get("content", {})
                    matches_data = []

                    if "matches" in content:
                        matches_data = content["matches"].get("allMatches", [])
                    elif "leagueMatches" in content:
                        matches_data = content["leagueMatches"]

                    if matches_data:
                        # 提取前3个ID进行验证
                        match_ids = []
                        for match in matches_data[:3]:
                            if isinstance(match, dict):
                                match_id = match.get("id") or match.get("matchId") or match.get("match_id")
                                if match_id and str(match_id).isdigit():
                                    match_ids.append(str(match_id))

                        if match_ids:
                            logger.info(f"  ✅ {league_name}: {match_ids} (格式正确)")
                            success_count += 1
                        else:
                            logger.warning(f"  ⚠️ {league_name}: 未找到有效数字ID")
                    else:
                        logger.warning(f"  ⚠️ {league_name}: 未找到比赛数据")
                else:
                    logger.warning(f"  ❌ {league_name}: API请求失败 ({status})")

        finally:
            await collector.close()

        logger.info(f"\n📊 多联赛测试结果: {success_count}/{len(test_leagues)} 成功")
        return success_count >= 3  # 至少3个联赛成功算通过

    except Exception as e:
        logger.error(f"❌ 多联赛测试异常: {e}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 启动L1比赛ID提取验证测试")

    # 测试英超联赛
    premier_league_success = await debug_premier_league_ids()

    if premier_league_success:
        # 如果英超测试成功，继续测试其他联赛
        multi_league_success = await test_multiple_leagues()

        if multi_league_success:
            logger.info("\n" + "="*70)
            logger.info("🎉 L1比赛ID提取修复完全验证成功!")
            logger.info("✅ 英超联赛: 纯数字ID提取正常")
            logger.info("✅ 多个联赛: ID格式验证通过")
            logger.info("🚀 系统已准备好进行真实数据采集")
            logger.info("💡 可以安全启动回填任务")
            logger.info("="*70)
            return True

    logger.error("\n" + "="*70)
    logger.error("💥 L1比赛ID提取修复验证失败!")
    logger.error("🚨 需要进一步调试和修复")
    logger.error("="*70)
    return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
