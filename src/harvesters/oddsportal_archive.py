"""V41.832: OddsPortal Archive Harvester.

工业级归档收割机，用于从 OddsPortal 归档页面批量提取比赛映射数据。

核心功能:
    - 物理点击分页按钮（8 页）
    - 内容锁验证机制
    - 异常自愈与事务回滚
    - Ghost Page 检测

架构设计:
    - BrowserHelper: 浏览器操作辅助
    - MatchExtractor: 比赛数据提取
    - DatabaseInserter: 数据库插入

Usage:
    ```python
    from src.harvesters.oddsportal_archive import OddsPortalArchiveHarvester

    harvester = OddsPortalArchiveHarvester(league="Premier League", season="2024/2025")
    await harvester.harvest()
    ```

Author: Senior Lead Data Architect
Version: V41.832 "Production Blueprint"
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Final

from playwright.async_api import Page, async_playwright
import psycopg2
from psycopg2 import Error as PostgresError

from src.config.crawler_config import ODDSPORTAL_CONFIG
from src.config_unified import get_settings
from src.harvesters.database_inserter import DatabaseInserter
from src.parsers.match_parser import MatchData, MatchExtractor
from src.utils.browser_helper import BrowserHelper

logger = logging.getLogger(__name__)


@dataclass
class HarvestConfig:
    """收割配置.

    Attributes:
        league: 联赛名称
        season: 赛季 (例如 "2024/2025")
        country: 国家代码 (默认 "england")
        dry_run: 干跑模式
        lockdown_mode: 封锁模式（强制 8 页）
        max_pages: 最大页数
    """

    league: str
    season: str
    country: str = "england"
    dry_run: bool = False
    lockdown_mode: bool = False
    max_pages: int = 8

    def __post_init__(self) -> None:
        """验证配置.

        Raises:
            ValueError: 配置无效
        """
        if not self.league or not self.league.strip():
            raise ValueError("League cannot be empty")
        if not self.season or not self.season.strip():
            raise ValueError("Season cannot be empty")


@dataclass
class HarvestResult:
    """收割结果.

    Attributes:
        total_matches: 总提取比赛数
        inserted_count: 插入数据库数量
        pages_processed: 处理的页数
        first_match_date: 第一场比赛日期
        last_match_date: 最后一场比赛日期
        errors: 错误列表
    """

    total_matches: int = 0
    inserted_count: int = 0
    pages_processed: int = 0
    first_match_date: datetime | None = None
    last_match_date: datetime | None = None
    errors: list[str] = field(default_factory=list)


class OddsPortalArchiveHarvester:
    """OddsPortal 归档收割机.

    负责从 OddsPortal 归档页面批量提取比赛数据并写入数据库。

    工作流程:
        1. 访问目标 URL
        2. 滚动到底部加载分页条
        3. 提取 Page 1 数据并验证
        4. 逐页点击并提取数据（Page 2-8）
        5. 批量入库
    """

    # URL Templates
    URL_TEMPLATE: Final[str] = (
        f"{ODDSPORTAL_CONFIG.BASE_URL}/football/{{country}}/{{league_slug}}/results/"
    )

    def __init__(self, config: HarvestConfig) -> None:
        """初始化收割机.

        Args:
            config: 收割配置

        Raises:
            ValueError: 配置无效
        """
        if not config.league or not config.season:
            raise ValueError("League and season are required")

        self.config = config
        self.conn: psycopg2.extensions.connection | None = None
        self.extractor = MatchExtractor()
        self.result = HarvestResult()

    def _build_url(self) -> str:
        """构建目标 URL.

        Returns:
            完整的 OddsPortal URL
        """
        league_slug = self.config.league.lower().replace(" ", "-")
        season_slug = self.config.season.replace("/", "-")

        return f"{ODDSPORTAL_CONFIG.BASE_URL}/football/{self.config.country}/{league_slug}-{season_slug}/results/"

    def _connect_database(self) -> None:
        """连接数据库.

        Raises:
            PostgresError: 数据库连接失败
        """
        settings = get_settings()

        try:
            self.conn = psycopg2.connect(
                host=settings.database.host,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            logger.info(
                f"[OddsPortalArchiveHarvester][_connect_database] ✓ Connected to {settings.database.name}"
            )

        except PostgresError as e:
            logger.error(
                f"[OddsPortalArchiveHarvester][_connect_database] ❌ Connection failed: {e}"
            )
            raise

    async def harvest(self) -> HarvestResult:
        """执行收割流程.

        Returns:
            HarvestResult 收割结果

        Raises:
            PostgresError: 数据库操作失败
            Exception: 其他未预期错误
        """
        target_url = self._build_url()

        logger.info("=" * 60)
        logger.info("V41.832 OddsPortal Archive Harvester 启动")
        logger.info("=" * 60)
        logger.info(f"League: {self.config.league}")
        logger.info(f"Season: {self.config.season}")
        logger.info(f"Target URL: {target_url}")
        logger.info(f"Mode: {'DRY RUN' if self.config.dry_run else 'EXECUTE'}")
        logger.info("=" * 60)

        try:
            # 连接数据库
            self._connect_database()

            if self.config.dry_run:
                logger.info("[DRY RUN] Skipping database operations")
            else:
                db_inserter = DatabaseInserter(self.conn)

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 访问目标页面
                await page.goto(target_url, wait_until="domcontentloaded")

                # 初始化辅助工具
                helper = BrowserHelper(page)

                # Step 1: 提取 Page 1
                logger.info("")
                logger.info("=" * 60)
                logger.info("Step 1: Extract Page 1")
                logger.info("=" * 60)

                await helper.scroll_to_bottom()
                page1_matches = await self.extractor.extract_from_page(page)

                logger.info(f"✓ Page 1: {len(page1_matches)} matches extracted")

                # Step 2: 逐页提取 (Page 2-8)
                logger.info("")
                logger.info("=" * 60)
                logger.info("Step 2: Extract Pages 2-8")
                logger.info("=" * 60)

                all_matches = page1_matches.copy()
                max_pages = self.config.max_pages if self.config.lockdown_mode else 8

                for page_num in range(2, max_pages + 1):
                    await self._process_page(page, helper, page_num, all_matches)

                # Step 3: 批量入库
                if not self.config.dry_run:
                    logger.info("")
                    logger.info("=" * 60)
                    logger.info("Step 3: Bulk Insert")
                    logger.info("=" * 60)

                    stats = db_inserter.bulk_insert(
                        all_matches,
                        self.config.league,
                        self.config.season,
                    )

                    self.result.inserted_count = stats["inserted"]

                await browser.close()

            # 更新结果
            self.result.total_matches = len(all_matches)
            self.result.pages_processed = max_pages

            # 打印最终报告
            self._print_final_report()

            return self.result

        except PostgresError as e:
            logger.error(f"[OddsPortalArchiveHarvester][harvest] ❌ Database error: {e}")
            self.result.errors.append(str(e))
            raise
        except Exception as e:
            logger.error(f"[OddsPortalArchiveHarvester][harvest] ❌ Unexpected error: {e}")
            self.result.errors.append(str(e))
            raise
        finally:
            self.close()

    async def _process_page(
        self,
        page: Page,
        helper: BrowserHelper,
        page_num: int,
        all_matches: list[MatchData],
    ) -> None:
        """处理单个分页.

        Args:
            page: Playwright Page 对象
            helper: BrowserHelper 实例
            page_num: 页码
            all_matches: 累积的比赛列表

        Raises:
            PlaywrightTimeoutError: 点击超时
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Processing Page {page_num}/{self.config.max_pages}")
        logger.info("=" * 60)

        # 点击分页按钮
        success = await helper.click_page_button(page_num)

        if not success:
            logger.warning(f"⚠️ Failed to click Page {page_num}, skipping")
            return

        # 等待内容填充
        min_matches = (
            ODDSPORTAL_CONFIG.MIN_MATCHES_LAST_PAGE
            if page_num == 8
            else ODDSPORTAL_CONFIG.MIN_MATCHES_PER_PAGE
        )

        await helper.wait_for_content_lock(min_matches=min_matches)

        # 提取比赛
        matches = await self.extractor.extract_from_page(page)

        # 验证数量
        if not self.extractor.validate_match_count(matches, page_num, min_matches):
            logger.warning(f"⚠️ Page {page_num} has insufficient matches, continuing anyway")

        all_matches.extend(matches)
        self.result.pages_processed += 1

        # 短暂等待
        await asyncio.sleep(ODDSPORTAL_CONFIG.RETRY_DELAY)

    def _print_final_report(self) -> None:
        """打印最终收割报告."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("V41.832 Harvest Report")
        logger.info("=" * 60)
        logger.info(f"Total matches extracted: {self.result.total_matches}")
        logger.info(f"Matches inserted: {self.result.inserted_count}")
        logger.info(f"Pages processed: {self.result.pages_processed}")
        logger.info("=" * 60)

    def close(self) -> None:
        """关闭资源."""
        if self.conn:
            self.conn.close()
            logger.info("[OddsPortalArchiveHarvester][close] ✓ Database connection closed")
