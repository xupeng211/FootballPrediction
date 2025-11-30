#!/usr/bin/env python3
"""
🕵️‍♂️ 懂球帝深度探测脚本 v2.0

专注探测懂球帝的实际数据结构，特别寻找 xG 和阵容数据
使用真实的比赛 ID 进行详情接口探测
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any

import httpx
from curl_cffi import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DongqiudiDeepProbe:
    """懂球帝深度探测器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://m.dongqiudi.com/",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    async def extract_real_match_data(self):
        """从懂球帝网页提取真实的比赛数据"""
        logger.info("🌐 从懂球帝主页提取真实比赛数据...")

        urls = ["https://m.dongqiudi.com/", "https://dongqiudi.com/"]

        for url in urls:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    html = response.text

                    # 查找所有可能的 JSON 数据
                    json_patterns = [
                        r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
                        r"window\.__NUXT__\s*=\s*({.*?});",
                        r"window\.g_config\s*=\s*({.*?});",
                        r"var\s+matchData\s*=\s*({.*?});",
                        r"const\s+matchList\s*=\s*({.*?});",
                    ]

                    for pattern in json_patterns:
                        matches = re.findall(pattern, html, re.DOTALL)
                        for match_json in matches:
                            try:
                                data = json.loads(match_json)
                                matches_info = self._extract_matches_from_json(data)
                                if matches_info:
                                    logger.info(
                                        f"✅ 从 {url} 提取到 {len(matches_info)} 场比赛"
                                    )
                                    return matches_info
                            except json.JSONDecodeError:
                                continue

                    # 直接在 HTML 中查找比赛相关的链接和ID
                    match_id_pattern = r"/data/(\d+)\.html"
                    match_ids = re.findall(match_id_pattern, html)
                    if match_ids:
                        logger.info(f"🎯 在页面中找到 {len(set(match_ids))} 个比赛ID")
                        return [
                            {"id": mid, "source": "html_link"}
                            for mid in set(match_ids[:10])
                        ]

            except Exception:
                logger.error(f"访问 {url} 失败: {e}")
                continue

        return None

    def _extract_matches_from_json(self, data: Any) -> list[dict]:
        """从JSON数据中提取比赛信息"""
        matches = []

        def find_objects_with_key(obj, target_keys):
            """递归查找包含目标键的对象"""
            found = []

            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(
                        target_key in str(key).lower() for target_key in target_keys
                    ):
                        found.append(obj)
                    elif isinstance(value, (dict, list)):
                        found.extend(find_objects_with_key(value, target_keys))

            elif isinstance(obj, list):
                for item in obj:
                    found.extend(find_objects_with_key(item, target_keys))

            return found

        # 寻找包含比赛相关键的对象
        match_keywords = ["match", "game", "比赛", "赛程", "fixture"]
        match_objects = find_objects_with_key(data, match_keywords)

        for obj in match_objects:
            if isinstance(obj, dict):
                # 提取比赛ID
                match_id = None
                for id_key in ["id", "match_id", "matchId", "game_id", "gameId"]:
                    if id_key in obj:
                        match_id = str(obj[id_key])
                        break

                if match_id:
                    match_info = {"id": match_id, "raw_data": obj}
                    matches.append(match_info)

        return matches

    async def probe_match_detail_endpoints(self, match_id: str) -> list[dict]:
        """针对特定比赛ID探测所有可能的详情端点"""
        logger.info(f"🔬 探测比赛 {match_id} 的详情接口...")

        # 懂球帝可能使用的详情端点模式
        endpoint_patterns = [
            # 基础API端点
            f"https://m.dongqiudi.com/api/match/detail?id={match_id}",
            f"https://m.dongqiudi.com/api/match/{match_id}",
            f"https://m.dongqiudi.com/api/v1/match/detail?id={match_id}",
            f"https://m.dongqiudi.com/api/v1/match/{match_id}",
            f"https://m.dongqiudi.com/data/{match_id}.json",
            # 完整域名
            f"https://dongqiudi.com/api/match/detail?id={match_id}",
            f"https://dongqiudi.com/api/match/{match_id}",
            f"https://dongqiudi.com/api/v1/match/detail?id={match_id}",
            f"https://dongqiudi.com/api/v1/match/{match_id}",
            f"https://dongqiudi.com/data/{match_id}.json",
            # API子域名
            f"https://api.dongqiudi.com/match/detail?id={match_id}",
            f"https://api.dongqiudi.com/match/{match_id}",
            f"https://api.dongqiudi.com/v1/match/detail?id={match_id}",
            f"https://api.dongqiudi.com/v1/match/{match_id}",
            # 移动端专用
            f"https://m.dongqiudi.com/mobile/match/{match_id}",
            f"https://m.dongqiudi.com/h5/match/{match_id}",
            f"https://m.dongqiudi.com/app/match/{match_id}",
            # 统计数据端点
            f"https://m.dongqiudi.com/api/match/statistics?id={match_id}",
            f"https://m.dongqiudi.com/api/match/stats?id={match_id}",
            f"https://m.dongqiudi.com/api/match/lineup?id={match_id}",
            f"https://m.dongqiudi.com/api/v1/match/statistics?id={match_id}",
            f"https://m.dongqiudi.com/api/v1/match/lineup?id={match_id}",
        ]

        successful_endpoints = []

        for url in endpoint_patterns:
            try:
                logger.info(f"尝试: {url}")
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        validation = self._analyze_match_data(data, match_id)

                        if validation["is_match_data"]:
                            successful_endpoints.append(
                                {"url": url, "data": data, "validation": validation}
                            )
                            logger.info(f"✅ 成功: {url}")
                            logger.info(
                                f"   xG数据: {'有' if validation['has_xg'] else '无'}"
                            )
                            logger.info(
                                f"   阵容数据: {'有' if validation['has_lineup'] else '无'}"
                            )
                            logger.info(
                                f"   技术统计: {'有' if validation['has_stats'] else '无'}"
                            )

                    except json.JSONDecodeError:
                        logger.debug(f"非JSON响应: {url}")
                        continue

                elif response.status_code == 403:
                    logger.debug(f"访问被拒绝: {url}")
                elif response.status_code == 404:
                    logger.debug(f"不存在: {url}")

            except Exception:
                logger.debug(f"请求失败 {url}: {e}")
                continue

        return successful_endpoints

    def _analyze_match_data(self, data: Any, expected_id: str) -> dict:
        """分析比赛数据的质量和内容"""
        analysis = {
            "is_match_data": False,
            "has_xg": False,
            "has_lineup": False,
            "has_stats": False,
            "match_id_found": False,
            "data_structure": {},
            "key_findings": [],
        }

        if not isinstance(data, (dict, list)) or not data:
            return analysis

        # 基本数据结构分析
        if isinstance(data, dict):
            analysis["data_structure"] = {
                k: type(v).__name__ for k, v in data.items()[:10]
            }

        # 验证是否包含预期的比赛ID
        if self._search_for_id(data, expected_id):
            analysis["match_id_found"] = True
            analysis["is_match_data"] = True

        # 搜索xG相关数据
        xg_patterns = [
            r"xg",
            r"expected_goal",
            r"期望进球",
            r"xG",
            r"expected_goals",
            r"xg_total",
            r"xg_home",
            r"xg_away",
            r"xg[\'\"]?\s*:\s*[\d.]+",
        ]

        if self._search_patterns_in_data(data, xg_patterns):
            analysis["has_xg"] = True
            analysis["key_findings"].append("发现xG相关数据")

        # 搜索阵容相关数据
        lineup_patterns = [
            r"lineup",
            r"formation",
            r"首发",
            r"starting",
            r"players",
            r"squad",
            r"阵容",
            r"lineups",
            r"team_lineup",
        ]

        if self._search_patterns_in_data(data, lineup_patterns):
            analysis["has_lineup"] = True
            analysis["key_findings"].append("发现阵容相关数据")

        # 搜索技术统计数据
        stats_patterns = [
            r"statistic",
            r"technical",
            r"possession",
            r"射正",
            r"传球",
            r"控球率",
            r"射门",
            r"passes",
            r"shots",
            r"corners",
        ]

        if self._search_patterns_in_data(data, stats_patterns):
            analysis["has_stats"] = True
            analysis["key_findings"].append("发现技术统计数据")

        return analysis

    def _search_for_id(self, data: Any, target_id: str) -> bool:
        """在数据中搜索目标ID"""
        data_str = json.dumps(data, ensure_ascii=False).lower()
        return target_id.lower() in data_str

    def _search_patterns_in_data(self, data: Any, patterns: list[str]) -> bool:
        """在数据中搜索模式"""
        data_str = json.dumps(data, ensure_ascii=False)

        for pattern in patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                return True

        return False

    async def probe_web_page_match_data(self, match_id: str):
        """探测网页端比赛数据"""
        logger.info(f"🌐 探测比赛 {match_id} 的网页数据...")

        web_urls = [
            f"https://m.dongqiudi.com/data/{match_id}.html",
            f"https://dongqiudi.com/data/{match_id}.html",
            f"https://www.dongqiudi.com/data/{match_id}.html",
        ]

        for url in web_urls:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    html = response.text

                    # 从网页中提取JSON数据
                    json_patterns = [
                        r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
                        r"window\.__NUXT__\s*=\s*({.*?});",
                        r"window\.matchData\s*=\s*({.*?});",
                    ]

                    for pattern in json_patterns:
                        matches = re.findall(pattern, html, re.DOTALL)
                        for match_json in matches:
                            try:
                                data = json.loads(match_json)
                                validation = self._analyze_match_data(data, match_id)

                                if validation["is_match_data"]:
                                    logger.info(f"✅ 从网页提取到比赛数据: {url}")
                                    return {
                                        "url": url,
                                        "source": "web_page",
                                        "data": data,
                                        "validation": validation,
                                    }
                            except json.JSONDecodeError:
                                continue

            except Exception:
                logger.debug(f"访问网页失败 {url}: {e}")
                continue

        return None

    def print_detailed_analysis(self, results: list[dict]):
        """打印详细的分析结果"""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 懂球帝API探测结果分析")
        logger.info("=" * 80)

        for i, result in enumerate(results, 1):
            logger.info(f"\n📊 结果 {i}: {result['url']}")
            validation = result["validation"]

            logger.info(f"  ✅ 比赛ID匹配: {validation['match_id_found']}")
            logger.info(f"  📈 xG数据: {'✅ 有' if validation['has_xg'] else '❌ 无'}")
            logger.info(
                f"  👥 阵容数据: {'✅ 有' if validation['has_lineup'] else '❌ 无'}"
            )
            logger.info(
                f"  📊 技术统计: {'✅ 有' if validation['has_stats'] else '❌ 无'}"
            )

            if validation["key_findings"]:
                logger.info(f"  🎯 关键发现: {', '.join(validation['key_findings'])}")

            if validation["data_structure"]:
                logger.info("  📋 数据结构:")
                for key, type_name in validation["data_structure"].items():
                    logger.info(f"     {key}: {type_name}")

    async def run_comprehensive_probe(self):
        """运行全面的探测流程"""
        logger.info("🚀 开始懂球帝深度探测...")

        # 步骤1: 提取真实比赛数据
        matches = await self.extract_real_match_data()

        if not matches:
            logger.error("❌ 无法提取到比赛数据")
            return

        # 选择前几个比赛ID进行探测
        target_matches = matches[:3]
        logger.info(f"📋 选择 {len(target_matches)} 场比赛进行详细探测")

        all_results = []

        for match in target_matches:
            match_id = match["id"]
            logger.info(f"\n{'=' * 60}")
            logger.info(f"🔍 探测比赛 ID: {match_id}")
            logger.info(f"{'=' * 60}")

            # 步骤2: 探测API端点
            api_results = await self.probe_match_detail_endpoints(match_id)

            # 步骤3: 探测网页数据
            web_result = await self.probe_web_page_match_data(match_id)

            # 收集结果
            match_results = api_results
            if web_result:
                match_results.append(web_result)

            all_results.extend(match_results)

        # 打印总结
        self.print_summary(all_results)

        return all_results

    def print_summary(self, all_results: list[dict]):
        """打印探测总结"""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 懂球帝API探测总结")
        logger.info("=" * 80)

        total_endpoints = len(all_results)
        endpoints_with_xg = sum(1 for r in all_results if r["validation"]["has_xg"])
        endpoints_with_lineup = sum(
            1 for r in all_results if r["validation"]["has_lineup"]
        )
        endpoints_with_stats = sum(
            1 for r in all_results if r["validation"]["has_stats"]
        )

        logger.info("📊 探测统计:")
        logger.info(f"  • 成功端点: {total_endpoints}")
        logger.info(f"  • 包含xG数据: {endpoints_with_xg}")
        logger.info(f"  • 包含阵容数据: {endpoints_with_lineup}")
        logger.info(f"  • 包含技术统计: {endpoints_with_stats}")

        if endpoints_with_xg > 0:
            logger.info("\n✅ xG数据可用性: 懂球帝包含期望进球数据!")
        else:
            logger.info("\n❌ xG数据可用性: 未发现期望进球数据")

        if endpoints_with_lineup > 0:
            logger.info("✅ 阵容数据可用性: 懂球帝包含详细阵容信息!")
        else:
            logger.info("❌ 阵容数据可用性: 未发现阵容数据")

        if endpoints_with_stats > 0:
            logger.info("✅ 技术统计可用性: 懂球帝包含完整技术统计!")
        else:
            logger.info("❌ 技术统计可用性: 未发现技术统计数据")


async def main():
    """主函数"""
    probe = DongqiudiDeepProbe()
    results = await probe.run_comprehensive_probe()

    if results:
        probe.print_detailed_analysis(results)
    else:
        logger.error("❌ 探测失败，未获取到任何数据")


if __name__ == "__main__":
    asyncio.run(main())
