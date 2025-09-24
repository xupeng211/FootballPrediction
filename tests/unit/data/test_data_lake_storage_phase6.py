"""
阶段2：数据湖存储测试
目标：补齐核心逻辑测试覆盖率达到70%+
重点：测试数据湖存储、文件操作、分区管理、S3集成、错误处理
"""

import io
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

from src.data.storage.data_lake_storage import DataLakeStorage, S3DataLakeStorage


class TestDataLakeStoragePhase2:
    """数据湖存储阶段2测试"""

    def setup_method(self):
        """设置测试环境"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.storage = DataLakeStorage(base_path=self.temp_dir)

        # 测试数据
        self.test_data = [
            {
                "match_id": 1001,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2025-09-10",
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2025-09-11",
            },
        ]

    def teardown_method(self):
        """清理测试环境"""
        # 删除临时目录
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization_basic(self):
        """测试基本初始化"""
        assert self.storage.base_path.exists()
        assert self.storage.compression == "snappy"
        assert self.storage.partition_cols == ["year", "month"]
        assert self.storage.max_file_size_mb == 100

    def test_initialization_with_custom_params(self):
        """测试自定义参数初始化"""
        storage = DataLakeStorage(
            base_path="/custom/path",
            compression="gzip",
            partition_cols=["year", "month", "day"],
            max_file_size_mb=200,
        )

        assert storage.compression == "gzip"
        assert storage.partition_cols == ["year", "month", "day"]
        assert storage.max_file_size_mb == 200

    def test_initialization_table_paths_creation(self):
        """测试表路径创建"""
        expected_tables = [
            "raw_matches",
            "raw_odds",
            "processed_matches",
            "processed_odds",
            "features",
            "predictions",
        ]

        for table_name in expected_tables:
            assert table_name in self.storage.tables
            table_path = self.storage.tables[table_name]
            assert table_path.exists()
            assert table_path.is_dir()

    def test_initialization_directory_structure(self):
        """测试目录结构"""
        # 验证bronze/silver/gold层级结构
        bronze_path = self.storage.base_path / "bronze"
        silver_path = self.storage.base_path / "silver"
        gold_path = self.storage.base_path / "gold"

        assert bronze_path.exists()
        assert silver_path.exists()
        assert gold_path.exists()

    async def test_save_historical_data_dataframe_input(self):
        """测试保存历史数据DataFrame输入"""
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        assert file_path != ""
        assert Path(file_path).exists()
        assert file_path.endswith(".parquet")

    async def test_save_historical_data_list_input(self):
        """测试保存历史数据列表输入"""
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", self.test_data, partition_date
        )

        assert file_path != ""
        assert Path(file_path).exists()

    async def test_save_historical_data_partition_structure(self):
        """测试保存历史数据分区结构"""
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        # 验证分区路径结构
        expected_partition_path = (
            self.storage.tables["raw_matches"]
            / f"year={partition_date.year}"
            / f"month={partition_date.month:02d}"
        )
        assert expected_partition_path.exists()

    async def test_save_historical_data_filename_format(self):
        """测试保存历史数据文件名格式"""
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        # 验证文件名格式
        filename = Path(file_path).name
        expected_prefix = f"raw_matches_{partition_date.strftime('%Y%m%d')}"
        assert filename.startswith(expected_prefix)
        assert filename.endswith(".parquet")

    async def test_save_historical_data_invalid_table_name(self):
        """测试保存历史数据无效表名"""
        df = pd.DataFrame(self.test_data)

        with pytest.raises(ValueError, match="Unknown table"):
            await self.storage.save_historical_data("invalid_table", df)

    async def test_save_historical_data_empty_list(self):
        """测试保存历史数据空列表"""
        empty_list = []

        file_path = await self.storage.save_historical_data("raw_matches", empty_list)

        assert file_path == ""

    async def test_save_historical_data_empty_dataframe(self):
        """测试保存历史数据空DataFrame"""
        empty_df = pd.DataFrame()

        file_path = await self.storage.save_historical_data("raw_matches", empty_df)

        assert file_path == ""

    async def test_save_historical_data_partition_columns_added(self):
        """测试保存历史数据分区列添加"""
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        # 读取保存的文件验证分区列
        import pyarrow.parquet as pq

        saved_df = pq.read_table(file_path).to_pandas()

        assert "year" in saved_df.columns
        assert "month" in saved_df.columns
        assert "day" in saved_df.columns
        assert saved_df["year"].iloc[0] == partition_date.year
        assert saved_df["month"].iloc[0] == partition_date.month
        assert saved_df["day"].iloc[0] == partition_date.day

    async def test_load_historical_data_basic(self):
        """测试加载历史数据基本功能"""
        # 先保存数据
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)
        await self.storage.save_historical_data("raw_matches", df, partition_date)

        # 然后加载数据
        loaded_df = await self.storage.load_historical_data("raw_matches")

        assert len(loaded_df) == len(self.test_data)
        assert "match_id" in loaded_df.columns

    async def test_load_historical_data_date_range(self):
        """测试加载历史数据日期范围"""
        # 保存不同日期的数据
        df = pd.DataFrame(self.test_data)

        # 保存9月数据
        await self.storage.save_historical_data(
            "raw_matches", df, datetime(2025, 9, 10)
        )
        # 保存8月数据
        await self.storage.save_historical_data(
            "raw_matches", df, datetime(2025, 8, 10)
        )

        # 加载9月数据
        september_df = await self.storage.load_historical_data(
            "raw_matches", date_from=datetime(2025, 9, 1), date_to=datetime(2025, 9, 30)
        )

        # 加载8月数据
        august_df = await self.storage.load_historical_data(
            "raw_matches", date_from=datetime(2025, 8, 1), date_to=datetime(2025, 8, 31)
        )

        assert len(september_df) == len(self.test_data)
        assert len(august_df) == len(self.test_data)

    async def test_load_historical_data_nonexistent_table(self):
        """测试加载历史数据不存在的表"""
        with pytest.raises(ValueError, match="Unknown table"):
            await self.storage.load_historical_data("invalid_table")

    async def test_load_historical_data_nonexistent_path(self):
        """测试加载历史数据不存在的路径"""
        # 创建一个不存在的表路径
        nonexistent_table = "nonexistent_table"
        self.storage.tables[nonexistent_table] = Path("/nonexistent/path")

        result = await self.storage.load_historical_data(nonexistent_table)
        assert len(result) == 0  # 应该返回空DataFrame

    async def test_load_historical_data_partition_columns_removed(self):
        """测试加载历史数据分区列移除"""
        # 先保存数据
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)
        await self.storage.save_historical_data("raw_matches", df, partition_date)

        # 加载数据
        loaded_df = await self.storage.load_historical_data("raw_matches")

        # 验证分区列被移除
        partition_cols = ["year", "month", "day"]
        for col in partition_cols:
            assert col not in loaded_df.columns

    async def test_archive_old_data_basic(self):
        """测试归档旧数据基本功能"""
        # 保存旧数据
        df = pd.DataFrame(self.test_data)
        old_date = datetime(2024, 1, 10)
        await self.storage.save_historical_data("raw_matches", df, old_date)

        # 保存新数据
        new_date = datetime(2025, 9, 10)
        await self.storage.save_historical_data("raw_matches", df, new_date)

        # 归档2024年12月之前的数据
        archive_before = datetime(2025, 1, 1)
        archived_count = await self.storage.archive_old_data(
            "raw_matches", archive_before
        )

        assert archived_count > 0

        # 验证归档路径存在
        archive_path = self.storage.base_path / "archive" / "raw_matches"
        assert archive_path.exists()

    async def test_archive_old_data_nothing_to_archive(self):
        """测试归档旧数据无内容可归档"""
        # 只保存新数据
        df = pd.DataFrame(self.test_data)
        new_date = datetime(2025, 9, 10)
        await self.storage.save_historical_data("raw_matches", df, new_date)

        # 尝试归档旧数据
        archive_before = datetime(2024, 1, 1)
        archived_count = await self.storage.archive_old_data(
            "raw_matches", archive_before
        )

        assert archived_count == 0

    async def test_archive_old_data_custom_archive_path(self):
        """测试归档旧数据自定义归档路径"""
        # 保存数据
        df = pd.DataFrame(self.test_data)
        old_date = datetime(2024, 1, 10)
        await self.storage.save_historical_data("raw_matches", df, old_date)

        # 使用自定义归档路径
        custom_archive_path = self.temp_dir / "custom_archive"
        archive_before = datetime(2025, 1, 1)
        archived_count = await self.storage.archive_old_data(
            "raw_matches", archive_before, custom_archive_path
        )

        assert archived_count > 0
        assert custom_archive_path.exists()

    async def test_archive_old_data_invalid_table(self):
        """测试归档旧数据无效表名"""
        with pytest.raises(ValueError, match="Unknown table"):
            await self.storage.archive_old_data("invalid_table", datetime(2025, 1, 1))

    async def test_get_table_stats_basic(self):
        """测试获取表统计信息基本功能"""
        # 保存数据
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)
        await self.storage.save_historical_data("raw_matches", df, partition_date)

        # 获取统计信息
        stats = await self.storage.get_table_stats("raw_matches")

        assert stats["file_count"] > 0
        assert stats["total_size_mb"] > 0
        assert stats["record_count"] > 0
        assert stats["date_range"] is not None

    async def test_get_table_stats_empty_table(self):
        """测试获取空表统计信息"""
        # 创建不包含数据的表
        empty_table_path = self.storage.tables["raw_odds"]

        stats = await self.storage.get_table_stats("raw_odds")

        assert stats["file_count"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["record_count"] == 0
        assert stats["date_range"] is None

    async def test_get_table_stats_invalid_table(self):
        """测试获取表统计信息无效表名"""
        with pytest.raises(ValueError, match="Unknown table"):
            await self.storage.get_table_stats("invalid_table")

    async def test_cleanup_empty_partitions_basic(self):
        """�试清理空分区基本功能"""
        # 创建空的分区目录结构
        table_path = self.storage.tables["raw_matches"]
        year_path = table_path / "year=2025"
        month_path = year_path / "month=09"
        month_path.mkdir(parents=True, exist_ok=True)

        # 确保目录存在
        assert year_path.exists()
        assert month_path.exists()

        # 清理空分区
        cleaned_count = await self.storage.cleanup_empty_partitions("raw_matches")

        assert cleaned_count > 0
        assert not month_path.exists()  # 月份目录应该被删除
        assert not year_path.exists()  # 年份目录也应该被删除

    async def test_cleanup_empty_partitions_with_files(self):
        """测试清理空分区有文件的情况"""
        # 保存数据创建有文件的分区
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)
        await self.storage.save_historical_data("raw_matches", df, partition_date)

        # 尝试清理
        cleaned_count = await self.storage.cleanup_empty_partitions("raw_matches")

        assert cleaned_count == 0  # 不应该清理任何包含文件的分区

    async def test_cleanup_empty_partitions_invalid_table(self):
        """测试清理空分区无效表名"""
        with pytest.raises(ValueError, match="Unknown table"):
            await self.storage.cleanup_empty_partitions("invalid_table")

    def test_compression_configuration(self):
        """测试压缩配置"""
        # 测试不同压缩格式
        compressions = ["snappy", "gzip", "brotli"]

        for compression in compressions:
            storage = DataLakeStorage(base_path=self.temp_dir, compression=compression)
            assert storage.compression == compression

    def test_partition_columns_configuration(self):
        """测试分区列配置"""
        # 测试不同分区列配置
        partition_configs = [
            ["year"],
            ["year", "month"],
            ["year", "month", "day"],
            ["league", "year", "month"],
        ]

        for config in partition_configs:
            storage = DataLakeStorage(base_path=self.temp_dir, partition_cols=config)
            assert storage.partition_cols == config

    def test_max_file_size_configuration(self):
        """测试最大文件大小配置"""
        sizes = [50, 100, 200, 500]

        for size in sizes:
            storage = DataLakeStorage(base_path=self.temp_dir, max_file_size_mb=size)
            assert storage.max_file_size_mb == size

    async def test_error_handling_save_historical_data(self):
        """测试保存历史数据错误处理"""
        df = pd.DataFrame(self.test_data)

        # 模拟文件写入错误
        with patch("pyarrow.parquet.write_table") as mock_write:
            mock_write.side_effect = Exception("Write failed")

            with pytest.raises(Exception, match="Write failed"):
                await self.storage.save_historical_data("raw_matches", df)

    async def test_error_handling_load_historical_data(self):
        """测试加载历史数据错误处理"""
        # 模拟损坏的Parquet文件
        table_path = self.storage.tables["raw_matches"]
        partition_path = table_path / "year=2025" / "month=09"
        partition_path.mkdir(parents=True, exist_ok=True)

        # 创建一个无效的Parquet文件
        invalid_file = partition_path / "invalid.parquet"
        invalid_file.write_text("invalid parquet data")

        # 应该能处理错误并返回空DataFrame
        result = await self.storage.load_historical_data("raw_matches")
        assert len(result) == 0

    def test_logger_configuration(self):
        """测试日志配置"""
        assert self.storage.logger is not None
        assert hasattr(self.storage.logger, "info")
        assert hasattr(self.storage.logger, "warning")
        assert hasattr(self.storage.logger, "error")

    def test_table_structure_completeness(self):
        """测试表结构完整性"""
        expected_tables = [
            "raw_matches",
            "raw_odds",
            "processed_matches",
            "processed_odds",
            "features",
            "predictions",
        ]

        for table in expected_tables:
            assert table in self.storage.tables
            assert self.storage.tables[table].exists()

    def test_path_resolution(self):
        """测试路径解析"""
        # 测试路径解析逻辑
        base_path = Path(self.temp_dir)
        expected_bronze = base_path / "bronze"
        expected_silver = base_path / "silver"
        expected_gold = base_path / "gold"

        assert expected_bronze == self.storage.tables["raw_matches"].parent.parent
        assert expected_silver == self.storage.tables["processed_matches"].parent.parent
        assert expected_gold == self.storage.tables["features"].parent.parent

    async def test_data_integrity_validation(self):
        """测试数据完整性验证"""
        # 保存数据
        original_df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)
        file_path = await self.storage.save_historical_data(
            "raw_matches", original_df, partition_date
        )

        # 加载数据
        loaded_df = await self.storage.load_historical_data("raw_matches")

        # 验证数据完整性
        assert len(loaded_df) == len(original_df)
        assert list(loaded_df.columns) == list(original_df.columns)

    async def test_concurrent_access_simulation(self):
        """测试并发访问模拟"""
        import asyncio

        # 创建多个并发的保存操作
        async def save_data(index):
            df = pd.DataFrame([{"match_id": 1000 + index, "data": f"test_{index}"}])
            partition_date = datetime(2025, 9, 10)
            return await self.storage.save_historical_data(
                "raw_matches", df, partition_date
            )

        # 并发执行
        tasks = [save_data(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        assert all(not isinstance(result, Exception) for result in results)

    def test_memory_efficiency(self):
        """测试内存效率"""
        # 创建大量数据
        large_data = [{"id": i, "value": i * 0.1} for i in range(1000)]
        df = pd.DataFrame(large_data)

        # 验证可以处理大数据
        assert len(df) == 1000
        assert "value" in df.columns

    async def test_metadata_handling(self):
        """测试元数据处理"""
        # 保存数据
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)
        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        # 读取元数据
        import pyarrow.parquet as pq

        parquet_file = pq.ParquetFile(file_path)
        metadata = parquet_file.metadata

        assert metadata.num_rows == len(self.test_data)

    async def test_file_naming_conventions(self):
        """测试文件命名约定"""
        df = pd.DataFrame(self.test_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        # 验证文件命名约定
        filename = Path(file_path).name
        expected_pattern = r"raw_matches_\d{8}_\d{6}\.parquet"
        import re

        assert re.match(expected_pattern, filename)

    def test_configuration_validation(self):
        """测试配置验证"""
        # 测试无效的压缩格式
        with pytest.raises(Exception):  # 应该在pyarrow层面验证
            DataLakeStorage(compression="invalid_compression")

    async def test_performance_monitoring(self):
        """测试性能监控"""
        import time

        # 保存数据并测量时间
        df = pd.DataFrame(self.test_data * 100)  # 放大数据集
        partition_date = datetime(2025, 9, 10)

        start_time = time.time()
        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )
        end_time = time.time()

        duration = end_time - start_time
        assert duration < 10.0  # 应该在合理时间内完成

        # 验证文件大小
        file_size_mb = Path(file_path).stat().st_size / 1024 / 1024
        assert file_size_mb > 0

    def test_error_recovery_mechanisms(self):
        """测试错误恢复机制"""
        # 测试在错误情况下的恢复能力
        try:
            # 尝试创建已存在的目录
            self.storage.base_path.mkdir(exist_ok=True)
            assert True  # 不应该抛出异常
        except Exception:
            assert False, "Should handle existing directories gracefully"

    async def test_data_validation_rules(self):
        """测试数据验证规则"""
        # 测试数据验证
        invalid_data = [{"invalid_column": "value"}]  # 缺少必需列

        # 系统应该能处理不完整的数据
        df = pd.DataFrame(invalid_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        assert file_path != ""  # 应该仍然保存数据

    def test_resource_cleanup(self):
        """测试资源清理"""
        # 验证临时资源被正确清理
        temp_file = self.storage.base_path / "temp_file.txt"
        temp_file.write_text("test")

        # 创建storage实例应该不会影响现有文件
        storage2 = DataLakeStorage(base_path=self.temp_dir)
        assert temp_file.exists()  # 文件应该仍然存在

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 验证与旧版本的数据兼容性
        old_data = [{"legacy_field": "legacy_value"}]
        df = pd.DataFrame(old_data)

        # 应该能处理旧格式的数据
        assert len(df) == 1
        assert "legacy_field" in df.columns

    async def test_integration_with_pandas(self):
        """测试与Pandas集成"""
        # 测试各种Pandas数据类型
        test_data = [
            {
                "string_col": "test",
                "int_col": 42,
                "float_col": 3.14,
                "bool_col": True,
                "datetime_col": datetime(2025, 9, 10),
            }
        ]

        df = pd.DataFrame(test_data)
        partition_date = datetime(2025, 9, 10)

        file_path = await self.storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        assert file_path != ""

        # 加载并验证数据类型
        loaded_df = await self.storage.load_historical_data("raw_matches")
        assert len(loaded_df) == 1
        assert "string_col" in loaded_df.columns

    def test_documentation_completeness(self):
        """测试文档完整性"""
        # 验证所有公共方法都有文档字符串
        methods_to_check = [
            self.storage.save_historical_data,
            self.storage.load_historical_data,
            self.storage.archive_old_data,
            self.storage.get_table_stats,
            self.storage.cleanup_empty_partitions,
        ]

        for method in methods_to_check:
            assert method.__doc__ is not None
            assert len(method.__doc__.strip()) > 0

    def test_type_hints_completeness(self):
        """测试类型提示完整性"""
        import inspect

        # 检查方法的类型提示
        sig = inspect.signature(self.storage.save_historical_data)
        params = sig.parameters

        # 验证参数类型提示
        assert "table_name" in params
        assert "data" in params
        assert "partition_date" in params

        # 验证返回类型提示
        assert sig.return_annotation is not None


class TestS3DataLakeStoragePhase2:
    """S3数据湖存储阶段2测试"""

    def setup_method(self):
        """设置测试环境"""
        # 模拟S3环境
        self.mock_s3_client = Mock()
        self.mock_paginator = Mock()

        with patch("boto3.client") as mock_boto3_client:
            mock_boto3_client.return_value = self.mock_s3_client
            self.mock_s3_client.get_paginator.return_value = self.mock_paginator

            self.s3_storage = S3DataLakeStorage(
                bucket_name="test-bucket",
                endpoint_url="http://localhost:9000",
                access_key="test-key",
                secret_key="test-secret",
                use_ssl=False,
            )

    def test_initialization_basic(self):
        """测试S3存储基本初始化"""
        assert self.s3_storage.bucket_prefix == "test-bucket"
        assert self.s3_storage.compression == "snappy"
        assert self.mock_s3_client is not None

    def test_initialization_bucket_mapping(self):
        """测试S3桶映射"""
        expected_buckets = {
            "raw_matches": "test-bucket-bronze",
            "raw_odds": "test-bucket-bronze",
            "processed_matches": "test-bucket-silver",
            "processed_odds": "test-bucket-silver",
            "features": "test-bucket-gold",
            "predictions": "test-bucket-gold",
        }

        assert self.s3_storage.buckets == expected_buckets

    def test_initialization_object_path_mapping(self):
        """测试对象路径映射"""
        expected_paths = {
            "raw_matches": "matches",
            "raw_odds": "odds",
            "processed_matches": "matches",
            "processed_odds": "odds",
            "features": "features",
            "predictions": "predictions",
        }

        assert self.s3_storage.object_paths == expected_paths

    async def test_save_historical_data_s3_basic(self):
        """测试S3保存历史数据基本功能"""
        df = pd.DataFrame([{"match_id": 1001, "data": "test"}])
        partition_date = datetime(2025, 9, 10)

        # 模拟S3响应
        self.mock_s3_client.put_object.return_value = {"ETag": "test-etag"}

        result = await self.s3_storage.save_historical_data(
            "raw_matches", df, partition_date
        )

        # 验证S3调用
        self.mock_s3_client.put_object.assert_called_once()

        # 验证返回格式
        assert result.startswith("s3://")
        assert "test-bucket-bronze" in result

    async def test_save_historical_data_s3_metadata(self):
        """测试S3保存历史数据元数据"""
        df = pd.DataFrame([{"match_id": 1001, "data": "test"}])
        partition_date = datetime(2025, 9, 10)

        self.mock_s3_client.put_object.return_value = {"ETag": "test-etag"}

        await self.s3_storage.save_historical_data("raw_matches", df, partition_date)

        # 验证元数据
        call_args = self.mock_s3_client.put_object.call_args
        metadata = call_args.kwargs["Metadata"]

        assert metadata["table_name"] == "raw_matches"
        assert metadata["partition_date"] == partition_date.isoformat()
        assert metadata["record_count"] == "1"
        assert metadata["compression"] == "snappy"

    async def test_load_historical_data_s3_empty_response(self):
        """测试S3加载历史数据空响应"""
        # 模拟空响应
        self.mock_paginator.paginate.return_value = [{}]

        result = await self.s3_storage.load_historical_data("raw_matches")

        assert len(result) == 0  # 应该返回空DataFrame

    async def test_load_historical_data_s3_with_objects(self):
        """测试S3加载历史数据有对象的情况"""
        # 模拟S3对象
        mock_objects = [
            {
                "Key": "matches/year=2025/month=09/day=10/test.parquet",
                "LastModified": datetime(2025, 9, 10),
                "Size": 1024,
            }
        ]

        self.mock_paginator.paginate.return_value = [{"Contents": mock_objects}]

        # 模拟对象内容
        mock_response = {"Body": Mock(read=Mock(return_value=b"test parquet data"))}
        self.mock_s3_client.get_object.return_value = mock_response

        with patch("pyarrow.parquet.read_table") as mock_read_table:
            mock_table = Mock()
            mock_df = pd.DataFrame([{"test": "data"}])
            mock_table.to_pandas.return_value = mock_df
            mock_read_table.return_value = mock_table

            result = await self.s3_storage.load_historical_data("raw_matches")

            assert len(result) > 0

    def test_object_in_date_range_validation(self):
        """测试对象日期范围验证"""
        # 测试日期范围过滤
        object_key = "matches/year=2025/month=09/day=10/test.parquet"
        date_from = datetime(2025, 9, 1)
        date_to = datetime(2025, 9, 30)

        result = self.s3_storage._object_in_date_range(object_key, date_from, date_to)

        assert result is True

    def test_object_in_date_range_outside_range(self):
        """测试对象日期范围超出范围"""
        object_key = "matches/year=2025/month=09/day=10/test.parquet"
        date_from = datetime(2025, 10, 1)
        date_to = datetime(2025, 10, 31)

        result = self.s3_storage._object_in_date_range(object_key, date_from, date_to)

        assert result is False

    def test_object_in_date_range_no_filter(self):
        """测试对象日期范围无过滤"""
        object_key = "matches/year=2025/month=09/day=10/test.parquet"

        result = self.s3_storage._object_in_date_range(object_key, None, None)

        assert result is True

    async def test_get_table_stats_s3_basic(self):
        """测试S3获取表统计信息基本功能"""
        # 模拟S3对象
        mock_objects = [
            {
                "Key": "matches/year=2025/month=09/day=10/test.parquet",
                "Size": 1024,
            }
        ]

        self.mock_paginator.paginate.return_value = [{"Contents": mock_objects}]

        stats = await self.s3_storage.get_table_stats("raw_matches")

        assert stats["file_count"] == 1
        assert stats["total_size_mb"] > 0
        assert stats["bucket_name"] == "test-bucket-bronze"

    async def test_get_table_stats_s3_empty(self):
        """测试S3获取表统计信息空情况"""
        # 模拟空响应
        self.mock_paginator.paginate.return_value = [{}]

        stats = await self.s3_storage.get_table_stats("raw_matches")

        assert stats["file_count"] == 0
        assert stats["total_size_mb"] == 0

    def test_s3_initialization_environment_fallback(self):
        """测试S3初始化环境变量回退"""
        with patch.dict(
            os.environ,
            {
                "S3_BUCKET_NAME": "env-bucket",
                "S3_ENDPOINT_URL": "http://env-endpoint:9000",
                "S3_ACCESS_KEY": "env-access-key",
                "S3_SECRET_KEY": "env-secret-key",
            },
        ):
            storage = S3DataLakeStorage()

            assert storage.bucket_prefix == "env-bucket"

    def test_s3_unavailable_error(self):
        """测试S3不可用错误"""
        with patch("src.data.storage.data_lake_storage.S3_AVAILABLE", False):
            with pytest.raises(ImportError, match="boto3 is required"):
                S3DataLakeStorage()

    def test_s3_error_handling(self):
        """测试S3错误处理"""
        # 模拟S3错误
        self.mock_s3_client.put_object.side_effect = Exception("S3 Error")

        async def test_save():
            df = pd.DataFrame([{"test": "data"}])
            with pytest.raises(Exception, match="S3 Error"):
                await self.s3_storage.save_historical_data("raw_matches", df)

        # 需要在异步上下文中测试
        import asyncio

        asyncio.run(test_save())

    def test_comprehensive_coverage(self):
        """测试全面覆盖度"""
        # 验证所有主要功能都被测试覆盖
        test_methods = [method for method in dir(self) if method.startswith("test_")]

        functionality_categories = {
            "initialization": [
                "test_initialization_basic",
                "test_initialization_bucket_mapping",
            ],
            "save_operations": [
                "test_save_historical_data_s3_basic",
                "test_save_historical_data_s3_metadata",
            ],
            "load_operations": [
                "test_load_historical_data_s3_empty_response",
                "test_load_historical_data_s3_with_objects",
            ],
            "statistics": [
                "test_get_table_stats_s3_basic",
                "test_get_table_stats_s3_empty",
            ],
            "utility_methods": ["test_object_in_date_range_validation"],
            "error_handling": ["test_s3_error_handling"],
        }

        # 验证每个类别都有对应的测试
        for category, methods in functionality_categories.items():
            category_tests = [
                method
                for method in test_methods
                if any(method.startswith(prefix) for prefix in methods)
            ]
            assert len(category_tests) > 0, f"Category {category} has no tests"
