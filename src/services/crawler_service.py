#!/usr/bin/env python3
"""
V41.83 Crawler Service - 网络爬虫服务层（重构版）
=============================================================

V41.83 更新:
- 深度扁平化：消除深层嵌套，使用 Guard Clauses
- 原子化拆解：将长方法拆分为私有辅助方法
- 严格类型化：补充所有方法的 Type Hints
- 异常对齐：使用自定义异常替代内置异常

设计原则:
- 单一职责: 每个方法只做一件事
- 提前返回: 使用 Guard Clauses 减少嵌套
- 透明化: 逻辑清晰，易于理解和测试

Author: 资深软件架构师
Version: V41.83
Date: 2026-01-15
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import random
import socket
import sys

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from src.api.collectors.bayesian_delay_engine import BayesianDelayEngine
from src.core.exceptions import NetworkError, ProxyError
from src.core.proxy_health_checker import ProxyHealthChecker
from src.core.semantic_refiner import SemanticRefiner
from src.services.harvest_config import AntiScrapingConfig

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class MatchInfo:
    """比赛信息（V41.83: 补充完整类型提示）"""

    match_id: str | None
    home_team: str
    away_team: str
    hash_value: str
    url: str
    confidence: float = 0.0
    league_name: str = ""
    season: str = ""


@dataclass
class CrawlStats:
    """爬虫统计"""

    visited: int = 0
    extracted: int = 0
    pages: int = 0
    last_proxy_port: int | None = None
    successful_matches: int = 0
    failed_matches: int = 0


@dataclass
class CrawlResult:
    """爬虫结果"""

    matches: list[MatchInfo]
    stats: CrawlStats
    success: bool
    error: str | None = None


# ============================================================================
# Crawler Service
# ============================================================================


class CrawlerService:
    """
    V41.83: 网络爬虫服务（重构版）

    负责所有网络通信相关操作：
    - Playwright 浏览器管理
    - 动态代理池管理（ProxyHealthChecker 自愈）
    - 页面翻页逻辑
    - DOM 数据提取
    - 语义化 URL 解析（SemanticRefiner）
    - 贝叶斯自适应延迟

    V41.83 重构:
    - 深度扁平化：消除深层嵌套，使用 Guard Clauses
    - 原子化拆解：长方法拆分为私有辅助方法
    - 严格类型化：补充所有方法的 Type Hints
    - 异常对齐：使用自定义异常替代内置异常
    """

    # V41.121: 使用统一配置（移除硬编码）
    MAX_CONCURRENT_REQUESTS: int = 3

    def __init__(
        self,
        db_conn,
        proxy_ports: list[int] | None = None,
        enable_bayesian: bool = True,
        enable_proxy_health_check: bool = True,
        headless: bool = True,
        confidence_threshold: float = 85.0,
        max_concurrent_requests: int | None = None,
    ) -> None:
        """
        V41.121: 初始化爬虫服务（重构版 - 零硬编码）

        Args:
            db_conn: 数据库连接（用于 SemanticRefiner）
            proxy_ports: 代理端口列表（默认从统一配置读取）
            enable_bayesian: 是否启用贝叶斯延迟引擎
            enable_proxy_health_check: 是否启用代理健康检查
            headless: 是否无头模式
            confidence_threshold: SemanticRefiner 置信度阈值
            max_concurrent_requests: 最大并发请求数
        """
        # V41.121: 从统一配置读取代理设置
        from src.config_unified import get_config

        config = get_config()
        proxy_config = config.proxy

        # V41.83: 基础属性初始化
        self.db_conn = db_conn
        self.proxy_ports = proxy_ports or proxy_config.proxy_ports
        self.enable_bayesian = enable_bayesian
        self.headless = headless

        # V41.80: 并发流控
        self.max_concurrent_requests = max_concurrent_requests or self.MAX_CONCURRENT_REQUESTS
        self._concurrency_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # V41.83: 模块化初始化（提取私有方法）
        self.semantic_refiner = self._initialize_semantic_refiner(db_conn, confidence_threshold)

        self.proxy_health_checker, self.available_ports = self._initialize_proxy_health_checker(
            enable_proxy_health_check
        )

        self.bayesian_engine = self._initialize_bayesian_engine(enable_bayesian)

        # 统计信息
        self.stats = CrawlStats()

        # V41.121: 环境检测 - 使用统一配置
        self.is_wsl2 = self._is_wsl2_environment()
        self.proxy_host = proxy_config.wsl2_bridge_host if self.is_wsl2 else "127.0.0.1"

        # V41.83: 统一日志记录
        self._log_initialization_status(
            enable_bayesian, enable_proxy_health_check, confidence_threshold
        )

    def _initialize_semantic_refiner(self, db_conn, confidence_threshold: float) -> SemanticRefiner:
        """
        V41.83: 初始化 SemanticRefiner

        Args:
            db_conn: 数据库连接
            confidence_threshold: 置信度阈值

        Returns:
            SemanticRefiner 实例
        """
        return SemanticRefiner(
            db_conn=db_conn,
            confidence_threshold=confidence_threshold,
        )

    def _initialize_proxy_health_checker(
        self, enable_proxy_health_check: bool
    ) -> tuple[ProxyHealthChecker | None, set[int]]:
        """
        V41.83: 初始化 ProxyHealthChecker

        Args:
            enable_proxy_health_check: 是否启用代理健康检查

        Returns:
            (ProxyHealthChecker 实例或 None, 可用端口集合)
        """
        if not enable_proxy_health_check:
            return None, set(self.proxy_ports)

        checker = ProxyHealthChecker(
            proxy_host=self._get_proxy_host(),
            check_interval=60,
            max_consecutive_failures=3,
        )
        checker.set_ports(self.proxy_ports)
        available_ports = checker.get_available_ports()

        # V41.83: 提前返回（Guard Clause）
        if len(available_ports) < 10:
            logger.warning(
                f"⚠️  V41.83: 可用代理端口数量较低 "
                f"({len(available_ports)}/{len(self.proxy_ports)})，"
                f"建议检查代理配置"
            )

        logger.info(
            f"🔍 V41.83: 代理健康检查已启用，"
            f"初始可用端口: {len(available_ports)}/{len(self.proxy_ports)}"
        )

        return checker, available_ports

    def _initialize_bayesian_engine(self, enable_bayesian: bool) -> BayesianDelayEngine | None:
        """
        V41.83: 初始化 BayesianDelayEngine

        Args:
            enable_bayesian: 是否启用贝叶斯延迟引擎

        Returns:
            BayesianDelayEngine 实例或 None
        """
        if not enable_bayesian:
            return None

        return BayesianDelayEngine(
            base_delay=30.0,
            min_delay=15.0,
            max_delay=300.0,
        )

    def _log_initialization_status(
        self, enable_bayesian: bool, enable_proxy_health_check: bool, confidence_threshold: float
    ) -> None:
        """
        V41.83: 记录初始化状态

        Args:
            enable_bayesian: 是否启用贝叶斯延迟引擎
            enable_proxy_health_check: 是否启用代理健康检查
            confidence_threshold: 置信度阈值
        """
        logger.info(
            f"✅ V41.83 CrawlerService 初始化完成 "
            f"(proxies={len(self.available_ports)}/{len(self.proxy_ports)}, "
            f"bayesian={enable_bayesian}, wsl2={self.is_wsl2}, "
            f"proxy_health_check={enable_proxy_health_check}, "
            f"confidence_threshold={confidence_threshold}, "
            f"max_concurrent={self.max_concurrent_requests})"
        )

    # ========================================================================
    # 环境检测
    # ========================================================================

    @staticmethod
    def _is_wsl2_environment() -> bool:
        """
        V41.83: 检测是否运行在 WSL2 环境

        Returns:
            True 如果运行在 WSL2 环境
        """
        try:
            with open("/proc/version") as f:
                version_content = f.read().lower()
                return "microsoft" in version_content and "wsl2" in version_content
        except (OSError, FileNotFoundError):
            return False

    def _get_proxy_host(self) -> str:
        """
        V41.121: 获取代理主机地址（使用统一配置）

        Returns:
            代理主机地址
        """
        from src.config_unified import get_config

        config = get_config()
        proxy_config = config.proxy

        is_wsl2 = self._is_wsl2_environment()
        if is_wsl2:
            return proxy_config.wsl2_bridge_host
        return "127.0.0.1"

    # ========================================================================
    # 代理管理
    # ========================================================================

    def get_proxy_port(self) -> int:
        """
        V41.83: 获取随机代理端口

        Returns:
            代理端口号
        """
        port = random.choice(self.proxy_ports)
        self.stats.last_proxy_port = port
        return port

    def check_proxy_health(self, port: int, timeout: float = 1.0) -> bool:
        """
        V41.83: 检查代理端口健康状态

        Args:
            port: 代理端口
            timeout: 连接超时时间

        Returns:
            True 如果端口可用
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.proxy_host, port))
            sock.close()
            return result == 0
        except OSError:
            return False

    def get_healthy_proxy_port(self, excluded_ports: set[int] | None = None) -> int | None:
        """
        V41.83: 获取健康的代理端口

        Args:
            excluded_ports: 要排除的端口集合

        Returns:
            可用的代理端口号，如果没有可用端口则返回 None
        """
        # V41.83: Guard Clause
        if excluded_ports is None:
            excluded_ports = set()

        # V41.83: 优先使用 ProxyHealthChecker 的可用端口
        if self.proxy_health_checker:
            self.available_ports = self.proxy_health_checker.get_available_ports()
            available = [p for p in self.available_ports if p not in excluded_ports]
        else:
            available = [p for p in self.proxy_ports if p not in excluded_ports]

        # V41.83: Guard Clause
        if not available:
            logger.warning("⚠️  没有可用的代理端口")
            return None

        return random.choice(available)

    # ========================================================================
    # 并发流控
    # ========================================================================

    async def _acquire_concurrency_slot(self) -> None:
        """V41.80: 获取并发槽位"""
        await self._concurrency_semaphore.acquire()

    def _release_concurrency_slot(self) -> None:
        """V41.80: 释放并发槽位"""
        self._concurrency_semaphore.release()

    # ========================================================================
    # DOM 提取
    # ========================================================================

    def extract_matches_from_html(
        self, html: str, league_name: str, season: str
    ) -> list[MatchInfo]:
        """
        V41.83: 从 HTML 提取比赛信息（使用 SemanticRefiner）

        Args:
            html: 页面 HTML
            league_name: 联赛名称
            season: 赛季

        Returns:
            MatchInfo 列表（包含 match_id）
        """
        soup = BeautifulSoup(html, "html.parser")
        matches = []

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            result = self.semantic_refiner.refine_url(href, league_name, season)

            # V41.83: 提取 MatchInfo 创建逻辑
            match_info = self._create_match_info_from_result(result, href)

            if match_info:
                matches.append(match_info)
                self.stats.successful_matches += 1
            else:
                self.stats.failed_matches += 1
                logger.debug(f"⚠️  URL 对齐失败: {href} - {result.failure_reason}")

        return matches

    async def extract_matches_from_dom(
        self, page: Page, league_name: str, season: str
    ) -> list[MatchInfo]:
        """
        V41.83: 从 Playwright Page 对象提取比赛信息

        Args:
            page: Playwright Page 对象
            league_name: 联赛名称
            season: 赛季

        Returns:
            MatchInfo 列表（包含 match_id）
        """
        # V41.83: 提取 JavaScript 代码逻辑
        matches = await self._extract_links_from_page(page)
        return self._parse_matches_to_info(matches, league_name, season)

    async def _extract_links_from_page(self, page: Page) -> list[dict]:
        """
        V41.83: 从页面提取链接（JavaScript 执行）

        Args:
            page: Playwright Page 对象

        Returns:
            链接列表
        """
        return await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (href && href.match(/[A-Za-z0-9]{8}\\/?$/)) {
                        results.push({ href: href });
                    }
                });

                return results;
            }
        """)

    def _parse_matches_to_info(
        self, matches: list[dict], league_name: str, season: str
    ) -> list[MatchInfo]:
        """
        V41.83: 将比赛链接解析为 MatchInfo 列表

        Args:
            matches: 比赛链接列表
            league_name: 联赛名称
            season: 赛季

        Returns:
            MatchInfo 列表
        """
        parsed_matches = []

        for match in matches:
            href = match.get("href", "")
            result = self.semantic_refiner.refine_url(href, league_name, season)

            # V41.83: 提取 MatchInfo 创建逻辑
            match_info = self._create_match_info_from_result(result, href)

            if match_info:
                parsed_matches.append(match_info)
                self.stats.successful_matches += 1
            else:
                self.stats.failed_matches += 1
                logger.debug(f"⚠️  URL 对齐失败: {href} - {result.failure_reason}")

        return parsed_matches

    def _create_match_info_from_result(self, result, href: str) -> MatchInfo | None:
        """
        V41.83: 从 SemanticRefiner 结果创建 MatchInfo

        Args:
            result: SemanticRefiner 结果
            href: URL

        Returns:
            MatchInfo 对象或 None（如果不匹配）
        """
        # V41.83: Guard Clause
        if not result.is_match:
            return None

        return MatchInfo(
            match_id=result.match_id,
            home_team=result.home_team,
            away_team=result.away_team,
            hash_value=result.hash_value,
            url=href,
            confidence=result.confidence,
            league_name=result.league_name,
            season=result.season,
        )

    # ========================================================================
    # 延迟管理
    # ========================================================================

    async def calculate_delay(self, last_success: bool | None = None) -> float:
        """
        V41.83: 计算延迟时间（贝叶斯或随机）

        Args:
            last_success: 上一次请求是否成功

        Returns:
            延迟时间（秒）
        """
        # V41.83: Guard Clause
        if not self.bayesian_engine:
            return random.uniform(5, 9)

        delay = self.bayesian_engine.calculate_delay(last_success=last_success)
        logger.debug(f"🧠 贝叶斯延迟: {delay:.1f}s")
        return delay

    async def wait_with_delay(self, last_success: bool | None = None) -> None:
        """
        V41.83: 等待延迟时间

        Args:
            last_success: 上一次请求是否成功
        """
        delay = await self.calculate_delay(last_success)
        logger.debug(f"⏳ 等待 {delay:.1f}s...")
        await asyncio.sleep(delay)

    # ========================================================================
    # 核心爬取方法
    # ========================================================================

    async def crawl_league(
        self,
        league_name: str,
        season: str,
        base_url: str,
        max_pages: int = 10,
        tier: int = 1,
    ) -> CrawlResult:
        """
        V41.83: 爬取联赛比赛信息（重构版）

        Args:
            league_name: 联赛名称
            season: 赛季
            base_url: 基础 URL
            max_pages: 最大页数
            tier: 联赛等级（影响延迟）

        Returns:
            CrawlResult 对象
        """
        # V41.83: Guard Clauses - 验证前置条件
        validation_error = self._validate_crawl_prerequisites()
        if validation_error:
            return validation_error

        # V41.83: 初始化
        all_matches: list[MatchInfo] = []
        stats = CrawlStats()
        empty_page_count = 0

        # V41.83: 记录开始信息
        self._log_crawl_start(league_name, season, base_url, max_pages)

        # V41.83: 主循环
        try:
            async with async_playwright() as p:
                browser, page, proxy_port = await self._initialize_browser(p)

                if not browser or not page:
                    return CrawlResult(
                        matches=[], stats=stats, success=False, error="浏览器初始化失败"
                    )

                try:
                    await self._navigate_to_base_page(page, base_url)
                    await self.wait_with_delay(last_success=None)

                    # V41.83: 页面处理循环
                    for page_num in range(1, max_pages + 1):
                        page_result = await self._process_single_page(
                            page, page_num, league_name, season, proxy_port, empty_page_count
                        )

                        all_matches.extend(page_result.matches)
                        empty_page_count = page_result.empty_page_count

                        # V41.83: 检查是否应该结束
                        if page_result.should_stop:
                            break

                        # V41.83: 翻页
                        navigate_result = await self._navigate_to_next_page(
                            page, page_num, base_url
                        )

                        if not navigate_result.success:
                            break

                        await self.wait_with_delay(last_success=len(page_result.matches) > 0)

                    # V41.83: 收割冷却期
                    await self._apply_cooldown_period(all_matches)

                finally:
                    await self._cleanup_browser(browser)

        except Exception as e:
            logger.exception(f"❌ V41.83 crawl_league 失败: {e}")
            return CrawlResult(matches=all_matches, stats=stats, success=False, error=str(e))

        finally:
            self._log_crawl_statistics(league_name, all_matches, stats)

        stats.extracted = len(all_matches)
        return CrawlResult(matches=all_matches, stats=stats, success=True)

    def _validate_crawl_prerequisites(self) -> CrawlResult | None:
        """
        V41.83: 验证爬取前置条件

        Returns:
            CrawlResult 如果验证失败，否则 None
        """
        if not async_playwright:
            logger.error("❌ Playwright 未安装")
            return CrawlResult(
                matches=[], stats=CrawlStats(), success=False, error="Playwright 未安装"
            )
        return None

    def _log_crawl_start(
        self, league_name: str, season: str, base_url: str, max_pages: int
    ) -> None:
        """
        V41.83: 记录爬取开始信息

        Args:
            league_name: 联赛名称
            season: 赛季
            base_url: 基础 URL
            max_pages: 最大页数
        """
        logger.info(f"🚀 V41.83 开始爬取: {league_name} {season}")
        logger.info(f"   URL: {base_url}")
        logger.info(f"   最大页数: {max_pages}")
        logger.info("   🔌 代理池状态:")
        logger.info(f"      可用端口: {len(self.available_ports)}/{len(self.proxy_ports)}")
        logger.info(f"      健康检查: {'已启用' if self.proxy_health_checker else '已禁用'}")

    async def _initialize_browser(self, playwright_instance):
        """
        V41.83: 初始化浏览器

        Args:
            playwright_instance: Playwright 实例

        Returns:
            (browser, page, proxy_port) 元组
        """
        proxy_port = self.get_healthy_proxy_port()

        # V41.83: Guard Clause
        if not proxy_port:
            logger.error("❌ 无可用代理端口")
            raise ProxyError("无可用代理端口")

        browser = await playwright_instance.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )

        proxy_config = f"http://{self.proxy_host}:{proxy_port}"
        logger.info(f"🔌 使用代理: {proxy_config} (WSL2={self.is_wsl2})")

        context = await browser.new_context(
            proxy={"server": proxy_config},
            user_agent=random.choice(AntiScrapingConfig.USER_AGENTS),
            viewport=random.choice(AntiScrapingConfig.VIEWPORT_SIZES),
            locale=random.choice(AntiScrapingConfig.BROWSER_LOCALES),
            timezone_id=random.choice(AntiScrapingConfig.BROWSER_TIMEZONES),
        )

        page = await context.new_page()
        return browser, page, proxy_port

    async def _navigate_to_base_page(self, page: Page, base_url: str) -> None:
        """
        V41.83: 导航到基础页面

        Args:
            page: Playwright Page 对象
            base_url: 基础 URL

        Raises:
            NetworkError: 如果导航失败
        """
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            raise NetworkError(f"导航到基础页面失败: {e}")

    async def _process_single_page(
        self,
        page: Page,
        page_num: int,
        league_name: str,
        season: str,
        proxy_port: int,
        empty_page_count: int,
    ):
        """
        V41.83: 处理单个页面

        Args:
            page: Playwright Page 对象
            page_num: 当前页码
            league_name: 联赛名称
            season: 赛季
            proxy_port: 代理端口
            empty_page_count: 空页面计数

        Returns:
            页面处理结果对象
        """
        from dataclasses import dataclass

        @dataclass
        class PageResult:
            matches: list[MatchInfo]
            empty_page_count: int
            should_stop: bool

        logger.info(f"📖 正在处理第 {page_num} 页...")
        logger.info(f"   🔌 当前可用代理端口: {len(self.available_ports)}/{len(self.proxy_ports)}")

        # V41.83: 提取比赛
        matches = await self.extract_matches_from_dom(page, league_name, season)
        self.stats.pages += 1
        self.stats.visited += 1

        logger.info(
            f"   提取到 {len(matches)} 场比赛 "
            f"(成功: {self.stats.successful_matches}, "
            f"失败: {self.stats.failed_matches})"
        )

        # V41.83: 处理空页面熔断
        new_empty_count, should_stop = await self._handle_empty_page(
            matches, empty_page_count, page
        )

        return PageResult(
            matches=matches, empty_page_count=new_empty_count, should_stop=should_stop
        )

    async def _handle_empty_page(
        self, matches: list[MatchInfo], empty_page_count: int, page: Page
    ) -> tuple[int, bool]:
        """
        V41.83: 处理空页面熔断

        Args:
            matches: 提取的比赛列表
            empty_page_count: 当前空页面计数
            page: Playwright Page 对象

        Returns:
            (新的空页面计数, 是否应该停止)
        """
        # V41.83: Guard Clause
        if len(matches) > 0:
            return 0, False

        try:
            page_title = await page.title()
            if "Results" in page_title:
                new_count = empty_page_count + 1
                logger.warning(f"⚠️  空页面检测: {new_count}/3")

                # V41.83: Guard Clause
                if new_count >= 3:
                    logger.error("🚨 触发 IP 保护熔断：Shadow Ban 检测")
                    logger.error("   正在强制退出以保护 IP...")
                    sys.exit(1)

                return new_count, False
        except Exception:
            pass

        return empty_page_count, False

    async def _navigate_to_next_page(self, page: Page, current_page_num: int, base_url: str):
        """
        V41.83: 导航到下一页

        Args:
            page: Playwright Page 对象
            current_page_num: 当前页码
            base_url: 基础 URL

        Returns:
            导航结果对象
        """
        from dataclasses import dataclass

        @dataclass
        class NavigateResult:
            success: bool

        next_page_num = current_page_num + 1
        next_page_url = self._build_next_page_url(page.url, next_page_num)

        logger.info(f"📍 翻页到第 {next_page_num} 页: {next_page_url}")

        try:
            await page.goto(next_page_url, wait_until="domcontentloaded", timeout=60000)

            # V41.83: 检查页面是否有内容
            check_hash = await self.extract_matches_from_dom(
                page,
                "",
                "",  # 联赛和赛季不影响检查
            )

            if len(check_hash) == 0:
                logger.info(f"✅ 第 {next_page_num} 页无内容，结束翻页")
                return NavigateResult(success=False)

            return NavigateResult(success=True)

        except Exception as e:
            logger.warning(f"⚠️  URL 翻页失败: {e}")
            return NavigateResult(success=False)

    async def _apply_cooldown_period(self, all_matches: list[MatchInfo]) -> None:
        """
        V41.83: 应用收割冷却期

        Args:
            all_matches: 已提取的比赛列表
        """
        # V41.83: Guard Clause
        if len(all_matches) == 0:
            return

        cooldown_delay = random.uniform(60, 120)
        logger.info(f"💤 收割冷却期: {cooldown_delay:.1f}s")
        await asyncio.sleep(cooldown_delay)

    async def _cleanup_browser(self, browser) -> None:
        """
        V41.83: 清理浏览器资源

        Args:
            browser: Playwright Browser 对象
        """
        if not browser:
            return

        try:
            await browser.close()
            logger.info("✅ 浏览器已安全关闭")
        except Exception as e:
            logger.warning(f"⚠️  关闭浏览器时出错: {e}")

    def _log_crawl_statistics(
        self, league_name: str, all_matches: list[MatchInfo], stats: CrawlStats
    ) -> None:
        """
        V41.83: 记录爬取统计信息

        Args:
            league_name: 联赛名称
            all_matches: 已提取的比赛列表
            stats: 爬取统计对象
        """
        logger.info("=" * 60)
        logger.info(f"📊 {league_name} 爬取统计:")
        logger.info(f"   总采集: {len(all_matches)} 场")
        logger.info(f"   访问页数: {stats.pages} 页")
        logger.info("=" * 60)

    def _build_next_page_url(self, current_url: str, next_page_num: int) -> str:
        """
        V41.83: 构建下一页 URL

        Args:
            current_url: 当前页面 URL
            next_page_num: 下一页页码

        Returns:
            下一页 URL
        """
        if "/page/" in current_url:
            base_url_without_page = current_url.split("/page/")[0]
            return f"{base_url_without_page}/page/{next_page_num}/"
        return f"{current_url.rstrip('/')}/page/{next_page_num}/"


# ============================================================================
# 工厂函数
# ============================================================================


def create_crawler_service(
    db_conn,
    proxy_ports: list[int] | None = None,
    enable_bayesian: bool = True,
    enable_proxy_health_check: bool = True,
    headless: bool = True,
    confidence_threshold: float = 85.0,
) -> CrawlerService:
    """
    V41.83: 创建爬虫服务实例

    Args:
        db_conn: 数据库连接（用于 SemanticRefiner）
        proxy_ports: 代理端口列表
        enable_bayesian: 是否启用贝叶斯延迟引擎
        enable_proxy_health_check: 是否启用代理健康检查
        headless: 是否无头模式
        confidence_threshold: SemanticRefiner 置信度阈值

    Returns:
        CrawlerService 实例
    """
    return CrawlerService(
        db_conn=db_conn,
        proxy_ports=proxy_ports,
        enable_bayesian=enable_bayesian,
        enable_proxy_health_check=enable_proxy_health_check,
        headless=headless,
        confidence_threshold=confidence_threshold,
    )
