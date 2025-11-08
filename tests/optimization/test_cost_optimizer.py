#!/usr/bin/env python3
"""
成本优化器测试
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from src.optimization.cost_optimizer import (
    CostBreakdown,
    CostOptimizer,
    OptimizationLevel,
    OptimizationRecommendation,
    ResourceType,
    ResourceUsage,
)


class TestCostOptimizer:
    """成本优化器测试"""

    @pytest.fixture
    def optimizer(self):
        """创建成本优化器实例"""
        config = {
            "monitoring_interval": 60,
            "history_retention_days": 7,
            "optimization_threshold": 0.15,
            "alert_threshold": 0.20,
            "enable_auto_optimization": False,
            "min_savings_threshold": Decimal("5.00"),
        }
        return CostOptimizer(config)

    @pytest.fixture
    def sample_metrics(self):
        """示例资源指标"""
        return {
            ResourceType.CPU: ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=25.0,
                max_capacity=100.0,
                unit="percent",
                timestamp=datetime.now(),
                cost_per_hour=Decimal("0.10"),
            ),
            ResourceType.MEMORY: ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=85.0,
                max_capacity=100.0,
                unit="percent",
                timestamp=datetime.now(),
                cost_per_hour=Decimal("0.05"),
            ),
            ResourceType.DISK: ResourceUsage(
                resource_type=ResourceType.DISK,
                current_usage=500.0,
                max_capacity=1000.0,
                unit="GB",
                timestamp=datetime.now(),
                cost_per_hour=Decimal("0.20"),
            ),
        }

    @pytest.mark.asyncio
    async def test_optimizer_initialization(self, optimizer):
        """测试优化器初始化"""
        assert optimizer.config["monitoring_interval"] == 60
        assert optimizer.config["min_savings_threshold"] == Decimal("5.00")
        assert not optimizer.baseline_established
        assert len(optimizer.optimization_actions) > 0

    @pytest.mark.asyncio
    async def test_collect_cpu_metrics(self, optimizer):
        """测试CPU指标收集"""
        with (
            patch("psutil.cpu_percent", return_value=75.0),
            patch("psutil.cpu_count", return_value=4),
            patch("psutil.getloadavg", return_value=(2.5, 2.8, 3.0)),
        ):

            metrics = await optimizer._collect_cpu_metrics()

            assert len(metrics) >= 2
            assert any(m.name == "cpu_usage_percent" for m in metrics)
            assert any(m.name == "load_average_1m" for m in metrics)

            cpu_metric = next(m for m in metrics if m.name == "cpu_usage_percent")
            assert cpu_metric.current_value == 75.0
            assert cpu_metric.is_warning
            assert not cpu_metric.is_critical

    @pytest.mark.asyncio
    async def test_collect_memory_metrics(self, optimizer):
        """测试内存指标收集"""
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_memory.total = 16 * 1024**3  # 16GB

        mock_swap = Mock()
        mock_swap.percent = 10.0

        with (
            patch("psutil.virtual_memory", return_value=mock_memory),
            patch("psutil.swap_memory", return_value=mock_swap),
        ):

            metrics = await optimizer._collect_memory_metrics()

            assert len(metrics) == 3
            assert any(m.name == "memory_usage_percent" for m in metrics)
            assert any(m.name == "memory_available_gb" for m in metrics)

            memory_metric = next(m for m in metrics if m.name == "memory_usage_percent")
            assert memory_metric.current_value == 60.0
            assert not memory_metric.is_warning

    @pytest.mark.asyncio
    async def test_collect_database_metrics(self, optimizer):
        """测试数据库指标收集"""
        metrics = await optimizer._collect_database_metrics()

        assert len(metrics) == 4
        assert any(m.name == "active_connections" for m in metrics)
        assert any(m.name == "avg_query_time_ms" for m in metrics)
        assert any(m.name == "slow_queries_count" for m in metrics)

        connections_metric = next(m for m in metrics if m.name == "active_connections")
        assert connections_metric.resource_type == ResourceType.DATABASE_CONNECTIONS
        assert connections_metric.current_value == 25

    @pytest.mark.asyncio
    async def test_collect_cache_metrics(self, optimizer):
        """测试缓存指标收集"""
        metrics = await optimizer._collect_cache_metrics()

        assert len(metrics) == 3
        assert any(m.name == "memory_usage_percent" for m in metrics)
        assert any(m.name == "hit_rate_percent" for m in metrics)

        hit_rate_metric = next(m for m in metrics if m.name == "hit_rate_percent")
        assert hit_rate_metric.current_value == 82.0
        assert not hit_rate_metric.is_warning  # 82% > 70% threshold

    @pytest.mark.asyncio
    async def test_calculate_costs(self, optimizer, sample_metrics):
        """测试成本计算"""
        costs = await optimizer.calculate_costs(sample_metrics)

        assert len(costs) == len(sample_metrics)
        assert ResourceType.CPU in costs
        assert ResourceType.MEMORY in costs
        assert ResourceType.DISK in costs

        cpu_cost = costs[ResourceType.CPU]
        assert cpu_cost.hourly_cost == Decimal("0.10")
        assert cpu_cost.daily_cost == Decimal("2.40")
        assert cpu_cost.monthly_cost == Decimal("72.00")
        assert cpu_cost.annual_cost == Decimal("864.00")

    @pytest.mark.asyncio
    async def test_generate_underutilization_recommendations(self, optimizer):
        """测试低利用率优化建议生成"""
        low_usage = ResourceUsage(
            resource_type=ResourceType.CPU,
            current_usage=20.0,  # 低于50%阈值
            max_capacity=100.0,
            unit="percent",
            timestamp=datetime.now(),
            cost_per_hour=Decimal("0.10"),
        )

        recommendations = await optimizer._generate_underutilization_recommendation(
            ResourceType.CPU, low_usage, optimizer.optimization_rules[ResourceType.CPU]
        )

        assert recommendations is not None
        assert recommendations.resource_type == ResourceType.CPU
        assert recommendations.optimization_level == OptimizationLevel.MEDIUM
        assert "缩减" in recommendations.recommended_action
        assert recommendations.potential_savings > 0

    @pytest.mark.asyncio
    async def test_generate_overutilization_recommendations(self, optimizer):
        """测试过载优化建议生成"""
        high_usage = ResourceUsage(
            resource_type=ResourceType.CPU,
            current_usage=95.0,  # 高于90%阈值
            max_capacity=100.0,
            unit="percent",
            timestamp=datetime.now(),
            cost_per_hour=Decimal("0.10"),
        )

        recommendations = await optimizer._generate_overutilization_recommendation(
            ResourceType.CPU, high_usage, optimizer.optimization_rules[ResourceType.CPU]
        )

        assert recommendations is not None
        assert recommendations.resource_type == ResourceType.CPU
        assert recommendations.optimization_level == OptimizationLevel.HIGH
        assert (
            "增加" in recommendations.recommended_action
            or "优化" in recommendations.recommended_action
        )
        assert recommendations.risk_level in ["low", "medium"]

    @pytest.mark.asyncio
    async def test_generate_database_recommendations(self, optimizer):
        """测试数据库优化建议生成"""
        low_connection_usage = ResourceUsage(
            resource_type=ResourceType.DATABASE_CONNECTIONS,
            current_usage=30.0,  # 30%使用率
            max_capacity=100.0,
            unit="connections",
            timestamp=datetime.now(),
            cost_per_hour=Decimal("0.20"),
        )

        recommendations = await optimizer._generate_database_recommendation(
            low_connection_usage, optimizer.optimization_rules[ResourceType.DATABASE]
        )

        if recommendations:  # 只有在使用率过低时才生成建议
            assert recommendations.resource_type == ResourceType.DATABASE_CONNECTIONS
            assert "连接池" in recommendations.recommended_action

    @pytest.mark.asyncio
    async def test_generate_cache_recommendations(self, optimizer):
        """测试缓存优化建议生成"""
        low_hit_rate_usage = ResourceUsage(
            resource_type=ResourceType.CACHE,
            current_usage=1.5,  # GB
            max_capacity=4.0,
            unit="GB",
            timestamp=datetime.now(),
            cost_per_hour=Decimal("0.06"),
        )

        # 模拟低命中率
        with patch.object(optimizer, "_generate_cache_recommendation") as mock_gen:
            mock_gen.return_value = OptimizationRecommendation(
                resource_type=ResourceType.CACHE,
                current_usage=low_hit_rate_usage,
                recommended_action="优化缓存策略",
                potential_savings=Decimal("15.00"),
                optimization_level=OptimizationLevel.HIGH,
                implementation_effort="medium",
                risk_level="low",
                description="缓存命中率过低",
                steps=["分析缓存键分布", "调整缓存策略"],
            )

            recommendations = await optimizer._generate_cache_recommendation(
                low_hit_rate_usage, optimizer.optimization_rules[ResourceType.CACHE]
            )

            assert recommendations is not None
            assert recommendations.resource_type == ResourceType.CACHE
            assert "缓存" in recommendations.recommended_action

    @pytest.mark.asyncio
    async def test_generate_cost_report(self, optimizer, sample_metrics):
        """测试成本报告生成"""
        costs = await optimizer.calculate_costs(sample_metrics)
        recommendations = await optimizer.generate_optimization_recommendations(
            sample_metrics
        )

        report = await optimizer.generate_cost_report(
            sample_metrics, costs, recommendations
        )

        assert "timestamp" in report
        assert "summary" in report
        assert "resource_costs" in report
        assert "recommendations" in report

        summary = report["summary"]
        assert "total_monthly_cost" in summary
        assert "total_potential_savings" in summary
        assert "optimization_rate" in summary

        assert summary["total_resources_monitored"] == len(sample_metrics)

        if recommendations:
            assert len(report["recommendations"]) == len(recommendations)

    @pytest.mark.asyncio
    async def test_auto_optimize_resources(self, optimizer):
        """测试自动资源优化"""
        # 创建测试建议
        test_recommendations = [
            OptimizationRecommendation(
                resource_type=ResourceType.CPU,
                current_usage=ResourceUsage(
                    resource_type=ResourceType.CPU,
                    current_usage=20.0,
                    max_capacity=100.0,
                    unit="percent",
                    timestamp=datetime.now(),
                    cost_per_hour=Decimal("0.10"),
                ),
                recommended_action="缩减vCPU数量",
                potential_savings=Decimal("20.00"),
                optimization_level=OptimizationLevel.HIGH,
                implementation_effort="medium",
                risk_level="low",
                description="CPU使用率过低",
                steps=["分析使用模式", "调整配置"],
            )
        ]

        # 测试dry run模式
        results = await optimizer.auto_optimize_resources(
            test_recommendations, dry_run=True
        )

        assert "total_recommendations" in results
        assert "processed" in results
        assert "successful" in results
        assert "applied_optimizations" in results

        assert results["total_recommendations"] == 1
        assert results["processed"] == 1
        assert results["successful"] == 1
        assert len(results["applied_optimizations"]) == 1

        applied_opt = results["applied_optimizations"][0]
        assert applied_opt["status"] == "dry_run_success"
        assert applied_opt["potential_savings"] == 20.00

    @pytest.mark.asyncio
    async def test_execute_optimization_cpu(self, optimizer):
        """测试CPU优化执行"""
        recommendation = OptimizationRecommendation(
            resource_type=ResourceType.CPU,
            current_usage=ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=95.0,
                max_capacity=100.0,
                unit="percent",
                timestamp=datetime.now(),
                cost_per_hour=Decimal("0.10"),
            ),
            recommended_action="增加vCPU数量",
            potential_savings=Decimal("0.00"),
            optimization_level=OptimizationLevel.HIGH,
            implementation_effort="high",
            risk_level="medium",
            description="CPU使用率过高",
            steps=["增加vCPU", "监控性能"],
        )

        with patch.object(
            optimizer, "_optimize_cpu_resources", return_value=True
        ) as mock_optimize:
            result = await optimizer._execute_optimization(recommendation)
            assert result is True
            mock_optimize.assert_called_once_with(recommendation)

    @pytest.mark.asyncio
    async def test_execute_optimization_memory(self, optimizer):
        """测试内存优化执行"""
        recommendation = OptimizationRecommendation(
            resource_type=ResourceType.MEMORY,
            current_usage=ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=90.0,
                max_capacity=100.0,
                unit="percent",
                timestamp=datetime.now(),
                cost_per_hour=Decimal("0.05"),
            ),
            recommended_action="增加内存资源",
            potential_savings=Decimal("0.00"),
            optimization_level=OptimizationLevel.HIGH,
            implementation_effort="high",
            risk_level="medium",
            description="内存使用率过高",
            steps=["增加内存", "优化内存使用"],
        )

        with patch.object(
            optimizer, "_optimize_memory_resources", return_value=True
        ) as mock_optimize:
            result = await optimizer._execute_optimization(recommendation)
            assert result is True
            mock_optimize.assert_called_once_with(recommendation)

    @pytest.mark.asyncio
    async def test_optimization_statistics(self, optimizer):
        """测试优化统计信息"""
        # 模拟一些历史数据
        optimizer.cost_history = [
            {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_resources_monitored": 5,
                    "optimized_resources": 3,
                    "total_monthly_cost": 500.0,
                    "total_potential_savings": 75.0,
                },
                "recommendations": [],
            }
        ]

        stats = optimizer.get_optimization_statistics()

        assert "report_timestamp" in stats
        assert "total_resources" in stats
        assert "optimization_rate" in stats
        assert "savings_opportunity" in stats

        assert stats["total_resources"] == 5
        assert stats["optimization_rate"] == 60.0  # 3/5 * 100

    def test_cost_trends_insufficient_data(self, optimizer):
        """测试成本趋势（数据不足）"""
        trends = optimizer._get_cost_trends()
        assert trends["trend"] == "insufficient_data"
        assert trends["change_percentage"] == 0

    def test_cost_trends_with_data(self, optimizer):
        """测试成本趋势（有数据）"""
        # 创建历史数据
        now = datetime.now()
        optimizer.cost_history = [
            {
                "timestamp": (now - timedelta(hours=3)).isoformat(),
                "summary": {"total_monthly_cost": 400.0},
            },
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "summary": {"total_monthly_cost": 450.0},
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "summary": {"total_monthly_cost": 500.0},
            },
        ]

        trends = optimizer._get_cost_trends()
        assert trends["trend"] == "increasing"
        assert trends["change_percentage"] == 25.0  # (500-400)/400 * 100
        assert trends["data_points"] == 3

    @pytest.mark.asyncio
    async def test_check_cost_alerts(self, optimizer):
        """测试成本告警检查"""
        # 创建高成本报告
        high_cost_report = {
            "summary": {"total_monthly_cost": 1000.0, "optimization_rate": 30.0}
        }

        # 添加历史基准数据
        optimizer.cost_history = [{"summary": {"total_monthly_cost": 500.0}}]

        with patch.object(optimizer, "_send_cost_alert") as mock_alert:
            await optimizer._check_cost_alerts(high_cost_report)
            mock_alert.assert_called()

            # 检查告警参数
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "cost_increase"
            assert call_args["current_cost"] == 1000.0
            assert call_args["historical_average"] == 500.0

    @pytest.mark.asyncio
    async def test_collect_all_metrics(self, optimizer):
        """测试收集所有指标"""
        with (
            patch.object(optimizer, "_collect_cpu_metrics", return_value=[]),
            patch.object(optimizer, "_collect_memory_metrics", return_value=[]),
            patch.object(optimizer, "_collect_disk_io_metrics", return_value=[]),
            patch.object(optimizer, "_collect_network_metrics", return_value=[]),
            patch.object(optimizer, "_collect_database_metrics", return_value=[]),
            patch.object(optimizer, "_collect_cache_metrics", return_value=[]),
            patch.object(optimizer, "_collect_api_metrics", return_value=[]),
            patch.object(
                optimizer, "_collect_background_task_metrics", return_value=[]
            ),
        ):

            metrics = await optimizer._collect_all_metrics()
            assert isinstance(metrics, list)

    @pytest.mark.asyncio
    async def test_integration_workflow(self, optimizer):
        """测试完整集成工作流"""
        # 模拟完整的成本优化工作流
        with (
            patch.object(optimizer, "collect_resource_metrics") as mock_collect,
            patch.object(optimizer, "calculate_costs") as mock_costs,
            patch.object(
                optimizer, "generate_optimization_recommendations"
            ) as mock_recommendations,
            patch.object(optimizer, "generate_cost_report") as mock_report,
        ):

            # 设置模拟返回值
            mock_metrics = {
                ResourceType.CPU: ResourceUsage(
                    resource_type=ResourceType.CPU,
                    current_usage=80.0,
                    max_capacity=100.0,
                    unit="percent",
                    timestamp=datetime.now(),
                    cost_per_hour=Decimal("0.10"),
                )
            }
            mock_collect.return_value = mock_metrics

            mock_costs.return_value = {
                ResourceType.CPU: CostBreakdown(
                    resource_type=ResourceType.CPU,
                    hourly_cost=Decimal("0.10"),
                    daily_cost=Decimal("2.40"),
                    monthly_cost=Decimal("72.00"),
                    annual_cost=Decimal("864.00"),
                )
            }

            mock_recommendations.return_value = []
            mock_report.return_value = {
                "timestamp": datetime.now().isoformat(),
                "summary": {"total_monthly_cost": 72.00},
            }

            # 执行工作流
            metrics = await optimizer.collect_resource_metrics()
            costs = await optimizer.calculate_costs(metrics)
            recommendations = await optimizer.generate_optimization_recommendations(
                metrics
            )
            report = await optimizer.generate_cost_report(
                metrics, costs, recommendations
            )

            # 验证结果
            assert len(metrics) == 1
            assert ResourceType.CPU in costs
            assert isinstance(recommendations, list)
            assert "summary" in report

            # 验证模拟调用
            mock_collect.assert_called_once()
            mock_costs.assert_called_once_with(metrics)
            mock_recommendations.assert_called_once_with(metrics)
            mock_report.assert_called_once_with(metrics, costs, recommendations)


if __name__ == "__main__":
    pytest.main([__file__])
