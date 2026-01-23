#!/usr/bin/env python3
"""V41.631 Cross-Source Mapping Recovery - 多源数据关联自动补全.

该脚本用于修复 `matches_mapping` 表中缺失 `oddsportal_url` 的记录。
核心算法：球队名语义相似度 + 时间窗口匹配。

核心流程：
    Step 1: League History Scraper (联赛历史页爬取器)
        - 基于 LeagueUrlMapper 构建目标站点 URL
        - 使用 BaseExtractor Ghost Protocol 访问列表页
        - 提取 [日期, 主队, 客队, 详情页URL哈希]
        - 使用 playwright + asyncio + 5 并发线程

    Step 2: Fuzzy Match Engine (模糊匹配引擎)
        - 时间锚定：±1 天窗口（处理跨时区）
        - 文本相似度：TeamNameNormalizer.fuzzy_match()
        - 阈值控制：> 80% 视为匹配成功
        - 多阶段回退策略：100% → 90% → 80%

    Step 3: Database Update (数据库回填)
        - 批量更新 matches_mapping.oddsportal_url
        - 记录 mapping_method = 'v41_631_fuzzy_recovery'
        - 设置 confidence = 相似度分数 / 100
        - 生成修复报告

Usage:
    # 运行完整修复流程（测试模式 - 10 条记录）
    python scripts/ops/v41_631_cross_source_mapping_recovery.py --limit 10 --dry-run

    # 运行完整修复流程（生产模式 - 所有记录）
    python scripts/ops/v41_631_cross_source_mapping_recovery.py

    # 仅针对特定联赛
    python scripts/ops/v41_631_cross_source_mapping_recovery.py --league "Premier League" --season "2024/2025"

    # 查看缺失 URL 统计
    python scripts/ops/v41_631_cross_source_mapping_recovery.py --stats-only

Example:
    >>> # Step 1: 爬取目标站点数据
    >>> scraper = LeagueHistoryScraper()
    >>> matches_data = await scraper.scrape_league_season("Premier League", "2024/2025")
    >>>
    >>> # Step 2: 执行模糊匹配
    >>> engine = FuzzyMatchEngine()
    >>> results = engine.match_and_recover(limit=100)
    >>>
    >>> # Step 3: 查看修复报告
    >>> print(results.summary())
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any

import click
from playwright.async_api import async_playwright, Browser, Page
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from bs4 import BeautifulSoup

from src.api.collectors.base_extractor import BaseExtractor
from src.config_unified import get_settings
from src.utils.text_processor import (
    TeamNameNormalizer,
    LeagueUrlMapper,
    YouthTeamDetector,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration & Constants
# ============================================================================

# 目标站点基础 URL
BASE_URL = "https://www.oddsportal.com"

# 并发配置 (V41.634: 升级到 18 线程并发)
DEFAULT_CONCURRENT_WORKERS = 18
DEFAULT_PAGE_TIMEOUT = 90000  # 90 seconds (V41.634: 增加超时以支持深度渲染)

# 匹配阈值
DEFAULT_CONFIDENCE_THRESHOLD = 0.80
HIGH_CONFIDENCE_THRESHOLD = 1.00
MEDIUM_CONFIDENCE_THRESHOLD = 0.90

# 时间窗口（天）
TIME_WINDOW_DAYS = 1


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class SourceMatchRecord:
    """从目标站点提取的比赛记录."""

    match_date: datetime
    home_team: str
    away_team: str
    url_hash: str
    full_url: str
    league_name: str
    season: str

    def to_tuple(self) -> tuple:
        """转换为元组用于缓存."""
        return (
            self.match_date,
            self.home_team,
            self.away_team,
            self.url_hash,
            self.full_url,
        )


@dataclass
class MatchMappingRecord:
    """数据库中的比赛映射记录."""

    fotmob_id: str
    match_date: datetime | None
    home_team: str | None
    away_team: str | None
    league_name: str | None
    season: str | None
    oddsportal_url: str | None = None

    @classmethod
    def from_db_row(cls, row: dict) -> MatchMappingRecord:
        """从数据库行构造."""
        return cls(
            fotmob_id=row["fotmob_id"],
            match_date=row.get("match_date"),
            home_team=row.get("home_team"),
            away_team=row.get("away_team"),
            league_name=row.get("league_name"),
            season=row.get("season"),
            oddsportal_url=row.get("oddsportal_url"),
        )


@dataclass
class MatchResult:
    """匹配结果."""

    fotmob_id: str
    matched_url: str
    confidence: float
    home_similarity: float
    away_similarity: float
    date_diff_days: int
    source_record: SourceMatchRecord | None = None


@dataclass
class RecoveryStats:
    """修复统计."""

    total_missing: int = 0
    total_processed: int = 0
    high_confidence_matches: int = 0
    medium_confidence_matches: int = 0
    low_confidence_matches: int = 0
    no_match: int = 0
    errors: int = 0

    leagues_scanned: list[str] = field(default_factory=list)
    total_source_records: int = 0

    @property
    def success_rate(self) -> float:
        """计算成功率."""
        if self.total_processed == 0:
            return 0.0
        matched = (
            self.high_confidence_matches
            + self.medium_confidence_matches
            + self.low_confidence_matches
        )
        return (matched / self.total_processed) * 100

    def summary(self) -> str:
        """生成统计摘要."""
        return f"""
╔══════════════════════════════════════════════════════════════════════╗
║           V41.631 Cross-Source Mapping Recovery - 报告              ║
╚══════════════════════════════════════════════════════════════════════╝

📊 总体统计:
  • 缺失 URL 记录数: {self.total_missing}
  • 已处理记录数: {self.total_processed}
  • 源站点记录数: {self.total_source_records}
  • 修复成功率: {self.success_rate:.2f}%

🎯 匹配质量分布:
  • 高置信度 (>95%): {self.high_confidence_matches}
  • 中置信度 (90-95%): {self.medium_confidence_matches}
  • 低置信度 (80-90%): {self.low_confidence_matches}
  • 未匹配: {self.no_match}
  • 错误: {self.errors}

🏆 扫描联赛:
  {', '.join(self.leagues_scanned) if self.leagues_scanned else '无'}
"""


# ============================================================================
# Step 1: League History Scraper
# ============================================================================


class LeagueHistoryScraper:
    """V41.631 Step 1: 联赛历史页爬取器.

    从目标站点的联赛历史结果页提取比赛列表。
    使用 Ghost Protocol 进行反爬检测。
    """

    def __init__(
        self,
        concurrent_workers: int = DEFAULT_CONCURRENT_WORKERS,
        enable_ghost_protocol: bool = True,
    ) -> None:
        """初始化爬取器.

        Args:
            concurrent_workers: 并发工作线程数
            enable_ghost_protocol: 是否启用 Ghost Protocol
        """
        self.concurrent_workers = concurrent_workers
        self.enable_ghost_protocol = enable_ghost_protocol
        self.base_extractor = BaseExtractor(enable_ghost_protocol=enable_ghost_protocol)
        self.league_mapper = LeagueUrlMapper()
        self._results_cache: dict[tuple[str, str], list[SourceMatchRecord]] = {}

    async def scrape_league_season(
        self,
        league_name: str,
        season: str,
        force_refresh: bool = False,
    ) -> list[SourceMatchRecord]:
        """爬取指定联赛赛季的历史结果页.

        Args:
            league_name: 联赛名称
            season: 赛季 (如 "2024/2025")
            force_refresh: 是否强制刷新缓存

        Returns:
            源站点比赛记录列表
        """
        cache_key = (league_name, season)

        # 检查缓存
        if not force_refresh and cache_key in self._results_cache:
            logger.info(f"  📦 使用缓存: {league_name} {season}")
            return self._results_cache[cache_key]

        # 构建目标 URL
        target_url = self.league_mapper.construct_results_url(league_name, season)
        if not target_url:
            logger.warning(f"  ⚠️  无法构建 URL: {league_name} {season}")
            return []

        # 修复赛季格式：2025/2026 -> 2025-2026
        # 目标站点使用短横线分隔而非斜杠
        target_url = target_url.replace("-2025/2026", "-2025-2026")
        target_url = target_url.replace("-2024/2025", "-2024-2025")
        target_url = target_url.replace("-2023/2024", "-2023-2024")
        target_url = target_url.replace("-2022/2023", "-2022-2023")
        target_url = target_url.replace("-2021/2022", "-2021-2022")
        target_url = target_url.replace("-2020/2021", "-2020-2021")

        logger.info(f"  🔗 目标 URL: {target_url}")

        # 使用 playwright 爬取
        records = await self._scrape_with_playwright(target_url, league_name, season)

        # 如果 playwright 失败，尝试备用方法
        if not records:
            logger.warning("  ⚠️  Playwright 提取失败，尝试备用方法 (requests + BeautifulSoup)...")
            records = self._scrape_with_requests(target_url, league_name, season)

        # 缓存结果
        self._results_cache[cache_key] = records

        logger.info(f"  ✅ 提取到 {len(records)} 条记录")
        return records

    def _scrape_with_requests(
        self,
        url: str,
        league_name: str,
        season: str,
    ) -> list[SourceMatchRecord]:
        """使用 requests + BeautifulSoup 爬取页面（备用方法）.

        Args:
            url: 目标 URL
            league_name: 联赛名称
            season: 赛季

        Returns:
            提取的比赛记录列表
        """
        records = []

        try:
            logger.info(f"  📡 使用 requests 访问: {url}")

            # 使用代理（如果配置了）
            proxies = None
            if self.base_extractor.proxy_config:
                proxies = {
                    "http": self.base_extractor.proxy_config["server"],
                    "https": self.base_extractor.proxy_config["server"],
                }

            # 发送请求
            headers = {
                "User-Agent": self.base_extractor.get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            response.raise_for_status()

            logger.info(f"  📄 响应状态: {response.status_code}, 内容长度: {len(response.content)}")

            # 解析 HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找所有比赛链接
            # 目标站点的链接格式: /football/matches/xxxxxxxx/...
            match_links = soup.find_all("a", href=re.compile(r"/football/matches/[a-z0-9]{8}"))

            logger.info(f"  🔗 找到 {len(match_links)} 个比赛链接")

            # 提取比赛数据
            seen_hashes = set()
            for link in match_links:
                try:
                    href = link.get("href", "")
                    # 提取 hash
                    hash_match = re.search(r"/football/matches/([a-z0-9]{8})", href)
                    if not hash_match:
                        continue

                    url_hash = hash_match.group(1)
                    if url_hash in seen_hashes:
                        continue
                    seen_hashes.add(url_hash)

                    full_url = f"{BASE_URL}{href}"

                    # 尝试获取球队名
                    home_team = ""
                    away_team = ""
                    date_text = ""

                    # 查找最近的行元素
                    row = link.find_parent("tr")
                    if not row:
                        row = link.find_parent("div", class_=re.compile(r"row|match|event", re.I))

                    if row:
                        # 提取日期
                        first_cell = row.find(["td", "div", "span"])
                        if first_cell:
                            date_text = first_cell.get_text(strip=True)

                        # 提取球队名 - 查找同一行中的所有球队链接
                        team_links = row.find_all("a", href=re.compile(r"/football/(matches|teams)/"))
                        if len(team_links) >= 2:
                            home_team = team_links[0].get_text(strip=True)
                            away_team = team_links[1].get_text(strip=True)

                    # 如果没找到球队名，使用链接文本
                    if not home_team:
                        link_text = link.get_text(strip=True)
                        if link_text and len(link_text) < 50:  # 合理的球队名长度
                            home_team = link_text

                    # 只保留有球队名的记录
                    if home_team or away_team:
                        match_date = self._parse_match_date(date_text)
                        records.append(SourceMatchRecord(
                            match_date=match_date,
                            home_team=home_team,
                            away_team=away_team,
                            url_hash=url_hash,
                            full_url=full_url,
                            league_name=league_name,
                            season=season,
                        ))

                except Exception as e:
                    logger.debug(f"    ⚠️  链接解析失败: {e}")
                    continue

            logger.info(f"  ✅ requests 提取到 {len(records)} 条记录")

        except Exception as e:
            logger.error(f"  ❌ requests 提取失败: {e}")

        return records

    async def _scrape_with_playwright(
        self,
        url: str,
        league_name: str,
        season: str,
    ) -> list[SourceMatchRecord]:
        """V41.633: 使用 Playwright 网络拦截器窃听 JSON 数据流.

        Args:
            url: 目标 URL
            league_name: 联赛名称
            season: 赛季

        Returns:
            提取的比赛记录列表
        """
        records = []
        intercepted_data = []  # 存储截获的 JSON 数据

        async def response_handler(response):
            """V41.633: 网络响应处理器 - 窃听 JSON 数据流.

            核心逻辑：
            1. 过滤 JSON 响应
            2. 解析数据提取比赛信息
            3. 存储到 intercepted_data 列表
            """
            try:
                # 只处理成功的响应
                if response.status != 200:
                    return

                # V41.633: 记录所有响应（用于调试）
                response_url = response.url
                content_type = response.headers.get("content-type", "")

                # 只处理 JSON 响应
                if "application/json" not in content_type.lower():
                    return

                logger.info(f"  🎯 拦截到 JSON: {response_url}")

                # 获取响应数据
                try:
                    # 尝试获取响应文本
                    text = await response.text()
                    if not text or text.strip() == "":
                        logger.debug(f"    响应为空，跳过")
                        return

                    # 解析 JSON
                    import json
                    data = json.loads(text)

                except Exception as e:
                    logger.debug(f"    JSON 解析失败: {e}")
                    return

                # V41.633: 深度解析 JSON 提取比赛信息
                extracted = self._parse_json_response(data, response_url, league_name, season)
                if extracted:
                    intercepted_data.extend(extracted)
                    logger.info(f"    ✓ 解析出 {len(extracted)} 条记录")

            except Exception as e:
                logger.debug(f"  ⚠️  响应处理失败: {e}")

        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)

            # 创建 Ghost Protocol context
            context, page = await self.base_extractor.create_ghost_context(browser)

            try:
                # V41.633: 在 goto 之前挂载响应监听器
                page.on("response", lambda resp: asyncio.create_task(response_handler(resp)))
                logger.info("  🎧 已挂载网络响应窃听器")

                # 访问页面
                logger.info(f"  🌐 正在访问: {url}")
                await page.goto(url, timeout=DEFAULT_PAGE_TIMEOUT)

                # V41.634: 暴力等待与滚动（深度渲染触发）
                logger.info("  🔄 V41.634 深度渲染模式：执行 5 轮暴力滚动...")

                # 第一阶段：等待初始网络空闲
                await page.wait_for_load_state("networkidle", timeout=45000)

                # 第二阶段：5 轮暴力滚动到底部 + 等待
                for i in range(5):
                    logger.info(f"    📜 滚动轮次 {i+1}/5...")
                    # 滚动到底部
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    # 等待 2 秒让内容加载
                    await asyncio.sleep(2)

                # 第三阶段：强制等待网络空闲（60 秒超时）
                logger.info("  ⏳ 等待网络空闲...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=60000)
                    logger.info("    ✓ 网络已空闲")
                except Exception as e:
                    logger.warning(f"    ⚠️  网络未完全空闲: {e}")

                # 第四阶段：最终等待（确保所有懒加载完成）
                await asyncio.sleep(3)

                logger.info(f"  📦 拦截到 {len(intercepted_data)} 条原始记录")

                # 如果拦截失败，尝试 DOM 方法
                if not intercepted_data:
                    logger.warning("  ⚠️  拦截器未捕获数据，尝试 DOM 方法...")
                    records = await self._scrape_via_dom(page, league_name, season)
                else:
                    records = intercepted_data

            except Exception as e:
                logger.error(f"  ❌ 页面爬取失败: {e}")

            finally:
                await context.close()
                await browser.close()

        return records

    async def _scrape_via_dom(
        self,
        page: Page,
        league_name: str,
        season: str,
    ) -> list[SourceMatchRecord]:
        """V41.634: 降维提取 - 直接遍历所有 <a> 标签，使用正则匹配.

        核心思想：
        - 不依赖复杂的 DOM 结构
        - 直接遍历所有 <a> 标签
        - 使用正则匹配 URL 模式
        - 提取 URL hash 和链接文本
        """
        records = []

        try:
            # V41.634: 深度调试模式 - 检查多种可能的数据源
            debug_js = """
            () => {
                const info = {
                    totalLinks: document.querySelectorAll('a').length,
                    totalScripts: document.querySelectorAll('script').length,
                    totalDivs: document.querySelectorAll('div').length,
                    pageTitle: document.title,
                    pageURL: window.location.href,
                };

                // 检查是否有 data-* 属性包含比赛数据
                const allElements = document.querySelectorAll('*');
                const dataElements = [];
                for (let elem of allElements) {
                    for (let attr of elem.attributes) {
                        if (attr.name.startsWith('data-') &&
                            (attr.name.includes('match') || attr.name.includes('event') || attr.name.includes('game'))) {
                            dataElements.push({
                                tag: elem.tagName,
                                attr: attr.name,
                                value: attr.value?.substring(0, 100)
                            });
                            if (dataElements.length >= 10) break;
                        }
                    }
                    if (dataElements.length >= 10) break;
                }
                info.dataElements = dataElements;

                // 检查 script 标签内容
                const scripts = Array.from(document.querySelectorAll('script'));
                const scriptsWithData = [];
                for (let script of scripts) {
                    const text = script.textContent || '';
                    if (text.includes('match') || text.includes('event') || text.includes('odds')) {
                        const sample = text.substring(0, 200);
                        scriptsWithData.push({
                            hasSrc: !!script.src,
                            sampleLength: text.length,
                            sample: sample
                        });
                        if (scriptsWithData.length >= 5) break;
                    }
                }
                info.scriptsWithData = scriptsWithData;

                // 查找所有包含 8 字符 hash 的元素
                const hashPattern = /\\b[a-z0-9]{8}\\b/gi;
                const hashElements = [];
                for (let elem of allElements) {
                    const text = elem.textContent || '';
                    const hashes = text.match(hashPattern);
                    if (hashes && hashes.length > 0) {
                        hashElements.push({
                            tag: elem.tagName,
                            className: elem.className,
                            textSample: text.substring(0, 100),
                            hashes: hashes.slice(0, 5)
                        });
                        if (hashElements.length >= 10) break;
                    }
                }
                info.hashElements = hashElements;

                // 获取页面 HTML 的前 5000 字符
                info.htmlSample = document.body.innerHTML.substring(0, 5000);

                return info;
            }
            """

            debug_result = await page.evaluate(debug_js)
            logger.info(f"  🔍 深度调试信息:")
            logger.info(f"    - 页面标题: {debug_result.get('pageTitle')}")
            logger.info(f"    - 总链接数: {debug_result.get('totalLinks')}")
            logger.info(f"    - Script 标签数: {debug_result.get('totalScripts')}")
            logger.info(f"    - Div 元素数: {debug_result.get('totalDivs')}")
            logger.info(f"    - Data 属性元素: {len(debug_result.get('dataElements', []))}")
            logger.info(f"    - 包含数据的脚本: {len(debug_result.get('scriptsWithData', []))}")
            logger.info(f"    - 包含 hash 的元素: {len(debug_result.get('hashElements', []))}")

            # 显示包含 hash 的元素样本
            if debug_result.get('hashElements'):
                logger.info(f"  📋 包含 8 字符 hash 的元素样本:")
                for i, elem in enumerate(debug_result.get('hashElements', [])[:3]):
                    logger.info(f"    {i+1}. tag={elem.get('tag')}, class={elem.get('className')}, hashes={elem.get('hashes')}")

            # 显示 HTML 样本
            html_sample = debug_result.get('htmlSample', '')
            if html_sample:
                logger.info(f"  📄 页面 HTML 样本 (前 1000 字符):")
                logger.info(f"    {html_sample[:1000]}")

            # V41.634: 分析 script 标签内容，提取可能的比赛数据
            # Vue.js SPA 将数据存储在 script 标签或 window 对象中
            js_code = """
            () => {
                const results = [];

                // 方法1: 检查 window 对象中的 Vue 数据
                if (window.__INITIAL_STATE__ || window.__NUXT__ || window.__VUE_DATA__) {
                    const vueData = window.__INITIAL_STATE__ || window.__NUXT__ || window.__VUE_DATA__;
                    results.push({
                        source: 'window_object',
                        type: typeof vueData,
                        sample: JSON.stringify(vueData).substring(0, 500)
                    });
                }

                // 方法2: 提取所有 script 标签内容
                const scripts = Array.from(document.querySelectorAll('script'));
                const scriptContents = [];
                for (let script of scripts) {
                    if (!script.src && script.textContent) {
                        const text = script.textContent.trim();
                        if (text.length > 50) {
                            scriptContents.push({
                                length: text.length,
                                content: text.substring(0, 1000)
                            });
                        }
                    }
                }
                results.push({
                    source: 'script_tags',
                    count: scriptContents.length,
                    scripts: scriptContents.slice(0, 5)  // 前5个
                });

                // 方法3: 搜索所有包含 8 字母数字混合的 hash (OddsPortal 格式)
                // OddsPortal 的比赛 hash 是 8 位字母数字混合 (如: 2gtNqWxK, z3ro5w5c, CrfO0IE4)
                const allText = document.body.textContent || '';
                const hashPattern = /\\b([a-zA-Z0-9]{8})\\b/g;
                const hashes = new Set();
                let match;
                while ((match = hashPattern.exec(allText)) !== null) {
                    const hash = match[1];
                    // 过滤掉常见的 8 字母单词
                    const commonWords = ['Football', 'selected', 'browsing', 'hostname', 'document', 'function'];
                    if (!commonWords.includes(hash)) {
                        hashes.add(hash);
                    }
                }

                results.push({
                    source: 'body_text_hashes',
                    count: hashes.size,
                    hashes: Array.from(hashes).slice(0, 50)  // 前50个
                });

                return results;
            }
            """

            analysis_result = await page.evaluate(js_code)
            logger.info(f"  🔍 V41.634 深度分析结果:")

            # 分析每个结果
            for item in analysis_result:
                source = item.get('source')
                logger.info(f"    • 数据源: {source}")

                if source == 'window_object':
                    logger.info(f"      类型: {item.get('type')}")
                    logger.info(f"      样本: {item.get('sample')[:200]}...")

                elif source == 'script_tags':
                    logger.info(f"      Script 数量: {item.get('count')}")
                    for i, script in enumerate(item.get('scripts', [])):
                        logger.info(f"      Script {i+1}: 长度={script.get('length')}")
                        # 检查是否包含可能的比赛数据
                        content = script.get('content', '')
                        if 'match' in content.lower() or 'event' in content.lower():
                            logger.info(f"        内容预览: {content[:300]}...")

                elif source == 'body_text_hashes':
                    hash_list = item.get('hashes', [])
                    logger.info(f"      发现 {len(hash_list)} 个可能的 hash")
                    if hash_list:
                        logger.info(f"      前20个: {hash_list[:20]}")

            # 如果找到了 hash，尝试创建记录
            hash_list = []
            for item in analysis_result:
                if item.get('source') == 'body_text_hashes':
                    hash_list = item.get('hashes', [])
                    break

            page_data = []
            if hash_list:
                for h in hash_list:
                    page_data.append({
                        'urlHash': h,
                        'fullUrl': f"https://www.oddsportal.com/football/matches/{h}/",
                        'rawText': 'extracted_from_body'
                    })
                logger.info(f"  📋 V41.634 文本提取: 遍历 {len(page_data)} 个 hash")
            else:
                logger.info(f"  ⚠️  未发现任何 hash")

            # 使用集合去重（基于 hash）
            seen_hashes = {}

            # 转换为 SourceMatchRecord
            for item in page_data:
                try:
                    url_hash = item.get('urlHash')
                    if not url_hash:
                        continue

                    # 去重：保留第一次出现的记录
                    if url_hash in seen_hashes:
                        continue
                    seen_hashes[url_hash] = True

                    raw_text = item.get('rawText', '')

                    records.append(SourceMatchRecord(
                        match_date=None,  # 日期将在后续匹配中推断
                        home_team=raw_text,  # 先把原始文本存入
                        away_team='',  # 待解析
                        url_hash=url_hash,
                        full_url=item.get('fullUrl', ''),
                        league_name=league_name,
                        season=season,
                    ))

                except Exception as e:
                    logger.debug(f"    ⚠️  记录转换失败: {e}")
                    continue

            logger.info(f"  ✅ V41.634 提取到 {len(records)} 条唯一记录")

        except Exception as e:
            logger.error(f"  ❌ V41.634 DOM 提取失败: {e}")

        return records

    def _parse_json_response(
        self,
        data: dict | list,
        response_url: str,
        league_name: str,
        season: str,
    ) -> list[SourceMatchRecord]:
        """V41.633: 解析 JSON 响应数据，提取比赛信息.

        Args:
            data: JSON 数据（dict 或 list）
            response_url: 响应 URL
            league_name: 联赛名称
            season: 赛季

        Returns:
            提取的比赛记录列表
        """
        records = []

        try:
            # V41.633: 专门处理 archive 类型的 AJAX 请求
            if "archive" in response_url.lower():
                logger.info(f"    🎯 发现 archive 类型请求，尝试深度解析...")
                # 这种类型的请求通常包含嵌套的比赛数据
                # 尝试递归搜索所有可能的比赛数据
                records = self._deep_search_json(data, league_name, season)
                if records:
                    logger.info(f"    ✓ 深度搜索找到 {len(records)} 条记录")
                    return records

            # 处理不同类型的 JSON 结构
            if isinstance(data, dict):
                # 情况 1: 标准的 API 响应格式
                # {"data": [...], "matches": [...], "results": [...]}
                for key in ["data", "matches", "results", "events", "items", "rows"]:
                    if key in data and isinstance(data[key], list):
                        records.extend(self._extract_from_list(data[key], league_name, season))
                        break

                # 情况 2: 嵌套结构
                # {"pagination": {"data": [...]}}
                if "pagination" in data and isinstance(data["pagination"], dict):
                    pagination = data["pagination"]
                    for key in ["data", "results", "matches"]:
                        if key in pagination and isinstance(pagination[key], list):
                            records.extend(self._extract_from_list(pagination[key], league_name, season))
                            break

            elif isinstance(data, list):
                # 情况 3: 直接是列表
                records.extend(self._extract_from_list(data, league_name, season))

            if records:
                logger.info(f"    ✓ 从 {response_url} 解析出 {len(records)} 条记录")

        except Exception as e:
            logger.debug(f"    ⚠️  JSON 解析失败: {e}")

        return records

    def _deep_search_json(
        self,
        data: Any,
        league_name: str,
        season: str,
    ) -> list[SourceMatchRecord]:
        """V41.633: 深度搜索 JSON 数据，提取比赛信息.

        递归搜索所有可能的比赛数据结构。

        Args:
            data: JSON 数据（可以是 dict, list, 或其他类型）
            league_name: 联赛名称
            season: 赛季

        Returns:
            提取的比赛记录列表
        """
        records = []

        def search_recursive(obj, depth=0):
            """递归搜索对象."""
            if depth > 10:  # 限制递归深度
                return

            if isinstance(obj, dict):
                # 检查是否包含比赛信息的键
                has_team_data = any(key in obj for key in ["home_team", "away_team", "home", "away", "team1", "team2"])
                has_id_data = any(key in obj for key in ["id", "match_id", "hash", "url"])

                if has_team_data and has_id_data:
                    # 尝试从这个对象提取比赛记录
                    extracted = self._extract_from_list([obj], league_name, season)
                    if extracted:
                        records.extend(extracted)
                        return

                # 递归搜索所有值
                for value in obj.values():
                    search_recursive(value, depth + 1)

            elif isinstance(obj, list) and len(obj) > 0:
                # 检查是否是包含比赛数据的列表
                first_item = obj[0]
                if isinstance(first_item, dict):
                    # 检查第一个元素是否包含比赛信息
                    if any(key in first_item for key in ["home_team", "away_team", "home", "away", "team1", "team2"]):
                        # 尝试从这个列表提取比赛记录
                        extracted = self._extract_from_list(obj, league_name, season)
                        if extracted:
                            records.extend(extracted)
                            return

                # 递归搜索所有元素
                for item in obj[:50]:  # 限制检查的元素数量
                    search_recursive(item, depth + 1)

        search_recursive(data)
        return records

    def _extract_from_list(
        self,
        items: list,
        league_name: str,
        season: str,
    ) -> list[SourceMatchRecord]:
        """从列表中提取比赛记录.

        Args:
            items: 数据列表
            league_name: 联赛名称
            season: 赛季

        Returns:
            提取的比赛记录列表
        """
        records = []

        for item in items:
            try:
                if not isinstance(item, dict):
                    continue

                # 提取 URL hash
                url_hash = None
                full_url = None

                # 尝试多种可能的字段名
                for key in ["id", "match_id", "hash", "url_hash", "_id"]:
                    if key in item:
                        hash_value = str(item[key])
                        if len(hash_value) == 8 and hash_value.isalnum():
                            url_hash = hash_value
                            break

                # 尝试从 URL 字段提取 hash
                if not url_hash:
                    for key in ["url", "match_url", "link", "href"]:
                        if key in item:
                            url_value = str(item[key])
                            hash_match = re.search(r"/([a-z0-9]{8})", url_value)
                            if hash_match:
                                url_hash = hash_match.group(1)
                                full_url = url_value if url_value.startswith("http") else f"{BASE_URL}{url_value}"
                                break

                # 如果找到 URL，构建完整 URL
                if url_hash and not full_url:
                    full_url = f"{BASE_URL}/football/matches/{url_hash}/"

                # 提取球队名
                home_team = ""
                away_team = ""

                # 尝试多种可能的字段名
                for home_key in ["home_team", "homeTeam", "home", "team1", "team_a"]:
                    if home_key in item:
                        home_team = str(item[home_key]).strip()
                        break

                for away_key in ["away_team", "awayTeam", "away", "team2", "team_b"]:
                    if away_key in item:
                        away_team = str(item[away_key]).strip()
                        break

                # 提取日期
                match_date = None
                for date_key in ["date", "match_date", "time", "start_time", "datetime"]:
                    if date_key in item:
                        date_value = item[date_key]
                        if isinstance(date_value, str):
                            match_date = self._parse_match_date(date_value)
                        elif isinstance(date_value, (int, float)):
                            # 可能是 Unix 时间戳
                            match_date = datetime.fromtimestamp(date_value)
                        break

                # 只保留有效记录
                if url_hash and (home_team or away_team):
                    records.append(SourceMatchRecord(
                        match_date=match_date or datetime.now(),
                        home_team=home_team,
                        away_team=away_team,
                        url_hash=url_hash,
                        full_url=full_url or f"{BASE_URL}/football/matches/{url_hash}/",
                        league_name=league_name,
                        season=season,
                    ))

            except Exception as e:
                logger.debug(f"    ⚠️  项解析失败: {e}")
                continue

        return records

    async def _extract_match_row(
        self,
        row_element: Any,
        league_name: str,
        season: str,
    ) -> SourceMatchRecord | None:
        """从单行提取比赛数据.

        Args:
            row_element: Playwright ElementHandle
            league_name: 联赛名称
            season: 赛季

        Returns:
            源比赛记录或 None
        """
        try:
            # 提取日期
            date_cell = await row_element.query_selector("td:first-child")
            if not date_cell:
                return None

            date_text = await date_cell.inner_text()
            match_date = self._parse_match_date(date_text)

            # 提取球队名
            # 目标站点结构：通常在 <a> 标签中
            team_links = await row_element.query_selector_all("a[href*='/football/matches/']")
            if len(team_links) < 2:
                return None

            home_team_text = await team_links[0].inner_text()
            away_team_text = await team_links[1].inner_text()

            # 提取 URL hash
            detail_link = await row_element.query_selector("a[href*='/football/matches/']")
            if not detail_link:
                return None

            href = await detail_link.get_attribute("href")
            if not href:
                return None

            # 从 URL 中提取 hash (8位字符)
            # URL 格式: /football/matches/xxxxxxxx/...
            url_match = re.search(r"/football/matches/([a-z0-9]{8})", href)
            if not url_match:
                return None

            url_hash = url_match.group(1)
            full_url = f"{BASE_URL}{href}"

            return SourceMatchRecord(
                match_date=match_date,
                home_team=home_team_text.strip(),
                away_team=away_team_text.strip(),
                url_hash=url_hash,
                full_url=full_url,
                league_name=league_name,
                season=season,
            )

        except Exception as e:
            logger.debug(f"    ⚠️  行解析失败: {e}")
            return None

    def _parse_match_date(self, date_text: str) -> datetime:
        """解析比赛日期.

        Args:
            date_text: 日期文本 (如 "12.01.2025", "12/01/2025")

        Returns:
            datetime 对象
        """
        # 尝试多种日期格式
        formats = [
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d %b %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue

        # 默认返回当前时间
        logger.warning(f"  ⚠️  无法解析日期: {date_text}")
        return datetime.now()


# ============================================================================
# Step 2: Fuzzy Match Engine
# ============================================================================


class FuzzyMatchEngine:
    """V41.631 Step 2: 模糊匹配引擎.

    使用球队名语义相似度和时间窗口匹配目标记录。
    """

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        time_window_days: int = TIME_WINDOW_DAYS,
    ) -> None:
        """初始化匹配引擎.

        Args:
            confidence_threshold: 置信度阈值 (0-1)
            time_window_days: 时间窗口（天）
        """
        self.confidence_threshold = confidence_threshold
        self.time_window_days = time_window_days
        self.team_normalizer = TeamNameNormalizer()
        self.youth_detector = YouthTeamDetector()

    def find_best_match(
        self,
        target_record: MatchMappingRecord,
        source_records: list[SourceMatchRecord],
    ) -> MatchResult | None:
        """在源记录中查找最佳匹配.

        Args:
            target_record: 目标记录（数据库中缺失 URL 的记录）
            source_records: 源记录列表（从目标站点爬取）

        Returns:
            匹配结果或 None
        """
        if not source_records:
            return None

        best_match: MatchResult | None = None
        best_score = 0.0

        for source in source_records:
            # 阶段 1: 时间锚定（硬约束）
            if not self._is_within_time_window(target_record.match_date, source.match_date):
                continue

            # 阶段 2: 青年队碰撞检测
            if self._has_youth_team_collision(target_record, source):
                continue

            # 阶段 3: 计算文本相似度
            home_similarity = self._calculate_team_similarity(
                target_record.home_team or "",
                source.home_team,
            )
            away_similarity = self._calculate_team_similarity(
                target_record.away_team or "",
                source.away_team,
            )

            # 综合相似度（主队和客队的加权平均）
            overall_similarity = (home_similarity + away_similarity) / 2

            # 时间差异惩罚 (V41.634: 处理 None 日期)
            if source.match_date and target_record.match_date:
                date_diff = abs((target_record.match_date - source.match_date).days)
                time_penalty = max(0, 1 - (date_diff / (self.time_window_days * 2)))
            else:
                # 如果任一日期缺失，使用中性惩罚
                date_diff = 0
                time_penalty = 0.85  # 轻微惩罚

            # 最终分数
            final_score = overall_similarity * time_penalty

            if final_score > best_score:
                best_score = final_score
                best_match = MatchResult(
                    fotmob_id=target_record.fotmob_id,
                    matched_url=source.full_url,
                    confidence=final_score / 100,  # 转换为 0-1 范围
                    home_similarity=home_similarity,
                    away_similarity=away_similarity,
                    date_diff_days=date_diff,
                    source_record=source,
                )

        # 检查阈值
        if best_match and best_match.confidence >= self.confidence_threshold:
            return best_match

        return None

    def _is_within_time_window(
        self,
        target_date: datetime | None,
        source_date: datetime | None,
    ) -> bool:
        """检查是否在时间窗口内.

        Args:
            target_date: 目标日期
            source_date: 源日期

        Returns:
            True 如果在时间窗口内
        """
        # V41.634: 如果任一日期为 None，不进行时间过滤
        if not target_date or not source_date:
            return True

        time_diff = abs((target_date - source_date).days)
        return time_diff <= self.time_window_days

    def _has_youth_team_collision(
        self,
        target: MatchMappingRecord,
        source: SourceMatchRecord,
    ) -> bool:
        """检查是否存在青年队碰撞.

        Args:
            target: 目标记录
            source: 源记录

        Returns:
            True 如果存在青年队碰撞
        """
        target_home = target.home_team or ""
        target_away = target.away_team or ""
        source_home = source.home_team
        source_away = source.away_team

        # 检查主队碰撞
        if self.youth_detector.are_different_tiers(target_home, source_home):
            return True

        # 检查客队碰撞
        if self.youth_detector.are_different_tiers(target_away, source_away):
            return True

        return False

    def _calculate_team_similarity(self, name1: str, name2: str) -> float:
        """计算球队名相似度.

        使用 TeamNameNormalizer.fuzzy_match() 方法。

        Args:
            name1: 球队名1
            name2: 球队名2

        Returns:
            相似度分数 (0-100)
        """
        return self.team_normalizer.fuzzy_match(name1, name2)


# ============================================================================
# Step 3: Database Update
# ============================================================================


class MappingRecoveryService:
    """V41.631 Step 3: 数据库映射恢复服务.

    整合爬取和匹配，执行完整的修复流程。
    """

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        concurrent_workers: int = DEFAULT_CONCURRENT_WORKERS,
        dry_run: bool = False,
    ) -> None:
        """初始化服务.

        Args:
            confidence_threshold: 置信度阈值
            concurrent_workers: 并发工作线程数
            dry_run: 是否为干跑模式
        """
        self.confidence_threshold = confidence_threshold
        self.concurrent_workers = concurrent_workers
        self.dry_run = dry_run

        self.scraper = LeagueHistoryScraper(concurrent_workers=concurrent_workers)
        self.engine = FuzzyMatchEngine(confidence_threshold=confidence_threshold)
        self.stats = RecoveryStats()

        # 数据库连接
        self.settings = get_settings()
        self._db_conn = None

    @property
    def db_conn(self):
        """获取数据库连接（懒加载）."""
        if self._db_conn is None:
            self._db_conn = psycopg2.connect(
                host=self.settings.database.host,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._db_conn

    def close(self) -> None:
        """关闭数据库连接."""
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None

    def get_missing_url_records(
        self,
        league_name: str | None = None,
        season: str | None = None,
        limit: int | None = None,
    ) -> list[MatchMappingRecord]:
        """获取缺失 URL 的记录.

        Args:
            league_name: 联赛过滤
            season: 赛季过滤
            limit: 限制数量

        Returns:
            缺失 URL 的记录列表
        """
        query = """
            SELECT
                fotmob_id,
                match_date,
                home_team,
                away_team,
                league_name,
                season,
                oddsportal_url
            FROM matches_mapping
            WHERE oddsportal_url IS NULL
        """

        params = []
        conditions = []

        if league_name:
            conditions.append("league_name = %s")
            params.append(league_name)

        if season:
            conditions.append("season = %s")
            params.append(season)

        if conditions:
            query += " AND " + " AND ".join(conditions)

        if limit:
            query += f" LIMIT {limit}"

        with self.db_conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        return [MatchMappingRecord.from_db_row(row) for row in rows]

    def update_mapping_record(
        self,
        fotmob_id: str,
        oddsportal_url: str,
        confidence: float,
    ) -> bool:
        """更新单条映射记录.

        Args:
            fotmob_id: FotMob ID
            oddsportal_url: OddsPortal URL
            confidence: 置信度

        Returns:
            True 如果更新成功
        """
        if self.dry_run:
            logger.info(f"  🔕 [DRY RUN] 将更新: {fotmob_id} → {oddsportal_url}")
            return True

        query = """
            UPDATE matches_mapping
            SET
                oddsportal_url = %s,
                confidence = %s,
                mapping_method = 'v41_631_fuzzy_recovery',
                updated_at = NOW()
            WHERE fotmob_id = %s
        """

        try:
            with self.db_conn.cursor() as cur:
                cur.execute(query, (oddsportal_url, confidence, fotmob_id))
                self.db_conn.commit()
                return True
        except Exception as e:
            logger.error(f"  ❌ 更新失败 {fotmob_id}: {e}")
            self.db_conn.rollback()
            return False

    async def run_recovery(
        self,
        league_name: str | None = None,
        season: str | None = None,
        limit: int | None = None,
    ) -> RecoveryStats:
        """执行完整的恢复流程.

        Args:
            league_name: 联赛过滤
            season: 赛季过滤
            limit: 限制数量

        Returns:
            恢复统计
        """
        logger.info("=" * 80)
        logger.info("V41.631 Cross-Source Mapping Recovery - 启动")
        logger.info("=" * 80)

        # 获取缺失记录
        logger.info("\n📊 Step 0: 获取缺失 URL 的记录...")
        missing_records = self.get_missing_url_records(league_name, season, limit)
        self.stats.total_missing = len(missing_records)

        logger.info(f"  • 找到 {len(missing_records)} 条缺失记录")

        if not missing_records:
            logger.info("  ✅ 无需修复，所有记录均有 URL")
            return self.stats

        # 按联赛分组
        from collections import defaultdict

        grouped = defaultdict(list)
        for record in missing_records:
            key = (record.league_name or "unknown", record.season or "unknown")
            grouped[key].append(record)

        logger.info(f"  • 涉及 {len(grouped)} 个联赛/赛季组合")

        # 逐个联赛处理
        for (league, season), records in grouped.items():
            logger.info(f"\n🏆 处理联赛: {league} - {season} ({len(records)} 条记录)")
            self.stats.leagues_scanned.append(f"{league} {season}")

            # Step 1: 爬取源数据
            logger.info(f"  Step 1: 爬取源数据...")
            source_records = await self.scraper.scrape_league_season(league, season)
            self.stats.total_source_records += len(source_records)

            if not source_records:
                logger.warning(f"  ⚠️  未获取到源数据，跳过该联赛")
                self.stats.no_match += len(records)
                continue

            # Step 2: 执行匹配
            logger.info(f"  Step 2: 执行模糊匹配...")
            for target_record in records:
                self.stats.total_processed += 1

                result = self.engine.find_best_match(target_record, source_records)

                if result:
                    # Step 3: 更新数据库
                    success = self.update_mapping_record(
                        result.fotmob_id,
                        result.matched_url,
                        result.confidence,
                    )

                    if success:
                        # 按置信度分类
                        if result.confidence >= 0.95:
                            self.stats.high_confidence_matches += 1
                            logger.info(
                                f"    ✅ HIGH: {result.fotmob_id} → {result.matched_url[-50:]} "
                                f"({result.confidence:.2%})"
                            )
                        elif result.confidence >= 0.90:
                            self.stats.medium_confidence_matches += 1
                            logger.info(
                                f"    ✅ MEDIUM: {result.fotmob_id} → {result.matched_url[-50:]} "
                                f"({result.confidence:.2%})"
                            )
                        else:
                            self.stats.low_confidence_matches += 1
                            logger.info(
                                f"    ✅ LOW: {result.fotmob_id} → {result.matched_url[-50:]} "
                                f"({result.confidence:.2%})"
                            )
                else:
                    self.stats.no_match += 1
                    logger.debug(f"    ❌ 无匹配: {target_record.fotmob_id}")

        logger.info("\n" + "=" * 80)
        logger.info("V41.631 恢复完成")
        logger.info("=" * 80)

        return self.stats


# ============================================================================
# CLI
# ============================================================================


@click.command()
@click.option(
    "--league",
    "-l",
    help="指定联赛名称 (如 'Premier League')",
    type=str,
    default=None,
)
@click.option(
    "--season",
    "-s",
    help="指定赛季 (如 '2024/2025')",
    type=str,
    default=None,
)
@click.option(
    "--limit",
    "-n",
    help="限制处理记录数 (用于测试)",
    type=int,
    default=None,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="干跑模式（不实际更新数据库）",
)
@click.option(
    "--stats-only",
    is_flag=True,
    help="仅显示统计信息",
)
@click.option(
    "--confidence",
    "-c",
    help="置信度阈值 (0-1, 默认 0.80)",
    type=float,
    default=DEFAULT_CONFIDENCE_THRESHOLD,
)
@click.option(
    "--workers",
    "-w",
    help="并发工作线程数",
    type=int,
    default=DEFAULT_CONCURRENT_WORKERS,
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="详细输出",
)
def main(
    league: str | None,
    season: str | None,
    limit: int | None,
    dry_run: bool,
    stats_only: bool,
    confidence: float,
    workers: int,
    verbose: bool,
) -> None:
    """V41.631 Cross-Source Mapping Recovery CLI.

    修复 matches_mapping 表中缺失的 oddsportal_url。

    示例:

        # 查看统计信息
        python v41_631_cross_source_mapping_recovery.py --stats-only

        # 测试模式（10 条记录）
        python v41_631_cross_source_mapping_recovery.py --limit 10 --dry-run

        # 生产模式（所有记录）
        python v41_631_cross_source_mapping_recovery.py

        # 指定联赛
        python v41_631_cross_source_mapping_recovery.py --league "Premier League" --season "2024/2025"
    """
    # 配置日志
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 仅统计模式
    if stats_only:
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        league_name,
                        season,
                        COUNT(*) as missing_count
                    FROM matches_mapping
                    WHERE oddsportal_url IS NULL
                    GROUP BY league_name, season
                    ORDER BY missing_count DESC
                """)
                rows = cur.fetchall()

                print("\n╔══════════════════════════════════════════════════════════════════════╗")
                print("║              V41.631 缺失 URL 统计                                   ║")
                print("╚══════════════════════════════════════════════════════════════════════╝\n")

                total = 0
                for row in rows:
                    print(f"  {row['league_name']:20} {row['season']:12} {row['missing_count']:6} 条")
                    total += row["missing_count"]

                print(f"\n  总计: {total} 条缺失记录")

        finally:
            conn.close()
        return

    # 执行恢复
    service = MappingRecoveryService(
        confidence_threshold=confidence,
        concurrent_workers=workers,
        dry_run=dry_run,
    )

    try:
        stats = asyncio.run(service.run_recovery(league, season, limit))

        # 打印报告
        print(stats.summary())

    finally:
        service.close()


if __name__ == "__main__":
    main()
