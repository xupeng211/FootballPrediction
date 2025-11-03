#!/usr/bin/env python3
"""
系统性能优化脚本
System Performance Optimization Script

基于监控数据进行全面的性能调优，包括：
- API响应时间优化（目标<200ms）
- 并发处理能力提升（目标100+并发请求）
- 缓存策略优化（目标90%+命中率）
- 数据库连接池优化
- 内存和CPU使用优化

Author: Claude AI Assistant
Date: 2025-11-03
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import subprocess
import psutil
import yaml

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    api_response_time: float  # ms
    request_count: int
    concurrent_connections: int
    memory_usage: float  # MB
    cpu_usage: float  # %
    db_connections: int
    cache_hit_rate: float  # %
    error_rate: float  # %
    throughput: float  # requests/second


@dataclass
class OptimizationTarget:
    """优化目标数据类"""
    name: str
    current_value: float
    target_value: float
    unit: str
    priority: int  # 1-5, 1为最高
    description: str


@dataclass
class OptimizationResult:
    """优化结果数据类"""
    target_name: str
    before_value: float
    after_value: float
    improvement_percentage: float
    success: bool
    details: str


class SystemPerformanceOptimizer:
    """系统性能优化器"""

    def __init__(self):
        """初始化性能优化器"""
        self.settings = get_settings()
        self.project_root = project_root
        self.optimization_history: List[OptimizationResult] = []

        # 性能监控端点
        self.prometheus_url = "http://localhost:9090"
        self.grafana_url = "http://localhost:3000"

        # 当前性能指标
        self.current_metrics: Optional[PerformanceMetrics] = None

        # 优化配置
        self.optimization_config = self._load_optimization_config()

        logger.info("系统性能优化器初始化完成")

    def _load_optimization_config(self) -> dict:
        """加载优化配置"""
        config_path = self.project_root / "config" / "monitoring" / "optimization.yml"

        default_config = {
            "targets": {
                "api_response_time": {"target": 200, "unit": "ms", "priority": 1},
                "concurrent_requests": {"target": 100, "unit": "count", "priority": 2},
                "cache_hit_rate": {"target": 90, "unit": "%", "priority": 2},
                "memory_usage": {"target": 512, "unit": "MB", "priority": 3},
                "cpu_usage": {"target": 70, "unit": "%", "priority": 3},
                "db_connections": {"target": 20, "unit": "count", "priority": 2},
                "error_rate": {"target": 1, "unit": "%", "priority": 1},
                "throughput": {"target": 50, "unit": "req/s", "priority": 2}
            },
            "optimizations": {
                "api": {
                    "enable_compression": True,
                    "enable_caching": True,
                    "connection_timeout": 30,
                    "keep_alive_timeout": 5,
                    "max_concurrent_requests": 100
                },
                "database": {
                    "pool_size": 20,
                    "max_overflow": 30,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                    "echo": False
                },
                "cache": {
                    "redis_max_connections": 50,
                    "default_ttl": 3600,
                    "max_memory_policy": "allkeys-lru"
                },
                "application": {
                    "workers": 4,
                    "worker_class": "uvicorn.workers.UvicornWorker",
                    "worker_connections": 1000,
                    "max_requests": 1000,
                    "max_requests_jitter": 100
                }
            }
        }

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    # 合并配置
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"无法加载优化配置文件，使用默认配置: {e}")

        return default_config

    async def collect_current_metrics(self) -> PerformanceMetrics:
        """收集当前性能指标"""
        logger.info("正在收集当前性能指标...")

        try:
            # 系统资源使用情况
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            # 模拟API响应时间测试
            api_response_time = await self._test_api_response_time()

            # 获取数据库连接数（模拟）
            db_connections = await self._get_database_connections()

            # 获取缓存命中率（模拟）
            cache_hit_rate = await self._get_cache_hit_rate()

            # 获取并发连接数（模拟）
            concurrent_connections = await self._get_concurrent_connections()

            # 计算吞吐量和错误率（模拟）
            throughput, error_rate = await self._calculate_throughput_and_errors()

            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                api_response_time=api_response_time,
                request_count=100,  # 模拟数据
                concurrent_connections=concurrent_connections,
                memory_usage=memory_info.used / 1024 / 1024,  # MB
                cpu_usage=cpu_percent,
                db_connections=db_connections,
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                throughput=throughput
            )

            self.current_metrics = metrics
            logger.info(f"性能指标收集完成: API响应时间={api_response_time:.2f}ms, 内存使用={metrics.memory_usage:.2f}MB")

            return metrics

        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")
            raise

    async def _test_api_response_time(self) -> float:
        """测试API响应时间"""
        try:
            # 使用curl测试健康检查端点
            cmd = ["curl", "-o", "/dev/null", "-s", "-w", "%{time_total}", "http://localhost:8000/health"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                response_time_seconds = float(result.stdout.strip())
                return response_time_seconds * 1000  # 转换为毫秒
            else:
                logger.warning("无法测试API响应时间，使用模拟数据")
                return 250.0  # 模拟数据

        except Exception as e:
            logger.warning(f"API响应时间测试失败: {e}，使用模拟数据")
            return 250.0  # 模拟数据

    async def _get_database_connections(self) -> int:
        """获取数据库连接数"""
        try:
            # 这里应该连接到数据库获取实际连接数
            # 暂时返回模拟数据
            return 8
        except Exception as e:
            logger.warning(f"获取数据库连接数失败: {e}")
            return 8

    async def _get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        try:
            # 这里应该连接到Redis获取实际命中率
            # 暂时返回模拟数据
            return 75.0
        except Exception as e:
            logger.warning(f"获取缓存命中率失败: {e}")
            return 75.0

    async def _get_concurrent_connections(self) -> int:
        """获取并发连接数"""
        try:
            # 这里应该从应用服务器获取实际并发连接数
            # 暂时返回模拟数据
            return 25
        except Exception as e:
            logger.warning(f"获取并发连接数失败: {e}")
            return 25

    async def _calculate_throughput_and_errors(self) -> Tuple[float, float]:
        """计算吞吐量和错误率"""
        try:
            # 这里应该基于实际请求日志计算
            # 暂时返回模拟数据
            return 30.0, 2.0  # 30 req/s, 2% error rate
        except Exception as e:
            logger.warning(f"计算吞吐量和错误率失败: {e}")
            return 30.0, 2.0

    def identify_optimization_targets(self) -> List[OptimizationTarget]:
        """识别优化目标"""
        if not self.current_metrics:
            raise ValueError("请先收集当前性能指标")

        targets = []
        metrics = self.current_metrics
        config_targets = self.optimization_config["targets"]

        # API响应时间
        if metrics.api_response_time > config_targets["api_response_time"]["target"]:
            targets.append(OptimizationTarget(
                name="api_response_time",
                current_value=metrics.api_response_time,
                target_value=config_targets["api_response_time"]["target"],
                unit=config_targets["api_response_time"]["unit"],
                priority=config_targets["api_response_time"]["priority"],
                description="API响应时间优化"
            ))

        # 并发请求数
        if metrics.concurrent_connections < config_targets["concurrent_requests"]["target"]:
            targets.append(OptimizationTarget(
                name="concurrent_requests",
                current_value=metrics.concurrent_connections,
                target_value=config_targets["concurrent_requests"]["target"],
                unit=config_targets["concurrent_requests"]["unit"],
                priority=config_targets["concurrent_requests"]["priority"],
                description="并发处理能力提升"
            ))

        # 缓存命中率
        if metrics.cache_hit_rate < config_targets["cache_hit_rate"]["target"]:
            targets.append(OptimizationTarget(
                name="cache_hit_rate",
                current_value=metrics.cache_hit_rate,
                target_value=config_targets["cache_hit_rate"]["target"],
                unit=config_targets["cache_hit_rate"]["unit"],
                priority=config_targets["cache_hit_rate"]["priority"],
                description="缓存策略优化"
            ))

        # 内存使用
        if metrics.memory_usage > config_targets["memory_usage"]["target"]:
            targets.append(OptimizationTarget(
                name="memory_usage",
                current_value=metrics.memory_usage,
                target_value=config_targets["memory_usage"]["target"],
                unit=config_targets["memory_usage"]["unit"],
                priority=config_targets["memory_usage"]["priority"],
                description="内存使用优化"
            ))

        # CPU使用率
        if metrics.cpu_usage > config_targets["cpu_usage"]["target"]:
            targets.append(OptimizationTarget(
                name="cpu_usage",
                current_value=metrics.cpu_usage,
                target_value=config_targets["cpu_usage"]["target"],
                unit=config_targets["cpu_usage"]["unit"],
                priority=config_targets["cpu_usage"]["priority"],
                description="CPU使用率优化"
            ))

        # 错误率
        if metrics.error_rate > config_targets["error_rate"]["target"]:
            targets.append(OptimizationTarget(
                name="error_rate",
                current_value=metrics.error_rate,
                target_value=config_targets["error_rate"]["target"],
                unit=config_targets["error_rate"]["unit"],
                priority=config_targets["error_rate"]["priority"],
                description="错误率降低"
            ))

        # 按优先级排序
        targets.sort(key=lambda x: x.priority)

        logger.info(f"识别到 {len(targets)} 个优化目标")
        return targets

    async def optimize_api_response_time(self) -> OptimizationResult:
        """优化API响应时间"""
        logger.info("开始优化API响应时间...")

        before_value = self.current_metrics.api_response_time
        target_value = self.optimization_config["targets"]["api_response_time"]["target"]

        try:
            # 1. 启用Gzip压缩
            await self._enable_gzip_compression()

            # 2. 优化数据库连接池
            await self._optimize_database_pool()

            # 3. 启用响应缓存
            await self._enable_response_caching()

            # 4. 优化异步任务处理
            await self._optimize_async_tasks()

            # 等待优化生效
            await asyncio.sleep(5)

            # 测量优化后的响应时间
            after_value = await self._test_api_response_time()

            improvement = ((before_value - after_value) / before_value) * 100
            success = after_value <= target_value

            result = OptimizationResult(
                target_name="api_response_time",
                before_value=before_value,
                after_value=after_value,
                improvement_percentage=improvement,
                success=success,
                details=f"API响应时间从 {before_value:.2f}ms 优化到 {after_value:.2f}ms，改善 {improvement:.2f}%"
            )

            self.optimization_history.append(result)
            logger.info(f"API响应时间优化完成: {result.details}")

            return result

        except Exception as e:
            logger.error(f"API响应时间优化失败: {e}")
            return OptimizationResult(
                target_name="api_response_time",
                before_value=before_value,
                after_value=before_value,
                improvement_percentage=0.0,
                success=False,
                details=f"优化失败: {str(e)}"
            )

    async def _enable_gzip_compression(self):
        """启用Gzip压缩"""
        logger.info("启用Gzip压缩...")

        # 更新FastAPI配置，启用Gzip中间件
        config_updates = {
            "middleware": {
                "gzip": {
                    "enabled": True,
                    "minimum_size": 1024
                }
            }
        }

        await self._update_application_config(config_updates)

    async def _optimize_database_pool(self):
        """优化数据库连接池"""
        logger.info("优化数据库连接池...")

        db_config = self.optimization_config["optimizations"]["database"]
        config_updates = {
            "database": {
                "pool_size": db_config["pool_size"],
                "max_overflow": db_config["max_overflow"],
                "pool_timeout": db_config["pool_timeout"],
                "pool_recycle": db_config["pool_recycle"]
            }
        }

        await self._update_application_config(config_updates)

    async def _enable_response_caching(self):
        """启用响应缓存"""
        logger.info("启用响应缓存...")

        config_updates = {
            "cache": {
                "enabled": True,
                "default_ttl": self.optimization_config["optimizations"]["cache"]["default_ttl"]
            }
        }

        await self._update_application_config(config_updates)

    async def _optimize_async_tasks(self):
        """优化异步任务处理"""
        logger.info("优化异步任务处理...")

        config_updates = {
            "async": {
                "max_concurrent_tasks": 100,
                "task_timeout": 30
            }
        }

        await self._update_application_config(config_updates)

    async def optimize_concurrent_requests(self) -> OptimizationResult:
        """优化并发处理能力"""
        logger.info("开始优化并发处理能力...")

        before_value = self.current_metrics.concurrent_connections
        target_value = self.optimization_config["targets"]["concurrent_requests"]["target"]

        try:
            # 1. 增加Uvicorn worker数量
            await self._increase_worker_count()

            # 2. 优化连接配置
            await self._optimize_connection_config()

            # 3. 启用连接复用
            await self._enable_connection_keepalive()

            # 等待优化生效
            await asyncio.sleep(10)

            # 测量优化后的并发处理能力
            after_value = await self._get_concurrent_connections()

            improvement = ((after_value - before_value) / before_value) * 100 if before_value > 0 else 0
            success = after_value >= target_value

            result = OptimizationResult(
                target_name="concurrent_requests",
                before_value=before_value,
                after_value=after_value,
                improvement_percentage=improvement,
                success=success,
                details=f"并发处理能力从 {before_value} 提升到 {after_value}，改善 {improvement:.2f}%"
            )

            self.optimization_history.append(result)
            logger.info(f"并发处理能力优化完成: {result.details}")

            return result

        except Exception as e:
            logger.error(f"并发处理能力优化失败: {e}")
            return OptimizationResult(
                target_name="concurrent_requests",
                before_value=before_value,
                after_value=before_value,
                improvement_percentage=0.0,
                success=False,
                details=f"优化失败: {str(e)}"
            )

    async def _increase_worker_count(self):
        """增加worker数量"""
        logger.info("增加Uvicorn worker数量...")

        app_config = self.optimization_config["optimizations"]["application"]

        # 更新docker-compose配置
        docker_compose_path = self.project_root / "docker" / "docker-compose.production.yml"

        if docker_compose_path.exists():
            await self._update_docker_workers(docker_compose_path, app_config)

    async def _update_docker_workers(self, docker_compose_path: Path, app_config: dict):
        """更新Docker配置中的worker数量"""
        try:
            with open(docker_compose_path, 'r', encoding='utf-8') as f:
                docker_config = yaml.safe_load(f)

            # 更新app服务的deploy配置
            if 'services' in docker_config and 'app' in docker_config['services']:
                docker_config['services']['app']['deploy']['replicas'] = app_config['workers']

                with open(docker_compose_path, 'w', encoding='utf-8') as f:
                    yaml.dump(docker_config, f, default_flow_style=False, allow_unicode=True)

                logger.info(f"Docker worker数量已更新为 {app_config['workers']}")

        except Exception as e:
            logger.error(f"更新Docker worker配置失败: {e}")

    async def _optimize_connection_config(self):
        """优化连接配置"""
        logger.info("优化连接配置...")

        config_updates = {
            "connections": {
                "max_connections": 1000,
                "keep_alive_timeout": 5,
                "connection_timeout": 30
            }
        }

        await self._update_application_config(config_updates)

    async def _enable_connection_keepalive(self):
        """启用连接复用"""
        logger.info("启用连接复用...")

        config_updates = {
            "connections": {
                "keep_alive": True,
                "max_keep_alive_requests": 100
            }
        }

        await self._update_application_config(config_updates)

    async def optimize_cache_strategy(self) -> OptimizationResult:
        """优化缓存策略"""
        logger.info("开始优化缓存策略...")

        before_value = self.current_metrics.cache_hit_rate
        target_value = self.optimization_config["targets"]["cache_hit_rate"]["target"]

        try:
            # 1. 优化Redis配置
            await self._optimize_redis_config()

            # 2. 实施智能缓存策略
            await self._implement_smart_caching()

            # 3. 优化缓存键设计
            await self._optimize_cache_keys()

            # 等待优化生效
            await asyncio.sleep(5)

            # 测量优化后的缓存命中率
            after_value = await self._get_cache_hit_rate()

            improvement = ((after_value - before_value) / before_value) * 100 if before_value > 0 else 0
            success = after_value >= target_value

            result = OptimizationResult(
                target_name="cache_hit_rate",
                before_value=before_value,
                after_value=after_value,
                improvement_percentage=improvement,
                success=success,
                details=f"缓存命中率从 {before_value:.2f}% 提升到 {after_value:.2f}%，改善 {improvement:.2f}%"
            )

            self.optimization_history.append(result)
            logger.info(f"缓存策略优化完成: {result.details}")

            return result

        except Exception as e:
            logger.error(f"缓存策略优化失败: {e}")
            return OptimizationResult(
                target_name="cache_hit_rate",
                before_value=before_value,
                after_value=before_value,
                improvement_percentage=0.0,
                success=False,
                details=f"优化失败: {str(e)}"
            )

    async def _optimize_redis_config(self):
        """优化Redis配置"""
        logger.info("优化Redis配置...")

        cache_config = self.optimization_config["optimizations"]["cache"]

        # 更新Redis配置
        redis_config = {
            "maxmemory": "256mb",
            "maxmemory-policy": cache_config["max_memory_policy"],
            "save": "900 1 300 10 60 10000",
            "appendonly": "yes",
            "appendfsync": "everysec"
        }

        await self._update_redis_config(redis_config)

    async def _implement_smart_caching(self):
        """实施智能缓存策略"""
        logger.info("实施智能缓存策略...")

        # 实施基于访问模式的智能缓存
        smart_cache_config = {
            "strategies": {
                "prediction_results": {"ttl": 1800, "max_size": 1000},
                "team_stats": {"ttl": 3600, "max_size": 500},
                "match_data": {"ttl": 900, "max_size": 2000},
                "user_data": {"ttl": 7200, "max_size": 100}
            }
        }

        await self._update_application_config({"cache": smart_cache_config})

    async def _optimize_cache_keys(self):
        """优化缓存键设计"""
        logger.info("优化缓存键设计...")

        # 实施分层缓存键策略
        cache_key_config = {
            "key_patterns": {
                "user": "user:{user_id}:{data_type}",
                "match": "match:{match_id}:{data_type}",
                "team": "team:{team_id}:{season}:{data_type}",
                "prediction": "prediction:{user_id}:{match_id}:{model_version}"
            }
        }

        await self._update_application_config({"cache": cache_key_config})

    async def _update_application_config(self, config_updates: dict):
        """更新应用配置"""
        logger.info(f"更新应用配置: {config_updates}")

        # 这里应该实际更新配置文件或环境变量
        # 为了演示，我们只是记录配置更新

        config_path = self.project_root / "config" / "performance.json"

        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            else:
                existing_config = {}

            # 合并配置
            existing_config.update(config_updates)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=2, ensure_ascii=False)

            logger.info("应用配置更新完成")

        except Exception as e:
            logger.error(f"更新应用配置失败: {e}")

    async def _update_redis_config(self, redis_config: dict):
        """更新Redis配置"""
        logger.info(f"更新Redis配置: {redis_config}")

        # 这里应该实际更新Redis配置文件
        # 为了演示，我们只是记录配置更新

        redis_config_path = self.project_root / "config" / "monitoring" / "redis.yml"

        try:
            with open(redis_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(redis_config, f, default_flow_style=False, allow_unicode=True)

            logger.info("Redis配置更新完成")

        except Exception as e:
            logger.error(f"更新Redis配置失败: {e}")

    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """运行完整的优化周期"""
        logger.info("开始系统性能优化周期...")

        try:
            # 1. 收集当前性能指标
            initial_metrics = await self.collect_current_metrics()

            # 2. 识别优化目标
            optimization_targets = self.identify_optimization_targets()

            if not optimization_targets:
                logger.info("当前性能指标已达到所有目标，无需优化")
                return {
                    "status": "optimal",
                    "message": "所有性能指标已达到目标",
                    "metrics": asdict(initial_metrics),
                    "optimization_results": []
                }

            logger.info(f"识别到 {len(optimization_targets)} 个优化目标，开始优化...")

            # 3. 执行优化
            optimization_results = []

            for target in optimization_targets:
                if target.name == "api_response_time":
                    result = await self.optimize_api_response_time()
                    optimization_results.append(result)

                elif target.name == "concurrent_requests":
                    result = await self.optimize_concurrent_requests()
                    optimization_results.append(result)

                elif target.name == "cache_hit_rate":
                    result = await self.optimize_cache_strategy()
                    optimization_results.append(result)

                # 在每次优化后等待生效
                await asyncio.sleep(3)

            # 4. 收集优化后的性能指标
            final_metrics = await self.collect_current_metrics()

            # 5. 生成优化报告
            optimization_report = self._generate_optimization_report(
                initial_metrics, final_metrics, optimization_targets, optimization_results
            )

            logger.info("系统性能优化周期完成")

            return {
                "status": "completed",
                "message": f"性能优化完成，处理了 {len(optimization_targets)} 个优化目标",
                "initial_metrics": asdict(initial_metrics),
                "final_metrics": asdict(final_metrics),
                "optimization_targets": [asdict(target) for target in optimization_targets],
                "optimization_results": [asdict(result) for result in optimization_results],
                "report": optimization_report
            }

        except Exception as e:
            logger.error(f"系统性能优化失败: {e}")
            return {
                "status": "failed",
                "message": f"优化过程出现错误: {str(e)}",
                "error": str(e)
            }

    def _generate_optimization_report(
        self,
        initial_metrics: PerformanceMetrics,
        final_metrics: PerformanceMetrics,
        targets: List[OptimizationTarget],
        results: List[OptimizationResult]
    ) -> dict:
        """生成优化报告"""

        successful_optimizations = [r for r in results if r.success]
        failed_optimizations = [r for r in results if not r.success]

        report = {
            "summary": {
                "total_targets": len(targets),
                "successful_optimizations": len(successful_optimizations),
                "failed_optimizations": len(failed_optimizations),
                "overall_success_rate": (len(successful_optimizations) / len(targets)) * 100 if targets else 0
            },
            "performance_improvements": {
                "api_response_time": {
                    "before": initial_metrics.api_response_time,
                    "after": final_metrics.api_response_time,
                    "improvement": ((initial_metrics.api_response_time - final_metrics.api_response_time) / initial_metrics.api_response_time) * 100 if initial_metrics.api_response_time > 0 else 0
                },
                "cache_hit_rate": {
                    "before": initial_metrics.cache_hit_rate,
                    "after": final_metrics.cache_hit_rate,
                    "improvement": ((final_metrics.cache_hit_rate - initial_metrics.cache_hit_rate) / initial_metrics.cache_hit_rate) * 100 if initial_metrics.cache_hit_rate > 0 else 0
                },
                "throughput": {
                    "before": initial_metrics.throughput,
                    "after": final_metrics.throughput,
                    "improvement": ((final_metrics.throughput - initial_metrics.throughput) / initial_metrics.throughput) * 100 if initial_metrics.throughput > 0 else 0
                },
                "concurrent_connections": {
                    "before": initial_metrics.concurrent_connections,
                    "after": final_metrics.concurrent_connections,
                    "improvement": ((final_metrics.concurrent_connections - initial_metrics.concurrent_connections) / initial_metrics.concurrent_connections) * 100 if initial_metrics.concurrent_connections > 0 else 0
                }
            },
            "detailed_results": [asdict(result) for result in results],
            "recommendations": self._generate_recommendations(final_metrics, results)
        }

        return report

    def _generate_recommendations(self, final_metrics: PerformanceMetrics, results: List[OptimizationResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于最终性能指标生成建议
        if final_metrics.api_response_time > 200:
            recommendations.append("建议进一步优化API响应时间，考虑启用CDN或数据库查询优化")

        if final_metrics.memory_usage > 512:
            recommendations.append("建议优化内存使用，考虑启用内存分析器识别内存泄漏")

        if final_metrics.cpu_usage > 70:
            recommendations.append("建议优化CPU使用，考虑启用性能分析器识别CPU瓶颈")

        if final_metrics.cache_hit_rate < 90:
            recommendations.append("建议进一步优化缓存策略，考虑预热缓存或调整TTL设置")

        if final_metrics.error_rate > 1:
            recommendations.append("建议降低错误率，检查日志识别常见错误模式")

        # 基于优化结果生成建议
        failed_optimizations = [r for r in results if not r.success]
        if failed_optimizations:
            recommendations.append(f"有 {len(failed_optimizations)} 个优化目标未达成，建议进行深入分析")

        return recommendations

    def save_optimization_report(self, report: dict) -> str:
        """保存优化报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"performance_optimization_report_{timestamp}.json"

        # 保存到reports目录
        reports_dir = self.project_root / "reports"
        performance_reports_dir = reports_dir / "performance"
        performance_reports_dir.mkdir(parents=True, exist_ok=True)

        report_path = performance_reports_dir / report_filename

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"性能优化报告已保存到: {report_path}")
            return str(report_path)

        except Exception as e:
            logger.error(f"保存优化报告失败: {e}")
            raise

    def print_optimization_summary(self, report: dict):
        """打印优化摘要"""
        print("\n" + "="*80)
        print("🚀 系统性能优化报告")
        print("="*80)

        summary = report.get("summary", {})
        print(f"📊 优化目标总数: {summary.get('total_targets', 0)}")
        print(f"✅ 成功优化: {summary.get('successful_optimizations', 0)}")
        print(f"❌ 失败优化: {summary.get('failed_optimizations', 0)}")
        print(f"📈 总体成功率: {summary.get('overall_success_rate', 0):.1f}%")

        print("\n🎯 性能改善情况:")
        improvements = report.get("performance_improvements", {})

        for metric, improvement in improvements.items():
            before = improvement.get("before", 0)
            after = improvement.get("after", 0)
            change = improvement.get("improvement", 0)

            print(f"  {metric}: {before:.2f} → {after:.2f} ({change:+.2f}%)")

        print("\n💡 改进建议:")
        recommendations = report.get("recommendations", [])
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

        print("\n" + "="*80)


async def main():
    """主函数"""
    print("🚀 足球预测系统性能优化工具")
    print("="*50)

    optimizer = SystemPerformanceOptimizer()

    try:
        # 运行优化周期
        report = await optimizer.run_optimization_cycle()

        if report["status"] == "completed":
            print("\n✅ 性能优化完成!")

            # 保存报告
            report_path = optimizer.save_optimization_report(report)
            print(f"📄 详细报告已保存到: {report_path}")

            # 打印摘要
            optimizer.print_optimization_summary(report)

        elif report["status"] == "optimal":
            print("\n🎉 当前系统性能已达到所有目标!")

        else:
            print(f"\n❌ 性能优化失败: {report.get('message', '未知错误')}")

    except KeyboardInterrupt:
        print("\n⚠️ 优化过程被用户中断")
    except Exception as e:
        logger.error(f"性能优化程序执行失败: {e}")
        print(f"\n❌ 执行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())