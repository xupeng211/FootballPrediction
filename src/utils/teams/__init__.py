#!/usr/bin/env python3
"""队名别名引擎包。"""

from __future__ import annotations

from .constants import (
    COMMON_EPL_TEAMS,
    CONFIDENCE_THRESHOLD,
    MULTI_WORD_TEAMS,
    PLACE_NAME_PRIORITY,
    SAME_CITY_DERBIES,
    TEAM_ABBREVIATIONS,
    TEAM_PREFIXES,
    TEAM_SUFFIXES,
)
from .matching import calculate_similarity, expand_team_name, match_teams, semantic_match
from .models import MatchResult, TeamAliasMatch
from .normalization import denoise_team_name, extract_place_name, normalize_team_name
from .test_harness import _TeamAliasTests, run_module_tests
from .url_tools import (
    batch_normalize_team_names,
    determine_tier,
    extract_team_names_from_url,
    get_team_aliases,
    is_safe_confidence,
)

__all__ = [
    "COMMON_EPL_TEAMS",
    "CONFIDENCE_THRESHOLD",
    "MULTI_WORD_TEAMS",
    "PLACE_NAME_PRIORITY",
    "SAME_CITY_DERBIES",
    "TEAM_ABBREVIATIONS",
    "TEAM_PREFIXES",
    "TEAM_SUFFIXES",
    "MatchResult",
    "TeamAliasMatch",
    "_TeamAliasTests",
    "batch_normalize_team_names",
    "calculate_similarity",
    "denoise_team_name",
    "determine_tier",
    "expand_team_name",
    "extract_place_name",
    "extract_team_names_from_url",
    "get_team_aliases",
    "is_safe_confidence",
    "match_teams",
    "normalize_team_name",
    "run_module_tests",
    "semantic_match",
]
