#!/usr/bin/env python3
"""
云资源优化器
提供多云环境资源优化、成本分析、自动扩缩容和资源调度功能
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from src.core.logger import get_logger

logger = get_logger(__name__)


class CloudProvider(Enum):
    """云服务提供商"""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ALIBABA = "alibaba"
    TENCENT = "tencent"
    PRIVATE = "private"


class InstanceType(Enum):
    """实例类型"""

    GENERAL_PURPOSE = "general_purpose"  # 通用型
    COMPUTE_OPTIMIZED = "compute_optimized"  # 计算优化型
    MEMORY_OPTIMIZED = "memory_optimized"  # 内存优化型
    STORAGE_OPTIMIZED = "storage_optimized"  # 存储优化型
    GPU_OPTIMIZED = "gpu_optimized"  # GPU优化型
    BURSTABLE = "burstable"  # 突发型


class ScalingDirection(Enum):
    """扩缩容方向"""

    SCALE_UP = "scale_up"  # 扩容
    SCALE_DOWN = "scale_down"  # 缩容
    SCALE_OUT = "scale_out"  # 水平扩展
    SCALE_IN = "scale_in"  # 水平收缩


@dataclass
class CloudInstance:
    """云实例信息"""

    instance_id: str
    instance_name: str
    provider: CloudProvider
    instance_type: InstanceType
    cpu_cores: int
    memory_gb: float
    storage_gb: float
    network_performance: str  # low, medium, high, ultra
    region: str
    availability_zone: str
    status: str  # running, stopped, terminated
    hourly_cost: Decimal
    monthly_cost: Decimal
    tags: dict[str, str] = None
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "provider": self.provider.value,
            "instance_type": self.instance_type.value,
            "cpu_cores": self.cpu_cores,
            "memory_gb": float(self.memory_gb),
            "storage_gb": float(self.storage_gb),
            "network_performance": self.network_performance,
            "region": self.region,
            "availability_zone": self.availability_zone,
            "status": self.status,
            "hourly_cost": float(self.hourly_cost),
            "monthly_cost": float(self.monthly_cost),
            "tags": self.tags or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class ResourceUsageMetric:
    """资源使用指标"""

    instance_id: str
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_in_mbps: float
    network_out_mbps: float
    requests_per_minute: int
    avg_response_time_ms: float
    error_rate_percent: float

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "instance_id": self.instance_id,
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_percent": self.memory_usage_percent,
            "disk_usage_percent": self.disk_usage_percent,
            "network_in_mbps": self.network_in_mbps,
            "network_out_mbps": self.network_out_mbps,
            "requests_per_minute": self.requests_per_minute,
            "avg_response_time_ms": self.avg_response_time_ms,
            "error_rate_percent": self.error_rate_percent,
        }


@dataclass
class OptimizationRecommendation:
    """优化建议"""

    recommendation_id: str
    instance_id: str
    recommendation_type: str  # resize, terminate, migrate, rightsize
    current_instance: CloudInstance
    recommended_instance: CloudInstance | None
    potential_monthly_savings: Decimal
    performance_impact: str  # positive, neutral, negative
    confidence_score: float  # 0-1
    implementation_effort: str  # low, medium, high
    risk_level: str  # low, medium, high
    reason: str
    estimated_downtime_minutes: int
    tags: dict[str, str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "recommendation_id": self.recommendation_id,
            "instance_id": self.instance_id,
            "recommendation_type": self.recommendation_type,
            "current_instance": self.current_instance.to_dict(),
            "recommended_instance": (
                self.recommended_instance.to_dict()
                if self.recommended_instance
                else None
            ),
            "potential_monthly_savings": float(self.potential_monthly_savings),
            "performance_impact": self.performance_impact,
            "confidence_score": self.confidence_score,
            "implementation_effort": self.implementation_effort,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "estimated_downtime_minutes": self.estimated_downtime_minutes,
            "tags": self.tags or {},
        }


@dataclass
class ScalingPolicy:
    """扩缩容策略"""

    policy_id: str
    name: str
    resource_group: str  # 应用此策略的资源组
    min_instances: int
    max_instances: int
    target_cpu_percent: float
    target_memory_percent: float
    scale_up_cooldown: int  # 秒
    scale_down_cooldown: int  # 秒
    scale_up_threshold: float
    scale_down_threshold: float
    enabled: bool
    last_scale_time: datetime | None = None

    def should_scale_up(self, avg_cpu: float, avg_memory: float) -> bool:
        """判断是否应该扩容"""
        if not self.enabled:
            return False

        # 检查冷却时间
        if self.last_scale_time:
            cooldown_elapsed = datetime.now() - self.last_scale_time
            if cooldown_elapsed.total_seconds() < self.scale_up_cooldown:
                return False

        # 检查阈值
        return (
            avg_cpu >= self.scale_up_threshold or avg_memory >= self.scale_up_threshold
        )

    def should_scale_down(self, avg_cpu: float, avg_memory: float) -> bool:
        """判断是否应该缩容"""
        if not self.enabled:
            return False

        # 检查冷却时间
        if self.last_scale_time:
            cooldown_elapsed = datetime.now() - self.last_scale_time
            if cooldown_elapsed.total_seconds() < self.scale_down_cooldown:
                return False

        # 检查阈值
        return (
            avg_cpu <= self.scale_down_threshold
            and avg_memory <= self.scale_down_threshold
        )


class CloudProviderAdapter(ABC):
    """云服务提供商适配器抽象基类"""

    @abstractmethod
    async def get_instances(self) -> list[CloudInstance]:
        """获取所有实例"""
        pass

    @abstractmethod
    async def get_instance_metrics(
        self, instance_id: str, start_time: datetime, end_time: datetime
    ) -> list[ResourceUsageMetric]:
        """获取实例指标"""
        pass

    @abstractmethod
    async def resize_instance(self, instance_id: str, new_instance_type: str) -> bool:
        """调整实例规格"""
        pass

    @abstractmethod
    async def terminate_instance(self, instance_id: str) -> bool:
        """终止实例"""
        pass

    @abstractmethod
    async def start_instance(self, instance_id: str) -> bool:
        """启动实例"""
        pass

    @abstractmethod
    async def stop_instance(self, instance_id: str) -> bool:
        """停止实例"""
        pass

    @abstractmethod
    def get_instance_pricing(self, instance_type: str, region: str) -> dict:
        """获取实例定价"""
        pass


class AWSAdapter(CloudProviderAdapter):
    """AWS适配器"""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        # 这里应该初始化AWS SDK
        logger.info(f"AWS适配器初始化完成，区域: {region}")

    async def get_instances(self) -> list[CloudInstance]:
        """获取AWS EC2实例"""
        # 模拟AWS API调用
        instances = []

        # 模拟数据
        mock_instances = [
            {
                "instance_id": "i-1234567890abcdef0",
                "instance_name": "web-server-1",
                "instance_type": "t3.medium",
                "cpu_cores": 2,
                "memory_gb": 4.0,
                "storage_gb": 100,
                "status": "running",
                "hourly_cost": Decimal("0.0416"),
            },
            {
                "instance_id": "i-1234567890abcdef1",
                "instance_name": "db-server-1",
                "instance_type": "r5.large",
                "cpu_cores": 2,
                "memory_gb": 16.0,
                "storage_gb": 500,
                "status": "running",
                "hourly_cost": Decimal("0.126"),
            },
            {
                "instance_id": "i-1234567890abcdef2",
                "instance_name": "cache-server-1",
                "instance_type": "cache.t3.micro",
                "cpu_cores": 2,
                "memory_gb": 1.0,
                "storage_gb": 20,
                "status": "stopped",
                "hourly_cost": Decimal("0.0084"),
            },
        ]

        for instance_data in mock_instances:
            instance = CloudInstance(
                instance_id=instance_data["instance_id"],
                instance_name=instance_data["instance_name"],
                provider=CloudProvider.AWS,
                instance_type=self._map_instance_type(instance_data["instance_type"]),
                cpu_cores=instance_data["cpu_cores"],
                memory_gb=instance_data["memory_gb"],
                storage_gb=instance_data["storage_gb"],
                network_performance="medium",
                region=self.region,
                availability_zone=f"{self.region}a",
                status=instance_data["status"],
                hourly_cost=instance_data["hourly_cost"],
                monthly_cost=instance_data["hourly_cost"]
                * Decimal("730"),  # 730小时/月
                created_at=datetime.now() - timedelta(days=30),
            )
            instances.append(instance)

        logger.info(f"获取到 {len(instances)} 个AWS实例")
        return instances

    def _map_instance_type(self, aws_type: str) -> InstanceType:
        """映射AWS实例类型到标准类型"""
        if aws_type.startswith("t3.") or aws_type.startswith("t2."):
            return InstanceType.BURSTABLE
        elif aws_type.startswith("c5.") or aws_type.startswith("c4."):
            return InstanceType.COMPUTE_OPTIMIZED
        elif aws_type.startswith("r5.") or aws_type.startswith("r4."):
            return InstanceType.MEMORY_OPTIMIZED
        elif aws_type.startswith("i3.") or aws_type.startswith("d2."):
            return InstanceType.STORAGE_OPTIMIZED
        elif aws_type.startswith("p3.") or aws_type.startswith("g4."):
            return InstanceType.GPU_OPTIMIZED
        else:
            return InstanceType.GENERAL_PURPOSE

    async def get_instance_metrics(
        self, instance_id: str, start_time: datetime, end_time: datetime
    ) -> list[ResourceUsageMetric]:
        """获取实例指标"""
        # 模拟CloudWatch数据
        import random

        metrics = []
        current_time = start_time

        while current_time <= end_time:
            metric = ResourceUsageMetric(
                instance_id=instance_id,
                timestamp=current_time,
                cpu_usage_percent=random.uniform(20, 80),
                memory_usage_percent=random.uniform(40, 90),
                disk_usage_percent=random.uniform(10, 60),
                network_in_mbps=random.uniform(1, 50),
                network_out_mbps=random.uniform(1, 30),
                requests_per_minute=random.randint(100, 1000),
                avg_response_time_ms=random.uniform(50, 500),
                error_rate_percent=random.uniform(0, 5),
            )
            metrics.append(metric)
            current_time += timedelta(minutes=5)

        return metrics

    async def resize_instance(self, instance_id: str, new_instance_type: str) -> bool:
        """调整AWS实例规格"""
        logger.info(f"AWS调整实例规格: {instance_id} -> {new_instance_type}")
        await asyncio.sleep(2)  # 模拟API调用
        return True

    async def terminate_instance(self, instance_id: str) -> bool:
        """终止AWS实例"""
        logger.info(f"AWS终止实例: {instance_id}")
        await asyncio.sleep(1)  # 模拟API调用
        return True

    async def start_instance(self, instance_id: str) -> bool:
        """启动AWS实例"""
        logger.info(f"AWS启动实例: {instance_id}")
        await asyncio.sleep(1)
        return True

    async def stop_instance(self, instance_id: str) -> bool:
        """停止AWS实例"""
        logger.info(f"AWS停止实例: {instance_id}")
        await asyncio.sleep(1)
        return True

    def get_instance_pricing(self, instance_type: str, region: str) -> dict:
        """获取AWS实例定价"""
        # 模拟定价数据
        pricing_map = {
            "t3.micro": {"hourly": 0.0104, "monthly": 7.59},
            "t3.small": {"hourly": 0.0208, "monthly": 15.18},
            "t3.medium": {"hourly": 0.0416, "monthly": 30.37},
            "c5.large": {"hourly": 0.085, "monthly": 62.05},
            "r5.large": {"hourly": 0.126, "monthly": 91.98},
        }

        return pricing_map.get(instance_type, {"hourly": 0.1, "monthly": 73.0})


class CloudOptimizer:
    """云资源优化器"""

    def __init__(self, config: dict | None = None):
        self.config = config or self._get_default_config()
        self.adapters: dict[CloudProvider, CloudProviderAdapter] = {}
        self.instances: dict[str, CloudInstance] = {}
        self.metrics_history: dict[str, list[ResourceUsageMetric]] = {}
        self.scaling_policies: dict[str, ScalingPolicy] = {}
        self.recommendations: list[OptimizationRecommendation] = []

        # 成本优化规则
        self.optimization_rules = self._load_optimization_rules()

        # 初始化适配器
        self._initialize_adapters()

        logger.info("云资源优化器初始化完成")

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "metrics_retention_days": 30,
            "recommendation_refresh_interval": 3600,  # 1小时
            "auto_optimization_enabled": False,
            "cost_savings_threshold": Decimal("10.00"),  # $10/月
            "performance_threshold": 0.1,  # 10%性能阈值
            "risk_tolerance": "medium",  # low, medium, high
            "regions": ["us-east-1", "us-west-2"],
            "monitoring_interval": 300,  # 5分钟
        }

    def _load_optimization_rules(self) -> dict:
        """加载优化规则"""
        return {
            "under_utilization_threshold": 30.0,  # 30%以下为低利用率
            "over_utilization_threshold": 85.0,  # 85%以上为高利用率
            "idle_threshold": 5.0,  # 5%以下为空闲
            "cost_savings_min_threshold": 0.15,  # 最小15%成本节省
            "performance_degradation_max": 0.1,  # 最大10%性能下降
            "recommendation_confidence_min": 0.7,  # 最小70%置信度
            "instance_type_mappings": {
                InstanceType.GENERAL_PURPOSE: {
                    "low": ["t3.nano", "t3.micro"],
                    "medium": ["t3.small", "t3.medium"],
                    "high": ["t3.large", "t3.xlarge"],
                },
                InstanceType.COMPUTE_OPTIMIZED: {
                    "low": ["c5.large", "c5.xlarge"],
                    "medium": ["c5.2xlarge", "c5.4xlarge"],
                    "high": ["c5.9xlarge", "c5.18xlarge"],
                },
                InstanceType.MEMORY_OPTIMIZED: {
                    "low": ["r5.large", "r5.xlarge"],
                    "medium": ["r5.2xlarge", "r5.4xlarge"],
                    "high": ["r5.8xlarge", "r5.16xlarge"],
                },
            },
        }

    def _initialize_adapters(self) -> None:
        """初始化云服务适配器"""
        # 初始化AWS适配器
        for region in self.config["regions"]:
            aws_adapter = AWSAdapter(region)
            self.adapters[CloudProvider.AWS] = aws_adapter

        logger.info(f"初始化了 {len(self.adapters)} 个云服务适配器")

    async def discover_instances(self) -> None:
        """发现所有云实例"""
        logger.info("发现云实例...")

        all_instances = []
        for provider, adapter in self.adapters.items():
            try:
                instances = await adapter.get_instances()
                all_instances.extend(instances)
                logger.info(f"{provider.value}: 发现 {len(instances)} 个实例")
            except Exception as e:
                logger.error(f"发现{provider.value}实例失败: {e}")

        # 更新实例缓存
        for instance in all_instances:
            self.instances[instance.instance_id] = instance

        logger.info(f"总共发现 {len(self.instances)} 个实例")

    async def collect_metrics(self, hours_back: int = 24) -> None:
        """收集实例指标"""
        logger.info(f"收集过去 {hours_back} 小时的实例指标...")

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        for instance_id, instance in self.instances.items():
            try:
                adapter = self.adapters.get(instance.provider)
                if not adapter:
                    continue

                metrics = await adapter.get_instance_metrics(
                    instance_id, start_time, end_time
                )
                self.metrics_history[instance_id] = metrics

                logger.debug(f"实例 {instance_id}: 收集了 {len(metrics)} 个指标")

            except Exception as e:
                logger.warning(f"收集实例 {instance_id} 指标失败: {e}")

        logger.info("指标收集完成")

    async def generate_recommendations(self) -> list[OptimizationRecommendation]:
        """生成优化建议"""
        logger.info("生成云资源优化建议...")

        recommendations = []

        for instance_id, instance in self.instances.items():
            metrics = self.metrics_history.get(instance_id, [])
            if not metrics:
                continue

            # 计算平均使用率
            avg_cpu = sum(m.cpu_usage_percent for m in metrics) / len(metrics)
            avg_memory = sum(m.memory_usage_percent for m in metrics) / len(metrics)
            avg_requests = sum(m.requests_per_minute for m in metrics) / len(metrics)

            # 生成不同类型的建议
            instance_recommendations = []

            # 1. 低利用率实例优化
            if avg_cpu < self.optimization_rules["under_utilization_threshold"]:
                rec = await self._generate_underutilization_recommendation(
                    instance, avg_cpu, avg_memory, metrics
                )
                if rec:
                    instance_recommendations.append(rec)

            # 2. 过载实例优化
            elif avg_cpu > self.optimization_rules["over_utilization_threshold"]:
                rec = await self._generate_overutilization_recommendation(
                    instance, avg_cpu, avg_memory, metrics
                )
                if rec:
                    instance_recommendations.append(rec)

            # 3. 空闲实例终止
            if avg_cpu < self.optimization_rules["idle_threshold"]:
                rec = await self._generate_termination_recommendation(instance, metrics)
                if rec:
                    instance_recommendations.append(rec)

            # 4. 实例类型优化
            rec = await self._generate_rightsize_recommendation(
                instance, avg_cpu, avg_memory, metrics
            )
            if rec:
                instance_recommendations.append(rec)

            recommendations.extend(instance_recommendations)

        # 按潜在节省金额排序
        recommendations.sort(key=lambda x: x.potential_monthly_savings, reverse=True)

        self.recommendations = recommendations
        logger.info(f"生成了 {len(recommendations)} 条优化建议")

        return recommendations

    async def _generate_underutilization_recommendation(
        self,
        instance: CloudInstance,
        avg_cpu: float,
        avg_memory: float,
        metrics: list[ResourceUsageMetric],
    ) -> OptimizationRecommendation | None:
        """生成低利用率优化建议"""

        # 寻找更小的实例类型
        current_type = instance.instance_type
        smaller_instances = self._find_smaller_instances(current_type)

        if not smaller_instances:
            return None

        # 选择最合适的更小实例
        target_instance = smaller_instances[0]
        adapter = self.adapters.get(instance.provider)
        if not adapter:
            return None

        pricing = adapter.get_instance_pricing(target_instance, instance.region)
        new_hourly_cost = Decimal(str(pricing["hourly"]))
        new_monthly_cost = new_hourly_cost * Decimal("730")

        # 计算节省金额
        potential_savings = instance.monthly_cost - new_monthly_cost

        if potential_savings < self.config["cost_savings_threshold"]:
            return None

        # 创建新实例对象
        new_instance = CloudInstance(
            instance_id=instance.instance_id + "_optimized",
            instance_name=instance.instance_name + "_optimized",
            provider=instance.provider,
            instance_type=InstanceType.GENERAL_PURPOSE,  # 根据实际情况调整
            cpu_cores=(
                target_instance["cpu_cores"]
                if isinstance(target_instance, dict)
                else instance.cpu_cores // 2
            ),
            memory_gb=(
                target_instance["memory_gb"]
                if isinstance(target_instance, dict)
                else instance.memory_gb / 2
            ),
            storage_gb=instance.storage_gb,
            network_performance=instance.network_performance,
            region=instance.region,
            availability_zone=instance.availability_zone,
            status="proposed",
            hourly_cost=new_hourly_cost,
            monthly_cost=new_monthly_cost,
        )

        return OptimizationRecommendation(
            recommendation_id=f"underutil_{instance.instance_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            instance_id=instance.instance_id,
            recommendation_type="resize",
            current_instance=instance,
            recommended_instance=new_instance,
            potential_monthly_savings=potential_savings,
            performance_impact="neutral",
            confidence_score=0.8,
            implementation_effort="medium",
            risk_level="low",
            reason=f"实例CPU使用率过低({avg_cpu:.1f}%)，建议降配到更小实例",
            estimated_downtime_minutes=5,
            tags={"auto_generated": "true", "category": "cost_optimization"},
        )

    async def _generate_overutilization_recommendation(
        self,
        instance: CloudInstance,
        avg_cpu: float,
        avg_memory: float,
        metrics: list[ResourceUsageMetric],
    ) -> OptimizationRecommendation | None:
        """生成过载优化建议"""

        # 寻找更大的实例类型
        larger_instances = self._find_larger_instances(instance.instance_type)

        if not larger_instances:
            return None

        target_instance = larger_instances[0]
        adapter = self.adapters.get(instance.provider)
        if not adapter:
            return None

        pricing = adapter.get_instance_pricing(target_instance, instance.region)
        new_hourly_cost = Decimal(str(pricing["hourly"]))
        new_monthly_cost = new_hourly_cost * Decimal("730")

        # 计算成本增加
        cost_increase = new_monthly_cost - instance.monthly_cost

        # 创建新实例对象
        new_instance = CloudInstance(
            instance_id=instance.instance_id + "_upgraded",
            instance_name=instance.instance_name + "_upgraded",
            provider=instance.provider,
            instance_type=InstanceType.COMPUTE_OPTIMIZED,
            cpu_cores=(
                target_instance["cpu_cores"]
                if isinstance(target_instance, dict)
                else instance.cpu_cores * 2
            ),
            memory_gb=(
                target_instance["memory_gb"]
                if isinstance(target_instance, dict)
                else instance.memory_gb * 2
            ),
            storage_gb=instance.storage_gb,
            network_performance=instance.network_performance,
            region=instance.region,
            availability_zone=instance.availability_zone,
            status="proposed",
            hourly_cost=new_hourly_cost,
            monthly_cost=new_monthly_cost,
        )

        return OptimizationRecommendation(
            recommendation_id=f"overutil_{instance.instance_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            instance_id=instance.instance_id,
            recommendation_type="resize",
            current_instance=instance,
            recommended_instance=new_instance,
            potential_monthly_savings=Decimal(str(-cost_increase)),  # 负数表示成本增加
            performance_impact="positive",
            confidence_score=0.9,
            implementation_effort="medium",
            risk_level="medium",
            reason=f"实例CPU使用率过高({avg_cpu:.1f}%)，建议升级到更大实例",
            estimated_downtime_minutes=10,
            tags={"auto_generated": "true", "category": "performance_optimization"},
        )

    async def _generate_termination_recommendation(
        self, instance: CloudInstance, metrics: list[ResourceUsageMetric]
    ) -> OptimizationRecommendation | None:
        """生成实例终止建议"""

        # 检查实例是否长时间空闲
        if instance.status != "stopped":
            return None

        # 计算潜在节省（100%节省）
        potential_savings = instance.monthly_cost

        if potential_savings < self.config["cost_savings_threshold"]:
            return None

        return OptimizationRecommendation(
            recommendation_id=f"terminate_{instance.instance_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            instance_id=instance.instance_id,
            recommendation_type="terminate",
            current_instance=instance,
            recommended_instance=None,
            potential_monthly_savings=potential_savings,
            performance_impact="neutral",
            confidence_score=0.95,
            implementation_effort="low",
            risk_level="low",
            reason="实例已停止且长时间未使用，建议终止以节省成本",
            estimated_downtime_minutes=0,
            tags={"auto_generated": "true", "category": "cleanup"},
        )

    async def _generate_rightsize_recommendation(
        self,
        instance: CloudInstance,
        avg_cpu: float,
        avg_memory: float,
        metrics: list[ResourceUsageMetric],
    ) -> OptimizationRecommendation | None:
        """生成实例规格优化建议"""

        # 根据CPU和内存使用率推荐最合适的实例类型
        optimal_instance_type = self._recommend_optimal_instance_type(
            avg_cpu, avg_memory
        )

        if optimal_instance_type == instance.instance_type:
            return None  # 当前实例类型已经是最优

        adapter = self.adapters.get(instance.provider)
        if not adapter:
            return None

        # 模拟新实例类型
        new_instance = CloudInstance(
            instance_id=instance.instance_id + "_rightsized",
            instance_name=instance.instance_name + "_rightsized",
            provider=instance.provider,
            instance_type=optimal_instance_type,
            cpu_cores=self._estimate_cpu_for_type(optimal_instance_type, avg_cpu),
            memory_gb=self._estimate_memory_for_type(optimal_instance_type, avg_memory),
            storage_gb=instance.storage_gb,
            network_performance=instance.network_performance,
            region=instance.region,
            availability_zone=instance.availability_zone,
            status="proposed",
            hourly_cost=instance.hourly_cost * Decimal("0.9"),  # 假设10%节省
            monthly_cost=instance.monthly_cost * Decimal("0.9"),
        )

        potential_savings = instance.monthly_cost - new_instance.monthly_cost

        return OptimizationRecommendation(
            recommendation_id=f"rightsize_{instance.instance_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            instance_id=instance.instance_id,
            recommendation_type="rightsize",
            current_instance=instance,
            recommended_instance=new_instance,
            potential_monthly_savings=potential_savings,
            performance_impact="positive",
            confidence_score=0.75,
            implementation_effort="medium",
            risk_level="medium",
            reason=f"基于使用模式推荐更合适的实例类型: {optimal_instance_type.value}",
            estimated_downtime_minutes=15,
            tags={"auto_generated": "true", "category": "optimization"},
        )

    def _find_smaller_instances(self, current_type: InstanceType) -> list[str]:
        """寻找更小的实例类型"""
        type_mappings = {
            InstanceType.GENERAL_PURPOSE: ["t3.small", "t3.medium"],
            InstanceType.COMPUTE_OPTIMIZED: ["c5.large", "c5.xlarge"],
            InstanceType.MEMORY_OPTIMIZED: ["r5.large", "r5.xlarge"],
        }
        return type_mappings.get(current_type, [])

    def _find_larger_instances(self, current_type: InstanceType) -> list[str]:
        """寻找更大的实例类型"""
        type_mappings = {
            InstanceType.GENERAL_PURPOSE: ["t3.large", "t3.xlarge"],
            InstanceType.COMPUTE_OPTIMIZED: ["c5.2xlarge", "c5.4xlarge"],
            InstanceType.MEMORY_OPTIMIZED: ["r5.2xlarge", "r5.4xlarge"],
        }
        return type_mappings.get(current_type, [])

    def _recommend_optimal_instance_type(
        self, avg_cpu: float, avg_memory: float
    ) -> InstanceType:
        """推荐最优实例类型"""
        cpu_memory_ratio = avg_cpu / avg_memory if avg_memory > 0 else 1

        if cpu_memory_ratio > 1.5:
            return InstanceType.COMPUTE_OPTIMIZED
        elif avg_memory > 70:
            return InstanceType.MEMORY_OPTIMIZED
        elif avg_cpu < 30:
            return InstanceType.BURSTABLE
        else:
            return InstanceType.GENERAL_PURPOSE

    def _estimate_cpu_for_type(
        self, instance_type: InstanceType, target_usage: float
    ) -> int:
        """为实例类型估算CPU核心数"""
        base_cpu = {
            InstanceType.GENERAL_PURPOSE: 2,
            InstanceType.COMPUTE_OPTIMIZED: 4,
            InstanceType.MEMORY_OPTIMIZED: 2,
            InstanceType.BURSTABLE: 1,
        }
        return base_cpu.get(instance_type, 2)

    def _estimate_memory_for_type(
        self, instance_type: InstanceType, target_usage: float
    ) -> float:
        """为实例类型估算内存大小"""
        base_memory = {
            InstanceType.GENERAL_PURPOSE: 4.0,
            InstanceType.COMPUTE_OPTIMIZED: 8.0,
            InstanceType.MEMORY_OPTIMIZED: 16.0,
            InstanceType.BURSTABLE: 1.0,
        }
        return base_memory.get(instance_type, 4.0)

    async def apply_recommendation(
        self, recommendation: OptimizationRecommendation, dry_run: bool = True
    ) -> bool:
        """应用优化建议"""
        logger.info(
            f"应用优化建议: {recommendation.recommendation_id} (dry_run={dry_run})"
        )

        try:
            if dry_run:
                logger.info(f"[DRY RUN] 将执行: {recommendation.recommendation_type}")
                return True

            instance = self.instances.get(recommendation.instance_id)
            if not instance:
                logger.error(f"实例不存在: {recommendation.instance_id}")
                return False

            adapter = self.adapters.get(instance.provider)
            if not adapter:
                logger.error(f"提供商适配器不存在: {instance.provider}")
                return False

            if recommendation.recommendation_type == "resize":
                if recommendation.recommended_instance:
                    # 执行实例规格调整
                    new_type = "t3.large"  # 根据实际情况确定
                    success = await adapter.resize_instance(
                        recommendation.instance_id, new_type
                    )
                    if success:
                        logger.info(f"实例 {recommendation.instance_id} 规格调整完成")
                    return success

            elif recommendation.recommendation_type == "terminate":
                success = await adapter.terminate_instance(recommendation.instance_id)
                if success:
                    logger.info(f"实例 {recommendation.instance_id} 已终止")
                    # 从缓存中移除
                    del self.instances[recommendation.instance_id]
                return success

            elif recommendation.recommendation_type == "start":
                success = await adapter.start_instance(recommendation.instance_id)
                if success:
                    logger.info(f"实例 {recommendation.instance_id} 已启动")
                return success

            elif recommendation.recommendation_type == "stop":
                success = await adapter.stop_instance(recommendation.instance_id)
                if success:
                    logger.info(f"实例 {recommendation.instance_id} 已停止")
                return success

            else:
                logger.warning(
                    f"不支持的优化类型: {recommendation.recommendation_type}"
                )
                return False

        except Exception as e:
            logger.error(f"应用优化建议失败: {e}")
            return False

    async def auto_scaling(self) -> dict:
        """自动扩缩容"""
        logger.info("执行自动扩缩容...")

        results = {
            "evaluated_policies": 0,
            "scale_up_actions": 0,
            "scale_down_actions": 0,
            "errors": [],
        }

        for policy_id, policy in self.scaling_policies.items():
            if not policy.enabled:
                continue

            results["evaluated_policies"] += 1

            try:
                # 获取资源组的实例
                group_instances = [
                    inst
                    for inst in self.instances.values()
                    if policy.resource_group in inst.instance_name
                ]

                if not group_instances:
                    continue

                # 计算平均使用率
                total_cpu = 0
                total_memory = 0
                instance_count = 0

                for instance in group_instances:
                    metrics = self.metrics_history.get(instance.instance_id, [])
                    if metrics:
                        recent_metrics = metrics[-12:]  # 最近1小时（假设5分钟间隔）
                        if recent_metrics:
                            total_cpu += sum(
                                m.cpu_usage_percent for m in recent_metrics
                            ) / len(recent_metrics)
                            total_memory += sum(
                                m.memory_usage_percent for m in recent_metrics
                            ) / len(recent_metrics)
                            instance_count += 1

                if instance_count == 0:
                    continue

                avg_cpu = total_cpu / instance_count
                avg_memory = total_memory / instance_count

                # 检查是否需要扩容
                if policy.should_scale_up(avg_cpu, avg_memory):
                    if await self._execute_scale_up(policy, group_instances):
                        results["scale_up_actions"] += 1
                        policy.last_scale_time = datetime.now()

                # 检查是否需要缩容
                elif policy.should_scale_down(avg_cpu, avg_memory):
                    if await self._execute_scale_down(policy, group_instances):
                        results["scale_down_actions"] += 1
                        policy.last_scale_time = datetime.now()

            except Exception as e:
                error_msg = f"扩缩容策略 {policy_id} 执行失败: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        logger.info(
            f"自动扩缩容完成: 扩容 {results['scale_up_actions']}, 缩容 {results['scale_down_actions']}"
        )
        return results

    async def _execute_scale_up(
        self, policy: ScalingPolicy, instances: list[CloudInstance]
    ) -> bool:
        """执行扩容"""
        if len(instances) >= policy.max_instances:
            return False

        logger.info(f"扩容资源组 {policy.resource_group}")
        # 实际实现中，这里会调用云服务API创建新实例
        await asyncio.sleep(2)  # 模拟API调用
        return True

    async def _execute_scale_down(
        self, policy: ScalingPolicy, instances: list[CloudInstance]
    ) -> bool:
        """执行缩容"""
        if len(instances) <= policy.min_instances:
            return False

        logger.info(f"缩容资源组 {policy.resource_group}")
        # 实际实现中，这里会调用云服务API终止实例
        await asyncio.sleep(2)  # 模拟API调用
        return True

    def get_cost_summary(self) -> dict:
        """获取成本摘要"""
        total_monthly_cost = sum(
            instance.monthly_cost for instance in self.instances.values()
        )
        total_hourly_cost = sum(
            instance.hourly_cost for instance in self.instances.values()
        )

        # 按提供商统计
        provider_costs = {}
        for provider in CloudProvider:
            provider_instances = [
                inst for inst in self.instances.values() if inst.provider == provider
            ]
            if provider_instances:
                provider_costs[provider.value] = {
                    "instance_count": len(provider_instances),
                    "monthly_cost": float(
                        sum(inst.monthly_cost for inst in provider_instances)
                    ),
                    "hourly_cost": float(
                        sum(inst.hourly_cost for inst in provider_instances)
                    ),
                }

        # 按实例类型统计
        type_costs = {}
        for instance_type in InstanceType:
            type_instances = [
                inst
                for inst in self.instances.values()
                if inst.instance_type == instance_type
            ]
            if type_instances:
                type_costs[instance_type.value] = {
                    "instance_count": len(type_instances),
                    "monthly_cost": float(
                        sum(inst.monthly_cost for inst in type_instances)
                    ),
                }

        # 潜在节省
        total_potential_savings = sum(
            rec.potential_monthly_savings
            for rec in self.recommendations
            if rec.potential_monthly_savings > 0
        )

        return {
            "summary": {
                "total_instances": len(self.instances),
                "total_monthly_cost": float(total_monthly_cost),
                "total_hourly_cost": float(total_hourly_cost),
                "total_potential_savings": float(total_potential_savings),
                "savings_percentage": (
                    round((total_potential_savings / total_monthly_cost * 100), 2)
                    if total_monthly_cost > 0
                    else 0
                ),
            },
            "by_provider": provider_costs,
            "by_instance_type": type_costs,
            "recommendations_count": len(self.recommendations),
            "last_updated": datetime.now().isoformat(),
        }


async def demo_cloud_optimizer():
    """演示云资源优化功能"""
    print("☁️ 演示企业级云资源优化系统")
    print("=" * 50)

    # 初始化云资源优化器
    optimizer = CloudOptimizer()

    print("\n🔍 发现云实例...")
    await optimizer.discover_instances()

    print(f"发现 {len(optimizer.instances)} 个实例:")
    for instance_id, instance in optimizer.instances.items():
        status_icon = (
            "🟢"
            if instance.status == "running"
            else "🔴" if instance.status == "stopped" else "⚪"
        )
        print(
            f"  {status_icon} [{instance.provider.value}] {instance.instance_name} "
            f"({instance.cpu_cores}vCPU, {instance.memory_gb}GB) "
            f"${instance.monthly_cost:.2f}/月"
        )

    print("\n📊 收集实例指标...")
    await optimizer.collect_metrics(hours_back=24)

    print("\n💡 生成优化建议...")
    recommendations = await optimizer.generate_recommendations()

    if recommendations:
        print(f"生成了 {len(recommendations)} 条优化建议:")
        for i, rec in enumerate(recommendations, 1):
            savings_text = (
                f"节省 ${rec.potential_monthly_savings:.2f}/月"
                if rec.potential_monthly_savings > 0
                else f"成本增加 ${abs(rec.potential_monthly_savings):.2f}/月"
            )
            print(f"  {i}. [{rec.recommendation_type.upper()}] {rec.reason}")
            print(
                f"     {savings_text} | 置信度: {rec.confidence_score:.1%} | 风险: {rec.risk_level}"
            )
    else:
        print("暂无优化建议")

    print("\n📈 成本摘要:")
    cost_summary = optimizer.get_cost_summary()
    summary = cost_summary["summary"]
    print(f"  总实例数: {summary['total_instances']}")
    print(f"  月度成本: ${summary['total_monthly_cost']:.2f}")
    print(
        f"  潜在节省: ${summary['total_potential_savings']:.2f} ({summary['savings_percentage']:.1f}%)"
    )

    if cost_summary["by_provider"]:
        print("\n按提供商:")
        for provider, data in cost_summary["by_provider"].items():
            print(
                f"  {provider}: {data['instance_count']} 实例, ${data['monthly_cost']:.2f}/月"
            )

    print("\n🤖 演示自动优化 (dry run)...")
    if recommendations:
        # 应用第一个建议（dry run）
        first_rec = recommendations[0]
        success = await optimizer.apply_recommendation(first_rec, dry_run=True)
        print(
            f"  优化建议 '{first_rec.recommendation_type}' 执行{'成功' if success else '失败'}"
        )

    print("\n✅ 云资源优化演示完成")


if __name__ == "__main__":
    asyncio.run(demo_cloud_optimizer())
