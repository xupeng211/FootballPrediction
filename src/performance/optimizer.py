"""
性能优化服务
Performance Optimization Service

提供系统性能优化功能。
Provides system performance optimization features.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .monitoring import get_system_monitor, get_performance_analyzer
from ..cache.unified_cache import get_cache_manager

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """性能优化器"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.system_monitor = get_system_monitor()
        self.performance_analyzer = get_performance_analyzer()
        self.cache_manager = get_cache_manager()

    async def optimize_database_indexes(self) -> Dict[str, Any]:
        """优化数据库索引"""
        logger.info("Starting database index optimization")

        indexes_to_create = [
            # 比赛数据索引
            {
                'name': 'idx_matches_league_date',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_league_date
                    ON matches(league_id, match_date DESC)
                """
            },
            {
                'name': 'idx_matches_teams',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_teams
                    ON matches(home_team_id, away_team_id)
                """
            },
            {
                'name': 'idx_matches_status',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_status
                    ON matches(status) WHERE status != 'finished'
                """
            },

            # 预测数据索引
            {
                'name': 'idx_predictions_match',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_match
                    ON predictions(match_id)
                """
            },
            {
                'name': 'idx_predictions_created',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_created
                    ON predictions(created_at DESC)
                """
            },
            {
                'name': 'idx_predictions_confidence',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_confidence
                    ON predictions(confidence_score)
                """
            },

            # 用户数据索引
            {
                'name': 'idx_users_email',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email
                    ON users(email)
                """
            },
            {
                'name': 'idx_users_active',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active
                    ON users(is_active) WHERE is_active = true
                """
            },

            # 数据收集日志索引
            {
                'name': 'idx_data_logs_timestamp',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_logs_timestamp
                    ON data_collection_logs(timestamp DESC)
                """
            },
            {
                'name': 'idx_data_logs_status',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_logs_status
                    ON data_collection_logs(status)
                """
            },

            # 复合索引
            {
                'name': 'idx_predictions_user_confidence',
                'sql': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_user_confidence
                    ON predictions(user_id, confidence_score DESC)
                """
            }
        ]

        results = {
            'created': [],
            'failed': [],
            'existing': []
        }

        for index_config in indexes_to_create:
            try:
                await self.db_session.execute(text(index_config['sql']))
                await self.db_session.commit()
                results['created'].append(index_config['name'])
                logger.info(f"Index created: {index_config['name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    results['existing'].append(index_config['name'])
                    logger.info(f"Index already exists: {index_config['name']}")
                else:
                    results['failed'].append({
                        'name': index_config['name'],
                        'error': str(e)
                    })
                    logger.error(f"Failed to create index {index_config['name']}: {e}")
                    await self.db_session.rollback()

        logger.info(f"Database index optimization completed: "
                   f"Created: {len(results['created'])}, "
                   f"Existing: {len(results['existing'])}, "
                   f"Failed: {len(results['failed'])}")

        return results

    async def optimize_slow_queries(self) -> Dict[str, Any]:
        """优化慢查询"""
        logger.info("Starting slow query optimization")

        # 分析慢查询
        slow_queries = [
            {
                'name': 'matches_with_teams',
                'sql': """
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT m.*, t1.name as home_team_name, t2.name as away_team_name
                    FROM matches m
                    JOIN teams t1 ON m.home_team_id = t1.id
                    JOIN teams t2 ON m.away_team_id = t2.id
                    WHERE m.league_id = :league_id
                    AND m.match_date >= :start_date
                    ORDER BY m.match_date DESC
                    LIMIT 100
                """,
                'params': {'league_id': 1, 'start_date': '2024-01-01'}
            },
            {
                'name': 'predictions_with_details',
                'sql': """
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT p.*, m.home_score, m.away_score, m.match_date
                    FROM predictions p
                    JOIN matches m ON p.match_id = m.id
                    WHERE p.user_id = :user_id
                    AND p.created_at >= :start_date
                    ORDER BY p.created_at DESC
                """,
                'params': {'user_id': 1, 'start_date': '2024-01-01'}
            }
        ]

        query_results = {}

        for query in slow_queries:
            try:
                result = await self.db_session.execute(text(query['sql']), query['params'])
                analysis = {
                    'name': query['name'],
                    'execution_plan': result.fetchall(),
                    'recommendations': self._analyze_query_plan(result.fetchall())
                }
                query_results[query['name']] = analysis
                logger.info(f"Analyzed query: {query['name']}")
            except Exception as e:
                logger.error(f"Failed to analyze query {query['name']}: {e}")
                query_results[query['name']] = {'error': str(e)}

        return query_results

    def _analyze_query_plan(self, plan_rows: List) -> List[str]:
        """分析查询执行计划"""
        recommendations = []

        for row in plan_rows:
            plan_text = str(row[0]) if row else ""

            # 检查常见的性能问题
            if 'Seq Scan' in plan_text:
                recommendations.append("考虑添加索引以避免全表扫描")

            if 'Sort' in plan_text:
                recommendations.append("考虑在排序列上添加索引")

            if 'Hash Join' in plan_text:
                recommendations.append("确保连接条件上有索引")

            if 'Nested Loop' in plan_text:
                recommendations.append("考虑优化嵌套查询或使用连接查询")

        return recommendations

    async def implement_query_cache(self) -> Dict[str, Any]:
        """实现查询结果缓存"""
        logger.info("Implementing query result caching")

        cacheable_queries = {
            'team_standings': {
                'sql': """
                    SELECT * FROM team_standings
                    WHERE league_id = :league_id
                    AND season = :season
                    ORDER BY points DESC
                """,
                'params': {'league_id': 1, 'season': '2024'},
                'ttl': 1800  # 30分钟
            },
            'upcoming_matches': {
                'sql': """
                    SELECT m.*, t1.name as home_team_name, t2.name as away_team_name
                    FROM matches m
                    JOIN teams t1 ON m.home_team_id = t1.id
                    JOIN teams t2 ON m.away_team_id = t2.id
                    WHERE m.match_date > NOW()
                    AND m.match_date < NOW() + INTERVAL '7 days'
                    ORDER BY m.match_date
                """,
                'params': {},
                'ttl': 300  # 5分钟
            },
            'recent_predictions': {
                'sql': """
                    SELECT p.*, m.home_team, m.away_team, m.match_date
                    FROM predictions p
                    JOIN matches m ON p.match_id = m.id
                    WHERE p.created_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY p.created_at DESC
                    LIMIT 50
                """,
                'params': {},
                'ttl': 600  # 10分钟
            }
        }

        cache_results = {
            'cached': [],
            'failed': [],
            'total': len(cacheable_queries)
        }

        for query_name, query_info in cacheable_queries.items():
            try:
                # 执行查询
                result = await self.db_session.execute(text(query_info['sql']), query_info['params'])
                data = result.fetchall()

                # 转换为字典列表
                if result.returns_rows:
                    columns = [desc[0] for desc in result.cursor.description]
                    data_list = [dict(zip(columns, row)) for row in data]
                else:
                    data_list = []

                # 缓存结果
                await self.cache_manager.set(
                    f"query_result:{query_name}",
                    data_list,
                    'database_query',
                    query_info['ttl']
                )

                cache_results['cached'].append(query_name)
                logger.info(f"Cached query result: {query_name} ({len(data_list)} rows)")

            except Exception as e:
                cache_results['failed'].append({
                    'name': query_name,
                    'error': str(e)
                })
                logger.error(f"Failed to cache query {query_name}: {e}")

        logger.info(f"Query caching completed: "
                   f"Cached: {len(cache_results['cached'])}, "
                   f"Failed: {len(cache_results['failed'])}")

        return cache_results

    async def optimize_cache_configuration(self) -> Dict[str, Any]:
        """优化缓存配置"""
        logger.info("Optimizing cache configuration")

        # 获取当前缓存统计
        cache_stats = await self.cache_manager.get_cache_stats()

        # 分析缓存命中率
        recommendations = []

        if cache_stats.get('hit_rate', 0) < 0.7:
            recommendations.append("缓存命中率较低，考虑增加缓存使用")
            recommendations.append("优化缓存键的设计以提高命中率")

        if cache_stats.get('local_cache_size', 0) > 800:
            recommendations.append("本地缓存大小较大，考虑调整大小或TTL")

        # 优化建议
        optimization_actions = {
            'increase_cache_sizes': [
                'prediction_result', 'team_stats', 'match_data'
            ],
            'decrease_cache_sizes': [
                'season_data', 'league_data'
            ],
            'add_warmup_queries': [
                'popular_teams', 'active_matches'
            ],
            'implement_cache_invalidation': [
                'user_predictions', 'team_standings'
            ]
        }

        return {
            'current_stats': cache_stats,
            'recommendations': recommendations,
            'optimization_actions': optimization_actions
        }

    async def monitor_performance_improvements(self) -> Dict[str, Any]:
        """监控性能改进效果"""
        logger.info("Monitoring performance improvements")

        # 获取当前性能指标
        current_metrics = self.system_monitor.get_current_metrics()
        performance_summary = self.system_monitor.get_metrics_summary(minutes=10)

        # 分析性能趋势
        trends = self.performance_analyzer.analyze_trends(hours=1)

        # 获取优化建议
        recommendations = self.performance_analyzer.get_performance_recommendations(performance_summary)

        # 检查性能警报
        alerts = self.system_monitor.check_performance_alerts()

        return {
            'current_metrics': current_metrics,
            'performance_summary': performance_summary,
            'trends': trends,
            'recommendations': recommendations,
            'alerts': alerts,
            'improvement_status': self._calculate_improvement_status(performance_summary)
        }

    def _calculate_improvement_status(self, performance_summary: Dict[str, Any]) -> Dict[str, Any]:
        """计算改进状态"""
        status = {
            'overall': 'unknown',
            'cpu': 'unknown',
            'memory': 'unknown',
            'performance': 'unknown'
        }

        if not performance_summary:
            return status

        # CPU状态
        cpu_avg = performance_summary.get('cpu', {}).get('avg', 0)
        if cpu_avg < 50:
            status['cpu'] = 'excellent'
        elif cpu_avg < 70:
            status['cpu'] = 'good'
        elif cpu_avg < 85:
            status['cpu'] = 'warning'
        else:
            status['cpu'] = 'critical'

        # 内存状态
        memory_avg = performance_summary.get('memory', {}).get('avg', 0)
        if memory_avg < 60:
            status['memory'] = 'excellent'
        elif memory_avg < 75:
            status['memory'] = 'good'
        elif memory_avg < 85:
            status['memory'] = 'warning'
        else:
            status['memory'] = 'critical'

        # 性能状态
        response_time = performance_summary.get('performance', {}).get('avg_response_time', 0)
        if response_time < 0.5:
            status['performance'] = 'excellent'
        elif response_time < 1.0:
            status['performance'] = 'good'
        elif response_time < 2.0:
            status['performance'] = 'warning'
        else:
            status['performance'] = 'critical'

        # 整体状态
        statuses = [v for v in status.values() if v != 'unknown']
        if all(s == 'excellent' for s in statuses):
            status['overall'] = 'excellent'
        elif any(s in ['warning', 'critical'] for s in statuses):
            status['overall'] = 'needs_attention'
        else:
            status['overall'] = 'good'

        return status


# 全局性能优化器实例
_performance_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_optimizer(db_session: AsyncSession) -> PerformanceOptimizer:
    """获取性能优化器实例"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer(db_session)
    return _performance_optimizer