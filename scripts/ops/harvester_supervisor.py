#!/usr/bin/env python3
"""
V30.2 收割机守护程序 - 并发模式监控

核心功能：
1. 进程监控：每 60 秒检查 harvest_pinnacle_concurrent.py 是否存活
2. 崩溃分析：自动提取最后 50 行日志，分析崩溃原因
3. 自动重启：检测到进程退出后自动重启
4. 崩溃审计：将崩溃原因存入 logs/crash_summary.json
5. MALFORMED 熔断：连续 10 场失败自动停止并保存现场快照
6. V30.2 新增：多进程模式监控，默认 3 工作进程

并发模式配置：
- 默认工作进程数：3（保守方案，避免代理硬碰撞）
- 代理端口：7890-7892
- 每进程采集数：50 场

准入红线：在 Supervisor 守护程序跑通之前，不准再手动启动任何收割脚本！

Author: 高级 DevOps 架构师 (Staff DevOps Engineer)
Date: 2026-01-11
Version: V30.2 (Concurrent Mode Support)
"""

import asyncio
import json
import logging
import os
import psutil
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2  # V30.1 新增：用于 MALFORMED 告警检查

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V30.3: 配置日志轮转
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# 创建根日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')

# 文件处理器 - 轮转 (50MB x 10)
file_handler = RotatingFileHandler(
    'logs/harvester_supervisor.log',
    maxBytes=50*1024*1024,  # 50MB
    backupCount=10,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置日志记录器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 防止重复日志
logger.propagate = False


# ============================================================================
# 配置常量 (V30.2: 并发模式)
# ============================================================================

HARVESTER_SCRIPT = "scripts/ops/harvest_pinnacle_concurrent.py"
HARVESTER_ARGS = ["--workers", "8", "--limit", "50"]  # V32.0: 8进程全速模式
CHECK_INTERVAL = 60  # 检查间隔（秒）
LOG_LINES_TO_ANALYZE = 50  # 分析日志行数
CRASH_SUMMARY_FILE = "logs/crash_summary.json"
CONCURRENT_LOG_FILE = "logs/harvest_pinnacle_concurrent.log"  # V30.2: 并发日志文件

# 信号处理
shutdown_requested = False


def signal_handler(signum, frame):
    """信号处理器"""
    global shutdown_requested
    logger.info(f"收到信号 {signum}，准备优雅关闭...")
    shutdown_requested = True


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ============================================================================
# 进程管理
# ============================================================================

def find_harvester_process() -> Optional[psutil.Process]:
    """查找正在运行的收割机进程 (V30.2: 并发模式)

    Returns:
        找到的进程对象，如果未找到返回 None
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline:
                cmdline_str = ' '.join(cmdline)
                # V30.2: 检测并发脚本或单线程脚本
                if 'harvest_pinnacle_concurrent.py' in cmdline_str or \
                   'harvest_pinnacle_odds.py' in cmdline_str:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def start_harvester() -> Optional[psutil.Popen]:
    """启动收割机进程 (V30.2: 并发模式)

    Returns:
        启动的进程对象，如果启动失败返回 None
    """
    try:
        # 使用 nohup 启动，避免终端关闭影响进程
        cmd = ["python", HARVESTER_SCRIPT] + HARVESTER_ARGS

        logger.info(f"启动收割机: {' '.join(cmd)}")

        # V30.2: 使用并发日志文件
        log_file = Path(CONCURRENT_LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 使用 Popen 启动进程
        process = psutil.Popen(
            cmd,
            stdout=open(log_file, "a"),
            stderr=open(log_file, "a"),
            cwd=str(Path(__file__).parent.parent.parent)
        )

        logger.info(f"✅ 收割机已启动，PID: {process.pid}")
        return process

    except Exception as e:
        logger.error(f"❌ 启动收割机失败: {e}")
        return None


# ============================================================================
# 日志分析
# ============================================================================

def analyze_crash(log_file: str) -> Dict[str, any]:
    """分析崩溃日志

    Args:
        log_file: 日志文件路径

    Returns:
        崩溃分析结果字典
    """
    if not os.path.exists(log_file):
        return {
            "error": "日志文件不存在",
            "log_file": log_file
        }

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 读取最后 N 行
            lines = f.readlines()[-LOG_LINES_TO_ANALYZE:]

        # 提取关键信息
        errors = []
        last_error = None
        timeout_count = 0
        pinnacle_missing_count = 0

        for line in lines:
            line_lower = line.lower()

            # 统计错误类型
            if 'error' in line_lower or 'failed' in line_lower:
                errors.append(line.strip())

            if 'timeout' in line_lower:
                timeout_count += 1

            if '未找到.*pinnacle' in line_lower or 'pinnacle.*not found' in line_lower:
                pinnacle_missing_count += 1

            # 捕获最后的错误信息
            if 'error' in line_lower or 'exception' in line_lower:
                last_error = line.strip()

        # 确定崩溃原因
        crash_reason = "UNKNOWN"
        if timeout_count > 5:
            crash_reason = "TIMEOUT"
        elif pinnacle_missing_count > 10:
            crash_reason = "PINNACLE_MISSING"
        elif last_error:
            if 'timeout' in last_error.lower():
                crash_reason = "TIMEOUT"
            elif 'pinnacle' in last_error.lower():
                crash_reason = "PINNACLE_MISSING"
            elif 'connection' in last_error.lower():
                crash_reason = "CONNECTION_ERROR"
            elif 'attribute' in last_error.lower():
                crash_reason = "CONFIG_ERROR"

        return {
            "crash_reason": crash_reason,
            "last_error": last_error,
            "error_count": len(errors),
            "timeout_count": timeout_count,
            "pinnacle_missing_count": pinnacle_missing_count,
            "log_tail": ''.join(lines[-10:])  # 最后 10 行
        }

    except Exception as e:
        return {
            "error": str(e),
            "log_file": log_file
        }


def save_crash_summary(crash_data: Dict):
    """保存崩溃摘要到文件

    Args:
        crash_data: 崩溃数据字典
    """
    try:
        # 读取现有数据
        existing_data = []
        if os.path.exists(CRASH_SUMMARY_FILE):
            with open(CRASH_SUMMARY_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # 添加新记录
        crash_record = {
            "timestamp": datetime.now().isoformat(),
            "crash_reason": crash_data.get("crash_reason", "UNKNOWN"),
            "last_error": crash_data.get("last_error"),
            "error_count": crash_data.get("error_count", 0),
            "timeout_count": crash_data.get("timeout_count", 0),
            "pinnacle_missing_count": crash_data.get("pinnacle_missing_count", 0)
        }
        existing_data.append(crash_record)

        # 保存到文件
        os.makedirs(os.path.dirname(CRASH_SUMMARY_FILE), exist_ok=True)
        with open(CRASH_SUMMARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 崩溃摘要已保存: {CRASH_SUMMARY_FILE}")

    except Exception as e:
        logger.error(f"❌ 保存崩溃摘要失败: {e}")


def check_malformed_alert() -> Dict[str, any]:
    """检查 MALFORMED 告警状态（连续失败熔断）

    Returns:
        告警状态字典
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'football_db'),
            user=os.getenv('DB_USER', 'football_user'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        # 检查最近 10 分钟的 MALFORMED 记录
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE is_malformed = TRUE) as malformed_count,
                COUNT(*) FILTER (WHERE is_malformed = TRUE AND updated_at >= NOW() - INTERVAL '10 minutes') as recent_malformed
            FROM matches_mapping
            WHERE updated_at >= NOW() - INTERVAL '1 hour';
        """)

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        malformed_count = result[0] if result else 0
        recent_malformed = result[1] if result else 0

        # 判断是否触发告警（连续10场失败）
        alert_triggered = recent_malformed >= 10

        return {
            'malformed_count': malformed_count,
            'recent_malformed': recent_malformed,
            'alert_threshold': 10,
            'alert_triggered': alert_triggered
        }

    except Exception as e:
        logger.error(f"❌ 检查 MALFORMED 告警失败: {e}")
        return {
            'malformed_count': 0,
            'recent_malformed': 0,
            'alert_threshold': 10,
            'alert_triggered': False
        }


def check_batch_quality_alert(threshold_percent: float = 15.0) -> Dict[str, any]:
    """V32.1.2: 检查批次质量告警（malformed 比例监控）

    如果当前批次（最近采集的记录）的 malformed 比例超过阈值，
    自动触发停止并保存现场快照。

    Args:
        threshold_percent: malformed 比例阈值（默认 15%）

    Returns:
        质量告警状态字典

    示例:
        >>> check_batch_quality_alert(threshold_percent=15.0)
        {
            'total_count': 100,
            'malformed_count': 20,
            'malformed_ratio': 0.20,  # 20%
            'alert_threshold': 0.15,   # 15%
            'alert_triggered': True,   # 触发告警
            'by_league': {
                'La Liga': {'total': 11, 'malformed': 4, 'ratio': 0.36},
                'Premier League': {'total': 89, 'malformed': 16, 'ratio': 0.18}
            }
        }
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'football_db'),
            user=os.getenv('DB_USER', 'football_user'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        # 检查最近 1 小时采集的批次数据质量
        cursor.execute("""
            WITH recent_batch AS (
                SELECT
                    league_name,
                    COUNT(*) as total_count,
                    COUNT(*) FILTER (WHERE is_malformed = TRUE) as malformed_count
                FROM matches_mapping
                WHERE updated_at >= NOW() - INTERVAL '1 hour'
                  AND oddsportal_url IS NOT NULL
                GROUP BY league_name
            )
            SELECT
                SUM(total_count) as total_batch,
                SUM(malformed_count) as total_malformed,
                ARRAY_AGG(league_name) as leagues,
                ARRAY_AGG(json_build_object(
                    'league', league_name,
                    'total', total_count,
                    'malformed', malformed_count,
                    'ratio', CASE
                        WHEN total_count > 0 THEN ROUND(malformed_count::numeric / total_count, 4)
                        ELSE 0
                    END
                )) as by_league
            FROM recent_batch;
        """)

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result or result[0] is None:
            return {
                'total_count': 0,
                'malformed_count': 0,
                'malformed_ratio': 0.0,
                'alert_threshold': threshold_percent / 100.0,
                'alert_triggered': False,
                'by_league': {}
            }

        total_batch = result[0]
        total_malformed = result[1]
        by_league_raw = result[3] or []

        # 计算 malformed 比例
        malformed_ratio = total_malformed / total_batch if total_batch > 0 else 0.0

        # 构建按联赛统计的字典
        by_league = {}
        for item in by_league_raw:
            league = item['league']
            by_league[league] = {
                'total': item['total'],
                'malformed': item['malformed'],
                'ratio': item['ratio']
            }

        # 判断是否触发告警
        alert_threshold = threshold_percent / 100.0
        alert_triggered = malformed_ratio > alert_threshold

        # 记录详细信息
        if alert_triggered:
            logger.error(f"🚨 批次质量告警触发！")
            logger.error(f"   总计: {total_batch} 场 | Malformed: {total_malformed} 场 | 比例: {malformed_ratio:.2%}")
            logger.error(f"   阈值: {threshold_percent}% | 实际: {malformed_ratio * 100:.2f}%")
            logger.error(f"   按联赛统计:")
            for league, stats in by_league.items():
                logger.error(f"     - {league}: {stats['malformed']}/{stats['total']} ({stats['ratio']:.2%})")
        else:
            logger.info(f"✅ 批次质量检查通过: {total_malformed}/{total_batch} ({malformed_ratio:.2%}) < {threshold_percent}%")

        return {
            'total_count': total_batch,
            'malformed_count': total_malformed,
            'malformed_ratio': malformed_ratio,
            'alert_threshold': alert_threshold,
            'alert_triggered': alert_triggered,
            'by_league': by_league
        }

    except Exception as e:
        logger.error(f"❌ 检查批次质量告警失败: {e}")
        return {
            'total_count': 0,
            'malformed_count': 0,
            'malformed_ratio': 0.0,
            'alert_threshold': threshold_percent / 100.0,
            'alert_triggered': False,
            'by_league': {}
        }


def save_scene_snapshot(reason: str = "MALFORMED_ALERT"):
    """保存现场快照

    Args:
        reason: 快照原因
    """
    try:
        snapshot_file = f"logs/scene_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # 收集现场信息
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'football_db'),
            user=os.getenv('DB_USER', 'football_user'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()

        # 获取最近 20 条 MALFORMED 记录
        cursor.execute("""
            SELECT
                id,
                fotmob_id,
                league_name,
                home_team,
                away_team,
                oddsportal_url,
                is_malformed,
                status,
                updated_at
            FROM matches_mapping
            WHERE is_malformed = TRUE
            ORDER BY updated_at DESC
            LIMIT 20;
        """)

        columns = ['id', 'fotmob_id', 'league_name', 'home_team', 'away_team',
                   'oddsportal_url', 'is_malformed', 'status', 'updated_at']
        malformed_records = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # 转换 datetime 对象为字符串（JSON序列化兼容）
            if record.get('updated_at'):
                record['updated_at'] = record['updated_at'].isoformat()
            malformed_records.append(record)

        cursor.close()
        conn.close()

        # 保存快照
        snapshot_data = {
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'malformed_records': malformed_records,
            'process_info': {
                'supervisor_pid': os.getpid(),
                'harvester_pid': find_harvester_process().pid if find_harvester_process() else None
            }
        }

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 现场快照已保存: {snapshot_file}")
        return snapshot_file

    except Exception as e:
        logger.error(f"❌ 保存现场快照失败: {e}")
        return None


def emergency_shutdown(reason: str):
    """紧急停止所有收割进程

    Args:
        reason: 停止原因
    """
    logger.error(f"🚨 触发紧急停止！原因: {reason}")

    # 停止收割机进程
    harvester = find_harvester_process()
    if harvester:
        try:
            logger.info(f"🛑 停止收割机进程 PID: {harvester.pid}")
            harvester.terminate()
            harvester.wait(timeout=5)
            logger.info("✅ 收割机进程已停止")
        except:
            logger.warning("⚠️  收割机关闭超时，强制杀死")
            harvester.kill()

    # 保存现场快照
    snapshot_file = save_scene_snapshot(reason)

    # 记录紧急停止事件
    alert_data = {
        'timestamp': datetime.now().isoformat(),
        'event': 'EMERGENCY_SHUTDOWN',
        'reason': reason,
        'snapshot_file': snapshot_file
    }

    # 保存到崩溃摘要
    existing_data = []
    if os.path.exists(CRASH_SUMMARY_FILE):
        with open(CRASH_SUMMARY_FILE, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

    existing_data.append(alert_data)

    os.makedirs(os.path.dirname(CRASH_SUMMARY_FILE), exist_ok=True)
    with open(CRASH_SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 紧急停止事件已记录到: {CRASH_SUMMARY_FILE}")

    # 设置全局停止标志
    global shutdown_requested
    shutdown_requested = True

    logger.error("🛑 所有收割进程已停止，守护程序将退出")


# ============================================================================
# 主循环
# ============================================================================

async def supervise():
    """主监控循环 (V30.2: 并发模式)"""
    logger.info("=" * 70)
    logger.info("🤖 收割机守护程序已启动 (V30.2 并发模式)")
    logger.info("=" * 70)
    logger.info(f"监控脚本: {HARVESTER_SCRIPT}")
    logger.info(f"启动参数: {' '.join(HARVESTER_ARGS)}")
    logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
    logger.info(f"崩溃摘要: {CRASH_SUMMARY_FILE}")
    logger.info("")

    harvester_process = None

    # 首次启动：检查是否已有进程在运行
    existing_process = find_harvester_process()
    if existing_process:
        logger.info(f"✅ 检测到正在运行的收割机进程，PID: {existing_process.pid}")
    else:
        logger.info("⚠️  未检测到运行中的收割机，准备启动...")
        harvester_process = start_harvester()

    # 主监控循环
    while not shutdown_requested:
        try:
            # 等待检查间隔
            await asyncio.sleep(CHECK_INTERVAL)

            # V30.1 新增：MALFORMED 告警检查（连续失败熔断）
            alert_status = check_malformed_alert()
            if alert_status['alert_triggered']:
                logger.error(f"🚨 MALFORMED 告警触发！近10分钟异常: {alert_status['recent_malformed']} 场")
                emergency_shutdown("CONSECUTIVE_MALFORMED_ALERT")
                break  # 退出监控循环

            # V32.1.2 新增：批次质量告警检查（malformed 比例 > 15%）
            quality_status = check_batch_quality_alert(threshold_percent=15.0)
            if quality_status['alert_triggered']:
                logger.error(f"🚨 批次质量告警触发！malformed 比例: {quality_status['malformed_ratio']:.2%}")
                emergency_shutdown("BATCH_QUALITY_ALERT")
                break  # 退出监控循环

            # 检查进程状态
            current_process = find_harvester_process()

            if current_process:
                # 进程运行中
                logger.debug(f"✅ 收割机运行正常，PID: {current_process.pid}")

                # 更新进程对象引用
                harvester_process = current_process

            else:
                # 进程已停止
                logger.warning("⚠️  收割机进程已停止！")

                # V30.2: 分析崩溃原因（使用并发日志文件）
                log_file = CONCURRENT_LOG_FILE
                logger.info(f"🔍 分析崩溃日志: {log_file}")

                crash_data = analyze_crash(log_file)
                logger.info(f"📊 崩溃原因: {crash_data.get('crash_reason', 'UNKNOWN')}")
                logger.info(f"   错误数量: {crash_data.get('error_count', 0)}")
                logger.info(f"   超时次数: {crash_data.get('timeout_count', 0)}")
                logger.info(f"   Pinnacle 缺失: {crash_data.get('pinnacle_missing_count', 0)}")

                # 保存崩溃摘要
                save_crash_summary(crash_data)

                # 自动重启
                logger.info("🔄 准备自动重启收割机...")
                await asyncio.sleep(5)  # 等待 5 秒再重启

                harvester_process = start_harvester()

                if harvester_process:
                    logger.info("✅ 收割机已自动重启")
                else:
                    logger.error("❌ 自动重启失败，等待下次检查...")

        except Exception as e:
            logger.error(f"❌ 监控循环异常: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

    # 优雅关闭
    logger.info("正在关闭守护程序...")

    # 检查是否需要关闭收割机进程
    if harvester_process:
        try:
            harvester_process.terminate()
            harvester_process.wait(timeout=5)
            logger.info("✅ 收割机进程已关闭")
        except:
            logger.warning("⚠️  收割机关闭超时，强制杀死")
            harvester_process.kill()

    logger.info("👋 守护程序已退出")


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    """命令行入口 (V30.2: 并发模式)"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V30.2 收割机守护程序 - 并发模式监控"
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=CHECK_INTERVAL,
        help=f'检查间隔（秒），默认: {CHECK_INTERVAL}'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='只执行一次检查（调试用）'
    )

    args = parser.parse_args()

    if args.once:
        # 单次运行模式（调试用）
        logger.info("🔍 单次检查模式")
        process = find_harvester_process()
        if process:
            logger.info(f"✅ 收割机运行中，PID: {process.pid}")
        else:
            logger.warning("⚠️  收割机未运行")
        return

    # 正常运行模式
    try:
        asyncio.run(supervise())
    except KeyboardInterrupt:
        logger.info("收到 Ctrl+C，退出...")
    except Exception as e:
        logger.error(f"❌ 守护程序异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
