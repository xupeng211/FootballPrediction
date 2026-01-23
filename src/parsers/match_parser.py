"""V41.832: Match Parser Module.

提供比赛数据解析功能，包括：
- 比赛哈希提取
- 队名解析
- 数据结构定义

Author: Senior Lead Data Architect
Version: V41.832 "Production Blueprint"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import re
from typing import Final

from playwright.async_api import Page

from src.config.crawler_config import ODDSPORTAL_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class MatchData:
    """比赛数据模型.

    Attributes:
        fotmob_id: FotMob 比赛 ID
        oddsportal_hash: OddsPortal 比赛哈希
        oddsportal_url: OddsPortal 完整 URL
        match_date: 比赛日期
        home_team: 主队名称
        away_team: 客队名称
        similarity: 队名相似度 (0-100)
        confidence: 映射置信度 (0-1)
    """

    fotmob_id: str | None = None
    oddsportal_hash: str | None = None
    oddsportal_url: str | None = None
    match_date: datetime | None = None
    home_team: str | None = None
    away_team: str | None = None
    similarity: float = 0.0
    confidence: float = 0.0


@dataclass
class TeamNames:
    """解析后的队名对.

    Attributes:
        home_team: 主队名称
        away_team: 客队名称
        url_slug: URL slug (原始)
    """

    home_team: str
    away_team: str
    url_slug: str


class TeamNameParser:
    """队名解析器.

    从 OddsPortal URL slug 中提取主客队名称。
    """

    # 常见英超队名映射（OddsPortal -> 标准）
    PREMIER_LEAGUE_MAPPING: Final[dict[str, tuple[str, str]]] = {
        "manchester-united": ("Manchester United", "Man Utd"),
        "manchester-city": ("Manchester City", "Man City"),
        "liverpool": ("Liverpool", "Liverpool"),
        "chelsea": ("Chelsea", "Chelsea"),
        "arsenal": ("Arsenal", "Arsenal"),
        "tottenham": ("Tottenham Hotspur", "Spurs"),
        "newcastle-united": ("Newcastle United", "Newcastle"),
        "brighton": ("Brighton & Hove Albion", "Brighton"),
        "aston-villa": ("Aston Villa", "Aston Villa"),
        "west-ham": ("West Ham United", "West Ham"),
        "brentford": ("Brentford", "Brentford"),
        "fulham": ("Fulham", "Fulham"),
        "crystal-palace": ("Crystal Palace", "Crystal Palace"),
        "wolverhampton": ("Wolverhampton Wanderers", "Wolves"),
        "everton": ("Everton", "Everton"),
        "nottingham-forest": ("Nottingham Forest", "Nottm Forest"),
        "bournemouth": ("Bournemouth", "Bournemouth"),
        "luton-town": ("Luton Town", "Luton"),
        "burnley": ("Burnley", "Burnley"),
        "sheffield-united": ("Sheffield United", "Sheffield Utd"),
    }

    @classmethod
    def parse_url_slug(cls, url_slug: str) -> TeamNames | None:
        """解析 URL slug 提取队名.

        Args:
            url_slug: URL slug (例如 "arsenal-chelsea-12345678")

        Returns:
            TeamNames 对象，解析失败返回 None
        """
        if not url_slug:
            return None

        # 移除哈希部分
        slug_without_hash = re.sub(r"-[A-Za-z0-9]{8,10}$", "", url_slug)

        # 分割主客队
        parts = slug_without_hash.split("-")

        if len(parts) < 2:
            return None

        # 查找分割点（通常是第一个 "-" 后的第一个单词边界）
        # 例如 "manchester-united-chelsea" -> ["manchester", "united", "chelsea"]
        # 需要找到主队和客队的边界

        teams = cls.split_hyphenated_url_slug(slug_without_hash)

        if not teams:
            return None

        home_raw, away_raw = teams[0]

        # 标准化队名
        home_team = cls._normalize_team_name(home_raw)
        away_team = cls._normalize_team_name(away_raw)

        return TeamNames(
            home_team=home_team,
            away_team=away_team,
            url_slug=url_slug,
        )

    @classmethod
    def _normalize_team_name(cls, raw_name: str) -> str:
        """标准化队名.

        Args:
            raw_name: 原始队名（hyphenated 格式）

        Returns:
            标准化的队名
        """
        # 查找映射表
        for slug, (full, short) in cls.PREMIER_LEAGUE_MAPPING.items():
            if slug in raw_name:
                return full

        # 默认：转换 hyphenated 为 spaced
        return raw_name.replace("-", " ").title()

    @classmethod
    def split_hyphenated_url_slug(cls, url_slug: str) -> list[tuple[str, str]] | None:
        """分割 hyphenated URL slug 为主客队组合.

        Args:
            url_slug: URL slug (例如 "arsenal-chelsea")

        Returns:
            [(home_team, away_team)] 列表，失败返回 None
        """
        # 移除哈希
        clean_slug = re.sub(r"-[A-Za-z0-9]{8,10}$", "", url_slug)

        parts = clean_slug.split("-")
        if len(parts) < 2:
            return None

        # 尝试所有可能的分割点
        combinations = []

        for i in range(1, len(parts)):
            home = "-".join(parts[:i])
            away = "-".join(parts[i:])

            if len(home) > 2 and len(away) > 2:
                combinations.append((home, away))

        return combinations if combinations else None


class MatchExtractor:
    """比赛数据提取器.

    从 OddsPortal HTML 页面中提取比赛哈希和基本信息。
    """

    # 三段式正则模式: /football/country/league-season/name-hash/
    THREE_SEGMENT_PATTERN: Final[re.Pattern[str]] = re.compile(
        ODDSPORTAL_CONFIG.THREE_SEGMENT_PATTERN
    )

    def __init__(self) -> None:
        """初始化提取器."""
        self.team_parser = TeamNameParser()

    async def extract_from_page(self, page: Page) -> list[MatchData]:
        """从页面中提取所有比赛数据.

        Args:
            page: Playwright Page 对象

        Returns:
            MatchData 列表

        Raises:
            ValueError: 页面内容为空
        """
        html = await page.content()

        if not html or len(html) < 1000:
            raise ValueError("Page content is too short or empty")

        matches = self.extract_from_html(html)
        logger.info(f"[MatchExtractor][extract_from_page] Extracted {len(matches)} matches")

        return matches

    def extract_from_html(self, html: str) -> list[MatchData]:
        """从 HTML 中提取比赛数据.

        Args:
            html: HTML 内容

        Returns:
            MatchData 列表
        """
        matches: list[MatchData] = []
        seen_hashes: set[str] = set()

        for match in self.THREE_SEGMENT_PATTERN.finditer(html):
            try:
                url_slug = match.group(1)
                oddsportal_hash = match.group(2)

                # 去重
                if oddsportal_hash in seen_hashes:
                    continue
                seen_hashes.add(oddsportal_hash)

                # 解析队名
                team_names = self.team_parser.parse_url_slug(url_slug)
                if not team_names:
                    continue

                match_data = MatchData(
                    oddsportal_hash=oddsportal_hash,
                    oddsportal_url=f"{ODDSPORTAL_CONFIG.BASE_URL}/football/england/premier-league-2024-2025/{url_slug}/",
                    home_team=team_names.home_team,
                    away_team=team_names.away_team,
                )

                matches.append(match_data)

            except (IndexError, ValueError) as e:
                logger.warning(f"[MatchExtractor][extract_from_html] Failed to parse match: {e}")
                continue

        return matches

    def validate_match_count(
        self, matches: list[MatchData], page_num: int, min_matches: int
    ) -> bool:
        """验证提取的比赛数量是否达标.

        Args:
            matches: 提取的比赛列表
            page_num: 当前页码
            min_matches: 最小比赛数量

        Returns:
            是否通过验证
        """
        count = len(matches)

        if count < min_matches and page_num < 8:
            logger.warning(
                f"[MatchExtractor][validate_match_count] ⚠️ Page {page_num}: Only {count} matches (expected >={min_matches})"
            )
            return False

        logger.info(
            f"[MatchExtractor][validate_match_count] ✅ Page {page_num}: Verified {count} matches"
        )
        return True
