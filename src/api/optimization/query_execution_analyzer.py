"""查询执行计划分析器
Query Execution Plan Analyzer.

提供SQL查询执行计划分析、索引使用检测和性能瓶颈识别功能。
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlanNode:
    """执行计划节点."""

    node_type: str
    relation_name: str | None = None
    alias: str | None = None
    startup_cost: float = 0.0
    total_cost: float = 0.0
    rows: int = 0
    width: int = 0
    actual_rows: int = 0
    actual_loops: int = 0
    actual_total_time: float = 0.0
    actual_startup_time: float = 0.0
    plans: list["ExecutionPlanNode"] = None
    parent_relationship: str | None = None
    join_type: str | None = None
    index_name: str | None = None
    index_condition: str | None = None
    hash_condition: str | None = None
    sort_key: list[str] | None = None

    def __post_init__(self):
        if self.plans is None:
            self.plans = []


@dataclass
class ExecutionPlanAnalysis:
    """执行计划分析结果."""

    query_hash: str
    query_text: str
    execution_plan: list[ExecutionPlanNode]
    total_cost: float
    estimated_rows: int
    execution_time: float
    planning_time: float
    indexes_used: list[str]
    missing_indexes: list[dict[str, Any]]
    performance_issues: list[dict[str, Any]]
    optimization_suggestions: list[dict[str, Any]]
    analysis_timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "query_hash": self.query_hash,
            "query_text": (
                self.query_text[:200] + "..."
                if len(self.query_text) > 200
                else self.query_text
            ),
            "total_cost": round(self.total_cost, 2),
            "estimated_rows": self.estimated_rows,
            "execution_time": round(self.execution_time, 4),
            "planning_time": round(self.planning_time, 4),
            "indexes_used": self.indexes_used,
            "missing_indexes": self.missing_indexes,
            "performance_issues": self.performance_issues,
            "optimization_suggestions": self.optimization_suggestions,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "execution_plan": self._serialize_plan_nodes(self.execution_plan),
        }

    def _serialize_plan_nodes(
        self, nodes: list[ExecutionPlanNode]
    ) -> list[dict[str, Any]]:
        """序列化执行计划节点."""
        result = []
        for node in nodes:
            node_dict = {
                "node_type": node.node_type,
                "relation_name": node.relation_name,
                "alias": node.alias,
                "startup_cost": round(node.startup_cost, 2),
                "total_cost": round(node.total_cost, 2),
                "rows": node.rows,
                "width": node.width,
                "actual_rows": node.actual_rows,
                "actual_loops": node.actual_loops,
                "actual_total_time": round(node.actual_total_time, 4),
                "actual_startup_time": round(node.actual_startup_time, 4),
                "parent_relationship": node.parent_relationship,
                "join_type": node.join_type,
                "index_name": node.index_name,
                "index_condition": node.index_condition,
                "hash_condition": node.hash_condition,
                "sort_key": node.sort_key,
                "child_plans": self._serialize_plan_nodes(node.plans),
            }
            result.append(node_dict)
        return result


class QueryExecutionAnalyzer:
    """查询执行分析器."""

    def __init__(self):
        self.plan_cache: dict[str, ExecutionPlanAnalysis] = {}
        self.analysis_history: list[dict[str, Any]] = []
        self.performance_patterns: dict[str, list[dict[str, Any]]] = {}

    async def analyze_query_execution_plan(
        self,
        query: str,
        session: AsyncSession,
        analyze_options: dict[str, Any] | None = None,
    ) -> ExecutionPlanAnalysis:
        """分析查询执行计划."""
        query_hash = self._generate_query_hash(query)

        # 检查缓存
        if query_hash in self.plan_cache:
            logger.debug(f"Using cached execution plan for query hash: {query_hash}")
            return self.plan_cache[query_hash]

        try:
            # 获取执行计划
            explain_result = await self._get_execution_plan(
                query, session, analyze_options
            )

            # 解析执行计划
            execution_plan = self._parse_execution_plan(explain_result)

            # 分析性能问题
            analysis = await self._analyze_execution_performance(
                query, query_hash, execution_plan, explain_result
            )

            # 缓存结果
            self.plan_cache[query_hash] = analysis

            # 记录分析历史
            self.analysis_history.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_hash": query_hash,
                    "query_text": query[:100] + "..." if len(query) > 100 else query,
                    "total_cost": analysis.total_cost,
                    "execution_time": analysis.execution_time,
                    "issues_count": len(analysis.performance_issues),
                    "suggestions_count": len(analysis.optimization_suggestions),
                }
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing query execution plan: {e}")
            raise

    async def _get_execution_plan(
        self,
        query: str,
        session: AsyncSession,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """获取执行计划."""
        analyze_format = options.get("format", "JSON") if options else "JSON"
        analyze_options = (
            options.get("options", ["ANALYZE", "BUFFERS"])
            if options
            else ["ANALYZE", "BUFFERS"]
        )

        # 构建EXPLAIN查询
        explain_query = (
            f"EXPLAIN (FORMAT {analyze_format}, {', '.join(analyze_options)}) {query}"
        )

        try:
            result = await session.execute(text(explain_query))
            explain_data = result.fetchone()[0]

            if isinstance(explain_data, str):
                # 如果返回的是字符串格式，尝试解析为JSON
                return self._parse_text_explain(explain_data)
            else:
                # 如果已经是JSON格式
                return explain_data

        except Exception as e:
            logger.error(f"Error getting execution plan: {e}")
            # 返回一个基本的执行计划结构
            return {
                "Plan": {
                    "Node typing.Type": "Result",
                    "Total Cost": 0.0,
                    "Plan Rows": 0,
                    "Actual Total Time": 0.0,
                    "Actual Rows": 0,
                },
                "Execution Time": 0.0,
                "Planning Time": 0.0,
            }

    def _parse_text_explain(self, explain_text: str) -> dict[str, Any]:
        """解析文本格式的EXPLAIN输出."""
        lines = explain_text.strip().split("\n")

        # 查找执行时间信息
        execution_time = 0.0
        planning_time = 0.0

        for line in lines:
            if "Execution Time:" in line:
                execution_time = float(
                    re.search(r"Execution Time:\s*([\d.]+)", line).group(1)
                )
            elif "Planning Time:" in line:
                planning_time = float(
                    re.search(r"Planning Time:\s*([\d.]+)", line).group(1)
                )

        # 创建基本的执行计划结构
        return {
            "Plan": {
                "Node typing.Type": "Unknown",
                "Total Cost": 0.0,
                "Plan Rows": 0,
                "Actual Total Time": execution_time,
                "Actual Rows": 0,
            },
            "Execution Time": execution_time,
            "Planning Time": planning_time,
        }

    def _parse_execution_plan(
        self, explain_data: dict[str, Any]
    ) -> list[ExecutionPlanNode]:
        """解析执行计划."""
        if "Plan" not in explain_data:
            return []

        return [self._parse_plan_node(explain_data["Plan"])]

    def _parse_plan_node(self, node_data: dict[str, Any]) -> ExecutionPlanNode:
        """解析单个执行计划节点."""
        node = ExecutionPlanNode(
            node_type=node_data.get("Node typing.Type", "Unknown"),
            relation_name=node_data.get("Relation Name"),
            alias=node_data.get("Alias"),
            startup_cost=float(node_data.get("Startup Cost", 0.0)),
            total_cost=float(node_data.get("Total Cost", 0.0)),
            rows=int(node_data.get("Plan Rows", 0)),
            width=int(node_data.get("Plan Width", 0)),
            actual_rows=int(node_data.get("Actual Rows", 0)),
            actual_loops=int(node_data.get("Actual Loops", 0)),
            actual_total_time=float(node_data.get("Actual Total Time", 0.0)),
            actual_startup_time=float(node_data.get("Actual Startup Time", 0.0)),
            parent_relationship=node_data.get("Parent Relationship"),
            join_type=node_data.get("Join typing.Type"),
            index_name=node_data.get("Index Name"),
            index_condition=node_data.get("Index Condition"),
            hash_condition=node_data.get("Hash Condition"),
            sort_key=node_data.get("Sort Key", []),
        )

        # 递归解析子计划
        if "Plans" in node_data:
            for child_plan_data in node_data["Plans"]:
                child_node = self._parse_plan_node(child_plan_data)
                node.plans.append(child_node)

        return node

    async def _analyze_execution_performance(
        self,
        query: str,
        query_hash: str,
        execution_plan: list[ExecutionPlanNode],
        explain_data: dict[str, Any],
    ) -> ExecutionPlanAnalysis:
        """分析执行性能."""
        # 计算总成本
        total_cost = sum(node.total_cost for node in execution_plan)
        estimated_rows = sum(node.rows for node in execution_plan)

        # 获取执行时间
        execution_time = explain_data.get("Execution Time", 0.0)
        planning_time = explain_data.get("Planning Time", 0.0)

        # 识别使用的索引
        indexes_used = self._identify_used_indexes(execution_plan)

        # 检测缺失的索引
        missing_indexes = await self._detect_missing_indexes(query, execution_plan)

        # 识别性能问题
        performance_issues = self._identify_performance_issues(
            execution_plan, execution_time
        )

        # 生成优化建议
        optimization_suggestions = await self._generate_optimization_suggestions(
            query, execution_plan, performance_issues, missing_indexes
        )

        return ExecutionPlanAnalysis(
            query_hash=query_hash,
            query_text=query,
            execution_plan=execution_plan,
            total_cost=total_cost,
            estimated_rows=estimated_rows,
            execution_time=execution_time,
            planning_time=planning_time,
            indexes_used=indexes_used,
            missing_indexes=missing_indexes,
            performance_issues=performance_issues,
            optimization_suggestions=optimization_suggestions,
            analysis_timestamp=datetime.utcnow(),
        )

    def _identify_used_indexes(
        self, execution_plan: list[ExecutionPlanNode]
    ) -> list[str]:
        """识别使用的索引."""
        indexes = set()

        for node in execution_plan:
            if node.index_name:
                indexes.add(node.index_name)

            # 递归检查子计划
            if node.plans:
                child_indexes = self._identify_used_indexes(node.plans)
                indexes.update(child_indexes)

        return list(indexes)

    async def _detect_missing_indexes(
        self, query: str, execution_plan: list[ExecutionPlanNode]
    ) -> list[dict[str, Any]]:
        """检测缺失的索引."""
        missing_indexes = []

        for node in execution_plan:
            # 检查是否进行了全表扫描
            if node.node_type == "Seq Scan" and node.relation_name:
                # 分析WHERE条件中的字段
                where_fields = self._extract_where_fields(query)
                if where_fields:
                    missing_indexes.append(
                        {
                            "table": node.relation_name,
                            "fields": where_fields,
                            "reason": "Sequential scan detected on large table",
                            "priority": "high" if node.rows > 1000 else "medium",
                            "estimated_impact": (
                                "high" if node.actual_total_time > 1.0 else "medium"
                            ),
                        }
                    )

            # 检查排序操作
            if node.node_type == "Sort" and not node.index_name:
                sort_fields = self._extract_order_fields(query)
                if sort_fields and node.relation_name:
                    missing_indexes.append(
                        {
                            "table": node.relation_name,
                            "fields": sort_fields,
                            "reason": "Sort operation without index",
                            "priority": "medium",
                            "estimated_impact": "medium",
                        }
                    )

            # 递归检查子计划
            if node.plans:
                child_missing = await self._detect_missing_indexes(query, node.plans)
                missing_indexes.extend(child_missing)

        return missing_indexes

    def _extract_where_fields(self, query: str) -> list[str]:
        """提取WHERE条件中的字段."""
        # 简化的字段提取逻辑
        where_pattern = r"WHERE\s+([^;]+)"
        match = re.search(where_pattern, query, re.IGNORECASE)

        if match:
            where_clause = match.group(1)
            # 提取字段名（简化版本）
            field_pattern = r"(\w+)\s*(?:=|>|<|>=|<=|like|in)"
            fields = re.findall(field_pattern, where_clause, re.IGNORECASE)
            return [
                field.lower()
                for field in fields
                if field.lower() not in ["id", "created_at", "updated_at"]
            ]

        return []

    def _extract_order_fields(self, query: str) -> list[str]:
        """提取ORDER BY字段."""
        order_pattern = r"ORDER\s+BY\s+([^;\s]+(?:\s+(?:ASC|DESC))?)"
        matches = re.findall(order_pattern, query, re.IGNORECASE)

        fields = []
        for match in matches:
            field = match.split()[0]  # 移除ASC/DESC
            if field.lower() not in ["id", "created_at", "updated_at"]:
                fields.append(field.lower())

        return fields

    def _identify_performance_issues(
        self, execution_plan: list[ExecutionPlanNode], execution_time: float
    ) -> list[dict[str, Any]]:
        """识别性能问题."""
        issues = []

        # 检查执行时间
        if execution_time > 5.0:
            issues.append(
                {
                    "typing.Type": "slow_execution",
                    "severity": "high",
                    "description": f"查询执行时间过长: {execution_time:.4f}s",
                    "threshold": 5.0,
                }
            )
        elif execution_time > 1.0:
            issues.append(
                {
                    "typing.Type": "moderate_slow_execution",
                    "severity": "medium",
                    "description": f"查询执行时间较长: {execution_time:.4f}s",
                    "threshold": 1.0,
                }
            )

        # 检查执行计划中的问题
        for node in execution_plan:
            self._check_node_performance_issues(node, issues)

        return issues

    def _check_node_performance_issues(
        self, node: ExecutionPlanNode, issues: list[dict[str, Any]]
    ):
        """检查节点的性能问题."""
        # 检查全表扫描
        if node.node_type == "Seq Scan" and node.rows > 10000:
            issues.append(
                {
                    "typing.Type": "full_table_scan",
                    "severity": "high",
                    "description": f"对表 {node.relation_name} 进行全表扫描，预估行数: {node.rows}",
                    "table": node.relation_name,
                    "estimated_rows": node.rows,
                }
            )

        # 检查嵌套循环连接
        if node.node_type == "Nested Loop" and node.total_cost > 1000:
            issues.append(
                {
                    "typing.Type": "expensive_nested_loop",
                    "severity": "medium",
                    "description": f"昂贵的嵌套循环连接，成本: {node.total_cost:.2f}",
                    "cost": node.total_cost,
                }
            )

        # 检查哈希连接
        if node.node_type == "Hash Join" and node.actual_total_time > 1.0:
            issues.append(
                {
                    "typing.Type": "slow_hash_join",
                    "severity": "medium",
                    "description": f"哈希连接时间过长: {node.actual_total_time:.4f}s",
                    "execution_time": node.actual_total_time,
                }
            )

        # 递归检查子计划
        if node.plans:
            for child_node in node.plans:
                self._check_node_performance_issues(child_node, issues)

    async def _generate_optimization_suggestions(
        self,
        query: str,
        execution_plan: list[ExecutionPlanNode],
        performance_issues: list[dict[str, Any]],
        missing_indexes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """生成优化建议."""
        suggestions = []

        # 基于缺失索引的建议
        for missing_index in missing_indexes:
            suggestion = {
                "typing.Type": "add_index",
                "priority": missing_index["priority"],
                "description": f"在表 {missing_index['table']} 上创建索引",
                "details": {
                    "table": missing_index["table"],
                    "fields": missing_index["fields"],
                    "sql": f"CREATE INDEX idx_{missing_index['table']}_{'_'.join(missing_index['fields'])} ON {missing_index['table']} ({', '.join(missing_index['fields'])})",
                    "estimated_impact": missing_index["estimated_impact"],
                },
            }
            suggestions.append(suggestion)

        # 基于性能问题的建议
        for issue in performance_issues:
            if issue["typing.Type"] == "full_table_scan":
                suggestions.append(
                    {
                        "typing.Type": "optimize_query",
                        "priority": "high",
                        "description": "优化查询以避免全表扫描",
                        "details": {
                            "issue": issue["description"],
                            "suggestion": "添加适当的WHERE条件或索引",
                        },
                    }
                )
            elif issue["typing.Type"] == "slow_execution":
                suggestions.append(
                    {
                        "typing.Type": "query_rewrite",
                        "priority": "high",
                        "description": "重写查询以提高性能",
                        "details": {
                            "issue": issue["description"],
                            "suggestion": "考虑分解复杂查询或使用更高效的JOIN策略",
                        },
                    }
                )

        # 基于查询模式的建议
        query_suggestions = self._analyze_query_patterns(query)
        suggestions.extend(query_suggestions)

        # 去重并按优先级排序
        unique_suggestions = self._deduplicate_suggestions(suggestions)
        return sorted(
            unique_suggestions,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3),
        )

    def _analyze_query_patterns(self, query: str) -> list[dict[str, Any]]:
        """分析查询模式."""
        suggestions = []
        query_lower = query.lower()

        # 检查SELECT *
        if "select *" in query_lower:
            suggestions.append(
                {
                    "typing.Type": "select_specific_fields",
                    "priority": "medium",
                    "description": "避免使用SELECT *，只查询需要的字段",
                    "details": {
                        "current_pattern": "SELECT *",
                        "suggestion": "指定具体字段名以减少数据传输",
                    },
                }
            )

        # 检查LIKE查询
        if "like" in query_lower and "'%" in query:
            suggestions.append(
                {
                    "typing.Type": "optimize_like_query",
                    "priority": "high",
                    "description": "优化LIKE查询以使用索引",
                    "details": {
                        "current_pattern": "LIKE '%pattern'",
                        "suggestion": "使用全文索引或修改查询逻辑",
                    },
                }
            )

        # 检查ORDER BY without LIMIT
        if "order by" in query_lower and "limit" not in query_lower:
            suggestions.append(
                {
                    "typing.Type": "add_limit",
                    "priority": "low",
                    "description": "为ORDER BY查询添加LIMIT",
                    "details": {
                        "current_pattern": "ORDER BY without LIMIT",
                        "suggestion": "添加LIMIT以减少排序开销",
                    },
                }
            )

        return suggestions

    def _deduplicate_suggestions(
        self, suggestions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """去重建议."""
        seen = set()
        unique_suggestions = []

        for suggestion in suggestions:
            # 创建唯一的标识符
            identifier = f"{suggestion['typing.Type']}_{suggestion.get('description', '')}"
            if identifier not in seen:
                seen.add(identifier)
                unique_suggestions.append(suggestion)

        return unique_suggestions

    def _generate_query_hash(self, query: str) -> str:
        """生成查询哈希值."""
        import hashlib

        # 标准化查询文本
        normalized_query = " ".join(query.strip().split()).lower()
        return hashlib.sha256(normalized_query.encode()).hexdigest()

    def get_cached_analysis(self, query_hash: str) -> ExecutionPlanAnalysis | None:
        """获取缓存的分析结果."""
        return self.plan_cache.get(query_hash)

    def clear_cache(self):
        """清空缓存."""
        self.plan_cache.clear()
        logger.info("Execution plan cache cleared")

    def get_analysis_statistics(self) -> dict[str, Any]:
        """获取分析统计信息."""
        if not self.analysis_history:
            return {
                "total_analyzed": 0,
                "avg_execution_time": 0.0,
                "avg_total_cost": 0.0,
                "common_issues": [],
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        total_analyzed = len(self.analysis_history)
        avg_execution_time = (
            sum(record["execution_time"] for record in self.analysis_history)
            / total_analyzed
        )
        avg_total_cost = (
            sum(record["total_cost"] for record in self.analysis_history)
            / total_analyzed
        )

        # 统计常见问题
        issue_types = {}
        for record in self.analysis_history:
            if record["issues_count"] > 0:
                # 这里需要更详细的记录来统计问题类型
                pass

        return {
            "total_analyzed": total_analyzed,
            "cache_size": len(self.plan_cache),
            "avg_execution_time": round(avg_execution_time, 4),
            "avg_total_cost": round(avg_total_cost, 2),
            "common_issues": issue_types,
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }


# 全局查询执行分析器实例
_execution_analyzer: QueryExecutionAnalyzer | None = None


def get_query_execution_analyzer() -> QueryExecutionAnalyzer:
    """获取全局查询执行分析器实例."""
    global _execution_analyzer
    if _execution_analyzer is None:
        _execution_analyzer = QueryExecutionAnalyzer()
    return _execution_analyzer


async def initialize_query_execution_analyzer() -> QueryExecutionAnalyzer:
    """初始化查询执行分析器."""
    global _execution_analyzer
    _execution_analyzer = QueryExecutionAnalyzer()
    logger.info("Query execution analyzer initialized")
    return _execution_analyzer
