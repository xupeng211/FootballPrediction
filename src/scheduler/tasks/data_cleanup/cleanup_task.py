"""
数据清理任务

负责数据归档、清理和维护。
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from src.data.storage.data_lake_storage import DataLakeStorage, S3DataLakeStorage
from src.database.connection import get_async_session
from sqlalchemy import text
from ...celery_config import app
from ..base.base_task import BaseDataTask

logger = logging.getLogger(__name__)


async def _initialize_storage():
    """初始化数据湖存储"""
    try:
        # 尝试使用MinIO/S3存储
        storage = S3DataLakeStorage(
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER")),
            secret_key=os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD")),
            use_ssl=False,
        )
        logger.info("使用MinIO/S3数据湖存储")
        return storage
    except Exception as e:
        logger.warning(f"MinIO/S3不可用，回退到本地存储: {str(e)}")
        # 使用当前目录下的data子目录，确保测试环境可访问
        data_path = os.path.join(os.getcwd(), "data", "football_lake")
        os.makedirs(data_path, exist_ok=True)
        storage = DataLakeStorage(base_path=data_path)
        return storage


async def _archive_data_to_lake(storage, archive_before):
    """归档数据到数据湖"""
    tables_to_archive = [
        "raw_matches",
        "raw_odds",
        "processed_matches",
        "processed_odds",
    ]

    archived_records = 0
    for table_name in tables_to_archive:
        try:
            if hasattr(storage, "archive_old_data"):
                # 本地存储支持直接归档
                count = await storage.archive_old_data(table_name, archive_before)
                archived_records += count
                logger.info(f"归档了 {count} 个 {table_name} 文件")
            else:
                # S3存储需要先下载数据再重新上传到归档桶
                logger.info(f"S3存储的 {table_name} 数据将通过生命周期策略自动归档")
        except Exception as e:
            logger.error(f"归档 {table_name} 失败: {str(e)}")

    return archived_records


async def _cleanup_expired_database_data(archive_before):
    """清理过期的数据库数据"""
    cleaned_records = 0
    async with get_async_session() as session:
        try:
            # 清理过期的原始比赛数据
            result = await session.execute(
                text(
                    """
                    DELETE FROM raw_match_data
                    WHERE created_at < :archive_date AND processed = true
                """
                ),
                {"archive_date": archive_before},
            )
            match_deleted = result.rowcount
            cleaned_records += match_deleted
            logger.info(f"清理了 {match_deleted} 条过期的原始比赛数据")

            # 清理过期的原始赔率数据
            result = await session.execute(
                text(
                    """
                    DELETE FROM raw_odds_data
                    WHERE created_at < :archive_date AND processed = true
                """
                ),
                {"archive_date": archive_before},
            )
            odds_deleted = result.rowcount
            cleaned_records += odds_deleted
            logger.info(f"清理了 {odds_deleted} 条过期的原始赔率数据")

            # 清理过期的原始比分数据
            result = await session.execute(
                text(
                    """
                    DELETE FROM raw_scores_data
                    WHERE created_at < :archive_date AND processed = true
                """
                ),
                {"archive_date": archive_before},
            )
            scores_deleted = result.rowcount
            cleaned_records += scores_deleted
            logger.info(f"清理了 {scores_deleted} 条过期的原始比分数据")

            # 清理过期的数据采集日志
            result = await session.execute(
                text(
                    """
                    DELETE FROM data_collection_logs
                    WHERE created_at < :archive_date
                """
                ),
                {"archive_date": archive_before},
            )
            log_deleted = result.rowcount
            cleaned_records += log_deleted
            logger.info(f"清理了 {log_deleted} 条过期的数据采集日志")

            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"清理数据库记录失败: {str(e)}")
            raise

    return cleaned_records


async def _cleanup_temp_files(archive_before):
    """清理临时文件"""
    import glob

    temp_dirs = [
        "/tmp/football_data",
        os.path.join(os.getcwd(), "temp"),
        os.path.join(os.getcwd(), "data", "temp"),
    ]

    cleaned_files = 0
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            # 清理旧的临时文件
            for file_pattern in ["*.tmp", "*.temp", "*.json.tmp"]:
                for file_path in glob.glob(os.path.join(temp_dir, file_pattern)):
                    try:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime < archive_before:
                            os.remove(file_path)
                            cleaned_files += 1
                            logger.debug(f"删除临时文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除临时文件失败 {file_path}: {str(e)}")

    return cleaned_files


async def _cleanup_empty_partitions(storage):
    """清理空分区"""
    if hasattr(storage, "cleanup_empty_partitions"):
        try:
            cleaned_partitions = await storage.cleanup_empty_partitions()
            logger.info(f"清理了 {cleaned_partitions} 个空分区")
            return cleaned_partitions
        except Exception as e:
            logger.warning(f"清理空分区失败: {str(e)}")
    return 0


@app.task(base=BaseDataTask)
def cleanup_data(days_to_keep: int = 30):
    """
    数据清理任务

    Args:
        days_to_keep: 保留最近N天的数据
    """
    logger.info(f"开始执行数据清理任务，保留最近 {days_to_keep} 天的数据")

    try:
        archive_before = datetime.now() - timedelta(days=days_to_keep)

        async def _cleanup_task():
            # 1. 初始化存储
            storage = await _initialize_storage()

            # 2. 归档数据到数据湖
            logger.info("开始归档数据到数据湖")
            archived_records = await _archive_data_to_lake(storage, archive_before)

            # 3. 清理过期的数据库数据
            logger.info("开始清理过期的数据库数据")
            cleaned_records = await _cleanup_expired_database_data(archive_before)

            # 4. 清理临时文件
            logger.info("开始清理临时文件")
            cleaned_files = await _cleanup_temp_files(archive_before)

            # 5. 清理空分区
            logger.info("开始清理空分区")
            cleaned_partitions = await _cleanup_empty_partitions(storage)

            return {
                "archived_records": archived_records,
                "cleaned_records": cleaned_records,
                "cleaned_files": cleaned_files,
                "cleaned_partitions": cleaned_partitions,
            }

        # 运行异步清理任务
        results = asyncio.run(_cleanup_task())

        logger.info(
            f"数据清理完成: 归档 {results['archived_records']} 条记录，"
            f"清理 {results['cleaned_records']} 条数据库记录，"
            f"删除 {results['cleaned_files']} 个临时文件，"
            f"清理 {results['cleaned_partitions']} 个空分区"
        )

        return {
            "status": "success",
            "days_to_keep": days_to_keep,
            "cutoff_date": archive_before.isoformat(),
            **results,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据清理任务失败: {str(exc)}")
        raise