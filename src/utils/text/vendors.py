#!/usr/bin/env python3
"""Vendor 名称清洗工具。"""

from __future__ import annotations

import re
from typing import ClassVar


class VendorNameCleaner:
    """Vendor/Bookmaker 名称标准化。"""

    SUFFIXES: ClassVar[list[str]] = [
        "bet",
        "odds",
        "sports",
        "bookmaker",
        "bookies",
        "sportsbook",
        "wagering",
        "gaming",
    ]

    def __init__(self) -> None:
        self.suffix_pattern = re.compile(r"\s+(" + "|".join(self.SUFFIXES) + r")$", re.IGNORECASE)

    def clean(self, raw_name: str) -> str:
        if not raw_name:
            return ""

        cleaned = re.sub(r"&[a-z]+;", "", raw_name)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        cleaned = re.sub(r"1\s*x\s*2", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"1x2", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^a-zA-Z\s]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return self.suffix_pattern.sub("", cleaned)
