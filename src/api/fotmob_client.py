#!/usr/bin/env python3
"""
FotMob API客户端 - 真实数据采集，集成Tenacity重试机制
FotMob API Client - Real Data Collection with Tenacity Retry
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, AsyncRetrying

logger = logging.getLogger(__name__)


class FotMobAPIClient:
    """FotMob API客户端 - 集成Tenacity重试机制"""

    def __init__(self, base_url: str = "https://www.fotmob.com/api", timeout: int = 10,
                 max_retries: int = 3, retry_delay: float = 1.0):
        """初始化API客户端

        Args:
            base_url: API基础URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟基数（秒）
        """
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, aiohttp.ClientError)),
        before_sleep=lambda retry_state: logger.warning(
            f"API请求重试 {retry_state.attempt_number}/3 - Match ID: {retry_state.kwargs.get('match_id', 'unknown')}"
        )
    )
    async def get_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛详情（带重试机制）

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]]: 比赛数据或None
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        url = f"{self.base_url}/matchDetails"
        params = {"matchId": match_id}

        try:
            logger.info(f"获取比赛详情 - Match ID: {match_id}")
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"成功获取比赛 {match_id} 的数据")
                    return data
                else:
                    logger.error(f"API请求失败 - Status: {response.status}, Match ID: {match_id}")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
        except asyncio.TimeoutError:
            logger.error(f"API请求超时 - Match ID: {match_id}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"API客户端错误 - Match ID: {match_id}, Error: {e}")
            raise
        except Exception as e:
            logger.error(f"API请求异常 - Match ID: {match_id}, Error: {e}")
            # 非网络错误不重试
            return None

    async def get_match_data(self, match_id: str) -> Dict[str, Any]:
        """实现DataClientProtocol接口"""
        data = await self.get_match_details(match_id)
        return data if data is not None else {}

    async def get_multiple_matches(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """批量获取比赛数据（实现DataClientProtocol接口）"""
        tasks = [self.get_match_details(match_id) for match_id in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        matches = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"获取比赛 {match_ids[i]} 失败: {result}")
                matches.append({})
            elif result is not None:
                matches.append(result)
            else:
                matches.append({})

        return matches

    async def get_matches_by_date(self, date_str: str) -> Optional[List[Dict[str, Any]]]:
        """根据日期获取比赛列表

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)

        Returns:
            Optional[List[Dict[str, Any]]]: 比赛列表或None
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        url = f"{self.base_url}/matchesByDate"
        params = {"date": date_str}

        try:
            logger.info(f"获取日期 {date_str} 的比赛列表")
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get('matches', [])
                    logger.info(f"成功获取 {len(matches)} 场比赛")
                    return matches
                else:
                    logger.error(f"API请求失败 - Status: {response.status}, Date: {date_str}")
                    return None
        except Exception as e:
            logger.error(f"API请求异常 - Date: {date_str}, Error: {e}")
            return None

    async def get_league_matches(self, league_id: str, season_id: str = None, fetch_history: bool = True) -> Optional[List[Dict[str, Any]]]:
        """获取联赛比赛列表（L1索引同步）- 支持历史赛果抓取

        Args:
            league_id: 联赛ID (英超: 47, 德甲: 54)
            season_id: 赛季ID
            fetch_history: 是否抓取历史赛果（默认True）

        Returns:
            Optional[List[Dict[str, Any]]]: 比赛列表或None
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        # 构建正确的API URL
        if fetch_history:
            # 抓取历史赛果 - 使用results端点
            url = f"{self.base_url}/leagues"
            params = {"id": league_id, "tab": "results"}
            if season_id:
                params["seasonId"] = season_id
        else:
            # 抓取未来赛程
            url = f"{self.base_url}/leagues"
            params = {"id": league_id, "tab": "fixtures"}
            if season_id:
                params["seasonId"] = season_id

        try:
            if fetch_history:
                logger.info(f"获取联赛 {league_id} 的历史赛果（2025-08-01至今）")
            else:
                logger.info(f"获取联赛 {league_id} 的未来赛程")

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # 提取比赛数据
                    matches = []

                    # 从FotMob API实际数据结构中提取比赛
                    if 'data' in data:
                        league_data = data['data']
                        if 'matches' in league_data:
                            matches = league_data['matches']
                        elif 'allMatches' in league_data:
                            matches = league_data['allMatches']
                        elif 'matches' in league_data.get('stats', {}):
                            matches = league_data['stats']['matches']
                    elif 'fixtures' in data and 'allMatches' in data['fixtures']:
                        matches = data['fixtures']['allMatches']
                    elif 'allMatches' in data:
                        matches = data['allMatches']
                    elif 'matches' in data:
                        matches = data['matches']

                    # 过滤比赛 - 只保留2025-08-01至今的完场比赛
                    filtered_matches = []
                    from datetime import datetime, timezone

                    for match in matches:
                        # 检查比赛状态和时间
                        status = match.get('status', {}).get('finished', False)
                        match_time_str = match.get('status', {}).get('utcTime', '') or match.get('time', {}).get('utcTime', '')

                        # 只处理完场比赛且在指定时间范围内
                        if status and match_time_str:
                            try:
                                # 解析比赛时间
                                if 'T' in match_time_str:
                                    match_time = datetime.fromisoformat(match_time_str.replace('Z', '+00:00'))
                                else:
                                    # 处理其他时间格式
                                    match_time = datetime.strptime(match_time_str[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)

                                # 检查是否在2025-08-01之后
                                cutoff_date = datetime(2025, 8, 1, tzinfo=timezone.utc)
                                if match_time >= cutoff_date:
                                    filtered_matches.append(match)

                            except (ValueError, TypeError) as e:
                                logger.warning(f"无法解析比赛时间 {match_time_str}: {e}")
                                continue

                    logger.info(f"成功获取联赛 {league_id} 的 {len(filtered_matches)} 场历史完场比赛")
                    return filtered_matches
                else:
                    logger.error(f"API请求失败 - Status: {response.status}, League ID: {league_id}")
                    return None
        except Exception as e:
            logger.error(f"API请求异常 - League ID: {league_id}, Error: {e}")
            return None


# 便捷函数
async def fetch_match_data(match_id: str) -> Optional[Dict[str, Any]]:
    """获取比赛数据的便捷函数

    Args:
        match_id: 比赛ID

    Returns:
        Optional[Dict[str, Any]]: 比赛数据或None
    """
    async with FotMobAPIClient() as client:
        return await client.get_match_details(match_id)