#!/usr/bin/env python3
"""
维护日志系统
Maintenance Logger System

用于记录和跟踪目录维护的历史记录

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class MaintenanceRecord:
    """维护记录数据结构"""
    timestamp: str
    action_type: str
    description: str
    files_affected: int
    size_freed_mb: float
    issues_found: int
    issues_fixed: int
    health_score_before: int
    health_score_after: int
    execution_time_seconds: float
    success: bool
    error_message: str | None = None

class MaintenanceLogger:
    """维护日志记录器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logs_dir = project_root / "logs" / "maintenance"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 数据库文件路径
        self.db_path = self.logs_dir / "maintenance_history.db"
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建维护记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT,
                files_affected INTEGER DEFAULT 0,
                size_freed_mb REAL DEFAULT 0.0,
                issues_found INTEGER DEFAULT 0,
                issues_fixed INTEGER DEFAULT 0,
                health_score_before INTEGER DEFAULT 0,
                health_score_after INTEGER DEFAULT 0,
                execution_time_seconds REAL DEFAULT 0.0,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建健康趋势表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                health_score INTEGER NOT NULL,
                root_files INTEGER DEFAULT 0,
                python_files INTEGER DEFAULT 0,
                markdown_files INTEGER DEFAULT 0,
                total_size_mb REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def log_maintenance(self, record: MaintenanceRecord) -> bool:
        """记录维护活动"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO maintenance_records
                (timestamp, action_type, description, files_affected, size_freed_mb,
                 issues_found, issues_fixed, health_score_before, health_score_after,
                 execution_time_seconds, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.timestamp,
                record.action_type,
                record.description,
                record.files_affected,
                record.size_freed_mb,
                record.issues_found,
                record.issues_fixed,
                record.health_score_before,
                record.health_score_after,
                record.execution_time_seconds,
                record.success,
                record.error_message
            ))

            conn.commit()
            conn.close()
            return True

        except Exception:
            return False

    def log_health_snapshot(self, health_report: dict[str, Any]):
        """记录健康快照"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = health_report.get("statistics", {})
            cursor.execute('''
                INSERT INTO health_trends
                (timestamp,
    health_score,
    root_files,
    python_files,
    markdown_files,
    total_size_mb)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                health_report.get("timestamp"),
                health_report.get("health_score"),
                stats.get("root_files"),
                stats.get("python_files"),
                stats.get("markdown_files"),
                stats.get("total_size_mb")
            ))

            conn.commit()
            conn.close()

        except Exception:
            pass

    def get_maintenance_history(self, days: int = 30) -> list[dict[str, Any]]:
        """获取维护历史记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute('''
                SELECT * FROM maintenance_records
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (cutoff_date,))

            columns = [desc[0] for desc in cursor.description]
            records = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

            conn.close()
            return records

        except Exception:
            return []

    def get_health_trends(self, days: int = 30) -> list[dict[str, Any]]:
        """获取健康趋势数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute('''
                SELECT * FROM health_trends
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (cutoff_date,))

            columns = [desc[0] for desc in cursor.description]
            trends = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

            conn.close()
            return trends

        except Exception:
            return []

    def generate_maintenance_report(self, days: int = 7) -> dict[str, Any]:
        """生成维护报告"""
        maintenance_history = self.get_maintenance_history(days)
        health_trends = self.get_health_trends(days)

        # 统计维护活动
        total_maintenance = len(maintenance_history)
        successful_maintenance = len([r for r in maintenance_history if r["success"]])
        total_files_affected = sum(r["files_affected"] for r in maintenance_history)
        total_size_freed = sum(r["size_freed_mb"] for r in maintenance_history)
        total_issues_fixed = sum(r["issues_fixed"] for r in maintenance_history)

        # 健康趋势分析
        if health_trends:
            latest_health = health_trends[-1]["health_score"]
            earliest_health = health_trends[0]["health_score"]
            health_change = latest_health - earliest_health
        else:
            latest_health = 0
            health_change = 0

        # 最近的活动
        recent_activities = maintenance_history[:5]

        report = {
            "report_period_days": days,
            "generated_at": datetime.now().isoformat(),
            "maintenance_summary": {
                "total_maintenance_activities": total_maintenance,
                "successful_activities": successful_maintenance,
                "success_rate": round(successful_maintenance / total_maintenance * 100,
    2) if total_maintenance > 0 else 0,

                "total_files_affected": total_files_affected,
                "total_size_freed_mb": round(total_size_freed, 2),
                "total_issues_fixed": total_issues_fixed
            },
            "health_analysis": {
                "current_health_score": latest_health,
                "health_score_change": health_change,
                "health_trend": "improving" if health_change > 0 else "declining" if health_change < 0 else "stable"
            },
            "recent_activities": recent_activities,
            "health_trends": health_trends[-10:] if health_trends else []  # 最近10个数据点
        }

        return report

    def save_maintenance_report(self, report: dict[str, Any]) -> Path:
        """保存维护报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.logs_dir / f"maintenance_report_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report_file

    def cleanup_old_logs(self, days_to_keep: int = 90):
        """清理旧的日志文件"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0

        # 清理旧的JSON日志文件
        for log_file in self.logs_dir.glob("*.json"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                log_file.unlink()
                cleaned_count += 1

        # 清理数据库中的旧记录
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_str = cutoff_date.isoformat()
            cursor.execute('DELETE FROM maintenance_records WHERE timestamp < ?',
    (cutoff_str,
    ))
            cursor.execute('DELETE FROM health_trends WHERE timestamp < ?',
    (cutoff_str,
    ))

            conn.commit()
            conn.close()

        except Exception:
            pass


def main():
    """主函数 - 用于测试"""
    project_root = Path(__file__).parent.parent.parent
    logger = MaintenanceLogger(project_root)

    # 生成测试记录
    test_record = MaintenanceRecord(
        timestamp=datetime.now().isoformat(),
        action_type="test_maintenance",
        description="测试维护活动",
        files_affected=10,
        size_freed_mb=2.5,
        issues_found=3,
        issues_fixed=2,
        health_score_before=75,
        health_score_after=85,
        execution_time_seconds=12.5,
        success=True
    )

    # 记录测试数据
    logger.log_maintenance(test_record)

    # 生成报告
    report = logger.generate_maintenance_report(7)
    logger.save_maintenance_report(report)


if __name__ == "__main__":
    main()
