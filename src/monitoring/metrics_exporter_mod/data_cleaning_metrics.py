"""
数据清洗指标记录器 / Data Cleaning Metrics Recorder

负责记录数据清洗相关的各项指标。
"""


logger = logging.getLogger(__name__)


class DataCleaningMetrics:
    """数据清洗指标记录器

    负责记录数据清洗的成功/失败次数、耗时等指标。
    """

    def __init__(self, metrics_defs):
        """
        初始化数据清洗指标记录器

        Args:
            metrics_defs: 指标定义实例
        """
        self.metrics = metrics_defs

    def record_cleaning(
        self,
        data_type: str,
        success: bool,
        duration: float,
        error_type: Optional[str] = None,
        records_processed: int = 1,
    ) -> None:
        """
        记录数据清洗指标

        Args:
            data_type: 数据类型（match/odds/scores）
            success: 是否成功
            duration: 清洗耗时（秒）
            error_type: 错误类型（如果失败）
            records_processed: 处理记录数
        """
        try:
            # 增加清洗总数
            self.metrics.data_cleaning_total.labels(
                data_type=data_type
            ).inc(records_processed)

            # 记录清洗耗时
            self.metrics.data_cleaning_duration.labels(
                data_type=data_type
            ).observe(duration)

            # 记录错误（如果失败）
            if not success and error_type:
                self.metrics.data_cleaning_errors.labels(
                    data_type=data_type,
                    error_type=error_type
                ).inc()

        except Exception as e:
            logger.error(f"记录数据清洗指标失败: {e}")

    def record_success(
        self,
        records_processed: int = 1,
        data_type: str = "default",
        duration: float = 0.0,
    ) -> None:
        """
        记录数据清洗成功 - 简化接口

        Args:
            records_processed: 处理记录数
            data_type: 数据类型
            duration: 清洗耗时
        """
        self.record_cleaning(
            data_type=data_type,
            success=True,
            duration=duration,
            records_processed=records_processed,
        )

    def record_failure(
        self,
        data_type: str,
        error_type: str,
        duration: float = 0.0,
    ) -> None:
        """
        记录数据清洗失败 - 简化接口

        Args:
            data_type: 数据类型
            error_type: 错误类型
            duration: 清洗耗时
        """
        self.record_cleaning(
            data_type=data_type,
            success=False,
            duration=duration,
            error_type=error_type,
        )

    def record_batch(
        self,
        cleaning_records: list,
    ) -> None:
        """
        批量记录数据清洗指标

        Args:
            cleaning_records: 清洗记录列表，每个记录包含清洗信息
        """
        for record in cleaning_records:
            self.record_cleaning(**record)

