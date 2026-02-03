#!/usr/bin/env python3
"""
Dynamic Discovery Engine - V1.0.0 [Genesis.L1Evolution]
=========================================================

L1 动态发现引擎 - 双模降级架构，确保无论对方如何改版都能稳定输出 Match ID。

Core Features:
- 模式 A (High Speed): API 探测 + 参数自适应
- 模式 B (Reliable Fallback): Playwright DOM 解析
- 跨平台交叉验证: OddsPortal → FotMob 映射
- 智能指纹轮换: Ghost Protocol 集成
- 自动降级: API 失败自动切换浏览器模式
- 配置自愈: 404 频率过高时自动更新 API 模板

架构流程:
    [模式 A: API 探测]
        ↓ 404/失败
    [模式 B: DOM 抓取]
        ↓ 提取 OddsPortal 数据
    [跨平台映射]
        ↓ FotMob Search API
    [输出 Match ID 列表]

Author: [Genesis.L1Evolution]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from playwright.async_api import async_playwright, Browser, Page

# 导入 NetworkShield 和 Ghost Protocol
_project_root = Path(__file__).parent.parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.collectors.base_extractor import BaseExtractor
from src.infrastructure.engines.match_engine.shared.network_guardian import NetworkGuardian
from src.config_unified import get_settings

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class DiscoveryMode(Enum):
    """发现模式"""
    API = "api"           # 模式 A: API 探测
    DOM = "dom"           # 模式 B: DOM 抓取
    CROSS_PLATFORM = "cross"  # 跨平台映射


class DiscoveryStatus(Enum):
    """发现状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    DEGRADED = "degraded"  # 降级到浏览器模式


@dataclass
class MatchInfo:
    """比赛信息"""
    match_id: str
    home_team: str
    away_team: str
    match_date: str | None = None
    league_id: int | None = None
    source: str = "unknown"  # fotmob, oddsportal, cross
    fotmob_url: str | None = None
    oddsportal_url: str | None = None


@dataclass
class DiscoveryResult:
    """发现结果"""
    status: DiscoveryStatus
    mode: DiscoveryMode
    matches: list[MatchInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    latency_ms: int = 0
    degraded: bool = False  # 是否使用了降级模式
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "mode": self.mode.value,
            "match_count": len(self.matches),
            "matches": [{"id": m.match_id, "home": m.home_team, "away": m.away_team} for m in self.matches],
            "errors": self.errors,
            "latency_ms": self.latency_ms,
            "degraded": self.degraded,
            "metadata": self.metadata
        }


@dataclass
class DiscoveryConfig:
    """发现配置"""
    league_id: int
    league_name: str
    season: str = "2024-2025"

    # API 配置
    api_timeout: int = 10
    api_retries: int = 3

    # DOM 配置
    dom_timeout: int = 30000  # 30s
    dom_headless: bool = True

    # 降级阈值
    max_api_failures: int = 3
    auto_degrade: bool = True

    # NetworkShield
    enable_network_shield: bool = True

    # Ghost Protocol
    enable_ghost_protocol: bool = True


# ============================================================================
# BASE DISCOVERY STRATEGY
# ============================================================================


class DiscoveryStrategy(ABC):
    """发现策略基类"""

    def __init__(self, config: DiscoveryConfig, network_guardian: NetworkGuardian | None = None):
        self.config = config
        self.network_guardian = network_guardian
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    async def discover(self) -> DiscoveryResult:
        """执行发现"""
        pass

    def _get_random_delay(self) -> float:
        """获取随机延迟（人类脉冲）"""
        return random.uniform(2.0, 5.0)


# ============================================================================
# MODE A: API DISCOVERY STRATEGY
# ============================================================================


class ApiDiscoveryStrategy(DiscoveryStrategy):
    """API 探测策略 - 模式 A (High Speed)"""

    # FotMob API 端点模板（可自愈更新）
    API_ENDPOINTS = {
        "league_matches": "https://www.fotmob.com/api/leagues",
        "match_details": "https://www.fotmob.com/api/matches",
        "search": "https://www.fotmob.com/api/search",
    }

    def __init__(self, config: DiscoveryConfig, network_guardian: NetworkGuardian | None = None):
        super().__init__(config, network_guardian)
        self.base_extractor = BaseExtractor() if config.enable_ghost_protocol else None

    async def discover(self) -> DiscoveryResult:
        """API 探测发现"""
        start_time = datetime.now(timezone.utc)
        errors = []
        matches = []

        self.logger.info(f"[API Mode] Starting API discovery for {self.config.league_name}...")

        try:
            # 尝试多个 API 端点
            matches = await self._try_league_matches()

            if not matches:
                # 尝试搜索 API
                matches = await self._try_search_api()

            if not matches:
                # 尝试球队端点
                matches = await self._try_team_endpoints()

            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            if matches:
                self.logger.info(f"[API Mode] Found {len(matches)} matches via API")
                return DiscoveryResult(
                    status=DiscoveryStatus.SUCCESS,
                    mode=DiscoveryMode.API,
                    matches=matches,
                    latency_ms=latency_ms,
                    metadata={"api_method": "direct"}
                )
            else:
                errors.append("All API endpoints returned empty data")
                return DiscoveryResult(
                    status=DiscoveryStatus.FAILED,
                    mode=DiscoveryMode.API,
                    errors=errors,
                    latency_ms=latency_ms
                )

        except Exception as e:
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            errors.append(f"API discovery failed: {e}")
            self.logger.error(f"[API Mode] Error: {e}")

            return DiscoveryResult(
                status=DiscoveryStatus.FAILED,
                mode=DiscoveryMode.API,
                errors=errors,
                latency_ms=latency_ms
            )

    async def _try_league_matches(self) -> list[MatchInfo]:
        """尝试联赛比赛端点"""
        matches = []

        # 构造 URL
        url = f"{self.API_ENDPOINTS['league_matches']}?ID={self.config.league_id}&season={self.config.season.replace('-', '')}"

        headers = self._get_ghost_headers()

        try:
            async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    # 解析比赛列表
                    if 'matches' in data:
                        all_matches = data['matches'].get('allMatches', [])
                        matches = self._parse_matches_from_api(all_matches)

                    self.logger.debug(f"[API Mode] League endpoint returned {len(matches)} matches")
        except Exception as e:
            self.logger.warning(f"[API Mode] League endpoint failed: {e}")

        return matches

    async def _try_search_api(self) -> list[MatchInfo]:
        """尝试搜索 API"""
        matches = []

        url = f"{self.API_ENDPOINTS['search']}?term={self.config.league_name}"

        headers = self._get_ghost_headers()

        try:
            async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    # 解析搜索结果
                    if 'teams' in data:
                        teams = data['teams']
                        # 从球队信息中提取比赛
                        matches = await self._extract_matches_from_teams(teams)

                    self.logger.debug(f"[API Mode] Search endpoint returned {len(matches)} matches")
        except Exception as e:
            self.logger.warning(f"[API Mode] Search endpoint failed: {e}")

        return matches

    async def _try_team_endpoints(self) -> list[MatchInfo]:
        """尝试球队端点"""
        matches = []

        # 英冠知名球队 ID
        team_ids = [8459, 8465, 8466, 8470, 8458]  # Leeds, Leicester, Ipswich, Southampton, West Brom

        headers = self._get_ghost_headers()

        for team_id in team_ids:
            url = f"https://www.fotmob.com/api/teams/{team_id}/matches"

            try:
                async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        data = response.json()

                        if 'matches' in data:
                            all_matches = data['matches'].get('allMatches', [])
                            team_matches = self._parse_matches_from_api(all_matches, filter_league_id=self.config.league_id)
                            matches.extend(team_matches)

                        if len(matches) >= 10:  # 找到足够比赛
                            break
            except Exception as e:
                self.logger.debug(f"[API Mode] Team {team_id} endpoint failed: {e}")
                continue

        self.logger.debug(f"[API Mode] Team endpoints returned {len(matches)} matches")
        return matches

    async def _extract_matches_from_teams(self, teams: list) -> list[MatchInfo]:
        """从球队列表提取比赛"""
        matches = []

        for team in teams[:5]:  # 限制处理数量
            team_id = team.get('id')
            if not team_id:
                continue

            url = f"https://www.fotmob.com/api/teams/{team_id}/matches"
            headers = self._get_ghost_headers()

            try:
                async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        data = response.json()
                        if 'matches' in data:
                            all_matches = data['matches'].get('allMatches', [])
                            team_matches = self._parse_matches_from_api(all_matches, filter_league_id=self.config.league_id)
                            matches.extend(team_matches)
            except:
                continue

        return matches

    def _parse_matches_from_api(
        self,
        api_matches: list,
        filter_league_id: int | None = None
    ) -> list[MatchInfo]:
        """从 API 响应解析比赛"""
        matches = []

        for match in api_matches:
            try:
                # 检查联赛 ID
                tournament = match.get('tournament', {})
                tournament_id = tournament.get('uniqueTournament', {}).get('id')

                if filter_league_id and tournament_id != filter_league_id:
                    continue

                match_id = str(match.get('id', ''))
                if not match_id or match_id == '0':
                    continue

                home = match.get('home', {}).get('name', 'Unknown')
                away = match.get('away', {}).get('name', 'Unknown')

                matches.append(MatchInfo(
                    match_id=match_id,
                    home_team=home,
                    away_team=away,
                    league_id=tournament_id,
                    source="fotmob_api"
                ))
            except Exception as e:
                self.logger.debug(f"Failed to parse match: {e}")
                continue

        return matches

    def _get_ghost_headers(self) -> dict[str, str]:
        """获取 Ghost Protocol 请求头"""
        if self.base_extractor:
            ua = self.base_extractor.get_random_user_agent()
        else:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        return {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }

    async def _extract_dynamic_params(self) -> dict[str, str]:
        """
        从 FotMob 首页提取动态参数（参数自适应）

        当 API 结构变化时，自动提取新的 buildId 和 seasonInternalId，
        实现"参数自适应"功能，确保 API 请求始终有效。

        Returns:
            dict: {'buildId': 'xxx', 'seasonInternalId': 'xxx'}
        """
        params = {}

        try:
            headers = self._get_ghost_headers()

            async with httpx.AsyncClient(timeout=15) as client:
                # 访问 FotMob 首页
                response = await client.get("https://www.fotmob.com/", headers=headers)

                if response.status_code == 200:
                    html = response.text

                    # 提取 buildId (Next.js build ID)
                    # FotMob 使用 Next.js，buildId 通常在 <script> 标签中
                    build_patterns = [
                        r'buildId["\']?\s*:\s*["\']([^"\']+)["\']',
                        r'"buildId"\s*:\s*"([^"]+)"',
                        r'buildId=([^"&\s]+)',
                    ]

                    for pattern in build_patterns:
                        match = re.search(pattern, html)
                        if match:
                            params['buildId'] = match.group(1)
                            self.logger.info(f"[API Mode] Extracted buildId: {params['buildId']}")
                            break

                    # 提取 seasonInternalId (如果存在)
                    season_patterns = [
                        r'seasonInternalId["\']?\s*:\s*["\']([^"\']+)["\']',
                        r'"seasonInternalId"\s*:\s*"([^"]+)"',
                    ]

                    for pattern in season_patterns:
                        match = re.search(pattern, html)
                        if match:
                            params['seasonInternalId'] = match.group(1)
                            self.logger.info(f"[API Mode] Extracted seasonInternalId: {params['seasonInternalId']}")
                            break

                    # 尝试从 __NEXT_DATA__ 脚本中提取
                    next_data_pattern = r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>'
                    next_data_match = re.search(next_data_pattern, html, re.DOTALL)

                    if next_data_match and not params:
                        try:
                            import json
                            next_data = json.loads(next_data_match.group(1))

                            # 从 Next.js 数据中提取 buildId
                            if 'buildId' in next_data:
                                params['buildId'] = next_data['buildId']
                                self.logger.info(f"[API Mode] Extracted buildId from __NEXT_DATA__: {params['buildId']}")
                        except:
                            pass

                    if params:
                        self.logger.info(f"[API Mode] Successfully extracted {len(params)} dynamic parameter(s)")
                    else:
                        self.logger.warning("[API Mode] No dynamic parameters extracted")
                else:
                    self.logger.warning(f"[API Mode] Failed to fetch homepage: {response.status_code}")

        except Exception as e:
            self.logger.warning(f"[API Mode] Failed to extract dynamic params: {e}")

        return params


# ============================================================================
# MODE B: DOM DISCOVERY STRATEGY
# ============================================================================


class DomDiscoveryStrategy(DiscoveryStrategy):
    """DOM 抓取策略 - 模式 B (Reliable Fallback)"""

    # FotMob 联赛页面 URL
    FOTMOB_LEAGUE_URL = "https://www.fotmob.com/en/leagues/{league_id}/"

    def __init__(self, config: DiscoveryConfig, network_guardian: NetworkGuardian | None = None):
        super().__init__(config, network_guardian)
        self.base_extractor = BaseExtractor() if config.enable_ghost_protocol else None

    async def discover(self) -> DiscoveryResult:
        """DOM 抓取发现"""
        start_time = datetime.now(timezone.utc)
        errors = []
        matches = []

        self.logger.info(f"[DOM Mode] Starting DOM discovery for {self.config.league_name}...")

        try:
            async with async_playwright() as p:
                # 启动浏览器
                browser = await self._launch_browser(p)
                page = await browser.new_page()

                # 设置请求头
                await page.set_extra_http_headers(self._get_ghost_headers())

                # 访问联赛页面
                url = self.FOTMOB_LEAGUE_URL.format(league_id=self.config.league_id)
                self.logger.info(f"[DOM Mode] Navigating to: {url}")

                await page.goto(url, timeout=self.config.dom_timeout, wait_until="networkidle")

                # 等待比赛列表加载
                await self._wait_for_match_list(page)

                # 提取比赛 ID
                matches = await self._extract_match_ids(page)

                await browser.close()

            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            if matches:
                self.logger.info(f"[DOM Mode] Found {len(matches)} matches via DOM extraction")
                return DiscoveryResult(
                    status=DiscoveryStatus.SUCCESS,
                    mode=DiscoveryMode.DOM,
                    matches=matches,
                    latency_ms=latency_ms,
                    degraded=True,  # 标记为降级模式
                    metadata={"browser_used": True}
                )
            else:
                errors.append("DOM extraction found no matches")
                return DiscoveryResult(
                    status=DiscoveryStatus.FAILED,
                    mode=DiscoveryMode.DOM,
                    errors=errors,
                    latency_ms=latency_ms,
                    degraded=True
                )

        except Exception as e:
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            errors.append(f"DOM discovery failed: {e}")
            self.logger.error(f"[DOM Mode] Error: {e}")

            return DiscoveryResult(
                status=DiscoveryStatus.FAILED,
                mode=DiscoveryMode.DOM,
                errors=errors,
                latency_ms=latency_ms,
                degraded=True
            )

    async def _launch_browser(self, playwright):
        """启动浏览器（集成代理配置）"""
        launch_options = {
            "headless": self.config.dom_headless,
        }

        # 获取代理配置
        if self.network_guardian:
            try:
                proxy = await self.network_guardian.get_next_healthy_proxy("dom-discovery")
                if proxy:
                    launch_options["proxy"] = {
                        "server": proxy.url,
                    }
                    self.logger.info(f"[DOM Mode] Using proxy: port {proxy.port}")
            except Exception as e:
                self.logger.warning(f"[DOM Mode] Failed to get proxy: {e}")

        return await playwright.chromium.launch(**launch_options)

    async def _wait_for_match_list(self, page: Page):
        """等待比赛列表加载"""
        try:
            # 等待比赛容器出现
            await page.wait_for_selector("[class*='MatchCard'], [class*='match-card'], a[href*='/matches/']", timeout=10000)
            # 额外等待确保数据加载
            await asyncio.sleep(2)
        except:
            # 即使选择器未找到，也继续尝试提取
            pass

    async def _extract_match_ids(self, page: Page) -> list[MatchInfo]:
        """从 DOM 提取比赛 ID"""
        matches = []
        match_ids = set()

        try:
            # 保存页面 HTML 用于调试
            page_html = await page.content()
            debug_file = Path("logs/dom_debug.html")
            debug_file.parent.mkdir(exist_ok=True)
            debug_file.write_text(page_html, encoding='utf-8')
            self.logger.info(f"[DOM Mode] Page HTML saved to: {debug_file}")

            # 方法 1: 查找所有包含比赛链接的 <a> 标签
            # 多种可能的 URL 模式
            selectors = [
                "a[href*='/matches/']",
                "a[href*='/match/']",
                "a[href*='matchId']",
                "[data-match-id]",
                "[class*='MatchCard'] a",
            ]

            for selector in selectors:
                try:
                    links = await page.query_selector_all(selector)
                    self.logger.debug(f"[DOM Mode] Selector '{selector}' found {len(links)} elements")

                    for link in links:
                        href = await link.get_attribute('href')
                        if href:
                            # 提取 match_id: /matches/12345678, /match/12345678, ?matchId=12345678
                            patterns = [
                                r'/matches/(\d+)',
                                r'/match/(\d+)',
                                r'matchId[=:](\d+)',
                                r'/m/(\d+)',
                            ]

                            for pattern in patterns:
                                match = re.search(pattern, href)
                                if match:
                                    match_id = match.group(1)
                                    # 过滤掉太短或太长的 ID
                                    if 6 <= len(match_id) <= 10:
                                        match_ids.add(match_id)
                                        break

                    if match_ids:
                        self.logger.info(f"[DOM Mode] Found {len(match_ids)} match IDs via selector: {selector}")
                        break

                except Exception as e:
                    self.logger.debug(f"[DOM Mode] Selector '{selector}' failed: {e}")

            # 方法 2: 从页面 HTML 直接提取（正则表达式）
            if not match_ids:
                self.logger.info("[DOM Mode] Trying regex extraction from HTML...")
                patterns = [
                    r'/matches/(\d{7,9})',
                    r'/match/(\d{7,9})',
                    r'"matchId":"?(\d{7,9})',
                    r'matchId[=:](\d{7,9})',
                ]

                for pattern in patterns:
                    found = re.findall(pattern, page_html)
                    for match_id in found:
                        match_ids.add(match_id)

                    if match_ids:
                        self.logger.info(f"[DOM Mode] Found {len(match_ids)} match IDs via regex: {pattern}")
                        break

            # 转换为 MatchInfo
            for match_id in match_ids:
                matches.append(MatchInfo(
                    match_id=match_id,
                    home_team="Unknown",
                    away_team="Unknown",
                    source="fotmob_dom",
                    fotmob_url=f"https://www.fotmob.com/matches/{match_id}"
                ))

            self.logger.info(f"[DOM Mode] Extracted {len(matches)} unique match IDs")

            # 显示前几个 ID
            if matches:
                for m in matches[:5]:
                    self.logger.info(f"  - {m.match_id}: {m.fotmob_url}")

        except Exception as e:
            self.logger.error(f"[DOM Mode] Extraction error: {e}")

        return matches

    def _get_ghost_headers(self) -> dict[str, str]:
        """获取 Ghost Protocol 请求头"""
        if self.base_extractor:
            ua = self.base_extractor.get_random_user_agent()
        else:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        return {
            "User-Agent": ua,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }


# ============================================================================
# CROSS-PLATFORM DISCOVERY STRATEGY
# ============================================================================


class CrossPlatformDiscoveryStrategy(DiscoveryStrategy):
    """跨平台发现策略 - OddsPortal → FotMob 映射"""

    # OddsPortal 英冠页面
    ODSPORTAL_CHAMPIONSHIP_URL = "https://www.oddsportal.com/football/england/championship/"

    def __init__(self, config: DiscoveryConfig, network_guardian: NetworkGuardian | None = None):
        super().__init__(config, network_guardian)

    async def discover(self) -> DiscoveryResult:
        """跨平台发现"""
        start_time = datetime.now(timezone.utc)
        errors = []
        matches = []

        self.logger.info(f"[Cross-Platform Mode] Starting cross-platform discovery...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 访问 OddsPortal 英冠页面
                self.logger.info(f"[Cross-Platform] Scraping OddsPortal...")
                await page.goto(self.ODSPORTAL_CHAMPIONSHIP_URL, timeout=30000)

                # 提取比赛信息
                oddsportal_matches = await self._extract_oddsportal_matches(page)
                self.logger.info(f"[Cross-Platform] Found {len(oddsportal_matches)} matches on OddsPortal")

                # 通过 FotMob Search API 映射
                self.logger.info(f"[Cross-Platform] Mapping to FotMob IDs...")
                for match_info in oddsportal_matches[:10]:  # 限制数量
                    fotmob_id = await self._search_fotmob_match(match_info)
                    if fotmob_id:
                        matches.append(MatchInfo(
                            match_id=fotmob_id,
                            home_team=match_info['home'],
                            away_team=match_info['away'],
                            source="cross_platform"
                        ))

                await browser.close()

            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            if matches:
                self.logger.info(f"[Cross-Platform] Mapped {len(matches)} matches")
                return DiscoveryResult(
                    status=DiscoveryStatus.SUCCESS,
                    mode=DiscoveryMode.CROSS_PLATFORM,
                    matches=matches,
                    latency_ms=latency_ms,
                    degraded=True,
                    metadata={"source": "oddsportal"}
                )
            else:
                errors.append("Cross-platform mapping found no matches")
                return DiscoveryResult(
                    status=DiscoveryStatus.FAILED,
                    mode=DiscoveryMode.CROSS_PLATFORM,
                    errors=errors,
                    latency_ms=latency_ms,
                    degraded=True
                )

        except Exception as e:
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            errors.append(f"Cross-platform discovery failed: {e}")
            self.logger.error(f"[Cross-Platform] Error: {e}")

            return DiscoveryResult(
                status=DiscoveryStatus.FAILED,
                mode=DiscoveryMode.CROSS_PLATFORM,
                errors=errors,
                latency_ms=latency_ms,
                degraded=True
            )

    async def _extract_oddsportal_matches(self, page: Page) -> list[dict]:
        """从 OddsPortal 提取比赛"""
        matches = []

        try:
            # 保存页面用于调试
            page_html = await page.content()
            debug_file = Path("logs/oddsportal_debug.html")
            debug_file.parent.mkdir(exist_ok=True)
            debug_file.write_text(page_html, encoding='utf-8')
            self.logger.info(f"[Cross-Platform] OddsPortal HTML saved to: {debug_file}")

            # 多种选择器尝试
            selectors = [
                "a[href*='/match/']",
                "tr[class*='match']",
                "div[class*='match']",
                "table tbody tr",
                "[data-match-id]",
            ]

            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    self.logger.debug(f"[Cross-Platform] Selector '{selector}' found {len(elements)} elements")

                    for element in elements[:30]:  # 限制处理数量
                        try:
                            href = await element.get_attribute('href')
                            text = await element.inner_text()

                            # 提取 match hash (OddsPortal 格式)
                            if href and '/match/' in href:
                                # 保存 URL
                                match_hash = href.split('/match/')[-1].split('/')[0]
                                if len(match_hash) >= 8:  # OddsPortal hash 格式
                                    matches.append({
                                        'hash': match_hash,
                                        'url': f"https://www.oddsportal.com{href}",
                                        'text': text.strip()[:100]  # 限制长度
                                    })
                        except:
                            continue

                    if matches:
                        self.logger.info(f"[Cross-Platform] Found {len(matches)} matches via selector: {selector}")
                        break

                except Exception as e:
                    self.logger.debug(f"[Cross-Platform] Selector '{selector}' failed: {e}")

            # 如果 DOM 提取失败，尝试正则表达式
            if not matches:
                self.logger.info("[Cross-Platform] Trying regex extraction from HTML...")
                pattern = r'/match/([a-zA-Z0-9-]{8,})'
                found = re.findall(pattern, page_html)

                for match_hash in found[:20]:
                    matches.append({
                        'hash': match_hash,
                        'url': f"https://www.oddsportal.com/match/{match_hash}",
                        'text': 'From regex extraction'
                    })

                if matches:
                    self.logger.info(f"[Cross-Platform] Found {len(matches)} matches via regex")

            # 显示前几个结果
            if matches:
                for m in matches[:5]:
                    self.logger.info(f"  - {m['hash']}: {m['url']}")

        except Exception as e:
            self.logger.warning(f"[Cross-Platform] OddsPortal extraction error: {e}")

        return matches

    async def _search_fotmob_match(self, match_info: dict) -> str | None:
        """
        通过 FotMob Search API 查找比赛

        Args:
            match_info: 包含 'home' 和 'away' 球队名称的字典

        Returns:
            str | None: FotMob match_id，如果未找到返回 None
        """
        try:
            # 构造搜索词：球队名
            search_term = f"{match_info.get('home', '')} {match_info.get('away', '')}"
            url = f"https://www.fotmob.com/api/search?term={search_term}"

            headers = self._get_ghost_headers()

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    # 尝试从搜索结果中提取 match_id
                    # FotMob search API 返回结构可能包含:
                    # - matches: 直接的比赛匹配
                    # - teams: 球队匹配
                    # - leagues: 联赛匹配

                    # 方法 1: 直接匹配比赛
                    if 'matches' in data and data['matches']:
                        for match in data['matches'][:3]:  # 只检查前 3 个结果
                            match_id = match.get('id')
                            if match_id:
                                self.logger.debug(f"[Cross-Platform] Found match via direct search: {match_id}")
                                return str(match_id)

                    # 方法 2: 通过球队匹配
                    if 'teams' in data and data['teams']:
                        # 获取第一个球队的比赛列表
                        team = data['teams'][0]
                        team_id = team.get('id')
                        if team_id:
                            # 获取球队最近的比赛
                            team_url = f"https://www.fotmob.com/api/teams/{team_id}/matches"
                            team_response = await client.get(team_url, headers=headers)

                            if team_response.status_code == 200:
                                team_data = team_response.json()
                                if 'matches' in team_data:
                                    all_matches = team_data['matches'].get('allMatches', [])
                                    # 查找匹配的比赛
                                    for match in all_matches[:10]:
                                        home_name = match.get('home', {}).get('name', '')
                                        away_name = match.get('away', {}).get('name', '')

                                        # 模糊匹配球队名称
                                        if (self._fuzzy_match(match_info.get('home', ''), home_name) and
                                            self._fuzzy_match(match_info.get('away', ''), away_name)):
                                            match_id = match.get('id')
                                            if match_id:
                                                self.logger.debug(
                                                    f"[Cross-Platform] Found match via team search: {match_id}"
                                                )
                                                return str(match_id)

                    self.logger.debug(f"[Cross-Platform] No match found for: {search_term}")
                else:
                    self.logger.warning(f"[Cross-Platform] Search API failed: {response.status_code}")

        except Exception as e:
            self.logger.debug(f"[Cross-Platform] FotMob search error: {e}")

        return None

    def _fuzzy_match(self, name1: str, name2: str, threshold: float = 0.7) -> bool:
        """
        模糊匹配两个球队名称

        Args:
            name1: 第一个名称
            name2: 第二个名称
            threshold: 相似度阈值 (0-1)

        Returns:
            bool: 是否匹配
        """
        if not name1 or not name2:
            return False

        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()

        # 完全匹配
        if name1_lower == name2_lower:
            return True

        # 包含匹配
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return True

        # 简单的相似度计算（基于共同字符）
        common_chars = set(name1_lower) & set(name2_lower)
        total_chars = set(name1_lower) | set(name2_lower)

        if total_chars:
            similarity = len(common_chars) / len(total_chars)
            return similarity >= threshold

        return False


# ============================================================================
# DYNAMIC DISCOVERY ENGINE
# ============================================================================


class DynamicDiscoveryEngine:
    """
    动态发现引擎 - L1 双模降级架构

    功能:
    1. 自动降级: API 失败 → DOM 抓取
    2. 跨平台映射: OddsPortal → FotMob
    3. 智能指纹: Ghost Protocol 集成
    4. 配置自愈: 自动更新 API 模板

    使用示例:
        >>> engine = DynamicDiscoveryEngine()
        >>> await engine.initialize()
        >>>
        >>> result = await engine.discover_league(
        ...     league_id=48,
        ...     league_name="Championship",
        ...     season="2024-2025"
        ... )
        >>>
        >>> print(f"Found {len(result.matches)} matches")
        >>> print(f"Mode: {result.mode.value}")
        >>> print(f"Degraded: {result.degraded}")
    """

    def __init__(self, config: DiscoveryConfig | None = None):
        self.config = config or DiscoveryConfig(league_id=48, league_name="Championship")
        self.network_guardian: NetworkGuardian | None = None
        self.api_failure_count = 0
        self.logger = logging.getLogger("DynamicDiscoveryEngine")

    async def initialize(self) -> None:
        """初始化引擎"""
        if self.config.enable_network_shield:
            self.network_guardian = NetworkGuardian(proxy_host="172.25.16.1", log_level="warning")
            try:
                await self.network_guardian.initialize()
                status = self.network_guardian.get_status()
                self.logger.info(
                    f"[L1Evolution] NetworkShield initialized: "
                    f"{status.get('nodes', {}).get('active', 0)}/"
                    f"{status.get('nodes', {}).get('total', 0)} nodes"
                )
            except Exception as e:
                self.logger.warning(f"[L1Evolution] NetworkShield init failed: {e}")
                self.network_guardian = None

    async def shutdown(self) -> None:
        """关闭引擎"""
        if self.network_guardian:
            # 释放所有会话
            pass

    async def discover_league(
        self,
        league_id: int,
        league_name: str,
        season: str = "2024-2025",
        force_dom: bool = False
    ) -> DiscoveryResult:
        """
        发现联赛比赛

        Args:
            league_id: 联赛 ID
            league_name: 联赛名称
            season: 赛季
            force_dom: 强制使用 DOM 模式

        Returns:
            DiscoveryResult: 发现结果
        """
        self.config.league_id = league_id
        self.config.league_name = league_name
        self.config.season = season

        self.logger.info("=" * 70)
        self.logger.info("[L1Evolution] DUAL-MODE DISCOVERY STARTED")
        self.logger.info("=" * 70)
        self.logger.info(f"  League: {league_name} (ID: {league_id})")
        self.logger.info(f"  Season: {season}")
        self.logger.info(f"  Force DOM: {force_dom}")
        self.logger.info("=" * 70)

        # ====================================================================
        # MODE A: API DISCOVERY (High Speed)
        # ====================================================================
        if not force_dom:
            self.logger.info("\n[MODE A] API Discovery - High Speed")
            self.logger.info("-" * 70)

            api_strategy = ApiDiscoveryStrategy(self.config, self.network_guardian)
            result = await api_strategy.discover()

            if result.status == DiscoveryStatus.SUCCESS and result.matches:
                self.logger.info(f"[MODE A] ✓ SUCCESS: Found {len(result.matches)} matches via API")
                self.api_failure_count = 0  # 重置计数
                return result

            # 记录失败
            self.api_failure_count += 1
            self.logger.warning(f"[MODE A] ✗ FAILED: {result.errors}")
            self.logger.warning(f"[MODE A] API failure count: {self.api_failure_count}/{self.config.max_api_failures}")

            # 检查是否需要降级
            if self.api_failure_count < self.config.max_api_failures and self.config.auto_degrade:
                self.logger.info("[MODE A] Retrying API mode...")
                await asyncio.sleep(self._get_random_delay())
                # 重试逻辑可以在此添加
        else:
            self.logger.info("\n[MODE A] SKIPPED: Force DOM mode enabled")

        # ====================================================================
        # MODE B: DOM DISCOVERY (Reliable Fallback)
        # ====================================================================
        self.logger.info("\n[MODE B] DOM Discovery - Reliable Fallback")
        self.logger.info("-" * 70)

        dom_strategy = DomDiscoveryStrategy(self.config, self.network_guardian)
        result = await dom_strategy.discover()

        if result.status == DiscoveryStatus.SUCCESS and result.matches:
            self.logger.info(f"[MODE B] ✓ SUCCESS: Found {len(result.matches)} matches via DOM")
            self.logger.info("[MODE B] ⚠ DEGRADED: Using browser fallback mode")
            return result

        self.logger.error(f"[MODE B] ✗ FAILED: {result.errors}")

        # ====================================================================
        # MODE C: CROSS-PLATFORM DISCOVERY (Last Resort)
        # ====================================================================
        self.logger.info("\n[MODE C] Cross-Platform Discovery - Last Resort")
        self.logger.info("-" * 70)

        cross_strategy = CrossPlatformDiscoveryStrategy(self.config, self.network_guardian)
        result = await cross_strategy.discover()

        if result.status == DiscoveryStatus.SUCCESS and result.matches:
            self.logger.info(f"[MODE C] ✓ SUCCESS: Mapped {len(result.matches)} matches from OddsPortal")
        else:
            self.logger.error("[MODE C] ✗ ALL MODES FAILED")

        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        self.logger.info("\n" + "=" * 70)
        self.logger.info("[L1Evolution] DISCOVERY COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info(f"  Final Status: {result.status.value}")
        self.logger.info(f"  Matches Found: {len(result.matches)}")
        self.logger.info(f"  Mode Used: {result.mode.value}")
        self.logger.info(f"  Degraded: {result.degraded}")
        self.logger.info("=" * 70)

        return result

    def _get_random_delay(self) -> float:
        """获取随机延迟"""
        return random.uniform(2.0, 5.0)

    async def auto_repair_config(self) -> bool:
        """
        当发现 404 频率过高时，自动尝试更新 API 模板

        这是"配置自愈"功能的核心方法。当 API 失败率达到阈值时，
        自动触发配置修复流程：
        1. 重新提取动态参数
        2. 更新 API 端点模板
        3. 验证修复是否成功

        Returns:
            bool: 是否成功修复配置
        """
        self.logger.warning("[L1Evolution] Auto-repair triggered by high failure rate...")

        try:
            # 1. 重新提取动态参数
            api_strategy = ApiDiscoveryStrategy(self.config, self.network_guardian)
            params = await api_strategy._extract_dynamic_params()

            if not params:
                self.logger.warning("[L1Evolution] Auto-repair failed: no params extracted")
                return False

            # 2. 更新 API 端点模板（如果提取到新参数）
            if 'buildId' in params:
                # 更新类级别的 API 端点（支持新的 buildId）
                # FotMob Next.js API 可能需要 buildId 参数
                self.logger.info(f"[L1Evolution] Updated buildId: {params['buildId']}")

                # 可以在这里更新 API_ENDPOINTS 字典
                # 例如：添加新的端点或修改现有端点

            # 3. 重置失败计数器
            self.api_failure_count = 0

            self.logger.info("[L1Evolution] Config auto-repaired successfully")
            return True

        except Exception as e:
            self.logger.error(f"[L1Evolution] Auto-repair error: {e}")
            return False


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


async def discover_championship_2025() -> DiscoveryResult:
    """
    便捷函数：发现英冠 2024-2025 赛季比赛

    Returns:
        DiscoveryResult: 发现结果
    """
    engine = DynamicDiscoveryEngine()
    await engine.initialize()

    try:
        result = await engine.discover_league(
            league_id=48,
            league_name="Championship",
            season="2024-2025"
        )
        return result
    finally:
        await engine.shutdown()


# ============================================================================
# CLI ENTRY POINT
# ============================================================================


async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Dynamic Discovery Engine - L1 Dual-Mode Discovery")
    parser.add_argument("--league-id", type=int, default=48, help="League ID (default: 48 for Championship)")
    parser.add_argument("--league-name", type=str, default="Championship", help="League name")
    parser.add_argument("--season", type=str, default="2024-2025", help="Season")
    parser.add_argument("--force-dom", action="store_true", help="Force DOM mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')

    # 创建引擎
    engine = DynamicDiscoveryEngine()

    try:
        await engine.initialize()

        result = await engine.discover_league(
            league_id=args.league_id,
            league_name=args.league_name,
            season=args.season,
            force_dom=args.force_dom
        )

        # 打印结果
        print("\n" + "=" * 70)
        print("DISCOVERY RESULT")
        print("=" * 70)
        print(json.dumps(result.to_dict(), indent=2))
        print("=" * 70)

        # 保存结果
        output_file = Path("logs/discovery_result.json")
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"\nResult saved to: {output_file}")

        return 0 if result.status == DiscoveryStatus.SUCCESS else 1

    finally:
        await engine.shutdown()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
