"""
from .metadata import S3MetadataManager
from .partition import PartitionManager

S3数据湖存储
S3 Data Lake Storage

提供基于S3/MinIO的数据湖存储功能。
"""




try:
    import boto3
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False


class S3DataLakeStorage:
    """
    基于S3/MinIO的数据湖存储管理器

    支持将数据存储到S3兼容的对象存储中，
    提供高可用性和无限扩展能力。
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: str = None,
        access_key: str = None,
        secret_key: str = None,
        region: str = "us-east-1",
        compression: str = "snappy",
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

        # 初始化组件
        self.partition_manager = PartitionManager(["year", "month", "day"])
        self.metadata_manager = S3MetadataManager(self.s3_client)

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
            df = self.partition_manager.add_partition_columns(df, partition_date)

            # 转换为Parquet格式的字节流
            table = pa.Table.from_pandas(df)

            # 写入到内存缓冲区
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
                ContentType="application/octet-stream",
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
                    df = self.partition_manager.remove_partition_columns(df)

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
                if part.startswith("year="):
                    year_part = int(part.split("=")[1])
                elif part.startswith("month="):
                    month_part = int(part.split("=")[1])
                elif part.startswith("day="):
                    day_part = int(part.split("=")[1])

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

            return await self.metadata_manager.get_table_stats(bucket_name, object_path)

        except Exception as e:



            self.logger.error(f"Failed to get S3 stats for {table_name}: {str(e)}")
            return {"error": str(e)}