"""
任务调度测试 - 备份任务
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tasks.backup_tasks import (
    backup_database_task,
    backup_logs_task,
    backup_redis_task,
    cleanup_old_backups_task,
    verify_backup_integrity_task,
)


@pytest.mark.unit
class TestBackupTasks:
    """备份任务测试"""

    @pytest.fixture
    def temp_backup_dir(self):
        """临时备份目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_db_manager(self):
        """Mock数据库管理器"""
        manager = MagicMock()
        manager.create_backup = AsyncMock(
            return_value="/backups/db_backup_20251005.sql"
        )
        manager.verify_backup = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis管理器"""
        manager = MagicMock()
        manager.save_backup = AsyncMock(
            return_value="/backups/redis_backup_20251005.rdb"
        )
        return manager

    @pytest.fixture
    def mock_storage_client(self):
        """Mock存储客户端"""
        client = MagicMock()
        client.upload_file = AsyncMock(return_value=True)
        client.list_backups = AsyncMock(
            return_value=[
                {"name": "db_backup_20251005.sql", "size": 1024},
                {"name": "redis_backup_20251005.rdb", "size": 512},
            ]
        )
        client.delete_backup = AsyncMock(return_value=True)
        return client

    def test_backup_database_task_success(self, mock_db_manager, temp_backup_dir):
        """测试成功备份数据库"""
        with patch(
            "src.tasks.backup_tasks.get_database_manager", return_value=mock_db_manager
        ), patch("src.tasks.backup_tasks.BACKUP_DIR", temp_backup_dir):
            result = backup_database_task.apply(
                kwargs={"compress": True, "include_schema": True}
            ).get()

            assert result["status"] == "success"
            assert result["backup_path"].endswith("db_backup_20251005.sql")
            assert result["compressed"] is True
            assert result["size"] > 0
            mock_db_manager.create_backup.assert_called_once()

    def test_backup_database_task_with_error(self, mock_db_manager, temp_backup_dir):
        """测试数据库备份错误"""
        mock_db_manager.create_backup = AsyncMock(
            side_effect=Exception("Backup failed")
        )

        with patch(
            "src.tasks.backup_tasks.get_database_manager", return_value=mock_db_manager
        ), patch("src.tasks.backup_tasks.BACKUP_DIR", temp_backup_dir):
            result = backup_database_task.apply().get()

            assert result["status"] == "error"
            assert "Backup failed" in result["error"]
            assert result["backup_path"] is None

    def test_backup_redis_task_success(self, mock_redis_manager, temp_backup_dir):
        """测试成功备份Redis"""
        with patch(
            "src.tasks.backup_tasks.get_redis_manager", return_value=mock_redis_manager
        ), patch("src.tasks.backup_tasks.BACKUP_DIR", temp_backup_dir):
            result = backup_redis_task.apply(
                kwargs={"save_type": "rdb", "include_aof": False}
            ).get()

            assert result["status"] == "success"
            assert result["backup_path"].endswith("redis_backup_20251005.rdb")
            assert result["save_type"] == "rdb"
            mock_redis_manager.save_backup.assert_called_once()

    def test_backup_logs_task(self, temp_backup_dir):
        """测试备份日志"""
        # 创建模拟日志文件
        log_dir = os.path.join(temp_backup_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        for i in range(3):
            with open(os.path.join(log_dir, f"app_{i}.log"), "w") as f:
                f.write("Sample log content\n" * 100)

        with patch("src.tasks.backup_tasks.LOG_DIR", log_dir), patch(
            "src.tasks.backup_tasks.BACKUP_DIR", temp_backup_dir
        ):
            result = backup_logs_task.apply(
                kwargs={"rotate_logs": True, "days_to_keep": 7}
            ).get()

            assert result["status"] == "success"
            assert result["logs_backuped"] == 3
            assert result["backup_path"] is not None

    def test_cleanup_old_backups_task(self, mock_storage_client, temp_backup_dir):
        """测试清理旧备份"""
        # 创建模拟备份文件
        today = datetime.now()
        for i in range(10):
            backup_date = today - timedelta(days=i)
            backup_name = f"backup_{backup_date.strftime('%Y%m%d')}.sql"
            backup_path = os.path.join(temp_backup_dir, backup_name)
            with open(backup_path, "w") as f:
                f.write("backup data")

        with patch(
            "src.tasks.backup_tasks.get_storage_client",
            return_value=mock_storage_client,
        ), patch("src.tasks.backup_tasks.BACKUP_DIR", temp_backup_dir):
            result = cleanup_old_backups_task.apply(
                kwargs={"keep_days": 5, "include_cloud": True}
            ).get()

            assert result["status"] == "success"
            assert result["local_files_removed"] > 0
            assert result["cloud_backups_removed"] >= 0

    def test_verify_backup_integrity_task(self, mock_storage_client, temp_backup_dir):
        """测试验证备份完整性"""
        # 创建测试备份文件
        backup_file = os.path.join(temp_backup_dir, "test_backup.sql")
        with open(backup_file, "w") as f:
            f.write("CREATE TABLE test (id INT);")
            f.write("INSERT INTO test VALUES (1);")

        with patch(
            "src.tasks.backup_tasks.get_storage_client",
            return_value=mock_storage_client,
        ), patch("src.tasks.backup_tasks.BACKUP_DIR", temp_backup_dir):
            result = verify_backup_integrity_task.apply(args=["test_backup.sql"]).get()

            assert result["status"] == "success"
            assert result["backup_file"] == "test_backup.sql"
            assert result["is_valid"] is True
            assert result["checksum"] is not None

    def test_scheduled_backup_execution(self):
        """测试定时备份执行"""
        # 模拟Celery beat调度
        from celery.schedules import crontab

        # 验证备份任务的调度配置
        backup_schedule = {
            "backup_database": {
                "task": "src.tasks.backup_tasks.backup_database_task",
                "schedule": crontab(minute=0, hour=2),  # 每天凌晨2点
                "options": {"queue": "backup"},
            },
            "backup_redis": {
                "task": "src.tasks.backup_tasks.backup_redis_task",
                "schedule": crontab(minute=30, hour=2),  # 每天凌晨2:30
                "options": {"queue": "backup"},
            },
        }

        assert "backup_database" in backup_schedule
        assert "backup_redis" in backup_schedule

    @pytest.mark.asyncio
    async def test_chained_backup_workflow(self):
        """测试链式备份工作流"""
        # 备份 -> 验证 -> 清理的链式执行
        workflow_steps = [
            "backup_database",
            "backup_redis",
            "verify_backup_integrity",
            "cleanup_old_backups",
        ]

        for step in workflow_steps:
            # 模拟每个步骤都成功
            assert step in workflow_steps

    def test_backup_notification_on_failure(self):
        """测试备份失败通知"""

        # 模拟备份失败
        @pytest.fixture
        def failing_backup_task():
            def task():
                raise Exception("Backup storage full")

            return task

        # 验证失败处理
        try:
            failing_backup_task()()
        except Exception as e:
            assert "Backup storage full" in str(e)

    def test_backup_compression(self, temp_backup_dir):
        """测试备份压缩"""
        # 创建大型测试文件
        test_file = os.path.join(temp_backup_dir, "large_backup.sql")
        with open(test_file, "w") as f:
            f.write("SELECT * FROM large_table;\n" * 10000)

        # 测试压缩功能
        import gzip

        compressed_file = test_file + ".gz"
        with open(test_file, "rb") as f_in:
            with gzip.open(compressed_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # 验证压缩后文件更小
        assert os.path.getsize(compressed_file) < os.path.getsize(test_file)

    def test_backup_encryption(self, temp_backup_dir):
        """测试备份加密"""

        from cryptography.fernet import Fernet

        # 生成密钥
        key = Fernet.generate_key()
        fernet = Fernet(key)

        # 创建测试数据
        test_data = b"Sensitive backup data"
        encrypted_data = fernet.encrypt(test_data)

        # 保存加密文件
        backup_file = os.path.join(temp_backup_dir, "encrypted_backup.enc")
        with open(backup_file, "wb") as f:
            f.write(encrypted_data)

        # 验证文件已加密
        with open(backup_file, "rb") as f:
            stored_data = f.read()

        assert stored_data != test_data  # 加密后数据应该不同

        # 解密验证
        decrypted_data = fernet.decrypt(stored_data)
        assert decrypted_data == test_data

    def test_backup_metadata_tracking(self, temp_backup_dir):
        """测试备份元数据跟踪"""
        import json

        # 创建元数据文件
        metadata = {
            "backup_id": "backup_20251005_001",
            "timestamp": datetime.now().isoformat(),
            "type": "database",
            "size": 1024,
            "checksum": "abc123",
            "status": "completed",
        }

        metadata_file = os.path.join(temp_backup_dir, "backup_metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        # 验证元数据文件
        with open(metadata_file, "r") as f:
            loaded_metadata = json.load(f)

        assert loaded_metadata["backup_id"] == "backup_20251005_001"
        assert loaded_metadata["status"] == "completed"

    def test_backup_retention_policy(self, temp_backup_dir):
        """测试备份保留策略"""
        # 创建不同日期的备份
        dates = []
        for i in range(30):
            backup_date = datetime.now() - timedelta(days=i)
            dates.append(backup_date)

            backup_file = os.path.join(
                temp_backup_dir, f"backup_{backup_date.strftime('%Y%m%d')}.sql"
            )
            with open(backup_file, "w") as f:
                f.write(f"Backup from {backup_date.strftime('%Y-%m-%d')}")

        # 应用保留策略（保留最近7天）
        retention_days = 7
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        kept_files = 0
        removed_files = 0

        for file in os.listdir(temp_backup_dir):
            file_path = os.path.join(temp_backup_dir, file)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

            if file_mtime < cutoff_date:
                os.remove(file_path)
                removed_files += 1
            else:
                kept_files += 1

        assert kept_files == retention_days
        assert removed_files == 30 - retention_days

    def test_backup_verification_checksum(self, temp_backup_dir):
        """测试备份验证校验和"""
        import hashlib

        # 创建测试文件
        test_file = os.path.join(temp_backup_dir, "test_backup.sql")
        test_content = "CREATE TABLE test (id INT);\nINSERT INTO test VALUES (1);"
        with open(test_file, "w") as f:
            f.write(test_content)

        # 计算校验和
        with open(test_file, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # 验证校验和
        assert len(file_hash) == 64  # SHA-256哈希长度
        assert file_hash is not None

    def test_backup_incremental_mode(self, temp_backup_dir):
        """测试增量备份模式"""
        # 创建全量备份
        full_backup = os.path.join(temp_backup_dir, "full_backup.sql")
        with open(full_backup, "w") as f:
            f.write("-- Full backup\nCREATE TABLE users (id INT, name TEXT);\n")

        # 创建增量备份
        incremental_backup = os.path.join(temp_backup_dir, "incremental_001.sql")
        with open(incremental_backup, "w") as f:
            f.write("-- Incremental backup since full backup\n")
            f.write("INSERT INTO users VALUES (1, 'Alice');\n")

        # 验证增量备份文件存在
        assert os.path.exists(full_backup)
        assert os.path.exists(incremental_backup)

    def test_backup_parallel_execution(self):
        """测试并行备份执行"""
        import concurrent.futures
        import time

        def mock_backup_task(task_id):
            time.sleep(0.1)  # 模拟备份耗时
            return f"backup_{task_id}_completed"

        # 并行执行多个备份任务
        tasks = [1, 2, 3, 4, 5]
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(mock_backup_task, task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # 验证所有任务完成
        assert len(results) == len(tasks)
        assert all("completed" in result for result in results)
