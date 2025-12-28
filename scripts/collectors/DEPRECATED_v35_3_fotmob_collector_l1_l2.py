#!/usr/bin/env python3
"""
FotMob API L1/L2 采集器 - 企业级数据采集架构
FootballPrediction L1/L2 Data Collection Architecture

功能说明:
- L1采集: 获取赛程底座数据，存入matches表
- L2采集: 利用L1的ID获取详情JSON，存入raw_match_data表
- 状态管理: 自动更新采集状态和解析状态
- 批量处理: 支持大规模数据批量采集

作者: FootballPrediction Team
版本: v2.0.0
日期: 2024-12-19
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
import asyncpg

from src.config_unified import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class CollectionStats:
    """采集统计信息"""

    l1_matches_found: int = 0
    l1_matches_saved: int = 0
    l2_attempts: int = 0
    l2_successful: int = 0
    l2_failed: int = 0
    total_requests: int = 0
    total_bytes_saved: int = 0


class FotMobL1L2Collector:
    """
    FotMob L1/L2 采集器

    L1 (Index Layer): 赛程底座数据采集
    L2 (Raw Data Layer): 原始详情数据采集
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout: int = 30,
        batch_size: int = 50,
        delay_between_requests: float = 3.0,  # V26.0 限流增强（防封禁）
        max_l2_concurrency: int = 2,  # V26.0 并发限流（降低 API 压力）
        silent_mode: bool = False,  # 静默生产模式
        progress_interval: int = 500,  # V26.0 进度输出间隔（500 场）
    ):
        """初始化采集器"""
        self.max_retries = max_retries
        self.timeout = timeout
        self.batch_size = batch_size
        self.delay_between_requests = delay_between_requests
        self.max_l2_concurrency = max_l2_concurrency
        self.silent_mode = silent_mode
        self.progress_interval = progress_interval
        self.client: aiohttp.ClientSession | None = None
        self.db_pool: asyncpg.Pool | None = None

        # 采集统计
        self.stats = CollectionStats()

        # 进度计数器（用于静默模式）
        self._l1_saved_count = 0
        self._l2_saved_count = 0
        self._last_progress_output = 0

        # L2并发控制信号量
        self.l2_semaphore = None

        # 专用进度日志器（独立于主日志器）
        self.progress_logger = logging.getLogger("harvest_progress")
        self.progress_logger.setLevel(logging.INFO)
        if not self.progress_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
            self.progress_logger.addHandler(handler)
        self.progress_logger.propagate = False

        # 最新认证头 (2024-12-20更新)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
            "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9tYXRjaERldGFpbHM/bWF0Y2hJZD00NTA2NTk0IiwiY29kZSI6MTc2NjE5MzY3MzMwMiwiZm9vIjoicHJvZHVjdGlvbjo0YTVlZjI5ZTY4Yjg5YTAyNDIyMjVkMDliOGU2MTE3ZGYwOGE1YTVlIn0sInNpZ25hdHVyZSI6IjgyMDE5QjJBRTYwRDBFNDUzMEFBQTdDNDFDN0Q1QTYwIn0=",
            "x-foo": "production:4a5ef29e68b89a0242225d09b8e6117df08a5a5e",
        }

        logger.info("🚀 FotMob L1/L2采集器初始化完成")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def initialize(self):
        """初始化HTTP客户端和数据库连接"""
        # 初始化HTTP客户端
        if not self.client or self.client.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.client = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
            )

        # 初始化数据库连接池
        if not self.db_pool:
            self.db_pool = await asyncpg.create_pool(
                settings.database.get_connection_string(), min_size=2, max_size=10, command_timeout=60
            )

        # 初始化L2并发控制信号量
        if not self.l2_semaphore:
            self.l2_semaphore = asyncio.Semaphore(self.max_l2_concurrency)

        logger.info("✅ HTTP客户端、数据库连接池和L2并发控制初始化完成")

    async def close(self):
        """关闭资源"""
        if self.client and not self.client.closed:
            await self.client.close()
            logger.info("🔐 HTTP客户端已关闭")

        if self.db_pool:
            await self.db_pool.close()
            logger.info("🔐 数据库连接池已关闭")

    # ===============================================================
    # L1 采集逻辑：赛程底座数据
    # ===============================================================

    async def collect_l1_matches_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """
        L1采集：按日期采集比赛列表 (已弃用 - 请使用 collect_season_matches)

        Args:
            date_str: 日期字符串，格式: YYYY-MM-DD

        Returns:
            比赛列表
        """
        logger.warning("⚠️ collect_l1_matches_by_date已弃用，请使用collect_season_matches")
        return []

    async def collect_season_matches(
        self,
        league_id: int,
        season_code: str,
        league_name: str,
        season_display: str,
    ) -> list[dict[str, Any]]:
        """
        L1采集：采集整个赛季的所有比赛数据
        使用最新API端点: /api/leagues?id={league_id}&season={season_code}

        V35.4 修正: 移除硬编码默认值，强制要求显式传递 league_name

        Args:
            league_id: 联赛 ID (必须显式传递)
            season_code: 赛季代码 (必须显式传递)
            league_name: 联赛名称 (必须显式传递，严禁使用默认值)
            season_display: 赛季显示名称 (必须显式传递)

        Returns:
            比赛列表
        """
        # V35.4: 参数验证，防止硬编码默认值污染
        if not league_name or league_name == "Premier League" and league_id != 47:
            raise ValueError(
                f"⚠️ league_name 必须显式传递且匹配 league_id! "
                f"收到: league_id={league_id}, league_name='{league_name}'"
            )
        try:
            if not self.client:
                await self.initialize()

            # 使用最新API端点
            url = "https://www.fotmob.com/api/leagues"
            params = {"id": league_id, "season": season_code}

            logger.info(f"🎯 L1赛季请求: {url}?id={league_id}&season={season_code}")

            async with self.client.get(url, params=params) as response:
                self.stats.total_requests += 1
                logger.info(f"📊 L1响应状态码: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    matches = self._parse_season_matches(
                        data, league_name=league_name, league_id=league_id, season_display=season_display
                    )
                    self.stats.l1_matches_found = len(matches)
                    logger.info(f"✅ L1赛季采集成功，找到 {len(matches)} 场比赛")
                    return matches
                else:
                    response_text = await response.text()
                    logger.error(f"❌ L1赛季请求失败，状态码: {response.status}")
                    logger.error(f"🔍 响应内容: {response_text[:200]}...")
                    return []

        except Exception as e:
            logger.error(f"❌ L1赛季采集异常: {e}")
            return []

    def _parse_season_matches(
        self,
        data: dict[str, Any],
        league_name: str,
        league_id: int,
        season_display: str,
    ) -> list[dict[str, Any]]:
        """
        解析赛季比赛数据

        V35.4: 移除默认值，强制要求显式传递参数
        """
        matches = []

        try:
            # 从 overview.matches.allMatches 提取比赛数据
            if "overview" in data and "matches" in data["overview"]:
                matches_data = data["overview"]["matches"]
                if "allMatches" in matches_data:
                    raw_matches = matches_data["allMatches"]
                    logger.info(f"📊 从 allMatches 提取 {len(raw_matches)} 场比赛")

                    # 标准化比赛数据（传递联赛和赛季参数）
                    for match in raw_matches:
                        if isinstance(match, dict):
                            standardized = self._standardize_season_match(
                                match, league_name=league_name, league_id=league_id, season_display=season_display
                            )
                            if standardized:
                                matches.append(standardized)

            return matches

        except Exception as e:
            logger.error(f"❌ L1赛季数据解析失败: {e}")
            return []

    def _standardize_season_match(
        self,
        match: dict[str, Any],
        league_name: str,
        league_id: int,
        season_display: str,
    ) -> dict[str, Any] | None:
        """
        标准化赛季比赛数据

        V35.4: 移除默认值，强制要求显式传递参数

        Args:
            match: 原始比赛数据
            league_name: 联赛名称 (必须显式传递)
            league_id: 联赛 ID (必须显式传递)
            season_display: 赛季显示名称 (必须显式传递)

        Returns:
            标准化后的比赛数据
        """
        try:
            # 提取基础信息
            match_id = str(match.get("id", ""))
            if not match_id:
                return None

            # 提取队伍信息
            home = match.get("home", {})
            away = match.get("away", {})

            home_name = home.get("name", "")
            away_name = away.get("name", "")

            if not home_name or not away_name:
                return None

            # 提取比赛时间
            match_time = self._parse_match_time(match.get("status", {}).get("utcTime"))

            # 提取状态
            status_obj = match.get("status", {})
            status = "Fixture"  # 默认状态
            if status_obj.get("finished"):
                status = "Finished"
            elif status_obj.get("started"):
                status = "Live"

            # 提取比分
            result_score = None
            if status_obj.get("scoreStr"):
                result_score = status_obj["scoreStr"]
            elif "scoreStr" in match:
                result_score = match["scoreStr"]

            # 提取轮次信息
            round_info = match.get("round", "")
            round_name = match.get("roundName", round_info)

            return {
                "id": match_id,  # 添加 id 字段用于数据库主键
                "external_id": match_id,
                "league_name": league_name,  # ✅ 动态联赛名称
                "season": season_display,  # ✅ 动态赛季名称
                "match_time": match_time,
                "status": status,
                "home_team": home_name,
                "away_team": away_name,
                "league_id": league_id,  # ✅ 动态联赛 ID
                "home_team_id": int(home.get("id", 0) or 0),  # 确保是整数
                "away_team_id": int(away.get("id", 0) or 0),  # 确保是整数
                "round_info": str(round_name),
                "venue_name": match.get("venue", {}).get("name") if match.get("venue") else None,
                "result_score": result_score,
                "raw_data": match,
            }

        except Exception as e:
            logger.error(f"❌ 赛季比赛数据标准化失败: {e}")
            return None

    def _parse_match_time(self, time_str: str) -> datetime:
        """解析比赛时间"""
        try:
            if not time_str:
                return datetime.now()

            # 尝试不同的时间格式
            time_formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with milliseconds
                "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y%m%dT%H%M%S",
            ]

            for fmt in time_formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue

            # 如果都失败了，返回当前时间
            logger.warning(f"⚠️ 无法解析时间格式: {time_str}")
            return datetime.now()

        except Exception as e:
            logger.error(f"❌ 时间解析异常: {e}")
            return datetime.now()

    def _parse_l1_matches(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """解析L1比赛数据"""
        matches = []

        try:
            # 解析不同结构的响应
            if "matches" in data:
                matches = data["matches"]
            elif "leagues" in data:
                for league in data["leagues"]:
                    if "matches" in league:
                        matches.extend(league["matches"])
            else:
                # 尝试在根级别查找比赛列表
                for _key, value in data.items():
                    if isinstance(value, list) and value:
                        # 检查是否是比赛数据
                        first_item = value[0]
                        if isinstance(first_item, dict):
                            # 检查是否包含比赛关键字段
                            if any(key in first_item for key in ["id", "matchId", "homeTeam", "awayTeam"]):
                                matches.extend(value)
                                break

            # 标准化比赛数据
            standardized_matches = []
            for match in matches:
                if not isinstance(match, dict):
                    continue

                standardized_match = self._standardize_l1_match(match)
                if standardized_match:
                    standardized_matches.append(standardized_match)

            return standardized_matches

        except Exception as e:
            logger.error(f"❌ L1数据解析失败: {e}")
            return []

    def _standardize_l1_match(self, match: dict[str, Any]) -> dict[str, Any] | None:
        """标准化L1比赛数据"""
        try:
            # 提取基础信息
            match_id = str(match.get("id", match.get("matchId", "")))
            if not match_id:
                return None

            # 提取主客队信息
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})

            home_team_name = home_team.get("name") or home_team.get("shortName") or str(home_team.get("id", ""))
            away_team_name = away_team.get("name") or away_team.get("shortName") or str(away_team.get("id", ""))

            if not home_team_name or not away_team_name:
                return None

            # 提取联赛信息
            tournament = match.get("tournament", {})
            league_name = tournament.get("name") or tournament.get("leagueName") or "Unknown League"

            # 解析比赛时间
            match_time = None
            start_time = match.get("startTime") or match.get("utcTime")
            if start_time:
                try:
                    match_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"⚠️ 时间格式解析失败: {start_time}")

            # 提取状态
            status = match.get("status", "Fixture")

            return {
                "external_id": match_id,
                "league_name": league_name,
                "season": str(match.get("season", "2024/25")),
                "match_time": match_time or datetime.now(),
                "status": status,
                "home_team": home_team_name,
                "away_team": away_team_name,
                "league_id": tournament.get("tournamentId"),
                "home_team_id": home_team.get("id"),
                "away_team_id": away_team.get("id"),
                "venue_name": match.get("venue", {}).get("name") if match.get("venue") else None,
                "result_score": match.get("scoreStr"),
                "raw_data": match,  # 保存原始数据用于调试
            }

        except Exception as e:
            logger.error(f"❌ L1比赛数据标准化失败: {e}")
            return None

    async def _save_l1_match_index(self, match: dict[str, Any]) -> bool:
        """
        保存单场L1比赛索引到数据库

        Args:
            match: 标准化的比赛数据

        Returns:
            是否保存成功
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    # 使用 external_id + season 作为唯一标识符（避免不同赛季的 ID 冲突）
                    external_id = match.get("external_id") or match.get("id", "")
                    season = match.get("season", "unknown")
                    unique_match_id = f"{external_id}_{season}"

                    query = """
                        INSERT INTO matches (
                            match_id, external_id, league_name, season, match_date, status,
                            home_team, away_team, league_id, home_team_id, away_team_id,
                            venue_name, result_score, round_info, collection_status, l1_collected_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'pending', NOW())
                        ON CONFLICT (match_id)
                        DO UPDATE SET
                            match_date = EXCLUDED.match_date,
                            status = EXCLUDED.status,
                            result_score = EXCLUDED.result_score,
                            round_info = EXCLUDED.round_info,
                            l1_collected_at = GREATEST(matches.l1_collected_at, EXCLUDED.l1_collected_at),
                            updated_at = NOW()
                    """

                    await conn.execute(
                        query,
                        unique_match_id,  # $1 match_id (使用唯一复合键)
                        external_id,  # $2 external_id (保留原始 FotMob ID)
                        match.get("league_name"),  # $3
                        season,  # $4
                        match.get("match_time"),  # $5 match_date
                        match.get("status"),  # $6
                        match.get("home_team"),  # $7
                        match.get("away_team"),  # $8
                        match.get("league_id"),  # $9
                        match.get("home_team_id"),  # $10
                        match.get("away_team_id"),  # $11
                        match.get("venue_name"),  # $12
                        match.get("result_score"),  # $13
                        match.get("round_info"),  # $14
                    )

                    # 静默模式：只输出进度
                    if not self.silent_mode:
                        logger.info(
                            f"✅ L1索引保存成功: {match.get('home_team', 'Unknown')} vs {match.get('away_team', 'Unknown')}"
                        )
                    else:
                        self._l1_saved_count += 1
                        if self._l1_saved_count % self.progress_interval == 0:
                            self.progress_logger.info(f"⏳ L1保存进度: {self._l1_saved_count} 场")
                    return True

        except Exception as e:
            logger.error(f"❌ L1索引保存失败 {match.get('external_id', 'unknown')}: {e}")
            return False

    async def save_all_l1_matches(self, matches: list[dict[str, Any]]) -> int:
        """
        保存所有L1比赛到数据库

        Args:
            matches: 标准化的比赛数据列表

        Returns:
            成功保存的比赛数量
        """
        saved_count = 0
        for match in matches:
            if await self._save_l1_match_index(match):
                saved_count += 1

        self.stats.l1_matches_saved = saved_count
        logger.info(f"✅ L1索引保存完成: {saved_count}/{len(matches)} 场比赛")
        return saved_count

    async def _filter_new_matches(self, match_ids: list[str]) -> list[str]:
        """
        过滤出需要采集 L2 的新比赛（已存在 raw_match_data 的跳过）

        Args:
            match_ids: 比赛ID列表（格式：{external_id}_{season}）

        Returns:
            需要采集的比赛ID列表（格式：{external_id}_{season}）
        """
        if not match_ids:
            return []

        try:
            async with self.db_pool.acquire() as conn:
                # V26.0 最终修复：raw_match_data.match_id 现在使用 {external_id}_{season} 格式
                # 直接查询完整的 match_id
                query = """
                    SELECT DISTINCT match_id
                    FROM raw_match_data
                    WHERE match_id = ANY($1)
                """
                existing = await conn.fetch(query, match_ids)
                existing_ids = set(row["match_id"] for row in existing)

                # 返回不存在的比赛ID
                new_matches = [mid for mid in match_ids if mid not in existing_ids]
                logger.info(f"🔍 V26.0 过滤结果: {len(new_matches)}/{len(match_ids)} 场新比赛")
                return new_matches

        except Exception as e:
            logger.error(f"❌ 过滤新比赛失败: {e}")
            # 出错时返回全部，避免遗漏
            return match_ids

    # ===============================================================
    # L2 采集逻辑：原始详情数据
    # ===============================================================

    async def collect_l2_match_data(self, match_id: str) -> dict[str, Any] | None:
        """
        L2采集：获取单场比赛详情数据（带并发控制）

        Args:
            match_id: 比赛ID（格式：{external_id}_{season} 或原始 external_id）

        Returns:
            比赛详情数据
        """
        # 使用信号量控制并发
        async with self.l2_semaphore:
            try:
                if not self.client:
                    await self.initialize()

                # 从 match_id 中提取原始 external_id（移除 season 后缀）
                external_id = match_id.rsplit("_", 1)[0] if "_" in match_id else match_id

                url = "https://www.fotmob.com/api/matchDetails"
                params = {"matchId": external_id}  # 使用原始 ID 请求 API

                if not self.silent_mode:
                    full_url = f"{url}?matchId={external_id}"
                    logger.info(f"🎯 L2请求: {full_url} [并发: {self.l2_semaphore._value}/{self.max_l2_concurrency}]")

                async with self.client.get(url, params=params) as response:
                    self.stats.total_requests += 1
                    self.stats.l2_attempts += 1

                    if response.status == 200:
                        data = await response.json()
                        data_size = len(json.dumps(data, ensure_ascii=False))
                        self.stats.total_bytes_saved += data_size
                        self.stats.l2_successful += 1

                        if not self.silent_mode:
                            logger.info(f"✅ L2采集成功: {match_id}, 数据大小: {data_size} 字节")
                        return data
                    else:
                        response_text = await response.text()
                        logger.error(f"❌ L2请求失败，状态码: {response.status}")
                        logger.error(f"🔍 响应内容: {response_text[:200]}...")
                        self.stats.l2_failed += 1
                        return None

            except Exception as e:
                logger.error(f"❌ L2采集异常 {match_id}: {e}")
                self.stats.l2_failed += 1
                return None

    async def _save_l2_raw_data(self, match_id: str, data: dict[str, Any]) -> bool:
        """
        保存L2原始数据并更新采集状态

        Args:
            match_id: 比赛ID（格式：{external_id}_{season}）
            data: 原始数据

        Returns:
            是否保存成功
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    # 从 match_id 中提取原始 external_id（移除 season 后缀）
                    external_id = match_id.rsplit("_", 1)[0] if "_" in match_id else match_id

                    # 1. 保存L2原始数据（V26.0 修复：使用 match_id 作为主键，包含 season 后缀）
                    # 这样可以正确区分不同赛季的同 ID 比赛
                    query = """
                        INSERT INTO raw_match_data
                        (match_id, external_id, raw_data, source, collected_at, created_at, updated_at)
                        VALUES ($1, $2, $3, 'fotmob', NOW(), NOW(), NOW())
                        ON CONFLICT (match_id)
                        DO UPDATE SET
                            raw_data = EXCLUDED.raw_data,
                            data_version = raw_match_data.data_version + 1,
                            updated_at = NOW()
                    """

                    # V26.0 最终修复：raw_match_data.match_id 使用完整格式 {external_id}_{season}
                    await conn.execute(query, match_id, external_id, json.dumps(data, ensure_ascii=False))

                    # 2. 更新matches表的L2采集状态（使用 match_id 精确匹配）
                    update_query = """
                        UPDATE matches
                        SET collection_status = 'completed',
                            l2_collected_at = NOW(),
                            updated_at = NOW()
                        WHERE match_id = $1
                    """

                    await conn.execute(update_query, match_id)

                    # 静默模式：只输出进度
                    if not self.silent_mode:
                        data_size = len(json.dumps(data, ensure_ascii=False))
                        logger.info(f"✅ L2数据保存成功: {match_id}, 大小: {data_size} 字节")
                    else:
                        self._l2_saved_count += 1
                        if self._l2_saved_count % self.progress_interval == 0:
                            self.progress_logger.info(f"⏳ L2保存进度: {self._l2_saved_count} 场")
                    return True

        except Exception as e:
            logger.error(f"❌ L2数据保存失败 {match_id}: {e}")
            return False

    async def batch_collect_l2_concurrent(self, match_ids: list[str]) -> dict[str, int]:
        """
        批量并发采集L2数据

        Args:
            match_ids: 比赛ID列表

        Returns:
            采集结果统计
        """
        if not match_ids:
            return {"successful": 0, "failed": 0, "total": 0}

        logger.info(f"🚀 开始批量L2并发采集: {len(match_ids)} 场比赛，并发限制: {self.max_l2_concurrency}")

        # 创建并发任务
        tasks = []
        for match_id in match_ids:
            task = self._collect_and_save_l2(match_id)
            tasks.append(task)

        # 执行并发任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        successful = 0
        failed = 0
        for i, result in enumerate(results):
            match_id = match_ids[i]
            if isinstance(result, Exception):
                logger.error(f"❌ L2采集异常 {match_id}: {result}")
                failed += 1
            elif result:
                successful += 1
            else:
                failed += 1

        logger.info(f"🎉 批量L2采集完成: {successful}/{len(match_ids)} 成功")
        return {
            "successful": successful,
            "failed": failed,
            "total": len(match_ids),
            "success_rate": round(successful / len(match_ids) * 100, 2) if match_ids else 0,
        }

    async def _collect_and_save_l2(self, match_id: str) -> bool:
        """
        采集并保存单场L2数据

        Args:
            match_id: 比赛ID

        Returns:
            是否成功
        """
        try:
            # 采集L2数据
            data = await self.collect_l2_match_data(match_id)
            if not data:
                return False

            # 保存到数据库
            return await self._save_l2_raw_data(match_id, data)

        except Exception as e:
            logger.error(f"❌ L2采集和保存失败 {match_id}: {e}")
            return False

    async def _update_collection_status_batch(self, match_ids: list[str], status: str) -> bool:
        """批量更新采集状态（使用 match_id）"""
        if not match_ids:
            return True

        try:
            async with self.db_pool.acquire() as conn:
                placeholders = ",".join([f"${i + 2}" for i in range(len(match_ids))])
                query = f"""
                    UPDATE matches
                    SET collection_status = $1, updated_at = NOW()
                    WHERE match_id IN ({placeholders})
                """

                await conn.execute(query, status, *match_ids)
                logger.info(f"✅ 批量更新L2状态: {len(match_ids)} -> {status}")
                return True

        except Exception as e:
            logger.error(f"❌ 批量更新状态失败: {e}")
            return False

    # ===============================================================
    # 批量处理逻辑
    # ===============================================================

    async def batch_process_matches(self, date_str: str) -> dict[str, Any]:
        """
        批量处理L1->L2完整流程

        Args:
            date_str: 日期字符串，格式: YYYY-MM-DD

        Returns:
            处理统计信息
        """
        logger.info(f"🚀 开始批量处理: {date_str}")
        start_time = datetime.now()

        try:
            # 1. L1采集：获取比赛列表
            matches = await self.collect_l1_matches_by_date(date_str)
            if not matches:
                logger.warning(f"⚠️ 未找到比赛: {date_str}")
                return {
                    "date": date_str,
                    "l1_matches_found": 0,
                    "l1_matches_saved": 0,
                    "l2_attempts": 0,
                    "l2_successful": 0,
                    "l2_failed": 0,
                    "success_rate": 0.0,
                }

            # 2. 保存L1索引数据
            l1_success = await self._save_l1_match_index(matches)
            if not l1_success:
                logger.error("❌ L1索引保存失败，停止L2采集")
                return {"error": "L1 save failed"}

            # 3. 提取match_ids
            match_ids = [match["external_id"] for match in matches]

            # 4. 标记L2采集状态为in_progress
            await self._update_collection_status_batch(match_ids, "in_progress")

            # 5. L2采集：批量获取详情数据
            l2_results = []
            for i, match_id in enumerate(match_ids, 1):
                logger.info(f"🔄 L2采集进度: {i}/{len(match_ids)} - {match_id}")

                try:
                    data = await self.collect_l2_match_data(match_id)
                    if data:
                        # 保存L2数据
                        save_success = await self._save_l2_raw_data(match_id, data)
                        if save_success:
                            l2_results.append((match_id, True))
                        else:
                            l2_results.append((match_id, False))
                    else:
                        l2_results.append((match_id, False))

                    # 智能延迟
                    if i < len(match_ids):
                        delay = self.delay_between_requests + (i % 2) * 0.5
                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"❌ L2采集处理失败 {match_id}: {e}")
                    l2_results.append((match_id, False))

            # 6. 统计结果
            successful = sum(1 for _, success in l2_results if success)
            failed = len(l2_results) - successful

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "date": date_str,
                "l1_matches_found": len(matches),
                "l1_matches_saved": len(matches) if l1_success else 0,
                "l2_attempts": len(match_ids),
                "l2_successful": successful,
                "l2_failed": failed,
                "success_rate": round(successful / len(match_ids) * 100, 2) if match_ids else 0,
                "duration_seconds": round(duration, 2),
                "total_requests": self.stats.total_requests,
                "total_bytes_saved": self.stats.total_bytes_saved,
            }

            logger.info(f"🎉 批量处理完成: {date_str}")
            logger.info(f"   L1比赛: {result['l1_matches_saved']}/{result['l1_matches_found']}")
            logger.info(f"   L2采集: {result['l2_successful']}/{result['l2_attempts']} ({result['success_rate']}%)")
            logger.info(f"   耗时: {result['duration_seconds']}s")

            return result

        except Exception as e:
            logger.error(f"❌ 批量处理失败: {e}")
            return {"error": str(e), "date": date_str}

    async def process_date_range(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """
        处理日期范围

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            每日处理结果列表
        """
        from datetime import timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        results = []
        current = start

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            result = await self.batch_process_matches(date_str)
            results.append(result)
            current += timedelta(days=1)

        return results

    # ===============================================================
    # 统计和监控
    # ===============================================================

    def get_stats(self) -> dict[str, Any]:
        """获取采集统计信息"""
        return {
            "total_requests": self.stats.total_requests,
            "l1_matches_found": self.stats.l1_matches_found,
            "l1_matches_saved": self.stats.l1_matches_saved,
            "l2_attempts": self.stats.l2_attempts,
            "l2_successful": self.stats.l2_successful,
            "l2_failed": self.stats.l2_failed,
            "l2_success_rate": (round(self.stats.l2_successful / max(self.stats.l2_attempts, 1) * 100, 2)),
            "total_bytes_saved": self.stats.total_bytes_saved,
            "avg_data_size_per_match": (round(self.stats.total_bytes_saved / max(self.stats.l2_successful, 1), 2)),
        }

    def _log_stats(self):
        """记录统计信息"""
        stats = self.get_stats()
        logger.info("📊 采集统计:")
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")


# ===============================================================
# 高阶数据解析功能
# ===============================================================


class AdvancedDataParser:
    """高阶数据解析器 - 用于解析L2原始JSON数据"""

    @staticmethod
    def parse_xg_data(raw_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        解析xG (预期进球) 数据

        Args:
            raw_data: L2原始JSON数据

        Returns:
            解析后的xG数据
        """
        try:
            xg_data = {}

            # 从content中提取xG数据
            content = raw_data.get("content", {})

            # 查找xG相关数据
            if "stats" in content:
                stats = content["stats"]
                for stat_category in stats:
                    if "stats" in stat_category:
                        for stat in stat_category["stats"]:
                            if stat.get("key") == "expected_goals":
                                xg_data["home_xg"] = stat.get("stats", {}).get("home", 0)
                                xg_data["away_xg"] = stat.get("stats", {}).get("away", 0)
                            elif stat.get("key") == "xg_on_target":
                                xg_data["home_xg_on_target"] = stat.get("stats", {}).get("home", 0)
                                xg_data["away_xg_on_target"] = stat.get("stats", {}).get("away", 0)

            # 从header中提取比分信息
            header = raw_data.get("header", {})
            if "status" in header:
                status_obj = header["status"]
                if "scoreStr" in status_obj:
                    xg_data["final_score"] = status_obj["scoreStr"]

            return xg_data if xg_data else None

        except Exception as e:
            logger.error(f"❌ xG数据解析失败: {e}")
            return None

    @staticmethod
    def parse_lineup_data(raw_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        解析阵容数据

        Args:
            raw_data: L2原始JSON数据

        Returns:
            解析后的阵容数据
        """
        try:
            lineup_data = {"home_lineup": {}, "away_lineup": {}}

            # 从content中提取阵容数据
            content = raw_data.get("content", {})

            # 查找阵容数据
            if "lineup" in content:
                lineup = content["lineup"]

                # 主队阵容
                if "home" in lineup:
                    home_lineup = lineup["home"]
                    lineup_data["home_lineup"] = {
                        "formation": home_lineup.get("formation", ""),
                        "players": home_lineup.get("players", []),
                    }

                # 客队阵容
                if "away" in lineup:
                    away_lineup = lineup["away"]
                    lineup_data["away_lineup"] = {
                        "formation": away_lineup.get("formation", ""),
                        "players": away_lineup.get("players", []),
                    }

            # 检查是否有有效的阵容数据
            if lineup_data["home_lineup"].get("players") or lineup_data["away_lineup"].get("players"):
                return lineup_data

            return None

        except Exception as e:
            logger.error(f"❌ 阵容数据解析失败: {e}")
            return None

    @staticmethod
    def parse_match_stats(raw_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        解析比赛统计数据

        Args:
            raw_data: L2原始JSON数据

        Returns:
            解析后的比赛统计数据
        """
        try:
            stats_data = {}

            # 从content中提取统计数据
            content = raw_data.get("content", {})

            if "stats" in content:
                stats = content["stats"]
                for stat_category in stats:
                    category_title = stat_category.get("title", "")
                    if "stats" in stat_category:
                        for stat in stat_category["stats"]:
                            stat_key = stat.get("key", "")
                            stat_title = stat.get("title", "")
                            home_value = stat.get("stats", {}).get("home", 0)
                            away_value = stat.get("stats", {}).get("away", 0)

                            # 创建统计键
                            stat_key_full = f"{category_title}_{stat_key}" if category_title else stat_key

                            stats_data[stat_key_full] = {
                                "title": stat_title,
                                "home": home_value,
                                "away": away_value,
                                "diff": home_value - away_value,
                            }

            return stats_data if stats_data else None

        except Exception as e:
            logger.error(f"❌ 比赛统计数据解析失败: {e}")
            return None

    @staticmethod
    def comprehensive_parse(raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        综合解析L2数据

        Args:
            raw_data: L2原始JSON数据

        Returns:
            综合解析结果
        """
        result = {
            "match_id": raw_data.get("general", {}).get("matchId", ""),
            "parse_time": datetime.now().isoformat(),
            "xg_data": None,
            "lineup_data": None,
            "match_stats": None,
            "parse_status": "success",
        }

        try:
            # 解析xG数据
            result["xg_data"] = AdvancedDataParser.parse_xg_data(raw_data)

            # 解析阵容数据
            result["lineup_data"] = AdvancedDataParser.parse_lineup_data(raw_data)

            # 解析比赛统计数据
            result["match_stats"] = AdvancedDataParser.parse_match_stats(raw_data)

            # 统计解析结果
            parsed_sections = sum(
                1 for data in [result["xg_data"], result["lineup_data"], result["match_stats"]] if data
            )
            result["parsed_sections"] = parsed_sections
            result["total_sections"] = 3

            logger.info(f"✅ 综合解析完成: {result['match_id']} - {parsed_sections}/3 个部分解析成功")

        except Exception as e:
            logger.error(f"❌ 综合解析失败: {e}")
            result["parse_status"] = "failed"
            result["error"] = str(e)

        return result


# ===============================================================
# 便捷函数
# ===============================================================


async def create_fotmob_l1_l2_collector(**kwargs) -> FotMobL1L2Collector:
    """创建FotMob L1/L2采集器实例"""
    return FotMobL1L2Collector(**kwargs)


# ===============================================================
# 主函数示例
# ===============================================================


async def main():
    """主函数：演示正规化L1/L2采集流程"""
    # 配置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        # 创建采集器（带L2并发控制）
        async with FotMobL1L2Collector(max_l2_concurrency=3) as collector:
            logger.info("🚀 开始正规化采集系统演示")

            # 1. L1赛季采集
            logger.info("📋 步骤1: L1赛季数据采集")
            matches = await collector.collect_season_matches()
            if not matches:
                logger.error("❌ L1赛季采集失败，退出")
                return 1

            logger.info(f"✅ L1赛季采集成功，找到 {len(matches)} 场比赛")

            # 2. 保存L1数据
            logger.info("💾 步骤2: 保存L1数据到数据库")
            saved_count = await collector.save_all_l1_matches(matches)
            logger.info(f"✅ L1数据保存完成: {saved_count}/{len(matches)} 场比赛")

            # 3. L2并发采集演示（前5场比赛）
            logger.info("🔥 步骤3: L2并发采集演示（前5场比赛）")
            first_5_match_ids = [match["external_id"] for match in matches[:5]]

            # 标记状态为进行中
            await collector._update_collection_status_batch(first_5_match_ids, "in_progress")

            # 并发采集L2数据
            l2_results = await collector.batch_collect_l2_concurrent(first_5_match_ids)
            logger.info(f"🎉 L2并发采集完成: {l2_results}")

            # 4. 高阶解析演示
            logger.info("🧠 步骤4: 高阶解析演示")
            # 从数据库获取一场L2数据进行解析演示
            if l2_results["successful"] > 0:
                demo_match_id = first_5_match_ids[0]
                async with collector.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT raw_data FROM raw_match_data WHERE external_id = $1", demo_match_id
                    )
                    if row:
                        raw_data = json.loads(row["raw_data"])
                        parser_result = AdvancedDataParser.comprehensive_parse(raw_data)

                        print("\n" + "=" * 60)
                        print("🧠 高阶解析演示结果")
                        print("=" * 60)
                        print(f"比赛ID: {parser_result['match_id']}")
                        print(f"解析状态: {parser_result['parse_status']}")
                        print(
                            f"解析成功部分: {parser_result.get('parsed_sections', 0)}/{parser_result.get('total_sections', 3)}"
                        )

                        if parser_result.get("xg_data"):
                            print(f"\n📊 xG数据: {parser_result['xg_data']}")
                        if parser_result.get("lineup_data"):
                            home_formation = parser_result["lineup_data"].get("home_lineup", {}).get("formation", "")
                            away_formation = parser_result["lineup_data"].get("away_lineup", {}).get("formation", "")
                            print(f"👥 阵容: 主队 {home_formation} vs 客队 {away_formation}")
                        if parser_result.get("match_stats"):
                            stats_count = len(parser_result["match_stats"])
                            print(f"📈 比赛统计: {stats_count} 项数据")

            # 5. 输出完整统计
            print("\n" + "=" * 60)
            print("📊 正规化采集系统统计报告")
            print("=" * 60)
            stats = collector.get_stats()
            for key, value in stats.items():
                print(f"{key:25} : {value}")
            print("=" * 60)

            logger.info("🎉 正规化采集系统演示完成！")

    except Exception as e:
        logger.error(f"❌ 主函数执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
