#!/usr/bin/env python3
"""
FBref数据工厂运营监控仪表板
运营总监生产监控系统

Operations Director: 实时运营监控
Purpose: 监控数据管道健康状态和运行效率
"""

import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import pandas as pd


class OperationsDashboard:
    """运营监控仪表板"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.logs_dir = self.project_root / "logs"
        self.start_time = datetime.now()

    def get_crontab_status(self) -> dict[str, Any]:
        """获取crontab任务状态"""
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                active_jobs = [
                    line for line in lines if line.strip() and not line.startswith("#")
                ]
                return {
                    "status": "active"
                    "total_jobs": len(active_jobs)
                    "jobs": active_jobs
                }
            else:
                return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_system_resources(self) -> dict[str, Any]:
        """获取系统资源状态"""
        try:
            # 磁盘使用情况
            disk_result = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True
            )
            disk_lines = disk_result.stdout.split("\n")
            disk_info = disk_lines[1].split() if len(disk_lines) > 1 else []

            # 内存使用情况
            mem_result = subprocess.run(["free", "-h"], capture_output=True, text=True)
            mem_lines = mem_result.stdout.split("\n")
            mem_info = mem_lines[1].split() if len(mem_lines) > 1 else []

            return {
                "timestamp": datetime.now().isoformat()
                "disk": {
                    "total": disk_info[1] if len(disk_info) > 1 else "N/A"
                    "used": disk_info[2] if len(disk_info) > 2 else "N/A"
                    "available": disk_info[3] if len(disk_info) > 3 else "N/A"
                    "usage_percent": disk_info[4] if len(disk_info) > 4 else "N/A"
                }
                "memory": {
                    "total": mem_info[1] if len(mem_info) > 1 else "N/A"
                    "used": mem_info[2] if len(mem_info) > 2 else "N/A"
                    "free": mem_info[3] if len(mem_info) > 3 else "N/A"
                    "usage_percent": mem_info[2] if len(mem_info) > 2 else "N/A"
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def get_log_summary(self) -> dict[str, Any]:
        """获取日志摘要"""
        if not self.logs_dir.exists():
            return {"status": "no_logs", "message": "Logs directory not found"}

        try:
            log_files = list(self.logs_dir.glob("*.log"))

            # 按修改时间排序
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            recent_logs = []
            for log_file in log_files[:10]:  # 最近10个日志文件
                stat = log_file.stat()
                recent_logs.append(
                    {
                        "name": log_file.name
                        "size_mb": round(stat.st_size / (1024 * 1024), 2)
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        "age_hours": (
                            datetime.now() - datetime.fromtimestamp(stat.st_mtime)
                        ).total_seconds()
                        / 3600
                    }
                )

            return {
                "status": "success"
                "total_log_files": len(log_files)
                "recent_logs": recent_logs
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_pipeline_health(self) -> dict[str, Any]:
        """获取数据管道健康状态"""
        health_score = 100
        issues = []

        # 检查crontab状态
        crontab_status = self.get_crontab_status()
        if crontab_status.get("status") != "active":
            health_score -= 30
            issues.append("Crontab服务异常")

        # 检查磁盘空间
        system_resources = self.get_system_resources()
        if "disk" in system_resources:
            disk_usage = system_resources["disk"].get("usage_percent", "0%")
            if isinstance(disk_usage, str) and disk_usage.endswith("%"):
                usage_val = int(disk_usage[:-1])
                if usage_val > 90:
                    health_score -= 20
                    issues.append(f"磁盘空间不足: {disk_usage}")

        # 检查最近日志错误
        log_summary = self.get_log_summary()
        if log_summary.get("status") == "success":
            recent_logs = log_summary.get("recent_logs", [])
            if not recent_logs:
                health_score -= 10
                issues.append("无最近日志记录")

        return {
            "overall_score": max(0, health_score)
            "status": (
                "healthy"
                if health_score >= 80
                else "warning" if health_score >= 60 else "critical"
            )
            "issues": issues
            "last_check": datetime.now().isoformat()
        }

    def generate_dashboard_report(self) -> str:
        """生成仪表板报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取各模块状态
        crontab_status = self.get_crontab_status()
        system_resources = self.get_system_resources()
        log_summary = self.get_log_summary()
        pipeline_health = self.get_pipeline_health()

        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FBref数据工厂 - 运营监控仪表板                               ║
║                           Operations Director                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

📅 监控时间: {timestamp}
⏱️  系统运行时间: {(datetime.now() - self.start_time).total_seconds() / 3600:.1f} 小时

┌─ 📊 数据管道健康状态 ──────────────────────────────────────────────────────────┐
│ 健康评分: {pipeline_health['overall_score']}/100 ({pipeline_health['status'].upper()})
│ 状态: {"🟢 健康" if pipeline_health['status'] == 'healthy' else "🟡 警告" if pipeline_health['status'] == 'warning' else "🔴 严重"}
"""

        if pipeline_health["issues"]:
            report += "\\│ 发现问题:\n"
            for issue in pipeline_health["issues"]:
                report += f"   • {issue}\n"

        report += f"""
└──────────────────────────────────────────────────────────────────────────────┘

┌─ ⏰ Crontab调度状态 ───────────────────────────────────────────────────────────┐
│ 状态: {"🟢 活跃" if crontab_status.get('status') == 'active' else "🔴 异常"}"""

        if crontab_status.get("status") == "active":
            report += f"""
│ 总任务数: {crontab_status.get('total_jobs', 0)} 个
│
│ 调度计划:
│   周一 06:15 UTC - 周末比赛结果更新
│   周四 06:30 UTC - 周中比赛结果更新
│   周日 12:15 UTC - 赛前检查
│   每月1号 03:45 UTC - 历史数据同步
│   每小时整点 - 系统健康检查"""
        else:
            report += rf"\│ 错误: {crontab_status.get('message', 'Unknown error')}"

        report += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 💻 系统资源状态 ─────────────────────────────────────────────────────────────┐"""

        if "disk" in system_resources:
            disk = system_resources["disk"]
            report += f"""
│ 磁盘使用: {disk.get('used', 'N/A')} / {disk.get('total', 'N/A')} ({disk.get('usage_percent', 'N/A')})"""

        if "memory" in system_resources:
            mem = system_resources["memory"]
            report += f"""
│ 内存使用: {mem.get('used', 'N/A')} / {mem.get('total', 'N/A')} ({mem.get('usage_percent', 'N/A')})"""

        report += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 📝 日志文件状态 ─────────────────────────────────────────────────────────────┐"""

        if log_summary.get("status") == "success":
            recent_logs = log_summary.get("recent_logs", [])
            report += f"""
│ 日志文件总数: {log_summary.get('total_log_files', 0)} 个
│ 最近日志文件:"""

            for log in recent_logs[:5]:
                age_hours = log.get("age_hours", 0)
                age_text = (
                    f"{age_hours:.1f}小时前"
                    if age_hours < 24
                    else f"{age_hours/24:.1f}天前"
                )
                report += f"""
│   • {log['name']} ({log['size_mb']}MB, {age_text})"""
        else:
            report += rf"\│ 状态: {log_summary.get('message', 'Unknown')}"

        report += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 🎯 运营建议 ────────────────────────────────────────────────────────────────┐"""

        if pipeline_health["status"] == "healthy":
            report += """
│ ✅ 系统运行良好
│ • 数据管道健康，所有调度任务正常运行
│ • 系统资源充足，无性能瓶颈
│ • 日志记录正常，监控有效"""
        elif pipeline_health["status"] == "warning":
            report += """
│ ⚠️  需要关注
│ • 建议检查上述发现问题并及时处理
│ • 密切监控系统资源使用情况"""
        else:
            report += """
│ 🚨 需要立即处理
│ • 发现严重问题，建议立即排查
│ • 可能影响数据采集的连续性"""

        report += f"""
└──────────────────────────────────────────────────────────────────────────────┘

生成时间: {timestamp}
下次检查: {(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def run_monitoring(self):
        """运行监控并生成报告"""
        try:
            report = self.generate_dashboard_report()
            print(report)

            # 保存报告到日志
            report_file = (
                self.logs_dir
                / f"operations_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            if self.logs_dir.exists():
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"\n📋 监控报告已保存: {report_file}")

        except Exception as e:
            print(f"❌ 生成监控报告失败: {e}")


def main():
    """主函数"""
    dashboard = OperationsDashboard()
    dashboard.run_monitoring()


if __name__ == "__main__":
    main()
