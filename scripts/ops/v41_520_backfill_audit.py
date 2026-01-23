#!/usr/bin/env python3
"""
V41.520 Backfill Strategy Audit - 存量特征回填审计
=================================================

任务：
1. 缺口量化统计 - 统计 golden_features 为空的比赛数量
2. 赔率对齐大追查 - 调查赔率数据覆盖率低的原因
3. 回填压力预估 - 性能测试并计算全库回填时间

Author: V41.520 Audit Team
Version: V41.520 "Backfill Strategy Audit"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.api.collectors.v41_500_pipeline_integration import PipelineIntegrator

logger = logging.getLogger(__name__)


# =============================================================================
# Audit Results
# =============================================================================

@dataclass
class AuditResults:
    """审计结果数据类"""

    # 缺口统计
    total_matches: int = 0
    golden_features_missing: int = 0
    golden_features_exists: int = 0
    l2_raw_json_exists: int = 0
    l2_raw_json_missing: int = 0

    # 赔率覆盖
    odds_data_matches: int = 0  # match_odds_intelligence 有记录的比赛
    odds_coverage: float = 0.0

    # 特征提取失败分析
    l2_exists_but_no_golden: int = 0
    golden_parse_errors: int = 0

    # 性能测试
    sample_processed: int = 0
    sample_success: int = 0
    sample_failed: int = 0
    sample_total_time: float = 0.0
    sample_avg_time: float = 0.0

    # 回填预估
    estimated_total_time_min: float = 0.0

    def print_report(self):
        """打印审计报告"""
        print()
        print("=" * 80)
        print("V41.520 Backfill Strategy Audit - 最终报告")
        print("=" * 80)
        print()

        # 缺口统计
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  缺口量化统计                                                 │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  总比赛数:           {self.total_matches:7d}                                  │")
        print(f"  │  golden_features 缺失: {self.golden_features_missing:7d} ({self.golden_features_missing/max(self.total_matches,1)*100:5.1f}%)          │")
        print(f"  │  golden_features 存在: {self.golden_features_exists:7d} ({self.golden_features_exists/max(self.total_matches,1)*100:5.1f}%)          │")
        print(f"  │  l2_raw_json 存在:     {self.l2_raw_json_exists:7d} ({self.l2_raw_json_exists/max(self.total_matches,1)*100:5.1f}%)          │")
        print(f"  │  l2_raw_json 缺失:     {self.l2_raw_json_missing:7d} ({self.l2_raw_json_missing/max(self.total_matches,1)*100:5.1f}%)          │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        # L2 存在但 golden_features 缺失
        if self.l2_raw_json_exists > 0:
            l2_no_golden_rate = self.l2_exists_but_no_golden / self.l2_raw_json_exists * 100
            print(f"  📌 L2 存在但 golden_features 缺失: {self.l2_exists_but_no_golden} ({l2_no_golden_rate:.1f}%)")

        # 赔率覆盖
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  赔率数据覆盖                                                 │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  有赔率数据的比赛:     {self.odds_data_matches:7d}                                  │")
        print(f"  │  赔率覆盖率:         {self.odds_coverage:5.1f}%                                   │")
        print(f"  │  无赔率数据比赛:       {self.total_matches - self.odds_data_matches:7d}              │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        # 性能测试
        if self.sample_processed > 0:
            print("  ┌─────────────────────────────────────────────────────────────┐")
            print("  │  回填压力预估 (基于 100 场样本)                                │")
            print("  ├─────────────────────────────────────────────────────────────┤")
            print(f"  │  处理数量:           {self.sample_processed}                              │")
            print(f"  │  成功:               {self.sample_success} ({self.sample_success/max(self.sample_processed,1)*100:5.1f}%)                │")
            print(f"  │  失败:               {self.sample_failed} ({self.sample_failed/max(self.sample_processed,1)*100:5.1f}%)                │")
            print(f"  │  总耗时:             {self.sample_total_time:.2f} 秒                             │")
            print(f"  │  平均耗时:           {self.sample_avg_time:.3f} 秒/场                          │")
            print(f"  │  预估全库回填时间:   {self.estimated_total_time_min:.1f} 分钟                 │")
            print("  └─────────────────────────────────────────────────────────────┘")
            print()

        print("=" * 80)
        print("✅ V41.520 存量特征回填审计完成")
        print("=" * 80)


# =============================================================================
# Main Auditor
# =============================================================================

def run_gap_analysis() -> dict:
    """Step 1: 缺口量化统计"""
    print()
    print("[Step 1] 缺口量化统计...")
    print()

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    results = {}

    # 总比赛数
    cursor.execute("SELECT COUNT(*) as count FROM matches")
    results["total_matches"] = cursor.fetchone()["count"]

    # golden_features 缺失统计
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE golden_features IS NULL) as missing,
            COUNT(*) FILTER (WHERE golden_features IS NOT NULL) as exists
        FROM matches
    """)
    row = cursor.fetchone()
    results["golden_features_missing"] = row["missing"]
    results["golden_features_exists"] = row["exists"]

    # l2_raw_json 统计
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE l2_raw_json IS NOT NULL) as exists,
            COUNT(*) FILTER (WHERE l2_raw_json IS NULL) as missing
        FROM matches
    """)
    row = cursor.fetchone()
    results["l2_raw_json_exists"] = row["exists"]
    results["l2_raw_json_missing"] = row["missing"]

    # L2 存在但 golden_features 缺失
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM matches
        WHERE l2_raw_json IS NOT NULL
          AND (golden_features IS NULL OR golden_features = '{}'::jsonb)
    """)
    results["l2_exists_but_no_golden"] = cursor.fetchone()["count"]

    cursor.close()
    conn.close()

    # 打印中间结果
    print(f"  总比赛数: {results['total_matches']}")
    print(f"  golden_features 缺失: {results['golden_features_missing']} ({results['golden_features_missing']/results['total_matches']*100:.1f}%)")
    print(f"  l2_raw_json 存在: {results['l2_raw_json_exists']} ({results['l2_raw_json_exists']/results['total_matches']*100:.1f}%)")

    return results


def run_odds_gap_investigation(limit: int = 50) -> dict:
    """Step 2: 赔率对齐大追查"""
    print()
    print("[Step 2] 赔率对齐大追查...")
    print()

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    results = {}

    # 统计有赔率数据的比赛
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM match_odds_intelligence
    """)
    results["odds_data_matches"] = cursor.fetchone()["count"]

    # 获取总比赛数（用于计算覆盖率）
    cursor.execute("SELECT COUNT(*) as count FROM matches")
    total_matches = cursor.fetchone()["count"]
    results["total_matches_for_odds"] = total_matches
    results["odds_coverage"] = results["odds_data_matches"] / total_matches * 100 if total_matches > 0 else 0

    # 随机选取 50 场没有赔率数据的比赛
    cursor.execute("""
        SELECT m.match_id, m.league_name, m.home_team, m.away_team
        FROM matches m
        LEFT JOIN match_odds_intelligence o ON m.match_id = o.match_id
        WHERE o.match_id IS NULL
        ORDER BY RANDOM()
        LIMIT %s
    """, (limit,))

    matches_without_odds = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"  有赔率数据的比赛: {results['odds_data_matches']}")
    print(f"  赔率覆盖率: {results['odds_coverage']:.1f}%")

    # 调查：为什么赔率覆盖率低？
    print(f"  分析：只有 {results['odds_coverage']:.1f}% 的比赛有赔率数据")
    print(f"  可能原因：")
    print(f"    1. match_odds_intelligence 主要收录 Pinnacle (Entity_P) 数据")
    print(f"    2. 需要通过 matches_mapping 关联到 oddsportal 数据")
    print(f"    3. 赔率数据采集独立进行，没有与主流程集成")

    return results


def run_performance_benchmark(sample_size: int = 100) -> dict:
    """Step 3: 回填压力预估"""
    print()
    print(f"[Step 3] 回填压力预估 (样本: {sample_size} 场)...")
    print()

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()

    # 获取需要回填的比赛（有 l2_raw_json 但 golden_features 为空）
    cursor.execute("""
        SELECT match_id
        FROM matches
        WHERE l2_raw_json IS NOT NULL
          AND (golden_features IS NULL OR golden_features = '{}'::jsonb)
        ORDER BY RANDOM()
        LIMIT %s
    """, (sample_size,))

    matches_to_process = [row["match_id"] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    print(f"  找到 {len(matches_to_process)} 场需要回填的比赛")

    if len(matches_to_process) == 0:
        return {
            "sample_processed": 0,
            "sample_success": 0,
            "sample_failed": 0,
            "sample_total_time": 0.0,
            "sample_avg_time": 0.0,
            "estimated_total_time_min": 0.0,
        }

    # 运行回填测试
    integrator = PipelineIntegrator()

    success_count = 0
    failed_count = 0
    start_time = time.time()

    for i, match_id in enumerate(matches_to_process):
        try:
            result = integrator.process_match(match_id, verbose=False)
            if result:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Error processing {match_id}: {e}")
            failed_count += 1

        if (i + 1) % 20 == 0:
            print(f"  进度: {i + 1}/{len(matches_to_process)}")

    end_time = time.time()
    total_time = end_time - start_time

    integrator.cleanup()

    # 计算结果
    results = {
        "sample_processed": len(matches_to_process),
        "sample_success": success_count,
        "sample_failed": failed_count,
        "sample_total_time": total_time,
        "sample_avg_time": total_time / len(matches_to_process) if matches_to_process else 0,
    }

    # 获取总需要回填的比赛数
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM matches
        WHERE l2_raw_json IS NOT NULL
          AND (golden_features IS NULL OR golden_features = '{}'::jsonb)
    """)
    total_backfill = cursor.fetchone()["count"]
    cursor.close()
    conn.close()

    # 预估全库回填时间（假设线性扩展）
    if results["sample_avg_time"] > 0:
        results["estimated_total_time_min"] = (results["sample_avg_time"] * total_backfill) / 60
    else:
        results["estimated_total_time_min"] = 0

    print(f"  总耗时: {total_time:.2f} 秒")
    print(f"  平均耗时: {results['sample_avg_time']:.3f} 秒/场")
    print(f"  全库需要回填: {total_backfill} 场")
    print(f"  预估回填时间: {results['estimated_total_time_min']:.1f} 分钟")

    return results


# =============================================================================
# Main
# =============================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print()
    print("=" * 80)
    print("V41.520 Backfill Strategy Audit - 存量特征回填审计")
    print("=" * 80)
    print()

    audit = AuditResults()

    # Step 1: 缺口量化统计
    gap_results = run_gap_analysis()
    audit.total_matches = gap_results["total_matches"]
    audit.golden_features_missing = gap_results["golden_features_missing"]
    audit.golden_features_exists = gap_results["golden_features_exists"]
    audit.l2_raw_json_exists = gap_results["l2_raw_json_exists"]
    audit.l2_raw_json_missing = gap_results["l2_raw_json_missing"]
    audit.l2_exists_but_no_golden = gap_results["l2_exists_but_no_golden"]

    # Step 2: 赔率对齐大追查
    odds_results = run_odds_gap_investigation(limit=50)
    audit.odds_data_matches = odds_results["odds_data_matches"]
    audit.odds_coverage = odds_results["odds_coverage"]

    # Step 3: 回填压力预估
    perf_results = run_performance_benchmark(sample_size=100)
    audit.sample_processed = perf_results["sample_processed"]
    audit.sample_success = perf_results["sample_success"]
    audit.sample_failed = perf_results["sample_failed"]
    audit.sample_total_time = perf_results["sample_total_time"]
    audit.sample_avg_time = perf_results["sample_avg_time"]
    audit.estimated_total_time_min = perf_results["estimated_total_time_min"]

    # 打印最终报告
    audit.print_report()


if __name__ == "__main__":
    main()
