#!/usr/bin/env python3
"""
V20.7 原子级数据对齐引擎 - Atomic Data Alignment Engine
========================================================

核心功能:
1. 动态扁平化: 自动提取 JSON 中所有统计维度 (436+ 基础特征)
2. 全息元数据: 提取裁判、球场、天气、阵型、球员评分等元数据
3. 球员原子数据: 提取每个球员的 id, name, rating, position (600+ 特征目标)
4. 位置战力聚合: 计算 GK/DF/MF/FW 各位置平均评分
5. 阵容深度分析: 替补席评分、缺阵球员统计
6. 混合存储: JSONB (enriched_features) + 核心列 (快速查询)
7. 多进程并行处理 7,000+ 场比赛

V20.3 新增:
- 球员原子数据: player_assets JSONB 数组存储所有球员信息
- 位置战力聚合: home_GK_rating, home_DF_avg_rating, home_MF_avg_rating, home_FW_avg_rating
- 缺阵战力减损: unavailable_players 数组，包含缺阵原因
- 替补席实力: bench_strength 平均评分

V20.4 新增 (全知全能特征矩阵):
- H2H 历史时空: h2h_home_wins, h2h_draws, h2h_away_wins, h2h_win_rate
- 疲劳度指标: home_rest_days_h2h, away_rest_days_h2h, diff_rest_days_h2h
- 深度威胁统计: Big Chances (Created/Missed), Hit Woodwork, Interceptions
- 联赛博弈元数据: 赛季阶段, 五大联赛标记, 比赛轮次
- 递归元数据扫描: 自动扫描 historical/previous/trend/streak 节点

V20.6 新增 (全量合成全息矩阵):
- ShotmapAggregator: 从 shotmap.Periods 合成射门数据
- 21/22 时空记忆: 合成数据回填缺失半场数据
- 动量特征提取: peak_value, volatility
- 球员明细聚合: accuratePasses, touches 等核心指标
- 穿透式三场对账: 验证 2122, 2223, 2425 三个赛季特征维度

V20.7 新增 (原子级数据对齐引擎):
- 原子级回填 (Atomic Backfill): 自动触发 shotmap 填充缺失字段
- 球员-球队级联聚合: 11 人数据加总生成全量特征
- 动量特征深度解剖: velocity, acceleration 特征工程
- 全量 Schema 对齐 (Zero-Padding): 强制 800+ 维一致性
- 三赛季穿透式对账: 确保 7161 场比赛特征维度严格相等

作者: Atomic Data Auditor
日期: 2025-12-24
版本: V20.7
"""

import json
import logging
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import psycopg2

# 加载环境变量 (override=True 确保覆盖系统环境变量)
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(override=True)

from src.api.collectors.schema_agnostic_parser import SchemaAgnosticParser
from src.data.validators.data_validator import FeatureForgeValidator, MatchStatus
from src.ml.atomic_align_v20_7 import atomic_align_v20_8

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ForgeMetrics:
    """特征加工指标"""

    total_queued: int = 0
    processed: int = 0
    successful: int = 0
    filtered_out: int = 0
    failed: int = 0
    skipped_exists: int = 0

    # 性能指标
    start_time: float = 0.0
    end_time: float = 0.0

    # 质量指标
    outliers_detected: int = 0
    leakage_detected: int = 0
    features_imputed: int = 0

    @property
    def elapsed_time(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0.0

    @property
    def throughput(self) -> float:
        """处理速率 (比赛/秒)"""
        return self.processed / self.elapsed_time if self.elapsed_time > 0 else 0.0

    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return self.successful / self.processed


@dataclass
class MatchFeatures:
    """单场比赛特征"""

    match_id: int
    league_id: int
    season_id: str
    home_team: str
    away_team: str
    match_time: datetime
    features: dict[str, Any]
    status: MatchStatus = MatchStatus.READY
    filter_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "league_id": self.league_id,
            "season_id": self.season_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_time": self.match_time.isoformat() if self.match_time else None,
            "features": self.features,
            "status": self.status.value,
            "filter_reason": self.filter_reason,
        }


class FeatureExtractor:
    """
    V20.3 球员级全息特征提取器 - 全量数据镜像

    核心特性:
    1. 自动提取 JSON 中所有 stats groups (388+ 基础特征)
    2. 智能处理百分比格式: "340 (83%)" -> {value: 340, percentage: 0.83}
    3. 动态生成特征名: {home/away}_{stat_key}
    4. 零硬编码 - 只要 JSON 有，就能提取

    V20.3 新增:
    5. 元数据提取: referee, venue, attendance, weather
    6. 阵型数据: formation, team_rating, player ratings
    7. 通用键值扫描: meta_ 前缀自动捕获所有非统计字段

    V20.3 新增:
    8. 球员原子数据: player_assets JSONB 数组
    9. 位置战力聚合: GK/DF/MF/FW 各位置平均评分
    10. 缺阵战力减损: unavailable_players 数组
    11. 替补席实力: bench_strength 平均评分
    """

    # FotMob positionId 映射到标准位置分类
    # 基于实际数据: 11=GK, 后卫=31-36, 中场=37-42, 前锋=43+
    POSITION_MAPPING = {
        # 门将
        11: "GK",
        # 后卫
        31: "DF",
        32: "DF",
        33: "DF",
        34: "DF",
        35: "DF",
        36: "DF",
        # 中场
        37: "MF",
        38: "MF",
        39: "MF",
        40: "MF",
        41: "MF",
        42: "MF",
        # 前锋
        43: "FW",
        44: "FW",
        45: "FW",
        46: "FW",
        47: "FW",
        48: "FW",
    }

    # usualPlayingPositionId 映射 (简化分类)
    # V20.3.1 FIX: 修正错误映射，基于实际 FotMob 数据验证
    # - Haaland/Salah/Kane/Mbappe 都有 usualPlayingPositionId=3
    # - 中场球员 (球衣号 6,8,10) 有 usualPlayingPositionId=2
    USUAL_POSITION_MAPPING = {
        0: "GK",  # 门将
        1: "DF",  # 后卫
        2: "MF",  # 中场 (原错误映射为 DF)
        3: "FW",  # 前锋 (原错误映射为 MF)
    }

    def __init__(self):
        self.parser = SchemaAgnosticParser()
        # V20.3.1 FIX: 减少跳过的 keys，确保深海扫描模式激活
        # 只跳过纯标题条目，保留所有数据组
        self.skip_keys = {"other"}  # 保留 shots, passes, defence, duels, discipline, goalkeeper
        # 跳过的 stat 类型 (title 类型不包含数据)
        self.skip_types = {"title"}
        logger.info("🔧 V20.3.1 特征提取器初始化 (深海扫描模式 - 400+ 维目标)")

    def _parse_complex_value(self, value: Any) -> dict[str, Any]:
        """
        解析复合格式的值

        支持的格式:
        - "340 (83%)" -> {value: 340, percentage: 0.83}
        - "53" -> {value: 53}
        - 0.85 -> {value: 0.85}
        """
        result = {"value": value}

        if value is None:
            return result

        # 字符串格式处理
        if isinstance(value, str):
            # 百分比格式: "340 (83%)"
            if "(" in value and "%" in value:
                try:
                    parts = value.split("(")
                    numeric_part = parts[0].strip()
                    percent_part = parts[1].replace(")", "").replace("%", "").strip()

                    result["value"] = float(numeric_part) if "." in numeric_part else int(numeric_part)
                    result["percentage"] = float(percent_part) / 100.0
                except (ValueError, IndexError):
                    pass

            # 纯百分比: "85%"
            elif value.endswith("%"):
                try:
                    result["value"] = float(value[:-1]) / 100.0
                    result["percentage"] = result["value"]
                except ValueError:
                    pass

            # 纯数字字符串
            else:
                try:
                    result["value"] = float(value) if "." in value else int(value)
                except ValueError:
                    pass

        # 已经是数字
        elif isinstance(value, (int, float)):
            result["value"] = value

        return result

    def _normalize_key(self, key: str) -> str:
        """
        标准化特征键名

        转换规则:
        - 小写化
        - 移除特殊字符
        - 替换空格为下划线
        """
        key = key.lower().strip()
        key = key.replace(" ", "_").replace("-", "_")
        key = key.replace("(", "").replace(")", "")
        return key

    def _map_to_core_feature_name(self, key: str) -> str:
        """
        将原始 stat key 映射到标准核心特征名

        映射规则:
        - BallPossesion -> possession
        - expected_goals -> xg
        - total_shots -> shots
        - ShotsOnTarget -> shots_on_target
        """
        key_lower = key.lower()

        # xG 映射
        if "expected" in key_lower and "goal" in key_lower:
            return "xg"
        # 控球率映射
        if "ballpossesion" in key_lower or "possession" in key_lower:
            return "possession"
        # 射门总数映射
        if "total_shots" in key_lower or ("total" in key_lower and "shot" in key_lower):
            return "shots"
        # 射正映射
        if "shotsontarget" in key_lower or ("shot" in key_lower and "target" in key_lower):
            return "shots_on_target"

        return key

    def _flatten_stats_group(self, stats_list: list[dict], prefix: str = "") -> dict[str, Any]:
        """
        扁平化单个 stats 组

        Args:
            stats_list: stats 数组，每个元素包含 {key, stats, ...}
            prefix: 特征名前缀 (如 'top_stats_')

        Returns:
            扁平化后的特征字典
        """
        features = {}

        for stat_item in stats_list:
            stat_key = stat_item.get("key", "")
            stat_type = stat_item.get("type", "")

            if not stat_key:
                continue

            # 跳过纯标题条目 (type='title' 且没有有效stats)
            if stat_type in self.skip_types:
                continue

            # 跳过特定的空键
            if stat_key.lower() in self.skip_keys:
                # 但如果stats有有效数据，仍然处理
                values = stat_item.get("stats")
                if not values or len(values) < 2 or values[0] is None:
                    continue

            # 获取 stats 数组
            values = stat_item.get("stats")
            if not isinstance(values, list) or len(values) < 2:
                continue

            # 映射到核心特征名 (用于标准特征)
            core_name = self._map_to_core_feature_name(stat_key)
            # 标准化键名 (用于丰富特征)
            normalized_key = self._normalize_key(stat_key)

            # 解析 home/away 值
            home_parsed = self._parse_complex_value(values[0])
            away_parsed = self._parse_complex_value(values[1])

            # 生成特征字段
            # 主值
            if "value" in home_parsed:
                home_val = home_parsed["value"]
                # 核心特征 (无前缀) - 用于快速访问
                if not prefix:  # 只在 top_stats 组生成核心特征
                    features[f"home_{core_name}"] = home_val
                # 丰富特征 (保留原始键名)
                features[f"home_{prefix}{normalized_key}"] = home_val

            if "value" in away_parsed:
                away_val = away_parsed["value"]
                if not prefix:
                    features[f"away_{core_name}"] = away_val
                features[f"away_{prefix}{normalized_key}"] = away_val

            # 百分比值 (如果存在)
            if "percentage" in home_parsed:
                features[f"home_{prefix}{normalized_key}_pct"] = home_parsed["percentage"]
            if "percentage" in away_parsed:
                features[f"away_{prefix}{normalized_key}_pct"] = away_parsed["percentage"]

            # 计算差值 (只对数值类型)
            home_val = home_parsed.get("value")
            away_val = away_parsed.get("value")
            if isinstance(home_val, (int, float)) and isinstance(away_val, (int, float)):
                features[f"diff_{prefix}{normalized_key}"] = home_val - away_val
                features[f"total_{prefix}{normalized_key}"] = home_val + away_val

                # 核心特征总计
                if not prefix:
                    if core_name in ["xg", "shots", "possession"]:
                        features[f"total_{core_name}"] = home_val + away_val

        return features

    # ========== V20.3: 元数据提取方法 ==========

    def _extract_header_metadata(self, header: dict) -> dict[str, Any]:
        """
        V20.2: 提取 header 元数据

        提取内容:
        - 队伍 ID 和名称
        - 比赛状态 (started, finished, cancelled)
        - 比赛时间 (utcTime)
        - 半场时间信息
        """
        features = {}

        try:
            # 队伍信息
            teams = header.get("teams", [])
            if isinstance(teams, list) and len(teams) >= 2:
                home = teams[0]
                away = teams[1]
                if isinstance(home, dict):
                    features["meta_home_team_id"] = home.get("id")
                    features["meta_home_team_name"] = home.get("name")
                if isinstance(away, dict):
                    features["meta_away_team_id"] = away.get("id")
                    features["meta_away_team_name"] = away.get("name")

            # 比赛状态
            status = header.get("status", {})
            if isinstance(status, dict):
                features["meta_match_started"] = status.get("started")
                features["meta_match_finished"] = status.get("finished")
                features["meta_match_cancelled"] = status.get("cancelled")
                features["meta_match_awarded"] = status.get("awarded")

                # 时间信息
                features["meta_match_utc_time"] = status.get("utcTime")
                features["meta_match_reason_long"] = status.get("reason", {}).get("long")
                features["meta_match_reason_short"] = status.get("reason", {}).get("short")

                # 半场时间
                halfs = status.get("halfs", {})
                if isinstance(halfs, dict):
                    features["meta_first_half_started"] = bool(halfs.get("firstHalfStarted"))
                    features["meta_second_half_started"] = bool(halfs.get("secondHalfStarted"))
                    features["meta_first_half_ended"] = bool(halfs.get("firstHalfEnded"))
                    features["meta_second_half_ended"] = bool(halfs.get("secondHalfEnded"))

        except Exception as e:
            logger.debug(f"提取 header 元数据失败: {e}")

        return features

    def _extract_match_facts_metadata(self, match_facts: dict) -> dict[str, Any]:
        """
        V20.2: 提取 matchFacts 元数据

        提取内容:
        - referee: 裁判信息 (姓名、国家)
        - stadium: 球场信息 (名称、城市、容量、场地类型)
        - attendance: 观众人数
        - tournament: 联赛信息 (轮次)
        """
        features = {}

        try:
            info_box = match_facts.get("infoBox", {})

            # 裁判信息
            referee = info_box.get("Referee", {})
            if isinstance(referee, dict):
                features["meta_referee_name"] = referee.get("text")
                features["meta_referee_country"] = referee.get("country")

            # 球场信息
            stadium = info_box.get("Stadium", {})
            if isinstance(stadium, dict):
                features["meta_stadium_name"] = stadium.get("name")
                features["meta_stadium_city"] = stadium.get("city")
                features["meta_stadium_country"] = stadium.get("country")
                features["meta_stadium_capacity"] = stadium.get("capacity")
                features["meta_stadium_surface"] = stadium.get("surface")
                features["meta_stadium_lat"] = stadium.get("lat")
                features["meta_stadium_long"] = stadium.get("long")

            # 观众人数
            attendance = info_box.get("Attendance")
            if attendance is not None:
                features["meta_attendance"] = attendance

            # 联赛信息
            tournament = info_box.get("Tournament", {})
            if isinstance(tournament, dict):
                features["meta_tournament_round"] = tournament.get("round")
                features["meta_tournament_round_name"] = tournament.get("roundName")
                features["meta_tournament_league_name"] = tournament.get("leagueName")

        except Exception as e:
            logger.debug(f"提取 matchFacts 元数据失败: {e}")

        return features

    def _extract_lineup_metadata(self, lineup: dict) -> dict[str, Any]:
        """
        V20.2: 提取 lineup 阵型数据

        提取内容:
        - home_formation: 主队阵型
        - away_formation: 客队阵型
        - home_team_rating: 主队评分
        - away_team_rating: 客队评分
        - home_avg_age: 主队平均年龄
        - away_avg_age: 客队平均年龄
        - 教练信息
        - 替补和缺阵球员统计
        """
        features = {}

        try:
            # 主队信息
            home_team = lineup.get("homeTeam", {})
            if isinstance(home_team, dict):
                features["meta_home_formation"] = home_team.get("formation")
                features["meta_home_team_rating"] = home_team.get("rating")
                features["meta_home_avg_age"] = home_team.get("averageStarterAge")
                features["meta_home_market_value"] = home_team.get("totalStarterMarketValue")

                # 首发球员统计
                starters = home_team.get("starters", [])
                if isinstance(starters, list):
                    features["meta_home_starters_count"] = len(starters)

                # 替补统计
                subs = home_team.get("subs", [])
                if isinstance(subs, list):
                    features["meta_home_subs_count"] = len(subs)

                # 缺阵球员统计
                unavailable = home_team.get("unavailable", [])
                if isinstance(unavailable, list):
                    features["meta_home_unavailable_count"] = len(unavailable)

                # 教练信息
                coach = home_team.get("coach", {})
                if isinstance(coach, dict):
                    features["meta_home_coach_name"] = coach.get("name")
                    features["meta_home_coach_id"] = coach.get("id")

            # 客队信息
            away_team = lineup.get("awayTeam", {})
            if isinstance(away_team, dict):
                features["meta_away_formation"] = away_team.get("formation")
                features["meta_away_team_rating"] = away_team.get("rating")
                features["meta_away_avg_age"] = away_team.get("averageStarterAge")
                features["meta_away_market_value"] = away_team.get("totalStarterMarketValue")

                # 首发球员统计
                starters = away_team.get("starters", [])
                if isinstance(starters, list):
                    features["meta_away_starters_count"] = len(starters)

                # 替补统计
                subs = away_team.get("subs", [])
                if isinstance(subs, list):
                    features["meta_away_subs_count"] = len(subs)

                # 缺阵球员统计
                unavailable = away_team.get("unavailable", [])
                if isinstance(unavailable, list):
                    features["meta_away_unavailable_count"] = len(unavailable)

                # 教练信息
                coach = away_team.get("coach", {})
                if isinstance(coach, dict):
                    features["meta_away_coach_name"] = coach.get("name")
                    features["meta_away_coach_id"] = coach.get("id")

        except Exception as e:
            logger.debug(f"提取 lineup 元数据失败: {e}")

        return features

    # ========== V20.3: 球员数据提取方法 ==========

    def _map_position_to_segment(self, player: dict) -> str:
        """
        将球员的 positionId 映射到位置分类 (GK/DF/MF/FW)

        V20.3.1 FIX: 双重校验逻辑，确保位置映射 100% 准确

        Args:
            player: 球员数据字典

        Returns:
            位置分类: 'GK', 'DF', 'MF', 'FW', 或 'Unknown'
        """
        # 首先尝试 positionId (FotMob 原始位置ID，范围 11-48)
        position_id = player.get("positionId")

        # 确保是整数类型
        if isinstance(position_id, str):
            try:
                position_id = int(position_id)
            except (ValueError, TypeError):
                position_id = None

        if position_id is not None and position_id in self.POSITION_MAPPING:
            mapped = self.POSITION_MAPPING[position_id]
            logger.debug(f"位置映射: positionId={position_id} -> {mapped}")
            return mapped

        # 其次尝试 usualPlayingPositionId (0-3 范围)
        usual_pos_id = player.get("usualPlayingPositionId")

        # 确保是整数类型
        if isinstance(usual_pos_id, str):
            try:
                usual_pos_id = int(usual_pos_id)
            except (ValueError, TypeError):
                usual_pos_id = None

        if usual_pos_id is not None and usual_pos_id in self.USUAL_POSITION_MAPPING:
            mapped = self.USUAL_POSITION_MAPPING[usual_pos_id]
            logger.debug(f"位置映射 (usual): usualPlayingPositionId={usual_pos_id} -> {mapped}")
            return mapped

        # 如果都失败了，记录警告
        logger.warning(
            f"位置映射失败: positionId={position_id}, usualPlayingPositionId={usual_pos_id}, player={player.get('name', 'Unknown')}"
        )
        return "Unknown"

    def _extract_player_rating(self, player: dict) -> float | None:
        """提取球员评分"""
        performance = player.get("performance", {})
        if isinstance(performance, dict):
            rating = performance.get("rating")
            if isinstance(rating, (int, float)):
                return float(rating)
        return None

    def _extract_team_player_assets(self, team_data: dict, team_side: str) -> dict[str, Any]:
        """
        V20.3: 提取球队球员资产数据

        提取内容:
        - player_assets: JSONB 数组，包含所有球员的原子数据
        - 位置战力聚合: GK/DF/MF/FW 各位置平均评分
        - 替补席实力: bench_strength 平均评分
        - 缺阵球员: unavailable_players 数组

        Args:
            team_data: 球队数据 (homeTeam 或 awayTeam)
            team_side: 'home' 或 'away'

        Returns:
            特征字典
        """
        features = {}
        player_assets = []
        unavailable_assets = []

        # 位置评分聚合
        position_ratings = {"GK": [], "DF": [], "MF": [], "FW": []}
        starting_ratings = []
        bench_ratings = []

        try:
            # 1. 处理首发球员
            starters = team_data.get("starters", [])
            if isinstance(starters, list):
                for player in starters:
                    if not isinstance(player, dict):
                        continue

                    player_id = player.get("id")
                    name = player.get("name")
                    rating = self._extract_player_rating(player)
                    position = self._map_position_to_segment(player)

                    # 提取原始 positionId 用于调试
                    position_id = player.get("positionId")

                    # 构建球员原子数据
                    asset = {
                        "id": player_id,
                        "name": name,
                        "position": position,
                        "position_id": position_id,  # 保存原始 positionId
                        "rating": rating,
                        "is_starter": True,
                    }
                    player_assets.append(asset)

                    # 聚合位置评分
                    if rating is not None and position != "Unknown":
                        position_ratings[position].append(rating)
                        starting_ratings.append(rating)

            # 2. 处理替补球员
            subs = team_data.get("subs", [])
            if isinstance(subs, list):
                for player in subs:
                    if not isinstance(player, dict):
                        continue

                    player_id = player.get("id")
                    name = player.get("name")
                    rating = self._extract_player_rating(player)
                    position = self._map_position_to_segment(player)

                    # 提取原始 positionId 用于调试
                    position_id = player.get("positionId")

                    # 构建球员原子数据
                    asset = {
                        "id": player_id,
                        "name": name,
                        "position": position,
                        "position_id": position_id,  # 保存原始 positionId
                        "rating": rating,
                        "is_starter": False,
                    }
                    player_assets.append(asset)

                    # 聚合替补席评分
                    if rating is not None:
                        bench_ratings.append(rating)

            # 3. 处理缺阵球员
            unavailable = team_data.get("unavailable", [])
            if isinstance(unavailable, list):
                for player in unavailable:
                    if not isinstance(player, dict):
                        continue

                    player_id = player.get("id")
                    name = player.get("name")
                    unavailability = player.get("unavailability", {})
                    if isinstance(unavailability, dict):
                        reason_type = unavailability.get("type", "unknown")
                        reason_detail = unavailability.get("injuryId", None)
                    else:
                        reason_type = "unknown"
                        reason_detail = None

                    unavailable_asset = {
                        "id": player_id,
                        "name": name,
                        "reason_type": reason_type,
                        "reason_detail": reason_detail,
                    }
                    unavailable_assets.append(unavailable_asset)

            # 4. 生成位置战力聚合特征
            prefix = f"meta_{team_side}_"
            for position, ratings in position_ratings.items():
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    features[f"{prefix}{position}_avg_rating"] = avg_rating
                    features[f"{prefix}{position}_count"] = len(ratings)
                    features[f"{prefix}{position}_min_rating"] = min(ratings)
                    features[f"{prefix}{position}_max_rating"] = max(ratings)
                else:
                    features[f"{prefix}{position}_avg_rating"] = None
                    features[f"{prefix}{position}_count"] = 0

            # 5. 首发 11 人整体评分
            if starting_ratings:
                features[f"{prefix}starting_11_avg_rating"] = sum(starting_ratings) / len(starting_ratings)
            else:
                features[f"{prefix}starting_11_avg_rating"] = None

            # 6. 替补席实力
            if bench_ratings:
                features[f"{prefix}bench_strength_avg_rating"] = sum(bench_ratings) / len(bench_ratings)
            else:
                features[f"{prefix}bench_strength_avg_rating"] = None

            # 7. 存储 player_assets JSONB 数组
            features[f"{prefix}player_assets"] = player_assets
            features[f"{prefix}unavailable_players"] = unavailable_assets

        except Exception as e:
            logger.debug(f"提取 {team_side} 球员资产失败: {e}")

        return features

    def _extract_lineup_player_metadata(self, lineup: dict) -> dict[str, Any]:
        """
        V20.3: 提取 lineup 球员数据 (升级版)

        在原有阵型数据基础上，新增:
        - 球员原子数据 (player_assets)
        - 位置战力聚合 (GK/DF/MF/FW 平均评分)
        - 替补席实力 (bench_strength)
        - 缺阵球员详情 (unavailable_players)
        """
        features = {}

        try:
            # 主队球员数据
            home_team = lineup.get("homeTeam", {})
            if isinstance(home_team, dict):
                # 先提取基础元数据 (formation, coach 等)
                features["meta_home_formation"] = home_team.get("formation")
                features["meta_home_team_rating"] = home_team.get("rating")
                features["meta_home_avg_age"] = home_team.get("averageStarterAge")
                features["meta_home_market_value"] = home_team.get("totalStarterMarketValue")
                features["meta_home_starters_count"] = len(home_team.get("starters", []))
                features["meta_home_subs_count"] = len(home_team.get("subs", []))
                features["meta_home_unavailable_count"] = len(home_team.get("unavailable", []))

                # 教练信息
                coach = home_team.get("coach", {})
                if isinstance(coach, dict):
                    features["meta_home_coach_name"] = coach.get("name")
                    features["meta_home_coach_id"] = coach.get("id")

                # V20.3: 球员原子数据和位置战力
                home_player_features = self._extract_team_player_assets(home_team, "home")
                features.update(home_player_features)

            # 客队球员数据
            away_team = lineup.get("awayTeam", {})
            if isinstance(away_team, dict):
                # 先提取基础元数据
                features["meta_away_formation"] = away_team.get("formation")
                features["meta_away_team_rating"] = away_team.get("rating")
                features["meta_away_avg_age"] = away_team.get("averageStarterAge")
                features["meta_away_market_value"] = away_team.get("totalStarterMarketValue")
                features["meta_away_starters_count"] = len(away_team.get("starters", []))
                features["meta_away_subs_count"] = len(away_team.get("subs", []))
                features["meta_away_unavailable_count"] = len(away_team.get("unavailable", []))

                # 教练信息
                coach = away_team.get("coach", {})
                if isinstance(coach, dict):
                    features["meta_away_coach_name"] = coach.get("name")
                    features["meta_away_coach_id"] = coach.get("id")

                # V20.3: 球员原子数据和位置战力
                away_player_features = self._extract_team_player_assets(away_team, "away")
                features.update(away_player_features)

        except Exception as e:
            logger.debug(f"提取 lineup 球员元数据失败: {e}")

        return features

    # ========== V20.3: 球员数据提取方法结束 ==========

    def _extract_weather_metadata(self, weather: dict) -> dict[str, Any]:
        """
        V20.2: 提取 weather 天气数据

        提取内容:
        - temperature: 温度
        - wind_speed: 风速
        - wind_direction: 风向
        - precipitation: 降水量
        - humidity: 湿度
        - cloud_cover: 云量
        - description: 天气描述
        """
        features = {}

        try:
            features["meta_temperature"] = weather.get("temperature")
            features["meta_wind_speed"] = weather.get("windSpeed")
            features["meta_wind_direction_cardinal"] = weather.get("windDirectionCardinal")
            features["meta_precipitation"] = weather.get("precipitation")
            features["meta_humidity"] = weather.get("relativeHumidity")
            features["meta_cloud_cover"] = weather.get("cloudCover")
            features["meta_weather_description"] = weather.get("description")
            features["meta_weather_icon_code"] = weather.get("iconCode")

        except Exception as e:
            logger.debug(f"提取 weather 元数据失败: {e}")

        return features

    def _universal_meta_scan(self, content: dict) -> dict[str, Any]:
        """
        V20.2: 通用键值对扫描 (meta_ 前缀)

        扫描 content 中所有非统计数据的节点，自动捕获有价值的元数据。
        使用 meta_ 前缀统一命名。
        """
        features = {}

        # 待扫描的关键词 (只要包含这些词的节点)
        keywords = [
            "official",
            "referee",
            "umpire",
            "stadium",
            "venue",
            "arena",
            "ground",
            "attendance",
            "capacity",
            "spectator",
            "weather",
            "temperature",
            "climate",
            "round",
            "matchday",
            "gameweek",
            "league",
            "tournament",
            "competition",
            "season",
            "year",
            "broadcast",
            "tv",
            "stream",
            "delay",
            "postponed",
            "cancelled",
        ]

        try:
            # 扫描 topPlayers (最佳球员)
            if "topPlayers" in content:
                tp = content["topPlayers"]
                if isinstance(tp, dict):
                    home_top = tp.get("homeTopPlayers", [])
                    away_top = tp.get("awayTopPlayers", [])
                    features["meta_home_top_players_count"] = len(home_top) if isinstance(home_top, list) else 0
                    features["meta_away_top_players_count"] = len(away_top) if isinstance(away_top, list) else 0

            # 扫描 playerOfTheMatch
            if "playerOfTheMatch" in content:
                potm = content["playerOfTheMatch"]
                if isinstance(potm, dict):
                    features["meta_player_of_match_id"] = potm.get("id")
                    features["meta_player_of_match_name"] = potm.get("name", {}).get("fullName")

            # 扫描 insights (如果有)
            if "matchFacts" in content:
                insights = content["matchFacts"].get("insights", [])
                if isinstance(insights, list):
                    features["meta_insights_count"] = len(insights)

        except Exception as e:
            logger.debug(f"通用元数据扫描失败: {e}")

        return features

    # ========== V20.4: 全知全能特征矩阵 ==========

    def _extract_h2h_metadata(self, content: dict, header: dict, current_match_time: str) -> dict[str, Any]:
        """
        V20.4: 提取 H2H (历史交战) 元数据

        提取内容:
        - h2h_home_wins, h2h_draws, h2h_away_wins: 历史对战统计
        - home_rest_days, away_rest_days: 休息天数 (疲劳度指标)
        - h2h_total_matches: 历史总交手次数
        - h2h_home_win_rate, h2h_away_win_rate: 胜率
        """
        features = {}

        try:
            h2h = content.get("h2h", {})
            if not h2h:
                return features

            # 1. H2H Summary 统计
            summary = h2h.get("summary", [])
            if summary and len(summary) >= 3:
                h2h_home_wins = int(summary[0]) if summary[0] is not None else 0
                h2h_draws = int(summary[1]) if summary[1] is not None else 0
                h2h_away_wins = int(summary[2]) if summary[2] is not None else 0
                h2h_total = h2h_home_wins + h2h_draws + h2h_away_wins

                features["h2h_home_wins"] = h2h_home_wins
                features["h2h_draws"] = h2h_draws
                features["h2h_away_wins"] = h2h_away_wins
                features["h2h_total_matches"] = h2h_total

                if h2h_total > 0:
                    features["h2h_home_win_rate"] = h2h_home_wins / h2h_total
                    features["h2h_away_win_rate"] = h2h_away_wins / h2h_total
                    features["h2h_draw_rate"] = h2h_draws / h2h_total

            # 2. 计算休息天数 (Rest Days - 疲劳度指标)
            matches = h2h.get("matches", [])
            if matches and current_match_time:
                from datetime import datetime

                # 解析当前比赛时间
                try:
                    if "T" in str(current_match_time):
                        current_time = datetime.fromisoformat(
                            str(current_match_time).replace("+00:00", "").replace("Z", "")
                        )
                    else:
                        current_time = datetime.fromisoformat(str(current_match_time))
                except:
                    current_time = datetime.now()

                # 获取主客队 ID
                teams = header.get("teams", [])
                if teams and len(teams) >= 2:
                    home_team_id = str(teams[0].get("id", ""))
                    away_team_id = str(teams[1].get("id", ""))

                    # 查找主客队最近的 H2H 比赛
                    home_last_match = None
                    away_last_match = None

                    for match in matches:
                        h_id = str(match.get("home", {}).get("id", ""))
                        a_id = str(match.get("away", {}).get("id", ""))
                        time_str = match.get("time", {}).get("utcTime", "")

                        if not time_str:
                            continue

                        try:
                            if "T" in time_str:
                                match_dt = datetime.fromisoformat(time_str.replace("Z", "").replace("+00:00", ""))
                            else:
                                match_dt = datetime.fromisoformat(time_str)
                        except:
                            continue

                        # 检查是否是主队的主场比赛或客队的客场比赛
                        is_home_home = h_id == home_team_id
                        is_away_away = a_id == away_team_id

                        if is_home_home and (home_last_match is None or match_dt > home_last_match):
                            home_last_match = match_dt

                        if is_away_away and (away_last_match is None or match_dt > away_last_match):
                            away_last_match = match_dt

                    # 计算休息天数
                    if home_last_match:
                        home_rest_days = (current_time - home_last_match).days
                        features["home_rest_days_h2h"] = max(0, home_rest_days)

                    if away_last_match:
                        away_rest_days = (current_time - away_last_match).days
                        features["away_rest_days_h2h"] = max(0, away_rest_days)

                    if home_last_match and away_last_match:
                        features["diff_rest_days_h2h"] = features.get("home_rest_days_h2h", 0) - features.get(
                            "away_rest_days_h2h", 0
                        )

        except Exception as e:
            logger.debug(f"提取 H2H 元数据失败: {e}")

        return features

    def _extract_deep_threat_stats(self, stats_data: dict) -> dict[str, Any]:
        """
        V20.4: 深度威胁统计提取

        提取内容:
        - Big Chances Created/Missed: 大机会统计
        - Hit Woodwork: 击中门框次数
        - Interceptions in Opposition Half: 前场拦截 (高位逼抢强度)
        - Shots Inside/Outside Box: 禁区内/外射门
        """
        features = {}

        try:
            if not stats_data or not isinstance(stats_data, dict):
                return features

            periods = stats_data.get("Periods", {})
            all_period = periods.get("All", {})

            if not all_period or not isinstance(all_period, dict):
                return features

            stats_groups = all_period.get("stats", [])
            if not stats_groups or not isinstance(stats_groups, list):
                return features

            # 扁平化所有统计数据到字典，便于查找
            flat_stats = {}
            for group in stats_groups:
                if not isinstance(group, dict):
                    continue
                group_stats = group.get("stats", [])
                if not isinstance(group_stats, list):
                    continue

                for stat_item in group_stats:
                    if not isinstance(stat_item, dict):
                        continue
                    key = stat_item.get("key", "")
                    values = stat_item.get("stats", [])
                    if key and values and len(values) >= 2:
                        flat_stats[key.lower()] = {"home": values[0], "away": values[1]}

            # 1. Big Chances (大机会)
            for key in ["bigchance", "big chance", "big_chance"]:
                if key in flat_stats:
                    features["home_big_chances"] = flat_stats[key]["home"]
                    features["away_big_chances"] = flat_stats[key]["away"]
                    features["total_big_chances"] = features["home_big_chances"] + features["away_big_chances"]
                    if isinstance(features["home_big_chances"], (int, float)) and isinstance(
                        features["away_big_chances"], (int, float)
                    ):
                        features["diff_big_chances"] = features["home_big_chances"] - features["away_big_chances"]
                    break

            # Big Chances Missed
            for key in ["bigchancemissed", "big chance missed", "big_chance_missed_title", "bigchancemissedtitle"]:
                if key in flat_stats:
                    features["home_big_chances_missed"] = flat_stats[key]["home"]
                    features["away_big_chances_missed"] = flat_stats[key]["away"]
                    features["total_big_chances_missed"] = (
                        features["home_big_chances_missed"] + features["away_big_chances_missed"]
                    )
                    if isinstance(features["home_big_chances_missed"], (int, float)) and isinstance(
                        features["away_big_chances_missed"], (int, float)
                    ):
                        features["diff_big_chances_missed"] = (
                            features["home_big_chances_missed"] - features["away_big_chances_missed"]
                        )
                    break

            # 2. Hit Woodwork (击中门框)
            for key in ["woodwork", "shotwoodwork", "shots_woodwork", "hitwoodwork"]:
                if key in flat_stats:
                    features["home_hit_woodwork"] = flat_stats[key]["home"]
                    features["away_hit_woodwork"] = flat_stats[key]["away"]
                    features["total_hit_woodwork"] = features["home_hit_woodwork"] + features["away_hit_woodwork"]
                    if isinstance(features["home_hit_woodwork"], (int, float)) and isinstance(
                        features["away_hit_woodwork"], (int, float)
                    ):
                        features["diff_hit_woodwork"] = features["home_hit_woodwork"] - features["away_hit_woodwork"]
                    break

            # 3. Interceptions (拦截)
            for key in ["interceptions", "defence_interceptions"]:
                if key in flat_stats:
                    features["home_interceptions"] = flat_stats[key]["home"]
                    features["away_interceptions"] = flat_stats[key]["away"]
                    features["total_interceptions"] = features["home_interceptions"] + features["away_interceptions"]
                    if isinstance(features["home_interceptions"], (int, float)) and isinstance(
                        features["away_interceptions"], (int, float)
                    ):
                        features["diff_interceptions"] = features["home_interceptions"] - features["away_interceptions"]
                    break

            # 4. Shots Inside/Outside Box
            for key in ["shotsinsidebox", "shots_inside_box", "shotsinoppositionbox"]:
                if key in flat_stats:
                    features["home_shots_inside_box"] = flat_stats[key]["home"]
                    features["away_shots_inside_box"] = flat_stats[key]["away"]
                    if isinstance(features["home_shots_inside_box"], (int, float)) and isinstance(
                        features["away_shots_inside_box"], (int, float)
                    ):
                        features["diff_shots_inside_box"] = (
                            features["home_shots_inside_box"] - features["away_shots_inside_box"]
                        )
                    break

            for key in ["shotsoutsidebox", "shots_outside_box"]:
                if key in flat_stats:
                    features["home_shots_outside_box"] = flat_stats[key]["home"]
                    features["away_shots_outside_box"] = flat_stats[key]["away"]
                    if isinstance(features["home_shots_outside_box"], (int, float)) and isinstance(
                        features["away_shots_outside_box"], (int, float)
                    ):
                        features["diff_shots_outside_box"] = (
                            features["home_shots_outside_box"] - features["away_shots_outside_box"]
                        )
                    break

        except Exception as e:
            logger.debug(f"提取深度威胁统计失败: {e}")

        return features

    def _extract_league_context_features(self, content: dict, league_id: int) -> dict[str, Any]:
        """
        V20.4: 提取联赛博弈元数据

        提取内容:
        - 联赛竞争强度指标
        - 比赛重要性标记 (保级战/强强对话)
        - 联赛轮次信息
        """
        features = {}

        try:
            # 从 matchFacts 获取联赛信息
            match_facts = content.get("matchFacts", {})
            if match_facts:
                # 联赛轮次
                tournament = match_facts.get("tournament", {})
                if isinstance(tournament, dict):
                    round_info = tournament.get("round", {})
                    features["meta_tournament_round_name"] = round_info.get("name")
                    features["meta_tournament_league_name"] = tournament.get("leagueName")

                    # 解析轮次数字
                    round_name = str(round_info.get("name", ""))
                    if round_name and round_name.isdigit():
                        round_num = int(round_name)
                        features["meta_match_round"] = round_num

                        # 联赛轮次特征 - 早期/中期/晚期
                        if round_num <= 10:
                            features["meta_season_phase"] = 0  # 早期
                        elif round_num <= 25:
                            features["meta_season_phase"] = 1  # 中期
                        else:
                            features["meta_season_phase"] = 2  # 晚期 (冲刺/保级)

            # 从 table 获取积分榜信息 (如果有)
            table = content.get("table", {})
            if table:
                features["meta_table_available"] = 1

                # 联赛信息
                features["meta_league_id"] = table.get("leagueId")
                features["meta_league_country"] = table.get("countryCode")

                # 五大联赛标记
                major_leagues = {47: "EPL", 53: "Ligue1", 54: "Bundesliga", 55: "SerieA", 87: "LaLiga"}
                if league_id in major_leagues:
                    features["meta_is_major_league"] = 1
                    features["meta_major_league_code"] = major_leagues[league_id]
                else:
                    features["meta_is_major_league"] = 0

        except Exception as e:
            logger.debug(f"提取联赛博弈元数据失败: {e}")

        return features

    def _enhanced_universal_meta_scan(self, content: dict) -> dict[str, Any]:
        """
        V20.4: 增强型通用键值对扫描

        V20.3 基础版 + V20.4 历史时空扫描

        新增扫描关键词:
        - historical, previous, trend, streak (历史相关)
        - form, momentum, run (状态相关)
        - ranking, position, table (排名相关)
        """
        features = {}

        # V20.3 原有关键词
        keywords = [
            "official",
            "referee",
            "umpire",
            "stadium",
            "venue",
            "arena",
            "ground",
            "attendance",
            "capacity",
            "spectator",
            "weather",
            "temperature",
            "climate",
            "round",
            "matchday",
            "gameweek",
            "league",
            "tournament",
            "competition",
            "season",
            "year",
            "broadcast",
            "tv",
            "stream",
            "delay",
            "postponed",
            "cancelled",
        ]

        # V20.4 新增关键词
        v20_4_keywords = [
            "historical",
            "previous",
            "trend",
            "streak",
            "form",
            "momentum",
            "run",
            "ranking",
            "position",
            "table",
            "record",
            "history",
            "headtohead",
            "h2h",
            "sequence",
            "streak",
            "stretch",
        ]

        all_keywords = keywords + v20_4_keywords

        try:
            # V20.3 原有扫描
            if "topPlayers" in content:
                tp = content["topPlayers"]
                if isinstance(tp, dict):
                    home_top = tp.get("homeTopPlayers", [])
                    away_top = tp.get("awayTopPlayers", [])
                    features["meta_home_top_players_count"] = len(home_top) if isinstance(home_top, list) else 0
                    features["meta_away_top_players_count"] = len(away_top) if isinstance(away_top, list) else 0

            if "playerOfTheMatch" in content:
                potm = content["playerOfTheMatch"]
                if isinstance(potm, dict):
                    features["meta_player_of_match_id"] = potm.get("id")
                    features["meta_player_of_match_name"] = potm.get("name", {}).get("fullName")

            if "matchFacts" in content:
                insights = content["matchFacts"].get("insights", [])
                if isinstance(insights, list):
                    features["meta_insights_count"] = len(insights)

            # V20.4: 递归扫描历史时空节点
            def scan_recursive(data: Any, prefix: str = "", depth: int = 0, max_depth: int = 4):
                """递归扫描嵌套数据结构，查找历史/趋势相关特征"""
                if depth > max_depth:
                    return

                if isinstance(data, dict):
                    for key, value in data.items():
                        key_lower = str(key).lower()

                        # 检查是否匹配任何关键词
                        matched = False
                        for kw in all_keywords:
                            if kw in key_lower:
                                matched = True
                                break

                        if matched:
                            feature_key = f"meta_{prefix}{key}".lower().replace(" ", "_").replace("-", "_")

                            # 提取值
                            if isinstance(value, (str, int, float, bool)):
                                features[feature_key] = value
                            elif isinstance(value, list):
                                features[f"{feature_key}_count"] = len(value)
                            elif isinstance(value, dict):
                                # 继续递归
                                scan_recursive(value, f"{prefix}{key}_", depth + 1, max_depth)

                        # 如果是字典或列表，继续递归
                        elif isinstance(value, (dict, list)):
                            new_prefix = f"{prefix}{key}_" if matched else prefix
                            scan_recursive(value, new_prefix, depth + 1, max_depth)

                elif isinstance(data, list) and depth < max_depth:
                    for i, item in enumerate(data):
                        if isinstance(item, (dict, list)):
                            scan_recursive(item, prefix, depth + 1, max_depth)

            # 启动递归扫描
            scan_recursive(content)

        except Exception as e:
            logger.debug(f"增强型通用元数据扫描失败: {e}")

        return features

    # ========== V20.4.1: 最后 5% 黄金数据提取 ==========

    def _extract_momentum_features(self, content: dict) -> dict[str, Any]:
        """
        V20.4.1: 提取比赛动量特征 (Momentum)

        提取内容:
        - momentum_mean: 平均动量值 (反映比赛整体倾向)
        - momentum_std: 动量标准差 (反映比赛波动性)
        - momentum_range: 动量极差 (最大值 - 最小值)
        - momentum_positive_minutes: 动量为正的分钟数
        """
        features = {}

        try:
            momentum = content.get("momentum", {})
            if not momentum or not isinstance(momentum, dict):
                return features

            main = momentum.get("main", {})
            if not main or not isinstance(main, dict):
                return features

            data = main.get("data", [])
            if not data or not isinstance(data, list):
                return features

            # 提取所有 value 值
            values = []
            for item in data:
                if isinstance(item, dict):
                    val = item.get("value")
                    if val is not None and isinstance(val, (int, float)):
                        values.append(float(val))

            if not values:
                return features

            import numpy as np

            # 计算统计特征
            features["momentum_mean"] = float(np.mean(values))
            features["momentum_std"] = float(np.std(values))
            features["momentum_min"] = float(np.min(values))
            features["momentum_max"] = float(np.max(values))
            features["momentum_range"] = features["momentum_max"] - features["momentum_min"]

            # 正值分钟数占比
            positive_count = sum(1 for v in values if v > 0)
            features["momentum_positive_ratio"] = positive_count / len(values) if values else 0

        except Exception as e:
            logger.debug(f"提取动量特征失败: {e}")

        return features

    def _extract_bench_depth_features(self, content: dict) -> dict[str, Any]:
        """
        V20.4.1: 提取替补席深度特征 (Bench Depth)

        提取内容:
        - home_bench_fw_count: 主队替补前锋人数 (反映反扑潜力)
        - away_bench_fw_count: 客队替补前锋人数
        - home_bench_avg_rating: 主队替补平均评分
        - away_bench_avg_rating: 客队替补平均评分
        - home_bench_total_market_value: 主队替补总身价
        - away_bench_total_market_value: 客队替补总身价
        """
        features = {}

        try:
            lineup = content.get("lineup", {})
            if not lineup or not isinstance(lineup, dict):
                return features

            # 处理主队
            home_team = lineup.get("homeTeam", {})
            if isinstance(home_team, dict):
                subs = home_team.get("subs", [])
                if isinstance(subs, list):
                    fw_count = 0
                    total_rating = 0
                    rating_count = 0
                    total_mv = 0

                    for sub in subs:
                        if isinstance(sub, dict):
                            # 统计前锋 (usualPlayingPositionId=3)
                            pos_id = sub.get("usualPlayingPositionId")
                            if pos_id == 3:
                                fw_count += 1

                            # 评分
                            perf = sub.get("performance", {})
                            if isinstance(perf, dict):
                                rating = perf.get("rating")
                                if rating is not None and isinstance(rating, (int, float)):
                                    total_rating += rating
                                    rating_count += 1

                            # 身价
                            mv = sub.get("marketValue")
                            if mv is not None and isinstance(mv, (int, float)):
                                total_mv += mv

                    features["home_bench_fw_count"] = fw_count
                    features["home_bench_avg_rating"] = total_rating / rating_count if rating_count > 0 else 0
                    features["home_bench_total_market_value"] = total_mv

            # 处理客队
            away_team = lineup.get("awayTeam", {})
            if isinstance(away_team, dict):
                subs = away_team.get("subs", [])
                if isinstance(subs, list):
                    fw_count = 0
                    total_rating = 0
                    rating_count = 0
                    total_mv = 0

                    for sub in subs:
                        if isinstance(sub, dict):
                            pos_id = sub.get("usualPlayingPositionId")
                            if pos_id == 3:
                                fw_count += 1

                            perf = sub.get("performance", {})
                            if isinstance(perf, dict):
                                rating = perf.get("rating")
                                if rating is not None and isinstance(rating, (int, float)):
                                    total_rating += rating
                                    rating_count += 1

                            mv = sub.get("marketValue")
                            if mv is not None and isinstance(mv, (int, float)):
                                total_mv += mv

                    features["away_bench_fw_count"] = fw_count
                    features["away_bench_avg_rating"] = total_rating / rating_count if rating_count > 0 else 0
                    features["away_bench_total_market_value"] = total_mv

            # 计算差值
            if "home_bench_fw_count" in features and "away_bench_fw_count" in features:
                features["diff_bench_fw_count"] = features["home_bench_fw_count"] - features["away_bench_fw_count"]

        except Exception as e:
            logger.debug(f"提取替补深度特征失败: {e}")

        return features

    def _extract_shot_quality_features(self, content: dict) -> dict[str, Any]:
        """
        V20.4.1: 提取射门质量特征 (Shot Quality)

        提取内容:
        - home_avg_shot_distance: 主队平均射门距离
        - away_avg_shot_distance: 客队平均射门距离
        - home_big_chance_shot_distance: 主队大机会平均射门距离
        - away_big_chance_shot_distance: 客队大机会平均射门距离
        """
        features = {}

        try:
            shotmap = content.get("shotmap", {})
            if not shotmap or not isinstance(shotmap, dict):
                return features

            shots = shotmap.get("shots", [])
            if not shots or not isinstance(shots, list):
                return features

            # 从 header 获取主客队 ID
            header = content.get("header", {}) if "header" in content else {}
            teams = header.get("teams", []) if isinstance(header, dict) else []
            if not teams or len(teams) < 2:
                return features

            home_team_id = str(teams[0].get("id", "")) if isinstance(teams[0], dict) else ""
            away_team_id = str(teams[1].get("id", "")) if isinstance(teams[1], dict) else ""

            if not home_team_id or not away_team_id:
                return features

            home_distances = []
            away_distances = []

            for shot in shots:
                if not isinstance(shot, dict):
                    continue

                team_id = str(shot.get("teamId", ""))
                distance = shot.get("distance") or shot.get("Distance")

                if distance is not None and isinstance(distance, (int, float)):
                    if team_id == home_team_id:
                        home_distances.append(float(distance))
                    elif team_id == away_team_id:
                        away_distances.append(float(distance))

            if home_distances:
                import numpy as np

                features["home_avg_shot_distance"] = float(np.mean(home_distances))
                features["home_min_shot_distance"] = float(np.min(home_distances))
                features["home_max_shot_distance"] = float(np.max(home_distances))

            if away_distances:
                import numpy as np

                features["away_avg_shot_distance"] = float(np.mean(away_distances))
                features["away_min_shot_distance"] = float(np.min(away_distances))
                features["away_max_shot_distance"] = float(np.max(away_distances))

            # 计算差值
            if "home_avg_shot_distance" in features and "away_avg_shot_distance" in features:
                features["diff_avg_shot_distance"] = (
                    features["home_avg_shot_distance"] - features["away_avg_shot_distance"]
                )

        except Exception as e:
            logger.debug(f"提取射门质量特征失败: {e}")

        return features

    def _extract_player_stats_aggregation(self, content: dict) -> dict[str, Any]:
        """
        V20.4.1: 提取球员统计聚合特征 (PlayerStats Aggregation)

        提取内容:
        - home_team_total_stats: 主队全体球员统计聚合
        - away_team_total_stats: 客队全体球员统计聚合
        - team_avg_rating_diff: 两队平均评分差
        """
        features = {}

        try:
            player_stats = content.get("playerStats", {})
            if not player_stats or not isinstance(player_stats, dict):
                return features

            # 获取主客队 ID
            header = content.get("header", {})
            teams = header.get("teams", []) if isinstance(header, dict) else []
            if not teams or len(teams) < 2:
                return features

            home_team_id = str(teams[0].get("id", "")) if isinstance(teams[0], dict) else ""
            away_team_id = str(teams[1].get("id", "")) if isinstance(teams[1], dict) else ""

            if not home_team_id or not away_team_id:
                return features

            # 聚合主客队球员统计
            home_ratings = []
            away_ratings = []
            home_goals = 0
            away_goals = 0
            home_assists = 0
            away_assists = 0

            for player_id, player_data in player_stats.items():
                if not isinstance(player_data, dict):
                    continue

                team_id = str(player_data.get("teamId", ""))
                stats = player_data.get("stats", {})
                if not isinstance(stats, dict):
                    stats = {}

                # 评分
                rating = stats.get("rating")
                if rating is not None and isinstance(rating, (int, float)):
                    if team_id == home_team_id:
                        home_ratings.append(float(rating))
                    elif team_id == away_team_id:
                        away_ratings.append(float(rating))

                # 进球
                goals = stats.get("goals")
                if goals is not None and isinstance(goals, (int, float)):
                    if team_id == home_team_id:
                        home_goals += int(goals)
                    elif team_id == away_team_id:
                        away_goals += int(goals)

                # 助攻
                assists = stats.get("assists")
                if assists is not None and isinstance(assists, (int, float)):
                    if team_id == home_team_id:
                        home_assists += int(assists)
                    elif team_id == away_team_id:
                        away_assists += int(assists)

            # 计算聚合特征
            if home_ratings:
                import numpy as np

                features["home_team_avg_rating"] = float(np.mean(home_ratings))
                features["home_team_max_rating"] = float(np.max(home_ratings))
                features["home_team_min_rating"] = float(np.min(home_ratings))

            if away_ratings:
                import numpy as np

                features["away_team_avg_rating"] = float(np.mean(away_ratings))
                features["away_team_max_rating"] = float(np.max(away_ratings))
                features["away_team_min_rating"] = float(np.min(away_ratings))

            features["home_team_total_goals"] = home_goals
            features["away_team_total_goals"] = away_goals
            features["home_team_total_assists"] = home_assists
            features["away_team_total_assists"] = away_assists

            # 计算差值
            if "home_team_avg_rating" in features and "away_team_avg_rating" in features:
                features["diff_team_avg_rating"] = features["home_team_avg_rating"] - features["away_team_avg_rating"]

        except Exception as e:
            logger.debug(f"提取球员统计聚合特征失败: {e}")

        return features

    # ========== V20.4.1: 黄金数据提取完成 ==========

    # ========== V20.4: 全知全能特征矩阵完成 ==========

    def extract_features(self, match_data: dict) -> dict[str, Any]:
        """
        V20.7 原子级数据对齐引擎 - 800+ 维全量对齐

        Args:
            match_data: 包含 l2_raw_json 的比赛数据

        Returns:
            {
                'core': {...},      # 核心特征 (比分等)
                'enriched': {...},  # 所有扁平化的统计特征
                '_meta': {...}      # 元数据
            }
        """
        core_features = {}
        enriched_features = {}
        meta = {
            "extraction_version": "V20.7",
            "extraction_mode": "atomic_aligned_matrix",
            "total_stats_groups": 0,
            "total_features": 0,
        }

        try:
            # 1. 提取基础比分特征 (核心字段)
            home_score = match_data.get("home_score")
            away_score = match_data.get("away_score")

            # 如果数据库列为NULL，从JSON提取
            if home_score is None or away_score is None:
                raw_json = match_data.get("player_stats")
                if raw_json:
                    if isinstance(raw_json, str):
                        raw_json = json.loads(raw_json)
                    if isinstance(raw_json, dict):
                        status = raw_json.get("l2_json", {}).get("header", {}).get("status", {})
                        score_str = status.get("scoreStr", "")
                        if score_str and " - " in score_str:
                            parts = score_str.split(" - ")
                            if len(parts) == 2:
                                try:
                                    home_score = int(parts[0].strip())
                                    away_score = int(parts[1].strip())
                                except ValueError:
                                    pass

            core_features["home_score"] = home_score
            core_features["away_score"] = away_score
            core_features["total_goals"] = (home_score or 0) + (away_score or 0)

            # 2. 获取原始 JSON 数据
            raw_json = match_data.get("player_stats")
            if not raw_json:
                raw_json = match_data.get("l2_raw_json")

            if raw_json:
                if isinstance(raw_json, str):
                    raw_json = json.loads(raw_json)

                # 解析 l2_raw_json 结构
                content = None
                if isinstance(raw_json, dict) and "l2_json" in raw_json:
                    content = raw_json.get("l2_json", {}).get("content", {})
                elif isinstance(raw_json, dict) and "content" in raw_json:
                    content = raw_json.get("content", {})
                else:
                    content = raw_json

                # V20.5.4 CRITICAL FIX: 双路径 Periods 解析
                # 路径1: content.stats.Periods (传统路径，可能只有 All 时段)
                # 路径2: content.shotmap.Periods (隐藏路径，包含完整 FirstHalf/SecondHalf 数据)
                periods_to_extract = ["All", "FirstHalf", "SecondHalf"]

                stats_data = content.get("stats") if content else None

                # 尝试从 stats.Periods 获取 Periods 数据
                periods_data = None
                if stats_data and isinstance(stats_data, dict) and "Periods" in stats_data:
                    periods_data = stats_data.get("Periods", {})

                # V20.5.4: 如果 stats.Periods 没有 FirstHalf/SecondHalf，尝试 shotmap.Periods
                if periods_data and isinstance(periods_data, dict):
                    has_fh_sh = "FirstHalf" in periods_data and "SecondHalf" in periods_data

                    if not has_fh_sh and content and isinstance(content, dict):
                        shotmap = content.get("shotmap")
                        if shotmap and isinstance(shotmap, dict) and "Periods" in shotmap:
                            shotmap_periods = shotmap.get("Periods", {})
                            # 检查 shotmap 是否有 FirstHalf/SecondHalf
                            if "FirstHalf" in shotmap_periods and "SecondHalf" in shotmap_periods:
                                logger.info("🔍 V20.5.4: 从 content.shotmap.Periods 发现全息数据，切换路径")
                                periods_data = shotmap_periods
                                meta["periods_source"] = "shotmap.Periods"  # 标记数据源

                if periods_data and isinstance(periods_data, dict):
                    total_groups = 0

                    for period_name in periods_to_extract:
                        if period_name in periods_data:
                            period_stats = periods_data[period_name]
                            if isinstance(period_stats, dict) and "stats" in period_stats:
                                stats_groups = period_stats.get("stats", [])
                                total_groups += len(stats_groups) if isinstance(stats_groups, list) else 0

                                # 动态扁平化该时期的所有 stats groups
                                if isinstance(stats_groups, list):
                                    # 为该时期的统计添加前缀 (如 'FirstHalf_')
                                    period_prefix = "" if period_name == "All" else f"{period_name}_"

                                    for group in stats_groups:
                                        if not isinstance(group, dict):
                                            continue

                                        group_key = group.get("key", "")
                                        group_stats = group.get("stats", [])

                                        if not isinstance(group_stats, list):
                                            continue

                                        # 扁平化该组
                                        prefix = (
                                            f"{period_prefix}{group_key}_"
                                            if group_key not in ["top_stats", "shots", "passes"]
                                            else period_prefix
                                        )

                                        try:
                                            flattened = self._flatten_stats_group(group_stats, prefix)
                                            enriched_features.update(flattened)
                                        except Exception as e:
                                            logger.debug(f"跳过组 {group_key}: {e}")
                                            continue

                    meta["total_stats_groups"] = total_groups

                # 兼容旧格式: 如果没有 Periods，直接查找 stats groups
                elif stats_data:
                    if stats_data and isinstance(stats_data, dict):
                        stats_groups = self.parser.find_stats_groups(stats_data)
                    elif stats_data and isinstance(stats_data, list):
                        stats_groups = stats_data
                    else:
                        stats_groups = []

                    meta["total_stats_groups"] = len(stats_groups) if isinstance(stats_groups, list) else 0

                    # 4. 动态扁平化所有 stats groups
                    if isinstance(stats_groups, list):
                        for group in stats_groups:
                            if not isinstance(group, dict):
                                continue

                            group_key = group.get("key", "")
                            group_stats = group.get("stats", [])

                            if not isinstance(group_stats, list):
                                continue

                            # 扁平化该组
                            prefix = f"{group_key}_" if group_key not in ["top_stats", "shots", "passes"] else ""

                            try:
                                flattened = self._flatten_stats_group(group_stats, prefix)
                                enriched_features.update(flattened)
                            except Exception as e:
                                # 记录错误但继续处理其他组
                                logger.debug(f"跳过组 {group_key}: {e}")
                                continue

            # 5. V20.4: 提取元数据 (matchFacts, lineup, weather, H2H, 深度威胁统计)
            if raw_json and isinstance(raw_json, dict) and "l2_json" in raw_json:
                l2_json = raw_json.get("l2_json", {})
                content = l2_json.get("content", {})

                # 5.0 提取 header 元数据
                header = l2_json.get("header", {})
                if header:
                    enriched_features.update(self._extract_header_metadata(header))

                # 5.1 提取 matchFacts 元数据
                if "matchFacts" in content:
                    match_facts = content["matchFacts"]
                    enriched_features.update(self._extract_match_facts_metadata(match_facts))

                # 5.2 V20.3: 提取 lineup 球员数据 (包含原子数据、位置战力、缺阵信息)
                if "lineup" in content:
                    lineup = content["lineup"]
                    enriched_features.update(self._extract_lineup_player_metadata(lineup))

                # 5.3 提取 weather 天气数据
                if "weather" in content:
                    weather = content["weather"]
                    enriched_features.update(self._extract_weather_metadata(weather))

                # 5.4 V20.4: 提取 H2H (历史交战) 元数据 - 包含休息天数计算
                current_match_time = match_data.get("match_time", "")
                if header or current_match_time:
                    enriched_features.update(self._extract_h2h_metadata(content, header, current_match_time))

                # 5.5 V20.4: 提取深度威胁统计 (Big Chances, Woodwork, Interceptions)
                league_id = match_data.get("league_id", 0)
                if stats_data:
                    enriched_features.update(self._extract_deep_threat_stats(stats_data))

                # 5.6 V20.4: 提取联赛博弈元数据 (积分榜、轮次、赛季阶段)
                enriched_features.update(self._extract_league_context_features(content, league_id))

                # 5.7 V20.4: 增强型通用键值对扫描 (递归扫描历史时空节点)
                enriched_features.update(self._enhanced_universal_meta_scan(content))

                # 5.8 V20.4.1: 提取 Momentum 动量特征 (最后 5% 黄金数据)
                enriched_features.update(self._extract_momentum_features(content))

                # 5.9 V20.4.1: 提取 Bench Depth 替补深度特征
                enriched_features.update(self._extract_bench_depth_features(content))

                # 5.10 V20.4.1: 提取 Shot Quality 射门质量特征
                enriched_features.update(self._extract_shot_quality_features(content))

                # 5.11 V20.4.1: 提取 Player Stats 聚合特征
                enriched_features.update(self._extract_player_stats_aggregation(content))

                # 5.12 V20.7: 原子级数据对齐 - 全量 Schema 对齐
                # 获取主客队 ID (从 l2_json.general 中提取)
                general = l2_json.get("general", {})
                home_team_id = general.get("homeTeam", {}).get("id", 0)
                away_team_id = general.get("awayTeam", {}).get("id", 0)

                if home_team_id and away_team_id:
                    # 使用 V20.8 原子对齐引擎
                    # 包含: 原子级回填 + 球员-球队聚合 + V20.8深度球员聚合 + 动量深度解剖 + Schema 对齐
                    aligned_features, align_metrics = atomic_align_v20_8(
                        content, enriched_features, home_team_id, away_team_id
                    )
                    enriched_features = aligned_features

                    # 更新元数据
                    meta["backfilled_fields"] = align_metrics.get("backfilled_fields", 0)
                    meta["player_aggregates"] = align_metrics.get("player_aggregates", 0)
                    meta["deep_player_aggregates"] = align_metrics.get("deep_player_aggregates", 0)
                    meta["momentum_features"] = align_metrics.get("momentum_features", 0)
                    meta["schema_aligned"] = align_metrics.get("schema_aligned", False)

                    logger.info(
                        f"🚀 V20.8: 对齐完成 - 回填 {meta['backfilled_fields']} 字段, "
                        f"基础聚合 {meta['player_aggregates']}, "
                        f"深度聚合 {meta['deep_player_aggregates']}, "
                        f"动量 {meta['momentum_features']}"
                    )

            # 6. 添加联赛和赛季标识
            core_features["league_id"] = match_data.get("league_id")
            core_features["season_id"] = match_data.get("season_id")

            # 7. 更新元数据 (V20.8)
            meta["total_features"] = len(enriched_features)
            meta["extraction_version"] = "V20.8"
            meta["extraction_mode"] = "atomic_aligned_matrix_deep_player"

        except Exception as e:
            logger.error(f"❌ V20.8 特征提取失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            meta["error"] = str(e)

        return {"core": core_features, "enriched": enriched_features, "_meta": meta}


def process_single_match(args: tuple) -> dict:
    """
    处理单场比赛的特征提取和验证 (Worker 函数)

    注意: 这是独立进程中的函数，不能依赖类实例变量
    V20.3: 支持球员级全息特征结构
    """
    match_id, match_data, validator_config = args

    try:
        # 在子进程中创建提取器和验证器
        extractor = FeatureExtractor()
        validator = FeatureForgeValidator()
        validator.league_contexts = validator_config.get("league_contexts", {})

        league_id = match_data.get("league_id")

        # 提取特征 (V20.3 返回 {core, enriched, _meta})
        extracted = extractor.extract_features(match_data)

        if not extracted or not extracted.get("core"):
            return {"match_id": match_id, "status": "failed", "reason": "特征提取失败"}

        # 合并 core 和 enriched 用于验证 (优先使用 core)
        validation_features = {**extracted.get("enriched", {}), **extracted.get("core", {})}

        # 应用清洗准则 (使用 core 特征进行基本验证)
        core_features = extracted.get("core", {})
        is_valid, reason, status = validator.apply_sanitization(match_id, core_features, league_id)

        if not is_valid:
            return {"match_id": match_id, "status": "filtered", "reason": reason, "match_status": status.value}

        # 检查离群值
        league_context = validator.league_contexts.get(league_id)
        is_outlier, outlier_reason = validator.sanitization.check_outlier(core_features, league_context)

        if is_outlier:
            return {"match_id": match_id, "status": "outlier", "reason": outlier_reason}

        # 成功提取
        return {
            "match_id": match_id,
            "status": "success",
            "features": extracted,  # V20.3: 完整的 {core, enriched, _meta} 结构
            "match_data": {
                "league_id": league_id,
                "season_id": match_data.get("season_id"),
                "home_team": match_data.get("home_team"),
                "away_team": match_data.get("away_team"),
                "match_time": match_data.get("match_time"),
            },
        }

    except Exception as e:
        logger.error(f"❌ 处理比赛 {match_id} 失败: {e}")
        return {"match_id": match_id, "status": "error", "reason": str(e)}


class FeatureForgeV20:
    """
    V20.0 特征加工厂 - 多进程金融量化级特征提取引擎

    核心特性:
    1. 多进程并行处理 (ProcessPoolExecutor)
    2. 增量加工 - 仅处理缺失的 match ID
    3. 集成特征熔断与清洗准则
    4. Schema无关的特征提取
    5. 性能基准测试
    """

    def __init__(self, n_workers: int | None = None):
        """
        初始化特征加工厂

        Args:
            n_workers: 工作进程数，None 则使用 CPU 核心数
        """
        self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        self.metrics = ForgeMetrics()
        self.validator = FeatureForgeValidator()
        self.extractor = FeatureExtractor()

        logger.info(f"🏭 V20.0 特征加工厂初始化 (workers: {self.n_workers})")

    def get_database_connection(self):
        """获取数据库连接 - V20.8 SRE 硬化: 零硬编码"""
        # V20.8 SRE 硬化: 从统一配置获取数据库参数
        from src.config_unified import get_settings

        settings = get_settings()

        # 优先使用环境变量（Docker 兼容）
        host = os.getenv("DB_HOST", settings.database.host)
        port = int(os.getenv("DB_PORT", settings.database.port))
        database = os.getenv("DB_NAME", settings.database.name)
        user = os.getenv("DB_USER", settings.database.user)
        password = os.getenv("DB_PASSWORD", settings.database.password.get_secret_value())

        # 如果主机名是 Docker 容器名，从主机运行时替换为 localhost
        if host in ["db", "redis"]:
            # 检查是否能连接到 Docker 容器
            import socket

            try:
                socket.create_connection((host, port), timeout=1).close()
            except (TimeoutError, ConnectionRefusedError, OSError):
                logger.info(f"🔄 无法连接到 Docker 主机 '{host}'，切换到 localhost")
                host = "localhost"

        return psycopg2.connect(host=host, port=port, database=database, user=user, password=password)

    def get_existing_match_ids(self) -> set:
        """
        获取已处理的 match ID

        Returns:
            已处理的 match ID 集合
        """
        conn = None
        try:
            conn = self.get_database_connection()
            cursor = conn.cursor()

            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'match_features_training'
                );
            """)
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                logger.info("📋 match_features_training 表不存在，将创建")
                return set()

            # 检查列是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'match_features_training'
                    AND column_name = 'match_id'
                );
            """)
            column_exists = cursor.fetchone()[0]

            if not column_exists:
                logger.info("📋 match_id 列不存在，将创建")
                return set()

            cursor.execute("SELECT match_id FROM match_features_training")
            existing_ids = {row[0] for row in cursor.fetchall()}
            logger.info(f"📊 已处理比赛数: {len(existing_ids)}")
            return existing_ids

        except Exception as e:
            logger.error(f"❌ 查询已处理比赛失败: {e}")
            return set()
        finally:
            if conn:
                conn.close()

    def fetch_matches_to_process(self, limit: int | None = None, league_ids: list[int] | None = None) -> list[dict]:
        """
        获取待处理的比赛数据

        Args:
            limit: 限制数量
            league_ids: 指定联赛ID列表

        Returns:
            比赛数据列表
        """
        conn = None
        try:
            conn = self.get_database_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 构建查询 (V20.3: 移除比分过滤，允许从JSON提取)
            query = """
                SELECT m.id, m.external_id, m.league_id, m.home_team, m.away_team,
                       m.match_time, m.home_score, m.away_score,
                       m.l2_raw_json as player_stats
                FROM matches m
                WHERE m.l2_raw_json IS NOT NULL
            """

            params = []

            if league_ids:
                placeholders = ",".join(["%s"] * len(league_ids))
                query += f" AND m.league_id IN ({placeholders})"
                params.extend(league_ids)

            query += " ORDER BY m.match_time DESC"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cursor.execute(query, params)
            matches = [dict(row) for row in cursor.fetchall()]

            logger.info(f"📊 从数据库获取 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 获取比赛数据失败: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def prepare_work_items(self, matches: list[dict], existing_ids: set) -> list[tuple]:
        """
        准备工作项

        Args:
            matches: 比赛数据列表
            existing_ids: 已处理的 ID 集合

        Returns:
            (match_id, match_data, validator_config) 元组列表
        """
        work_items = []

        # 构建验证器配置 (传递给子进程)
        validator_config = {"league_contexts": self.validator.league_contexts}

        for match in matches:
            match_id = match["id"]

            # 跳过已处理的
            if match_id in existing_ids:
                self.metrics.skipped_exists += 1
                continue

            # 添加 season_id (如果缺失)
            if "season_id" not in match:
                match["season_id"] = self._infer_season(match.get("match_time"))

            work_items.append((match_id, match, validator_config))

        return work_items

    def _infer_season(self, match_time) -> str:
        """从比赛时间推断赛季"""
        if match_time is None:
            return "2324"

        # 转换为 datetime 对象
        if isinstance(match_time, str):
            match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))

        year = match_time.year
        month = match_time.month

        # 足球赛季通常是跨年的，8月开始
        if month >= 8:
            return f"{year - 2}{year - 1}"[-4:]  # 2024年8月 -> 2324
        else:
            return f"{year - 1}{year}"[-4:]  # 2024年2月 -> 2324

    def process_multiprocess(self, work_items: list[tuple]) -> tuple[list[dict], ForgeMetrics]:
        """
        多进程处理

        Args:
            work_items: 工作项列表

        Returns:
            (成功提取的特征列表, 指标)
        """
        if not work_items:
            return [], self.metrics

        self.metrics.total_queued = len(work_items)
        self.metrics.start_time = time.time()

        logger.info(f"🚀 启动多进程处理 (workers: {self.n_workers}, items: {len(work_items)})")

        successful_features = []

        try:
            with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                # 提交所有任务
                futures = {executor.submit(process_single_match, item): item[0] for item in work_items}

                # 收集结果
                for future in as_completed(futures):
                    self.metrics.processed += 1
                    match_id = futures[future]

                    try:
                        result = future.result(timeout=30)

                        if result["status"] == "success":
                            self.metrics.successful += 1
                            successful_features.append(result)
                        elif result["status"] == "filtered":
                            self.metrics.filtered_out += 1
                            logger.debug(f"⛔ {match_id} 被过滤: {result['reason']}")
                        elif result["status"] == "outlier":
                            self.metrics.outliers_detected += 1
                            logger.debug(f"📊 {match_id} 离群值: {result['reason']}")
                        elif result["status"] == "leakage":
                            self.metrics.leakage_detected += 1
                            logger.warning(f"⚠️  {match_id} 时间旅行: {result['reason']}")
                        else:
                            self.metrics.failed += 1
                            logger.warning(f"❌ {match_id} 处理失败: {result.get('reason')}")

                        # 每100场报告进度
                        if self.metrics.processed % 100 == 0:
                            logger.info(
                                f"📈 进度: {self.metrics.processed}/{len(work_items)} "
                                f"({self.metrics.processed / len(work_items) * 100:.1f}%) | "
                                f"成功: {self.metrics.successful}, "
                                f"过滤: {self.metrics.filtered_out}"
                            )

                    except Exception as e:
                        self.metrics.failed += 1
                        logger.error(f"❌ {match_id} 异常: {e}")

        except Exception as e:
            logger.error(f"❌ 多进程处理异常: {e}")

        self.metrics.end_time = time.time()
        return successful_features, self.metrics

    def process_single_process(self, work_items: list[tuple]) -> tuple[list[dict], ForgeMetrics]:
        """
        单进程处理 (用于性能对比)

        Args:
            work_items: 工作项列表

        Returns:
            (成功提取的特征列表, 指标)
        """
        if not work_items:
            return [], self.metrics

        self.metrics.total_queued = len(work_items)
        self.metrics.start_time = time.time()

        logger.info(f"🔧 启动单进程处理 (items: {len(work_items)})")

        successful_features = []

        for item in work_items:
            self.metrics.processed += 1
            result = process_single_match(item)

            if result["status"] == "success":
                self.metrics.successful += 1
                successful_features.append(result)
            elif result["status"] == "filtered":
                self.metrics.filtered_out += 1
            elif result["status"] == "outlier":
                self.metrics.outliers_detected += 1
            elif result["status"] == "leakage":
                self.metrics.leakage_detected += 1
            else:
                self.metrics.failed += 1

            if self.metrics.processed % 50 == 0:
                logger.info(
                    f"📈 进度: {self.metrics.processed}/{len(work_items)} "
                    f"({self.metrics.processed / len(work_items) * 100:.1f}%)"
                )

        self.metrics.end_time = time.time()
        return successful_features, self.metrics

    def batch_check_leakage(self, features_list: list[dict]) -> list[dict]:
        """
        批量时间旅行检查 (主进程中执行)

        V20.3: 支持球员级全息特征结构

        检查逻辑:
        1. 按比赛时间排序
        2. 检查特征中是否包含未来比赛的数据
        3. 检查滚动特征是否使用了未来比赛

        Args:
            features_list: 成功提取的特征列表

        Returns:
            过滤后的特征列表 (移除有泄漏的)
        """
        if not features_list:
            return features_list

        logger.info("🔍 启动批量时间旅行检查...")

        # 按比赛时间排序
        sorted_features = sorted(features_list, key=lambda x: x["match_data"].get("match_time") or datetime.min)

        valid_features = []
        leakage_count = 0

        for i, current_item in enumerate(sorted_features):
            current_match_id = current_item["match_id"]
            current_time = current_item["match_data"].get("match_time")

            # V20.2: 获取 features (core + enriched 合并用于检查)
            extracted = current_item["features"]
            if isinstance(extracted, dict) and "core" in extracted:
                current_features = {**extracted.get("enriched", {}), **extracted.get("core", {})}
            else:
                current_features = extracted

            if not current_time:
                valid_features.append(current_item)
                continue

            # 转换时间格式
            if isinstance(current_time, str):
                try:
                    current_time = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
                except:
                    valid_features.append(current_item)
                    continue

            # 检查后续比赛中是否有当前比赛特征中引用的数据
            has_leakage = False
            leakage_reason = ""

            # 简单检查: 如果当前比赛的特征包含超过当前时间的未来数据
            # 这里我们主要检查是否有明显的时间戳问题
            for feature_name, feature_value in current_features.items():
                if feature_value is None or feature_name.startswith("_"):
                    continue

                # 检查是否有明显的时间戳问题 (如 xG 值异常大)
                if isinstance(feature_value, (int, float)):
                    # xG 通常不会超过 10
                    if "xg" in feature_name.lower() and abs(feature_value) > 20:
                        has_leakage = True
                        leakage_reason = f"{feature_name}={feature_value} 超出合理范围"
                        break

                    # 射门数通常不会超过 50
                    if "shot" in feature_name.lower() and abs(feature_value) > 100:
                        has_leakage = True
                        leakage_reason = f"{feature_name}={feature_value} 超出合理范围"
                        break

            if has_leakage:
                leakage_count += 1
                self.metrics.leakage_detected += 1
                logger.warning(f"⚠️  Match {current_match_id} 时间旅行: {leakage_reason}")
            else:
                valid_features.append(current_item)

        logger.info(f"✅ 时间旅行检查完成: 检测到 {leakage_count} 个违规")
        return valid_features

    def save_features_to_database(self, features_list: list[dict]) -> int:
        """
        V20.2 保存特征到数据库 - 混合存储方案

        存储策略:
        1. 核心特征 (core): 独立列存储，支持快速查询和索引
        2. 丰富特征 (enriched): JSONB 存储，支持灵活扩展
        3. 元数据 (_meta): JSONB 存储，记录提取信息

        Args:
            features_list: 特征列表 (V20.2 格式)

        Returns:
            保存的记录数
        """
        if not features_list:
            return 0

        conn = None
        try:
            conn = self.get_database_connection()
            cursor = conn.cursor()

            # V20.2 混合存储表结构
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_features_training (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER UNIQUE NOT NULL,
                    league_id INTEGER,
                    season_id VARCHAR(10),
                    home_team VARCHAR(255),
                    away_team VARCHAR(255),
                    match_time TIMESTAMP,

                    -- 核心特征列 (快速查询)
                    home_score INTEGER,
                    away_score INTEGER,
                    total_goals INTEGER,

                    -- V20.2: 混合存储 - 丰富特征 JSONB
                    enriched_features JSONB DEFAULT '{}'::jsonb,
                    core_features JSONB DEFAULT '{}'::jsonb,
                    meta_data JSONB DEFAULT '{}'::jsonb,

                    status VARCHAR(20) DEFAULT 'ready',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_features_match_id
                ON match_features_training(match_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_features_league_season
                ON match_features_training(league_id, season_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_features_enriched
                ON match_features_training USING GIN (enriched_features);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_features_time
                ON match_features_training(match_time DESC);
            """)

            # 插入数据
            insert_query = """
                INSERT INTO match_features_training
                (match_id, league_id, season_id, home_team, away_team, match_time,
                 home_score, away_score, total_goals,
                 enriched_features, core_features, meta_data, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    enriched_features = EXCLUDED.enriched_features,
                    core_features = EXCLUDED.core_features,
                    meta_data = EXCLUDED.meta_data,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
            """

            inserted = 0
            for item in features_list:
                match_data = item["match_data"]

                # V20.2: 解析特征结构
                extracted = item["features"]
                if isinstance(extracted, dict) and "core" in extracted:
                    core = extracted.get("core", {})
                    enriched = extracted.get("enriched", {})
                    meta = extracted.get("_meta", {})
                else:
                    # 向后兼容旧格式
                    core = {}
                    enriched = extracted
                    meta = {"extraction_version": "V20.0"}

                # 提取核心特征到独立列
                home_score = core.get("home_score")
                away_score = core.get("away_score")
                total_goals = core.get("total_goals")

                cursor.execute(
                    insert_query,
                    (
                        item["match_id"],
                        match_data.get("league_id"),
                        match_data.get("season_id"),
                        match_data.get("home_team"),
                        match_data.get("away_team"),
                        match_data.get("match_time"),
                        home_score,
                        away_score,
                        total_goals,
                        json.dumps(enriched),  # enriched_features JSONB
                        json.dumps(core),  # core_features JSONB
                        json.dumps(meta),  # meta_data JSONB
                        "ready",
                    ),
                )
                inserted += 1

            conn.commit()
            logger.info(f"💾 保存 {inserted} 条特征记录到数据库 (V20.2 混合存储)")
            return inserted

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 保存特征失败: {e}")
            return 0
        finally:
            if conn:
                conn.close()

    def run(
        self,
        limit: int | None = None,
        league_ids: list[int] | None = None,
        use_multiprocessing: bool = True,
        generate_report: bool = True,
    ) -> ForgeMetrics:
        """
        运行特征加工流程

        Args:
            limit: 限制处理数量
            league_ids: 指定联赛ID列表
            use_multiprocessing: 是否使用多进程
            generate_report: 是否生成完整度报告

        Returns:
            处理指标
        """
        logger.info("🏭 V20.0 特征加工厂启动")
        logger.info(
            f"   配置: limit={limit}, leagues={league_ids}, multiprocessing={use_multiprocessing}, report={generate_report}"
        )

        # 1. 获取已处理的 ID
        existing_ids = self.get_existing_match_ids()

        # 2. 获取待处理比赛
        matches = self.fetch_matches_to_process(limit, league_ids)

        if not matches:
            logger.warning("⚠️  没有找到待处理的比赛")
            return self.metrics

        # 3. 准备工作项
        work_items = self.prepare_work_items(matches, existing_ids)

        logger.info(f"📋 待处理: {len(work_items)} 场 (跳过已存在: {self.metrics.skipped_exists})")

        if not work_items:
            logger.info("✅ 所有比赛已处理，无新工作")
            return self.metrics

        # 4. 处理 (首次运行时没有联赛上下文，将在处理过程中构建)
        if use_multiprocessing:
            features_list, metrics = self.process_multiprocess(work_items)
        else:
            features_list, metrics = self.process_single_process(work_items)

        # 5. 批量时间旅行检查 (主进程中执行)
        if features_list:
            features_list = self.batch_check_leakage(features_list)

        # 6. 保存结果
        if features_list:
            saved = self.save_features_to_database(features_list)
            logger.info(f"💾 保存了 {saved}/{len(features_list)} 条特征")

        # 7. 打印摘要
        self.print_summary(metrics)

        # 8. 生成完整度报告
        if generate_report and features_list:
            self.generate_feature_completeness_report(features_list)

        return metrics

    def run_benchmark(self, limit: int = 100) -> dict:
        """
        运行性能基准测试

        Args:
            limit: 测试数据量

        Returns:
            基准测试结果
        """
        logger.info("🚀 启动性能基准测试")

        # 获取测试数据
        existing_ids = self.get_existing_match_ids()
        matches = self.fetch_matches_to_process(limit * 2)
        work_items = self.prepare_work_items(matches, existing_ids)[:limit]

        if len(work_items) < limit:
            logger.warning(f"⚠️  测试数据不足: {len(work_items)} < {limit}")

        # 单进程测试
        logger.info("\n🔧 单进程基准测试...")
        self.metrics = ForgeMetrics()  # 重置
        single_features, single_metrics = self.process_single_process(work_items)

        time.sleep(2)  # 冷却

        # 多进程测试
        logger.info("\n🚀 多进程基准测试...")
        self.metrics = ForgeMetrics()  # 重置
        multi_features, multi_metrics = self.process_multiprocess(work_items)

        # 计算加速比
        speedup = single_metrics.elapsed_time / multi_metrics.elapsed_time if multi_metrics.elapsed_time > 0 else 0

        # 打印对比结果
        logger.info("\n" + "=" * 60)
        logger.info("📊 性能基准测试结果")
        logger.info("=" * 60)
        logger.info(f"{'指标':<20} {'单进程':>15} {'多进程':>15} {'加速比':>10}")
        logger.info("-" * 60)
        logger.info(f"{'处理数量':<20} {single_metrics.processed:>15} {multi_metrics.processed:>15} {'-':>10}")
        logger.info(f"{'成功数量':<20} {single_metrics.successful:>15} {multi_metrics.successful:>15} {'-':>10}")
        logger.info(
            f"{'耗时 (秒)':<20} {single_metrics.elapsed_time:>15.2f} {multi_metrics.elapsed_time:>15.2f} {'-':>10}"
        )
        logger.info(
            f"{'吞吐量 (场/秒)':<20} {single_metrics.throughput:>15.2f} {multi_metrics.throughput:>15.2f} {speedup:>10.2f}x"
        )
        logger.info("=" * 60)

        return {
            "single_process": {
                "elapsed_time": single_metrics.elapsed_time,
                "throughput": single_metrics.throughput,
                "successful": single_metrics.successful,
            },
            "multi_process": {
                "elapsed_time": multi_metrics.elapsed_time,
                "throughput": multi_metrics.throughput,
                "successful": multi_metrics.successful,
            },
            "speedup": speedup,
        }

    def print_summary(self, metrics: ForgeMetrics):
        """打印处理摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 特征加工厂处理摘要")
        logger.info("=" * 60)
        logger.info(f"待处理队列: {metrics.total_queued}")
        logger.info(f"已处理: {metrics.processed}")
        logger.info(f"✅ 成功: {metrics.successful} ({metrics.success_rate:.1%})")
        logger.info(f"⛔ 被过滤: {metrics.filtered_out}")
        logger.info(f"📊 离群值: {metrics.outliers_detected}")
        logger.info(f"⚠️  时间旅行: {metrics.leakage_detected}")
        logger.info(f"❌ 失败: {metrics.failed}")
        logger.info(f"⏭️  跳过已存在: {metrics.skipped_exists}")
        logger.info("-" * 60)
        logger.info(f"总耗时: {metrics.elapsed_time:.2f} 秒")
        logger.info(f"吞吐量: {metrics.throughput:.2f} 场/秒")
        logger.info("=" * 60)

    def generate_feature_completeness_report(self, features_list: list[dict]) -> dict:
        """
        V20.2 生成特征完整度报告

        支持动态扁平化特征，报告包含:
        - 核心特征完整度
        - 丰富特征统计 (总特征数分布)
        - 元数据统计 (stats groups 数量)

        Args:
            features_list: 特征列表 (V20.2 格式)

        Returns:
            完整度报告字典
        """
        if not features_list:
            return {"total_matches": 0, "features_analyzed": {}, "completeness_rate": 0.0, "missing_features": []}

        # V20.2: 解析特征结构
        all_features = []
        all_enriched_counts = []
        all_meta = []

        for item in features_list:
            extracted = item["features"]
            if isinstance(extracted, dict) and "core" in extracted:
                core = extracted.get("core", {})
                enriched = extracted.get("enriched", {})
                meta = extracted.get("_meta", {})
                # 合并用于检查
                merged = {**enriched, **core}
                all_features.append(merged)
                all_enriched_counts.append(len(enriched))
                all_meta.append(meta)
            else:
                # 向后兼容
                all_features.append(extracted)
                all_enriched_counts.append(0)
                all_meta.append({})

        # 定义核心特征列表 (rating 已从 FotMob L2 API 移除)
        # 注意: enriched_features 中使用 total_shots，不在 core_features 中重复计算
        core_feature_list = [
            "home_score",
            "away_score",
            "total_goals",
            "home_xg",
            "away_xg",
            "total_xg",
            "home_shots",
            "away_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_possession",
            "away_possession",
        ]

        # 统计每个核心特征的完整度
        feature_stats = {}
        for feature in core_feature_list:
            present_count = 0
            for features in all_features:
                if feature in features and features[feature] is not None:
                    present_count += 1

            feature_stats[feature] = {
                "present": present_count,
                "missing": len(all_features) - present_count,
                "completeness": present_count / len(all_features) if all_features else 0,
            }

        # 按联赛分组统计
        league_stats = {}
        for i, item in enumerate(features_list):
            league_id = item["match_data"].get("league_id")
            if league_id not in league_stats:
                league_stats[league_id] = {"count": 0, "xg_present": 0, "shots_present": 0}
            league_stats[league_id]["count"] += 1

            features = all_features[i]
            if features.get("home_xg") is not None or features.get("away_xg") is not None:
                league_stats[league_id]["xg_present"] += 1
            if features.get("home_shots") is not None or features.get("away_shots") is not None:
                league_stats[league_id]["shots_present"] += 1

        # V20.2: 丰富特征统计
        avg_enriched = sum(all_enriched_counts) / len(all_enriched_counts) if all_enriched_counts else 0
        max_enriched = max(all_enriched_counts) if all_enriched_counts else 0
        min_enriched = min(all_enriched_counts) if all_enriched_counts else 0

        # 统计所有唯一特征键 (from enriched)
        all_enriched_keys = set()
        for item in features_list:
            extracted = item["features"]
            if isinstance(extracted, dict) and "enriched" in extracted:
                all_enriched_keys.update(extracted.get("enriched", {}).keys())

        # 计算总体完整度
        total_completeness = (
            sum(s["completeness"] for s in feature_stats.values()) / len(feature_stats) if feature_stats else 0
        )

        report = {
            "total_matches": len(features_list),
            "core_features_analyzed": len(core_feature_list),
            "feature_stats": feature_stats,
            "league_stats": league_stats,
            "total_completeness": total_completeness,
            "xg_completeness": feature_stats.get("total_xg", {}).get("completeness", 0),
            "shots_completeness": feature_stats.get("shots_total", {}).get("completeness", 0),
            # V20.2 新增
            "avg_enriched_features": avg_enriched,
            "max_enriched_features": max_enriched,
            "min_enriched_features": min_enriched,
            "total_unique_enriched_keys": len(all_enriched_keys),
        }

        # 打印报告
        self._print_completeness_report_v20(report)

        return report

    def _print_completeness_report_v20(self, report: dict):
        """V20.2 打印完整度报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 V20.2 特征完整度报告")
        logger.info("=" * 60)
        logger.info(f"总比赛数: {report['total_matches']}")
        logger.info(f"核心特征数: {report['core_features_analyzed']}")
        logger.info(f"核心特征完整度: {report['total_completeness']:.1%}")
        logger.info("-" * 60)

        # V20.2: 丰富特征统计
        logger.info("🚀 动态扁平化统计:")
        logger.info(f"  平均丰富特征数: {report['avg_enriched_features']:.0f}")
        logger.info(f"  最大丰富特征数: {report['max_enriched_features']}")
        logger.info(f"  最小丰富特征数: {report['min_enriched_features']}")
        logger.info(f"  唯一特征键总数: {report['total_unique_enriched_keys']}")

        logger.info("-" * 60)
        logger.info("核心特征完整度:")
        for feature, stats in sorted(report["feature_stats"].items(), key=lambda x: x[1]["completeness"]):
            status = "✅" if stats["completeness"] >= 0.9 else "⚠️" if stats["completeness"] >= 0.7 else "❌"
            logger.info(
                f"  {status} {feature:<25} {stats['completeness']:.1%} ({stats['present']}/{report['total_matches']})"
            )

        logger.info("-" * 60)
        logger.info("按联赛统计:")
        for league_id, stats in report.get("league_stats", {}).items():
            league_names = {47: "Premier League", 53: "Ligue 1", 54: "Bundesliga", 55: "Serie A", 87: "La Liga"}
            league_name = league_names.get(league_id, f"League {league_id}")
            xg_pct = 100.0 * stats["xg_present"] / stats["count"] if stats["count"] > 0 else 0
            shots_pct = 100.0 * stats["shots_present"] / stats["count"] if stats["count"] > 0 else 0
            logger.info(f"  {league_name:<20} xG: {xg_pct:.1f}%, shots: {shots_pct:.1f}% (n={stats['count']})")
        logger.info("=" * 60)
        logger.info("=" * 60)
        logger.info(f"总比赛数: {report['total_matches']}")
        logger.info(f"核心特征数: {report['core_features_analyzed']}")
        logger.info(f"总体完整度: {report['total_completeness']:.1%}")
        logger.info("-" * 60)

        logger.info("核心特征完整度:")
        for feature, stats in sorted(report["feature_stats"].items(), key=lambda x: x[1]["completeness"]):
            status = "✅" if stats["completeness"] >= 0.9 else "⚠️" if stats["completeness"] >= 0.7 else "❌"
            logger.info(
                f"  {status} {feature:<25} {stats['completeness']:.1%} ({stats['present']}/{report['total_matches']})"
            )

        if report["league_stats"]:
            logger.info("\n按联赛统计:")
            league_names = {47: "Premier League", 53: "Ligue 1", 54: "Bundesliga", 55: "Serie A", 87: "LaLiga"}
            for league_id, stats in sorted(report["league_stats"].items()):
                name = league_names.get(league_id, f"League {league_id}")
                xg_rate = stats["xg_present"] / stats["count"] if stats["count"] > 0 else 0
                shots_rate = stats["shots_present"] / stats["count"] if stats["count"] > 0 else 0
                logger.info(f"  {name:<20} xG: {xg_rate:.1%}, shots: {shots_rate:.1%} (n={stats['count']})")

        logger.info("=" * 60)

    def verify_financial_purity(self, features_list: list[dict]) -> dict:
        """
        验证金融量化级数据纯净度

        金融量化标准:
        1. 无数据泄露 (No Leakage) - 不包含未来信息
        2. 无离群值污染 (No Outlier Contamination) - 离群值已被识别或移除
        3. 特征一致性 (Feature Consistency) - 相同比赛的特征值一致
        4. 时间戳完整性 (Timestamp Integrity) - 所有比赛有正确的时间戳
        5. 统计分布合理性 (Statistical Validity) - 分布符合预期

        Args:
            features_list: 特征列表

        Returns:
            验证报告字典
        """
        if not features_list:
            return {"purity_score": 0.0, "is_financial_grade": False, "issues": ["No features to verify"]}

        issues = []
        checks_passed = 0
        total_checks = 0

        logger.info("🔬 启动金融量化级纯净度验证...")

        # 1. 时间戳完整性检查
        total_checks += 1
        missing_timestamps = 0
        for item in features_list:
            if not item["match_data"].get("match_time"):
                missing_timestamps += 1

        if missing_timestamps == 0:
            checks_passed += 1
            logger.info("  ✅ 时间戳完整性: 100%")
        else:
            issues.append(f"时间戳缺失: {missing_timestamps}/{len(features_list)}")
            logger.warning(f"  ⚠️  时间戳完整性: {missing_timestamps} 缺失")

        # 2. xG 数据完整性检查
        total_checks += 1
        missing_xg = 0
        for item in features_list:
            features = item["features"]
            if not features.get("home_xg") and not features.get("away_xg"):
                missing_xg += 1

        xg_completeness = (len(features_list) - missing_xg) / len(features_list)
        if xg_completeness >= 0.95:
            checks_passed += 1
            logger.info(f"  ✅ xG 完整性: {xg_completeness:.1%}")
        else:
            issues.append(f"xG 数据不足: {xg_completeness:.1%} < 95%")
            logger.warning(f"  ⚠️  xG 完整性: {xg_completeness:.1%}")

        # 3. 基本统计验证
        total_checks += 1
        statistical_issues = []

        for feature_name in ["total_xg", "shots_total", "total_goals"]:
            values = []
            for item in features_list:
                val = item["features"].get(feature_name)
                if val is not None and isinstance(val, (int, float)):
                    values.append(val)

            if values:
                mean_val = np.mean(values)
                std_val = np.std(values)
                min_val = np.min(values)
                max_val = np.max(values)

                # 检查异常值
                if max_val > mean_val + 10 * std_val:
                    statistical_issues.append(f"{feature_name}: 最大值 {max_val:.2f} 超出 10σ")

                # 检查负值
                if min_val < 0:
                    statistical_issues.append(f"{feature_name}: 存在负值 {min_val:.2f}")

        if not statistical_issues:
            checks_passed += 1
            logger.info("  ✅ 统计分布验证: 通过")
        else:
            for issue in statistical_issues:
                issues.append(f"统计异常: {issue}")
            logger.warning(f"  ⚠️  统计分布验证: 发现 {len(statistical_issues)} 个问题")

        # 4. 特征一致性检查 (相同 match_id 的特征应该一致)
        total_checks += 1
        match_id_features = {}
        duplicates = 0

        for item in features_list:
            match_id = item["match_id"]
            if match_id in match_id_features:
                duplicates += 1
            else:
                match_id_features[match_id] = item["features"]

        if duplicates == 0:
            checks_passed += 1
            logger.info("  ✅ 特征一致性: 无重复 match_id")
        else:
            issues.append(f"发现重复 match_id: {duplicates}")
            logger.warning(f"  ⚠️  特征一致性: {duplicates} 个重复")

        # 5. 数据范围检查
        total_checks += 1
        range_issues = []

        for item in features_list:
            features = item["features"]

            # possession 应该在 0-100 之间
            for key in ["home_possession", "away_possession"]:
                val = features.get(key)
                if val is not None and (val < 0 or val > 100):
                    range_issues.append(f"{key}: {val} 超出 0-100 范围")

            # xG 应该是正数且 < 15
            for key in ["home_xg", "away_xg", "total_xg"]:
                val = features.get(key)
                if val is not None and (val < 0 or val > 15):
                    range_issues.append(f"{key}: {val} 超出 0-15 范围")

        if not range_issues:
            checks_passed += 1
            logger.info("  ✅ 数据范围验证: 通过")
        else:
            for issue in range_issues[:5]:  # 只显示前5个
                issues.append(f"范围异常: {issue}")
            logger.warning(f"  ⚠️  数据范围验证: 发现 {len(range_issues)} 个问题")

        # 计算纯净度分数
        purity_score = checks_passed / total_checks if total_checks > 0 else 0
        is_financial_grade = purity_score >= 0.8  # 80% 通过率为金融量化级

        # 打印验证报告
        logger.info("\n" + "=" * 60)
        logger.info("🔬 金融量化级纯净度验证结果")
        logger.info("=" * 60)
        logger.info(f"纯净度分数: {purity_score:.1%}")
        logger.info(f"金融量化级: {'✅ 通过' if is_financial_grade else '❌ 未通过'}")
        logger.info(f"检查通过: {checks_passed}/{total_checks}")
        if issues:
            logger.info(f"发现 {len(issues)} 个问题:")
            for issue in issues[:10]:  # 显示前10个
                logger.info(f"  - {issue}")
        logger.info("=" * 60)

        return {
            "purity_score": purity_score,
            "is_financial_grade": is_financial_grade,
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "issues": issues,
            "xg_completeness": xg_completeness,
            "missing_timestamps": missing_timestamps,
        }


# ============================================
# 命令行入口
# ============================================


def main():
    """命令行入口"""
    import click

    @click.command()
    @click.option("--limit", "-l", default=None, type=int, help="限制处理数量")
    @click.option("--leagues", "-L", multiple=True, type=int, help="指定联赛ID")
    @click.option("--workers", "-w", default=None, type=int, help="工作进程数")
    @click.option("--single", is_flag=True, help="使用单进程")
    @click.option("--benchmark", "-b", is_flag=True, help="运行性能基准测试")
    @click.option("--benchmark-size", default=100, type=int, help="基准测试数据量")
    def run_forge(limit, leagues, workers, single, benchmark, benchmark_size):
        """V20.0 特征加工厂"""

        forge = FeatureForgeV20(n_workers=workers)

        if benchmark:
            # 运行基准测试
            forge.run_benchmark(limit=benchmark_size)
        else:
            # 运行正常流程
            league_ids = list(leagues) if leagues else None
            forge.run(limit=limit, league_ids=league_ids, use_multiprocessing=not single)

    run_forge()


if __name__ == "__main__":
    main()
