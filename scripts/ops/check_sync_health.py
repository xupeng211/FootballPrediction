#!/usr/bin/env python3
"""
V41.235 合龙健康度自检脚本
============================

核心功能：
    - 统计 match_odds_intelligence 表中记录总数
    - 计算平均 similarity_score（相似度评分）
    - 筛选出 link_method == 'none' 的异常场次

Usage:
    python scripts/ops/check_sync_health.py
    python scripts/ops/check_sync_health.py --verbose
    python scripts/ops/check_sync_health.py --output health_report.json

Author: V41.235 Engineering Team
Date: 2026-01-19
Version: V41.235 "Production Readiness"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import argparse

# 项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config
import psycopg2
from psycopg2.extras import RealDictCursor

# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class HealthMetrics:
    """健康度指标"""
    total_records: int
    avg_similarity: float
    exact_matches: int
    fuzzy_matches: int
    failed_matches: int
    similarity_distribution: dict[str, int]


@dataclass
class AnomalyRecord:
    """异常记录"""
    match_id: str
    home_team: str
    away_team: str
    match_date: datetime
    reason: str


@dataclass
class HealthReport:
    """健康度报告"""
    timestamp: str
    metrics: HealthMetrics
    anomalies: list[AnomalyRecord]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "metrics": {
                "total_records": self.metrics.total_records,
                "avg_similarity": round(self.metrics.avg_similarity, 4),
                "exact_matches": self.metrics.exact_matches,
                "fuzzy_matches": self.metrics.fuzzy_matches,
                "failed_matches": self.metrics.failed_matches,
                "similarity_distribution": self.metrics.similarity_distribution,
            },
            "anomalies": [
                {
                    "match_id": a.match_id,
                    "home_team": a.home_team,
                    "away_team": a.away_team,
                    "match_date": a.match_date.isoformat(),
                    "reason": a.reason,
                }
                for a in self.anomalies
            ],
            "status": self.status,
        }


# =============================================================================
# 健康检查器
# =============================================================================


class SyncHealthChecker:
    """合龙健康度检查器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.config = get_config()

    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.config.database.host,
            database=self.config.database.name,
            user=self.config.database.user,
            password=self.config.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def check_table_exists(self) -> bool:
        """检查 match_odds_intelligence 表是否存在"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'match_odds_intelligence'
                )
            """)
            exists = cursor.fetchone()["exists"]
            return exists
        finally:
            cursor.close()
            conn.close()

    def collect_metrics(self) -> HealthMetrics:
        """收集健康度指标"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 统计总数
            cursor.execute("SELECT COUNT(*) as total FROM match_odds_intelligence")
            total = cursor.fetchone()["total"]

            if total == 0:
                return HealthMetrics(
                    total_records=0,
                    avg_similarity=0.0,
                    exact_matches=0,
                    fuzzy_matches=0,
                    failed_matches=0,
                    similarity_distribution={},
                )

            # 平均相似度
            cursor.execute("""
                SELECT AVG(similarity_score) as avg_sim
                FROM match_odds_intelligence
                WHERE similarity_score IS NOT NULL
            """)
            avg_sim = cursor.fetchone()["avg_sim"] or 0.0

            # 按链接方法分组
            cursor.execute("""
                SELECT link_method, COUNT(*) as count
                FROM match_odds_intelligence
                GROUP BY link_method
            """)
            method_counts = {row["link_method"]: row["count"] for row in cursor.fetchall()}

            # 相似度分布
            cursor.execute("""
                SELECT
                    CASE
                        WHEN similarity_score >= 0.95 THEN 'excellent'
                        WHEN similarity_score >= 0.85 THEN 'good'
                        WHEN similarity_score >= 0.75 THEN 'fair'
                        ELSE 'poor'
                    END as quality,
                    COUNT(*) as count
                FROM match_odds_intelligence
                WHERE similarity_score IS NOT NULL
                GROUP BY quality
            """)
            distribution = {row["quality"]: row["count"] for row in cursor.fetchall()}

            return HealthMetrics(
                total_records=total,
                avg_similarity=avg_sim,
                exact_matches=method_counts.get("exact", 0),
                fuzzy_matches=method_counts.get("fuzzy", 0),
                failed_matches=method_counts.get("none", 0),
                similarity_distribution=distribution,
            )

        finally:
            cursor.close()
            conn.close()

    def detect_anomalies(self) -> list[AnomalyRecord]:
        """检测异常记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            anomalies = []

            # 查询 link_method == 'none' 的记录
            cursor.execute("""
                SELECT m.match_id, m.home_team, m.away_team, m.match_date
                FROM match_odds_intelligence o
                JOIN matches m ON o.match_id = m.match_id
                WHERE o.link_method = 'none'
                ORDER BY m.match_date DESC
                LIMIT 50
            """)

            for row in cursor.fetchall():
                anomalies.append(
                    AnomalyRecord(
                        match_id=row["match_id"],
                        home_team=row["home_team"],
                        away_team=row["away_team"],
                        match_date=row["match_date"],
                        reason="link_method == 'none' (匹配失败)",
                    )
                )

            # 查询低相似度记录 (< 0.75)
            cursor.execute("""
                SELECT m.match_id, m.home_team, m.away_team, m.match_date,
                       o.similarity_score
                FROM match_odds_intelligence o
                JOIN matches m ON o.match_id = m.match_id
                WHERE o.similarity_score < 0.75
                  AND o.similarity_score IS NOT NULL
                ORDER BY o.similarity_score ASC
                LIMIT 50
            """)

            for row in cursor.fetchall():
                anomalies.append(
                    AnomalyRecord(
                        match_id=row["match_id"],
                        home_team=row["home_team"],
                        away_team=row["away_team"],
                        match_date=row["match_date"],
                        reason=f"低相似度: {row['similarity_score']:.2%}",
                    )
                )

            return anomalies

        finally:
            cursor.close()
            conn.close()

    def generate_report(self) -> HealthReport:
        """生成健康度报告"""
        metrics = self.collect_metrics()
        anomalies = self.detect_anomalies()

        # 计算状态
        if metrics.total_records == 0:
            status = "EMPTY"
        elif metrics.failed_matches > 0:
            status = "WARNING"
        elif metrics.avg_similarity < 0.85:
            status = "FAIR"
        else:
            status = "HEALTHY"

        return HealthReport(
            timestamp=datetime.now().isoformat(),
            metrics=metrics,
            anomalies=anomalies,
            status=status,
        )

    def print_report(self, report: HealthReport) -> None:
        """打印报告到终端"""
        print("\n" + "=" * 60)
        print("V41.235 合龙健康度报告")
        print("=" * 60)

        print(f"\n生成时间: {report.timestamp}")
        print(f"系统状态: {self._get_status_emoji(report.status)} {report.status}")

        print("\n" + "-" * 60)
        print("📊 核心指标")
        print("-" * 60)
        print(f"总记录数: {report.metrics.total_records:,}")
        print(f"平均相似度: {report.metrics.avg_similarity:.2%}")

        print("\n" + "-" * 60)
        print("🔗 匹配方法分布")
        print("-" * 60)
        print(f"精确匹配 (exact): {report.metrics.exact_matches:,}")
        print(f"模糊匹配 (fuzzy): {report.metrics.fuzzy_matches:,}")
        print(f"匹配失败 (none):  {report.metrics.failed_matches:,}")

        if report.metrics.similarity_distribution:
            print("\n" + "-" * 60)
            print("📈 相似度分布")
            print("-" * 60)
            for quality, count in report.metrics.similarity_distribution.items():
                emoji = {"excellent": "🟢", "good": "🔵", "fair": "🟡", "poor": "🔴"}.get(quality, "⚪")
                print(f"{emoji} {quality.capitalize()}: {count:,}")

        if report.anomalies:
            print("\n" + "-" * 60)
            print(f"⚠️  异常记录 (共 {len(report.anomalies)} 条)")
            print("-" * 60)
            for i, anomaly in enumerate(report.anomalies[:10], 1):
                print(f"\n  [{i}] {anomaly.match_id}")
                print(f"      比赛: {anomaly.home_team} vs {anomaly.away_team}")
                print(f"      时间: {anomaly.match_date.strftime('%Y-%m-%d %H:%M')}")
                print(f"      原因: {anomaly.reason}")

            if len(report.anomalies) > 10:
                print(f"\n  ... 还有 {len(report.anomalies) - 10} 条异常记录")

        print("\n" + "=" * 60)
        print(f"结论: {self._get_recommendation(report)}")
        print("=" * 60 + "\n")

    def _get_status_emoji(self, status: str) -> str:
        """获取状态 Emoji"""
        return {
            "HEALTHY": "✅",
            "FAIR": "🟡",
            "WARNING": "⚠️",
            "EMPTY": "🔵",
        }.get(status, "❓")

    def _get_recommendation(self, report: HealthReport) -> str:
        """获取建议"""
        if report.status == "EMPTY":
            return "数据库为空，请先运行数据同步"
        elif report.status == "WARNING":
            return f"存在 {report.metrics.failed_matches} 条匹配失败记录，建议检查队名映射"
        elif report.status == "FAIR":
            return f"平均相似度偏低 ({report.metrics.avg_similarity:.1%})，建议调整匹配阈值"
        else:
            return "系统运行正常，数据合龙健康"


# =============================================================================
# 主程序
# =============================================================================


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V41.235 合龙健康度自检脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="详细输出模式",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="输出 JSON 报告到指定文件",
    )

    args = parser.parse_args()

    # 创建检查器
    checker = SyncHealthChecker(verbose=args.verbose)

    # 检查表是否存在
    if not checker.check_table_exists():
        print("❌ 错误: match_odds_intelligence 表不存在")
        print("\n请先运行 V41.234 测试创建表:")
        print("  python scripts/ops/v41_234_great_alignment.py")
        return 1

    # 生成报告
    report = checker.generate_report()

    # 打印报告
    checker.print_report(report)

    # 保存 JSON 报告（如果指定）
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"📄 JSON 报告已保存: {output_path}\n")

    # 返回退出码
    return 0 if report.status in ["HEALTHY", "FAIR"] else 1


if __name__ == "__main__":
    exit(main())
