#!/usr/bin/env python3
"""
V36.0 Morning Report - 晨报脚本

功能：
1. 统计过去一个晚上 8 个 Workers 的收割成果
2. 检查 match_features 表中 payout_ratio 非空比例
3. 判断是否可以启动 V36.1 全量重训练

使用：
    python scripts/ops/morning_report.py

Author: 高级机器学习架构师 (Staff ML Architect)
Date: 2026-01-12
Version: V36.0 (Morning Report)
"""

import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class MorningReport:
    """晨报生成器"""

    def __init__(self):
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def get_harvest_stats(self, hours_ago: int = 12) -> Dict[str, Any]:
        """
        统计过去 N 小时的收割成果

        Args:
            hours_ago: 统计过去多少小时（默认 12 小时）

        Returns:
            统计结果字典
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cutoff_time = datetime.now() - timedelta(hours=hours_ago)

                # 统计新收割的比赛（按 created_at 判断）
                cur.execute("""
                    SELECT
                        COUNT(*) as total_harvested,
                        COUNT(DISTINCT DATE(match_date)) as days_covered,
                        COUNT(DISTINCT league_name) as leagues_covered
                    FROM matches
                    WHERE created_at >= %s
                      AND status = 'harvested'
                """, (cutoff_time,))

                result = cur.fetchone()
                return dict(result) if result else {"total_harvested": 0, "days_covered": 0, "leagues_covered": 0}

        finally:
            conn.close()

    def get_payout_ratio_stats(self) -> Dict[str, Any]:
        """
        统计 match_features 表中 payout_ratio 非空比例

        Returns:
            统计结果字典
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 统计 payout_ratio 非空比例
                cur.execute("""
                    SELECT
                        COUNT(*) as total_features,
                        COUNT(payout_ratio) as payout_ratio_count,
                        COUNT(movement_velocity) as movement_velocity_count,
                        ROUND(100.0 * COUNT(payout_ratio) / NULLIF(COUNT(*), 0), 2) as payout_ratio_pct,
                        ROUND(100.0 * COUNT(movement_velocity) / NULLIF(COUNT(*), 0), 2) as movement_velocity_pct
                    FROM match_features
                """)

                result = cur.fetchone()
                return dict(result) if result else {
                    "total_features": 0,
                    "payout_ratio_count": 0,
                    "movement_velocity_count": 0,
                    "payout_ratio_pct": 0.0,
                    "movement_velocity_pct": 0.0
                }

        finally:
            conn.close()

    def get_high_payout_matches(self, limit: int = 10) -> list:
        """
        获取高返还率比赛列表

        Args:
            limit: 返回记录数限制

        Returns:
            高返还率比赛列表
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        mf.match_id,
                        m.league_name,
                        m.home_team,
                        m.away_team,
                        m.match_date,
                        mf.payout_ratio,
                        mf.closing_home,
                        mf.closing_draw,
                        mf.closing_away
                    FROM match_features mf
                    JOIN matches m ON mf.match_id = m.match_id
                    WHERE mf.payout_ratio > 0.95
                      AND m.match_date > NOW() - INTERVAL '7 days'
                    ORDER BY mf.payout_ratio DESC
                    LIMIT %s
                """, (limit,))

                return [dict(row) for row in cur.fetchall()]

        finally:
            conn.close()

    def get_disk_space_stats(self) -> Dict[str, Any]:
        """
        检查磁盘剩余空间

        V36.2 新增功能：监控数据库和备份目录的磁盘使用情况

        Returns:
            磁盘空间统计字典
        """
        project_root = Path(__file__).parent.parent.parent

        # 检查项目根目录磁盘空间
        # 在 Docker 环境中，这会显示容器内的磁盘使用情况
        usage = shutil.disk_usage(project_root)

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        used_pct = (used_gb / total_gb) * 100 if total_gb > 0 else 0

        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_pct": round(used_pct, 2),
            "status": "warning" if used_pct > 80 else "ok"
        }

    def generate_report(self, hours_ago: int = 12) -> str:
        """
        生成晨报

        Args:
            hours_ago: 统计过去多少小时

        Returns:
            晨报文本
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("🌅 V36.2 Morning Report - 晨报")
        report_lines.append("=" * 70)
        report_lines.append(f"⏰ 统计时间范围: 过去 {hours_ago} 小时")
        report_lines.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # 1. 收割成果统计
        report_lines.append("📊 1. 收割成果统计")
        report_lines.append("-" * 40)

        harvest_stats = self.get_harvest_stats(hours_ago)
        report_lines.append(f"   ✅ 成功收割: {harvest_stats['total_harvested']} 场比赛")
        report_lines.append(f"   📆 覆盖天数: {harvest_stats['days_covered']} 天")
        report_lines.append(f"   🏆 覆盖联赛: {harvest_stats['leagues_covered']} 个")
        report_lines.append("")

        # 2. V34.0 特征数据统计
        report_lines.append("📊 2. V34.0 特征数据统计")
        report_lines.append("-" * 40)

        payout_stats = self.get_payout_ratio_stats()
        report_lines.append(f"   总特征记录数: {payout_stats['total_features']}")
        report_lines.append(f"   payout_ratio 非空: {payout_stats['payout_ratio_count']} ({payout_stats['payout_ratio_pct']}%)")
        report_lines.append(f"   movement_velocity 非空: {payout_stats['movement_velocity_count']} ({payout_stats['movement_velocity_pct']}%)")
        report_lines.append("")

        # 3. V36.2 磁盘空间检查
        report_lines.append("💾 3. V36.2 磁盘空间检查")
        report_lines.append("-" * 40)

        disk_stats = self.get_disk_space_stats()
        status_icon = "✅" if disk_stats['status'] == "ok" else "⚠️"
        report_lines.append(f"   {status_icon} 总空间: {disk_stats['total_gb']:.2f} GB")
        report_lines.append(f"   📊 已使用: {disk_stats['used_gb']:.2f} GB ({disk_stats['used_pct']:.1f}%)")
        report_lines.append(f"   📉 剩余: {disk_stats['free_gb']:.2f} GB")

        if disk_stats['status'] == "warning":
            report_lines.append("")
            report_lines.append("   ⚠️  磁盘空间不足警告！")
            report_lines.append("   建议:")
            report_lines.append("      → 清理过期日志文件 (find logs/ -name '*.log' -mtime +7 -delete)")
            report_lines.append("      → 清理旧备份文件 (find backups/ -name '*.sql.gz' -mtime +15 -delete)")
            report_lines.append("      → 检查是否有大文件占用空间 (du -sh * | sort -hr)")

        report_lines.append("")

        # 4. 高返还率比赛列表
        high_payout_matches = self.get_high_payout_matches()
        if high_payout_matches:
            report_lines.append("🎯 4. 高返还率比赛 (Top 10)")
            report_lines.append("-" * 40)
            for i, match in enumerate(high_payout_matches, 1):
                report_lines.append(
                    f"   {i:2}. {match['league_name']:25} | "
                    f"{match['home_team']:20} vs {match['away_team']:<20} | "
                    f"payout={match['payout_ratio']:.4f}"
                )
            report_lines.append("")

        # 5. 建议与结论
        report_lines.append("💡 5. 建议与结论")
        report_lines.append("-" * 40)

        payout_ratio_pct = payout_stats['payout_ratio_pct']

        if payout_ratio_pct >= 50.0:
            report_lines.append("   ✅ 条件满足！payout_ratio 非空比例 >= 50%")
            report_lines.append("")
            report_lines.append("   🚀 建议操作:")
            report_lines.append("      → 可以启动 V36.1 全量重训练")
            report_lines.append("      → 新特征将有足够数据支持模型学习")
            report_lines.append("")
            report_lines.append("   执行命令:")
            report_lines.append("      export DB_NAME=football_db")
            report_lines.append("      python scripts/ml/train_v51_3_full_power.py")
        elif payout_ratio_pct >= 20.0:
            report_lines.append(f"   ⚠️  接近目标！payout_ratio 非空比例 = {payout_ratio_pct}%")
            report_lines.append("")
            report_lines.append("   建议: 继续收集数据，等待达到 50% 阈值")
        else:
            report_lines.append(f"   ❌ 数据不足！payout_ratio 非空比例 = {payout_ratio_pct}%")
            report_lines.append("")
            report_lines.append("   建议:")
            report_lines.append("      → 需要继续运行 harvester_supervisor")
            report_lines.append("      → 确保 odds_history 数据被正确采集")
            report_lines.append("      → 目标阈值: 50%")

        report_lines.append("")
        report_lines.append("=" * 70)

        return "\n".join(report_lines)


def main():
    """主入口"""
    logger.info("🌅 生成 V36.2 晨报...")

    report = MorningReport()

    # 生成过去 12 小时的晨报（默认覆盖一个晚上）
    hours_ago = 12
    report_text = report.generate_report(hours_ago)

    print("\n" + report_text)

    # 保存到日志文件
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    report_file = log_dir / f"morning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_file.write_text(report_text)

    logger.info(f"✅ 晨报已保存: {report_file}")
    logger.info(f"📊 过去 {hours_ago} 小时收割成果统计完成")


if __name__ == "__main__":
    main()
