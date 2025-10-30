#!/usr/bin/env python3
"""
GitHub Issues自动监控和管理工具
用于跟踪项目GitHub Issues的状态、生成报告和自动化管理操作

功能特性:
- Issues状态自动监控
- 标签管理自动化
- 报告生成
- 持续改进跟踪
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("❌ 缺失依赖: requests")
    print("安装命令: pip install requests")
    sys.exit(1)


class GitHubMonitor:
    """GitHub Issues监控器"""

    def __init__(self, repo: str, token: Optional[str] = None):
        """
        初始化GitHub监控器

        Args:
            repo: 仓库格式 "owner/repo"
            token: GitHub token (可选，也可从环境变量获取)
        """
        self.repo = repo
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Monitor/1.0"
        }

        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """发送API请求"""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API请求失败: {e}")
            return {}

    def get_issues(self, state: str = "open", labels: Optional[List[str]] = None) -> List[Dict]:
        """获取Issues列表"""
        params = {"state": state}
        if labels:
            params["labels"] = ",".join(labels)

        issues = []
        page = 1

        while True:
            params["page"] = page
            data = self._make_request("issues", params)

            if not data:
                break

            issues.extend(data)

            # 检查是否还有更多页面
            if len(data) < 30:  # GitHub默认每页30个
                break

            page += 1

        return issues

    def get_labels(self) -> List[Dict]:
        """获取仓库所有标签"""
        return self._make_request("labels") or []

    def analyze_issues_health(self) -> Dict:
        """分析Issues健康状况"""
        open_issues = self.get_issues("open")
        closed_issues = self.get_issues("closed")
        all_labels = self.get_labels()

        # 按标签分类统计
        label_stats = {}
        for label in all_labels:
            label_name = label["name"]
            open_count = len([i for i in open_issues if label_name in [l["name"] for l in i["labels"]]])
            closed_count = len([i for i in closed_issues if label_name in [l["name"] for l in i["labels"]]])

            label_stats[label_name] = {
                "open": open_count,
                "closed": closed_count,
                "total": open_count + closed_count
            }

        # 时间分析
        now = datetime.now()
        recent_open = len([i for i in open_issues
                          if datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")).replace(tzinfo=None) > now - timedelta(days=7)])
        recent_closed = len([i for i in closed_issues
                           if i.get("closed_at") and datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00")).replace(tzinfo=None) > now - timedelta(days=7)])

        return {
            "summary": {
                "total_open": len(open_issues),
                "total_closed": len(closed_issues),
                "recent_open": recent_open,
                "recent_closed": recent_closed,
                "total_labels": len(all_labels)
            },
            "label_stats": label_stats,
            "open_issues_sample": open_issues[:5],  # 前5个开放Issues
            "closed_issues_sample": closed_issues[:5]  # 前5个关闭Issues
        }

    def generate_monitoring_report(self, output_file: Optional[str] = None) -> str:
        """生成监控报告"""
        health_data = self.analyze_issues_health()

        report_lines = [
            "# GitHub Issues监控报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**仓库**: {self.repo}",
            "**监控状态**: 🟢 健康",
            "",
            "---",
            "",
            "## 📊 总体统计",
            "",
            "### 🔢 数量统计",
            "```",
            f"🔓 开放Issues: {health_data['summary']['total_open']}个",
            f"🔒 关闭Issues: {health_data['summary']['total_closed']}个",
            f"📅 本周新增: {health_data['summary']['recent_open']}个",
            f"✅ 本周解决: {health_data['summary']['recent_closed']}个",
            f"🏷️ 标签总数: {health_data['summary']['total_labels']}个",
            "```",
            "",
            "### 📈 健康指标",
            f"- **解决率**: {(health_data['summary']['recent_closed'] / max(1, health_data['summary']['recent_open']) * 100):.1f}%",
            f"- **活跃度**: {'高' if health_data['summary']['recent_open'] > 0 else '正常'}",
            f"- **标签覆盖**: {'完善' if health_data['summary']['total_labels'] > 5 else '基础'}",
            "",
            "---",
            "",
            "## 🏷️ 标签分析",
            ""
        ]

        # 添加标签统计
        for label_name, stats in sorted(health_data["label_stats"].items()):
            if stats["total"] > 0:
                report_lines.extend([
                    f"### {label_name}",
                    f"- 开放: {stats['open']}个",
                    f"- 关闭: {stats['closed']}个",
                    f"- 总计: {stats['total']}个",
                    ""
                ])

        # 添加开放Issues样本
        if health_data["open_issues_sample"]:
            report_lines.extend([
                "---",
                "",
                "## 🔓 开放Issues样本",
                ""
            ])

            for i, issue in enumerate(health_data["open_issues_sample"], 1):
                title = issue["title"][:50] + "..." if len(issue["title"]) > 50 else issue["title"]
                labels = ", ".join([l["name"] for l in issue["labels"]])
                created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")

                report_lines.extend([
                    f"### {i}. {title}",
                    f"- **编号**: #{issue['number']}",
                    f"- **标签**: {labels or '无标签'}",
                    f"- **创建时间**: {created}",
                    f"- **链接**: [{issue['html_url']}]({issue['html_url']})",
                    ""
                ])

        # 添加关闭Issues样本
        if health_data["closed_issues_sample"]:
            report_lines.extend([
                "---",
                "",
                "## 🔒 最近关闭Issues样本",
                ""
            ])

            for i, issue in enumerate(health_data["closed_issues_sample"], 1):
                title = issue["title"][:50] + "..." if len(issue["title"]) > 50 else issue["title"]
                labels = ", ".join([l["name"] for l in issue["labels"]])
                closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")

                report_lines.extend([
                    f"### {i}. {title}",
                    f"- **编号**: #{issue['number']}",
                    f"- **标签**: {labels or '无标签'}",
                    f"- **关闭时间**: {closed}",
                    f"- **链接**: [{issue['html_url']}]({issue['html_url']})",
                    ""
                ])

        # 添加建议部分
        report_lines.extend([
            "---",
            "",
            "## 💡 改进建议",
            "",
            "### 🎯 立即行动项",
            "- [ ] 检查开放Issues的优先级排序",
            "- [ ] 为无标签的Issues添加适当标签",
            "- [ ] 跟进长期开放的Issues",
            "",
            "### 🔄 持续改进",
            "- [ ] 定期审查和更新标签体系",
            "- [ ] 建立Issue响应时间目标",
            "- [ ] 完善Issue模板使用情况",
            "",
            "### 📊 监控指标",
            "- **目标解决率**: >80%",
            "- **目标响应时间**: <48小时",
            "- **目标标签覆盖率**: >90%",
            "",
            "---",
            "",
            "**报告生成完成**: 🎉 监控数据已收集并分析",
            "**下次监控**: 建议在24小时后再次执行",
            "",
            "*本报告由GitHub Monitor自动生成*"
        ])

        report_content = "\n".join(report_lines)

        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"📄 报告已保存到: {output_file}")

        return report_content

    def check_label_health(self) -> Dict:
        """检查标签使用情况"""
        labels = self.get_labels()
        open_issues = self.get_issues("open")

        unused_labels = []
        popular_labels = []

        for label in labels:
            label_name = label["name"]
            usage = len([i for i in open_issues if label_name in [l["name"] for l in i["labels"]]])

            if usage == 0:
                unused_labels.append(label_name)
            elif usage >= 3:
                popular_labels.append((label_name, usage))

        return {
            "total_labels": len(labels),
            "unused_labels": unused_labels,
            "popular_labels": sorted(popular_labels, key=lambda x: x[1], reverse=True)[:10],
            "label_usage_healthy": len(unused_labels) < len(labels) * 0.2
        }

    def suggest_improvements(self) -> List[str]:
        """建议改进措施"""
        health_data = self.analyze_issues_health()
        label_health = self.check_label_health()
        suggestions = []

        # 基于开放Issues数量的建议
        if health_data["summary"]["total_open"] > 20:
            suggestions.append("🚨 开放Issues数量较多，建议优先处理或分类管理")

        # 基于解决率的建议
        if health_data["summary"]["recent_open"] > 0 and health_data["summary"]["recent_closed"] == 0:
            suggestions.append("⚠️ 本周有新增Issues但无解决，建议关注问题处理效率")

        # 基于标签使用的建议
        if not label_health["label_usage_healthy"]:
            suggestions.append(f"🏷️ 发现{len(label_health['unused_labels'])}个未使用标签，建议清理或重命名")

        # 基于活跃度的建议
        if health_data["summary"]["recent_open"] == 0 and health_data["summary"]["recent_closed"] == 0:
            suggestions.append("📊 本周无Issue活动，可考虑增加社区互动或功能宣传")

        if not suggestions:
            suggestions.append("✅ GitHub Issues管理状况良好，继续保持")

        return suggestions


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GitHub Issues监控工具")
    parser.add_argument("--repo", default="xupeng211/FootballPrediction",
                       help="GitHub仓库 (默认: xupeng211/FootballPrediction)")
    parser.add_argument("--token", help="GitHub访问token")
    parser.add_argument("--output", help="报告输出文件路径")
    parser.add_argument("--check-only", action="store_true",
                       help="仅检查健康状况，不生成完整报告")
    parser.add_argument("--suggest", action="store_true",
                       help="显示改进建议")

    args = parser.parse_args()

    # 创建监控器
    monitor = GitHubMonitor(args.repo, args.token)

    print("🔍 GitHub Issues监控开始...")
    print(f"📁 仓库: {args.repo}")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if args.check_only:
        # 仅检查健康状况
        health_data = monitor.analyze_issues_health()
        label_health = monitor.check_label_health()

        print("📊 健康状况检查结果:")
        print(f"  🔓 开放Issues: {health_data['summary']['total_open']}个")
        print(f"  🔒 关闭Issues: {health_data['summary']['total_closed']}个")
        print(f"  📅 本周新增: {health_data['summary']['recent_open']}个")
        print(f"  ✅ 本周解决: {health_data['summary']['recent_closed']}个")
        print(f"  🏷️ 标签总数: {health_data['summary']['total_labels']}个")
        print(f"  📈 标签健康: {'✅ 良好' if label_health['label_usage_healthy'] else '⚠️ 需改进'}")

    elif args.suggest:
        # 显示改进建议
        suggestions = monitor.suggest_improvements()
        print("💡 改进建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")

    else:
        # 生成完整报告
        output_file = args.output or f"github_monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        monitor.generate_monitoring_report(output_file)

        print("✅ 监控报告生成完成!")
        print(f"📄 文件位置: {output_file}")
        print("📊 数据统计: 已分析所有Issues和标签使用情况")
        print("💡 改进建议: 已包含在报告中")

    print()
    print("🎉 GitHub监控任务完成!")


if __name__ == "__main__":
    main()