"""
元数据管理器
Metadata Manager

管理数据湖的元数据信息。
"""



logger = logging.getLogger(__name__)


class MetadataManager:
    """本地文件系统元数据管理器"""

    def __init__(self, metadata_path: Optional[Path] = None):
        """
        初始化元数据管理器

        Args:
            metadata_path: 元数据存储路径
        """
        if metadata_path is None:
            metadata_path = Path.cwd() / "data" / "football_lake" / "metadata"

        self.metadata_path = metadata_path
        self.logger = logging.getLogger(f"storage.{self.__class__.__name__}")

        # 确保元数据目录存在
        self.metadata_path.mkdir(parents=True, exist_ok=True)

        # 元数据文件路径
        self.tables_metadata_file = self.metadata_path / "tables.json"
        self.schemas_file = self.metadata_path / "schemas.json"

        # 加载现有元数据
        self._load_metadata()

    def _load_metadata(self) -> None:
        """加载现有元数据"""
        # 加载表元数据
        if self.tables_metadata_file.exists():
            try:
                with open(self.tables_metadata_file, 'r') as f:
                    self.tables_metadata = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load tables metadata: {e}")
                self.tables_metadata = {}
        else:
            self.tables_metadata = {}

        # 加载模式元数据
        if self.schemas_file.exists():
            try:
                with open(self.schemas_file, 'r') as f:
                    self.schemas_metadata = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load schemas metadata: {e}")
                self.schemas_metadata = {}
        else:
            self.schemas_metadata = {}

    def _save_metadata(self) -> None:
        """保存元数据到文件"""
        try:
            # 保存表元数据
            with open(self.tables_metadata_file, 'w') as f:
                json.dump(self.tables_metadata, f, indent=2, default=str)

            # 保存模式元数据
            with open(self.schemas_file, 'w') as f:
                json.dump(self.schemas_metadata, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")

    async def update_table_metadata(
        self,
        table_name: str,
        file_path: str,
        record_count: int,
        file_size: int,
        partition_date: datetime,
        schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新表元数据

        Args:
            table_name: 表名
            file_path: 文件路径
            record_count: 记录数量
            file_size: 文件大小（字节）
            partition_date: 分区日期
            schema: 表模式信息
        """
        try:
            # 初始化表元数据
            if table_name not in self.tables_metadata:
                self.tables_metadata[table_name] = {
                    "created_at": datetime.now().isoformat(),
                    "files": [],
                    "total_records": 0,
                    "total_size_bytes": 0,
                    "partitions": set()
                }

            # 添加文件信息
            table_meta = self.tables_metadata[table_name]
            file_info = {
                "path": str(file_path),
                "record_count": record_count,
                "size_bytes": file_size,
                "partition_date": partition_date.isoformat(),
                "created_at": datetime.now().isoformat()
            }
            table_meta["files"].append(file_info)

            # 更新统计信息
            table_meta["total_records"] += record_count
            table_meta["total_size_bytes"] += file_size
            table_meta["partitions"].add(f"{partition_date.year}-{partition_date.month:02d}")
            table_meta["last_updated"] = datetime.now().isoformat()

            # 转换set为list以便JSON序列化
            table_meta["partitions"] = list(table_meta["partitions"])

            # 保存模式信息
            if schema:
                self.schemas_metadata[table_name] = {
                    "schema": schema,
                    "last_updated": datetime.now().isoformat()
                }

            # 保存到文件
            self._save_metadata()

            self.logger.info(
                f"Updated metadata for {table_name}: "
                f"+{record_count} records, +{file_size / 1024 / 1024:.2f} MB"
            )

        except Exception as e:
            self.logger.error(f"Failed to update metadata for {table_name}: {e}")

    async def get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """
        获取表元数据

        Args:
            table_name: 表名

        Returns:
            Dict: 表元数据
        """
        return self.tables_metadata.get(table_name, {})

    async def get_table_stats(self, table_path: Path) -> Dict[str, Any]:
        """
        获取表的统计信息

        Args:
            table_path: 表路径

        Returns:
            Dict: 统计信息
        """
        try:
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
                        year_part = [p for p in parts if p.startswith("year=")]
                        month_part = [p for p in parts if p.startswith("month=")]

                        if year_part and month_part:
                            year = int(year_part[0].split("=")[1])
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
            self.logger.error(f"Failed to get stats for {table_path}: {str(e)}")
            return {"error": str(e)}

    async def delete_table_metadata(self, table_name: str) -> None:
        """
        删除表元数据

        Args:
            table_name: 表名
        """
        try:
            if table_name in self.tables_metadata:
                del self.tables_metadata[table_name]

            if table_name in self.schemas_metadata:
                del self.schemas_metadata[table_name]

            self._save_metadata()

            self.logger.info(f"Deleted metadata for table: {table_name}")

        except Exception as e:
            self.logger.error(f"Failed to delete metadata for {table_name}: {e}")

    async def list_tables(self) -> List[str]:
        """
        列出所有表

        Returns:
            List[str]: 表名列表
        """
        return list(self.tables_metadata.keys())

    async def get_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取表模式

        Args:
            table_name: 表名

        Returns:
            Dict: 表模式信息
        """
        return self.schemas_metadata.get(table_name, {}).get("schema")

    async def cleanup_metadata(self, table_path: Path) -> int:
        """
        清理无效的元数据条目

        Args:
            table_path: 表路径

        Returns:
            int: 清理的条目数量
        """
        try:
            cleaned_count = 0

            for table_name, table_meta in list(self.tables_metadata.items()):
                # 检查文件是否仍然存在
                valid_files = []
                for file_info in table_meta.get("files", []):
                    file_path = Path(file_info["path"])
                    if file_path.exists():
                        valid_files.append(file_info)
                    else:
                        cleaned_count += 1

                # 更新文件列表
                if len(valid_files) != len(table_meta.get("files", [])):
                    if valid_files:
                        table_meta["files"] = valid_files
                        # 重新计算统计信息
                        table_meta["total_records"] = sum(f["record_count"] for f in valid_files)
                        table_meta["total_size_bytes"] = sum(f["size_bytes"] for f in valid_files)
                    else:
                        # 如果没有有效文件，删除整个表元数据
                        del self.tables_metadata[table_name]
                        if table_name in self.schemas_metadata:
                            del self.schemas_metadata[table_name]

            # 保存更新后的元数据
            if cleaned_count > 0:
                self._save_metadata()
                self.logger.info(f"Cleaned up {cleaned_count} invalid metadata entries")

            return cleaned_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup metadata: {e}")
            return 0


class S3MetadataManager:
    """S3元数据管理器"""

    def __init__(self, s3_client):
        """
        初始化S3元数据管理器

        Args:
            s3_client: S3客户端
        """
        self.s3_client = s3_client
        self.logger = logging.getLogger(f"storage.{self.__class__.__name__}")

    async def update_table_metadata(
        self,
        bucket_name: str,
        object_key: str,
        table_name: str,
        record_count: int,
        file_size: int,
        partition_date: datetime,
        schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新S3对象元数据

        Args:
            bucket_name: S3桶名
            object_key: 对象键
            table_name: 表名
            record_count: 记录数量
            file_size: 文件大小
            partition_date: 分区日期
            schema: 表模式信息
        """
        try:
            # 更新对象标签
            tags = [
                {"Key": "Table", "Value": table_name},
                {"Key": "Records", "Value": str(record_count)},
                {"Key": "Partition", "Value": f"{partition_date.year}-{partition_date.month:02d}"},
                {"Key": "UpdatedAt", "Value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            ]

            # 将标签转换为查询字符串格式
            tag_string = "&".join([f"{tag['Key']}={tag['Value']}" for tag in tags])

            self.s3_client.put_object_tagging(
                Bucket=bucket_name,
                Key=object_key,
                Tagging={
                    "TagSet": tags
                }
            )

            self.logger.debug(f"Updated S3 metadata for {object_key}")

        except Exception as e:
            self.logger.warning(f"Failed to update S3 metadata: {e}")

    async def get_table_stats(self, bucket_name: str, object_path: str) -> Dict[str, Any]:
        """
        获取S3表的统计信息

        Args:
            bucket_name: S3桶名
            object_path: 对象路径前缀

        Returns:
            Dict: 统计信息
        """
        try:
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
                                if part.startswith("year="):
                                    year_part = int(part.split("=")[1])
                                elif part.startswith("month="):
                                    month_part = int(part.split("=")[1])
                                elif part.startswith("day="):
                                    day_part = int(part.split("=")[1])

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
            self.logger.error(f"Failed to get S3 stats for {bucket_name}/{object_path}: {e}")
            return {"error": str(e)}