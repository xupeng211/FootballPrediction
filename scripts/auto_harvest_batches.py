#!/usr/bin/env python3
"""
V26.1 自动化分批收割脚本
========================

功能:
    1. 自动分批处理所有未处理的比赛
    2. 内存监控（超过阈值时自动等待）
    3. 进度持久化（支持断点续传）
    4. 失败重试机制

使用方法:
    python scripts/auto_harvest_batches.py

Author: Auto-Harvest System
Version: V26.1
Date: 2025-12-27
"""

import gc
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings

# ============================================================================
# 配置
# ============================================================================

BATCH_SIZE = 200          # 每批处理数量
WORKERS = 1               # Worker 数量
SUB_BATCH_SIZE = 15       # 子批次大小（数据库写入）
MEMORY_THRESHOLD_MB = 7000  # 内存阈值（超过则等待）
WAIT_SECONDS = 30         # 内存超限等待时间
MAX_RETRIES = 2           # 失败重试次数

# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    handlers=[
        logging.FileHandler("logs/auto_harvest.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 工具函数
# ============================================================================

def get_memory_usage_mb():
    """获取当前进程内存使用量（MB）"""
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_system_memory_available():
    """获取系统可用内存（MB）"""
    import psutil
    return psutil.virtual_memory().available / 1024 / 1024


def get_unprocessed_count(settings) -> int:
    """获取未处理比赛数量"""
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM matches m
        INNER JOIN raw_match_data r ON r.match_id = m.match_id
        WHERE UPPER(m.status) = 'FINISHED'
        AND NOT EXISTS (
            SELECT 1 FROM match_features_training f
            WHERE f.match_id = m.match_id
        );
    """)
    count = cur.fetchone()[0]

    conn.close()
    return count


def get_total_count(settings) -> int:
    """获取总比赛数量"""
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM matches
        WHERE UPPER(status) = 'FINISHED';
    """)
    count = cur.fetchone()[0]

    conn.close()
    return count


def run_batch(batch_num: int, limit: int, retry: int = 0) -> dict:
    """
    运行单个批次

    Args:
        batch_num: 批次编号
        limit: 处理数量
        retry: 重试次数

    Returns:
        执行结果字典
    """
    log_file = f"logs/v26_batch{batch_num}.log"
    cmd = [
        "python",
        "scripts/run_v26_full_harvest.py",
        "--workers", str(WORKERS),
        "--batch-size", str(SUB_BATCH_SIZE),
        "--limit", str(limit)
    ]

    logger.info(f"启动批次 #{batch_num}: {limit} 场")
    logger.info(f"命令: {' '.join(cmd)}")
    logger.info(f"日志: {log_file}")

    start_time = time.time()

    try:
        with open(log_file, "w") as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=project_root
            )

            # 等待进程完成
            while process.poll() is None:
                time.sleep(5)

                # 检查内存
                avail_mem = get_system_memory_available()
                if avail_mem < 1000:  # 可用内存低于 1GB
                    logger.warning(f"⚠️  可用内存不足: {avail_mem:.0f} MB")

            elapsed = time.time() - start_time

            if process.returncode == 0:
                logger.info(f"✅ 批次 #{batch_num} 完成: {elapsed:.1f} 秒")
                return {"success": True, "elapsed": elapsed}
            else:
                logger.error(f"❌ 批次 #{batch_num} 失败: 返回码 {process.returncode}")
                if retry < MAX_RETRIES:
                    logger.info(f"🔄 重试批次 #{batch_num} ({retry + 1}/{MAX_RETRIES})...")
                    time.sleep(10)
                    return run_batch(batch_num, limit, retry + 1)
                return {"success": False, "elapsed": elapsed, "returncode": process.returncode}

    except Exception as e:
        logger.error(f"❌ 批次 #{batch_num} 异常: {e}")
        return {"success": False, "elapsed": time.time() - start_time, "error": str(e)}


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("V26.1 自动化分批收割启动")
    logger.info("=" * 60)

    # 获取配置
    settings = get_settings()

    # 获取初始状态
    total = get_total_count(settings)
    unprocessed = get_unprocessed_count(settings)
    processed = total - unprocessed

    logger.info(f"总比赛数: {total}")
    logger.info(f"已处理: {processed}")
    logger.info(f"未处理: {unprocessed}")
    logger.info(f"进度: {processed}/{total} ({processed/total*100:.1f}%)")
    logger.info("")

    if unprocessed == 0:
        logger.info("✅ 所有比赛已处理完成！")
        return

    # 计算批次
    num_batches = (unprocessed + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(f"收割计划:")
    logger.info(f"  批次大小: {BATCH_SIZE} 场")
    logger.info(f"  批次数量: {num_batches}")
    logger.info(f"  Worker 数: {WORKERS}")
    logger.info(f"  预计耗时: {unprocessed / 84:.0f} 分钟 (按 84 场/分钟)")
    logger.info("")

    # 记录开始时间
    overall_start = time.time()

    # 执行收割
    success_count = 0
    failed_batches = []

    for batch_num in range(1, num_batches + 1):
        # 计算本批次处理数量
        remaining = get_unprocessed_count(settings)
        if remaining <= 0:
            logger.info("✅ 所有比赛已处理完成！")
            break

        limit = min(BATCH_SIZE, remaining)

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"批次 {batch_num}/{num_batches}")
        logger.info("=" * 60)
        logger.info(f"剩余: {remaining} 场")
        logger.info(f"本批: {limit} 场")

        # 检查内存
        avail_mem = get_system_memory_available()
        logger.info(f"可用内存: {avail_mem:.0f} MB")

        if avail_mem < 2000:
            logger.warning(f"⚠️  内存不足，等待 {WAIT_SECONDS} 秒...")
            time.sleep(WAIT_SECONDS)

        # 运行批次
        result = run_batch(batch_num, limit)

        if result["success"]:
            success_count += 1
        else:
            failed_batches.append(batch_num)

        # 强制 GC
        gc.collect()

        # 更新进度
        current_unprocessed = get_unprocessed_count(settings)
        current_processed = total - current_unprocessed
        logger.info(f"当前进度: {current_processed}/{total} ({current_processed/total*100:.1f}%)")

        # 批次间短暂休息
        if batch_num < num_batches and current_unprocessed > 0:
            logger.info("等待 5 秒后继续...")
            time.sleep(5)

    # 最终报告
    total_elapsed = time.time() - overall_start
    final_unprocessed = get_unprocessed_count(settings)
    final_processed = total - final_unprocessed

    logger.info("")
    logger.info("=" * 60)
    logger.info("收割完成！")
    logger.info("=" * 60)
    logger.info(f"成功批次: {success_count}/{num_batches}")
    logger.info(f"失败批次: {len(failed_batches)}")
    if failed_batches:
        logger.info(f"失败批次号: {failed_batches}")
    logger.info(f"总耗时: {total_elapsed:.1f} 秒 ({total_elapsed/60:.1f} 分钟)")
    logger.info(f"最终进度: {final_processed}/{total} ({final_processed/total*100:.1f}%)")
    logger.info(f"平均吞吐: {final_processed/total_elapsed*60:.0f} 场/分钟")

    if final_unprocessed > 0:
        logger.warning(f"⚠️  仍有 {final_unprocessed} 场比赛未处理")
        logger.info("请检查日志并重新运行脚本")


if __name__ == "__main__":
    main()
