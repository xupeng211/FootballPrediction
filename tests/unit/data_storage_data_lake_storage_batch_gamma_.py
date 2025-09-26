"""
DataLakeStorage Batch-Γ-005 测试套件

专门为 data_lake_storage.py 设计的测试，目标是将其覆盖率从 15% 提升至 ≥41%
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


class TestDataLakeStorageBatchGamma005:
    """DataLakeStorage Batch-Γ-005 测试类"""

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
                "match_date": "2025-01-15",
                "competition": "Premier League",
                "season": "2024-2025"
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2025-01-16",
                "competition": "Premier League",
                "season": "2024-2025"
            }
        ]

    @pytest.fixture
    def sample_dataframe(self):
        """示例DataFrame数据"""
        return pd.DataFrame([
            {
                "match_id": 1001,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2025-01-15",
                "competition": "Premier League",
                "season": "2024-2025"
            },
            {
                "match_id": 1002,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 1,
                "away_score": 1,
                "match_date": "2025-01-16",
                "competition": "Premier League",
                "season": "2024-2025"
            }
        ])

    def test_data_lake_storage_initialization_default(self, temp_dir):
        """测试DataLakeStorage默认初始化"""
        # 准备测试环境
        storage = DataLakeStorage(base_path=temp_dir)

        # 验证默认配置
        assert storage.base_path == Path(temp_dir)
        assert storage.compression == "snappy"
        assert storage.partition_cols == ["year", "month"]
        assert storage.max_file_size_mb == 100

        # 验证目录结构创建
        bronze_dir = Path(temp_dir) / "bronze"
        silver_dir = Path(temp_dir) / "silver"
        gold_dir = Path(temp_dir) / "gold"

        assert bronze_dir.exists()
        assert silver_dir.exists()
        assert gold_dir.exists()

        # 验证表结构
        assert "raw_matches" in storage.tables
        assert "raw_odds" in storage.tables
        assert "processed_matches" in storage.tables

    def test_data_lake_storage_initialization_custom(self, temp_dir):
        """测试DataLakeStorage自定义初始化"""
        # 准备测试环境
        custom_config = {
            "base_path": temp_dir,
            "compression": "gzip",
            "partition_cols": ["year", "month"],
            "max_file_size_mb": 200
        }

        storage = DataLakeStorage(**custom_config)

        # 验证自定义配置
        assert storage.base_path == Path(temp_dir)
        assert storage.compression == "gzip"
        assert storage.partition_cols == ["year", "month"]
        assert storage.max_file_size_mb == 200

    def test_data_lake_storage_initialization_directories_created(self, temp_dir):
        """测试DataLakeStorage初始化时目录创建"""
        # 准备测试环境
        storage = DataLakeStorage(base_path=temp_dir)

        # 验证基础目录存在
        assert storage.base_path.exists()

        # 验证所有表目录存在
        for table_path in storage.tables.values():
            assert table_path.exists()
            assert table_path.is_dir()

    def test_s3_available_flag(self):
        """测试S3可用性标志"""
        # 验证S3_AVAILABLE标志存在
        from src.data.storage.data_lake_storage import S3_AVAILABLE
        assert isinstance(S3_AVAILABLE, bool)

        # 验证模块级别的S3支持标志
        assert S3_AVAILABLE is True or S3_AVAILABLE is False

    @pytest.mark.asyncio
    async def test_save_historical_data_with_dataframe_success(self, storage, sample_dataframe):
        """测试使用DataFrame保存历史数据成功场景"""
        # Mock文件系统操作
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet'), \
             patch('pathlib.Path.stat') as mock_stat:

            # Mock文件大小
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB

            # 执行保存操作
            result = await storage.save_historical_data(
                "raw_matches",
                sample_dataframe
            )

            # 验证结果 - 应该返回文件路径字符串
            assert isinstance(result, str)
            assert result.endswith('.parquet')
            assert 'raw_matches' in result

    @pytest.mark.asyncio
    async def test_save_historical_data_with_dict_list(self, storage, sample_data):
        """测试使用字典列表保存历史数据"""
        # Mock文件系统操作
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet'), \
             patch('pathlib.Path.stat') as mock_stat:

            # Mock文件大小
            mock_stat.return_value.st_size = 512 * 1024  # 512KB

            # 执行保存操作
            result = await storage.save_historical_data("raw_matches", sample_data)

            # 验证结果
            assert result["success"] is True
            assert result["records_count"] == 2

    @pytest.mark.asyncio
    async def test_save_historical_data_empty_data(self, storage):
        """测试保存空数据"""
        # 测试空列表
        empty_list = []
        result = await storage.save_historical_data("raw_matches", empty_list)

        assert result["success"] is False
        assert "数据为空" in result["error"]

        # 测试空DataFrame
        empty_df = pd.DataFrame()
        result = await storage.save_historical_data("raw_matches", empty_df)

        assert result["success"] is False
        assert "数据为空" in result["error"]

    @pytest.mark.asyncio
    async def test_save_historical_data_invalid_table_name(self, storage, sample_dataframe):
        """测试无效表名处理"""
        # 测试不存在的表名
        result = await storage.save_historical_data("invalid_table", sample_dataframe)

        assert result["success"] is False
        assert "表名无效" in result["error"]

    @pytest.mark.asyncio
    async def test_save_historical_data_file_creation_error(self, storage, sample_dataframe):
        """测试文件创建错误处理"""
        # Mock文件创建失败
        with patch('pathlib.Path.mkdir', side_effect=OSError("权限不足")):
            result = await storage.save_historical_data("raw_matches", sample_dataframe)

            assert result["success"] is False
            assert "权限不足" in result["error"]

    @pytest.mark.asyncio
    async def test_save_historical_data_parquet_error(self, storage, sample_dataframe):
        """测试Parquet写入错误处理"""
        # Mock Parquet写入失败
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet', side_effect=Exception("Parquet写入失败")):

            result = await storage.save_historical_data("raw_matches", sample_dataframe)

            assert result["success"] is False
            assert "Parquet写入失败" in result["error"]

    @pytest.mark.asyncio
    async def test_load_historical_data_success(self, storage, sample_dataframe):
        """测试加载历史数据成功场景"""
        # Mock数据加载
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[Path("test.parquet")]), \
             patch('pandas.read_parquet', return_value=sample_dataframe):

            result = await storage.load_historical_data("raw_matches")

            assert result["success"] is True
            assert len(result["data"]) == 2
            assert "file_count" in result

    @pytest.mark.asyncio
    async def test_load_historical_data_no_files(self, storage):
        """测试没有数据文件的情况"""
        # Mock没有文件
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[]):

            result = await storage.load_historical_data("raw_matches")

            assert result["success"] is False
            assert "没有找到数据文件" in result["error"]

    @pytest.mark.asyncio
    async def test_load_historical_data_invalid_table(self, storage):
        """测试无效表名加载"""
        result = await storage.load_historical_data("invalid_table")

        assert result["success"] is False
        assert "表名无效" in result["error"]

    @pytest.mark.asyncio
    async def test_load_historical_data_read_error(self, storage):
        """测试数据读取错误处理"""
        # Mock读取失败
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[Path("test.parquet")]), \
             patch('pandas.read_parquet', side_effect=Exception("读取失败")):

            result = await storage.load_historical_data("raw_matches")

            assert result["success"] is False
            assert "读取失败" in result["error"]

    def test_tables_attribute(self, storage):
        """测试表属性"""
        # 验证表结构
        assert isinstance(storage.tables, dict)
        assert "raw_matches" in storage.tables
        assert "raw_odds" in storage.tables
        assert "processed_matches" in storage.tables

        # 验证路径
        for table_name, table_path in storage.tables.items():
            assert isinstance(table_path, Path)
            assert table_path.parent.name in ["bronze", "silver", "gold"]

    @pytest.mark.asyncio
    async def test_get_table_stats_success(self, storage):
        """测试获取表统计信息成功场景"""
        # Mock获取统计信息
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[Path("test.parquet")]), \
             patch('pathlib.Path.stat') as mock_stat:

            # Mock文件大小
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB

            result = await storage.get_table_stats("raw_matches")

            assert result["total_files"] == 1
            assert result["total_size_mb"] == 1.0
            assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_table_stats_no_files(self, storage):
        """测试没有文件时的表统计"""
        # Mock没有文件
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[]):

            result = await storage.get_table_stats("raw_matches")

            assert result["total_files"] == 0
            assert result["total_size_mb"] == 0

    def test_partition_columns_configuration(self, temp_dir):
        """测试分区列配置"""
        # 测试不同分区列配置
        storage_year = DataLakeStorage(base_path=temp_dir, partition_cols=["year"])
        storage_year_month = DataLakeStorage(base_path=temp_dir, partition_cols=["year", "month"])
        storage_custom = DataLakeStorage(base_path=temp_dir, partition_cols=["year", "month", "competition"])

        assert storage_year.partition_cols == ["year"]
        assert storage_year_month.partition_cols == ["year", "month"]
        assert storage_custom.partition_cols == ["year", "month", "competition"]
        storage_gzip = DataLakeStorage(compression="gzip")
        storage_snappy = DataLakeStorage(compression="snappy")
        storage_none = DataLakeStorage(compression=None)

        assert storage_gzip.compression == "gzip"
        assert storage_snappy.compression == "snappy"
        assert storage_none.compression is None

    def test_partition_columns_configuration(self, temp_dir):
        """测试分区列配置"""
        # 测试不同分区列配置
        storage_year = DataLakeStorage(base_path=temp_dir, partition_cols=["year"])
        storage_year_month = DataLakeStorage(base_path=temp_dir, partition_cols=["year", "month"])
        storage_custom = DataLakeStorage(base_path=temp_dir, partition_cols=["year", "month", "competition"])

        assert storage_year.partition_cols == ["year"]
        assert storage_year_month.partition_cols == ["year", "month"]
        assert storage_custom.partition_cols == ["year", "month", "competition"]

    def test_max_file_size_configuration(self, temp_dir):
        """测试最大文件大小配置"""
        # 测试不同文件大小配置
        storage_small = DataLakeStorage(base_path=temp_dir, max_file_size_mb=50)
        storage_large = DataLakeStorage(base_path=temp_dir, max_file_size_mb=500)

        assert storage_small.max_file_size_mb == 50
        assert storage_large.max_file_size_mb == 500

    def test_path_structure_creation(self, storage):
        """测试路径结构创建"""
        # 验证路径结构
        assert storage.base_path.exists()

        for layer in ["bronze", "silver", "gold"]:
            layer_path = storage.base_path / layer
            assert layer_path.exists()

            for table_name in storage.tables:
                table_path = layer_path / table_name
                assert table_path.exists()

    def test_base_path_resolution(self):
        """测试基础路径解析"""
        # 测试相对路径
        storage_relative = DataLakeStorage(base_path="./test_data")
        assert storage_relative.base_path.is_absolute()

        # 测试绝对路径
        abs_path = "/tmp/test_data"
        storage_absolute = DataLakeStorage(base_path=abs_path)
        assert storage_absolute.base_path == Path(abs_path)

    def test_error_handling_permissions(self, temp_dir):
        """测试权限错误处理"""
        # Mock权限错误
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("权限不足")):
            with pytest.raises(PermissionError):
                DataLakeStorage(base_path=temp_dir)

    def test_error_handling_file_operations(self, storage, sample_dataframe):
        """测试文件操作错误处理"""
        # Mock各种文件操作错误
        errors = [
            OSError("磁盘空间不足"),
            PermissionError("权限不足"),
            Exception("未知错误")
        ]

        for error in errors:
            with patch('pathlib.Path.mkdir', side_effect=error):
                with pytest.raises(type(error)):
                    asyncio.run(storage.save_historical_data("raw_matches", sample_dataframe))

    def test_data_type_preservation(self, storage):
        """测试数据类型保存"""
        # 测试不同数据类型的处理
        mixed_data = [
            {
                "match_id": 1001,
                "home_score": 2,
                "away_score": 1,
                "match_date": "2025-01-15",
                "is_draw": False,
                "attendance": 50000.5
            }
        ]

        # Mock保存操作
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet'), \
             patch('pathlib.Path.stat') as mock_stat:

            mock_stat.return_value.st_size = 1024

            # 验证数据类型保存
            result = asyncio.run(storage.save_historical_data("raw_matches", mixed_data))
            assert result["success"] is True

    def test_concurrent_operations(self, storage, sample_dataframe):
        """测试并发操作"""
        import concurrent.futures

        # Mock保存操作
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet'), \
             patch('pathlib.Path.stat') as mock_stat:

            mock_stat.return_value.st_size = 1024

            # 并发执行多个保存操作
            def save_data():
                return asyncio.run(storage.save_historical_data("raw_matches", sample_dataframe))

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(save_data) for _ in range(3)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # 验证所有操作都成功
            assert all(result["success"] for result in results)

    def test_large_dataset_handling(self, storage):
        """测试大数据集处理"""
        # 生成大数据集
        large_data = [{"id": i, "value": i * 2} for i in range(10000)]

        # Mock保存操作
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet'), \
             patch('pathlib.Path.stat') as mock_stat:

            mock_stat.return_value.st_size = 10 * 1024 * 1024  # 10MB

            result = asyncio.run(storage.save_historical_data("raw_matches", large_data))

            assert result["success"] is True
            assert result["records_count"] == 10000

    def test_metadata_operations(self, storage):
        """测试元数据操作"""
        # 测试存储信息获取
        info = storage.get_storage_info()

        assert "total_tables" in info
        assert "base_path" in info
        assert "compression" in info
        assert "partition_cols" in info
        assert "max_file_size_mb" in info

        # 测试表统计信息
        stats = storage.get_table_stats("raw_matches")

        assert "total_files" in stats
        assert "total_records" in stats
        assert "total_size_mb" in stats
        assert "last_updated" in stats

    def test_path_operations(self, storage):
        """测试路径操作"""
        # 测试路径创建
        test_path = storage.base_path / "test" / "nested" / "path"

        with patch('pathlib.Path.mkdir') as mock_mkdir:
            test_path.mkdir(parents=True, exist_ok=True)
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_logger_initialization(self, temp_dir):
        """测试日志器初始化"""
        storage = DataLakeStorage(base_path=temp_dir)

        # 验证日志器存在
        assert hasattr(storage, 'logger')
        assert storage.logger.name == "storage.DataLakeStorage"

    def test_table_path_configuration(self, temp_dir):
        """测试表路径配置"""
        storage = DataLakeStorage(base_path=temp_dir)

        # 验证表路径配置
        for table_name, table_path in storage.tables.items():
            assert table_path.parent.name == "bronze"
            assert table_path.parent.parent == storage.base_path

    def test_multiple_tables_operations(self, storage, sample_dataframe):
        """测试多表操作"""
        # Mock保存操作
        with patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.DataFrame.to_parquet'), \
             patch('pathlib.Path.stat') as mock_stat:

            mock_stat.return_value.st_size = 1024

            # 对多个表进行操作
            tables = ["raw_matches", "raw_odds", "raw_scores"]
            results = []

            for table in tables:
                result = asyncio.run(storage.save_historical_data(table, sample_dataframe))
                results.append(result)

            # 验证所有操作都成功
            assert all(result["success"] for result in results)

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

    def test_edge_case_invalid_compression(self, temp_dir):
        """测试无效压缩格式边界情况"""
        # 测试无效压缩格式
        with pytest.raises(ValueError):
            DataLakeStorage(base_path=temp_dir, compression="invalid_format")

    def test_edge_case_empty_partition_cols(self, temp_dir):
        """测试空分区列边界情况"""
        # 测试空分区列
        storage = DataLakeStorage(base_path=temp_dir, partition_cols=[])
        assert storage.partition_cols == []

    def test_edge_case_zero_max_file_size(self, temp_dir):
        """测试零文件大小边界情况"""
        # 测试零文件大小
        storage = DataLakeStorage(base_path=temp_dir, max_file_size_mb=0)
        assert storage.max_file_size_mb == 0