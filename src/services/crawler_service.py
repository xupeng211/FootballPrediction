#!/usr/bin/env python3
"""
V41.78 Crawler Service - 网络爬虫服务层（SemanticRefiner 集成版）
=============================================================

本模块实现了网络爬虫的职责分离，从 HashAlignmentService 中提取出所有网络通信逻辑。

V41.78 更新：
- 集成 SemanticRefiner 替代脆弱的正则表达式
- 移除 HASH_PATTERNS，使用语义化对齐引擎
- 支持数据库连接，直接返回 match_id

设计原则:
- 单一职责: 只负责浏览器管理和数据提取
- 依赖注入: 接收代理配置、延迟引擎、数据库连接
- 可测试性: 支持依赖注入和 Mock

核心能力:
- Playwright 浏览器生命周期管理
- 动态代理池管理（ProxyHealthChecker）
- 页面翻页逻辑（URL 遍历模式）
- DOM 数据提取
- 语义化 URL 解析（SemanticRefiner）
- 贝叶斯自适应延迟

Author: 资深软件架构师
Version: V41.78
Date: 2026-01-15
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import random
import socket
import sys
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from src.api.collectors.bayesian_delay_engine import BayesianDelayEngine
from src.core.proxy_health_checker import ProxyHealthChecker
from src.core.semantic_refiner import SemanticRefiner
from src.services.harvest_config import AntiScrapingConfig

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class MatchInfo:
    """比赛信息（V41.78: 增加 match_id 字段）"""
    match_id: Optional[str]  # V41.78: 数据库中的 match_id（通过 SemanticRefiner 获取）
    home_team: str
    away_team: str
    hash_value: str
    url: str
    confidence: float = 0.0  # V41.78: 对齐置信度 (0-100)
    league_name: str = ""  # V41.78: 联赛名称
    season: str = ""  # V41.78: 赛季


@dataclass
class CrawlStats:
    """爬虫统计"""
    visited: int = 0
    extracted: int = 0
    pages: int = 0
    last_proxy_port: int | None = None
    successful_matches: int = 0  # V41.78: 成功对齐的比赛数量
    failed_matches: int = 0  # V41.78: 对齐失败的比赛数量


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
    V41.78: 网络爬虫服务（SemanticRefiner 集成版）

    负责所有网络通信相关操作：
    - Playwright 浏览器管理
    - 动态代理池管理（ProxyHealthChecker 自愈）
    - 页面翻页逻辑
    - DOM 数据提取
    - 语义化 URL 解析（SemanticRefiner）
    - 贝叶斯自适应延迟

    V41.78 更新：
    - 移除 HASH_PATTERNS 正则，使用 SemanticRefiner
    - 集成 ProxyHealthChecker 实现代理池自愈
    - 直接返回数据库 match_id

    Example:
        >>> crawler = CrawlerService(
        ...     db_conn=conn,
        ...     enable_proxy_health_check=True
        ... )
        >>> result = await crawler.crawl_league(
        ...     league_name="Premier League",
        ...     season="2023/2024",
        ...     base_url="https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
        ...     max_pages=10
        ... )
    """

    # V41.78: 代理端口配置（全部 19 个端口）
    PROXY_PORTS: list[int] = list(range(7891, 7910))  # 7891-7909

    # V41.78: WSL2 代理主机配置
    WSL2_PROXY_HOST: str = "172.25.16.1"
    LOCAL_PROXY_HOST: str = "127.0.0.1"

    def __init__(
        self,
        db_conn,
        proxy_ports: list[int] | None = None,
        enable_bayesian: bool = True,
        enable_proxy_health_check: bool = True,
        headless: bool = True,
        confidence_threshold: float = 85.0,
    ):
        """
        初始化爬虫服务

        Args:
            db_conn: 数据库连接（用于 SemanticRefiner）
            proxy_ports: 代理端口列表（默认使用 19 个端口）
            enable_bayesian: 是否启用贝叶斯延迟引擎
            enable_proxy_health_check: 是否启用代理健康检查
            headless: 是否无头模式
            confidence_threshold: SemanticRefiner 置信度阈值
        """
        self.db_conn = db_conn
        self.proxy_ports = proxy_ports or self.PROXY_PORTS
        self.enable_bayesian = enable_bayesian
        self.headless = headless

        # V41.78: 初始化 SemanticRefiner
        self.semantic_refiner = SemanticRefiner(
            db_conn=db_conn,
            confidence_threshold=confidence_threshold,
        )

        # V41.78: 初始化 ProxyHealthChecker
        self.proxy_health_checker = None
        self.available_ports = set(self.proxy_ports)  # 初始假设全部可用

        if enable_proxy_health_check:
            self.proxy_health_checker = ProxyHealthChecker(
                proxy_host=self._get_proxy_host(),
                check_interval=60,
                max_consecutive_failures=3,
            )
            # 设置初始端口列表
            self.proxy_health_checker.set_ports(self.proxy_ports)
            # 更新可用端口列表
            self.available_ports = self.proxy_health_checker.get_available_ports()

            # V41.78: 拆分长日志消息
            logger.info(
                f"🔍 V41.78: 代理健康检查已启用，"
                f"初始可用端口: {len(self.available_ports)}/{len(self.proxy_ports)}"
            )

        # V41.78: 如果可用端口 < 10，给出预警
        if len(self.available_ports) < 10:
            logger.warning(
                f"⚠️  V41.78: 可用代理端口数量较低 "
                f"({len(self.available_ports)}/{len(self.proxy_ports)})，"
                f"建议检查代理配置"
            )

        # V41.71: 初始化贝叶斯延迟引擎
        self.bayesian_engine = BayesianDelayEngine(
            base_delay=30.0,
            min_delay=15.0,
            max_delay=300.0,
        ) if enable_bayesian else None

        # 统计信息
        self.stats = CrawlStats()

        # V41.71: 检测 WSL2 环境
        self.is_wsl2 = self._is_wsl2_environment()
        self.proxy_host = self.WSL2_PROXY_HOST if self.is_wsl2 else self.LOCAL_PROXY_HOST

        logger.info(
            f"✅ V41.78 CrawlerService 初始化完成 "
            f"(proxies={len(self.available_ports)}/{len(self.proxy_ports)}, "
            f"bayesian={enable_bayesian}, wsl2={self.is_wsl2}, "
            f"semantic_refiner=True)"
        )

    # ========================================================================
    # 环境检测
    # ========================================================================

    @staticmethod
    def _is_wsl2_environment() -> bool:
        """检测是否运行在 WSL2 环境"""
        try:
            with open("/proc/version", "r") as f:
                version_content = f.read().lower()
                return "microsoft" in version_content and "wsl2" in version_content
        except (FileNotFoundError, IOError):
            return False

    def _get_proxy_host(self) -> str:
        """
        获取代理主机地址

        根据 WSL2 环境检测结果返回对应的代理主机。

        Returns:
            代理主机地址
        """
        is_wsl2 = self._is_wsl2_environment()
        return self.WSL2_PROXY_HOST if is_wsl2 else self.LOCAL_PROXY_HOST

    # ========================================================================
    # 代理管理
    # ========================================================================

    def get_proxy_port(self) -> int:
        """
        获取随机代理端口

        Returns:
            代理端口号
        """
        port = random.choice(self.proxy_ports)
        self.stats.last_proxy_port = port
        return port

    def check_proxy_health(self, port: int, timeout: float = 1.0) -> bool:
        """
        检查代理端口健康状态

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
        except (socket.error, OSError):
            return False

    def get_healthy_proxy_port(self, excluded_ports: set[int] | None = None) -> int | None:
        """
        获取健康的代理端口

        Args:
            excluded_ports: 要排除的端口集合

        Returns:
            可用的代理端口
        """
        if excluded_ports is None:
            excluded_ports = set()

        available_ports = [p for p in self.proxy_ports if p not in excluded_ports]

        if not available_ports:
            logger.warning("⚠️  没有可用的代理端口")
            return None

        random.shuffle(available_ports)

        for port in available_ports:
            if self.check_proxy_health(port):
                logger.debug(f"✅ 找到健康代理端口: {port}")
                return port

        logger.warning("⚠️  未找到健康代理端口")
        return None

    # ========================================================================
    # 数据提取（V41.78: SemanticRefiner 集成）
    # ========================================================================

    def extract_matches_from_html(
        self,
        html: str,
        league_name: str,
        season: str,
    ) -> list[MatchInfo]:
        """
        从 HTML 中提取所有比赛信息（使用 SemanticRefiner）

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

            # V41.78: 使用 SemanticRefiner 而不是正则表达式
            result = self.semantic_refiner.refine_url(href, league_name, season)

            if result.is_match:
                matches.append(MatchInfo(
                    match_id=result.match_id,
                    home_team=result.home_team,
                    away_team=result.away_team,
                    hash_value=result.hash_value,
                    url=href,
                    confidence=result.confidence,
                    league_name=result.league_name,
                    season=result.season,
                ))
                self.stats.successful_matches += 1
            else:
                # 对齐失败，记录到 stats
                self.stats.failed_matches += 1
                logger.debug(f"⚠️  URL 对齐失败: {href} - {result.failure_reason}")

        return matches

    async def extract_matches_from_dom(
        self,
        page: Page,
        league_name: str,
        season: str,
    ) -> list[MatchInfo]:
        """
        从 Playwright Page 对象提取比赛信息（使用 SemanticRefiner）

        Args:
            page: Playwright Page 对象
            league_name: 联赛名称
            season: 赛季

        Returns:
            MatchInfo 列表（包含 match_id）
        """
        # V41.78: 简化 JavaScript - 只提取包含 8 位哈希的链接
        matches = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    // 简单检查：URL 必须以 8 位字母数字结尾
                    if (href && href.match(/[A-Za-z0-9]{8}\\/?$/)) {
                        results.push({ href: href });
                    }
                });

                return results;
            }
        """)

        parsed_matches = []
        for match in matches:
            href = match.get('href', '')

            # V41.78: 使用 SemanticRefiner 而不是正则表达式
            result = self.semantic_refiner.refine_url(href, league_name, season)

            if result.is_match:
                parsed_matches.append(MatchInfo(
                    match_id=result.match_id,
                    home_team=result.home_team,
                    away_team=result.away_team,
                    hash_value=result.hash_value,
                    url=href,
                    confidence=result.confidence,
                    league_name=result.league_name,
                    season=result.season,
                ))
                self.stats.successful_matches += 1
            else:
                # 对齐失败，记录到 stats
                self.stats.failed_matches += 1
                logger.debug(f"⚠️  URL 对齐失败: {href} - {result.failure_reason}")

        return parsed_matches

    # ========================================================================
    # 延迟管理
    # ========================================================================

    async def calculate_delay(self, last_success: bool | None = None) -> float:
        """
        计算下一次请求的延迟

        Args:
            last_success: 上一次请求是否成功

        Returns:
            延迟秒数
        """
        if self.bayesian_engine:
            delay = self.bayesian_engine.calculate_delay(last_success=last_success)
            logger.debug(f"🧠 贝叶斯延迟: {delay:.1f}s")
            return delay
        else:
            # 回退到随机延迟
            return random.uniform(5, 9)

    async def wait_with_delay(self, last_success: bool | None = None) -> None:
        """
        等待延迟时间

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
        爬取联赛比赛信息（V41.78: 使用 SemanticRefiner）

        Args:
            league_name: 联赛名称（如 "Premier League"）
            season: 赛季（如 "2023/2024"）
            base_url: 基础 URL
            max_pages: 最大页数
            tier: 联赛等级（影响延迟）

        Returns:
            CrawlResult 对象（包含 match_id）
        """
        if not async_playwright:
            logger.error("❌ Playwright 未安装")
            return CrawlResult(
                matches=[],
                stats=self.stats,
                success=False,
                error="Playwright 未安装"
            )

        all_matches = []
        stats = CrawlStats()

        logger.info(f"🚀 V41.78 开始爬取: {league_name} {season}")
        logger.info(f"   URL: {base_url}")
        logger.info(f"   最大页数: {max_pages}")

        # V41.78: 输出代理池状态
        logger.info("   🔌 代理池状态:")
        logger.info(f"      可用端口: {len(self.available_ports)}/{len(self.proxy_ports)}")
        if self.proxy_health_checker:
            logger.info("      健康检查: 已启用")
        else:
            logger.info("      健康检查: 已禁用")

        browser = None
        try:
            async with async_playwright() as p:
                # V41.78: 获取健康代理端口（使用 ProxyHealthChecker 更新的列表）
                proxy_port = self.get_healthy_proxy_port()
                if not proxy_port:
                    logger.error("❌ 无可用代理端口")
                    return CrawlResult(matches=[], stats=stats, success=False, error="无可用代理")

                # V41.76: 启动浏览器 (代理在 context 中配置)
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ],
                    ignore_default_args=["--enable-automation"]
                )

                # V41.76: 创建浏览器上下文 (代理配置在此)
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

                try:
                    # 访问联赛结果页面
                    await page.goto(
                        base_url,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    # V41.71: 初始延迟
                    await self.wait_with_delay(last_success=None)

                    # V41.71: 熔断机制计数器
                    empty_page_count = 0

                    for page_num in range(1, max_pages + 1):
                        logger.info(f"📖 正在处理第 {page_num} 页...")
                        # V41.78: 拆分长日志消息
                        logger.info(
                            f"   🔌 当前可用代理端口: "
                            f"{len(self.available_ports)}/{len(self.proxy_ports)}"
                        )

                        # V41.78: 每页切换代理端口
                        if page_num > 1:
                            new_proxy_port = self.get_healthy_proxy_port(
                                excluded_ports={proxy_port} if proxy_port else None
                            )
                            if new_proxy_port and new_proxy_port != proxy_port:
                                logger.info(f"🔌 切换代理端口: {proxy_port} → {new_proxy_port}")
                                proxy_port = new_proxy_port
                                # 注意：Playwright 不支持运行时切换代理
                                # 这里仅记录，实际切换需要重启浏览器

                        # V41.78: 提取比赛（使用 SemanticRefiner）
                        matches = await self.extract_matches_from_dom(page, league_name, season)
                        stats.pages += 1
                        stats.visited += 1

                        # V41.78: 拆分长日志消息
                        logger.info(
                            f"   提取到 {len(matches)} 场比赛 "
                            f"(成功: {self.stats.successful_matches}, "
                            f"失败: {self.stats.failed_matches})"
                        )
                        all_matches.extend(matches)

                        # V41.71: 熔断机制
                        if len(matches) == 0:
                            try:
                                page_title = await page.title()
                                if "Results" in page_title:
                                    empty_page_count += 1
                                    logger.warning(f"⚠️  空页面检测: {empty_page_count}/3")

                                    if empty_page_count >= 3:
                                        logger.error("🚨 触发 IP 保护熔断：Shadow Ban 检测")
                                        logger.error("   正在强制退出以保护 IP...")
                                        sys.exit(1)
                            except Exception:
                                pass
                        else:
                            empty_page_count = 0

                        # 翻页
                        if page_num >= max_pages:
                            logger.info(f"✅ 已达到最大页数 {max_pages}")
                            break

                        # V41.71: URL 遍历模式翻页
                        next_page_url = self._build_next_page_url(page.url, page_num + 1)
                        logger.info(f"📍 翻页到第 {page_num + 1} 页: {next_page_url}")

                        try:
                            # V41.78: 拆分长行
                            await page.goto(
                                next_page_url,
                                wait_until="domcontentloaded",
                                timeout=60000
                            )

                            # V41.71: 贝叶斯延迟
                            await self.wait_with_delay(last_success=len(matches) > 0)

                            # 检查是否有内容
                            check_hash = await self.extract_matches_from_dom(
                                page, league_name, season
                            )
                            if len(check_hash) == 0:
                                logger.info(
                                    f"✅ 第 {page_num + 1} 页无内容，结束翻页"
                                )
                                break

                        except Exception as e:
                            logger.warning(f"⚠️  URL 翻页失败: {e}")
                            break

                    # V41.71: 收割冷却期
                    if len(all_matches) > 0:
                        cooldown_delay = random.uniform(60, 120)
                        logger.info(f"💤 收割冷却期: {cooldown_delay:.1f}s")
                        await asyncio.sleep(cooldown_delay)

                except Exception as e:
                    logger.error(f"❌ 爬取过程出错: {e}")
                    return CrawlResult(
                        matches=all_matches,
                        stats=stats,
                        success=False,
                        error=str(e)
                    )

                finally:
                    if browser:
                        try:
                            await browser.close()
                            logger.info("✅ 浏览器已安全关闭")
                        except Exception as e:
                            logger.warning(f"⚠️  关闭浏览器时出错: {e}")

        except Exception as e:
            logger.error(f"❌ V41.71 crawl_league 失败: {e}")
            return CrawlResult(matches=all_matches, stats=stats, success=False, error=str(e))

        finally:
            logger.info("=" * 60)
            logger.info(f"📊 {league_name} 爬取统计:")
            logger.info(f"   总采集: {len(all_matches)} 场")
            logger.info(f"   访问页数: {stats.pages} 页")
            logger.info("=" * 60)

        stats.extracted = len(all_matches)
        return CrawlResult(matches=all_matches, stats=stats, success=True)

    def _build_next_page_url(self, current_url: str, next_page_num: int) -> str:
        """
        构建下一页 URL

        Args:
            current_url: 当前页面 URL
            next_page_num: 下一页页码

        Returns:
            下一页 URL
        """
        if "/page/" in current_url:
            base_url_without_page = current_url.split("/page/")[0]
            return f"{base_url_without_page}/page/{next_page_num}/"
        else:
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
    创建爬虫服务实例

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
