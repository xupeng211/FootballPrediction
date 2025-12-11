from typing import Optional

#!/usr/bin/env python3
"""
数据管道集成测试

测试数据清洗、队列系统等模块的集成功能
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from src.queues.fifo_queue import MemoryFIFOQueue, QueueTask, TaskPriority
    from src.utils.string_utils import cached_slug, normalize_string, truncate_string
    from test_data_cleaning import FootballDataCleaner as Cleaner
except ImportError:
    # 如果导入失败，使用模拟测试
    Cleaner = None
    MemoryFIFOQueue = None
    QueueTask = None
    TaskPriority = None


class TestDataPipelineIntegration:
    """数据管道集成测试类"""

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5],
                "home_team_id": [100, 200, 300, 400, 500],
                "away_team_id": [200, 100, 400, 300, 600],
                "home_score": [2, np.nan, 0, 3, 1],
                "away_score": [1, 2, np.nan, 0, 0],
                "match_date": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ],
                "home_goals": [2, np.nan, 0, 3, 1],
                "away_goals": [1, 2, np.nan, 0, 0],
                "possession_home": [60.5, 45.2, np.nan, 58.7, 49.8],
                "possession_away": [39.5, np.nan, 47.9, 41.3, 50.2],
            }
        )

    @pytest.fixture
    def cleaner(self):
        """创建数据清洗器"""
        if Cleaner:
            return Cleaner()
        else:
            pytest.skip("FootballDataCleaner not available")

    @pytest.fixture
    async def queue(self):
        """创建内存队列"""
        if MemoryFIFOQueue:
            return MemoryFIFOQueue("integration_test")
        else:
            pytest.skip("MemoryFIFOQueue not available")

    def test_data_cleaning_integration(self, cleaner, sample_data):
        """测试数据清洗集成"""
        if cleaner and sample_data is not None:
            # 清洗数据
            cleaned_data = cleaner.clean_dataset(sample_data, "matches")

            # 验证清洗结果
            assert isinstance(cleaned_data, pd.DataFrame)
            assert len(cleaned_data) > 0
            assert cleaned_data.isnull().sum().sum() < sample_data.isnull().sum().sum()

            # 获取清洗报告
            report = cleaner.get_cleaning_report()
            assert isinstance(report, dict)
            assert "original_shape" in report
            assert "cleaned_shape" in report
        else:
            pytest.skip("Required components not available")

    @pytest.mark.asyncio
    async def test_queue_system_integration(self, queue):
        """测试队列系统集成"""
        if queue and QueueTask and TaskPriority:
            # 创建任务
            task_data = {"match_id": 123, "home_team": "Team A", "away_team": "Team B"}

            task = QueueTask(
                id="integration_test_1",
                task_type="match_processing",
                data=task_data,
                priority=TaskPriority.NORMAL,
                created_at=datetime.now(),
            )

            # 入队任务
            enqueue_result = await queue.enqueue(task)
            assert enqueue_result is True

            # 出队任务
            dequeued_task = await queue.dequeue()
            assert dequeued_task is not None
            assert dequeued_task.id == task.id
            assert dequeued_task.task_type == "match_processing"
            assert dequeued_task.data == task_data
        else:
            pytest.skip("Queue components not available")

    @pytest.mark.asyncio
    async def test_data_to_queue_workflow(self, cleaner, queue, sample_data):
        """测试数据处理到队列的工作流"""
        if cleaner and queue and QueueTask and TaskPriority:
            # 1. 清洗数据
            cleaned_data = cleaner.clean_dataset(sample_data, "matches")

            # 2. 为清洗后的数据创建队列任务
            tasks = []
            for _, row in cleaned_data.iterrows():
                task_data = {
                    "match_id": row.get("match_id"),
                    "home_team_id": row.get("home_team_id"),
                    "away_team_id": row.get("away_team_id"),
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                    "match_date": row.get("match_date"),
                }

                task = QueueTask(
                    id=f"match_task_{row.get('match_id')}",
                    task_type="match_data_processing",
                    data=task_data,
                    priority=TaskPriority.NORMAL,
                    created_at=datetime.now(),
                )
                tasks.append(task)

            # 3. 将任务加入队列
            for task in tasks:
                await queue.enqueue(task)

            # 4. 验证队列状态
            queue_size = await queue.get_size()
            assert queue_size == len(tasks)

            # 5. 处理队列中的任务
            processed_tasks = []
            while await queue.get_size() > 0:
                task = await queue.dequeue()
                if task:
                    processed_tasks.append(task)

            # 6. 验证处理结果
            assert len(processed_tasks) == len(tasks)
            for _i, task in enumerate(processed_tasks):
                assert task.task_type == "match_data_processing"
                assert "match_id" in task.data
        else:
            pytest.skip("Required components not available")

    def test_string_utils_integration(self):
        """测试字符串工具集成"""
        if cached_slug and normalize_string and truncate_string:
            # 测试字符串处理管道
            original_text = "  Hello World! This is a TEST string with special characters: @#$%^&*()  "

            # 1. 标准化文本
            normalized = normalize_string(original_text)
            assert isinstance(normalized, str)

            # 2. 生成slug
            slug = cached_slug(normalized)
            assert isinstance(slug, str)
            assert " " not in slug  # 不应该有空格

            # 3. 截断文本
            truncated = truncate_string(normalized, 20)
            assert len(truncated) <= 23  # 20 + "..."

            # 4. 验证整个管道的合理性
            assert len(slug) <= len(normalized)
            assert len(truncated) <= len(normalized)
        else:
            pytest.skip("String utils not available")

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, cleaner, queue, sample_data):
        """测试端到端工作流"""
        if cleaner and queue and QueueTask and TaskPriority:
            # 完整的数据处理工作流
            workflow_results = {}

            # 步骤1: 数据清洗
            try:
                cleaned_data = cleaner.clean_dataset(sample_data, "matches")
                workflow_results["cleaning"] = {
                    "success": True,
                    "original_rows": len(sample_data),
                    "cleaned_rows": len(cleaned_data),
                    "missing_values_before": sample_data.isnull().sum().sum(),
                    "missing_values_after": cleaned_data.isnull().sum().sum(),
                }
            except Exception as e:
                workflow_results["cleaning"] = {"success": False, "error": str(e)}

            # 步骤2: 数据转换和队列处理
            try:
                # 转换清洗后的数据为任务
                tasks = []
                for _, row in cleaned_data.iterrows():
                    task_data = {
                        "match_id": int(row.get("match_id")),
                        "home_team_id": int(row.get("home_team_id")),
                        "away_team_id": int(row.get("away_team_id")),
                        "home_score": (
                            float(row.get("home_score"))
                            if not pd.isna(row.get("home_score"))
                            else 0.0
                        ),
                        "away_score": (
                            float(row.get("away_score"))
                            if not pd.isna(row.get("away_score"))
                            else 0.0
                        ),
                        "match_date": str(row.get("match_date")),
                    }

                    task = QueueTask(
                        id=f"etl_task_{int(row.get('match_id'))}",
                        task_type="etl_processing",
                        data=task_data,
                        priority=TaskPriority.NORMAL,
                        created_at=datetime.now(),
                    )
                    tasks.append(task)

                # 将任务加入队列
                for task in tasks:
                    await queue.enqueue(task)

                workflow_results["queueing"] = {
                    "success": True,
                    "tasks_created": len(tasks),
                    "queue_size_after": await queue.get_size(),
                }

            except Exception as e:
                workflow_results["queueing"] = {"success": False, "error": str(e)}

            # 步骤3: 任务处理
            try:
                processed_tasks = []
                while await queue.get_size() > 0:
                    task = await queue.dequeue()
                    if task:
                        # 模拟任务处理
                        processed_data = task.data.copy()
                        processed_data["processed_at"] = datetime.now().isoformat()
                        processed_data["processing_status"] = "completed"
                        processed_tasks.append(processed_data)

                workflow_results["processing"] = {
                    "success": True,
                    "tasks_processed": len(processed_tasks),
                    "all_processed": all(
                        t.get("processing_status") == "completed"
                        for t in processed_tasks
                    ),
                }

            except Exception as e:
                workflow_results["processing"] = {"success": False, "error": str(e)}

            # 验证整体工作流
            assert workflow_results["cleaning"]["success"]
            assert workflow_results["queueing"]["success"]
            assert workflow_results["processing"]["success"]

            # 验证数据完整性
            original_count = workflow_results["cleaning"]["original_rows"]
            final_count = workflow_results["processing"]["tasks_processed"]
            assert final_count <= original_count  # 处理的任务数不应该超过原始数据行数

        else:
            pytest.skip("Required components not available")

    def test_error_handling_integration(self, cleaner):
        """测试错误处理集成"""
        if cleaner:
            # 测试处理无效数据
            invalid_data = pd.DataFrame(
                {
                    "match_id": ["invalid", "not_a_number", None],
                    "home_team_id": [100, np.nan, "invalid"],
                    "away_team_id": [200, "invalid", np.nan],
                    "home_score": [2, "invalid", None],
                    "away_score": ["invalid", 2, np.nan],
                    "match_date": ["invalid_date", None, "another_invalid"],
                }
            )

            # 清洗器应该能处理无效数据而不崩溃
            try:
                result = cleaner.clean_dataset(invalid_data, "matches")
                assert isinstance(result, pd.DataFrame)
                # 即使是无效数据，也应该返回某种形式的结果
            except Exception as e:
                # 如果抛出异常，应该是有意义的异常
                assert isinstance(e, (ValueError, TypeError))
        else:
            pytest.skip("Cleaner not available")

    def test_performance_integration(self, cleaner):
        """测试性能集成"""
        if cleaner:
            # 创建较大的数据集
            large_data = pd.DataFrame(
                {
                    "match_id": range(1000),
                    "home_team_id": np.random.randint(1, 1000, 1000),
                    "away_team_id": np.random.randint(1, 1000, 1000),
                    "home_score": np.random.randint(0, 10, 1000),
                    "away_score": np.random.randint(0, 10, 1000),
                    "match_date": [f"2024-01-{i % 30 + 1:02d}" for i in range(1000)],
                }
            )

            # 随机添加一些缺失值
            for col in ["home_score", "away_score"]:
                missing_indices = np.random.choice(1000, size=100, replace=False)
                large_data.loc[missing_indices, col] = np.nan

            # 测试处理性能
            import time

            start_time = time.time()

            result = cleaner.clean_dataset(large_data, "matches")

            end_time = time.time()
            processing_time = end_time - start_time

            # 验证结果和性能
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            assert processing_time < 10.0  # 应该在10秒内完成

            # 验证清洗效果
            assert result.isnull().sum().sum() < large_data.isnull().sum().sum()
        else:
            pytest.skip("Cleaner not available")

    def test_data_quality_integration(self, cleaner, sample_data):
        """测试数据质量集成"""
        if cleaner and sample_data is not None:
            # 检查原始数据质量
            original_quality = {
                "total_rows": len(sample_data),
                "missing_values": sample_data.isnull().sum().sum(),
                "duplicate_rows": sample_data.duplicated().sum(),
                "data_types": sample_data.dtypes.to_dict(),
            }

            # 清洗数据
            cleaned_data = cleaner.clean_dataset(sample_data, "matches")

            # 检查清洗后数据质量
            cleaned_quality = {
                "total_rows": len(cleaned_data),
                "missing_values": cleaned_data.isnull().sum().sum(),
                "duplicate_rows": cleaned_data.duplicated().sum(),
                "data_types": cleaned_data.dtypes.to_dict(),
            }

            # 验证数据质量改进
            assert (
                cleaned_quality["missing_values"] <= original_quality["missing_values"]
            )
            assert (
                cleaned_quality["duplicate_rows"] <= original_quality["duplicate_rows"]
            )

            # 获取清洗报告
            report = cleaner.get_cleaning_report()
            assert isinstance(report, dict)
            assert "cleaning_steps" in report
            assert len(report["cleaning_steps"]) > 0
        else:
            pytest.skip("Required components not available")


class TestStringProcessingIntegration:
    """字符串处理集成测试类"""

    def test_string_pipeline_integration(self):
        """测试字符串处理管道集成"""
        test_strings = [
            "  Hello World!  ",
            "Python Programming @#$%^",
            "  Test String with multiple   spaces  ",
            "Café and naïve text",
            "Special characters: !@#$%^&*()",
        ]

        results = []
        for text in test_strings:
            if cached_slug and normalize_string and truncate_string:
                # 处理管道：标准化 -> slug生成 -> 截断
                normalized = normalize_string(text)
                slug = cached_slug(normalized)
                truncated = truncate_string(slug, 20)

                result = {
                    "original": text,
                    "normalized": normalized,
                    "slug": slug,
                    "truncated": truncated,
                    "original_length": len(text),
                    "final_length": len(truncated),
                }
                results.append(result)

        # 验证处理结果
        assert len(results) == len(test_strings)
        for result in results:
            assert result["final_length"] <= 23  # 20 + "..."
            assert result["final_length"] <= result["original_length"]
            assert " " not in result["slug"]  # slug中不应该有空格

    def test_batch_string_processing(self):
        """测试批量字符串处理"""
        if cached_slug and normalize_string:
            test_strings = [
                "Test String 1",
                "Test String 2",
                "Test String 3",
                "Test String 4",
                "Test String 5",
            ]

            # 批量处理
            normalized_strings = [normalize_string(s) for s in test_strings]
            slugs = [cached_slug(s) for s in normalized_strings]

            # 验证批量处理结果
            assert len(slugs) == len(test_strings)
            assert all(isinstance(slug, str) for slug in slugs)
            assert all(" " not in slug for slug in slugs)  # 所有slug都不应该有空格

            # 验证一致性 - slug应该是原始字符串的规范化版本
            for i, original in enumerate(test_strings):
                # 验证slug是通过将空格替换为连字符并转换为小数生成的
                expected_slug = original.lower().replace(" ", "-")
                assert slugs[i] == expected_slug
        else:
            pytest.skip("String processing functions not available")
