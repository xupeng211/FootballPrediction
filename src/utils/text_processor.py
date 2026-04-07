#!/usr/bin/env python3
"""兼容层：保留旧导入路径 `src.utils.text_processor`。"""

from __future__ import annotations

from src.utils.text import (
    LeagueUrlMapper,
    TeamNameNormalizer,
    VendorNameCleaner,
    YouthTeamDetector,
    normalize_team_list,
    normalize_vendor_list,
)

__all__ = [
    "LeagueUrlMapper",
    "TeamNameNormalizer",
    "VendorNameCleaner",
    "YouthTeamDetector",
    "normalize_team_list",
    "normalize_vendor_list",
]
