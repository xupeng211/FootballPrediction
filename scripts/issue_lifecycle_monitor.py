#!/usr/bin/env python3
"""
GitHub Issue生命周期监控工具
GitHub Issue Lifecycle Monitor

监控和分析Issue的生命周期数据
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class IssueLifecycleMonitor:
    """Issue生命周期监控器"""

    def __init__(self, repo: str):
        self.repo = repo

    def run_command(self, command: str) -> dict[str, Any]:
        """运行shell命令并返回结果"""
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                "success": True,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "stdout": e.stdout.strip() if e.stdout else "",
                "stderr": e.stderr.strip() if e.stderr else str(e)
            }

    def get_all_issues(self) -> list[dict[str, Any]]:
        """获取所有Issues（包括已关闭的）"""
        # 获取开放Issues
        open_cmd = f"gh issue list --repo {self.repo} --state open --limit 100 --json number,title,labels,state,createdAt,updatedAt,closedAt,author,assignees"
        open_result = self.run_command(open_cmd)

        # 获取已关闭Issues
        closed_cmd = f"gh issue list --repo {self.repo} --state closed --limit 100 --json number,title,labels,state,createdAt,updatedAt,closedAt,author,assignees"
        closed_result = self.run_command(closed_cmd)

        issues = []

        if open_result["success"]:
            try:
                issues.extend(json.loads(open_result["stdout"]))
            except json.JSONDecodeError:
                pass

        if closed_result["success"]:
            try:
                issues.extend(json.loads(closed_result["stdout"]))
            except json.JSONDecodeError:
                pass

        return issues

    def parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(date_str)
            return dt.replace(tzinfo=None)
        except (ValueError, AttributeError):
            return None

    def calculate_lifecycle_metrics(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        """计算生命周期指标"""
        now = datetime.now()
        metrics = {
            "total_issues": len(issues),
            "open_issues": 0,
            "closed_issues": 0,
            "average_lifetime_days": 0,
            "lifespan_distribution": {
                "less_than_1_day": 0,
                "1_to_7_days": 0,
                "1_to_4_weeks": 0,
                "1_to_3_months": 0,
                "more_than_3_months": 0
            },
            "stale_issues": 0,
            "very_stale_issues": 0,
            "issues_without_priority": 0,
            "unassigned_issues": 0,
            "label_usage": {}
        }

        lifespans = []

        for issue in issues:
            # 统计开放/关闭状态
            if issue["state"] == "open":
                metrics["open_issues"] += 1
            else:
                metrics["closed_issues"] += 1

            # 计算生命周期
            created_at = self.parse_date(issue["createdAt"])
            closed_at = self.parse_date(issue["closedAt"]) or now

            if created_at:
                lifespan = (closed_at - created_at).days
                lifespans.append(lifespan)

                # 生命周期分布
                if lifespan < 1:
                    metrics["lifespan_distribution"]["less_than_1_day"] += 1
                elif lifespan <= 7:
                    metrics["lifespan_distribution"]["1_to_7_days"] += 1
                elif lifespan <= 30:
                    metrics["lifespan_distribution"]["1_to_4_weeks"] += 1
                elif lifespan <= 90:
                    metrics["lifespan_distribution"]["1_to_3_months"] += 1
                else:
                    metrics["lifespan_distribution"]["more_than_3_months"] += 1

            # 检查过期Issues（仅开放Issues）
            if issue["state"] == "open":
                updated_at = self.parse_date(issue["updatedAt"])
                if updated_at:
                    days_since_update = (now - updated_at).days
                    if days_since_update > 60:
                        metrics["stale_issues"] += 1
                    if days_since_update > 180:
                        metrics["very_stale_issues"] += 1

            # 检查优先级标签
            has_priority = any(
                label["name"].startswith("priority/")
                for label in issue.get("labels", [])
            )
            if not has_priority:
                metrics["issues_without_priority"] += 1

            # 检查分配状态
            if not issue.get("assignees"):
                metrics["unassigned_issues"] += 1

            # 统计标签使用
            for label in issue.get("labels", []):
                label_name = label["name"]
                metrics["label_usage"][label_name] = metrics["label_usage"].get(label_name, 0) + 1

        # 计算平均生命周期
        if lifespans:
            metrics["average_lifetime_days"] = sum(lifespans) / len(lifespans)

        return metrics

    def generate_lifecycle_dashboard(self, metrics: dict[str, Any]) -> str:
        """生成生命周期仪表板"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        dashboard = f"""# GitHub Issue生命周期监控仪表板

**监控时间**: {now}
**仓库**: {self.repo}

## 📊 核心指标

### Issue状态分布
- **总Issues数**: {metrics["total_issues"]}
- **开放Issues**: {metrics["open_issues"]} ({metrics["open_issues"]/metrics["total_issues"]*100:.1f}%)
- **已关闭Issues**: {metrics["closed_issues"]} ({metrics["closed_issues"]/metrics["total_issues"]*100:.1f}%)

### 生命周期指标
- **平均生命周期**: {metrics["average_lifetime_days"]:.1f} 天
- **过期Issues (>60天)**: {metrics["stale_issues"]}
- **严重过期Issues (>180天)**: {metrics["very_stale_issues"]}

### 质量指标
- **缺少优先级标签**: {metrics["issues_without_priority"]} ({metrics["issues_without_priority"]/metrics["total_issues"]*100:.1f}%)
- **未分配Issues**: {metrics["unassigned_issues"]} ({metrics["unassigned_issues"]/metrics["total_issues"]*100:.1f}%)

## 📈 生命周期分布

| 生命周期范围 | 数量 | 占比 |
|-------------|------|------|
| < 1天 | {metrics["lifespan_distribution"]["less_than_1_day"]} | {metrics["lifespan_distribution"]["less_than_1_day"]/metrics["total_issues"]*100:.1f}% |
| 1-7天 | {metrics["lifespan_distribution"]["1_to_7_days"]} | {metrics["lifespan_distribution"]["1_to_7_days"]/metrics["total_issues"]*100:.1f}% |
| 1-4周 | {metrics["lifespan_distribution"]["1_to_4_weeks"]} | {metrics["lifespan_distribution"]["1_to_4_weeks"]/metrics["total_issues"]*100:.1f}% |
| 1-3个月 | {metrics["lifespan_distribution"]["1_to_3_months"]} | {metrics["lifespan_distribution"]["1_to_3_months"]/metrics["total_issues"]*100:.1f}% |
| > 3个月 | {metrics["lifespan_distribution"]["more_than_3_months"]} | {metrics["lifespan_distribution"]["more_than_3_months"]/metrics["total_issues"]*100:.1f}% |

## 🏷️ 标签使用统计

### 最常用标签 (前15个)
"""

        # 添加标签使用统计
        sorted_labels = sorted(metrics["label_usage"].items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:15]:
            percentage = (count / metrics["total_issues"]) * 100
            dashboard += f"- **{label}**: {count}次 ({percentage:.1f}%)\n"

        dashboard += """

## 🎯 健康度评估

### 🟢 良好指标
"""

        # 添加健康度评估
        if metrics["stale_issues"] < metrics["total_issues"] * 0.1:
            dashboard += f"- ✅ 过期Issues控制在10%以内 ({metrics['stale_issues']}个)\n"

        if metrics["issues_without_priority"] < metrics["total_issues"] * 0.2:
            dashboard += "- ✅ 大部分Issues有优先级标签\n"

        if metrics["average_lifetime_days"] < 30:
            dashboard += f"- ✅ 平均生命周期较短 ({metrics['average_lifetime_days']:.1f}天)\n"

        dashboard += "\n### 🟡 需要关注\n"

        if metrics["stale_issues"] > 0:
            dashboard += f"- ⚠️ 有 {metrics['stale_issues']} 个过期Issues需要处理\n"

        if metrics['issues_without_priority'] > metrics['total_issues'] * 0.3:
            dashboard += "- ⚠️ 超过30%的Issues缺少优先级标签\n"

        if metrics['unassigned_issues'] > metrics['total_issues'] * 0.5:
            dashboard += "- ⚠️ 超过50%的Issues未分配负责人\n"

        dashboard += "\n### 🔴 严重问题\n"

        if metrics["very_stale_issues"] > 0:
            dashboard += f"- 🚨 有 {metrics['very_stale_issues']} 个严重过期Issues (>180天)\n"

        if metrics["average_lifetime_days"] > 90:
            dashboard += f"- 🚨 平均生命周期过长 ({metrics['average_lifetime_days']:.1f}天)\n"

        dashboard += """

## 💡 改进建议

### 立即执行
"""

        if metrics["very_stale_issues"] > 0:
            dashboard += "1. **处理严重过期Issues**: 立即审查和更新超过180天未更新的Issues\n"

        if metrics["unassigned_issues"] > 0:
            dashboard += "2. **分配Issue负责人**: 为未分配的Issues指定维护者\n"

        if metrics["issues_without_priority"] > 0:
            dashboard += "3. **完善优先级标签**: 为缺少优先级的Issues添加标签\n"

        dashboard += """
### 流程改进
1. **定期审查**: 建立每周Issue状态审查机制
2. **自动提醒**: 设置过期Issue自动提醒
3. **标签规范化**: 统一标签使用标准
4. **生命周期监控**: 持续监控Issue处理效率

---

*仪表板由自动化系统生成 | 更新频率: 每周*
"""

        return dashboard

    def run_monitoring(self) -> dict[str, Any]:
        """执行监控"""

        # 获取所有Issues
        issues = self.get_all_issues()
        if not issues:
            return {"success": False}


        # 计算指标
        metrics = self.calculate_lifecycle_metrics(issues)

        # 生成仪表板
        dashboard = self.generate_lifecycle_dashboard(metrics)

        # 保存报告
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        dashboard_path = reports_dir / "issue_lifecycle_dashboard.md"
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard)


        # 输出关键指标

        return {
            "success": True,
            "metrics": metrics,
            "dashboard_path": str(dashboard_path)
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GitHub Issue生命周期监控")
    parser.add_argument("--repo", default="xupeng211/FootballPrediction", help="仓库名称")

    args = parser.parse_args()

    monitor = IssueLifecycleMonitor(args.repo)
    results = monitor.run_monitoring()

    if not results["success"]:
        exit(1)


if __name__ == "__main__":
    main()
