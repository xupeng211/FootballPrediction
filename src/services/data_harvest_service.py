"""
V41.262 Data Harvest Service - 工业级收割引擎
==============================================

这是 V41.262 "Standardized Delivery" 的核心服务类，
整合了 V41.255-V41.261 的所有补丁逻辑，提供统一的、
无硬编码的、可配置的收割接口。

核心功能：
    1. Odds 数据收割（标准模式）
    2. 深度链接恢复（盲区恢复）
    3. 自愈重试机制（指数级退避）
    4. 代理端口轮换

Usage:
    from src.services.data_harvest_service import OddsHarvestService, get_harvester_config

    # 加载配置
    config = get_harvester_config()

    # 创建服务
    service = OddsHarvestService(config)

    # 执行收割
    result = service.run(mode="backfill", limit=100)

Author: V41.262 Architecture Team
Date: 2026-01-20
Version: V41.262 "Standardized Delivery"
"""

from __future__ import annotations

import logging
import re
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Optional, List, Dict, Literal
from urllib.parse import quote

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_config as get_unified_config
from src.services.harvester_config import HarvesterV2Config, get_harvester_config
from src.core.scrapers.industrial_auditor import IndustrialAuditor, AuditorConfig

logger = logging.getLogger("OddsHarvestService")


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
    oddsportal_url: Optional[str] = None


@dataclass
class HarvestStats:
    """收割统计"""
    mode: HarvestMode
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped_no_url: int = 0
    urls_recovered: int = 0
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
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
        except ImportError:
            logger.warning("requests module not available, deep search disabled")

    def search_match_url(self, home_team: str, away_team: str, match_date: str) -> Optional[str]:
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
            logger.error(f"Deep search error: {e}")
            return None

    def _extract_detail_url(self, html: str, home_team: str, away_team: str) -> Optional[str]:
        """从 HTML 提取详情页 URL"""
        hash_pattern = re.compile(self.config.deep_search.hash_pattern)
        detail_pattern = re.compile(self.config.deep_search.detail_page_pattern, re.IGNORECASE)

        matches = detail_pattern.findall(html)
        if not matches:
            matches = re.findall(r'href="(/football/[^"]+)"', html)

        for match in matches:
            match_lower = match.lower()
            if (home_team.lower() in match_lower or away_team.lower() in match_lower):
                hash_match = hash_pattern.search(match)
                if hash_match:
                    return f"https://www.oddsportal.com{match}"
        return None

    def update_match_url(self, match_id: str, url: str) -> bool:
        """更新数据库中的 URL"""
        conn = psycopg2.connect(
            host=self.db_config.host,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value(),
        )
        cursor = conn.cursor()

        try:
            hash_pattern = re.compile(self.config.deep_search.hash_pattern)
            hash_match = hash_pattern.search(url)
            odds_hash = hash_match.group(1) if hash_match else None

            cursor.execute("""
                UPDATE matches_mapping
                SET oddsportal_url = %s,
                    oddsportal_hash = %s,
                    mapping_method = 'V41.262_Deep_Search',
                    confidence = 0.85,
                    updated_at = NOW()
                WHERE fotmob_id = %s
            """, (url, odds_hash, match_id))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update URL for {match_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


# =============================================================================
# 核心收割服务
# =============================================================================


class OddsHarvestService:
    """
    V41.262 Odds 数据收割服务

    工业级统一收割引擎，整合了所有补丁逻辑。
    """

    def __init__(self, config: Optional[HarvesterV2Config] = None):
        """
        初始化收割服务

        Args:
            config: 收割配置（如果为 None，从默认路径加载）
        """
        self.config = config or get_harvester_config()
        self.db_config = get_unified_config()
        self.search_engine = OddsPortalSearchEngine(self.config, self.db_config)

        # 代理端口轮换
        self._proxy_port_index = 0
        self._proxy_lock = Lock()

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
        delay = self.config.retry.base_delay_seconds * (self.config.retry.backoff_multiplier ** attempt)
        return min(delay, self.config.retry.max_delay_seconds)

    # ========================================================================
    # 数据库操作
    # ========================================================================

    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.db_config.host,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def fetch_pending_matches(self, limit: int) -> List[MatchInfo]:
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
            conn.close()

    def fetch_blind_spot_matches(self, limit: int) -> List[MatchInfo]:
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
            conn.close()

    # ========================================================================
    # 数据提取
    # ========================================================================

    def _extract_with_retry(self, target_url: str) -> Optional[dict]:
        """
        带指数级退避和代理轮换的数据提取

        Args:
            target_url: 目标 URL

        Returns:
            提取结果字典，如果所有重试都失败则返回 None
        """
        last_error = None

        for attempt in range(self.config.retry.max_attempts):
            proxy_port = self._get_next_proxy_port()

            try:
                logger.info(f"  Attempt [{attempt + 1}/{self.config.retry.max_attempts}] with proxy port {proxy_port}")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                auditor_config = AuditorConfig(
                    target_url=target_url,
                    target_patterns=self.config.target_patterns,
                    headless=True,
                    proxy_port=proxy_port,
                    navigation_timeout=self.config.auditor.navigation_timeout,
                )

                auditor = IndustrialAuditor(auditor_config)
                extraction_result = loop.run_until_complete(auditor.audit())
                loop.close()

                if not extraction_result or extraction_result.entities_extracted == 0:
                    raise RuntimeError(f"Incomplete page: entities_extracted={extraction_result.entities_extracted if extraction_result else 0}")

                entity = extraction_result.entities[0]
                entity_dict = entity.to_dict()

                logger.info(f"  ✓ Extraction successful: {extraction_result.entities_extracted} entities")
                return {
                    'entity_dict': entity_dict,
                    'extraction_result': extraction_result,
                    'proxy_port': proxy_port,
                }

            except Exception as e:
                last_error = e
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
            cursor.execute("""
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
            """, (
                match_id,
                json.dumps(initial_price) if initial_price else None,
                json.dumps(closing_price) if closing_price else None,
                json.dumps(movement_history) if movement_history else None,
                metadata.get("Quality_Rating", "unknown"),
                metadata.get("Deviation_Percentage", 0),
                "V41.262_Harvest_Service",
            ))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Storage error for {match_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    # ========================================================================
    # 单场比赛收割
    # ========================================================================

    def harvest_single_match(self, match: MatchInfo) -> bool:
        """
        收割单场比赛

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

            extract_result = self._extract_with_retry(match.oddsportal_url)
            if not extract_result:
                return False

            entity_dict = extract_result['entity_dict']
            proxy_port = extract_result['proxy_port']

            initial_price = entity_dict.get("Initial_Price", [])
            closing_price = entity_dict.get("Closing_Price", [])
            movement_history = entity_dict.get("Movement_History", [])

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
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"  ✗ Error: {match.match_id} - {e}")
            return False

    # ========================================================================
    # 主要运行接口
    # ========================================================================

    def run(
        self,
        mode: Literal["standard", "backfill", "deep_search", "targeted"] = "backfill",
        limit: int = 100,
        match_ids: Optional[List[str]] = None,
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
        logger.info(f"V41.262 OddsHarvestService - Starting")
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
                        match.home_team,
                        match.away_team,
                        str(match.match_date)
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

            with ThreadPoolExecutor(max_workers=self.config.concurrency.default_workers) as executor:
                futures = {
                    executor.submit(self.harvest_single_match, match): match
                    for match in matches
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
                        logger.error(f"Unexpected error: {e}")
                        with stats.lock:
                            stats.total_processed += 1
                            stats.failed += 1

            stats.end_time = datetime.now()

        except Exception as e:
            logger.error(f"Fatal error in harvest service: {e}")
            import traceback
            traceback.print_exc()

        return stats

    def print_stats(self, stats: HarvestStats):
        """打印收割统计"""
        print("\n" + "=" * 70)
        print("V41.262 OddsHarvestService - 收割统计")
        print("=" * 70)
        print(f"模式: {stats.mode.value}")
        print(f"开始时间: {stats.start_time.isoformat()}")
        print(f"结束时间: {stats.end_time.isoformat() if stats.end_time else 'N/A'}")
        print(f"\n📊 处理统计:")
        print(f"  总处理: {stats.total_processed}")
        print(f"  成功: {stats.successful}")
        print(f"  失败: {stats.failed}")
        print(f"  跳过(无URL): {stats.skipped_no_url}")
        print(f"  URL恢复: {stats.urls_recovered}")
        if stats.total_processed > 0:
            print(f"  成功率: {stats.successful / stats.total_processed * 100:.1f}%")
        print("=" * 70 + "\n")


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
