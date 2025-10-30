#!/usr/bin/env python3
"""
持续质量监控系统
Phase G Week 2 - 建立自动化质量监控
"""

import ast
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class ContinuousQualityMonitor:
    def __init__(self):
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_files": 0,
            "syntax_healthy_files": 0,
            "syntax_broken_files": 0,
            "syntax_health_percentage": 0.0,
            "modules_status": {},
            "recommendations": []
        }

    def check_file_syntax(self, file_path: str) -> bool:
        """检查单个文件的语法健康度"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return True
        except Exception:
            return False

    def analyze_directory(self, directory: str) -> Dict:
        """分析目录的语法健康度"""
        python_files = list(Path(directory).rglob("*.py"))

        self.metrics["total_files"] = len(python_files)
        healthy_files = 0

        for file_path in python_files:
            if self.check_file_syntax(str(file_path)):
                healthy_files += 1

        self.metrics["syntax_healthy_files"] = healthy_files
        self.metrics["syntax_broken_files"] = len(python_files) - healthy_files

        if self.metrics["total_files"] > 0:
            self.metrics["syntax_health_percentage"] = (healthy_files / len(python_files)) * 100

        return self.metrics

    def generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        health_pct = self.metrics["syntax_health_percentage"]

        if health_pct >= 90:
            recommendations.append("🎉 优秀！语法健康度超过90%，项目处于非常健康的状态")
        elif health_pct >= 80:
            recommendations.append("👍 良好！语法健康度超过80%，继续维护现有质量")
        elif health_pct >= 70:
            recommendations.append("⚠️ 需要关注！语法健康度70-80%，建议重点修复语法错误")
        elif health_pct >= 50:
            recommendations.append("🚨 需要行动！语法健康度50-70%，需要系统性语法修复")
        else:
            recommendations.append("🆘 紧急！语法健康度低于50%，需要立即开展语法修复行动")

        # 基于损坏文件数量的建议
        broken_files = self.metrics["syntax_broken_files"]
        if broken_files > 100:
            recommendations.append(f"📊 建议：{broken_files}个文件需要修复，建议使用批量修复工具")
        elif broken_files > 50:
            recommendations.append(f"📊 建议：{broken_files}个文件需要修复，可以分批处理")
        elif broken_files > 0:
            recommendations.append(f"📊 建议：{broken_files}个文件需要修复，建议手动处理关键文件")

        # Phase G工具建议
        if health_pct < 85:
            recommendations.append("🔧 建议：运行 Phase G Week 2 语法修复工具")
            recommendations.append("🔧 建议：优先修复核心业务模块（api/, domain/, services/）")

        return recommendations

    def save_report(self, output_path: str = None) -> str:
        """保存质量报告"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"continuous_quality_report_{timestamp}.json"

        self.metrics["recommendations"] = self.generate_recommendations()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

        return output_path

    def print_summary(self) -> None:
        """打印质量摘要"""
        print("=" * 60)
        print("📊 持续质量监控报告")
        print("=" * 60)
        print(f"📅 检测时间: {self.metrics['timestamp']}")
        print(f"📁 总文件数: {self.metrics['total_files']}")
        print(f"✅ 语法健康: {self.metrics['syntax_healthy_files']}")
        print(f"❌ 语法错误: {self.metrics['syntax_broken_files']}")
        print(f"📈 健康度: {self.metrics['syntax_health_percentage']:.1f}%")

        print("\n🎯 改进建议:")
        for rec in self.generate_recommendations():
            print(f"   {rec}")

        print("=" * 60)

def main():
    import sys

    monitor = ContinuousQualityMonitor()

    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "src"  # 默认监控src目录

    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return

    print(f"🔍 开始持续质量监控...")
    print(f"📁 监控目录: {directory}")

    # 分析质量
    metrics = monitor.analyze_directory(directory)

    # 打印摘要
    monitor.print_summary()

    # 保存报告
    report_path = monitor.save_report()
    print(f"\n📄 详细报告已保存: {report_path}")

    # 返回退出码
    if metrics["syntax_health_percentage"] >= 80:
        print("✅ 质量检查通过")
        sys.exit(0)
    else:
        print("⚠️ 质量需要改进")
        sys.exit(1)

if __name__ == "__main__":
    main()