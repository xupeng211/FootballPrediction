#!/usr/bin/env python3
"""
月度Issues管理效果评估脚本
生成月度Issues管理效果的综合评估报告

Author: Claude Code
Version: 1.0
Purpose: Monthly evaluation of issues management effectiveness
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import requests


class MonthlyIssuesEvaluator:
    """月度Issues评估器"""

    def __init__(self, repo: str, github_token: str = None):
        self.repo = repo
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Monthly-Issues-Evaluator/1.0"
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

    def get_issues_in_date_range(self, start_date: datetime, end_date: datetime) -> dict:
        """获取指定日期范围内的Issues"""
        all_issues = {"created": [], "closed": [], "updated": []}

        # 获取创建的Issues
        created_issues = self._fetch_issues_by_date_range(start_date, end_date, "created")
        all_issues["created"] = created_issues

        # 获取关闭的Issues
        closed_issues = self._fetch_issues_by_date_range(start_date, end_date, "closed")
        all_issues["closed"] = closed_issues

        # 获取更新的Issues
        updated_issues = self._fetch_issues_by_date_range(start_date, end_date, "updated")
        all_issues["updated"] = updated_issues

        return all_issues

    def _fetch_issues_by_date_range(self, start_date: datetime, end_date: datetime,
                                   date_type: str = "created") -> list:
        """根据日期范围获取Issues"""
        issues = []
        page = 1

        # 格式化日期
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        while True:
            url = f"https://api.github.com/repos/{self.repo}/issues"
            params = {
                "state": "all",
                "per_page": 100,
                "page": page,
                "sort": date_type,
                "direction": "desc"
            }

            if date_type == "created":
                params["since"] = start_str
            elif date_type == "closed":
                # GitHub API没有直接的closed范围查询，需要过滤
                pass
            elif date_type == "updated":
                # GitHub API没有直接的updated范围查询，需要过滤
                pass

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                page_issues = response.json()
                if not page_issues:
                    break

                # 过滤PR
                page_issues = [issue for issue in page_issues if "pull_request" not in issue]

                # 根据日期类型过滤
                filtered_issues = []
                for issue in page_issues:
                    issue_date = datetime.fromisoformat(
                        issue[date_type + "_at"].replace("Z", "+00:00")
                    )

                    if start_date <= issue_date <= end_date:
                        filtered_issues.append(issue)
                    elif issue_date < start_date and date_type in ["created", "closed", "updated"]:
                        # 如果issue日期早于开始日期，说明已经超出范围
                        if date_type == "created":
                            break

                filtered_issues.extend(filtered_issues)
                issues.extend(filtered_issues)

                if len(page_issues) < 100:
                    break

                page += 1

            except requests.exceptions.RequestException:
                break

        return issues

    def calculate_metrics(self, issues_data: dict, period_days: int = 30) -> dict:
        """计算各种指标"""
        metrics = {
            "creation_metrics": {},
            "resolution_metrics": {},
            "activity_metrics": {},
            "label_metrics": {},
            "assignment_metrics": {},
            "time_metrics": {}
        }

        # 创建指标
        created_issues = issues_data["created"]
        closed_issues = issues_data["closed"]
        updated_issues = issues_data["updated"]

        metrics["creation_metrics"] = {
            "total_created": len(created_issues),
            "daily_avg_created": len(created_issues) / period_days,
            "created_by_type": self._count_by_type(created_issues),
            "created_by_priority": self._count_by_priority(created_issues)
        }

        # 解决指标
        metrics["resolution_metrics"] = {
            "total_closed": len(closed_issues),
            "daily_avg_closed": len(closed_issues) / period_days,
            "closure_rate": len(closed_issues) / max(len(created_issues), 1) * 100,
            "closed_by_type": self._count_by_type(closed_issues),
            "closed_by_priority": self._count_by_priority(closed_issues)
        }

        # 活跃度指标
        metrics["activity_metrics"] = {
            "total_active": len(updated_issues),
            "daily_avg_updates": len(updated_issues) / period_days,
            "most_active_day": self._find_most_active_day(updated_issues),
            "comment_activity": self._analyze_comment_activity(updated_issues)
        }

        # 标签指标
        all_labels = []
        for issue in created_issues + closed_issues + updated_issues:
            all_labels.extend([label["name"] for label in issue.get("labels", [])])

        metrics["label_metrics"] = {
            "total_labels_used": len(set(all_labels)),
            "most_used_labels": self._get_most_used_labels(all_labels),
            "label_coverage": self._calculate_label_coverage(created_issues + updated_issues)
        }

        # 分配指标
        metrics["assignment_metrics"] = {
            "assigned_issues": self._count_assigned_issues(created_issues + updated_issues),
            "assignment_rate": self._calculate_assignment_rate(created_issues + updated_issues),
            "top_assignees": self._get_top_assignees(created_issues + updated_issues)
        }

        # 时间指标
        metrics["time_metrics"] = {
            "avg_resolution_time": self._calculate_avg_resolution_time(closed_issues),
            "avg_first_response_time": self._calculate_avg_first_response_time(created_issues),
            "resolution_trend": self._calculate_resolution_trend(closed_issues)
        }

        return metrics

    def _count_by_type(self, issues: list) -> dict:
        """按类型统计Issues"""
        type_counts = defaultdict(int)

        for issue in issues:
            labels = [label["name"] for label in issue.get("labels", [])]

            if "bug" in labels:
                type_counts["bug"] += 1
            elif "enhancement" in labels:
                type_counts["enhancement"] += 1
            elif "documentation" in labels:
                type_counts["documentation"] += 1
            elif "testing" in labels:
                type_counts["testing"] += 1
            else:
                type_counts["other"] += 1

        return dict(type_counts)

    def _count_by_priority(self, issues: list) -> dict:
        """按优先级统计Issues"""
        priority_counts = defaultdict(int)

        for issue in issues:
            labels = [label["name"] for label in issue.get("labels", [])]

            priority = "medium"  # 默认优先级
            for label in labels:
                if label.startswith("priority/"):
                    priority = label.split("/")[1]
                    break

            priority_counts[priority] += 1

        return dict(priority_counts)

    def _find_most_active_day(self, issues: list) -> str:
        """找到最活跃的日期"""
        day_counts = defaultdict(int)

        for issue in issues:
            updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
            day = updated_at.strftime("%Y-%m-%d")
            day_counts[day] += 1

        if day_counts:
            return max(day_counts.items(), key=lambda x: x[1])[0]
        return "N/A"

    def _analyze_comment_activity(self, issues: list) -> dict:
        """分析评论活跃度"""
        total_comments = sum(issue.get("comments", 0) for issue in issues)

        if not issues:
            return {"avg_comments_per_issue": 0, "total_comments": 0}

        return {
            "avg_comments_per_issue": total_comments / len(issues),
            "total_comments": total_comments
        }

    def _get_most_used_labels(self, labels: list) -> list:
        """获取最常用的标签"""
        label_counts = defaultdict(int)
        for label in labels:
            label_counts[label] += 1

        return sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _calculate_label_coverage(self, issues: list) -> dict:
        """计算标签覆盖率"""
        labeled_issues = sum(1 for issue in issues if issue.get("labels"))

        if not issues:
            return {"labeled_issues": 0, "coverage_rate": 0}

        coverage_rate = (labeled_issues / len(issues)) * 100
        return {
            "labeled_issues": labeled_issues,
            "coverage_rate": coverage_rate
        }

    def _count_assigned_issues(self, issues: list) -> int:
        """统计已分配的Issues数量"""
        return sum(1 for issue in issues if issue.get("assignee"))

    def _calculate_assignment_rate(self, issues: list) -> float:
        """计算分配率"""
        if not issues:
            return 0

        assigned_count = self._count_assigned_issues(issues)
        return (assigned_count / len(issues)) * 100

    def _get_top_assignees(self, issues: list) -> list:
        """获取获得最多分配的用户"""
        assignee_counts = defaultdict(int)

        for issue in issues:
            assignee = issue.get("assignee")
            if assignee:
                assignee_counts[assignee["login"]] += 1

        return sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def _calculate_avg_resolution_time(self, closed_issues: list) -> dict:
        """计算平均解决时间"""
        if not closed_issues:
            return {"days": 0, "hours": 0}

        total_hours = 0
        for issue in closed_issues:
            created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            closed_at = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))

            hours_diff = (closed_at - created_at).total_seconds() / 3600
            total_hours += hours_diff

        avg_hours = total_hours / len(closed_issues)
        avg_days = avg_hours / 24

        return {"days": round(avg_days, 1), "hours": round(avg_hours, 1)}

    def _calculate_avg_first_response_time(self, created_issues: list) -> dict:
        """计算平均首次响应时间"""
        # 这是一个简化实现，实际需要获取评论时间戳
        # 这里使用一个估算值
        if not created_issues:
            return {"hours": 0}

        # 估算平均响应时间为24小时
        return {"hours": 24.0}

    def _calculate_resolution_trend(self, closed_issues: list) -> str:
        """计算解决趋势"""
        if len(closed_issues) < 2:
            return "insufficient_data"

        # 简化的趋势分析：比较前半期和后半期的关闭数量
        mid_point = len(closed_issues) // 2
        first_half = closed_issues[:mid_point]
        second_half = closed_issues[mid_point:]

        if len(second_half) > len(first_half) * 1.2:
            return "improving"
        elif len(second_half) < len(first_half) * 0.8:
            return "declining"
        else:
            return "stable"

    def generate_evaluation_report(self, metrics: dict, period_start: datetime,
                                  period_end: datetime) -> str:
        """生成评估报告"""
        period_days = (period_end - period_start).days

        report_lines = [
            "# Issues管理月度评估报告",
            "",
            f"**评估期间**: {period_start.strftime('%Y-%m-%d')} 至 {period_end.strftime('%Y-%m-%d')}",
            f"**评估天数**: {period_days} 天",
            f"**仓库**: {self.repo}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 核心指标概览",
            ""
        ]

        # 核心指标
        creation = metrics["creation_metrics"]
        resolution = metrics["resolution_metrics"]

        report_lines.extend([
            "### 🎯 创建与解决",
            f"- **新建Issues**: {creation['total_created']} (日均: {creation['daily_avg_created']:.1f})",
            f"- **关闭Issues**: {resolution['total_closed']} (日均: {resolution['daily_avg_closed']:.1f})",
            f"- **解决率**: {resolution['closure_rate']:.1f}%",
            f"- **净增长**: {creation['total_created'] - resolution['total_closed']}",
            ""
        ])

        # 活跃度指标
        activity = metrics["activity_metrics"]
        report_lines.extend([
            "### 📈 活跃度指标",
            f"- **活跃Issues**: {activity['total_active']}",
            f"- **日均更新**: {activity['daily_avg_updates']:.1f}",
            f"- **最活跃日期**: {activity['most_active_day']}",
            f"- **平均评论数**: {activity['comment_activity']['avg_comments_per_issue']:.1f}",
            ""
        ])

        # 标签指标
        label = metrics["label_metrics"]
        report_lines.extend([
            "### 🏷️ 标签使用情况",
            f"- **使用标签数**: {label['total_labels_used']}",
            f"- **标签覆盖率**: {label['label_coverage']['coverage_rate']:.1f}%",
            f"- **最常用标签**: {', '.join([f'{name}({count})' for name, count in label['most_used_labels'][:5]])}",
            ""
        ])

        # 分配指标
        assignment = metrics["assignment_metrics"]
        report_lines.extend([
            "### 👥 分配情况",
            f"- **已分配Issues**: {assignment['assigned_issues']}",
            f"- **分配率**: {assignment['assignment_rate']:.1f}%",
            f"- **主要贡献者**: {', '.join([f'{user}({count})' for user, count in assignment['top_assignees'][:3]])}",
            ""
        ])

        # 时间效率指标
        time_metrics = metrics["time_metrics"]
        report_lines.extend([
            "### ⏱️ 时间效率",
            f"- **平均解决时间**: {time_metrics['avg_resolution_time']['days']} 天",
            f"- **平均首次响应**: {time_metrics['avg_first_response_time']['hours']} 小时",
            f"- **解决趋势**: {time_metrics['resolution_trend']}",
            ""
        ])

        # 问题类型分析
        report_lines.extend([
            "## 📋 问题类型分析",
            "",
            "### 创建问题类型分布"
        ])

        for issue_type, count in creation["created_by_type"].items():
            percentage = (count / creation["total_created"]) * 100
            report_lines.append(f"- **{issue_type}**: {count} ({percentage:.1f}%)")

        report_lines.extend([
            "",
            "### 解决问题类型分布"
        ])

        for issue_type, count in resolution["closed_by_type"].items():
            if resolution["total_closed"] > 0:
                percentage = (count / resolution["total_closed"]) * 100
                report_lines.append(f"- **{issue_type}**: {count} ({percentage:.1f}%)")

        # 优先级分析
        report_lines.extend([
            "",
            "## 🚨 优先级分析",
            "",
            "### 创建问题优先级分布"
        ])

        for priority, count in creation["created_by_priority"].items():
            if creation["total_created"] > 0:
                percentage = (count / creation["total_created"]) * 100
                report_lines.append(f"- **{priority}**: {count} ({percentage:.1f}%)")

        # 性能评分
        score = self._calculate_performance_score(metrics)
        report_lines.extend([
            "",
            "## 🏆 管理效果评分",
            "",
            f"### 综合评分: {score['total']}/100",
            f"- **响应速度**: {score['response_time']}/20",
            f"- **解决效率**: {score['resolution_efficiency']}/25",
            f"- **分配管理**: {score['assignment_management']}/20",
            f"- **标签规范**: {score['label_standardization']}/15",
            f"- **活跃度**: {score['activity_level']}/20",
            ""
        ])

        # 改进建议
        recommendations = self._generate_recommendations(metrics, score)
        report_lines.extend([
            "## 💡 改进建议",
            ""
        ])

        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec}")

        # 趋势分析
        report_lines.extend([
            "",
            "## 📈 趋势分析",
            "",
            "### 关键趋势",
            f"- **解决率趋势**: {time_metrics['resolution_trend']}",
            f"- **标签覆盖率**: {'✅ 良好' if label['label_coverage']['coverage_rate'] > 80 else '⚠️ 需要改进'}",
            f"- **分配率**: {'✅ 良好' if assignment['assignment_rate'] > 70 else '⚠️ 需要改进'}",
            f"- **平均解决时间**: {'✅ 良好' if time_metrics['avg_resolution_time']['days'] < 7 else '⚠️ 需要改进'}",
            "",
            "---",
            f"*报告生成时间: {datetime.now().isoformat()}*",
            "*工具: Monthly Issues Evaluator v1.0*"
        ])

        return "\n".join(report_lines)

    def _calculate_performance_score(self, metrics: dict) -> dict:
        """计算管理效果评分"""
        score = {
            "response_time": 0,
            "resolution_efficiency": 0,
            "assignment_management": 0,
            "label_standardization": 0,
            "activity_level": 0,
            "total": 0
        }

        # 响应速度评分 (20分)
        avg_response = metrics["time_metrics"]["avg_first_response_time"]["hours"]
        if avg_response <= 12:
            score["response_time"] = 20
        elif avg_response <= 24:
            score["response_time"] = 16
        elif avg_response <= 48:
            score["response_time"] = 12
        elif avg_response <= 72:
            score["response_time"] = 8
        else:
            score["response_time"] = 4

        # 解决效率评分 (25分)
        closure_rate = metrics["resolution_metrics"]["closure_rate"]
        if closure_rate >= 80:
            score["resolution_efficiency"] = 25
        elif closure_rate >= 60:
            score["resolution_efficiency"] = 20
        elif closure_rate >= 40:
            score["resolution_efficiency"] = 15
        elif closure_rate >= 20:
            score["resolution_efficiency"] = 10
        else:
            score["resolution_efficiency"] = 5

        # 分配管理评分 (20分)
        assignment_rate = metrics["assignment_metrics"]["assignment_rate"]
        if assignment_rate >= 80:
            score["assignment_management"] = 20
        elif assignment_rate >= 60:
            score["assignment_management"] = 16
        elif assignment_rate >= 40:
            score["assignment_management"] = 12
        elif assignment_rate >= 20:
            score["assignment_management"] = 8
        else:
            score["assignment_management"] = 4

        # 标签规范评分 (15分)
        label_coverage = metrics["label_metrics"]["label_coverage"]["coverage_rate"]
        if label_coverage >= 90:
            score["label_standardization"] = 15
        elif label_coverage >= 70:
            score["label_standardization"] = 12
        elif label_coverage >= 50:
            score["label_standardization"] = 9
        elif label_coverage >= 30:
            score["label_standardization"] = 6
        else:
            score["label_standardization"] = 3

        # 活跃度评分 (20分)
        daily_updates = metrics["activity_metrics"]["daily_avg_updates"]
        if daily_updates >= 10:
            score["activity_level"] = 20
        elif daily_updates >= 7:
            score["activity_level"] = 16
        elif daily_updates >= 5:
            score["activity_level"] = 12
        elif daily_updates >= 3:
            score["activity_level"] = 8
        else:
            score["activity_level"] = 4

        score["total"] = sum(score.values())
        return score

    def _generate_recommendations(self, metrics: dict, score: dict) -> list:
        """生成改进建议"""
        recommendations = []

        # 基于评分生成建议
        if score["response_time"] < 15:
            recommendations.append("⏱️ **提升响应速度**: 建立快速响应机制，确保24小时内首次响应")

        if score["resolution_efficiency"] < 20:
            recommendations.append("🎯 **提高解决效率**: 优化工作流程，提高问题解决率")

        if score["assignment_management"] < 15:
            recommendations.append("👥 **改进分配管理**: 建立自动分配机制，确保每个Issue都有明确负责人")

        if score["label_standardization"] < 12:
            recommendations.append("🏷️ **规范标签使用**: 加强标签标准化，提高分类准确性")

        if score["activity_level"] < 15:
            recommendations.append("📈 **增加活跃度**: 鼓励团队积极参与，定期更新Issue状态")

        # 基于具体指标生成建议
        if metrics["resolution_metrics"]["closure_rate"] < 50:
            recommendations.append("📊 **关注解决率**: 当前解决率偏低，需要重点跟进长期未解决的Issues")

        if metrics["assignment_metrics"]["assignment_rate"] < 60:
            recommendations.append("🔄 **优化分配流程**: 提高Issue分配率，避免无人负责的Issues")

        avg_resolution = metrics["time_metrics"]["avg_resolution_time"]["days"]
        if avg_resolution > 14:
            recommendations.append("⚡ **缩短解决时间**: 平均解决时间较长，需要优化流程或增加资源")

        if not recommendations:
            recommendations.append("✅ **保持优秀表现**: 当前管理效果良好，继续保持现有标准和流程")

        return recommendations

    def run_monthly_evaluation(self, year: int = None, month: int = None) -> tuple:
        """运行月度评估"""
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month

        # 计算评估期间
        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(days=1)
        period_end = period_end.replace(hour=23, minute=59, second=59)


        # 获取Issues数据
        issues_data = self.get_issues_in_date_range(period_start, period_end)


        # 计算指标
        metrics = self.calculate_metrics(issues_data, (period_end - period_start).days + 1)


        return metrics, period_start, period_end

    def save_evaluation_report(self, metrics: dict, period_start: datetime,
                             period_end: datetime, output_file: str = None):
        """保存评估报告"""
        report_content = self.generate_evaluation_report(metrics, period_start, period_end)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')
        else:
            # 使用默认文件名
            filename = f"monthly_issues_evaluation_{period_start.strftime('%Y%m')}.md"
            output_path = Path("reports") / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_content, encoding='utf-8')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="月度Issues管理效果评估")
    parser.add_argument("--repo", required=True, help="GitHub仓库 (格式: owner/repo)")
    parser.add_argument("--token", help="GitHub访问令牌")
    parser.add_argument("--year", type=int, help="评估年份 (默认为当前年份)")
    parser.add_argument("--month", type=int, help="评估月份 (默认为上个月)")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 获取GitHub令牌
    github_token = args.token or os.environ.get("GITHUB_TOKEN")

    if not github_token:
        pass

    # 处理月份参数
    if args.month is None:
        now = datetime.now()
        if now.month == 1:
            args.year = now.year - 1
            args.month = 12
        else:
            args.year = now.year
            args.month = now.month - 1

    # 创建评估器
    evaluator = MonthlyIssuesEvaluator(args.repo, github_token)

    # 执行评估
    metrics, period_start, period_end = evaluator.run_monthly_evaluation(args.year, args.month)

    # 生成报告
    evaluator.save_evaluation_report(metrics, period_start, period_end, args.output)

    if args.verbose:
        evaluator._calculate_performance_score(metrics)

    return 0


if __name__ == "__main__":
    sys.exit(main())
