#!/usr/bin/env python3
"""
FotMob Scout - V41.115 标准化侦察兵模块
========================================

V41.115 "铁板大一统" - 侦察兵模块化

核心功能:
1. 发现比赛（Scout 阶段）- 从 FotMob API 获取比赛列表
2. 26维字段提取（一鱼多吃）- 完整保存所有可用字段
3. 配置驱动设计（杜绝硬编码）- 使用 config_unified 配置系统
4. UPSERT 机制支持 - 数据库安全插入/更新

特性:
- 从 /api/leagues?id={league_id}&season={season} 端点发现比赛
- 支持赛季标准化（多种格式互转）
- 代理池轮换支持
- 结构化日志记录

作者：高级系统可靠性工程师 (V41.115)
日期：2026-01-16
"""

from datetime import datetime
import logging
from typing import Any

import requests

# 配置日志
logger = logging.getLogger(__name__)


class FotMobScout:
    """
    V41.115 FotMob 侦察兵 - 比赛发现模块

    Scout 阶段：发现新比赛并保存基础信息（26维字段）

    核心职责：
    1. 从 FotMob API 发现比赛
    2. 提取完整的 26 维基础字段
    3. 支持数据库 UPSERT 操作
    """

    def __init__(self):
        """初始化侦察兵"""
        from src.config_unified import get_settings

        settings = get_settings()
        self.api_config = settings.fotmob_api
        self.league_ids = self.api_config.LEAGUE_IDS
        self.season_mapping = self.api_config.SEASON_MAPPING

        # 创建会话
        self.session = requests.Session()

        # 统计信息
        self.stats = {
            "total_discovered": 0,
            "successful_seasons": 0,
            "failed_seasons": 0,
        }

    def discover_league_matches(
        self, league_name: str, seasons: list[str], proxy: str | None = None
    ) -> dict[str, Any]:
        """
        发现联赛比赛（Scout 阶段）

        Args:
            league_name: 联赛名称（如 "Bundesliga"）
            seasons: 赛季列表（如 ["2023/2024", "2024/2025"]）
            proxy: 代理 URL（可选）

        Returns:
            采集结果字典
        """
        # 从配置获取 League ID
        league_id = self.api_config.get_league_id(league_name)

        if not league_id:
            logger.error(f"❌ 联赛未在配置中找到: {league_name}")
            return {
                "success": False,
                "error": f"League not found in config: {league_name}",
                "league_name": league_name,
                "matches": [],
            }

        logger.info("🔍 V41.115 Scout: 发现联赛比赛")
        logger.info(f"   联赛: {league_name} (ID: {league_id})")
        logger.info(f"   赛季: {', '.join(seasons)}")

        all_matches = []
        season_results = {}

        # 逐赛季采集
        for season in seasons:
            # 标准化赛季格式
            normalized_season = self.api_config.normalize_season(season)

            logger.info(f"🔄 采集 {season} → {normalized_season}...")

            matches = self._fetch_season_matches(league_id, normalized_season, proxy)

            if matches is None:
                self.stats["failed_seasons"] += 1
                season_results[season] = []
                continue

            self.stats["successful_seasons"] += 1
            self.stats["total_discovered"] += len(matches)

            # 添加元数据
            enriched_matches = [
                self._enrich_match_data(m, league_id, league_name, normalized_season)
                for m in matches
            ]

            all_matches.extend(enriched_matches)
            season_results[season] = enriched_matches

            logger.info(f"   ✅ {normalized_season}: {len(matches)} 场比赛")

        return {
            "success": True,
            "league_name": league_name,
            "league_id": league_id,
            "seasons": seasons,
            "stats": self.stats,
            "season_results": season_results,
            "matches": all_matches,
        }

    def _fetch_season_matches(
        self, league_id: int, season: str, proxy: str | None = None
    ) -> list[dict] | None:
        """
        获取指定赛季的比赛

        Args:
            league_id: 联赛 ID
            season: 标准化赛季代码（如 "2324"）
            proxy: 代理 URL（可选）

        Returns:
            比赛列表
        """
        url = self.api_config.build_url("leagues", id=league_id, season=season)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{self.api_config.base_web_url}/",
        }

        proxies = {"http": proxy, "https": proxy} if proxy else None

        try:
            # V41.115: 代理可选，不可用时直连
            if proxies:
                try:
                    response = self.session.get(url, headers=headers, proxies=proxies, timeout=30)
                except requests.exceptions.ProxyError:
                    logger.info("⚠️  代理不可用，切换到直连模式")
                    response = self.session.get(url, headers=headers, timeout=30)
            else:
                response = self.session.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if "fixtures" not in data or "allMatches" not in data["fixtures"]:
                    logger.warning("⚠️  数据格式异常")
                    return None

                return data["fixtures"]["allMatches"]
            logger.warning(f"⚠️  HTTP {response.status_code}")
            return None

        except Exception as e:
            logger.exception(f"❌ 请求失败: {e}")
            return None

    def _enrich_match_data(
        self, match: dict, league_id: int, league_name: str, season: str
    ) -> dict:
        """
        V41.115: 丰富比赛数据（26维字段）

        Args:
            match: 原始比赛数据
            league_id: 联赛 ID
            league_name: 联赛名称
            season: 赛季代码

        Returns:
            丰富后的比赛数据（26维字段）
        """
        status_obj = match.get("status", {})

        # 解析比分
        score_str = status_obj.get("scoreStr", "")
        home_score, away_score = self._parse_score(score_str)

        return {
            # === 核心标识 ===
            "match_id": match.get("id"),
            # === 球队信息 ===
            "home_team": match.get("home", {}).get("name"),
            "home_team_id": match.get("home", {}).get("id"),
            "home_team_short_name": match.get("home", {}).get("shortName"),
            "away_team": match.get("away", {}).get("name"),
            "away_team_id": match.get("away", {}).get("id"),
            "away_team_short_name": match.get("away", {}).get("shortName"),
            # === 比赛状态 ===
            "status_code": status_obj.get("reason", {}).get("short", ""),
            "is_finished": status_obj.get("finished", False),
            "is_started": status_obj.get("started", False),
            "is_cancelled": status_obj.get("cancelled", False),
            "is_awarded": status_obj.get("awarded", False),
            # === 比分和时间 ===
            "home_score": home_score,
            "away_score": away_score,
            "score_str": score_str,
            "match_time_utc": status_obj.get("utcTime"),
            # === 轮次和链接 ===
            "round": match.get("round"),
            "round_name": match.get("roundName"),
            "page_url": match.get("pageUrl"),
            # === 采集元数据 ===
            "league_id": league_id,
            "league_name": league_name,
            "season": season,
            "data_source": "fotmob_scout_v41_115",
            "collection_status": "discovered",
            "collected_at": datetime.now().isoformat(),
        }

    def _parse_score(self, score_str: str | None) -> tuple[int | None, int | None]:
        """
        解析比分字符串

        Args:
            score_str: "2 - 3" 格式的比分

        Returns:
            (home_score, away_score) 或 (None, None)
        """
        if not score_str:
            return None, None

        try:
            parts = score_str.split(" - ")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass

        return None, None

    def save_matches_to_database(
        self, matches: list[dict], batch_size: int = 100
    ) -> dict[str, Any]:
        """
        保存比赛到数据库（UPSERT 机制）

        Args:
            matches: 比赛列表
            batch_size: 批次大小

        Returns:
            保存结果
        """
        import psycopg2

        from src.config_unified import get_settings

        settings = get_settings()
        conn = None

        try:
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            total_saved = 0

            # 批量处理
            for i in range(0, len(matches), batch_size):
                batch = matches[i : i + batch_size]

                with conn.cursor() as cur:
                    for match in batch:
                        # UPSERT 操作
                        upsert_sql = """
                        INSERT INTO matches (
                            match_id, home_team, home_team_id, home_team_short_name,
                            away_team, away_team_id, away_team_short_name,
                            status, is_finished, is_started, is_cancelled, is_awarded,
                            home_score, away_score, score_str, match_date,
                            round, round_name, page_url,
                            league_id, league_name, season,
                            data_source, collection_status, collected_at
                        ) VALUES (
                            %(match_id)s, %(home_team)s, %(home_team_id)s, %(home_team_short_name)s,
                            %(away_team)s, %(away_team_id)s, %(away_team_short_name)s,
                            %(status_code)s, %(is_finished)s, %(is_started)s, %(is_cancelled)s, %(is_awarded)s,
                            %(home_score)s, %(away_score)s, %(score_str)s, %(match_time_utc)s,
                            %(round)s, %(round_name)s, %(page_url)s,
                            %(league_id)s, %(league_name)s, %(season)s,
                            %(data_source)s, %(collection_status)s, %(collected_at)s
                        )
                        ON CONFLICT (match_id) DO UPDATE SET
                            home_team = EXCLUDED.home_team,
                            home_team_id = EXCLUDED.home_team_id,
                            away_team = EXCLUDED.away_team,
                            away_team_id = EXCLUDED.away_team_id,
                            updated_at = NOW()
                        """

                        cur.execute(upsert_sql, match)
                        total_saved += 1

                conn.commit()
                logger.info(f"✅ 批次 {i // batch_size + 1}: 保存 {len(batch)} 条记录")

            return {
                "success": True,
                "total_saved": total_saved,
                "total_batches": (len(matches) + batch_size - 1) // batch_size,
            }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception(f"❌ 数据库保存失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_saved": 0,
            }
        finally:
            if conn:
                conn.close()


# 便捷函数
def create_scout() -> FotMobScout:
    """创建侦察兵实例

    Returns:
        FotMobScout 实例
    """
    return FotMobScout()


def discover_and_save(
    league_name: str, seasons: list[str], save_to_db: bool = True
) -> dict[str, Any]:
    """
    发现并保存比赛（便捷函数）

    Args:
        league_name: 联赛名称
        seasons: 赛季列表
        save_to_db: 是否保存到数据库

    Returns:
        操作结果
    """
    scout = create_scout()

    # 发现比赛
    result = scout.discover_league_matches(league_name, seasons)

    if not result["success"]:
        return result

    # 保存到数据库
    if save_to_db:
        save_result = scout.save_matches_to_database(result["matches"])
        result["save_result"] = save_result

    return result
