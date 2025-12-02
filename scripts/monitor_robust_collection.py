#!/usr/bin/env python3
"""
稳健型采集状态监控器
用于监控Low & Slow模式的采集进度
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_progress() -> Dict:
    """加载采集进度"""
    progress_file = "logs/coverage_progress.json"
    try:
        if Path(progress_file).exists():
            with open(progress_file, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ 加载进度失败：{e}")

    return {"completed_leagues": [], "failed_leagues": [], "last_update": None}


def load_failed_logs() -> List[Dict]:
    """加载失败日志"""
    failed_log_file = "logs/failed_leagues.log"
    failed_leagues = []

    try:
        if Path(failed_log_file).exists():
            with open(failed_log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith("{") and line.endswith("}"):
                        try:
                            failed_leagues.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        print(f"❌ 加载失败日志失败：{e}")

    return failed_leagues


def check_process_status() -> bool:
    """检查采集进程是否运行"""
    try:
        import subprocess

        result = subprocess.run(
            ["pgrep", "-f", "launch_robust_coverage.py"], capture_output=True, text=True
        )
        return len(result.stdout.strip()) > 0
    except Exception:
        return False


def count_data_files() -> int:
    """统计数据文件数量"""
    data_dir = Path("data/fbref")
    if data_dir.exists():
        return len(list(data_dir.glob("*.csv")))
    return 0


def calculate_eta(completed: int, total: int, start_time: Optional[str] = None) -> str:
    """计算预计完成时间"""
    if completed == 0:
        return "计算中..."

    if not start_time:
        return "未知"

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        elapsed = (datetime.now() - start_dt).total_seconds()

        if elapsed > 0:
            rate = completed / elapsed  # 每秒完成数
            remaining = total - completed
            eta_seconds = remaining / rate

            hours = int(eta_seconds // 3600)
            minutes = int((eta_seconds % 3600) // 60)

            return f"{hours}小时{minutes}分钟"
    except Exception:
        pass

    return "计算失败"


def main():
    """主监控函数"""
    print("🔍 稳健型采集状态监控器")
    print("=" * 50)

    # 检查进程状态
    is_running = check_process_status()
    print(f"🔄 采集进程状态：{'🟢 运行中' if is_running else '🔴 已停止'}")

    # 加载进度
    progress = load_progress()
    completed = len(progress.get("completed_leagues", []))
    failed = len(progress.get("failed_leagues", []))

    # 总联赛数（38个主要联赛）
    total_leagues = 38

    print(
        f"📊 采集进度：{completed}/{total_leagues} ({(completed/total_leagues)*100:.1f}%)"
    )
    print(f"✅ 已完成：{completed} 个联赛")
    print(f"❌ 失败：{failed} 个联赛")

    # 数据文件统计
    data_files = count_data_files()
    print(f"💾 数据文件：{data_files} 个CSV文件")

    # 最后更新时间
    last_update = progress.get("last_update")
    if last_update:
        try:
            update_time = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            print(f"🕐 最后更新：{update_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # 计算预计完成时间
            eta = calculate_eta(completed, total_leagues, last_update)
            print(f"⏱️  预计完成时间：{eta}")
        except Exception:
            print(f"🕐 最后更新：{last_update}")

    print("\n📋 已完成联赛列表：")
    if progress.get("completed_leagues"):
        for league_id in sorted(progress["completed_leagues"]):
            print(f"  ✅ {league_id}")
    else:
        print("  暂无")

    # 显示失败联赛
    failed_logs = load_failed_logs()
    if failed_logs:
        print(f"\n⚠️  失败联赛详情：")
        for failure in failed_logs[-5:]:  # 显示最近5个失败的
            print(
                f"  ❌ {failure.get('league_name', 'Unknown')} ({failure.get('league_id', 'Unknown')})"
            )
            print(f"     错误：{failure.get('error', 'Unknown error')}")
            print(f"     时间：{failure.get('timestamp', 'Unknown')}")

    # 显示数据目录状态
    data_dir = Path("data/fbref")
    if data_dir.exists():
        print(f"\n📂 数据目录状态：")
        print(f"  路径：{data_dir.absolute()}")
        print(
            f"  大小：{sum(f.stat().st_size for f in data_dir.glob('**/*') if f.is_file()) / 1024 / 1024:.1f} MB"
        )

    # 状态总结
    print(f"\n🎯 采集状态总结：")
    if is_running and completed > 0:
        print("  🟢 采集器正常运行，数据持续增长中")
    elif is_running and completed == 0:
        print("  🟡 采集器运行中，但尚未完成任何联赛")
    elif not is_running and completed == total_leagues:
        print("  🟢 采集任务已完成")
    elif not is_running and completed > 0:
        print("  🟡 采集器已停止，可能有异常发生")
    else:
        print("  🔴 采集器未运行，无采集记录")

    print(f"\n📝 实时日志查看：tail -f logs/robust_coverage.log")
    print(
        f"🔄 重启采集器：nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &"
    )


if __name__ == "__main__":
    main()
