"""
data_lake_storage.py 简化测试文件
测试数据湖存储管理器功能的基础方法
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pathlib import Path
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestDataLakeStorageSimple:
    """测试数据湖存储管理器 - 简化版本"""

    @patch('src.data.storage.data_lake_storage.pd')
    @patch('src.data.storage.data_lake_storage.pa')
    @patch('src.data.storage.data_lake_storage.pq')
    @patch('src.data.storage.data_lake_storage.fs')
    def test_basic_initialization(self, mock_fs, mock_pq, mock_pa, mock_pd):
        """测试基本初始化"""
        # Mock the pandas DataFrame
        mock_df = Mock()
        mock_df.empty = False
        mock_pd.DataFrame.return_value = mock_df

        # Import after patching to avoid import errors
        from src.data.storage.data_lake_storage import DataLakeStorage

        # Create instance with mocked dependencies
        storage = DataLakeStorage(
            base_path="/tmp/test_data_lake",
            compression="snappy",
            partition_cols=["year", "month"],
            max_file_size_mb=100
        )

        # Verify basic properties
        assert storage.base_path == Path("/tmp/test_data_lake")
        assert storage.compression == "snappy"
        assert storage.partition_cols == ["year", "month"]
        assert storage.max_file_size_mb == 100
        assert "raw_matches" in storage.tables
        assert "features" in storage.tables

    @patch('src.data.storage.data_lake_storage.pd')
    @patch('src.data.storage.data_lake_storage.os.getcwd')
    @patch('pathlib.Path.mkdir')
    def test_initialization_with_defaults(self, mock_mkdir, mock_getcwd, mock_pd):
        """测试默认初始化"""
        mock_getcwd.return_value = '/current/dir'

        # Import after patching
        from src.data.storage.data_lake_storage import DataLakeStorage

        storage = DataLakeStorage()
        expected_path = Path('/current/dir/data/football_lake')
        assert storage.base_path == expected_path

    @patch('src.data.storage.data_lake_storage.pd')
    @patch('src.data.storage.data_lake_storage.pa')
    @patch('src.data.storage.data_lake_storage.pq')
    @patch('src.data.storage.data_lake_storage.fs')
    @patch('pathlib.Path.mkdir')
    def test_directories_creation_on_init(self, mock_mkdir, mock_fs, mock_pq, mock_pa, mock_pd):
        """测试初始化时目录创建"""
        # Import after patching
        from src.data.storage.data_lake_storage import DataLakeStorage

        DataLakeStorage(base_path="/tmp/test")

        # Verify mkdir was called for directory creation
        assert mock_mkdir.call_count > 0

    @patch('src.data.storage.data_lake_storage.pd')
    def test_compression_options(self, mock_pd):
        """测试不同的压缩选项"""
        from src.data.storage.data_lake_storage import DataLakeStorage

        compressions = ["snappy", "gzip", "brotli"]
        for compression in compressions:
            storage = DataLakeStorage(compression=compression)
            assert storage.compression == compression

    @patch('src.data.storage.data_lake_storage.pd')
    def test_partition_columns(self, mock_pd):
        """测试不同的分区列配置"""
        from src.data.storage.data_lake_storage import DataLakeStorage

        partition_configs = [
            ["year"],
            ["year", "month"],
            ["year", "month", "day"],
            ["league", "season"]
        ]

        for partition_cols in partition_configs:
            storage = DataLakeStorage(partition_cols=partition_cols)
            assert storage.partition_cols == partition_cols

    @patch('src.data.storage.data_lake_storage.pd')
    def test_file_size_limits(self, mock_pd):
        """测试不同的文件大小限制"""
        from src.data.storage.data_lake_storage import DataLakeStorage

        sizes = [50, 100, 200, 500]
        for size in sizes:
            storage = DataLakeStorage(max_file_size_mb=size)
            assert storage.max_file_size_mb == size


class TestS3DataLakeStorageSimple:
    """测试S3数据湖存储管理器 - 简化版本"""

    @patch('src.data.storage.data_lake_storage.boto3')
    @patch('src.data.storage.data_lake_storage.pd')
    @patch('src.data.storage.data_lake_storage.pa')
    @patch('src.data.storage.data_lake_storage.pq')
    def test_s3_initialization(self, mock_pq, mock_pa, mock_pd, mock_boto3):
        """测试S3存储初始化"""
        # Mock boto3 client
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client

        # Import after patching
        from src.data.storage.data_lake_storage import S3DataLakeStorage

        with patch('src.data.storage.data_lake_storage.S3_AVAILABLE', True):
            s3_storage = S3DataLakeStorage(
                bucket_name="test-bucket",
                endpoint_url="http://localhost:9000",
                access_key="test-key",
                secret_key="test-secret",
                compression="snappy"
            )

        assert s3_storage.bucket_prefix == "test-bucket"
        assert s3_storage.compression == "snappy"
        assert "raw_matches" in s3_storage.buckets

    @patch('src.data.storage.data_lake_storage.pd')
    def test_s3_unavailable_error(self, mock_pd):
        """测试S3不可用时的错误"""
        from src.data.storage.data_lake_storage import S3DataLakeStorage

        with patch('src.data.storage.data_lake_storage.S3_AVAILABLE', False):
            with pytest.raises(ImportError) as exc_info:
                S3DataLakeStorage()

            assert "boto3 is required" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])