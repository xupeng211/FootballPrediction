#!/usr/bin/env python3
"""文本处理工具包。"""

from __future__ import annotations

from .leagues import LeagueUrlMapper
from .team_normalizer import TeamNameNormalizer
from .vendors import VendorNameCleaner
from .youth import YouthTeamDetector

__all__ = [
    "LeagueUrlMapper",
    "TeamNameNormalizer",
    "VendorNameCleaner",
    "YouthTeamDetector",
    "normalize_team_list",
    "normalize_vendor_list",
]


def normalize_team_list(team_names: list[str]) -> list[str]:
    normalizer = TeamNameNormalizer()
    return [normalizer.normalize(name) for name in team_names]


def normalize_vendor_list(vendor_names: list[str]) -> list[str]:
    cleaner = VendorNameCleaner()
    return [cleaner.clean(name) for name in vendor_names]
