#!/usr/bin/env python3
"""
自动化质量监控体系
Automated Quality Monitoring System

建立持续的质量监控和报告系统
"""

import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomatedQualityMonitor:
    """自动化质量监控器"""

    def __init__(self):
        self.monitoring_data = {
            'start_time': datetime.now().isoformat(),
            'checkpoints': [],
            'alerts': [],
            'trends': []
        }

    def get_quality_metrics(self) -> Dict:
        """获取质量指标"""
        try:
            # 获取ruff统计
            result = subprocess.run(
                ['ruff', 'check', '--statistics'],
                capture_output=True,
                text=True,
                timeout=60
            )

            total_errors = 0
            error_types = {}

            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Found' in line and 'errors' in line:
                        match = line.match(r'Found (\d+) errors')
                        if match:
                            total_errors = int(match.group(1))
                    else:
                        # 解析错误类型统计
                        parts = line.split()
                        if len(parts) >= 2 and parts[0].isdigit():
                            count = int(parts[0])
                            error_code = parts[1]
                            error_types[error_code] = count

            # 获取文件统计
            file_count = 0
            try:
                result = subprocess.run(
                    ['find', 'src', '-name', '*.py', '-type', 'f'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.stdout:
                    file_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
except Exception:
                file_count = 0

            # 计算质量分数
            quality_score = max(0, 100 - (total_errors * 0.1))  # 简单的质量评分算法

            return {
                'timestamp': datetime.now().isoformat(),
                'total_errors': total_errors,
                'error_types': error_types,
                'file_count': file_count,
                'quality_score': round(quality_score, 2),
                'status': self.get_quality_status(total_errors, quality_score)
            }

        except Exception as e:
            logger.error(f"获取质量指标失败: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'total_errors': -1,
                'error_types': {},
                'file_count': 0,
                'quality_score': 0,
                'status': 'error'
            }

    def get_quality_status(self, error_count: int, quality_score: float) -> str:
        """获取质量状态"""
        if error_count == 0:
            return 'excellent'
        elif error_count < 100:
            return 'good'
        elif error_count < 500:
            return 'fair'
        elif error_count < 1000:
            return 'poor'
        else:
            return 'critical'

    def add_checkpoint(self, name: str) -> Dict:
        """添加质量检查点"""
        metrics = self.get_quality_metrics()
        checkpoint = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }
        self.monitoring_data['checkpoints'].append(checkpoint)
        return checkpoint

    def generate_quality_report(self) -> Dict:
        """生成质量报告"""
        current_metrics = self.get_quality_metrics()

        # 分析趋势
        if len(self.monitoring_data['checkpoints']) > 1:
            previous = self.monitoring_data['checkpoints'][-2]['metrics']
            current = current_metrics

            error_trend = current['total_errors'] - previous['total_errors']
            quality_trend = current['quality_score'] - previous['quality_score']

            trend_analysis = {
                'error_trend': error_trend,
                'quality_trend': quality_trend,
                'trend_direction': 'improving' if error_trend < 0 else 'degrading' if error_trend > 0 else 'stable'
            }
        else:
            trend_analysis = {
                'error_trend': 0,
                'quality_trend': 0,
                'trend_direction': 'no_data'
            }

        # 生成建议
        recommendations = self.generate_recommendations(current_metrics)

        report = {
            'report_timestamp': datetime.now().isoformat(),
            'current_metrics': current_metrics,
            'trend_analysis': trend_analysis,
            'recommendations': recommendations,
            'monitoring_summary': {
                'total_checkpoints': len(self.monitoring_data['checkpoints']),
                'monitoring_duration': self.calculate_monitoring_duration(),
                'alerts_count': len(self.monitoring_data['alerts'])
            },
            'quality_gate_status': self.check_quality_gate(current_metrics)
        }

        return report

    def generate_recommendations(self, metrics: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if metrics['total_errors'] > 1000:
            recommendations.append("🚨 错误数量过高，建议立即进行全面代码清理")
        elif metrics['total_errors'] > 500:
            recommendations.append("⚠️ 错误数量较多，建议制定系统化改进计划")
        elif metrics['total_errors'] > 100:
            recommendations.append("📋 错误数量适中，建议逐步改进代码质量")
        else:
            recommendations.append("✅ 代码质量良好，继续保持")

        # 针对特定错误类型的建议
        error_types = metrics.get('error_types', {})
        if 'E722' in error_types:
            recommendations.append(f"🔧 修复 {error_types['E722']} 个bare except错误")
        if 'F841' in error_types:
            recommendations.append(f"🔧 清理 {error_types['F841']} 个未使用变量")
        if 'invalid-syntax' in str(error_types):
            recommendations.append("🔧 修复语法错误，确保代码可执行")

        if metrics['quality_score'] < 80:
            recommendations.append("📈 建议建立持续质量监控流程")
        if metrics['quality_score'] < 60:
            recommendations.append("🚨 建议暂停新功能开发，专注质量改进")

        return recommendations

    def check_quality_gate(self, metrics: Dict) -> Dict:
        """检查质量门禁"""
        error_count = metrics['total_errors']
        quality_score = metrics['quality_score']

        if error_count == 0:
            status = 'excellent'
            color = 'green'
            message = '质量优秀，可以发布到生产环境'
        elif error_count < 100 and quality_score > 90:
            status = 'good'
            color = 'blue'
            message = '质量良好，适合持续集成'
        elif error_count < 500 and quality_score > 80:
            status = 'acceptable'
            color = 'yellow'
            message = '质量可接受，建议改进后发布'
        elif error_count < 1000 and quality_score > 70:
            status = 'warning'
            color = 'orange'
            message = '质量警告，需要优先处理错误'
        else:
            status = 'failed'
            color = 'red'
            message = '质量门禁失败，不建议发布'

        return {
            'status': status,
            'color': color,
            'message': message,
            'error_threshold': error_count,
            'quality_threshold': quality_score
        }

    def calculate_monitoring_duration(self) -> str:
        """计算监控持续时间"""
        if not self.monitoring_data['start_time']:
            return "0 seconds"

        start = datetime.fromisoformat(self.monitoring_data['start_time'])
        now = datetime.now()
        duration = now - start

        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60

        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        else:
            return f"{int(minutes)}m"

    def save_monitoring_data(self, filename: str = None):
        """保存监控数据"""
        if filename is None:
            filename = f"quality_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        file_path = Path(filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.monitoring_data, f, indent=2, ensure_ascii=False)

        logger.info(f"监控数据已保存到: {file_path}")
        return file_path

    def run_monitoring_cycle(self) -> Dict:
        """运行一次完整的监控周期"""
        logger.info("🔄 开始质量监控周期...")

        # 1. 添加检查点
        checkpoint = self.add_checkpoint("manual_check")
        logger.info(f"📊 质量检查点: {checkpoint['metrics']['total_errors']} 错误, 质量分数: {checkpoint['metrics']['quality_score']}")

        # 2. 生成报告
        report = self.generate_quality_report()
        logger.info(f"📋 质量状态: {report['quality_gate_status']['status']} - {report['quality_gate_status']['message']}")

        # 3. 保存数据
        self.save_monitoring_data()

        return report

def main():
    """主函数"""
    print("🔄 自动化质量监控体系")
    print("=" * 60)
    print("🎯 目标: 建立持续质量监控和报告")
    print("📊 策略: 实时监控 + 趋势分析 + 自动报告")
    print("=" * 60)

    monitor = AutomatedQualityMonitor()
    report = monitor.run_monitoring_cycle()

    print("\n📊 质量监控报告:")
    print(f"   监控时间: {report['report_timestamp']}")
    print(f"   当前错误数: {report['current_metrics']['total_errors']}")
    print(f"   质量分数: {report['current_metrics']['quality_score']}/100")
    print(f"   质量状态: {report['current_metrics']['status']}")

    print("\n📈 趋势分析:")
    print(f"   错误趋势: {report['trend_analysis']['error_trend']:+d}")
    print(f"   质量趋势: {report['trend_analysis']['quality_trend']:+.1f}")
    print(f"   趋势方向: {report['trend_analysis']['trend_direction']}")

    print("\n🚪 质量门禁:")
    gate = report['quality_gate_status']
    print(f"   状态: {gate['status']}")
    print(f"   消息: {gate['message']}")

    if report['recommendations']:
        print("\n💡 改进建议:")
        for rec in report['recommendations']:
            print(f"   {rec}")

    # 保存完整报告
    report_file = Path('quality_monitoring_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 质量监控报告已保存到: {report_file}")
    return report

if __name__ == '__main__':
    main()