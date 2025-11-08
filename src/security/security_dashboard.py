#!/usr/bin/env python3
"""
安全仪表板和可视化系统
提供实时安全监控界面、威胁可视化、报告生成等功能
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.core.logger import get_logger
from src.security.security_automation import get_automation_engine
from src.security.security_monitor import (
    ThreatLevel,
    get_security_monitor,
)

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/security", tags=["security"])


class SecurityDashboardRequest(BaseModel):
    """安全仪表板请求"""

    time_range: str = "24h"  # 1h, 24h, 7d, 30d
    filters: dict[str, Any] = {}


class SecurityMetricsResponse(BaseModel):
    """安全指标响应"""

    total_events: int
    events_by_type: dict[str, int]
    events_by_level: dict[str, int]
    blocked_ips: int
    auto_responses: int
    threat_trend: dict[str, int]


class ThreatIntelligenceResponse(BaseModel):
    """威胁情报响应"""

    top_attacker_ips: list[dict[str, Any]]
    attack_patterns: list[dict[str, Any]]
    geographic_threats: list[dict[str, Any]]
    emerging_threats: list[dict[str, Any]]


class SecurityDashboardData:
    """安全仪表板数据管理"""

    def __init__(self):
        self.monitor = get_security_monitor()
        self.automation_engine = get_automation_engine()
        self._cache = {}
        self._cache_expiry = {}

    async def get_dashboard_overview(self, time_range: str = "24h") -> dict[str, Any]:
        """获取仪表板概览数据"""
        cache_key = f"overview_{time_range}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # 计算时间范围
        end_time = datetime.now()
        start_time = self._get_start_time(time_range, end_time)

        # 获取安全监控数据
        dashboard_data = self.monitor.get_security_dashboard()

        # 获取自动化引擎数据
        automation_status = self.automation_engine.get_automation_status()

        # 计算趋势数据
        threat_trend = await self._calculate_threat_trend(start_time, end_time)

        # 生成威胁情报
        threat_intelligence = await self._generate_threat_intelligence(
            start_time, end_time
        )

        overview_data = {
            "timestamp": end_time.isoformat(),
            "time_range": time_range,
            "summary": dashboard_data["summary"],
            "threat_trend": threat_trend,
            "threat_intelligence": threat_intelligence,
            "automation_status": {
                "enabled_rules": automation_status["enabled_rules"],
                "total_rules": automation_status["total_rules"],
                "recent_executions": automation_status["executions_24h"],
                "success_rate": (
                    automation_status["successful_executions_24h"]
                    / max(1, automation_status["executions_24h"])
                    * 100
                ),
            },
            "system_health": await self._get_system_health(),
            "recommendations": await self._generate_recommendations(),
        }

        # 缓存数据
        self._cache[cache_key] = overview_data
        self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)

        return overview_data

    async def get_real_time_alerts(self) -> list[dict[str, Any]]:
        """获取实时安全告警"""
        # 获取最近1小时的高危事件
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        recent_events = [
            event
            for event in self.monitor.events
            if event.timestamp > one_hour_ago
            and event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        ]

        alerts = []
        for event in sorted(recent_events, key=lambda x: x.timestamp, reverse=True):
            alert = {
                "id": event.event_id,
                "type": event.event_type.value,
                "level": event.threat_level.value,
                "timestamp": event.timestamp.isoformat(),
                "source_ip": event.source_ip,
                "description": event.description,
                "location": event.geo_location,
                "resolved": event.is_resolved,
                "actions_taken": event.response_action or [],
            }

            # 添加严重程度标识
            if event.threat_level == ThreatLevel.CRITICAL:
                alert["severity"] = "critical"
                alert["priority"] = 1
            else:
                alert["severity"] = "high"
                alert["priority"] = 2

            alerts.append(alert)

        return alerts

    async def get_security_metrics(
        self, time_range: str = "24h"
    ) -> SecurityMetricsResponse:
        """获取详细安全指标"""
        start_time = self._get_start_time(time_range, datetime.now())

        # 过滤指定时间范围的事件
        filtered_events = [
            event for event in self.monitor.events if event.timestamp > start_time
        ]

        # 统计事件类型分布
        events_by_type = defaultdict(int)
        for event in filtered_events:
            events_by_type[event.event_type.value] += 1

        # 统计威胁等级分布
        events_by_level = defaultdict(int)
        for event in filtered_events:
            events_by_level[event.threat_level.value] += 1

        # 计算威胁趋势
        threat_trend = await self._calculate_threat_trend(start_time, datetime.now())

        return SecurityMetricsResponse(
            total_events=len(filtered_events),
            events_by_type=dict(events_by_type),
            events_by_level=dict(events_by_level),
            blocked_ips=len(self.monitor.blocked_ips),
            auto_responses=self.monitor.metrics.auto_responses,
            threat_trend=threat_trend,
        )

    async def get_threat_intelligence(self) -> ThreatIntelligenceResponse:
        """获取威胁情报"""
        now = datetime.now()
        start_time = now - timedelta(days=7)

        threat_intelligence = await self._generate_threat_intelligence(start_time, now)

        return ThreatIntelligenceResponse(
            top_attacker_ips=threat_intelligence["top_attacker_ips"],
            attack_patterns=threat_intelligence["attack_patterns"],
            geographic_threats=threat_intelligence["geographic_threats"],
            emerging_threats=threat_intelligence["emerging_threats"],
        )

    async def _calculate_threat_trend(
        self, start_time: datetime, end_time: datetime
    ) -> dict[str, int]:
        """计算威胁趋势"""
        # 按小时分组统计事件
        hourly_counts = defaultdict(int)
        current_time = start_time

        while current_time <= end_time:
            hour_key = current_time.strftime("%H")
            hourly_counts[hour_key] = 0
            current_time += timedelta(hours=1)

        # 统计每个小时的事件数
        for event in self.monitor.events:
            if start_time <= event.timestamp <= end_time:
                hour_key = event.timestamp.strftime("%H")
                hourly_counts[hour_key] += 1

        return dict(hourly_counts)

    async def _generate_threat_intelligence(
        self, start_time: datetime, end_time: datetime
    ) -> dict[str, Any]:
        """生成威胁情报"""
        # 过滤指定时间范围的事件
        filtered_events = [
            event
            for event in self.monitor.events
            if start_time <= event.timestamp <= end_time
        ]

        # 统计攻击者IP
        ip_counts = defaultdict(int)
        for event in filtered_events:
            ip_counts[event.source_ip] += 1

        top_attacker_ips = [
            {"ip": ip, "attack_count": count, "last_seen": None}
            for ip, count in sorted(
                ip_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # 分析攻击模式
        attack_patterns = []
        pattern_counts = defaultdict(int)
        for event in filtered_events:
            pattern_counts[event.event_type.value] += 1

        for pattern, count in sorted(
            pattern_counts.items(), key=lambda x: x[1], reverse=True
        ):
            attack_patterns.append(
                {
                    "pattern": pattern,
                    "count": count,
                    "percentage": (
                        (count / len(filtered_events) * 100) if filtered_events else 0
                    ),
                }
            )

        # 分析地理威胁
        geo_counts = defaultdict(int)
        for event in filtered_events:
            country = event.geo_location.get("country", "Unknown")
            geo_counts[country] += 1

        geographic_threats = [
            {
                "country": country,
                "attack_count": count,
                "percentage": (
                    (count / len(filtered_events) * 100) if filtered_events else 0
                ),
            }
            for country, count in sorted(
                geo_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # 识别新兴威胁
        recent_events = [
            event
            for event in filtered_events
            if event.timestamp > (end_time - timedelta(hours=24))
        ]

        emerging_threats = []
        if recent_events:
            recent_types = defaultdict(int)
            for event in recent_events:
                recent_types[event.event_type.value] += 1

            for threat_type, count in sorted(
                recent_types.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                emerging_threats.append(
                    {
                        "threat_type": threat_type,
                        "recent_count": count,
                        "trend": "increasing",
                    }
                )

        return {
            "top_attacker_ips": top_attacker_ips,
            "attack_patterns": attack_patterns,
            "geographic_threats": geographic_threats,
            "emerging_threats": emerging_threats,
        }

    async def _get_system_health(self) -> dict[str, Any]:
        """获取系统健康状态"""
        try:
            # 检查安全监控系统状态
            monitor_status = "healthy" if len(self.monitor.events) > 0 else "warning"

            # 检查自动化引擎状态
            automation_status = self.automation_engine.get_automation_status()
            engine_status = (
                "healthy" if automation_status["enabled_rules"] > 0 else "warning"
            )

            # 检查最近是否有严重威胁
            recent_critical = [
                event
                for event in self.monitor.events
                if (
                    event.timestamp > datetime.now() - timedelta(hours=1)
                    and event.threat_level == ThreatLevel.CRITICAL
                )
            ]

            threat_status = "critical" if recent_critical else "normal"

            # 综合健康评分
            health_score = 100
            if monitor_status != "healthy":
                health_score -= 20
            if engine_status != "healthy":
                health_score -= 20
            if threat_status == "critical":
                health_score -= 30

            health_level = (
                "excellent"
                if health_score >= 90
                else (
                    "good"
                    if health_score >= 70
                    else "warning" if health_score >= 50 else "critical"
                )
            )

            return {
                "overall_status": health_level,
                "health_score": health_score,
                "components": {
                    "security_monitor": monitor_status,
                    "automation_engine": engine_status,
                    "threat_detection": threat_status,
                },
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
            return {
                "overall_status": "error",
                "health_score": 0,
                "components": {},
                "last_check": datetime.now().isoformat(),
                "error": str(e),
            }

    async def _generate_recommendations(self) -> list[dict[str, Any]]:
        """生成安全建议"""
        recommendations = []
        now = datetime.now()
        last_24h = now - timedelta(hours=24)

        # 分析最近24小时的事件
        recent_events = [
            event for event in self.monitor.events if event.timestamp > last_24h
        ]

        # 高危事件数量
        high_risk_events = [
            event
            for event in recent_events
            if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        ]

        if len(high_risk_events) > 10:
            recommendations.append(
                {
                    "type": "critical",
                    "title": "高危事件过多",
                    "description": f"过去24小时发现 {len(high_risk_events)} 个高危安全事件",
                    "action": "建议立即检查安全配置并加强监控",
                }
            )

        # 阻止IP数量
        if len(self.monitor.blocked_ips) > 100:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "阻止IP数量过多",
                    "description": f"当前阻止了 {len(self.monitor.blocked_ips)} 个IP地址",
                    "action": "建议定期清理过期的IP阻止记录",
                }
            )

        # 自动化执行率
        automation_status = self.automation_engine.get_automation_status()
        if automation_status["executions_24h"] > 0:
            success_rate = (
                automation_status["successful_executions_24h"]
                / automation_status["executions_24h"]
            ) * 100

            if success_rate < 80:
                recommendations.append(
                    {
                        "type": "warning",
                        "title": "自动化响应成功率低",
                        "description": f"自动化响应成功率仅为 {success_rate:.1f}%",
                        "action": "建议检查响应规则配置和执行环境",
                    }
                )

        # 事件类型分析
        event_types = defaultdict(int)
        for event in recent_events:
            event_types[event.event_type.value] += 1

        # 找出最常见的攻击类型
        if event_types:
            most_common = max(event_types.items(), key=lambda x: x[1])
            if most_common[1] > 5:
                recommendations.append(
                    {
                        "type": "info",
                        "title": f"常见攻击类型: {most_common[0]}",
                        "description": f"检测到 {most_common[1]} 次 {most_common[0]} 攻击",
                        "action": "建议针对该攻击类型加强防护措施",
                    }
                )

        if not recommendations:
            recommendations.append(
                {
                    "type": "success",
                    "title": "安全状态良好",
                    "description": "系统运行正常，未发现明显的安全问题",
                    "action": "继续保持当前的安全配置和监控策略",
                }
            )

        return recommendations

    def _get_start_time(self, time_range: str, end_time: datetime) -> datetime:
        """获取开始时间"""
        time_ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        return end_time - time_ranges.get(time_range, timedelta(hours=24))

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False

        if cache_key not in self._cache_expiry:
            return False

        return datetime.now() < self._cache_expiry[cache_key]


# 全局仪表板数据实例
_global_dashboard: SecurityDashboardData | None = None


def get_security_dashboard() -> SecurityDashboardData:
    """获取全局安全仪表板实例"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = SecurityDashboardData()
    return _global_dashboard


# API路由定义
@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_html():
    """获取安全仪表板HTML页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>安全监控仪表板</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .dashboard { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2em; font-weight: bold; margin-bottom: 10px; }
            .metric-label { color: #666; }
            .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .alert { background: #ff6b6b; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .alert.warning { background: #feca57; }
            .alert.success { background: #48dbfb; }
            .loading { text-align: center; padding: 50px; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <h1>🔒 安全监控仪表板</h1>
                <p>实时安全监控和威胁检测系统</p>
            </div>

            <div id="loading" class="loading">
                <p>正在加载安全数据...</p>
            </div>

            <div id="content" style="display: none;">
                <div class="metrics-grid" id="metrics-grid">
                    <!-- 指标卡片将通过JavaScript动态生成 -->
                </div>

                <div class="chart-container">
                    <h3>威胁趋势</h3>
                    <canvas id="threat-chart"></canvas>
                </div>

                <div class="chart-container">
                    <h3>实时告警</h3>
                    <div id="alerts-container">
                        <!-- 实时告警将通过JavaScript动态生成 -->
                    </div>
                </div>
            </div>
        </div>

        <script>
            // 页面加载完成后获取数据
            document.addEventListener('DOMContentLoaded', function() {
                loadDashboardData();
                setInterval(loadDashboardData, 30000); // 每30秒刷新一次
            });

            async function loadDashboardData() {
                try {
                    const response = await fetch('/security/api/overview');
                    const data = await response.json();

                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('content').style.display = 'block';

                    updateMetrics(data);
                    updateChart(data.threat_trend);
                    updateAlerts(data.recent_alerts || []);

                } catch (error) {
                    console.error('加载仪表板数据失败:', error);
                    document.getElementById('loading').innerHTML = '<p class="alert">加载数据失败，请刷新页面重试</p>';
                }
            }

            function updateMetrics(data) {
                const metricsGrid = document.getElementById('metrics-grid');
                const summary = data.summary;

                metricsGrid.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-value">${summary.total_events_24h}</div>
                        <div class="metric-label">24小时事件总数</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${summary.blocked_ips}</div>
                        <div class="metric-label">阻止IP数量</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${summary.auto_responses}</div>
                        <div class="metric-label">自动响应次数</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${summary.critical_threats}</div>
                        <div class="metric-label">严重威胁</div>
                    </div>
                `;
            }

            function updateChart(trendData) {
                // 这里应该使用实际的图表库（如Chart.js）
                const canvas = document.getElementById('threat-chart');
                const ctx = canvas.getContext('2d');

                // 简单的文本显示
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '16px Arial';
                ctx.fillText('威胁趋势图（需要Chart.js库）', 20, 50);
                ctx.fillText('数据点: ' + Object.keys(trendData).length, 20, 80);
            }

            function updateAlerts(alerts) {
                const container = document.getElementById('alerts-container');

                if (alerts.length === 0) {
                    container.innerHTML = '<p class="alert success">暂无活跃的安全告警</p>';
                    return;
                }

                container.innerHTML = alerts.map(alert => `
                    <div class="alert ${alert.severity === 'critical' ? '' : 'warning'}">
                        <strong>${alert.type}</strong> - ${alert.description}
                        <br><small>来源: ${alert.source_ip} | 时间: ${new Date(alert.timestamp).toLocaleString()}</small>
                    </div>
                `).join('');
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/api/overview")
async def get_overview_api(time_range: str = "24h"):
    """获取仪表板概览API"""
    try:
        dashboard = get_security_dashboard()
        overview_data = await dashboard.get_dashboard_overview(time_range)
        return overview_data
    except Exception as e:
        logger.error(f"获取仪表板概览失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全数据失败")


@router.get("/api/alerts")
async def get_alerts_api():
    """获取实时告警API"""
    try:
        dashboard = get_security_dashboard()
        alerts = await dashboard.get_real_time_alerts()
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"获取实时告警失败: {e}")
        raise HTTPException(status_code=500, detail="获取告警数据失败")


@router.get("/api/metrics")
async def get_metrics_api(time_range: str = "24h"):
    """获取安全指标API"""
    try:
        dashboard = get_security_dashboard()
        metrics = await dashboard.get_security_metrics(time_range)
        return metrics.dict()
    except Exception as e:
        logger.error(f"获取安全指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取指标数据失败")


@router.get("/api/threat-intelligence")
async def get_threat_intelligence_api():
    """获取威胁情报API"""
    try:
        dashboard = get_security_dashboard()
        intelligence = await dashboard.get_threat_intelligence()
        return intelligence.dict()
    except Exception as e:
        logger.error(f"获取威胁情报失败: {e}")
        raise HTTPException(status_code=500, detail="获取威胁情报失败")


@router.get("/api/system-health")
async def get_system_health_api():
    """获取系统健康状态API"""
    try:
        dashboard = get_security_dashboard()
        health = await dashboard._get_system_health()
        return health
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取健康状态失败")


@router.get("/api/recommendations")
async def get_recommendations_api():
    """获取安全建议API"""
    try:
        dashboard = get_security_dashboard()
        recommendations = await dashboard._generate_recommendations()
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"获取安全建议失败: {e}")
        raise HTTPException(status_code=500, detail="获取建议失败")


if __name__ == "__main__":
    import uvicorn

    # 创建FastAPI应用
    from fastapi import FastAPI

    app = FastAPI(title="Security Dashboard API", version="1.0.0")
    app.include_router(router)

    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8001)
