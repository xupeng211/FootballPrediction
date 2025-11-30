"""数据血缘报告器.

集成 OpenLineage 标准,自动上报数据血缘信息到 Marquez。
跟踪数据流转过程,包括采集,清洗,转换等各个环节.
"""

import logging
from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    # For Python < 3.11
    UTC = timezone.utc
from typing import Any
from uuid import uuid4

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import InputDataset, Job, OutputDataset, Run, RunEvent
from openlineage.client.facet_v2 import (
    error_message_run,
    schema_dataset,
    source_code_location_job,
    sql_job,
)

logger = logging.getLogger(__name__)


class LineageReporter:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    数据血缘报告器

    负责向 Marquez 报告数据血缘信息,
    跟踪数据流转过程。
    支持多种数据处理场景:采集、清洗,
    转换,
    聚合等.
    """

    def __init__(
        self,
        marquez_url: str = "http://localhost:5000",
        namespace: str = "football_prediction",
    ):
        """初始化数据血缘报告器.

        Args:
            marquez_url: Marquez 服务地址
            namespace: 数据血缘命名空间
        """
        self.client = OpenLineageClient(url=marquez_url)
        self.namespace = namespace
        self._active_runs: dict[str, str] = {}  # job_name -> run_id

    def start_job_run(
        self,
        job_name: str,
        job_type: str = "BATCH",
        inputs: list[dict[str, Any]] | None = None,
        description: str | None = None,
        source_location: str | None = None,
        parent_run_id: str | None = None,
        transformation_sql: str | None = None,
    ) -> str:
        """开始一个作业运行.

        Args:
            job_name: 作业名称
            job_type: 作业类型（BATCH/STREAM）
            inputs: 输入数据集信息
            description: 作业描述
            source_location: 源码位置
            parent_run_id: 父运行ID（如果是子作业）
            transformation_sql: 转换SQL语句

        Returns:
            str: 运行ID
        """
        if inputs is None:
            inputs = []

        run_id = str(uuid4())
        self._active_runs[job_name] = run_id

        # 构建作业信息
        job_facets = {}
        if description:
            job_facets["description"] = {"description": description}
        if source_location:
            job_facets["sourceCodeLocation"] = (
                source_code_location_job.SourceCodeLocationJobFacet(
                    type="git", url=source_location
                )
            )
        if transformation_sql:
            job_facets["sql"] = sql_job.SQLJobFacet(query=transformation_sql)

        # 构建运行信息
        run_facets: dict[str, Any] = {}
        # 实现parent_run功能
        if parent_run_id:
            from openlineage.client.facet_v2 import parent_run

            run_facets["parentRun"] = parent_run.ParentRunFacet(
                run=parent_run.ParentRun(
                    runId=parent_run_id, namespace=self.namespace, name=job_name
                )
            )

        # 构建输入数据集
        input_datasets = []
        for input_info in inputs:
            dataset_name = input_info.get("name", "unknown")
            dataset_namespace = input_info.get("namespace", self.namespace)

            dataset_facets = {}
            if "schema" in input_info:
                dataset_facets["schema"] = schema_dataset.SchemaDatasetFacet(
                    fields=input_info["schema"]
                )

            input_datasets.append(
                InputDataset(
                    namespace=dataset_namespace,
                    name=dataset_name,
                    facets=dataset_facets,
                )
            )

        # 发送开始事件
        event = RunEvent(
            eventType="START",
            eventTime=datetime.now(UTC).isoformat(),
            run=Run(runId=run_id, facets=run_facets),
            job=Job(namespace=self.namespace, name=job_name, facets=job_facets),
            inputs=input_datasets,
            outputs=[],
            producer="football_prediction_lineage_reporter",
        )

        try:
            self.client.emit(event)
            logger.info(f"Started job run: {job_name} with run_id: {run_id}")
            return run_id
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"Failed to emit start event for job {job_name}: {e}")
            raise

    def complete_job_run(
        self,
        job_name: str,
        outputs: list[dict[str, Any]] | None = None,
        metrics: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> bool:
        """完成一个作业运行.

        Args:
            job_name: 作业名称
            outputs: 输出数据集信息
            metrics: 运行指标
            run_id: 运行ID（如果不提供,从活跃运行中获取）

        Returns:
            bool: 是否成功
        """
        if outputs is None:
            outputs = []

        # 获取运行ID
        if run_id is None:
            run_id = self._active_runs.get(job_name)
            if run_id is None:
                logger.error(f"No active run found for job: {job_name}")
                return False

        # 构建输出数据集
        output_datasets = []
        for output_info in outputs:
            dataset_name = output_info.get("name", "unknown")
            dataset_namespace = output_info.get("namespace", self.namespace)

            dataset_facets = {}
            if "schema" in output_info:
                dataset_facets["schema"] = schema_dataset.SchemaDatasetFacet(
                    fields=output_info["schema"]
                )
            if "statistics" in output_info:
                dataset_facets["dataQualityMetrics"] = {
                    "dataQualityMetrics": output_info["statistics"]
                }

            output_datasets.append(
                OutputDataset(
                    namespace=dataset_namespace,
                    name=dataset_name,
                    facets=dataset_facets,
                )
            )

        # 构建运行指标
        run_facets: dict[str, Any] = {}
        if metrics:
            run_facets["processing_engine"] = {
                "processing_engine": {
                    "version": "1.0.0",
                    "name": "football_prediction_engine",
                    "openlineageAdapterVersion": "1.0.0",
                }
            }

        # 发送完成事件
        event = RunEvent(
            eventType="COMPLETE",
            eventTime=datetime.now(UTC).isoformat(),
            run=Run(runId=run_id, facets=run_facets),
            job=Job(namespace=self.namespace, name=job_name, facets={}),
            inputs=[],
            outputs=output_datasets,
            producer="football_prediction_lineage_reporter",
        )

        # 清理活跃运行记录
        if job_name in self._active_runs:
            del self._active_runs[job_name]

        try:
            self.client.emit(event)
            logger.info(f"Completed job run: {job_name} with run_id: {run_id}")
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"Failed to emit complete event for job {job_name}: {e}")
            return False

    def fail_job_run(
        self, job_name: str, error_message: str, run_id: str | None = None
    ) -> bool:
        """标记作业运行失败.

        Args:
                job_name: 作业名称
                error_message: 错误信息
                run_id: 运行ID（如果不提供,
        从活跃运行中获取）

        Returns:
                bool: 是否成功
        """
        # 获取运行ID
        if run_id is None:
            run_id = self._active_runs.get(job_name)
            if run_id is None:
                logger.error(f"No active run found for job: {job_name}")
                return False

        # 构建错误信息
        run_facets = {
            "errorMessage": error_message_run.ErrorMessageRunFacet(
                message=error_message, programmingLanguage="PYTHON"
            )
        }

        # 发送失败事件
        event = RunEvent(
            eventType="FAIL",
            eventTime=datetime.now(UTC).isoformat(),
            run=Run(runId=run_id, facets=run_facets),
            job=Job(namespace=self.namespace, name=job_name, facets={}),
            inputs=[],
            outputs=[],
            producer="football_prediction_lineage_reporter",
        )

        try:
            self.client.emit(event)
            logger.info(
                f"Failed job run: {job_name} with run_id: {run_id}, error: {error_message}"
            )

            # 清理活跃运行记录
            if job_name in self._active_runs:
                del self._active_runs[job_name]

            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"Failed to emit fail event for job {job_name}: {e}")
            return False

    def report_data_collection(
        self,
        source_name: str,
        target_table: str,
        records_collected: int,
        collection_time: datetime,
        source_config: dict[str, Any] | None = None,
    ) -> str:
        """报告数据采集过程.

        Args:
            source_name: 数据源名称
            target_table: 目标表名
            records_collected: 采集的记录数
            collection_time: 采集时间
            source_config: 数据源配置

        Returns:
            str: 运行ID
        """
        job_name = f"data_collection_{source_name}"

        # 输入数据集（外部数据源）
        inputs = [
            {
                "name": source_name,
                "namespace": "external",
                "schema": source_config.get("schema", {}) if source_config else {},
            }
        ]

        # 开始作业
        run_id = self.start_job_run(
            job_name=job_name,
            job_type="BATCH",
            inputs=inputs,
            description=f"Collect data from {source_name} to {target_table}",
            source_location="src/data/collectors/",
        )

        # 输出数据集（数据库表）
        outputs = [
            {
                "name": target_table,
                "namespace": "football_prediction_db",
                "statistics": {
                    "rowCount": records_collected,
                    "collectionTime": collection_time.isoformat(),
                },
            }
        ]

        # 完成作业
        self.complete_job_run(
            job_name=job_name,
            outputs=outputs,
            metrics={
                "records_collected": records_collected,
                "collection_duration": "unknown",
            },
            run_id=run_id,
        )

        return run_id

    def report_data_transformation(
        self,
        source_tables: list[str],
        target_table: str,
        transformation_sql: str,
        records_processed: int,
        transformation_type: str = "ETL",
    ) -> str:
        """报告数据转换过程.

        Args:
            source_tables: 源表列表
            target_table: 目标表
            transformation_sql: 转换SQL
            records_processed: 处理的记录数
            transformation_type: 转换类型

        Returns:
            str: 运行ID
        """
        job_name = f"data_transformation_{target_table}"

        # 输入数据集
        inputs = [
            {"name": table, "namespace": "football_prediction_db"}
            for table in source_tables
        ]

        # 开始作业
        run_id = self.start_job_run(
            job_name=job_name,
            job_type="BATCH",
            inputs=inputs,
            description=f"{transformation_type} transformation to create {target_table}",
            source_location="src/data/processing/",
            transformation_sql=transformation_sql,
        )

        # 输出数据集
        outputs = [
            {
                "name": target_table,
                "namespace": "football_prediction_db",
                "statistics": {
                    "rowCount": records_processed,
                    "transformationType": transformation_type,
                },
            }
        ]

        # 完成作业
        self.complete_job_run(
            job_name=job_name,
            outputs=outputs,
            metrics={
                "records_processed": records_processed,
                "transformation_type": transformation_type,
            },
            run_id=run_id,
        )

        return run_id

    def get_active_runs(self) -> dict[str, str]:
        """获取当前活跃的运行.

        Returns:
            dict[str, str]: 作业名称到运行ID的映射
        """
        return self._active_runs.copy()

    def clear_active_runs(self) -> None:
        """清理所有活跃运行记录."""
        self._active_runs.clear()
        logger.info("Cleared all active runs")


# 全局实例
lineage_reporter = LineageReporter()
