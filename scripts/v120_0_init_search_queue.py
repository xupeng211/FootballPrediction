#!/usr/bin/env python3
"""V120.0 Phase 2: Initialize Match Search Queue.

This script performs one-time initialization of the match_search_queue table
by injecting all matches that lack oddsportal_url.

Usage:
    python scripts/v120_0_init_search_queue.py --dry-run
    python scripts/v120_0_init_search_queue.py --execute
"""

import argparse
import logging
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def count_pending_tasks(conn: psycopg2.extensions.connection) -> int:
    """统计需要注入的任务数量."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM matches
        WHERE oddsportal_url IS NULL
           OR oddsportal_url = ''
           OR LENGTH(TRIM(oddsportal_url)) = 0
    """)
    result = cursor.fetchone()
    cursor.close()
    return result["count"] if result else 0


def get_pending_match_ids(conn: psycopg2.extensions.connection, limit: int | None = None):
    """获取需要处理的比赛 ID 列表."""
    query = """
        SELECT match_id
        FROM matches
        WHERE oddsportal_url IS NULL
           OR oddsportal_url = ''
           OR LENGTH(TRIM(oddsportal_url)) = 0
        ORDER BY match_date DESC
    """
    if limit:
        query += f" LIMIT {limit}"

    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return [row["match_id"] for row in results]


def check_existing_queue(conn: psycopg2.extensions.connection) -> int:
    """检查队列表中已有任务数量."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM match_search_queue")
    result = cursor.fetchone()
    cursor.close()
    return result["count"] if result else 0


def inject_tasks(
    conn: psycopg2.extensions.connection,
    match_ids: list[str],
    batch_size: int = 1000
) -> int:
    """批量注入任务到队列表.

    Args:
        conn: 数据库连接
        match_ids: 比赛 ID 列表
        batch_size: 批量插入大小

    Returns:
        成功插入的任务数量
    """
    total_injected = 0

    cursor = conn.cursor()

    for i in range(0, len(match_ids), batch_size):
        batch = match_ids[i:i + batch_size]

        # 使用 INSERT ... ON CONFLICT DO NOTHING 避免重复
        values = ",".join(
            f"('{mid}', 'PENDING', 0, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            for mid in batch
        )

        insert_sql = f"""
            INSERT INTO match_search_queue (match_id, status, retry_count, max_retries, created_at, updated_at)
            VALUES {values}
            ON CONFLICT (match_id) DO NOTHING
        """

        cursor.execute(insert_sql)
        injected = cursor.rowcount
        total_injected += injected

        conn.commit()

        logger.info(
            f"Batch {i//batch_size + 1}: "
            f"注入 {injected}/{len(batch)} 条任务 "
            f"(累计: {total_injected})"
        )

    cursor.close()
    return total_injected


def print_queue_statistics(conn: psycopg2.extensions.connection):
    """打印队列统计信息."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            status,
            COUNT(*) as count
        FROM match_search_queue
        GROUP BY status
        ORDER BY status
    """)
    results = cursor.fetchall()
    cursor.close()

    logger.info("\n队列状态统计:")
    logger.info("-" * 40)
    for row in results:
        logger.info(f"  {row['status']}: {row['count']} 条")
    logger.info("-" * 40)


def main():
    parser = argparse.ArgumentParser(
        description="V120.0: Initialize match_search_queue table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计，不执行注入"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行注入操作"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制注入数量 (测试用)"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        logger.error("\n错误: 必须指定 --dry-run 或 --execute")
        sys.exit(1)

    # 获取数据库配置
    settings = get_settings()

    # 连接数据库
    logger.info("连接数据库...")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        # 1. 检查现有队列
        existing_count = check_existing_queue(conn)
        logger.info(f"现有队列任务数: {existing_count}")

        # 2. 统计需要注入的任务
        pending_count = count_pending_tasks(conn)
        logger.info(f"待注入任务数: {pending_count}")

        if pending_count == 0:
            logger.info("没有需要注入的任务，退出。")
            return

        # 3. 获取待处理比赛 ID
        match_ids = get_pending_match_ids(conn, limit=args.limit)
        logger.info(f"获取到 {len(match_ids)} 个比赛 ID")

        if args.dry_run:
            logger.info("\n[DRY-RUN] 仅统计，不执行注入")
            logger.info(f"预计注入: {len(match_ids)} 条任务")
            return

        # 4. 执行注入
        if args.execute:
            logger.info("\n开始注入任务...")
            injected = inject_tasks(conn, match_ids)

            logger.info(f"\n注入完成: {injected}/{len(match_ids)} 条任务")

            # 5. 打印统计信息
            print_queue_statistics(conn)

    finally:
        conn.close()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    main()
