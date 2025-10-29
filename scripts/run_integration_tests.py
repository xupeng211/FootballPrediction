#!/usr/bin/env python3
"""
集成测试运行脚本
自动设置环境、运行测试并生成报告
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path


def check_prerequisites():
    """检查先决条件"""
    print("🔍 检查先决条件...")

    # 检查 Docker
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("✅ Docker 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker 未安装或不在 PATH 中")
        return False

    # 检查 Docker Compose
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        print("✅ Docker Compose 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
            print("✅ Docker Compose 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker Compose 未安装")
            return False

    return True


def start_test_environment():
    """启动测试环境"""
    print("\n🚀 启动测试环境...")

    # 使用管理脚本启动环境
    result = subprocess.run(
        ["./scripts/manage_test_env.sh", "start"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ 启动测试环境失败: {result.stderr}")
        return False

    print("✅ 测试环境启动成功")

    # 等待服务就绪
    print("⏳ 等待服务就绪...")
    time.sleep(30)

    return True


def check_service_health():
    """检查服务健康状态"""
    print("\n🏥 检查服务健康状态...")

    # 使用管理脚本检查健康
    result = subprocess.run(
        ["./scripts/manage_test_env.sh", "check"], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"⚠️ 服务健康检查警告: {result.stderr}")
        print("继续运行测试...")
    else:
        print("✅ 所有服务健康")

    return True


def run_integration_tests():
    """运行集成测试"""
    print("\n🧪 运行集成测试...")

    # 创建报告目录
    Path("reports").mkdir(exist_ok=True)

    # 运行测试
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xml_file = f"reports/integration_{timestamp}.xml"
    html_file = f"reports/integration_{timestamp}.html"
    json_file = f"reports/integration_{timestamp}.json"

    cmd = [
        "pytest",
        "tests/integration/",
        "-v",
        "--tb=short",
        "--disable-warnings",
        f"--junit-xml={xml_file}",
        f"--html={html_file}",
        "--self-contained-html",
        "--json-report",
        f"--json-report-file={json_file}",
        "--maxfail=10",
        "-x",  # 第一个失败时停止
    ]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed_time = time.time() - start_time

    # 输出结果
    print("\n" + result.stdout)
    if result.stderr:
        print("\n错误输出:")
        print(result.stderr)

    # 解析结果
    success = result.returncode == 0

    # 生成摘要报告
    summary = {
        "timestamp": timestamp,
        "success": success,
        "elapsed_time": elapsed_time,
        "xml_file": xml_file,
        "html_file": html_file,
        "json_file": json_file,
    }

    # 尝试解析 JSON 报告获取详细信息
    try:
        with open(json_file, "r") as f:
            json_data = json.load(f)
            summary.update(
                {
                    "total": json_data.get("summary", {}).get("total", 0),
                    "passed": json_data.get("summary", {}).get("passed", 0),
                    "failed": json_data.get("summary", {}).get("failed", 0),
                    "skipped": json_data.get("summary", {}).get("skipped", 0),
                    "error": json_data.get("summary", {}).get("error", 0),
                }
            )
    except Exception as e:
        print(f"⚠️ 无法解析测试报告: {e}")

    return success, summary


def generate_report(summary):
    """生成测试报告"""
    print("\n📊 生成测试报告...")

    # 创建 Markdown 报告
    report_path = f"docs/_reports/INTEGRATION_TEST_RESULT_{summary['timestamp']}.md"
    Path("docs/_reports").mkdir(exist_ok=True)

    report_content = f"""# 集成测试报告 - {summary['timestamp']}

## 📋 测试概览

- **执行时间**: {summary['timestamp']}
- **总耗时**: {summary['elapsed_time']:.2f} 秒
- **总测试数**: {summary.get('total', 'N/A')}
- **通过**: {summary.get('passed', 0)}
- **失败**: {summary.get('failed', 0)}
- **跳过**: {summary.get('skipped', 0)}
- **错误**: {summary.get('error', 0)}
- **成功率**: {(summary.get('passed', 0) / max(summary.get('total', 1), 1) * 100):.1f}%

## 📊 测试结果

### 整体状态
{'✅ 通过' if summary['success'] else '❌ 失败'}

### 详细报告
- [HTML报告](../{summary['html_file']})
- [XML报告](../{summary['xml_file']})
- [JSON数据](../{summary['json_file']})

## 🔍 测试覆盖范围

- **API 集成测试**: 预测 API、比赛 API、用户 API
- **数据库集成测试**: 连接池、事务、查询优化
- **服务间通信测试**: Kafka、Redis（如果启用）

## 🚨 失败分析

{generate_failure_analysis(summary)}

## 💡 建议

{generate_recommendations(summary)}

## 📈 历史趋势

[查看历史报告](./INTEGRATION_TEST_HISTORY.md)

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    with open(report_path, "w") as f:
        f.write(report_content)

    print(f"✅ 报告已生成: {report_path}")

    # 更新历史记录
    update_history(summary)


def generate_failure_analysis(summary):
    """生成失败分析"""
    if summary.get("failed", 0) == 0 and summary.get("error", 0) == 0:
        return "✅ 所有测试通过，无失败案例"

    analysis = []

    if summary.get("failed", 0) > 0:
        analysis.append(f"- **失败测试**: {summary['failed']} 个")

    if summary.get("error", 0) > 0:
        analysis.append(f"- **错误测试**: {summary['error']} 个")

    analysis.append("\n请查看详细的 HTML 报告获取具体失败原因。")

    return "\n".join(analysis)


def generate_recommendations(summary):
    """生成改进建议"""
    recommendations = []

    if not summary["success"]:
        recommendations.append("- 🚨 优先修复失败的测试用例")

    if summary.get("total", 0) < 50:
        recommendations.append("- 📈 增加集成测试覆盖率")

    if summary.get("elapsed_time", 0) > 300:
        recommendations.append("- ⚡ 优化测试执行速度")

    if not recommendations:
        recommendations.append("- ✅ 测试状态良好，继续保持")

    return "\n".join(recommendations)


def update_history(summary):
    """更新历史记录"""
    history_path = "docs/_reports/INTEGRATION_TEST_HISTORY.md"

    history_entry = f"| {summary['timestamp']} | {summary.get('total', 'N/A')} | {summary.get('passed', 0)} | {summary.get('failed', 0)} | {summary.get('skipped', 0)} | {summary['elapsed_time']:.2f}s | {'✅' if summary['success'] else '❌'} |\n"

    # 读取或创建历史文件
    if Path(history_path).exists():
        with open(history_path, "r") as f:
            content = f.read()
        # 在表格后添加新行
        if "\n---\n\n" in content:
            content = content.replace("\n---\n\n", f"\n{history_entry}---\n\n")
        else:
            content += f"\n{history_entry}"
    else:
        content = f"""# 集成测试历史记录

| 时间 | 总数 | 通过 | 失败 | 跳过 | 耗时 | 状态 |
|------|------|------|------|------|------|------|
{history_entry}
"""

    with open(history_path, "w") as f:
        f.write(content)


def cleanup_environment():
    """清理测试环境"""
    print("\n🧹 清理测试环境...")

    # 询问是否停止环境
    response = input("\n是否停止测试环境？(y/N): ").strip().lower()

    if response == "y" or response == "yes":
        result = subprocess.run(
            ["./scripts/manage_test_env.sh", "stop"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ 测试环境已停止")
        else:
            print(f"⚠️ 停止环境时出错: {result.stderr}")
    else:
        print("ℹ️ 测试环境保持运行状态")
        print("   使用 './scripts/manage_test_env.sh stop' 手动停止")


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 集成测试运行器")
    print("=" * 60)

    # 检查先决条件
    if not check_prerequisites():
        print("\n❌ 先决条件检查失败，退出")
        sys.exit(1)

    try:
        # 启动测试环境
        if not start_test_environment():
            print("\n❌ 无法启动测试环境")
            sys.exit(1)

        # 检查服务健康
        check_service_health()

        # 运行测试
        success, summary = run_integration_tests()

        # 生成报告
        generate_report(summary)

        # 打印摘要
        print("\n" + "=" * 60)
        print("📊 测试摘要")
        print("=" * 60)
        print(f"状态: {'✅ 成功' if success else '❌ 失败'}")
        print(f"总测试: {summary.get('total', 'N/A')}")
        print(f"通过: {summary.get('passed', 0)}")
        print(f"失败: {summary.get('failed', 0)}")
        print(f"跳过: {summary.get('skipped', 0)}")
        print(f"耗时: {summary['elapsed_time']:.2f} 秒")
        print("=" * 60)

        # 清理环境
        cleanup_environment()

        # 设置退出码
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        cleanup_environment()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        cleanup_environment()
        sys.exit(1)


if __name__ == "__main__":
    main()
