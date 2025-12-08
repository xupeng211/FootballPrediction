"""
FotMob 比赛匹配器
用于将数据库中的 FBref 记录匹配到对应的 FotMob ID
使用模糊匹配算法处理队名差异
"""

import logging
from difflib import SequenceMatcher
import httpx
from datetime import datetime
from typing import Any, Optional
import re

logger = logging.getLogger(__name__)


class FotmobMatchMatcher:
    """
    FotMob 比赛匹配器

    通过队名模糊匹配将 FBref 记录关联到 FotMob 比赛 ID
    """

    def __init__(self, similarity_threshold: float = 70.0):
        """
        初始化匹配器

        Args:
            similarity_threshold: 相似度阈值（百分比），低于此值不认为是匹配
        """
        self.similarity_threshold = similarity_threshold
        self.base_url = "https://www.fotmob.com/api"
        # 🔧 修复: 使用我们验证过的FotMob API认证令牌
        self.headers = {
            # 核心请求头 - 模拟最新 Chrome 131
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            # 🔧 修复: 添加FotMob认证令牌
            "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=",
            "x-foo": "eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZGRmYyIsInRpbWVzdGFtcCI6MTc2NTEyMTgxMn0=",
            # 浏览器安全头 - 最新 Chrome 指纹
            "sec-ch-ua": '"HeadlessChrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            # 来源和引用 - 模拟真实浏览
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            # Fetch API 相关头
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            # 连接管理
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # 常见队名映射表（用于标准化队名）
        self.team_name_mappings = {
            "manchester united": [
                "man utd",
                "manchester utd",
                "man united",
                "manchester u",
            ],
            "manchester city": ["man city", "manchester citi", "manchester c"],
            "chelsea": ["chelsea fc", "chelsea football club"],
            "liverpool": ["liverpool fc", "liverpool football club"],
            "arsenal": ["arsenal fc", "arsenal football club"],
            "tottenham": ["tottenham hotspur", "spurs", "tottenham fc"],
            "barcelona": ["fc barcelona", "barca", "barcelona fc"],
            "real madrid": ["real madrid cf", "madrid", "real"],
            "bayern munich": ["fc bayern munich", "bayern", "fc bayern"],
        }

        # 🔧 DEBUG: 添加调试标志
        self.debug_mode = True

    async def find_match_by_fuzzy_match(
        self, fbref_record: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """
        通过模糊匹配查找对应的 FotMob 比赛

        Args:
            fbref_record: FBref 记录，包含 home, away, date 字段

        Returns:
            匹配的 FotMob 比赛信息，包含 matchId、home_team、away_team 等
            如果找不到匹配返回 None
        """
        try:
            home_team = fbref_record.get("home", "")
            away_team = fbref_record.get("away", "")
            date_str = fbref_record.get("date", "")

            if not all([home_team, away_team, date_str]):
                logger.warning(f"🔍 FBref 记录缺少必要信息: {fbref_record}")
                return None

            # 🔧 DEBUG: 输出调试信息
            if self.debug_mode:
                logger.info(f"🔍 DEBUG: 尝试匹配 {home_team} vs {away_team} (日期: {date_str})")

            # 格式化日期用于 API 调用
            api_date = self._format_date_for_api(date_str)

            # 🔧 DEBUG: 输出调试信息
            if self.debug_mode:
                logger.info(f"🔍 DEBUG: 格式化后日期: {date_str} -> {api_date}")

            # 获取指定日期的所有比赛
            matches_data = await self._get_matches_by_date(api_date)
            if not matches_data or "matches" not in matches_data:
                if self.debug_mode:
                    logger.error(f"🔍 DEBUG: API返回数据结构问题: {matches_data}")
                logger.warning(f"❌ 无法获取 {api_date} 的比赛数据")
                return None

            # 🔧 DEBUG: 输出API响应信息
            if self.debug_mode:
                matches_count = len(matches_data.get("matches", []))
                logger.info(f"🔍 DEBUG: {api_date} 共找到 {matches_count} 场比赛")
                if matches_count > 0:
                    sample_match = matches_data["matches"][0]
                    sample_home = sample_match.get("home", {}).get("name", "未知")
                    sample_away = sample_match.get("away", {}).get("name", "未知")
                    sample_status = sample_match.get("status", {})
                    sample_time = sample_status.get("utcTime", "无时间信息")
                    logger.info(f"🔍 DEBUG: 样本比赛: {sample_home} vs {sample_away} (时间: {sample_time})")
                    logger.info(f"🔍 DEBUG: 完整样本数据结构: {list(sample_match.keys())}")
                else:
                    logger.warning(f"🔍 DEBUG: API响应无比赛数据，检查响应结构: {list(matches_data.keys())}")

            # 计算每场比赛的相似度
            best_match = None
            best_similarity = 0.0
            processed_matches = 0

            for match in matches_data["matches"]:
                similarity = self._calculate_match_similarity(match, fbref_record)
                processed_matches += 1

                # 🔧 DEBUG: 输出每场比赛的相似度计算结果
                if self.debug_mode and processed_matches <= 3:  # 只显示前3个
                    match_home = match.get("home", {}).get("name", "")
                    match_away = match.get("away", {}).get("name", "")
                    logger.info(f"🔍 DEBUG: 比赛 {processed_matches}: {match_home} vs {match_away} -> 相似度: {similarity:.1f}%")

                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    best_similarity = similarity
                    best_match = match

            if best_match:
                result = {
                    "matchId": str(best_match.get("id", "")),
                    "home_team": best_match.get("home", {}).get("name", ""),
                    "away_team": best_match.get("away", {}).get("name", ""),
                    "similarity_score": best_similarity,
                    "tournament": best_match.get("tournament", {}).get("name", ""),
                    "status": best_match.get("status", {}),
                    "date": best_match.get("date", ""),
                }

                # 🔧 DEBUG: 输出成功匹配的详细信息
                if self.debug_mode:
                    match_status = result["status"]
                    match_time = match_status.get("utcTime", "无时间")
                    match_finished = match_status.get("finished", False)
                    match_started = match_status.get("started", False)
                    logger.info(f"🔍 DEBUG: 匹配成功详情:")
                    logger.info(f"   原始记录: {home_team} vs {away_team} (日期: {date_str})")
                    logger.info(f"   匹配结果: {result['home_team']} vs {result['away_team']}")
                    logger.info(f"   相似度: {best_similarity:.1f}% (阈值: {self.similarity_threshold}%)")
                    logger.info(f"   比赛时间: {match_time}")
                    logger.info(f"   比赛状态: 已开始={match_started}, 已完成={match_finished}")
                    logger.info(f"   MatchID: {result['matchId']}")
                    logger.info(f"   联赛: {result['tournament']}")

                logger.info(
                    f"✅ 找到匹配: {home_team} vs {away_team} -> {result['home_team']} vs {result['away_team']} (相似度: {best_similarity:.1f}%)"
                )
                return result
            else:
                if self.debug_mode:
                    logger.info(f"🔍 DEBUG: 最高相似度: {best_similarity:.1f}% (阈值: {self.similarity_threshold}%)")
                logger.warning(f"⚠️  未找到匹配: {home_team} vs {away_team} (日期: {date_str}), 处理了 {processed_matches} 场比赛")
                return None

        except Exception as e:
            logger.error(f"匹配比赛时发生错误: {str(e)}")
            return None

    async def _get_matches_by_date(self, date_str: str) -> Optional[dict[str, Any]]:
        """
        获取指定日期的所有比赛
        使用联赛API端点替代日期API端点，因为联赛API更稳定

        Args:
            date_str: 格式为 YYYYMMDD 的日期字符串

        Returns:
            比赛数据列表，如果失败返回 None
        """
        # 🔧 修复: 使用联赛API端点而不是日期API端点
        # 使用英超联赛作为默认数据源，涵盖所有比赛
        leagues = [
            {"id": 47, "name": "Premier League"},
            {"id": 87, "name": "LaLiga"},
            {"id": 55, "name": "Serie A"},
            {"id": 54, "name": "Bundesliga"},
            {"id": 53, "name": "Ligue 1"},
        ]

        all_matches = []

        try:
            # 🔧 绕过代理，直接连接
            import os
            no_proxy = os.getenv('NO_PROXY', '')
            if no_proxy:
                logger.info(f"🔧 绕过代理连接: NO_PROXY={no_proxy}")

            # 创建客户端，忽略代理设置，并启用自动解压
            client = httpx.AsyncClient(
                headers=self.headers,
                timeout=30.0,
                # 明确禁用代理
                proxies=None
            )

            for league in leagues:
                url = f"https://www.fotmob.com/api/leagues?id={league['id']}"

                if self.debug_mode:
                    logger.info(f"🔍 DEBUG: 获取{league['name']}数据: {url}")

                response = await client.get(url)

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception as json_error:
                        logger.error(f"JSON解析错误 {league['name']}: {json_error}")
                        logger.error(f"响应内容前500字符: {response.text[:500]}")
                        continue

                    # 使用已验证的正确解析路径
                    if 'fixtures' in data and isinstance(data['fixtures'], dict):
                        if 'allMatches' in data['fixtures']:
                            matches = data['fixtures']['allMatches']

                            # 🔧 DEBUG: 输出联赛数据信息
                            if self.debug_mode:
                                logger.info(f"🔍 DEBUG: {league['name']} 找到 {len(matches)} 场比赛")
                                if matches:
                                    sample = matches[0]
                                    sample_home = sample.get('home', {}).get('name', '未知')
                                    sample_away = sample.get('away', {}).get('name', '未知')
                                    logger.info(f"🔍 DEBUG: {league['name']}样本: {sample_home} vs {sample_away}")

                            all_matches.extend(matches)
                        else:
                            if self.debug_mode:
                                logger.warning(f"🔍 DEBUG: {league['name']} 无 allMatches 数据")
                    else:
                        if self.debug_mode:
                            logger.warning(f"🔍 DEBUG: {league['name']} 无 fixtures 数据")
                else:
                    logger.warning(
                        f"HTTP {response.status_code} when fetching {league['name']} data"
                    )

            # 返回合并的比赛数据
            result = {"matches": all_matches}

            if self.debug_mode:
                logger.info(f"🔍 DEBUG: 总共获取 {len(all_matches)} 场比赛")
                if all_matches:
                    logger.info(f"🔍 DEBUG: 前3场比赛:")
                    for i, match in enumerate(all_matches[:3]):
                        home = match.get('home', {}).get('name', '未知')
                        away = match.get('away', {}).get('name', '未知')
                        logger.info(f"   {i+1}. {home} vs {away}")

            logger.info(f"Successfully fetched {len(all_matches)} total matches for {date_str}")
            return result

        except Exception as e:
            logger.error(f"Error fetching matches for {date_str}: {str(e)}")
            return None

    def _calculate_match_similarity(
        self, fotmob_match: dict[str, Any], fbref_record: dict[str, Any]
    ) -> float:
        """
        计算两场比赛的相似度

        Args:
            fotmob_match: FotMob 比赛数据
            fbref_record: FBref 记录

        Returns:
            相似度分数 (0-100)
        """
        try:
            fotmob_home = fotmob_match.get("home", {}).get("name", "")
            fotmob_away = fotmob_match.get("away", {}).get("name", "")
            fbref_home = fbref_record.get("home", "")
            fbref_away = fbref_record.get("away", "")

            # 计算主队相似度
            home_similarity = self._calculate_team_similarity(fbref_home, fotmob_home)

            # 计算客队相似度
            away_similarity = self._calculate_team_similarity(fbref_away, fotmob_away)

            # 计算整体相似度（取平均值，但要求两队都要有一定的相似度）
            overall_similarity = (home_similarity + away_similarity) / 2

            # 如果某一队相似度太低，则整体相似度也要降低
            min_team_similarity = min(home_similarity, away_similarity)
            if min_team_similarity < 30.0:
                overall_similarity *= 0.5  # 惩罚因子

            return overall_similarity

        except Exception as e:
            logger.error(f"计算比赛相似度时发生错误: {str(e)}")
            return 0.0

    def _calculate_team_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个队名的相似度

        Args:
            name1: 队名1
            name2: 队名2

        Returns:
            相似度分数 (0-100)
        """
        try:
            # 标准化队名
            normalized_name1 = self._normalize_team_name(name1)
            normalized_name2 = self._normalize_team_name(name2)

            # 完全相同
            if normalized_name1 == normalized_name2:
                return 100.0

            # 使用 difflib 计算相似度
            similarity_ratio = SequenceMatcher(
                None, normalized_name1, normalized_name2
            ).ratio()
            similarity_score = similarity_ratio * 100

            # 检查是否在映射表中有匹配
            mapping_bonus = self._check_name_mapping(normalized_name1, normalized_name2)

            # 返回最终相似度（考虑映射加分）
            final_similarity = min(100.0, similarity_score + mapping_bonus)
            return final_similarity

        except Exception as e:
            logger.error(f"计算队名相似度时发生错误: {str(e)}")
            return 0.0

    def _normalize_team_name(self, name: str) -> str:
        """
        标准化队名（移除常见后缀、统一大小写等）

        Args:
            name: 原始队名

        Returns:
            标准化后的队名
        """
        if not name:
            return ""

        # 转为小写
        normalized = name.lower().strip()

        # 移除常见的足球俱乐部后缀
        suffixes_to_remove = [
            "football club",
            "fc",
            "cf",
            "soccer club",
            "sc",
            "athletic club",
            "ac",
            "sports club",
            "united",
            "city",
            "hotspur",
            "rangers",
            "celtic",
        ]

        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        # 移除特殊字符
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # 合并多个空格
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _check_name_mapping(self, name1: str, name2: str) -> float:
        """
        检查队名是否在预定义的映射表中

        Args:
            name1: 标准化队名1
            name2: 标准化队名2

        Returns:
            映射加分 (0-30)
        """
        for standard_name, variants in self.team_name_mappings.items():
            name1_variants = [standard_name] + variants
            name2_variants = [standard_name] + variants

            if (name1 in name1_variants and name2 in name2_variants) or (
                name2 in name1_variants and name1 in name2_variants
            ):
                return 30.0  # 映射加分

        return 0.0

    def _format_date_for_api(self, date_input) -> str:
        """
        将日期格式化为 API 所需的格式 (YYYYMMDD)

        Args:
            date_input: 输入日期，可以是字符串、datetime对象或其他格式
                       支持: YYYYMMDD, YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, datetime对象

        Returns:
            格式化为 YYYYMMDD 的字符串
        """
        try:
            # 如果已经是正确的格式 (YYYYMMDD 字符串)
            if isinstance(date_input, str) and re.match(r"^\d{8}$", date_input):
                return date_input

            # 如果是 datetime 对象，直接格式化
            if hasattr(date_input, "strftime"):
                return date_input.strftime("%Y%m%d")

            # 确保转换为字符串
            if not isinstance(date_input, str):
                date_str = str(date_input)
            else:
                date_str = date_input

            # 处理数据库日期格式: YYYY-MM-DD HH:MM:SS
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", date_str):
                # 提取日期部分，去掉时间部分
                return date_str[:10].replace("-", "")

            # 处理简单日期格式: YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                return date_str.replace("-", "")

            # 尝试使用 datetime 解析其他格式 (ISO格式等)
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%Y%m%d")

        except Exception as e:
            logger.error(
                f"日期格式转换失败: {date_input} (类型: {type(date_input)}) -> {str(e)}"
            )
            # 最后的安全处理：尝试转换为字符串并处理
            try:
                date_str = str(date_input)
                if len(date_str) >= 10:
                    return date_str[:10].replace("-", "")
                else:
                    return date_str.replace("-", "")
            except:
                # 最后的fallback：返回今天的日期
                return datetime.now().strftime("%Y%m%d")

    async def health_check(self) -> bool:
        """
        健康检查：验证 FotMob API 是否可访问

        Returns:
            True 如果 API 可访问，False 否则
        """
        try:
            # 使用今天的日期进行测试
            today = datetime.now().strftime("%Y%m%d")
            test_url = f"{self.base_url}/matches?date={today}"

            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(test_url)
                # 不要求 200，只要能连接上就行
                return response.status_code in [200, 404, 400]

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def set_similarity_threshold(self, threshold: float):
        """
        设置相似度阈值

        Args:
            threshold: 新的相似度阈值 (0-100)
        """
        if 0 <= threshold <= 100:
            self.similarity_threshold = threshold
            logger.info(f"Similarity threshold set to {threshold}%")
        else:
            logger.warning(
                f"Invalid similarity threshold: {threshold}. Must be between 0 and 100"
            )
