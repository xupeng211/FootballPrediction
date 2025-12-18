#!/usr/bin/env python3
"""
Infrastructure Optimization Skill for Claude Code
基础设施优化专业技能 - Docker/容器环境性能优化专家
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import re
import yaml
from pathlib import Path

class InfrastructureOptimizationSkill:
    """
    Infrastructure Optimization Skill - 专注于基础设施性能调优和资源优化
    """

    def __init__(self):
        self.skill_name = "infrastructure-optimization"
        self.capabilities = [
            "resource-allocation",
            "performance-tuning",
            "capacity-planning",
            "docker-optimization",
            "memory-management",
            "cpu-scheduling",
            "storage-optimization"
        ]

    def analyze_docker_resource_allocation(self, docker_compose_content: str,
                                         host_memory_gb: float,
                                         host_cpu_cores: int) -> Dict[str, Any]:
        """
        分析Docker Compose资源配置并提供优化建议

        Args:
            docker_compose_content: docker-compose.yml文件内容
            host_memory_gb: 宿主机内存(GB)
            host_cpu_cores: 宿主机CPU核心数

        Returns:
            包含分析和建议的字典
        """
        try:
            # 解析docker-compose配置
            config = yaml.safe_load(docker_compose_content)

            analysis = {
                "total_memory_requested": 0,
                "total_cpu_requested": 0,
                "services": {},
                "optimization_recommendations": [],
                "risk_level": "low"
            }

            # 计算总资源请求
            if 'services' in config:
                for service_name, service_config in config['services'].items():
                    service_analysis = {
                        "memory_limit": None,
                        "cpu_limit": None,
                        "memory_reservation": None,
                        "optimization_needed": False
                    }

                    # 分析资源限制
                    deploy_config = service_config.get('deploy', {}).get('resources', {})
                    limits = deploy_config.get('limits', {})
                    reservations = deploy_config.get('reservations', {})

                    # 解析内存限制
                    if 'memory' in limits:
                        memory_limit = self._parse_memory_string(limits['memory'])
                        service_analysis["memory_limit"] = limits['memory']
                        analysis["total_memory_requested"] += memory_limit

                    # 解析CPU限制
                    if 'cpus' in limits:
                        cpu_limit = float(limits['cpus'])
                        service_analysis["cpu_limit"] = limits['cpus']
                        analysis["total_cpu_requested"] += cpu_limit

                    # 解析内存预留
                    if 'memory' in reservations:
                        service_analysis["memory_reservation"] = reservations['memory']

                    # 评估是否需要优化
                    service_analysis["optimization_needed"] = self._evaluate_service_optimization(
                        service_name, service_config, host_memory_gb, host_cpu_cores
                    )

                    analysis["services"][service_name] = service_analysis

            # 风险评估
            memory_usage_percent = (analysis["total_memory_requested"] / (host_memory_gb * 1024)) * 100
            cpu_usage_percent = (analysis["total_cpu_requested"] / host_cpu_cores) * 100

            if memory_usage_percent > 90:
                analysis["risk_level"] = "critical"
                analysis["optimization_recommendations"].append(
                    f"内存使用率过高: {memory_usage_percent:.1f}%, 建议减少服务内存分配"
                )
            elif memory_usage_percent > 75:
                analysis["risk_level"] = "high"
                analysis["optimization_recommendations"].append(
                    f"内存使用率较高: {memory_usage_percent:.1f}%, 建议监控内存使用"
                )

            if cpu_usage_percent > 90:
                analysis["risk_level"] = "critical"
                analysis["optimization_recommendations"].append(
                    f"CPU使用率过高: {cpu_usage_percent:.1f}%, 建议减少服务CPU分配"
                )

            # 生成具体优化建议
            analysis["optimization_recommendations"].extend(
                self._generate_optimization_recommendations(analysis, host_memory_gb, host_cpu_cores)
            )

            return analysis

        except Exception as e:
            return {"error": f"分析失败: {str(e)}"}

    def optimize_for_high_load(self, base_config: Dict[str, Any],
                              expected_qps: int = 1000,
                              data_volume_gb: int = 50) -> Dict[str, Any]:
        """
        针对高负载场景优化配置

        Args:
            base_config: 基础配置
            expected_qps: 预期QPS
            data_volume_gb: 数据量(GB)

        Returns:
            优化后的配置
        """
        try:
            optimized_config = base_config.copy()

            # 根据QPS调整配置
            if expected_qps > 500:
                # 高QPS配置
                if 'services' in optimized_config:
                    # 应用服务优化
                    if 'app' in optimized_config['services']:
                        app_config = optimized_config['services']['app']

                        # 增加worker数量
                        if 'command' in app_config:
                            command = app_config['command']
                            if isinstance(command, list) and 'uvicorn' in ' '.join(command):
                                # 增加workers
                                for i, cmd in enumerate(command):
                                    if cmd == '--workers':
                                        if i + 1 < len(command):
                                            command[i + 1] = str(min(int(command[i + 1]) * 2, 8))
                                        break
                                else:
                                    command.extend(['--workers', '4'])

                        # 调整连接池
                        app_config['environment'] = app_config.get('environment', [])
                        if isinstance(app_config['environment'], dict):
                            app_config['environment'].update({
                                'DATABASE_POOL_SIZE': '20',
                                'DATABASE_MAX_OVERFLOW': '30',
                                'REDIS_CONNECTION_POOL_SIZE': '50'
                            })

                    # 数据库优化
                    if 'db' in optimized_config['services']:
                        db_config = optimized_config['services']['db']

                        # 增加数据库内存
                        deploy_config = db_config.get('deploy', {}).get('resources', {})
                        limits = deploy_config.get('limits', {})

                        if 'memory' in limits:
                            # 增加25%内存
                            current_memory = self._parse_memory_string(limits['memory'])
                            new_memory = current_memory * 1.25
                            limits['memory'] = f"{new_memory:.0f}M"

                        # 添加PostgreSQL性能参数
                        db_config['environment'] = db_config.get('environment', {})
                        db_config['environment'].update({
                            'POSTGRES_SHARED_BUFFERS': '512MB',
                            'POSTGRES_EFFECTIVE_CACHE_SIZE': '1.5GB',
                            'POSTGRES_WORK_MEM': '16MB',
                            'POSTGRES_MAINTENANCE_WORK_MEM': '128MB',
                            'POSTGRES_CHECKPOINT_COMPLETION_TARGET': '0.8',
                            'POSTGRES_MAX_CONNECTIONS': '100'
                        })

                    # Redis优化
                    if 'redis' in optimized_config['services']:
                        redis_config = optimized_config['services']['redis']

                        # 增加Redis内存
                        deploy_config = redis_config.get('deploy', {}).get('resources', {})
                        limits = deploy_config.get('limits', {})

                        if 'memory' in limits:
                            current_memory = self._parse_memory_string(limits['memory'])
                            new_memory = current_memory * 1.5
                            limits['memory'] = f"{new_memory:.0f}M"

            # 数据卷优化
            if 'volumes' in optimized_config:
                # 添加性能优化选项
                for volume_name in optimized_config['volumes']:
                    volume_config = optimized_config['volumes'][volume_name]
                    if volume_config.get('driver') == 'local':
                        volume_config['driver_opts'] = volume_config.get('driver_opts', {})
                        volume_config['driver_opts'].update({
                            'type': 'none',
                            'o': 'bind'
                        })

            return {
                "optimized_config": optimized_config,
                "optimization_summary": {
                    "target_qps": expected_qps,
                    "data_volume_gb": data_volume_gb,
                    "changes_made": [
                        "Increased application workers for high QPS",
                        "Optimized database memory settings",
                        "Enhanced connection pool sizes",
                        "Improved Redis memory allocation",
                        "Added volume performance optimizations"
                    ]
                }
            }

        except Exception as e:
            return {"error": f"优化失败: {str(e)}"}

    def generate_capacity_planning_report(self, current_metrics: Dict[str, Any],
                                        growth_projection_months: int = 6) -> Dict[str, Any]:
        """
        生成容量规划报告

        Args:
            current_metrics: 当前系统指标
            growth_projection_months: 预测增长月数

        Returns:
            容量规划报告
        """
        try:
            report = {
                "current_status": current_metrics,
                "projections": {},
                "recommendations": [],
                "timeline": []
            }

            # 基于历史数据预测
            current_cpu = current_metrics.get("cpu", {}).get("usage_percent", 0)
            current_memory = current_metrics.get("memory", {}).get("percent", 0)
            current_storage = current_metrics.get("disk", {}).get("percent", 0)

            # 假设每月增长率
            monthly_growth_rate = 0.1  # 10%月增长

            for month in range(1, growth_projection_months + 1):
                projected_cpu = current_cpu * (1 + monthly_growth_rate) ** month
                projected_memory = current_memory * (1 + monthly_growth_rate) ** month
                projected_storage = current_storage * (1 + monthly_growth_rate) ** month

                report["projections"][f"month_{month}"] = {
                    "cpu_usage_percent": min(projected_cpu, 100),
                    "memory_usage_percent": min(projected_memory, 100),
                    "storage_usage_percent": min(projected_storage, 100)
                }

                # 检查是否需要扩容
                if projected_cpu > 80:
                    report["timeline"].append({
                        "month": month,
                        "issue": "CPU将达到瓶颈",
                        "action": "建议增加CPU核心或优化应用"
                    })

                if projected_memory > 85:
                    report["timeline"].append({
                        "month": month,
                        "issue": "内存将达到瓶颈",
                        "action": "建议增加内存或优化内存使用"
                    })

                if projected_storage > 80:
                    report["timeline"].append({
                        "month": month,
                        "issue": "存储空间将达到瓶颈",
                        "action": "建议清理存储或扩容"
                    })

            # 生成建议
            if any(item["cpu_usage_percent"] > 70 for item in report["projections"].values()):
                report["recommendations"].append({
                    "priority": "high",
                    "category": "CPU",
                    "action": "考虑增加CPU核心数或实施负载均衡"
                })

            if any(item["memory_usage_percent"] > 75 for item in report["projections"].values()):
                report["recommendations"].append({
                    "priority": "high",
                    "category": "Memory",
                    "action": "考虑增加内存或实施内存优化策略"
                })

            if any(item["storage_usage_percent"] > 70 for item in report["projections"].values()):
                report["recommendations"].append({
                    "priority": "medium",
                    "category": "Storage",
                    "action": "实施数据清理策略或准备存储扩容"
                })

            return report

        except Exception as e:
            return {"error": f"容量规划失败: {str(e)}"}

    def suggest_memory_optimization(self, container_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于容器指标建议内存优化策略

        Args:
            container_metrics: 容器指标列表

        Returns:
            内存优化建议
        """
        try:
            suggestions = []
            total_current_memory = 0
            total_optimized_memory = 0

            for container in container_metrics:
                container_name = container.get("name", "unknown")
                current_memory_mb = self._parse_memory_string(container.get("memory_usage", "0M"))
                current_memory_percent = float(container.get("memory_percent", 0))

                total_current_memory += current_memory_mb

                # 分析优化空间
                optimization = {
                    "container": container_name,
                    "current_memory_mb": current_memory_mb,
                    "current_percent": current_memory_percent,
                    "suggested_limit_mb": None,
                    "potential_savings_mb": 0
                }

                if current_memory_percent < 50:
                    # 内存使用率低，可以减少限制
                    suggested_mb = int(current_memory_mb * 0.7)
                    optimization["suggested_limit_mb"] = f"{suggested_mb}M"
                    optimization["potential_savings_mb"] = current_memory_mb - suggested_mb
                    optimization["reason"] = "内存使用率偏低，可减少分配"

                elif current_memory_percent > 90:
                    # 内存使用率高，需要增加限制
                    suggested_mb = int(current_memory_mb * 1.3)
                    optimization["suggested_limit_mb"] = f"{suggested_mb}M"
                    optimization["potential_savings_mb"] = -(suggested_mb - current_memory_mb)
                    optimization["reason"] = "内存使用率过高，建议增加分配"

                total_optimized_memory += current_memory_mb - optimization["potential_savings_mb"]
                suggestions.append(optimization)

            total_savings = total_current_memory - total_optimized_memory

            return {
                "analysis": {
                    "total_current_memory_mb": total_current_memory,
                    "total_optimized_memory_mb": total_optimized_memory,
                    "total_potential_savings_mb": total_savings,
                    "optimization_impact": "high" if total_savings > 512 else "medium" if total_savings > 256 else "low"
                },
                "container_suggestions": suggestions,
                "implementation_plan": self._generate_memory_optimization_plan(suggestions)
            }

        except Exception as e:
            return {"error": f"内存优化分析失败: {str(e)}"}

    # Helper methods
    def _parse_memory_string(self, memory_str: str) -> int:
        """解析内存字符串为MB"""
        if not memory_str:
            return 0

        memory_str = memory_str.strip().upper()
        if memory_str.endswith('GB'):
            return float(memory_str[:-2]) * 1024
        elif memory_str.endswith('MB'):
            return float(memory_str[:-2])
        elif memory_str.endswith('GB'):
            return float(memory_str[:-2]) * 1024
        elif memory_str.endswith('M'):
            return float(memory_str[:-1])
        elif memory_str.endswith('G'):
            return float(memory_str[:-1]) * 1024
        else:
            # 默认为MB
            return float(memory_str)

    def _evaluate_service_optimization(self, service_name: str,
                                     service_config: Dict[str, Any],
                                     host_memory_gb: float,
                                     host_cpu_cores: int) -> bool:
        """评估服务是否需要优化"""
        deploy_config = service_config.get('deploy', {}).get('resources', {})
        limits = deploy_config.get('limits', {})

        # 检查是否设置了资源限制
        has_memory_limit = 'memory' in limits
        has_cpu_limit = 'cpus' in limits

        # 检查服务类型
        service_type = self._classify_service_type(service_name, service_config)

        # 不同服务类型的优化需求
        optimization_rules = {
            "app": not (has_memory_limit and has_cpu_limit),
            "db": not has_memory_limit,  # 数据库必须设置内存限制
            "redis": not has_memory_limit,  # Redis必须设置内存限制
            "monitoring": False,  # 监控服务通常不需要优化
            "nginx": False  # 反向代理通常不需要优化
        }

        return optimization_rules.get(service_type, True)

    def _classify_service_type(self, service_name: str, service_config: Dict[str, Any]) -> str:
        """分类服务类型"""
        if 'app' in service_name.lower() or 'api' in service_name.lower():
            return "app"
        elif 'db' in service_name.lower() or 'postgres' in service_name.lower() or 'mysql' in service_name.lower():
            return "db"
        elif 'redis' in service_name.lower() or 'cache' in service_name.lower():
            return "redis"
        elif 'monitoring' in service_name.lower() or 'prometheus' in service_name.lower() or 'grafana' in service_name.lower():
            return "monitoring"
        elif 'nginx' in service_name.lower() or 'proxy' in service_name.lower():
            return "nginx"
        else:
            return "unknown"

    def _generate_optimization_recommendations(self, analysis: Dict[str, Any],
                                             host_memory_gb: float,
                                             host_cpu_cores: int) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于服务分析生成建议
        for service_name, service_data in analysis["services"].items():
            if service_data["optimization_needed"]:
                if not service_data["memory_limit"]:
                    recommendations.append(
                        f"服务 {service_name} 缺少内存限制，建议设置适当的内存限制"
                    )
                if not service_data["cpu_limit"]:
                    recommendations.append(
                        f"服务 {service_name} 缺少CPU限制，建议设置适当的CPU限制"
                    )

        # 通用建议
        if host_memory_gb >= 16:
            recommendations.append("宿主机内存充足，可考虑增加数据库shared_buffers至1GB")
        elif host_memory_gb < 8:
            recommendations.append("宿主机内存有限，建议启用内存交换空间")

        if host_cpu_cores >= 8:
            recommendations.append("CPU核心充足，可考虑增加应用并发处理能力")

        return recommendations

    def _generate_memory_optimization_plan(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成内存优化实施计划"""
        plan = []

        # 按优先级排序
        savings = [(s, abs(s["potential_savings_mb"])) for s in suggestions if s["potential_savings_mb"] > 0]
        savings.sort(key=lambda x: x[1], reverse=True)

        for suggestion, _ in savings[:5]:  # 取前5个最有价值的优化
            plan.append({
                "container": suggestion["container"],
                "action": f"调整内存限制至 {suggestion['suggested_limit_mb']}",
                "estimated_savings": f"{suggestion['potential_savings_mb']}MB",
                "priority": "high" if suggestion["potential_savings_mb"] > 256 else "medium"
            })

        return plan

# 技能实例
infrastructure_optimization_skill = InfrastructureOptimizationSkill()

# 导出技能信息
def get_skill_info():
    return {
        "name": infrastructure_optimization_skill.skill_name,
        "description": "Infrastructure Optimization - Docker/容器环境性能优化专家",
        "capabilities": infrastructure_optimization_skill.capabilities,
        "version": "1.0.0"
    }

# 主要功能函数
def analyze_docker_resources(docker_compose_path: str, host_memory_gb: float, host_cpu_cores: int):
    """分析Docker资源配置"""
    with open(docker_compose_path, 'r') as f:
        content = f.read()
    return infrastructure_optimization_skill.analyze_docker_resource_allocation(
        content, host_memory_gb, host_cpu_cores
    )

def optimize_for_high_load(base_config_path: str, expected_qps: int = 1000, data_volume_gb: int = 50):
    """高负载场景优化"""
    with open(base_config_path, 'r') as f:
        config = yaml.safe_load(f)
    return infrastructure_optimization_skill.optimize_for_high_load(config, expected_qps, data_volume_gb)

if __name__ == "__main__":
    # 示例用法
    print("Infrastructure Optimization Skill initialized")
    print(f"Capabilities: {infrastructure_optimization_skill.capabilities}")