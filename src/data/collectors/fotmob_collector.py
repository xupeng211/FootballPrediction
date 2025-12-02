"""
FotMob 数据采集器 - 重构版
使用 Next.js Data API 获取真实数据，基于成功的Web逆向工程结果
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List

try:
    from curl_cffi.requests import AsyncSession
except ImportError:
    raise ImportError("curl_cffi is required. Install with: pip install curl_cffi")

from .base_collector import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)


class FotmobCollector(BaseCollector):
    """
    重构版 FotMob 数据采集器

    基于成功的Web逆向工程，使用 Next.js Data API:
    - 动态获取 buildId
    - 使用 _next/data/ 端点
    - 移除所有 Mock 回退逻辑
    - 纯真实数据采集
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        # FotMob 特定配置
        self.base_url = "https://www.fotmob.com"

        # Session 配置
        self._session: AsyncSession | None = None

        # BuildId 缓存
        self.build_id: Optional[str] = None
        self.build_id_cache_time = 0
        self.build_id_cache_duration = 3600  # 1小时缓存

        # 请求统计
        self.request_count = 0
        self.last_request_time = 0

    async def _get_session(self) -> AsyncSession:
        """获取或创建异步会话"""
        if self._session is None:
            # 使用Chrome 110进行身份伪装 (基于逆向工程成功案例)
            self._session = AsyncSession(
                impersonate="chrome110",
                timeout=self.timeout
            )

            # 访问主页建立会话
            try:
                await self._session.get(f"{self.base_url}/", timeout=10)
                self.logger.info("FotMob session initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize FotMob session: {e}")
                raise

        return self._session

    async def _get_build_id(self, force_refresh: bool = False) -> str:
        """
        动态获取FotMob的buildId

        Args:
            force_refresh: 是否强制刷新buildId

        Returns:
            str: 当前buildId
        """
        current_time = time.time()

        # 检查缓存
        if (not force_refresh and
            self.build_id and
            current_time - self.build_id_cache_time < self.build_id_cache_duration):
            self.logger.debug(f"Using cached buildId: {self.build_id}")
            return self.build_id

        try:
            session = await self._get_session()
            self.logger.info("Fetching latest FotMob buildId...")

            response = await session.get(
                self.base_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )

            if response.status_code == 200:
                html = response.text

                # 多种buildId提取模式
                patterns = [
                    r'"buildId":\s*"([^"]+)"',
                    r'buildId:"([^"]+)"',
                    r'__NEXT_DATA__.*?"buildId":"([^"]+)"'
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, html)
                    if matches:
                        self.build_id = matches[0]
                        self.build_id_cache_time = current_time
                        self.logger.info(f"Successfully fetched buildId: {self.build_id}")
                        return self.build_id

                # 尝试从__NEXT_DATA__中提取
                next_data_match = re.search(
                    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                    html, re.DOTALL
                )
                if next_data_match:
                    try:
                        next_data = json.loads(next_data_match.group(1))
                        if 'buildId' in next_data:
                            self.build_id = next_data['buildId']
                            self.build_id_cache_time = current_time
                            self.logger.info(f"Got buildId from __NEXT_DATA__: {self.build_id}")
                            return self.build_id
                    except json.JSONDecodeError:
                        pass

            self.logger.warning(f"Failed to fetch buildId, status code: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error fetching buildId: {e}")

        # 回退到已知的buildId (来自逆向工程)
        fallback_build_id = "vrWmgMfJW8Tr_5R8oDBrU"
        if not self.build_id:
            self.logger.warning(f"Using fallback buildId: {fallback_build_id}")
            self.build_id = fallback_build_id

        return self.build_id

    def _get_nextjs_data_url(self, endpoint: str, **params) -> str:
        """
        构建Next.js Data API URL

        Args:
            endpoint: API端点 (如 'matches', 'leagues')
            **params: URL参数

        Returns:
            str: 完整的API URL
        """
        if not self.build_id:
            raise ValueError("buildId not set, call _get_build_id() first")

        base_api_url = f"{self.base_url}/_next/data/{self.build_id}/{endpoint}.json"

        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            return f"{base_api_url}?{query_string}"

        return base_api_url

    async def _make_nextjs_request(self, url: str) -> Dict[str, Any]:
        """
        发送Next.js Data API请求

        Args:
            url: 完整的API URL

        Returns:
            Dict: API响应数据

        Raises:
            Exception: 当请求失败时
        """
        session = await self._get_session()

        # 智能延迟，避免过于频繁的请求
        current_time = time.time()
        if current_time - self.last_request_time < 2.0:
            await asyncio.sleep(2.0 - (current_time - self.last_request_time))

        self.request_count += 1
        self.last_request_time = time.time()

        try:
            response = await session.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': f'{self.base_url}/',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ Successfully fetched data from {url} (size: {len(str(data))} chars)")
                return data
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200] if response.text else 'No content'}"
                self.logger.error(f"❌ Next.js API request failed: {error_msg}")
                raise Exception(f"Next.js API error: {error_msg}")

        except Exception as e:
            self.logger.error(f"❌ Next.js API request exception: {e}")
            raise

    def _extract_matches_from_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从Next.js响应中提取比赛数据

        Args:
            data: Next.js API响应数据

        Returns:
            List[Dict]: 标准化的比赛数据列表
        """
        matches = []

        fallback = data.get("pageProps", {}).get("fallback", {})

        # 查找所有包含比赛数据的键
        for key, value in fallback.items():
            # 跳过翻译映射
            if key == "/api/translationmapping?locale=matches":
                continue

            # 查找包含matches字段的响应
            if isinstance(value, dict) and "matches" in value:
                match_list = value["matches"]
                if isinstance(match_list, list) and match_list:
                    self.logger.debug(f"Found {len(match_list)} matches from {key}")

                    # 标准化比赛数据格式
                    for match in match_list:
                        if isinstance(match, dict):
                            standardized_match = self._standardize_match_data(match)
                            matches.append(standardized_match)

        return matches

    def _standardize_match_data(self, raw_match: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化比赛数据格式

        Args:
            raw_match: 原始比赛数据

        Returns:
            Dict: 标准化的比赛数据
        """
        # 根据FotMob实际返回的数据结构进行标准化
        # 这里需要根据实际API响应结构进行调整
        return {
            "id": raw_match.get("id"),
            "home_team": raw_match.get("home", {}).get("name"),
            "away_team": raw_match.get("away", {}).get("name"),
            "home_score": raw_match.get("homeScore"),
            "away_score": raw_match.get("awayScore"),
            "status": raw_match.get("status", {}).get("name"),
            "match_date": raw_match.get("startTime"),
            "venue": raw_match.get("venue", {}).get("name"),
            "league": raw_match.get("tournament", {}).get("name"),
            "raw_data": raw_match  # 保留原始数据以备进一步分析
        }

    async def collect_matches_by_date(self, date_str: str) -> CollectionResult:
        """
        按日期收集比赛数据 (重构版 - 使用Next.js Data API)

        Args:
            date_str: 日期字符串，格式为 YYYYMMDD

        Returns:
            CollectionResult: 包含当天所有比赛详情的结果
        """
        try:
            self.logger.info(f"🚀 Collecting matches for date {date_str} using Next.js Data API")

            # 确保有最新的buildId
            await self._get_build_id()

            # 构建API URL
            url = self._get_nextjs_data_url("matches", date=date_str)
            self.logger.info(f"📡 Requesting: {url}")

            # 发送请求
            data = await self._make_nextjs_request(url)

            # 提取比赛数据
            matches = self._extract_matches_from_response(data)

            if not matches:
                self.logger.warning(f"⚠️ No matches found for date {date_str}")
                return self.create_error_result(f"No matches available for date {date_str}")

            # 限制处理数量以避免过载
            max_matches = self.config.get("max_matches_per_date", 100)
            if len(matches) > max_matches:
                matches = matches[:max_matches]
                self.logger.info(f"Limited matches to {max_matches} for date {date_str}")

            # 构建元数据
            metadata = {
                "date": date_str,
                "matches_collected": len(matches),
                "source": "fotmob_nextjs_api",
                "build_id": self.build_id,
                "collected_at": datetime.now().isoformat(),
                "api_url": url
            }

            self.logger.info(f"✅ Successfully collected {len(matches)} matches for {date_str}")
            return self.create_success_result(matches, metadata)

        except Exception as e:
            self.logger.error(f"❌ Error collecting matches for date {date_str}: {e}")
            return self.create_error_result(f"Failed to collect matches for {date_str}: {e}")

    async def collect_league_data(self, league_id: int) -> CollectionResult:
        """
        收集联赛数据

        Args:
            league_id: 联赛ID

        Returns:
            CollectionResult: 包含联赛数据的结果
        """
        try:
            self.logger.info(f"🏆 Collecting league data for ID {league_id}")

            await self._get_build_id()

            url = self._get_nextjs_data_url("leagues", id=str(league_id))
            self.logger.info(f"📡 Requesting league data: {url}")

            data = await self._make_nextjs_request(url)

            # 提取联赛数据
            fallback = data.get("pageProps", {}).get("fallback", {})
            league_data = {}

            for key, value in fallback.items():
                if "league" in key.lower() and isinstance(value, dict):
                    league_data.update(value)

            if not league_data:
                self.logger.warning(f"⚠️ No league data found for ID {league_id}")
                return self.create_error_result(f"No data available for league {league_id}")

            metadata = {
                "league_id": league_id,
                "source": "fotmob_nextjs_api",
                "build_id": self.build_id,
                "collected_at": datetime.now().isoformat()
            }

            self.logger.info(f"✅ Successfully collected league data for ID {league_id}")
            return self.create_success_result(league_data, metadata)

        except Exception as e:
            self.logger.error(f"❌ Error collecting league data for {league_id}: {e}")
            return self.create_error_result(f"Failed to collect league data for {league_id}: {e}")

    async def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            bool: 连接是否成功
        """
        try:
            self.logger.info("🧪 Testing FotMob Next.js API connection...")

            # 测试buildId获取
            build_id = await self._get_build_id()
            self.logger.info(f"✅ BuildId fetch successful: {build_id}")

            # 测试一个简单的API调用
            test_date = datetime.now().strftime("%Y%m%d")
            matches = await self.collect_matches_by_date(test_date)

            if matches.success:
                match_count = len(matches.data) if matches.data else 0
                self.logger.info(f"✅ API test successful, got {match_count} matches")
                return True
            else:
                self.logger.error(f"❌ API test failed: {matches.error}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            return False

    async def collect(self, *args, **kwargs) -> CollectionResult:
        """
        主收集方法

        支持的参数:
        - date: 收集指定日期的比赛 (格式: YYYYMMDD)
        - league_id: 收集指定联赛的数据
        - test: 运行连接测试

        Returns:
            CollectionResult: 收集结果
        """
        if "date" in kwargs:
            date_str = kwargs["date"]
            return await self.collect_matches_by_date(date_str)

        elif "league_id" in kwargs:
            league_id = kwargs["league_id"]
            return await self.collect_league_data(league_id)

        elif "test" in kwargs:
            success = await self.test_connection()
            if success:
                return self.create_success_result({"test": "passed"}, {"message": "API connection successful"})
            else:
                return self.create_error_result("API connection test failed")

        else:
            # 默认收集昨天的数据
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            return await self.collect_matches_by_date(yesterday)

    async def close(self):
        """关闭会话"""
        if self._session:
            self._session = None
            self.logger.info("FotMob session closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()