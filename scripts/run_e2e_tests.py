#!/usr/bin/env python3
"""
E2E 测试运行脚本
自动启动 Staging 环境并运行端到端测试
"""

import os
import sys
import subprocess
import time
import json
import argparse
from datetime import datetime
from pathlib import Path


def check_prerequisites():
    """检查先决条件"""
    print("🔍 检查先决条件...")

    # 检查 Docker
    try:
        result = subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("✅ Docker 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker 未安装或不在 PATH 中")
        return False

    # 检查 Docker Compose
    try:
        result = subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        print("✅ Docker Compose 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            result = subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
            print("✅ Docker Compose 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker Compose 未安装")
            return False

    return True


def setup_staging_environment():
    """设置 Staging 环境"""
    print("\n🚀 设置 Staging 环境...")

    # 检查 Staging 环境是否已运行
    result = subprocess.run(
        ["./scripts/manage_staging_env.sh", "status"],
        capture_output=True,
        text=True
    )

    if "app" in result.stdout and "Up" in result.stdout:
        print("✅ Staging 环境已在运行")
    else:
        print("📥 启动 Staging 环境...")
        result = subprocess.run(
            ["./scripts/manage_staging_env.sh", "start"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ 启动 Staging 环境失败: {result.stderr}")
            return False

        # 等待服务就绪
        print("⏳ 等待服务就绪...")
        time.sleep(60)

    # 验证环境健康
    print("🏥 检查环境健康状态...")
    result = subprocess.run(
        ["./scripts/manage_staging_env.sh", "health"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ 环境健康检查通过")
    else:
        print("⚠️ 环境健康检查有警告，继续执行测试")

    return True


def run_e2e_tests(test_type="all", tags=None, verbose=False):
    """运行 E2E 测试"""
    print(f"\n🧪 运行 E2E 测试 ({test_type})...")

    # 创建报告目录
    Path("reports").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 构建 pytest 命令
    cmd = [
        "pytest",
        "tests/e2e/",
        "-v",
        "--tb=short",
        "--disable-warnings",
        f"--html=reports/e2e_{timestamp}.html",
        "--self-contained-html",
        f"--junit-xml=reports/e2e_{timestamp}.xml",
        "--json-report",
        f"--json-report-file=reports/e2e_{timestamp}.json",
        "-m", "e2e"
    ]

    # 添加测试类型
    if test_type == "smoke":
        cmd.extend(["-m", "smoke"])
    elif test_type == "critical":
        cmd.extend(["-m", "critical"])
    elif test_type == "performance":
        cmd.extend(["-m", "performance"])
    elif test_type == "regression":
        cmd.extend(["-m", "regression"])

    # 添加标签过滤
    if tags:
        for tag in tags:
            cmd.extend(["-m", tag])

    # 添加详细输出
    if verbose:
        cmd.append("-vv")

    # 添加超时设置
    cmd.extend(["--timeout=300"])  # 5分钟超时

    # 打印执行命令
    print(f"执行命令: {' '.join(cmd)}")

    # 执行测试
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
        "test_type": test_type,
        "success": success,
        "elapsed_time": elapsed_time,
        "html_report": f"reports/e2e_{timestamp}.html",
        "xml_report": f"reports/e2e_{timestamp}.xml",
        "json_report": f"reports/e2e_{timestamp}.json",
    }

    # 尝试解析 JSON 报告获取详细信息
    try:
        with open(summary["json_report"], 'r') as f:
            json_data = json.load(f)
            summary.update({
                "total": json_data.get("summary", {}).get("total", 0),
                "passed": json_data.get("summary", {}).get("passed", 0),
                "failed": json_data.get("summary", {}).get("failed", 0),
                "skipped": json_data.get("summary", {}).get("skipped", 0),
                "error": json_data.get("summary", {}).get("error", 0),
                "duration": json_data.get("summary", {}).get("duration", elapsed_time),
            })
    except Exception as e:
        print(f"⚠️ 无法解析测试报告: {e}")

    return success, summary


def generate_report(summary):
    """生成测试报告"""
    print("\n📊 生成 E2E 测试报告...")

    # 创建 Markdown 报告
    report_path = f"docs/_reports/E2E_TEST_RESULT_{summary['timestamp']}.md"
    Path("docs/_reports").mkdir(exist_ok=True)

    status_emoji = "✅" if summary["success"] else "❌"
    status_text = "通过" if summary["success"] else "失败"

    report_content = f"""# 端到端测试报告 - {summary['timestamp']}

## 📊 测试概览

- **测试类型**: {summary['test_type']}
- **执行时间**: {summary['timestamp']}
- **总耗时**: {summary['elapsed_time']:.2f} 秒
- **测试状态**: {status_emoji} {status_text}
- **总测试数**: {summary.get('total', 'N/A')}
- **通过**: {summary.get('passed', 0)}
- **失败**: {summary.get('failed', 0)}
- **跳过**: {summary.get('skipped', 0)}
- **错误**: {summary.get('error', 0)}
- **成功率**: {(summary.get('passed', 0) / max(summary.get('total', 1), 1) * 100):.1f}%

## 📋 测试覆盖范围

### 关键业务流程
- ✅ 用户注册到预测完整流程
- ✅ 比赛实时更新流程
- ✅ 批量数据处理流程

### 性能测试
- ✅ 并发用户负载测试
- ✅ API端点性能测试
- ✅ 数据库查询性能测试
- ✅ 缓存性能测试
- ✅ 压力测试

## 📊 测试结果

### 整体状态
{status_emoji} {'测试通过' if summary['success'] else '测试失败'}

### 性能指标
- 平均响应时间: < 1s (目标)
- P95响应时间: < 2s (目标)
- 并发处理能力: ≥ 50 用户 (目标)
- 系统可用性: ≥ 99% (目标)

### 详细报告
- [HTML报告](../{summary['html_report']})
- [XML报告](../{summary['xml_report']})
- [JSON数据](../{summary['json_report']})

## 🚨 失败分析

{generate_failure_analysis(summary)}

## 💡 改进建议

{generate_recommendations(summary)}

## 🌐 测试环境信息

- **环境**: Staging
- **基础架构**: Docker Compose
- **数据库**: PostgreSQL
- **缓存**: Redis
- **消息队列**: Kafka
- **负载均衡**: Nginx
- **监控系统**: Prometheus + Grafana

## 📈 历史趋势

[查看历史报告](./E2E_TEST_HISTORY.md)

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    with open(report_path, 'w') as f:
        f.write(report_content)

    print(f"✅ 报告已生成: {report_path}")

    # 更新历史记录
    update_history(summary)

    # 打开浏览器查看报告（可选）
    try:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(summary['html_report'])}")
    except:
        pass


def generate_failure_analysis(summary):
    """生成失败分析"""
    if summary.get('failed', 0) == 0 and summary.get('error', 0) == 0:
        return "✅ 所有测试通过，无失败案例"

    analysis = []

    if summary.get('failed', 0) > 0:
        analysis.append(f"- **失败测试**: {summary['failed']} 个")

    if summary.get('error', 0) > 0:
        analysis.append(f"- **错误测试**: {summary['error']} 个")

    if summary.get('duration', 0) > 1800:  # 30分钟
        analysis.append(f"- **执行时间过长**: {summary['duration']/60:.1f} 分钟")

    analysis.append("\n请查看详细的 HTML 报告获取具体失败原因。")

    return "\n".join(analysis)


def generate_recommendations(summary):
    """生成改进建议"""
    recommendations = []

    if not summary['success']:
        recommendations.append("- 🚨 优先修复失败的测试用例")
        recommendations.append("- 🔍 检查 Staging 环境配置和服务状态")

    if summary.get('failed', 0) / max(summary.get('total', 1), 1) > 0.1:
        recommendations.append("- 📈 修复失败测试以提高成功率")

    if summary.get('duration', 0) > 600:  # 10分钟
        recommendations.append("- ⚡ 优化测试执行速度")

    if summary.get('total', 0) < 20:
        recommendations.append("- 📝 增加更多 E2E 测试用例以覆盖更多场景")

    if not recommendations:
        recommendations.append("- ✅ 测试状态良好，继续保持")

    return "\n".join(recommendations)


def update_history(summary):
    """更新历史记录"""
    history_path = "docs/_reports/E2E_TEST_HISTORY.md"

    history_entry = f"| {summary['timestamp']} | {summary.get('total', 'N/A')} | {summary.get('passed', 0)} | {summary.get('failed', 0)} | {summary.get('skipped', 0)} | {summary['elapsed_time']:.2f}s | {'✅' if summary['success'] else '❌'} |\n"

    # 读取或创建历史文件
    if Path(history_path).exists():
        with open(history_path, 'r') as f:
            content = f.read()
        # 在表格后添加新行
        if '\n---\n\n' in content:
            content = content.replace('\n---\n\n', f'\n{history_entry}---\n\n')
        else:
            content += f'\n{history_entry}'
    else:
        content = f"""# E2E 测试历史记录

| 时间 | 总数 | 通过 | 失败 | 跳过 | 耗时 | 状态 |
|------|------|------|------|------|------|------|
{history_entry}
"""

    with open(history_path, 'w') as f:
        f.write(content)


def cleanup_environment():
    """清理环境"""
    print("\n🧹 清理环境...")

    response = input("\n是否停止 Staging 环境？(y/N): ").strip().lower()

    if response == 'y' or response == 'yes':
        result = subprocess.run(
            ["./scripts/manage_staging_env.sh", "stop"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Staging 环境已停止")
        else:
            print(f"⚠️ 停止环境时出错: {result.stderr}")
    else:
        print("ℹ️ Staging 环境保持运行状态")
        print("   使用 './scripts/manage_staging_env.sh stop' 手动停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="E2E 测试运行器")
    parser.add_argument(
        "--type",
        choices=["all", "smoke", "critical", "performance", "regression"],
        default="all",
        help="测试类型 (default: all)"
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        help="额外的 pytest 标签"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="测试后不清理环境"
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="跳过环境设置"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🧪 端到端测试运行器")
    print("=" * 60)

    # 检查先决条件
    if not check_prerequisites():
        print("\n❌ 先决条件检查失败，退出")
        sys.exit(1)

    try:
        # 设置环境
        if not args.skip_setup:
            if not setup_staging_environment():
                print("\n❌ 无法设置测试环境")
                sys.exit(1)

        # 运行测试
        success, summary = run_e2e_tests(
            test_type=args.type,
            tags=args.tags,
            verbose=args.verbose
        )

        # 生成报告
        generate_report(summary)

        # 打印摘要
        print("\n" + "=" * 60)
        print("📊 E2E 测试摘要")
        print("=" * 60)
        print(f"状态: {'✅ 成功' if success else '❌ 失败'}")
        print(f"类型: {summary['test_type']}")
        print(f"总测试: {summary.get('total', 'N/A')}")
        print(f"通过: {summary.get('passed', 0)}")
        print(f"失败: {summary.get('failed', 0)}")
        print(f"跳过: {summary.get('skipped', 0)}")
        print(f"耗时: {summary['elapsed_time']:.2f} 秒")
        print("=" * 60)

        # 清理环境
        if not args.no_cleanup:
            cleanup_environment()

        # 设置退出码
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        if not args.no_cleanup:
            cleanup_environment()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        if not args.no_cleanup:
            cleanup_environment()
        sys.exit(1)


if __name__ == "__main__":
    main()
