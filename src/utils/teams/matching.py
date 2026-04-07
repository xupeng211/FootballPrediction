#!/usr/bin/env python3
"""队名语义匹配与相似度计算。"""

from __future__ import annotations

from difflib import SequenceMatcher
import functools
import logging

from .constants import MULTI_WORD_TEAMS, SAME_CITY_DERBIES
from .normalization import denoise_team_name, extract_place_name, normalize_team_name

logger = logging.getLogger(__name__)

DERBY_REJECTION_SCORE = 40.0
HIGH_SIMILARITY_THRESHOLD = 85.0
MIN_TEAM_TOKEN_LENGTH = 3
REVERSE_WARNING_THRESHOLD = 70.0
GENERIC_TERMS = {"city", "united", "fc", "athletic", "club", "ac", "inter", "real"}


@functools.lru_cache(maxsize=8192)
def semantic_match(name1: str, name2: str) -> tuple[float, str]:  # noqa: PLR0911
    if not name1 or not name2:
        return 0.0, "Empty name"

    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    if norm1 == norm2:
        return 100.0, "Perfect match (normalized)"

    derby_result = _check_derby_rejection(norm1, norm2)
    if derby_result is not None:
        return derby_result, "Derby rejection: Different teams in same city"

    if norm1 in GENERIC_TERMS or norm2 in GENERIC_TERMS:
        generic = norm1 if norm1 in GENERIC_TERMS else norm2
        return 40.0, f"Generic term: '{generic}' cannot uniquely identify team"

    place1 = extract_place_name(name1)
    place2 = extract_place_name(name2)
    if place1 and place2 and place1 == place2:
        derby_result_place = _check_derby_rejection_by_place(name1, name2, place1)
        if derby_result_place is not None:
            return derby_result_place, f"Derby rejection: '{place1}' has multiple teams"

        base_confidence = 95.0
        if norm1 in norm2 or norm2 in norm1:
            base_confidence = 98.0
        return base_confidence, f"Place name match: '{place1}'"

    denoised1 = denoise_team_name(name1)
    denoised2 = denoise_team_name(name2)
    if denoised1 == denoised2:
        return 90.0, f"Denoised match: '{denoised1}'"

    similarity = calculate_similarity(name1, name2)
    if similarity >= HIGH_SIMILARITY_THRESHOLD:
        return similarity, f"High similarity: {similarity:.1f}%"
    return similarity, f"Low similarity: {similarity:.1f}%"


def _check_derby_rejection(norm1: str, norm2: str) -> float | None:
    derby_indicators = [
        "united",
        "city",
        "hotspur",
        "spurs",
        "inter",
        "ac",
        "real",
        "atletico",
        "athletic",
        "fc",
        "wanderers",
        "rovers",
        "palace",
        "albion",
        "forest",
        "borough",
        "county",
        "rangers",
        "celtic",
        "dynamo",
        "schalke",
        "juventus",
        "torino",
        "roma",
        "lazio",
        "olympiakos",
        "panathinaikos",
        "fenerbahce",
        "galatasaray",
        "besiktas",
    ]

    def has_derby_indicator(norm: str) -> bool:
        if any(indicator in norm for indicator in derby_indicators):
            return True
        for teams in SAME_CITY_DERBIES.values():
            for team in teams:
                if norm == normalize_team_name(team):
                    return True
        return False

    if not (has_derby_indicator(norm1) and has_derby_indicator(norm2)):
        return None

    for teams in SAME_CITY_DERBIES.values():
        team1_found = False
        team2_found = False
        for team in teams:
            team_norm = normalize_team_name(team)
            if norm1 == team_norm or (
                team_norm in norm1 and len(team_norm) > MIN_TEAM_TOKEN_LENGTH
            ):
                team1_found = True
            if norm2 == team_norm or (
                team_norm in norm2 and len(team_norm) > MIN_TEAM_TOKEN_LENGTH
            ):
                team2_found = True
        if team1_found and team2_found and norm1 != norm2:
            return DERBY_REJECTION_SCORE

    return None


def _check_derby_rejection_by_place(name1: str, name2: str, place: str) -> float | None:
    place_key = place.lower()
    if place_key not in SAME_CITY_DERBIES:
        return None

    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    derby_indicators = [
        "united",
        "city",
        "hotspur",
        "spurs",
        "inter",
        "ac",
        "real",
        "atletico",
        "athletic",
        "fc",
        "wanderers",
        "rovers",
        "palace",
        "albion",
        "forest",
        "borough",
        "county",
        "rangers",
        "celtic",
    ]

    if not (
        any(indicator in norm1 for indicator in derby_indicators)
        and any(indicator in norm2 for indicator in derby_indicators)
    ):
        return None

    team1_matches: list[str] = []
    team2_matches: list[str] = []
    for team in SAME_CITY_DERBIES[place_key]:
        team_norm = normalize_team_name(team)
        if norm1 == team_norm or (team_norm in norm1 and len(team_norm) > MIN_TEAM_TOKEN_LENGTH):
            team1_matches.append(team)
        if norm2 == team_norm or (team_norm in norm2 and len(team_norm) > MIN_TEAM_TOKEN_LENGTH):
            team2_matches.append(team)

    if team1_matches and team2_matches and norm1 != norm2:
        return DERBY_REJECTION_SCORE
    return None


def expand_team_name(name: str) -> list[str]:
    variants = [name]
    for full_name, abbreviations in MULTI_WORD_TEAMS.items():
        if isinstance(abbreviations, str):
            if name == abbreviations:
                variants.append(full_name)
            continue
        if name == full_name.lower():
            variants.extend(abbreviations)
        elif name in abbreviations:
            variants.append(full_name)
    return list(set(variants))


def calculate_similarity(name1: str, name2: str) -> float:  # noqa: PLR0911
    if not name1 or not name2:
        return 0.0

    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)

    combined1 = name1.lower() + " " + norm1
    combined2 = name2.lower() + " " + norm2
    if (
        "man utd" in combined1 or "manchester utd" in combined1
    ) and "manchester united" in combined2:
        return 97.0
    if (
        "man utd" in combined2 or "manchester utd" in combined2
    ) and "manchester united" in combined1:
        return 97.0
    if ("man city" in combined1) and "manchester city" in combined2:
        return 75.0
    if ("man city" in combined2) and "manchester city" in combined1:
        return 75.0
    if (
        ("spurs" in combined1 or "spurs" in combined2)
        and "tottenham" in norm1
        and "tottenham" in norm2
    ):
        return 96.0
    if norm1 == norm2:
        return 100.0

    seq_ratio = SequenceMatcher(None, norm1, norm2).ratio() * 100
    max_variant_score = seq_ratio
    for v1 in expand_team_name(norm1):
        for v2 in expand_team_name(norm2):
            variant_score = SequenceMatcher(None, v1, v2).ratio() * 100
            max_variant_score = max(max_variant_score, variant_score)

    return max_variant_score


def match_teams(
    scraped_home: str,
    scraped_away: str,
    db_home: str,
    db_away: str,
) -> tuple[float, str]:
    norm_scraped_home = normalize_team_name(scraped_home)
    norm_scraped_away = normalize_team_name(scraped_away)

    if norm_scraped_home in GENERIC_TERMS or norm_scraped_away in GENERIC_TERMS:
        home_semantic, home_details = semantic_match(scraped_home, db_home)
        away_semantic, away_details = semantic_match(scraped_away, db_away)
        avg_score = (home_semantic + away_semantic) / 2
        details = [f"Home (semantic): {home_details}", f"Away (semantic): {away_details}"]
        return avg_score, "; ".join(details)

    home_sim = calculate_similarity(scraped_home, db_home)
    away_sim = calculate_similarity(scraped_away, db_away)
    home_reverse_sim = calculate_similarity(scraped_home, db_away)
    away_reverse_sim = calculate_similarity(scraped_away, db_home)

    forward_score = (home_sim + away_sim) / 2
    reverse_score = (home_reverse_sim + away_reverse_sim) / 2
    best_score = max(forward_score, reverse_score)

    details = [
        f"Home: '{scraped_home}' vs '{db_home}' = {home_sim:.1f}%",
        f"Away: '{scraped_away}' vs '{db_away}' = {away_sim:.1f}%",
    ]
    if reverse_score > forward_score and reverse_score > REVERSE_WARNING_THRESHOLD:
        details.append(f"⚠️ 可能主客颠倒: {reverse_score:.1f}%")

    return best_score, "; ".join(details)
