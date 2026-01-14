#!/usr/bin/env python3
"""
V41.58: Docker 内部哈希对齐收割脚本
====================================
用途: 在 Docker 容器内执行哈希对齐收割
环境: 必须在 Docker 容器内运行
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import argparse
from loguru import logger

from src.config_unified import get_settings
from src.services.hash_alignment_service import create_hash_alignment_service
import psycopg2
from psycopg2.extras import RealDictCursor


def main():
    parser = argparse.ArgumentParser(description="V41.58 Docker 哈希对齐收割")
    parser.add_argument("--league", required=True, help="联赛名称")
    parser.add_argument("--season", required=True, help="赛季 (如: 23/24)")
    args = parser.parse_args()

    league = args.league
    season = args.season

    logger.info("=" * 60)
    logger.info("V41.58: Docker 哈希对齐收割")
    logger.info("=" * 60)
    logger.info(f"联赛: {league}")
    logger.info(f"赛季: {season}")
    logger.info(f"数据库: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    logger.info("")

    # 获取配置
    settings = get_settings()

    # 连接数据库
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        # 创建哈希对齐服务
        service = create_hash_alignment_service(conn, season=season)

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
