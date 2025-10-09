"""
分区管理器
Partition Manager

管理数据湖的分区策略和操作。
"""



logger = logging.getLogger(__name__)


class PartitionManager:
    """分区管理器"""

    def __init__(self, partition_cols: List[str]):
        """
        初始化分区管理器

        Args:
            partition_cols: 分区列名列表
        """
        self.partition_cols = partition_cols
        self.logger = logging.getLogger(f"storage.{self.__class__.__name__}")

    def create_partition_path(self, table_path: Path, partition_date: datetime) -> Path:
        """
        创建分区路径

        Args:
            table_path: 表基础路径
            partition_date: 分区日期

        Returns:
            Path: 分区路径
        """
        partition_path = (
            table_path
            / f"year={partition_date.year}"
            / f"month={partition_date.month:02d}"
        )

        if "day" in self.partition_cols:
            partition_path = partition_path / f"day={partition_date.day:02d}"

        partition_path.mkdir(parents=True, exist_ok=True)
        return partition_path

    def add_partition_columns(self, df: pd.DataFrame, partition_date: datetime) -> pd.DataFrame:
        """
        添加分区列到DataFrame

        Args:
            df: 原始DataFrame
            partition_date: 分区日期

        Returns:
            pd.DataFrame: 包含分区列的DataFrame
        """
        df = df.copy()
        df["year"] = partition_date.year
        df["month"] = partition_date.month

        if "day" in self.partition_cols:
            df["day"] = partition_date.day

        return df

    def remove_partition_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        移除分区列

        Args:
            df: 包含分区列的DataFrame

        Returns:
            pd.DataFrame: 移除分区列后的DataFrame
        """
        partition_cols_to_drop = [col for col in self.partition_cols if col in df.columns]
        if partition_cols_to_drop:
            df = df.drop(columns=partition_cols_to_drop)

        return df

    def build_date_filters(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Any]:
        """
        构建日期过滤器

        Args:
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            List[Any]: 过滤器列表
        """
        filters = []

        if date_from:
            filters.append(("year", ">=", date_from.year))
            filters.append(("month", ">=", date_from.month))
            if "day" in self.partition_cols:
                filters.append(("day", ">=", date_from.day))

        if date_to:
            filters.append(("year", "<=", date_to.year))
            filters.append(("month", "<=", date_to.month))
            if "day" in self.partition_cols:
                filters.append(("day", "<=", date_to.day))

        return filters

    async def archive_partitions(
        self,
        table_path: Path,
        archive_before: datetime,
        archive_path: Path,
    ) -> int:
        """
        归档分区

        Args:
            table_path: 表路径
            archive_before: 归档截止日期
            archive_path: 归档路径

        Returns:
            int: 归档的文件数量
        """
        if not table_path.exists():
            return 0

        archive_path.mkdir(parents=True, exist_ok=True)
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
                        archive_path / year_dir.name / month_dir.name
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
            f"Archived {archived_count} files "
            f"before {archive_before.strftime('%Y-%m-%d')}"
        )

        return archived_count

    async def cleanup_empty_partitions(self, table_path: Path) -> int:
        """
        清理空的分区目录

        Args:
            table_path: 表路径

        Returns:
            int: 清理的目录数量
        """
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

    def get_partition_info_from_path(self, file_path: Path) -> Dict[str, Any]:
        """
        从文件路径提取分区信息

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 分区信息
        """
        partition_info = {}

        for part in file_path.parts:
            if part.startswith("year="):
                partition_info["year"] = int(part.split("=")[1])
            elif part.startswith("month="):
                partition_info["month"] = int(part.split("=")[1])
            elif part.startswith("day="):
                partition_info["day"] = int(part.split("=")[1])

        return partition_info

    def validate_partition_schema(self, table: Any) -> bool:
        """
        验证分区模式

        Args:
            table: PyArrow表

        Returns:
            bool: 是否有效
        """
        schema = table.schema
        missing_cols = []

        for col in self.partition_cols:
            if col not in schema.names:
                missing_cols.append(col)



        if missing_cols:
            self.logger.warning(
                f"Missing partition columns: {missing_cols}"
            )
            return False

        return True