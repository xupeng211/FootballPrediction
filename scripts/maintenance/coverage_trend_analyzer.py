#!/usr/bin/env python3
"""
覆盖率趋势分析器
Coverage Trend Analyzer

分析测试覆盖率的历史数据，生成趋势报告和预测。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
import math

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class CoverageData:
    """覆盖率数据点"""
    timestamp: str
    total_coverage: float
    module_coverage: Dict[str, float]
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    execution_time: float

@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    trend_direction: str  # 'improving', 'declining', 'stable'
    trend_strength: float  # 0-1, 趋势强度
    avg_coverage: float
    max_coverage: float
    min_coverage: float
    coverage_variance: float
    prediction_7d: float
    prediction_30d: float
    confidence: float  # 预测置信度

@dataclass
class ModuleAnalysis:
    """模块分析结果"""
    module_name: str
    current_coverage: float
    trend_direction: str
    trend_strength: float
    prediction_7d: float
    priority: str  # 'high', 'medium', 'low'

class CoverageTrendAnalyzer:
    """覆盖率趋势分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

        # 数据存储路径
        self.db_path = project_root / "data" / "coverage_trends.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

        # 分析参数
        self.analysis_window_days = 30  # 分析窗口期
        self.prediction_days = [7, 30]  # 预测天数
        self.significant_threshold = 2.0  # 显著变化阈值(%)

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coverage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_coverage REAL NOT NULL,
                    module_coverage TEXT NOT NULL,
                    total_tests INTEGER NOT NULL,
                    passed_tests INTEGER NOT NULL,
                    failed_tests INTEGER NOT NULL,
                    error_tests INTEGER NOT NULL,
                    execution_time REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON coverage_history(timestamp)
            """)

    def collect_current_coverage(self) -> Optional[CoverageData]:
        """收集当前覆盖率数据"""
        try:
            # 运行pytest生成覆盖率报告
            import subprocess

            result = subprocess.run(
                ["pytest", "--cov=src", "--cov-report=json", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                print(f"⚠️ 测试运行失败: {result.stderr}")
                return None

            # 读取覆盖率报告
            coverage_file = self.project_root / "coverage.json"
            if not coverage_file.exists():
                print("⚠️ 覆盖率报告文件不存在")
                return None

            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)

            # 提取总覆盖率
            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0.0)

            # 提取模块覆盖率
            module_coverage = {}
            for file_path, file_data in coverage_data.get("files", {}).items():
                if "src/" in file_path:
                    module_name = file_path.split("src/")[1].split("/")[0]
                    module_coverage[module_name] = file_data.get("summary", {}).get("percent_covered", 0.0)

            # 解析测试结果
            test_output = result.stdout
            total_tests = passed_tests = failed_tests = error_tests = 0
            execution_time = 0.0

            lines = test_output.split('\n')
            for line in lines:
                if 'passed' in line and ('failed' in line or 'error' in line):
                    parts = line.split()
                    for part in parts:
                        if part.endswith('passed'):
                            passed_tests = int(part.replace('passed', ''))
                        elif part.endswith('failed'):
                            failed_tests = int(part.replace('failed', ''))
                        elif part.endswith('error'):
                            error_tests = int(part.replace('error', ''))
                    total_tests = passed_tests + failed_tests + error_tests

                if 'seconds' in line and '=' in line:
                    try:
                        time_part = line.split('=')[1].strip()
                        execution_time = float(time_part.split()[0])
                    except (IndexError, ValueError):
                        continue

            return CoverageData(
                timestamp=datetime.now().isoformat(),
                total_coverage=total_coverage,
                module_coverage=module_coverage,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                error_tests=error_tests,
                execution_time=execution_time
            )

        except Exception as e:
            print(f"❌ 收集覆盖率数据失败: {e}")
            return None

    def store_coverage_data(self, data: CoverageData):
        """存储覆盖率数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO coverage_history
                (timestamp, total_coverage, module_coverage, total_tests,
                 passed_tests, failed_tests, error_tests, execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.timestamp,
                data.total_coverage,
                json.dumps(data.module_coverage),
                data.total_tests,
                data.passed_tests,
                data.failed_tests,
                data.error_tests,
                data.execution_time
            ))

    def get_historical_data(self, days: int = 30) -> List[CoverageData]:
        """获取历史数据"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, total_coverage, module_coverage, total_tests,
                       passed_tests, failed_tests, error_tests, execution_time
                FROM coverage_history
                WHERE timestamp >= ?
                ORDER BY timestamp
            """, (cutoff_date,))

            results = []
            for row in cursor.fetchall():
                results.append(CoverageData(
                    timestamp=row[0],
                    total_coverage=row[1],
                    module_coverage=json.loads(row[2]),
                    total_tests=row[3],
                    passed_tests=row[4],
                    failed_tests=row[5],
                    error_tests=row[6],
                    execution_time=row[7]
                ))

        return results

    def calculate_trend(self, values: List[float]) -> Tuple[str, float]:
        """计算趋势方向和强度"""
        if len(values) < 2:
            return "stable", 0.0

        # 计算线性回归
        x = list(range(len(values)))
        y = values

        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        # 计算斜率
        if n * sum_x2 - sum_x ** 2 == 0:
            return "stable", 0.0

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

        # 计算相关系数
        mean_x = sum_x / n
        mean_y = sum_y / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))

        if sum_sq_x * sum_sq_y == 0:
            correlation = 0.0
        else:
            correlation = numerator / math.sqrt(sum_sq_x * sum_sq_y)

        # 确定趋势方向
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "improving"
        else:
            direction = "declining"

        # 趋势强度基于斜率和相关系数
        strength = min(1.0, abs(slope) * abs(correlation))

        return direction, strength

    def predict_coverage(self, values: List[float], days: int) -> Tuple[float, float]:
        """预测未来覆盖率"""
        if len(values) < 3:
            return values[-1] if values else 0.0, 0.0

        # 使用简单移动平均和趋势进行预测
        recent_values = values[-7:] if len(values) >= 7 else values
        avg_recent = statistics.mean(recent_values)

        # 计算趋势
        direction, strength = self.calculate_trend(values)

        # 基于趋势调整预测
        if direction == "improving":
            # 改进趋势：使用指数增长模型
            trend_factor = 1 + (strength * 0.02 * days / 7)
        elif direction == "declining":
            # 下降趋势：使用线性衰减模型
            trend_factor = 1 - (strength * 0.01 * days / 7)
        else:
            # 稳定趋势：保持当前水平
            trend_factor = 1.0

        prediction = min(100.0, max(0.0, avg_recent * trend_factor))

        # 计算置信度（基于数据点的数量和趋势强度）
        data_confidence = min(1.0, len(values) / 30)  # 30个数据点达到100%置信度
        trend_confidence = strength
        confidence = (data_confidence + trend_confidence) / 2

        return prediction, confidence

    def analyze_trends(self, days: int = 30) -> TrendAnalysis:
        """分析覆盖率趋势"""
        historical_data = self.get_historical_data(days)

        if not historical_data:
            return TrendAnalysis(
                trend_direction="stable",
                trend_strength=0.0,
                avg_coverage=0.0,
                max_coverage=0.0,
                min_coverage=0.0,
                coverage_variance=0.0,
                prediction_7d=0.0,
                prediction_30d=0.0,
                confidence=0.0
            )

        # 提取覆盖率值
        coverage_values = [data.total_coverage for data in historical_data]

        # 计算基本统计
        avg_coverage = statistics.mean(coverage_values)
        max_coverage = max(coverage_values)
        min_coverage = min(coverage_values)
        coverage_variance = statistics.variance(coverage_values) if len(coverage_values) > 1 else 0.0

        # 计算趋势
        trend_direction, trend_strength = self.calculate_trend(coverage_values)

        # 预测未来覆盖率
        prediction_7d, confidence_7d = self.predict_coverage(coverage_values, 7)
        prediction_30d, confidence_30d = self.predict_coverage(coverage_values, 30)

        # 综合置信度
        confidence = (confidence_7d + confidence_30d) / 2

        return TrendAnalysis(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            avg_coverage=avg_coverage,
            max_coverage=max_coverage,
            min_coverage=min_coverage,
            coverage_variance=coverage_variance,
            prediction_7d=prediction_7d,
            prediction_30d=prediction_30d,
            confidence=confidence
        )

    def analyze_modules(self, days: int = 30) -> List[ModuleAnalysis]:
        """分析模块覆盖率趋势"""
        historical_data = self.get_historical_data(days)

        if not historical_data:
            return []

        # 收集所有模块
        all_modules = set()
        for data in historical_data:
            all_modules.update(data.module_coverage.keys())

        module_analyses = []

        for module in all_modules:
            # 提取该模块的覆盖率历史
            module_coverages = []
            for data in historical_data:
                coverage = data.module_coverage.get(module, 0.0)
                module_coverages.append(coverage)

            if len(module_coverages) < 2:
                continue

            # 计算趋势
            trend_direction, trend_strength = self.calculate_trend(module_coverages)

            # 预测未来覆盖率
            prediction_7d, _ = self.predict_coverage(module_coverages, 7)

            # 确定优先级
            current_coverage = module_coverages[-1]
            if current_coverage < 30:
                priority = "high"
            elif current_coverage < 60:
                priority = "medium"
            else:
                priority = "low"

            module_analyses.append(ModuleAnalysis(
                module_name=module,
                current_coverage=current_coverage,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                prediction_7d=prediction_7d,
                priority=priority
            ))

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        module_analyses.sort(key=lambda x: (priority_order[x.priority], -x.current_coverage))

        return module_analyses

    def generate_report(self, days: int = 30) -> Dict[str, Any]:
        """生成趋势分析报告"""
        print(f"📈 生成覆盖率趋势分析报告 (最近{days}天)...")

        # 收集当前数据
        current_data = self.collect_current_coverage()
        if current_data:
            self.store_coverage_data(current_data)
            print(f"✅ 已收集当前覆盖率数据: {current_data.total_coverage:.1f}%")

        # 分析趋势
        trend_analysis = self.analyze_trends(days)
        module_analyses = self.analyze_modules(days)

        # 生成建议
        recommendations = self._generate_recommendations(trend_analysis, module_analyses)

        # 构建报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_period_days": days,
            "total_data_points": len(self.get_historical_data(days)),
            "trend_analysis": asdict(trend_analysis),
            "module_analyses": [asdict(analysis) for analysis in module_analyses],
            "recommendations": recommendations,
            "summary": {
                "overall_trend": f"{trend_analysis.trend_direction} ({trend_analysis.trend_strength:.2f})",
                "current_coverage": current_data.total_coverage if current_data else 0.0,
                "prediction_7d": trend_analysis.prediction_7d,
                "prediction_30d": trend_analysis.prediction_30d,
                "high_priority_modules": len([m for m in module_analyses if m.priority == "high"]),
                "improving_modules": len([m for m in module_analyses if m.trend_direction == "improving"]),
                "declining_modules": len([m for m in module_analyses if m.trend_direction == "declining"])
            }
        }

        return report

    def _generate_recommendations(self, trend: TrendAnalysis, modules: List[ModuleAnalysis]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于总体趋势的建议
        if trend.trend_direction == "declining" and trend.trend_strength > 0.3:
            recommendations.append("🚨 **覆盖率持续下降**，建议立即审查测试策略和代码变更")
        elif trend.trend_direction == "stable" and trend.avg_coverage < 50:
            recommendations.append("📊 **覆盖率偏低且停滞不前**，建议制定覆盖率提升计划")
        elif trend.trend_direction == "improving":
            recommendations.append("📈 **覆盖率持续改善**，继续保持当前测试策略")

        # 基于预测的建议
        if trend.prediction_30d < trend.avg_coverage - 5:
            recommendations.append("⚠️ **预测覆盖率将下降**，建议提前采取预防措施")

        # 基于模块优先级的建议
        high_priority_modules = [m for m in modules if m.priority == "high"]
        if high_priority_modules:
            recommendations.append(f"🎯 **重点关注高优先级模块** ({len(high_priority_modules)}个):")
            for module in high_priority_modules[:3]:  # 显示前3个
                recommendations.append(f"   - {module.module_name}: {module.current_coverage:.1f}% → {module.prediction_7d:.1f}%")

        # 基于模块趋势的建议
        declining_modules = [m for m in modules if m.trend_direction == "declining" and m.trend_strength > 0.2]
        if declining_modules:
            recommendations.append(f"📉 **模块覆盖率下降警告** ({len(declining_modules)}个):")
            for module in declining_modules[:3]:  # 显示前3个
                recommendations.append(f"   - {module.module_name}: 下降趋势 ({module.trend_strength:.2f})")

        if not recommendations:
            recommendations.append("✅ **覆盖率状况良好**，继续保持现有测试质量")

        return recommendations

    def export_report(self, report: Dict[str, Any], output_file: Optional[Path] = None) -> Path:
        """导出趋势分析报告"""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.project_root / "reports" / "coverage_trends" / f"coverage_trend_report_{timestamp}.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return output_file

    def generate_html_report(self, report: Dict[str, Any]) -> Path:
        """生成HTML格式的趋势报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = self.project_root / "reports" / "coverage_trends" / f"coverage_trend_report_{timestamp}.html"

        html_file.parent.mkdir(parents=True, exist_ok=True)

        trend = report["trend_analysis"]
        summary = report["summary"]

        # 趋势颜色映射
        trend_colors = {
            "improving": "#28a745",
            "declining": "#dc3545",
            "stable": "#6c757d"
        }

        trend_emojis = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️"
        }

        trend_direction = trend.get("trend_direction", "stable")

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>覆盖率趋势分析报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }}
        .trend-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .trend-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid {trend_colors[trend_direction]};
            text-align: center;
        }}
        .trend-value {{
            font-size: 2em;
            font-weight: bold;
            color: {trend_colors[trend_direction]};
            margin: 10px 0;
        }}
        .modules-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .module-card {{
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            background: white;
        }}
        .module-header {{
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .priority-high {{ border-left: 4px solid #dc3545; }}
        .priority-medium {{ border-left: 4px solid #ffc107; }}
        .priority-low {{ border-left: 4px solid #28a745; }}
        .recommendations {{
            background: #e7f3ff;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .recommendations h3 {{
            margin-top: 0;
            color: #0056b3;
        }}
        .trend-indicator {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            background: {trend_colors[trend_direction]};
            color: white;
            font-size: 0.8em;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 覆盖率趋势分析报告</h1>
            <p>生成时间: {report['timestamp'][:19].replace('T', ' ')}</p>
            <p>分析期间: 最近 {report['analysis_period_days']} 天 ({report['total_data_points']} 个数据点)</p>
        </div>

        <div class="trend-overview">
            <div class="trend-card">
                <h3>总体趋势</h3>
                <div class="trend-value">{trend_emojis[trend_direction]} {trend_direction.upper()}</div>
                <p>趋势强度: {trend.get('trend_strength', 0):.2f}</p>
            </div>
            <div class="trend-card">
                <h3>当前覆盖率</h3>
                <div class="trend-value">{summary['current_coverage']:.1f}%</div>
                <p>平均: {trend.get('avg_coverage', 0):.1f}%</p>
            </div>
            <div class="trend-card">
                <h3>7天预测</h3>
                <div class="trend-value">{trend.get('prediction_7d', 0):.1f}%</div>
                <p>置信度: {trend.get('confidence', 0):.1%}</p>
            </div>
            <div class="trend-card">
                <h3>30天预测</h3>
                <div class="trend-value">{trend.get('prediction_30d', 0):.1f}%</div>
                <p>最高: {trend.get('max_coverage', 0):.1f}%</p>
            </div>
        </div>

        <h2>📊 模块覆盖率分析</h2>
        <div class="modules-grid">
"""

        # 添加模块分析卡片
        for module in report["module_analyses"][:12]:  # 显示前12个模块
            trend_emoji = trend_emojis.get(module["trend_direction"], "➡️")
            priority_class = f"priority-{module['priority']}"

            html_content += f"""
            <div class="module-card {priority_class}">
                <div class="module-header">
                    <h4>{module['module_name']}</h4>
                    <span class="trend-indicator">{trend_emoji} {module['trend_direction']}</span>
                </div>
                <p><strong>当前覆盖率:</strong> {module['current_coverage']:.1f}%</p>
                <p><strong>7天预测:</strong> {module['prediction_7d']:.1f}%</p>
                <p><strong>趋势强度:</strong> {module['trend_strength']:.2f}</p>
                <p><strong>优先级:</strong> {module['priority'].upper()}</p>
            </div>
"""

        html_content += """
        </div>

        <div class="recommendations">
            <h3>💡 改进建议</h3>
            <ul>
"""

        # 添加建议
        for rec in report["recommendations"]:
            html_content += f"                <li>{rec}</li>\n"

        html_content += """
            </ul>
        </div>

        <div style="text-align: center; margin-top: 40px; color: #6c757d;">
            <p>报告由 CoverageTrendAnalyzer 自动生成</p>
        </div>
    </div>
</body>
</html>
"""

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return html_file

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="覆盖率趋势分析器")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="分析天数 (默认: 30)"
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="仅收集数据，不生成报告"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="生成HTML格式报告"
    )

    args = parser.parse_args()

    # 创建分析器实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    analyzer = CoverageTrendAnalyzer(project_root)

    try:
        if args.collect_only:
            # 仅收集数据
            print("📊 收集当前覆盖率数据...")
            data = analyzer.collect_current_coverage()
            if data:
                analyzer.store_coverage_data(data)
                print(f"✅ 数据已存储: 覆盖率 {data.total_coverage:.1f}%")
            else:
                print("❌ 数据收集失败")
                sys.exit(1)
        else:
            # 生成完整报告
            report = analyzer.generate_report(args.days)

            # 导出JSON报告
            json_file = analyzer.export_report(report)
            print(f"📄 JSON报告已生成: {json_file}")

            # 生成HTML报告
            if args.html:
                html_file = analyzer.generate_html_report(report)
                print(f"🌐 HTML报告已生成: {html_file}")

            # 显示摘要
            summary = report["summary"]
            print(f"\n📈 趋势分析摘要:")
            print(f"   总体趋势: {summary['overall_trend']}")
            print(f"   当前覆盖率: {summary['current_coverage']:.1f}%")
            print(f"   7天预测: {summary['prediction_7d']:.1f}%")
            print(f"   30天预测: {summary['prediction_30d']:.1f}%")
            print(f"   高优先级模块: {summary['high_priority_modules']}个")
            print(f"   改善中模块: {summary['improving_modules']}个")
            print(f"   下降模块: {summary['declining_modules']}个")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()