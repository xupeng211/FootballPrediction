#!/usr/bin/env python3
"""
赔率数据采集客户端 (Odds API Client) - V1.0
=====================================
功能:
- 异步采集赔率数据 (基于 aiohttp)
- 代理支持 (WSL2 环境适配)
- Pydantic 数据校验
- UPSERT 入库逻辑
- tenacity 指数退避重试
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import os
from typing import Any

import aiohttp
from pydantic import BaseModel, Field, field_validator, model_validator
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config_unified import get_settings

logger = logging.getLogger(__name__)

# ============================================================
# V37.0 继承: 深度反爬盔甲
# ============================================================

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

LANGUAGE_POOL = [
    "en-US,en;q=0.9,en-GB;q=0.8",
    "en-GB,en;q=0.9",
]

# ============================================================
# Pydantic 数据模型
# ============================================================


class MarketPriceSchema(BaseModel):
    """赔率数据校验模型"""

    match_id: str = Field(..., description="关联 matches.match_id")
    external_id: str | None = Field(None, description="外部比赛ID")
    provider: str = Field(..., description="数据源 (bet365, william_hill, etc.)")
    home_win_odds: float | None = Field(None, gt=0, description="主胜赔率")
    draw_odds: float | None = Field(None, gt=0, description="平局赔率")
    away_win_odds: float | None = Field(None, gt=0, description="客胜赔率")
    asian_handicap_home: float | None = Field(None, description="亚盘主队让球")
    asian_handicap_home_odds: float | None = Field(None, gt=0, description="亚盘主队赔率")
    over_under_line: float | None = Field(None, description="大小球盘口")
    over_odds: float | None = Field(None, gt=0, description="大球赔率")
    under_odds: float | None = Field(None, gt=0, description="小球赔率")
    market_type: str = Field(default="1X2", description="市场类型 (1X2, AH, OU)")
    is_opening: bool = Field(default=False, description="是否为初盘赔率")
    is_closing: bool = Field(default=False, description="是否为终盘赔率")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"bet365", "william_hill", "ladbrokes", "pinnacle", "betfair", "unibet", "bwin", "other"}
        if v.lower() not in allowed:
            logger.warning(f"Unknown provider: {v}, defaulting to 'other'")
            return "other"
        return v.lower()

    @field_validator("market_type")
    @classmethod
    def validate_market_type(cls, v: str) -> str:
        allowed = {"1X2", "AH", "OU", "ALL"}
        if v.upper() not in allowed:
            raise ValueError(f"Invalid market_type: {v}")
        return v.upper()

    @model_validator(mode="after")
    def validate_odds_not_all_none(self) -> "MarketPriceSchema":
        if self.home_win_odds is None and self.draw_odds is None and self.away_win_odds is None:
            if self.asian_handicap_home_odds is None and self.over_odds is None and self.under_odds is None:
                raise ValueError("至少需要提供一种赔率类型")
        return self


@dataclass
class OddsCollectionStats:
    """采集统计"""

    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    rate_limited: int = 0
    database_errors: int = 0
    retry_count: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful / self.total_requests) * 100


# ============================================================
# 赔率采集客户端
# ============================================================


class OddsAPIClient:
    """赔率数据采集客户端 - V1.0"""

    # 限流配置
    RATE_LIMIT = {"requests": 100, "window": 60}  # 100 req/min
    BASE_DELAY = (1.0, 2.0)  # 随机延迟区间 (秒)
    MAX_CONCURRENT = 3  # 最大并发数 (与 V37 保持一致)

    def __init__(
        self,
        proxy_url: str | None = None,
        db_config: dict | None = None,
        semaphore_limit: int = 3,
    ):
        """
        初始化赔率采集客户端

        Args:
            proxy_url: 代理 URL (默认从环境变量读取)
            db_config: 数据库配置 (默认从 config_unified 读取)
            semaphore_limit: 并发限制
        """
        self.settings = get_settings()

        # 代理配置
        self.proxy_url = proxy_url or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

        # 数据库配置
        if db_config is None:
            db_config = {
                "host": self.settings.database.host,
                "port": self.settings.database.port,
                "database": "football_prediction_dev",  # 生产环境数据库名
                "user": self.settings.database.user,
                "password": self.settings.database.password.get_secret_value(),
            }
        self.db_config = db_config

        # 并发控制
        self.semaphore = asyncio.Semaphore(semaphore_limit)

        # 统计
        self.stats = OddsCollectionStats()

        logger.info(f"OddsAPIClient 初始化完成 | 并发限制: {semaphore_limit} | 代理: {self.proxy_url}")

    # ============================================================
    # 网络请求 (带重试和代理支持)
    # ============================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """
        异步 HTTP 请求 (带重试和代理)

        Args:
            session: aiohttp 会话
            url: 请求 URL
            params: 查询参数

        Returns:
            响应 JSON 数据
        """
        headers = {
            "User-Agent": os.environ.get("CUSTOM_USER_AGENT", UA_POOL[0]),
            "Accept-Language": LANGUAGE_POOL[0],
            "Accept": "application/json",
        }

        proxy = self.proxy_url if self.proxy_url else None

        try:
            async with session.get(url, params=params, headers=headers, proxy=proxy, timeout=aiohttp.ClientTimeout(total=30)) as response:
                # 429 Too Many Requests
                if response.status == 429:
                    self.stats.rate_limited += 1
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"触发限流，等待 {retry_after} 秒...")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Rate limited (429), Retry-After: {retry_after}",
                    )

                # 其他错误响应
                response.raise_for_status()
                data = await response.json()
                self.stats.successful += 1
                return data

        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                raise  # 触发重试
            self.stats.failed += 1
            logger.error(f"HTTP 错误: {e.status} | {url}")
            raise

    # ============================================================
    # 数据入库 (UPSERT)
    # ============================================================

    async def save_to_db(self, odds_data: MarketPriceSchema) -> bool:
        """
        保存赔率数据到数据库 (UPSERT)

        Args:
            odds_data: 赔率数据 (经过 Pydantic 校验)

        Returns:
            是否成功
        """
        import psycopg2
        from psycopg2.extras import RealDictCursor

        try:
            conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
            cursor = conn.cursor()

            upsert_sql = """
            INSERT INTO match_odds (
                match_id, external_id, provider,
                home_win_odds, draw_odds, away_win_odds,
                asian_handicap_home, asian_handicap_home_odds,
                over_under_line, over_odds, under_odds,
                market_type, is_opening, is_closing, timestamp
            ) VALUES (
                %(match_id)s, %(external_id)s, %(provider)s,
                %(home_win_odds)s, %(draw_odds)s, %(away_win_odds)s,
                %(asian_handicap_home)s, %(asian_handicap_home_odds)s,
                %(over_under_line)s, %(over_odds)s, %(under_odds)s,
                %(market_type)s, %(is_opening)s, %(is_closing)s, %(timestamp)s
            )
            ON CONFLICT (match_id, provider, timestamp)
            DO UPDATE SET
                home_win_odds = EXCLUDED.home_win_odds,
                draw_odds = EXCLUDED.draw_odds,
                away_win_odds = EXCLUDED.away_win_odds,
                asian_handicap_home = EXCLUDED.asian_handicap_home,
                asian_handicap_home_odds = EXCLUDED.asian_handicap_home_odds,
                over_under_line = EXCLUDED.over_under_line,
                over_odds = EXCLUDED.over_odds,
                under_odds = EXCLUDED.under_odds,
                is_opening = EXCLUDED.is_opening,
                is_closing = EXCLUDED.is_closing;
            """

            cursor.execute(upsert_sql, odds_data.model_dump())
            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            self.stats.database_errors += 1
            logger.error(f"数据库入库失败: {e} | match_id: {odds_data.match_id}")
            return False

    # ============================================================
    # 公共接口
    # ============================================================

    async def collect_match_odds(
        self,
        match_id: str,
        external_id: str | None = None,
        provider: str = "bet365",
    ) -> MarketPriceSchema | None:
        """
        采集单场比赛赔率 (示例接口)

        Args:
            match_id: 比赛 ID
            external_id: 外部比赛 ID
            provider: 数据源

        Returns:
            赔率数据 (校验后)
        """
        async with self.semaphore:
            self.stats.total_requests += 1

            # 示例: 这里需要替换为实际的赔率 API 端点
            # 目前返回模拟数据用于验证
            mock_data = MarketPriceSchema(
                match_id=match_id,
                external_id=external_id,
                provider=provider,
                home_win_odds=2.50,
                draw_odds=3.20,
                away_win_odds=2.80,
                market_type="1X2",
                is_opening=True,
            )

            # 入库
            if await self.save_to_db(mock_data):
                logger.debug(f"赔率数据已入库 | match_id: {match_id} | provider: {provider}")
                return mock_data

            return None

    async def collect_batch(
        self,
        matches: list[dict[str, Any]],
        provider: str = "bet365",
    ) -> list[MarketPriceSchema]:
        """
        批量采集赔率

        Args:
            matches: 比赛列表 [{"match_id": "...", "external_id": "..."}]
            provider: 数据源

        Returns:
            采集到的赔率数据列表
        """
        tasks = [
            self.collect_match_odds(m["match_id"], m.get("external_id"), provider)
            for m in matches
        ]

        # 添加随机延迟，避免触发限流
        results = []
        for i, task in enumerate(tasks):
            result = await task
            if result:
                results.append(result)

            # 最后一个任务不延迟
            if i < len(tasks) - 1:
                delay = __import__("random").uniform(*self.BASE_DELAY)
                await asyncio.sleep(delay)

        logger.info(
            f"批量采集完成 | 总计: {len(matches)} | "
            f"成功: {len(results)} | 成功率: {len(results)/len(matches)*100:.1f}%"
        )

        return results

    def get_stats(self) -> dict[str, Any]:
        """获取采集统计"""
        return {
            "total_requests": self.stats.total_requests,
            "successful": self.stats.successful,
            "failed": self.stats.failed,
            "rate_limited": self.stats.rate_limited,
            "database_errors": self.stats.database_errors,
            "success_rate": f"{self.stats.success_rate():.2f}%",
            "elapsed_seconds": (datetime.now(UTC) - self.stats.start_time).total_seconds(),
        }


# ============================================================
# 便捷函数
# ============================================================

async def quick_collect(
    matches: list[dict[str, Any]],
    proxy_url: str | None = None,
) -> list[MarketPriceSchema]:
    """
    快速采集赔率数据

    Args:
        matches: 比赛列表
        proxy_url: 代理 URL (默认从环境变量读取)

    Returns:
        采集到的赔率数据列表
    """
    client = OddsAPIClient(proxy_url=proxy_url)
    return await client.collect_batch(matches)


if __name__ == "__main__":
    # 测试代码
    async def main():
        client = OddsAPIClient()
        test_matches = [
            {"match_id": "test_001", "external_id": "ext_001"},
            {"match_id": "test_002", "external_id": "ext_002"},
        ]
        results = await client.collect_batch(test_matches)
        print(f"采集结果: {len(results)} 条")
        print(f"统计: {client.get_stats()}")

    asyncio.run(main())
