"""
查询优化器
提供查询优化建议和自动优化功能
"""

import re
import time
import asyncio
from typing import Any,  List[Any], Dict[str, Any], Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.pool_config import with_connection_pool_health_check

logger = get_logger(__name__)


@dataclass
class QueryMetrics:
    """查询指标"""
    query: str
    duration: float
    rows: int
    cache_hits: int
    cache_misses: int
    timestamp: float


class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self.slow_query_threshold = 1.0  # 1秒
        self.query_history: List[QueryMetrics] = []
        self.max_history_size = 1000

    async def analyze_query_plan(
        self,
        session: AsyncSession,
        query: str,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """分析查询执行计划"""
        try:
            # 使用EXPLAIN ANALYZE获取执行计划
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"

            result = await session.execute(
                text(explain_query),
                params or {}
            )

            plan_data = result.fetchone()[0]

            # 解析执行计划
            analysis = self._parse_execution_plan(plan_data)

            logger.info(
                "查询计划分析完成",
                query=query[:100],
                total_cost=analysis.get('total_cost', 0),
                planning_time=analysis.get('planning_time', 0),
                execution_time=analysis.get('execution_time', 0)
            )

            return analysis

        except Exception as e:
            logger.error("查询计划分析失败", query=query[:100], error=str(e))
            return {}

    def _parse_execution_plan(self, plan_data: List[Dict[str, Any]) -> Dict[str, Any]:
        """解析执行计划数据"""
        if not plan_data:
            return {}

        plan = plan_data[0].get('Plan', {})

        # 提取关键指标
        analysis = {
            'total_cost': plan.get('Total Cost', 0),
            'actual_rows': plan.get('Actual Rows', 0),
            'actual_loops': plan.get('Actual Loops', 0),
            'planning_time': plan_data[0].get('Planning Time', 0),
            'execution_time': plan_data[0].get('Execution Time', 0),
            'node_type': plan.get('Node Type[Any]', ''),
            'scan_type': plan.get('Scan', {}).get('Node Type[Any]', '') if plan.get('Scan') else '',
            'relation_name': plan.get('Relation Name', ''),
            'alias': plan.get('Alias', ''),
            'buffers': plan_data[0].get('Buffers', {}),
        }

        # 分析缓冲区使用
        buffers = analysis['buffers']
        if buffers:
            analysis['shared_hit_blocks'] = buffers.get('Shared Hit Blocks', 0)
            analysis['shared_read_blocks'] = buffers.get('Shared Read Blocks', 0)
            analysis['local_hit_blocks'] = buffers.get('Local Hit Blocks', 0)
            analysis['local_read_blocks'] = buffers.get('Local Read Blocks', 0)

            # 计算缓存命中率
            total_shared = analysis['shared_hit_blocks'] + analysis['shared_read_blocks']
            if total_shared > 0:
                analysis['cache_hit_rate'] = analysis['shared_hit_blocks'] / total_shared
            else:
                analysis['cache_hit_rate'] = 0

        # 递归分析子计划
        if 'Plans' in plan:
            analysis['subplans'] = [
                self._parse_execution_plan([{'Plan': subplan, 'Planning Time': 0, 'Execution Time': 0}])
                for subplan in plan['Plans']
            ]

        return analysis

    def identify_slow_queries(self) -> List[QueryMetrics]:
        """识别慢查询"""
        slow_queries = [
            q for q in self.query_history
            if q.duration > self.slow_query_threshold
        ]

        # 按持续时间排序
        slow_queries.sort(key=lambda x: x.duration, reverse=True)

        return slow_queries

    def generate_optimization_suggestions(
        self,
        query_plan: Dict[str, Any]
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []

        # 检查全表扫描
        if query_plan.get('node_type') == 'Seq Scan':
            table_name = query_plan.get('relation_name', '')
            if table_name:
                suggestions.append(
                    f"建议为表 '{table_name}' 添加适当的索引以避免全表扫描"
                )

        # 检查嵌套循环连接
        if query_plan.get('node_type') == 'Nested Loop':
            suggestions.append(
                "检测到嵌套循环连接，考虑使用哈希连接或归并连接替代"
            )

        # 检查低缓存命中率
        cache_hit_rate = query_plan.get('cache_hit_rate', 1)
        if cache_hit_rate < 0.9:
            suggestions.append(
                f"缓存命中率较低({cache_hit_rate:.2%})，考虑增加shared_buffers或优化查询"
            )

        # 检查高执行成本
        total_cost = query_plan.get('total_cost', 0)
        if total_cost > 1000:
            suggestions.append(
                f"查询成本较高({total_cost:.2f})，考虑重写查询或添加索引"
            )

        # 检查排序操作
        if query_plan.get('node_type') in ['Sort', 'Incremental Sort']:
            suggestions.append(
                "检测到排序操作，如果结果集很大，考虑添加索引避免排序"
            )

        # 检查哈希聚合
        if query_plan.get('node_type') == 'HashAggregate':
            suggestions.append(
                "检测到哈希聚合，确保work_mem配置足够大"
            )

        # 检查CTE（通用表表达式）
        if 'CTE Scan' in str(query_plan):
            suggestions.append(
                "检测到CTE使用，对于复杂查询考虑使用子查询替代以优化性能"
            )

        return suggestions

    async def suggest_missing_indexes(
        self,
        session: AsyncSession
    ) -> List[Dict[str, Any]:
        """建议缺失的索引"""
        suggestions = []

        # 查询频繁使用的列但没有索引的情况
        query = text("""
            SELECT
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats
            WHERE schemaname = 'public'
            AND attname NOT IN (
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = tablename
                AND column_name IN (
                    SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_schema = 'public'
                    AND table_name = tablename
                )
            )
            AND most_common_vals IS NOT NULL
            ORDER BY schemaname, tablename, n_distinct DESC
            LIMIT 20
        """)

        try:
            result = await session.execute(query)

            for row in result.fetchall():
                if row.n_distinct > 10:  # 高基数字段
                    suggestions.append({
                        'table': row.tablename,
                        'column': row.attname,
                        'distinct_values': row.n_distinct,
                        'reason': '高基数字段适合创建索引',
                        'sql': f'CREATE INDEX CONCURRENTLY idx_{row.tablename}_{row.attname} ON {row.tablename} ({row.attname})'
                    })

        except Exception as e:
            logger.error("建议缺失索引失败", error=str(e))

        return suggestions

    async def analyze_query_patterns(
        self,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """分析查询模式"""
        # 从pg_stat_statements获取查询统计
        query = text("""
            SELECT
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements
            WHERE calls > 10
            ORDER BY total_exec_time DESC
            LIMIT 50
        """)

        try:
            result = await session.execute(query)

            patterns = {
                'top_queries_by_time': [],
                'top_queries_by_calls': [],
                'slow_queries': [],
                'low_cache_hit_queries': []
            }

            for row in result.fetchall():
                query_info = {
                    'query': row.query[:200] + '...' if len(row.query) > 200 else row.query,
                    'calls': row.calls,
                    'total_time': row.total_exec_time,
                    'mean_time': row.mean_exec_time,
                    'rows': row.rows,
                    'hit_percent': row.hit_percent
                }

                patterns['top_queries_by_time'].append(query_info)

                if row.calls > 100:
                    patterns['top_queries_by_calls'].append(query_info)

                if row.mean_exec_time > self.slow_query_threshold:
                    patterns['slow_queries'].append(query_info)

                if row.hit_percent < 0.95:
                    patterns['low_cache_hit_queries'].append(query_info)

            return patterns

        except Exception as e:
            logger.error("分析查询模式失败", error=str(e))
            return {}

    def optimize_query_text(self, query: str) -> str:
        """优化查询文本"""
        optimized = query

        # 1. 使用EXISTS替代IN（适用于子查询）
        optimized = re.sub(
            r'WHERE\s+(\w+)\s+IN\s*\((.*?)\)',
            lambda m: f"WHERE EXISTS (SELECT 1 FROM {m.group(2).split('FROM')[1].strip()} WHERE {m.group(1)} = ...)",
            optimized,
            flags=re.IGNORECASE | re.DOTALL
        )

        # 2. 使用UNION ALL替代UNION（如果不需要去重）
        if 'UNION' in optimized.upper() and 'DISTINCT' not in optimized.upper():
            optimized = optimized.replace('UNION', 'UNION ALL')

        # 3. 避免在WHERE子句中使用函数
        optimized = re.sub(
            r'WHERE\s+UPPER\((\w+)\)\s*=',
            lambda m: f"WHERE {m.group(1)} =",
            optimized,
            flags=re.IGNORECASE
        )

        # 4. 使用LIMIT限制结果集
        if 'SELECT' in optimized.upper() and 'LIMIT' not in optimized.upper():
            # 在适当的位置添加LIMIT（简单启发式）
            if ';' in optimized:
                optimized = optimized.replace(';', ' LIMIT 1000;')

        return optimized

    @with_connection_pool_health_check
    async def execute_optimized_query(
        self,
        session: AsyncSession,
        query: str,
        params: Dict[str, Any] = None,
        auto_optimize: bool = True
    ) -> Tuple[Any, Dict[str, Any]:
        """执行优化的查询"""
        start_time = time.time()

        # 如果启用自动优化，先优化查询
        if auto_optimize:
            optimized_query = self.optimize_query_text(query)
            if optimized_query != query:
                logger.info("查询已自动优化", original_length=len(query), optimized_length=len(optimized_query))
                query = optimized_query

        try:
            # 执行查询
            result = await session.execute(text(query), params or {})
            rows = result.fetchall()

            # 计算执行时间
            duration = time.time() - start_time

            # 记录查询指标
            metrics = QueryMetrics(
                query=query[:200],
                duration=duration,
                rows=len(rows),
                cache_hits=0,  # 需要从pg_stat_statements获取
                cache_misses=0,
                timestamp=time.time()
            )

            self._add_to_history(metrics)

            # 如果是慢查询，生成优化建议
            if duration > self.slow_query_threshold:
                logger.warning(
                    "检测到慢查询",
                    duration=duration,
                    rows=len(rows),
                    query=query[:100]
                )

                # 分析执行计划
                plan_analysis = await self.analyze_query_plan(session, query, params)
                suggestions = self.generate_optimization_suggestions(plan_analysis)

                if suggestions:
                    logger.info("优化建议", suggestions=suggestions)

            return rows, {
                'duration': duration,
                'rows': len(rows),
                'optimized': auto_optimize and optimized_query != query
            }

        except Exception as e:
            logger.error("查询执行失败", query=query[:100], error=str(e))
            raise

    def _add_to_history(self, metrics: QueryMetrics):
        """添加查询指标到历史记录"""
        self.query_history.append(metrics)

        # 限制历史记录大小
        if len(self.query_history) > self.max_history_size:
            self.query_history = self.query_history[-self.max_history_size:]

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.query_history:
            return {"message": "暂无查询历史记录"}

        # 计算统计指标
        total_queries = len(self.query_history)
        total_duration = sum(q.duration for q in self.query_history)
        avg_duration = total_duration / total_queries
        max_duration = max(q.duration for q in self.query_history)
        min_duration = min(q.duration for q in self.query_history)

        # 计算百分位数
        sorted_durations = sorted(q.duration for q in self.query_history)
        p50 = sorted_durations[int(total_queries * 0.5)]
        p95 = sorted_durations[int(total_queries * 0.95)]
        p99 = sorted_durations[int(total_queries * 0.99)]

        # 慢查询统计
        slow_queries = self.identify_slow_queries()

        return {
            'summary': {
                'total_queries': total_queries,
                'total_duration': total_duration,
                'avg_duration': avg_duration,
                'min_duration': min_duration,
                'max_duration': max_duration,
                'p50_duration': p50,
                'p95_duration': p95,
                'p99_duration': p99,
                'slow_query_count': len(slow_queries),
                'slow_query_rate': len(slow_queries) / total_queries
            },
            'slow_queries': [
                {
                    'query': q.query,
                    'duration': q.duration,
                    'rows': q.rows,
                    'timestamp': q.timestamp
                }
                for q in slow_queries[:10]  # 只返回前10个
            ],
            'recommendations': self._generate_general_recommendations()
        }

    def _generate_general_recommendations(self) -> List[str]:
        """生成通用优化建议"""
        recommendations = []

        if not self.query_history:
            return recommendations

        # 分析查询模式
        avg_duration = sum(q.duration for q in self.query_history) / len(self.query_history)

        if avg_duration > 0.5:
            recommendations.append("平均查询时间较长，建议全面审查查询性能")

        slow_rate = len(self.identify_slow_queries()) / len(self.query_history)
        if slow_rate > 0.1:
            recommendations.append("慢查询比例较高，建议优化查询或增加数据库资源")

        # 检查是否有大量结果集的查询
        large_result_queries = [q for q in self.query_history if q.rows > 1000]
        if len(large_result_queries) > len(self.query_history) * 0.2:
            recommendations.append("检测到大量返回大结果集的查询，考虑添加分页或限制条件")

        return recommendations


# 全局查询优化器实例
query_optimizer = QueryOptimizer()
