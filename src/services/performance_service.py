#!/usr/bin/env python3
"""
性能服务
整合所有性能优化功能，提供统一的性能管理接口
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from src.core.logger import get_logger
from src.database.connection import DatabaseManager
from src.performance.async_optimizer import (
    get_batch_processor,
    get_connection_pool,
    get_file_optimizer,
    get_query_optimizer,
)
from src.performance.db_query_optimizer import get_database_optimizer

logger = get_logger(__name__)


@dataclass
class PerformanceReport:
    """性能报告数据类"""

    timestamp: float
    database_metrics: dict[str, Any]
    async_metrics: dict[str, Any]
    query_metrics: dict[str, Any]
    connection_pool_metrics: dict[str, Any]
    recommendations: list[str]
    overall_score: float


class PerformanceService:
    """性能服务 - 统一性能管理"""

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db_manager = db_manager or DatabaseManager()
        self.batch_processor = get_batch_processor()
        self.connection_pool = get_connection_pool()
        self.file_optimizer = get_file_optimizer()
        self.query_optimizer = get_query_optimizer()
        self.db_optimizer = get_database_optimizer()

        # 性能基线
        self.baseline_metrics = {
            "query_response_time": 0.5,  # 500ms
            "batch_throughput": 1000,  # 1000 ops/sec
            "connection_utilization": 0.7,  # 70%
            "error_rate": 0.05,  # 5%
        }

    async def initialize(self):
        """初始化性能服务"""
        try:
            logger.info("初始化性能服务...")
            # 确保数据库管理器已初始化
            if (
                not hasattr(self.db_manager, "initialized")
                or not self.db_manager.initialized
            ):
                self.db_manager.initialize()

            logger.info("✅ 性能服务初始化完成")
        except Exception as e:
            logger.error(f"性能服务初始化失败: {e}")
            raise

    # ========================================
    # 数据库性能优化
    # ========================================

    async def optimize_database_queries(
        self, queries: list[dict[str, Any]]
    ) -> list[Any]:
        """
        优化数据库查询执行

        Args:
            queries: 查询列表 [{"query": "...", "params": {...}}, ...]

        Returns:
            优化执行结果
        """
        start_time = time.time()

        try:
            # 使用查询优化器执行
            results = await self.query_optimizer.execute_batch_with_optimization(
                queries, max_concurrent=10
            )

            execution_time = time.time() - start_time
            logger.info(
                f"批量查询优化完成: {len(queries)}个查询, 耗时 {execution_time:.3f}秒"
            )

            return results

        except Exception as e:
            logger.error(f"数据库查询优化失败: {e}")
            raise

    async def analyze_database_performance(
        self, table_names: list[str] | None = None
    ) -> dict[str, Any]:
        """分析数据库性能"""
        try:
            if table_names is None:
                # 获取所有用户表
                async with self.db_manager.get_async_session() as session:
                    tables_query = """
                    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
                    """
                    from sqlalchemy import text

                    stmt = text(tables_query)
                    result = await session.execute(stmt)
                    table_names = [row[0] for row in result.fetchall()]

            # 分析表性能
            performance_data = await self.db_optimizer.analyze_table_performance(
                table_names
            )

            # 获取查询性能报告
            query_report = self.query_optimizer.get_performance_report()

            return {
                "tables": performance_data,
                "queries": query_report,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.error(f"数据库性能分析失败: {e}")
            raise

    # ========================================
    # 异步I/O性能优化
    # ========================================

    async def optimize_batch_processing(
        self,
        items: list[Any],
        processor_func: callable,
        batch_size: int = 100,
        max_concurrent: int = 5,
    ) -> list[Any]:
        """
        优化批量处理性能

        Args:
            items: 要处理的数据
            processor_func: 处理函数
            batch_size: 批次大小
            max_concurrent: 最大并发数

        Returns:
            处理结果
        """
        try:
            # 配置批量处理器
            self.batch_processor.batch_size = batch_size
            self.batch_processor.max_concurrent_batches = max_concurrent

            # 执行批量处理
            results = await self.batch_processor.process_batch(items, processor_func)

            logger.info(f"批量处理优化完成: {len(items)}项数据")

            return results

        except Exception as e:
            logger.error(f"批量处理优化失败: {e}")
            raise

    async def optimize_file_operations(
        self, file_path: str, operation: str = "read"
    ) -> Any:
        """优化文件操作性能"""
        try:
            if operation == "read":
                # 读取文件统计
                import aiofiles.os

                file_size = (await aiofiles.os.stat(file_path)).st_size
                logger.info(f"文件 {file_path} 大小: {file_size} bytes")

                return {"file_size": file_size, "optimized": True}
            else:
                logger.info(f"文件操作 {operation} 优化完成")
                return {"optimized": True}

        except Exception as e:
            logger.error(f"文件操作优化失败: {e}")
            raise

    # ========================================
    # 连接池优化
    # ========================================

    def get_connection_pool_status(self) -> dict[str, Any]:
        """获取连接池状态"""
        return {
            "pool_stats": self.connection_pool.get_pool_stats(),
            "baseline": self.baseline_metrics["connection_utilization"],
            "status": "healthy" if self._is_pool_healthy() else "warning",
        }

    def _is_pool_healthy(self) -> bool:
        """检查连接池健康状态"""
        stats = self.connection_pool.get_pool_stats()
        utilization = stats.get("utilization", 0)
        return utilization <= self.baseline_metrics["connection_utilization"]

    # ========================================
    # 性能监控和报告
    # ========================================

    async def generate_performance_report(self) -> PerformanceReport:
        """生成综合性能报告"""
        try:
            timestamp = time.time()

            # 收集各项性能指标
            database_metrics = await self.analyze_database_performance()
            async_metrics = {
                "batch_processor": self.batch_processor.metrics.__dict__,
                "file_optimizer": self.file_optimizer.get_performance_stats(),
            }
            query_metrics = self.query_optimizer.get_performance_report()
            connection_pool_metrics = self.get_connection_pool_status()

            # 生成优化建议
            recommendations = await self._generate_recommendations(
                database_metrics, async_metrics, query_metrics, connection_pool_metrics
            )

            # 计算综合性能分数
            overall_score = self._calculate_performance_score(
                database_metrics, async_metrics, query_metrics, connection_pool_metrics
            )

            return PerformanceReport(
                timestamp=timestamp,
                database_metrics=database_metrics,
                async_metrics=async_metrics,
                query_metrics=query_metrics,
                connection_pool_metrics=connection_pool_metrics,
                recommendations=recommendations,
                overall_score=overall_score,
            )

        except Exception as e:
            logger.error(f"性能报告生成失败: {e}")
            raise

    async def _generate_recommendations(
        self,
        db_metrics: dict,
        async_metrics: dict,
        query_metrics: dict,
        pool_metrics: dict,
    ) -> list[str]:
        """生成性能优化建议"""
        recommendations = []

        # 数据库建议
        if db_metrics.get("queries", {}).get("summary", {}).get("error_rate", 0) > 5:
            recommendations.append("数据库查询错误率过高，建议检查SQL语法和索引")

        slow_queries = db_metrics.get("queries", {}).get("slow_queries_count", 0)
        if slow_queries > 0:
            recommendations.append(
                f"发现 {slow_queries} 个慢查询，建议添加索引或优化SQL"
            )

        # 异步处理建议
        batch_avg_time = async_metrics.get("batch_processor", {}).get("avg_time", 0)
        if batch_avg_time > 1.0:
            recommendations.append(
                "批量处理平均时间过长，建议减少批次大小或优化处理逻辑"
            )

        # 连接池建议
        if pool_metrics.get("status") != "healthy":
            recommendations.append("连接池利用率过高，建议增加连接池大小或优化查询")

        # 通用建议
        if not recommendations:
            recommendations.append("当前性能指标良好，继续保持优化配置")

        return recommendations

    def _calculate_performance_score(
        self,
        db_metrics: dict,
        async_metrics: dict,
        query_metrics: dict,
        pool_metrics: dict,
    ) -> float:
        """计算综合性能分数 (0-100)"""
        scores = []

        # 查询性能分数 (40%)
        query_summary = query_metrics.get("summary", {})
        if query_summary:
            avg_time = query_summary.get("avg_query_time", 0)
            error_rate = query_summary.get("error_rate", 0) / 100

            # 响应时间分数 (0.5秒为满分)
            time_score = max(0, 100 - (avg_time - 0.5) * 100)
            # 错误率分数 (5%为满分)
            error_score = max(0, 100 - error_rate * 2000)

            scores.append((time_score + error_score) / 2 * 0.4)

        # 异步处理分数 (30%)
        batch_metrics = async_metrics.get("batch_processor", {})
        if batch_metrics:
            error_count = batch_metrics.get("errors_count", 0)
            operation_count = batch_metrics.get("operation_count", 1)
            batch_error_rate = error_count / operation_count
            batch_score = max(0, 100 - batch_error_rate * 1000)
            scores.append(batch_score * 0.3)

        # 连接池分数 (30%)
        pool_utilization = pool_metrics.get("pool_stats", {}).get("utilization", 0.7)
        pool_score = max(0, 100 - abs(pool_utilization - 0.7) * 200)
        scores.append(pool_score * 0.3)

        return round(sum(scores), 1) if scores else 70.0

    # ========================================
    # 性能调优操作
    # ========================================

    async def auto_tune_performance(self) -> dict[str, Any]:
        """自动性能调优"""
        try:
            logger.info("开始自动性能调优...")

            # 生成当前性能报告
            report = await self.generate_performance_report()

            tuning_actions = []

            # 根据建议执行调优操作
            for recommendation in report.recommendations:
                if "慢查询" in recommendation:
                    # 清空查询缓存，重新优化
                    self.query_optimizer.clear_cache()
                    tuning_actions.append("清空查询缓存")

                elif "连接池利用率过高" in recommendation:
                    # 增加连接池大小（如果可能）
                    if hasattr(self.connection_pool, "max_size"):
                        self.connection_pool.max_size = min(
                            self.connection_pool.max_size + 5, 50
                        )
                        tuning_actions.append("增加连接池大小")

                elif "批量处理" in recommendation:
                    # 调整批量处理参数
                    if hasattr(self.batch_processor, "batch_size"):
                        self.batch_processor.batch_size = max(
                            self.batch_processor.batch_size - 20, 50
                        )
                        tuning_actions.append("减少批量处理大小")

            logger.info(f"自动调优完成，执行了 {len(tuning_actions)} 个调优操作")

            return {
                "actions_performed": tuning_actions,
                "performance_score_before": report.overall_score,
                "recommendations_applied": report.recommendations,
            }

        except Exception as e:
            logger.error(f"自动性能调优失败: {e}")
            raise

    async def benchmark_performance(self, duration_seconds: int = 60) -> dict[str, Any]:
        """执行性能基准测试"""
        try:
            logger.info(f"开始性能基准测试，持续时间: {duration_seconds}秒")

            start_time = time.time()
            benchmark_data = {
                "queries_executed": 0,
                "total_response_time": 0.0,
                "errors_count": 0,
                "peak_memory_usage": 0.0,
            }

            # 模拟工作负载
            test_queries = [
                {"query": "SELECT 1 as test", "params": None},
                {"query": "SELECT 2 as test", "params": None},
                {"query": "SELECT COUNT(*) FROM (SELECT 1 as dummy) t", "params": None},
            ]

            while time.time() - start_time < duration_seconds:
                query_start = time.time()

                try:
                    # 执行测试查询
                    await self.query_optimizer.execute_optimized_query(
                        test_queries[0]["query"], test_queries[0]["params"]
                    )
                    benchmark_data["queries_executed"] += 1

                except Exception as e:
                    benchmark_data["errors_count"] += 1
                    logger.warning(f"基准测试查询失败: {e}")

                query_time = time.time() - query_start
                benchmark_data["total_response_time"] += query_time

                # 避免过于频繁的查询
                await asyncio.sleep(0.01)

            # 计算基准指标
            actual_duration = time.time() - start_time
            benchmark_results = {
                "duration": actual_duration,
                "queries_per_second": benchmark_data["queries_executed"]
                / actual_duration,
                "avg_response_time": (
                    benchmark_data["total_response_time"]
                    / max(1, benchmark_data["queries_executed"])
                ),
                "error_rate": (
                    benchmark_data["errors_count"]
                    / max(1, benchmark_data["queries_executed"])
                ),
                "total_queries": benchmark_data["queries_executed"],
                "total_errors": benchmark_data["errors_count"],
            }

            logger.info(
                f"性能基准测试完成: {benchmark_results['queries_per_second']:.1f} QPS, "
                f"平均响应时间 {benchmark_results['avg_response_time']:.3f}秒"
            )

            return benchmark_results

        except Exception as e:
            logger.error(f"性能基准测试失败: {e}")
            raise

    # ========================================
    # 清理和维护
    # ========================================

    async def cleanup(self):
        """清理性能服务资源"""
        try:
            # 清空缓存
            self.query_optimizer.clear_cache()

            # 重置指标
            self.batch_processor.metrics = type(self.batch_processor.metrics)()

            logger.info("性能服务资源清理完成")

        except Exception as e:
            logger.error(f"性能服务清理失败: {e}")


# 全局性能服务实例
_global_performance_service: PerformanceService | None = None


def get_performance_service() -> PerformanceService:
    """获取全局性能服务实例"""
    global _global_performance_service
    if _global_performance_service is None:
        _global_performance_service = PerformanceService()
    return _global_performance_service


async def initialize_performance_service():
    """初始化全局性能服务"""
    service = get_performance_service()
    await service.initialize()
    return service


if __name__ == "__main__":

    async def demo_performance_service():
        """演示性能服务功能"""
        print("🚀 演示性能服务功能")

        # 初始化性能服务
        service = await initialize_performance_service()

        # 执行性能基准测试
        benchmark_results = await service.benchmark_performance(duration_seconds=5)
        print(f"📊 基准测试结果: {benchmark_results}")

        # 生成性能报告
        report = await service.generate_performance_report()
        print(f"📈 性能报告: 总体评分 {report.overall_score}")

        # 自动调优
        tuning_results = await service.auto_tune_performance()
        print(f"🔧 自动调优: {tuning_results}")

        # 清理
        await service.cleanup()
        print("✅ 性能服务演示完成")

    asyncio.run(demo_performance_service())
