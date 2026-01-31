#!/usr/bin/env python3
"""V57.0 Data Quality Inspector for Production Harvesting.

This script provides real-time monitoring of harvested data quality metrics:
1. Pinnacle Coverage Rate: Percentage of matches with Entity_P opening_time_h
2. Temporal Alignment: Average time delta between opening odds and match time
3. Anomaly Detection: Critical warnings for low success rates (< 70%)

Usage:
    python scripts/check_data_quality.py
    python scripts/check_data_quality.py --season 21/22 --league "Bundesliga"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

# ANSI Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def get_db_connection():
    """Establishes database connection using unified config."""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )


def print_header(title: str) -> None:
    """Prints formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{title:^70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")


def print_metric(label: str, value: str | float, status: str = "OK") -> None:
    """Prints metric with color coding based on status."""
    if status == "CRITICAL":
        color = Colors.FAIL
        icon = "🚨"
    elif status == "WARNING":
        color = Colors.WARNING
        icon = "⚠️"
    else:
        color = Colors.OKGREEN
        icon = "✅"

    print(f"{icon} {label:40} {color}{value}{Colors.ENDC}")


def check_pinnacle_coverage(conn, season: str | None = None, league: str | None = None) -> dict:
    """Checks Pinnacle (Entity_P) coverage rate.

    Args:
        conn: Database connection
        season: Optional season filter (e.g., "21/22")
        league: Optional league filter (e.g., "Bundesliga")

    Returns:
        Dictionary with coverage statistics
    """
    cursor = conn.cursor()

    # Build query with optional filters
    where_clause = "WHERE m.season = %s" if season else ""
    params = [season] if season else []

    if league:
        if where_clause:
            where_clause += " AND m.league_name = %s"
        else:
            where_clause = "WHERE m.league_name = %s"
        params.append(league)

    query = f"""
        SELECT
            m.season,
            m.league_name,
            COUNT(DISTINCT m.match_id) as total_matches,
            COUNT(DISTINCT CASE WHEN msd.opening_time_h IS NOT NULL THEN m.match_id END) as with_pinnacle,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN msd.opening_time_h IS NOT NULL THEN m.match_id END) /
                  NULLIF(COUNT(DISTINCT m.match_id), 0), 2) as coverage_rate
        FROM matches m
        LEFT JOIN metrics_multi_source_data msd
            ON m.match_id = msd.match_id
            AND msd.source_name = 'Entity_P'
        {where_clause}
        GROUP BY m.season, m.league_name
        ORDER BY m.season DESC, m.league_name;
    """

    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()

    return results


def check_temporal_alignment(conn, season: str | None = None, league: str | None = None) -> dict:
    """Checks temporal alignment (opening odds time vs match time).

    Args:
        conn: Database connection
        season: Optional season filter
        league: Optional league filter

    Returns:
        Dictionary with temporal statistics
    """
    cursor = conn.cursor()

    where_clause = "WHERE m.season = %s" if season else ""
    params = [season] if season else []

    if league:
        if where_clause:
            where_clause += " AND m.league_name = %s"
        else:
            where_clause = "WHERE m.league_name = %s"
        params.append(league)

    query = f"""
        SELECT
            m.season,
            m.league_name,
            COUNT(*) as total_records,
            ROUND(AVG(EXTRACT(EPOCH FROM (m.match_date - msd.opening_time_h)) / 3600), 2) as avg_hours_before_match,
            MIN(EXTRACT(EPOCH FROM (m.match_date - msd.opening_time_h)) / 3600) as min_hours,
            MAX(EXTRACT(EPOCH FROM (m.match_date - msd.opening_time_h)) / 3600) as max_hours
        FROM metrics_multi_source_data msd
        JOIN matches m ON msd.match_id = m.match_id
        {where_clause}
        AND msd.source_name = 'Entity_P'
        AND msd.opening_time_h IS NOT NULL
        GROUP BY m.season, m.league_name
        ORDER BY m.season DESC, m.league_name;
    """

    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()

    return results


def check_data_integrity(conn, season: str | None = None, league: str | None = None) -> dict:
    """Checks data integrity scores.

    Args:
        conn: Database connection
        season: Optional season filter
        league: Optional league filter

    Returns:
        Dictionary with integrity statistics
    """
    cursor = conn.cursor()

    where_clause = "WHERE m.season = %s" if season else ""
    params = [season] if season else []

    if league:
        if where_clause:
            where_clause += " AND m.league_name = %s"
        else:
            where_clause = "WHERE m.league_name = %s"
        params.append(league)

    query = f"""
        SELECT
            m.season,
            m.league_name,
            COUNT(*) as total_records,
            COUNT(CASE WHEN msd.integrity_score BETWEEN 1.02 AND 1.08 THEN 1 END) as valid_scores,
            ROUND(AVG(msd.integrity_score), 4) as avg_integrity_score,
            ROUND(MIN(msd.integrity_score), 4) as min_score,
            ROUND(MAX(msd.integrity_score), 4) as max_score
        FROM metrics_multi_source_data msd
        JOIN matches m ON msd.match_id = m.match_id
        {where_clause}
        AND msd.source_name = 'Entity_P'
        AND msd.integrity_score IS NOT NULL
        GROUP BY m.season, m.league_name
        ORDER BY m.season DESC, m.league_name;
    """

    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()

    return results


def generate_summary_report(conn, season: str | None = None, league: str | None = None) -> None:
    """Generates comprehensive data quality summary report.

    Args:
        conn: Database connection
        season: Optional season filter
        league: Optional league filter
    """
    print_header("📊 V57.0 Production Data Quality Inspector")

    # 1. Pinnacle Coverage
    print(f"{Colors.BOLD}【1. Pinnacle 覆盖率监控】{Colors.ENDC}")
    print(f"   说明: 统计已处理比赛中 Entity_P 的 opening_time_h 占比\n")

    coverage_results = check_pinnacle_coverage(conn, season, league)

    if not coverage_results:
        print(f"{Colors.WARNING}   ⚠️  未找到匹配数据{Colors.ENDC}")
    else:
        for row in coverage_results:
            rate = row['coverage_rate']
            if rate < 70:
                status = "CRITICAL"
            elif rate < 85:
                status = "WARNING"
            else:
                status = "OK"

            print_metric(
                f"{row['league_name']} {row['season']}",
                f"{rate:.2f}% ({row['with_pinnacle']}/{row['total_matches']})",
                status
            )

    # 2. Temporal Alignment
    print(f"\n{Colors.BOLD}【2. 时空对齐度监控】{Colors.ENDC}")
    print(f"   说明: 开盘时间距离比赛开始平均时长（小时）\n")

    temporal_results = check_temporal_alignment(conn, season, league)

    if not temporal_results:
        print(f"{Colors.WARNING}   ⚠️  未找到时间戳数据{Colors.ENDC}")
    else:
        for row in temporal_results:
            avg_hours = row['avg_hours_before_match']
            min_hours = row['min_hours']
            max_hours = row['max_hours']

            # Detect anomalies (negative time = time travel!)
            if min_hours < 0:
                status = "CRITICAL"
            elif avg_hours < 1:
                status = "WARNING"
            else:
                status = "OK"

            print_metric(
                f"{row['league_name']} {row['season']}",
                f"平均 {avg_hours:.1f}h (范围: {min_hours:.1f}h ~ {max_hours:.1f}h)",
                status
            )

    # 3. Data Integrity
    print(f"\n{Colors.BOLD}【3. 数据完整性评分】{Colors.ENDC}")
    print(f"   说明: integrity_score 有效范围 [1.02, 1.08]\n")

    integrity_results = check_data_integrity(conn, season, league)

    if not integrity_results:
        print(f"{Colors.WARNING}   ⚠️  未找到完整性评分数据{Colors.ENDC}")
    else:
        for row in integrity_results:
            avg_score = row['avg_integrity_score']
            valid_rate = 100.0 * row['valid_scores'] / row['total_records'] if row['total_records'] > 0 else 0

            if valid_rate < 90:
                status = "WARNING"
            else:
                status = "OK"

            print_metric(
                f"{row['league_name']} {row['season']}",
                f"平均分 {avg_score:.4f} (有效 {valid_rate:.1f}%)",
                status
            )

    # 4. Critical Alerts
    print(f"\n{Colors.BOLD}【4. 异常预警汇总】{Colors.ENDC}\n")

    critical_count = 0
    warning_count = 0

    for row in coverage_results:
        if row['coverage_rate'] < 70:
            critical_count += 1
            print(f"{Colors.FAIL}   [CRITICAL] {row['league_name']} {row['season']}: "
                  f"Pinnacle 覆盖率仅 {row['coverage_rate']:.2f}% (< 70%){Colors.ENDC}")
        elif row['coverage_rate'] < 85:
            warning_count += 1
            print(f"{Colors.WARNING}   [WARNING] {row['league_name']} {row['season']}: "
                  f"Pinnacle 覆盖率 {row['coverage_rate']:.2f}% (< 85%){Colors.ENDC}")

    for row in temporal_results:
        if row['min_hours'] < 0:
            critical_count += 1
            print(f"{Colors.FAIL}   [CRITICAL] {row['league_name']} {row['season']}: "
                  f"检测到时间穿越（开盘时间晚于比赛时间）！{Colors.ENDC}")

    if critical_count == 0 and warning_count == 0:
        print(f"{Colors.OKGREEN}   ✅ 所有指标正常，无异常预警{Colors.ENDC}")

    # Footer
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}检查完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def main():
    """Main entry point for data quality inspector."""
    parser = argparse.ArgumentParser(
        description="V57.0 Data Quality Inspector - Production monitoring tool"
    )
    parser.add_argument(
        "--season",
        type=str,
        help="Filter by season (e.g., '21/22', '22/23', '23/24')"
    )
    parser.add_argument(
        "--league",
        type=str,
        help="Filter by league (e.g., 'Bundesliga', 'Premier League')"
    )

    args = parser.parse_args()

    try:
        conn = get_db_connection()
        generate_summary_report(conn, args.season, args.league)
        conn.close()

    except Exception as e:
        print(f"{Colors.FAIL}[ERROR] Database connection failed: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
