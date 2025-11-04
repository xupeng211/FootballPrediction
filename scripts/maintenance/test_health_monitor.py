#!/usr/bin/env python3
"""
测试健康监控工具
Test Health Monitoring Tool

专门用于监控测试系统的健康状况，包括测试覆盖率、执行状态、错误率等指标。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.maintenance.maintenance_logger import MaintenanceLogger, MaintenanceRecord

@dataclass
class TestHealthMetrics:
    """测试健康指标数据结构"""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    coverage_percentage: float
    collection_time_seconds: float
    execution_time_seconds: float
    health_score: int
    issues: List[str]

@dataclass
class TestHealthAlert:
    """测试健康警报"""
    alert_type: str
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    current_value: Any
    threshold_value: Any
    timestamp: str
    resolved: bool = False

class TestHealthMonitor:
    """测试健康监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = MaintenanceLogger(project_root)

        # 测试健康阈值配置
        self.thresholds = {
            "min_coverage": 10.0,          # 最低覆盖率
            "max_fail_rate": 20.0,          # 最大失败率百分比
            "max_error_rate": 5.0,          # 最大错误率百分比
            "min_pass_rate": 70.0,          # 最低通过率百分比
            "max_execution_time": 300.0,    # 最大执行时间(秒)
            "min_health_score": 70,         # 最低健康评分
            "max_collection_errors": 5      # 最大收集错误数
        }

        # 监控数据目录
        self.monitoring_dir = project_root / "logs" / "test_monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.monitoring_dir / "test_health_metrics.json"
        self.alerts_file = self.monitoring_dir / "test_health_alerts.json"
        self.config_file = self.monitoring_dir / "test_monitoring_config.json"

    def _load_config(self):
        """加载监控配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.thresholds.update(config.get("thresholds", {}))
            except Exception as e:
                print(f"⚠️  加载测试监控配置失败: {e}")

    def _save_config(self):
        """保存监控配置"""
        try:
            config = {
                "thresholds": self.thresholds,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存测试监控配置失败: {e}")

    def _run_pytest_collection(self) -> Tuple[int, float, List[str]]:
        """运行pytest收集测试"""
        try:
            start_time = time.time()
            result = subprocess.run(
                ["python3", "-m", "pytest", "--collect-only", "-q"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            collection_time = time.time() - start_time

            if result.returncode != 0:
                # 解析收集错误
                errors = []
                for line in result.stderr.split('\n'):
                    if 'ERROR' in line:
                        errors.append(line.strip())
                return 0, collection_time, errors
            else:
                # 解析收集结果
                for line in result.stdout.split('\n'):
                    if 'collected' in line and 'items' in line:
                        # 提取 "collected X items / Y errors"
                        if '/' in line:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == 'collected':
                                    total_tests = int(parts[i+1])
                                    return total_tests, collection_time, []
                return 0, collection_time, []

        except subprocess.TimeoutExpired:
            return 0, 60.0, ["收集测试超时"]
        except Exception as e:
            return 0, 0.0, [f"收集测试失败: {e}"]

    def _run_pytest_execution(self) -> Tuple[int, int, int, int, float, List[str]]:
        """运行pytest执行测试"""
        try:
            start_time = time.time()
            result = subprocess.run(
                ["python3", "-m", "pytest", "--tb=no", "--maxfail=10", "-x"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            execution_time = time.time() - start_time

            # 解析pytest输出
            passed = failed = skipped = errors = 0
            for line in result.stdout.split('\n'):
                if line.strip().endswith('passed'):
                    passed += 1
                elif line.strip().endswith('failed'):
                    failed += 1
                elif line.strip().endswith('skipped'):
                    skipped += 1
                elif line.strip().endswith('error'):
                    errors += 1

            return passed, failed, skipped, errors, execution_time, []

        except subprocess.TimeoutExpired:
            return 0, 0, 0, 0, 300.0, ["测试执行超时"]
        except Exception as e:
            return 0, 0, 0, 0, 0.0, [f"测试执行失败: {e}"]

    def _get_coverage_percentage(self) -> float:
        """获取测试覆盖率百分比"""
        try:
            # 尝试解析覆盖率XML文件
            coverage_file = self.project_root / "coverage.xml"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    content = f.read()
                    # 简单的XML解析
                    if 'line-rate="' in content:
                        start = content.find('line-rate="') + 11
                        end = content.find('"', start)
                        if start > 10 and end > start:
                            return float(content[start:end]) * 100

            # 备用方法：从pytest输出解析
            result = subprocess.run(
                ["python3", "-m", "pytest", "--cov=src", "--cov-report=term-missing", "--disable-warnings"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            for line in result.stdout.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith('%'):
                            return float(part[:-1])

        except Exception:
            pass

        return 0.0

    def _calculate_health_score(self, metrics: TestHealthMetrics) -> int:
        """计算测试健康评分"""
        score = 100

        # 覆盖率评分 (30%权重)
        coverage_score = min(metrics.coverage_percentage / self.thresholds["min_coverage"] * 30,
    30)
        score -= (30 - coverage_score)

        # 通过率评分 (25%权重)
        total_non_error = metrics.passed_tests + metrics.failed_tests
        if total_non_error > 0:
            pass_rate = (metrics.passed_tests / total_non_error) * 100
            pass_score = min(pass_rate / self.thresholds["min_pass_rate"] * 25, 25)
            score -= (25 - pass_score)

        # 失败率评分 (20%权重)
        if metrics.total_tests > 0:
            fail_rate = (metrics.failed_tests / metrics.total_tests) * 100
            if fail_rate > self.thresholds["max_fail_rate"]:
                score -= 20
            else:
                fail_score = 20 - (fail_rate / self.thresholds["max_fail_rate"]) * 20
                score -= (20 - fail_score)

        # 错误率评分 (15%权重)
        if metrics.total_tests > 0:
            error_rate = (metrics.error_tests / metrics.total_tests) * 100
            if error_rate > self.thresholds["max_error_rate"]:
                score -= 15
            else:
                error_score = 15 - (error_rate / self.thresholds["max_error_rate"]) * 15
                score -= (15 - error_score)

        # 执行时间评分 (10%权重)
        if metrics.execution_time_seconds > self.thresholds["max_execution_time"]:
            score -= 10
        else:
            time_score = 10 - (metrics.execution_time_seconds / self.thresholds["max_execution_time"]) * 10
            score -= (10 - time_score)

        return max(0, int(score))

    def _check_coverage_alert(self,
    metrics: TestHealthMetrics) -> Optional[TestHealthAlert]:
        """检查覆盖率警报"""
        if metrics.coverage_percentage < self.thresholds["min_coverage"]:
            severity = "critical" if metrics.coverage_percentage < self.thresholds["min_coverage"] * 0.5 else "warning"
            return TestHealthAlert(
                alert_type="coverage",
                severity=severity,
                title="测试覆盖率过低",
                message=f"当前覆盖率 {metrics.coverage_percentage:.1f}%，低于阈值 {self.thresholds['min_coverage']:.1f}%",
                current_value=metrics.coverage_percentage,
                threshold_value=self.thresholds["min_coverage"],
                timestamp=datetime.now().isoformat()
            )
        return None

    def _check_pass_rate_alert(self,
    metrics: TestHealthMetrics) -> Optional[TestHealthAlert]:
        """检查通过率警报"""
        total_non_error = metrics.passed_tests + metrics.failed_tests
        if total_non_error > 0:
            pass_rate = (metrics.passed_tests / total_non_error) * 100
            if pass_rate < self.thresholds["min_pass_rate"]:
                severity = "critical" if pass_rate < self.thresholds["min_pass_rate"] * 0.7 else "warning"
                return TestHealthAlert(
                    alert_type="pass_rate",
                    severity=severity,
                    title="测试通过率过低",
                    message=f"当前通过率 {pass_rate:.1f}%，低于阈值 {self.thresholds['min_pass_rate']:.1f}%",
                    current_value=pass_rate,
                    threshold_value=self.thresholds["min_pass_rate"],
                    timestamp=datetime.now().isoformat()
                )
        return None

    def _check_error_rate_alert(self,
    metrics: TestHealthMetrics) -> Optional[TestHealthAlert]:
        """检查错误率警报"""
        if metrics.total_tests > 0:
            error_rate = (metrics.error_tests / metrics.total_tests) * 100
            if error_rate > self.thresholds["max_error_rate"]:
                severity = "critical" if error_rate > self.thresholds["max_error_rate"] * 2 else "warning"
                return TestHealthAlert(
                    alert_type="error_rate",
                    severity=severity,
                    title="测试错误率过高",
                    message=f"当前错误率 {error_rate:.1f}%，超过阈值 {self.thresholds['max_error_rate']:.1f}%",
                    current_value=error_rate,
                    threshold_value=self.thresholds["max_error_rate"],
                    timestamp=datetime.now().isoformat()
                )
        return None

    def _check_health_score_alert(self,
    metrics: TestHealthMetrics) -> Optional[TestHealthAlert]:
        """检查健康评分警报"""
        if metrics.health_score < self.thresholds["min_health_score"]:
            severity = "critical" if metrics.health_score < self.thresholds["min_health_score"] * 0.5 else "warning"
            return TestHealthAlert(
                alert_type="health_score",
                severity=severity,
                title="测试健康评分过低",
                message=f"当前健康评分 {metrics.health_score}，低于阈值 {self.thresholds['min_health_score']}",
                current_value=metrics.health_score,
                threshold_value=self.thresholds["min_health_score"],
                timestamp=datetime.now().isoformat()
            )
        return None

    def run_test_health_check(self) -> Dict[str, Any]:
        """执行测试健康检查"""
        print("🔍 开始测试健康检查...")

        start_time = time.time()

        # 运行测试收集
        print("📊 收集测试信息...")
        total_tests, collection_time, collection_errors = self._run_pytest_collection()

        # 运行测试执行
        print("🧪 执行测试...")
        passed,
    failed,
    skipped,
    errors,
    execution_time,
    execution_errors = self._run_pytest_execution()

        # 获取覆盖率
        print("📈 计算覆盖率...")
        coverage_percentage = self._get_coverage_percentage()

        # 创建指标
        metrics = TestHealthMetrics(
            timestamp=datetime.now().isoformat(),
            total_tests=total_tests,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=errors,
            coverage_percentage=coverage_percentage,
            collection_time_seconds=collection_time,
            execution_time_seconds=execution_time,
            health_score=0,  # 将在下面计算
            issues=collection_errors + execution_errors
        )

        # 计算健康评分
        metrics.health_score = self._calculate_health_score(metrics)

        # 生成警报
        print("🚨 检查健康警报...")
        alerts = []

        alert_functions = [
            self._check_coverage_alert,
            self._check_pass_rate_alert,
            self._check_error_rate_alert,
            self._check_health_score_alert
        ]

        for alert_func in alert_functions:
            try:
                alert = alert_func(metrics)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                print(f"⚠️  警报检查失败: {e}")

        # 如果没有警报，生成信息性警报
        if not alerts:
            info_alert = TestHealthAlert(
                alert_type="test_health_status",
                severity="info",
                title="测试系统健康状态良好",
                message=f"健康评分 {metrics.health_score}，覆盖率 {metrics.coverage_percentage:.1f}%，通过率 {(metrics.passed_tests/(metrics.passed_tests+metrics.failed_tests)*100 if metrics.passed_tests+metrics.failed_tests>0 else 0):.1f}%",
    
                current_value=metrics.health_score,
                threshold_value=100,
                timestamp=datetime.now().isoformat()
            )
            alerts.append(info_alert)

        # 保存指标
        try:
            self._save_metrics(metrics)
            self._save_alerts(alerts)
        except Exception as e:
            print(f"⚠️  保存监控数据失败: {e}")

        # 记录到维护日志
        try:
            self.logger.log_maintenance(MaintenanceRecord(
                timestamp=metrics.timestamp,
                action_type="test_health_check",
                description="测试系统健康监控检查",
                files_affected=metrics.total_tests,
                size_freed_mb=0,
                issues_found=len(alerts),
                issues_fixed=0,
                health_score_before=metrics.health_score,
                health_score_after=metrics.health_score,
                execution_time_seconds=time.time() - start_time,
                success=True,
                error_message=None
            ))
        except Exception as e:
            print(f"⚠️  记录维护日志失败: {e}")

        # 生成结果摘要
        critical_count = len([a for a in alerts if a.severity == "critical"])
        warning_count = len([a for a in alerts if a.severity == "warning"])

        print(f"\n📊 测试健康检查完成!")
        print(f"🏥 健康评分: {metrics.health_score}")
        print(f"📈 覆盖率: {metrics.coverage_percentage:.1f}%")
        print(f"🧪 测试统计: {metrics.passed_tests} 通过,
    {metrics.failed_tests} 失败,
    {metrics.skipped_tests} 跳过,
    {metrics.error_tests} 错误")
        print(f"⚡ 执行时间: {metrics.execution_time_seconds:.2f}秒")
        print(f"🚨 严重警报: {critical_count} 个")
        print(f"⚠️  警告警报: {warning_count} 个")

        if critical_count > 0:
            print("📞 建议立即处理严重问题！")

        return {
            "metrics": asdict(metrics),
            "alerts": [asdict(alert) for alert in alerts],
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "health_score": metrics.health_score,
                "coverage_percentage": metrics.coverage_percentage,
                "total_tests": metrics.total_tests,
                "passed_tests": metrics.passed_tests,
                "failed_tests": metrics.failed_tests,
                "critical_alerts": critical_count,
                "warning_alerts": warning_count,
                "execution_time_seconds": metrics.execution_time_seconds
            }
        }

    def _save_metrics(self, metrics: TestHealthMetrics):
        """保存测试指标"""
        try:
            # 加载现有指标
            metrics_history = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    metrics_history = json.load(f)

            # 添加新指标
            metrics_history.append(asdict(metrics))

            # 保留最近100条记录
            metrics_history = metrics_history[-100:]

            # 保存
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️  保存测试指标失败: {e}")

    def _save_alerts(self, alerts: List[TestHealthAlert]):
        """保存警报记录"""
        try:
            # 加载现有警报
            alerts_history = []
            if self.alerts_file.exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    alerts_history = json.load(f)

            # 添加新警报
            alerts_history.extend([asdict(alert) for alert in alerts])

            # 保留最近30天的警报
            cutoff_date = datetime.now() - timedelta(days=30)
            filtered_alerts = [
                alert for alert in alerts_history
                if datetime.fromisoformat(alert["timestamp"]) > cutoff_date
            ]

            # 保存
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_alerts, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️  保存警报记录失败: {e}")

    def get_test_health_trends(self, days: int = 7) -> Dict[str, Any]:
        """获取测试健康趋势数据"""
        try:
            if not self.metrics_file.exists():
                return {"message": "暂无趋势数据"}

            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                metrics_history = json.load(f)

            # 过滤指定天数的数据
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_metrics = [
                metric for metric in metrics_history
                if datetime.fromisoformat(metric["timestamp"]) > cutoff_date
            ]

            if not recent_metrics:
                return {"message": f"最近{days}天无数据"}

            # 计算趋势统计
            health_scores = [m["health_score"] for m in recent_metrics]
            coverage_rates = [m["coverage_percentage"] for m in recent_metrics]
            pass_rates = []
            for m in recent_metrics:
                total = m["passed_tests"] + m["failed_tests"]
                if total > 0:
                    pass_rates.append(m["passed_tests"] / total * 100)

            trend_analysis = {
                "period_days": days,
                "data_points": len(recent_metrics),
                "health_score": {
                    "current": health_scores[-1] if health_scores else 0,
                    "average": round(sum(health_scores) / len(health_scores),
    1) if health_scores else 0,
    
                    "min": min(health_scores) if health_scores else 0,
                    "max": max(health_scores) if health_scores else 0,
                    "trend": "improving" if len(health_scores) > 1 and health_scores[-1] > health_scores[0] else "stable"
                },
                "coverage": {
                    "current": coverage_rates[-1] if coverage_rates else 0,
                    "average": round(sum(coverage_rates) / len(coverage_rates),
    1) if coverage_rates else 0,
    
                    "min": min(coverage_rates) if coverage_rates else 0,
                    "max": max(coverage_rates) if coverage_rates else 0,
                    "trend": "improving" if len(coverage_rates) > 1 and coverage_rates[-1] > coverage_rates[0] else "stable"
                },
                "pass_rate": {
                    "current": pass_rates[-1] if pass_rates else 0,
                    "average": round(sum(pass_rates) / len(pass_rates),
    1) if pass_rates else 0,
    
                    "min": min(pass_rates) if pass_rates else 0,
                    "max": max(pass_rates) if pass_rates else 0,
                    "trend": "improving" if len(pass_rates) > 1 and pass_rates[-1] > pass_rates[0] else "stable"
                }
            }

            return trend_analysis

        except Exception as e:
            return {"error": f"获取趋势数据失败: {e}"}

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FootballPrediction 测试健康监控工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python3 test_health_monitor.py                    # 运行测试健康检查
  python3 test_health_monitor.py --trends            # 查看健康趋势
  python3 test_health_monitor.py --check-only         # 仅检查不保存
        """
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径 (默认: 自动检测)"
    )

    parser.add_argument(
        "--trends",
        action="store_true",
        help="显示健康趋势分析"
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅执行检查，不保存结果"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="显示配置信息"
    )

    args = parser.parse_args()

    # 创建测试健康监控器实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    monitor = TestHealthMonitor(project_root)

    try:
        if args.config:
            # 显示配置信息
            print("📋 测试健康监控配置:")
            print(f"项目根目录: {project_root}")
            print(f"监控数据目录: {monitor.monitoring_dir}")
            print("阈值配置:")
            for key, value in monitor.thresholds.items():
                print(f"  {key}: {value}")

        elif args.trends:
            # 显示健康趋势
            trends = monitor.get_test_health_trends(30)
            print("\n📈 测试健康趋势分析:")
            print(json.dumps(trends, indent=2, ensure_ascii=False, default=str))

        else:
            # 运行测试健康检查
            results = monitor.run_test_health_check()

            if not args.check_only:
                print(f"\n💾 监控数据已保存:")
                print(f"  - 指标文件: {monitor.metrics_file}")
                print(f"  - 警报文件: {monitor.alerts_file}")

            # 显示关键警报
            alerts = results["alerts"]
            critical_alerts = [a for a in alerts if a["severity"] == "critical"]
            warning_alerts = [a for a in alerts if a["severity"] == "warning"]

            if critical_alerts:
                print(f"\n🚨 严重警报 ({len(critical_alerts)} 个):")
                for alert in critical_alerts:
                    print(f"   - {alert['title']}: {alert['message']}")

            if warning_alerts:
                print(f"\n⚠️  警告警报 ({len(warning_alerts)} 个):")
                for alert in warning_alerts:
                    print(f"   - {alert['title']}: {alert['message']}")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()