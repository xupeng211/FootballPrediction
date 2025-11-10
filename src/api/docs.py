#!/usr/bin/env python3
"""
API文档增强端点
Enhanced API Documentation Endpoints

Author: Claude Code
Version: 1.0.0
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config.swagger_ui_config import SwaggerUIConfig
from ..core.config import get_settings

router = APIRouter(prefix="/docs", tags=["API文档"])
settings = get_settings()


@router.get("/enhanced", response_class=HTMLResponse)
async def enhanced_swagger_ui():
    """
    获取增强版Swagger UI页面

    提供了丰富的交互功能，包括：
    - 实时API状态监控
    - 快速操作面板
    - 请求追踪和性能监控
    - 代码示例生成
    - 批量测试功能
    """
    config = SwaggerUIConfig()

    return config.get_custom_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Football Prediction API - 增强版文档",
        oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "operationsSorter": "alpha",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True,
        },
    )


@router.get("/interactive", response_class=HTMLResponse)
async def interactive_playground():
    """
    获取交互式API测试页面

    提供专门用于API测试的界面，包括：
    - 一键测试功能
    - 测试结果保存
    - 性能基准测试
    - 批量API调用
    """

    interactive_html = """
<!DOCTYPE html>
<html>
<head>
    <title>API交互式测试平台</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .api-card {
            transition: all 0.3s ease;
        }
        .api-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        .method-get { border-left: 4px solid #61affe; }
        .method-post { border-left: 4px solid #49cc90; }
        .method-put { border-left: 4px solid #fca130; }
        .method-delete { border-left: 4px solid #f93e3e; }

        .test-result {
            background: #f8f9fa;
            border-radius: 6px;
            padding: 16px;
            margin-top: 12px;
        }

        .loading-spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-100">
    <!-- 头部导航 -->
    <header class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <i class="fas fa-flask text-blue-600 text-2xl mr-3"></i>
                    <h1 class="text-xl font-semibold text-gray-900">API交互式测试平台</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <span id="connection-status" class="flex items-center">
                        <span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                        <span class="text-sm text-gray-600">已连接</span>
                    </span>
                    <button onclick="runAllTests()" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
                        <i class="fas fa-play mr-2"></i>运行所有测试
                    </button>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- 快速测试面板 -->
        <section class="mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-6">快速测试</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

                <!-- 健康检查 -->
                <div class="api-card bg-white rounded-lg shadow-md p-6 method-get">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">健康检查</h3>
                        <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">GET</span>
                    </div>
                    <p class="text-gray-600 mb-4">检查API服务状态和健康度</p>
                    <button onclick="testHealthCheck()" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                        <i class="fas fa-heartbeat mr-2"></i>测试
                    </button>
                    <div id="health-result" class="test-result hidden"></div>
                </div>

                <!-- 获取API信息 -->
                <div class="api-card bg-white rounded-lg shadow-md p-6 method-get">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">API信息</h3>
                        <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">GET</span>
                    </div>
                    <p class="text-gray-600 mb-4">获取API版本和系统信息</p>
                    <button onclick="testApiInfo()" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                        <i class="fas fa-info-circle mr-2"></i>测试
                    </button>
                    <div id="apiinfo-result" class="test-result hidden"></div>
                </div>

                <!-- 创建预测 -->
                <div class="api-card bg-white rounded-lg shadow-md p-6 method-post">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">创建预测</h3>
                        <span class="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">POST</span>
                    </div>
                    <p class="text-gray-600 mb-4">创建新的比赛预测</p>
                    <button onclick="testCreatePrediction()" class="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 transition">
                        <i class="fas fa-chart-line mr-2"></i>测试
                    </button>
                    <div id="prediction-result" class="test-result hidden"></div>
                </div>

                <!-- 获取比赛列表 -->
                <div class="api-card bg-white rounded-lg shadow-md p-6 method-get">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">比赛列表</h3>
                        <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">GET</span>
                    </div>
                    <p class="text-gray-600 mb-4">获取比赛数据列表</p>
                    <button onclick="testMatchList()" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                        <i class="fas fa-list mr-2"></i>测试
                    </button>
                    <div id="matchlist-result" class="test-result hidden"></div>
                </div>

                <!-- 获取用户统计 -->
                <div class="api-card bg-white rounded-lg shadow-md p-6 method-get">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">用户统计</h3>
                        <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">GET</span>
                    </div>
                    <p class="text-gray-600 mb-4">获取用户预测统计数据</p>
                    <button onclick="testUserStats()" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                        <i class="fas fa-chart-bar mr-2"></i>测试
                    </button>
                    <div id="userstats-result" class="test-result hidden"></div>
                </div>

                <!-- 系统监控 -->
                <div class="api-card bg-white rounded-lg shadow-md p-6 method-get">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">系统监控</h3>
                        <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">GET</span>
                    </div>
                    <p class="text-gray-600 mb-4">获取系统性能监控数据</p>
                    <button onclick="testMetrics()" class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                        <i class="fas fa-tachometer-alt mr-2"></i>测试
                    </button>
                    <div id="metrics-result" class="test-result hidden"></div>
                </div>
            </div>
        </section>

        <!-- 测试结果汇总 -->
        <section class="mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-6">测试结果汇总</h2>
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div class="text-center">
                        <div class="text-3xl font-bold text-green-600" id="success-count">0</div>
                        <div class="text-gray-600">成功</div>
                    </div>
                    <div class="text-center">
                        <div class="text-3xl font-bold text-red-600" id="error-count">0</div>
                        <div class="text-gray-600">失败</div>
                    </div>
                    <div class="text-center">
                        <div class="text-3xl font-bold text-blue-600" id="total-count">0</div>
                        <div class="text-gray-600">总计</div>
                    </div>
                    <div class="text-center">
                        <div class="text-3xl font-bold text-purple-600" id="avg-response-time">0ms</div>
                        <div class="text-gray-600">平均响应时间</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 详细测试日志 -->
        <section>
            <div class="flex justify-between items-center mb-6">
                <h2 class="text-2xl font-bold text-gray-900">测试日志</h2>
                <button onclick="clearLogs()" class="text-red-600 hover:text-red-700 transition">
                    <i class="fas fa-trash mr-2"></i>清除日志
                </button>
            </div>
            <div class="bg-white rounded-lg shadow-md p-6">
                <div id="test-logs" class="space-y-4 max-h-96 overflow-y-auto">
                    <div class="text-gray-500 text-center py-8">
                        <i class="fas fa-clipboard-list text-4xl mb-4"></i>
                        <p>暂无测试日志，请运行测试</p>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <script>
        let testResults = {
            success: 0,
            error: 0,
            total: 0,
            responseTimes: []
        };

        function updateStats() {
            document.getElementById('success-count').textContent = testResults.success;
            document.getElementById('error-count').textContent = testResults.error;
            document.getElementById('total-count').textContent = testResults.total;

            if (testResults.responseTimes.length > 0) {
                const avgTime = testResults.responseTimes.reduce((a, b) => a + b, 0) / testResults.responseTimes.length;
                document.getElementById('avg-response-time').textContent = Math.round(avgTime) + 'ms';
            }
        }

        function addLog(message, type = 'info') {
            const logsContainer = document.getElementById('test-logs');
            const timestamp = new Date().toLocaleTimeString();

            const logEntry = document.createElement('div');
            logEntry.className = `p-4 rounded-lg border-l-4 ${
                type === 'success' ? 'bg-green-50 border-green-500' :
                type === 'error' ? 'bg-red-50 border-red-500' :
                type === 'warning' ? 'bg-yellow-50 border-yellow-500' :
                'bg-gray-50 border-gray-300'
            }`;

            const icon = type === 'success' ? 'check-circle' :
                         type === 'error' ? 'exclamation-circle' :
                         type === 'warning' ? 'exclamation-triangle' : 'info-circle';

            const color = type === 'success' ? 'text-green-600' :
                         type === 'error' ? 'text-red-600' :
                         type === 'warning' ? 'text-yellow-600' : 'text-blue-600';

            logEntry.innerHTML = `
                <div class="flex items-start">
                    <i class="fas fa-${icon} ${color} mt-1 mr-3"></i>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="font-medium text-gray-900">${message}</span>
                            <span class="text-sm text-gray-500">${timestamp}</span>
                        </div>
                    </div>
                </div>
            `;

            if (logsContainer.firstChild.classList.contains('text-center')) {
                logsContainer.innerHTML = '';
            }

            logsContainer.insertBefore(logEntry, logsContainer.firstChild);

            // 限制日志数量
            while (logsContainer.children.length > 20) {
                logsContainer.removeChild(logsContainer.lastChild);
            }
        }

        async function makeAPIRequest(method, endpoint, data = null) {
            const startTime = Date.now();

            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Test-Client': 'Interactive-Playground'
                    }
                };

                if (data) {
                    options.body = JSON.stringify(data);
                }

                const response = await fetch(endpoint, options);
                const responseTime = Date.now() - startTime;

                testResults.responseTimes.push(responseTime);

                if (response.ok) {
                    testResults.success++;
                    const responseData = await response.json();
                    return {
                        success: true,
                        data: responseData,
                        responseTime: responseTime
                    };
                } else {
                    testResults.error++;
                    return {
                        success: false,
                        error: `HTTP ${response.status}: ${response.statusText}`,
                        responseTime: responseTime
                    };
                }
            } catch (error) {
                testResults.error++;
                return {
                    success: false,
                    error: error.message,
                    responseTime: Date.now() - startTime
                };
            } finally {
                testResults.total++;
                updateStats();
            }
        }

        function displayResult(elementId, result) {
            const element = document.getElementById(elementId);
            element.classList.remove('hidden');

            if (result.success) {
                element.innerHTML = `
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-green-600 font-medium">
                            <i class="fas fa-check-circle mr-2"></i>测试成功
                        </span>
                        <span class="text-sm text-gray-500">${result.responseTime}ms</span>
                    </div>
                    <div class="bg-gray-800 text-gray-100 p-3 rounded text-sm overflow-x-auto">
                        <pre>${JSON.stringify(result.data, null, 2)}</pre>
                    </div>
                `;
                addLog(`${elementId.replace('-result', '')} 测试成功 (${result.responseTime}ms)`, 'success');
            } else {
                element.innerHTML = `
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-red-600 font-medium">
                            <i class="fas fa-exclamation-circle mr-2"></i>测试失败
                        </span>
                        <span class="text-sm text-gray-500">${result.responseTime}ms</span>
                    </div>
                    <div class="bg-red-50 border border-red-200 text-red-800 p-3 rounded text-sm">
                        ${result.error}
                    </div>
                `;
                addLog(`${elementId.replace('-result', '')} 测试失败: ${result.error}`, 'error');
            }
        }

        async function testHealthCheck() {
            addLog('开始健康检查测试...');
            const result = await makeAPIRequest('GET', '/health');
            displayResult('health-result', result);
        }

        async function testApiInfo() {
            addLog('开始API信息测试...');
            const result = await makeAPIRequest('GET', '/api/info');
            displayResult('apiinfo-result', result);
        }

        async function testCreatePrediction() {
            addLog('开始创建预测测试...');
            const testData = {
                match_id: "test_match_123",
                home_team: "测试主队",
                away_team: "测试客队",
                match_date: "2025-11-15T20:00:00Z",
                league: "测试联赛"
            };

            const result = await makeAPIRequest('POST', '/predictions/enhanced', testData);
            displayResult('prediction-result', result);
        }

        async function testMatchList() {
            addLog('开始比赛列表测试...');
            const result = await makeAPIRequest('GET', '/matches?page=1&page_size=5');
            displayResult('matchlist-result', result);
        }

        async function testUserStats() {
            addLog('开始用户统计测试...');
            const result = await makeAPIRequest('GET', '/user/statistics');
            displayResult('userstats-result', result);
        }

        async function testMetrics() {
            addLog('开始系统监控测试...');
            const result = await makeAPIRequest('GET', '/api/metrics');
            displayResult('metrics-result', result);
        }

        async function runAllTests() {
            addLog('开始运行所有测试...', 'info');

            // 重置统计
            testResults = {
                success: 0,
                error: 0,
                total: 0,
                responseTimes: []
            };
            updateStats();

            // 依次运行所有测试
            await testHealthCheck();
            await new Promise(resolve => setTimeout(resolve, 500));

            await testApiInfo();
            await new Promise(resolve => setTimeout(resolve, 500));

            await testMatchList();
            await new Promise(resolve => setTimeout(resolve, 500));

            await testCreatePrediction();
            await new Promise(resolve => setTimeout(resolve, 500));

            await testUserStats();
            await new Promise(resolve => setTimeout(resolve, 500));

            await testMetrics();

            addLog(`所有测试完成，成功: ${testResults.success}, 失败: ${testResults.error}`,
                   testResults.error === 0 ? 'success' : 'warning');
        }

        function clearLogs() {
            document.getElementById('test-logs').innerHTML = `
                <div class="text-gray-500 text-center py-8">
                    <i class="fas fa-clipboard-list text-4xl mb-4"></i>
                    <p>暂无测试日志，请运行测试</p>
                </div>
            `;

            testResults = {
                success: 0,
                error: 0,
                total: 0,
                responseTimes: []
            };
            updateStats();
        }

        // 页面加载时检查连接状态
        window.addEventListener('load', function() {
            checkConnection();
            setInterval(checkConnection, 30000); // 每30秒检查一次
        });

        async function checkConnection() {
            try {
                const response = await fetch('/health');
                const statusEl = document.getElementById('connection-status');

                if (response.ok) {
                    statusEl.innerHTML = `
                        <span class="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                        <span class="text-sm text-gray-600">已连接</span>
                    `;
                } else {
                    statusEl.innerHTML = `
                        <span class="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
                        <span class="text-sm text-gray-600">连接异常</span>
                    `;
                }
            } catch (error) {
                const statusEl = document.getElementById('connection-status');
                statusEl.innerHTML = `
                    <span class="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                    <span class="text-sm text-gray-600">连接失败</span>
                `;
            }
        }
    </script>
</body>
</html>
    """

    return interactive_html


@router.get("/examples", response_class=HTMLResponse)
async def api_examples():
    """
    获取API使用示例页面

    提供各种编程语言的使用示例，包括：
    - Python SDK使用
    - JavaScript/Node.js示例
    - Java示例
    - cURL命令示例
    """

    examples_html = """
<!DOCTYPE html>
<html>
<head>
    <title>API使用示例 - Football Prediction</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/plugins/autoloader/prism-autoloader.min.js"></script>
</head>
<body class="bg-gray-100">
    <header class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <i class="fas fa-code text-blue-600 text-2xl mr-3"></i>
                    <h1 class="text-xl font-semibold text-gray-900">API使用示例</h1>
                </div>
                <nav class="flex space-x-4">
                    <button onclick="showExamples('python')" class="tab-btn text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Python</button>
                    <button onclick="showExamples('javascript')" class="tab-btn text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">JavaScript</button>
                    <button onclick="showExamples('java')" class="tab-btn text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Java</button>
                    <button onclick="showExamples('curl')" class="tab-btn text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">cURL</button>
                </nav>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Python示例 -->
        <div id="python-examples" class="examples-content">
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">Python SDK使用示例</h2>
                <div class="prose max-w-none">
                    <p class="text-gray-600 mb-6">使用官方Python SDK快速集成API功能</p>
                </div>

                <div class="space-y-6">
                    <!-- 安装SDK -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">1. 安装SDK</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-bash">pip install football-prediction-sdk</code></pre>
                        </div>
                    </div>

                    <!-- 基础使用 -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">2. 基础使用</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-python">from football_prediction_sdk import FootballPredictionClient
from datetime import datetime

# 初始化客户端
client = FootballPredictionClient(
    api_key="your_api_key",
    base_url="https://api.football-prediction.com/v1"
)

# 创建预测
request = PredictionRequest(
    match_id="match_123",
    home_team="Manchester United",
    away_team="Liverpool",
    match_date=datetime(2025, 11, 15, 20, 0),
    league="Premier League"
)

try:
    response = client.predictions.create(request)
    prediction = response.prediction

    print(f"预测ID: {prediction.prediction_id}")
    print(f"主胜概率: {prediction.probabilities['home_win']:.2%}")
    print(f"推荐投注: {prediction.recommended_bet}")

except Exception as e:
    print(f"预测失败: {e}")</code></pre>
                        </div>
                    </div>

                    <!-- 批量预测 -->
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">3. 批量预测</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-python"># 创建多个预测请求
requests = [
    PredictionRequest(
        match_id="match_123",
        home_team="Team A",
        away_team="Team B",
        match_date=datetime(2025, 11, 15, 20, 0),
        league="Premier League"
    ),
    PredictionRequest(
        match_id="match_124",
        home_team="Team C",
        away_team="Team D",
        match_date=datetime(2025, 11, 16, 15, 0),
        league="Premier League"
    )
]

# 批量创建预测
batch_result = client.predictions.batch_create(requests)
print(f"批量ID: {batch_result['batch_id']}")
print(f"处理时间: {batch_result['processing_estimated_time']}秒")</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- JavaScript示例 -->
        <div id="javascript-examples" class="examples-content hidden">
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">JavaScript使用示例</h2>
                <div class="space-y-6">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">基础API调用</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-javascript">const API_BASE_URL = 'https://api.football-prediction.com/v1';
const API_KEY = 'your_api_key';

class FootballPredictionAPI {
    constructor(apiKey, baseUrl = API_BASE_URL) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        };
    }

    async createPrediction(matchData) {
        try {
            const response = await fetch(`${this.baseUrl}/predictions/enhanced`, {
                method: 'POST',
                headers: this.headers,
                body: JSON.stringify(matchData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('创建预测失败:', error);
            throw error;
        }
    }

    async getMatchList(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = `${this.baseUrl}/matches${queryString ? '?' + queryString : ''}`;

        try {
            const response = await fetch(url, {
                headers: this.headers
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('获取比赛列表失败:', error);
            throw error;
        }
    }
}

// 使用示例
const api = new FootballPredictionAPI(API_KEY);

// 创建预测
const matchData = {
    match_id: "match_123",
    home_team: "Manchester United",
    away_team: "Liverpool",
    match_date: "2025-11-15T20:00:00Z",
    league: "Premier League"
};

api.createPrediction(matchData)
    .then(response => {
        console.log('预测创建成功:', response);
    })
    .catch(error => {
        console.error('预测创建失败:', error);
    });

// 获取比赛列表
api.getMatchList({ page: 1, page_size: 10 })
    .then(response => {
        console.log('比赛列表:', response.data);
    })
    .catch(error => {
        console.error('获取比赛列表失败:', error);
    });</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Java示例 -->
        <div id="java-examples" class="examples-content hidden">
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">Java使用示例</h2>
                <div class="space-y-6">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">Maven依赖</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-xml">&lt;dependency&gt;
    &lt;groupId&gt;com.football-prediction&lt;/groupId&gt;
    &lt;artifactId&gt;sdk&lt;/artifactId&gt;
    &lt;version&gt;1.0.0&lt;/version&gt;
&lt;/dependency&gt;</code></pre>
                        </div>
                    </div>

                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">基础使用</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-java">import com.football.prediction.sdk.FootballPredictionClient;
import com.football.prediction.sdk.model.PredictionRequest;
import com.football.prediction.sdk.model.PredictionResponse;

public class PredictionExample {
    public static void main(String[] args) {
        // 初始化客户端
        FootballPredictionClient client = new FootballPredictionClient
            .Builder("your_api_key")
            .baseUrl("https://api.football-prediction.com/v1")
            .timeout(30000)
            .build();

        try {
            // 创建预测请求
            PredictionRequest request = PredictionRequest.builder()
                .matchId("match_123")
                .homeTeam("Manchester United")
                .awayTeam("Liverpool")
                .matchDate("2025-11-15T20:00:00Z")
                .league("Premier League")
                .build();

            // 发送预测请求
            PredictionResponse response = client.predictions()
                .create(request);

            // 处理响应
            if (response.isSuccess()) {
                System.out.println("预测ID: " + response.getPrediction().getPredictionId());
                System.out.println("主胜概率: " +
                    String.format("%.2f%%",
                        response.getPrediction().getProbabilities().get("home_win") * 100));
            }

        } catch (Exception e) {
            System.err.println("预测失败: " + e.getMessage());
        }
    }
}</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- cURL示例 -->
        <div id="curl-examples" class="examples-content hidden">
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">cURL命令示例</h2>
                <div class="space-y-6">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">1. 健康检查</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-bash">curl -X GET "https://api.football-prediction.com/v1/health" \\
  -H "Accept: application/json"</code></pre>
                        </div>
                    </div>

                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">2. 创建预测</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-bash">curl -X POST "https://api.football-prediction.com/v1/predictions/enhanced" \\
  -H "Authorization: Bearer your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "match_id": "match_123",
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "match_date": "2025-11-15T20:00:00Z",
    "league": "Premier League"
  }'</code></pre>
                        </div>
                    </div>

                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">3. 获取比赛列表</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-bash">curl -X GET "https://api.football-prediction.com/v1/matches?page=1&page_size=10" \\
  -H "Authorization: Bearer your_api_key" \\
  -H "Accept: application/json"</code></pre>
                        </div>
                    </div>

                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 mb-3">4. 获取预测结果</h3>
                        <div class="bg-gray-800 rounded-lg p-4">
                            <pre><code class="language-bash">curl -X GET "https://api.football-prediction.com/v1/predictions/pred_12345" \\
  -H "Authorization: Bearer your_api_key" \\
  -H "Accept: application/json"</code></pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        function showExamples(language) {
            // 隐藏所有内容
            document.querySelectorAll('.examples-content').forEach(el => {
                el.classList.add('hidden');
            });

            // 重置所有按钮样式
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('text-blue-600', 'font-semibold');
                btn.classList.add('text-gray-600');
            });

            // 显示选中的内容
            document.getElementById(language + '-examples').classList.remove('hidden');

            // 高亮选中的按钮
            event.target.classList.remove('text-gray-600');
            event.target.classList.add('text-blue-600', 'font-semibold');
        }

        // 默认显示Python示例
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelector('[onclick="showExamples(\'python\')"]').click();
        });
    </script>
</body>
</html>
    """

    return examples_html


@router.get("/openapi.json")
async def get_openapi_spec() -> dict[str, Any]:
    """获取OpenAPI规范JSON"""
    # 这里应该从应用获取OpenAPI规范
    # 暂时返回基本结构
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Football Prediction API",
            "version": "1.0.0",
            "description": "足球比赛结果预测系统API",
        },
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
    }


@router.get("/status")
async def docs_status():
    """获取文档系统状态"""
    return {
        "status": "active",
        "features": {
            "enhanced_swagger_ui": True,
            "interactive_playground": True,
            "api_examples": True,
            "real_time_monitoring": True,
        },
        "endpoints": {
            "enhanced_docs": "/docs/enhanced",
            "interactive_playground": "/docs/interactive",
            "api_examples": "/docs/examples",
            "openapi_spec": "/docs/openapi.json",
            "standard_docs": "/docs",
            "redoc": "/redoc",
        },
        "last_updated": datetime.now().isoformat(),
    }


def setup_docs_routes(app) -> None:
    """设置文档路由"""
    app.include_router(router)
