#!/usr/bin/env python3
"""
数据库备份恢复工具
支持全量备份、增量备份、定时备份和恢复功能
"""

import os
import sys
import asyncio
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from src.core.logging import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


class DatabaseBackupManager:
    """数据库备份管理器"""

    def __init__(self):
        self.settings = get_settings()
        self.backup_dir = Path("backups/database")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 备份配置
        self.backup_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "football_prediction"),
            "username": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD"),
            "retention_days": int(os.getenv("BACKUP_RETENTION_DAYS", "30")),
            "s3_bucket": os.getenv("BACKUP_S3_BUCKET"),
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "encryption_key": os.getenv("BACKUP_ENCRYPTION_KEY"),
        }

    def get_backup_filename(self, backup_type: str, timestamp: datetime = None) -> str:
        """生成备份文件名"""
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{backup_type}_{self.backup_config['database']}_{date_str}.sql"

    async def create_full_backup(
        self, compress: bool = True, encrypt: bool = True
    ) -> Dict[str, Any]:
        """创建全量备份"""
        logger.info("开始创建全量数据库备份...")

        timestamp = datetime.now()
        filename = self.get_backup_filename("full", timestamp)
        filepath = self.backup_dir / filename

        try:
            # 构建pg_dump命令
            cmd = [
                "pg_dump",
                "-h",
                self.backup_config["host"],
                "-p",
                self.backup_config["port"],
                "-U",
                self.backup_config["username"],
                "-d",
                self.backup_config["database"],
                "--verbose",
                "--clean",
                "--no-owner",
                "--no-privileges",
                "--format=custom",
                f"--file={filepath}",
            ]

            # 设置密码环境变量
            env = os.environ.copy()
            env["PGPASSWORD"] = self.backup_config["password"]

            # 执行备份
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                file_size = filepath.stat().st_size

                result = {
                    "success": True,
                    "type": "full",
                    "filename": filename,
                    "filepath": str(filepath),
                    "size_bytes": file_size,
                    "size_human": self._format_bytes(file_size),
                    "timestamp": timestamp,
                    "duration": (datetime.now() - timestamp).total_seconds(),
                }

                # 压缩备份文件
                if compress:
                    await self._compress_backup(filepath)

                # 加密备份文件
                if encrypt and self.backup_config["encryption_key"]:
                    await self._encrypt_backup(filepath)

                # 上传到S3
                if self.backup_config["s3_bucket"]:
                    await self._upload_to_s3(filepath, filename)

                logger.info(
                    "全量备份成功", filename=filename, size=result["size_human"]
                )

                return result
            else:
                error_msg = stderr.decode() if stderr else "未知错误"
                logger.error(f"备份失败: {error_msg}")
                return {"success": False, "error": error_msg, "type": "full"}

        except Exception as e:
            logger.error("创建备份失败", error=str(e))
            return {"success": False, "error": str(e), "type": "full"}

    async def create_incremental_backup(self) -> Dict[str, Any]:
        """创建增量备份（基于WAL）"""
        logger.info("开始创建增量备份...")

        # PostgreSQL的增量备份通常通过WAL归档实现
        # 这里创建一个基础备份并启用WAL归档

        timestamp = datetime.now()
        filename = self.get_backup_filename("incremental", timestamp)
        filepath = self.backup_dir / filename

        try:
            # 创建基础备份
            cmd = [
                "pg_basebackup",
                "-h",
                self.backup_config["host"],
                "-p",
                self.backup_config["port"],
                "-U",
                self.backup_config["username"],
                "-D",
                str(filepath),
                "-Ft",  # tar格式
                "-z",  # 压缩
                "-P",  # 显示进度
                "-W",  # 写入恢复配置
                "-v",  # 详细模式
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = self.backup_config["password"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # 计算备份大小
                total_size = 0
                for root, dirs, files in os.walk(filepath):
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))

                result = {
                    "success": True,
                    "type": "incremental",
                    "filename": filename,
                    "filepath": str(filepath),
                    "size_bytes": total_size,
                    "size_human": self._format_bytes(total_size),
                    "timestamp": timestamp,
                    "duration": (datetime.now() - timestamp).total_seconds(),
                }

                # 上传到S3
                if self.backup_config["s3_bucket"]:
                    await self._upload_directory_to_s3(filepath, filename)

                logger.info(
                    "增量备份成功", filename=filename, size=result["size_human"]
                )

                return result
            else:
                error_msg = stderr.decode() if stderr else "未知错误"
                logger.error(f"增量备份失败: {error_msg}")
                return {"success": False, "error": error_msg, "type": "incremental"}

        except Exception as e:
            logger.error("创建增量备份失败", error=str(e))
            return {"success": False, "error": str(e), "type": "incremental"}

    async def restore_database(
        self, backup_file: str, drop_existing: bool = False
    ) -> Dict[str, Any]:
        """恢复数据库"""
        logger.info(f"开始恢复数据库: {backup_file}")

        backup_path = Path(backup_file)
        if not backup_path.exists():
            # 尝试从S3下载
            if self.backup_config["s3_bucket"]:
                backup_path = await self._download_from_s3(backup_file)
                if not backup_path:
                    return {
                        "success": False,
                        "error": f"备份文件 {backup_file} 不存在且无法从S3下载",
                    }
            else:
                return {"success": False, "error": f"备份文件 {backup_file} 不存在"}

        timestamp = datetime.now()

        try:
            # 如果需要，先删除现有数据库
            if drop_existing:
                await self._drop_database()

            # 创建新数据库
            await self._create_database()

            # 检查备份文件类型
            if backup_path.suffix == ".gz":
                # 解压文件
                uncompressed_path = backup_path.with_suffix("")
                await self._decompress_backup(backup_path, uncompressed_path)
                backup_path = uncompressed_path

            # 使用pg_restore恢复
            cmd = [
                "pg_restore",
                "-h",
                self.backup_config["host"],
                "-p",
                self.backup_config["port"],
                "-U",
                self.backup_config["username"],
                "-d",
                self.backup_config["database"],
                "--verbose",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                str(backup_path),
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = self.backup_config["password"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = {
                    "success": True,
                    "backup_file": backup_file,
                    "timestamp": timestamp,
                    "duration": (datetime.now() - timestamp).total_seconds(),
                }

                logger.info("数据库恢复成功", backup_file=backup_file)
                return result
            else:
                error_msg = stderr.decode() if stderr else "未知错误"
                logger.error(f"恢复失败: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "backup_file": backup_file,
                }

        except Exception as e:
            logger.error("恢复数据库失败", error=str(e))
            return {"success": False, "error": str(e), "backup_file": backup_file}

    async def list_backups(self, backup_type: str = None) -> List[Dict[str, Any]]:
        """列出备份文件"""
        backups = []

        # 列出本地备份
        for file in self.backup_dir.glob("*.sql*"):
            if file.is_file():
                stat = file.stat()
                filename = file.name

                # 解析备份类型
                if "full_" in filename:
                    type = "full"
                elif "incremental_" in filename:
                    type = "incremental"
                else:
                    type = "unknown"

                if backup_type and type != backup_type:
                    continue

                backups.append(
                    {
                        "filename": filename,
                        "filepath": str(file),
                        "type": type,
                        "size_bytes": stat.st_size,
                        "size_human": self._format_bytes(stat.st_size),
                        "created_at": datetime.fromtimestamp(stat.st_ctime),
                        "location": "local",
                    }
                )

        # 列出S3备份（如果配置了）
        if self.backup_config["s3_bucket"]:
            s3_backups = await self._list_s3_backups(backup_type)
            backups.extend(s3_backups)

        # 按创建时间排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        return backups

    async def cleanup_old_backups(self) -> int:
        """清理旧备份文件"""
        logger.info("开始清理旧备份文件...")

        cutoff_date = datetime.now() - timedelta(
            days=self.backup_config["retention_days"]
        )
        deleted_count = 0

        # 清理本地备份
        for file in self.backup_dir.glob("*"):
            if file.is_file():
                stat = file.stat()
                if datetime.fromtimestamp(stat.st_ctime) < cutoff_date:
                    try:
                        file.unlink()
                        deleted_count += 1
                        logger.info(f"删除旧备份: {file.name}")
                    except Exception as e:
                        logger.error(f"删除备份文件失败: {file.name}", error=str(e))

        # 清理S3备份
        if self.backup_config["s3_bucket"]:
            s3_deleted = await self._cleanup_s3_backups(cutoff_date)
            deleted_count += s3_deleted

        logger.info(f"清理完成，删除了 {deleted_count} 个旧备份文件")
        return deleted_count

    async def verify_backup(self, backup_file: str) -> Dict[str, Any]:
        """验证备份文件完整性"""
        backup_path = Path(backup_file)

        if not backup_path.exists():
            return {"success": False, "error": "备份文件不存在"}

        try:
            # 对于自定义格式的备份，使用pg_restore验证
            if backup_path.suffix == ".sql" or backup_path.suffix == ".dump":
                cmd = ["pg_restore", "--list", str(backup_path)]

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    # 计算校验和
                    import hashlib

                    with open(backup_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()

                    return {
                        "success": True,
                        "valid": True,
                        "checksum": file_hash,
                        "size_bytes": backup_path.stat().st_size,
                    }
                else:
                    return {
                        "success": False,
                        "valid": False,
                        "error": stderr.decode() if stderr else "验证失败",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def schedule_backup(
        self, backup_type: str = "full", schedule: str = "0 2 * * *"
    ):
        """调度定时备份"""
        logger.info(f"调度定时备份: {backup_type}, 计划: {schedule}")

        # 这里可以使用APScheduler等任务调度器
        # 简单示例：每天凌晨2点执行备份
        import schedule
        import time

        def run_backup():
            asyncio.run(self._run_scheduled_backup(backup_type))

        # 解析cron表达式并设置调度
        if schedule == "0 2 * * *":  # 每天凌晨2点
            schedule.every().day.at("02:00").do(run_backup)
        elif schedule == "0 */6 * * *":  # 每6小时
            schedule.every(6).hours.do(run_backup)
        else:
            logger.warning(f"不支持的调度表达式: {schedule}")

        # 运行调度器
        while True:
            schedule.run_pending()
            time.sleep(60)

    async def _run_scheduled_backup(self, backup_type: str):
        """执行调度的备份"""
        if backup_type == "full":
            result = await self.create_full_backup()
        elif backup_type == "incremental":
            result = await self.create_incremental_backup()
        else:
            logger.error(f"不支持的备份类型: {backup_type}")
            return

        if result["success"]:
            logger.info("定时备份成功", filename=result["filename"])

            # 清理旧备份
            await self.cleanup_old_backups()
        else:
            logger.error("定时备份失败", error=result.get("error"))

    # 辅助方法
    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"

    async def _compress_backup(self, filepath: Path):
        """压缩备份文件"""
        logger.info(f"压缩备份文件: {filepath.name}")

        cmd = ["gzip", str(filepath)]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.communicate()

    async def _decompress_backup(self, compressed_path: Path, output_path: Path):
        """解压备份文件"""
        logger.info(f"解压备份文件: {compressed_path.name}")

        cmd = ["gunzip", "-c", str(compressed_path)]

        with open(output_path, "wb") as f:
            process = await asyncio.create_subprocess_exec(*cmd, stdout=f)
            await process.communicate()

    async def _encrypt_backup(self, filepath: Path):
        """加密备份文件"""
        if not self.backup_config["encryption_key"]:
            return

        logger.info(f"加密备份文件: {filepath.name}")

        cmd = [
            "gpg",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "--batch",
            "--passphrase",
            self.backup_config["encryption_key"],
            "--output",
            f"{filepath}.gpg",
            str(filepath),
        ]

        process = await asyncio.create_subprocess_exec(*cmd)
        await process.communicate()

        # 删除原文件
        filepath.unlink()

    async def _upload_to_s3(self, filepath: Path, filename: str):
        """上传备份到S3"""
        if not self.backup_config["s3_bucket"]:
            return

        try:
            s3_client = boto3.client("s3", region_name=self.backup_config["aws_region"])

            s3_client.upload_file(
                str(filepath),
                self.backup_config["s3_bucket"],
                f"database-backups/{filename}",
            )

            logger.info(
                f"备份已上传到S3: s3://{self.backup_config['s3_bucket']}/database-backups/{filename}"
            )

        except ClientError as e:
            logger.error("上传到S3失败", error=str(e))

    async def _download_from_s3(self, filename: str) -> Optional[Path]:
        """从S3下载备份"""
        if not self.backup_config["s3_bucket"]:
            return None

        try:
            s3_client = boto3.client("s3", region_name=self.backup_config["aws_region"])

            download_path = self.backup_dir / filename

            s3_client.download_file(
                self.backup_config["s3_bucket"],
                f"database-backups/{filename}",
                str(download_path),
            )

            logger.info(f"备份已从S3下载: {filename}")
            return download_path

        except ClientError as e:
            logger.error("从S3下载失败", error=str(e))
            return None

    async def _drop_database(self):
        """删除现有数据库"""
        cmd = [
            "dropdb",
            "-h",
            self.backup_config["host"],
            "-p",
            self.backup_config["port"],
            "-U",
            self.backup_config["username"],
            "--if-exists",
            self.backup_config["database"],
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = self.backup_config["password"]

        process = await asyncio.create_subprocess_exec(*cmd, env=env)
        await process.communicate()

    async def _create_database(self):
        """创建新数据库"""
        cmd = [
            "createdb",
            "-h",
            self.backup_config["host"],
            "-p",
            self.backup_config["port"],
            "-U",
            self.backup_config["username"],
            self.backup_config["database"],
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = self.backup_config["password"]

        process = await asyncio.create_subprocess_exec(*cmd, env=env)
        await process.communicate()

    async def _list_s3_backups(self, backup_type: str = None) -> List[Dict[str, Any]]:
        """列出S3中的备份"""
        if not self.backup_config["s3_bucket"]:
            return []

        try:
            s3_client = boto3.client("s3", region_name=self.backup_config["aws_region"])

            response = s3_client.list_objects_v2(
                Bucket=self.backup_config["s3_bucket"], Prefix="database-backups/"
            )

            backups = []
            for obj in response.get("Contents", []):
                filename = obj["Key"].replace("database-backups/", "")

                if "full_" in filename:
                    type = "full"
                elif "incremental_" in filename:
                    type = "incremental"
                else:
                    type = "unknown"

                if backup_type and type != backup_type:
                    continue

                backups.append(
                    {
                        "filename": filename,
                        "filepath": f"s3://{self.backup_config['s3_bucket']}/{obj['Key']}",
                        "type": type,
                        "size_bytes": obj["Size"],
                        "size_human": self._format_bytes(obj["Size"]),
                        "created_at": obj["LastModified"].replace(tzinfo=None),
                        "location": "s3",
                    }
                )

            return backups

        except ClientError as e:
            logger.error("列出S3备份失败", error=str(e))
            return []

    async def _cleanup_s3_backups(self, cutoff_date: datetime) -> int:
        """清理S3中的旧备份"""
        if not self.backup_config["s3_bucket"]:
            return 0

        try:
            s3_client = boto3.client("s3", region_name=self.backup_config["aws_region"])

            response = s3_client.list_objects_v2(
                Bucket=self.backup_config["s3_bucket"], Prefix="database-backups/"
            )

            deleted_count = 0

            for obj in response.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                    s3_client.delete_object(
                        Bucket=self.backup_config["s3_bucket"], Key=obj["Key"]
                    )
                    deleted_count += 1

            return deleted_count

        except ClientError as e:
            logger.error("清理S3备份失败", error=str(e))
            return 0

    async def _upload_directory_to_s3(self, dirpath: Path, filename: str):
        """上传整个目录到S3（用于增量备份）"""
        if not self.backup_config["s3_bucket"]:
            return

        try:
            s3_client = boto3.client("s3", region_name=self.backup_config["aws_region"])

            for root, dirs, files in os.walk(dirpath):
                for file in files:
                    local_path = os.path.join(root, file)
                    s3_key = f"database-backups/{filename}/{os.path.relpath(local_path, dirpath)}"

                    s3_client.upload_file(
                        local_path, self.backup_config["s3_bucket"], s3_key
                    )

            logger.info(f"增量备份已上传到S3: {filename}")

        except ClientError as e:
            logger.error("上传目录到S3失败", error=str(e))


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库备份恢复工具")
    parser.add_argument(
        "action", choices=["backup", "restore", "list", "cleanup", "verify", "schedule"]
    )
    parser.add_argument(
        "--type", choices=["full", "incremental"], default="full", help="备份类型"
    )
    parser.add_argument("--file", help="备份文件路径（用于恢复和验证）")
    parser.add_argument("--compress", action="store_true", help="压缩备份")
    parser.add_argument("--encrypt", action="store_true", help="加密备份")
    parser.add_argument("--drop", action="store_true", help="恢复时删除现有数据库")
    parser.add_argument(
        "--schedule", default="0 2 * * *", help="备份计划（cron表达式）"
    )

    args = parser.parse_args()

    backup_manager = DatabaseBackupManager()

    if args.action == "backup":
        result = await backup_manager.create_full_backup(
            compress=args.compress, encrypt=args.encrypt
        )
        print(result)

    elif args.action == "restore":
        if not args.file:
            print("错误: 恢复操作需要指定 --file 参数")
            sys.exit(1)
        result = await backup_manager.restore_database(args.file, args.drop)
        print(result)

    elif args.action == "list":
        backups = await backup_manager.list_backups(args.type)
        print(f"\n找到 {len(backups)} 个备份:")
        for backup in backups:
            print(
                f"  - {backup['filename']} ({backup['size_human']}, {backup['created_at']})"
            )

    elif args.action == "cleanup":
        count = await backup_manager.cleanup_old_backups()
        print(f"\n清理了 {count} 个旧备份文件")

    elif args.action == "verify":
        if not args.file:
            print("错误: 验证操作需要指定 --file 参数")
            sys.exit(1)
        result = await backup_manager.verify_backup(args.file)
        print(result)

    elif args.action == "schedule":
        await backup_manager.schedule_backup(args.type, args.schedule)


if __name__ == "__main__":
    asyncio.run(main())
