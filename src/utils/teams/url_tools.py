#!/usr/bin/env python3
"""URL 解析与便捷函数。"""

from __future__ import annotations

from difflib import SequenceMatcher
import re

from .constants import COMMON_EPL_TEAMS, CONFIDENCE_THRESHOLD
from .matching import expand_team_name
from .models import TeamAliasMatch
from .normalization import normalize_team_name

SLUG_ID_MIN_LENGTH = 8
SLUG_ID_MAX_LENGTH = 12
MIN_TEAM_PARTS = 2
FALLBACK_TEAM_PART_LIMIT = 3
ALIAS_CONFIDENCE_THRESHOLD = 0.85


def determine_tier(confidence: float) -> str:
    if confidence >= CONFIDENCE_THRESHOLD["HIGH"]:
        return "HIGH"
    if confidence >= CONFIDENCE_THRESHOLD["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def is_safe_confidence(confidence: float) -> bool:
    return confidence >= CONFIDENCE_THRESHOLD["SAFE_MIN"]


def extract_team_names_from_url(url: str) -> tuple[str, str] | None:
    match = re.search(r"/football/england/premier-league-[^/]+/([^/]+)/?", url)
    if not match:
        return None

    teams_part = match.group(1)
    parts = teams_part.split("-")

    id_idx = None
    for i, part in enumerate(parts):
        if SLUG_ID_MIN_LENGTH <= len(part) <= SLUG_ID_MAX_LENGTH:
            has_digit = any(c.isdigit() for c in part)
            has_upper = any(c.isupper() for c in part)
            is_id = has_digit or has_upper or not part.isalpha()
            if is_id:
                id_idx = i
                break

    team_parts = parts[:id_idx] if id_idx is not None else parts
    if len(team_parts) < MIN_TEAM_PARTS:
        return None

    home, away = _split_teams_smartly(team_parts)
    if home is None or away is None:
        return None
    return (home, away)


def _split_teams_smartly(parts: list[str]) -> tuple[str | None, str | None]:
    fallback_match: tuple[str, str] | None = None

    for i in range(1, len(parts)):
        home_parts = parts[:i]
        away_parts = parts[i:]
        home_candidate = " ".join(home_parts).title()
        away_candidate = " ".join(away_parts).title()
        home_norm = normalize_team_name(home_candidate)
        away_norm = normalize_team_name(away_candidate)
        home_known = home_norm in COMMON_EPL_TEAMS
        away_known = away_norm in COMMON_EPL_TEAMS

        if home_known and away_known:
            return (home_candidate, away_candidate)

        if fallback_match is None and (
            (home_known and len(away_parts) <= FALLBACK_TEAM_PART_LIMIT)
            or (away_known and len(home_parts) <= FALLBACK_TEAM_PART_LIMIT)
        ):
            fallback_match = (home_candidate, away_candidate)

    if fallback_match is not None:
        return fallback_match
    if len(parts) == MIN_TEAM_PARTS:
        return (parts[0].title(), parts[1].title())
    return (None, None)


def get_team_aliases(team_name: str) -> TeamAliasMatch:
    if not team_name:
        return TeamAliasMatch(normalized_name="", aliases=[], similarity=0.0, is_confident=False)

    normalized = normalize_team_name(team_name)
    aliases = expand_team_name(normalized)
    similarity = SequenceMatcher(None, normalized.lower(), team_name.lower()).ratio()
    is_confident = similarity >= ALIAS_CONFIDENCE_THRESHOLD

    return TeamAliasMatch(
        normalized_name=normalized,
        aliases=aliases,
        similarity=similarity * 100,
        is_confident=is_confident,
    )


def batch_normalize_team_names(team_names: list[str]) -> dict[str, str]:
    return {name: normalize_team_name(name) for name in team_names}
