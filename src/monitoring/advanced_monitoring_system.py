from typing import List
from typing import Dict
from typing import Any
from src.core.config import 
from src.core.config import 
""""""""
高级质量监控系统
Issue #123: Phase 3: 高级质量监控系统开发

提供实时Web监控面板和质量门禁功能：
- 实时质量指标收集
- Web监控面板
- 自动化质量门禁
- 告警系统
- 仪表盘可视化
""""""""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import asyncio

from fastapi.responses import HTMLResponse
import uvicorn

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """质量指标数据类"""

    timestamp: datetime
    overall_score: float
    test_coverage: float
    code_quality_score: float
    security_score: float
    performance_score: float
    reliability_score: float
    maintainability_index: float
    technical_debt_ratio: float
    srs_compliance: float
    ml_model_accuracy: float
    api_availability: float
    error_rate: float
    response_time: float


@dataclass
class QualityGate:
    """质量门禁配置"""

    name: str
    threshold: float
    operator: str  # "gte", "lte", "eq"
    critical: bool = False
    description: str = ""


class AdvancedMonitoringSystem:
    """高级质量监控系统"""

    def __init__(self):
        self.app = FastAPI(title="高级质量监控系统", version="1.0.0")
        self.metrics_history: List[QualityMetrics] = []
        self.quality_gates: List[QualityGate] = []
        self.alerts_sent: List[Dict] = []
        self.monitoring_active = False

        # 设置路由
        self._setup_routes()

        # 初始化质量门禁
        self._init_quality_gates()

    def _init_quality_gates(self):
        """初始化质量门禁规则"""
        self.quality_gates = [
            QualityGate(
                name="综合质量分数",
                threshold=8.5,
                operator="gte",
                critical=True,
                description="系统整体质量分数必须≥8.5",
            ),
            QualityGate(
                name="测试覆盖率",
                threshold=80.0,
                operator="gte",
                critical=True,
                description="测试覆盖率必须≥80%",
            ),
            QualityGate(
                name="代码质量分数",
                threshold=8.0,
                operator="gte",
                critical=True,
                description="代码质量分数必须≥8.0",
            ),
            QualityGate(
                name="安全分数",
                threshold=9.0,
                operator="gte",
                critical=True,
                description="安全分数必须≥9.0",
            ),
            QualityGate(
                name="SRS符合性",
                threshold=95.0,
                operator="gte",
                critical=True,
                description="SRS符合性必须≥95%",
            ),
            QualityGate(
                name="ML模型准确率",
                threshold=65.0,
                operator="gte",
                critical=False,
                description="ML模型准确率必须≥65%",
            ),
            QualityGate(
                name="API可用性",
                threshold=99.0,
                operator="gte",
                critical=True,
                description="API可用性必须≥99%",
            ),
            QualityGate(
                name="错误率",
                threshold=5.0,
                operator="lte",
                critical=True,
                description="错误率必须≤5%",
            ),
            QualityGate(
                name="响应时间",
                threshold=500.0,
                operator="lte",
                critical=False,
                description="平均响应时间必须≤500ms",
            ),
            QualityGate(
                name="技术债务比例",
                threshold=10.0,
                operator="lte",
                critical=False,
                description="技术债务比例必须≤10%",
            ),
        ]

    def _setup_routes(self):
        """设置API路由"""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """主监控面板"""
            return await self._generate_dashboard_html()

        @self.app.get("/api/metrics/current")
        async def get_current_metrics():
            """获取当前质量指标"""
            if not self.metrics_history:
                return {"error": "暂无质量指标数据"}

            latest = self.metrics_history[-1]
            return {
                "timestamp": latest.timestamp.isoformat(),
                "metrics": asdict(latest),
                "quality_gates": await self._check_quality_gates(latest),
                "status": ("healthy" if await self._evaluate_health(latest) else "unhealthy"),
            }

        @self.app.get("/api/metrics/history")
        async def get_metrics_history(limit: int = 100):
            """获取历史质量指标"""
            history = self.metrics_history[-limit:] if limit > 0 else self.metrics_history
            return {
                "metrics": [asdict(m) for m in history],
                "total_count": len(history),
            }

        @self.app.get("/api/quality-gates")
        async def get_quality_gates():
            """获取质量门禁配置"""
            return {
                "gates": [asdict(gate) for gate in self.quality_gates],
                "total_count": len(self.quality_gates),
            }

        @self.app.get("/api/alerts")
        async def get_alerts(limit: int = 50):
            """获取告警历史"""
            alerts = self.alerts_sent[-limit:] if limit > 0 else self.alerts_sent
            return {"alerts": alerts, "total_count": len(alerts)}

        @self.app.post("/api/monitoring/start")
        async def start_monitoring(background_tasks: BackgroundTasks):
            """启动监控"""
            if self.monitoring_active:
                return {"status": "already_running"}

            background_tasks.add_task(self._start_monitoring_loop)
            self.monitoring_active = True
            return {"status": "started"}

        @self.app.post("/api/monitoring/stop")
        async def stop_monitoring():
            """停止监控"""
            self.monitoring_active = False
            return {"status": "stopped"}

        @self.app.get("/api/health")
        async def health_check():
            """健康检查端点"""
            return {
                "status": "healthy" if self.monitoring_active else "stopped",
                "monitoring_active": self.monitoring_active,
                "metrics_count": len(self.metrics_history),
                "last_update": (
                    self.metrics_history[-1].timestamp.isoformat() if self.metrics_history else None
                ),
            }

    async def _collect_metrics(self) -> QualityMetrics:
        """收集质量指标"""
        try:
            # 使用独立的质量指标收集器
            from .quality_metrics_collector import QualityMetricsCollector

            collector = QualityMetricsCollector()
            metrics_data = await collector.collect_all_metrics()

            # 转换为QualityMetrics对象
            metrics = QualityMetrics(
                timestamp=datetime.now(timezone.utc),
                overall_score=metrics_data.get("overall_score", 0.0),
                test_coverage=metrics_data.get("test_coverage", 0.0),
                code_quality_score=metrics_data.get("code_quality_score", 0.0),
                security_score=metrics_data.get("security_score", 10.0),
                performance_score=metrics_data.get("performance_score", 8.0),
                reliability_score=metrics_data.get("reliability_score", 8.0),
                maintainability_index=metrics_data.get("maintainability_index", 70.0),
                technical_debt_ratio=metrics_data.get("technical_debt_ratio", 5.0),
                srs_compliance=metrics_data.get("srs_compliance", 95.0),
                ml_model_accuracy=metrics_data.get("ml_model_accuracy", 0.0),
                api_availability=metrics_data.get("api_availability", 99.0),
                error_rate=metrics_data.get("error_rate", 2.0),
                response_time=metrics_data.get("response_time", 200.0),
            )

            logger.info(f"收集质量指标完成: 综合分数 {metrics.overall_score}/10")
            return metrics

        except Exception as e:
            logger.error(f"收集质量指标失败: {e}")
            # 返回默认指标
            return QualityMetrics(
                timestamp=datetime.now(timezone.utc),
                overall_score=7.0,
                test_coverage=75.0,
                code_quality_score=7.0,
                security_score=9.0,
                performance_score=7.5,
                reliability_score=7.5,
                maintainability_index=65.0,
                technical_debt_ratio=8.0,
                srs_compliance=90.0,
                ml_model_accuracy=60.0,
                api_availability=95.0,
                error_rate=5.0,
                response_time=300.0,
            )

    async def _check_quality_gates(self, metrics: QualityMetrics) -> Dict[str, Any]:
        """检查质量门禁"""
        results = {"passed": 0, "failed": 0, "critical_failed": 0, "gates": []}

        for gate in self.quality_gates:
            # 获取指标值
            metric_value = getattr(metrics, self._get_metric_field_name(gate.name))

            # 评估门禁
            passed = self._evaluate_gate(gate, metric_value)

            gate_result = {
                "name": gate.name,
                "threshold": gate.threshold,
                "current": metric_value,
                "passed": passed,
                "critical": gate.critical,
                "description": gate.description,
            }

            results["gates"].append(gate_result)

            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
                if gate.critical:
                    results["critical_failed"] += 1

        results["overall_status"] = "passed" if results["critical_failed"] == 0 else "failed"
        return results

    def _get_metric_field_name(self, gate_name: str) -> str:
        """获取指标字段名映射"""
        mapping = {
            "综合质量分数": "overall_score",
            "测试覆盖率": "test_coverage",
            "代码质量分数": "code_quality_score",
            "安全分数": "security_score",
            "SRS符合性": "srs_compliance",
            "ML模型准确率": "ml_model_accuracy",
            "API可用性": "api_availability",
            "错误率": "error_rate",
            "响应时间": "response_time",
            "技术债务比例": "technical_debt_ratio",
        }
        return mapping.get(gate_name, "overall_score")

    def _evaluate_gate(self, gate: QualityGate, value: float) -> bool:
        """评估单个质量门禁"""
        if gate.operator == "gte":
            return value >= gate.threshold
        elif gate.operator == "lte":
            return value <= gate.threshold
        elif gate.operator == "eq":
            return abs(value - gate.threshold) < 0.01
        return False

    async def _evaluate_health(self, metrics: QualityMetrics) -> bool:
        """评估系统整体健康状态"""
        gate_results = await self._check_quality_gates(metrics)
        return gate_results["critical_failed"] == 0

    async def _send_alert(self, gate: QualityGate, current_value: float):
        """发送告警"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gate_name": gate.name,
            "threshold": gate.threshold,
            "current_value": current_value,
            "severity": "critical" if gate.critical else "warning",
            "description": f"质量门禁失败: {gate.name} 当前值 {current_value}, 阈值 {gate.threshold}",
        }

        self.alerts_sent.append(alert)
        logger.warning(f"质量告警: {alert['description']}")

        # 这里可以集成实际的告警系统（邮件、Slack等）

    async def _start_monitoring_loop(self):
        """启动监控循环"""
        logger.info("启动质量监控循环")

        while self.monitoring_active:
            try:
                # 收集指标
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)

                # 保持历史记录不超过1000条
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]

                # 检查质量门禁
                gate_results = await self._check_quality_gates(metrics)

                # 发送告警
                for gate_result in gate_results["gates"]:
                    if not gate_result["passed"]:
                        gate = next(g for g in self.quality_gates if g.name == gate_result["name"])
                        await self._send_alert(gate, gate_result["current"])

                # 等待60秒
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(60)

    async def _generate_dashboard_html(self) -> str:
        """生成监控面板HTML"""
        return """"""""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>高级质量监控系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .metric-card { @apply bg-white rounded-lg shadow-md p-6; }
        .status-healthy { @apply text-green-600; }
        .status-unhealthy { @apply text-red-600; }
        .status-warning { @apply text-yellow-600; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <!-- 标题栏 -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">🚀 高级质量监控系统</h1>
            <p class="text-gray-600">实时监控足球预测系统质量指标和SRS符合性</p>
        </div>

        <!-- 状态概览 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="metric-card">
                <h3 class="text-lg font-semibold mb-2">系统状态</h3>
                <div id="system-status" class="text-2xl font-bold">检查中...</div>
            </div>
            <div class="metric-card">
                <h3 class="text-lg font-semibold mb-2">综合质量分数</h3>
                <div id="overall-score" class="text-2xl font-bold">--</div>
            </div>
            <div class="metric-card">
                <h3 class="text-lg font-semibold mb-2">测试覆盖率</h3>
                <div id="test-coverage" class="text-2xl font-bold">--</div>
            </div>
            <div class="metric-card">
                <h3 class="text-lg font-semibold mb-2">SRS符合性</h3>
                <div id="srs-compliance" class="text-2xl font-bold">--</div>
            </div>
        </div>

        <!-- 质量门禁状态 -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4">🛡️ 质量门禁状态</h2>
            <div id="quality-gates" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div class="text-gray-500">加载中...</div>
            </div>
        </div>

        <!-- 图表区域 -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4">📈 质量趋势</h2>
                <canvas id="quality-trend-chart"></canvas>
            </div>
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4">🎯 关键指标雷达图</h2>
                <canvas id="metrics-radar-chart"></canvas>
            </div>
        </div>

        <!-- 控制面板 -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold mb-4">⚙️ 监控控制</h2>
            <div class="flex gap-4">
                <button id =
    "start-monitoring" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                    启动监控
                </button>
                <button id =
    "stop-monitoring" class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
                    停止监控
                </button>
                <button id =
    "refresh-data" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    刷新数据
                </button>
            </div>
        </div>

        <!-- 告警区域 -->
        <div class="bg-white rounded-lg shadow-md p-6 mt-8">
            <h2 class="text-xl font-semibold mb-4">🚨 最近告警</h2>
            <div id="alerts-container" class="space-y-2">
                <div class="text-gray-500">暂无告警</div>
            </div>
        </div>
    </div>

    <script>
        let qualityTrendChart = null;
        let metricsRadarChart = null;
        let monitoringInterval = null;

        // 初始化图表
        function initCharts() {
            const trendCtx = document.getElementById('quality-trend-chart').getContext('2d');
            qualityTrendChart = new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '综合质量分数',
                        data: [],
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 10
                        }
                    }
                }
            });

            const radarCtx = document.getElementById('metrics-radar-chart').getContext('2d');
            metricsRadarChart = new Chart(radarCtx, {
                type: 'radar',
                data: {
                    labels: ['测试覆盖率', '代码质量', '安全性', 'SRS符合性', 'API可用性'],
                    datasets: [{
                        label: '当前指标',
                        data: [],
                        borderColor: 'rgb(34, 197, 94)',
                        backgroundColor: 'rgba(34, 197, 94, 0.2)'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }

        // 获取当前指标
        async function fetchCurrentMetrics() {
            try {
                const response = await fetch('/api/metrics/current');
                const data = await response.json();

                if (data.error) {
                    document.getElementById('system-status').innerHTML =
    '<span class="status-warning">⚠️ 无数据</span>';
                    return;
                }

                // 更新状态卡片
                const statusClass =
    data.status === 'healthy' ? 'status-healthy' : 'status-unhealthy';
                const statusText = data.status === 'healthy' ? '✅ 健康' : '❌ 异常';
                document.getElementById('system-status').innerHTML =
    `<span class="${statusClass}">${statusText}</span>`;

                document.getElementById('overall-score').innerHTML =
    `<span class="text-blue-600">${data.metrics.overall_score.toFixed(1)}/10</span>`;
                document.getElementById('test-coverage').innerHTML =
    `<span class="text-green-600">${data.metrics.test_coverage.toFixed(1)}%</span>`;
                document.getElementById('srs-compliance').innerHTML =
    `<span class="text-purple-600">${data.metrics.srs_compliance.toFixed(1)}%</span>`;

                // 更新质量门禁
                updateQualityGates(data.quality_gates);

                // 更新图表
                updateCharts(data.metrics);

            } catch (error) {
                console.error('获取指标失败:', error);
                document.getElementById('system-status').innerHTML =
    '<span class="status-unhealthy">❌ 连接失败</span>';
            }
        }

        // 更新质量门禁显示
        function updateQualityGates(gateResults) {
            const container = document.getElementById('quality-gates');
            container.innerHTML = '';

            gateResults.gates.forEach(gate => {
                const gateClass =
    gate.passed ? 'bg-green-100 border-green-300' : 'bg-red-100 border-red-300';
                const statusIcon = gate.passed ? '✅' : '❌';
                const statusText = gate.passed ? '通过' : '失败';

                const gateElement = document.createElement('div');
                gateElement.className = `border rounded-lg p-4 ${gateClass}`;
                gateElement.innerHTML = `
                    <div class="flex items-center justify-between">
                        <span class="font-semibold">${statusIcon} ${gate.name}</span>
                        <span class="text-sm">${gate.current.toFixed(1)} / ${gate.threshold}</span>
                    </div>
                    <div class="text-sm text-gray-600 mt-1">${statusText}</div>
                    ${gate.critical ? '<div class="text-xs text-red-600 mt-1">关键门禁</div>' : ''}
                `;
                container.appendChild(gateElement);
            });
        }

        // 更新图表
        function updateCharts(metrics) {
            // 更新趋势图
            if (qualityTrendChart) {
                const now = new Date().toLocaleTimeString();
                qualityTrendChart.data.labels.push(now);
                qualityTrendChart.data.datasets[0].data.push(metrics.overall_score);

                // 保持最近20个数据点
                if (qualityTrendChart.data.labels.length > 20) {
                    qualityTrendChart.data.labels.shift();
                    qualityTrendChart.data.datasets[0].data.shift();
                }

                qualityTrendChart.update();
            }

            // 更新雷达图
            if (metricsRadarChart) {
                metricsRadarChart.data.datasets[0].data = [
                    metrics.test_coverage,
                    metrics.code_quality_score * 10,
                    metrics.security_score * 10,
                    metrics.srs_compliance,
                    metrics.api_availability
                ];
                metricsRadarChart.update();
            }
        }

        // 启动监控
        async function startMonitoring() {
            try {
                const response = await fetch('/api/monitoring/start', {method: 'POST'});
                const data = await response.json();

                if (data.status === 'started') {
                    // 开始自动刷新
                    if (monitoringInterval) clearInterval(monitoringInterval);
                    monitoringInterval = setInterval(fetchCurrentMetrics, 30000); // 30秒刷新一次
                    fetchCurrentMetrics(); // 立即获取一次
                }
            } catch (error) {
                console.error('启动监控失败:', error);
            }
        }

        // 停止监控
        async function stopMonitoring() {
            try {
                const response = await fetch('/api/monitoring/stop', {method: 'POST'});
                const data = await response.json();

                if (data.status === 'stopped' && monitoringInterval) {
                    clearInterval(monitoringInterval);
                    monitoringInterval = null;
                }
            } catch (error) {
                console.error('停止监控失败:', error);
            }
        }

        // 事件绑定
        document.getElementById('start-monitoring').addEventListener('click', startMonitoring);
        document.getElementById('stop-monitoring').addEventListener('click', stopMonitoring);
        document.getElementById('refresh-data').addEventListener('click', fetchCurrentMetrics);

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            fetchCurrentMetrics();
            // 自动启动监控
            setTimeout(startMonitoring, 1000);
        });
    </script>
</body>
</html>
        """"""""

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """启动监控系统"""
        logger.info(f"启动高级质量监控系统: http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="info")


# 创建全局监控实例
monitoring_system = AdvancedMonitoringSystem()


if __name__ == "__main__":
    # 直接运行监控系统
    monitoring_system.run()
