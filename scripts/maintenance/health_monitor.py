#!/usr/bin/env python3
"""
目录健康监控系统
Directory Health Monitoring System

用于监控项目目录结构的健康状况，提供实时警报和趋势分析

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import smtplib
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# 尝试导入邮件相关模块，如果失败则跳过
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_SUPPORT = True
except ImportError:
    MimeText = None
    MimeMultipart = None
    EMAIL_SUPPORT = False

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.maintenance.directory_maintenance import DirectoryMaintenance
from scripts.maintenance.maintenance_logger import MaintenanceLogger

@dataclass
class HealthAlert:
    """健康警报数据结构"""
    alert_type: str
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    current_value: Any
    threshold_value: Any
    timestamp: str
    resolved: bool = False

class HealthMonitor:
    """目录健康监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.maintenance = DirectoryMaintenance(project_root)
        self.logger = MaintenanceLogger(project_root)

        # 健康阈值配置
        self.thresholds = {
            "max_root_files": 400,
            "max_empty_dirs": 5,
            "min_health_score": 70,
            "max_naming_violations": 10,
            "max_misplaced_files": 20,
            "max_project_size_gb": 5.0,
            "max_old_reports_days": 30
        }

        # 监控状态文件
        self.monitoring_dir = project_root / "logs" / "monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = self.monitoring_dir / "health_alerts.json"
        self.config_file = self.monitoring_dir / "monitoring_config.json"

        # 加载配置
        self._load_config()

    def _load_config(self):
        """加载监控配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.thresholds.update(config.get("thresholds", {}))
            except Exception as e:
                print(f"⚠️  加载监控配置失败: {e}")

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
            print(f"⚠️  保存监控配置失败: {e}")

    def _load_alerts(self) -> List[HealthAlert]:
        """加载历史警报"""
        if not self.alerts_file.exists():
            return []

        try:
            with open(self.alerts_file, 'r', encoding='utf-8') as f:
                alerts_data = json.load(f)
                return [HealthAlert(**alert) for alert in alerts_data]
        except Exception as e:
            print(f"⚠️  加载警报历史失败: {e}")
            return []

    def _save_alerts(self, alerts: List[HealthAlert]):
        """保存警报记录"""
        try:
            alerts_data = [asdict(alert) for alert in alerts]
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存警报记录失败: {e}")

    def _check_root_files_count(self,
    health_report: Dict[str,
    Any]) -> Optional[HealthAlert]:
        """检查根目录文件数量"""
        root_files = health_report["statistics"]["root_files"]
        threshold = self.thresholds["max_root_files"]

        if root_files > threshold:
            severity = "critical" if root_files > threshold * 1.5 else "warning"
            return HealthAlert(
                alert_type="root_files_count",
                severity=severity,
                title="根目录文件过多",
                message=f"根目录有 {root_files} 个文件，超过阈值 {threshold}",
                current_value=root_files,
                threshold_value=threshold,
                timestamp=datetime.now().isoformat()
            )

        return None

    def _check_health_score(self,
    health_report: Dict[str,
    Any]) -> Optional[HealthAlert]:
        """检查健康评分"""
        health_score = health_report["health_score"]
        threshold = self.thresholds["min_health_score"]

        if health_score < threshold:
            severity = "critical" if health_score < threshold * 0.7 else "warning"
            return HealthAlert(
                alert_type="health_score",
                severity=severity,
                title="健康评分过低",
                message=f"当前健康评分 {health_score}，低于阈值 {threshold}",
                current_value=health_score,
                threshold_value=threshold,
                timestamp=datetime.now().isoformat()
            )

        return None

    def _check_empty_directories(self,
    health_report: Dict[str,
    Any]) -> Optional[HealthAlert]:
        """检查空目录数量"""
        empty_dirs = health_report.get("empty_dirs", 0)
        threshold = self.thresholds["max_empty_dirs"]

        if empty_dirs > threshold:
            severity = "warning" if empty_dirs < threshold * 2 else "critical"
            return HealthAlert(
                alert_type="empty_directories",
                severity=severity,
                title="空目录过多",
                message=f"发现 {empty_dirs} 个空目录，超过阈值 {threshold}",
                current_value=empty_dirs,
                threshold_value=threshold,
                timestamp=datetime.now().isoformat()
            )

        return None

    def _check_naming_violations(self,
    health_report: Dict[str,
    Any]) -> Optional[HealthAlert]:
        """检查命名规范违规"""
        violations = health_report.get("naming_violations", 0)
        threshold = self.thresholds["max_naming_violations"]

        if violations > threshold:
            severity = "warning"
            return HealthAlert(
                alert_type="naming_violations",
                severity=severity,
                title="命名规范违规过多",
                message=f"发现 {violations} 个命名规范问题，超过阈值 {threshold}",
                current_value=violations,
                threshold_value=threshold,
                timestamp=datetime.now().isoformat()
            )

        return None

    def _check_misplaced_files(self,
    health_report: Dict[str,
    Any]) -> Optional[HealthAlert]:
        """检查错误放置的文件"""
        misplaced = health_report.get("misplaced_files", 0)
        threshold = self.thresholds["max_misplaced_files"]

        if misplaced > threshold:
            severity = "warning"
            return HealthAlert(
                alert_type="misplaced_files",
                severity=severity,
                title="错误放置文件过多",
                message=f"发现 {misplaced} 个错误放置的文件，超过阈值 {threshold}",
                current_value=misplaced,
                threshold_value=threshold,
                timestamp=datetime.now().isoformat()
            )

        return None

    def _check_project_size(self,
    health_report: Dict[str,
    Any]) -> Optional[HealthAlert]:
        """检查项目大小"""
        size_mb = health_report["statistics"]["total_size_mb"]
        threshold_gb = self.thresholds["max_project_size_gb"]
        threshold_mb = threshold_gb * 1024

        if size_mb > threshold_mb:
            severity = "warning"
            return HealthAlert(
                alert_type="project_size",
                severity=severity,
                title="项目大小过大",
                message=f"项目大小 {size_mb:.1f} MB，超过阈值 {threshold_mb:.1f} MB ({threshold_gb} GB)",
    
                current_value=size_mb,
                threshold_value=threshold_mb,
                timestamp=datetime.now().isoformat()
            )

        return None

    def check_health(self) -> Tuple[Dict[str, Any], List[HealthAlert]]:
        """执行健康检查并生成警报"""
        print("🔍 开始目录健康检查...")

        # 生成健康报告
        health_report = self.maintenance.generate_health_report()

        # 执行各项检查
        alerts = []

        check_functions = [
            self._check_root_files_count,
            self._check_health_score,
            self._check_empty_directories,
            self._check_naming_violations,
            self._check_misplaced_files,
            self._check_project_size
        ]

        for check_func in check_functions:
            try:
                alert = check_func(health_report)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                print(f"⚠️  健康检查项失败: {e}")

        # 如果没有警报，生成一个信息性的健康状态警报
        if not alerts:
            info_alert = HealthAlert(
                alert_type="health_status",
                severity="info",
                title="目录健康状态良好",
                message=f"健康评分 {health_report['health_score']}，所有指标正常",
                current_value=health_report['health_score'],
                threshold_value=100,
                timestamp=datetime.now().isoformat()
            )
            alerts.append(info_alert)

        print(f"📊 健康检查完成，评分: {health_report['health_score']}")
        print(f"🚨 发现 {len([a for a in alerts if a.severity != 'info'])} 个问题")

        return health_report, alerts

    def save_monitoring_report(self,
    health_report: Dict[str,
    Any],
    alerts: List[HealthAlert]) -> Path:
        """保存监控报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.monitoring_dir / f"health_monitoring_{timestamp}.json"

        monitoring_data = {
            "timestamp": datetime.now().isoformat(),
            "health_report": health_report,
            "alerts": [asdict(alert) for alert in alerts],
            "thresholds": self.thresholds,
            "summary": {
                "health_score": health_report["health_score"],
                "total_alerts": len(alerts),
                "critical_alerts": len([a for a in alerts if a.severity == "critical"]),
                "warning_alerts": len([a for a in alerts if a.severity == "warning"]),
                "info_alerts": len([a for a in alerts if a.severity == "info"])
            }
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(monitoring_data, f, indent=2, ensure_ascii=False)

        print(f"💾 监控报告已保存: {report_file}")
        return report_file

    def get_health_trends(self, days: int = 30) -> Dict[str, Any]:
        """获取健康趋势数据"""
        trends = self.logger.get_health_trends(days)

        if not trends:
            return {"message": "暂无趋势数据"}

        # 计算趋势统计
        health_scores = [t["health_score"] for t in trends]
        root_files = [t["root_files"] for t in trends]
        project_sizes = [t["total_size_mb"] for t in trends]

        trend_analysis = {
            "period_days": days,
            "data_points": len(trends),
            "health_score": {
                "current": health_scores[-1] if health_scores else 0,
                "average": round(sum(health_scores) / len(health_scores),
    1) if health_scores else 0,
    
                "min": min(health_scores) if health_scores else 0,
                "max": max(health_scores) if health_scores else 0,
                "trend": "improving" if len(health_scores) > 1 and health_scores[-1] > health_scores[0] else "stable"
            },
            "root_files": {
                "current": root_files[-1] if root_files else 0,
                "average": round(sum(root_files) / len(root_files),
    1) if root_files else 0,
    
                "min": min(root_files) if root_files else 0,
                "max": max(root_files) if root_files else 0,
                "trend": "increasing" if len(root_files) > 1 and root_files[-1] > root_files[0] else "stable"
            },
            "project_size": {
                "current_mb": project_sizes[-1] if project_sizes else 0,
                "average_mb": round(sum(project_sizes) / len(project_sizes),
    1) if project_sizes else 0,
    
                "min_mb": min(project_sizes) if project_sizes else 0,
                "max_mb": max(project_sizes) if project_sizes else 0,
                "trend": "growing" if len(project_sizes) > 1 and project_sizes[-1] > project_sizes[0] else "stable"
            },
            "raw_data": trends[-10:] if trends else []  # 最近10个数据点
        }

        return trend_analysis

    def generate_health_dashboard(self) -> Dict[str, Any]:
        """生成健康仪表板数据"""
        # 获取当前健康状态
        health_report, alerts = self.check_health()

        # 获取趋势数据
        trends = self.get_health_trends(7)  # 最近7天

        # 获取维护历史
        maintenance_history = self.logger.get_maintenance_history(7)

        # 统计警报类型
        alert_summary = {
            "total": len(alerts),
            "critical": len([a for a in alerts if a.severity == "critical"]),
            "warning": len([a for a in alerts if a.severity == "warning"]),
            "info": len([a for a in alerts if a.severity == "info"])
        }

        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "current_health": health_report,
            "alerts": [asdict(alert) for alert in alerts],
            "alert_summary": alert_summary,
            "trends": trends,
            "recent_maintenance": maintenance_history[:5],
            "thresholds": self.thresholds,
            "recommendations": self._generate_recommendations(alerts, health_report)
        }

        return dashboard

    def _generate_recommendations(self,
    alerts: List[HealthAlert],
    health_report: Dict[str,
    Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于警报生成建议
        for alert in alerts:
            if alert.alert_type == "root_files_count":
                recommendations.append("🗂️  运行 `python3 scripts/maintenance/directory_maintenance.py --auto-fix` 清理根目录")
                recommendations.append("📦 将散落的文件移动到适当的目录中")

            elif alert.alert_type == "health_score":
                recommendations.append("🔧 运行完整的维护流程 `python3 scripts/maintenance/directory_maintenance.py`")
                recommendations.append("📋 检查并修复命名规范问题")

            elif alert.alert_type == "empty_directories":
                recommendations.append("🧹 删除不必要的空目录")
                recommendations.append("📁 检查是否有未完成的功能模块")

            elif alert.alert_type == "naming_violations":
                recommendations.append("📝 运行命名规范检查 `python3 scripts/utils/naming_convention_checker.py`")
                recommendations.append("🔤 统一目录和文件的命名规范")

            elif alert.alert_type == "misplaced_files":
                recommendations.append("📋 将错误放置的文件移动到正确位置")
                recommendations.append("🔧 运行自动修复工具")

            elif alert.alert_type == "project_size":
                recommendations.append("📦 归档旧的报告和日志文件")
                recommendations.append("🗑️  清理不需要的大文件")

        # 基于健康评分生成通用建议
        if health_report["health_score"] < 80:
            recommendations.append("📊 定期运行健康检查和维护任务")
            recommendations.append("🤖 考虑设置定期维护任务 `python3 scripts/maintenance/scheduled_maintenance.py --daemon`")

        if not recommendations:
            recommendations.append("✅ 目录结构健康状况良好，继续保持！")
            recommendations.append("📈 建议定期运行健康检查以维持良好状态")

        return recommendations

    def run_monitoring(self, save_report: bool = True) -> Dict[str, Any]:
        """运行完整的健康监控"""
        print("🚀 开始目录健康监控...")

        # 执行健康检查
        health_report, alerts = self.check_health()

        # 保存监控报告
        report_file = None
        if save_report:
            report_file = self.save_monitoring_report(health_report, alerts)

        # 更新警报记录
        existing_alerts = self._load_alerts()
        all_alerts = alerts + existing_alerts

        # 保留最近30天的警报
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered_alerts = [
            alert for alert in all_alerts
            if datetime.fromisoformat(alert.timestamp) > cutoff_date
        ]

        self._save_alerts(filtered_alerts)

        # 生成结果摘要
        critical_count = len([a for a in alerts if a.severity == "critical"])
        warning_count = len([a for a in alerts if a.severity == "warning"])

        print(f"\n📊 健康监控完成!")
        print(f"🏥 当前健康评分: {health_report['health_score']}")
        print(f"🚨 严重警报: {critical_count} 个")
        print(f"⚠️  警告警报: {warning_count} 个")

        if critical_count > 0:
            print("📞 建议立即处理严重问题！")

        return {
            "health_report": health_report,
            "alerts": [asdict(alert) for alert in alerts],
            "report_file": str(report_file) if report_file else None,
            "timestamp": datetime.now().isoformat()
        }

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FootballPrediction 目录健康监控工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python3 health_monitor.py                        # 运行健康监控
  python3 health_monitor.py --trends              # 查看健康趋势
  python3 health_monitor.py --dashboard            # 生成健康仪表板
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
        "--dashboard",
        action="store_true",
        help="生成健康仪表板"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存监控报告"
    )

    args = parser.parse_args()

    # 创建健康监控器实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    monitor = HealthMonitor(project_root)

    try:
        if args.dashboard:
            # 生成健康仪表板
            dashboard = monitor.generate_health_dashboard()
            print("\n📊 健康仪表板:")
            print(json.dumps(dashboard, indent=2, ensure_ascii=False, default=str))

        elif args.trends:
            # 显示健康趋势
            trends = monitor.get_health_trends(30)
            print("\n📈 健康趋势分析:")
            print(json.dumps(trends, indent=2, ensure_ascii=False, default=str))

        else:
            # 运行健康监控
            results = monitor.run_monitoring(save_report=not args.no_save)

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

if __name__ == "__main__":
    main()