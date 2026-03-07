#!/usr/bin/env python3
"""V4.42 MatchDataService - 比赛数据服务统一组件"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_config, get_database_url
from src.constants.shared_constants import MatchStatus

logger = logging.getLogger("V4.42.MatchDataService")


@dataclass
class MatchAlignment:
    """比赛对齐数据"""
    match_id: str
    fotmob_id: str | None = None
    oddsportal_hash: str | None = None
    oddsportal_url: str | None = None
    time_diff_hours: float | None = None
    time_valid: bool = True
    alignment_confidence: float = 0.0
    notes: str = ""

    def is_valid(self) -> bool:
        return (
            self.match_id
            and self.oddsportal_hash
            and self.time_valid
            and self.alignment_confidence >= 0.7
        )


class MatchDataService:
    """V4.42 比赛数据服务 - 统一的数据管理组件"""

    TIME_DIFF_THRESHOLD = 2.0
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self):
        self.config = get_config()
        self._conn = None

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(get_database_url())
        return self._conn

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


# 向后兼容的别名
MatchAligner = MatchDataService
MatchLinker = MatchDataService


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = MatchDataService()
    print("MatchDataService V4.42 initialized")
    service.close()
