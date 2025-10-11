# TODO: 此文件过长（750行），需要拆分为更小的模块
# TODO: This file is too long (750 lines), needs to be split into smaller modules

"""
性能分析器
Performance Analyzer

提供性能数据分析和优化建议：
- 性能瓶颈识别
- 资源使用分析
- 趋势分析
- 优化建议生成
- 性能报告生成
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

from src.core.logging import get_logger

logger = get_logger(__name__)


class PerformanceInsight(BaseModel):
    """性能洞察数据结构"""

    category: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    impact: str
    recommendation: str
    metrics: Dict[str, Any] = {}
    timestamp: datetime


class PerformanceTrend(BaseModel):
    """性能趋势数据"""

    metric_name: str
    time_series: List[Tuple[datetime, float]]
    trend: str  # improving, stable, degrading
    slope: float
    confidence: float


class PerformanceAnalyzer:
    """性能分析器主类"""

    def __init__(self):
        """初始化性能分析器"""
        self.insights: List[PerformanceInsight] = []
        self.trends: Dict[str, PerformanceTrend] = {}
        self.thresholds = self._load_default_thresholds()

    def _load_default_thresholds(self) -> Dict[str, Dict]:
        """加载默认的性能阈值"""
        return {
            "response_time": {
                "excellent": 0.1,  # 100ms
                "good": 0.5,  # 500ms
                "acceptable": 1.0,  # 1s
                "poor": 2.0,  # 2s
            },
            "memory_usage": {
                "excellent": 50,  # 50MB
                "good": 100,  # 100MB
                "acceptable": 200,  # 200MB
                "poor": 500,  # 500MB
            },
            "cpu_usage": {
                "excellent": 20,  # 20%
                "good": 50,  # 50%
                "acceptable": 70,  # 70%
                "poor": 90,  # 90%
            },
            "error_rate": {
                "excellent": 0.01,  # 0.01%
                "good": 0.1,  # 0.1%
                "acceptable": 1.0,  # 1%
                "poor": 5.0,  # 5%
            },
            "throughput": {
                "excellent": 1000,  # 1000 req/s
                "good": 500,  # 500 req/s
                "acceptable": 100,  # 100 req/s
                "poor": 50,  # 50 req/s
            },
        }

    def analyze_api_performance(self, api_stats: Dict) -> List[PerformanceInsight]:
        """分析API性能"""
        insights = []

        # 分析响应时间
        if "response_time" in api_stats:
            avg_time = api_stats["response_time"]["average"]
            p95_time = api_stats["response_time"]["p95"]
            api_stats["response_time"]["max"]

            # 平均响应时间分析
            if avg_time > self.thresholds["response_time"]["poor"]:
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="api",
                        severity="critical",
                        title="API响应时间过慢",
                        description=f"平均响应时间为{avg_time:.2f}秒，超过可接受阈值",
                        impact="严重影响用户体验，可能导致请求超时",
                        recommendation="优化数据库查询、添加缓存、减少不必要的计算",
                        metrics={
                            "avg_response_time": avg_time,
                            "threshold": self.thresholds["response_time"]["poor"],
                        },
                    )
                )
            elif avg_time > self.thresholds["response_time"]["acceptable"]:
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="api",
                        severity="medium",
                        title="API响应时间需要优化",
                        description=f"平均响应时间为{avg_time:.2f}秒，接近可接受阈值上限",
                        impact="影响用户体验，需要关注",
                        recommendation="检查慢查询、优化算法、考虑异步处理",
                        metrics={"avg_response_time": avg_time},
                    )
                )

            # P95响应时间分析
            if p95_time > avg_time * 3:
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="api",
                        severity="high",
                        title="API响应时间不稳定",
                        description=f"P95响应时间({p95_time:.2f}s)是平均值的{p95_time/avg_time:.1f}倍",
                        impact="部分用户响应时间过长，体验不一致",
                        recommendation="检查是否存在性能尖峰，优化异常情况处理",
                        metrics={"p95_time": p95_time, "avg_time": avg_time},
                    )
                )

        # 分析并发请求
        max_concurrent = api_stats.get("max_concurrent_requests", 0)
        if max_concurrent > 100:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="api",
                    severity="high",
                    title="高并发请求",
                    description=f"最大并发请求数达到{max_concurrent}",
                    impact="可能导致服务器资源耗尽",
                    recommendation="考虑使用负载均衡、限流、或垂直扩展",
                    metrics={"max_concurrent": max_concurrent},
                )
            )

        # 分析慢端点
        slow_endpoints = api_stats.get("slow_endpoints", [])
        if slow_endpoints:
            for endpoint in slow_endpoints[:3]:  # 最慢的3个端点
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="api",
                        severity="high",
                        title=f"慢端点: {endpoint['endpoint']}",
                        description=f"端点{endpoint['endpoint']}平均响应时间{endpoint['average_duration']:.2f}秒",
                        impact="该端点性能较差，影响整体系统性能",
                        recommendation="优化该端点的业务逻辑、数据库查询或添加缓存",
                        metrics=endpoint,
                    )
                )

        return insights

    def analyze_database_performance(self, db_stats: Dict) -> List[PerformanceInsight]:
        """分析数据库性能"""
        insights = []

        # 分析查询统计
        if "query_types" in db_stats:
            for query_type, stats in db_stats["query_types"].items():
                avg_time = stats["average_time"]
                error_rate = stats["error_rate"]

                # 查询时间分析
                if avg_time > 0.5:  # 超过500ms
                    insights.append(
                        PerformanceInsight(  # type: ignore
                            category="database",
                            severity="high" if avg_time > 1.0 else "medium",
                            title=f"{query_type}查询过慢",
                            description=f"{query_type}查询平均耗时{avg_time:.2f}秒",
                            impact="影响API响应时间，降低系统吞吐量",
                            recommendation="优化SQL语句、添加索引、考虑使用查询缓存",
                            metrics={"query_type": query_type, "avg_time": avg_time},
                        )
                    )

                # 错误率分析
                if error_rate > 0.05:  # 错误率超过5%
                    insights.append(
                        PerformanceInsight(  # type: ignore
                            category="database",
                            severity="critical" if error_rate > 0.1 else "high",
                            title=f"{query_type}查询错误率过高",
                            description=f"{query_type}查询错误率为{error_rate:.2%}",
                            impact="数据操作失败，影响系统可靠性",
                            recommendation="检查数据库连接、SQL语法、数据完整性约束",
                            metrics={
                                "query_type": query_type,
                                "error_rate": error_rate,
                            },
                        )
                    )

        # 分析慢查询
        slow_queries = db_stats.get("slow_queries", [])
        if len(slow_queries) > 10:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="database",
                    severity="medium",
                    title="慢查询数量过多",
                    description=f"发现{len(slow_queries)}个慢查询",
                    impact="影响数据库整体性能",
                    recommendation="定期分析慢查询日志，优化查询语句",
                    metrics={"slow_query_count": len(slow_queries)},
                )
            )

        return insights

    def analyze_cache_performance(self, cache_stats: Dict) -> List[PerformanceInsight]:
        """分析缓存性能"""
        insights = []

        hit_rate = cache_stats.get("hit_rate", 0)
        total_requests = cache_stats.get("total_requests", 0)

        # 命中率分析
        if hit_rate < 0.5 and total_requests > 100:  # 命中率低于50%
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="cache",
                    severity="medium",
                    title="缓存命中率过低",
                    description=f"缓存命中率为{hit_rate:.2%}，低于理想值",
                    impact="增加数据库负载，降低响应速度",
                    recommendation="优化缓存策略、调整TTL、增加缓存预热",
                    metrics={"hit_rate": hit_rate, "total_requests": total_requests},
                )
            )
        elif hit_rate < 0.8 and total_requests > 100:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="cache",
                    severity="low",
                    title="缓存命中率可提升",
                    description=f"缓存命中率为{hit_rate:.2%}，有提升空间",
                    impact="适度影响性能",
                    recommendation="分析缓存未命中的原因，优化缓存键设计",
                    metrics={"hit_rate": hit_rate},
                )
            )

        # 缓存操作时间分析
        avg_hit_time = cache_stats.get("average_hit_time", 0)
        avg_set_time = cache_stats.get("average_set_time", 0)

        if avg_hit_time > 0.01:  # 超过10ms
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="cache",
                    severity="medium",
                    title="缓存读取时间过长",
                    description=f"缓存平均读取时间{avg_hit_time*1000:.2f}ms",
                    impact="影响缓存效果，增加请求延迟",
                    recommendation="检查缓存服务器性能、网络延迟、序列化方式",
                    metrics={"avg_hit_time": avg_hit_time},
                )
            )

        if avg_set_time > 0.05:  # 超过50ms
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="cache",
                    severity="medium",
                    title="缓存写入时间过长",
                    description=f"缓存平均写入时间{avg_set_time*1000:.2f}ms",
                    impact="影响写操作性能",
                    recommendation="优化缓存写入策略、考虑批量写入、异步写入",
                    metrics={"avg_set_time": avg_set_time},
                )
            )

        return insights

    def analyze_memory_usage(self, memory_data: List[Dict]) -> List[PerformanceInsight]:
        """分析内存使用情况"""
        insights = []  # type: ignore

        if not memory_data:
            return insights

        # 计算内存使用统计
        memory_values = [m["rss"] for m in memory_data]
        avg_memory = np.mean(memory_values)
        max_memory = np.max(memory_values)
        np.min(memory_values)

        # 内存使用水平分析
        if max_memory > self.thresholds["memory_usage"]["poor"]:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="memory",
                    severity="critical",
                    title="内存使用过高",
                    description=f"最大内存使用达到{max_memory:.1f}MB",
                    impact="可能导致OOM错误，系统不稳定",
                    recommendation="检查内存泄漏、优化数据结构、增加内存配置",
                    metrics={
                        "max_memory": max_memory,
                        "threshold": self.thresholds["memory_usage"]["poor"],
                    },
                )
            )
        elif avg_memory > self.thresholds["memory_usage"]["acceptable"]:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="memory",
                    severity="medium",
                    title="内存使用较高",
                    description=f"平均内存使用为{avg_memory:.1f}MB",
                    impact="可能影响系统性能",
                    recommendation="监控内存增长趋势，优化内存使用",
                    metrics={"avg_memory": avg_memory},
                )
            )

        # 内存增长趋势分析
        if len(memory_data) > 10:
            # 计算内存增长率
            start_memory = memory_values[0]
            end_memory = memory_values[-1]
            growth_rate = (end_memory - start_memory) / start_memory * 100

            if growth_rate > 20:  # 增长超过20%
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="memory",
                        severity="high",
                        title="内存使用持续增长",
                        description=f"内存使用增长了{growth_rate:.1f}%",
                        impact="可能存在内存泄漏",
                        recommendation="使用内存分析工具检查泄漏点",
                        metrics={
                            "growth_rate": growth_rate,
                            "start_memory": start_memory,
                            "end_memory": end_memory,
                        },
                    )
                )

        return insights

    def analyze_task_performance(self, task_stats: Dict) -> List[PerformanceInsight]:
        """分析后台任务性能"""
        insights = []

        # 分析活跃任务
        active_tasks = task_stats.get("active_tasks", 0)
        if active_tasks > 50:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="tasks",
                    severity="medium",
                    title="活跃后台任务过多",
                    description=f"当前有{active_tasks}个活跃的后台任务",
                    impact="可能影响系统响应性能",
                    recommendation="检查任务队列长度，考虑增加工作进程",
                    metrics={"active_tasks": active_tasks},
                )
            )

        # 分析任务执行情况
        task_types = task_stats.get("task_types", {})
        for task_name, stats in task_types.items():
            success_rate = stats["success_rate"]
            avg_time = stats["average_time"]

            # 成功率分析
            if success_rate < 0.9 and stats["total_count"] > 10:
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="tasks",
                        severity="high" if success_rate < 0.8 else "medium",
                        title=f"任务{task_name}成功率低",
                        description=f"任务{task_name}成功率为{success_rate:.2%}",
                        impact="任务执行失败，影响业务流程",
                        recommendation="检查任务失败原因，增加重试机制",
                        metrics={"task_name": task_name, "success_rate": success_rate},
                    )
                )

            # 执行时间分析
            if avg_time > 300:  # 超过5分钟
                insights.append(
                    PerformanceInsight(  # type: ignore
                        category="tasks",
                        severity="medium",
                        title=f"任务{task_name}执行时间过长",
                        description=f"任务{task_name}平均执行时间{avg_time/60:.1f}分钟",
                        impact="占用系统资源时间过长",
                        recommendation="优化任务逻辑，考虑拆分为小任务",
                        metrics={"task_name": task_name, "avg_time": avg_time},
                    )
                )

        # 分析最近失败
        recent_failures = task_stats.get("recent_failures", [])
        if len(recent_failures) > 5:
            insights.append(
                PerformanceInsight(  # type: ignore
                    category="tasks",
                    severity="high",
                    title="任务失败频繁",
                    description=f"最近有{len(recent_failures)}个任务失败",
                    impact="影响系统可靠性",
                    recommendation="检查失败原因，修复问题或增加容错机制",
                    metrics={"failure_count": len(recent_failures)},
                )
            )

        return insights

    def analyze_performance_trend(
        self, metric_data: Dict[str, List[Tuple[datetime, float]]]
    ) -> Dict[str, PerformanceTrend]:
        """分析性能趋势"""
        trends = {}

        for metric_name, data_points in metric_data.items():
            if len(data_points) < 10:
                continue

            # 转换为numpy数组
            times = np.array(
                [(t - data_points[0][0]).total_seconds() for t, _ in data_points]
            )
            values = np.array([v for _, v in data_points])

            # 线性回归分析趋势
            if len(times) > 1:
                slope, intercept = np.polyfit(times, values, 1)
                r_squared = self._calculate_r_squared(times, values, slope, intercept)

                # 判断趋势
                if abs(slope) < 0.001:
                    trend = "stable"
                elif slope > 0:
                    trend = "degrading"  # 值越大越差（如响应时间）
                else:
                    trend = "improving"

                trends[metric_name] = PerformanceTrend(
                    metric_name=metric_name,
                    time_series=data_points,
                    trend=trend,
                    slope=slope,
                    confidence=r_squared,
                )

        return trends

    def _calculate_r_squared(
        self, x: np.ndarray, y: np.ndarray, slope: float, intercept: float
    ) -> float:
        """计算R²值"""
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    def generate_optimization_recommendations(
        self, insights: List[PerformanceInsight]
    ) -> List[Dict]:
        """生成优化建议"""
        recommendations = []

        # 按严重程度分组
        critical_issues = [i for i in insights if i.severity == "critical"]
        high_issues = [i for i in insights if i.severity == "high"]
        [i for i in insights if i.severity == "medium"]

        # 生成优先级建议
        if critical_issues:
            recommendations.append(
                {
                    "priority": "critical",
                    "title": "立即处理关键性能问题",
                    "description": f"发现{len(critical_issues)}个关键性能问题需要立即处理",
                    "actions": ["分配专人处理", "制定修复计划", "监控修复效果"],
                    "related_issues": [i.title for i in critical_issues],
                }
            )

        if high_issues:
            recommendations.append(
                {
                    "priority": "high",
                    "title": "优先处理高优先级问题",
                    "description": f"发现{len(high_issues)}个高优先级性能问题",
                    "actions": ["纳入迭代计划", "评估影响范围", "准备回滚方案"],
                    "related_issues": [i.title for i in high_issues],
                }
            )

        # 生成优化策略建议
        categories = set(i.category for i in insights)
        for category in categories:
            category_issues = [i for i in insights if i.category == category]
            recommendations.append(
                {
                    "priority": "optimization",
                    "title": f"{category.upper()}模块优化建议",
                    "description": f"针对{category}模块的{len(category_issues)}个问题进行优化",
                    "optimization_strategies": self._get_category_optimization_strategies(
                        category
                    ),
                    "related_issues": [i.title for i in category_issues],
                }
            )

        return recommendations

    def _get_category_optimization_strategies(self, category: str) -> List[str]:
        """获取特定类别的优化策略"""
        strategies = {
            "api": [
                "实施请求缓存",
                "优化数据库查询",
                "使用CDN加速静态资源",
                "实现响应压缩",
                "考虑异步处理",
            ],
            "database": [
                "优化SQL查询",
                "添加合适的索引",
                "使用查询缓存",
                "考虑读写分离",
                "优化表结构",
            ],
            "cache": [
                "调整缓存策略",
                "优化缓存键设计",
                "实现缓存预热",
                "考虑多级缓存",
                "监控缓存效果",
            ],
            "memory": [
                "修复内存泄漏",
                "优化数据结构",
                "使用内存池",
                "实现对象复用",
                "调整JVM/Python内存配置",
            ],
            "tasks": [
                "优化任务队列",
                "实现任务优先级",
                "增加重试机制",
                "使用批处理",
                "监控任务执行",
            ],
        }
        return strategies.get(category, ["分析性能瓶颈", "优化代码逻辑", "增加监控"])

    def generate_performance_report(
        self,
        api_stats: Optional[Dict] = None,
        db_stats: Optional[Dict] = None,
        cache_stats: Optional[Dict] = None,
        memory_data: Optional[List[Dict]] = None,
        task_stats: Optional[Dict] = None,
    ) -> Dict:
        """生成综合性能报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_insights": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
            },
            "insights": [],
            "trends": {},
            "recommendations": [],
        }

        # 收集各类洞察
        all_insights = []

        if api_stats:
            all_insights.extend(self.analyze_api_performance(api_stats))

        if db_stats:
            all_insights.extend(self.analyze_database_performance(db_stats))

        if cache_stats:
            all_insights.extend(self.analyze_cache_performance(cache_stats))

        if memory_data:
            all_insights.extend(self.analyze_memory_usage(memory_data))

        if task_stats:
            all_insights.extend(self.analyze_task_performance(task_stats))

        # 统计洞察
        report["insights"] = all_insights  # type: ignore
        report["summary"]["total_insights"] = len(all_insights)  # type: ignore
        report["summary"]["critical_issues"] = len(  # type: ignore
            [i for i in all_insights if i.severity == "critical"]
        )
        report["summary"]["high_issues"] = len(  # type: ignore
            [i for i in all_insights if i.severity == "high"]
        )
        report["summary"]["medium_issues"] = len(  # type: ignore
            [i for i in all_insights if i.severity == "medium"]
        )
        report["summary"]["low_issues"] = len(  # type: ignore
            [i for i in all_insights if i.severity == "low"]
        )

        # 生成建议
        if all_insights:
            report["recommendations"] = self.generate_optimization_recommendations(  # type: ignore
                all_insights
            )

        # 生成趋势分析
        # 这里需要历史数据，暂时跳过
        # report["trends"] = self.analyze_performance_trend(trend_data)

        # 生成性能评分
        report["performance_score"] = self._calculate_performance_score(all_insights)

        return report

    def _calculate_performance_score(self, insights: List[PerformanceInsight]) -> Dict:
        """计算性能评分（0-100）"""
        if not insights:
            return {"score": 100, "grade": "A"}

        # 根据严重程度扣分
        deductions = {"critical": 20, "high": 10, "medium": 5, "low": 2}

        total_deduction = sum(deductions.get(i.severity, 0) for i in insights)
        score = max(0, 100 - total_deduction)

        # 评级
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "deduction_breakdown": {
                severity: sum(1 for i in insights if i.severity == severity)
                for severity in ["critical", "high", "medium", "low"]
            },
        }

    def export_report(self, report: Dict, format: str = "json") -> str:
        """导出性能报告"""
        if format == "json":
            return json.dumps(report, indent=2, default=str)
        elif format == "html":
            return self._generate_html_report(report)
        else:
            return str(report)

    def _generate_html_report(self, report: Dict) -> str:
        """生成HTML格式的报告"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>性能分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .score {{ font-size: 24px; font-weight: bold; }}
                .critical {{ color: #d32f2f; }}
                .high {{ color: #f57c00; }}
                .medium {{ color: #fbc02d; }}
                .low {{ color: #388e3c; }}
                .insight {{ margin: 10px 0; padding: 10px; border-left: 4px solid; }}
                .insight.critical {{ border-color: #d32f2f; background-color: #ffebee; }}
                .insight.high {{ border-color: #f57c00; background-color: #fff3e0; }}
                .insight.medium {{ border-color: #fbc02d; background-color: #fffde7; }}
                .insight.low {{ border-color: #388e3c; background-color: #e8f5e9; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>性能分析报告</h1>
                <p>生成时间: {report['timestamp']}</p>
                <div class="score">
                    性能评分: {report['performance_score']['score']}/100 ({report['performance_score']['grade']})
                </div>
            </div>

            <h2>问题摘要</h2>
            <ul>
                <li>关键问题: {report['summary']['critical_issues']}</li>
                <li>高优先级问题: {report['summary']['high_issues']}</li>
                <li>中优先级问题: {report['summary']['medium_issues']}</li>
                <li>低优先级问题: {report['summary']['low_issues']}</li>
            </ul>

            <h2>性能洞察</h2>
        """

        for insight in report["insights"]:
            html += f"""
            <div class="insight {insight['severity']}">
                <h3 class="{insight['severity']}">{insight['title']}</h3>
                <p><strong>描述:</strong> {insight['description']}</p>
                <p><strong>影响:</strong> {insight['impact']}</p>
                <p><strong>建议:</strong> {insight['recommendation']}</p>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html
