#!/usr/bin/env python3
"""
V81.000 Radar Trigger - 桥接雷达触发器
========================================

当 BridgeEngine 模糊匹配失败时，此脚本被触发，使用 RapidFuzz
进行全量暴力模糊搜索，填补映射空缺。

Usage:
    python v81_000_radar_trigger.py --match-id <MATCH_ID> \
        --home-team "<HOME>" --away-team "<AWAY>" \
        --league "<LEAGUE>" --match-date "<DATE>"

Author: V81.000 Engineering Team
Version: V81.000 "Discovery Radar"
Date: 2026-01-25
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.cpp_bridge_radar import (
    BridgeRadarEngine,
    RadarQuery,
    RadarMatchResult,
    get_bridge_radar,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_radar_query(
    match_id: str,
    home_team: str,
    away_team: str,
    league_name: str,
    match_date: str,
    min_threshold: float = 65.0,
    max_candidates: int = 10
) -> RadarQuery:
    """
    创建雷达查询参数

    Args:
        match_id: 比赛 ID
        home_team: 主队名称
        away_team: 客队名称
        league_name: 联赛名称
        match_date: 比赛日期 (ISO format)
        min_threshold: 最低相似度阈值
        max_candidates: 最大候选数

    Returns:
        RadarQuery 对象
    """
    try:
        # Parse match_date
        if isinstance(match_date, str):
            match_date_dt = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
        else:
            match_date_dt = match_date

        return RadarQuery(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            league_name=league_name,
            match_date=match_date_dt,
            min_threshold=min_threshold,
            max_candidates=max_candidates
        )
    except ValidationError as e:
        logger.error(f"参数验证失败: {e}")
        raise


def trigger_radar(
    match_id: str,
    home_team: str,
    away_team: str,
    league_name: str,
    match_date: str,
    min_threshold: float = 65.0,
    max_candidates: int = 10,
    verbose: bool = False
) -> dict:
    """
    触发雷达扫描

    Args:
        match_id: 比赛 ID
        home_team: 主队名称
        away_team: 客队名称
        league_name: 联赛名称
        match_date: 比赛日期
        min_threshold: 最低相似度阈值
        max_candidates: 最大候选数
        verbose: 详细日志

    Returns:
        结果字典 {
            "success": bool,
            "match_id": str,
            "url": str | None,
            "confidence": float | None,
            "discovery_method": str,
            "trace_id": str | None,
            "error": str | None
        }
    """
    trace_id = None

    try:
        # 创建雷达查询
        query = create_radar_query(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            league_name=league_name,
            match_date=match_date,
            min_threshold=min_threshold,
            max_candidates=max_candidates
        )

        logger.info({
            "event": "radar_trigger_start",
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "league": league_name,
            "threshold": min_threshold,
        })

        # 获取雷达引擎实例
        radar = get_bridge_radar()

        # 执行动态桥接 (先查表，无结果则雷达扫描)
        url = radar.dynamic_bridge(query, verbose=verbose)

        if url:
            # 获取统计信息
            stats = radar.get_stats()

            logger.info({
                "event": "radar_discovery_success",
                "match_id": match_id,
                "url": url,
                "discovery_method": "DYNAMIC_BRIDGE",
                "total_queried": stats.total_queried,
                "radar_discoveries": stats.radar_discoveries,
                "static_lookups": stats.static_lookups,
            })

            return {
                "success": True,
                "match_id": match_id,
                "url": url,
                "confidence": None,  # 动态桥接不返回置信度
                "discovery_method": "DYNAMIC_BRIDGE",
                "trace_id": trace_id,
                "error": None
            }
        else:
            logger.warning({
                "event": "radar_discovery_failed",
                "match_id": match_id,
                "reason": "no_match_found",
            })

            return {
                "success": False,
                "match_id": match_id,
                "url": None,
                "confidence": None,
                "discovery_method": "NONE",
                "trace_id": trace_id,
                "error": "No match found"
            }

    except Exception as e:
        logger.error({
            "event": "radar_trigger_error",
            "match_id": match_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
        })

        return {
            "success": False,
            "match_id": match_id,
            "url": None,
            "confidence": None,
            "discovery_method": "ERROR",
            "trace_id": trace_id,
            "error": str(e)
        }


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description='V81.000 Radar Trigger - 桥接雷达触发器',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--match-id',
        required=True,
        help='比赛 ID (fotmob_id)'
    )
    parser.add_argument(
        '--home-team',
        required=True,
        help='主队名称'
    )
    parser.add_argument(
        '--away-team',
        required=True,
        help='客队名称'
    )
    parser.add_argument(
        '--league',
        required=True,
        help='联赛名称'
    )
    parser.add_argument(
        '--match-date',
        required=True,
        help='比赛日期 (ISO format, e.g., 2024-01-25T15:00:00)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=65.0,
        help='最低相似度阈值 (默认: 65.0)'
    )
    parser.add_argument(
        '--max-candidates',
        type=int,
        default=10,
        help='最大候选数 (默认: 10)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='启用详细日志'
    )

    args = parser.parse_args()

    # 触发雷达
    result = trigger_radar(
        match_id=args.match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        league_name=args.league,
        match_date=args.match_date,
        min_threshold=args.threshold,
        max_candidates=args.max_candidates,
        verbose=args.verbose
    )

    # V82.600: 输出 JSON 结果 (使用特殊标记包裹，单行输出)
    print(f"[JSON_RESULT]{json.dumps(result, ensure_ascii=False)}[JSON_RESULT]")

    # 返回退出码
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
