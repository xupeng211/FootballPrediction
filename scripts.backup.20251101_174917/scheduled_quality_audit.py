#!/usr/bin/env python3
"""
定期质量审计调度器
支持每周、每月的质量检查自动化
"""

import subprocess
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


class ScheduledQualityAuditor:
    """定期质量审计调度器"""

    def __init__(self, project_root: str = "/home/user/projects/FootballPrediction"):
        self.project_root = Path(project_root)
        self.reports_dir = self.project_root / "reports" / "quality"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.reports_dir / "audit_history.json"

    def load_audit_history(self) -> Dict[str, Any]:
        """加载审计历史"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  加载历史记录失败: {e}")
                return {"audits": []}
        return {"audits": []}

    def save_audit_history(self, history: Dict[str, Any]) -> None:
        """保存审计历史"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存历史记录失败: {e}")

    def run_quick_audit(self) -> Dict[str, Any]:
        """运行快速审计"""
        print("🔍 执行快速质量审计...")

        try:
            result = subprocess.run(
                ["python", "scripts/quick_quality_check.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            # 解析输出结果
            output_lines = result.stdout.split("\n")
            total_score = None
            grade = None
            mypy_errors = None

            for line in output_lines:
                if "总体评分:" in line:
                    # 提取 "40.0/100 (D级)" 格式
                    match = re.search(r"(\d+\.\d+)/100 \((\w+)级\)", line)
                    if match:
                        total_score = float(match.group(1))
                        grade = match.group(2)
                elif "发现" in line and "个类型错误" in line:
                    match = re.search(r"发现 (\d+) 个类型错误", line)
                    if match:
                        mypy_errors = int(match.group(1))

            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "quick",
                "success": result.returncode == 0,
                "total_score": total_score,
                "grade": grade,
                "mypy_errors": mypy_errors,
                "output": result.stdout,
                "duration": "quick",
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "quick",
                "success": False,
                "error": str(e),
                "duration": "quick",
            }

    def run_detailed_audit(self) -> Dict[str, Any]:
        """运行详细审计"""
        print("🔍 执行详细质量审计...")

        try:
            result = subprocess.run(
                ["python", "scripts/quality_audit.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )

            # 查找最新报告文件
            report_files = list(self.reports_dir.glob("quality_audit_*.json"))
            if report_files:
                latest_report = max(report_files, key=lambda x: x.stat().st_mtime)

                try:
                    with open(latest_report, "r", encoding="utf-8") as f:
                        report_data = json.load(f)

                    return {
                        "timestamp": datetime.now().isoformat(),
                        "audit_type": "detailed",
                        "success": result.returncode == 0,
                        "report_file": str(latest_report),
                        "quality_score": report_data.get("quality_score", {}),
                        "analysis_results": report_data,
                        "duration": "detailed",
                    }
                except Exception as e:
                    print(f"⚠️  读取报告文件失败: {e}")

            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "detailed",
                "success": False,
                "error": "No report file generated",
                "duration": "detailed",
            }
        except subprocess.TimeoutExpired:
            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "detailed",
                "success": False,
                "error": "Audit timed out after 5 minutes",
                "duration": "detailed",
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "detailed",
                "success": False,
                "error": str(e),
                "duration": "detailed",
            }

    def run_mypy_analysis(self) -> Dict[str, Any]:
        """运行MyPy深度分析"""
        print("🔍 执行MyPy深度分析...")

        try:
            result = subprocess.run(
                ["python", "scripts/analyze_mypy_progress.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            # 查找最新分析报告
            analysis_files = list(self.reports_dir.glob("mypy_analysis_*.json"))
            if analysis_files:
                latest_analysis = max(analysis_files, key=lambda x: x.stat().st_mtime)

                try:
                    with open(latest_analysis, "r", encoding="utf-8") as f:
                        analysis_data = json.load(f)

                    return {
                        "timestamp": datetime.now().isoformat(),
                        "audit_type": "mypy_analysis",
                        "success": result.returncode == 0,
                        "analysis_file": str(latest_analysis),
                        "total_errors": analysis_data.get("total_errors", 0),
                        "errors_by_file": analysis_data.get("errors_by_file", {}),
                        "error_types": analysis_data.get("error_types", {}),
                        "duration": "mypy_analysis",
                    }
                except Exception as e:
                    print(f"⚠️  读取分析文件失败: {e}")

            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "mypy_analysis",
                "success": False,
                "error": "No analysis file generated",
                "duration": "mypy_analysis",
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "audit_type": "mypy_analysis",
                "success": False,
                "error": str(e),
                "duration": "mypy_analysis",
            }

    def schedule_weekly_audit(self) -> Dict[str, Any]:
        """安排每周审计"""
        print("📅 执行每周质量审计...")
        print("=" * 50)

        # 执行多种审计
        results = {"schedule_type": "weekly", "timestamp": datetime.now().isoformat(), "audits": []}

        # 快速审计
        quick_result = self.run_quick_audit()
        results["audits"].append(quick_result)

        # MyPy分析
        mypy_result = self.run_mypy_analysis()
        results["audits"].append(mypy_result)

        # 生成周报摘要
        results["summary"] = self.generate_weekly_summary(results["audits"])

        # 保存到历史记录
        history = self.load_audit_history()
        history["audits"].append(results)
        self.save_audit_history(history)

        return results

    def generate_weekly_summary(self, audits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成周报摘要"""
        summary = {
            "week_number": datetime.now().isocalendar()[1],
            "year": datetime.now().year,
            "key_metrics": {},
            "trends": {},
            "recommendations": [],
        }

        # 提取关键指标
        for audit in audits:
            if audit["audit_type"] == "quick" and audit["success"]:
                summary["key_metrics"]["quality_score"] = audit.get("total_score")
                summary["key_metrics"]["quality_grade"] = audit.get("grade")
                summary["key_metrics"]["mypy_errors"] = audit.get("mypy_errors")

            elif audit["audit_type"] == "mypy_analysis" and audit["success"]:
                summary["key_metrics"]["total_files_with_errors"] = len(
                    audit.get("errors_by_file", {})
                )
                summary["key_metrics"]["error_types_count"] = len(audit.get("error_types", {}))

        # 生成建议
        score = summary["key_metrics"].get("quality_score", 0)
        errors = summary["key_metrics"].get("mypy_errors", 0)

        if score < 30:
            summary["recommendations"].append("质量评分较低，需要加强类型安全改进")
        if errors > 1500:
            summary["recommendations"].append("类型错误较多，建议增加修复频率")
        elif errors > 1000:
            summary["recommendations"].append("继续当前的小批量修复策略")
        elif errors < 500:
            summary["recommendations"].append("类型错误控制在良好范围内")

        return summary

    def check_audit_schedule(self) -> Optional[str]:
        """检查是否需要运行审计"""
        history = self.load_audit_history()
        audits = history.get("audits", [])

        if not audits:
            return "需要初始化审计"

        # 检查最后一次审计时间
        last_audit = max(audits, key=lambda x: x.get("timestamp", ""))
        try:
            last_time = datetime.fromisoformat(last_audit["timestamp"].replace("Z", "+00:00"))
            time_diff = datetime.now() - last_time

            if time_diff.days >= 7:
                return f"距离上次审计已过{time_diff.days}天，建议运行周审计"
            elif time_diff.days >= 1:
                return f"距离上次审计已过{time_diff.days}天，可以考虑运行快速检查"
            else:
                return "近期已审计，无需重复运行"
    def run_scheduled_audit(self, audit_type: str = "weekly") -> Dict[str, Any]:
        """运行定期审计"""
        print(f"🚀 启动{audit_type}质量审计...")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if audit_type == "weekly":
            return self.schedule_weekly_audit()
        elif audit_type == "quick":
            return {"audits": [self.run_quick_audit()]}
        elif audit_type == "detailed":
            return {"audits": [self.run_detailed_audit()]}
        elif audit_type == "mypy":
            return {"audits": [self.run_mypy_analysis()]}
        else:
            raise ValueError(f"不支持的审计类型: {audit_type}")


def main():
    """主函数"""
    import argparse
    import re

    parser = argparse.ArgumentParser(description="定期质量审计调度器")
    parser.add_argument(
        "--type", choices=["weekly", "quick", "detailed", "mypy"], default="weekly", help="审计类型"
    )
    parser.add_argument("--check-schedule", action="store_true", help="检查审计计划")
    parser.add_argument("--show-history", action="store_true", help="显示审计历史")

    args = parser.parse_args()

    auditor = ScheduledQualityAuditor()

    if args.check_schedule:
        status = auditor.check_audit_schedule()
        print(f"📅 审计计划检查: {status}")
        return

    if args.show_history:
        history = auditor.load_audit_history()
        audits = history.get("audits", [])

        if not audits:
            print("📝 暂无审计历史记录")
        else:
            print(f"📝 审计历史记录 (共{len(audits)}次):")
            print("-" * 60)
            for i, audit in enumerate(reversed(audits[-5:]), 1):  # 显示最近5次
                timestamp = audit.get("timestamp", "Unknown")
                schedule_type = audit.get("schedule_type", audit.get("audit_type", "Unknown"))
                print(f"{i:2d}. {timestamp[:19]}  {schedule_type}")
        return

    # 运行审计
    try:
        results = auditor.run_scheduled_audit(args.type)

        print("=" * 50)
        print("📊 审计结果摘要:")

        for i, audit in enumerate(results.get("audits", []), 1):
            audit_type = audit.get("audit_type", "Unknown")
            success = audit.get("success", False)

            if success:
                print(f"✅ {i}. {audit_type}: 成功")

                if audit_type == "quick":
                    score = audit.get("total_score")
                    grade = audit.get("grade")
                    errors = audit.get("mypy_errors")
                    print(f"   评分: {score}/100 ({grade}级), 错误: {errors}个")

                elif audit_type == "mypy_analysis":
                    errors = audit.get("total_errors", 0)
                    files = len(audit.get("errors_by_file", {}))
                    print(f"   类型错误: {errors}个, 涉及文件: {files}个")

            else:
                print(f"❌ {i}. {audit_type}: 失败")
                error = audit.get("error", "Unknown error")
                print(f"   错误: {error}")

        # 显示摘要
        if "summary" in results:
            summary = results["summary"]
            print("\n📈 周报摘要:")
            print(f"   • 周数: {summary.get('week_number', 'N/A')}")
            print(f"   • 质量评分: {summary['key_metrics'].get('quality_score', 'N/A')}/100")
            print(f"   • 质量等级: {summary['key_metrics'].get('quality_grade', 'N/A')}")
            print(f"   • 类型错误: {summary['key_metrics'].get('mypy_errors', 'N/A')}个")

            recommendations = summary.get("recommendations", [])
            if recommendations:
                print("   • 建议:")
                for rec in recommendations:
                    print(f"     - {rec}")

        print(f"\n🎯 审计完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"❌ 审计执行失败: {e}")


if __name__ == "__main__":
    main()
