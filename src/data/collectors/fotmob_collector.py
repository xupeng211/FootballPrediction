"""
FotMob 数据采集器
使用 curl_cffi 进行 TLS 指纹伪装和签名认证，绕过反爬保护
"""

import asyncio
import base64
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    from curl_cffi.requests import AsyncSession
except ImportError:
    raise ImportError("curl_cffi is required. Install with: pip install curl_cffi")

from .base_collector import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)


class FotmobCollector(BaseCollector):
    """
    FotMob 数据采集器

    基于我们成功的探测结果，使用以下端点：
    - /api/data/audio-matches: 获取比赛 ID 列表 (需要签名)
    - /api/match?id={id}: 获取比赛详情 (需要签名)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        # FotMob 特定配置
        self.base_url = "https://www.fotmob.com"
        self.client_version = "production:208a8f87c2cc13343f1dd8671471cf5a039dced3"

        # Session 配置
        self._session: AsyncSession | None = None

        # 基础 Headers
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

        # 已知的有效签名 (从探测脚本获取)
        self.known_signature = "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0="

    async def _get_session(self) -> AsyncSession:
        """获取或创建异步会话"""
        if self._session is None:
            self._session = AsyncSession(impersonate="chrome120")

            # 首先访问主页建立会话
            try:
                await self._session.get(f"{self.base_url}/")
                logger.info("FotMob session initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize FotMob session: {e}")
                raise

        return self._session

    def _generate_x_mas_header(self, api_url: str) -> str:
        """
        生成 x-mas 认证头

        Args:
            api_url: API 端点路径

        Returns:
            Base64 编码的认证头
        """
        # 生成当前时间戳
        timestamp = int(time.time() * 1000)

        # 构建请求体数据
        body_data = {
            "url": api_url,
            "code": timestamp,
            "foo": self.client_version
        }

        # 生成签名 (基于成功探测的模式)
        signature = self._generate_signature(body_data, api_url)

        # 构建完整的 x-mas 头
        x_mas_data = {
            "body": body_data,
            "signature": signature
        }

        # 编码为 Base64
        x_mas_str = json.dumps(x_mas_data, separators=(',', ':'))
        x_mas_encoded = base64.b64encode(x_mas_str.encode()).decode()

        return x_mas_encoded

    def _generate_signature(self, body_data: dict[str, Any], api_url: str) -> str:
        """生成签名 (基于成功探测的算法)"""
        # 方法1: URL + code + client_version 的 MD5 前16位
        base_str = f"{api_url}{body_data['code']}{self.client_version}"
        signature = hashlib.md5(base_str.encode()).hexdigest().upper()[:16]
        return signature

    def _get_headers(self, api_url: str, use_known_signature: bool = False) -> dict[str, str]:
        """
        获取请求头

        Args:
            api_url: API 端点路径
            use_known_signature: 是否使用已知的有效签名

        Returns:
            包含认证头的请求头字典
        """
        headers = self.base_headers.copy()

        if use_known_signature and (
            api_url == "/api/data/audio-matches" or
            api_url.startswith("/api/matches?date=") or
            api_url.startswith("/api/data/matches?date=")
        ):
            # 对音频匹配接口和历史数据接口使用已知的有效签名
            headers["x-mas"] = self.known_signature
        else:
            # 动态生成签名
            x_mas = self._generate_x_mas_header(api_url)
            headers["x-mas"] = x_mas

        return headers

    async def _make_authenticated_request(
        self,
        api_url: str,
        use_known_signature: bool = False,
        timeout: float = 30.0
    ) -> dict[str, Any] | None:
        """
        发送认证请求

        Args:
            api_url: API 端点路径
            use_known_signature: 是否使用已知的有效签名
            timeout: 请求超时时间

        Returns:
            响应 JSON 数据或 None
        """
        session = await self._get_session()
        headers = self._get_headers(api_url, use_known_signature)
        full_url = f"{self.base_url}{api_url}"

        try:
            self.logger.debug(f"Making authenticated request to {api_url}")

            response = await session.get(
                full_url,
                headers=headers,
                timeout=timeout
            )

            self.logger.debug(f"Response status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    self.logger.debug(f"Successfully received data from {api_url}")
                    return data
                except ValueError as e:
                    self.logger.error(f"Failed to parse JSON from {api_url}: {e}")
                    return None
            else:
                self.logger.warning(f"HTTP {response.status_code} for {api_url}")
                if response.text:
                    self.logger.debug(f"Response text: {response.text[:200]}")
                return None

        except Exception as e:
            self.logger.error(f"Request failed for {api_url}: {e}")
            return None

    async def collect_matches_by_date_api(self, date_str: str) -> CollectionResult:
        """
        使用新的历史数据接口收集指定日期的比赛数据

        Args:
            date_str: 日期字符串，格式为 YYYYMMDD

        Returns:
            CollectionResult: 包含比赛数据的结果
        """
        try:
            self.logger.info(f"Collecting matches for date {date_str} using historical API")

            # 使用支持历史日期的新接口
            api_url = f"/api/matches?date={date_str}"

            data = await self._make_authenticated_request(
                api_url,
                use_known_signature=True
            )

            if data is None:
                return self.create_error_result(f"Failed to fetch matches for date {date_str}")

            if isinstance(data, dict) and 'leagues' in data:
                # 从联赛数据中提取比赛信息
                matches = []
                leagues = data.get('leagues', [])

                for league in leagues:
                    league_matches = league.get('matches', [])
                    for match in league_matches:
                        # 添加联赛信息到比赛数据中
                        match['league_info'] = {
                            'id': league.get('id'),
                            'name': league.get('name'),
                            'country': league.get('country'),
                        }
                        matches.append(match)

                metadata = {
                    "date": date_str,
                    "total_leagues": len(leagues),
                    "total_matches": len(matches),
                    "source": "fotmob_date_api",
                    "api_url": api_url
                }

                self.logger.info(f"Successfully collected {len(matches)} matches from {len(leagues)} leagues for date {date_str}")
                return self.create_success_result(matches, metadata)
            else:
                return self.create_error_result(f"Unexpected data format for date {date_str}")

        except Exception as e:
            self.logger.error(f"Error collecting matches for date {date_str}: {e}")
            return self.create_error_result(f"Date API collection failed for {date_str}: {e}")

    async def collect_match_details(self, match_id: str) -> CollectionResult:
        """
        收集单场比赛详情

        Args:
            match_id: 比赛 ID

        Returns:
            CollectionResult: 包含比赛详情的结果
        """
        try:
            self.logger.info(f"Collecting match details for match {match_id}")

            data = await self._make_authenticated_request(f"/api/match?id={match_id}")

            if data is None:
                return self.create_error_result(f"Failed to fetch match details for {match_id}")

            # 验证数据格式
            required_fields = ['id', 'home', 'away']
            if not all(field in data for field in required_fields):
                return self.create_error_result(f"Invalid match details format for {match_id}")

            # 添加元数据
            metadata = {
                "match_id": match_id,
                "source": "fotmob_match_details",
                "collected_at": datetime.now().isoformat(),
                "data_fields": list(data.keys())
            }

            self.logger.info(f"Successfully collected match details for {match_id}")
            return self.create_success_result(data, metadata)

        except Exception as e:
            self.logger.error(f"Error collecting match details for {match_id}: {e}")
            return self.create_error_result(f"Match details collection failed for {match_id}: {e}")

    async def collect_matches_by_date(self, date_str: str) -> CollectionResult:
        """
        按日期收集比赛数据

        Args:
            date_str: 日期字符串，格式为 YYYYMMDD

        Returns:
            CollectionResult: 包含当天所有比赛详情的结果
        """
        try:
            self.logger.info(f"Collecting matches for date {date_str} using historical API")

            # 直接使用新的历史数据接口，一步获取比赛数据
            result = await self.collect_matches_by_date_api(date_str)

            if not result.success:
                return self.create_error_result(f"Failed to get matches for date {date_str}: {result.error}")

            matches = result.data
            metadata = result.metadata or {}

            # 限制处理数量以避免过载
            max_matches = self.config.get("max_matches_per_date", 50)
            if len(matches) > max_matches:
                matches = matches[:max_matches]
                self.logger.info(f"Limited matches to {max_matches} for date {date_str}")

            # 更新元数据
            metadata.update({
                "date": date_str,
                "matches_processed": len(matches),
                "source": "fotmob_date_collection_v2"
            })

            self.logger.info(
                f"Successfully collected {len(matches)} matches for {date_str} "
                f"(from {metadata.get('total_leagues', 'unknown')} leagues)"
            )

            return self.create_success_result(matches, metadata)

            # 限制处理数量以避免过载
            max_matches = self.config.get("max_matches_per_date", 50)
            match_ids = match_ids[:max_matches]

            # 并发获取比赛详情
            match_details = []
            errors = []

            semaphore = asyncio.Semaphore(5)  # 限制并发数

            async def collect_single_match(match_id: str) -> dict[str, Any] | None:
                async with semaphore:
                    result = await self.collect_match_details(match_id)
                    if result.success:
                        return result.data
                    else:
                        errors.append(f"Match {match_id}: {result.error}")
                        return None

            # 并发执行
            tasks = [collect_single_match(match_id) for match_id in match_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for result in results:
                if isinstance(result, dict) and result is not None:
                    match_details.append(result)
                elif isinstance(result, Exception):
                    errors.append(f"Exception: {result}")

            metadata = {
                "date": date_str,
                "total_match_ids": len(match_ids),
                "successful_details": len(match_details),
                "errors": len(errors),
                "error_details": errors[:5],  # 只记录前5个错误
                "source": "fotmob_date_collection"
            }

            self.logger.info(
                f"Collected {len(match_details)} match details for {date_str} "
                f"(from {len(match_ids)} match IDs, {len(errors)} errors)"
            )

            return self.create_success_result(match_details, metadata)

        except Exception as e:
            self.logger.error(f"Error collecting matches for date {date_str}: {e}")
            return self.create_error_result(f"Date collection failed for {date_str}: {e}")

    async def collect(self, *args, **kwargs) -> CollectionResult:
        """
        主收集方法 - 根据 kwargs 决定收集策略

        支持的参数:
        - date: 收集指定日期的比赛
        - match_id: 收集指定比赛的详情
        - audio_matches: 收集音频比赛列表

        Returns:
            CollectionResult: 收集结果
        """
        if "date" in kwargs:
            date_str = kwargs["date"]
            return await self.collect_matches_by_date(date_str)

        elif "match_id" in kwargs:
            match_id = kwargs["match_id"]
            return await self.collect_match_details(match_id)

        elif "audio_matches" in kwargs:
            return await self.collect_audio_matches()

        else:
            # 默认收集昨天的数据
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            return await self.collect_matches_by_date(yesterday)

    async def close(self):
        """关闭会话"""
        if self._session:
            # curl_cffi 的 AsyncSession 可能没有 aclose 方法
            self._session = None
            self.logger.info("FotMob session closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
