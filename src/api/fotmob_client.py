#!/usr/bin/env python3
"""
FotMob API客户端 - 真实数据采集，集成Tenacity重试机制
FotMob API Client - Real Data Collection with Tenacity Retry
"""

import aiohttp
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, AsyncRetrying

logger = logging.getLogger(__name__)

# 配置常量 - 从配置系统读取
DEFAULT_API_CONFIG = {"base_url": "https://www.fotmob.com/api", "timeout": 10, "max_retries": 3, "retry_delay": 1.0}

# 熔断器配置
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,  # 连续失败次数阈值
    "recovery_timeout": 60,  # 熔断恢复时间（秒）
    "expected_exception": Exception,  # 触发熔断的异常类型
}


class CircuitState(Enum):
    """熔断器状态枚举"""

    CLOSED = "CLOSED"  # 正常状态
    OPEN = "OPEN"  # 熔断状态
    HALF_OPEN = "HALF_OPEN"  # 半开状态（试探性恢复）


class CircuitBreaker:
    """API熔断器 - 防止雪崩效应的工业级保护机制"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        初始化熔断器

        Args:
            failure_threshold: 连续失败次数阈值
            recovery_timeout: 熔断恢复时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call_allowed(self) -> bool:
        """
        检查是否允许调用API

        Returns:
            bool: True表示允许调用，False表示熔断中
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("🔌 熔断器进入半开状态，尝试恢复API调用")
                return True
            return False

        # HALF_OPEN状态允许少量调用进行试探
        return True

    def record_success(self) -> None:
        """记录成功调用，重置失败计数"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("✅ 熔断器已恢复正常，关闭熔断")

        self.failure_count = 0
        self.last_failure_time = None

    def record_failure(self, exception: Exception) -> None:
        """
        记录失败调用

        Args:
            exception: 异常对象
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"🚨 API熔断器触发！连续失败{self.failure_count}次，熔断{self.recovery_timeout}秒")
            logger.warning(f"触发异常类型: {type(exception).__name__}: {str(exception)}")


class FotMobAPIClient:
    """FotMob API客户端 - 集成Tenacity重试机制和熔断器保护"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        circuit_breaker_failure_threshold: Optional[int] = None,
        circuit_breaker_recovery_timeout: Optional[int] = None,
    ):
        """
        初始化API客户端

        Args:
            base_url: API基础URL，默认从配置读取
            timeout: 请求超时时间（秒），默认从配置读取
            max_retries: 最大重试次数，默认从配置读取
            retry_delay: 重试延迟基数（秒），默认从配置读取
            circuit_breaker_failure_threshold: 熔断器失败阈值，默认5次
            circuit_breaker_recovery_timeout: 熔断器恢复时间（秒），默认60秒
        """
        # 使用配置系统或默认值
        self.base_url = base_url or DEFAULT_API_CONFIG["base_url"]
        timeout_val = timeout or DEFAULT_API_CONFIG["timeout"]
        self.timeout = aiohttp.ClientTimeout(total=timeout_val)
        self.max_retries = max_retries or DEFAULT_API_CONFIG["max_retries"]
        self.retry_delay = retry_delay or DEFAULT_API_CONFIG["retry_delay"]
        self.session = None

        # 初始化熔断器
        cb_threshold = circuit_breaker_failure_threshold or CIRCUIT_BREAKER_CONFIG["failure_threshold"]
        cb_timeout = circuit_breaker_recovery_timeout or CIRCUIT_BREAKER_CONFIG["recovery_timeout"]
        self.circuit_breaker = CircuitBreaker(failure_threshold=cb_threshold, recovery_timeout=cb_timeout)

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
        ),
    )
    async def get_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取比赛详情（带重试机制和熔断器保护）

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]]: 比赛数据或None
        """
        # 检查熔断器状态
        if not self.circuit_breaker.call_allowed():
            logger.warning(f"🚫 API熔断器拒绝调用 - Match ID: {match_id}，熔断中")
            return None

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
                    self.circuit_breaker.record_success()
                    return data
                else:
                    error_msg = f"API请求失败 - Status: {response.status}, Match ID: {match_id}"
                    logger.error(error_msg)
                    exc = aiohttp.ClientResponseError(
                        request_info=response.request_info, history=response.history, status=response.status
                    )
                    self.circuit_breaker.record_failure(exc)
                    raise exc
        except asyncio.TimeoutError as e:
            error_msg = f"API请求超时 - Match ID: {match_id}"
            logger.error(error_msg)
            self.circuit_breaker.record_failure(e)
            raise
        except aiohttp.ClientError as e:
            error_msg = f"API客户端错误 - Match ID: {match_id}, Error: {e}"
            logger.error(error_msg)
            self.circuit_breaker.record_failure(e)
            raise
        except Exception as e:
            error_msg = f"API请求异常 - Match ID: {match_id}, Error: {e}"
            logger.error(error_msg)
            # 非网络错误不重试，但记录熔断器状态
            self.circuit_breaker.record_failure(e)
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
                    matches = data.get("matches", [])
                    logger.info(f"成功获取 {len(matches)} 场比赛")
                    return matches
                else:
                    logger.error(f"API请求失败 - Status: {response.status}, Date: {date_str}")
                    return None
        except Exception as e:
            logger.error(f"API请求异常 - Date: {date_str}, Error: {e}")
            return None

    async def get_league_matches(
        self, league_id: str, season_id: str = None, fetch_history: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
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
                    if "data" in data:
                        league_data = data["data"]
                        if "matches" in league_data:
                            matches = league_data["matches"]
                        elif "allMatches" in league_data:
                            matches = league_data["allMatches"]
                        elif "matches" in league_data.get("stats", {}):
                            matches = league_data["stats"]["matches"]
                    elif "fixtures" in data and "allMatches" in data["fixtures"]:
                        matches = data["fixtures"]["allMatches"]
                    elif "allMatches" in data:
                        matches = data["allMatches"]
                    elif "matches" in data:
                        matches = data["matches"]

                    # 过滤比赛 - 只保留2025-08-01至今的完场比赛
                    filtered_matches = []
                    from datetime import datetime, timezone

                    for match in matches:
                        # 检查比赛状态和时间
                        status = match.get("status", {}).get("finished", False)
                        match_time_str = match.get("status", {}).get("utcTime", "") or match.get("time", {}).get(
                            "utcTime", ""
                        )

                        # 只处理完场比赛且在指定时间范围内
                        if status and match_time_str:
                            try:
                                # 解析比赛时间
                                if "T" in match_time_str:
                                    match_time = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                                else:
                                    # 处理其他时间格式
                                    match_time = datetime.strptime(match_time_str[:10], "%Y-%m-%d").replace(
                                        tzinfo=timezone.utc
                                    )

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
