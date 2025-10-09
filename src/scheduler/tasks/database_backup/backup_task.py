"""
数据库备份任务

负责创建和管理数据库备份。
"""

import asyncio
import gzip
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

from src.data.storage.data_lake_storage import DataLakeStorage, S3DataLakeStorage
from ...celery_config import app
from ..base.base_task import BaseDataTask

logger = logging.getLogger(__name__)


async def _create_database_backup(timestamp: str) -> tuple:
    """创建数据库备份"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL环境变量未设置")

    # 解析数据库连接信息
    if db_url.startswith("postgresql://"):
        # 提取数据库连接参数
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        db_name = parsed.path[1:]  # 去掉开头的 /
        db_user = parsed.username
        db_password = parsed.password
        db_host = parsed.hostname
        db_port = parsed.port or 5432

        # 创建备份文件路径
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")
        compressed_file = f"{backup_file}.gz"

        # 构建pg_dump命令
        pg_dump_cmd = [
            "pg_dump",
            f"--host={db_host}",
            f"--port={db_port}",
            f"--username={db_user}",
            f"--dbname={db_name}",
            "--no-password",
            "--verbose",
            "--clean",
            "--no-acl",
            "--no-owner",
            "--format=custom",
            f"--file={backup_file}"
        ]

        # 设置密码环境变量
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        try:
            # 执行备份
            logger.info(f"开始创建数据库备份: {backup_file}")
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )

            if result.returncode != 0:
                raise Exception(f"pg_dump失败: {result.stderr}")

            # 压缩备份文件
            logger.info(f"压缩备份文件: {backup_file}")
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # 获取文件大小
            file_size = os.path.getsize(compressed_file)

            # 删除未压缩的文件
            os.remove(backup_file)

            logger.info(f"数据库备份创建成功: {compressed_file} ({file_size} 字节)")

            return compressed_file, file_size

        except subprocess.TimeoutExpired:
            raise Exception("数据库备份超时")
        except Exception as e:
            # 清理失败的备份文件
            if os.path.exists(backup_file):
                os.remove(backup_file)
            if os.path.exists(compressed_file):
                os.remove(compressed_file)
            raise e
    else:
        raise ValueError("不支持的数据库类型，仅支持PostgreSQL")


async def _upload_backup_to_storage(
    local_path: str,
    storage_key: str,
    storage: Optional[DataLakeStorage] = None
) -> str:
    """上传备份到存储"""
    if not storage:
        # 初始化存储
        try:
            storage = S3DataLakeStorage(
                endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER")),
                secret_key=os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD")),
                use_ssl=False,
            )
        except Exception as e:
            logger.warning(f"S3存储不可用: {str(e)}")
            return local_path

    try:
        # 上传文件
        with open(local_path, 'rb') as f:
            await storage.upload_fileobj(
                fileobj=f,
                key=storage_key,
                metadata={
                    "backup_type": "database",
                    "created_at": datetime.now().isoformat(),
                    "source": "celery_task"
                }
            )

        logger.info(f"备份已上传到存储: {storage_key}")

        # 删除本地文件以节省空间
        os.remove(local_path)
        logger.info(f"已删除本地备份文件: {local_path}")

        return f"s3://{storage.bucket_name}/{storage_key}"

    except Exception as e:
        logger.error(f"上传备份失败: {str(e)}")
        return local_path


async def _cleanup_s3_backups(storage, cutoff_date: float) -> int:
    """清理S3中的旧备份"""
    try:
        # 列出备份文件
        objects = await storage.list_objects(
            prefix="backups/database/",
            older_than=cutoff_date
        )

        deleted_count = 0
        for obj in objects:
            await storage.delete_object(obj.key)
            deleted_count += 1
            logger.info(f"删除旧备份: {obj.key}")

        return deleted_count

    except Exception as e:
        logger.error(f"清理S3备份失败: {str(e)}")
        return 0


async def _cleanup_local_backups(local_backup_dir: str, cutoff_date: float) -> int:
    """清理本地旧备份"""
    deleted_count = 0

    if os.path.exists(local_backup_dir):
        for filename in os.listdir(local_backup_dir):
            if filename.startswith("backup_") and filename.endswith(".sql.gz"):
                file_path = os.path.join(local_backup_dir, filename)
                file_mtime = os.path.getmtime(file_path)

                if file_mtime < cutoff_date:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"删除本地旧备份: {filename}")

    return deleted_count


async def _cleanup_old_backups(storage=None, local_backup_dir=None):
    """清理旧备份"""
    # 保留最近7天的备份
    cutoff_date = datetime.now().timestamp() - (7 * 24 * 60 * 60)

    # 清理S3备份
    if storage:
        s3_deleted = await _cleanup_s3_backups(storage, cutoff_date)
    else:
        s3_deleted = 0

    # 清理本地备份
    if local_backup_dir:
        local_deleted = await _cleanup_local_backups(local_backup_dir, cutoff_date)
    else:
        local_deleted = 0

    return s3_deleted + local_deleted


async def _cleanup_temp_files(backup_path: str, compressed_path: str):
    """清理临时文件"""
    for path in [backup_path, compressed_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.debug(f"删除临时文件: {path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败 {path}: {str(e)}")


@app.task(base=BaseDataTask)
def backup_database():
    """
    数据库备份任务
    """
    logger.info("开始执行数据库备份任务")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        async def _backup_task():
            # 1. 创建数据库备份
            backup_file, file_size = await _create_database_backup(timestamp)

            # 2. 上传到存储
            storage_key = f"backups/database/backup_{timestamp}.sql.gz"
            backup_location = await _upload_backup_to_storage(
                backup_file,
                storage_key
            )

            # 3. 清理旧备份
            local_backup_dir = os.path.join(os.getcwd(), "backups")
            storage = None
            if backup_location.startswith("s3://"):
                try:
                    storage = S3DataLakeStorage(
                        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
                        access_key=os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER")),
                        secret_key=os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD")),
                        use_ssl=False,
                    )
                except Exception:
                    pass

            deleted_count = await _cleanup_old_backups(storage, local_backup_dir)

            return {
                "backup_location": backup_location,
                "file_size": file_size,
                "deleted_old_backups": deleted_count
            }

        # 运行异步备份任务
        result = asyncio.run(_backup_task())

        logger.info(
            f"数据库备份完成: {result['backup_location']}, "
            f"大小: {result['file_size']} 字节, "
            f"清理旧备份: {result['deleted_old_backups']} 个"
        )

        return {
            "status": "success",
            "backup_location": result["backup_location"],
            "file_size": result["file_size"],
            "deleted_old_backups": result["deleted_old_backups"],
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"数据库备份任务失败: {str(exc)}")
        raise