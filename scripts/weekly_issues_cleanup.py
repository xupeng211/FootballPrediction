#!/usr/bin/env python3
"""
每周GitHub Issues定期清理工具
Weekly GitHub Issues Cleanup Tool

用于每周自动检查和清理GitHub Issues，保持项目管理健康状态。
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import argparse
import os


class WeeklyIssuesCleanup:
    """每周Issues清理管理器"""

    def __init__(self, repo: str = "xupeng211/FootballPrediction"):
        self.repo = repo
        self.weekly_report = {
            "cleanup_date": datetime.now().isoformat(),
            "week_number": datetime.now().isocalendar()[1],
            "issues_analyzed": 0,
            "actions_taken": [],
            "recommendations": [],
            "health_score": 0
        }

    def run_gh_command(self, command: str) -> Dict[str, Any]:
        """运行GitHub CLI命令"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {"success": True, "output": result.stdout, "error": result.stderr}
            else:
                return {"success": False, "output": result.stdout, "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_issues_summary(self) -> Dict[str, Any]:
        """获取Issues概要信息"""
        print("📊 获取Issues概要信息...")

        # 获取开放Issues
        open_command = f"gh issue list --repo {self.repo} --limit 100 --state open --json number,title,labels,createdAT,updatedAt"
        open_result = self.run_gh_command(open_command)

        # 获取关闭Issues
        closed_command = f"gh issue list --repo {self.repo} --limit 50 --state closed --json number,title,labels,createdAT,updatedAt,closedAt"
        closed_result = self.run_gh_command(closed_command)

        summary = {
            "open_issues": [],
            "closed_issues": [],
            "total_open": 0,
            "total_closed": 0,
            "issues_by_state": {},
            "issues_by_age": {"new": 0, "recent": 0, "old": 0},
            "issues_by_status": {}
        }

        if open_result["success"]:
            try:
                open_issues = json.loads(open_result["output"])
                summary["open_issues"] = open_issues
                summary["total_open"] = len(open_issues)

                # 按状态分类
                for issue in open_issues:
                    labels = [label['name'] for label in issue.get('labels', [])]
                    if 'status/in-progress' in labels:
                        summary["issues_by_state"]["in_progress"] = summary["issues_by_state"].get("in_progress", 0) + 1
                    elif 'status/completed' in labels or 'completed' in labels:
                        summary["issues_by_state"]["completed"] = summary["issues_by_state"].get("completed", 0) + 1
                    else:
                        summary["issues_by_state"]["pending"] = summary["issues_by_state"].get("pending", 0) + 1

                    # 按年龄分类
                    created_at = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    age_days = (now - created_at).days

                    if age_days <= 7:
                        summary["issues_by_age"]["new"] += 1
                    elif age_days <= 30:
                        summary["issues_by_age"]["recent"] += 1
                    else:
                        summary["issues_by_age"]["old"] += 1

            except json.JSONDecodeError:
                print("❌ 解析开放Issues数据失败")

        if closed_result["success"]:
            try:
                closed_issues = json.loads(closed_result["output"])
                summary["closed_issues"] = closed_issues
                summary["total_closed"] = len(closed_issues)
            except json.JSONDecodeError:
                print("❌ 解析关闭Issues数据失败")

        self.weekly_report["issues_analyzed"] = summary["total_open"] + summary["total_closed"]
        return summary

    def find_issues_needing_attention(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查找需要关注的Issues"""
        issues_needing_attention = []

        print("🔍 查找需要关注的Issues...")

        # 查找过时的开放Issues
        for issue in summary["open_issues"]:
            labels = [label['name'] for label in issue.get('labels', [])]
            created_at = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age_days = (now - created_at).days

            # 检查是否需要关注
            needs_attention = False
            reason = ""

            if age_days > 30:
                needs_attention = True
                reason = f"超过30天未更新"
            elif 'status/in-progress' in labels and age_days > 14:
                needs_attention = True
                reason = f"进行中超过14天"
            elif age_days > 7 and not any(label.startswith('status/') for label in labels):
                needs_attention = True
                reason = f"超过7天无状态标签"

            if needs_attention:
                issues_needing_attention.append({
                    "issue": issue,
                    "age_days": age_days,
                    "reason": reason,
                    "labels": labels
                })

        return issues_needing_attention

    def find_duplicate_titles(self) -> List[List[Dict[str, Any]]]:
        """查找重复标题的Issues"""
        print("🔍 查找重复标题的Issues...")

        duplicate_groups = []
        title_map = {}

        # 获取所有Issues标题
        open_command = f"gh issue list --repo {self.repo} --limit 100 --state open --json number,title"
        result = self.run_gh_command(open_command)

        if result["success"]:
            try:
                issues = json.loads(result["output"])

                # 简单的重复检测
                for issue in issues:
                    title = issue['title'].lower()

                    # 提取关键词
                    keywords = set(title.split())
                    found_duplicate = False

                    for key, group in title_map.items():
                        # 检查关键词重叠
                        key_keywords = set(key.split())
                        overlap = len(keywords.intersection(key_keywords))

                        if overlap >= 3 and len(keywords) >= 4:  # 至少3个关键词重叠
                            group.append(issue)
                            found_duplicate = True
                            break

                    if not found_duplicate:
                        title_map[title] = [issue]

                # 只保留有重复的组
                duplicate_groups = [group for group in title_map.values() if len(group) > 1]

            except json.JSONDecodeError:
                print("❌ 解析Issues数据失败")

        return duplicate_groups

    def calculate_health_score(self, summary: Dict[str, Any], attention_issues: List[Dict[str, Any]], duplicates: List[List[Dict[str, Any]]]) -> int:
        """计算项目健康分数 (0-100)"""
        score = 100

        # Issues数量影响 (理想15-25个)
        open_count = summary["total_open"]
        if open_count > 30:
            score -= (open_count - 30) * 2
        elif open_count < 10:
            score -= (10 - open_count)

        # 过时Issues影响
        old_issues = len([i for i in attention_issues if i["age_days"] > 30])
        score -= old_issues * 5

        # 重复Issues影响
        duplicate_count = len(duplicates)
        score -= duplicate_count * 10

        # 状态分布影响
        if "completed" in summary["issues_by_state"] and summary["issues_by_state"]["completed"] > 5:
            score += 5  # 有足够多的已完成项

        return max(0, min(100, score))

    def generate_weekly_recommendations(self, summary: Dict[str, Any], attention_issues: List[Dict[str, Any]], duplicates: List[List[Dict[str, Any]]]) -> List[str]:
        """生成每周建议"""
        recommendations = []

        # 基于分析结果生成建议
        if len(attention_issues) > 0:
            recommendations.append(f"🔍 关注 {len(attention_issues)} 个需要更新的Issues")

        if len(duplicates) > 0:
            recommendations.append(f"🔄 合并 {len(duplicates)} 组重复Issues")

        if summary["issues_by_age"]["old"] > 5:
            recommendations.append(f"⏰ 审查 {summary['issues_by_age']['old']} 个超过30天的Issues")

        if summary["total_open"] > 25:
            recommendations.append(f"📊 Issue数量过多 ({summary['total_open']}个)，建议清理关闭一些")

        if summary["total_open"] < 10:
            recommendations.append(f"📝 Issue数量较少 ({summary['total_open']}个)，可以考虑创建新的任务")

        # 添加常规建议
        recommendations.append("🏷️ 检查并统一Issue标签")
        recommendations.append("📋 更新长期未更新的进行中Issues")
        recommendations.append("🔄 定期回顾和调整优先级")

        return recommendations

    def generate_weekly_report(self) -> str:
        """生成每周清理报告"""
        print("📄 生成每周清理报告...")

        # 获取分析数据
        summary = self.get_issues_summary()
        attention_issues = self.find_issues_needing_attention(summary)
        duplicates = self.find_duplicate_titles()
        recommendations = self.generate_weekly_recommendations(summary, attention_issues, duplicates)
        health_score = self.calculate_health_score(summary, attention_issues, duplicates)

        self.weekly_report.update({
            "total_open": summary["total_open"],
            "total_closed": summary["total_closed"],
            "attention_issues": len(attention_issues),
            "duplicate_groups": len(duplicates),
            "recommendations": recommendations,
            "health_score": health_score
        })

        # 生成报告
        report = f"""# 每周GitHub Issues清理报告

## 📊 基础信息
- **清理日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **仓库**: {self.repo}
- **周数**: {datetime.now().isocalendar()[1]}
- **健康分数**: {health_score}/100 {"🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"}

## 📈 Issues概览
- **开放Issues**: {summary["total_open"]}
- **关闭Issues**: {summary["total_closed"]}
- **本周分析**: {self.weekly_report["issues_analyzed"]}

### 按状态分布
"""

        for state, count in summary["issues_by_state"].items():
            status_emoji = {"in_progress": "🔄", "completed": "✅", "pending": "⏳"}.get(state, "📋")
            report += f"- {status_emoji} {state}: {count}\n"

        report += f"""
### 按年龄分布
- 🆕 新创建 (≤7天): {summary["issues_by_age"]["new"]}
- 📅 中期 (8-30天): {summary["issues_by_age"]["recent"]}
- ⏰ 老旧 (>30天): {summary["issues_by_age"]["old"]}

## 🔍 需要关注的Issues ({len(attention_issues)})

"""

        if attention_issues:
            for item in attention_issues[:10]:  # 只显示前10个
                issue = item["issue"]
                report += f"- **#{issue['number']}**: {issue['title'][:50]}{'...' if len(issue['title']) > 50 else ''}\n"
                report += f"  - 原因: {item['reason']} (创建于{item['age_days']}天前)\n"
        else:
            report += "✅ 没有发现需要特别关注的Issues\n"

        report += f"""
## 🔄 重复Issues ({len(duplicates)})

"""

        if duplicates:
            for i, group in enumerate(duplicates[:5]):  # 只显示前5组
                report += f"- 第{i+1}组: {len(group)}个重复\n"
                for issue in group:
                    report += f"  - #{issue['number']}: {issue['title'][:30]}{'...' if len(issue['title']) > 30 else ''}\n"
        else:
            report += "✅ 没有发现明显的重复Issues\n"

        report += f"""
## 💡 本周建议 ({len(recommendations)})

"""

        for i, rec in enumerate(recommendations):
            report += f"{i+1}. {rec}\n"

        report += f"""
## 🎯 行动计划

### 立即行动 (本周内)
"""

        if len(attention_issues) > 0:
            report += f"- 更新 {min(3, len(attention_issues))} 个需要关注的Issues\n"

        if len(duplicates) > 0:
            report += f"- 合并 {min(2, len(duplicates))} 组重复Issues\n"

        report += f"""
### 本周内完成
- 检查并统一Issue标签使用
- 更新长期未响应的进行中Issues
- 创建新的任务或关闭不再需要的Issues

### 持续改进
- 建立定期回顾机制
- 完善Issue创建模板
- 优化标签分类体系

## 📊 健康指标趋势
- **当前健康分数**: {health_score}/100
- **目标**: 保持80分以上
- **上次健康分数**: 将在下周更新

---

*报告生成时间: {datetime.now().isoformat()}*
*工具: Weekly Issues Cleanup Script*
"""

        return report

    def save_weekly_report(self, report: str) -> str:
        """保存每周报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reports/weekly_issues_cleanup_{timestamp}.md"

        # 确保reports目录存在
        os.makedirs("reports", exist_ok=True)

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            # 保存JSON数据
            json_filename = f"reports/weekly_issues_data_{timestamp}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.weekly_report, f, indent=2, ensure_ascii=False)

            print(f"📝 报告已保存到: {filename}")
            print(f"📊 数据已保存到: {json_filename}")

            return filename
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            return ""

    def run_weekly_cleanup(self) -> Dict[str, Any]:
        """执行每周清理流程"""
        print("🚀 开始每周GitHub Issues清理流程")
        print("=" * 60)

        # 生成报告
        report = self.generate_weekly_report()

        # 保存报告
        report_file = self.save_weekly_report(report)

        print("\n" + "=" * 60)
        print("✅ 每周清理流程完成!")

        # 打印健康分数和建议
        health_score = self.weekly_report["health_score"]
        health_emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
        print(f"📊 健康分数: {health_score}/100 {health_emoji}")

        if self.weekly_report["attention_issues"] > 0:
            print(f"⚠️  有 {self.weekly_report['attention_issues']} 个Issues需要关注")

        if self.weekly_report["duplicate_groups"] > 0:
            print(f"🔄 发现 {self.weekly_report['duplicate_groups']} 组重复Issues")

        return {
            "report_file": report_file,
            "weekly_report": self.weekly_report,
            "health_score": health_score
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="每周GitHub Issues清理工具")
    parser.add_argument("--repo", default="xupeng211/FootballPrediction", help="GitHub仓库路径")
    parser.add_argument("--dry-run", action="store_true", help="只分析，不执行实际操作")

    args = parser.parse_args()

    print("🧹 每周GitHub Issues清理工具")
    print(f"📂 仓库: {args.repo}")
    print(f"📅 清理日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.dry_run:
        print("🔍 预览模式 - 只进行分析，不执行实际操作")

    # 创建清理器
    cleanup = WeeklyIssuesCleanup(args.repo)

    try:
        # 执行清理
        result = cleanup.run_weekly_cleanup()

        print(f"\n💡 下一步建议:")
        print(f"  1. 查看详细报告: {result['report_file']}")
        print(f"  2. 根据建议执行相应的清理操作")
        print(f"  3. 更新项目管理流程")

    except KeyboardInterrupt:
        print("\n❌ 用户取消操作")
    except Exception as e:
        print(f"\n❌ 清理过程出错: {e}")


if __name__ == "__main__":
    main()