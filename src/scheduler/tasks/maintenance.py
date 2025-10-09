"""
    from sqlalchemy import text
    import tempfile

from ..celery_config import app
from .base import BaseDataTask
from src.data.storage.data_lake_storage import DataLakeStorage, S3DataLakeStorage
from src.database.connection import get_async_session

维护任务
Maintenance Tasks

包含数据清理和数据库备份任务。
"""




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


async def _create_database_backup(timestamp: str) -> Tuple[float, str, str, str]:
    """创建数据库备份文件"""
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
) -> Tuple[str, Optional[object], Optional[str]]:
    """上传备份文件到存储"""
    try:
        # 尝试使用S3存储
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


async def _cleanup_old_backups(storage=None, local_backup_dir=None):
    """清理旧备份文件"""
    cleaned_count = 0
    cutoff_date = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7天前

    # 清理S3中的旧备份
    if storage and hasattr(storage, "list_objects"):
        try:
            objects = await storage.list_objects("backups/")
            for obj in objects:
                if obj.get("last_modified", 0) < cutoff_date:
                    await storage.delete_object(obj["key"])
                    cleaned_count += 1
        except Exception as e:
            logger.warning(f"清理S3旧备份失败: {str(e)}")

    # 清理本地旧备份
    if local_backup_dir and os.path.exists(local_backup_dir):
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


async def _cleanup_temp_backup_files(backup_path: str, compressed_path: str):
    """清理临时文件"""
    if os.path.exists(backup_path):
        os.remove(backup_path)
    if os.path.exists(compressed_path) and os.path.dirname(compressed_path) == "/tmp":
        os.remove(compressed_path)


@app.task(base=BaseDataTask)
def backup_database():
    """数据库备份任务"""
    try:
        logger.info("开始执行数据库备份任务")

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
            await _cleanup_temp_backup_files(backup_path, compressed_path)

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