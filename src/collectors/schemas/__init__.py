#!/usr/bin/env python3
"""
V36.0 L1 采集器 Pydantic Schema 包
=============================
工业级数据完整性校验层

作者: ML Architect
日期: 2025-12-28
Phase: Production-Grade Refactor
Version: V36.0
"""

from src.collectors.schemas.l1_match_schema import (
    L1CollectionSummary,
    L1MatchData,
    LeagueId,
    MatchStatus,
)

__all__ = [
    "L1CollectionSummary",
    "L1MatchData",
    "LeagueId",
    "MatchStatus",
]
