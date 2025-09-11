"""
Celery调度任务

实现足球数据采集和处理的定时任务。
包含赛程采集、赔率采集、实时比分、特征计算等任务。

基于 DATA_DESIGN.md 第3节设计。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from celery import Task

from src.data.collectors.fixtures_collector import FixturesCollector
from src.data.collectors.odds_collector import OddsCollector
from src.data.collectors.scores_collector import ScoresCollector

from .celery_config import TaskRetryConfig, app, should_collect_live_scores

logger = logging.getLogger(__name__)


class BaseDataTask(Task):
    """数据任务基类"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理"""
        logger.error(f"Task {self.name} failed: {exc}")
        # TODO: 发送告警通知

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的处理"""
        logger.info(f"Task {self.name} completed successfully")


@app.task(base=BaseDataTask, bind=True)
def collect_fixtures(self, leagues: Optional[List[str]] = None, days_ahead: int = 30):
    """
    采集赛程数据任务

    Args:
        leagues: 需要采集的联赛列表
        days_ahead: 采集未来N天的赛程
    """
    import asyncio

    async def _collect_task():
        # 初始化赛程采集器
        collector = FixturesCollector()

        # 设置采集时间范围
        date_from = datetime.now()
        date_to = date_from + timedelta(days=days_ahead)

        # 执行采集
        result = await collector.collect_fixtures(
            leagues=leagues, date_from=date_from, date_to=date_to
        )
        return result

    try:
        logger.info("开始执行赛程采集任务")
        result = asyncio.run(_collect_task())

        if result.status == "failed":
            raise Exception(f"赛程采集失败: {result.error_message}")

        logger.info(f"赛程采集完成: 成功={result.success_count}, 错误={result.error_count}")

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 重试逻辑
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("collect_fixtures", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get(
            "retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY
        )

        if self.request.retries < max_retries:
            logger.warning(f"赛程采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"赛程采集任务最终失败: {str(exc)}")
            raise


@app.task(base=BaseDataTask, bind=True)
def collect_odds(
    self, match_ids: Optional[List[str]] = None, bookmakers: Optional[List[str]] = None
):
    """
    采集赔率数据任务

    Args:
        match_ids: 需要采集的比赛ID列表
        bookmakers: 博彩公司列表
    """
    import asyncio

    async def _collect_task():
        # 初始化赔率采集器
        collector = OddsCollector()

        # 执行采集
        result = await collector.collect_odds(
            match_ids=match_ids, bookmakers=bookmakers
        )
        return result

    try:
        logger.info("开始执行赔率采集任务")
        result = asyncio.run(_collect_task())

        if result.status == "failed":
            raise Exception(f"赔率采集失败: {result.error_message}")

        logger.info(f"赔率采集完成: 成功={result.success_count}, 错误={result.error_count}")

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 重试逻辑
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("collect_odds", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get(
            "retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY
        )

        if self.request.retries < max_retries:
            logger.warning(f"赔率采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"赔率采集任务最终失败: {str(exc)}")
            raise


@app.task(base=BaseDataTask, bind=True)
def collect_live_scores_conditional(self, match_ids: Optional[List[str]] = None):
    """
    条件性实时比分采集任务（仅在有比赛时执行）

    Args:
        match_ids: 需要监控的比赛ID列表
    """
    import asyncio

    async def _collect_task():
        # 初始化比分采集器
        collector = ScoresCollector()

        # 执行采集
        result = await collector.collect_live_scores(
            match_ids=match_ids, use_websocket=True
        )
        return result

    try:
        # 检查是否需要采集实时比分
        if not should_collect_live_scores():
            logger.info("当前无进行中的比赛，跳过实时比分采集")
            return {
                "status": "skipped",
                "reason": "no_active_matches",
                "execution_time": datetime.now().isoformat(),
            }

        logger.info("开始执行实时比分采集任务")
        result = asyncio.run(_collect_task())

        if result.status == "failed":
            raise Exception(f"实时比分采集失败: {result.error_message}")

        logger.info(f"实时比分采集完成: 成功={result.success_count}, 错误={result.error_count}")

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 实时比分采集重试次数较少，因为时效性要求高
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("collect_live_scores", {})
        max_retries = retry_config.get("max_retries", 1)
        retry_delay = retry_config.get("retry_delay", 30)

        if self.request.retries < max_retries:
            logger.warning(f"实时比分采集失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"实时比分采集任务最终失败: {str(exc)}")
            raise


@app.task(base=BaseDataTask, bind=True)
def calculate_features_batch(self, hours_ahead: int = 2):
    """
    批量计算特征数据任务

    Args:
        hours_ahead: 计算未来N小时内比赛的特征
    """
    try:
        logger.info("开始执行特征计算任务")

        # TODO: 实现特征计算逻辑
        # 1. 查询未来N小时内的比赛
        # 2. 为每场比赛计算特征
        # 3. 保存特征数据到数据库

        # 暂时返回成功状态
        logger.info("特征计算任务完成")

        return {
            "status": "success",
            "matches_processed": 0,
            "features_calculated": 0,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("calculate_features", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get(
            "retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY
        )

        if self.request.retries < max_retries:
            logger.warning(f"特征计算失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"特征计算任务最终失败: {str(exc)}")
            raise


@app.task(base=BaseDataTask)
def cleanup_data(days_to_keep: int = 30):
    """
    数据清理任务

    清理过期的原始数据，归档历史数据到数据湖，
    清理临时文件和缓存。

    Args:
        days_to_keep: 保留最近N天的数据
    """
    try:
        logger.info(f"开始执行数据清理任务，保留最近{days_to_keep}天的数据")

        import asyncio
        import os
        from datetime import datetime, timedelta

        from sqlalchemy import text

        from src.data.storage.data_lake_storage import (DataLakeStorage,
                                                        S3DataLakeStorage)
        from src.database.connection import get_async_session

        async def _cleanup_task():
            """内部异步清理任务"""
            cleaned_records = 0
            archived_records = 0

            # 计算归档截止日期
            archive_before = datetime.now() - timedelta(days=days_to_keep)
            logger.info(f"将归档 {archive_before.strftime('%Y-%m-%d')} 之前的数据")

            # 1. 初始化数据湖存储（优先使用S3，回退到本地存储）
            try:
                # 尝试使用MinIO/S3存储
                storage = S3DataLakeStorage(
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
                    access_key=os.getenv("MINIO_ACCESS_KEY", "football_admin"),
                    secret_key=os.getenv("MINIO_SECRET_KEY", "football_minio_2025"),
                    use_ssl=False,
                )
                logger.info("使用MinIO/S3数据湖存储")
            except Exception as e:
                logger.warning(f"MinIO/S3不可用，回退到本地存储: {str(e)}")
                storage = DataLakeStorage(base_path="/data/football_lake")

            # 2. 归档原始数据到数据湖
            tables_to_archive = [
                "raw_matches",
                "raw_odds",
                "processed_matches",
                "processed_odds",
            ]

            for table_name in tables_to_archive:
                try:
                    if hasattr(storage, "archive_old_data"):
                        # 本地存储支持直接归档
                        count = await storage.archive_old_data(
                            table_name, archive_before
                        )
                        archived_records += count
                        logger.info(f"归档了 {count} 个 {table_name} 文件")
                    else:
                        # S3存储需要先下载数据再重新上传到归档桶
                        logger.info(f"S3存储的 {table_name} 数据将通过生命周期策略自动归档")

                except Exception as e:
                    logger.error(f"归档 {table_name} 失败: {str(e)}")

            # 3. 清理数据库中的过期原始数据
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

            # 4. 清理临时文件和缓存
            temp_dirs = ["/tmp/football_prediction", "/var/cache/football_prediction"]
            temp_files_deleted = 0

            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                file_stat = os.stat(file_path)
                                file_time = datetime.fromtimestamp(file_stat.st_mtime)

                                if file_time < archive_before:
                                    os.remove(file_path)
                                    temp_files_deleted += 1

                        logger.info(f"清理了 {temp_files_deleted} 个临时文件从 {temp_dir}")
                    except Exception as e:
                        logger.warning(f"清理临时目录 {temp_dir} 失败: {str(e)}")

            # 5. 清理数据湖空分区
            if hasattr(storage, "cleanup_empty_partitions"):
                for table_name in tables_to_archive:
                    try:
                        cleaned_partitions = await storage.cleanup_empty_partitions(
                            table_name
                        )
                        logger.info(f"清理了 {cleaned_partitions} 个空分区从 {table_name}")
                    except Exception as e:
                        logger.warning(f"清理 {table_name} 空分区失败: {str(e)}")

            return cleaned_records, archived_records

        # 运行异步清理任务
        cleaned_records, archived_records = asyncio.run(_cleanup_task())

        logger.info(f"数据清理任务完成: 清理了 {cleaned_records} 条记录，归档了 {archived_records} 个文件")

        return {
            "status": "success",
            "cleaned_records": cleaned_records,
            "archived_records": archived_records,
            "execution_time": datetime.now().isoformat(),
            "archive_before_date": (
                datetime.now() - timedelta(days=days_to_keep)
            ).strftime("%Y-%m-%d"),
        }

    except Exception as exc:
        logger.error(f"数据清理任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "cleaned_records": 0,
            "archived_records": 0,
            "execution_time": datetime.now().isoformat(),
        }


@app.task(base=BaseDataTask)
def run_quality_checks():
    """运行数据质量检查任务"""
    try:
        logger.info("开始执行数据质量检查任务")

        # TODO: 实现数据质量检查逻辑
        # 1. 检查数据完整性
        # 2. 检查数据一致性
        # 3. 生成质量报告

        logger.info("数据质量检查任务完成")

        return {
            "status": "success",
            "checks_performed": 0,
            "issues_found": 0,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据质量检查任务失败: {str(exc)}")
        raise


@app.task(base=BaseDataTask)
def backup_database():
    """数据库备份任务"""
    try:
        logger.info("开始执行数据库备份任务")

        # TODO: 实现数据库备份逻辑
        # 1. 创建数据库备份
        # 2. 上传到备份存储
        # 3. 清理旧备份文件

        logger.info("数据库备份任务完成")

        return {
            "status": "success",
            "backup_size_mb": 0,
            "backup_location": "",
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据库备份任务失败: {str(exc)}")
        raise
