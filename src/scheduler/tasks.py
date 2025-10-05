"""
Celery调度任务

实现足球数据采集和处理的定时任务。
包含赛程采集、赔率采集、实时比分、特征计算等任务。

基于 DATA_DESIGN.md 第3节设计。
"""

import asyncio
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
        # 发送告警通知
        self._send_alert_notification(
            task_name=self.name,
            error=str(exc),
            task_id=task_id,
            args=args,
            kwargs=kwargs,
        )

    def _send_alert_notification(self, task_name, error, task_id, args, kwargs):
        """发送告警通知"""
        try:
            import asyncio

            from src.monitoring.alert_manager import AlertManager

            async def _send_alert():
                alert_manager = AlertManager()

                # 创建告警消息
                alert_message = {
                    "title": f"任务失败告警: {task_name}",
                    "description": f"任务 {task_name} 执行失败",
                    "error": error,
                    "task_id": task_id,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "severity": "high",
                    "timestamp": datetime.now().isoformat(),
                    "source": "celery_task",
                }

                # 发送告警
                result = await alert_manager.send_alert(alert_message)
                if result.get("status") == "success":
                    logger.info(f"告警通知发送成功: {task_name}")
                else:
                    logger.error(f"告警通知发送失败: {result.get('error')}")

            # 运行异步告警发送
            asyncio.run(_send_alert())

        except Exception as e:
            logger.error(f"发送告警通知时出错: {str(e)}")

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

        logger.info(
            f"赛程采集完成: 成功={result.success_count}, 错误={result.error_count}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 重试逻辑
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get(str("collect_fixtures"), {})
        max_retries = retry_config.get(str("max_retries"), TaskRetryConfig.MAX_RETRIES)
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

        logger.info(
            f"赔率采集完成: 成功={result.success_count}, 错误={result.error_count}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 重试逻辑
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get(str("collect_odds"), {})
        max_retries = retry_config.get(str("max_retries"), TaskRetryConfig.MAX_RETRIES)
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

        logger.info(
            f"实时比分采集完成: 成功={result.success_count}, 错误={result.error_count}"
        )

        return {
            "status": result.status,
            "records_collected": result.records_collected,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        # 实时比分采集重试次数较少，因为时效性要求高
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get(str("collect_live_scores"), {})
        max_retries = retry_config.get(str("max_retries"), 1)
        retry_delay = retry_config.get(str("retry_delay"), 30)

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
        logger.info(f"开始执行特征计算任务，计算未来{hours_ahead}小时内的比赛特征")

        import asyncio

        from sqlalchemy import text

        from src.data.features.feature_store import FeatureStore
        from src.database.connection import get_async_session

        async def _calculate_features():
            """异步计算特征"""
            async with get_async_session() as session:
                # 1. 查询未来N小时内的比赛
                result = await session.execute(
                    text(
                        """
                    SELECT id, home_team, away_team, match_date, league_id
                    FROM matches
                    WHERE match_date BETWEEN NOW() AND NOW() + INTERVAL :hours_ahead hours
                    AND status = 'scheduled'
                    ORDER BY match_date ASC
                    """
                    ),
                    {"hours_ahead": hours_ahead},
                )

                matches = result.fetchall()
                if not matches:
                    logger.info(f"未来{hours_ahead}小时内没有需要计算特征的比赛")
                    return 0, 0

                # 2. 初始化特征存储
                feature_store = FeatureStore()

                matches_processed = 0
                features_calculated = 0

                # 3. 为每场比赛计算特征
                for match in matches:
                    try:
                        match_id = match.id
                        home_team = match.home_team
                        away_team = match.away_team
                        match_date = match.match_date
                        league_id = match.league_id

                        logger.info(
                            f"为比赛 {match_id} ({home_team} vs {away_team}) 计算特征"
                        )

                        # 计算比赛特征
                        feature_result = await feature_store.calculate_match_features(
                            match_id=match_id,
                            home_team=home_team,
                            away_team=away_team,
                            match_date=match_date,
                            league_id=league_id,
                        )

                        if feature_result.get("status") == "success":
                            matches_processed += 1
                            features_calculated += feature_result.get(
                                "features_count", 0
                            )
                            logger.info(
                                f"比赛 {match_id} 特征计算成功，生成了 {feature_result.get(str('features_count'), 0)} 个特征"
                            )
                        else:
                            logger.warning(
                                f"比赛 {match_id} 特征计算失败: {feature_result.get(str('error'), 'Unknown error')}"
                            )

                    except Exception as e:
                        logger.error(f"为比赛 {match.id} 计算特征时出错: {str(e)}")
                        continue

                return matches_processed, features_calculated

        # 运行异步特征计算
        matches_processed, features_calculated = asyncio.run(_calculate_features())

        logger.info(
            f"特征计算任务完成: 处理了 {matches_processed} 场比赛，计算了 {features_calculated} 个特征"
        )

        return {
            "status": "success",
            "matches_processed": matches_processed,
            "features_calculated": features_calculated,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get(str("calculate_features"), {})
        max_retries = retry_config.get(str("max_retries"), TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get(
            "retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY
        )

        if self.request.retries < max_retries:
            logger.warning(f"特征计算失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"特征计算任务最终失败: {str(exc)}")
            raise


async def _initialize_storage():
    """初始化数据湖存储"""
    import os
    from src.data.storage.data_lake_storage import DataLakeStorage, S3DataLakeStorage

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
    from sqlalchemy import text
    from src.database.connection import get_async_session

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
    import os
    import tempfile
    from datetime import datetime

    # 使用安全的临时目录获取方法
    temp_base = tempfile.gettempdir()
    temp_dirs = [
        os.path.join(temp_base, "football_prediction"),
        os.path.join(os.path.expanduser("~"), ".cache", "football_prediction"),
    ]
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

    return temp_files_deleted


async def _cleanup_empty_partitions(storage):
    """清理数据湖空分区"""
    tables_to_archive = [
        "raw_matches",
        "raw_odds",
        "processed_matches",
        "processed_odds",
    ]

    if hasattr(storage, "cleanup_empty_partitions"):
        for table_name in tables_to_archive:
            try:
                cleaned_partitions = await storage.cleanup_empty_partitions(table_name)
                logger.info(f"清理了 {cleaned_partitions} 个空分区从 {table_name}")
            except Exception as e:
                logger.warning(f"清理 {table_name} 空分区失败: {str(e)}")


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
        from datetime import datetime, timedelta

        async def _cleanup_task():
            """内部异步清理任务"""
            # 计算归档截止日期
            archive_before = datetime.now() - timedelta(days=days_to_keep)
            logger.info(f"将归档 {archive_before.strftime('%Y-%m-%d')} 之前的数据")

            # 1. 初始化数据湖存储
            storage = await _initialize_storage()

            # 2. 归档数据到数据湖
            archived_records = await _archive_data_to_lake(storage, archive_before)

            # 3. 清理过期数据库数据
            cleaned_records = await _cleanup_expired_database_data(archive_before)

            # 4. 清理临时文件
            await _cleanup_temp_files(archive_before)

            # 5. 清理数据湖空分区
            await _cleanup_empty_partitions(storage)

            return cleaned_records, archived_records

        # 运行异步清理任务
        cleaned_records, archived_records = asyncio.run(_cleanup_task())

        logger.info(
            f"数据清理任务完成: 清理了 {cleaned_records} 条记录，归档了 {archived_records} 个文件"
        )

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


async def _check_data_integrity(session, monitor):
    """检查数据完整性"""
    checks_performed = 0
    issues_found = 0

    logger.info("检查数据完整性...")
    integrity_checks = [
        ("matches", "检查比赛数据完整性"),
        ("teams", "检查球队数据完整性"),
        ("leagues", "检查联赛数据完整性"),
        ("raw_match_data", "检查原始比赛数据完整性"),
        ("raw_odds_data", "检查原始赔率数据完整性"),
    ]

    for table_name, description in integrity_checks:
        try:
            result = await monitor.check_data_integrity(session, table_name)
            checks_performed += 1
            if not result.get("passed", True):
                issues_found += result.get("issues_count", 1)
                logger.warning(f"{description} 发现问题: {result.get('issues', [])}")
            else:
                logger.info(f"{description} 通过")
        except Exception as e:
            logger.error(f"{description} 检查失败: {str(e)}")
            issues_found += 1

    return checks_performed, issues_found


async def _check_data_consistency(session, monitor):
    """检查数据一致性"""
    checks_performed = 0
    issues_found = 0

    logger.info("检查数据一致性...")
    consistency_checks = [
        ("check_match_team_consistency", "检查比赛与球队数据一致性"),
        ("check_odds_match_consistency", "检查赔率与比赛数据一致性"),
        ("check_league_team_consistency", "检查联赛与球队数据一致性"),
    ]

    for check_name, description in consistency_checks:
        try:
            result = await monitor.check_data_consistency(session, check_name)
            checks_performed += 1
            if not result.get("passed", True):
                issues_found += result.get("issues_count", 1)
                logger.warning(f"{description} 发现问题: {result.get('issues', [])}")
            else:
                logger.info(f"{description} 通过")
        except Exception as e:
            logger.error(f"{description} 检查失败: {str(e)}")
            issues_found += 1

    return checks_performed, issues_found


async def _check_data_freshness(session, monitor):
    """检查数据新鲜度"""
    checks_performed = 0
    issues_found = 0

    logger.info("检查数据新鲜度...")
    freshness_checks = [
        ("matches", "检查比赛数据新鲜度", 24),  # 24小时
        ("raw_match_data", "检查原始比赛数据新鲜度", 6),  # 6小时
        ("raw_odds_data", "检查原始赔率数据新鲜度", 12),  # 12小时
    ]

    for table_name, description, hours_threshold in freshness_checks:
        try:
            result = await monitor.check_data_freshness(
                session, table_name, hours_threshold
            )
            checks_performed += 1
            if not result.get("passed", True):
                issues_found += result.get("issues_count", 1)
                logger.warning(f"{description} 发现问题: {result.get('issues', [])}")
            else:
                logger.info(f"{description} 通过")
        except Exception as e:
            logger.error(f"{description} 检查失败: {str(e)}")
            issues_found += 1

    return checks_performed, issues_found


async def _generate_quality_report(session, monitor):
    """生成质量报告"""
    checks_performed = 0
    issues_found = 0

    logger.info("生成数据质量报告...")
    try:
        report_result = await monitor.generate_quality_report(session)
        if report_result.get("status") == "success":
            logger.info("数据质量报告生成成功")
            checks_performed += 1
        else:
            logger.error(
                f"数据质量报告生成失败: {report_result.get('error', 'Unknown error')}"
            )
            issues_found += 1
    except Exception as e:
        logger.error(f"生成数据质量报告时出错: {str(e)}")
        issues_found += 1

    return checks_performed, issues_found


@app.task(base=BaseDataTask)
def run_quality_checks():
    """运行数据质量检查任务"""
    try:
        logger.info("开始执行数据质量检查任务")

        import asyncio
        from datetime import datetime

        from src.data.quality.data_quality_monitor import DataQualityMonitor
        from src.database.connection import get_async_session

        async def _run_checks():
            """异步运行质量检查"""
            async with get_async_session() as session:
                # 初始化数据质量监控器
                monitor = DataQualityMonitor()

                # 1. 检查数据完整性
                integrity_checks, integrity_issues = await _check_data_integrity(
                    session, monitor
                )

                # 2. 检查数据一致性
                consistency_checks, consistency_issues = await _check_data_consistency(
                    session, monitor
                )

                # 3. 检查数据新鲜度
                freshness_checks, freshness_issues = await _check_data_freshness(
                    session, monitor
                )

                # 4. 生成质量报告
                report_checks, report_issues = await _generate_quality_report(
                    session, monitor
                )

                total_checks = (
                    integrity_checks
                    + consistency_checks
                    + freshness_checks
                    + report_checks
                )
                total_issues = (
                    integrity_issues
                    + consistency_issues
                    + freshness_issues
                    + report_issues
                )

                return total_checks, total_issues

        # 运行异步质量检查
        checks_performed, issues_found = asyncio.run(_run_checks())

        logger.info(
            f"数据质量检查任务完成: 执行了 {checks_performed} 项检查，发现 {issues_found} 个问题"
        )

        return {
            "status": "success",
            "checks_performed": checks_performed,
            "issues_found": issues_found,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据质量检查任务失败: {str(exc)}")
        raise


async def _create_database_backup(timestamp: str) -> tuple:
    """创建数据库备份文件"""
    import os
    import subprocess
    import gzip
    import shutil

    backup_filename = f"football_prediction_backup_{timestamp}.sql"
    backup_path = f"/tmp/{backup_filename}"
    compressed_path = f"{backup_path}.gz"

    try:
        # 获取数据库连接信息
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "football_prediction_dev")
        db_user = os.getenv("DB_USER", "football_user")
        db_password = os.getenv("DB_PASSWORD", "")

        # 使用pg_dump创建备份
        pg_dump_cmd = [
            "pg_dump",
            f"--host={db_host}",
            f"--port={db_port}",
            f"--username={db_user}",
            f"--dbname={db_name}",
            "--no-password",
            "--verbose",
            "--file=" + backup_path,
            "--format=custom",
            "--compress=9",
        ]

        # 设置PGPASSWORD环境变量
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        logger.info("开始创建数据库备份...")
        result = subprocess.run(pg_dump_cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"pg_dump失败: {result.stderr}")

        # 压缩备份文件
        logger.info("压缩备份文件...")
        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # 获取备份文件大小
        backup_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)

        return backup_size_mb, backup_path, compressed_path, backup_filename

    except Exception:
        # 清理临时文件
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
        raise


async def _upload_backup_to_storage(
    compressed_path: str, backup_filename: str
) -> tuple:
    """上传备份文件到存储"""
    import os
    import shutil

    try:
        # 尝试使用S3存储
        from src.data.storage.data_lake_storage import S3DataLakeStorage

        storage = S3DataLakeStorage(
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER")),
            secret_key=os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD")),
            use_ssl=False,
        )

        # 上传到备份桶
        backup_key = f"backups/{backup_filename}.gz"
        upload_result = await storage.upload_file(compressed_path, backup_key)

        if upload_result.get("status") == "success":
            backup_location = f"s3://{backup_key}"
            logger.info(f"备份文件已上传到: {backup_location}")
            return backup_location, storage, None
        else:
            raise Exception(f"S3上传失败: {upload_result.get('error')}")

    except Exception as e:
        logger.warning(f"S3存储不可用，回退到本地存储: {str(e)}")
        # 使用本地存储
        local_backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(local_backup_dir, exist_ok=True)
        local_backup_path = os.path.join(local_backup_dir, f"{backup_filename}.gz")
        shutil.move(compressed_path, local_backup_path)
        backup_location = local_backup_path
        logger.info(f"备份文件已保存到本地: {backup_location}")
        return backup_location, None, local_backup_dir


async def _cleanup_s3_backups(storage, cutoff_date: float) -> int:
    """清理S3中的旧备份"""
    cleaned_count = 0
    try:
        objects = await storage.list_objects("backups/")
        for obj in objects:
            if obj.get("last_modified", 0) < cutoff_date:
                await storage.delete_object(obj["key"])
                cleaned_count += 1
    except Exception as e:
        logger.warning(f"清理S3旧备份失败: {str(e)}")
    return cleaned_count


async def _cleanup_local_backups(local_backup_dir: str, cutoff_date: float) -> int:
    """清理本地旧备份"""
    import os

    cleaned_count = 0
    try:
        for filename in os.listdir(local_backup_dir):
            filepath = os.path.join(local_backup_dir, filename)
            if os.path.isfile(filepath) and filename.endswith(".gz"):
                file_time = os.path.getmtime(filepath)
                if file_time < cutoff_date:
                    os.remove(filepath)
                    cleaned_count += 1
    except Exception as e:
        logger.warning(f"清理本地旧备份失败: {str(e)}")
    return cleaned_count


async def _cleanup_old_backups(storage=None, local_backup_dir=None):
    """清理旧备份文件"""
    from datetime import datetime

    cleaned_count = 0
    cutoff_date = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7天前

    # 清理S3中的旧备份
    if storage and hasattr(storage, "list_objects"):
        cleaned_count += await _cleanup_s3_backups(storage, cutoff_date)

    # 清理本地旧备份
    if local_backup_dir and os.path.exists(local_backup_dir):
        cleaned_count += await _cleanup_local_backups(local_backup_dir, cutoff_date)

    return cleaned_count


async def _cleanup_temp_files(backup_path: str, compressed_path: str):
    """清理临时文件"""
    import os

    if os.path.exists(backup_path):
        os.remove(backup_path)
    if os.path.exists(compressed_path) and os.path.dirname(compressed_path) == "/tmp":
        os.remove(compressed_path)


@app.task(base=BaseDataTask)
def backup_database():
    """数据库备份任务"""
    try:
        logger.info("开始执行数据库备份任务")

        import asyncio
        from datetime import datetime

        async def _backup_database():
            """异步备份数据库"""
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. 创建数据库备份
            (
                backup_size_mb,
                backup_path,
                compressed_path,
                backup_filename,
            ) = await _create_database_backup(timestamp)

            # 2. 上传到备份存储
            (
                backup_location,
                storage,
                local_backup_dir,
            ) = await _upload_backup_to_storage(compressed_path, backup_filename)

            # 3. 清理旧备份文件（保留最近7天）
            try:
                logger.info("清理旧备份文件...")
                cleanup_result = await _cleanup_old_backups(storage, local_backup_dir)
                logger.info(f"清理了 {cleanup_result} 个旧备份文件")
            except Exception as e:
                logger.warning(f"清理旧备份文件时出错: {str(e)}")

            # 4. 清理临时文件
            await _cleanup_temp_files(backup_path, compressed_path)

            return backup_size_mb, backup_location

        # 运行异步备份
        backup_size_mb, backup_location = asyncio.run(_backup_database())

        logger.info(
            f"数据库备份任务完成: 备份大小 {backup_size_mb:.2f} MB，保存位置 {backup_location}"
        )

        return {
            "status": "success",
            "backup_size_mb": round(backup_size_mb, 2),
            "backup_location": backup_location,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据库备份任务失败: {str(exc)}")
        return {
            "status": "failed",
            "error": str(exc),
            "backup_size_mb": 0,
            "backup_location": "",
            "execution_time": datetime.now().isoformat(),
        }


@app.task(base=BaseDataTask, bind=True)
def generate_predictions(self, match_ids: Optional[List[int]] = None):
    """
    生成预测任务

    Args:
        match_ids: 需要生成预测的比赛ID列表
    """
    try:
        logger.info("开始执行预测生成任务")

        import asyncio

        from sqlalchemy import text

        from src.database.connection import get_async_session
        from src.models.prediction_service import PredictionService

        async def _generate_predictions():
            """异步生成预测"""
            async with get_async_session() as session:
                # 1. 获取待预测的比赛
                if match_ids:
                    # 指定比赛ID
                    result = await session.execute(
                        text(
                            """
                        SELECT id, home_team, away_team, match_date, league_id
                        FROM matches
                        WHERE id = ANY(:match_ids)
                        AND match_date > NOW()
                        AND status = 'scheduled'
                        """
                        ),
                        {"match_ids": match_ids},
                    )
                else:
                    # 获取未来24小时内待预测的比赛
                    result = await session.execute(
                        text(
                            """
                        SELECT id, home_team, away_team, match_date, league_id
                        FROM matches
                        WHERE match_date BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                        AND status = 'scheduled'
                        ORDER BY match_date ASC
                        """
                        )
                    )

                matches = result.fetchall()
                if not matches:
                    logger.info("没有找到需要预测的比赛")
                    return 0

                # 2. 初始化预测服务
                prediction_service = PredictionService()

                predictions_generated = 0

                # 3. 为每场比赛生成预测
                for match in matches:
                    try:
                        match_id = match.id
                        home_team = match.home_team
                        away_team = match.away_team
                        match_date = match.match_date
                        league_id = match.league_id

                        logger.info(
                            f"为比赛 {match_id} ({home_team} vs {away_team}) 生成预测"
                        )

                        # 生成预测
                        prediction_result = (
                            await prediction_service.generate_match_prediction(
                                match_id=match_id,
                                home_team=home_team,
                                away_team=away_team,
                                match_date=match_date,
                                league_id=league_id,
                            )
                        )

                        if prediction_result.get("status") == "success":
                            predictions_generated += 1
                            logger.info(f"比赛 {match_id} 预测生成成功")
                        else:
                            logger.warning(
                                f"比赛 {match_id} 预测生成失败: {prediction_result.get(str('error'), 'Unknown error')}"
                            )

                    except Exception as e:
                        logger.error(f"为比赛 {match.id} 生成预测时出错: {str(e)}")
                        continue

                return predictions_generated

        # 运行异步预测生成
        predictions_generated = asyncio.run(_generate_predictions())

        logger.info(f"预测生成任务完成: 生成了 {predictions_generated} 个预测")

        return {
            "status": "success",
            "predictions_generated": predictions_generated,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"预测生成任务失败: {str(exc)}")
        raise


def _get_bronze_table_query(table_name: str) -> str:
    """获取Bronze表查询语句"""
    queries = {
        "raw_matches": """
            SELECT id, data, created_at, source
            FROM raw_matches
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
        "raw_odds": """
            SELECT id, data, created_at, source
            FROM raw_odds
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
        "raw_scores": """
            SELECT id, data, created_at, source
            FROM raw_scores
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
    }
    return queries.get(table_name)


def _get_update_query(table_name: str):
    """获取更新查询语句"""
    from sqlalchemy import text

    queries = {
        "raw_matches": text(
            """
            UPDATE raw_matches
            SET processed = true, processed_at = NOW()
            WHERE id = :record_id
        """
        ),
        "raw_odds": text(
            """
            UPDATE raw_odds
            SET processed = true, processed_at = NOW()
            WHERE id = :record_id
        """
        ),
        "raw_scores": text(
            """
            UPDATE raw_scores
            SET processed = true, processed_at = NOW()
            WHERE id = :record_id
        """
        ),
    }
    return queries.get(table_name)


async def _transform_to_silver_format(cleaned_data, bronze_table, record_id):
    """转换为Silver层格式"""
    from datetime import datetime

    if bronze_table == "raw_matches":
        # 转换比赛数据
        return {
            "match_id": cleaned_data.get("match_id"),
            "home_team": cleaned_data.get("home_team"),
            "away_team": cleaned_data.get("away_team"),
            "match_date": cleaned_data.get("match_date"),
            "league_id": cleaned_data.get("league_id"),
            "venue": cleaned_data.get("venue"),
            "status": cleaned_data.get("status", "scheduled"),
            "source": cleaned_data.get("source"),
            "processed_at": datetime.now().isoformat(),
            "data_quality_score": cleaned_data.get("quality_score", 1.0),
        }

    elif bronze_table == "raw_odds":
        # 转换赔率数据
        return {
            "match_id": cleaned_data.get("match_id"),
            "bookmaker": cleaned_data.get("bookmaker"),
            "home_win_odds": cleaned_data.get("home_win_odds"),
            "draw_odds": cleaned_data.get("draw_odds"),
            "away_win_odds": cleaned_data.get("away_win_odds"),
            "timestamp": cleaned_data.get("timestamp"),
            "source": cleaned_data.get("source"),
            "processed_at": datetime.now().isoformat(),
            "data_quality_score": cleaned_data.get("quality_score", 1.0),
        }

    elif bronze_table == "raw_scores":
        # 转换比分数据
        return {
            "match_id": cleaned_data.get("match_id"),
            "home_score": cleaned_data.get("home_score"),
            "away_score": cleaned_data.get("away_score"),
            "match_status": cleaned_data.get("match_status"),
            "timestamp": cleaned_data.get("timestamp"),
            "source": cleaned_data.get("source"),
            "processed_at": datetime.now().isoformat(),
            "data_quality_score": cleaned_data.get("quality_score", 1.0),
        }
    else:
        raise ValueError(f"未知的Bronze表类型: {bronze_table}")


async def _save_to_silver_layer(session, silver_data, bronze_table):
    """保存到Silver层"""
    from sqlalchemy import text

    # 确定Silver表名
    silver_table_map = {
        "raw_matches": "silver_matches",
        "raw_odds": "silver_odds",
        "raw_scores": "silver_scores",
    }
    silver_table = silver_table_map.get(bronze_table)

    if not silver_table:
        raise ValueError(f"无法找到对应的Silver表: {bronze_table}")

    # 验证表名防止SQL注入
    valid_silver_tables = ["silver_matches", "silver_odds", "silver_scores"]
    if silver_table not in valid_silver_tables:
        raise ValueError(f"非法的Silver表名: {silver_table}")

    # 构建插入SQL
    if bronze_table == "raw_matches":
        insert_query = text(
            """
            INSERT INTO silver_matches
            (match_id, home_team, away_team, match_date, league_id, venue, status, source, processed_at, data_quality_score)
            VALUES (:match_id, :home_team, :away_team, :match_date, :league_id, :venue, :status, :source, :processed_at, :data_quality_score)
            ON CONFLICT (match_id) DO UPDATE SET
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            match_date = EXCLUDED.match_date,
            league_id = EXCLUDED.league_id,
            venue = EXCLUDED.venue,
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            processed_at = EXCLUDED.processed_at,
            data_quality_score = EXCLUDED.data_quality_score
        """
        )
        await session.execute(insert_query, silver_data)

    elif bronze_table == "raw_odds":
        insert_query = text(
            """
            INSERT INTO silver_odds
            (match_id, bookmaker, home_win_odds, draw_odds, away_win_odds, timestamp, source, processed_at, data_quality_score)
            VALUES (:match_id, :bookmaker, :home_win_odds, :draw_odds, :away_win_odds, :timestamp, :source, :processed_at, :data_quality_score)
            ON CONFLICT (match_id, bookmaker, timestamp) DO UPDATE SET
            home_win_odds = EXCLUDED.home_win_odds,
            draw_odds = EXCLUDED.draw_odds,
            away_win_odds = EXCLUDED.away_win_odds,
            source = EXCLUDED.source,
            processed_at = EXCLUDED.processed_at,
            data_quality_score = EXCLUDED.data_quality_score
        """
        )
        await session.execute(insert_query, silver_data)

    elif bronze_table == "raw_scores":
        insert_query = text(
            """
            INSERT INTO silver_scores
            (match_id, home_score, away_score, match_status, timestamp, source, processed_at, data_quality_score)
            VALUES (:match_id, :home_score, :away_score, :match_status, :timestamp, :source, :processed_at, :data_quality_score)
            ON CONFLICT (match_id, timestamp) DO UPDATE SET
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            match_status = EXCLUDED.match_status,
            source = EXCLUDED.source,
            processed_at = EXCLUDED.processed_at,
            data_quality_score = EXCLUDED.data_quality_score
        """
        )
        await session.execute(insert_query, silver_data)


async def _process_bronze_record(
    session, record, table_name: str, data_cleaner, quality_monitor
):
    """处理单个Bronze记录"""
    try:
        raw_data = record.data
        source = record.source
        record_id = record.id

        # 数据清洗
        cleaned_data = await data_cleaner.clean_football_data(
            raw_data,
            data_type=table_name.replace("raw_", ""),
            source=source,
        )

        # 数据质量验证
        quality_result = await quality_monitor.validate_data_quality(
            cleaned_data,
            data_type=table_name.replace("raw_", ""),
        )

        if quality_result.get("passed", False):
            # 转换为Silver层格式
            silver_data = await _transform_to_silver_format(
                cleaned_data, table_name, record_id
            )

            # 保存到Silver层
            await _save_to_silver_layer(session, silver_data, table_name)

            # 标记Bronze记录为已处理
            update_query = _get_update_query(table_name)
            if update_query:
                await session.execute(update_query, {"record_id": record_id})

            return True
        else:
            logger.warning(f"数据质量验证失败: {quality_result.get('issues', [])}")
            return False
    except Exception as e:
        logger.error(f"处理记录 {record.id} 时出错: {str(e)}")
        return False


async def _process_bronze_table(
    session, table_name: str, batch_size: int, data_cleaner, quality_monitor
):
    """处理单个Bronze表"""
    logger.info(f"处理 {table_name} 表的数据...")

    # 验证表名
    valid_tables = ["raw_matches", "raw_odds", "raw_scores"]
    if table_name not in valid_tables:
        logger.error(f"非法表名: {table_name}")
        return 0

    # 获取查询语句
    from sqlalchemy import text

    query = _get_bronze_table_query(table_name)
    if not query:
        logger.error(f"不支持的表名: {table_name}")
        return 0

    # 执行查询
    result = await session.execute(text(query), {"batch_size": batch_size})
    bronze_records = result.fetchall()

    if not bronze_records:
        logger.info(f"{table_name} 表没有需要处理的数据")
        return 0

    # 处理记录
    logger.info(f"清洗和验证 {table_name} 数据...")
    records_processed = 0

    for record in bronze_records:
        if await _process_bronze_record(
            session, record, table_name, data_cleaner, quality_monitor
        ):
            records_processed += 1

        if records_processed % 100 == 0:
            logger.info(f"已处理 {records_processed} 条记录...")

    logger.info(f"完成 {table_name} 表的批次处理，处理了 {len(bronze_records)} 条记录")
    return records_processed


@app.task(base=BaseDataTask, bind=True)
def process_bronze_to_silver(self, batch_size: int = 1000):
    """
    Bronze层到Silver层数据处理任务

    Args:
        batch_size: 批处理大小
    """
    try:
        logger.info("开始执行Bronze到Silver数据处理任务")

        import asyncio

        from src.data.processing.football_data_cleaner import FootballDataCleaner
        from src.data.quality.data_quality_monitor import DataQualityMonitor
        from src.database.connection import get_async_session

        async def _process_data():
            """异步处理数据"""
            async with get_async_session() as session:
                # 初始化处理器
                data_cleaner = FootballDataCleaner()
                quality_monitor = DataQualityMonitor()

                records_processed = 0
                batches_processed = 0

                # 从Bronze层读取原始数据
                logger.info("从Bronze层读取原始数据...")
                bronze_tables = [
                    "raw_matches",
                    "raw_odds",
                    "raw_scores",
                ]

                for table_name in bronze_tables:
                    try:
                        table_records = await _process_bronze_table(
                            session,
                            table_name,
                            batch_size,
                            data_cleaner,
                            quality_monitor,
                        )
                        records_processed += table_records
                        batches_processed += 1
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"处理 {table_name} 表时出错: {str(e)}")
                        continue

                return records_processed, batches_processed

        # 运行异步数据处理
        records_processed, batches_processed = asyncio.run(_process_data())

        logger.info(
            f"Bronze到Silver数据处理任务完成: 处理了 {records_processed} 条记录，{batches_processed} 个批次"
        )

        return {
            "status": "success",
            "records_processed": records_processed,
            "batches_processed": batches_processed,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Bronze到Silver数据处理任务失败: {str(exc)}")
        raise


# 为兼容性添加任务别名
calculate_features_task = calculate_features_batch
collect_fixtures_task = collect_fixtures
collect_odds_task = collect_odds
generate_predictions_task = generate_predictions
process_data_task = process_bronze_to_silver
