"""
V41.285 Data Harvest Service - 工业级收割引擎
=================================================

这是 V41.285 "Stabilized Flow" 的核心服务类，
实现了"赔率入库，阵容必达"的全自动生产线。

V41.285 升级：
    1. 数据库连接池扩容 - 支持 6 并发连接
    2. 连接池健康监控
    3. 连接泄漏保护

核心功能：
    1. Odds 数据收割（标准模式）
    2. 深度链接恢复（盲区恢复）
    3. 自愈重试机制（指数级退避）
    4. 代理端口轮换
    5. V41.278: 自动阵容采集 - 赔率入库后立即触发阵容抓取
    6. V41.285: 连接池管理器 - 高并发下的连接复用

Usage:
    from src.services.data_harvest_service import OddsHarvestService, get_harvester_config

    # 加载配置
    config = get_harvester_config()

    # 创建服务
    service = OddsHarvestService(config)

    # 执行收割（会自动采集阵容）
    result = service.run(mode="backfill", limit=100)

Author: V41.285 Architecture Team
Date: 2026-01-20
Version: V41.285 "Stabilized Flow"
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import re
from threading import Lock
import time
from typing import Literal
from urllib.parse import quote

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from src.config_unified import get_config as get_unified_config
from src.core.scrapers.industrial_auditor import AuditorConfig, IndustrialAuditor
from src.services.harvester_config import HarvesterV2Config, get_harvester_config

logger = logging.getLogger("OddsHarvestService")


# =============================================================================
# 异常类
# =============================================================================


class ColumnScrambleError(Exception):
    """V41.272: 列错位异常 - 赔率强队与 xG 强队完全相反"""


# =============================================================================
# 数据模型
# =============================================================================


class HarvestMode(str, Enum):
    """收割模式"""

    STANDARD = "standard"  # 标准收割：从待处理队列获取比赛
    BACKFILL = "backfill"  # 回填模式：收割所有有 URL 但无数据的比赛
    DEEP_SEARCH = "deep_search"  # 深度搜索：恢复盲区 URL
    TARGETED = "targeted"  # 专项收割：针对指定 match_id 列表


@dataclass
class MatchInfo:
    """比赛信息"""

    match_id: str
    home_team: str
    away_team: str
    match_date: datetime
    league_name: str
    season: str
    oddsportal_url: str | None = None


@dataclass
class HarvestStats:
    """收割统计"""

    mode: HarvestMode
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped_no_url: int = 0
    urls_recovered: int = 0
    lineups_collected: int = 0  # V41.278: 阵容采集统计
    lock: Lock = field(default_factory=Lock)

    def to_dict(self) -> dict:
        """转换为字典"""
        elapsed = (self.end_time or datetime.now) - self.start_time
        return {
            "mode": self.mode.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": elapsed.total_seconds(),
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "skipped_no_url": self.skipped_no_url,
            "urls_recovered": self.urls_recovered,
            "lineups_collected": self.lineups_collected,  # V41.278
            "success_rate": self.successful / max(self.total_processed, 1) * 100,
        }


# =============================================================================
# 深度搜索引擎
# =============================================================================


class OddsPortalSearchEngine:
    """
    OddsPortal 搜索引擎 - 深度链接恢复

    基于 V41.261 的搜索逻辑，整合到 V41.262 服务中。
    """

    def __init__(self, config: HarvesterV2Config, db_config):
        self.config = config
        self.db_config = db_config
        self.session = None

        try:
            import requests

            self.session = requests.Session()
            proxy_url = f"http://{self.config.proxy.wsl2_bridge_host}:{self.config.proxy.ports[0]}"
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
        except ImportError:
            logger.warning("requests module not available, deep search disabled")

    def search_match_url(self, home_team: str, away_team: str, match_date: str) -> str | None:
        """搜索比赛详情页 URL"""
        if not self.session:
            return None

        query = f"{home_team} {away_team}"
        search_url = self.config.deep_search.search_url_template.format(query=quote(query))

        try:
            response = self.session.get(search_url, timeout=self.config.deep_search.timeout)
            if response.status_code != 200:
                return None

            return self._extract_detail_url(response.text, home_team, away_team)
        except Exception as e:
            logger.exception(f"Deep search error: {e}")
            return None

    def _extract_detail_url(self, html: str, home_team: str, away_team: str) -> str | None:
        """从 HTML 提取详情页 URL"""
        hash_pattern = re.compile(self.config.deep_search.hash_pattern)
        detail_pattern = re.compile(self.config.deep_search.detail_page_pattern, re.IGNORECASE)

        matches = detail_pattern.findall(html)
        if not matches:
            matches = re.findall(r'href="(/football/[^"]+)"', html)

        for match in matches:
            match_lower = match.lower()
            if home_team.lower() in match_lower or away_team.lower() in match_lower:
                hash_match = hash_pattern.search(match)
                if hash_match:
                    return f"https://www.oddsportal.com{match}"
        return None

    def update_match_url(self, match_id: str, url: str) -> bool:
        """更新数据库中的 URL"""
        conn = psycopg2.connect(
            host=self.db_config.database.host,
            database=self.db_config.database.name,
            user=self.db_config.database.user,
            password=self.db_config.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        try:
            hash_pattern = re.compile(self.config.deep_search.hash_pattern)
            hash_match = hash_pattern.search(url)
            odds_hash = hash_match.group(1) if hash_match else None

            cursor.execute(
                """
                UPDATE matches_mapping
                SET oddsportal_url = %s,
                    oddsportal_hash = %s,
                    mapping_method = 'V41.262_Deep_Search',
                    confidence = 0.85,
                    updated_at = NOW()
                WHERE fotmob_id = %s
            """,
                (url, odds_hash, match_id),
            )

            conn.commit()
            return True
        except Exception as e:
            logger.exception(f"Failed to update URL for {match_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._return_connection(conn)


# =============================================================================
# 核心收割服务
# =============================================================================


class OddsHarvestService:
    """
    V41.262 Odds 数据收割服务

    工业级统一收割引擎，整合了所有补丁逻辑。
    """

    def __init__(self, config: HarvesterV2Config | None = None):
        """
        初始化收割服务

        V41.285: 添加数据库连接池支持，支持 6 并发连接

        Args:
            config: 收割配置（如果为 None，从默认路径加载）
        """
        self.config = config or get_harvester_config()
        self.db_config = get_unified_config()
        self.search_engine = OddsPortalSearchEngine(self.config, self.db_config)

        # 代理端口轮换
        self._proxy_port_index = 0
        self._proxy_lock = Lock()

        # V41.278: 阵容采集统计
        self._lineup_collected_count = 0
        self._lineup_lock = Lock()

        # V41.285: 数据库连接池初始化
        # 最小连接数 = 2，最大连接数 = 10（支持 6 并发 + 4 冗余）
        self._connection_pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=self.db_config.database.host,
            database=self.db_config.database.name,
            user=self.db_config.database.user,
            password=self.db_config.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )
        logger.info("V41.285: Database connection pool initialized (min=2, max=10)")

        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, self.config.logging.level))

    def _get_next_proxy_port(self) -> int:
        """获取下一个代理端口（轮换）"""
        with self._proxy_lock:
            port = self.config.proxy.ports[self._proxy_port_index]
            self._proxy_port_index = (self._proxy_port_index + 1) % len(self.config.proxy.ports)
            return port

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """计算指数级退避延迟"""
        delay = self.config.retry.base_delay_seconds * (
            self.config.retry.backoff_multiplier**attempt
        )
        return min(delay, self.config.retry.max_delay_seconds)

    # ========================================================================
    # 数据库操作
    # ========================================================================

    def _get_connection(self):
        """
        V41.285: 从连接池获取数据库连接

        使用连接池而不是每次创建新连接，支持高并发场景
        """
        return self._connection_pool.getconn()

    def _return_connection(self, conn):
        """
        V41.285: 归还连接到连接池

        Args:
            conn: 数据库连接
        """
        self._connection_pool.putconn(conn)

    def _close_all_connections(self):
        """
        V41.285: 关闭所有连接池连接

        在服务关闭时调用
        """
        self._connection_pool.closeall()
        logger.info("V41.285: All database connections closed")

    def fetch_pending_matches(self, limit: int) -> list[MatchInfo]:
        """
        获取待收割比赛

        Args:
            limit: 最大获取数量

        Returns:
            待收割比赛列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.league_name,
                    m.season,
                    mm.oddsportal_url
                FROM matches m
                INNER JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE m.match_date >= %s
                  AND mm.oddsportal_url IS NOT NULL
                  AND m.match_id NOT IN (
                      SELECT match_id FROM match_odds_intelligence
                  )
                ORDER BY m.match_date ASC
                LIMIT %s
            """

            cursor.execute(query, (self.config.database.start_date, limit))
            rows = cursor.fetchall()

            return [
                MatchInfo(
                    match_id=row["match_id"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    match_date=row["match_date"],
                    league_name=row["league_name"],
                    season=row["season"],
                    oddsportal_url=row["oddsportal_url"],
                )
                for row in rows
            ]
        finally:
            self._return_connection(conn)

    def fetch_blind_spot_matches(self, limit: int) -> list[MatchInfo]:
        """
        获取盲区比赛（无 URL）

        Args:
            limit: 最大获取数量

        Returns:
            盲区比赛列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.league_name,
                    m.season
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE m.match_date >= %s
                  AND (mm.oddsportal_url IS NULL OR mm.oddsportal_url = '')
                ORDER BY m.match_date DESC
                LIMIT %s
            """

            cursor.execute(query, (self.config.database.start_date, limit))
            rows = cursor.fetchall()

            return [
                MatchInfo(
                    match_id=row["match_id"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    match_date=row["match_date"],
                    league_name=row["league_name"],
                    season=row["season"],
                    oddsportal_url=None,
                )
                for row in rows
            ]
        finally:
            self._return_connection(conn)

    # ========================================================================
    # 数据提取
    # ========================================================================

    def _extract_with_retry(self, target_url: str) -> dict | None:
        """
        带指数级退避和代理轮换的数据提取

        Args:
            target_url: 目标 URL

        Returns:
            提取结果字典，如果所有重试都失败则返回 None
        """

        for attempt in range(self.config.retry.max_attempts):
            proxy_port = self._get_next_proxy_port()

            try:
                logger.info(
                    f"  Attempt [{attempt + 1}/{self.config.retry.max_attempts}] with proxy port {proxy_port}"
                )

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                auditor_config = AuditorConfig(
                    target_url=target_url,
                    target_patterns=self.config.target_patterns,
                    headless=True,
                    proxy_port=proxy_port,
                    navigation_timeout=self.config.auditor.navigation_timeout,
                    # V41.268: 从 data_integrity 配置传递阈值
                    min_value_threshold=self.config.data_integrity.value_ranges.odds_min,
                    max_value_threshold=self.config.data_integrity.value_ranges.odds_max,
                )

                auditor = IndustrialAuditor(auditor_config)
                extraction_result = loop.run_until_complete(auditor.audit())
                loop.close()

                if not extraction_result or extraction_result.entities_extracted == 0:
                    raise RuntimeError(
                        f"Incomplete page: entities_extracted={extraction_result.entities_extracted if extraction_result else 0}"
                    )

                entity = extraction_result.entities[0]
                entity_dict = entity.to_dict()

                logger.info(
                    f"  ✓ Extraction successful: {extraction_result.entities_extracted} entities"
                )
                return {
                    "entity_dict": entity_dict,
                    "extraction_result": extraction_result,
                    "proxy_port": proxy_port,
                }

            except Exception as e:
                logger.warning(f"  ✗ Attempt [{attempt + 1}] failed: {e}")

                if attempt < self.config.retry.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"  ⏳ Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        logger.error(f"  ✗ All {self.config.retry.max_attempts} attempts failed")
        return None

    # ========================================================================
    # 数据存储
    # ========================================================================

    def _calculate_overround(self, odds_triplet: list) -> float | None:
        """
        V41.271 计算 Overround

        Overround = (1/H + 1/D + 1/A)

        Args:
            odds_triplet: [主胜, 平局, 客胜] 赔率三元组

        Returns:
            Overround 值，如果数据无效则返回 None
        """
        if not odds_triplet or len(odds_triplet) != 3:
            return None

        try:
            h, d, a = odds_triplet

            # 检查是否有 None 或非正值
            if None in (h, d, a) or any(x is None or x <= 0 for x in (h, d, a)):
                return None

            overround = (1.0 / h) + (1.0 / d) + (1.0 / a)
            return round(overround, 4)

        except (TypeError, ZeroDivisionError):
            return None

    def _validate_overround(
        self, odds_triplet: list, overround: float | None, match_id: str
    ) -> tuple[bool, str]:
        """
        V41.271 实时数学哨兵 - Overround 验证

        验证准则：
        - 任何赔率 < 1.05 → 拒绝（可能的亚盘/让球）
        - Overround < 1.00 → 数学不可能（数据损坏）
        - Overround > 1.25 → 异常结构（非1X2表格）

        Args:
            odds_triplet: 赔率三元组
            overround: 计算出的 Overround
            match_id: 比赛 ID（用于日志）

        Returns:
            (是否通过, 拒绝原因)
        """
        if not odds_triplet or len(odds_triplet) != 3:
            return False, "Invalid triplet structure"

        h, d, a = odds_triplet

        # V41.271: 任何赔率 < 1.05 → 拒绝（可能的亚盘/让球）
        if any(x is not None and x < 1.05 for x in (h, d, a)):
            return False, "MIN_ODDS_VIOLATION: odds < 1.05 detected (possible Asian Handicap)"

        # V41.271: Overround 边界检查
        if overround is not None:
            if overround < 1.00:
                return False, f"MATHEMATICAL_IMPOSSIBILITY: Overround {overround} < 1.00"
            if overround > 1.25:
                return False, f"ABNORMAL_STRUCTURE: Overround {overround} > 1.25 (non-1X2 table)"

        return True, ""

    def _validate_xg_fingerprint(
        self, match_id: str, initial_price: list, closing_price: list
    ) -> tuple[bool, str]:
        """
        V41.273 Smart Scramble Check - xG 数据交叉验证（市场洞察版）

        V41.273 升级：
        - 如果赔率与 xG 相反，不直接报错
        - 对比"开盘 vs 终盘"变盘方向
        - 如果变盘方向是向着赔率低的一方走的，判定为"市场洞察"而非"列错位"

        逻辑：
        1. 从 matches 表查询该比赛的 xG 数据 (rolling_xg_home, rolling_xg_away)
        2. 从 closing_price 确定赔率强队（最低赔率 = 最强队）
        3. 从 xG 数据确定 xG 强队（最高 xG = 最强队）
        4. 如果两个强队相反，检查变盘方向：
           - 如果变盘方向与赔率强队一致 → 市场洞察，通过验证
           - 如果变盘方向与赔率强队相反 → 可能的列错位，拒绝

        Args:
            match_id: 比赛 ID
            initial_price: 开盘赔率数组 [home, draw, away]
            closing_price: 终盘赔率数组 [home, draw, away]

        Returns:
            (是否通过, 拒绝原因)
        """
        if not closing_price or len(closing_price) < 3:
            return True, ""  # 无数据，跳过验证

        try:
            h_close, d_close, a_close = closing_price[:3]

            # 步骤 1: 查询 xG 数据
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            try:
                cursor.execute(
                    """
                    SELECT
                        home_team,
                        away_team,
                        (technical_features->>'rolling_xg_home')::float8 as xg_home,
                        (technical_features->>'rolling_xg_away')::float8 as xg_away
                    FROM matches
                    WHERE match_id = %s
                """,
                    (match_id,),
                )

                row = cursor.fetchone()

                if not row:
                    return True, "NO_XG_DATA: xG data not found, skipping validation"

                xg_home = row.get("xg_home")
                xg_away = row.get("xg_away")

                if xg_home is None or xg_away is None:
                    return True, "NO_XG_DATA: xG values are NULL, skipping validation"

                # 步骤 2: 确定终盘赔率强队（最低赔率 = 最强队）
                if h_close < a_close:
                    closing_favorite = "home"  # 主队赔率更低，主队更强
                elif a_close < h_close:
                    closing_favorite = "away"  # 客队赔率更低，客队更强
                else:
                    return (
                        True,
                        "ODDS_EQUAL: home and away odds are equal, cannot determine favorite",
                    )

                # 步骤 3: 确定 xG 强队（最高 xG = 最强队）
                if xg_home > xg_away:
                    xg_favorite = "home"
                elif xg_away > xg_home:
                    xg_favorite = "away"
                else:
                    return True, "XG_EQUAL: home and away xG are equal, cannot determine favorite"

                # 步骤 4: 交叉验证
                if closing_favorite != xg_favorite:
                    # ====================================================================
                    # V41.273 Step 3: 市场洞察判定
                    # ====================================================================
                    # 赔率与 xG 相反，检查变盘方向
                    logger.warning(
                        f"  ⚠️ xG mismatch for {match_id}: "
                        f"Odds favorite={closing_favorite}, xG favorite={xg_favorite}"
                    )

                    # 检查是否有开盘数据
                    if initial_price and len(initial_price) >= 3:
                        h_init, d_init, a_init = initial_price[:3]

                        # 确定开盘赔率强队
                        if h_init < a_init:
                            initial_favorite = "home"
                        elif a_init < h_init:
                            initial_favorite = "away"
                        else:
                            initial_favorite = None

                        # 判断变盘方向
                        if initial_favorite:
                            # 计算主队赔率变化（负值 = 赔率下降 = 热度上升）
                            home_odds_change = h_close - h_init
                            away_odds_change = a_close - a_init

                            # V41.273 市场洞察判定：
                            # 如果变盘方向是向着终盘强队走的，说明市场在"纠正"认知
                            # 这不是列错位，而是市场洞察
                            if closing_favorite == initial_favorite:
                                # 终盘与开盘强队一致，说明市场从一开始就看好这支队伍
                                # 但 xG 数据显示另一队更强 → 可能是市场洞察
                                logger.info(
                                    f"  ✓ MARKET INSIGHT detected for {match_id}: "
                                    f"Market consistently favors {closing_favorite} "
                                    f"(Initial: {initial_favorite}, Closing: {closing_favorite}), "
                                    f"despite xG favoring {xg_favorite}. "
                                    f"This suggests market insight, not column scrambling."
                                )
                                return (
                                    True,
                                    f"MARKET_INSIGHT: Market favors {closing_favorite} over xG favorite {xg_favorite}",
                                )

                            # 强队发生了变化，检查变盘方向
                            # 如果变盘方向是向着终盘强队走的，说明市场在纠正
                            if (closing_favorite == "home" and home_odds_change < 0) or (
                                closing_favorite == "away" and away_odds_change < 0
                            ):
                                logger.info(
                                    f"  ✓ MARKET INSIGHT detected for {match_id}: "
                                    f"Market shifted toward {closing_favorite} "
                                    f"(Home change: {home_odds_change:+.2f}, Away change: {away_odds_change:+.2f}), "
                                    f"aligning with closing odds despite xG favoring {xg_favorite}."
                                )
                                return (
                                    True,
                                    f"MARKET_INSIGHT: Market shifted to {closing_favorite}",
                                )

                        # 如果到达这里，没有明确的变盘信号 → 可能是列错位
                        error_msg = (
                            f"Potential ColumnScrambleError for {match_id}:\n"
                            f"  Initial favorite: {initial_favorite or 'N/A'} (H:{h_init:.2f} D:{d_init:.2f} A:{a_init:.2f})\n"
                            f"  Closing favorite: {closing_favorite} (H:{h_close:.2f} D:{d_close:.2f} A:{a_close:.2f})\n"
                            f"  xG favorite: {xg_favorite} (xG_H:{xg_home:.2f} xG_A:{xg_away:.2f})\n"
                            f"  No clear market shift detected - possible column scrambling"
                        )
                        logger.error(error_msg)
                        return False, error_msg
                    # 没有开盘数据，无法判断市场洞察 → 保守拒绝
                    error_msg = (
                        f"Potential ColumnScrambleError for {match_id}:\n"
                        f"  Closing favorite: {closing_favorite} (H:{h_close:.2f} D:{d_close:.2f} A:{a_close:.2f})\n"
                        f"  xG favorite: {xg_favorite} (xG_H:{xg_home:.2f} xG_A:{xg_away:.2f})\n"
                        f"  No initial price data for market insight validation"
                    )
                    logger.error(error_msg)
                    return False, error_msg

                logger.info(
                    f"  ✓ xG Fingerprint PASSED: {match_id} - "
                    f"Odds favorite={closing_favorite}, xG favorite={xg_favorite}"
                )
                return True, ""

            finally:
                self._return_connection(conn)

        except ColumnScrambleError:
            raise
        except Exception as e:
            logger.warning(f"  ⚠ xG validation error for {match_id}: {e}")
            return True, f"XG_VALIDATION_ERROR: {e!s}"  # 验证失败不阻塞存储

    def _store_odds_data(
        self,
        match_id: str,
        initial_price: list,
        closing_price: list,
        movement_history: list,
        metadata: dict,
    ) -> bool:
        """存储赔率数据"""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # ================================================================
            # V41.271 Step 2: 实时数学哨兵 - Overround 验证
            # ================================================================
            # 验证 Initial_Price
            if initial_price and len(initial_price) >= 3:
                initial_triplet = initial_price[:3]
                initial_overround = self._calculate_overround(initial_triplet)
                initial_valid, initial_reason = self._validate_overround(
                    initial_triplet, initial_overround, match_id
                )

                if not initial_valid:
                    logger.warning(f"V41.271 Math Sentry REJECTED {match_id}: {initial_reason}")
                    logger.warning(
                        f"  Initial_Price: {initial_triplet}, Overround: {initial_overround}"
                    )
                    return False

            # 验证 Closing_Price
            if closing_price and len(closing_price) >= 3:
                closing_triplet = closing_price[:3]
                closing_overround = self._calculate_overround(closing_triplet)
                closing_valid, closing_reason = self._validate_overround(
                    closing_triplet, closing_overround, match_id
                )

                if not closing_valid:
                    logger.warning(f"V41.271 Math Sentry REJECTED {match_id}: {closing_reason}")
                    logger.warning(
                        f"  Closing_Price: {closing_triplet}, Overround: {closing_overround}"
                    )
                    return False

            logger.info(f"V41.271 Math Sentry APPROVED {match_id}: Overround validation passed")

            # ================================================================
            # 存储到数据库
            # ================================================================
            cursor.execute(
                """
                INSERT INTO match_odds_intelligence (
                    match_id, initial_price, closing_price, movement_history,
                    quality_rating, deviation_percentage, link_method
                ) VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    initial_price = EXCLUDED.initial_price,
                    closing_price = EXCLUDED.closing_price,
                    movement_history = EXCLUDED.movement_history,
                    quality_rating = EXCLUDED.quality_rating,
                    deviation_percentage = EXCLUDED.deviation_percentage,
                    updated_at = NOW()
            """,
                (
                    match_id,
                    json.dumps(initial_price) if initial_price else None,
                    json.dumps(closing_price) if closing_price else None,
                    json.dumps(movement_history) if movement_history else None,
                    metadata.get("Quality_Rating", "unknown"),
                    metadata.get("Deviation_Percentage", 0),
                    "V41.271_Hardened_Service",
                ),
            )

            conn.commit()
            return True
        except Exception as e:
            logger.exception(f"Storage error for {match_id}: {e}")
            conn.rollback()
            return False
        finally:
            self._return_connection(conn)

    # ========================================================================
    # 单场比赛收割
    # ========================================================================

    def harvest_single_match(self, match: MatchInfo) -> bool:
        """
        收割单场比赛

        V41.278: 集成阵容采集 - 赔率入库后自动触发阵容抓取

        Args:
            match: 比赛信息

        Returns:
            是否成功
        """
        if not match.oddsportal_url:
            logger.warning(f"  ⊘ Skipped: {match.match_id} - No URL")
            return False

        try:
            logger.info(f"Processing: {match.home_team} vs {match.away_team}")

            # V41.268: 拼接完整 URL（数据库存储的是相对路径）
            target_url = match.oddsportal_url
            if target_url and not target_url.startswith("http"):
                target_url = f"https://www.oddsportal.com{target_url}"

            extract_result = self._extract_with_retry(target_url)
            if not extract_result:
                return False

            entity_dict = extract_result["entity_dict"]
            proxy_port = extract_result["proxy_port"]

            initial_price = entity_dict.get("Initial_Price", [])
            closing_price = entity_dict.get("Closing_Price", [])
            movement_history = entity_dict.get("Movement_History", [])

            # ====================================================================
            # V41.273 Step 3: Smart Scramble Check - xG 数据交叉验证（市场洞察版）
            # ====================================================================
            # 在存储前进行 xG 锚点指纹比对，检测列错位问题
            xg_valid, xg_reason = self._validate_xg_fingerprint(
                match_id=match.match_id, initial_price=initial_price, closing_price=closing_price
            )

            if not xg_valid:
                logger.error(f"  ✗ REJECTED: {match.match_id} - {xg_reason}")
                return False  # 拒绝入库

            stored = self._store_odds_data(
                match_id=match.match_id,
                initial_price=initial_price,
                closing_price=closing_price,
                movement_history=movement_history,
                metadata={
                    "Quality_Rating": entity_dict.get("Quality_Rating", "unknown"),
                    "Deviation_Percentage": entity_dict.get("Deviation_Percentage", 0),
                    "Source": "V41.262_Harvest_Service",
                    "URL": match.oddsportal_url,
                    "Proxy_Port": proxy_port,
                },
            )

            if stored:
                logger.info(f"  ✓ Success: {match.match_id}")

                # ====================================================================
                # V41.278 Step 1: 自动触发阵容采集 - 赔率入库，阵容必达
                # ====================================================================
                self._auto_collect_lineup(match.match_id)

                return True
            return False

        except Exception as e:
            logger.exception(f"  ✗ Error: {match.match_id} - {e}")
            return False

    def _auto_collect_lineup(self, match_id: str) -> bool:
        """
        V41.278 自动阵容采集 - 赔率入库后自动触发

        Args:
            match_id: 比赛 ID

        Returns:
            是否成功（失败不影响主流程）
        """
        try:
            from src.api.collectors.lineup_collector import LineupCollector

            collector = LineupCollector()
            result = collector.collect_and_save(match_id)

            if result.success:
                with self._lineup_lock:
                    self._lineup_collected_count += 1
                logger.info(f"    ✓ Lineup collected: {match_id}")
                return True
            logger.warning(f"    ⊘ Lineup skipped: {match_id} - {result.message}")
            return False

        except Exception as e:
            # 阵容采集失败不影响主流程（赔率已入库）
            logger.warning(f"    ⊘ Lineup collection failed for {match_id}: {e}")
            return False

    # ========================================================================
    # 主要运行接口
    # ========================================================================

    def run(
        self,
        mode: Literal["standard", "backfill", "deep_search", "targeted"] = "backfill",
        limit: int = 100,
        match_ids: list[str] | None = None,
    ) -> HarvestStats:
        """
        运行收割服务

        Args:
            mode: 收割模式
            limit: 最大处理数量
            match_ids: 指定的 match_id 列表（仅用于 targeted 模式）

        Returns:
            收割统计
        """
        stats = HarvestStats(mode=HarvestMode(mode))
        harvest_mode = HarvestMode(mode)

        logger.info("=" * 70)
        logger.info("V41.262 OddsHarvestService - Starting")
        logger.info(f"Mode: {mode}, Limit: {limit}")
        logger.info("=" * 70)

        try:
            # ====================================================================
            # Phase 1: 深度搜索恢复（如果启用）
            # ====================================================================
            if harvest_mode == HarvestMode.DEEP_SEARCH:
                blind_spots = self.fetch_blind_spot_matches(limit)

                for match in blind_spots:
                    with stats.lock:
                        stats.total_processed += 1

                    url = self.search_engine.search_match_url(
                        match.home_team, match.away_team, str(match.match_date)
                    )

                    if url and self.search_engine.update_match_url(match.match_id, url):
                        with stats.lock:
                            stats.urls_recovered += 1
                        logger.info(f"  ✓ Recovered URL for {match.match_id}")

                stats.end_time = datetime.now()
                return stats

            # ====================================================================
            # Phase 2: 标准收割 / 回填模式
            # ====================================================================
            matches = self.fetch_pending_matches(limit)

            if not matches:
                logger.warning("No matches to harvest")
                stats.end_time = datetime.now()
                return stats

            logger.info(f"Found {len(matches)} matches to harvest")

            with ThreadPoolExecutor(
                max_workers=self.config.concurrency.default_workers
            ) as executor:
                futures = {
                    executor.submit(self.harvest_single_match, match): match for match in matches
                }

                for future in as_completed(futures):
                    try:
                        success = future.result(timeout=self.config.concurrency.task_timeout)
                        with stats.lock:
                            stats.total_processed += 1
                            if success:
                                stats.successful += 1
                            else:
                                stats.failed += 1
                    except Exception as e:
                        logger.exception(f"Unexpected error: {e}")
                        with stats.lock:
                            stats.total_processed += 1
                            stats.failed += 1

            stats.end_time = datetime.now()

        except Exception as e:
            logger.exception(f"Fatal error in harvest service: {e}")
            import traceback

            traceback.print_exc()

        # V41.278: 转移阵容采集计数到 stats 对象
        stats.lineups_collected = self._lineup_collected_count

        return stats

    def print_stats(self, stats: HarvestStats):
        """打印收割统计"""
        if stats.total_processed > 0:
            pass


# =============================================================================
# 便捷函数
# =============================================================================


def run_harvest(
    mode: Literal["standard", "backfill", "deep_search"] = "backfill",
    limit: int = 100,
    config_path: str = "config/harvester_v2.yaml",
) -> HarvestStats:
    """
    便捷函数：运行收割服务

    Args:
        mode: 收割模式
        limit: 最大处理数量
        config_path: 配置文件路径

    Returns:
        收割统计
    """
    config = get_harvester_config(config_path)
    service = OddsHarvestService(config)
    stats = service.run(mode=mode, limit=limit)
    service.print_stats(stats)
    return stats
