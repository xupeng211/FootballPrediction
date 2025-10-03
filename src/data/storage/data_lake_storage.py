"""
数据湖存储管理器

提供数据湖的存储、检索、管理功能。
支持Parquet格式的高效存储和查询，实现历史数据归档。

主要功能：
- 历史数据保存到Parquet文件
- 数据分区管理（按时间/联赛等）
- 数据压缩和优化
- 元数据管理
- 支持MinIO/S3对象存储

基于 DATA_DESIGN.md 第2.2节数据湖设计。
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

try:
    import boto3

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False


class DataLakeStorage:
    """
    数据湖存储管理器

    负责管理足球预测系统的历史数据存储，
    使用Parquet格式提供高效的数据存储和查询能力。
    """

    def __init__(
        self,
        base_path: Optional[str] = None,
        compression: str = os.getenv("DATA_LAKE_STORAGE_STR_48"),
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

            # 添加分区列
            df["year"] = partition_date.year
            df["month"] = partition_date.month
            df["day"] = partition_date.day

            # 构建文件路径
            table_path = self.tables[table_name]
            partition_path = (
                table_path
                / f"year={partition_date.year}"
                / f"month={partition_date.month:02d}"
            )
            partition_path.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%H%M%S")
            file_name = (
                f"{table_name}_{partition_date.strftime('%Y%m%d')}_{timestamp}.parquet"
            )
            file_path = partition_path / file_name

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

            # 构建时间过滤器
            time_filters = []
            if date_from:
                time_filters.append(("year", ">=", date_from.year))
                time_filters.append(("month", ">=", date_from.month))
            if date_to:
                time_filters.append(("year", "<=", date_to.year))
                time_filters.append(("month", "<=", date_to.month))

            # 合并过滤器
            all_filters = time_filters
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
            partition_cols_to_drop = ["year", "month", "day"]
            df = df.drop(
                columns=[col for col in partition_cols_to_drop if col in df.columns]
            )

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

            table_path = self.tables[table_name]
            if not table_path.exists():
                return 0

            # 设置归档路径
            if archive_path is None:
                archive_path_obj = self.base_path / "archive" / table_name
            else:
                archive_path_obj = Path(archive_path)

            archive_path_obj.mkdir(parents=True, exist_ok=True)

            archived_count = 0

            # 遍历分区目录
            for year_dir in table_path.glob("year=*"):
                year = int(year_dir.name.split("=")[1])

                for month_dir in year_dir.glob("month=*"):
                    month = int(month_dir.name.split("=")[1])

                    # 检查是否需要归档
                    partition_date = datetime(year, month, 1)
                    if partition_date < archive_before:
                        # 移动整个月份目录到归档位置
                        archive_month_path = (
                            archive_path_obj / year_dir.name / month_dir.name
                        )
                        archive_month_path.parent.mkdir(parents=True, exist_ok=True)

                        month_dir.rename(archive_month_path)
                        archived_count += len(
                            list(archive_month_path.glob("*.parquet"))
                        )

                        self.logger.info(
                            f"Archived {month_dir} to {archive_month_path}"
                        )

            self.logger.info(
                f"Archived {archived_count} files for {table_name} "
                f"before {archive_before.strftime('%Y-%m-%d')}"
            )

            return archived_count

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

            table_path = self.tables[table_name]
            if not table_path.exists():
                return {
                    "file_count": 0,
                    "total_size_mb": 0,
                    "record_count": 0,
                    "date_range": None,
                }

            # 收集统计信息
            file_count = 0
            total_size = 0
            record_count = 0
            date_ranges = []

            for parquet_file in table_path.glob("**/*.parquet"):
                file_count += 1
                total_size += parquet_file.stat().st_size

                # 读取文件元数据
                try:
                    parquet_file_obj = pq.ParquetFile(parquet_file)
                    record_count += parquet_file_obj.metadata.num_rows

                    # 提取日期信息
                    if "year" in parquet_file_obj.schema.names:
                        # 从分区路径提取日期
                        parts = parquet_file.parts
                        year_part = [p for p in parts if p.startswith("year = os.getenv("DATA_LAKE_STORAGE_YEAR_365")month = os.getenv("DATA_LAKE_STORAGE_MONTH_365")=")[1])
                            month = int(month_part[0].split("=")[1])
                            date_ranges.append(datetime(year, month, 1))

                except Exception as e:
                    self.logger.warning(
                        f"Failed to read metadata from {parquet_file}: {str(e)}"
                    )

            # 计算日期范围
            date_range = None
            if date_ranges:
                date_range = {
                    "min_date": min(date_ranges).strftime("%Y-%m-%d"),
                    "max_date": max(date_ranges).strftime("%Y-%m-%d"),
                }

            stats = {
                "file_count": file_count,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "record_count": record_count,
                "date_range": date_range,
                "table_path": str(table_path),
                "last_updated": datetime.now().isoformat(),
            }

            return stats

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

            table_path = self.tables[table_name]
            if not table_path.exists():
                return 0

            cleaned_count = 0

            # 清理空的月份目录
            for year_dir in table_path.glob("year=*"):
                for month_dir in year_dir.glob("month=*"):
                    # 检查目录是否为空
                    if not any(month_dir.glob("*.parquet")):
                        month_dir.rmdir()
                        cleaned_count += 1
                        self.logger.info(f"Removed empty partition: {month_dir}")

                # 检查年份目录是否为空
                if not any(year_dir.glob("month=*")):
                    year_dir.rmdir()
                    cleaned_count += 1
                    self.logger.info(f"Removed empty year directory: {year_dir}")

            return cleaned_count

        except Exception as e:
            self.logger.error(
                f"Failed to cleanup partitions for {table_name}: {str(e)}"
            )
            return 0


class S3DataLakeStorage:
    """
    基于S3/MinIO的数据湖存储管理器

    支持将数据存储到S3兼容的对象存储中，
    提供高可用性和无限扩展能力。
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = os.getenv("DATA_LAKE_STORAGE_STR_456"),
        compression: str = os.getenv("DATA_LAKE_STORAGE_STR_48"),
        use_ssl: bool = False,
    ):
        """
        初始化S3数据湖存储

        Args:
            bucket_name: S3桶名前缀
            endpoint_url: MinIO/S3端点URL
            access_key: 访问密钥
            secret_key: 密钥
            region: 区域
            compression: 压缩格式
            use_ssl: 是否使用SSL
        """
        if not S3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            )

        # Load credentials from environment variables if not provided
        bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "football-lake")
        endpoint_url = endpoint_url or os.getenv(
            "S3_ENDPOINT_URL", "http://localhost:9000"
        )
        access_key = access_key or os.getenv("S3_ACCESS_KEY", "football_admin")
        secret_key = secret_key or os.getenv("S3_SECRET_KEY", "football_minio_2025")

        self.bucket_prefix = bucket_name
        self.compression = compression
        self.logger = logging.getLogger(f"storage.{self.__class__.__name__}")

        # 初始化S3客户端
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            use_ssl=use_ssl,
        )

        # 定义桶映射（Bronze/Silver/Gold层）
        self.buckets = {
            "raw_matches": f"{bucket_name}-bronze",
            "raw_odds": f"{bucket_name}-bronze",
            "processed_matches": f"{bucket_name}-silver",
            "processed_odds": f"{bucket_name}-silver",
            "features": f"{bucket_name}-gold",
            "predictions": f"{bucket_name}-gold",
        }

        # 表到对象路径的映射
        self.object_paths = {
            "raw_matches": "matches",
            "raw_odds": "odds",
            "processed_matches": "matches",
            "processed_odds": "odds",
            "features": "features",
            "predictions": "predictions",
        }

    async def save_historical_data(
        self,
        table_name: str,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        partition_date: Optional[datetime] = None,
    ) -> str:
        """
        保存历史数据到S3/MinIO

        Args:
            table_name: 表名
            data: 数据
            partition_date: 分区日期

        Returns:
            str: S3对象键
        """
        try:
            if table_name not in self.buckets:
                raise ValueError(
                    f"Unknown table: {table_name}. Available: {list(self.buckets.keys())}"
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

            # 构建S3对象键
            bucket_name = self.buckets[table_name]
            object_path = self.object_paths[table_name]
            timestamp = datetime.now().strftime("%H%M%S")

            object_key = (
                f"{object_path}/"
                f"year={partition_date.year}/"
                f"month={partition_date.month:02d}/"
                f"day={partition_date.day:02d}/"
                f"{table_name}_{partition_date.strftime('%Y%m%d')}_{timestamp}.parquet"
            )

            # 添加分区列
            df["year"] = partition_date.year
            df["month"] = partition_date.month
            df["day"] = partition_date.day

            # 转换为Parquet格式的字节流
            table = pa.Table.from_pandas(df)

            # 写入到内存缓冲区
            import io

            buffer = io.BytesIO()
            pq.write_table(
                table,
                buffer,
                compression=self.compression,
                use_dictionary=True,
                write_statistics=True,
            )

            # 上传到S3
            buffer.seek(0)
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=buffer.getvalue(),
                ContentType = os.getenv("DATA_LAKE_STORAGE_CONTENTTYPE_597"),
                Metadata={
                    "table_name": table_name,
                    "partition_date": partition_date.isoformat(),
                    "record_count": str(len(df)),
                    "compression": self.compression,
                },
            )

            self.logger.info(
                f"Saved {len(df)} records to s3://{bucket_name}/{object_key}, "
                f"size: {len(buffer.getvalue()) / 1024 / 1024:.2f} MB"
            )

            return f"s3://{bucket_name}/{object_key}"

        except Exception as e:
            self.logger.error(f"Failed to save data to S3 for {table_name}: {str(e)}")
            raise

    async def load_historical_data(
        self,
        table_name: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        从S3/MinIO加载历史数据

        Args:
            table_name: 表名
            date_from: 开始日期
            date_to: 结束日期
            limit: 限制记录数

        Returns:
            pd.DataFrame: 查询结果
        """
        try:
            if table_name not in self.buckets:
                raise ValueError(f"Unknown table: {table_name}")

            bucket_name = self.buckets[table_name]
            object_path = self.object_paths[table_name]

            # 构建搜索前缀
            if date_from and date_to:
                # 如果指定了日期范围，使用更精确的前缀搜索
                prefix = f"{object_path}/"
            else:
                prefix = f"{object_path}/"

            # 列出匹配的对象
            objects = []
            paginator = self.s3_client.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        # 简单的日期过滤（基于对象键路径）
                        if self._object_in_date_range(obj["Key"], date_from, date_to):
                            objects.append(obj)

            if not objects:
                self.logger.info(f"No objects found for {table_name} in date range")
                return pd.DataFrame()

            # 按修改时间排序，可选择限制数量
            objects.sort(key=lambda x: x["LastModified"], reverse=True)
            if limit:
                objects = objects[:limit]

            # 下载并合并数据
            dataframes = []
            for obj in objects:
                try:
                    response = self.s3_client.get_object(
                        Bucket=bucket_name, Key=obj["Key"]
                    )

                    # 读取Parquet数据
                    buffer = io.BytesIO(response["Body"].read())
                    table = pq.read_table(buffer)
                    df = table.to_pandas()

                    # 移除分区列
                    partition_cols_to_drop = ["year", "month", "day"]
                    df = df.drop(
                        columns=[
                            col for col in partition_cols_to_drop if col in df.columns
                        ]
                    )

                    dataframes.append(df)

                except Exception as e:
                    self.logger.warning(f"Failed to load object {obj['Key']}: {str(e)}")

            # 合并所有数据
            if dataframes:
                result_df = pd.concat(dataframes, ignore_index=True)
                self.logger.info(
                    f"Loaded {len(result_df)} records from {len(dataframes)} files for {table_name}"
                )
                return result_df
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Failed to load data from S3 for {table_name}: {str(e)}")
            return pd.DataFrame()

    def _object_in_date_range(
        self,
        object_key: str,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> bool:
        """
        检查S3对象是否在指定日期范围内

        Args:
            object_key: S3对象键
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            bool: 是否在范围内
        """
        if not date_from and not date_to:
            return True

        try:
            # 从对象键中提取年月日信息
            # 格式: path/year=2025/month=01/day=15/filename.parquet
            parts = object_key.split("/")

            year_part = None
            month_part = None
            day_part = None

            for part in parts:
                if part.startswith("year = os.getenv("DATA_LAKE_STORAGE_YEAR_740")=")[1])
                elif part.startswith("month = os.getenv("DATA_LAKE_STORAGE_MONTH_742")=")[1])
                elif part.startswith("day = os.getenv("DATA_LAKE_STORAGE_DAY_743")=")[1])

            if year_part and month_part and day_part:
                obj_date = datetime(year_part, month_part, day_part)

                if date_from and obj_date < date_from:
                    return False
                if date_to and obj_date > date_to:
                    return False

                return True

        except Exception as e:
            self.logger.warning(
                f"Failed to parse date from object key {object_key}: {str(e)}"
            )

        return True

    async def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        获取S3表的统计信息

        Args:
            table_name: 表名

        Returns:
            Dict: 统计信息
        """
        try:
            if table_name not in self.buckets:
                raise ValueError(f"Unknown table: {table_name}")

            bucket_name = self.buckets[table_name]
            object_path = self.object_paths[table_name]

            # 统计对象
            total_objects = 0
            total_size = 0
            date_ranges = []

            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=bucket_name, Prefix=f"{object_path}/"
            ):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        total_objects += 1
                        total_size += obj["Size"]

                        # 提取日期信息用于统计
                        try:
                            parts = obj["Key"].split("/")
                            year_part = month_part = day_part = None
                            for part in parts:
                                if part.startswith("year = os.getenv("DATA_LAKE_STORAGE_YEAR_798")=")[1])
                                elif part.startswith("month = os.getenv("DATA_LAKE_STORAGE_MONTH_799")=")[1])
                                elif part.startswith("day = os.getenv("DATA_LAKE_STORAGE_DAY_802")=")[1])

                            if year_part and month_part and day_part:
                                date_ranges.append(
                                    datetime(year_part, month_part, day_part)
                                )
                        except (ValueError, IndexError):
                            pass

            # 计算日期范围
            date_range = None
            if date_ranges:
                date_range = {
                    "min_date": min(date_ranges).strftime("%Y-%m-%d"),
                    "max_date": max(date_ranges).strftime("%Y-%m-%d"),
                }

            return {
                "bucket_name": bucket_name,
                "object_path": object_path,
                "file_count": total_objects,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "date_range": date_range,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get S3 stats for {table_name}: {str(e)}")
            return {"error": str(e)}
