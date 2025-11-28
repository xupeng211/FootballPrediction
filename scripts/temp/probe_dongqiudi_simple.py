#!/usr/bin/env python3
"""
🕵️‍♂️ 懂球帝简化探测脚本

使用已知的比赛ID和简单的请求方式探测数据结构
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any

import httpx

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DongqiudiSimpleProbe:
    """懂球帝简化探测器"""

    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                "Referer": "https://m.dongqiudi.com/",
            },
        )

        # 使用一些可能的比赛ID（英超、西甲等热门比赛的ID格式）
        self.test_match_ids = [
            "1337424",  # 示例ID
            "1337425",
            "1337426",
            "1337427",
            "1337428",
            # 尝试一些常见的ID格式
            "123456",
            "654321",
            "999999",
        ]

    async def probe_single_match(self, match_id: str) -> dict:
        """探测单个比赛的详细信息"""
        logger.info(f"🔍 探测比赛ID: {match_id}")

        # 懂球帝可能的端点
        endpoints = [
            f"https://m.dongqiudi.com/api/match/detail?id={match_id}",
            f"https://dongqiudi.com/api/match/detail?id={match_id}",
            f"https://m.dongqiudi.com/data/{match_id}.json",
            f"https://dongqiudi.com/data/{match_id}.json",
        ]

        results = []

        for endpoint in endpoints:
            try:
                logger.info(f"  尝试: {endpoint}")
                response = await self.session.get(endpoint)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        analysis = self._analyze_response(data)
                        results.append(
                            {
                                "endpoint": endpoint,
                                "status": "success",
                                "data": data,
                                "analysis": analysis,
                            }
                        )
                        logger.info("  ✅ 成功获取数据")

                    except json.JSONDecodeError:
                        # 检查是否是HTML页面
                        if "<html" in response.text:
                            logger.info("  🌐 返回HTML页面，可能包含数据")
                            # 尝试从HTML中提取JSON
                            json_data = self._extract_json_from_html(response.text)
                            if json_data:
                                analysis = self._analyze_response(json_data)
                                results.append(
                                    {
                                        "endpoint": endpoint,
                                        "status": "html_with_json",
                                        "data": json_data,
                                        "analysis": analysis,
                                    }
                                )
                                logger.info("  ✅ 从HTML提取到JSON数据")
                        else:
                            logger.info("  ❓ 非JSON响应")

                elif response.status_code == 403:
                    logger.info("  🚫 访问被拒绝")
                elif response.status_code == 404:
                    logger.info("  ❌ 不存在")
                else:
                    logger.info(f"  ⚠️ 状态码: {response.status_code}")

            except Exception as e:
                logger.info(f"  ❌ 请求失败: {e}")

        return {"match_id": match_id, "results": results, "has_data": len(results) > 0}

    def _extract_json_from_html(self, html: str) -> dict | None:
        """从HTML中提取JSON数据"""
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
            r"window\.__NUXT__\s*=\s*({.*?});",
            r"window\.matchData\s*=\s*({.*?});",
            r"data-match-id=.*?data-json=\'({.*?})\'",
            r"json-data\s*=\s*({.+?})(?=\s*[;\">])",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    return data
                except json.JSONDecodeError:
                    continue

        return None

    def _analyze_response(self, data: Any) -> dict:
        """分析响应数据"""
        analysis = {
            "is_match_data": False,
            "has_xg": False,
            "has_lineup": False,
            "has_stats": False,
            "data_keys": [],
            "sample_structure": {},
        }

        if not isinstance(data, dict):
            return analysis

        analysis["data_keys"] = list(data.keys())[:10]

        # 检查是否包含比赛相关键
        match_keys = ["match", "game", "fixture", "比赛", "赛事"]
        if any(key in str(data).lower() for key in match_keys):
            analysis["is_match_data"] = True

        # 递归搜索xG数据
        def search_xg(obj, depth=0):
            if depth > 5:  # 限制搜索深度
                return False

            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(
                        xg_term in str(key).lower()
                        for xg_term in ["xg", "expected_goal", "期望进球"]
                    ):
                        return True
                    if search_xg(value, depth + 1):
                        return True
            elif isinstance(obj, list):
                for item in obj:
                    if search_xg(item, depth + 1):
                        return True
            return False

        # 搜索阵容数据
        def search_lineup(obj, depth=0):
            if depth > 5:
                return False

            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(
                        lineup_term in str(key).lower()
                        for lineup_term in ["lineup", "formation", "首发", "players"]
                    ):
                        return True
                    if search_lineup(value, depth + 1):
                        return True
            elif isinstance(obj, list):
                for item in obj:
                    if search_lineup(item, depth + 1):
                        return True
            return False

        # 搜索统计数据
        def search_stats(obj, depth=0):
            if depth > 5:
                return False

            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(
                        stat_term in str(key).lower()
                        for stat_term in [
                            "statistic",
                            "technical",
                            "possession",
                            "射门",
                            "控球",
                        ]
                    ):
                        return True
                    if search_stats(value, depth + 1):
                        return True
            elif isinstance(obj, list):
                for item in obj:
                    if search_stats(item, depth + 1):
                        return True
            return False

        # 执行搜索
        analysis["has_xg"] = search_xg(data)
        analysis["has_lineup"] = search_lineup(data)
        analysis["has_stats"] = search_stats(data)

        # 显示数据结构样本
        if isinstance(data, dict):
            for key, value in list(data.items())[:5]:
                if isinstance(value, (dict, list)):
                    analysis["sample_structure"][key] = type(value).__name__
                else:
                    str_val = str(value)
                    analysis["sample_structure"][key] = (
                        str_val[:50] + "..." if len(str_val) > 50 else str_val
                    )

        return analysis

    async def run_probe(self):
        """运行探测流程"""
        logger.info("🚀 开始懂球帝简化探测")

        successful_probes = []

        for match_id in self.test_match_ids:
            result = await self.probe_single_match(match_id)

            if result["has_data"]:
                successful_probes.append(result)
                logger.info(f"✅ 比赛 {match_id} 有可用数据")

                # 如果找到数据，打印详细信息
                for res in result["results"]:
                    analysis = res["analysis"]
                    logger.info("  📊 数据分析:")
                    logger.info(
                        f"    - 比赛数据: {'✅' if analysis['is_match_data'] else '❌'}"
                    )
                    logger.info(f"    - xG数据: {'✅' if analysis['has_xg'] else '❌'}")
                    logger.info(
                        f"    - 阵容数据: {'✅' if analysis['has_lineup'] else '❌'}"
                    )
                    logger.info(
                        f"    - 技术统计: {'✅' if analysis['has_stats'] else '❌'}"
                    )

                    if analysis["data_keys"]:
                        logger.info(
                            f"    - 数据键: {', '.join(analysis['data_keys'][:5])}"
                        )

            else:
                logger.info(f"❌ 比赛 {match_id} 无可用数据")

        await self.session.aclose()

        # 打印总结
        self.print_summary(successful_probes)

        return successful_probes

    def print_summary(self, successful_probes: list[dict]):
        """打印探测总结"""
        logger.info("\n" + "=" * 60)
        logger.info("🎯 懂球帝探测总结")
        logger.info("=" * 60)

        total_matches = len(successful_probes)
        matches_with_xg = 0
        matches_with_lineup = 0
        matches_with_stats = 0

        for probe in successful_probes:
            for result in probe["results"]:
                analysis = result["analysis"]
                if analysis["has_xg"]:
                    matches_with_xg += 1
                if analysis["has_lineup"]:
                    matches_with_lineup += 1
                if analysis["has_stats"]:
                    matches_with_stats += 1

        logger.info("📊 探测结果:")
        logger.info(f"  • 有数据的比赛: {total_matches}")
        logger.info(f"  • 包含xG的接口: {matches_with_xg}")
        logger.info(f"  • 包含阵容的接口: {matches_with_lineup}")
        logger.info(f"  • 包含统计的接口: {matches_with_stats}")

        logger.info("\n🎯 结论:")
        if matches_with_xg > 0:
            logger.info("  ✅ 懂球帝包含xG数据!")
        else:
            logger.info("  ❌ 未发现懂球帝xG数据")

        if matches_with_lineup > 0:
            logger.info("  ✅ 懂球帝包含阵容数据!")
        else:
            logger.info("  ❌ 未发现懂球帝阵容数据")

        if matches_with_stats > 0:
            logger.info("  ✅ 懂球帝包含技术统计!")
        else:
            logger.info("  ❌ 未发现懂球帝技术统计")


async def main():
    """主函数"""
    probe = DongqiudiSimpleProbe()
    results = await probe.run_probe()


if __name__ == "__main__":
    asyncio.run(main())
