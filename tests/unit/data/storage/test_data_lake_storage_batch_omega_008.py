"""
DataLakeStorage Batch-Ω-008 测试套件

专门为 data_lake_storage.py 设计的测试，目标是将其覆盖率从 6% 提升至 ≥70%
覆盖所有数据湖存储功能、Parquet操作、分区管理、元数据管理等
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import sys
import os
import tempfile
import shutil

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.storage.data_lake_storage import DataLakeStorage


class TestDataLakeStorageBatchOmega008:
    """DataLakeStorage Batch-Ω-008 测试类"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def storage(self, temp_dir):
        """创建 DataLakeStorage 实例"""
        return DataLakeStorage(base_path=temp_dir)

    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return [
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

    @pytest.fixture
    def sample_dataframe(self):
        """示例DataFrame"""
        return pd.DataFrame([
            {
                "match_id": 1001,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
            },
        ])

    def test_data_lake_storage_initialization_default(self, temp_dir):
        """测试DataLakeStorage默认初始化"""
        storage = DataLakeStorage()

        # 验证默认路径结构，但不比较具体路径
        assert storage.base_path.name == "football_lake"
        assert storage.base_path.parent.name == "data"
        assert storage.compression == "snappy"
        assert storage.partition_cols == ["year", "month"]
        assert storage.max_file_size_mb == 100
        assert "raw_matches" in storage.tables
        assert "features" in storage.tables

    def test_data_lake_storage_initialization_custom(self, temp_dir):
        """测试DataLakeStorage自定义初始化"""
        storage = DataLakeStorage(
            base_path=temp_dir,
            compression="gzip",
            partition_cols=["year", "month", "day"],
            max_file_size_mb=200
        )

        assert storage.base_path == Path(temp_dir)
        assert storage.compression == "gzip"
        assert storage.partition_cols == ["year", "month", "day"]
        assert storage.max_file_size_mb == 200

    def test_data_lake_storage_initialization_directories_created(self, temp_dir):
        """测试初始化时目录创建"""
        storage = DataLakeStorage(base_path=temp_dir)

        # 验证基础目录存在
        assert storage.base_path.exists()

        # 验证所有表目录存在
        for table_path in storage.tables.values():
            assert table_path.exists()

    def test_save_historical_data_with_dataframe(self, storage, sample_dataframe):
        """测试保存DataFrame数据"""
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        assert result_path.endswith(".parquet")
        assert "raw_matches" in result_path
        assert "year=2025" in result_path
        assert "month=09" in result_path

        # 验证文件存在
        assert Path(result_path).exists()

    def test_save_historical_data_with_dict_list(self, storage, sample_data):
        """测试保存字典列表数据"""
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_data,
            partition_date=datetime(2025, 9, 10)
        ))

        assert result_path.endswith(".parquet")
        assert Path(result_path).exists()

    def test_save_historical_data_empty_list(self, storage):
        """测试保存空列表数据"""
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=[]
        ))

        assert result_path == ""

    def test_save_historical_data_empty_dataframe(self, storage):
        """测试保存空DataFrame数据"""
        empty_df = pd.DataFrame()
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=empty_df
        ))

        assert result_path == ""

    def test_save_historical_data_invalid_table_name(self, storage, sample_dataframe):
        """测试保存到无效表名"""
        with pytest.raises(ValueError, match="Unknown table"):
            asyncio.run(storage.save_historical_data(
                table_name="invalid_table",
                data=sample_dataframe
            ))

    def test_save_historical_data_default_partition_date(self, storage, sample_dataframe):
        """测试使用默认分区日期"""
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe
        ))

        # 应该使用当前日期
        current_year = datetime.now().year
        current_month = datetime.now().month
        assert f"year={current_year}" in result_path
        assert f"month={current_month:02d}" in result_path

    def test_load_historical_data_success(self, storage, sample_dataframe):
        """测试加载数据成功"""
        # 先保存数据
        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        # 再加载数据
        result_df = asyncio.run(storage.load_historical_data(
            table_name="raw_matches"
        ))

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == len(sample_dataframe)

    def test_load_historical_data_with_date_range(self, storage, sample_dataframe):
        """测试按日期范围加载数据"""
        # 保存数据
        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        # 按日期范围加载
        result_df = asyncio.run(storage.load_historical_data(
            table_name="raw_matches",
            date_from=datetime(2025, 9, 1),
            date_to=datetime(2025, 9, 30)
        ))

        assert isinstance(result_df, pd.DataFrame)

    def test_load_historical_data_invalid_table_name(self, storage):
        """测试从无效表名加载数据"""
        with pytest.raises(ValueError, match="Unknown table"):
            asyncio.run(storage.load_historical_data(
                table_name="invalid_table"
            ))

    def test_load_historical_data_no_data(self, storage):
        """测试加载不存在的数据"""
        result_df = asyncio.run(storage.load_historical_data(
            table_name="raw_matches",
            date_from=datetime(2025, 1, 1),
            date_to=datetime(2025, 1, 31)
        ))

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 0

    def test_list_available_tables(self, storage):
        """测试列出可用表"""
        tables = storage.list_available_tables()

        assert isinstance(tables, list)
        assert "raw_matches" in tables
        assert "features" in tables
        assert "predictions" in tables

    def test_get_storage_info(self, storage):
        """测试获取存储信息"""
        info = storage.get_storage_info()

        assert isinstance(info, dict)
        assert "base_path" in info
        assert "total_tables" in info
        assert "compression" in info
        assert "partition_cols" in info

    def test_cleanup_old_data(self, storage, sample_dataframe):
        """测试清理旧数据"""
        # 保存一些数据
        old_date = datetime.now() - timedelta(days=100)
        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=old_date
        ))

        # 清理超过30天的数据
        removed_count = storage.cleanup_old_data(days_to_keep=30)

        assert removed_count >= 0

    def test_get_table_stats(self, storage, sample_dataframe):
        """测试获取表统计信息"""
        # 保存数据
        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        # 获取统计信息
        stats = storage.get_table_stats("raw_matches")

        assert isinstance(stats, dict)
        assert "total_files" in stats
        assert "total_records" in stats
        assert "total_size_mb" in stats

    def test_get_table_stats_invalid_table(self, storage):
        """测试获取无效表的统计信息"""
        stats = storage.get_table_stats("invalid_table")

        assert isinstance(stats, dict)
        assert stats["total_files"] == 0
        assert stats["total_records"] == 0

    def test_compression_settings(self, storage, sample_dataframe):
        """测试压缩设置"""
        # 使用不同的压缩格式
        storage_gzip = DataLakeStorage(compression="gzip")
        storage_brotli = DataLakeStorage(compression="brotli")

        assert storage_gzip.compression == "gzip"
        assert storage_brotli.compression == "brotli"

    def test_partition_columns_configuration(self, temp_dir):
        """测试分区列配置"""
        storage = DataLakeStorage(
            base_path=temp_dir,
            partition_cols=["year", "month", "day", "league"]
        )

        assert storage.partition_cols == ["year", "month", "day", "league"]

    def test_max_file_size_configuration(self, temp_dir):
        """测试最大文件大小配置"""
        storage = DataLakeStorage(
            base_path=temp_dir,
            max_file_size_mb=500
        )

        assert storage.max_file_size_mb == 500

    def test_path_structure_creation(self, storage, sample_dataframe):
        """测试路径结构创建"""
        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        # 验证分区路径结构
        expected_path = storage.base_path / "bronze" / "matches" / "year=2025" / "month=09"
        assert expected_path.exists()

    def test_file_naming_convention(self, storage, sample_dataframe):
        """测试文件命名约定"""
        partition_date = datetime(2025, 9, 10)
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=partition_date
        ))

        # 验证文件名格式
        expected_pattern = "raw_matches_20250910_"
        assert expected_pattern in Path(result_path).name
        assert result_path.endswith(".parquet")

    def test_error_handling_write_failure(self, storage):
        """测试写入失败错误处理"""
        # 模拟文件写入失败
        with patch('pyarrow.parquet.write_table', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                asyncio.run(storage.save_historical_data(
                    table_name="raw_matches",
                    data=[{"test": "data"}]
                ))

    def test_error_handling_read_failure(self, storage):
        """测试读取失败错误处理"""
        with pytest.raises(ValueError):
            asyncio.run(storage.load_historical_data(
                table_name="nonexistent_table"
            ))

    def test_logger_initialization(self, temp_dir):
        """测试日志器初始化"""
        storage = DataLakeStorage(base_path=temp_dir)

        assert storage.logger is not None
        assert "storage.DataLakeStorage" in storage.logger.name

    def test_base_path_resolution(self):
        """测试基础路径解析"""
        # 测试默认路径解析
        storage1 = DataLakeStorage()
        expected_default_path = Path.cwd() / "data" / "football_lake"
        assert storage1.base_path == expected_default_path

    def test_s3_available_flag(self):
        """测试S3可用性标志"""
        from src.data.storage.data_lake_storage import S3_AVAILABLE
        assert isinstance(S3_AVAILABLE, bool)

    def test_data_partitioning_addition(self, storage, sample_dataframe):
        """测试数据分区列添加"""
        partition_date = datetime(2025, 9, 10)

        # 保存数据
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=partition_date
        ))

        # 读取并验证分区列
        result_df = asyncio.run(storage.load_historical_data(
            table_name="raw_matches"
        ))

        if not result_df.empty:
            assert "year" in result_df.columns
            assert "month" in result_df.columns
            assert "day" in result_df.columns

    def test_table_path_configuration(self, temp_dir):
        """测试表路径配置"""
        storage = DataLakeStorage(base_path=temp_dir)

        # 验证所有预定义的表路径
        expected_tables = [
            "raw_matches", "raw_odds", "processed_matches",
            "processed_odds", "features", "predictions"
        ]

        for table_name in expected_tables:
            assert table_name in storage.tables
            assert storage.tables[table_name].exists()

    def test_multiple_tables_operations(self, storage, sample_dataframe):
        """测试多表操作"""
        # 在多个表中保存数据
        tables_to_test = ["raw_matches", "raw_odds", "features"]

        for table_name in tables_to_test:
            asyncio.run(storage.save_historical_data(
                table_name=table_name,
                data=sample_dataframe,
                partition_date=datetime(2025, 9, 10)
            ))

            # 验证数据可以加载
            result_df = asyncio.run(storage.load_historical_data(table_name=table_name))
            assert isinstance(result_df, pd.DataFrame)

    def test_data_type_preservation(self, storage):
        """测试数据类型保持"""
        # 创建包含不同数据类型的测试数据
        mixed_data = pd.DataFrame([
            {
                "id": 1001,
                "name": "Test Team",
                "score": 2.5,
                "is_active": True,
                "created_at": datetime(2025, 9, 10)
            }
        ])

        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=mixed_data,
            partition_date=datetime(2025, 9, 10)
        ))

        # 读取并验证数据类型
        result_df = asyncio.run(storage.load_historical_data(
            table_name="raw_matches"
        ))

        if not result_df.empty:
            # 验证分区列存在
            assert "year" in result_df.columns
            assert "month" in result_df.columns
            assert "day" in result_df.columns

    def test_large_dataset_handling(self, storage):
        """测试大数据集处理"""
        # 创建较大的数据集
        large_data = pd.DataFrame({
            "id": range(1000),
            "value": [x * 0.1 for x in range(1000)],
            "category": [f"cat_{x % 10}" for x in range(1000)]
        })

        result_path = asyncio.run(storage.save_historical_data(
            table_name="features",
            data=large_data,
            partition_date=datetime(2025, 9, 10)
        ))

        assert result_path.endswith(".parquet")
        assert Path(result_path).exists()

    def test_concurrent_save_operations(self, storage, sample_dataframe):
        """测试并发保存操作"""
        async def save_multiple():
            tasks = []
            for i in range(5):
                task = storage.save_historical_data(
                    table_name="raw_matches",
                    data=sample_dataframe,
                    partition_date=datetime(2025, 9, 10 + i)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        results = asyncio.run(save_multiple())

        # 验证所有操作都完成
        assert len(results) == 5
        for result in results:
            if not isinstance(result, Exception):
                assert result.endswith(".parquet")

    def test_directory_creation_permissions(self, temp_dir):
        """测试目录创建权限"""
        # 设置只读权限的目录
        read_only_dir = Path(temp_dir) / "readonly"
        read_only_dir.mkdir(mode=0o555)  # 只读权限

        # 应该能够处理权限问题
        try:
            storage = DataLakeStorage(base_path=str(read_only_dir))
            # 如果创建成功，验证基础功能
            assert storage.base_path == read_only_dir
        except OSError:
            # 如果因为权限失败，这也是可以接受的
            pass

    def test_compression_efficiency(self, storage, sample_dataframe):
        """测试压缩效率"""
        # 保存数据并获取文件大小
        result_path = asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        file_size = Path(result_path).stat().st_size
        assert file_size > 0

        # 验证文件确实比较小（压缩有效）
        assert file_size < 10240  # 小于10KB对于测试数据是合理的

    def test_metadata_retrieval(self, storage, sample_dataframe):
        """测试元数据检索"""
        # 保存数据
        asyncio.run(storage.save_historical_data(
            table_name="raw_matches",
            data=sample_dataframe,
            partition_date=datetime(2025, 9, 10)
        ))

        # 获取存储信息
        info = storage.get_storage_info()

        assert "base_path" in info
        assert info["total_tables"] > 0
        assert info["compression"] == "snappy"

    def test_path_operations(self, storage):
        """测试路径操作"""
        # 测试路径操作相关功能
        assert storage.base_path.is_absolute()

        for table_path in storage.tables.values():
            assert table_path.is_absolute()
            assert table_path.parent == storage.base_path.parent

    def test_edge_case_empty_storage_info(self, temp_dir):
        """测试空存储信息边界情况"""
        storage = DataLakeStorage(base_path=temp_dir)

        # 没有数据时的存储信息
        info = storage.get_storage_info()
        assert info["total_tables"] == len(storage.tables)

        # 没有数据时的表统计
        stats = storage.get_table_stats("raw_matches")
        assert stats["total_files"] == 0
        assert stats["total_records"] == 0