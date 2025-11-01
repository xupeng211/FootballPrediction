#!/usr/bin/env python3
"""
GitHub Actions 工作流验证脚本
GitHub Actions Workflow Validation Script
"""

import os
import yaml
import json
from pathlib import Path
from datetime import datetime

def validate_workflow_syntax(workflow_path):
    """验证工作流YAML语法"""
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)

        missing_fields = []

        # 检查name字段
        if 'name' not in content:
            missing_fields.append('name')

        # 检查on字段（YAML中on可能被解析为True）
        if 'on' not in content and True not in content:
            missing_fields.append('on')

        # 检查jobs字段
        if 'jobs' not in content:
            missing_fields.append('jobs')

        if missing_fields:
            return False, f"缺少必需字段: {missing_fields}"

        return True, "语法正确"
    except yaml.YAMLError as e:
        return False, f"YAML语法错误: {str(e)}"
    except Exception as e:
        return False, f"验证失败: {str(e)}"

def analyze_workflows():
    """分析所有工作流文件"""
    workflows_dir = Path(".github/workflows")

    if not workflows_dir.exists():
        return {"error": "工作流目录不存在"}

    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    active_workflows = [f for f in workflow_files if "disabled" not in str(f)]

    results = {
        "total_workflows": len(workflow_files),
        "active_workflows": len(active_workflows),
        "disabled_workflows": len(workflow_files) - len(active_workflows),
        "workflows": []
    }

    for workflow_file in active_workflows:
        is_valid, message = validate_workflow_syntax(workflow_file)

        # 获取工作流基本信息
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            # 获取触发器（处理YAML中on被解析为True的情况）
            triggers = []
            if "on" in content and isinstance(content["on"], dict):
                triggers = list(content["on"].keys())
            elif True in content and isinstance(content[True], dict):
                triggers = list(content[True].keys())

            workflow_info = {
                "file": str(workflow_file),
                "name": content.get("name", "未命名"),
                "valid": is_valid,
                "message": message,
                "triggers": triggers,
                "jobs": list(content.get("jobs", {}).keys())
            }
        except:
            workflow_info = {
                "file": str(workflow_file),
                "name": "解析失败",
                "valid": False,
                "message": "无法解析工作流文件",
                "triggers": [],
                "jobs": []
            }

        results["workflows"].append(workflow_info)

    return results

def generate_report(results):
    """生成验证报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_workflows": results["total_workflows"],
            "active_workflows": results["active_workflows"],
            "disabled_workflows": results.get("disabled_workflows", 0),
            "valid_workflows": sum(1 for w in results["workflows"] if w["valid"]),
            "invalid_workflows": sum(1 for w in results["workflows"] if not w["valid"])
        },
        "workflows": results["workflows"]
    }

    return report

def save_report(report, filename="github-actions-validation-report.json"):
    """保存报告到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 报告已保存到: {filename}")

def main():
    """主函数"""
    print("🔍 GitHub Actions 工作流验证开始...")

    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print(f"📁 项目目录: {project_root.absolute()}")

    # 分析工作流
    results = analyze_workflows()

    if "error" in results:
        print(f"❌ {results['error']}")
        return 1

    # 生成报告
    report = generate_report(results)

    # 显示结果摘要
    summary = report["summary"]
    print("\n📊 验证结果摘要:")
    print(f"   总工作流数: {summary['total_workflows']}")
    print(f"   活跃工作流: {summary['active_workflows']}")
    print(f"   禁用工作流: {summary['disabled_workflows']}")
    print(f"   有效工作流: {summary['valid_workflows']}")
    print(f"   无效工作流: {summary['invalid_workflows']}")

    # 显示详细结果
    print("\n📋 详细结果:")
    for workflow in report["workflows"]:
        status = "✅" if workflow["valid"] else "❌"
        print(f"   {status} {workflow['name']} ({workflow['file']})")
        if not workflow["valid"]:
            print(f"      错误: {workflow['message']}")
        else:
            print(f"      触发器: {', '.join(workflow['triggers']) if workflow['triggers'] else '无'}")
            print(f"      作业: {', '.join(workflow['jobs']) if workflow['jobs'] else '无'}")

    # 保存报告
    save_report(report)

    # 生成Markdown报告
    generate_markdown_report(report)

    # 返回结果
    if summary["invalid_workflows"] == 0:
        print("\n🎉 所有工作流验证通过！GitHub Actions应该可以正常运行。")
        return 0
    else:
        print(f"\n⚠️  发现 {summary['invalid_workflows']} 个问题，需要修复。")
        return 1

def generate_markdown_report(report):
    """生成Markdown格式报告"""
    summary = report["summary"]

    markdown_content = f"""# GitHub Actions 验证报告

**生成时间**: {report['timestamp']}
**项目**: Football Prediction System

## 📊 验证摘要

| 指标 | 数量 |
|------|------|
| 总工作流数 | {summary['total_workflows']} |
| 活跃工作流 | {summary['active_workflows']} |
| 禁用工作流 | {summary['disabled_workflows']} |
| ✅ 有效工作流 | {summary['valid_workflows']} |
| ❌ 无效工作流 | {summary['invalid_workflows']} |

## 📋 工作流详情

"""

    for workflow in report["workflows"]:
        status = "✅ 有效" if workflow["valid"] else "❌ 无效"
        markdown_content += f"### {workflow['name']}\n\n"
        markdown_content += f"- **文件**: `{workflow['file']}`\n"
        markdown_content += f"- **状态**: {status}\n"

        if not workflow["valid"]:
            markdown_content += f"- **错误**: {workflow['message']}\n"
        else:
            if workflow["triggers"]:
                markdown_content += f"- **触发器**: {', '.join(workflow['triggers'])}\n"
            if workflow["jobs"]:
                markdown_content += f"- **作业**: {', '.join(workflow['jobs'])}\n"

        markdown_content += "\n"

    markdown_content += """## 🔧 修复建议

### 语法错误修复
1. 检查YAML缩进（使用2个空格）
2. 确保所有字符串正确引用
3. 检查特殊字符转义

### 必需字段修复
确保每个工作流包含以下字段：
- `name`: 工作流名称
- `on`: 触发器配置
- `jobs`: 作业定义

### 常见问题解决
1. **工作流不触发**: 检查`on:`配置和分支名称
2. **权限问题**: 添加`permissions:`配置
3. **超时问题**: 设置`timeout-minutes:`

## 🚀 下一步

1. 修复所有无效工作流
2. 提交修复到GitHub
3. 验证GitHub Actions正常运行

---
*此报告由自动化脚本生成*
"""

    # 保存Markdown报告
    markdown_file = f"github-actions-validation-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"📄 Markdown报告已保存到: {markdown_file}")

if __name__ == "__main__":
    import sys
    sys.exit(main())