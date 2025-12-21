#!/usr/bin/env python3
"""
V4.0: 真实赔率取证脚本
Real Odds Investigation Script - 拒绝模拟只要纯金！

目的: 物理取证FotMob API中的真实赔率数据，拆穿所有模拟器假象
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")

from src.api.fotmob_client import FotMobAPIClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class RealOddsInvestigator:
    """V4.0: 真实赔率取证员"""

    def __init__(self):
        logger.info("🕵️ V4.0 真实赔率取证员启动")
        logger.info("🎯 任务: 拆穿模拟器，找到纯金真实赔率")

    async def investigate_match(self, match_id: str, match_name: str) -> dict:
        """深度调查单场比赛的真实赔率数据

        Args:
            match_id: 比赛ID
            match_name: 比赛名称描述
        """
        logger.info(f"🔍 开始调查: {match_name} (ID: {match_id})")

        async with FotMobAPIClient() as client:
            # 获取完整比赛数据
            match_data = await client.get_match_details(match_id)

            if not match_data:
                logger.error(f"❌ 无法获取比赛 {match_id} 的数据")
                return {"found": False, "error": "无法获取比赛数据"}

            investigation_result = {
                "match_id": match_id,
                "match_name": match_name,
                "found": False,
                "raw_data": match_data,
                "betting_modules": []
            }

            # 第一步: 深度扫描所有可能的赔率字段
            logger.info("📡 深度扫描赔率相关字段...")

            # 方法1: 直接扫描 betting 模块
            if "betting" in match_data:
                logger.info("✅ 发现 'betting' 模块!")
                investigation_result["betting_modules"].append({
                    "module": "betting",
                    "data": match_data["betting"],
                    "type": type(match_data["betting"]).__name__
                })

            # 方法2: 扫描所有可能包含赔率的字段
            potential_odds_fields = [
                "odds", "bettingOdds", "bookmakerOdds", "marketOdds",
                "averageOdds", "prematchOdds", "liveOdds",
                "homeOdds", "awayOdds", "drawOdds",
                "bettingOffers", "bettingData", "priceData"
            ]

            for field in potential_odds_fields:
                if field in match_data:
                    logger.info(f"✅ 发现字段: '{field}'")
                    investigation_result["betting_modules"].append({
                        "module": field,
                        "data": match_data[field],
                        "type": type(match_data[field]).__name__
                    })

            # 方法3: 递归扫描整个JSON寻找任何包含赔率信息的内容
            def find_odds_in_json(obj, path=""):
                odds_info = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key

                        # 检查key是否包含赔率相关词汇
                        if any(word in key.lower() for word in
                           ['odds', 'bet', 'price', 'market', 'bookmaker', 'wager']):
                            odds_info.append({
                                "path": current_path,
                                "key": key,
                                "data": value,
                                "type": type(value).__name__
                            })

                        # 递归搜索
                        if isinstance(value, (dict, list)):
                            odds_info.extend(find_odds_in_json(value, current_path))

                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            odds_info.extend(find_odds_in_json(item, f"{path}[{i}]"))

                return odds_info

            all_odds_info = find_odds_in_json(match_data)
            if all_odds_info:
                logger.info(f"✅ 深度扫描发现 {len(all_odds_info)} 个赔率相关数据点!")
                investigation_result["deep_scan_results"] = all_odds_info

            # 判断是否找到真实赔率
            has_real_odds = (
                len(investigation_result["betting_modules"]) > 0 or
                len(all_odds_info) > 0
            )

            investigation_result["found"] = has_real_odds

            if has_real_odds:
                logger.info(f"🎉 在 {match_name} 中发现真实赔率数据!")
                logger.info(f"📊 赔率模块数量: {len(investigation_result['betting_modules'])}")
                logger.info(f"🔍 深度扫描数据点: {len(all_odds_info)}")
            else:
                logger.error(f"❌ {match_name} 中未发现任何真实赔率数据!")
                logger.error("🚨 这证实了我们的怀疑: FotMob 历史数据确实不包含赔率!")

            return investigation_result

    async def investigate_multiple_matches(self):
        """调查多场比赛的真实赔率情况"""
        logger.info("🌍 开始大规模真实赔率调查")

        # 使用数据库中真实的比赛ID进行调查
        test_matches = [
            ("4837152", "Elche vs Real Oviedo"),
            ("4837155", "Mallorca vs Atletico Madrid"),
            ("4837156", "Rayo Vallecano vs Celta Vigo"),
            ("4837154", "Valencia vs Athletic Club"),
            ("4837149", "Deportivo Alaves vs Sevilla"),
            ("4837143", "Real Madrid vs Real Sociedad"),
            ("4837141", "Barcelona vs Girona"),
            ("4837139", "Villarreal vs Real Betis"),
            ("4837134", "Athletic Bilbao vs Osasuna"),
            ("4837137", "Getafe vs Almeria")
        ]

        results = []

        for match_id, match_name in test_matches:
            try:
                result = await self.investigate_match(match_id, match_name)
                results.append(result)

                # 添加延迟避免API限流
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ 调查 {match_id} 失败: {e}")
                results.append({
                    "match_id": match_id,
                    "match_name": match_name,
                    "found": False,
                    "error": str(e)
                })

        return results

    def generate_investigation_report(self, results):
        """生成取证报告"""
        logger.info("📋 生成真实赔率取证报告")
        logger.info("="*80)

        found_count = sum(1 for r in results if r["found"])
        total_count = len(results)

        logger.info(f"🔍 调查比赛总数: {total_count}")
        logger.info(f"✅ 发现赔率数据: {found_count}")
        logger.info(f"❌ 未发现赔率: {total_count - found_count}")
        logger.info(f"📊 发现率: {found_count/total_count*100:.1f}%")
        logger.info("")

        if found_count > 0:
            logger.info("🎉 发现真实赔率的比赛:")
            for result in results:
                if result["found"]:
                    logger.info(f"   ✅ {result['match_name']} (ID: {result['match_id']})")
                    for module in result.get("betting_modules", []):
                        logger.info(f"      • {module['module']}: {module['type']}")
        else:
            logger.error("🚨 重大发现: 所有调查的比赛都没有真实赔率数据!")
            logger.error("🚨 这完全证实了项目经理的怀疑!")
            logger.error("🚨 V3.3所谓的'脱水模拟赔率'完全是自欺欺人!")

        logger.info("="*80)
        return {
            "total_investigated": total_count,
            "real_odds_found": found_count,
            "discovery_rate": found_count/total_count*100,
            "results": results
        }


async def main():
    """主取证程序"""
    investigator = RealOddsInvestigator()

    logger.info("🚀 V4.0 真实赔率取证行动开始!")
    logger.info("🎯 目标: 找到1克纯金真实赔率，拒绝所有模拟器!")

    results = await investigator.investigate_multiple_matches()
    report = investigator.generate_investigation_report(results)

    # 保存取证报告
    with open("logs/real_odds_investigation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info("📄 取证报告已保存到 logs/real_odds_investigation_report.json")

    if report["real_odds_found"] == 0:
        logger.error("🚨 V4.0 取证结论: FotMob 历史数据完全不包含赔率信息!")
        logger.error("🚨 我们需要寻找替代数据源: betexplorer.com, oddsportal.com 等")
        logger.error("🚨 或者承认: 历史真实赔率数据在商业上几乎不可获取!")
    else:
        logger.info("🎉 V4.0 取证成功: 找到了真实赔率数据!")


if __name__ == "__main__":
    asyncio.run(main())