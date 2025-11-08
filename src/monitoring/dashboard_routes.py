"""
实时监控仪表板路由
Real-time Monitoring Dashboard Routes

提供Web界面和WebSocket接口的实时性能监控。
"""

import logging

from fastapi import (
    APIRouter,
    FastAPI,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketState,
)
from fastapi.responses import HTMLResponse

from .realtime_dashboard import monitoring_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# ============================================================================
# HTML Dashboard Template
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FootballPrediction 实时监控仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            overflow-x: hidden;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #4a5568;
            font-size: 1.8rem;
            font-weight: 600;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: #f7fafc;
            border-radius: 2rem;
            font-size: 0.9rem;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #48bb78;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 2rem;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }

        .metric-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .metric-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #2d3748;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #4299e1;
            margin-bottom: 0.5rem;
        }

        .metric-unit {
            font-size: 0.9rem;
            color: #718096;
            margin-left: 0.25rem;
        }

        .metric-change {
            font-size: 0.85rem;
            font-weight: 500;
        }

        .metric-change.positive {
            color: #48bb78;
        }

        .metric-change.negative {
            color: #f56565;
        }

        .chart-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 1rem;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            height: 400px;
        }

        .alert-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .alert-item {
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .alert-item.warning {
            background: #fef5e7;
            border-left: 4px solid #f39c12;
            color: #d68910;
        }

        .alert-item.critical {
            background: #fadbd8;
            border-left: 4px solid #e74c3c;
            color: #c0392b;
        }

        .alert-icon {
            font-size: 1.2rem;
        }

        .alert-message {
            flex: 1;
            font-weight: 500;
        }

        .alert-time {
            font-size: 0.85rem;
            color: #718096;
        }

        .connection-status {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        }

        .connection-status.connected {
            border-left: 4px solid #48bb78;
        }

        .connection-status.disconnected {
            border-left: 4px solid #f56565;
        }

        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
            font-size: 1.1rem;
            color: #718096;
        }

        @media (max-width: 768px) {
            .container {
                padding: 0 1rem;
            }

            .metrics-grid {
                grid-template-columns: 1fr;
            }

            .header {
                flex-direction: column;
                gap: 1rem;
            }

            .connection-status {
                bottom: 1rem;
                right: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 FootballPrediction 实时监控仪表板</h1>
        <div class="status-indicator">
            <div class="status-dot"></div>
            <span id="connection-status">连接中...</span>
        </div>
    </div>

    <div class="container">
        <!-- 实时指标卡片 -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">📊 总请求数</span>
                    <span class="metric-change positive" id="requests-change">+0%</span>
                </div>
                <div class="metric-value">
                    <span id="total-requests">0</span>
                </div>
                <div style="color: #718096; font-size: 0.9rem;">过去5分钟</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">⚡ 平均响应时间</span>
                    <span class="metric-change" id="response-change">0ms</span>
                </div>
                <div class="metric-value">
                    <span id="avg-response-time">0</span>
                    <span class="metric-unit">ms</span>
                </div>
                <div style="color: #718096; font-size: 0.9rem;">API响应性能</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">🎯 缓存命中率</span>
                    <span class="metric-change positive" id="cache-change">+0%</span>
                </div>
                <div class="metric-value">
                    <span id="cache-hit-rate">0</span>
                    <span class="metric-unit">%</span>
                </div>
                <div style="color: #718096; font-size: 0.9rem;">Redis缓存性能</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">💾 数据库连接</span>
                    <span class="metric-change" id="db-change">稳定</span>
                </div>
                <div class="metric-value">
                    <span id="db-connections">0</span>
                    <span class="metric-unit">/20</span>
                </div>
                <div style="color: #718096; font-size: 0.9rem;">活跃连接数</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">🖥️ CPU使用率</span>
                    <span class="metric-change" id="cpu-change">0%</span>
                </div>
                <div class="metric-value">
                    <span id="cpu-usage">0</span>
                    <span class="metric-unit">%</span>
                </div>
                <div style="color: #718096; font-size: 0.9rem;">系统资源</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">🧠 内存使用率</span>
                    <span class="metric-change" id="memory-change">0%</span>
                </div>
                <div class="metric-value">
                    <span id="memory-usage">0</span>
                    <span class="metric-unit">%</span>
                </div>
                <div style="color: #718096; font-size: 0.9rem;">系统资源</div>
            </div>
        </div>

        <!-- 实时图表 -->
        <div class="chart-container">
            <canvas id="performance-chart"></canvas>
        </div>

        <!-- 告警面板 -->
        <div class="alert-container">
            <h3 style="margin-bottom: 1rem; color: #2d3748;">🚨 告警信息</h3>
            <div id="alerts-container">
                <div class="loading">暂无告警信息</div>
            </div>
        </div>
    </div>

    <!-- 连接状态指示器 -->
    <div class="connection-status" id="connection-indicator">
        <span id="connection-indicator-text">连接中...</span>
    </div>

    <script>
        // WebSocket连接管理
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        const reconnectDelay = 3000;

        // 图表配置
        const ctx = document.getElementById('performance-chart').getContext('2d');
        const performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: '响应时间 (ms)',
                        data: [],
                        borderColor: '#4299e1',
                        backgroundColor: 'rgba(66, 153, 225, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '请求/秒',
                        data: [],
                        borderColor: '#48bb78',
                        backgroundColor: 'rgba(72, 187, 120, 0.1)',
                        tension: 0.4,
                        fill: true,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: '实时性能趋势'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '时间'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '响应时间 (ms)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '请求/秒'
                        },
                        grid: {
                            drawOnChartArea: false,
                        }
                    }
                }
            }
        });

        // 历史数据存储
        let previousMetrics = null;
        const maxDataPoints = 50;

        // 连接WebSocket
        function connectWebSocket() {
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/monitoring/ws`;

                ws = new WebSocket(wsUrl);

                ws.onopen = function() {
                    console.log('WebSocket连接已建立');
                    updateConnectionStatus(true);
                    reconnectAttempts = 0;
                };

                ws.onmessage = function(event) {
                    try {
                        const metrics = JSON.parse(event.data);
                        updateDashboard(metrics);
                    } catch (error) {
                        console.error('解析WebSocket消息失败:', error);
                    }
                };

                ws.onclose = function() {
                    console.log('WebSocket连接已关闭');
                    updateConnectionStatus(false);
                    attemptReconnect();
                };

                ws.onerror = function(error) {
                    console.error('WebSocket错误:', error);
                    updateConnectionStatus(false);
                };

            } catch (error) {
                console.error('创建WebSocket连接失败:', error);
                updateConnectionStatus(false);
            }
        }

        // 尝试重连
        function attemptReconnect() {
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`尝试重连 (${reconnectAttempts}/${maxReconnectAttempts})...`);
                setTimeout(connectWebSocket, reconnectDelay);
            } else {
                updateConnectionStatus(false, '重连失败');
            }
        }

        // 更新连接状态
        function updateConnectionStatus(connected, message = null) {
            const statusElement = document.getElementById('connection-status');
            const indicatorElement = document.getElementById('connection-indicator');
            const indicatorTextElement = document.getElementById('connection-indicator-text');

            if (connected) {
                statusElement.textContent = '已连接';
                indicatorElement.className = 'connection-status connected';
                indicatorTextElement.textContent = '实时连接';
            } else {
                statusElement.textContent = message || '连接断开';
                indicatorElement.className = 'connection-status disconnected';
                indicatorTextElement.textContent = message || '连接断开';
            }
        }

        // 更新仪表板数据
        function updateDashboard(metrics) {
            // 更新指标卡片
            updateMetricCards(metrics);

            // 更新图表
            updateChart(metrics);

            // 更新告警
            updateAlerts(metrics);

            // 保存当前指标作为历史数据
            previousMetrics = metrics;
        }

        // 更新指标卡片
        function updateMetricCards(metrics) {
            const system = metrics.system || {};
            const cache = metrics.cache || {};
            const database = metrics.database || {};
            const systemInfo = metrics.system_info || {};

            // 计算变化率
            const requestsChange = previousMetrics ?
                ((system.total_requests - (previousMetrics.system?.total_requests || 0)) / (previousMetrics.system?.total_requests || 1) * 100).toFixed(1) : 0;

            // 更新DOM元素
            document.getElementById('total-requests').textContent = system.total_requests || 0;
            document.getElementById('avg-response-time').textContent = ((system.avg_response_time || 0) * 1000).toFixed(0);
            document.getElementById('cache-hit-rate').textContent = (cache.hit_rate || 0).toFixed(1);
            document.getElementById('db-connections').textContent = database.active_connections || 0;
            document.getElementById('cpu-usage').textContent = (systemInfo.cpu_percent || 0).toFixed(1);
            document.getElementById('memory-usage').textContent = (systemInfo.memory_percent || 0).toFixed(1);

            // 更新变化指示器
            updateChangeIndicator('requests-change', requestsChange);
            updateChangeIndicator('response-change', ((system.avg_response_time || 0) * 1000).toFixed(0) + 'ms');
            updateChangeIndicator('cache-change', '+' + (cache.hit_rate || 0).toFixed(1) + '%');
            updateChangeIndicator('cpu-change', (systemInfo.cpu_percent || 0).toFixed(1) + '%');
            updateChangeIndicator('memory-change', (systemInfo.memory_percent || 0).toFixed(1) + '%');
        }

        // 更新变化指示器
        function updateChangeIndicator(elementId, value) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value;

                // 根据值设置颜色
                if (value.includes('+') || value.includes('稳定')) {
                    element.className = 'metric-change positive';
                } else if (value.includes('-')) {
                    element.className = 'metric-change negative';
                } else {
                    element.className = 'metric-change';
                }
            }
        }

        // 更新图表
        function updateChart(metrics) {
            const system = metrics.system || {};
            const timestamp = new Date(metrics.timestamp).toLocaleTimeString();

            // 添加新数据点
            performanceChart.data.labels.push(timestamp);
            performanceChart.data.datasets[0].data.push((system.avg_response_time || 0) * 1000);
            performanceChart.data.datasets[1].data.push(system.requests_per_second || 0);

            // 限制数据点数量
            if (performanceChart.data.labels.length > maxDataPoints) {
                performanceChart.data.labels.shift();
                performanceChart.data.datasets[0].data.shift();
                performanceChart.data.datasets[1].data.shift();
            }

            performanceChart.update('none');
        }

        // 更新告警
        function updateAlerts(metrics) {
            const alerts = metrics.alerts || [];
            const container = document.getElementById('alerts-container');

            if (alerts.length === 0) {
                container.innerHTML = '<div class="loading">暂无告警信息 ✅</div>';
                return;
            }

            container.innerHTML = alerts.map(alert => `
                <div class="alert-item ${alert.level}">
                    <span class="alert-icon">${alert.level === 'critical' ? '🚨' : '⚠️'}</span>
                    <span class="alert-message">${alert.message}</span>
                    <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</span>
                </div>
            `).join('');
        }

        // 页面加载时建立连接
        document.addEventListener('DOMContentLoaded', function() {
            connectWebSocket();
        });

        // 页面卸载时关闭连接
        window.addEventListener('beforeunload', function() {
            if (ws) {
                ws.close();
            }
        });
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """获取监控仪表板页面"""
    return DASHBOARD_HTML


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点用于实时数据推送"""
    await websocket.accept()
    await monitoring_manager.register_client(websocket)

    try:
        # 启动监控（如果还没有启动）
        if not monitoring_manager.monitoring_active:
            await monitoring_manager.start_monitoring()

        # 保持连接活跃
        while websocket.client_state == WebSocketState.CONNECTED:
            await websocket.receive_text()  # 等待客户端消息保持连接

    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        await monitoring_manager.unregister_client(websocket)


@router.get("/metrics")
async def get_current_metrics():
    """获取当前性能指标"""
    try:
        metrics = await monitoring_manager._collect_metrics()
        return {"status": "success", "data": metrics}
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/metrics/history")
async def get_metrics_history(minutes: int = Query(30, ge=1, le=1440)):
    """获取历史指标数据"""
    try:
        history = monitoring_manager.get_metrics_history(minutes)
        return {"status": "success", "data": history, "count": len(history)}
    except Exception as e:
        logger.error(f"获取历史指标失败: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/start")
async def start_monitoring():
    """启动监控"""
    try:
        await monitoring_manager.initialize()
        await monitoring_manager.start_monitoring()
        return {"status": "success", "message": "监控已启动"}
    except Exception as e:
        logger.error(f"启动监控失败: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/stop")
async def stop_monitoring():
    """停止监控"""
    try:
        await monitoring_manager.stop_monitoring()
        return {"status": "success", "message": "监控已停止"}
    except Exception as e:
        logger.error(f"停止监控失败: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/status")
async def get_monitoring_status():
    """获取监控状态"""
    return {
        "status": "success",
        "data": {
            "monitoring_active": monitoring_manager.monitoring_active,
            "connected_clients": len(monitoring_manager.connected_clients),
            "update_interval": monitoring_manager.update_interval,
            "metrics_history_count": len(monitoring_manager.metrics_history),
            "initialized": monitoring_manager.performance_optimizer is not None,
        },
    }


def setup_monitoring_routes(app: FastAPI):
    """设置监控路由"""
    app.include_router(router)
    logger.info("监控路由已注册")
