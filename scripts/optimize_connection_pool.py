#!/usr/bin/env python3
"""
数据库连接池优化脚本
Database Connection Pool Optimization Script

优化数据库连接池配置，提升查询性能和并发处理能力。
"""

import asyncio
import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionPoolOptimizer:
    """连接池优化器"""

    def __init__(self):
        """初始化连接池优化器"""
        self.settings = get_settings()
        self.engines = {}
        self.pool_configs = {}

    def generate_optimized_pool_configs(self) -> dict[str, dict[str, Any]]:
        """生成优化的连接池配置"""
        logger.info("🔧 生成优化的连接池配置...")

        configs = {
            'default': {
                'pool_size': 20,
                'max_overflow': 30,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit',
                'echo': False,
                'future': True,
                'description': '默认连接池配置'
            },
            'high_concurrency': {
                'pool_size': 50,
                'max_overflow': 100,
                'pool_timeout': 60,
                'pool_recycle': 1800,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit',
                'echo': False,
                'future': True,
                'description': '高并发连接池配置'
            },
            'low_memory': {
                'pool_size': 5,
                'max_overflow': 10,
                'pool_timeout': 30,
                'pool_recycle': 7200,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit',
                'echo': False,
                'future': True,
                'description': '低内存连接池配置'
            },
            'batch_processing': {
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 120,
                'pool_recycle': 900,
                'pool_pre_ping': True,
                'pool_reset_on_return': 'commit',
                'echo': False,
                'future': True,
                'description': '批处理连接池配置'
            }
        }

        self.pool_configs = configs
        return configs

    def create_engine_with_config(self, config_name: str) -> Any:
        """根据配置创建引擎"""
        if config_name not in self.pool_configs:
            raise ValueError(f"未知的连接池配置: {config_name}")

        config = self.pool_configs[config_name]

        engine = create_async_engine(
            self.settings.database_url,
            **{k: v for k, v in config.items() if k != 'description'}
        )

        self.engines[config_name] = engine
        logger.info(f"✅ 创建引擎 {config_name}: {config['description']}")
        return engine

    async def test_connection_pool(self,
    config_name: str,
    concurrent_connections: int = 20) -> dict[str,
    Any]:
        """测试连接池性能"""
        logger.info(f"🧪 测试连接池配置: {config_name}")

        if config_name not in self.engines:
            self.create_engine_with_config(config_name)

        engine = self.engines[config_name]
        results = {
            'config_name': config_name,
            'concurrent_connections': concurrent_connections,
            'total_time': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'average_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf'),
            'connection_errors': []
        }

        async def test_single_connection(conn_id: int) -> dict[str, Any]:
            """测试单个连接"""
            start_time = time.time()
            result = {'conn_id': conn_id, 'success': False, 'error': None, 'response_time': 0}

            try:
                async with AsyncSession(engine) as session:
                    # 执行简单查询
                    await session.execute("SELECT 1")

                    response_time = time.time() - start_time
                    result.update({
                        'success': True,
                        'response_time': response_time
                    })

            except Exception as e:
                response_time = time.time() - start_time
                result.update({
                    'success': False,
                    'error': str(e),
                    'response_time': response_time
                })

            return result

        # 并发测试连接
        start_time = time.time()
        tasks = [test_single_connection(i) for i in range(concurrent_connections)]
        test_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # 统计结果
        successful_connections = 0
        failed_connections = 0
        response_times = []
        connection_errors = []

        for result in test_results:
            if isinstance(result, Exception):
                failed_connections += 1
                connection_errors.append(str(result))
            elif result['success']:
                successful_connections += 1
                response_times.append(result['response_time'])
            else:
                failed_connections += 1
                connection_errors.append(result['error'])

        # 计算统计信息
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = max_response_time = min_response_time = 0

        results.update({
            'total_time': total_time,
            'successful_connections': successful_connections,
            'failed_connections': failed_connections,
            'average_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'min_response_time': min_response_time,
            'connection_errors': connection_errors[:5]  # 只保留前5个错误
        })

        logger.info(f"📊 连接池 {config_name} 测试结果:")
        logger.info(f"  - 成功连接: {successful_connections}/{concurrent_connections}")
        logger.info(f"  - 失败连接: {failed_connections}")
        logger.info(f"  - 平均响应时间: {avg_response_time:.3f}s")
        logger.info(f"  - 最大响应时间: {max_response_time:.3f}s")

        return results

    async def compare_pool_configs(self) -> dict[str, Any]:
        """比较不同连接池配置的性能"""
        logger.info("📊 比较不同连接池配置的性能...")

        configs_to_test = ['default', 'high_concurrency', 'low_memory', 'batch_processing']
        comparison_results = {}

        for config_name in configs_to_test:
            try:
                results = await self.test_connection_pool(config_name,
    concurrent_connections=20)
                comparison_results[config_name] = results

                # 短暂休息以避免连接池冲突
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ 测试连接池配置 {config_name} 失败: {e}")
                comparison_results[config_name] = {'error': str(e)}

        return comparison_results

    async def analyze_pool_usage(self) -> dict[str, Any]:
        """分析连接池使用情况"""
        logger.info("🔍 分析连接池使用情况...")

        pool_usage_data = {}

        for config_name, engine in self.engines.items():
            try:
                pool = engine.pool

                pool_info = {
                    'config_name': config_name,
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                    'total_connections': pool.checkedin() + pool.checkedout(),
                    'available_connections': pool.checkedin(),
                    'busy_connections': pool.checkedout(),
                    'usage_percentage': 0
                }

                total = pool_info['total_connections']
                if total > 0:
                    pool_info['usage_percentage'] = (pool_info['busy_connections'] / total) * 100

                pool_usage_data[config_name] = pool_info

                logger.info(f"📊 连接池 {config_name} 使用情况:")
                logger.info(f"  - 总连接数: {pool_info['total_connections']}")
                logger.info(f"  - 可用连接数: {pool_info['available_connections']}")
                logger.info(f"  - 忙碌连接数: {pool_info['busy_connections']}")
                logger.info(f"  - 使用率: {pool_info['usage_percentage']:.1f}%")

            except Exception as e:
                logger.error(f"❌ 分析连接池 {config_name} 失败: {e}")
                pool_usage_data[config_name] = {'error': str(e)}

        return pool_usage_data

    async def generate_optimization_recommendations(self,
    comparison_results: dict[str,
    Any]) -> list[str]:
        """生成优化建议"""
        logger.info("💡 生成连接池优化建议...")

        recommendations = []

        # 分析测试结果
        successful_configs = {
            name: results for name, results in comparison_results.items()
            if 'error' not in results and results['successful_connections'] > 0
        }

        if not successful_configs:
            return ["❌ 所有连接池配置测试都失败，请检查数据库连接"]

        # 找出最佳配置
        best_config = min(successful_configs.items(),
    key=lambda x: x[1]['average_response_time'])
        best_config_name, best_config_results = best_config

        recommendations.append(f"🎯 推荐使用连接池配置: {best_config_name}")
        recommendations.append(f"📊 平均响应时间: {best_config_results['average_response_time']:.3f}s")
        recommendations.append(f"✅ 成功率: {(best_config_results['successful_connections']/best_config_results['concurrent_connections'])*100:.1f}%")

        # 分析不同使用场景的推荐
        if 'high_concurrency' in successful_configs:
            high_concurrency = successful_configs['high_concurrency']
            if high_concurrency['successful_connections'] >= high_concurrency['concurrent_connections'] * 0.9:
                recommendations.append("🚀 对于高并发场景，推荐使用 high_concurrency 配置")

        if 'low_memory' in successful_configs:
            low_memory = successful_configs['low_memory']
            if low_memory['successful_connections'] >= low_memory['concurrent_connections'] * 0.8:
                recommendations.append("💾 对于内存受限环境，推荐使用 low_memory 配置")

        # 通用优化建议
        recommendations.extend([
            "🔧 根据实际负载调整 pool_size 和 max_overflow",
            "⏰ 设置合适的 pool_timeout 以避免超时",
            "🔄 定期回收连接 (pool_recycle) 避免连接过期",
            "✅ 启用 pool_pre_ping 确保连接有效性",
            "📊 监控连接池使用情况，适时调整配置"
        ])

        return recommendations

    async def run_optimization_analysis(self) -> dict[str, Any]:
        """运行完整的连接池优化分析"""
        logger.info("🚀 开始连接池优化分析...")

        start_time = time.time()

        try:
            # 生成配置
            configs = self.generate_optimized_pool_configs()

            # 比较不同配置的性能
            comparison_results = await self.compare_pool_configs()

            # 分析连接池使用情况
            pool_usage = await self.analyze_pool_usage()

            # 生成优化建议
            recommendations = await self.generate_optimization_recommendations(comparison_results)

            analysis_time = time.time() - start_time

            # 生成分析报告
            report = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'analysis_time': analysis_time,
                'pool_configs': configs,
                'performance_comparison': comparison_results,
                'pool_usage_analysis': pool_usage,
                'recommendations': recommendations,
                'summary': {
                    'total_configs_tested': len(comparison_results),
                    'successful_configs': len([r for r in comparison_results.values() if 'error' not in r]),


                    'best_config': max(
                        [(name,
    results) for name,
    results in comparison_results.items() if 'error' not in results],

                        key=lambda x: x[1]['successful_connections']
                    )[0] if comparison_results else None
                }
            }

            logger.info(f"✅ 连接池优化分析完成，耗时: {analysis_time:.2f}s")

            return report

        except Exception as e:
            logger.error(f"❌ 连接池优化分析失败: {e}")
            raise

    async def close(self):
        """关闭所有引擎"""
        for config_name, engine in self.engines.items():
            try:
                await engine.dispose()
                logger.info(f"✅ 引擎 {config_name} 已关闭")
            except Exception as e:
                logger.error(f"❌ 关闭引擎 {config_name} 失败: {e}")


async def main():
    """主函数"""
    optimizer = ConnectionPoolOptimizer()

    try:
        # 运行优化分析
        report = await optimizer.run_optimization_analysis()

        # 保存分析报告
        import json
        with open('connection_pool_optimization_report.json',
    'w',
    encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info("📄 优化报告已保存到 connection_pool_optimization_report.json")

        # 输出摘要
        if report['summary']['best_config']:
            report['summary']['best_config'][0]

        # 输出优化建议
        for _i, _rec in enumerate(report['recommendations'], 1):
            pass

    except Exception as e:
        logger.error(f"❌ 优化分析过程失败: {e}")
        raise
    finally:
        await optimizer.close()


if __name__ == "__main__":
    asyncio.run(main())
