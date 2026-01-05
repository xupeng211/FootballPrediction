#!/usr/bin/env python3
"""
FootballPrediction V139.0 - 实时监控看板
============================================

一个轻量级监控脚本，为 V139.0 自动巡航控制器提供实时可视化反馈。

功能：
- L2 层链接补全率监控
- L3 层赔率转化率监控
- 进程心跳状态检测
- 最近入库记录质量追溯
- 自动刷新（30秒间隔）

使用：
    python scripts/dashboard.py

依赖：
    pip install rich psycopg2-binary psutil

作者：V139.0 DevOps Team
创建：2026-01-05
"""

import asyncio
import os
import sys
import time
import signal
from datetime import datetime
from typing import Optional, Dict, List, Any

import psycopg2
from psycopg2.extras import RealDictCursor
import psutil

# Rich 库用于终端美化
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align
    from rich.text import Text
    from rich.columns import Columns
    from rich.rule import Rule
except ImportError:
    print("⚠️  警告: 未安装 rich 库，使用 ASCII 模式")
    print("   安装: pip install rich")
    Console = None

# =============================================================================
# 配置
# =============================================================================

# 刷新间隔（秒）
REFRESH_INTERVAL = 30

# 数据库连接配置（从环境变量或默认值）
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'football_db'),
    'user': os.getenv('DB_USER', 'football_user'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# 进程名称
TARGET_PROCESS = 'v139_0_auto_cruise_controller.py'

# =============================================================================
# 数据库连接
# =============================================================================


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        return None


# =============================================================================
# 数据采集逻辑
# =============================================================================


def fetch_url_completion_stats(conn) -> Dict[str, Any]:
    """
    查询 matches 表中 URL 的补全情况

    Returns:
        Dict containing:
        - total_urls: 总比赛数
        - new_format_urls: 新格式 URL 数量
        - missing_urls: 空缺 URL 数量
        - completion_rate: 补全率 (百分比)
    """
    try:
        with conn.cursor() as cur:
            # 总比赛数
            cur.execute("""
                SELECT COUNT(*) as total
                FROM matches
            """)
            total = cur.fetchone()['total']

            # 新格式 URL 数量（URL 包含 /football/）
            cur.execute("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE odds_portal_url IS NOT NULL
                  AND odds_portal_url LIKE '%/football/%'
            """)
            new_format = cur.fetchone()['count']

            # 空缺 URL 数量
            cur.execute("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE odds_portal_url IS NULL
            """)
            missing = cur.fetchone()['count']

            completion_rate = (new_format / total * 100) if total > 0 else 0

            return {
                'total_urls': total,
                'new_format_urls': new_format,
                'missing_urls': missing,
                'completion_rate': completion_rate,
            }
    except Exception as e:
        return {
            'total_urls': 0,
            'new_format_urls': 0,
            'missing_urls': 0,
            'completion_rate': 0,
        }


def fetch_pinnacle_stats(conn) -> Dict[str, Any]:
    """
    查询 metrics_multi_source_data 中 Entity_P 的记录统计

    Returns:
        Dict containing:
        - total_records: Entity_P 总记录数
        - with_opening_time: 有开盘时间的记录数
        - avg_integrity_score: 平均完整性评分
    """
    try:
        with conn.cursor() as cur:
            # 总记录数
            cur.execute("""
                SELECT COUNT(*) as count
                FROM metrics_multi_source_data
                WHERE source_name = 'Entity_P'
            """)
            total = cur.fetchone()['count']

            # 有开盘时间的记录数
            cur.execute("""
                SELECT COUNT(*) as count
                FROM metrics_multi_source_data
                WHERE source_name = 'Entity_P'
                  AND opening_time_h IS NOT NULL
            """)
            with_opening = cur.fetchone()['count']

            # 平均完整性评分
            cur.execute("""
                SELECT AVG(integrity_score) as avg_score
                FROM metrics_multi_source_data
                WHERE source_name = 'Entity_P'
                  AND integrity_score IS NOT NULL
            """)
            result = cur.fetchone()
            avg_score = result['avg_score'] if result and result['avg_score'] else 0

            return {
                'total_records': total,
                'with_opening_time': with_opening,
                'avg_integrity_score': round(avg_score, 4) if avg_score else 0,
            }
    except Exception as e:
        return {
            'total_records': 0,
            'with_opening_time': 0,
            'avg_integrity_score': 0,
        }


def fetch_recent_records(conn, limit: int = 5) -> List[Dict[str, Any]]:
    """
    提取最近入库的记录及其 integrity_score

    Args:
        limit: 返回记录数量

    Returns:
        List of recent records
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_time,
                    msd.source_name,
                    msd.opening_time_h,
                    msd.integrity_score
                FROM metrics_multi_source_data msd
                JOIN matches m ON msd.match_id = m.match_id
                WHERE msd.source_name = 'Entity_P'
                ORDER BY msd.created_at DESC NULLS LAST
                LIMIT %s
            """, (limit,))
            return cur.fetchall()
    except Exception as e:
        return []


def check_process_status() -> Dict[str, Any]:
    """
    检测 v139_0_auto_cruise_controller.py 进程状态

    Returns:
        Dict containing:
        - is_running: 是否运行中
        - pid: 进程 ID (如果运行中)
        - cpu_percent: CPU 使用率
        - memory_mb: 内存使用 (MB)
    """
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and TARGET_PROCESS in ' '.join(cmdline):
                    return {
                        'is_running': True,
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'is_running': False,
            'pid': None,
            'cpu_percent': 0,
            'memory_mb': 0,
        }
    except Exception:
        return {
            'is_running': False,
            'pid': None,
            'cpu_percent': 0,
            'memory_mb': 0,
        }


# =============================================================================
# 可视化界面
# =============================================================================


def create_progress_bar(label: str, current: int, total: int, color: str = "blue") -> str:
    """创建简单的 ASCII 进度条"""
    if total == 0:
        percentage = 0
    else:
        percentage = (current / total) * 100

    bar_width = 30
    filled = int(bar_width * percentage / 100)
    bar = '█' * filled + '░' * (bar_width - filled)

    return f"{label}: [{bar}] {percentage:.1f}% ({current}/{total})"


def render_dashboard(console: Optional[Console] = None):
    """
    渲染监控看板

    Args:
        console: Rich Console 实例（如果使用 Rich）
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取数据
    conn = get_db_connection()
    if conn:
        url_stats = fetch_url_completion_stats(conn)
        pinnacle_stats = fetch_pinnacle_stats(conn)
        recent_records = fetch_recent_records(conn)
        conn.close()
    else:
        url_stats = {'total_urls': 0, 'new_format_urls': 0, 'missing_urls': 0, 'completion_rate': 0}
        pinnacle_stats = {'total_records': 0, 'with_opening_time': 0, 'avg_integrity_score': 0}
        recent_records = []

    process_status = check_process_status()

    # 使用 Rich 或 ASCII 模式渲染
    if Console and console:
        render_with_rich(console, timestamp, url_stats, pinnacle_stats, process_status, recent_records)
    else:
        render_ascii(timestamp, url_stats, pinnacle_stats, process_status, recent_records)


def render_with_rich(console: Console, timestamp: str, url_stats: Dict,
                     pinnacle_stats: Dict, process_status: Dict, recent_records: List):
    """使用 Rich 库渲染看板"""
    console.clear()

    # 标题
    title = Panel(
        Align.center(Text.assemble(
            ("FootballPrediction ", "bold cyan"),
            ("V139.0", "bold yellow"),
            (" 实时监控看板", "bold white")
        )),
        style="on dark_blue",
        padding=(0, 2)
    )
    console.print(title)

    # 状态卡片
    status_color = "green" if process_status['is_running'] else "red"
    status_text = "🟢 运行中" if process_status['is_running'] else "🔴 已停止"

    status_panel = Panel(
        f"[{status_color} bold]{status_text}[/{status_color} bold]\n\n"
        f"PID: {process_status['pid'] or 'N/A'}\n"
        f"CPU: {process_status['cpu_percent']:.1f}%\n"
        f"内存: {process_status['memory_mb']:.1f} MB",
        title="🚀 V139.0 进程状态",
        border_style=status_color
    )
    console.print(status_panel)

    console.print(Rule(style="dim"))

    # L2 层链接补全进度
    l2_progress = Text()
    l2_progress.append("L2 层链接补全率", style="bold cyan")
    l2_progress.append(f"\n{url_stats['completion_rate']:.1f}%", style="bold yellow")
    l2_progress.append(f"\n总计: {url_stats['total_urls']:,} | 新格式: {url_stats['new_format_urls']:,} | 空缺: {url_stats['missing_urls']:,}")

    l2_panel = Panel(
        l2_progress,
        title="📊 L2: URL Harvest",
        border_style="cyan"
    )
    console.print(l2_panel)

    # L3 层赔率转化进度
    conversion_rate = (pinnacle_stats['with_opening_time'] / pinnacle_stats['total_records'] * 100) if pinnacle_stats['total_records'] > 0 else 0
    l3_progress = Text()
    l3_progress.append("L3 层赔率转化率", style="bold magenta")
    l3_progress.append(f"\n{conversion_rate:.1f}%", style="bold yellow")
    l3_progress.append(f"\nEntity_P 记录: {pinnacle_stats['total_records']:,} | 有开盘时间: {pinnacle_stats['with_opening_time']:,}")

    l3_panel = Panel(
        l3_progress,
        title="💰 L3: RPA Extraction",
        border_style="magenta"
    )
    console.print(l3_panel)

    console.print(Rule(style="dim"))

    # 最近入库记录
    if recent_records:
        table = Table(title="📝 最近入库记录 (Top 5)", show_header=True, header_style="bold magenta")
        table.add_column("比赛 ID", style="dim", width=12)
        table.add_column("对阵", style="cyan")
        table.add_column("开盘时间", style="green")
        table.add_column("完整性", style="yellow")

        for record in recent_records:
            match_id = record.get('match_id', 'N/A')[:12]
            teams = f"{record.get('home_team', '?')} vs {record.get('away_team', '?')}"
            opening = record.get('opening_time_h') or 'N/A'
            integrity = record.get('integrity_score')
            integrity_str = f"{integrity:.4f}" if integrity else "N/A"

            table.add_row(match_id, teams, str(opening), integrity_str)

        console.print(table)

    # 平均完整性评分
    avg_score_panel = Panel(
        Text(f"{pinnacle_stats['avg_integrity_score']:.4f}", style="bold green", justify="center"),
        title="📈 平均完整性评分",
        border_style="green"
    )
    console.print(avg_score_panel)

    # 底部信息
    footer = Text.assemble(
        ("最后更新: ", "dim"),
        (timestamp, "cyan"),
        (" | 刷新间隔: ", "dim"),
        (f"{REFRESH_INTERVAL}秒", "yellow"),
        (" | 按 ", "dim"),
        ("Ctrl+C", "bold red"),
        (" 退出", "dim")
    )
    console.print(Align.center(footer))


def render_ascii(timestamp: str, url_stats: Dict, pinnacle_stats: Dict,
                 process_status: Dict, recent_records: List):
    """使用 ASCII 模式渲染看板"""
    os.system('clear' if os.name == 'posix' else 'cls')

    print("=" * 80)
    print(" " * 20 + "FootballPrediction V139.0 实时监控看板")
    print("=" * 80)
    print()

    # 进程状态
    status = "🟢 运行中" if process_status['is_running'] else "🔴 已停止"
    print(f"┌─ 🚀 V139.0 进程状态 {'─' * 52}┐")
    print(f"│ 状态: {status:<65} │")
    if process_status['is_running']:
        print(f"│ PID: {process_status['pid']:<65} │")
        print(f"│ CPU: {process_status['cpu_percent']:.1f}%{' ' * (64 - len(f'CPU: {process_status['cpu_percent']:.1f}%'))}│")
        print(f"│ 内存: {process_status['memory_mb']:.1f} MB{' ' * (64 - len(f'内存: {process_status['memory_mb']:.1f} MB'))}│")
    print(f"└{'─' * 78}┘")
    print()

    # L2 层链接补全
    l2_bar = create_progress_bar("L2 链接补全", url_stats['new_format_urls'], url_stats['total_urls'], "cyan")
    print(f"┌─ 📊 L2: URL Harvest {'─' * 51}┐")
    print(f"│ {l2_bar:<76} │")
    print(f"│ {'总计: ' + str(url_stats['total_urls']) + ' | 新格式: ' + str(url_stats['new_format_urls']) + ' | 空缺: ' + str(url_stats['missing_urls']):<76} │")
    print(f"└{'─' * 78}┘")
    print()

    # L3 层赔率转化
    conversion_rate = (pinnacle_stats['with_opening_time'] / pinnacle_stats['total_records'] * 100) if pinnacle_stats['total_records'] > 0 else 0
    l3_bar = create_progress_bar("L3 赔率转化", pinnacle_stats['with_opening_time'], pinnacle_stats['total_records'], "magenta")
    print(f"┌─ 💰 L3: RPA Extraction {'─' * 48}┐")
    print(f"│ {l3_bar:<76} │")
    print(f"│ {f'Entity_P 记录: {pinnacle_stats[\"total_records\"]:,} | 有开盘时间: {pinnacle_stats[\"with_opening_time\"]:,}':<76} │")
    print(f"└{'─' * 78}┘")
    print()

    # 最近入库记录
    if recent_records:
        print(f"┌─ 📝 最近入库记录 (Top 5) {'─' * 47}┐")
        print(f"│ {'比赛 ID':<12} | {'对阵':<30} | {'开盘时间':<12} | {'完整性':<8} │")
        print(f"├{'─' * 12}─┼{'─' * 32}─┼{'─' * 14}─┼{'─' * 10}┤")

        for record in recent_records:
            match_id = str(record.get('match_id', 'N/A'))[:10]
            teams = f"{record.get('home_team', '?')} vs {record.get('away_team', '?')}"[:28]
            opening = str(record.get('opening_time_h') or 'N/A')[:10]
            integrity = record.get('integrity_score')
            integrity_str = f"{integrity:.4f}" if integrity else "N/A"

            print(f"│ {match_id:<12} | {teams:<30} | {opening:<12} | {integrity_str:<8} │")

        print(f"└{'─' * 78}┘")
        print()

    # 平均完整性评分
    print(f"┌─ 📈 平均完整性评分 {'─' * 53}┐")
    print(f"│  {pinnacle_stats['avg_integrity_score']:.4f}{' ' * (74 - len(f'{pinnacle_stats[\"avg_integrity_score\"]:.4f}'))}│")
    print(f"└{'─' * 78}┘")
    print()

    # 底部信息
    print(f"{'─' * 80}")
    print(f"最后更新: {timestamp} | 刷新间隔: {REFRESH_INTERVAL}秒 | 按 Ctrl+C 退出")
    print(f"{'─' * 80}")


# =============================================================================
# 主程序
# =============================================================================


def signal_handler(signum, frame):
    """处理退出信号"""
    print("\n\n👋 监控看板已关闭。V139.0 任务继续在后台运行...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)

    # 确定使用哪个 Console
    use_rich = Console is not None
    console = Console() if use_rich else None

    if use_rich:
        print("🚀 启动 FootballPrediction V139.0 实时监控看板...")
        print("   使用 Rich 库渲染界面")
    else:
        print("🚀 启动 FootballPrediction V139.0 实时监控看板...")
        print("   ⚠️  未检测到 Rich 库，使用 ASCII 模式")
        print("   提示: 安装 Rich 获得更好体验: pip install rich")
    print(f"   刷新间隔: {REFRESH_INTERVAL} 秒")
    print("   按 Ctrl+C 退出\n")

    time.sleep(2)

    # 主循环
    try:
        while True:
            render_dashboard(console)

            if not use_rich:
                # ASCII 模式需要等待
                time.sleep(REFRESH_INTERVAL)
            else:
                # Rich 模式使用 Live 更新（简化版：仍然清屏重绘）
                time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
