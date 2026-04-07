#!/usr/bin/env python3
"""队名匹配数据模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchResult:
    """匹配结果。"""

    fotmob_id: int | None
    scraped_home: str
    scraped_away: str
    db_home: str
    db_away: str
    confidence: float
    tier: str
    url: str


@dataclass
class TeamAliasMatch:
    """队名别名匹配结果。"""

    normalized_name: str
    aliases: list[str]
    similarity: float
    is_confident: bool
