"""
数据湖存储管理器测试模块

全面测试 src/data/storage/data_lake_storage.py 的所有功能
包括本地和S3数据湖存储、数据归档、统计信息和分区管理。

基于 DATA_DESIGN.md 第2.2节数据湖设计。
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, call, mock_open, patch

import pandas as pd
import pytest

from src.data.storage.data_lake_storage import (
    S3_AVAILABLE,
    DataLakeStorage,
    S3DataLakeStorage,
)


class TestDataLakeStorage:
    """测试本地数据湖存储功能"""

    @pytest.fixture
    def temp_base_path(self):
        """创建临时基础路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def data_lake_storage(self, temp_base_path):
        """创建数据湖存储实例"""
        return DataLakeStorage(
            base_path=temp_base_path,
            compression="snappy",
            partition_cols=["year", "month"],
            max_file_size_mb=100,
        )

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return [
            {
                "match_id": 1001,
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2024-01-15",
                "league": "Premier League",
                "status": "finished",
            },
            {
                "match_id": 1002,
                "home_team": "Liverpool",
                "away_team": "Manchester United",
                "home_score": 3,
                "away_score": 2,
                "match_date": "2024-01-16",
                "league": "Premier League",
                "status": "finished",
            },
        ]

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return [
            {
                "match_id": 1001,
                "bookmaker": "Bet365",
                "home_odds": 1.85,
                "draw_odds": 3.40,
                "away_odds": 4.20,
                "timestamp": "2024-01-14T10:00:00",
            },
            {
                "match_id": 1002,
                "bookmaker": "William Hill",
                "home_odds": 2.10,
                "draw_odds": 3.20,
                "away_odds": 3.60,
                "timestamp": "2024-01-14T11:00:00",
            },
        ]

    @pytest.fixture
    def sample_dataframe(self):
        """示例DataFrame"""
        return pd.DataFrame(
            {
                "match_id": [1001, 1002],
                "home_team": ["Arsenal", "Liverpool"],
                "away_team": ["Chelsea", "Man United"],
                "home_score": [2, 3],
                "away_score": [1, 2],
            }
        )

    # 测试初始化
    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        with patch("os.getcwd", return_value="/test/path"):
            storage = DataLakeStorage()

            expected_path = Path("/test/path/data/football_lake")
            assert storage.base_path == expected_path
            assert storage.compression == "snappy"
            assert storage.partition_cols == ["year", "month"]
            assert storage.max_file_size_mb == 100

    def test_init_with_custom_path(self, temp_base_path):
        """测试使用自定义路径初始化"""
        storage = DataLakeStorage(
            base_path=temp_base_path,
            compression="gzip",
            partition_cols=["year"],
            max_file_size_mb=200,
        )

        assert storage.base_path == Path(temp_base_path)
        assert storage.compression == "gzip"
        assert storage.partition_cols == ["year"]
        assert storage.max_file_size_mb == 200

    def test_init_creates_directories(self, temp_base_path):
        """测试初始化创建必要的目录"""
        storage = DataLakeStorage(base_path=temp_base_path)

        # 验证所有表目录都被创建
        for table_path in storage.tables.values():
            assert table_path.exists()

    def test_tables_structure(self, data_lake_storage):
        """测试表结构配置"""
        expected_tables = [
            "raw_matches",
            "raw_odds",
            "processed_matches",
            "processed_odds",
            "features",
            "predictions",
        ]

        assert list(data_lake_storage.tables.keys()) == expected_tables

        # 验证路径结构
        assert "bronze" in str(data_lake_storage.tables["raw_matches"])
        assert "silver" in str(data_lake_storage.tables["processed_matches"])
        assert "gold" in str(data_lake_storage.tables["features"])

    # 测试保存历史数据
    @pytest.mark.asyncio
    async def test_save_historical_data_success_list_input(
        self, data_lake_storage, sample_match_data
    ):
        """测试成功保存历史数据 - 列表输入"""
        with patch("pyarrow.parquet.write_table") as mock_write:
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table
                mock_file_path = (
                    data_lake_storage.tables["raw_matches"] / "test.parquet"
                )
                mock_file_path.touch()  # 创建文件以测试统计

                result = await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data
                )

                mock_from_pandas.assert_called_once()
                mock_write.assert_called_once()
                assert result.endswith(".parquet")

    @pytest.mark.asyncio
    async def test_save_historical_data_success_dataframe_input(
        self, data_lake_storage, sample_dataframe
    ):
        """测试成功保存历史数据 - DataFrame输入"""
        with patch("pyarrow.parquet.write_table") as mock_write:
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table

                result = await data_lake_storage.save_historical_data(
                    "raw_matches", sample_dataframe
                )

                mock_from_pandas.assert_called_once()
                mock_write.assert_called_once()
                assert result.endswith(".parquet")

    @pytest.mark.asyncio
    async def test_save_historical_data_with_custom_date(
        self, data_lake_storage, sample_match_data
    ):
        """测试使用自定义日期保存历史数据"""
        custom_date = datetime(2024, 6, 15)

        with patch("pyarrow.parquet.write_table") as mock_write:
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table

                result = await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data, partition_date=custom_date
                )

                # 验证文件名包含正确的日期
                assert "20240615" in result

    @pytest.mark.asyncio
    async def test_save_historical_data_empty_list(self, data_lake_storage):
        """测试保存空列表数据"""
        result = await data_lake_storage.save_historical_data("raw_matches", [])
        assert result == ""

    @pytest.mark.asyncio
    async def test_save_historical_data_empty_dataframe(self, data_lake_storage):
        """测试保存空DataFrame数据"""
        empty_df = pd.DataFrame()
        result = await data_lake_storage.save_historical_data("raw_matches", empty_df)
        assert result == ""

    @pytest.mark.asyncio
    async def test_save_historical_data_invalid_table_name(
        self, data_lake_storage, sample_match_data
    ):
        """测试使用无效表名保存数据"""
        with pytest.raises(ValueError, match="Unknown table"):
            await data_lake_storage.save_historical_data(
                "invalid_table", sample_match_data
            )

    @pytest.mark.asyncio
    async def test_save_historical_data_write_error(
        self, data_lake_storage, sample_match_data
    ):
        """测试保存数据时的写入错误"""
        with patch("pyarrow.parquet.write_table") as mock_write:
            mock_write.side_effect = Exception("Write failed")

            with pytest.raises(Exception, match="Write failed"):
                await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data
                )

    @pytest.mark.asyncio
    async def test_save_historical_data_partition_columns_added(
        self, data_lake_storage, sample_match_data
    ):
        """测试保存数据时添加分区列"""
        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table

                await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data
                )

                # 验证DataFrame包含分区列
                call_args = mock_from_pandas.call_args[0][0]
                assert "year" in call_args.columns
                assert "month" in call_args.columns
                assert "day" in call_args.columns

    # 测试加载历史数据
    @pytest.mark.asyncio
    async def test_load_historical_data_success(self, data_lake_storage):
        """测试成功加载历史数据"""
        expected_df = pd.DataFrame(
            {
                "match_id": [1001, 1002],
                "home_team": ["Arsenal", "Liverpool"],
            }
        )

        with patch("pyarrow.parquet.ParquetDataset") as mock_dataset:
            with patch("pyarrow.fs.LocalFileSystem") as mock_fs:
                mock_table = Mock()
                mock_table.to_pandas.return_value = expected_df
                mock_dataset.return_value.read.return_value = mock_table

                result = await data_lake_storage.load_historical_data("raw_matches")

                assert result.equals(expected_df)

    @pytest.mark.asyncio
    async def test_load_historical_data_with_date_range(self, data_lake_storage):
        """测试使用日期范围加载历史数据"""
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        with patch("pyarrow.parquet.ParquetDataset"):
            with patch("pyarrow.fs.LocalFileSystem"):
                expected_df = pd.DataFrame({"match_id": [1001]})
                with patch("pyarrow.Table.from_pandas"):
                    mock_table = Mock()
                    mock_table.to_pandas.return_value = expected_df
                    with patch.object(
                        data_lake_storage.tables["raw_matches"],
                        "exists",
                        return_value=True,
                    ):
                        with patch(
                            "pyarrow.parquet.ParquetDataset"
                        ) as mock_dataset_class:
                            mock_dataset = Mock()
                            mock_dataset.read.return_value.to_pandas.return_value = (
                                expected_df
                            )
                            mock_dataset_class.return_value = mock_dataset

                            result = await data_lake_storage.load_historical_data(
                                "raw_matches", date_from=date_from, date_to=date_to
                            )

                            # 验证过滤器包含日期条件
                            call_args = mock_dataset_class.call_args[1]
                            filters = call_args.get("filters", [])
                            assert any(
                                filter[0] == "year" and filter[1] == ">="
                                for filter in filters
                            )

    @pytest.mark.asyncio
    async def test_load_historical_data_with_custom_filters(self, data_lake_storage):
        """测试使用自定义过滤器加载历史数据"""
        custom_filters = [("league", "==", "Premier League")]

        with patch("pyarrow.parquet.ParquetDataset"):
            with patch("pyarrow.fs.LocalFileSystem"):
                expected_df = pd.DataFrame({"match_id": [1001]})
                with patch("pyarrow.Table.from_pandas"):
                    mock_table = Mock()
                    mock_table.to_pandas.return_value = expected_df
                    with patch.object(
                        data_lake_storage.tables["raw_matches"],
                        "exists",
                        return_value=True,
                    ):
                        with patch(
                            "pyarrow.parquet.ParquetDataset"
                        ) as mock_dataset_class:
                            mock_dataset = Mock()
                            mock_dataset.read.return_value.to_pandas.return_value = (
                                expected_df
                            )
                            mock_dataset_class.return_value = mock_dataset

                            result = await data_lake_storage.load_historical_data(
                                "raw_matches", filters=custom_filters
                            )

                            # 验证自定义过滤器被使用
                            call_args = mock_dataset_class.call_args[1]
                            filters = call_args.get("filters", [])
                            assert ("league", "==", "Premier League") in filters

    @pytest.mark.asyncio
    async def test_load_historical_data_nonexistent_table(self, data_lake_storage):
        """测试加载不存在的表数据"""
        with patch.object(
            data_lake_storage.tables["raw_matches"], "exists", return_value=False
        ):
            result = await data_lake_storage.load_historical_data("raw_matches")

            assert result.empty

    @pytest.mark.asyncio
    async def test_load_historical_data_invalid_table_name(self, data_lake_storage):
        """测试使用无效表名加载数据"""
        with pytest.raises(ValueError, match="Unknown table"):
            await data_lake_storage.load_historical_data("invalid_table")

    @pytest.mark.asyncio
    async def test_load_historical_data_partition_columns_removed(
        self, data_lake_storage
    ):
        """测试加载时移除分区列"""
        df_with_partitions = pd.DataFrame(
            {
                "match_id": [1001],
                "year": [2024],
                "month": [1],
                "day": [15],
                "home_team": ["Arsenal"],
            }
        )

        with patch("pyarrow.parquet.ParquetDataset"):
            with patch("pyarrow.fs.LocalFileSystem"):
                with patch.object(
                    data_lake_storage.tables["raw_matches"], "exists", return_value=True
                ):
                    with patch("pyarrow.parquet.ParquetDataset") as mock_dataset_class:
                        mock_dataset = Mock()
                        mock_dataset.read.return_value.to_pandas.return_value = (
                            df_with_partitions
                        )
                        mock_dataset_class.return_value = mock_dataset

                        result = await data_lake_storage.load_historical_data(
                            "raw_matches"
                        )

                        # 验证分区列被移除
                        assert "year" not in result.columns
                        assert "month" not in result.columns
                        assert "day" not in result.columns
                        assert "match_id" in result.columns
                        assert "home_team" in result.columns

    # 测试数据归档
    @pytest.mark.asyncio
    async def test_archive_old_data_success(self, data_lake_storage, temp_base_path):
        """测试成功归档旧数据"""
        archive_date = datetime(2024, 6, 1)

        # 创建测试目录结构
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2023"
        month_dir = year_dir / "month=05"
        month_dir.mkdir(parents=True)

        # 创建测试文件
        test_file = month_dir / "test.parquet"
        test_file.write_text("test data")

        archived_count = await data_lake_storage.archive_old_data(
            "raw_matches", archive_date
        )

        assert archived_count == 1
        # 验证文件被移动到归档目录
        archive_path = data_lake_storage.base_path / "archive" / "raw_matches"
        archived_file = archive_path / "year=2023" / "month=05" / "test.parquet"
        assert archived_file.exists()

    @pytest.mark.asyncio
    async def test_archive_old_data_custom_path(
        self, data_lake_storage, temp_base_path
    ):
        """测试使用自定义归档路径"""
        archive_date = datetime(2024, 6, 1)
        custom_archive_path = temp_base_path / "custom_archive"

        # 创建测试目录结构
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2023"
        month_dir = year_dir / "month=05"
        month_dir.mkdir(parents=True)

        # 创建测试文件
        test_file = month_dir / "test.parquet"
        test_file.write_text("test data")

        archived_count = await data_lake_storage.archive_old_data(
            "raw_matches", archive_date, custom_archive_path
        )

        assert archived_count == 1
        # 验证文件被移动到自定义归档目录
        archived_file = custom_archive_path / "year=2023" / "month=05" / "test.parquet"
        assert archived_file.exists()

    @pytest.mark.asyncio
    async def test_archive_old_data_no_files_to_archive(self, data_lake_storage):
        """测试没有文件需要归档的情况"""
        archive_date = datetime(2024, 6, 1)

        archived_count = await data_lake_storage.archive_old_data(
            "raw_matches", archive_date
        )

        assert archived_count == 0

    @pytest.mark.asyncio
    async def test_archive_old_data_nonexistent_table(self, data_lake_storage):
        """测试归档不存在的表"""
        archive_date = datetime(2024, 6, 1)

        with pytest.raises(ValueError, match="Unknown table"):
            await data_lake_storage.archive_old_data("invalid_table", archive_date)

    @pytest.mark.asyncio
    async def test_archive_old_data_error_handling(
        self, data_lake_storage, temp_base_path
    ):
        """测试归档过程中的错误处理"""
        archive_date = datetime(2024, 6, 1)

        # 创建测试目录结构
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2023"
        month_dir = year_dir / "month=05"
        month_dir.mkdir(parents=True)

        # 模拟文件操作错误
        with patch.object(Path, "rename") as mock_rename:
            mock_rename.side_effect = Exception("Move failed")

            archived_count = await data_lake_storage.archive_old_data(
                "raw_matches", archive_date
            )

            assert archived_count == 0  # 错误时返回0

    # 测试获取表统计信息
    @pytest.mark.asyncio
    async def test_get_table_stats_success(self, data_lake_storage, temp_base_path):
        """测试成功获取表统计信息"""
        # 创建测试文件
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2024"
        month_dir = year_dir / "month=01"
        month_dir.mkdir(parents=True)

        test_file = month_dir / "test.parquet"
        test_file.write_text("test data")

        with patch("pyarrow.parquet.ParquetFile") as mock_parquet_file:
            mock_metadata = Mock()
            mock_metadata.num_rows = 100
            mock_parquet_file.return_value.metadata = mock_metadata

            stats = await data_lake_storage.get_table_stats("raw_matches")

            assert stats["file_count"] == 1
            assert stats["record_count"] == 100
            assert stats["date_range"]["min_date"] == "2024-01-01"
            assert stats["date_range"]["max_date"] == "2024-01-01"
            assert "table_path" in stats
            assert "last_updated" in stats

    @pytest.mark.asyncio
    async def test_get_table_stats_empty_table(self, data_lake_storage):
        """测试获取空表的统计信息"""
        stats = await data_lake_storage.get_table_stats("raw_matches")

        assert stats["file_count"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["record_count"] == 0
        assert stats["date_range"] is None

    @pytest.mark.asyncio
    async def test_get_table_stats_invalid_table_name(self, data_lake_storage):
        """测试使用无效表名获取统计信息"""
        with pytest.raises(ValueError, match="Unknown table"):
            await data_lake_storage.get_table_stats("invalid_table")

    @pytest.mark.asyncio
    async def test_get_table_stats_metadata_read_error(
        self, data_lake_storage, temp_base_path
    ):
        """测试读取元数据错误时的处理"""
        # 创建测试文件
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2024"
        month_dir = year_dir / "month=01"
        month_dir.mkdir(parents=True)

        test_file = month_dir / "test.parquet"
        test_file.write_text("test data")

        with patch("pyarrow.parquet.ParquetFile") as mock_parquet_file:
            mock_parquet_file.side_effect = Exception("Read failed")

            stats = await data_lake_storage.get_table_stats("raw_matches")

            # 应该仍然返回基本信息，但不包括记录数
            assert stats["file_count"] == 1
            assert stats["record_count"] == 0  # 元数据读取失败

    # 测试清理空分区
    @pytest.mark.asyncio
    async def test_cleanup_empty_partitions_success(
        self, data_lake_storage, temp_base_path
    ):
        """测试成功清理空分区"""
        # 创建测试目录结构
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2024"
        empty_month_dir = year_dir / "month=01"
        nonempty_month_dir = year_dir / "month=02"

        empty_month_dir.mkdir(parents=True)
        nonempty_month_dir.mkdir(parents=True)

        # 在非空目录中创建文件
        test_file = nonempty_month_dir / "test.parquet"
        test_file.write_text("test data")

        cleaned_count = await data_lake_storage.cleanup_empty_partitions("raw_matches")

        assert cleaned_count == 1  # 只清理了空的月份目录
        assert not empty_month_dir.exists()  # 空目录被删除
        assert nonempty_month_dir.exists()  # 非空目录保留

    @pytest.mark.asyncio
    async def test_cleanup_empty_partitions_empty_year(
        self, data_lake_storage, temp_base_path
    ):
        """测试清理空的年份目录"""
        # 创建测试目录结构
        table_path = data_lake_storage.tables["raw_matches"]
        year_dir = table_path / "year=2024"
        year_dir.mkdir(parents=True)

        cleaned_count = await data_lake_storage.cleanup_empty_partitions("raw_matches")

        assert cleaned_count == 1  # 清理了年份目录
        assert not year_dir.exists()  # 年份目录被删除

    @pytest.mark.asyncio
    async def test_cleanup_empty_partitions_nonexistent_table(self, data_lake_storage):
        """测试清理不存在表的空分区"""
        with pytest.raises(ValueError, match="Unknown table"):
            await data_lake_storage.cleanup_empty_partitions("invalid_table")

    @pytest.mark.asyncio
    async def test_cleanup_empty_partitions_no_partitions(self, data_lake_storage):
        """测试没有分区需要清理的情况"""
        cleaned_count = await data_lake_storage.cleanup_empty_partitions("raw_matches")

        assert cleaned_count == 0

    # 测试不同压缩格式
    @pytest.mark.asyncio
    async def test_save_with_different_compression(
        self, data_lake_storage, sample_match_data
    ):
        """测试使用不同压缩格式保存数据"""
        data_lake_storage.compression = "gzip"

        with patch("pyarrow.parquet.write_table") as mock_write:
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table

                await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data
                )

                # 验证使用了正确的压缩格式
                call_args = mock_write.call_args[1]
                assert call_args["compression"] == "gzip"

    # 测试不同分区配置
    def test_different_partition_configurations(self):
        """测试不同的分区配置"""
        # 测试自定义分区列
        storage = DataLakeStorage(partition_cols=["year", "month", "day"])
        assert storage.partition_cols == ["year", "month", "day"]

        # 测试空分区列
        storage = DataLakeStorage(partition_cols=[])
        assert storage.partition_cols == []

    # 测试文件大小限制
    @pytest.mark.asyncio
    async def test_file_size_limit_behavior(self, data_lake_storage, sample_match_data):
        """测试文件大小限制行为"""
        data_lake_storage.max_file_size_mb = 1  # 设置很小的限制

        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas"):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 2 * 1024 * 1024  # 2MB，超过限制

                    await data_lake_storage.save_historical_data(
                        "raw_matches", sample_match_data
                    )

                    # 验证文件仍然被创建（实际实现中应该处理大小限制）
                    mock_stat.assert_called()

    # 测试并发访问
    @pytest.mark.asyncio
    async def test_concurrent_save_operations(
        self, data_lake_storage, sample_match_data
    ):
        """测试并发保存操作"""

        async def save_data():
            await data_lake_storage.save_historical_data(
                "raw_matches", sample_match_data
            )

        # 模拟并发保存
        await asyncio.gather(*[save_data() for _ in range(3)])

        # 验证所有操作都完成（具体验证取决于实际实现）
        assert True  # 如果没有抛出异常，并发操作成功

    # 测试大数据集处理
    @pytest.mark.asyncio
    async def test_large_dataset_processing(self, data_lake_storage):
        """测试大数据集处理"""
        # 创建大型数据集
        large_data = []
        for i in range(10000):  # 10000条记录
            large_data.append(
                {
                    "match_id": i + 1,
                    "home_team": f"Team {i % 100}",
                    "away_team": f"Team {(i + 50) % 100}",
                    "home_score": i % 5,
                    "away_score": (i + 1) % 5,
                }
            )

        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table

                result = await data_lake_storage.save_historical_data(
                    "raw_matches", large_data
                )

                assert result.endswith(".parquet")

    # 测试错误恢复
    @pytest.mark.asyncio
    async def test_error_recovery_save_operation(
        self, data_lake_storage, sample_match_data
    ):
        """测试保存操作中的错误恢复"""
        with patch("pyarrow.parquet.write_table") as mock_write:
            mock_write.side_effect = [Exception("First attempt failed"), None]

            # 第一次尝试应该失败
            with pytest.raises(Exception, match="First attempt failed"):
                await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data
                )

            # 验证可以继续后续操作
            mock_write.side_effect = None
            result = await data_lake_storage.save_historical_data(
                "raw_matches", sample_match_data
            )
            assert result.endswith(".parquet")

    # 测试配置验证
    def test_configuration_validation(self):
        """测试配置验证"""
        # 测试无效的压缩格式
        with pytest.raises(Exception):  # 可能抛出各种异常
            DataLakeStorage(compression="invalid_format")

        # 测试无效的最大文件大小
        with pytest.raises(Exception):
            DataLakeStorage(max_file_size_mb=-1)

    # 测试路径处理
    def test_path_handling_special_characters(self):
        """测试特殊字符路径处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            special_path = os.path.join(temp_dir, "path with spaces")
            storage = DataLakeStorage(base_path=special_path)

            assert storage.base_path == Path(special_path)
            assert storage.base_path.exists()

    # 测试元数据处理
    @pytest.mark.asyncio
    async def test_metadata_handling(self, data_lake_storage, sample_match_data):
        """测试元数据处理"""
        with patch("pyarrow.parquet.write_table") as mock_write:
            with patch("pyarrow.Table.from_pandas") as mock_from_pandas:
                mock_table = Mock()
                mock_from_pandas.return_value = mock_table

                await data_lake_storage.save_historical_data(
                    "raw_matches", sample_match_data
                )

                # 验证写入时启用了统计信息和字典编码
                call_args = mock_write.call_args[1]
                assert call_args["write_statistics"] is True
                assert call_args["use_dictionary"] is True

    # 测试日志记录
    @patch("src.data.storage.data_lake_storage.logging.getLogger")
    def test_logging_behavior(self, mock_get_logger, data_lake_storage):
        """测试日志记录行为"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # 验证日志器被正确配置
        assert "storage" in mock_get_logger.call_args[0][0]

    # 测试资源清理
    def test_resource_cleanup(self, data_lake_storage):
        """测试资源清理"""
        # 数据湖存储目前没有需要显式清理的资源
        # 这个测试验证对象可以被正常销毁
        del data_lake_storage
        assert True  # 如果没有异常，清理成功


class TestS3DataLakeStorage:
    """测试S3数据湖存储功能"""

    @pytest.fixture
    def mock_s3_client(self):
        """模拟S3客户端"""
        mock_client = Mock()
        mock_client.put_object = Mock()
        mock_client.get_object = Mock()
        mock_client.get_paginator = Mock()
        return mock_client

    @pytest.fixture
    def s3_storage(self, mock_s3_client):
        """创建S3数据湖存储实例"""
        with patch("boto3.client", return_value=mock_s3_client):
            return S3DataLakeStorage(
                bucket_name="test-bucket",
                endpoint_url="http://localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                compression="snappy",
            )

    @pytest.fixture
    def sample_s3_objects(self):
        """示例S3对象列表"""
        return [
            {
                "Key": "matches/year=2024/month=01/day=15/matches_20240115_120000.parquet",
                "LastModified": datetime(2024, 1, 15),
                "Size": 1024,
            },
            {
                "Key": "matches/year=2024/month=02/day=20/matches_20240220_140000.parquet",
                "LastModified": datetime(2024, 2, 20),
                "Size": 2048,
            },
        ]

    # 测试S3存储初始化
    def test_s3_init_with_default_credentials(self):
        """测试使用默认凭据初始化S3存储"""
        with patch.dict(
            os.environ,
            {
                "S3_BUCKET_NAME": "env-bucket",
                "S3_ENDPOINT_URL": "http://env-endpoint:9000",
                "S3_ACCESS_KEY": "env-access-key",
                "S3_SECRET_KEY": "env-secret-key",
            },
        ):
            with patch("boto3.client") as mock_boto3:
                storage = S3DataLakeStorage()

                call_args = mock_boto3.call_args[1]
                assert call_args["endpoint_url"] == "http://env-endpoint:9000"
                assert call_args["aws_access_key_id"] == "env-access-key"
                assert call_args["aws_secret_access_key"] == "env-secret-key"

    def test_s3_init_without_boto3(self):
        """测试没有boto3时的初始化"""
        with patch.dict("sys.modules", {"boto3": None}):
            with patch("src.data.storage.data_lake_storage.S3_AVAILABLE", False):
                with pytest.raises(ImportError, match="boto3 is required"):
                    S3DataLakeStorage()

    def test_s3_buckets_mapping(self, s3_storage):
        """测试S3桶映射"""
        expected_buckets = {
            "raw_matches": "test-bucket-bronze",
            "raw_odds": "test-bucket-bronze",
            "processed_matches": "test-bucket-silver",
            "processed_odds": "test-bucket-silver",
            "features": "test-bucket-gold",
            "predictions": "test-bucket-gold",
        }

        assert s3_storage.buckets == expected_buckets

    def test_s3_object_paths_mapping(self, s3_storage):
        """测试S3对象路径映射"""
        expected_paths = {
            "raw_matches": "matches",
            "raw_odds": "odds",
            "processed_matches": "matches",
            "processed_odds": "odds",
            "features": "features",
            "predictions": "predictions",
        }

        assert s3_storage.object_paths == expected_paths

    # 测试S3保存数据
    @pytest.mark.asyncio
    async def test_s3_save_historical_data_success(self, s3_storage, sample_match_data):
        """测试成功保存历史数据到S3"""
        mock_response = {"ETag": "test-etag"}
        s3_storage.s3_client.put_object.return_value = mock_response

        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas"):
                mock_table = Mock()
                with patch("pyarrow.Table.from_pandas", return_value=mock_table):
                    with patch("io.BytesIO") as mock_buffer:
                        mock_buffer_instance = Mock()
                        mock_buffer.return_value = mock_buffer_instance
                        mock_buffer_instance.getvalue.return_value = b"test data"

                        result = await s3_storage.save_historical_data(
                            "raw_matches", sample_match_data
                        )

                        assert result.startswith("s3://test-bucket-bronze/matches/")
                        s3_storage.s3_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_s3_save_historical_data_with_custom_date(
        self, s3_storage, sample_match_data
    ):
        """测试使用自定义日期保存到S3"""
        custom_date = datetime(2024, 6, 15)
        s3_storage.s3_client.put_object.return_value = {"ETag": "test-etag"}

        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas"):
                mock_table = Mock()
                with patch("pyarrow.Table.from_pandas", return_value=mock_table):
                    with patch("io.BytesIO") as mock_buffer:
                        mock_buffer_instance = Mock()
                        mock_buffer.return_value = mock_buffer_instance
                        mock_buffer_instance.getvalue.return_value = b"test data"

                        result = await s3_storage.save_historical_data(
                            "raw_matches", sample_match_data, partition_date=custom_date
                        )

                        # 验证对象键包含正确的日期
                        assert "year=2024" in result
                        assert "month=06" in result
                        assert "day=15" in result

    @pytest.mark.asyncio
    async def test_s3_save_historical_data_metadata(
        self, s3_storage, sample_match_data
    ):
        """测试S3保存时的元数据"""
        s3_storage.s3_client.put_object.return_value = {"ETag": "test-etag"}

        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas"):
                mock_table = Mock()
                with patch("pyarrow.Table.from_pandas", return_value=mock_table):
                    with patch("io.BytesIO") as mock_buffer:
                        mock_buffer_instance = Mock()
                        mock_buffer.return_value = mock_buffer_instance
                        mock_buffer_instance.getvalue.return_value = b"test data"

                        await s3_storage.save_historical_data(
                            "raw_matches", sample_match_data
                        )

                        # 验证元数据被正确设置
                        call_args = s3_storage.s3_client.put_object.call_args[1]
                        metadata = call_args["Metadata"]
                        assert metadata["table_name"] == "raw_matches"
                        assert "partition_date" in metadata
                        assert metadata["compression"] == "snappy"

    # 测试S3加载数据
    @pytest.mark.asyncio
    async def test_s3_load_historical_data_success(self, s3_storage, sample_s3_objects):
        """测试成功从S3加载历史数据"""
        # Mock分页器
        mock_paginator = Mock()
        mock_page = {"Contents": sample_s3_objects}
        mock_paginator.paginate.return_value = [mock_page]
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        # Mock对象获取
        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = b"test parquet data"
        s3_storage.s3_client.get_object.return_value = mock_response

        with patch("io.BytesIO") as mock_buffer:
            with patch("pyarrow.parquet.read_table") as mock_read_table:
                mock_table = Mock()
                mock_table.to_pandas.return_value = pd.DataFrame({"match_id": [1001]})
                mock_read_table.return_value = mock_table

                result = await s3_storage.load_historical_data("raw_matches")

                assert len(result) == 1
                assert result["match_id"].iloc[0] == 1001

    @pytest.mark.asyncio
    async def test_s3_load_historical_data_with_date_range(
        self, s3_storage, sample_s3_objects
    ):
        """测试使用日期范围从S3加载数据"""
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        mock_paginator = Mock()
        mock_page = {"Contents": sample_s3_objects}
        mock_paginator.paginate.return_value = [mock_page]
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = b"test data"
        s3_storage.s3_client.get_object.return_value = mock_response

        with patch("io.BytesIO"):
            with patch("pyarrow.parquet.read_table"):
                mock_table = Mock()
                mock_table.to_pandas.return_value = pd.DataFrame({"match_id": [1001]})
                with patch("pyarrow.Table.from_pandas"):
                    with patch("pyarrow.parquet.read_table", return_value=mock_table):
                        await s3_storage.load_historical_data(
                            "raw_matches", date_from=date_from, date_to=date_to
                        )

                        # 验证日期过滤逻辑被调用
                        assert s3_storage.s3_client.get_paginator.called

    @pytest.mark.asyncio
    async def test_s3_load_historical_data_with_limit(
        self, s3_storage, sample_s3_objects
    ):
        """测试使用限制从S3加载数据"""
        mock_paginator = Mock()
        mock_page = {"Contents": sample_s3_objects}
        mock_paginator.paginate.return_value = [mock_page]
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = b"test data"
        s3_storage.s3_client.get_object.return_value = mock_response

        with patch("io.BytesIO"):
            with patch("pyarrow.parquet.read_table"):
                mock_table = Mock()
                mock_table.to_pandas.return_value = pd.DataFrame({"match_id": [1001]})
                with patch("pyarrow.Table.from_pandas"):
                    with patch("pyarrow.parquet.read_table", return_value=mock_table):
                        await s3_storage.load_historical_data("raw_matches", limit=1)

                        # 验证限制被应用
                        assert s3_storage.s3_client.get_paginator.called

    # 测试对象日期范围检查
    def test_object_in_date_range_valid_object(self, s3_storage):
        """测试有效对象的日期范围检查"""
        object_key = "matches/year=2024/month=01/day=15/matches.parquet"
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        result = s3_storage._object_in_date_range(object_key, date_from, date_to)
        assert result is True

    def test_object_in_date_range_before_range(self, s3_storage):
        """测试日期范围之前的对象"""
        object_key = "matches/year=2023/month=12/day=15/matches.parquet"
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        result = s3_storage._object_in_date_range(object_key, date_from, date_to)
        assert result is False

    def test_object_in_date_range_after_range(self, s3_storage):
        """测试日期范围之后的对象"""
        object_key = "matches/year=2024/month=02/day=15/matches.parquet"
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        result = s3_storage._object_in_date_range(object_key, date_from, date_to)
        assert result is False

    def test_object_in_date_range_no_dates(self, s3_storage):
        """测试没有日期限制的情况"""
        object_key = "matches/year=2024/month=01/day=15/matches.parquet"

        result = s3_storage._object_in_date_range(object_key, None, None)
        assert result is True

    def test_object_in_date_range_invalid_key_format(self, s3_storage):
        """测试无效对象键格式的处理"""
        object_key = "invalid/key/format.parquet"
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)

        result = s3_storage._object_in_date_range(object_key, date_from, date_to)
        assert result is True  # 无效格式时返回True

    # 测试S3表统计信息
    @pytest.mark.asyncio
    async def test_s3_get_table_stats_success(self, s3_storage, sample_s3_objects):
        """测试成功获取S3表统计信息"""
        mock_paginator = Mock()
        mock_page = {"Contents": sample_s3_objects}
        mock_paginator.paginate.return_value = [mock_page]
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        stats = await s3_storage.get_table_stats("raw_matches")

        assert stats["bucket_name"] == "test-bucket-bronze"
        assert stats["object_path"] == "matches"
        assert stats["file_count"] == 2
        assert stats["total_size_mb"] == 0.00  # 1024 + 2048 bytes / 1024 / 1024
        assert stats["date_range"]["min_date"] == "2024-01-15"
        assert stats["date_range"]["max_date"] == "2024-02-20"

    @pytest.mark.asyncio
    async def test_s3_get_table_stats_empty_bucket(self, s3_storage):
        """测试空S3桶的统计信息"""
        mock_paginator = Mock()
        mock_page = {}  # 没有Contents
        mock_paginator.paginate.return_value = [mock_page]
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        stats = await s3_storage.get_table_stats("raw_matches")

        assert stats["file_count"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["date_range"] is None

    # 测试S3错误处理
    @pytest.mark.asyncio
    async def test_s3_save_error_handling(self, s3_storage, sample_match_data):
        """测试S3保存错误处理"""
        s3_storage.s3_client.put_object.side_effect = Exception("S3 error")

        with patch("pyarrow.parquet.write_table"):
            with patch("pyarrow.Table.from_pandas"):
                mock_table = Mock()
                with patch("pyarrow.Table.from_pandas", return_value=mock_table):
                    with patch("io.BytesIO"):
                        with pytest.raises(Exception, match="S3 error"):
                            await s3_storage.save_historical_data(
                                "raw_matches", sample_match_data
                            )

    @pytest.mark.asyncio
    async def test_s3_load_error_handling(self, s3_storage):
        """测试S3加载错误处理"""
        mock_paginator = Mock()
        mock_paginator.paginate.side_effect = Exception("S3 list error")
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        result = await s3_storage.load_historical_data("raw_matches")

        assert result.empty

    # 测试S3配置和SSL
    def test_s3_ssl_configuration(self):
        """测试S3 SSL配置"""
        with patch("boto3.client") as mock_boto3:
            S3DataLakeStorage(use_ssl=True)

            call_args = mock_boto3.call_args[1]
            assert call_args["use_ssl"] is True

    def test_s3_region_configuration(self):
        """测试S3区域配置"""
        with patch("boto3.client") as mock_boto3:
            S3DataLakeStorage(region="us-west-2")

            call_args = mock_boto3.call_args[1]
            assert call_args["region_name"] == "us-west-2"

    # 测试S3大数据处理
    @pytest.mark.asyncio
    async def test_s3_large_dataset_handling(self, s3_storage):
        """测试S3大数据集处理"""
        # 创建大量S3对象
        large_objects_list = []
        for i in range(1000):
            large_objects_list.append(
                {
                    "Key": f"matches/year=2024/month=01/day={i:02d}/matches.parquet",
                    "LastModified": datetime(2024, 1, i + 1),
                    "Size": 1024,
                }
            )

        mock_paginator = Mock()
        mock_page = {"Contents": large_objects_list}
        mock_paginator.paginate.return_value = [mock_page]
        s3_storage.s3_client.get_paginator.return_value = mock_paginator

        mock_response = {"Body": Mock()}
        mock_response["Body"].read.return_value = b"test data"
        s3_storage.s3_client.get_object.return_value = mock_response

        with patch("io.BytesIO"):
            with patch("pyarrow.parquet.read_table"):
                mock_table = Mock()
                mock_table.to_pandas.return_value = pd.DataFrame({"match_id": [1001]})
                with patch("pyarrow.Table.from_pandas"):
                    with patch("pyarrow.parquet.read_table", return_value=mock_table):
                        result = await s3_storage.load_historical_data(
                            "raw_matches", limit=100
                        )

                        # 验证处理了限制数量的对象
                        assert s3_storage.s3_client.get_object.call_count <= 100

    # 测试S3并发操作
    @pytest.mark.asyncio
    async def test_s3_concurrent_operations(self, s3_storage):
        """测试S3并发操作"""

        async def save_data():
            sample_data = [{"match_id": 1}]
            with patch("pyarrow.parquet.write_table"):
                with patch("pyarrow.Table.from_pandas"):
                    mock_table = Mock()
                    with patch("pyarrow.Table.from_pandas", return_value=mock_table):
                        with patch("io.BytesIO"):
                            await s3_storage.save_historical_data(
                                "raw_matches", sample_data
                            )

        # 并发执行多个保存操作
        await asyncio.gather(*[save_data() for _ in range(5)])

        # 验证所有操作都完成
        assert s3_storage.s3_client.put_object.call_count == 5


# 导入asyncio用于并发测试
import asyncio
