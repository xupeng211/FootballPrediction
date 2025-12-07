"""
Football Prediction Evaluation Report Builder

足球预测评估报告构建器，生成详细的HTML和PDF评估报告。
整合所有评估结果，提供专业级的分析报告。

Author: Football Prediction Team
Version: 1.0.0
"""

import json
import os
import numpy as np
import pandas as pd
from typing import Optional, Union, Any
from pathlib import Path
from datetime import datetime
import logging
from dataclasses import asdict

try:
    from jinja2 import Environment, FileSystemLoader, Template

    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    logging.warning("jinja2 not available - HTML reports will be disabled")

try:
    import weasyprint

    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False
    logging.warning("weasyprint not available - PDF reports will be disabled")

logger = logging.getLogger(__name__)


class ReportBuilder:
    """评估报告构建器"""

    def __init__(self, output_dir: Union[str, Path] = None):
        """
        初始化报告构建器

        Args:
            output_dir: 输出目录
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(f"artifacts/eval/reports_{timestamp}")
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 创建模板
        self.template_env = self._create_template_environment()

    def _create_template_environment(self) -> Environment:
        """创建Jinja2模板环境"""
        if not HAS_JINJA2:
            return None

        # 使用内置模板
        template_str = self._get_html_template()
        template = Template(template_str)

        # 创建安全的环境（启用自动转义）
        env = Environment(autoescape=True)
        env.globals["template"] = template

        return env

    def _get_html_template(self) -> str:
        """获取HTML模板字符串"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
        }
        .header p {
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }
        .section {
            background: white;
            margin-bottom: 2rem;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
            margin-top: 0;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .metric-card h3 {
            margin: 0 0 0.5rem 0;
            color: #333;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        .metric-unit {
            font-size: 0.9rem;
            color: #666;
        }
        .good { color: #28a745; }
        .warning { color: #ffc107; }
        .danger { color: #dc3545; }
        .table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        .table th, .table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        .table th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        .badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-success { background-color: #28a745; color: white; }
        .badge-warning { background-color: #ffc107; color: #212529; }
        .badge-danger { background-color: #dc3545; color: white; }
        .progress {
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        .chart-placeholder {
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            color: #6c757d;
            margin: 1rem 0;
        }
        .footer {
            text-align: center;
            padding: 2rem;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
            margin-top: 3rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚽ {{ title }}</h1>
        <p>生成时间: {{ generation_time }} | 模型版本: {{ model_version }}</p>
    </div>

    {% if summary %}
    <div class="section">
        <h2>📊 执行摘要</h2>
        <div class="metrics-grid">
            {% for metric in summary %}
            <div class="metric-card">
                <h3>{{ metric.name }}</h3>
                <div class="metric-value {{ metric.class }}">
                    {{ metric.value }}<span class="metric-unit">{{ metric.unit }}</span>
                </div>
                {% if metric.description %}
                <p><small>{{ metric.description }}</small></p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    {% if metrics %}
    <div class="section">
        <h2>🎯 分类指标</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>指标</th>
                    <th>数值</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
                {% for key, value in metrics.items() %}
                <tr>
                    <td>{{ metric_names[key] or key }}</td>
                    <td>{{ "%.4f"|format(value) if value is number else value }}</td>
                    <td>
                        {% if key in ['accuracy', 'f1_weighted', 'precision_weighted', 'recall_weighted'] %}
                            {% if value >= 0.8 %}
                                <span class="badge badge-success">优秀</span>
                            {% elif value >= 0.6 %}
                                <span class="badge badge-warning">良好</span>
                            {% else %}
                                <span class="badge badge-danger">需改进</span>
                            {% endif %}
                        {% elif key in ['logloss', 'brier_score_avg'] %}
                            {% if value <= 0.3 %}
                                <span class="badge badge-success">优秀</span>
                            {% elif value <= 0.5 %}
                                <span class="badge badge-warning">良好</span>
                            {% else %}
                                <span class="badge badge-danger">需改进</span>
                            {% endif %}
                        {% else %}
                            <span class="badge badge-warning">标准</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if calibration_metrics %}
    <div class="section">
        <h2>🎛️ 概率校准指标</h2>
        <table class="table">
            <thead>
                <tr>
                    <th>类别</th>
                    <th>Brier分数</th>
                    <th>ECE</th>
                    <th>MCE</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
                {% for class_name in ['H', 'D', 'A'] %}
                <tr>
                    <td>{{ class_names[class_name] }}</td>
                    <td>{{ "%.4f"|format(calibration_metrics['brier_score_' + class_name]) }}</td>
                    <td>{{ "%.4f"|format(calibration_metrics['ece_' + class_name]) }}</td>
                    <td>{{ "%.4f"|format(calibration_metrics['mce_' + class_name]) }}</td>
                    <td>
                        {% set brier = calibration_metrics['brier_score_' + class_name] %}
                        {% if brier <= 0.15 %}
                            <span class="badge badge-success">校准良好</span>
                        {% elif brier <= 0.25 %}
                            <span class="badge badge-warning">校准一般</span>
                        {% else %}
                            <span class="badge badge-danger">需校准</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if backtest_result %}
    <div class="section">
        <h2>💰 回测分析</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>投资回报率 (ROI)</h3>
                <div class="metric-value {{ 'good' if backtest_result.roi > 0 else 'danger' }}">
                    {{ "%.2f"|format(backtest_result.roi) }}<span class="metric-unit">%</span>
                </div>
            </div>
            <div class="metric-card">
                <h3>胜率</h3>
                <div class="metric-value">
                    {{ "%.2f"|format(backtest_result.win_rate) }}<span class="metric-unit">%</span>
                </div>
            </div>
            <div class="metric-card">
                <h3>总投注次数</h3>
                <div class="metric-value">
                    {{ backtest_result.total_bets }}<span class="metric-unit">次</span>
                </div>
            </div>
            <div class="metric-card">
                <h3>最大回撤</h3>
                <div class="metric-value {{ 'warning' if backtest_result.max_drawdown_percentage > 10 else 'good' }}">
                    {{ "%.2f"|format(backtest_result.max_drawdown_percentage) }}<span class="metric-unit">%</span>
                </div>
            </div>
        </div>

        <h3>回测详情</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>指标</th>
                    <th>数值</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>初始资金</td><td>¥{{ "%.2f"|format(backtest_result.initial_bankroll) }}</td></tr>
                <tr><td>最终资金</td><td>¥{{ "%.2f"|format(backtest_result.final_bankroll) }}</td></tr>
                <tr><td>净收益</td><td>¥{{ "%.2f"|format(backtest_result.net_profit) }}</td></tr>
                <tr><td>总投注金额</td><td>¥{{ "%.2f"|format(backtest_result.total_stake) }}</td></tr>
                <tr><td>获胜次数</td><td>{{ backtest_result.winning_bets }}</td></tr>
                <tr><td>失败次数</td><td>{{ backtest_result.losing_bets }}</td></tr>
                <tr><td>平均赔率</td><td>{{ "%.2f"|format(backtest_result.avg_odds) }}</td></tr>
                <tr><td>夏普比率</td><td>{{ "%.4f"|format(backtest_result.sharpe_ratio) }}</td></tr>
                <tr><td>盈利因子</td><td>{{ "%.4f"|format(backtest_result.profit_factor) }}</td></tr>
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if charts %}
    <div class="section">
        <h2>📈 可视化图表</h2>
        {% for chart_info in charts %}
        <div class="chart-placeholder">
            <h3>{{ chart_info.title }}</h3>
            <p>图表文件: {{ chart_info.filename }}</p>
            <small>{{ chart_info.description }}</small>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if recommendations %}
    <div class="section">
        <h2>💡 改进建议</h2>
        {% for recommendation in recommendations %}
        <div class="metric-card">
            <h3>{{ recommendation.title }}</h3>
            <p>{{ recommendation.description }}</p>
            <strong>优先级:</strong>
            <span class="badge badge-{{ recommendation.priority_class }}">
                {{ recommendation.priority }}
            </span>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="footer">
        <p>报告由 Football Prediction Evaluation System 自动生成</p>
        <p>生成时间: {{ generation_time }}</p>
    </div>
</body>
</html>
        """

    def _get_metric_status(self, metric_name: str, value: float) -> str:
        """获取指标状态"""
        if metric_name in [
            "accuracy",
            "f1_weighted",
            "precision_weighted",
            "recall_weighted",
        ]:
            if value >= 0.8:
                return "优秀"
            elif value >= 0.6:
                return "良好"
            else:
                return "需改进"
        elif metric_name in ["logloss", "brier_score_avg"]:
            if value <= 0.3:
                return "优秀"
            elif value <= 0.5:
                return "良好"
            else:
                return "需改进"
        else:
            return "标准"

    def _get_metric_class(self, metric_name: str, value: float) -> str:
        """获取指标CSS类"""
        if self._get_metric_status(metric_name, value) == "优秀":
            return "good"
        elif self._get_metric_status(metric_name, value) == "需改进":
            return "danger"
        else:
            return "warning"

    def build_summary_metrics(
        self, metrics_result: dict, backtest_result=None
    ) -> list[dict]:
        """构建摘要指标"""
        summary = []

        # 添加关键分类指标
        if "accuracy" in metrics_result:
            summary.append(
                {
                    "name": "准确率",
                    "value": f"{metrics_result['accuracy']:.4f}",
                    "unit": "",
                    "class": self._get_metric_class(
                        "accuracy", metrics_result["accuracy"]
                    ),
                    "description": "模型预测正确的比例",
                }
            )

        if "logloss" in metrics_result:
            summary.append(
                {
                    "name": "Log Loss",
                    "value": f"{metrics_result['logloss']:.4f}",
                    "unit": "",
                    "class": self._get_metric_class(
                        "logloss", metrics_result["logloss"]
                    ),
                    "description": "概率预测质量指标，越小越好",
                }
            )

        # 添加校准指标
        if "brier_score_avg" in metrics_result:
            summary.append(
                {
                    "name": "平均Brier分数",
                    "value": f"{metrics_result['brier_score_avg']:.4f}",
                    "unit": "",
                    "class": self._get_metric_class(
                        "brier_score_avg", metrics_result["brier_score_avg"]
                    ),
                    "description": "概率校准质量，越小越好",
                }
            )

        # 添加回测指标
        if backtest_result:
            summary.append(
                {
                    "name": "ROI",
                    "value": f"{backtest_result.roi:.2f}",
                    "unit": "%",
                    "class": "good" if backtest_result.roi > 0 else "danger",
                    "description": "投资回报率",
                }
            )

            summary.append(
                {
                    "name": "胜率",
                    "value": f"{backtest_result.win_rate:.2f}",
                    "unit": "%",
                    "class": "good" if backtest_result.win_rate > 50 else "warning",
                    "description": "投注获胜比例",
                }
            )

        return summary

    def generate_recommendations(
        self, metrics_result: dict, backtest_result=None
    ) -> list[dict]:
        """生成改进建议"""
        recommendations = []

        # 基于分类指标的建议
        accuracy = metrics_result.get("accuracy", 0)
        if accuracy < 0.6:
            recommendations.append(
                {
                    "title": "提高模型准确率",
                    "description": f"当前准确率{accuracy:.2%}较低，建议增加特征工程、调整模型参数或尝试其他算法。",
                    "priority": "高",
                    "priority_class": "danger",
                }
            )

        # 基于校准指标的建议
        if "brier_score_avg" in metrics_result:
            brier_score = metrics_result["brier_score_avg"]
            if brier_score > 0.25:
                recommendations.append(
                    {
                        "title": "改进概率校准",
                        "description": f"平均Brier分数{brier_score:.4f}较高，建议应用概率校准方法如Isotonic回归或Platt缩放。",
                        "priority": "中",
                        "priority_class": "warning",
                    }
                )

        # 基于回测指标的建议
        if backtest_result:
            if backtest_result.roi < 0:
                recommendations.append(
                    {
                        "title": "优化投注策略",
                        "description": f"当前ROI为{backtest_result.roi:.2f}%，建议调整投注阈值、改进价值计算或采用更保守的资金管理策略。",
                        "priority": "高",
                        "priority_class": "danger",
                    }
                )

            if backtest_result.max_drawdown_percentage > 20:
                recommendations.append(
                    {
                        "title": "控制风险",
                        "description": f"最大回撤达到{backtest_result.max_drawdown_percentage:.2f}%，建议实施更严格的资金管理策略。",
                        "priority": "中",
                        "priority_class": "warning",
                    }
                )

        return recommendations

    def build_html_report(
        self,
        metrics_result: dict,
        calibration_result=None,
        backtest_result=None,
        charts: list[dict] = None,
        model_name: str = "Football Prediction Model",
        model_version: str = "1.0.0",
    ) -> str:
        """
        构建HTML评估报告

        Args:
            metrics_result: 分类指标结果
            calibration_result: 校准结果
            backtest_result: 回测结果
            charts: 图表信息列表
            model_name: 模型名称
            model_version: 模型版本

        Returns:
            HTML报告文件路径
        """
        if not HAS_JINJA2:
            logger.error("jinja2 not available - cannot build HTML report")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"evaluation_report_{timestamp}.html"

        # 准备模板数据
        template_data = {
            "title": f"{model_name} - 评估报告",
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model_version": model_version,
            "summary": self.build_summary_metrics(metrics_result, backtest_result),
            "metrics": metrics_result,
            "calibration_metrics": {
                k: v
                for k, v in metrics_result.items()
                if k.startswith("brier_score_")
                or k.startswith("ece_")
                or k.startswith("mce_")
            },
            "backtest_result": backtest_result,
            "charts": charts or [],
            "recommendations": self.generate_recommendations(
                metrics_result, backtest_result
            ),
            "metric_names": {
                "accuracy": "准确率",
                "precision_weighted": "加权精确率",
                "recall_weighted": "加权召回率",
                "f1_weighted": "加权F1分数",
                "precision_macro": "宏平均精确率",
                "recall_macro": "宏平均召回率",
                "f1_macro": "宏平均F1分数",
                "logloss": "对数损失",
                "brier_score_avg": "平均Brier分数",
                "ece_avg": "平均期望校准误差",
                "mce_avg": "平均最大校准误差",
            },
            "class_names": {"H": "主胜", "D": "平局", "A": "客胜"},
        }

        # 渲染HTML
        template = self.template_env.globals["template"]
        html_content = template.render(**template_data)

        # 保存HTML文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML report generated: {output_file}")
        return str(output_file)

    def build_json_report(
        self,
        metrics_result: dict,
        calibration_result=None,
        backtest_result=None,
        charts: list[dict] = None,
        model_name: str = "Football Prediction Model",
        model_version: str = "1.0.0",
    ) -> str:
        """
        构建JSON评估报告

        Args:
            metrics_result: 分类指标结果
            calibration_result: 校准结果
            backtest_result: 回测结果
            charts: 图表信息列表
            model_name: 模型名称
            model_version: 模型版本

        Returns:
            JSON报告文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"evaluation_report_{timestamp}.json"

        # 准备JSON数据
        report_data = {
            "metadata": {
                "model_name": model_name,
                "model_version": model_version,
                "generation_time": datetime.now().isoformat(),
                "report_version": "1.0.0",
            },
            "summary": self.build_summary_metrics(metrics_result, backtest_result),
            "metrics": metrics_result,
            "recommendations": self.generate_recommendations(
                metrics_result, backtest_result
            ),
            "charts": charts or [],
        }

        # 添加校准结果
        if calibration_result:
            report_data["calibration"] = (
                calibration_result.to_dict()
                if hasattr(calibration_result, "to_dict")
                else calibration_result
            )

        # 添加回测结果
        if backtest_result:
            report_data["backtest"] = backtest_result.to_dict()

        # 保存JSON文件
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"JSON report generated: {output_file}")
        return str(output_file)

    def build_pdf_report(self, html_file: str = None, **kwargs) -> str:
        """
        构建PDF评估报告

        Args:
            html_file: HTML文件路径（如果为None，先生成HTML）
            **kwargs: 传递给build_html_report的参数

        Returns:
            PDF报告文件路径
        """
        if not HAS_WEASYPRINT:
            logger.error("weasyprint not available - cannot build PDF report")
            return ""

        if html_file is None:
            html_file = self.build_html_report(**kwargs)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_file = self.output_dir / f"evaluation_report_{timestamp}.pdf"

        try:
            # 转换HTML为PDF
            html_doc = weasyprint.HTML(filename=html_file)
            html_doc.write_pdf(pdf_file)

            logger.info(f"PDF report generated: {pdf_file}")
            return str(pdf_file)

        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            return ""

    def build_comprehensive_report(
        self,
        metrics_result: dict,
        calibration_result=None,
        backtest_result=None,
        charts: list[dict] = None,
        model_name: str = "Football Prediction Model",
        model_version: str = "1.0.0",
        formats: list[str] = None,
    ) -> dict[str, str]:
        """
        构建综合评估报告

        Args:
            metrics_result: 分类指标结果
            calibration_result: 校准结果
            backtest_result: 回测结果
            charts: 图表信息列表
            model_name: 模型名称
            model_version: 模型版本
            formats: 要生成的报告格式列表

        Returns:
            生成的报告文件路径字典
        """
        if formats is None:
            formats = ["html", "json"]
        report_files = {}

        # 生成HTML报告
        if "html" in formats:
            html_file = self.build_html_report(
                metrics_result=metrics_result,
                calibration_result=calibration_result,
                backtest_result=backtest_result,
                charts=charts,
                model_name=model_name,
                model_version=model_version,
            )
            if html_file:
                report_files["html"] = html_file

                # 如果需要PDF且HTML已生成，尝试转换
                if "pdf" in formats:
                    pdf_file = self.build_pdf_report(html_file=html_file)
                    if pdf_file:
                        report_files["pdf"] = pdf_file

        # 生成JSON报告
        if "json" in formats:
            json_file = self.build_json_report(
                metrics_result=metrics_result,
                calibration_result=calibration_result,
                backtest_result=backtest_result,
                charts=charts,
                model_name=model_name,
                model_version=model_version,
            )
            if json_file:
                report_files["json"] = json_file

        logger.info(
            f"Comprehensive report generated with formats: {list(report_files.keys())}"
        )
        return report_files


# 便捷函数
def generate_evaluation_report(
    metrics_result: dict,
    calibration_result=None,
    backtest_result=None,
    charts: list[dict] = None,
    output_dir: str = None,
    model_name: str = "Model",
    formats: list[str] = None,
) -> dict[str, str]:
    """
    便捷的评估报告生成函数

    Args:
        metrics_result: 分类指标结果
        calibration_result: 校准结果
        backtest_result: 回测结果
        charts: 图表信息列表
        output_dir: 输出目录
        model_name: 模型名称
        formats: 要生成的报告格式列表

    Returns:
        生成的报告文件路径字典
    """
    if formats is None:
        formats = ["html", "json"]
    builder = ReportBuilder(output_dir=output_dir)
    return builder.build_comprehensive_report(
        metrics_result=metrics_result,
        calibration_result=calibration_result,
        backtest_result=backtest_result,
        charts=charts,
        model_name=model_name,
        formats=formats,
    )
