#!/usr/bin/env python3
"""
GitHub Issue标签自动修正工具
GitHub Issue Label Auto-Fixer

自动修正GitHub Issues的标签，确保标签使用规范化
"""

import json
import sys
import argparse
from typing import List, Dict, Any, Set
from pathlib import Path


class GitHubLabelFixer:
    """GitHub标签修正器"""

    def __init__(self, repo: str, dry_run: bool = True):
        """
        初始化标签修正器

        Args:
            repo: 仓库名称，格式为 "owner/repo"
            dry_run: 是否为试运行模式
        """
        self.repo = repo
        self.dry_run = dry_run

        # 标准化标签映射
        self.label_corrections = {
            # 状态标签标准化
            "status:completed": "status/completed",
            "status:resolved": "status/resolved",
            "status:in-progress": "status/in-progress",
            "status:inprogress": "status/in-progress",
            "status:cancelled": "status/cancelled",
            "status:canceled": "status/cancelled",
            "completed": "status/completed",
            "resolved": "status/resolved",
            "done": "status/completed",
            "finished": "status/completed",

            # 优先级标签标准化
            "priority:high": "priority/high",
            "priority:medium": "priority/medium",
            "priority:low": "priority/low",
            "priority:critical": "priority/critical",
            "high": "priority/high",
            "medium": "priority/medium",
            "low": "priority/low",
            "critical": "priority/critical",
            "urgent": "priority/critical",

            # 类型标签标准化
            "type:bug": "bug",
            "type:enhancement": "enhancement",
            "type:feature": "feature",
            "type:documentation": "documentation",
            "type:maintenance": "maintenance",
            "type:question": "question",
            "type:chore": "chore",

            # 其他常见标签
            "claude-code": "claude-code",
            "automated": "automated",
            "quality-assurance": "quality-assurance",
            "automation": "automation",
            "project-management": "project-management",
            "quality-gate": "quality-gate"
        }

        # 需要移除的重复或错误标签
        self.labels_to_remove = {
            "duplicate",
            "wontfix",
            "invalid",
            "wont do",
            "wontfix",
            "question"  # 如果不是真正的疑问
        }

    def run_command(self, command: str) -> Dict[str, Any]:
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

    def get_issues(self, state: str = "open") -> List[Dict[str, Any]]:
        """获取Issues列表"""
        command = f"gh issue list --repo {self.repo} --state {state} --limit 100 --json number,title,labels"
        result = self.run_command(command)

        if not result["success"]:
            print(f"❌ 获取Issues失败: {result['stderr']}")
            return []

        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError as e:
            print(f"❌ 解析Issues数据失败: {e}")
            return []

    def normalize_labels(self, labels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化标签

        Returns:
            {
                "to_add": [要添加的标签],
                "to_remove": [要移除的标签],
                "final_labels": [最终标签列表]
            }
        """
        current_labels = {label["name"] for label in labels}
        to_add = set()
        to_remove = set()

        # 检查每个标签是否需要修正
        for label in current_labels:
            if label in self.label_corrections:
                # 需要修正的标签
                corrected_label = self.label_corrections[label]
                if corrected_label != label:
                    to_remove.add(label)
                    to_add.add(corrected_label)
            elif label in self.labels_to_remove:
                # 需要移除的标签
                to_remove.add(label)

        # 检查是否有重复的状态标签
        status_labels = [l for l in current_labels if l.startswith("status/")]
        if len(status_labels) > 1:
            # 保留第一个，移除其他的
            to_remove.update(status_labels[1:])

        # 检查是否有重复的优先级标签
        priority_labels = [l for l in current_labels if l.startswith("priority/")]
        if len(priority_labels) > 1:
            # 保留最高优先级
            priority_order = ["priority/critical", "priority/high", "priority/medium", "priority/low"]
            for priority in priority_order:
                if priority in priority_labels:
                    to_remove.update([p for p in priority_labels if p != priority])
                    break

        # 计算最终标签列表
        final_labels = current_labels - to_remove | to_add

        return {
            "to_add": list(to_add),
            "to_remove": list(to_remove),
            "final_labels": list(final_labels)
        }

    def fix_issue_labels(self, issue: Dict[str, Any]) -> bool:
        """修正单个Issue的标签"""
        number = issue["number"]
        title = issue["title"]
        current_labels = [label["name"] for label in issue.get("labels", [])]

        # 标准化标签
        normalization = self.normalize_labels(issue.get("labels", []))

        if not normalization["to_add"] and not normalization["to_remove"]:
            # 无需修正
            return False

        print(f"🔧 Issue #{number}: {title}")
        print(f"   当前标签: {', '.join(current_labels)}")

        if normalization["to_remove"]:
            print(f"   移除标签: {', '.join(normalization['to_remove'])}")

        if normalization["to_add"]:
            print(f"   添加标签: {', '.join(normalization['to_add'])}")

        print(f"   最终标签: {', '.join(normalization['final_labels'])}")

        if self.dry_run:
            print(f"   🔍 [试运行] 将修正标签")
            return True

        # 执行标签修正
        try:
            # 先移除标签
            if normalization["to_remove"]:
                remove_labels = " ".join([f'"{label}"' for label in normalization["to_remove"]])
                remove_cmd = f'gh issue edit {number} --repo {self.repo} --remove-label {remove_labels}'
                result = self.run_command(remove_cmd)
                if not result["success"]:
                    print(f"   ❌ 移除标签失败: {result['stderr']}")
                    return False

            # 再添加标签
            if normalization["to_add"]:
                add_labels = " ".join([f'"{label}"' for label in normalization["to_add"]])
                add_cmd = f'gh issue edit {number} --repo {self.repo} --add-label {add_labels}'
                result = self.run_command(add_cmd)
                if not result["success"]:
                    print(f"   ❌ 添加标签失败: {result['stderr']}")
                    return False

            print(f"   ✅ 标签修正成功")
            return True

        except Exception as e:
            print(f"   ❌ 标签修正失败: {e}")
            return False

    def analyze_label_usage(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """分析标签使用情况"""
        label_count = {}

        for issue in issues:
            for label in issue.get("labels", []):
                label_name = label["name"]
                label_count[label_name] = label_count.get(label_name, 0) + 1

        return label_count

    def generate_label_report(self, issues: List[Dict[str, Any]], fixed_count: int) -> str:
        """生成标签修正报告"""
        report = []
        report.append("# GitHub Issue标签修正报告")
        report.append(f"仓库: {self.repo}")
        report.append(f"模式: {'试运行' if self.dry_run else '执行模式'}")
        report.append("")

        # 标签使用统计
        label_usage = self.analyze_label_usage(issues)
        total_labels = sum(label_usage.values())

        report.append("## 📊 标签使用统计")
        report.append(f"- 总标签数: {total_labels}")
        report.append(f"- 唯一标签数: {len(label_usage)}")
        report.append("")

        report.append("### 标签使用频率 (前20个)")
        sorted_labels = sorted(label_usage.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:20]:
            percentage = (count / total_labels) * 100
            report.append(f"- **{label}**: {count}次 ({percentage:.1f}%)")

        report.append("")

        # 修正结果统计
        report.append("## 🔧 修正结果")
        report.append(f"- 需要修正的Issues: {fixed_count}")
        report.append(f"- 总Issues数: {len(issues)}")
        report.append(f"- 修正比例: {(fixed_count/len(issues)*100):.1f}%" if issues else "N/A")
        report.append("")

        # 标签质量分析
        report.append("## 📋 标签质量分析")

        # 检查非标准标签
        non_standard_labels = []
        for label in label_usage:
            if label not in self.label_corrections.values() and not label.startswith(("status/", "priority/")):
                non_standard_labels.append((label, label_usage[label]))

        if non_standard_labels:
            report.append("### 非标准标签")
            for label, count in sorted(non_standard_labels, key=lambda x: x[1], reverse=True):
                report.append(f"- **{label}**: {count}次")
        else:
            report.append("✅ 所有标签都已标准化")

        report.append("")

        # 改进建议
        report.append("## 💡 改进建议")

        if fixed_count > 0:
            report.append("1. **定期执行标签修正**: 建议每周执行一次标签标准化")

        if non_standard_labels:
            report.append("2. **完善标签映射**: 考虑将常用的非标准标签加入标准化映射")

        if len(label_usage) > 50:
            report.append("3. **精简标签体系**: 当前标签数量较多，考虑合并相似标签")

        # 检查未标记优先级的Issues
        no_priority_issues = [issue for issue in issues
                             if not any(label["name"].startswith("priority/") for label in issue.get("labels", []))]

        if no_priority_issues:
            percentage = (len(no_priority_issues) / len(issues)) * 100
            report.append(f"4. **优先级标签完善**: {len(no_priority_issues)}个Issues ({percentage:.1f}%) 缺少优先级标签")

        return "\n".join(report)

    def run_label_fix(self) -> Dict[str, Any]:
        """执行标签修正"""
        print(f"🚀 开始GitHub Issue标签修正...")
        print(f"仓库: {self.repo}")
        print(f"模式: {'试运行' if self.dry_run else '执行模式'}")
        print("")

        # 获取所有开放Issues
        issues = self.get_issues("open")
        if not issues:
            print("❌ 无法获取Issues列表")
            return {"success": False}

        print(f"📊 找到 {len(issues)} 个开放Issues")
        print("")

        # 修正标签
        fixed_count = 0
        for issue in issues:
            if self.fix_issue_labels(issue):
                fixed_count += 1
            print("")

        # 生成报告
        report = self.generate_label_report(issues, fixed_count)

        # 保存报告
        report_path = Path("reports/github_label_fix_report.md")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📋 标签修正报告已保存到: {report_path}")
        print("")

        # 输出总结
        print("🎉 标签修正完成!")
        print(f"- 总Issues数: {len(issues)}")
        print(f"- 需要修正: {fixed_count}")
        print(f"- 修正模式: {'试运行' if self.dry_run else '执行模式'}")

        return {
            "success": True,
            "total_issues": len(issues),
            "fixed_issues": fixed_count,
            "report_path": str(report_path)
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GitHub Issue标签自动修正工具")
    parser.add_argument("--repo", default="xupeng211/FootballPrediction", help="仓库名称 (默认: xupeng211/FootballPrediction)")
    parser.add_argument("--execute", action="store_true", help="执行实际标签修正 (默认为试运行)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式 (默认)")

    args = parser.parse_args()

    # 确定运行模式
    dry_run = not args.execute

    # 创建标签修正器
    fixer = GitHubLabelFixer(args.repo, dry_run=dry_run)

    # 执行标签修正
    results = fixer.run_label_fix()

    if not results["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()