#!/usr/bin/env python3
"""Swagger UI 配置和增强功能
Swagger UI Configuration and Enhanced Features.

Author: Claude Code
Version: 1.0.0
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html


class SwaggerUIConfig:
    """Swagger UI 配置管理类."""

    @staticmethod
    def get_custom_swagger_ui_html(
        *,
        openapi_url: str,
        title: str,
        oauth2_redirect_url: str,
        init_oauth: dict[str, Any] | None = None,
        swagger_ui_parameters: dict[str, Any] | None = None,
    ) -> str:
        """获取自定义的Swagger UI HTML页面.

        Args:
            openapi_url: OpenAPI JSON文档URL
            title: 页面标题
            oauth2_redirect_url: OAuth2重定向URL
            init_oauth: OAuth初始化配置
            swagger_ui_parameters: Swagger UI参数

        Returns:
            str: 自定义的HTML页面
        """
        # 默认配置
        default_config = {
            "deepLinking": True,
            "displayRequestDuration": True,
            "docExpansion": "none",
            "operationsSorter": "alpha",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True,
            "requestInterceptor": """
                function(request) {
                    // 添加请求ID追踪
                    request.headers['X-Request-ID'] = generateUUID();
                    return request;
                }
            """,
            "responseInterceptor": """
                function(response) {
                    // 记录响应时间
                    if (response.duration) {
                        console.log(`Request duration: ${response.duration}ms`);
                    }
                    return response;
                }
            """,
        }

        # 合并用户配置
        if swagger_ui_parameters:
            default_config.update(swagger_ui_parameters)

        str(default_config).replace("'", '"')

        custom_html = f"""
<!DOCTYPE html>
<html>
<head>
    <link typing.Type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui.css" />
    <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
    <title>{title} - Swagger UI</title>
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}

        /* 自定义样式 */
        .swagger-ui .topbar {{
            background-color: #1b1b1b;
            border-bottom: 1px solid #000;
        }}

        .swagger-ui .topbar .download-url-wrapper .download-url-button {{
            background: #49cc90;
            color: #fff;
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
        }}

        .swagger-ui .info {{
            margin: 50px 0;
        }}

        .swagger-ui .info .title {{
            color: #3b4151;
            font-size: 36px;
            margin: 0;
        }}

        .swagger-ui .scheme-container {{
            background: #fff;
            border-radius: 4px;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,.15);
            margin: 0 0 20px;
            padding: 30px;
        }}

        .swagger-ui .opblock.opblock-post {{
            border-color: #49cc90;
            background: rgba(73,204,144,.1);
        }}

        .swagger-ui .opblock.opblock-get {{
            border-color: #61affe;
            background: rgba(97,175,254,.1);
        }}

        .swagger-ui .opblock.opblock-put {{
            border-color: #fca130;
            background: rgba(252,161,48,.1);
        }}

        .swagger-ui .opblock.opblock-delete {{
            border-color: #f93e3e;
            background: rgba(249,62,62,.1);
        }}

        .swagger-ui .opblock.opblock-patch {{
            border-color: #50e3c2;
            background: rgba(80,227,194,.1);
        }}

        /* API状态指示器 */
        .api-status {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fff;
            border-radius: 8px;
            padding: 12px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 9999;
            font-size: 14px;
        }}

        .api-status.online {{
            border-left: 4px solid #49cc90;
        }}

        .api-status.offline {{
            border-left: 4px solid #f93e3e;
        }}

        .status-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }}

        .status-dot.online {{
            background: #49cc90;
        }}

        .status-dot.offline {{
            background: #f93e3e;
        }}

        /* 快速操作面板 */
        .quick-actions {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #fff;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 9999;
        }}

        .quick-actions h4 {{
            margin: 0 0 12px 0;
            font-size: 14px;
            color: #3b4151;
        }}

        .quick-actions button {{
            display: block;
            width: 100%;
            margin: 4px 0;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #fff;
            cursor: pointer;
            font-size: 12px;
        }}

        .quick-actions button:hover {{
            background: #f7f7f7;
        }}

        /* 加载动画 */
        .loading-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        }}

        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #49cc90;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        /* 代码高亮 */
        .swagger-ui .highlight-code {{
            background: #f6f8fa;
            border: 1px solid #d1d5da;
            border-radius: 4px;
            padding: 12px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 12px;
            line-height: 1.45;
        }}

        /* 响应式设计 */
        @media (max-width: 768px) {{
            .api-status, .quick-actions {{
                position: relative;
                top: auto;
                right: auto;
                bottom: auto;
                margin: 20px;
            }}
        }}
    </style>
</head>
<body>
    <!-- API状态指示器 -->
    <div id="api-status" class="api-status offline">
        <span class="status-dot offline"></span>
        <span id="status-text">检查API状态中...</span>
    </div>

    <!-- 快速操作面板 -->
    <div class="quick-actions">
        <h4>快速操作</h4>
        <button onclick="testHealthCheck()">测试健康检查</button>
        <button onclick="testAuth()">测试认证</button>
        <button onclick="getApiInfo()">获取API信息</button>
        <button onclick="exportOpenAPI()">导出OpenAPI</button>
        <button onclick="clearLocalStorage()">清除缓存</button>
    </div>

    <!-- 加载动画 -->
    <div id="loading" class="loading-overlay">
        <div class="loading-spinner"></div>
    </div>

    <div id="swagger-ui"></div>

    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js"></script>

    <script>
        // 工具函数
        function generateUUID() {{
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
                const r = Math.random() * 16 | 0;
                const v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            }});
        }}

        function showLoading(show = true) {{
            document.getElementById('loading').style.display = show ? 'flex' : 'none';
        }}

        function updateApiStatus(online, message = '') {{
            const statusEl = document.getElementById('api-status');
            const statusText = document.getElementById('status-text');
            const dot = statusEl.querySelector('.status-dot');

            if (online) {{
                statusEl.className = 'api-status online';
                dot.className = 'status-dot online';
                statusText.textContent = message || 'API在线';
            }} else {{
                statusEl.className = 'api-status offline';
                dot.className = 'status-dot offline';
                statusText.textContent = message || 'API离线';
            }}
        }}

        // API状态检查
        async function checkApiStatus() {{
            try {{
                const response = await fetch('/health');
                if (response.ok) {{
                    const data = await response.json();
                    updateApiStatus(true, 'API在线 - ' + (data.status || '正常'));
                }} else {{
                    updateApiStatus(false, 'API异常 - HTTP ' + response.status);
                }}
            }} catch (error) {{
                updateApiStatus(false, 'API离线 - ' + error.message);
            }}
        }}

        // 快速操作函数
        async function testHealthCheck() {{
            showLoading(true);
            try {{
                const response = await fetch('/health');
                const data = await response.json();
                alert('健康检查结果:\\n' + JSON.stringify(data, null, 2));
            }} catch (error) {{
                alert('健康检查失败: ' + error.message);
            }} finally {{
                showLoading(false);
            }}
        }}

        async function testAuth() {{
            const token = prompt('请输入JWT Token:');
            if (!token) return;

            showLoading(true);
            try {{
                const response = await fetch('/user/profile', {{
                    headers: {{
                        'Authorization': 'Bearer ' + token
                    }}
                }});
                const data = await response.json();
                alert('认证测试结果:\\n' + JSON.stringify(data, null, 2));
            }} catch (error) {{
                alert('认证测试失败: ' + error.message);
            }} finally {{
                showLoading(false);
            }}
        }}

        async function getApiInfo() {{
            showLoading(true);
            try {{
                const response = await fetch('/api/info');
                const data = await response.json();
                alert('API信息:\\n' + JSON.stringify(data, null, 2));
            }} catch (error) {{
                alert('获取API信息失败: ' + error.message);
            }} finally {{
                showLoading(false);
            }}
        }}

        function exportOpenAPI() {{
            fetch('{openapi_url}')
                .then(response => response.json())
                .then(data => {{
                    const blob = new Blob([JSON.stringify(data, null, 2)], {{
                        typing.Type: 'application/json'
                    }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'openapi.json';
                    a.click();
                    URL.revokeObjectURL(url);
                }})
                .catch(error => {{
                    alert('导出失败: ' + error.message);
                }});
        }}

        function clearLocalStorage() {{
            if (confirm('确定要清除所有本地缓存吗？')) {{
                localStorage.clear();
                sessionStorage.clear();
                location.reload();
            }}
        }}

        // 初始化Swagger UI
        window.onload = function() {{
            // 检查API状态
            checkApiStatus();

            // 定期检查API状态
            setInterval(checkApiStatus, 30000); // 每30秒检查一次

            const ui = SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 2,
                defaultModelExpandDepth: 2,
                displayRequestDuration: true,
                docExpansion: "list",
                operationsSorter: "alpha",
                filter: true,
                tryItOutEnabled: true,
                requestInterceptor: function(request) {{
                    request.headers['X-Request-ID'] = generateUUID();
                    request.headers['X-Client-Version'] = '1.0.0';
                    return request;
                }},
                responseInterceptor: function(response) {{
                    console.log('API Response:', response);
                    return response;
                }},
                onComplete: function() {{
                    showLoading(false);
                    console.log('Swagger UI 加载完成');
                }},
                onError: function(error) {{
                    showLoading(false);
                    console.error('Swagger UI 错误:', error);
                    updateApiStatus(false, 'Swagger UI 加载失败');
                }}
            }});

            // 添加自定义样式和交互
            setTimeout(() => {{
                // 为所有Try it out按钮添加确认
                document.querySelectorAll('.try-out__btn').forEach(btn => {{
                    btn.addEventListener('click', function(e) {{
                        if (this.innerText === 'Try it out') {{
                            if (!confirm('确定要执行这个API调用吗？这可能会修改服务器数据。')) {{
                                e.preventDefault();
                            }}
                        }}
                    }});
                }});
            }}, 1000);
        }};
    </script>
</body>
</html>
        """
        return custom_html

    @staticmethod
    def setup_custom_swagger_ui(app: FastAPI) -> None:
        """设置自定义Swagger UI."""

        def swagger_ui_html(req):
            """自定义Swagger UI页面处理器."""
            return SwaggerUIConfig.get_custom_swagger_ui_html(
                openapi_url=app.openapi_url,
                title=f"{app.title} - Swagger UI",
                oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
                init_oauth=app.swagger_ui_init_oauth,
                swagger_ui_parameters={
                    "deepLinking": True,
                    "displayRequestDuration": True,
                    "docExpansion": "none",
                    "operationsSorter": "alpha",
                    "filter": True,
                    "showExtensions": True,
                    "showCommonExtensions": True,
                    "tryItOutEnabled": True,
                },
            )

        # 覆盖默认的docs端点
        app.docs_url = None  # 禁用默认docs
        app.redoc_url = None  # 禁用redoc

        # 添加自定义docs端点
        @app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            return swagger_ui_html

        @app.get("/docs/oauth2-redirect", include_in_schema=False)
        async def swagger_ui_redirect():
            return get_swagger_ui_html(
                openapi_url=app.openapi_url,
                title=f"{app.title} - Swagger UI",
                oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
                init_oauth=app.swagger_ui_init_oauth,
            )

    @staticmethod
    def get_enhanced_redoc_html(
        *,
        openapi_url: str,
        title: str,
        redoc_js_url: str = "https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
    ) -> str:
        """获取增强的ReDoc HTML页面."""
        redoc_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title} - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}

        .redoc-wrap {{
            background: #fff;
        }}

        /* 自定义ReDoc样式 */
        .api-info {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
        }}

        .api-info h1 {{
            color: white !important;
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }}

        .api-info p {{
            color: rgba(255,255,255,0.9);
            font-size: 1.1rem;
            line-height: 1.6;
        }}

        /* 状态指示器 */
        .api-status-banner {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #49cc90;
            color: white;
            padding: 8px 16px;
            text-align: center;
            font-size: 14px;
            z-index: 10000;
        }}

        .api-status-banner.error {{
            background: #f93e3e;
        }}

        /* 响应式优化 */
        @media (max-width: 768px) {{
            .api-info {{
                padding: 20px;
            }}

            .api-info h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div id="api-status-banner" class="api-status-banner">
        <span id="banner-status-text">正在连接API...</span>
    </div>

    <redoc spec-url="{openapi_url}"></redoc>
    <script src="{redoc_js_url}"></script>

    <script>
        // API状态检查
        async function checkApiStatus() {{
            try {{
                const response = await fetch('/health');
                if (response.ok) {{
                    const data = await response.json();
                    updateStatusBanner('API在线 - ' + (data.status || '正常'), false);
                }} else {{
                    updateStatusBanner('API异常 - HTTP ' + response.status, true);
                }}
            }} catch (error) {{
                updateStatusBanner('API离线 - ' + error.message, true);
            }}
        }}

        function updateStatusBanner(message, isError = false) {{
            const banner = document.getElementById('api-status-banner');
            const text = document.getElementById('banner-status-text');

            text.textContent = message;
            if (isError) {{
                banner.className = 'api-status-banner error';
            }} else {{
                banner.className = 'api-status-banner';
            }}
        }}

        // 页面加载完成后检查API状态
        window.addEventListener('load', function() {{
            checkApiStatus();
            // 定期检查状态
            setInterval(checkApiStatus, 30000);
        }});

        // ReDoc配置
        window.addEventListener('redoc-initialized', function() {{
            console.log('ReDoc 初始化完成');
        }});
    </script>
</body>
</html>
        """

        return redoc_html

    @staticmethod
    def setup_enhanced_redoc(app: FastAPI) -> None:
        """设置增强的ReDoc."""

        @app.get("/redoc", include_in_schema=False)
        async def custom_redoc_html():
            return SwaggerUIConfig.get_enhanced_redoc_html(
                openapi_url=app.openapi_url, title=f"{app.title} - ReDoc"
            )


def setup_enhanced_docs(app: FastAPI) -> None:
    """设置增强的API文档."""
    swagger_config = SwaggerUIConfig()

    # 设置自定义Swagger UI
    swagger_config.setup_custom_swagger_ui(app)

    # 设置增强ReDoc
    swagger_config.setup_enhanced_redoc(app)
