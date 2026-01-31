#!/usr/bin/env python3
"""
总攻作战室监控仪表盘 - War Room Monitor Dashboard

V147.5 生产环境实时监控系统

功能：
- 每60秒自动刷新收割进度
- 实时统计：已收割总数、L2数据覆盖率、出口IP状态
- 美化展示：Rich库 + ASCII表格 + 进度条
- 目标：5884场比赛收割完成

Usage:
    python scripts/maintenance/monitor_war_room.py

Author: Senior SRE (War Room Commander)
Date: 2026-01-06
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
except ImportError:
    print("⚠️  Rich 库未安装，使用基础输出模式")
    print("   安装: pip install rich")
    USE_RICH = False
else:
    USE_RICH = True

import psycopg2
from psycopg2.extras import RealDictCursor
import requests


class WarRoomMonitor:
    """总攻作战室监控器"""

    def __init__(self):
        self.console = Console() if USE_RICH else None
        self.harvest_target = 5884  # 目标收割数量
        self.refresh_interval = 60  # 刷新间隔（秒）

    def get_db_connection(self):
        """获取数据库连接"""
        try:
            from src.config_unified import get_settings
            settings = get_settings()

            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return None

    def get_harvest_statistics(self):
        """获取收割统计信息"""
        conn = self.get_db_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()

            # 1. 总收割数量
            cursor.execute("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(l2_raw_json) as l2_collected,
                    AVG(octet_length(l2_raw_json::text)) as avg_l2_size_bytes
                FROM matches
                WHERE match_time >= '2024-01-01'
            """)
            harvest_stats = cursor.fetchone()

            # 2. L3 数据收集统计
            cursor.execute("""
                SELECT
                    data_source,
                    COUNT(*) as records,
                    AVG(final_home_odds) as avg_home_odds
                FROM metrics_multi_source_data
                WHERE collected_at >= NOW() - INTERVAL '24 hours'
                GROUP BY data_source
            """)
            l3_stats = cursor.fetchall()

            # 3. 最近收割活动
            cursor.execute("""
                SELECT
                    DATE_TRUNC('hour', match_time) as hour,
                    COUNT(*) as matches_added
                FROM matches
                WHERE match_time >= NOW() - INTERVAL '24 hours'
                GROUP BY hour
                ORDER BY hour DESC
                LIMIT 24
            """)
            recent_activity = cursor.fetchall()

            cursor.close()
            conn.close()

            return {
                "harvest": harvest_stats,
                "l3": l3_stats,
                "activity": recent_activity
            }
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return None

    def check_ip_reputation(self):
        """检查出口IP状态"""
        try:
            # 检查本地IP
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if response.status_code == 200:
                local_ip = response.json().get('ip', 'Unknown')
            else:
                local_ip = 'Unknown'
        except:
            local_ip = 'Unknown'

        # 检查数据库连接IP
        conn = self.get_db_connection()
        db_status = "🟢 Connected" if conn else "🔴 Disconnected"
        if conn:
            conn.close()

        return {
            "local_ip": local_ip,
            "db_status": db_status,
            "status": "🟢 HEALTHY" if local_ip != 'Unknown' else "🟡 CHECKING"
        }

    def build_rich_dashboard(self, stats, ip_status):
        """构建 Rich 仪表盘"""
        layout = Layout()

        # 标题区域
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        # Header
        header_text = Text()
        header_text.append("🎯 总攻作战室监控仪表盘 ", style="bold red")
        header_text.append(f"V147.5", style="bold cyan")
        header_text.append(" | ", style="white")
        header_text.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

        layout["header"].update(Panel(
            header_text,
            style="bold white on blue",
            padding=(0, 1)
        ))

        # Body - 分为左右两列
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        # 左侧：收割进度
        if stats and stats["harvest"]:
            total = stats["harvest"]["total_matches"] or 0
            l2 = stats["harvest"]["l2_collected"] or 0
            l2_size = (stats["harvest"]["avg_l2_size_bytes"] or 0) / 1024

            progress_text = Text()
            progress_text.append(f"收割进度: {total}/{self.harvest_target}\n", style="bold cyan")
            progress_text.append(f"L2数据: {l2} ({l2/total*100 if total > 0 else 0:.1f}%)\n", style="green")
            progress_text.append(f"平均大小: {l2_size:.1f} KB", style="dim")

            layout["left"].update(Panel(
                progress_text,
                title="📊 收割统计",
                border_style="cyan"
            ))

        # 右侧：IP状态
        ip_text = Text()
        ip_text.append(f"出口IP: {ip_status['local_ip']}\n", style="bold cyan")
        ip_text.append(f"数据库: {ip_status['db_status']}\n", style="white")
        ip_text.append(f"状态: {ip_status['status']}", style="bold green")

        layout["right"].update(Panel(
            ip_text,
            title="🌐 网络状态",
            border_style="green"
        ))

        # Footer - 操作提示
        footer_text = Text()
        footer_text.append("按 ", style="dim")
        footer_text.append("Ctrl+C", style="bold red")
        footer_text.append(" 退出监控 | 刷新间隔: 60秒 | ", style="dim")
        footer_text.append("目标: 5884场比赛", style="bold yellow")

        layout["footer"].update(Panel(
            footer_text,
            style="dim white"
        ))

        return layout

    def build_ascii_dashboard(self, stats, ip_status):
        """构建 ASCII 仪表盘（备用）"""
        print("\n" + "="*60)
        print("🎯 总攻作战室监控仪表盘 V147.5")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        if stats and stats["harvest"]:
            total = stats["harvest"]["total_matches"] or 0
            l2 = stats["harvest"]["l2_collected"] or 0
            progress = (total / self.harvest_target) * 100

            print(f"\n📊 收割统计:")
            print(f"   进度: {total}/{self.harvest_target} ({progress:.1f}%)")
            print(f"   L2数据: {l2} ({l2/total*100 if total > 0 else 0:.1f}%)")

            # 进度条
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"   [{bar}]")

        print(f"\n🌐 网络状态:")
        print(f"   出口IP: {ip_status['local_ip']}")
        print(f"   数据库: {ip_status['db_status']}")
        print(f"   状态: {ip_status['status']}")

        print(f"\n💡 操作: 按 Ctrl+C 退出 | 刷新间隔: 60秒")
        print("="*60 + "\n")

    def run_once(self):
        """运行一次监控检查"""
        stats = self.get_harvest_statistics()
        ip_status = self.check_ip_reputation()

        if USE_RICH:
            layout = self.build_rich_dashboard(stats, ip_status)
            return layout
        else:
            self.build_ascii_dashboard(stats, ip_status)
            return None

    def run_continuous(self):
        """持续运行监控"""
        if USE_RICH:
            with Live(self.run_once(), refresh_per_second=1) as live:
                try:
                    iteration = 0
                    while True:
                        iteration += 1
                        time.sleep(self.refresh_interval)

                        layout = self.run_once()
                        live.update(layout)

                except KeyboardInterrupt:
                    self.console.print("\n\n👋 监控已停止", style="bold yellow")
        else:
            try:
                while True:
                    self.run_once()
                    time.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                print("\n\n👋 监控已停止")

    def run(self):
        """启动监控"""
        if USE_RICH:
            self.console.print("[bold cyan]🎯 启动总攻作战室监控仪表盘...[/bold cyan]")
            self.console.print("[dim]每 60 秒刷新一次数据[/dim]\n")
        else:
            print("🎯 启动总攻作战室监控仪表盘...")
            print("每 60 秒刷新一次数据\n")

        self.run_continuous()


def main():
    """主函数"""
    monitor = WarRoomMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
