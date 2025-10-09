"""
本地数据湖存储
Local Data Lake Storage

提供基于本地文件系统的数据湖存储功能。
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import fs

from .partition import PartitionManager
from .metadata import MetadataManager

logger = logging.getLogger(__name__)


class LocalDataLakeStorage:
    """
    本地数据湖存储管理器

    负责管理足球预测系统的历史数据存储，
    使用Parquet格式提供高效的数据存储和查询能力。
    """

    def __init__(
        self,
        base_path: Optional[str] = None,
        compression: str = "snappy",
        partition_cols: Optional[List[str]] = None,
        max_file_size_mb: int = 100,
    ):
        """
        初始化数据湖存储

        Args:
            base_path: 数据湖根目录路径
            compression: 压缩格式（snappy/gzip/brotli）
            partition_cols: 分区列名列表
            max_file_size_mb: 单个文件最大大小（MB）
        """
        # 设置默认路径为当前目录下的data子目录，确保在测试环境中可访问
        if base_path is None:
            base_path = os.path.join(os.getcwd(), "data", "football_lake")

        self.base_path = Path(base_path)
        self.compression = compression
        self.partition_cols = partition_cols or ["year", "month"]
        self.max_file_size_mb = max_file_size_mb
        self.logger = logging.getLogger(f"storage.{self.__class__.__name__}")

        # 确保基础目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 数据分区路径结构
        self.tables = {
            "raw_matches": self.base_path / "bronze" / "matches",
            "raw_odds": self.base_path / "bronze" / "odds",
            "processed_matches": self.base_path / "silver" / "matches",
            "processed_odds": self.base_path / "silver" / "odds",
            "features": self.base_path / "gold" / "features",
            "predictions": self.base_path / "gold" / "predictions",
        }

        # 创建表目录
        for table_path in self.tables.values():
            table_path.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.partition_manager = PartitionManager(self.partition_cols)
        self.metadata_manager = MetadataManager()

    async def save_historical_data(
        self,
        table_name: str,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        partition_date: Optional[datetime] = None,
    ) -> str:
        """
        保存历史数据到Parquet文件

        Args:
            table_name: 表名（raw_matches/raw_odds/features等）
            data: 要保存的数据（DataFrame或字典列表）
            partition_date: 分区日期，默认使用当前日期

        Returns:
            str: 保存的文件路径

        Raises:
            ValueError: 表名不存在或数据格式错误
            OSError: 文件写入失败
        """
        try:
            if table_name not in self.tables:
                raise ValueError(
                    f"Unknown table: {table_name}. Available: {list(self.tables.keys())}"
                )

            # 转换为DataFrame
            if isinstance(data, list):
                if not data:
                    self.logger.warning(f"No data to save for table {table_name}")
                    return ""
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            if df.empty:
                self.logger.warning(f"Empty DataFrame for table {table_name}")
                return ""

            # 设置分区日期
            if partition_date is None:
                partition_date = datetime.now()

            # 使用分区管理器处理分区
            partition_path = self.partition_manager.create_partition_path(
                self.tables[table_name], partition_date
            )

            # 生成文件名
            timestamp = datetime.now().strftime("%H%M%S")
            file_name = (
                f"{table_name}_{partition_date.strftime('%Y%m%d')}_{timestamp}.parquet"
            )
            file_path = partition_path / file_name

            # 添加分区列到数据
            df = self.partition_manager.add_partition_columns(df, partition_date)

            # 转换为PyArrow表
            table = pa.Table.from_pandas(df)

            # 写入Parquet文件
            pq.write_table(
                table,
                file_path,
                compression=self.compression,
                use_dictionary=True,  # 使用字典编码优化存储
                write_statistics=True,  # 写入统计信息便于查询优化
            )

            self.logger.info(
                f"Saved {len(df)} records to {file_path}, "
                f"file size: {file_path.stat().st_size / 1024 / 1024:.2f} MB"
            )

            return str(file_path)

        except Exception as e:
            self.logger.error(
                f"Failed to save historical data for {table_name}: {str(e)}"
            )
            raise

    async def load_historical_data(
        self,
        table_name: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        filters: Optional[List[Any]] = None,
    ) -> pd.DataFrame:
        """
        从数据湖加载历史数据

        Args:
            table_name: 表名
            date_from: 开始日期
            date_to: 结束日期
            filters: PyArrow过滤条件

        Returns:
            pd.DataFrame: 查询结果
        """
        try:
            if table_name not in self.tables:
                raise ValueError(f"Unknown table: {table_name}")

            table_path = self.tables[table_name]

            if not table_path.exists():
                self.logger.warning(f"Table path does not exist: {table_path}")
                return pd.DataFrame()

            # 使用分区管理器构建过滤器
            all_filters = self.partition_manager.build_date_filters(date_from, date_to)
            if filters:
                all_filters.extend(filters)

            # 读取Parquet数据
            dataset = pq.ParquetDataset(
                table_path,
                filesystem=fs.LocalFileSystem(),
                filters=all_filters if all_filters else None,
            )

            table = dataset.read()
            df = table.to_pandas()

            # 移除分区列（如果不需要）
            df = self.partition_manager.remove_partition_columns(df)

            self.logger.info(
                f"Loaded {len(df)} records from {table_name}, "
                f"date range: {date_from} to {date_to}"
            )

            return df

        except Exception as e:
            self.logger.error(
                f"Failed to load historical data for {table_name}: {str(e)}"
            )
            return pd.DataFrame()

    async def archive_old_data(
        self,
        table_name: str,
        archive_before: datetime,
        archive_path: Optional[Union[str, Path]] = None,
    ) -> int:
        """
        归档旧数据

        将指定日期之前的数据移动到归档目录，节省存储空间。

        Args:
            table_name: 表名
            archive_before: 归档截止日期
            archive_path: 归档目录，默认为archive子目录

        Returns:
            int: 归档的文件数量
        """
        try:
            if table_name not in self.tables:
                raise ValueError(f"Unknown table: {table_name}")

            return await self.partition_manager.archive_partitions(
                self.tables[table_name],
                archive_before,
                archive_path or self.base_path / "archive" / table_name
            )

        except Exception as e:
            self.logger.error(f"Failed to archive data for {table_name}: {str(e)}")
            return 0

    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        获取表的统计信息

        Args:
            table_name: 表名

        Returns:
            Dict: 统计信息（文件数量、总大小、记录数量、日期范围等）
        """
        try:
            if table_name not in self.tables:
                raise ValueError(f"Unknown table: {table_name}")

            return await self.metadata_manager.get_table_stats(self.tables[table_name])

        except Exception as e:
            self.logger.error(f"Failed to get stats for {table_name}: {str(e)}")
            return {"error": str(e)}

    async def cleanup_empty_partitions(self, table_name: str) -> int:
        """
        清理空的分区目录

        Args:
            table_name: 表名

        Returns:
            int: 清理的目录数量
        """
        try:
            if table_name not in self.tables:
                raise ValueError(f"Unknown table: {table_name}")

            return await self.partition_manager.cleanup_empty_partitions(
                self.tables[table_name]
            )

        except Exception as e:
            self.logger.error(
                f"Failed to cleanup partitions for {table_name}: {str(e)}"
            )
            return 0