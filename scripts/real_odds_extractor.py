#!/usr/bin/env python3
"""
V4.0: 真实赔率提取器
Real Odds Extractor - 纯金提取，拒绝任何模拟

目的: 从FotMob API中提取真实的赔率数值，不是投票调查
"""

import asyncio
import aiohttp
import json
import logging
import sys
import os
import re
from typing import Dict, Any, Optional, List

sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")

from src.api.fotmob_client import FotMobAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class RealOddsExtractor:
    """V4.0: 真实赔率提取器"""

    def __init__(self):
        logger.info("💎 V4.0 真实赔率提取器启动")
        logger.info("🎯 任务: 提取纯金赔率数值，拒绝投票调查")

    async def extract_real_odds_from_match(self, match_id: str, match_name: str) -> Dict:
        """从单场比赛提取真实赔率数值

        Args:
            match_id: 比赛ID
            match_name: 比赛名称
        """
        logger.info(f"💎 开始提取: {match_name} (ID: {match_id})")

        async with FotMobAPIClient() as client:
            # 获取完整比赛数据
            match_data = await client.get_match_details(match_id)

            if not match_data:
                return {"found": False, "error": "无法获取比赛数据"}

            # 寻找真实赔率数值 (应该是数字类型，如 2.15, 3.40 等)
            real_odds = self._find_real_odds_values(match_data)

            extraction_result = {
                "match_id": match_id,
                "match_name": match_name,
                "found": len(real_odds) > 0,
                "odds_values": real_odds,
                "raw_data_size": len(json.dumps(match_data))
            }

            if extraction_result["found"]:
                logger.info(f"🎉 成功提取 {match_name} 的真实赔率!")
                logger.info(f"💰 发现赔率数值: {len(real_odds)} 个")
                for i, odds in enumerate(real_odds[:5]):  # 显示前5个
                    logger.info(f"   {i+1}. {odds['path']}: {odds['value']}")
            else:
                logger.warning(f"⚠️ {match_name} 中未找到真实赔率数值")

            return extraction_result

    def _find_real_odds_values(self, data: Any, path: str = "") -> List[Dict]:
        """递归查找真实的赔率数值

        Args:
            data: 要搜索的数据
            path: 当前路径

        Returns:
            List[Dict]: 找到的赔率数值列表
        """
        odds_values = []

        if isinstance(data, dict):
            # 检查当前字典是否包含赔率信息
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                # 检查是否是赔率相关的键
                if self._is_odds_key(key):
                    # 如果值是数字且在合理范围内 (1.01 - 100.0)
                    if isinstance(value, (int, float)) and 1.01 <= value <= 100.0:
                        odds_values.append({
                            "path": current_path,
                            "key": key,
                            "value": value,
                            "type": "numeric_odds"
                        })
                    # 如果值是字符串，尝试解析为数字
                    elif isinstance(value, str):
                        try:
                            numeric_value = float(value)
                            if 1.01 <= numeric_value <= 100.0:
                                odds_values.append({
                                    "path": current_path,
                                    "key": key,
                                    "value": numeric_value,
                                    "type": "string_odds"
                                })
                        except ValueError:
                            pass

                # 递归搜索
                if isinstance(value, (dict, list)):
                    odds_values.extend(self._find_real_odds_values(value, current_path))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    odds_values.extend(self._find_real_odds_values(item, f"{path}[{i}]"))

        return odds_values

    def _is_odds_key(self, key: str) -> bool:
        """判断键名是否与赔率相关"""
        key_lower = key.lower()

        # 直接的赔率关键词
        odds_keywords = [
            "odds", "odd", "price", "bet", "market", "bookmaker",
            "decimal", "fractional", "american", "implied",
            "payout", "return", "stake", "wager"
        ]

        # 检查是否包含赔率关键词
        for keyword in odds_keywords:
            if keyword in key_lower:
                return True

        # 检查是否是典型的赔率值模式 (如 home_odds, away_price_1 等)
        if re.search(r'^(home|away|draw).*odds?$', key_lower):
            return True
        if re.search(r'.*(odds|price|bet)$', key_lower):
            return True

        return False

    async def extract_odds_from_multiple_matches(self):
        """从多场比赛提取真实赔率"""
        logger.info("💎 开始批量真实赔率提取")

        test_matches = [
            ("4837152", "Elche vs Real Oviedo"),
            ("4837155", "Mallorca vs Atletico Madrid"),
            ("4837156", "Rayo Vallecano vs Celta Vigo"),
            ("4837143", "Real Madrid vs Real Sociedad"),
            ("4837141", "Barcelona vs Girona")
        ]

        results = []

        for match_id, match_name in test_matches:
            try:
                result = await self.extract_real_odds_from_match(match_id, match_name)
                results.append(result)

                # 添加延迟避免API限流
                await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"❌ 提取 {match_id} 失败: {e}")
                results.append({
                    "match_id": match_id,
                    "match_name": match_name,
                    "found": False,
                    "error": str(e)
                })

        return results

    def generate_extraction_report(self, results):
        """生成赔率提取报告"""
        logger.info("💎 生成真实赔率提取报告")
        logger.info("="*80)

        matches_with_odds = [r for r in results if r["found"]]
        total_matches = len(results)

        logger.info(f"🔍 提取比赛总数: {total_matches}")
        logger.info(f"✅ 发现赔率数值: {len(matches_with_odds)}")
        logger.info(f"❌ 未发现赔率: {total_matches - len(matches_with_odds)}")
        logger.info(f"📊 发现率: {len(matches_with_odds)/total_matches*100:.1f}%")
        logger.info("")

        if matches_with_odds:
            logger.info("🎉 发现真实赔率数值的比赛:")
            total_odds_count = 0
            for result in matches_with_odds:
                odds_count = len(result.get("odds_values", []))
                total_odds_count += odds_count
                logger.info(f"   ✅ {result['match_name']}: {odds_count} 个赔率数值")

                # 显示最具代表性的赔率数值
                if result.get("odds_values"):
                    sample_odds = result["odds_values"][:3]
                    for odds in sample_odds:
                        logger.info(f"      💰 {odds['path']}: {odds['value']}")

            logger.info(f"💎 总计发现: {total_odds_count} 个真实赔率数值")
        else:
            logger.error("🚨 没有发现任何真实赔率数值!")
            logger.error("🚨 FotMob 可能不提供历史赔率数据")

        logger.info("="*80)
        return {
            "total_matches": total_matches,
            "matches_with_odds": len(matches_with_odds),
            "total_odds_values": sum(len(r.get("odds_values", [])) for r in results),
            "discovery_rate": len(matches_with_odds)/total_matches*100,
            "results": results
        }


async def main():
    """主提取程序"""
    extractor = RealOddsExtractor()

    logger.info("💎 V4.0 真实赔率提取行动开始!")
    logger.info("🎯 目标: 提取纯金赔率数值，拒绝投票调查!")

    results = await extractor.extract_odds_from_multiple_matches()
    report = extractor.generate_extraction_report(results)

    # 保存提取报告
    with open("logs/real_odds_extraction_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    logger.info("📄 提取报告已保存到 logs/real_odds_extraction_report.json")

    if report["matches_with_odds"] == 0:
        logger.error("🚨 V4.0 结论: FotMob 不提供历史赔率数值!")
        logger.error("🚨 我们需要寻找其他数据源或承认现实约束!")
    else:
        logger.info(f"🎉 V4.0 成功: 找到 {report['total_odds_values']} 个真实赔率数值!")


if __name__ == "__main__":
    asyncio.run(main())