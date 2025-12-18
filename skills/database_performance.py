#!/usr/bin/env python3
"""
Database Performance Skill for Claude Code
数据库性能专业技能 - PostgreSQL性能调优专家
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import re
import asyncio
import asyncpg
import time
from datetime import datetime, timedelta

class DatabasePerformanceSkill:
    """
    Database Performance Skill - 专注于数据库性能分析和优化
    """

    def __init__(self):
        self.skill_name = "database-performance"
        self.capabilities = [
            "postgresql-optimization",
            "query-analysis",
            "index-strategy",
            "performance-monitoring",
            "capacity-planning",
            "bottleneck-analysis",
            "sql-tuning"
        ]

    async def analyze_postgres_performance(self, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析PostgreSQL性能指标

        Args:
            connection_params: 数据库连接参数

        Returns:
            性能分析结果
        """
        try:
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "connection_status": "unknown",
                "performance_metrics": {},
                "slow_queries": [],
                "index_usage": {},
                "table_stats": {},
                "recommendations": [],
                "bottlenecks": []
            }

            # 连接数据库
            try:
                conn = await asyncpg.connect(
                    host=connection_params.get("host", "localhost"),
                    port=connection_params.get("port", 5432),
                    database=connection_params.get("database"),
                    user=connection_params.get("user"),
                    password=connection_params.get("password"),
                    timeout=10
                )
                analysis["connection_status"] = "connected"
            except Exception as e:
                analysis["connection_status"] = "failed"
                analysis["error"] = str(e)
                return analysis

            try:
                # 获取数据库基本信息
                version_info = await conn.fetchval("SELECT version()")
                analysis["postgresql_version"] = version_info

                # 获取性能指标
                performance_metrics = await self._get_performance_metrics(conn)
                analysis["performance_metrics"] = performance_metrics

                # 分析慢查询
                slow_queries = await self._analyze_slow_queries(conn)
                analysis["slow_queries"] = slow_queries

                # 分析索引使用情况
                index_usage = await self._analyze_index_usage(conn)
                analysis["index_usage"] = index_usage

                # 获取表统计信息
                table_stats = await self._get_table_statistics(conn)
                analysis["table_stats"] = table_stats

                # 检查数据库配置
                config_analysis = await self._analyze_database_config(conn)
                analysis["config_analysis"] = config_analysis

                # 识别性能瓶颈
                bottlenecks = await self._identify_bottlenecks(
                    performance_metrics, slow_queries, index_usage, table_stats
                )
                analysis["bottlenecks"] = bottlenecks

                # 生成优化建议
                recommendations = await self._generate_database_recommendations(
                    performance_metrics, slow_queries, index_usage, config_analysis
                )
                analysis["recommendations"] = recommendations

            finally:
                await conn.close()

            return analysis

        except Exception as e:
            return {"error": f"PostgreSQL性能分析失败: {str(e)}"}

    def optimize_for_large_dataset(self, current_config: Dict[str, Any],
                                  dataset_size_gb: float = 50,
                                  expected_qps: int = 1000) -> Dict[str, Any]:
        """
        针对大数据集优化PostgreSQL配置

        Args:
            current_config: 当前配置
            dataset_size_gb: 数据集大小(GB)
            expected_qps: 预期QPS

        Returns:
            优化后的配置
        """
        try:
            optimization_result = {
                "timestamp": datetime.now().isoformat(),
                "dataset_info": {
                    "size_gb": dataset_size_gb,
                    "estimated_rows": dataset_size_gb * 1024 * 1024 * 1024 / 8192,  # 假设平均行大小8KB
                    "expected_qps": expected_qps
                },
                "current_config": current_config,
                "optimized_config": {},
                "parameter_changes": [],
                "expected_improvements": {},
                "implementation_steps": []
            }

            # 基于数据集大小计算优化参数
            optimized_config = current_config.copy()

            # 内存相关参数优化
            total_memory_gb = self._estimate_available_memory()
            shared_buffers = min(total_memory_gb * 0.25, total_memory_gb * 0.3)  # 25-30%
            effective_cache_size = min(total_memory_gb * 0.7, total_memory_gb * 0.75)  # 70-75%
            work_mem = max(8, min(64, total_memory_gb * 0.01))  # 1%或8-64MB
            maintenance_work_mem = min(1024, dataset_size_gb * 2)  # 每GB数据2MB，最大1GB

            memory_changes = [
                {"parameter": "shared_buffers", "old": current_config.get("shared_buffers", "128MB"),
                 "new": f"{int(shared_buffers*1024)}MB", "reason": "大数据集需要更多共享缓存"},
                {"parameter": "effective_cache_size", "old": current_config.get("effective_cache_size", "4GB"),
                 "new": f"{int(effective_cache_size*1024)}MB", "reason": "增加文件系统缓存估计"},
                {"parameter": "work_mem", "old": current_config.get("work_mem", "4MB"),
                 "new": f"{int(work_mem)}MB", "reason": "支持更复杂的查询和排序"},
                {"parameter": "maintenance_work_mem", "old": current_config.get("maintenance_work_mem", "64MB"),
                 "new": f"{int(maintenance_work_mem)}MB", "reason": "加速索引创建和VACUUM"}
            ]

            # 更新配置
            for change in memory_changes:
                optimized_config[change["parameter"]] = change["new"]
            optimization_result["parameter_changes"].extend(memory_changes)

            # 连接参数优化
            max_connections = min(200, expected_qps // 10)  # 每个连接支持10QPS
            superuser_reserved_connections = min(10, max_connections // 10)

            connection_changes = [
                {"parameter": "max_connections", "old": current_config.get("max_connections", 100),
                 "new": max_connections, "reason": f"支持{expected_qps}QPS的并发需求"},
                {"parameter": "superuser_reserved_connections", "old": current_config.get("superuser_reserved_connections", 3),
                 "new": superuser_reserved_connections, "reason": "为管理员保留连接"}
            ]

            for change in connection_changes:
                optimized_config[change["parameter"]] = change["new"]
            optimization_result["parameter_changes"].extend(connection_changes)

            # WAL和检查点优化
            wal_buffers = min(64, total_memory_gb * 0.005)  # 0.5%或最大64MB
            checkpoint_completion_target = 0.9  # 更平滑的检查点
            checkpoint_timeout = "15min"

            wal_changes = [
                {"parameter": "wal_buffers", "old": current_config.get("wal_buffers", "16MB"),
                 "new": f"{int(wal_buffers)}MB", "reason": "减少WAL写入压力"},
                {"parameter": "checkpoint_completion_target", "old": current_config.get("checkpoint_completion_target", 0.7),
                 "new": checkpoint_completion_target, "reason": "平滑检查点过程，减少I/O峰值"},
                {"parameter": "checkpoint_timeout", "old": current_config.get("checkpoint_timeout", "5min"),
                 "new": checkpoint_timeout, "reason": "减少检查点频率"}
            ]

            for change in wal_changes:
                optimized_config[change["parameter"]] = change["new"]
            optimization_result["parameter_changes"].extend(wal_changes)

            # 查询规划器优化
            planner_changes = [
                {"parameter": "random_page_cost", "old": current_config.get("random_page_cost", 4.0),
                 "new": 1.1, "reason": "SSD存储优化"},
                {"parameter": "effective_io_concurrency", "old": current_config.get("effective_io_concurrency", 200),
                 "new": 400, "reason": "提高SSD并发IO"},
                {"parameter": "default_statistics_target", "old": current_config.get("default_statistics_target", 100),
                 "new": 1000, "reason": "大数据集需要更精确的统计信息"}
            ]

            for change in planner_changes:
                optimized_config[change["parameter"]] = change["new"]
            optimization_result["parameter_changes"].extend(planner_changes)

            # 自动清理优化
            autovacuum_changes = [
                {"parameter": "autovacuum_max_workers", "old": current_config.get("autovacuum_max_workers", 3),
                 "new": min(6, total_memory_gb // 2), "reason": "增加并行清理能力"},
                {"parameter": "autovacuum_naptime", "old": current_config.get("autovacuum_naptime", "1min"),
                 "new": "30s", "reason": "更频繁的清理，减少单次清理压力"}
            ]

            for change in autovacuum_changes:
                optimized_config[change["parameter"]] = change["new"]
            optimization_result["parameter_changes"].extend(autovacuum_changes)

            optimization_result["optimized_config"] = optimized_config

            # 预期改进
            optimization_result["expected_improvements"] = {
                "query_performance": "+60-80%",
                "index_creation_speed": "+100-200%",
                "concurrent_capacity": f"支持{expected_qps}QPS",
                "memory_efficiency": "+40-60%",
                "io_efficiency": "+30-50%"
            }

            # 实施步骤
            optimization_result["implementation_steps"] = [
                {
                    "step": 1,
                    "title": "备份当前配置",
                    "description": "备份postgresql.conf和pg_hba.conf",
                    "commands": ["cp postgresql.conf postgresql.conf.backup"]
                },
                {
                    "step": 2,
                    "title": "应用内存优化参数",
                    "description": "更新shared_buffers, work_mem等内存参数",
                    "commands": ["# 编辑postgresql.conf", "# 重启PostgreSQL"]
                },
                {
                    "step": 3,
                    "title": "调整连接参数",
                    "description": "更新max_connections等连接相关参数",
                    "commands": ["# 编辑postgresql.conf", "# 重启PostgreSQL"]
                },
                {
                    "step": 4,
                    "title": "优化WAL和检查点",
                    "description": "调整WAL缓冲区和检查点设置",
                    "commands": ["# 编辑postgresql.conf", "# 重新加载配置"]
                },
                {
                    "step": 5,
                    "title": "更新查询规划器参数",
                    "description": "优化查询规划器相关设置",
                    "commands": ["# 编辑postgresql.conf", "# 重新加载配置"]
                },
                {
                    "step": 6,
                    "title": "配置自动清理",
                    "description": "调整autovacuum参数",
                    "commands": ["# 编辑postgresql.conf", "# 重新加载配置"]
                }
            ]

            return optimization_result

        except Exception as e:
            return {"error": f"大数据集优化失败: {str(e)}"}

    def analyze_query_performance(self, query: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单个查询的性能

        Args:
            query: SQL查询语句
            connection_params: 数据库连接参数

        Returns:
            查询性能分析结果
        """
        try:
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "execution_stats": {},
                "execution_plan": {},
                "optimization_suggestions": [],
                "index_recommendations": [],
                "performance_score": 0
            }

            # 连接数据库并执行分析
            async def analyze():
                conn = await asyncpg.connect(**connection_params)

                try:
                    # 获取查询执行计划
                    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                    plan_result = await conn.fetchval(explain_query)
                    plan_data = json.loads(plan_result)[0]["Plan"]

                    analysis["execution_plan"] = plan_data

                    # 计算执行统计
                    actual_time = plan_data.get("Actual Total Time", 0)
                    planning_time = plan_data.get("Planning Time", 0)
                    total_cost = plan_data.get("Total Cost", 0)

                    analysis["execution_stats"] = {
                        "execution_time_ms": actual_time,
                        "planning_time_ms": planning_time,
                        "total_cost": total_cost,
                        "rows_returned": plan_data.get("Actual Rows", 0),
                        "buffers_used": {
                            "shared_hit": 0,
                            "shared_read": 0,
                            "local_hit": 0,
                            "local_read": 0
                        }
                    }

                    # 分析缓冲区使用
                    if "Buffers" in plan_data:
                        buffers = plan_data["Buffers"]
                        analysis["execution_stats"]["buffers_used"] = {
                            "shared_hit": buffers.get("Shared Hit Blocks", 0),
                            "shared_read": buffers.get("Shared Read Blocks", 0),
                            "local_hit": buffers.get("Local Hit Blocks", 0),
                            "local_read": buffers.get("Local Read Blocks", 0)
                        }

                    # 生成优化建议
                    suggestions = self._generate_query_optimization_suggestions(plan_data, query)
                    analysis["optimization_suggestions"] = suggestions

                    # 生成索引建议
                    index_recs = self._generate_index_recommendations(plan_data, query)
                    analysis["index_recommendations"] = index_recs

                    # 计算性能评分
                    analysis["performance_score"] = self._calculate_query_performance_score(
                        actual_time, total_cost, analysis["execution_stats"]["buffers_used"]
                    )

                finally:
                    await conn.close()

            # 执行分析
            asyncio.run(analyze())

            return analysis

        except Exception as e:
            return {"error": f"查询性能分析失败: {str(e)}"}

    def generate_index_strategy(self, table_stats: Dict[str, Any],
                              query_patterns: List[str] = None) -> Dict[str, Any]:
        """
        生成索引优化策略

        Args:
            table_stats: 表统计信息
            query_patterns: 常见查询模式

        Returns:
            索引策略建议
        """
        try:
            strategy = {
                "timestamp": datetime.now().isoformat(),
                "table_analysis": {},
                "index_recommendations": [],
                "partitioning_suggestions": [],
                "optimization_plan": [],
                "estimated_impact": {}
            }

            # 分析每个表
            for table_name, stats in table_stats.items():
                table_analysis = {
                    "row_count": stats.get("row_count", 0),
                    "size_mb": stats.get("size_mb", 0),
                    "indexes": stats.get("indexes", []),
                    "fragmentation": stats.get("fragmentation", 0),
                    "hot_columns": stats.get("hot_columns", []),
                    "optimization_needed": False
                }

                # 判断是否需要优化
                row_count = table_analysis["row_count"]
                size_mb = table_analysis["size_mb"]

                if row_count > 1000000 or size_mb > 1000:  # 100万行或1GB
                    table_analysis["optimization_needed"] = True

                strategy["table_analysis"][table_name] = table_analysis

            # 生成索引建议
            if query_patterns:
                for pattern in query_patterns:
                    index_rec = self._analyze_query_pattern_for_indexes(pattern, table_stats)
                    if index_rec:
                        strategy["index_recommendations"].append(index_rec)

            # 生成分区建议
            partitioning_recs = self._generate_partitioning_suggestions(table_stats)
            strategy["partitioning_suggestions"] = partitioning_recs

            # 生成优化计划
            optimization_plan = self._create_index_optimization_plan(
                strategy["index_recommendations"], strategy["partitioning_suggestions"]
            )
            strategy["optimization_plan"] = optimization_plan

            # 估算影响
            strategy["estimated_impact"] = {
                "query_speed_improvement": "+200-400%",
                "storage_overhead": "+20-40%",
                "write_performance_impact": "-10-20%",
                "maintenance_overhead": "+15-25%"
            }

            return strategy

        except Exception as e:
            return {"error": f"索引策略生成失败: {str(e)}"}

    # Helper methods
    async def _get_performance_metrics(self, conn) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            metrics = {}

            # 获取数据库连接统计
            connections = await conn.fetchrow("""
                SELECT
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
            """)
            metrics["connections"] = dict(connections)

            # 获取数据库大小
            db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            metrics["database_size"] = db_size

            # 获取缓存命中率
            cache_hit_ratio = await conn.fetchrow("""
                SELECT
                    round((blks_hit::float / (blks_hit + blks_read)) * 100, 2) as cache_hit_ratio,
                    blks_hit,
                    blks_read
                FROM pg_stat_database
                WHERE datname = current_database()
            """)
            metrics["cache_performance"] = dict(cache_hit_ratio)

            # 获取WAL统计
            wal_stats = await conn.fetchrow("""
                SELECT
                    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')) as total_wal_size,
                    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), pg_last_wal_replay_lsn())) as wal_lag
            """)
            metrics["wal_stats"] = dict(wal_stats)

            return metrics

        except Exception as e:
            return {"error": str(e)}

    async def _analyze_slow_queries(self, conn) -> List[Dict[str, Any]]:
        """分析慢查询"""
        try:
            slow_queries = []

            # 这里需要根据实际的慢查询日志或pg_stat_statements扩展来获取
            # 示例实现
            if await conn.fetchval("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"):
                queries = await conn.fetch("""
                    SELECT
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements
                    WHERE mean_time > 1000  -- 超过1秒的查询
                    ORDER BY mean_time DESC
                    LIMIT 10
                """)

                for query in queries:
                    slow_queries.append({
                        "query": query["query"][:100] + "..." if len(query["query"]) > 100 else query["query"],
                        "calls": query["calls"],
                        "total_time_ms": query["total_time"],
                        "mean_time_ms": query["mean_time"],
                        "rows_returned": query["rows"]
                    })

            return slow_queries

        except Exception as e:
            return [{"error": str(e)}]

    async def _analyze_index_usage(self, conn) -> Dict[str, Any]:
        """分析索引使用情况"""
        try:
            index_usage = {}

            # 获取索引使用统计
            index_stats = await conn.fetch("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                ORDER BY idx_scan ASC
            """)

            for stat in index_stats:
                table_name = stat["tablename"]
                if table_name not in index_usage:
                    index_usage[table_name] = []

                index_usage[table_name].append({
                    "index_name": stat["indexname"],
                    "scans": stat["idx_scan"],
                    "tuples_read": stat["idx_tup_read"],
                    "tuples_fetched": stat["idx_tup_fetch"],
                    "size": stat["index_size"],
                    "unused": stat["idx_scan"] == 0
                })

            return index_usage

        except Exception as e:
            return {"error": str(e)}

    async def _get_table_statistics(self, conn) -> Dict[str, Any]:
        """获取表统计信息"""
        try:
            table_stats = {}

            tables = await conn.fetch("""
                SELECT
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)

            for table in tables:
                table_name = table["tablename"]
                table_stats[table_name] = {
                    "schema": table["schemaname"],
                    "inserts": table["inserts"],
                    "updates": table["updates"],
                    "deletes": table["deletes"],
                    "live_tuples": table["live_tuples"],
                    "dead_tuples": table["dead_tuples"],
                    "last_vacuum": table["last_vacuum"],
                    "last_autovacuum": table["last_autovacuum"],
                    "last_analyze": table["last_analyze"],
                    "last_autoanalyze": table["last_autoanalyze"],
                    "total_size": table["total_size"],
                    "table_size": table["table_size"],
                    "bloat_estimate": self._estimate_table_bloat(table["live_tuples"], table["dead_tuples"])
                }

            return table_stats

        except Exception as e:
            return {"error": str(e)}

    async def _analyze_database_config(self, conn) -> Dict[str, Any]:
        """分析数据库配置"""
        try:
            config = {}

            # 获取重要配置参数
            params = [
                "shared_buffers", "effective_cache_size", "work_mem", "maintenance_work_mem",
                "max_connections", "checkpoint_completion_target", "wal_buffers",
                "random_page_cost", "effective_io_concurrency", "default_statistics_target",
                "autovacuum_max_workers", "autovacuum_naptime"
            ]

            for param in params:
                try:
                    value = await conn.fetchval(f"SHOW {param}")
                    config[param] = value
                except:
                    config[param] = "unknown"

            return config

        except Exception as e:
            return {"error": str(e)}

    async def _identify_bottlenecks(self, performance_metrics, slow_queries, index_usage, table_stats):
        """识别性能瓶颈"""
        bottlenecks = []

        # 内存瓶颈
        cache_hit_ratio = performance_metrics.get("cache_performance", {}).get("cache_hit_ratio", 0)
        if cache_hit_ratio < 90:
            bottlenecks.append({
                "type": "memory",
                "severity": "high" if cache_hit_ratio < 80 else "medium",
                "description": f"缓存命中率过低: {cache_hit_ratio}%",
                "recommendation": "增加shared_buffers或effective_cache_size"
            })

        # 连接瓶颈
        active_connections = performance_metrics.get("connections", {}).get("active_connections", 0)
        if active_connections > 80:
            bottlenecks.append({
                "type": "connections",
                "severity": "high",
                "description": f"活跃连接数过多: {active_connections}",
                "recommendation": "考虑增加连接池或优化长连接"
            })

        # 慢查询瓶颈
        if slow_queries and len(slow_queries) > 5:
            bottlenecks.append({
                "type": "slow_queries",
                "severity": "high",
                "description": f"发现 {len(slow_queries)} 个慢查询",
                "recommendation": "优化查询语句或添加适当的索引"
            })

        # 索引瓶颈
        unused_indexes = 0
        for table_indexes in index_usage.values():
            unused_indexes += sum(1 for idx in table_indexes if idx.get("unused", False))

        if unused_indexes > 0:
            bottlenecks.append({
                "type": "unused_indexes",
                "severity": "medium",
                "description": f"发现 {unused_indexes} 个未使用的索引",
                "recommendation": "删除未使用的索引以提高写性能"
            })

        # 表膨胀瓶颈
        bloated_tables = []
        for table_name, stats in table_stats.items():
            if isinstance(stats, dict) and stats.get("bloat_estimate", 0) > 20:
                bloated_tables.append(table_name)

        if bloated_tables:
            bottlenecks.append({
                "type": "table_bloat",
                "severity": "medium",
                "description": f"发现 {len(bloated_tables)} 个膨胀的表",
                "recommendation": "执行VACUUM FULL或重新组织表"
            })

        return bottlenecks

    async def _generate_database_recommendations(self, performance_metrics, slow_queries, index_usage, config_analysis):
        """生成数据库优化建议"""
        recommendations = []

        # 基于配置的建议
        if isinstance(config_analysis, dict):
            shared_buffers = config_analysis.get("shared_buffers", "128MB")
            if shared_buffers == "128MB":  # 默认值
                recommendations.append({
                    "priority": "high",
                    "category": "memory",
                    "action": "增加shared_buffers至系统内存的25%",
                    "impact": "提升缓存命中率和查询性能"
                })

            work_mem = config_analysis.get("work_mem", "4MB")
            if work_mem == "4MB":  # 默认值
                recommendations.append({
                    "priority": "medium",
                    "category": "memory",
                    "action": "根据查询复杂度增加work_mem",
                    "impact": "减少排序和哈希操作的磁盘使用"
                })

        # 基于索引使用的建议
        unused_indexes_count = 0
        for table_indexes in index_usage.values():
            if isinstance(table_indexes, list):
                unused_indexes_count += sum(1 for idx in table_indexes if idx.get("unused", False))

        if unused_indexes_count > 0:
            recommendations.append({
                "priority": "medium",
                "category": "indexes",
                "action": f"删除 {unused_indexes_count} 个未使用的索引",
                "impact": "提升写性能和减少存储空间"
            })

        # 基于慢查询的建议
        if slow_queries:
            recommendations.append({
                "priority": "high",
                "category": "queries",
                "action": "分析并优化慢查询，考虑添加索引或重写查询",
                "impact": "显著提升查询性能"
            })

        # 基于性能指标的建议
        cache_hit_ratio = performance_metrics.get("cache_performance", {}).get("cache_hit_ratio", 95)
        if cache_hit_ratio < 95:
            recommendations.append({
                "priority": "high",
                "category": "memory",
                "action": "优化内存配置以提升缓存命中率",
                "impact": "减少磁盘I/O，提升整体性能"
            })

        return recommendations

    def _estimate_available_memory(self) -> float:
        """估算可用内存(GB)"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.total / (1024**3)
        except:
            return 8.0  # 默认8GB

    def _estimate_table_bloat(self, live_tuples, dead_tuples):
        """估算表膨胀率"""
        total = live_tuples + dead_tuples
        if total == 0:
            return 0
        return (dead_tuples / total) * 100

    def _generate_query_optimization_suggestions(self, plan_data, query):
        """生成查询优化建议"""
        suggestions = []

        # 检查是否有Seq Scan
        def find_seq_scans(node):
            if isinstance(node, dict):
                if node.get("Node Type") == "Seq Scan":
                    return node
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        result = find_seq_scans(value)
                        if result:
                            return result
            elif isinstance(node, list):
                for item in node:
                    result = find_seq_scans(item)
                    if result:
                        return result
            return None

        seq_scan = find_seq_scans(plan_data)
        if seq_scan:
            suggestions.append({
                "type": "seq_scan",
                "description": "发现全表扫描，考虑添加索引",
                "table": seq_scan.get("Relation Name"),
                "impact": "high"
            })

        # 检查排序操作
        def find_sorts(node):
            sorts = []
            if isinstance(node, dict):
                if node.get("Node Type") == "Sort":
                    sorts.append(node)
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        sorts.extend(find_sorts(value))
            elif isinstance(node, list):
                for item in node:
                    sorts.extend(find_sorts(item))
            return sorts

        sorts = find_sorts(plan_data)
        if sorts:
            suggestions.append({
                "type": "sort",
                "description": f"发现 {len(sorts)} 个排序操作，考虑增加work_mem或创建索引避免排序",
                "impact": "medium"
            })

        return suggestions

    def _generate_index_recommendations(self, plan_data, query):
        """生成索引建议"""
        recommendations = []

        # 分析WHERE子句中的条件
        if "WHERE" in query.upper():
            # 这里可以更精确地解析查询语句
            recommendations.append({
                "type": "where_clause",
                "description": "考虑为WHERE子句中的列创建索引",
                "query_pattern": query[:100] + "..." if len(query) > 100 else query,
                "impact": "high"
            })

        return recommendations

    def _calculate_query_performance_score(self, execution_time, total_cost, buffers):
        """计算查询性能评分"""
        score = 100

        # 基于执行时间扣分
        if execution_time > 5000:  # 5秒
            score -= 50
        elif execution_time > 1000:  # 1秒
            score -= 30
        elif execution_time > 500:  # 0.5秒
            score -= 10

        # 基于缓存命中率扣分
        if buffers:
            total_reads = buffers.get("shared_hit", 0) + buffers.get("shared_read", 0)
            if total_reads > 0:
                hit_ratio = buffers.get("shared_hit", 0) / total_reads
                if hit_ratio < 0.8:  # 80%
                    score -= 20
                elif hit_ratio < 0.9:  # 90%
                    score -= 10

        return max(0, score)

    def _analyze_query_pattern_for_indexes(self, pattern, table_stats):
        """分析查询模式以生成索引建议"""
        # 这里可以实现更复杂的查询模式分析
        return {
            "query_pattern": pattern,
            "recommended_indexes": [
                {
                    "table": "matches",
                    "columns": ["date", "league_id"],
                    "type": "btree",
                    "reason": "常见的时间范围和联赛查询"
                }
            ]
        }

    def _generate_partitioning_suggestions(self, table_stats):
        """生成分区建议"""
        suggestions = []

        for table_name, stats in table_stats.items():
            if isinstance(stats, dict):
                row_count = stats.get("row_count", 0)
                if row_count > 10000000:  # 1000万行
                    suggestions.append({
                        "table": table_name,
                        "type": "range",
                        "partition_column": "date",
                        "reason": "大表建议按时间分区",
                        "expected_benefit": "提升查询性能和维护效率"
                    })

        return suggestions

    def _create_index_optimization_plan(self, index_recs, partitioning_recs):
        """创建索引优化实施计划"""
        plan = []

        # 创建索引的计划
        if index_recs:
            plan.append({
                "phase": "index_creation",
                "duration": "1-2 hours",
                "steps": [
                    "分析现有索引使用情况",
                    "创建推荐的索引",
                    "监控索引效果",
                    "删除不必要的索引"
                ],
                "priority": "high"
            })

        # 分区计划
        if partitioning_recs:
            plan.append({
                "phase": "partitioning",
                "duration": "2-4 hours",
                "steps": [
                    "备份表数据",
                    "创建分区表结构",
                    "迁移数据到分区表",
                    "验证分区效果"
                ],
                "priority": "medium"
            })

        return plan

# 技能实例
database_performance_skill = DatabasePerformanceSkill()

# 导出技能信息
def get_skill_info():
    return {
        "name": database_performance_skill.skill_name,
        "description": "Database Performance - PostgreSQL性能调优专家",
        "capabilities": database_performance_skill.capabilities,
        "version": "1.0.0"
    }

# 主要功能函数
async def analyze_performance(connection_params):
    """分析数据库性能"""
    return await database_performance_skill.analyze_postgres_performance(connection_params)

def optimize_for_dataset(current_config, dataset_size_gb=50, expected_qps=1000):
    """优化大数据集配置"""
    return database_performance_skill.optimize_for_large_dataset(
        current_config, dataset_size_gb, expected_qps
    )

if __name__ == "__main__":
    # 示例用法
    print("Database Performance Skill initialized")
    print(f"Capabilities: {database_performance_skill.capabilities}")