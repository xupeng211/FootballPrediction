#!/usr/bin/env python3
"""
V82.500 Data Backfill Monitor (Turbo Mode)
==========================================

实时监控看板 - production_backfill.json 监控与熔断机制

V82.500 新增功能:
- RPM (每分钟处理量) 监控
- 403 封禁预警与自动回滚
- Watchdog 自动重启逻辑

Usage:
    python scripts/ops/v82_000_monitor.py          # 单次检查
    python scripts/ops/v82_000_monitor.py --watch  # 持续监控模式
    python scripts/ops/v82_000_monitor.py --health # 快速健康检查
    python scripts/ops/v82_000_monitor.py --watchdog # Watchdog 模式 (自动重启)

Author: V82.500 Engineering Team
Date: 2026-01-25
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

# =============================================================================
# CONSTANTS
# =============================================================================

LOGS_DIR = PROJECT_ROOT / "logs"
PRODUCTION_BACKFILL_JSON = LOGS_DIR / "production_backfill.json"
PENDING_REVIEW_JSON = LOGS_DIR / "pending_review.json"
V82_STATS_JSON = LOGS_DIR / "v82_500_stats.json"  # V82.500: 新增性能统计文件

# 熔断阈值
CIRCUIT_BREAKER_403_THRESHOLD = 0.05  # 5% 403 错误率
CIRCUIT_BREAKER_COOLDOWN_MINUTES = 30  # 30 分钟冷却期

# V82.500: RPM 计算窗口
RPM_CALCULATION_WINDOW_MINUTES = 5  # 计算过去 5 分钟的 RPM
TARGET_MPH = 100  # 目标 MPH (Matches Per Hour)
TARGET_RPM = TARGET_MPH / 60  # 目标 RPM (Matches Per Minute)


# =============================================================================
# DATABASE QUERIES
# =============================================================================

def get_database_stats() -> dict[str, Any]:
    """从数据库获取生产统计

    V83.500: 重构监控逻辑，移除 temporal_metric_records 扫描，
    改为统计 technical_features 中的倾率特征（home_drop_ratio, total_movement）
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        cur = conn.cursor()

        # V83.500: 1. 总体进度（新增倾率特征统计）
        cur.execute("""
            SELECT
                COUNT(*) as total_matches,
                COUNT(CASE WHEN m.l2_raw_json IS NOT NULL THEN 1 END) as with_l2,
                COUNT(CASE WHEN mm.oddsportal_url IS NOT NULL THEN 1 END) as with_bridge,
                COUNT(CASE WHEN m.technical_features IS NOT NULL THEN 1 END) as with_l3,
                COUNT(CASE WHEN
                    m.technical_features IS NOT NULL
                    AND (
                        m.technical_features::text LIKE '%home_drop_ratio%'
                        OR m.technical_features::text LIKE '%total_movement%'
                    )
                THEN 1 END) as with_slope_features
            FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE m.match_date >= '2020-08-01'
        """)
        progress_stats = cur.fetchone()

        # V83.500: 2. 倾率数据质量统计（替代 temporal_metric_records）
        cur.execute("""
            SELECT
                COUNT(*) as total_with_l3,
                COUNT(CASE WHEN
                    m.technical_features IS NOT NULL
                    AND m.technical_features::text LIKE '%home_drop_ratio%'
                    AND m.technical_features::text LIKE '%total_movement%'
                THEN 1 END) as with_complete_slope,
                COUNT(CASE WHEN
                    m.technical_features IS NOT NULL
                    AND m.technical_features::text LIKE '%initial_price%'
                THEN 1 END) as with_initial_price,
                COUNT(CASE WHEN
                    m.technical_features IS NOT NULL
                    AND m.technical_features::text LIKE '%closing_price%'
                THEN 1 END) as with_closing_price
            FROM matches m
            WHERE m.match_date >= '2020-08-01'
                AND m.technical_features IS NOT NULL
        """)
        slope_stats = cur.fetchone()

        # 3. 错误统计（最近 24 小时）
        cur.execute("""
            SELECT
                COUNT(*) as total_errors,
                COUNT(CASE WHEN error_message LIKE '%403%' THEN 1 END) as error_403,
                COUNT(CASE WHEN error_message LIKE '%429%' THEN 1 END) as error_429
            FROM match_pipeline_state
            WHERE error_message IS NOT NULL
              AND updated_at >= NOW() - INTERVAL '24 hours'
        """)
        error_stats = cur.fetchone()

        # 4. 映射质量统计
        cur.execute("""
            SELECT
                review_status,
                COUNT(*) as count
            FROM matches_mapping
            WHERE review_status IS NOT NULL
            GROUP BY review_status
            ORDER BY review_status
        """)
        review_stats = {row["review_status"]: row["count"] for row in cur.fetchall()}

        cur.close()

        return {
            "progress": dict(progress_stats),
            "slope": dict(slope_stats),  # V83.500: 新增倾率统计
            "errors": dict(error_stats),
            "review": review_stats,
            "timestamp": datetime.now().isoformat()
        }
    finally:
        conn.close()


def check_breakpoint_resumption() -> dict[str, Any]:
    """验证断点续传能力"""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        cur = conn.cursor()

        # 检查需要断点续传的比赛
        cur.execute("""
            SELECT
                COUNT(*) as pending_count,
                MIN(match_id) as next_match_id
            FROM matches m
            WHERE m.match_date >= '2020-08-01'
              AND m.l2_raw_json IS NOT NULL
              AND m.technical_features IS NULL
        """)
        result = cur.fetchone()

        return {
            "pending_count": result["pending_count"],
            "next_match_id": result["next_match_id"],
            "breakpoint_capable": result["next_match_id"] is not None
        }
    finally:
        conn.close()


def get_circuit_breaker_status() -> dict[str, Any]:
    """检查熔断器状态"""
    stats = get_database_stats()
    errors = stats["errors"]

    total_errors = errors.get("total_errors", 0)
    error_403 = errors.get("error_403", 0)

    # 计算 403 错误率
    error_403_rate = error_403 / total_errors if total_errors > 0 else 0.0

    # 检查是否需要熔断
    should_trip = error_403_rate > CIRCUIT_BREAKER_403_THRESHOLD

    return {
        "total_errors": total_errors,
        "error_403": error_403,
        "error_403_rate": error_403_rate,
        "threshold": CIRCUIT_BREAKER_403_THRESHOLD,
        "should_trip": should_trip,
        "cooldown_minutes": CIRCUIT_BREAKER_COOLDOWN_MINUTES,
        "status": "TRIPPED" if should_trip else "CLOSED"
    }


# =============================================================================
# V82.500: RPM MONITORING
# =============================================================================

def calculate_rpm_and_mph() -> dict[str, Any]:
    """V82.500/V83.500: 计算每分钟处理量 (RPM) 和每小时处理量 (MPH)

    V83.500: 移除 temporal_metric_records 扫描，改为统计倾率特征产出
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        cur = conn.cursor()

        # V83.500: 查询过去 N 分钟内处理的比赛数和倾率特征产出
        cur.execute("""
            SELECT
                COUNT(*) as matches_processed,
                COUNT(CASE WHEN m.l2_raw_json IS NOT NULL THEN 1 END) as l2_enriched,
                COUNT(DISTINCT mm.fotmob_id) as bridge_mapped,
                COUNT(CASE WHEN
                    m.technical_features IS NOT NULL
                    AND (
                        m.technical_features::text LIKE '%home_drop_ratio%'
                        OR m.technical_features::text LIKE '%total_movement%'
                    )
                THEN 1 END) as slope_features_extracted
            FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE m.match_date >= NOW() - INTERVAL '%s minutes'
              AND m.match_date < NOW()
        """, (RPM_CALCULATION_WINDOW_MINUTES,))

        result = cur.fetchone()

        matches_processed = result["matches_processed"]
        window_minutes = RPM_CALCULATION_WINDOW_MINUTES

        # 计算 RPM 和 MPH
        rpm = matches_processed / window_minutes if window_minutes > 0 else 0
        mph = rpm * 60

        return {
            "rpm": round(rpm, 2),
            "mph": round(mph, 2),
            "matches_processed": matches_processed,
            "window_minutes": window_minutes,
            "l2_enriched": result["l2_enriched"],
            "bridge_mapped": result["bridge_mapped"],
            "slope_features_extracted": result["slope_features_extracted"],  # V83.500: 倾率特征产出
            "target_rpm": round(TARGET_RPM, 2),
            "target_mph": TARGET_MPH,
            "performance_percent": round((mph / TARGET_MPH) * 100, 1) if TARGET_MPH > 0 else 0
        }

    finally:
        conn.close()


def save_performance_stats(stats: dict[str, Any]) -> None:
    """V82.500: 保存性能统计到文件"""
    V82_STATS_JSON.parent.mkdir(parents=True, exist_ok=True)

    # 读取历史数据
    history = []
    if V82_STATS_JSON.exists():
        try:
            with open(V82_STATS_JSON) as f:
                history = json.load(f)
        except (OSError, json.JSONDecodeError):
            history = []

    # 添加新数据点（保留最近 100 个点）
    history.append({
        "timestamp": datetime.now().isoformat(),
        **stats
    })
    history = history[-100:]  # 只保留最近 100 个点

    with open(V82_STATS_JSON, "w") as f:
        json.dump(history, f, indent=2)


# =============================================================================
# V82.500: WATCHDOG
# =============================================================================

def check_orchestrator_alive() -> bool:
    """V82.500: 检查 Orchestrator 进程是否存活"""
    try:
        result = subprocess.run(
            ["bash", "scripts/ops/control.sh", "status"],
            check=False, capture_output=True,
            text=True,
            timeout=10
        )
        # 检查输出中是否包含 "running"
        return "running" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def watchdog_restart_orchestrator() -> bool:
    """V82.500: Watchdog 自动重启 Orchestrator"""
    print("\n[V82.500 Watchdog] ⚠️  Orchestrator process not detected!")
    print("[V82.500 Watchdog] Attempting to restart...")

    try:
        # 尝试重启
        result = subprocess.run(
            ["bash", "scripts/ops/control.sh", "restart"],
            check=False, capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("[V82.500 Watchdog] ✅ Orchestrator restarted successfully")
            return True
        print(f"[V82.500 Watchdog] ❌ Restart failed: {result.stderr}")
        return False

    except Exception as e:
        print(f"[V82.500 Watchdog] ❌ Error during restart: {e}")
        return False


# =============================================================================
# JSON MONITORING
# =============================================================================

def load_production_backfill() -> dict[str, Any] | None:
    """加载 production_backfill.json"""
    if not PRODUCTION_BACKFILL_JSON.exists():
        return None

    try:
        with open(PRODUCTION_BACKFILL_JSON) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def update_production_backfill(stats: dict[str, Any]) -> None:
    """更新 production_backfill.json"""
    PRODUCTION_BACKFILL_JSON.parent.mkdir(parents=True, exist_ok=True)

    existing = load_production_backfill() or {}

    # 合并历史数据
    backfill_data = {
        **existing,
        **stats,
        "last_updated": datetime.now().isoformat()
    }

    with open(PRODUCTION_BACKFILL_JSON, "w") as f:
        json.dump(backfill_data, f, indent=2, default=str)


def load_pending_review() -> list[dict[str, Any]] | None:
    """加载 pending_review.json"""
    if not PENDING_REVIEW_JSON.exists():
        return None

    try:
        with open(PENDING_REVIEW_JSON) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


# =============================================================================
# DISPLAY FUNCTIONS
# =============================================================================

def print_monitor_dashboard() -> None:
    """打印监控仪表盘"""
    print("=" * 80)
    print("V82.500 DATA BACKFILL MONITOR (TURBO MODE)")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 获取统计数据
    stats = get_database_stats()
    circuit = get_circuit_breaker_status()
    breakpoint = check_breakpoint_resumption()

    # V82.500: 获取性能数据
    perf_stats = calculate_rpm_and_mph()

    # 1. V82.500 吞吐量面板 (新增)
    print("┌─ THROUGHPUT MONITOR (V82.500) ─────────────────────────────────────────────┐")
    perf_color = "🟢" if perf_stats["performance_percent"] >= 80 else "🟡" if perf_stats["performance_percent"] >= 50 else "🔴"
    print(f"  Status:           {perf_color} {perf_stats['performance_percent']}% of target")
    print(f"  Current Speed:    {perf_stats['mph']} MPH ({perf_stats['rpm']} RPM)")
    print(f"  Target Speed:     {perf_stats['target_mph']} MPH ({perf_stats['target_rpm']} RPM)")
    print(f"  Window:           Last {perf_stats['window_minutes']} minutes")
    print(f"  Processed:       {perf_stats['matches_processed']} matches")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # 2. 进度面板
    print("┌─ HARVEST PROGRESS ─────────────────────────────────────────────────────┐")
    progress = stats["progress"]
    total = progress["total_matches"]
    with_l3 = progress["with_l3"]
    with_slope = progress["with_slope_features"]  # V83.500: 倾率特征
    progress_pct = (with_l3 / total * 100) if total > 0 else 0
    slope_coverage_pct = (with_slope / total * 100) if total > 0 else 0  # V83.500

    print(f"  Total Matches:    {total:,}")
    print(f"  L2 Enriched:      {progress['with_l2']:,} ({progress['with_l2']/total*100:.1f}%)")
    print(f"  Bridge Mapped:    {progress['with_bridge']:,} ({progress['with_bridge']/total*100:.1f}%)")
    print(f"  L3 Features:      {with_l3:,} ({progress_pct:.2f}%)")
    print(f"  Slope Features:   {with_slope:,} ({slope_coverage_pct:.2f}%)")  # V83.500
    print(f"  Progress:         [{'█' * int(progress_pct // 2)}{'░' * (50 - int(progress_pct // 2))}] {progress_pct:.1f}%")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # 3. 质量面板
    print("┌─ QUALITY GATE ──────────────────────────────────────────────────────────┐")
    review = stats["review"]
    approved = review.get("approved", 0)
    pending = review.get("pending_review", 0)
    total_review = approved + pending

    print(f"  Approved:         {approved:,}")
    print(f"  Pending Review:   {pending:,}")
    print(f"  Approval Rate:    {(approved/total_review*100):.1f}%" if total_review > 0 else "  Approval Rate:    N/A")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # 4. V82.500: 403 封禁预警面板 (增强)
    print("┌─ 403 BAN WARNING (V82.500) ───────────────────────────────────────────────┐")
    cb_color = "🔴" if circuit["should_trip"] else "🟢"
    print(f"  Status:           {cb_color} {circuit['status']}")
    print(f"  403 Error Rate:   {circuit['error_403_rate']:.2%} (threshold: {circuit['threshold']:.0%})")
    print(f"  403 Count:        {circuit['error_403']}")
    print(f"  Total Errors:     {circuit['total_errors']}")
    print(f"  Cooldown:         {circuit['cooldown_minutes']} minutes")
    if circuit["should_trip"]:
        print("  ⚠️  ACTION REQUIRED: Reduce concurrency immediately!")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # 5. 断点续传面板
    print("┌─ BREAKPOINT RESUMPTION ──────────────────────────────────────────────────┐")
    bp_color = "✅" if breakpoint["breakpoint_capable"] else "⚠️ "
    print(f"  Capable:          {bp_color}")
    print(f"  Pending Count:    {breakpoint['pending_count']:,}")
    print(f"  Next Match ID:    {breakpoint['next_match_id'] or 'N/A'}")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # 6. V83.500: 倾率特征质量面板（替代时间序列统计）
    print("┌─ SLOPE FEATURES QUALITY (V83.500) ───────────────────────────────────────┐")
    slope = stats["slope"]
    total_l3 = slope["total_with_l3"]
    complete_slope = slope["with_complete_slope"]
    with_initial = slope["with_initial_price"]
    with_closing = slope["with_closing_price"]

    slope_coverage = (complete_slope / total_l3 * 100) if total_l3 > 0 else 0
    initial_coverage = (with_initial / total_l3 * 100) if total_l3 > 0 else 0
    closing_coverage = (with_closing / total_l3 * 100) if total_l3 > 0 else 0

    print(f"  Total L3 Matches:         {total_l3:,}")
    print(f"  Complete Slope Features:  {complete_slope:,} ({slope_coverage:.1f}%)")
    print(f"  With Initial Price:       {with_initial:,} ({initial_coverage:.1f}%)")
    print(f"  With Closing Price:       {with_closing:,} ({closing_coverage:.1f}%)")
    quality_status = "✅ GOOD" if slope_coverage >= 80 else "🟡 MODERATE" if slope_coverage >= 50 else "🔴 LOW"
    print(f"  Coverage Status:          {quality_status}")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # V82.500: 保存性能统计
    save_performance_stats(perf_stats)


def print_health_check() -> None:
    """快速健康检查（机器可读）

    V83.500: 移除 temporal_metric_records 检查，改为检查倾率特征覆盖率
    """
    stats = get_database_stats()
    circuit = get_circuit_breaker_status()
    breakpoint = check_breakpoint_resumption()

    health_score = 10.0

    # 扣分项
    if circuit["should_trip"]:
        health_score -= 5.0

    progress = stats["progress"]
    slope = stats["slope"]

    # V83.500: 倾率特征覆盖率检查
    total_l3 = slope["total_with_l3"]
    complete_slope = slope["with_complete_slope"]
    slope_coverage = (complete_slope / total_l3 * 100) if total_l3 > 0 else 0

    if slope_coverage < 50:
        health_score -= 2.0
    elif slope_coverage < 80:
        health_score -= 1.0

    # 输出 JSON
    output = {
        "health_score": round(health_score, 1),
        "progress": f"{stats['progress']['with_l3']}/{stats['progress']['total_matches']}",
        "slope_coverage": f"{slope_coverage:.1f}%",  # V83.500
        "circuit_breaker": circuit["status"],
        "breakpoint_capable": breakpoint["breakpoint_capable"],
        "timestamp": datetime.now().isoformat()
    }

    print(json.dumps(output))


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="V82.000 Data Backfill Monitor")
    parser.add_argument("--watch", action="store_true", help="持续监控模式（每 30 秒刷新）")
    parser.add_argument("--health", action="store_true", help="快速健康检查（JSON 输出）")
    parser.add_argument("--update-json", action="store_true", help="更新 production_backfill.json")

    args = parser.parse_args()

    # 健康检查模式
    if args.health:
        print_health_check()
        return 0

    # 更新 JSON 模式
    if args.update_json:
        stats = get_database_stats()
        circuit = get_circuit_breaker_status()
        breakpoint = check_breakpoint_resumption()

        update_production_backfill({
            "database_stats": stats,
            "circuit_breaker": circuit,
            "breakpoint": breakpoint
        })
        print(f"[V82.000] ✅ Updated {PRODUCTION_BACKFILL_JSON}")
        return 0

    # 持续监控模式
    if args.watch:
        try:
            while True:
                os.system("clear" if os.name == "posix" else "cls")
                print_monitor_dashboard()

                # 检查熔断器状态
                circuit = get_circuit_breaker_status()
                if circuit["should_trip"]:
                    print()
                    print("⚠️  WARNING: Circuit breaker tripped! 403 error rate exceeds threshold.")
                    print(f"   Cooldown period: {circuit['cooldown_minutes']} minutes")
                    print()

                time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n[V82.000] Monitoring stopped.")
            return 0

    # 默认：单次检查
    print_monitor_dashboard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
