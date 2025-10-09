"""
数据采集指标记录器 / Data Collection Metrics Recorder

负责记录数据采集相关的各项指标。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DataCollectionMetrics:
    """数据采集指标记录器

    负责记录数据采集的成功/失败次数、耗时等指标。
    """

    def __init__(self, metrics_defs):
        """
        初始化数据采集指标记录器

        Args:
            metrics_defs: 指标定义实例
        """
        self.metrics = metrics_defs

    def record_collection(
        self,
        data_source: str,
        collection_type: str,
        success: bool,
        duration: float,
        error_type: Optional[str] = None,
        records_count: int = 0,
    ) -> None:
        """
        记录数据采集指标

        Args:
            data_source: 数据源名称
            collection_type: 采集类型（fixtures/odds/scores）
            success: 是否成功
            duration: 采集耗时（秒）
            error_type: 错误类型（如果失败）
            records_count: 采集记录数
        """
        try:
            # 增加采集总数
            self.metrics.data_collection_total.labels(
                data_source=data_source,
                collection_type=collection_type
            ).inc(records_count if records_count > 0 else 1)

            # 记录采集耗时
            self.metrics.data_collection_duration.labels(
                data_source=data_source,
                collection_type=collection_type
            ).observe(duration)

            # 记录错误（如果失败）
            if not success and error_type:
                self.metrics.data_collection_errors.labels(
                    data_source=data_source,
                    collection_type=collection_type,
                    error_type=error_type,
                ).inc()

        except Exception as e:
            logger.error(f"记录数据采集指标失败: {e}")

    def record_success(
        self,
        data_source: str,
        records_count: int = 1,
        collection_type: str = "default",
        duration: float = 0.0,
    ) -> None:
        """
        记录数据采集成功 - 简化接口

        Args:
            data_source: 数据源名称
            records_count: 采集记录数
            collection_type: 采集类型
            duration: 采集耗时
        """
        self.record_collection(
            data_source=data_source,
            collection_type=collection_type,
            success=True,
            duration=duration,
            records_count=records_count,
        )

    def record_failure(
        self,
        data_source: str,
        error_type: str,
        collection_type: str = "default",
        duration: float = 0.0,
    ) -> None:
        """
        记录数据采集失败 - 简化接口

        Args:
            data_source: 数据源名称
            error_type: 错误类型
            collection_type: 采集类型
            duration: 采集耗时
        """
        self.record_collection(
            data_source=data_source,
            collection_type=collection_type,
            success=False,
            duration=duration,
            error_type=error_type,
        )

    def record_batch(
        self,
        collections: list,
    ) -> None:
        """
        批量记录数据采集指标

        Args:
            collections: 采集记录列表，每个记录包含采集信息
        """
        for collection in collections:
            self.record_collection(**collection)