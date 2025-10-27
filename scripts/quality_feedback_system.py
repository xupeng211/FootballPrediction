#!/usr/bin/env python3
"""
快速质量反馈系统
Fast Quality Feedback System

基于Issue #98方法论，提供实时的代码质量反馈和监控
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
from flask import Flask, render_template_string, jsonify, request
import subprocess

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class QualityMetric:
    """质量指标数据类"""
    name: str
    value: float
    unit: str
    status: str  # good, warning, critical
    timestamp: datetime
    trend: str  # improving, stable, declining


@dataclass
class FeedbackEvent:
    """反馈事件数据类"""
    event_type: str
    message: str
    severity: str
    timestamp: datetime
    details: Dict[str, Any]


class QualityFeedbackSystem:
    """快速质量反馈系统 - 基于Issue #98方法论"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.feedback_data = {
            "metrics": {},
            "events": [],
            "status": "unknown",
            "last_update": None,
            "issue_98_methodology_applied": True
        }

        # 质量阈值
        self.quality_thresholds = {
            "test_coverage": 15.0,
            "code_quality_score": 6.0,
            "critical_issues": 0,
            "high_issues": 5,
            "complexity_average": 8.0
        }

        # 初始化Flask应用
        self.app = Flask(__name__)
        self._setup_routes()

        # 后台监控线程
        self.monitoring_active = False
        self.monitor_thread = None

    def _setup_routes(self):
        """设置Web路由"""

        @self.app.route('/')
        def dashboard():
            """主仪表板"""
            return render_template_string(self._get_dashboard_template())

        @self.app.route('/api/metrics')
        def get_metrics():
            """获取质量指标API"""
            return jsonify(self.feedback_data)

        @self.app.route('/api/status')
        def get_status():
            """获取状态API"""
            return jsonify({
                "status": self.feedback_data["status"],
                "last_update": self.feedback_data["last_update"],
                "metrics_count": len(self.feedback_data["metrics"]),
                "events_count": len(self.feedback_data["events"])
            })

        @self.app.route('/api/refresh', methods=['POST'])
        def refresh_metrics():
            """刷新指标API"""
            try:
                self.update_quality_metrics()
                return jsonify({"success": True, "message": "指标已更新"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/trigger-check', methods=['POST'])
        def trigger_check():
            """触发质量检查API"""
            try:
                result = self.run_quality_check()
                return jsonify({"success": True, "result": result})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    def start_monitoring(self, interval: int = 30):
        """启动后台监控"""
        if self.monitoring_active:
            logger.info("监控已在运行中")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"启动质量监控，间隔: {interval}秒")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("质量监控已停止")

    def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.monitoring_active:
            try:
                self.update_quality_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(interval)

    def update_quality_metrics(self):
        """更新质量指标"""
        logger.info("🔄 更新质量指标...")

        try:
            # 收集各种质量指标
            metrics = {}

            # 1. 测试覆盖率
            coverage = self._get_test_coverage()
            if coverage is not None:
                metrics["test_coverage"] = QualityMetric(
                    name="测试覆盖率",
                    value=coverage,
                    unit="%",
                    status="good" if coverage >= 15 else "warning" if coverage >= 10 else "critical",
                    timestamp=datetime.now(),
                    trend="stable"  # 简化版，实际应该计算趋势
                )

            # 2. 代码质量评分
            quality_score = self._get_code_quality_score()
            if quality_score is not None:
                metrics["code_quality_score"] = QualityMetric(
                    name="代码质量评分",
                    value=quality_score,
                    unit="分",
                    status="good" if quality_score >= 8 else "warning" if quality_score >= 6 else "critical",
                    timestamp=datetime.now(),
                    trend="stable"
                )

            # 3. 问题统计
            issues_stats = self._get_issues_statistics()
            if issues_stats:
                for severity, count in issues_stats.items():
                    metrics[f"issues_{severity}"] = QualityMetric(
                        name=f"{severity.upper()}问题数",
                        value=count,
                        unit="个",
                        status="good" if count == 0 else "warning" if count < 5 else "critical",
                        timestamp=datetime.now(),
                        trend="stable"
                    )

            # 4. 代码复杂度
            complexity = self._get_complexity_metrics()
            if complexity:
                metrics["complexity_average"] = QualityMetric(
                    name="平均复杂度",
                    value=complexity,
                    unit="",
                    status="good" if complexity <= 5 else "warning" if complexity <= 8 else "critical",
                    timestamp=datetime.now(),
                    trend="stable"
                )

            # 更新反馈数据
            self.feedback_data["metrics"] = {
                name: asdict(metric) for name, metric in metrics.items()
            }
            self.feedback_data["metrics"][k]["timestamp"] = v["timestamp"].isoformat()

            self.feedback_data["last_update"] = datetime.now().isoformat()

            # 评估整体状态
            self.feedback_data["status"] = self._evaluate_overall_status(metrics)

            logger.info("✅ 质量指标更新完成")

        except Exception as e:
            logger.error(f"更新质量指标失败: {e}")

    def _get_test_coverage(self) -> Optional[float]:
        """获取测试覆盖率"""
        try:
            # 尝试读取覆盖率报告
            coverage_file = self.project_root / "htmlcov" / "index.html"
            if coverage_file.exists():
                with open(coverage_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                import re
                match = re.search(r'([0-9]*\.[0-9]%)', content)
                if match:
                    return float(match.group(1).rstrip('%'))

            # 运行快速覆盖率检查
            result = subprocess.run([
                "python", "-m", "pytest", "tests/unit/utils/",
                "--cov=src/utils", "--cov-report=json",
                "-q"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)

            if result.returncode == 0:
                coverage_file = self.project_root / "htmlcov" / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        data = json.load(f)
                        return data.get("totals", {}).get("percent_covered", 0)

        except Exception as e:
            logger.error(f"获取测试覆盖率失败: {e}")

        return None

    def _get_code_quality_score(self) -> Optional[float]:
        """获取代码质量评分"""
        try:
            # 尝试读取代码审查报告
            review_file = self.project_root / "automated_code_review_report.json"
            if review_file.exists():
                with open(review_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("quality_score", 0)

            # 尝试读取质量修复报告
            fix_file = self.project_root / "enhanced_smart_quality_fix_report.json"
            if fix_file.exists():
                with open(fix_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("quality_score", 0)

        except Exception as e:
            logger.error(f"获取代码质量评分失败: {e}")

        return None

    def _get_issues_statistics(self) -> Optional[Dict[str, int]]:
        """获取问题统计"""
        try:
            review_file = self.project_root / "automated_code_review_report.json"
            if review_file.exists():
                with open(review_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("summary", {}).get("by_severity", {})

        except Exception as e:
            logger.error(f"获取问题统计失败: {e}")

        return None

    def _get_complexity_metrics(self) -> Optional[float]:
        """获取复杂度指标"""
        try:
            review_file = self.project_root / "automated_code_review_report.json"
            if review_file.exists():
                with open(review_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("metrics", {}).get("average_complexity", 0)

        except Exception as e:
            logger.error(f"获取复杂度指标失败: {e}")

        return None

    def _evaluate_overall_status(self, metrics: Dict[str, QualityMetric]) -> str:
        """评估整体状态"""
        if not metrics:
            return "unknown"

        critical_count = sum(1 for m in metrics.values() if m.status == "critical")
        warning_count = sum(1 for m in metrics.values() if m.status == "warning")

        if critical_count > 0:
            return "critical"
        elif warning_count > 2:
            return "warning"
        elif warning_count > 0:
            return "attention"
        else:
            return "good"

    def run_quality_check(self) -> Dict[str, Any]:
        """运行质量检查"""
        logger.info("🔍 运行质量检查...")

        try:
            # 运行质量守护工具
            result = subprocess.run([
                sys.executable, "scripts/quality_guardian.py", "--check-only"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=300)

            # 添加事件记录
            event = FeedbackEvent(
                event_type="quality_check",
                message="质量检查完成",
                severity="info" if result.returncode == 0 else "warning",
                timestamp=datetime.now(),
                details={
                    "returncode": result.returncode,
                    "stdout": result.stdout[:500],  # 限制输出长度
                    "stderr": result.stderr[:500]
                }
            )

            self.feedback_data["events"].append(asdict(event))
            self.feedback_data["events"][-1]["timestamp"] = event.timestamp.isoformat()

            # 保持最近的事件
            if len(self.feedback_data["events"]) > 100:
                self.feedback_data["events"] = self.feedback_data["events"][-50:]

            return {
                "success": result.returncode == 0,
                "message": "质量检查完成" if result.returncode == 0 else "发现问题需要修复",
                "output": result.stdout[:1000]
            }

        except subprocess.TimeoutExpired:
            event = FeedbackEvent(
                event_type="quality_check",
                message="质量检查超时",
                severity="error",
                timestamp=datetime.now(),
                details={"error": "timeout"}
            )
            self.feedback_data["events"].append(asdict(event))
            self.feedback_data["events"][-1]["timestamp"] = event.timestamp.isoformat()

            return {"success": False, "message": "质量检查超时"}

        except Exception as e:
            event = FeedbackEvent(
                event_type="quality_check",
                message=f"质量检查失败: {e}",
                severity="error",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )
            self.feedback_data["events"].append(asdict(event))
            self.feedback_data["events"][-1]["timestamp"] = event.timestamp.isoformat()

            return {"success": False, "message": f"质量检查失败: {e}"}

    def add_feedback_event(self, event_type: str, message: str, severity: str = "info", details: Dict = None):
        """添加反馈事件"""
        event = FeedbackEvent(
            event_type=event_type,
            message=message,
            severity=severity,
            timestamp=datetime.now(),
            details=details or {}
        )

        self.feedback_data["events"].append(asdict(event))
        self.feedback_data["events"][-1]["timestamp"] = event.timestamp.isoformat()

        # 保持最近的事件
        if len(self.feedback_data["events"]) > 100:
            self.feedback_data["events"] = self.feedback_data["events"][-50:]

    def _get_dashboard_template(self) -> str:
        """获取仪表板HTML模板"""
        return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>质量反馈系统 - Issue #98方法论</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .status-indicator { padding: 10px 20px; border-radius: 20px; color: white; font-weight: bold; }
        .status-good { background-color: #28a745; }
        .status-warning { background-color: #ffc107; color: black; }
        .status-critical { background-color: #dc3545; }
        .status-unknown { background-color: #6c757d; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-name { font-size: 14px; color: #666; margin-bottom: 5px; }
        .metric-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .metric-status { padding: 4px 8px; border-radius: 12px; font-size: 12px; color: white; }
        .events-section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .event-item { padding: 10px; border-bottom: 1px solid #eee; }
        .event-time { font-size: 12px; color: #666; }
        .event-message { margin: 5px 0; }
        .actions { text-align: center; margin: 20px 0; }
        .btn { padding: 10px 20px; margin: 0 10px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background-color: #007bff; color: white; }
        .btn-success { background-color: #28a745; color: white; }
        .last-update { text-align: center; color: #666; font-size: 14px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 快速质量反馈系统</h1>
            <p>基于Issue #98智能质量修复方法论</p>
            <div id="status-indicator" class="status-indicator status-unknown">检查中...</div>
        </div>

        <div class="metrics-grid" id="metrics-grid">
            <!-- 指标卡片将通过JavaScript动态生成 -->
        </div>

        <div class="actions">
            <button class="btn btn-primary" onclick="refreshMetrics()">🔄 刷新指标</button>
            <button class="btn btn-success" onclick="triggerCheck()">🔍 运行检查</button>
        </div>

        <div class="events-section">
            <h3>📋 最近事件</h3>
            <div id="events-list">
                <!-- 事件列表将通过JavaScript动态生成 -->
            </div>
        </div>

        <div class="last-update" id="last-update">
            最后更新: --
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                updateStatus(data.status);
                updateMetrics(data.metrics || {});
                updateEvents(data.events || []);
                updateLastUpdate(data.last_update);

            } catch (error) {
                console.error('加载数据失败:', error);
            }
        }

        function updateStatus(status) {
            const indicator = document.getElementById('status-indicator');
            indicator.className = `status-indicator status-${status}`;

            const statusText = {
                'good': '✅ 状态良好',
                'warning': '⚠️ 需要注意',
                'attention': '👁️ 需要关注',
                'critical': '🚨 严重问题',
                'unknown': '❓ 状态未知'
            };

            indicator.textContent = statusText[status] || '未知状态';
        }

        function updateMetrics(metrics) {
            const grid = document.getElementById('metrics-grid');
            grid.innerHTML = '';

            Object.entries(metrics).forEach(([key, metric]) => {
                const card = document.createElement('div');
                card.className = 'metric-card';

                card.innerHTML = `
                    <div class="metric-name">${metric.name}</div>
                    <div class="metric-value">${metric.value}${metric.unit}</div>
                    <div class="metric-status status-${metric.severity}">${metric.severity}</div>
                `;

                grid.appendChild(card);
            });
        }

        function updateEvents(events) {
            const list = document.getElementById('events-list');
            list.innerHTML = '';

            events.slice(-10).reverse().forEach(event => {
                const item = document.createElement('div');
                item.className = 'event-item';

                const time = new Date(event.timestamp).toLocaleString();
                const severityEmoji = {
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'critical': '🚨'
                };

                item.innerHTML = `
                    <div class="event-time">${time}</div>
                    <div class="event-message">${severityEmoji[event.severity] || ''} ${event.message}</div>
                `;

                list.appendChild(item);
            });

            if (events.length === 0) {
                list.innerHTML = '<div class="event-item">暂无事件记录</div>';
            }
        }

        function updateLastUpdate(lastUpdate) {
            const element = document.getElementById('last-update');
            if (lastUpdate) {
                const time = new Date(lastUpdate).toLocaleString();
                element.textContent = `最后更新: ${time}`;
            } else {
                element.textContent = '最后更新: --';
            }
        }

        async function refreshMetrics() {
            try {
                const response = await fetch('/api/refresh', {method: 'POST'});
                const result = await response.json();

                if (result.success) {
                    loadData();
                } else {
                    alert('刷新失败: ' + result.error);
                }
            } catch (error) {
                alert('刷新失败: ' + error.message);
            }
        }

        async function triggerCheck() {
            try {
                const response = await fetch('/api/trigger-check', {method: 'POST'});
                const result = await response.json();

                if (result.success) {
                    alert('检查完成: ' + result.message);
                    loadData();
                } else {
                    alert('检查失败: ' + result.error);
                }
            } catch (error) {
                alert('检查失败: ' + error.message);
            }
        }

        // 初始加载数据
        loadData();

        // 每30秒自动刷新
        setInterval(loadData, 30000);
    </script>
</body>
</html>
        '''

    def run_server(self, host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
        """运行Web服务器"""
        logger.info(f"🌐 启动质量反馈Web服务: http://{host}:{port}")
        logger.info("📊 基于Issue #98方法论的实时质量监控系统")

        # 启动监控
        self.start_monitoring()

        try:
            self.app.run(host=host, port=port, debug=debug, use_reloader=False)
        finally:
            self.stop_monitoring()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="快速质量反馈系统")
    parser.add_argument("--host", default="127.0.0.1", help="服务器主机")
    parser.add_argument("--port", type=int, default=5000, help="服务器端口")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--monitor-interval", type=int, default=30, help="监控间隔(秒)")

    args = parser.parse_args()

    # 创建反馈系统
    feedback_system = QualityFeedbackSystem()

    # 添加启动事件
    feedback_system.add_feedback_event(
        "system_start",
        "质量反馈系统启动",
        "info",
        {"host": args.host, "port": args.port}
    )

    try:
        # 运行服务器
        feedback_system.run_server(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        logger.info("👋 用户中断，关闭质量反馈系统")
    except Exception as e:
        logger.error(f"系统运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()