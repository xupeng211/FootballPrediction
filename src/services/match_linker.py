"""
V41.232 MatchLinker - 数据合龙桥接服务（防弹级增强版）
==========================================================

核心功能：
    - 基于队名相似度的比赛关联
    - 基于时间窗口的匹配过滤
    - PostgreSQL 数据库映射
    - 矩阵数据持久化

V41.232 数据合龙优化：
    - 相似度阈值灵活化：0.85 → 0.75
    - 队名缩写预处理：Man City, Man Utd 等常见缩写自动映射
    - 增强标准化算法：支持更多欧洲俱乐部命名规范

架构说明：
    - 从提取的 PriceVector 映射到 match_odds_intelligence 表
    - 支持模糊匹配和跨数据源关联
    - 完整的审计日志追踪

Usage:
    from src.services.match_linker import MatchLinker, LinkerConfig

    config = LinkerConfig(time_window_hours=48, similarity_threshold=0.75)
    linker = MatchLinker(config)
    result = await linker.link_and_store(vector_data)

Author: V41.232 Engineering Team
Date: 2026-01-19
Version: V41.232 "Bulletproof Finalization"
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_config

logger = logging.getLogger("MatchLinker")


# =============================================================================
# 数据模型 (Data Models)
# =============================================================================


@dataclass
class MatchCandidate:
    """比赛候选匹配"""
    match_id: str
    home_team: str
    away_team: str
    match_time: datetime
    similarity_score: float
    time_diff_hours: float


@dataclass
class LinkResult:
    """关联结果"""
    vector_id: int
    matched_match_id: str | None
    similarity_score: float
    time_diff_hours: float
    link_method: str  # "exact", "fuzzy", "time_window"
    stored: bool = False


@dataclass
class LinkerConfig:
    """关联器配置 - V41.232 优化"""
    time_window_hours: float = 48.0  # 时间窗口（小时）
    similarity_threshold: float = 0.75  # V41.232: 灵活相似度阈值（0.85 → 0.75）
    max_candidates: int = 10  # 最大候选数
    enable_fuzzy_match: bool = True  # 启用模糊匹配
    enable_abbreviation_expansion: bool = True  # V41.232: 启用缩写扩展

    # 数据库表配置
    matches_table: str = "matches"
    odds_table: str = "match_odds_intelligence"


# =============================================================================
# MatchLinker 核心服务
# =============================================================================


class MatchLinker:
    """
    V41.232 数据合龙桥接器（防弹级增强版）

    核心算法：
    1. 队名相似度匹配（Levenshtein 距离）
    2. 时间窗口过滤
    3. 多候选评分排序
    4. V41.232: 队名缩写预处理映射
    """

    # V41.232: 队名缩写映射表
    # 支持常见英文缩写和欧洲俱乐部命名规范
    ABBREVIATION_MAP = {
        # 英超缩写
        "man city": "manchester city",
        "manchester city": "manchester city",
        "man utd": "manchester united",
        "man united": "manchester united",
        "manchester united": "manchester united",
        "spurs": "tottenham",
        "tottenham": "tottenham hotspur",
        "tottenham hotspur": "tottenham hotspur",
        "wolves": "wolverhampton wanderers",
        "wolves": "wolverhampton",
        "wolverhampton": "wolverhampton wanderers",
        "wolverhampton wanderers": "wolverhampton wanderers",
        "foxes": "leicester city",
        "leicester": "leicester city",
        "leicester city": "leicester city",
        "the hammers": "west ham united",
        "west ham": "west ham united",
        "west ham united": "west ham united",
        "brighton": "brighton hove albion",
        "brighton hove albion": "brighton hove albion",
        "newcastle": "newcastle united",
        "newcastle united": "newcastle united",
        "nottingham forest": "nottingham forest",
        "nottm forest": "nottingham forest",
        # 西甲缩写
        "real madrid": "real madrid",
        "barca": "barcelona",
        "barcelona": "barcelona",
        "atleti": "atletico madrid",
        "atletico madrid": "atletico madrid",
        "ath bilbao": "athletic bilbao",
        "athletic bilbao": "athletic bilbao",
        "real betis": "real betis",
        "betis": "real betis",
        "real sociedad": "real sociedad",
        "sociedad": "real sociedad",
        "valencia": "valencia cf",
        "valencia cf": "valencia cf",
        "sevilla": "sevilla fc",
        "sevilla fc": "sevilla fc",
        "villarreal": "villarreal cf",
        "villarreal cf": "villarreal cf",
        # 意甲缩写
        "juve": "juventus",
        "juventus": "juventus",
        "inter": "inter milan",
        "inter milan": "inter milan",
        "milan": "ac milan",
        "ac milan": "ac milan",
        "napoli": "ssc napoli",
        "ssc napoli": "ssc napoli",
        "roma": "as roma",
        "as roma": "as roma",
        "lazio": "lazio roma",
        "lazio roma": "lazio roma",
        # 德甲缩写
        "bayern": "bayern munich",
        "bayern munich": "bayern munich",
        "dortmund": "borussia dortmund",
        "borussia dortmund": "borussia dortmund",
        "leverkusen": "bayer leverkusen",
        "bayer leverkusen": "bayer leverkusen",
        "frankfurt": "eintracht frankfurt",
        "eintracht frankfurt": "eintracht frankfurt",
        "mgladbach": "borussia monchengladbach",
        "borussia monchengladbach": "borussia monchengladbach",
        # 法甲缩写
        "psg": "paris saint germain",
        "paris saint germain": "paris saint germain",
        "monaco": "as monaco",
        "as monaco": "as monaco",
        "lyon": "olympique lyonnais",
        "olympique lyonnais": "olympique lyonnais",
        "marseille": "olympique marseille",
        "olympique marseille": "olympique marseille",
        "lille": "losc lille",
        "losc lille": "losc lille",
    }

    def __init__(self, config: LinkerConfig):
        self.config = config
        self.unified_config = get_config()
        self._db_conn = None

    def _get_connection(self):
        """获取数据库连接"""
        if self._db_conn is None:
            self._db_conn = psycopg2.connect(
                host=self.unified_config.database.host,
                database=self.unified_config.database.name,
                user=self.unified_config.database.user,
                password=self.unified_config.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._db_conn

    def close(self):
        """关闭数据库连接"""
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度

        使用 SequenceMatcher (基于 Ratcliff/Obershelp 算法)
        返回 0-1 之间的浮点数
        """
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def normalize_team_name(self, name: str) -> str:
        """
        V41.232 标准化队名（增强版）

        处理：
        1. 缩写扩展（Man City → Manchester City）
        2. 转小写
        3. 移除常见后缀 (FC, United, City 等)
        4. 移除多余空格
        5. 移除特殊字符
        """
        # 步骤 1: 缩写扩展（V41.232 新增）
        if self.config.enable_abbreviation_expansion:
            name_lower = name.lower().strip()
            # 查找映射表
            if name_lower in self.ABBREVIATION_MAP:
                name = self.ABBREVIATION_MAP[name_lower]
                logger.debug(f"Abbiation expanded: '{name_lower}' → '{name}'")

        # 步骤 2: 转小写并去除首尾空格
        normalized = name.lower().strip()

        # 步骤 3: 移除特殊字符
        import re
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # 步骤 4: 移除后缀（扩展列表）
        suffixes = [
            "fc", "fc ", "united", "city", "town", "athletic", "afc", "rc",
            "cf", "ac", "ssc", "as", "bc", "losc", "hove albion",
            "hotspur", "wanderers", " Rangers", "celtic", "dynamo",
            "fenerbahce", "galatasaray", "besiktas", "olympique",
            "saint germain", "etienne", "lens", "rennes", "reims",
        ]

        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        # 步骤 5: 压缩多余空格
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def find_candidates(
        self,
        home_team: str,
        away_team: str,
        match_time: datetime,
    ) -> list[MatchCandidate]:
        """
        查找匹配候选

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_time: 比赛时间

        Returns:
            候选比赛列表（按相似度降序）
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 时间窗口
        time_start = match_time - timedelta(hours=self.config.time_window_hours)
        time_end = match_time + timedelta(hours=self.config.time_window_hours)

        # 查询候选（V41.234: 使用 match_date 替代 match_time）
        query = """
            SELECT match_id, home_team, away_team, match_date
            FROM matches
            WHERE match_date BETWEEN %s AND %s
            ORDER BY match_date
            LIMIT %s
        """

        cursor.execute(query, (time_start, time_end, self.config.max_candidates * 2))
        rows = cursor.fetchall()

        candidates = []

        for row in rows:
            # 计算相似度
            home_sim = self.calculate_similarity(home_team, row["home_team"])
            away_sim = self.calculate_similarity(away_team, row["away_team"])

            # 综合相似度（平均）
            avg_similarity = (home_sim + away_sim) / 2

            # 时间差（V41.234: 使用 match_date）
            time_diff = abs((row["match_date"] - match_time).total_seconds() / 3600)

            candidate = MatchCandidate(
                match_id=row["match_id"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                match_time=row["match_date"],  # V41.234: 使用 match_date
                similarity_score=avg_similarity,
                time_diff_hours=time_diff,
            )

            candidates.append(candidate)

        # 按相似度降序排序
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)

        # 限制候选数量
        return candidates[: self.config.max_candidates]

    def select_best_match(
        self,
        candidates: list[MatchCandidate],
    ) -> MatchCandidate | None:
        """
        选择最佳匹配

        选择逻辑：
        1. 相似度超过阈值
        2. 选择相似度最高的
        """
        if not candidates:
            return None

        # 过滤低相似度候选
        qualified = [
            c
            for c in candidates
            if c.similarity_score >= self.config.similarity_threshold
        ]

        if not qualified:
            return None

        # 返回相似度最高的
        return qualified[0]

    def store_odds_intelligence(
        self,
        match_id: str,
        initial_price: list[float],
        closing_price: list[float],
        movement_history: list[float],
        metadata: dict[str, Any] | None = None,
        similarity_score: float | None = None,
        link_method: str | None = None,
    ) -> bool:
        """
        存储赔率情报到数据库

        Args:
            match_id: 比赛 ID
            initial_price: 初始价格
            closing_price: 当前价格
            movement_history: 变动历史
            metadata: 额外元数据
            similarity_score: V41.234: 相似度分数
            link_method: V41.234: 匹配方法 (exact/fuzzy/none)

        Returns:
            是否存储成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'match_odds_intelligence'
                )
            """)

            if not cursor.fetchone()["exists"]:
                # 创建表
                cursor.execute("""
                    CREATE TABLE match_odds_intelligence (
                        id SERIAL PRIMARY KEY,
                        match_id VARCHAR(50) REFERENCES matches(match_id),
                        initial_price JSONB,
                        closing_price JSONB,
                        movement_history JSONB,
                        quality_rating VARCHAR(20),
                        deviation_percentage FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("Created table: match_odds_intelligence")

            # V41.234: 转换为 JSON 字符串 (Python list → JSONB)
            # V41.234: 添加相似度和链接方法字段
            quality_rating = metadata.get("Quality_Rating") if metadata else None
            deviation_pct = metadata.get("Deviation_Percentage") if metadata else None

            cursor.execute("""
                INSERT INTO match_odds_intelligence
                (match_id, initial_price, closing_price, movement_history,
                 quality_rating, deviation_percentage, similarity_score, link_method,
                 created_at, updated_at)
                VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (match_id)
                DO UPDATE SET
                    initial_price = EXCLUDED.initial_price,
                    closing_price = EXCLUDED.closing_price,
                    movement_history = EXCLUDED.movement_history,
                    quality_rating = EXCLUDED.quality_rating,
                    deviation_percentage = EXCLUDED.deviation_percentage,
                    similarity_score = EXCLUDED.similarity_score,
                    link_method = EXCLUDED.link_method,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                match_id,
                json.dumps(initial_price),
                json.dumps(closing_price),
                json.dumps(movement_history),
                quality_rating,
                deviation_pct,
                similarity_score,
                link_method,
            ))

            conn.commit()
            logger.info(f"Stored odds intelligence for match: {match_id}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store odds intelligence: {e}")
            return False

    async def link_and_store(
        self,
        vector_data: dict[str, Any],
        home_team: str,
        away_team: str,
        match_time: datetime,
    ) -> LinkResult:
        """
        关联并存储矩阵数据

        Args:
            vector_data: PriceVector.to_dict() 输出
            home_team: 主队名称
            away_team: 客队名称
            match_time: 比赛时间

        Returns:
            关联结果
        """
        # 查找候选
        candidates = self.find_candidates(home_team, away_team, match_time)

        # 选择最佳匹配
        best_match = self.select_best_match(candidates)

        if best_match:
            # V41.234: 计算链接方法
            link_method = "fuzzy" if best_match.similarity_score < 1.0 else "exact"

            # 存储数据（包含相似度和链接方法）
            stored = self.store_odds_intelligence(
                match_id=best_match.match_id,
                initial_price=vector_data.get("Initial_Price", []),
                closing_price=vector_data.get("Closing_Price", []),
                movement_history=vector_data.get("Movement_History", []),
                metadata={
                    "Quality_Rating": vector_data.get("Quality_Rating"),
                    "Deviation_Percentage": vector_data.get("Deviation_Percentage"),
                },
                similarity_score=best_match.similarity_score,
                link_method=link_method,
            )

            return LinkResult(
                vector_id=hash(str(vector_data)),
                matched_match_id=best_match.match_id,
                similarity_score=best_match.similarity_score,
                time_diff_hours=best_match.time_diff_hours,
                link_method=link_method,
                stored=stored,
            )
        else:
            # 未找到匹配
            return LinkResult(
                vector_id=hash(str(vector_data)),
                matched_match_id=None,
                similarity_score=0.0,
                time_diff_hours=0.0,
                link_method="none",
                stored=False,
            )


# =============================================================================
# 工具函数
# =============================================================================


def create_linker_config(
    time_window_hours: float = 48.0,
    similarity_threshold: float = 0.75,  # V41.232: 更新默认阈值（0.85 → 0.75）
) -> LinkerConfig:
    """
    创建关联器配置（便捷函数）- V41.232 优化

    Args:
        time_window_hours: 时间窗口（小时）
        similarity_threshold: 相似度阈值（V41.232: 灵活化至 0.75）

    Returns:
        LinkerConfig: 配置实例
    """
    return LinkerConfig(
        time_window_hours=time_window_hours,
        similarity_threshold=similarity_threshold,
    )
