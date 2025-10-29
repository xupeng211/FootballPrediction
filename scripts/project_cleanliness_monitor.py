#!/usr/bin/env python3
"""
项目清洁度监控脚本
监控项目根目录的清洁状态，提供改进建议
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class ProjectCleanlinessMonitor:
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.report_file = self.project_path / "monitoring-data" / "cleanliness_report.json"
        self.report_file.parent.mkdir(exist_ok=True)

        # 清洁度标准
        self.standards = {
            "max_root_files": 50,  # 根目录最大文件数
            "max_markdown_files": 20,  # 最大Markdown文件数
            "max_archive_size_mb": 100,  # 最大归档大小(MB)
            "required_dirs": ["src", "tests", "docs", "scripts", "config"],  # 必需的目录
            "forbidden_files": ["*.pyc", "__pycache__", ".DS_Store"],  # 不应存在的文件
        }

    def count_root_files(self) -> int:
        """计算根目录文件数量"""
        return len([f for f in self.project_path.iterdir() if f.is_file()])

    def count_markdown_files(self) -> int:
        """计算Markdown文件数量"""
        return len(list(self.project_path.glob("*.md")))

    def get_archive_size(self) -> float:
        """获取归档目录大小(MB)"""
        archive_dir = self.project_path / "archive"
        if not archive_dir.exists():
            return 0.0

        total_size = 0
        for file in archive_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size

        return total_size / (1024 * 1024)  # 转换为MB

    def check_required_directories(self) -> List[str]:
        """检查必需目录是否存在"""
        missing = []
        for dir_name in self.standards["required_dirs"]:
            if not (self.project_path / dir_name).exists():
                missing.append(dir_name)
        return missing

    def check_forbidden_files(self) -> List[str]:
        """检查不应存在的文件"""
        found = []
        for pattern in self.standards["forbidden_files"]:
            found.extend([str(f) for f in self.project_path.rglob(pattern)])
        return found

    def get_file_type_distribution(self) -> Dict[str, int]:
        """获取文件类型分布"""
        distribution = {}
        for file in self.project_path.iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                if not ext:
                    ext = "无扩展名"
                distribution[ext] = distribution.get(ext, 0) + 1
        return distribution

    def calculate_cleanliness_score(self) -> Tuple[int, List[str]]:
        """计算清洁度分数（0-100）"""
        score = 100
        issues = []

        # 检查根目录文件数
        root_files = self.count_root_files()
        if root_files > self.standards["max_root_files"]:
            penalty = min(20, (root_files - self.standards["max_root_files"]) // 2)
            score -= penalty
            issues.append(f"根目录文件过多 ({root_files} > {self.standards['max_root_files']})")

        # 检查Markdown文件数
        md_files = self.count_markdown_files()
        if md_files > self.standards["max_markdown_files"]:
            penalty = min(15, (md_files - self.standards["max_markdown_files"]) // 2)
            score -= penalty
            issues.append(f"Markdown文件过多 ({md_files} > {self.standards['max_markdown_files']})")

        # 检查归档大小
        archive_size = self.get_archive_size()
        if archive_size > self.standards["max_archive_size_mb"]:
            penalty = min(10, int((archive_size - self.standards["max_archive_size_mb"]) / 10))
            score -= penalty
            issues.append(
                f"归档文件过大 ({archive_size:.1f}MB > {self.standards['max_archive_size_mb']}MB)"
            )

        # 检查必需目录
        missing_dirs = self.check_required_directories()
        if missing_dirs:
            score -= 5 * len(missing_dirs)
            issues.append(f"缺少必需目录: {', '.join(missing_dirs)}")

        # 检查禁止文件
        forbidden = self.check_forbidden_files()
        if forbidden:
            score -= min(10, len(forbidden) * 2)
            issues.append(f"发现不应存在的文件: {len(forbidden)}个")

        return max(0, score), issues

    def generate_report(self) -> Dict:
        """生成清洁度报告"""
        score, issues = self.calculate_cleanliness_score()

        report = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "cleanliness_score": score,
            "grade": self.get_grade(score),
            "metrics": {
                "root_files": self.count_root_files(),
                "markdown_files": self.count_markdown_files(),
                "archive_size_mb": round(self.get_archive_size(), 2),
                "file_distribution": self.get_file_type_distribution(),
                "missing_directories": self.check_required_directories(),
                "forbidden_files": len(self.check_forbidden_files()),
            },
            "issues": issues,
            "recommendations": self.get_recommendations(score, issues),
        }

        return report

    def get_grade(self, score: int) -> str:
        """获取清洁度等级"""
        if score >= 90:
            return "A+ (优秀)"
        elif score >= 80:
            return "A (良好)"
        elif score >= 70:
            return "B (一般)"
        elif score >= 60:
            return "C (需要改进)"
        else:
            return "D (急需清理)"

    def get_recommendations(self, score: int, issues: List[str]) -> List[str]:
        """获取改进建议"""
        recommendations = []

        if score < 70:
            recommendations.append("建议立即运行 ./scripts/weekly_cleanup.sh 进行清理")

        if any("Markdown文件" in issue for issue in issues):
            recommendations.append("考虑将临时报告移动到 archive/ 目录")

        if any("归档文件过大" in issue for issue in issues):
            recommendations.append("考虑清理旧的归档文件或移动到外部存储")

        if any("根目录文件" in issue for issue in issues):
            recommendations.append("将不必要的文件移动到合适的子目录")

        if score < 60:
            recommendations.append("考虑运行 ./scripts/monthly_cleanup.sh 进行深度清理")

        return recommendations

    def save_report(self, report: Dict):
        """保存报告到文件"""
        # 读取历史报告
        history = []
        if self.report_file.exists():
            try:
                with open(self.report_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
except Exception:
                history = []

        # 添加新报告
        history.append(report)

        # 只保留最近30条记录
        history = history[-30:]

        # 保存报告
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def print_report(self, report: Dict):
        """打印报告"""
        print("📊 项目清洁度监控报告")
        print("=" * 50)
        print(f"📅 检查时间: {report['timestamp']}")
        print(f"🎯 清洁度分数: {report['cleanliness_score']}/100 ({report['grade']})")
        print()

        print("📈 关键指标:")
        for key, value in report["metrics"].items():
            if key == "file_distribution":
                print("  文件类型分布:")
                for ext, count in value.items():
                    print(f"    {ext}: {count} 个")
            else:
                print(f"  {key}: {value}")

        print()
        if report["issues"]:
            print("⚠️  发现的问题:")
            for issue in report["issues"]:
                print(f"  • {issue}")
        else:
            print("✅ 未发现问题")

        print()
        if report["recommendations"]:
            print("💡 改进建议:")
            for rec in report["recommendations"]:
                print(f"  • {rec}")


def main():
    """主函数"""
    monitor = ProjectCleanlinessMonitor()

    print("🔍 正在分析项目清洁度...")

    # 生成报告
    report = monitor.generate_report()

    # 打印报告
    monitor.print_report(report)

    # 保存报告
    monitor.save_report(report)

    print(f"\n📋 报告已保存到: {monitor.report_file}")

    # 如果分数较低，建议立即清理
    if report["cleanliness_score"] < 70:
        print("\n🚨 项目清洁度较低，建议立即执行清理！")
        print("   运行: ./scripts/weekly_cleanup.sh")


if __name__ == "__main__":
    main()
