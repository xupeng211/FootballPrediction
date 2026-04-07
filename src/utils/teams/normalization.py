#!/usr/bin/env python3
"""队名标准化与去噪。"""

from __future__ import annotations

import functools
import re

from .constants import PLACE_NAME_PRIORITY, TEAM_ABBREVIATIONS, TEAM_SUFFIXES


@functools.lru_cache(maxsize=4096)
def normalize_team_name(name: str) -> str:
    if not name:
        return ""

    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)

    words = name.split()
    normalized_words: list[str] = []
    for word in words:
        if word in TEAM_ABBREVIATIONS:
            replacement = TEAM_ABBREVIATIONS[word]
            if replacement:
                normalized_words.append(replacement)
        else:
            normalized_words.append(word)

    name = " ".join(normalized_words)
    return " ".join(name.split())


@functools.lru_cache(maxsize=2048)
def denoise_team_name(name: str) -> str:
    if not name:
        return ""

    name = normalize_team_name(name)
    filtered_words: list[str] = []
    for word in name.split():
        is_suffix = False
        for suffix in TEAM_SUFFIXES:
            if word == suffix:
                is_suffix = True
                break
        if not is_suffix:
            filtered_words.append(word)

    return " ".join(filtered_words).strip()


@functools.lru_cache(maxsize=2048)
def extract_place_name(name: str) -> str:
    if not name:
        return ""

    normalized = normalize_team_name(name)
    for place_key, place_value in PLACE_NAME_PRIORITY.items():
        if place_key in normalized:
            return place_value

    denoised = denoise_team_name(name)
    if "&" in denoised:
        denoised = denoised.split("&")[0].strip()

    for place_key, place_value in PLACE_NAME_PRIORITY.items():
        if place_key in denoised:
            return place_value

    return denoised
