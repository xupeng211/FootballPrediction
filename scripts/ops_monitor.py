#!/usr/bin/env python3
"""
FBref数据工厂运维监控脚本
SRE + DBA 联合巡检工具

SRE/DBA: 生产系统健康监控专家
Purpose: 全方位监控数据管道健康状态和数据质量
"""

import asyncio
import logging
import sys
import os
import time
import json
import subprocess
import psutil
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入数据库连接
try:
    from src.database.connection import get_async_session
    from src.database.models.match import Match
    from sqlalchemy import text, select, func
    from sqlalchemy.ext.asyncio import AsyncSession

    DB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"数据库模块导入失败: {e}")
    DB_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class OpsMonitor:
    """
    运维监控仪表盘

    监控维度：
    1. 进程健康检查
    2. 日志分析统计
    3. 数据库质量验证
    4. 系统资源状态
    5. 数据采集进度
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.log_file = self.project_root / "logs" / "fbref_final_backfill.log"
        self.process_name = "final_fbref_backfill.py"
        self.check_time = datetime.now()

    def find_process(self) -> Optional[dict]:
        """查找目标进程信息"""
        logger.info(f"🔍 查找进程: {self.process_name}")

        try:
            # 方法1: 通过psutil查找
            for proc in psutil.process_iter(
                [
                    "pid"
                    "name"
                    "cmdline"
                    "cpu_percent"
                    "memory_percent"
                    "create_time"
                ]
            ):
                try:
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if self.process_name in cmdline:
                        return {
                            "pid": proc.info["pid"]
                            "name": proc.info["name"]
                            "cmdline": cmdline
                            "cpu_percent": proc.info["cpu_percent"]
                            "memory_percent": proc.info["memory_percent"]
                            "memory_mb": proc.memory_info().rss / 1024 / 1024
                            "create_time": datetime.fromtimestamp(
                                proc.info["create_time"]
                            )
                            "status": proc.status()
                            "running_time": datetime.now()
                            - datetime.fromtimestamp(proc.info["create_time"])
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 方法2: 通过pgrep查找
            try:
                result = subprocess.run(
                    ["pgrep", "-f", self.process_name], capture_output=True, text=True
                )
                if result.stdout.strip():
                    pids = [int(pid) for pid in result.stdout.strip().split("\n")]
                    for pid in pids:
                        try:
                            proc = psutil.Process(pid)
                            cmdline = " ".join(proc.cmdline() or [])
                            if self.process_name in cmdline:
                                return {
                                    "pid": pid
                                    "name": proc.name()
                                    "cmdline": cmdline
                                    "cpu_percent": proc.cpu_percent()
                                    "memory_percent": proc.memory_percent()
                                    "memory_mb": proc.memory_info().rss / 1024 / 1024
                                    "create_time": datetime.fromtimestamp(
                                        proc.create_time()
                                    )
                                    "status": proc.status()
                                    "running_time": datetime.now()
                                    - datetime.fromtimestamp(proc.create_time())
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            except FileNotFoundError:
                pass

        except Exception as e:
            logger.error(f"❌ 进程查找异常: {e}")

        return None

    def analyze_logs(self) -> dict:
        """分析日志文件"""
        logger.info("📋 分析日志文件...")

        if not self.log_file.exists():
            return {
                "file_exists": False
                "error": "日志文件不存在"
                "last_50_lines": []
                "success_count": 0
                "error_count": 0
                "last_timestamp": None
            }

        try:
            with open(self.log_file, encoding="utf-8") as f:
                lines = f.readlines()

            # 获取最后50行
            last_50_lines = lines[-50:] if len(lines) >= 50 else lines

            # 统计成功和失败次数
            success_count = sum(1 for line in lines if "✅" in line)
            error_count = sum(1 for line in lines if "❌" in line)
            warning_count = sum(1 for line in lines if "⚠️" in line)

            # 提取最后一条有意义的日志时间戳
            last_timestamp = None
            for line in reversed(lines):
                if line.strip() and "INFO" in line:
                    try:
                        # 提取时间戳格式: 2025-12-02 00:38:07
                        timestamp_str = line.split(" [")[0]
                        last_timestamp = datetime.strptime(
                            timestamp_str, "%Y-%m-%d %H:%M:%S"
                        )
                        break
                    except (ValueError, IndexError):
                        continue

            return {
                "file_exists": True
                "total_lines": len(lines)
                "last_50_lines": [line.strip() for line in last_50_lines]
                "success_count": success_count
                "error_count": error_count
                "warning_count": warning_count
                "last_timestamp": last_timestamp
                "log_age_minutes": (
                    (datetime.now() - last_timestamp).total_seconds() / 60
                    if last_timestamp
                    else None
                )
            }

        except Exception as e:
            return {
                "file_exists": True
                "error": str(e)
                "last_50_lines": []
                "success_count": 0
                "error_count": 0
                "last_timestamp": None
            }

    async def check_database(self) -> dict:
        """检查数据库状态和数据质量"""
        logger.info("🗄️ 检查数据库状态...")

        if not DB_AVAILABLE:
            return {
                "connected": False
                "error": "数据库模块不可用"
                "total_matches": 0
                "fbref_matches": 0
                "matches_with_stats": 0
                "matches_with_xg": 0
                "latest_match": None
            }

        try:
            async with get_async_session() as session:
                # 1. 总量统计
                total_result = await session.execute(
                    text("SELECT COUNT(*) FROM matches")
                )
                total_matches = total_result.scalar() or 0

                # 2. FBref数据统计
                fbref_result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM matches WHERE data_source LIKE '%fbref%'"
                    )
                )
                fbref_matches = fbref_result.scalar() or 0

                # 3. 有深度数据的比赛统计
                stats_result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM matches WHERE stats IS NOT NULL OR lineups IS NOT NULL"
                    )
                )
                matches_with_stats = stats_result.scalar() or 0

                # 4. xG数据统计 (检查JSON字段)
                xg_result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM matches WHERE (stats->>'home_xg') IS NOT NULL OR (stats->>'away_xg') IS NOT NULL OR (stats->>'xg_home') IS NOT NULL OR (stats->>'xg_away') IS NOT NULL)"
                    )
                )
                matches_with_xg = xg_result.scalar() or 0

                # 5. 最新入库的比赛
                latest_result = await session.execute(
                    text(
                        """
                        SELECT match_date, home_team, away_team, score, data_source, created_at
                        FROM matches
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    )
                )
                latest_row = latest_result.fetchone()

                latest_match = None
                if latest_row:
                    latest_match = {
                        "match_date": latest_row[0]
                        "home_team": latest_row[1]
                        "away_team": latest_row[2]
                        "score": latest_row[3]
                        "data_source": latest_row[4]
                        "created_at": latest_row[5]
                    }

                # 6. 最近一小时的数据增长
                recent_result = await session.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM matches
                        WHERE created_at >= NOW() - INTERVAL '1 hour'
                    """
                    )
                )
                recent_matches = recent_result.scalar() or 0

                return {
                    "connected": True
                    "total_matches": total_matches
                    "fbref_matches": fbref_matches
                    "matches_with_stats": matches_with_stats
                    "matches_with_xg": matches_with_xg
                    "latest_match": latest_match
                    "recent_matches_1h": recent_matches
                    "fbref_percentage": (
                        (fbref_matches / total_matches * 100)
                        if total_matches > 0
                        else 0
                    )
                    "stats_percentage": (
                        (matches_with_stats / total_matches * 100)
                        if total_matches > 0
                        else 0
                    )
                    "xg_percentage": (
                        (matches_with_xg / total_matches * 100)
                        if total_matches > 0
                        else 0
                    )
                }

        except Exception as e:
            return {
                "connected": False
                "error": str(e)
                "total_matches": 0
                "fbref_matches": 0
                "matches_with_stats": 0
                "matches_with_xg": 0
                "latest_match": None
            }

    def get_system_resources(self) -> dict:
        """获取系统资源状态"""
        try:
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # 内存信息
            memory = psutil.virtual_memory()

            # 磁盘信息
            disk = psutil.disk_usage("/")

            # 网络信息
            network = psutil.net_io_counters()

            return {
                "cpu_percent": cpu_percent
                "cpu_count": cpu_count
                "memory_total_gb": memory.total / (1024**3)
                "memory_used_gb": memory.used / (1024**3)
                "memory_available_gb": memory.available / (1024**3)
                "memory_percent": memory.percent
                "disk_total_gb": disk.total / (1024**3)
                "disk_used_gb": disk.used / (1024**3)
                "disk_free_gb": disk.free / (1024**3)
                "disk_percent": disk.percent
                "network_bytes_sent": network.bytes_sent
                "network_bytes_recv": network.bytes_recv
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate_progress(self, log_analysis: dict, db_stats: dict) -> dict:
        """计算数据采集进度"""
        if not log_analysis.get("success_count", 0):
            return {"estimated_progress": 0, "status": "Not Started"}

        # 基于日志成功次数估算进度
        total_tasks = 15  # 5联赛 × 3赛季
        completed_tasks = log_analysis["success_count"]
        estimated_progress = min(100, (completed_tasks / total_tasks) * 100)

        # 基于数据库数据验证进度
        if db_stats.get("fbref_matches", 0) > 0:
            fbref_matches = db_stats["fbref_matches"]
            expected_matches = total_tasks * 380  # 估算每赛季380场比赛
            db_progress = min(100, (fbref_matches / expected_matches) * 100)

            # 取两种方法的平均值
            final_progress = (estimated_progress + db_progress) / 2
        else:
            final_progress = estimated_progress

        # 判断状态
        if final_progress >= 95:
            status = "Completed"
        elif final_progress >= 50:
            status = "In Progress"
        elif final_progress > 0:
            status = "Starting"
        else:
            status = "Not Started"

        return {
            "estimated_progress": round(final_progress, 1)
            "status": status
            "log_based_progress": round(estimated_progress, 1)
            "db_based_progress": (
                round(db_progress, 1) if db_stats.get("fbref_matches", 0) > 0 else 0
            )
        }

    async def generate_dashboard(self) -> str:
        """生成运维监控仪表盘"""
        logger.info("📊 生成运维监控仪表盘...")

        # 执行各项检查
        process_info = self.find_process()
        log_analysis = self.analyze_logs()
        db_stats = await self.check_database()
        system_resources = self.get_system_resources()
        progress_info = self.calculate_progress(log_analysis, db_stats)

        # 生成报告
        timestamp = self.check_time.strftime("%Y-%m-%d %H:%M:%S")

        dashboard = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FBref数据工厂 - 运维监控仪表盘                               ║
║                           SRE + DBA 联合巡检                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

🕐 巡检时间: {timestamp}
📋 检查范围: 进程健康 | 日志分析 | 数据库质量 | 系统资源

┌─ 🔄 进程健康状态 ─────────────────────────────────────────────────────────────┐"""

        if process_info:
            status_emoji = "🟢" if process_info["status"] == "running" else "🟡"
            dashboard += f"""
│ 状态: {status_emoji} {process_info['status'].upper()}
│ PID: {process_info['pid']}
│ 运行时间: {process_info['running_time']}
│ CPU使用率: {process_info['cpu_percent']:.1f}%
│ 内存使用: {process_info['memory_mb']:.1f} MB ({process_info['memory_percent']:.1f}%)
│ 进程年龄: {process_info['create_time'].strftime('%Y-%m-%d %H:%M:%S')}
│ 命令行: {process_info['cmdline'][:80]}..."""
        else:
            dashboard += """
│ 状态: 🔴 NOT RUNNING
│ 详情: 未找到目标进程 'final_fbref_backfill.py'"""

        dashboard += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 📋 日志分析报告 ─────────────────────────────────────────────────────────────┐"""

        if log_analysis["file_exists"]:
            log_age = log_analysis["log_age_minutes"]
            age_status = "🟢" if log_age < 10 else "🟡" if log_age < 60 else "🔴"

            dashboard += f"""
│ 日志状态: {age_status} 正常
│ 总行数: {log_analysis['total_lines']:,}
│ 成功标记: ✅ {log_analysis['success_count']} 次
│ 失败标记: ❌ {log_analysis['error_count']} 次
│ 警告标记: ⚠️ {log_analysis['warning_count']} 次
│ 最后更新: {log_age:.1f} 分钟前 ({log_analysis['last_timestamp'] or 'Unknown'})"""
        else:
            dashboard += f"""
│ 日志状态: 🔴 文件不存在
│ 错误: {log_analysis.get('error', 'Unknown')}"""

        dashboard += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 🗄️ 数据库质量报告 ───────────────────────────────────────────────────────────┐"""

        if db_stats["connected"]:
            db_status = "🟢" if db_stats["fbref_matches"] > 0 else "🟡"
            dashboard += f"""
│ 数据库连接: {db_status} 正常
│ 总比赛数: {db_stats['total_matches']:,}
│ FBref数据: {db_stats['fbref_matches']:,} ({db_stats['fbref_percentage']:.1f}%)
│ 有统计数据: {db_stats['matches_with_stats']:,} ({db_stats['stats_percentage']:.1f}%)
│ 有xG数据: {db_stats['matches_with_xg']:,} ({db_stats['xg_percentage']:.1f}%)"""

            if db_stats["latest_match"]:
                latest = db_stats["latest_match"]
                dashboard += f"""
│ 最新入库: {latest['match_date']} {latest['home_team']} vs {latest['away_team']} ({latest['score']})
│ 数据来源: {latest['data_source']}"""

            dashboard += f"""
│ 最近1小时: +{db_stats['recent_matches_1h']} 场比赛"""
        else:
            dashboard += f"""
│ 数据库连接: 🔴 失败
│ 错误: {db_stats.get('error', 'Unknown')}"""

        dashboard += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 📈 采集进度评估 ─────────────────────────────────────────────────────────────┐"""

        progress_status = progress_info["status"]
        progress_emoji = {
            "Completed": "🟢"
            "In Progress": "🟡"
            "Starting": "🟠"
            "Not Started": "🔴"
        }.get(progress_status, "⚪")

        dashboard += f"""
│ 整体进度: {progress_emoji} {progress_info['estimated_progress']}% ({progress_status})
│ 基于日志: {progress_info['log_based_progress']}%
│ 基于数据库: {progress_info['db_based_progress']}%
│ 预计剩余: {(100 - progress_info['estimated_progress']) / 20 * 5:.1f} 分钟 (估算)"""

        dashboard += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 💻 系统资源状态 ────────────────────────────────────────────────────────────┐"""

        if "error" not in system_resources:
            cpu_status = (
                "🟢"
                if system_resources["cpu_percent"] < 80
                else "🟡" if system_resources["cpu_percent"] < 90 else "🔴"
            )
            mem_status = (
                "🟢"
                if system_resources["memory_percent"] < 80
                else "🟡" if system_resources["memory_percent"] < 90 else "🔴"
            )
            disk_status = (
                "🟢"
                if system_resources["disk_percent"] < 80
                else "🟡" if system_resources["disk_percent"] < 90 else "🔴"
            )

            dashboard += f"""
│ CPU: {cpu_status} {system_resources['cpu_percent']:.1f}% ({system_resources['cpu_count']} 核)
│ 内存: {mem_status} {system_resources['memory_used_gb']:.1f}GB / {system_resources['memory_total_gb']:.1f}GB ({system_resources['memory_percent']:.1f}%)
│ 磁盘: {disk_status} {system_resources['disk_used_gb']:.1f}GB / {system_resources['disk_total_gb']:.1f}GB ({system_resources['disk_percent']:.1f}%)
│ 可用内存: {system_resources['memory_available_gb']:.1f}GB"""
        else:
            dashboard += f"""
│ 系统监控: 🔴 异常
│ 错误: {system_resources['error']}"""

        dashboard += """
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 🎯 SRE建议 ───────────────────────────────────────────────────────────────────┐"""

        recommendations = []

        if not process_info:
            recommendations.append("🚨 立即重启数据采集进程")

        if log_analysis.get("log_age_minutes", 0) > 30:
            recommendations.append("⚠️ 检查进程是否假死")

        if db_stats.get("fbref_percentage", 0) == 0:
            recommendations.append("📊 确认数据是否成功入库")

        if system_resources.get("memory_percent", 0) > 85:
            recommendations.append("💾 内存使用过高，建议优化")

        if system_resources.get("disk_percent", 0) > 85:
            recommendations.append("💿 磁盘空间不足")

        if recommendations:
            for rec in recommendations:
                dashboard += f"│ {rec}\n"
        else:
            dashboard += "│ ✅ 系统运行正常，无需干预\n"

        dashboard += f"""└──────────────────────────────────────────────────────────────────────────────┘

📊巡检完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄下次巡检建议: {(datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')}
"""

        return dashboard

    async def run_monitoring(self):
        """运行完整的运维监控"""
        logger.info("🚀 启动FBref数据工厂运维监控")

        try:
            dashboard = await self.generate_dashboard()
            print(dashboard)

            # 保存监控报告
            report_file = (
                self.project_root
                / "logs"
                / f'ops_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(dashboard)

            logger.info(f"📋 监控报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"❌ 监控执行失败: {e}")
            import traceback

            traceback.print_exc()


async def main():
    """主函数"""
    monitor = OpsMonitor()
    await monitor.run_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
