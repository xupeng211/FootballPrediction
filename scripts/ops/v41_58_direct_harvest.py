#!/usr/bin/env python3
"""
V41.58: 直接收割脚本（绕过配置系统）
=====================================
用途: 直接使用指定数据库连接执行哈希对齐收割
"""

import sys
import os
import psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from src.services.hash_alignment_service import HashAlignmentService


def main():
    # 直接使用 Docker 数据库 IP
    DB_HOST = "172.20.0.3"
    DB_PORT = 5432
    DB_NAME = "football_db"
    DB_USER = "football_user"
    DB_PASSWORD = "football_pass"

    # 解析命令行参数
    league = sys.argv[1] if len(sys.argv) > 1 else "Ligue 1"
    season = sys.argv[2] if len(sys.argv) > 2 else "23/24"

    logger.info("=" * 60)
    logger.info("V41.58: 直接收割模式")
    logger.info("=" * 60)
    logger.info(f"联赛: {league}")
    logger.info(f"赛季: {season}")
    logger.info(f"数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info("")

    # 连接数据库
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

    try:
        # 创建哈希对齐服务
        service = HashAlignmentService(conn, season=season)

        # 执行收割
        logger.info(f"🚀 开始收割: {league} {season}")
        logger.info("")

        stats = service.align_league_hashes(
            league_name=league,
            run_harvest=True
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 收割统计")
        logger.info("=" * 60)
        logger.info(f"处理比赛数: {stats.processed}")
        logger.info(f"成功更新: {stats.updated}")
        logger.info(f"跳过记录: {stats.skipped}")
        logger.info(f"遇到错误: {stats.errors}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ 收割失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
