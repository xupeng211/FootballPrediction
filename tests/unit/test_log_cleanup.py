#!/usr/bin/env python3
"""
Unit Test: Log Lifecycle Cleanup (TDD First)

测试目标：验证 clean_old_logs.py 脚本能够精准删除旧日志文件

TDD 流程：
1. Red Phase: 测试失败（功能未实现）
2. Green Phase: 实现功能，测试通过
3. Refactor Phase: 优化代码（可选）

Author: 高级基础设施工程师 (Principal Infrastructure Engineer)
Date: 2026-01-11
Version: V32.1 (Log Lifecycle Management)
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# 添加项目根目录到路径以导入脚本
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.ops.clean_old_logs import cleanup_logs


class TestLogCleanup:
    """测试日志清理功能 (TDD)"""

    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            log_dir.mkdir()
            yield log_dir

    @pytest.fixture
    def create_old_files(self, temp_log_dir):
        """创建超过 7 天的旧文件"""
        now = datetime.now()
        old_files = []

        # 创建 8 天前的 .log 文件
        old_log = temp_log_dir / "old_app.log"
        old_log.write_text("old log content")
        old_time = now - timedelta(days=8)
        os.utime(old_log, (old_time.timestamp(), old_time.timestamp()))
        old_files.append(old_log)

        # 创建 10 天前的 .json 文件
        old_json = temp_log_dir / "old_report.json"
        old_json.write_text('{"old": "report"}')
        old_time = now - timedelta(days=10)
        os.utime(old_json, (old_time.timestamp(), old_time.timestamp()))
        old_files.append(old_json)

        # 创建 15 天前的 .log 文件
        very_old_log = temp_log_dir / "very_old.log"
        very_old_log.write_text("very old content")
        old_time = now - timedelta(days=15)
        os.utime(very_old_log, (old_time.timestamp(), old_time.timestamp()))
        old_files.append(very_old_log)

        return old_files

    @pytest.fixture
    def create_new_files(self, temp_log_dir):
        """创建最近文件（应该保留）"""
        # 创建今天的 .log 文件
        new_log = temp_log_dir / "new_app.log"
        new_log.write_text("new log content")

        # 创建 3 天前的 .json 文件
        recent_json = temp_log_dir / "recent_report.json"
        recent_json.write_text('{"recent": "report"}')
        recent_time = datetime.now() - timedelta(days=3)
        os.utime(recent_json, (recent_time.timestamp(), recent_time.timestamp()))

        # 创建 5 天前的 .log 文件
        medium_log = temp_log_dir / "medium_app.log"
        medium_log.write_text("medium log content")
        medium_time = datetime.now() - timedelta(days=5)
        os.utime(medium_log, (medium_time.timestamp(), medium_time.timestamp()))

        return [new_log, recent_json, medium_log]

    def test_cleanup_deletes_old_files(self, temp_log_dir, create_old_files):
        """测试：cleanup 函数删除超过指定天数的文件"""
        old_files = create_old_files

        # 验证旧文件存在
        for f in old_files:
            assert f.exists()

        # 调用清理函数
        deleted = cleanup_logs(temp_log_dir, days=7)

        # 验证旧文件已删除
        for f in old_files:
            assert not f.exists(), f"文件 {f.name} 应该被删除但仍存在"

    def test_cleanup_preserves_new_files(self, temp_log_dir, create_new_files):
        """测试：cleanup 函数保留最近的文件"""
        new_files = create_new_files

        # 验证新文件存在
        for f in new_files:
            assert f.exists()

        # 调用清理函数
        deleted = cleanup_logs(temp_log_dir, days=7)

        # 验证新文件仍存在
        for f in new_files:
            assert f.exists(), f"文件 {f.name} 不应该被删除但已被删除"

    def test_cleanup_returns_deleted_count(self, temp_log_dir, create_old_files, create_new_files):
        """测试：cleanup 函数返回删除的文件数量"""
        old_files = create_old_files
        new_files = create_new_files

        expected_deleted = len(old_files)

        # 调用清理函数
        deleted = cleanup_logs(temp_log_dir, days=7)

        assert deleted == expected_deleted, (
            f"期望删除 {expected_deleted} 个文件，实际删除 {deleted} 个"
        )

    def test_cleanup_with_custom_days(self, temp_log_dir):
        """测试：cleanup 函数支持自定义天数参数"""
        now = datetime.now()

        # 创建不同年龄的文件
        files_5_days = []
        for i in range(3):
            f = temp_log_dir / f"file_5d_{i}.log"
            f.write_text(f"content {i}")
            file_time = now - timedelta(days=5)
            os.utime(f, (file_time.timestamp(), file_time.timestamp()))
            files_5_days.append(f)

        files_10_days = []
        for i in range(2):
            f = temp_log_dir / f"file_10d_{i}.log"
            f.write_text(f"content {i}")
            file_time = now - timedelta(days=10)
            os.utime(f, (file_time.timestamp(), file_time.timestamp()))
            files_10_days.append(f)

        # 使用 7 天阈值，应该只删除 10 天前的文件
        deleted = cleanup_logs(temp_log_dir, days=7)

        # 验证：5 天前的文件保留
        for f in files_5_days:
            assert f.exists(), f"5 天前的文件 {f.name} 应该保留"

        # 验证：10 天前的文件删除
        for f in files_10_days:
            assert not f.exists(), f"10 天前的文件 {f.name} 应该被删除"

        assert deleted == 2, f"期望删除 2 个文件，实际删除 {deleted} 个"

    def test_cleanup_with_dry_run(self, temp_log_dir, create_old_files, create_new_files):
        """测试：dry-run 模式不实际删除文件"""
        old_files = create_old_files

        # 调用清理函数（dry-run 模式）
        deleted = cleanup_logs(temp_log_dir, days=7, dry_run=True)

        # 验证：dry-run 不删除文件
        for f in old_files:
            assert f.exists(), f"dry-run 模式不应该删除文件，但 {f.name} 已被删除"

    def test_cleanup_empty_directory(self, temp_log_dir):
        """测试：清理空目录不报错"""
        # 目录为空，应该正常处理
        deleted = cleanup_logs(temp_log_dir, days=7)

        assert deleted == 0, "空目录应该返回 0 个删除"

    def test_cleanup_only_target_extensions(self, temp_log_dir):
        """测试：只删除 .log 和 .json 文件，保留其他文件"""
        now = datetime.now()

        # 创建旧文件（不同扩展名）
        old_log = temp_log_dir / "old.log"
        old_log.write_text("old log")
        old_time = now - timedelta(days=10)
        os.utime(old_log, (old_time.timestamp(), old_time.timestamp()))

        old_json = temp_log_dir / "old.json"
        old_json.write_text('{"old": "json"}')
        old_time = now - timedelta(days=10)
        os.utime(old_json, (old_time.timestamp(), old_time.timestamp()))

        old_txt = temp_log_dir / "important.txt"
        old_txt.write_text("important text file")
        old_time = now - timedelta(days=10)
        os.utime(old_txt, (old_time.timestamp(), old_time.timestamp()))

        old_py = temp_log_dir / "script.py"
        old_py.write_text("# python script")
        old_time = now - timedelta(days=10)
        os.utime(old_py, (old_time.timestamp(), old_time.timestamp()))

        # 调用清理函数
        deleted = cleanup_logs(temp_log_dir, days=7)

        # 验证：.log 和 .json 被删除
        assert not old_log.exists(), ".log 文件应该被删除"
        assert not old_json.exists(), ".json 文件应该被删除"

        # 验证：.txt 和 .py 保留
        assert old_txt.exists(), ".txt 文件不应该被删除"
        assert old_py.exists(), ".py 文件不应该被删除"

        assert deleted == 2, f"期望删除 2 个文件，实际删除 {deleted} 个"
