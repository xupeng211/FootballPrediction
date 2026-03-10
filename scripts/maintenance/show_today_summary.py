#!/usr/bin/env python3
"""
TITAN 今日作战简报
==================

V4.46.8 监控看板 - 终端可视化简报

功能:
    1. 读取当日 JSON 结果文件
    2. 解析日志关键信息
    3. 生成终端友好的作战简报

使用方式:
    python scripts/maintenance/show_today_summary.py
    python scripts/maintenance/show_today_summary.py --watch  # 实时监控模式

@module scripts.maintenance.show_today_summary
@version V4.46.8
@updated 2026-03-11
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 路径配置
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
PREDICTIONS_DIR = PROJECT_ROOT / "predictions"


# ============================================================================
# ANSI 颜色
# ============================================================================

class C:
    """ANSI 颜色代码"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # 背景色
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


# ============================================================================
# 简报生成器
# ============================================================================

class TodaySummary:
    """今日作战简报生成器"""

    def __init__(self):
        self.today = datetime.now().strftime("%Y%m%d")
        self.now = datetime.now()

    def clear_screen(self):
        """清屏"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def get_cruise_reports(self) -> List[Dict]:
        """获取今日巡航报告"""
        reports = []
        if not LOG_DIR.exists():
            return reports

        for f in LOG_DIR.glob(f"cruise_report_{self.today}*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    reports.append(json.load(fp))
            except Exception:
                pass

        return sorted(reports, key=lambda x: x.get("started_at", ""))

    def get_prediction_results(self) -> List[Dict]:
        """获取今日预测结果"""
        predictions = []

        # 从日志中解析 JSON 输出
        if not LOG_DIR.exists():
            return predictions

        for f in LOG_DIR.glob("*.log"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    content = fp.read()

                # 尝试解析 JSON 块
                for line in content.split("\n"):
                    if '"predictions"' in line and '"total_matches"' in line:
                        try:
                            # 提取 JSON 部分
                            start = line.find("{")
                            if start >= 0:
                                data = json.loads(line[start:])
                                if "predictions" in data:
                                    predictions.append(data)
                        except json.JSONDecodeError:
                            pass
            except Exception:
                pass

        return predictions

    def get_alerts(self) -> List[Dict]:
        """获取今日告警"""
        alerts = []
        alert_file = LOG_DIR / "alerts.log"

        if not alert_file.exists():
            return alerts

        try:
            with open(alert_file, "r", encoding="utf-8") as f:
                for line in f:
                    if self.today in line:
                        alerts.append({"raw": line.strip()})
        except Exception:
            pass

        return alerts

    def get_log_stats(self) -> Dict[str, int]:
        """获取日志统计"""
        stats = defaultdict(int)

        for log_file in LOG_DIR.glob("*.log"):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    today_marker = datetime.now().strftime("%Y-%m-%d")
                    today_content = [l for l in content.split("\n") if today_marker in l]

                    stats["total_lines"] += len(today_content)
                    stats["errors"] += sum(1 for l in today_content if "[ERROR]" in l or "❌" in l)
                    stats["warnings"] += sum(1 for l in today_content if "[WARNING]" in l or "⚠️" in l)
                    stats["success"] += sum(1 for l in today_content if "✅" in l or "[SUCCESS]" in l)
            except Exception:
                pass

        return dict(stats)

    def render(self) -> str:
        """渲染简报"""
        lines = []

        # 标题
        lines.append("")
        lines.append(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}  🛡️  TITAN 今日作战简报  {C.RESET}")
        lines.append(f"{C.DIM}  生成时间: {self.now.strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}")
        lines.append("")

        # === 系统状态 ===
        lines.append(f"{C.BOLD}┌─ 系统状态 ──────────────────────────────────────┐{C.RESET}")

        # 检查 Docker 服务
        import subprocess
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "-q"],
                capture_output=True, text=True, timeout=5, cwd=PROJECT_ROOT
            )
            container_count = len([l for l in result.stdout.strip().split("\n") if l])
            status = f"{C.GREEN}✓{C.RESET}" if container_count >= 2 else f"{C.YELLOW}⚠{C.RESET}"
            lines.append(f"│  Docker 容器: {status} {container_count} 个运行中")
        except Exception:
            lines.append(f"│  Docker 容器: {C.RED}✗ 无法检查{C.RESET}")

        # 检查最近巡航
        cruise_reports = self.get_cruise_reports()
        if cruise_reports:
            last_report = cruise_reports[-1]
            status_icon = f"{C.GREEN}✓{C.RESET}" if last_report.get("overall_success") else f"{C.RED}✗{C.RESET}"
            last_time = last_report.get("finished_at", "未知")[:19]
            lines.append(f"│  最近巡航: {status_icon} {last_time}")
        else:
            lines.append(f"│  最近巡航: {C.DIM}今日暂无{C.RESET}")

        lines.append(f"{C.BOLD}└──────────────────────────────────────────────────┘{C.RESET}")
        lines.append("")

        # === 巡航统计 ===
        lines.append(f"{C.BOLD}┌─ 巡航统计 (今日) ─────────────────────────────────┐{C.RESET}")

        total_cruises = len(cruise_reports)
        success_cruises = sum(1 for r in cruise_reports if r.get("overall_success"))
        failed_cruises = total_cruises - success_cruises

        lines.append(f"│  巡航次数: {C.CYAN}{total_cruises}{C.RESET} (成功 {C.GREEN}{success_cruises}{C.RESET} / 失败 {C.RED}{failed_cruises}{C.RESET})")

        if cruise_reports:
            total_duration = sum(r.get("total_duration_seconds", 0) for r in cruise_reports)
            avg_duration = total_duration / total_cruises if total_cruises else 0
            lines.append(f"│  总耗时: {total_duration:.1f}s | 平均: {avg_duration:.1f}s")

            # 阶段统计
            phase_stats = defaultdict(lambda: {"success": 0, "failed": 0, "duration": 0})
            for report in cruise_reports:
                for phase in report.get("phases", []):
                    phase_name = phase.get("phase", "unknown")
                    if phase.get("success"):
                        phase_stats[phase_name]["success"] += 1
                    else:
                        phase_stats[phase_name]["failed"] += 1
                    phase_stats[phase_name]["duration"] += phase.get("duration_seconds", 0)

            phase_line = "│  阶段: "
            for phase, stats in phase_stats.items():
                icon = "✓" if stats["failed"] == 0 else f"✗{stats['failed']}"
                color = C.GREEN if stats["failed"] == 0 else C.RED
                phase_line += f"{phase}:{color}{icon}{C.RESET} "
            lines.append(phase_line)

        lines.append(f"{C.BOLD}└──────────────────────────────────────────────────┘{C.RESET}")
        lines.append("")

        # === 日志统计 ===
        log_stats = self.get_log_stats()
        lines.append(f"{C.BOLD}┌─ 日志统计 (今日) ─────────────────────────────────┐{C.RESET}")
        lines.append(f"│  总行数: {log_stats.get('total_lines', 0):,}")
        lines.append(f"│  成功: {C.GREEN}{log_stats.get('success', 0)}{C.RESET} | "
                   f"警告: {C.YELLOW}{log_stats.get('warnings', 0)}{C.RESET} | "
                   f"错误: {C.RED}{log_stats.get('errors', 0)}{C.RESET}")
        lines.append(f"{C.BOLD}└──────────────────────────────────────────────────┘{C.RESET}")
        lines.append("")

        # === 告警 ===
        alerts = self.get_alerts()
        lines.append(f"{C.BOLD}┌─ 今日告警 ({len(alerts)}) ─────────────────────────────────────┐{C.RESET}")

        if alerts:
            for alert in alerts[:5]:  # 最多显示 5 条
                raw = alert.get("raw", "")
                # 简化显示
                if "🔴" in raw:
                    lines.append(f"│  {C.RED}{raw[:60]}{C.RESET}")
                elif "⚠️" in raw:
                    lines.append(f"│  {C.YELLOW}{raw[:60]}{C.RESET}")
                else:
                    lines.append(f"│  {raw[:60]}")
            if len(alerts) > 5:
                lines.append(f"│  {C.DIM}... 还有 {len(alerts) - 5} 条告警{C.RESET}")
        else:
            lines.append(f"│  {C.GREEN}✓ 无告警{C.RESET}")

        lines.append(f"{C.BOLD}└──────────────────────────────────────────────────┘{C.RESET}")
        lines.append("")

        # === 快捷命令 ===
        lines.append(f"{C.DIM}┌─ 快捷命令 ─────────────────────────────────────┐{C.RESET}")
        lines.append(f"{C.DIM}│  查看完整日志:  tail -f logs/titan_cruise.log  │{C.RESET}")
        lines.append(f"{C.DIM}│  运行巡航:      python scripts/ops/titan_cruise_control.py │{C.RESET}")
        lines.append(f"{C.DIM}│  系统健康:      python scripts/maintenance/check_system_health.py │{C.RESET}")
        lines.append(f"{C.DIM}└──────────────────────────────────────────────────┘{C.RESET}")

        return "\n".join(lines)

    def show(self, watch: bool = False, interval: int = 60):
        """显示简报"""
        while True:
            self.clear_screen()
            print(self.render())

            if not watch:
                break

            print(f"\n{C.DIM}下次刷新: {interval} 秒后 (Ctrl+C 退出){C.RESET}")
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                print(f"\n{C.DIM}退出监控模式{C.RESET}")
                break


# ============================================================================
# CLI 入口
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="TITAN 今日作战简报 - 终端监控看板",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="实时监控模式 (每 60 秒刷新)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="监控刷新间隔 (秒，默认: 60)"
    )
    return parser.parse_args()


def main():
    """主入口"""
    args = parse_args()
    summary = TodaySummary()
    summary.show(watch=args.watch, interval=args.interval)


if __name__ == "__main__":
    main()
