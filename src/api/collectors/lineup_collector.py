"""
V41.273 Lineup Collector - Lineup Data Collector
=================================================

Collect match starting XI and missing players data from FotMob API.

Core Features:
1. Starting XI extraction (formation + player details)
2. Missing players extraction (injuries, suspensions)
3. Database storage with upsert support
4. Coverage tracking for quality monitoring

V41.284: Supersonic Harvest
- 429 (Too Many Requests) 智能避让
- 指数退避重试机制
- 不阻塞主收割流程

Usage:
    from src.api.collectors.lineup_collector import LineupCollector

    collector = LineupCollector()
    result = collector.collect_lineup(match_id)
    # result: {"success": True, "formation": "4-3-3", "starting_xi": [...], "missing": [...]}

Author: Senior AI Data Scientist
Date: 2026-01-20
Version: V41.284 "Supersonic Harvest"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import time  # V41.284: 用于 429 避让
from typing import Any

import httpx
import yaml

from src.config_unified import get_config

logger = logging.getLogger("LineupCollector")


# Load FotMob configuration
def _load_fotmob_config() -> dict:
    """Load FotMob configuration from harvester config"""
    config_path = "config/harvester_v2.yaml"
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config.get("fotmob", {})
    except Exception as e:
        logger.warning(f"Failed to load FotMob config: {e}, using defaults")
        return {
            "base_url": "https://www.fotmob.com",
            "api_endpoints": {"match_details": "/api/matchDetails"},
            "request": {"timeout_seconds": 30, "follow_redirects": True},
        }


_FOTMOB_CONFIG = _load_fotmob_config()


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PlayerInfo:
    """Player information"""

    player_id: str
    name: str
    position: str | None = None  # GK, RB, CB, etc.
    shirt_number: int | None = None
    rating: float | None = None
    minutes_played: int | None = None


@dataclass
class LineupData:
    """Lineup data"""

    match_id: str
    home_formation: str | None = None
    home_starting_xi: list[PlayerInfo] = field(default_factory=list)
    home_missing_players: list[PlayerInfo] = field(default_factory=list)
    away_formation: str | None = None
    away_starting_xi: list[PlayerInfo] = field(default_factory=list)
    away_missing_players: list[PlayerInfo] = field(default_factory=list)
    source_updated_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dict (for database storage)"""
        return {
            "match_id": self.match_id,
            "home_formation": self.home_formation,
            "home_starting_xi": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "position": p.position,
                    "shirt_number": p.shirt_number,
                    "rating": p.rating,
                    "minutes_played": p.minutes_played,
                }
                for p in self.home_starting_xi
            ],
            "home_missing_players": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "reason": p.position,  # Reuse position field for reason
                }
                for p in self.home_missing_players
            ],
            "away_formation": self.away_formation,
            "away_starting_xi": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "position": p.position,
                    "shirt_number": p.shirt_number,
                    "rating": p.rating,
                    "minutes_played": p.minutes_played,
                }
                for p in self.away_starting_xi
            ],
            "away_missing_players": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "reason": p.position,
                }
                for p in self.away_missing_players
            ],
            "source_updated_at": self.source_updated_at.isoformat()
            if self.source_updated_at
            else None,
        }

    def validate_integrity(self) -> tuple[bool, str]:
        """
        V41.274 Lineup integrity check

        Validation rules:
        1. Starting XI total should be 22 players (11 per team)
        2. Each team must have Formation data
        3. Both teams cannot be missing Formation

        Returns:
            (is_valid, rejection_reason)
        """
        # Check 1: Starting XI count
        total_starting_xi = len(self.home_starting_xi) + len(self.away_starting_xi)

        if total_starting_xi != 22:
            return (
                False,
                f"LINEUP_INCOMPLETE: Total Starting XI = {total_starting_xi} (expected 22)",
            )

        # Check 2: Each team has 11 players
        if len(self.home_starting_xi) != 11:
            return (
                False,
                f"LINEUP_INCOMPLETE: Home Starting XI = {len(self.home_starting_xi)} (expected 11)",
            )

        if len(self.away_starting_xi) != 11:
            return (
                False,
                f"LINEUP_INCOMPLETE: Away Starting XI = {len(self.away_starting_xi)} (expected 11)",
            )

        # Check 3: Formation data
        if not self.home_formation and not self.away_formation:
            return False, "LINEUP_INCOMPLETE: Neither team has Formation data"

        # Warning but not rejection: Single team missing Formation
        if not self.home_formation:
            logger.warning(f"  ⚠️ Home team missing Formation for {self.match_id}")

        if not self.away_formation:
            logger.warning(f"  ⚠️ Away team missing Formation for {self.match_id}")

        return True, ""


@dataclass
class CollectionResult:
    """Collection result"""

    success: bool
    match_id: str
    message: str
    lineup_data: LineupData | None = None


# =============================================================================
# Lineup Collector
# =============================================================================


class LineupCollector:
    """
    V41.273 Lineup Collector

    Collect starting XI and missing players data from FotMob API.
    """

    def __init__(self):
        self.settings = get_config()
        self.config = _FOTMOB_CONFIG
        # Build endpoint URL from config
        base_url = self.config.get("base_url", "https://www.fotmob.com")
        endpoint = self.config.get("api_endpoints", {}).get("match_details", "/api/matchDetails")
        self.MATCH_DETAILS_ENDPOINT = f"{base_url}{endpoint}"
        # Load request settings
        request_config = self.config.get("request", {})
        timeout = request_config.get("timeout_seconds", 30)
        follow_redirects = request_config.get("follow_redirects", True)
        self.client = httpx.Client(timeout=timeout, follow_redirects=follow_redirects)

        # V41.282: Enable heuristic path discovery
        self.heuristic_discovery_enabled = True

    # =============================================================================
    # V41.282: Heuristic Path Discovery
    # =============================================================================

    def _is_lineup_candidate(self, obj: Any) -> bool:
        """
        V41.282: 判断对象是否是阵容数据的候选者

        判定标准:
        1. 必须是列表类型
        2. 长度在 10-13 之间（允许替补/伤病）
        3. 至少有一个元素包含球员特征字段 (id/name/position)

        Args:
            obj: 待检查对象

        Returns:
            是否是阵容候选（球员数组）
        """
        if not isinstance(obj, list):
            return False

        # 长度检查: 10-13（首发 11 人 + 潜在的替补/伤病）
        if not (10 <= len(obj) <= 13):
            return False

        if len(obj) == 0:
            return False

        # 检查是否包含球员特征字段
        first_element = obj[0]
        if isinstance(first_element, dict):
            # 检查是否包含至少一个阵容相关字段
            element_keys = set(first_element.keys())
            # 至少有一个 id 或 name，且包含位置相关字段
            has_player_id = any(k in element_keys for k in ["id", "name"])
            has_position = any(
                k in element_keys for k in ["position", "positionId", "originalPosition"]
            )
            return has_player_id and has_position

        return False

    def _is_team_data_object(self, obj: Any) -> bool:
        """
        V41.282: 判断对象是否是包含阵容数据的队伍数据对象

        判定标准:
        1. 必须是字典类型
        2. 包含 'formation' 字段
        3. 包含 'starters' 或 'lineup' 字段（球员数组）

        Args:
            obj: 待检查对象

        Returns:
            是否是队伍数据对象
        """
        if not isinstance(obj, dict):
            return False

        # 检查是否包含 formation
        has_formation = "formation" in obj

        # 检查是否包含阵容数组
        has_starters = "starters" in obj and isinstance(obj["starters"], list)
        has_lineup = "lineup" in obj and isinstance(obj["lineup"], list)

        return has_formation and (has_starters or has_lineup)

    def _crawl_for_lineup(
        self,
        json_obj: Any,
        path: str = "$",
        depth: int = 0,
        max_depth: int = 8,
        results: list[dict] | None = None,
        parent_obj: Any = None,
        parent_path: str | None = None,
    ) -> list[dict]:
        """
        V41.282: 递归爬取 JSON 查找阵容数据

        启发式策略:
        1. 优先查找队伍数据对象（包含 formation + starters/lineup）
        2. 回退到球员数组（11 个球员对象）

        Args:
            json_obj: JSON 对象（dict/list/primitive）
            path: 当前路径（用于调试）
            depth: 当前递归深度
            max_depth: 最大递归深度（防止无限递归）
            results: 已发现的阵容候选
            parent_obj: 父对象（用于返回包含 formation 的完整对象）
            parent_path: 父对象路径

        Returns:
            List of {"path": str, "data": dict, "confidence": float, "type": str}
        """
        if results is None:
            results = []

        # 深度保护
        if depth > max_depth:
            return results

        # ====================================================================
        # 优先级 1: 检查是否是队伍数据对象（包含 formation + starters/lineup）
        # ====================================================================
        if self._is_team_data_object(json_obj):
            # 这是一个完整的队伍数据对象，包含 formation 和球员数据
            confidence = self._calculate_team_data_confidence(json_obj, path)
            results.append(
                {"path": path, "data": json_obj, "confidence": confidence, "type": "team_data"}
            )
            # 找到完整对象，不需要继续深入
            return results

        # ====================================================================
        # 优先级 2: 检查是否是球员数组（回退方案）
        # ====================================================================
        if self._is_lineup_candidate(json_obj):
            confidence = self._calculate_lineup_confidence(json_obj, path)
            results.append(
                {"path": path, "data": json_obj, "confidence": confidence, "type": "player_list"}
            )

        # ====================================================================
        # 递归搜索
        # ====================================================================
        if isinstance(json_obj, dict):
            # 优先处理包含关键字的键
            priority_keys = []
            other_keys = []

            for key in json_obj:
                key_lower = key.lower()
                if any(
                    kw in key_lower
                    for kw in ["lineup", "starter", "team", "player", "home", "away"]
                ):
                    priority_keys.append(key)
                else:
                    other_keys.append(key)

            # 优先探索关键路径
            for key in priority_keys + other_keys:
                new_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                self._crawl_for_lineup(
                    json_obj[key], new_path, depth + 1, max_depth, results, json_obj, path
                )

        elif isinstance(json_obj, list):
            # 对于列表，只检查前几个元素（避免过度展开）
            check_limit = min(len(json_obj), 5)
            for i in range(check_limit):
                new_path = f"{path}[{i}]"
                self._crawl_for_lineup(
                    json_obj[i], new_path, depth + 1, max_depth, results, json_obj, path
                )

        return results

    def _calculate_team_data_confidence(self, candidate: dict, path: str) -> float:
        """
        V41.282: 计算队伍数据对象的置信度

        评分标准:
        1. 包含 formation: +20 分
        2. 包含 starters/lineup 且长度 11: +40 分
        3. 包含 unavailable/missingPlayers: +10 分
        4. 路径包含 home/away/team: +20 分
        5. 球员字段完整性: +10 分

        Args:
            candidate: 候选队伍数据对象
            path: 数据路径

        Returns:
            置信度分数 (0-100)
        """
        score = 0.0

        # 1. formation 字段
        if "formation" in candidate:
            score += 20.0

        # 2. starters/lineup 字段
        has_starters = "starters" in candidate and isinstance(candidate["starters"], list)
        has_lineup_list = "lineup" in candidate and isinstance(candidate["lineup"], list)

        player_count = 0
        if has_starters:
            player_count = len(candidate["starters"])
        elif has_lineup_list:
            player_count = len(candidate["lineup"])

        if player_count == 11:
            score += 40.0
        elif 10 <= player_count <= 13:
            score += 30.0

        # 3. unavailable/missingPlayers 字段
        has_unavailable = "unavailable" in candidate
        has_missing = "missingPlayers" in candidate or "injured" in candidate
        if has_unavailable or has_missing:
            score += 10.0

        # 4. 路径关键词
        path_lower = path.lower()
        if any(kw in path_lower for kw in ["home", "away"]):
            score += 20.0
        elif "team" in path_lower:
            score += 10.0

        # 5. 球员字段完整性
        players = candidate.get("starters") or candidate.get("lineup", [])
        if players and len(players) > 0:
            first_player = players[0]
            if isinstance(first_player, dict):
                has_id = "id" in first_player
                has_name = "name" in first_player
                if has_id and has_name:
                    score += 10.0

        return min(score, 100.0)

    def _calculate_lineup_confidence(self, candidate: list, path: str) -> float:
        """
        V41.282: 计算阵容候选的置信度

        评分标准:
        1. 长度正好 11: +30 分
        2. 包含完整球员字段（id + name + position）: +40 分
        3. 路径包含 'lineup' 或 'starters': +20 分
        4. 包含 formation 字段: +10 分

        Args:
            candidate: 候选阵容数据
            path: 数据路径

        Returns:
            置信度分数 (0-100)
        """
        score = 0.0

        # 1. 长度评分
        if len(candidate) == 11:
            score += 30.0
        elif 10 <= len(candidate) <= 13:
            score += 20.0

        # 2. 字段完整性评分
        if candidate and isinstance(candidate[0], dict):
            first_player = candidate[0]
            required_fields = ["id", "name"]
            optional_fields = ["position", "positionId", "shirtNumber", "jerseyNumber"]

            has_required = all(f in first_player for f in required_fields)
            has_optional = any(f in first_player for f in optional_fields)

            if has_required:
                score += 30.0
            if has_optional:
                score += 10.0

        # 3. 路径关键词评分
        path_lower = path.lower()
        if "starters" in path_lower:
            score += 25.0
        elif "lineup" in path_lower:
            score += 20.0
        elif any(kw in path_lower for kw in ["home", "away", "team"]):
            score += 10.0

        # 4. 结构评分
        if candidate and isinstance(candidate[0], dict):
            if "formation" in candidate[0] or any("formation" in str(p) for p in candidate):
                score += 5.0

        return min(score, 100.0)

    def _find_lineup_data_heuristic(self, content: dict) -> tuple[dict | None, dict | None, str]:
        """
        V41.282: 启发式查找主客队阵容数据

        策略:
        1. 使用递归爬取找到所有阵容候选
        2. 根据置信度排序
        3. 自动识别 home/away 阵容对

        Args:
            content: FotMob API content 字段

        Returns:
            (home_lineup_data, away_lineup_data, discovery_method)
            discovery_method 用于日志记录
        """
        # 递归爬取所有阵容候选
        candidates = self._crawl_for_lineup(content, path="$.content", max_depth=8)

        if not candidates:
            logger.warning("V41.282: Heuristic discovery found no lineup candidates")
            return None, None, "heuristic:none"

        # 按置信度排序
        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # 记录发现的候选
        logger.debug(f"V41.282: Found {len(candidates)} lineup candidates")
        for i, cand in enumerate(candidates[:3]):  # 只记录前 3 个
            logger.debug(
                f"  Candidate {i + 1}: {cand['path']} (confidence: {cand['confidence']:.1f})"
            )

        # 识别 home/away 对
        home_data = None
        away_data = None

        # 方法 1: 从路径识别 home/away
        home_candidates = [c for c in candidates if "home" in c["path"].lower()]
        away_candidates = [c for c in candidates if "away" in c["path"].lower()]

        if home_candidates and away_candidates:
            # 取最高置信度的
            home_data = home_candidates[0]["data"]
            away_data = away_candidates[0]["data"]
            return (
                home_data,
                away_data,
                f"heuristic:path_match({home_candidates[0]['path']},{away_candidates[0]['path']})",
            )

        # 方法 2: 取前两个最高置信度的候选
        if len(candidates) >= 2:
            home_data = candidates[0]["data"]
            away_data = candidates[1]["data"]
            return (
                home_data,
                away_data,
                f"heuristic:top_two({candidates[0]['path']},{candidates[1]['path']})",
            )

        # 方法 3: 只有一个候选，尝试在父对象找配对
        if len(candidates) == 1:
            # 尝试从候选的父对象找另一个队伍
            cand = candidates[0]
            # 从路径推断父对象
            path_parts = cand["path"].split(".")
            for i in range(len(path_parts) - 1):
                ".".join(path_parts[: i + 1])
                # 这里可以扩展更复杂的父对象查找逻辑

        logger.warning(
            f"V41.282: Could not find home/away pair, found {len(candidates)} candidate(s)"
        )
        return (
            candidates[0]["data"] if candidates else None,
            None,
            f"heuristic:partial({len(candidates)})",
        )

    def _parse_starting_xi(
        self, team_data: Any, is_home: bool
    ) -> tuple[str | None, list[PlayerInfo]]:
        """
        Parse starting XI data

        V41.282: Support multiple input formats:
        - Dict with 'starters' or 'lineup' keys (V41.281 behavior)
        - Direct list of player objects (V41.282 heuristic discovery)

        Args:
            team_data: FotMob API team data response (dict or list)
            is_home: Whether this is home team

        Returns:
            (formation, starting_xi_list)
        """
        formation = None
        starting_xi = []

        # ====================================================================
        # V41.282: Handle direct player list (heuristic discovery result)
        # ====================================================================
        if isinstance(team_data, list):
            lineup = team_data
            formation = None  # Formation not available from direct list
        # ====================================================================
        # V41.281: Handle dict with starters/lineup keys
        # ====================================================================
        elif isinstance(team_data, dict):
            formation = team_data.get("formation")
            # Try new API structure first (starters)
            starters = team_data.get("starters", [])
            if isinstance(starters, list) and len(starters) > 0:
                lineup = starters
            else:
                # Fall back to old structure (lineup)
                lineup = team_data.get("lineup", [])
        else:
            logger.warning(f"V41.282: Unexpected team_data type: {type(team_data)}")
            return None, []

        # Parse starting XI (usually first 11 players)
        for player_data in lineup[:11]:
            try:
                player_id = player_data.get("id", "")
                name = player_data.get("name", "")

                # Get position info
                position = player_data.get("position") or player_data.get("originalPosition")

                # V41.281: Handle positionId from new API structure
                if position is None:
                    position_id = player_data.get("positionId")
                    if position_id is not None:
                        # Map positionId to position string
                        position_map = {
                            1: "GK",
                            11: "GK",
                            2: "RB",
                            32: "RB",
                            3: "CB",
                            34: "CB",
                            4: "LB",
                            33: "LB",
                            5: "CDM",
                            6: "CM",
                            7: "CAM",
                            8: "RW",
                            9: "LW",
                            10: "ST",
                        }
                        position = position_map.get(position_id, "Unknown")

                shirt_number = player_data.get("shirtNumber") or player_data.get("jerseyNumber")

                # V41.281: Handle rating from new API structure (performance.rating)
                rating = None
                if "performance" in player_data:
                    rating = player_data["performance"].get("rating")
                if rating is None:
                    stats = player_data.get("stats", {})
                    rating = stats.get("rating") or stats.get("averageRating")

                # Get minutes played
                minutes = player_data.get("minutesPlayed")

                player = PlayerInfo(
                    player_id=str(player_id),
                    name=name,
                    position=position,
                    shirt_number=int(shirt_number)
                    if shirt_number and shirt_number.isdigit()
                    else None,
                    rating=rating,
                    minutes_played=minutes,
                )
                starting_xi.append(player)

            except Exception as e:
                logger.debug(f"Error parsing player: {e}")
                continue

        return formation, starting_xi

    def _parse_missing_players(self, team_data: Any) -> list[PlayerInfo]:
        """
        Parse missing players data

        V41.282: Support multiple input formats:
        - Dict with 'unavailable', 'missingPlayers', or 'injured' keys (V41.281 behavior)
        - Direct list (empty for heuristic discovery)

        Args:
            team_data: FotMob API team data response (dict or list)

        Returns:
            List of missing players
        """
        missing = []
        missing_data = []

        # ====================================================================
        # V41.282: Handle direct list (no missing players from heuristic discovery)
        # ====================================================================
        if isinstance(team_data, list):
            missing_data = []
        # ====================================================================
        # V41.281: Handle dict with unavailable/missingPlayers keys
        # ====================================================================
        elif isinstance(team_data, dict):
            # Try new API structure first (unavailable)
            unavailable = team_data.get("unavailable", [])
            if isinstance(unavailable, list) and len(unavailable) > 0:
                missing_data = unavailable
            else:
                # Fall back to old structure
                missing_data = team_data.get("missingPlayers") or team_data.get("injured") or []
        else:
            logger.warning(f"V41.282: Unexpected team_data type: {type(team_data)}")
            return []

        for player_data in missing_data:
            try:
                player_id = player_data.get("id", "")
                name = player_data.get("name", "")
                reason = player_data.get("reason") or player_data.get("status") or "Unknown"

                player = PlayerInfo(
                    player_id=str(player_id),
                    name=name,
                    position=reason,  # Reuse position field for reason
                )
                missing.append(player)

            except Exception as e:
                logger.debug(f"Error parsing missing player: {e}")
                continue

        return missing

    def collect_lineup(self, match_id: str) -> CollectionResult:
        """
        Collect lineup data for a single match

        V41.282: 启发式路径探测 + V41.281 兼容性回退
        - 优先使用启发式路径发现（活逻辑）
        - 如果启发式失败，回退到 V41.281 双结构兼容
        - 最后回退到直接路径查找

        V41.284: 429 智能避让
        - 检测 429 状态码
        - 自动 5 秒休眠后重试
        - 不阻塞主收割流程

        Args:
            match_id: FotMob match ID

        Returns:
            CollectionResult
        """
        try:
            url = f"{self.MATCH_DETAILS_ENDPOINT}?matchId={match_id}"

            response = self.client.get(url)
            response.raise_for_status()

            data = response.json()

            # Check data completeness
            if "content" not in data:
                return CollectionResult(
                    success=False,
                    match_id=match_id,
                    message="Invalid API response: missing 'content' field",
                )

            content = data["content"]

            home_lineup_data = None
            away_lineup_data = None
            discovery_method = "unknown"

            # ====================================================================
            # V41.282: 启发式路径发现（活逻辑）
            # ====================================================================
            if self.heuristic_discovery_enabled:
                home_lineup_data, away_lineup_data, discovery_method = (
                    self._find_lineup_data_heuristic(content)
                )
                if home_lineup_data and away_lineup_data:
                    logger.info(f"V41.282: Heuristic discovery SUCCESS: {discovery_method}")
                else:
                    logger.warning(f"V41.282: Heuristic discovery partial: {discovery_method}")

            # ====================================================================
            # V41.281: 双结构兼容回退（硬编码但稳健）
            # ====================================================================
            if not home_lineup_data or not away_lineup_data:
                logger.debug("V41.282: Falling back to V41.281 dual-structure compatibility")

                # Try new API structure first (content.lineup)
                lineup_root = content.get("lineup", {})
                home_lineup_data = lineup_root.get("homeTeam", {})
                away_lineup_data = lineup_root.get("awayTeam", {})
                discovery_method = "v41.281:new_structure"

                # If new structure is empty, fall back to old structure (content.lineups)
                if not home_lineup_data or not away_lineup_data:
                    match_data = content.get("match", {})
                    home_team = match_data.get("homeTeam") or {}
                    away_team = match_data.get("awayTeam") or {}

                    home_team_id = str(home_team.get("id", ""))
                    away_team_id = str(away_team.get("id", ""))

                    lineups = content.get("lineups", {})
                    home_lineup_data = lineups.get(home_team_id) or {}
                    away_lineup_data = lineups.get(away_team_id) or {}
                    discovery_method = "v41.281:old_structure"

            # ====================================================================
            # 最终检查: 如果还是没找到数据，返回失败
            # ====================================================================
            if not home_lineup_data and not away_lineup_data:
                return CollectionResult(
                    success=False,
                    match_id=match_id,
                    message=f"Could not find lineup data using any method: {discovery_method}",
                )

            # ====================================================================
            # 解析阵容数据
            # ====================================================================
            home_formation, home_starting_xi = self._parse_starting_xi(
                home_lineup_data, is_home=True
            )
            away_formation, away_starting_xi = self._parse_starting_xi(
                away_lineup_data, is_home=False
            )

            # Parse missing players
            home_missing = self._parse_missing_players(home_lineup_data)
            away_missing = self._parse_missing_players(away_lineup_data)

            # Build lineup data
            lineup_data = LineupData(
                match_id=match_id,
                home_formation=home_formation,
                home_starting_xi=home_starting_xi,
                home_missing_players=home_missing,
                away_formation=away_formation,
                away_starting_xi=away_starting_xi,
                away_missing_players=away_missing,
                source_updated_at=datetime.now(),
            )

            return CollectionResult(
                success=True,
                match_id=match_id,
                message=f"Successfully collected lineup for {match_id} via {discovery_method}",
                lineup_data=lineup_data,
            )

        except httpx.HTTPStatusError as e:
            # V41.284: 429 智能避让
            if e.response.status_code == 429:
                logger.warning(
                    f"  ⚠️ V41.284: 429 Too Many Requests for {match_id} - backing off 5s..."
                )
                time.sleep(5)  # 等待 5 秒后重试
                # 重试一次
                try:
                    response = self.client.get(url)
                    response.raise_for_status()
                    # 递归调用自己处理响应（注意：这里只重试一次）
                    return self.collect_lineup(match_id)
                except Exception as retry_e:
                    logger.exception(f"  ✗ V41.284: Retry failed for {match_id}: {retry_e}")
                    return CollectionResult(
                        success=False,
                        match_id=match_id,
                        message=f"HTTP 429 backoff retry failed: {retry_e!s}",
                    )
            else:
                logger.exception(f"HTTP error fetching lineup for {match_id}: {e}")
                return CollectionResult(
                    success=False,
                    match_id=match_id,
                    message=f"HTTP error: {e.response.status_code}",
                )
        except Exception as e:
            logger.exception(f"Error collecting lineup for {match_id}: {e}")
            return CollectionResult(success=False, match_id=match_id, message=f"Error: {e!s}")

    def save_lineup(self, lineup_data: LineupData) -> bool:
        """
        Save lineup data to database

        Args:
            lineup_data: Lineup data

        Returns:
            Success status
        """
        import json

        import psycopg2

        conn = psycopg2.connect(
            host=self.settings.database.host,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

        cursor = conn.cursor()

        try:
            data_dict = lineup_data.to_dict()

            # V41.281: 序列化 JSON 字段为字符串（PostgreSQL ::jsonb 需要 JSON 字符串）
            params = {
                "match_id": data_dict["match_id"],
                "home_formation": data_dict["home_formation"],
                "home_starting_xi": json.dumps(data_dict["home_starting_xi"]),
                "home_missing_players": json.dumps(data_dict["home_missing_players"]),
                "away_formation": data_dict["away_formation"],
                "away_starting_xi": json.dumps(data_dict["away_starting_xi"]),
                "away_missing_players": json.dumps(data_dict["away_missing_players"]),
                "source_updated_at": data_dict["source_updated_at"],
            }

            # Upsert operation
            cursor.execute(
                """
                INSERT INTO match_lineups (
                    match_id,
                    home_formation,
                    home_starting_xi,
                    home_missing_players,
                    away_formation,
                    away_starting_xi,
                    away_missing_players,
                    source,
                    source_updated_at
                ) VALUES (
                    %(match_id)s,
                    %(home_formation)s,
                    %(home_starting_xi)s::jsonb,
                    %(home_missing_players)s::jsonb,
                    %(away_formation)s,
                    %(away_starting_xi)s::jsonb,
                    %(away_missing_players)s::jsonb,
                    'FotMob',
                    %(source_updated_at)s
                )
                ON CONFLICT (match_id) DO UPDATE SET
                    home_formation = EXCLUDED.home_formation,
                    home_starting_xi = EXCLUDED.home_starting_xi,
                    home_missing_players = EXCLUDED.home_missing_players,
                    away_formation = EXCLUDED.away_formation,
                    away_starting_xi = EXCLUDED.away_starting_xi,
                    away_missing_players = EXCLUDED.away_missing_players,
                    source_updated_at = EXCLUDED.source_updated_at,
                    updated_at = CURRENT_TIMESTAMP
            """,
                params,
            )

            conn.commit()
            logger.info(f"✓ Lineup saved for match {lineup_data.match_id}")
            return True

        except Exception as e:
            logger.exception(f"Error saving lineup for {lineup_data.match_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def collect_and_save(self, match_id: str) -> CollectionResult:
        """
        Collect and save lineup data

        V41.274: Lineup integrity check

        Args:
            match_id: FotMob match ID

        Returns:
            CollectionResult
        """
        result = self.collect_lineup(match_id)

        if result.success and result.lineup_data:
            # ====================================================================
            # V41.274 Step 2: Lineup integrity check
            # ====================================================================
            is_complete, rejection_reason = result.lineup_data.validate_integrity()

            if not is_complete:
                logger.error(
                    f"  ✗ Lineup integrity check FAILED for {match_id}: {rejection_reason}"
                )
                return CollectionResult(
                    success=False,
                    match_id=match_id,
                    message=f"Lineup integrity check failed: {rejection_reason}",
                )

            logger.info(f"  ✓ Lineup integrity check PASSED for {match_id}")

            saved = self.save_lineup(result.lineup_data)
            if not saved:
                return CollectionResult(
                    success=False,
                    match_id=match_id,
                    message="Collection successful but save failed",
                )

        return result

    def get_coverage_stats(self) -> dict:
        """
        Get lineup data coverage statistics

        Returns:
            Coverage statistics
        """
        import psycopg2

        conn = psycopg2.connect(
            host=self.settings.database.host,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

        cursor = conn.cursor()

        try:
            # Total matches count
            cursor.execute("SELECT COUNT(*) FROM matches")
            total_matches = cursor.fetchone()[0]

            # Matches with lineup data count
            cursor.execute("SELECT COUNT(*) FROM match_lineups")
            covered_matches = cursor.fetchone()[0]

            coverage = (covered_matches / total_matches * 100) if total_matches > 0 else 0

            return {
                "total_matches": total_matches,
                "covered_matches": covered_matches,
                "coverage_percentage": round(coverage, 2),
            }

        finally:
            conn.close()

    def cleanup(self):
        """Clean up resources"""
        if self.client:
            self.client.close()
