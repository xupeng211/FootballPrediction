#!/usr/bin/env python3
"""
🕵️‍♂️ 懂球帝 Web 端 API 逆向工程探测脚本

目标：探测懂球帝 Web 端接口，验证是否包含 xG (期望进球) 和阵容数据
避开 App 强校验，优先探测 Web/H5 端接口

作者：逆向工程专家 (针对中国体育媒体)
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import httpx
from curl_cffi import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DongqiudiWebProbe:
    """懂球帝 Web 端 API 探测器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://m.dongqiudi.com/'
        })

        # 懂球帝可能的 API 端点
        self.base_urls = [
            'https://m.dongqiudi.com/api',
            'https://dongqiudi.com/api',
            'https://www.dongqiudi.com/api',
            'https://api.dongqiudi.com'
        ]

        # 可能的比赛列表端点
        self.match_list_endpoints = [
            '/match/list',
            '/match/today',
            '/match/fixed',
            '/v1/match/list',
            '/v2/match/list',
            '/v3/match/list',
            '/mobile/match/list',
            '/h5/match/list'
        ]

        # 可能的比赛详情端点
        self.match_detail_endpoints = [
            '/match/detail',
            '/match/info',
            '/match/data',
            '/v1/match/detail',
            '/v2/match/detail',
            '/mobile/match/detail',
            '/h5/match/detail'
        ]

    async def probe_match_list(self) -> list[dict] | None:
        """步骤 A: 获取比赛列表，寻找五大联赛已完场比赛"""
        logger.info("🔍 步骤 A: 探测比赛列表接口...")

        for base_url in self.base_urls:
            for endpoint in self.match_list_endpoints:
                url = f"{base_url}{endpoint}"

                try:
                    logger.info(f"尝试: {url}")
                    response = self.session.get(url, timeout=10)

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"✅ 成功获取数据: {url}")

                            # 解析比赛数据
                            matches = self._parse_match_list(data)
                            if matches:
                                logger.info(f"📋 找到 {len(matches)} 场比赛")
                                return matches

                        except json.JSONDecodeError:
                            logger.warning(f"非 JSON 响应: {url}")
                            continue

                    elif response.status_code in [301, 302, 307, 308]:
                        # 处理重定向
                        redirect_url = response.headers.get('Location')
                        if redirect_url:
                            logger.info(f"重定向到: {redirect_url}")

                    else:
                        logger.warning(f"状态码 {response.status_code}: {url}")

                except Exception as e:
                    logger.error(f"请求失败 {url}: {e}")
                    continue

        # 如果 API 探测失败，尝试从网页抓取
        logger.info("🔄 API 探测失败，尝试从网页抓取...")
        return await self._scrape_match_list_from_web()

    def _parse_match_list(self, data: Any) -> list[dict]:
        """解析比赛列表数据"""
        matches = []

        # 尝试不同的数据结构
        if isinstance(data, dict):
            # 情况1: data.data 或 data.result
            for key in ['data', 'result', 'list', 'matches']:
                if key in data and isinstance(data[key], list):
                    matches.extend(data[key])

            # 情况2: 分页数据
            if 'data' in data and isinstance(data['data'], dict):
                for sub_key in ['list', 'matches', 'items']:
                    if sub_key in data['data'] and isinstance(data['data'][sub_key], list):
                        matches.extend(data['data'][sub_key])

        elif isinstance(data, list):
            matches = data

        # 过滤五大联赛已完场比赛
        filtered_matches = []
        for match in matches:
            if self._is_major_league_finished(match):
                filtered_matches.append(match)

        return filtered_matches

    def _is_major_league_finished(self, match: dict) -> bool:
        """判断是否为五大联赛已完场比赛"""
        try:
            # 五大联赛标识
            major_leagues = [
                '英超', '西甲', '德甲', '意甲', '法甲',
                'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1',
                'England', 'Spain', 'Germany', 'Italy', 'France'
            ]

            # 检查联赛名称
            league_name = ''
            for key in ['league', 'league_name', 'competition', 'comp']:
                if key in match and match[key]:
                    league_name = str(match[key]).lower()
                    break

            is_major = any(league.lower() in league_name for league in major_leagues)

            # 检查比赛状态
            status = ''
            for key in ['status', 'match_status', 'state', 'finished']:
                if key in match:
                    status = str(match[key]).lower()
                    break

            is_finished = any(word in status for word in ['finished', 'ended', '完场', '已结束'])

            return is_major and is_finished

        except Exception as e:
            logger.debug(f"解析比赛状态失败: {e}")
            return False

    async def _scrape_match_list_from_web(self) -> list[dict] | None:
        """从网页抓取比赛列表（简化版本，不使用BeautifulSoup）"""
        urls_to_try = [
            'https://m.dongqiudi.com/',
            'https://dongqiudi.com/',
            'https://www.dongqiudi.com/'
        ]

        for url in urls_to_try:
            try:
                logger.info(f"抓取网页: {url}")
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    # 尝试从 HTML 中提取比赛数据（使用正则表达式）
                    html_content = response.text

                    # 查找包含比赛数据的 script 标签
                    script_pattern = r'<script[^>]*>(.*?)</script>'
                    scripts = re.findall(script_pattern, html_content, re.DOTALL)

                    for script in scripts:
                        if 'match' in script.lower() or '比赛' in script:
                            # 尝试提取 JSON 数据
                            try:
                                # 查找 JSON 对象模式
                                json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
                                matches = re.findall(json_pattern, script, re.DOTALL)

                                for match_json in matches:
                                    try:
                                        data = json.loads(match_json)
                                        logger.info("✅ 从网页提取到初始状态数据")
                                        # 这里需要根据实际数据结构解析比赛信息
                                        return []
                                    except json.JSONDecodeError:
                                        continue

                            except Exception as e:
                                logger.debug(f"解析 script 失败: {e}")
                                continue

            except Exception as e:
                logger.error(f"抓取网页失败 {url}: {e}")
                continue

        return None

    async def probe_match_detail(self, match_id: str) -> dict | None:
        """步骤 B: 探测比赛详情接口"""
        logger.info(f"🔬 步骤 B: 探测比赛详情接口 (ID: {match_id})")

        for base_url in self.base_urls:
            for endpoint in self.match_detail_endpoints:
                # 尝试不同的参数格式
                param_formats = [
                    f"?id={match_id}",
                    f"?match_id={match_id}",
                    f"?matchId={match_id}",
                    f"/{match_id}",
                    f"/{match_id}.json"
                ]

                for param in param_formats:
                    url = f"{base_url}{endpoint}{param}"

                    try:
                        logger.info(f"尝试: {url}")
                        response = self.session.get(url, timeout=10)

                        if response.status_code == 200:
                            try:
                                data = response.json()
                                logger.info(f"✅ 成功获取比赛详情: {url}")

                                # 验证数据质量
                                validation_result = self._validate_match_detail(data)
                                if validation_result['has_data']:
                                    return {
                                        'url': url,
                                        'data': data,
                                        'validation': validation_result
                                    }

                            except json.JSONDecodeError:
                                logger.warning(f"非 JSON 响应: {url}")
                                continue

                        elif response.status_code == 404:
                            continue
                        else:
                            logger.debug(f"状态码 {response.status_code}: {url}")

                    except Exception as e:
                        logger.debug(f"请求失败 {url}: {e}")
                        continue

        return None

    def _validate_match_detail(self, data: dict) -> dict:
        """验证比赛详情数据质量"""
        validation = {
            'has_data': False,
            'has_xg': False,
            'has_lineup': False,
            'has_stats': False,
            'key_fields': []
        }

        try:
            # 检查基本数据结构
            if isinstance(data, dict) and data:
                validation['has_data'] = True

                # 递归查找 xG 相关字段
                xg_keywords = ['xg', 'expected_goals', 'xg_total', 'xg_home', 'xg_away', 'expected_goals']
                if self._find_keywords_in_data(data, xg_keywords):
                    validation['has_xg'] = True
                    validation['key_fields'].append('xG数据')

                # 递归查找阵容相关字段
                lineup_keywords = ['lineup', 'lineups', 'formation', 'starting_lineup', 'players', 'squad']
                if self._find_keywords_in_data(data, lineup_keywords):
                    validation['has_lineup'] = True
                    validation['key_fields'].append('阵容数据')

                # 递归查找技术统计相关字段
                stats_keywords = ['statistics', 'stats', 'technical', 'possession', 'shots', 'passes']
                if self._find_keywords_in_data(data, stats_keywords):
                    validation['has_stats'] = True
                    validation['key_fields'].append('技术统计')

        except Exception as e:
            logger.error(f"数据验证失败: {e}")

        return validation

    def _find_keywords_in_data(self, data: Any, keywords: list[str]) -> bool:
        """递归查找关键词"""
        if isinstance(data, dict):
            for key, value in data.items():
                # 检查键名
                if any(keyword in str(key).lower() for keyword in keywords):
                    return True

                # 递归检查值
                if self._find_keywords_in_data(value, keywords):
                    return True

        elif isinstance(data, list):
            for item in data:
                if self._find_keywords_in_data(item, keywords):
                    return True

        elif isinstance(data, str):
            # 检查字符串内容
            return any(keyword in data.lower() for keyword in keywords)

        return False

    async def run_probe(self):
        """运行完整的探测流程"""
        logger.info("🚀 开始懂球帝 Web 端 API 探测")

        # 步骤 1: 获取比赛列表
        matches = await self.probe_match_list()

        if not matches:
            logger.error("❌ 无法获取比赛列表")
            return

        # 选择一场比赛进行详情探测
        target_match = matches[0] if matches else None
        match_id = self._extract_match_id(target_match)

        if not match_id:
            logger.error("❌ 无法提取比赛 ID")
            return

        logger.info(f"📋 目标比赛: {target_match}")
        logger.info(f"🆔 比赛 ID: {match_id}")

        # 步骤 2: 探测比赛详情
        detail_result = await self.probe_match_detail(match_id)

        if detail_result:
            logger.info("✅ 探测成功!")
            logger.info(f"📡 成功接口: {detail_result['url']}")

            validation = detail_result['validation']
            logger.info("📊 数据验证结果:")
            logger.info(f"  - xG 数据: {'✅ 有' if validation['has_xg'] else '❌ 无'}")
            logger.info(f"  - 阵容数据: {'✅ 有' if validation['has_lineup'] else '❌ 无'}")
            logger.info(f"  - 技术统计: {'✅ 有' if validation['has_stats'] else '❌ 无'}")

            if validation['key_fields']:
                logger.info(f"🎯 发现关键字段: {', '.join(validation['key_fields'])}")

            # 打印部分数据结构
            self._print_data_structure(detail_result['data'])

        else:
            logger.error("❌ 无法获取比赛详情")

    def _extract_match_id(self, match: dict) -> str | None:
        """提取比赛 ID"""
        if not match:
            return None

        # 常见的 ID 字段名
        id_fields = ['id', 'match_id', 'matchId', 'game_id', 'gameId', 'pk']

        for field in id_fields:
            if field in match:
                return str(match[field])

        return None

    def _print_data_structure(self, data: Any, depth: int = 0, max_depth: int = 3):
        """打印数据结构（限制深度）"""
        if depth > max_depth:
            return

        indent = "  " * depth

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    logger.info(f"{indent}{key}:")
                    self._print_data_structure(value, depth + 1, max_depth)
                else:
                    # 截断长字符串
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    logger.info(f"{indent}{key}: {value}")

        elif isinstance(data, list):
            if data:
                logger.info(f"{indent}List (长度: {len(data)}):")
                # 只显示前几个元素
                for i, item in enumerate(data[:3]):
                    logger.info(f"{indent}[{i}]:")
                    self._print_data_structure(item, depth + 1, max_depth)
                if len(data) > 3:
                    logger.info(f"{indent}... (还有 {len(data) - 3} 个元素)")
            else:
                logger.info(f"{indent}空列表")
        else:
            logger.info(f"{indent}{data}")


async def main():
    """主函数"""
    probe = DongqiudiWebProbe()
    await probe.run_probe()


if __name__ == "__main__":
    asyncio.run(main())
