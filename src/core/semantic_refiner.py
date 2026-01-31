#!/usr/bin/env python3
"""
V41.77 SemanticRefiner - 联赛无关的通用对齐框架
==================================================

本模块彻底替代脆弱的正则表达式，实现：

1. URL 解析：简单提取 Hash 和 Slug
2. Slug 解析：使用 team_alias.py 进行智能队名解析
3. 模糊匹配：与数据库中的比赛进行双向模糊匹配
4. 失败记录：自动记录对齐失败到 CSV

核心设计理念：
- 联赛无关（League-Agnostic）
- 容错性强（支持各种符号、缩写）
- 可观测性（失败自动记录）
- 零中断（匹配失败不抛出异常）

Author: 首席系统架构师
Version: V41.77
Date: 2026-01-15
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re

import psycopg2
from psycopg2.extras import RealDictCursor

from src.utils.team_alias import match_teams, normalize_team_name

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class SlugMatchResult:
    """Slug 匹配结果"""
    match_id: str | None  # 数据库中的 match_id
    home_team: str  # 解析后的主队名
    away_team: str  # 解析后的客队名
    hash_value: str  # 8 位哈希
    confidence: float  # 置信度 (0-100)
    league_name: str  # 联赛名称
    season: str  # 赛季
    raw_slug: str  # 原始 Slug
    is_match: bool  # 是否找到匹配
    failure_reason: str = ""  # 失败原因


@dataclass
class AlignmentFailure:
    """对齐失败记录"""
    timestamp: str
    url: str
    slug: str
    raw_home: str
    raw_away: str
    hash_value: str
    failure_reason: str
    suggested_matches: list[str]  # 可能的候选 match_id


# ============================================================================
# 核心类：SemanticRefiner
# ============================================================================

class SemanticRefiner:
    """
    V41.77: 语义化对齐引擎

    职责：
    1. 从 URL 提取 Hash 和 Slug（联赛无关）
    2. 解析 Slug 获取队名
    3. 与数据库进行模糊匹配
    4. 记录失败案例

    示例 URL:
    - /football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-AbCd1234/
    - /football/germany/bundesliga/Borussia-Dortmund-vs-Bayern-Munich-XYZ12345/
    - /football/italy/serie-a/Roma-vs-Inter-Milan-QwEr7890/
    """

    def __init__(
        self,
        db_conn,
        failure_log_dir: str = "logs",
        confidence_threshold: float = 85.0,
    ):
        """
        初始化语义化对齐引擎

        Args:
            db_conn: 数据库连接
            failure_log_dir: 失败日志目录
            confidence_threshold: 置信度阈值（低于此值视为匹配失败）
        """
        self.conn = db_conn
        self.confidence_threshold = confidence_threshold
        # V41.77: 使用日期格式的失败日志文件名
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"alignment_failures_{date_str}.csv"
        self.failure_log_path = Path(failure_log_dir) / filename

        # 确保日志目录存在
        self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化失败日志（带表头）
        if not self.failure_log_path.exists():
            self._init_failure_log()

        logger.info(
            f"✅ V41.77 SemanticRefiner 初始化完成 "
            f"(threshold={confidence_threshold}%, log={self.failure_log_path.name})"
        )

    def _init_failure_log(self) -> None:
        """初始化失败日志 CSV 文件"""
        with open(self.failure_log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "url", "slug", "raw_home", "raw_away", "hash_value",
                "failure_reason", "suggested_matches"
            ])

    def extract_hash_and_slug(self, url: str) -> tuple[str, str]:
        """
        从 URL 提取 Hash 和 Slug（联赛无关）

        规则：
        - Hash: 最后 8 位字母数字
        - Slug: Hash 之前的所有内容

        Args:
            url: 完整 URL

        Returns:
            (hash_value, slug) 元组

        Examples:
            >>> extract_hash_and_slug(
            ...     "/football/england/premier-league-2023-2024/man-utd-vs-newcastle-AbCd1234/"
            ... )
            ("AbCd1234", "man-utd-vs-newcastle")
            >>> extract_hash_and_slug(
            ...     "/football/germany/bundesliga/Borussia-Dortmund-Bayern-XYZ12345/"
            ... )
            ("XYZ12345", "Borussia-Dortmund-Bayern")
        """
        # 提取最后一个路径段
        path_parts = url.rstrip("/").split("/")
        last_segment = path_parts[-1] if path_parts else ""

        # 提取 Hash（最后 8 位字母数字，且必须包含至少 1 个数字或大写字母）
        # V41.77: 这样可以避免将全小写的单词（如 "ewcastle"）误判为 Hash
        hash_match = re.search(r"([A-Za-z0-9]{8})$", last_segment)
        hash_value = ""

        if hash_match:
            potential_hash = hash_match.group(1)
            # 验证 Hash 必须包含至少 1 个数字或大写字母
            if any(c.isdigit() or c.isupper() for c in potential_hash):
                hash_value = potential_hash

        # Slug 是 Hash 之前的部分
        slug = last_segment[:-len(hash_value)].rstrip("-") if hash_value else last_segment

        return hash_value, slug

    def parse_slug(self, slug: str) -> tuple[str, str]:
        """
        解析 Slug 获取主客队名

        支持的分隔符：vs, -, _, /

        Args:
            slug: 原始 Slug（如 "man-utd-vs-newcastle"）

        Returns:
            (home_team, away_team) 元组

        Examples:
            >>> parse_slug("manchester-utd-vs-newcastle-utd")
            ("Manchester United", "Newcastle United")
            >>> parse_slug("Borussia Dortmund - Bayern Munich")
            ("Borussia Dortmund", "Bayern Munich")
            >>> parse_slug("Roma_Inter Milan")
            ("Roma", "Inter Milan")
        """
        if not slug:
            return "", ""

        # 标准化分隔符：统一使用 " vs " 作为分隔符
        normalized = slug
        normalized = re.sub(r"[_/-]+", " ", normalized)  # 先移除特殊符号
        normalized = re.sub(r"\s+vs\s+", " vs ", normalized, flags=re.IGNORECASE)  # 标准化 "vs"

        # 分割主客队
        parts = normalized.split(" vs ")

        if len(parts) >= 2:
            # 取前两部分，中间可能有其他内容（如日期、地点等）
            home_raw = parts[0].strip()
            away_raw = parts[1].strip()

            # 清理队名：移除可能的后缀（如 "2024", "Home" 等）
            home_clean = self._clean_team_name(home_raw)
            away_clean = self._clean_team_name(away_raw)

            return home_clean, away_clean
        if len(parts) == 1:
            # 没有 "vs"，尝试其他分隔方式
            # 可能格式: "team1-team2" 或 "team1 team2"
            teams = self._split_teams_without_vs(normalized)
            if teams:
                return teams[0], teams[1]

        # 无法解析
        return "", ""

    def _clean_team_name(self, raw_name: str) -> str:
        """
        清理队名：移除常见后缀和噪音

        Args:
            raw_name: 原始队名

        Returns:
            清理后的队名
        """
        # 移除常见后缀
        suffixes_to_remove = [
            r"\s+\d{4}$",  # 年份（如 "2024"）
            r"\s+Home$",   # "Home"
            r"\s+Away$",   # "Away"
            r"\s+\d{1,2}$",  # 数字
        ]

        cleaned = raw_name
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, "", cleaned, flags=re.IGNORECASE)

        # 标准化队名（使用 team_alias）
        normalized = normalize_team_name(cleaned)

        # 转换为标题格式（但保留已知缩写大写）
        return self._title_case_team(normalized)

    def _title_case_team(self, name: str) -> str:
        """
        转换为标题格式，但保留已知缩写大写

        Args:
            name: 队名

        Returns:
            标题格式的队名
        """
        # 已知大写缩写列表
        known_upper = ["fc", "ac", "bc", "ss", "sd", "rb", "vfb", "tsg", "us", "ud"]

        words = name.split()
        title_words = []

        for word in words:
            if word.upper() in known_upper:
                title_words.append(word.upper())
            else:
                title_words.append(word.title())

        return " ".join(title_words)

    def _split_teams_without_vs(self, text: str) -> list[str]:
        """
        分割没有 "vs" 的队名字符串

        Args:
            text: 队名字符串

        Returns:
            [home_team, away_team] 或空列表
        """
        # 尝试按最后一个连字符分割
        if "-" in text:
            parts = text.rsplit("-", 1)
            if len(parts) == 2:
                return [self._clean_team_name(parts[0]), self._clean_team_name(parts[1])]

        # 尝试按空格分割（可能有多余词）
        words = text.split()
        if len(words) >= 2:
            # 假设前半部分是主队，后半部分是客队
            # 这是一种启发式方法，可能不完美
            mid = len(words) // 2
            home = " ".join(words[:mid])
            away = " ".join(words[mid:])
            return [self._clean_team_name(home), self._clean_team_name(away)]

        return []

    def match_against_database(
        self,
        home_team: str,
        away_team: str,
        league_name: str,
        season: str,
    ) -> list[dict]:
        """
        与数据库中的比赛进行模糊匹配

        Args:
            home_team: 主队名
            away_team: 客队名
            league_name: 联赛名称
            season: 赛季

        Returns:
            匹配的比赛列表（按置信度排序）
        """
        if not home_team or not away_team:
            return []

        query = """
            SELECT match_id, home_team, away_team, league_name, season
            FROM matches
            WHERE league_name = %s AND season = %s
        """

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (league_name, season))
                db_matches = cur.fetchall()

                # 对每个数据库比赛计算置信度
                scored_matches = []
                for db_match in db_matches:
                    confidence, details = match_teams(
                        home_team, away_team,
                        db_match["home_team"], db_match["away_team"]
                    )

                    if confidence >= self.confidence_threshold:
                        scored_matches.append({
                            **db_match,
                            "confidence": confidence,
                            "details": details,
                        })

                # 按置信度排序
                scored_matches.sort(key=lambda x: x["confidence"], reverse=True)

                return scored_matches

        except Exception as e:
            logger.exception(f"❌ 数据库查询失败: {e}")
            return []

    def refine_url(self, url: str, league_name: str, season: str) -> SlugMatchResult:
        """
        完整的 URL 精炼流程

        Args:
            url: 完整 URL
            league_name: 联赛名称
            season: 赛季

        Returns:
            SlugMatchResult 对象
        """
        # 1. 提取 Hash 和 Slug
        hash_value, slug = self.extract_hash_and_slug(url)

        if not hash_value:
            return SlugMatchResult(
                match_id=None,
                home_team="",
                away_team="",
                hash_value="",
                confidence=0.0,
                league_name=league_name,
                season=season,
                raw_slug=slug,
                is_match=False,
                failure_reason="No hash found in URL"
            )

        # 2. 解析 Slug 获取队名
        home_team, away_team = self.parse_slug(slug)

        if not home_team or not away_team:
            # 记录失败
            self._log_failure(url, slug, "", "", hash_value, "Failed to parse team names from slug")
            return SlugMatchResult(
                match_id=None,
                home_team="",
                away_team="",
                hash_value=hash_value,
                confidence=0.0,
                league_name=league_name,
                season=season,
                raw_slug=slug,
                is_match=False,
                failure_reason="Failed to parse team names from slug"
            )

        # 3. 与数据库匹配
        matches = self.match_against_database(home_team, away_team, league_name, season)

        if not matches:
            # 记录失败（带可能候选）
            suggested = self._get_suggested_matches(home_team, away_team, league_name, season)
            self._log_failure(
                url, slug, home_team, away_team, hash_value,
                f"No database match above threshold ({self.confidence_threshold}%)",
                suggested
            )
            return SlugMatchResult(
                match_id=None,
                home_team=home_team,
                away_team=away_team,
                hash_value=hash_value,
                confidence=0.0,
                league_name=league_name,
                season=season,
                raw_slug=slug,
                is_match=False,
                failure_reason=f"No database match above threshold ({self.confidence_threshold}%)"
            )

        # 4. 返回最佳匹配
        best_match = matches[0]
        return SlugMatchResult(
            match_id=best_match["match_id"],
            home_team=home_team,
            away_team=away_team,
            hash_value=hash_value,
            confidence=best_match["confidence"],
            league_name=league_name,
            season=season,
            raw_slug=slug,
            is_match=True,
            failure_reason=""
        )

    def _get_suggested_matches(
        self,
        home_team: str,
        away_team: str,
        league_name: str,
        season: str,
        limit: int = 5,
    ) -> list[str]:
        """
        获取建议的候选比赛（用于失败日志）

        Args:
            home_team: 主队名
            away_team: 客队名
            league_name: 联赛名称
            season: 赛季
            limit: 返回数量限制

        Returns:
            建议的 match_id 列表
        """
        # 降低阈值获取可能的候选
        original_threshold = self.confidence_threshold
        self.confidence_threshold = 50.0  # 临时降低到 50%

        matches = self.match_against_database(home_team, away_team, league_name, season)

        # 恢复阈值
        self.confidence_threshold = original_threshold

        return [m["match_id"] for m in matches[:limit]]

    def _log_failure(
        self,
        url: str,
        slug: str,
        raw_home: str,
        raw_away: str,
        hash_value: str,
        failure_reason: str,
        suggested_matches: list[str] | None = None,
    ) -> None:
        """
        记录对齐失败到 CSV

        Args:
            url: 完整 URL
            slug: Slug
            raw_home: 原始主队名
            raw_away: 原始客队名
            hash_value: Hash 值
            failure_reason: 失败原因
            suggested_matches: 建议的候选 match_id 列表
        """
        try:
            with open(self.failure_log_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    url,
                    slug,
                    raw_home,
                    raw_away,
                    hash_value,
                    failure_reason,
                    "|".join(suggested_matches or [])
                ])
        except Exception as e:
            logger.exception(f"❌ 写入失败日志失败: {e}")


# ============================================================================
# 便捷函数
# ============================================================================

def create_semantic_refiner(
    db_conn,
    failure_log_dir: str = "logs",
    confidence_threshold: float = 85.0,
) -> SemanticRefiner:
    """
    创建并配置语义化对齐引擎

    Args:
        db_conn: 数据库连接
        failure_log_dir: 失败日志目录
        confidence_threshold: 置信度阈值

    Returns:
        SemanticRefiner 实例
    """
    return SemanticRefiner(
        db_conn=db_conn,
        failure_log_dir=failure_log_dir,
        confidence_threshold=confidence_threshold,
    )


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    # 测试 SemanticRefiner

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s"
    )

    async def test():
        from src.config_unified import get_settings

        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )

        refiner = create_semantic_refiner(conn)

        # 测试 URL
        test_urls = [
            "https://www.oddsportal.com/football/england/premier-league-2023-2024/manchester-utd-vs-newcastle-AbCd1234/",
            "/football/germany/bundesliga/Borussia-Dortmund-vs-Bayern-Munich-XYZ12345/",
            "/football/italy/serie-a/Roma-vs-Inter-Milan-QwEr7890/",
        ]


        for url in test_urls:
            result = refiner.refine_url(url, "Premier League", "2023/2024")
            if not result.is_match:
                pass

        conn.close()

    import asyncio
    asyncio.run(test())
