#!/usr/bin/env python3
"""
GhostRequester - V175 混合动力请求器
=====================================

混合架构核心组件:
- 接收浏览器截获的完整 Passport (x-mas + Cookie + Headers)
- 使用 curl_cffi 模拟 Chrome TLS 指纹
- 批量极速重放 API 请求

⚠️ 重要发现 (2026-03-01):
===========================
FotMob API 端点受到 **Cloudflare Turnstile** 人机验证保护！

混合方案:
1. 浏览器通过 Turnstile 验证
2. 截获完整的请求头 (包括动态 x-mas)
3. curl_cffi 使用截获的凭证进行批量请求

用法:
    # 直接运行测试
    python src/core/network/ghost_requester.py --match-ids 4803191,4803189 --passport '{"x_mas":"...","cookie":"..."}'

    # 作为模块导入
    from src.core.network.ghost_requester import GhostRequester
    async with GhostRequester() as requester:
        result = await requester.fetch_match(4803191, passport)

@module core/network/ghost_requester
@version V175.1.0
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from pathlib import Path

# curl_cffi - TLS 指纹模拟核心
from curl_cffi import requests as curl_requests
from curl_cffi.requests import AsyncSession

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class GhostResult:
    """隐身请求结果"""
    success: bool
    status_code: int
    match_id: str = ""
    data: Optional[dict] = None
    error: Optional[str] = None
    response_time_ms: float = 0.0
    size_bytes: int = 0
    url: str = ""
    tls_fingerprint: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Passport:
    """
    API 通行证 (从浏览器截获)

    包含浏览器通过 Turnstile 验证后的完整凭证
    """
    x_mas: str
    cookie: str = ""
    user_agent: str = ""
    accept: str = "*/*"
    accept_language: str = "en-US,en;q=0.9"
    referer: str = "https://www.fotmob.com/"
    origin: str = "https://www.fotmob.com"

    # 额外请求头
    extra_headers: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, json_str: str) -> 'Passport':
        """从 JSON 字符串创建 Passport"""
        data = json.loads(json_str)
        return cls(
            x_mas=data.get('x_mas', data.get('xMas', '')),
            cookie=data.get('cookie', ''),
            user_agent=data.get('user_agent', data.get('userAgent', '')),
            accept=data.get('accept', '*/*'),
            accept_language=data.get('accept_language', 'en-US,en;q=0.9'),
            referer=data.get('referer', 'https://www.fotmob.com/'),
            origin=data.get('origin', 'https://www.fotmob.com'),
            extra_headers=data.get('extra_headers', {})
        )

    def to_headers(self) -> dict:
        """转换为请求头字典"""
        headers = {
            'accept': self.accept,
            'accept-language': self.accept_language,
            'accept-encoding': 'gzip, deflate, br',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.referer,
            'origin': self.origin,
            'sec-ch-ua': '"Chromium";v="120", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
        }

        # 添加 x-mas 令牌
        if self.x_mas:
            headers['x-mas'] = self.x_mas

        # 添加 User-Agent
        if self.user_agent:
            headers['user-agent'] = self.user_agent

        # 添加额外请求头
        headers.update(self.extra_headers)

        return headers


@dataclass
class BatchResult:
    """批量请求结果"""
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: list = field(default_factory=list)
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    success_rate: float = 0.0

    def calculate_stats(self):
        """计算统计信息"""
        self.successful = sum(1 for r in self.results if r.success)
        self.failed = self.total - self.successful
        self.success_rate = (self.successful / self.total * 100) if self.total > 0 else 0
        self.avg_time_ms = sum(r.response_time_ms for r in self.results) / self.total if self.total > 0 else 0

    def to_dict(self) -> dict:
        return {
            'total': self.total,
            'successful': self.successful,
            'failed': self.failed,
            'success_rate': self.success_rate,
            'total_time_ms': self.total_time_ms,
            'avg_time_ms': self.avg_time_ms,
            'results': [r.to_dict() for r in self.results]
        }


# ============================================================================
# 配置常量
# ============================================================================

# FotMob API 端点
FOTMOB_API = {
    "match_details": "https://www.fotmob.com/api/data/matchDetails",
    "match_details_legacy": "https://www.fotmob.com/api/matchDetails",
}

# Chrome 浏览器指纹版本
CHROME_VERSION = "chrome120"


# ============================================================================
# GhostRequester - 隐身请求器
# ============================================================================

class GhostRequester:
    """
    V175 混合动力请求器

    特性:
    - TLS 指纹伪装 (curl_cffi)
    - 接收浏览器截获的完整 Passport
    - 批量极速重放

    示例:
        >>> async with GhostRequester() as requester:
        ...     passport = Passport.from_json('{"x_mas":"...","cookie":"..."}')
        ...     result = await requester.fetch_match("4803191", passport)
    """

    def __init__(
        self,
        chrome_version: str = CHROME_VERSION,
        proxy: Optional[str] = None,
        timeout: int = 30
    ):
        self.chrome_version = chrome_version
        self.proxy = proxy
        self.timeout = timeout
        self.session: Optional[AsyncSession] = None

        self.stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_time_ms": 0.0,
        }

        logger.info(f"🕵️ GhostRequester 初始化: Chrome={chrome_version}")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        """初始化异步会话"""
        if self.session is None:
            self.session = AsyncSession(
                impersonate=self.chrome_version,
                proxy=self.proxy,
                timeout=self.timeout,
                verify=True,
            )
            logger.info(f"✅ AsyncSession 创建成功: TLS={self.chrome_version}")

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None

    def _parse_cookies(self, cookie_str: str) -> dict:
        """解析 Cookie 字符串"""
        cookies = {}
        if cookie_str:
            for item in cookie_str.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value
        return cookies

    async def fetch_match(
        self,
        match_id: str,
        passport: Passport,
        use_legacy_url: bool = False
    ) -> GhostResult:
        """
        获取比赛详情

        Args:
            match_id: 比赛 ID
            passport: 浏览器截获的通行证
            use_legacy_url: 是否使用旧版 URL

        Returns:
            GhostResult: 请求结果
        """
        if not self.session:
            await self.initialize()

        # 选择 API 端点
        base_url = FOTMOB_API["match_details_legacy"] if use_legacy_url else FOTMOB_API["match_details"]
        url = f"{base_url}?matchId={match_id}"

        # 构建请求头
        headers = passport.to_headers()

        # 解析 Cookie
        cookies = self._parse_cookies(passport.cookie)

        start_time = time.perf_counter()
        self.stats["total_requests"] += 1

        try:
            logger.info(f"🌐 请求: matchId={match_id}")

            response = await self.session.get(
                url,
                headers=headers,
                cookies=cookies if cookies else None,
            )

            response_time_ms = (time.perf_counter() - start_time) * 1000
            self.stats["total_time_ms"] += response_time_ms

            if response.status_code == 200:
                try:
                    data = response.json()
                    size = len(response.content)
                    self.stats["successful"] += 1

                    # 提取比赛信息
                    home_team = "Unknown"
                    away_team = "Unknown"
                    if data and "content" in data:
                        participants = data["content"].get("header", {}).get("participants", [])
                        if len(participants) >= 2:
                            home_team = participants[0].get("name", "Unknown")
                            away_team = participants[1].get("name", "Unknown")

                    logger.info(f"   ✅ 成功! {home_team} vs {away_team} | {size} bytes | {response_time_ms:.0f}ms")

                    return GhostResult(
                        success=True,
                        status_code=response.status_code,
                        match_id=match_id,
                        data=data,
                        response_time_ms=response_time_ms,
                        size_bytes=size,
                        url=url,
                        tls_fingerprint=self.chrome_version
                    )
                except json.JSONDecodeError as e:
                    self.stats["failed"] += 1
                    logger.error(f"   ❌ JSON 解析失败: {e}")
                    return GhostResult(
                        success=False,
                        status_code=response.status_code,
                        match_id=match_id,
                        error=f"JSON 解析失败: {e}",
                        response_time_ms=response_time_ms,
                        url=url
                    )
            else:
                self.stats["failed"] += 1
                error_msg = f"HTTP {response.status_code}"

                # 尝试解析错误响应
                try:
                    error_data = response.json()
                    error_code = error_data.get("code", "UNKNOWN")
                    error_msg = f"HTTP {response.status_code} ({error_code})"
                    logger.error(f"   ❌ {error_msg}")
                except:
                    logger.error(f"   ❌ {error_msg}")

                return GhostResult(
                    success=False,
                    status_code=response.status_code,
                    match_id=match_id,
                    error=error_msg,
                    response_time_ms=response_time_ms,
                    url=url
                )

        except Exception as e:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self.stats["failed"] += 1
            logger.error(f"   ❌ 请求异常: {e}")

            return GhostResult(
                success=False,
                status_code=0,
                match_id=match_id,
                error=str(e),
                response_time_ms=response_time_ms,
                url=url
            )

    async def fetch_batch(
        self,
        match_ids: list[str],
        passport: Passport,
        delay_ms: float = 500
    ) -> BatchResult:
        """
        批量获取比赛详情

        Args:
            match_ids: 比赛 ID 列表
            passport: 浏览器截获的通行证
            delay_ms: 请求间隔 (毫秒)

        Returns:
            BatchResult: 批量结果
        """
        batch_start = time.perf_counter()
        results = []

        logger.info(f"\n🚀 开始批量请求: {len(match_ids)} 场比赛")
        logger.info(f"   TLS 指纹: {self.chrome_version}")
        logger.info(f"   x-mas 长度: {len(passport.x_mas)} 字符")
        logger.info(f"   Cookie 长度: {len(passport.cookie)} 字符")
        print()

        for i, match_id in enumerate(match_ids):
            logger.info(f"[{i + 1}/{len(match_ids)}]", )

            result = await self.fetch_match(match_id, passport)
            results.append(result)

            # 延迟
            if i < len(match_ids) - 1 and delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

        batch_time_ms = (time.perf_counter() - batch_start) * 1000

        batch_result = BatchResult(
            total=len(match_ids),
            results=results,
            total_time_ms=batch_time_ms
        )
        batch_result.calculate_stats()

        return batch_result

    def get_stats(self) -> dict:
        """获取统计信息"""
        avg_time = (
            self.stats["total_time_ms"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0 else 0
        )
        success_rate = (
            self.stats["successful"] / self.stats["total_requests"] * 100
            if self.stats["total_requests"] > 0 else 0
        )

        return {
            **self.stats,
            "avg_time_ms": avg_time,
            "success_rate": success_rate
        }


# ============================================================================
# CLI 入口
# ============================================================================

async def run_batch_test(match_ids: list[str], passport_json: str):
    """运行批量测试"""
    print("\n" + "=" * 60)
    print("  V175 Hybrid Strike - 混合动力批量测试")
    print("=" * 60 + "\n")

    # 解析 Passport
    try:
        passport = Passport.from_json(passport_json)
        print(f"📋 Passport 解析成功:")
        print(f"   x-mas: {passport.x_mas[:50]}...")
        print(f"   Cookie: {passport.cookie[:50] if passport.cookie else '(空)'}...")
        print(f"   User-Agent: {passport.user_agent[:50] if passport.user_agent else '(默认)'}...")
    except Exception as e:
        print(f"❌ Passport 解析失败: {e}")
        return

    # 创建请求器
    async with GhostRequester() as requester:
        # 批量请求
        batch_result = await requester.fetch_batch(match_ids, passport)

        # 打印结果
        print("\n" + "=" * 60)
        print("  批量测试结果")
        print("=" * 60)
        print(f"\n📊 统计:")
        print(f"   总请求数: {batch_result.total}")
        print(f"   成功: {batch_result.successful}")
        print(f"   失败: {batch_result.failed}")
        print(f"   成功率: {batch_result.success_rate:.1f}%")
        print(f"   总耗时: {batch_result.total_time_ms:.0f}ms")
        print(f"   平均耗时: {batch_result.avg_time_ms:.0f}ms")

        # 成功详情
        successes = [r for r in batch_result.results if r.success]
        if successes:
            print(f"\n✅ 成功的比赛:")
            for r in successes:
                if r.data:
                    content = r.data.get("content", {})
                    header = content.get("header", {})
                    participants = header.get("participants", [])
                    if len(participants) >= 2:
                        home = participants[0].get("name", "?")
                        away = participants[1].get("name", "?")
                        print(f"   - {r.match_id}: {home} vs {away} ({r.size_bytes} bytes)")

        # 失败详情
        failures = [r for r in batch_result.results if not r.success]
        if failures:
            print(f"\n❌ 失败的比赛:")
            for r in failures:
                print(f"   - {r.match_id}: {r.error}")

        # 输出 JSON 结果 (供 Node.js 解析)
        print("\n📦 JSON 结果:")
        print(json.dumps(batch_result.to_dict(), ensure_ascii=False))

        return batch_result


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="V175 GhostRequester - 混合动力请求器")
    parser.add_argument("--match-ids", type=str, required=True, help="比赛 ID 列表 (逗号分隔)")
    parser.add_argument("--passport", type=str, required=True, help="Passport JSON 字符串")
    parser.add_argument("--chrome", type=str, default=CHROME_VERSION, help="Chrome 版本指纹")

    args = parser.parse_args()

    # 解析比赛 ID
    match_ids = [id.strip() for id in args.match_ids.split(",")]

    asyncio.run(run_batch_test(match_ids, args.passport))


if __name__ == "__main__":
    main()
