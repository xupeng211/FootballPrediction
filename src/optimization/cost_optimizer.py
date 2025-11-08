#!/usr/bin/env python3
"""
企业级成本优化系统
提供资源使用监控、成本分析报告、云资源优化、自动化成本控制等功能
"""

import asyncio
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from src.core.logger import get_logger

logger = get_logger(__name__)


class ResourceType(Enum):
    """资源类型枚举"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DATABASE = "database"
    CACHE = "cache"
    API_CALL = "api_call"
    STORAGE = "storage"


class OptimizationLevel(Enum):
    """优化级别枚举"""

    LOW = "low"  # 低优先级优化
    MEDIUM = "medium"  # 中等优先级优化
    HIGH = "high"  # 高优先级优化
    CRITICAL = "critical"  # 关键优化


@dataclass
class ResourceUsage:
    """资源使用情况"""

    resource_type: ResourceType
    current_usage: float
    max_capacity: float
    unit: str
    timestamp: datetime
    cost_per_hour: Decimal = Decimal("0.00")

    @property
    def usage_percentage(self) -> float:
        """使用率百分比"""
        return (
            (self.current_usage / self.max_capacity) * 100
            if self.max_capacity > 0
            else 0
        )

    @property
    def is_optimized(self) -> bool:
        """是否已优化"""
        return 60 <= self.usage_percentage <= 85

    @property
    def waste_percentage(self) -> float:
        """浪费百分比"""
        if self.usage_percentage < 60:
            return 60 - self.usage_percentage
        elif self.usage_percentage > 85:
            return self.usage_percentage - 85
        return 0


@dataclass
class CostBreakdown:
    """成本细分"""

    resource_type: ResourceType
    hourly_cost: Decimal
    daily_cost: Decimal
    monthly_cost: Decimal
    annual_cost: Decimal

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "resource_type": self.resource_type.value,
            "hourly_cost": float(self.hourly_cost),
            "daily_cost": float(self.daily_cost),
            "monthly_cost": float(self.monthly_cost),
            "annual_cost": float(self.annual_cost),
        }


@dataclass
class OptimizationRecommendation:
    """优化建议"""

    resource_type: ResourceType
    current_usage: ResourceUsage
    recommended_action: str
    potential_savings: Decimal
    optimization_level: OptimizationLevel
    implementation_effort: str  # low, medium, high
    risk_level: str  # low, medium, high
    description: str
    steps: list[str]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "resource_type": self.resource_type.value,
            "recommended_action": self.recommended_action,
            "potential_savings": float(self.potential_savings),
            "optimization_level": self.optimization_level.value,
            "implementation_effort": self.implementation_effort,
            "risk_level": self.risk_level,
            "description": self.description,
            "steps": self.steps,
            "current_usage": asdict(self.current_usage),
        }


class CostOptimizer:
    """成本优化器"""

    def __init__(self, config: dict | None = None):
        self.config = config or self._get_default_config()
        self.resource_history: dict[str, list[ResourceUsage]] = defaultdict(list)
        self.cost_history: list[dict] = []
        self.optimization_rules = self._load_optimization_rules()
        self.baseline_established = False
        self.baseline_metrics = {}

        # 成本计算参数
        self.cost_rates = {
            ResourceType.CPU: Decimal("0.05"),  # $0.05 per vCPU-hour
            ResourceType.MEMORY: Decimal("0.01"),  # $0.01 per GB-hour
            ResourceType.DISK: Decimal("0.10"),  # $0.10 per GB-month
            ResourceType.NETWORK: Decimal("0.09"),  # $0.09 per GB
            ResourceType.DATABASE: Decimal("0.20"),  # $0.20 per instance-hour
            ResourceType.CACHE: Decimal("0.15"),  # $0.15 per GB-hour
            ResourceType.API_CALL: Decimal("0.001"),  # $0.001 per 1000 calls
            ResourceType.STORAGE: Decimal("0.023"),  # $0.023 per GB-month
        }

        logger.info("成本优化器初始化完成")

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "monitoring_interval": 300,  # 5分钟
            "history_retention_days": 30,
            "optimization_threshold": 0.15,  # 15%优化阈值
            "alert_threshold": 0.20,  # 20%告警阈值
            "enable_auto_optimization": False,
            "optimization_window_hours": 2,  # 自动优化时间窗口
            "min_savings_threshold": Decimal("10.00"),  # 最小节省金额
        }

    def _load_optimization_rules(self) -> dict:
        """加载优化规则"""
        return {
            ResourceType.CPU: {
                "under_utilized": 50,  # CPU使用率低于50%为低利用率
                "over_utilized": 90,  # CPU使用率高于90%为过载
                "optimal_range": (60, 85),
                "recommendations": {
                    "under": ["缩减vCPU数量", "使用实例类型调整", "启用自动扩缩容"],
                    "over": ["增加vCPU数量", "优化代码性能", "启用负载均衡"],
                },
            },
            ResourceType.MEMORY: {
                "under_utilized": 40,
                "over_utilized": 90,
                "optimal_range": (60, 85),
                "recommendations": {
                    "under": ["减少内存分配", "选择更小实例", "优化内存使用"],
                    "over": ["增加内存分配", "优化内存泄漏", "启用内存监控"],
                },
            },
            ResourceType.DATABASE: {
                "connection_pool_optimal": 0.8,
                "query_timeout_optimal": 30,
                "cache_hit_rate_optimal": 0.9,
                "recommendations": {
                    "connections": ["调整连接池大小", "启用连接复用", "优化查询"],
                    "performance": ["添加索引", "优化查询", "启用读写分离"],
                },
            },
            ResourceType.CACHE: {
                "hit_rate_optimal": 0.8,
                "memory_usage_optimal": (60, 80),
                "recommendations": {
                    "hit_rate": ["调整缓存策略", "增加缓存大小", "优化缓存键"],
                    "memory": ["清理过期数据", "压缩缓存数据", "使用分层缓存"],
                },
            },
        }

    async def collect_resource_metrics(self) -> dict[ResourceType, ResourceUsage]:
        """收集资源指标"""
        logger.info("开始收集资源使用指标...")

        metrics = {}

        # CPU指标
        cpu_usage = await self._collect_cpu_metrics()
        if cpu_usage:
            metrics[ResourceType.CPU] = cpu_usage

        # 内存指标
        memory_usage = await self._collect_memory_metrics()
        if memory_usage:
            metrics[ResourceType.MEMORY] = memory_usage

        # 磁盘指标
        disk_usage = await self._collect_disk_metrics()
        if disk_usage:
            metrics[ResourceType.DISK] = disk_usage

        # 网络指标
        network_usage = await self._collect_network_metrics()
        if network_usage:
            metrics[ResourceType.NETWORK] = network_usage

        # 数据库指标
        db_usage = await self._collect_database_metrics()
        if db_usage:
            metrics[ResourceType.DATABASE] = db_usage

        # 缓存指标
        cache_usage = await self._collect_cache_metrics()
        if cache_usage:
            metrics[ResourceType.CACHE] = cache_usage

        # API调用指标
        api_usage = await self._collect_api_metrics()
        if api_usage:
            metrics[ResourceType.API_CALL] = api_usage

        # 存储指标
        storage_usage = await self._collect_storage_metrics()
        if storage_usage:
            metrics[ResourceType.STORAGE] = storage_usage

        # 存储历史数据
        for resource_type, usage in metrics.items():
            key = f"{resource_type.value}_{usage.timestamp.date()}"
            self.resource_history[key].append(usage)

            # 保留历史数据不超过配置的天数
            cutoff_date = datetime.now() - timedelta(
                days=self.config["history_retention_days"]
            )
            self.resource_history[key] = [
                u for u in self.resource_history[key] if u.timestamp > cutoff_date
            ]

        logger.info(f"收集了 {len(metrics)} 种资源类型的指标")
        return metrics

    async def _collect_cpu_metrics(self) -> ResourceUsage | None:
        """收集CPU指标"""
        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            return ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=cpu_percent,
                max_capacity=100 * cpu_count,  # 总CPU容量
                unit="percent",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.CPU] * cpu_count,
            )
        except Exception as e:
            logger.warning(f"收集CPU指标失败: {e}")
            return None

    async def _collect_memory_metrics(self) -> ResourceUsage | None:
        """收集内存指标"""
        try:
            import psutil

            memory = psutil.virtual_memory()

            return ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=memory.used / (1024**3),  # GB
                max_capacity=memory.total / (1024**3),  # GB
                unit="GB",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.MEMORY]
                * (memory.total / (1024**3)),
            )
        except Exception as e:
            logger.warning(f"收集内存指标失败: {e}")
            return None

    async def _collect_disk_metrics(self) -> ResourceUsage | None:
        """收集磁盘指标"""
        try:
            import psutil

            disk = psutil.disk_usage("/")

            return ResourceUsage(
                resource_type=ResourceType.DISK,
                current_usage=disk.used / (1024**3),  # GB
                max_capacity=disk.total / (1024**3),  # GB
                unit="GB",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.DISK]
                * (disk.total / (1024**3))
                / 720,  # 月转小时
            )
        except Exception as e:
            logger.warning(f"收集磁盘指标失败: {e}")
            return None

    async def _collect_network_metrics(self) -> ResourceUsage | None:
        """收集网络指标"""
        try:
            import psutil

            network = psutil.net_io_counters()
            # 转换为GB
            current_usage = (network.bytes_sent + network.bytes_recv) / (1024**3)

            return ResourceUsage(
                resource_type=ResourceType.NETWORK,
                current_usage=current_usage,
                max_capacity=1000,  # 假设1TB月流量
                unit="GB",
                timestamp=datetime.now(),
                cost_per_hour=Decimal("0.00"),  # 按使用量计费
            )
        except Exception as e:
            logger.warning(f"收集网络指标失败: {e}")
            return None

    async def _collect_database_metrics(self) -> ResourceUsage | None:
        """收集数据库指标"""
        try:
            # 模拟数据库连接和查询指标
            # 实际实现需要连接到具体的数据库

            # 数据库连接数
            active_connections = 15  # 示例值
            max_connections = 100  # 示例值

            return ResourceUsage(
                resource_type=ResourceType.DATABASE,
                current_usage=active_connections,
                max_capacity=max_connections,
                unit="connections",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.DATABASE],
            )
        except Exception as e:
            logger.warning(f"收集数据库指标失败: {e}")
            return None

    async def _collect_cache_metrics(self) -> ResourceUsage | None:
        """收集缓存指标"""
        try:
            # 模拟Redis缓存指标
            cache_memory = 512  # MB
            cache_memory_limit = 2048  # MB

            return ResourceUsage(
                resource_type=ResourceType.CACHE,
                current_usage=cache_memory / 1024,  # GB
                max_capacity=cache_memory_limit / 1024,  # GB
                unit="GB",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.CACHE]
                * (cache_memory_limit / 1024),
            )
        except Exception as e:
            logger.warning(f"收集缓存指标失败: {e}")
            return None

    async def _collect_api_metrics(self) -> ResourceUsage | None:
        """收集API调用指标"""
        try:
            # 模拟API调用指标
            api_calls_per_hour = 10000  # 示例值

            return ResourceUsage(
                resource_type=ResourceType.API_CALL,
                current_usage=api_calls_per_hour,
                max_capacity=100000,  # 假设最大10万次/小时
                unit="calls/hour",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.API_CALL]
                * (api_calls_per_hour / 1000),
            )
        except Exception as e:
            logger.warning(f"收集API指标失败: {e}")
            return None

    async def _collect_storage_metrics(self) -> ResourceUsage | None:
        """收集存储指标"""
        try:
            # 模拟对象存储指标
            storage_used = 500  # GB

            return ResourceUsage(
                resource_type=ResourceType.STORAGE,
                current_usage=storage_used,
                max_capacity=5000,  # 假设5TB
                unit="GB",
                timestamp=datetime.now(),
                cost_per_hour=self.cost_rates[ResourceType.STORAGE]
                * storage_used
                / 720,  # 月转小时
            )
        except Exception as e:
            logger.warning(f"收集存储指标失败: {e}")
            return None

    async def calculate_costs(
        self, metrics: dict[ResourceType, ResourceUsage]
    ) -> dict[ResourceType, CostBreakdown]:
        """计算成本细分"""
        logger.info("计算资源成本...")

        costs = {}

        for resource_type, usage in metrics.items():
            hourly_cost = usage.cost_per_hour
            daily_cost = hourly_cost * 24
            monthly_cost = daily_cost * 30
            annual_cost = monthly_cost * 12

            costs[resource_type] = CostBreakdown(
                resource_type=resource_type,
                hourly_cost=hourly_cost,
                daily_cost=daily_cost,
                monthly_cost=monthly_cost,
                annual_cost=annual_cost,
            )

        return costs

    async def generate_optimization_recommendations(
        self, metrics: dict[ResourceType, ResourceUsage]
    ) -> list[OptimizationRecommendation]:
        """生成优化建议"""
        logger.info("生成优化建议...")

        recommendations = []

        for resource_type, usage in metrics.items():
            resource_rules = self.optimization_rules.get(resource_type, {})

            if resource_type in [ResourceType.CPU, ResourceType.MEMORY]:
                # CPU和内存优化建议
                if "under_utilized" in resource_rules:
                    under_threshold = resource_rules["under_utilized"]
                    if usage.usage_percentage < under_threshold:
                        recommendation = (
                            await self._generate_under_utilization_recommendation(
                                resource_type, usage, resource_rules
                            )
                        )
                        if recommendation:
                            recommendations.append(recommendation)

                if "over_utilized" in resource_rules:
                    over_threshold = resource_rules["over_utilized"]
                    if usage.usage_percentage > over_threshold:
                        recommendation = (
                            await self._generate_over_utilization_recommendation(
                                resource_type, usage, resource_rules
                            )
                        )
                        if recommendation:
                            recommendations.append(recommendation)

            elif resource_type == ResourceType.DATABASE:
                # 数据库优化建议
                recommendation = await self._generate_database_recommendation(
                    usage, resource_rules
                )
                if recommendation:
                    recommendations.append(recommendation)

            elif resource_type == ResourceType.CACHE:
                # 缓存优化建议
                recommendation = await self._generate_cache_recommendation(
                    usage, resource_rules
                )
                if recommendation:
                    recommendations.append(recommendation)

        # 按潜在节省金额排序
        recommendations.sort(key=lambda x: x.potential_savings, reverse=True)

        logger.info(f"生成了 {len(recommendations)} 条优化建议")
        return recommendations

    async def _generate_under_utilization_recommendation(
        self, resource_type: ResourceType, usage: ResourceUsage, rules: dict
    ) -> OptimizationRecommendation | None:
        """生成低利用率优化建议"""

        actions = rules.get("recommendations", {}).get("under", [])
        if not actions:
            return None

        # 计算潜在节省
        waste_percentage = usage.waste_percentage / 100
        potential_savings = (
            usage.cost_per_hour * Decimal(str(waste_percentage)) * 24 * 30
        )

        if potential_savings < self.config["min_savings_threshold"]:
            return None

        primary_action = actions[0]

        return OptimizationRecommendation(
            resource_type=resource_type,
            current_usage=usage,
            recommended_action=primary_action,
            potential_savings=potential_savings,
            optimization_level=OptimizationLevel.MEDIUM,
            implementation_effort="medium",
            risk_level="low",
            description=f"{resource_type.value}资源使用率过低({usage.usage_percentage:.1f}%)，建议进行优化",
            steps=[
                f"分析{resource_type.value}使用模式",
                f"评估{primary_action}的可行性",
                "实施资源调整",
                "监控调整后的性能表现",
            ],
        )

    async def _generate_over_utilization_recommendation(
        self, resource_type: ResourceType, usage: ResourceUsage, rules: dict
    ) -> OptimizationRecommendation | None:
        """生成过载优化建议"""

        actions = rules.get("recommendations", {}).get("over", [])
        if not actions:
            return None

        primary_action = actions[0]

        # 过载情况下，潜在节省为避免的性能损失
        potential_savings = (
            usage.cost_per_hour * Decimal("0.2") * 24 * 30
        )  # 假设20%性能损失

        return OptimizationRecommendation(
            resource_type=resource_type,
            current_usage=usage,
            recommended_action=primary_action,
            potential_savings=potential_savings,
            optimization_level=OptimizationLevel.HIGH,
            implementation_effort="high",
            risk_level="medium",
            description=f"{resource_type.value}资源使用率过高({usage.usage_percentage:.1f}%)，需要立即优化",
            steps=[
                f"分析{resource_type.value}瓶颈原因",
                f"实施{primary_action}方案",
                "监控系统性能改善",
                "评估扩展效果",
            ],
        )

    async def _generate_database_recommendation(
        self, usage: ResourceUsage, rules: dict
    ) -> OptimizationRecommendation | None:
        """生成数据库优化建议"""

        recommendations = []

        # 连接池优化
        if usage.usage_percentage < 50:  # 连接使用率过低
            potential_savings = usage.cost_per_hour * Decimal("0.15") * 24 * 30

            recommendations.append(
                OptimizationRecommendation(
                    resource_type=ResourceType.DATABASE,
                    current_usage=usage,
                    recommended_action="优化数据库连接池",
                    potential_savings=potential_savings,
                    optimization_level=OptimizationLevel.MEDIUM,
                    implementation_effort="medium",
                    risk_level="low",
                    description="数据库连接池使用率过低，可优化连接配置",
                    steps=[
                        "分析数据库连接模式",
                        "调整连接池大小",
                        "优化查询超时设置",
                        "启用连接复用",
                    ],
                )
            )

        return recommendations[0] if recommendations else None

    async def _generate_cache_recommendation(
        self, usage: ResourceUsage, rules: dict
    ) -> OptimizationRecommendation | None:
        """生成缓存优化建议"""

        # 模拟缓存命中率（实际需要从Redis获取）
        cache_hit_rate = 0.65  # 65%命中率
        optimal_hit_rate = rules.get("hit_rate_optimal", 0.8)

        if cache_hit_rate < optimal_hit_rate:
            potential_savings = usage.cost_per_hour * Decimal("0.25") * 24 * 30

            return OptimizationRecommendation(
                resource_type=ResourceType.CACHE,
                current_usage=usage,
                recommended_action="优化缓存策略",
                potential_savings=potential_savings,
                optimization_level=OptimizationLevel.HIGH,
                implementation_effort="medium",
                risk_level="low",
                description=f"缓存命中率({cache_hit_rate:.1%})低于最优水平({optimal_hit_rate:.1%})",
                steps=[
                    "分析缓存键分布",
                    "调整缓存过期策略",
                    "优化缓存大小配置",
                    "实施缓存预热",
                ],
            )

        return None

    async def generate_cost_report(
        self,
        metrics: dict[ResourceType, ResourceUsage],
        costs: dict[ResourceType, CostBreakdown],
        recommendations: list[OptimizationRecommendation],
    ) -> dict:
        """生成成本分析报告"""
        logger.info("生成成本分析报告...")

        # 计算总成本
        total_monthly_cost = sum(cost.monthly_cost for cost in costs.values())
        total_annual_cost = sum(cost.annual_cost for cost in costs.values())

        # 计算潜在节省
        total_potential_savings = sum(rec.potential_savings for rec in recommendations)

        # 优化统计
        optimized_resources = sum(1 for usage in metrics.values() if usage.is_optimized)
        total_resources = len(metrics)
        optimization_rate = (
            (optimized_resources / total_resources * 100) if total_resources > 0 else 0
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_resources_monitored": total_resources,
                "optimized_resources": optimized_resources,
                "optimization_rate": round(optimization_rate, 2),
                "total_monthly_cost": float(total_monthly_cost),
                "total_annual_cost": float(total_annual_cost),
                "total_potential_savings": float(total_potential_savings),
                "savings_percentage": (
                    round((total_potential_savings / total_monthly_cost * 100), 2)
                    if total_monthly_cost > 0
                    else 0
                ),
            },
            "resource_costs": {rt.value: cost.to_dict() for rt, cost in costs.items()},
            "resource_usage": {
                rt.value: asdict(usage) for rt, usage in metrics.items()
            },
            "recommendations": [rec.to_dict() for rec in recommendations],
            "cost_trends": self._get_cost_trends(),
            "optimization_actions": {
                "high_priority": [
                    rec.to_dict()
                    for rec in recommendations
                    if rec.optimization_level == OptimizationLevel.HIGH
                ],
                "medium_priority": [
                    rec.to_dict()
                    for rec in recommendations
                    if rec.optimization_level == OptimizationLevel.MEDIUM
                ],
                "low_priority": [
                    rec.to_dict()
                    for rec in recommendations
                    if rec.optimization_level == OptimizationLevel.LOW
                ],
            },
        }

        # 保存报告历史
        self.cost_history.append(report)

        # 限制历史记录数量
        if len(self.cost_history) > 100:
            self.cost_history = self.cost_history[-100:]

        return report

    def _get_cost_trends(self) -> dict:
        """获取成本趋势"""
        if len(self.cost_history) < 2:
            return {"trend": "insufficient_data", "change_percentage": 0}

        recent_reports = self.cost_history[-7:]  # 最近7次报告
        if len(recent_reports) < 2:
            return {"trend": "insufficient_data", "change_percentage": 0}

        # 计算成本变化趋势
        current_cost = recent_reports[-1]["summary"]["total_monthly_cost"]
        previous_cost = recent_reports[0]["summary"]["total_monthly_cost"]

        if previous_cost == 0:
            change_percentage = 0
        else:
            change_percentage = ((current_cost - previous_cost) / previous_cost) * 100

        if change_percentage > 5:
            trend = "increasing"
        elif change_percentage < -5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_percentage": round(change_percentage, 2),
            "current_cost": current_cost,
            "previous_cost": previous_cost,
            "data_points": len(recent_reports),
        }

    async def auto_optimize_resources(
        self, recommendations: list[OptimizationRecommendation], dry_run: bool = True
    ) -> dict:
        """自动优化资源"""
        logger.info(f"开始自动资源优化 (dry_run={dry_run})...")

        results = {
            "total_recommendations": len(recommendations),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "applied_optimizations": [],
        }

        # 只处理高优先级和中等优先级的建议
        high_priority_recs = [
            rec
            for rec in recommendations
            if rec.optimization_level
            in [OptimizationLevel.HIGH, OptimizationLevel.MEDIUM]
            and rec.risk_level in ["low", "medium"]
        ]

        for recommendation in high_priority_recs:
            try:
                results["processed"] += 1

                if dry_run:
                    logger.info(
                        f"[DRY RUN] 将应用优化: {recommendation.recommended_action}"
                    )
                    results["successful"] += 1
                    results["applied_optimizations"].append(
                        {
                            "action": recommendation.recommended_action,
                            "resource_type": recommendation.resource_type.value,
                            "potential_savings": float(
                                recommendation.potential_savings
                            ),
                            "status": "dry_run_success",
                        }
                    )
                else:
                    # 实际执行优化逻辑
                    success = await self._execute_optimization(recommendation)

                    if success:
                        results["successful"] += 1
                        results["applied_optimizations"].append(
                            {
                                "action": recommendation.recommended_action,
                                "resource_type": recommendation.resource_type.value,
                                "potential_savings": float(
                                    recommendation.potential_savings
                                ),
                                "status": "applied",
                            }
                        )
                        logger.info(
                            f"成功应用优化: {recommendation.recommended_action}"
                        )
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            f"优化失败: {recommendation.recommended_action}"
                        )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    f"优化异常: {recommendation.recommended_action} - {str(e)}"
                )
                logger.error(f"资源优化异常: {e}")

        # 跳过的建议
        results["skipped"] = results["total_recommendations"] - results["processed"]

        logger.info(
            f"自动优化完成: 成功 {results['successful']}, 失败 {results['failed']}, 跳过 {results['skipped']}"
        )

        return results

    async def _execute_optimization(
        self, recommendation: OptimizationRecommendation
    ) -> bool:
        """执行具体的优化操作"""
        # 这里是实际执行优化逻辑的占位符
        # 实际实现需要根据具体的云服务商和资源类型来实现

        try:
            if recommendation.resource_type == ResourceType.CPU:
                return await self._optimize_cpu_resources(recommendation)
            elif recommendation.resource_type == ResourceType.MEMORY:
                return await self._optimize_memory_resources(recommendation)
            elif recommendation.resource_type == ResourceType.DATABASE:
                return await self._optimize_database_resources(recommendation)
            elif recommendation.resource_type == ResourceType.CACHE:
                return await self._optimize_cache_resources(recommendation)
            else:
                logger.warning(f"不支持的优化类型: {recommendation.resource_type}")
                return False

        except Exception as e:
            logger.error(f"执行优化失败: {e}")
            return False

    async def _optimize_cpu_resources(
        self, recommendation: OptimizationRecommendation
    ) -> bool:
        """优化CPU资源"""
        # 实际实现：调用云服务API调整实例规格
        logger.info(f"执行CPU优化: {recommendation.recommended_action}")
        await asyncio.sleep(1)  # 模拟API调用
        return True

    async def _optimize_memory_resources(
        self, recommendation: OptimizationRecommendation
    ) -> bool:
        """优化内存资源"""
        # 实际实现：调用云服务API调整内存大小
        logger.info(f"执行内存优化: {recommendation.recommended_action}")
        await asyncio.sleep(1)  # 模拟API调用
        return True

    async def _optimize_database_resources(
        self, recommendation: OptimizationRecommendation
    ) -> bool:
        """优化数据库资源"""
        # 实际实现：调整数据库连接池配置
        logger.info(f"执行数据库优化: {recommendation.recommended_action}")
        await asyncio.sleep(1)  # 模拟配置更新
        return True

    async def _optimize_cache_resources(
        self, recommendation: OptimizationRecommendation
    ) -> bool:
        """优化缓存资源"""
        # 实际实现：调整Redis配置
        logger.info(f"执行缓存优化: {recommendation.recommended_action}")
        await asyncio.sleep(1)  # 模拟配置更新
        return True

    async def start_monitoring(self, interval: int | None = None) -> None:
        """启动成本监控"""
        monitor_interval = interval or self.config["monitoring_interval"]

        logger.info(f"启动成本监控，监控间隔: {monitor_interval}秒")

        while True:
            try:
                # 收集资源指标
                metrics = await self.collect_resource_metrics()

                # 计算成本
                costs = await self.calculate_costs(metrics)

                # 生成优化建议
                recommendations = await self.generate_optimization_recommendations(
                    metrics
                )

                # 生成报告
                report = await self.generate_cost_report(
                    metrics, costs, recommendations
                )

                # 检查是否需要告警
                await self._check_cost_alerts(report)

                # 自动优化（如果启用）
                if self.config.get("enable_auto_optimization", False):
                    await self.auto_optimize_resources(recommendations)

                logger.info("成本监控周期完成")

            except Exception as e:
                logger.error(f"成本监控周期异常: {e}")

            # 等待下一次监控
            await asyncio.sleep(monitor_interval)

    async def _check_cost_alerts(self, report: dict) -> None:
        """检查成本告警"""
        summary = report["summary"]

        # 检查总成本是否超过阈值
        monthly_cost = Decimal(str(summary["total_monthly_cost"]))
        alert_threshold = self.config["alert_threshold"]

        # 获取历史平均成本
        if len(self.cost_history) > 1:
            historical_costs = [
                r["summary"]["total_monthly_cost"] for r in self.cost_history[:-1]
            ]
            avg_historical_cost = sum(historical_costs) / len(historical_costs)

            if monthly_cost > Decimal(str(avg_historical_cost)) * (1 + alert_threshold):
                await self._send_cost_alert(
                    alert_type="cost_increase",
                    current_cost=float(monthly_cost),
                    historical_average=avg_historical_cost,
                    increase_percentage=(
                        (monthly_cost - Decimal(str(avg_historical_cost)))
                        / Decimal(str(avg_historical_cost))
                        * 100
                    ),
                )

        # 检查优化率
        optimization_rate = summary["optimization_rate"]
        if optimization_rate < 50:
            await self._send_cost_alert(
                alert_type="low_optimization", optimization_rate=optimization_rate
            )

    async def _send_cost_alert(self, **alert_data) -> None:
        """发送成本告警"""
        alert_type = alert_data.get("alert_type", "unknown")

        if alert_type == "cost_increase":
            message = (
                f"🚨 成本告警: 月度成本增加 {alert_data['increase_percentage']:.1f}%"
            )
            message += f"\n当前成本: ${alert_data['current_cost']:.2f}"
            message += f"\n历史平均: ${alert_data['historical_average']:.2f}"
        elif alert_type == "low_optimization":
            message = (
                f"⚠️ 优化告警: 资源优化率仅为 {alert_data['optimization_rate']:.1f}%"
            )
        else:
            message = f"📊 成本告警: {alert_data}"

        logger.warning(message)

        # 这里可以集成实际的告警系统（邮件、Slack、企业微信等）
        # await self._notification_service.send_alert(message)

    def get_optimization_statistics(self) -> dict:
        """获取优化统计信息"""
        if not self.cost_history:
            return {"status": "no_data"}

        latest_report = self.cost_history[-1]

        # 计算优化统计
        total_recommendations = len(latest_report["recommendations"])
        high_priority = len(
            [
                r
                for r in latest_report["recommendations"]
                if r["optimization_level"] == "high"
            ]
        )
        medium_priority = len(
            [
                r
                for r in latest_report["recommendations"]
                if r["optimization_level"] == "medium"
            ]
        )
        low_priority = len(
            [
                r
                for r in latest_report["recommendations"]
                if r["optimization_level"] == "low"
            ]
        )

        # 计算潜在节省统计
        total_savings = sum(
            r["potential_savings"] for r in latest_report["recommendations"]
        )

        return {
            "report_timestamp": latest_report["timestamp"],
            "total_resources": latest_report["summary"]["total_resources_monitored"],
            "optimized_resources": latest_report["summary"]["optimized_resources"],
            "optimization_rate": latest_report["summary"]["optimization_rate"],
            "total_monthly_cost": latest_report["summary"]["total_monthly_cost"],
            "total_potential_savings": latest_report["summary"][
                "total_potential_savings"
            ],
            "recommendations": {
                "total": total_recommendations,
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority,
            },
            "cost_trend": latest_report["cost_trends"],
            "savings_opportunity": {
                "total_monthly": float(total_savings),
                "total_annual": float(total_savings * 12),
                "percentage_of_cost": latest_report["summary"]["savings_percentage"],
            },
        }


async def demo_cost_optimizer():
    """演示成本优化功能"""
    print("💰 演示企业级成本优化系统")
    print("=" * 50)

    # 初始化成本优化器
    optimizer = CostOptimizer()

    # 收集资源指标
    print("\n📊 收集资源使用指标...")
    metrics = await optimizer.collect_resource_metrics()

    for resource_type, usage in metrics.items():
        print(
            f"  {resource_type.value}: {usage.current_usage:.2f} {usage.unit} "
            f"({usage.usage_percentage:.1f}%)"
        )

    # 计算成本
    print("\n💵 计算资源成本...")
    costs = await optimizer.calculate_costs(metrics)

    total_monthly = 0
    for resource_type, cost in costs.items():
        print(f"  {resource_type.value}: ${cost.monthly_cost:.2f}/月")
        total_monthly += cost.monthly_cost

    print(f"\n  总月度成本: ${total_monthly:.2f}")

    # 生成优化建议
    print("\n💡 生成优化建议...")
    recommendations = await optimizer.generate_optimization_recommendations(metrics)

    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec.recommended_action}")
        print(f"     资源: {rec.resource_type.value}")
        print(f"     潜在节省: ${rec.potential_savings:.2f}/月")
        print(f"     优化级别: {rec.optimization_level.value}")
        print(f"     实施难度: {rec.implementation_effort}")
        print()

    # 生成成本报告
    print("\n📋 生成成本分析报告...")
    report = await optimizer.generate_cost_report(metrics, costs, recommendations)

    print(f"  监控资源数量: {report['summary']['total_resources_monitored']}")
    print(f"  已优化资源: {report['summary']['optimized_resources']}")
    print(f"  优化率: {report['summary']['optimization_rate']:.1f}%")
    print(f"  总潜在节省: ${report['summary']['total_potential_savings']:.2f}/月")
    print(f"  节省比例: {report['summary']['savings_percentage']:.1f}%")

    # 自动优化演示
    print("\n🤖 演示自动优化 (dry run)...")
    optimization_results = await optimizer.auto_optimize_resources(
        recommendations, dry_run=True
    )

    print(f"  处理建议: {optimization_results['processed']}")
    print(f"  成功应用: {optimization_results['successful']}")
    print(f"  跳过建议: {optimization_results['skipped']}")

    # 获取优化统计
    print("\n📈 优化统计信息...")
    stats = optimizer.get_optimization_statistics()

    if "status" not in stats:
        print(f"  资源优化率: {stats['optimization_rate']:.1f}%")
        print(f"  月度成本: ${stats['total_monthly_cost']:.2f}")
        print(f"  年度节省机会: ${stats['savings_opportunity']['total_annual']:.2f}")
        print(f"  成本趋势: {stats['cost_trend']['trend']}")

    print("\n✅ 成本优化演示完成")


if __name__ == "__main__":
    asyncio.run(demo_cost_optimizer())
