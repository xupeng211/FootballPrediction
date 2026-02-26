#!/usr/bin/env python3
"""
V143.9: 数据库大一统验证脚本
==========================

功能：
1. 验证只存在一个 PostgreSQL 实例（Docker PostgreSQL 15）
2. 验证 WSL2 本地 PostgreSQL 14 已停止
3. 验证数据库连接指向正确的实例
4. 验证 matches 表 schema 完整性

Author: Senior Systems Architect
Version: V143.9
Date: 2026-01-06
"""

import os
import sys
import subprocess
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import psycopg2
from src.config_unified import get_settings


def check_local_postgresql_stopped() -> Dict[str, Any]:
    """检查 WSL2 本地 PostgreSQL 14 是否已停止"""
    result = {"status": "unknown", "details": ""}

    try:
        # 尝试检查服务状态
        output = subprocess.check_output(
            ["service", "postgresql", "status"],
            stderr=subprocess.STDOUT,
            text=True
        )

        if "inactive (dead)" in output:
            result["status"] = "pass"
            result["details"] = "✅ 本地 PostgreSQL 14 已停止"
        elif "active (exited)" in output or "active (running)" in output:
            result["status"] = "fail"
            result["details"] = "❌ 本地 PostgreSQL 14 仍在运行！"
        else:
            result["status"] = "warning"
            result["details"] = f"⚠️  状态未知: {output}"

    except Exception as e:
        # 如果 service 命令失败，尝试检查端口占用
        try:
            output = subprocess.check_output(
                ["ss", "-tlnp"],
                stderr=subprocess.STDOUT,
                text=True
            )
            if ":5432" in output and "postgres" in output.lower():
                result["status"] = "warning"
                result["details"] = "⚠️  端口 5432 仍被 PostgreSQL 进程占用"
            else:
                result["status"] = "pass"
                result["details"] = "✅ 端口 5432 未被本地 PostgreSQL 占用"
        except Exception:
            result["status"] = "skip"
            result["details"] = "⊘ 无法检查服务状态（非 root 权限）"

    return result


def check_docker_postgresql_running() -> Dict[str, Any]:
    """检查 Docker PostgreSQL 15 是否正在运行"""
    result = {"status": "unknown", "details": ""}

    try:
        # 检查 Docker 容器状态
        output = subprocess.check_output(
            ["docker-compose", "ps", "db"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            stderr=subprocess.STDOUT,
            text=True
        )

        if "Up" in output and "football_prediction_db" in output:
            result["status"] = "pass"
            result["details"] = "✅ Docker PostgreSQL 15 正在运行"
        else:
            result["status"] = "fail"
            result["details"] = "❌ Docker PostgreSQL 15 未运行"

    except Exception as e:
        result["status"] = "fail"
        result["details"] = f"❌ 无法检查 Docker 状态: {e}"

    return result


def check_database_connection() -> Dict[str, Any]:
    """检查数据库连接并验证版本（通过 Docker Compose）"""
    result = {"status": "unknown", "details": "", "version": None}

    try:
        # 使用 docker-compose exec 来连接数据库
        output = subprocess.check_output(
            ["docker-compose", "exec", "-T", "db", "psql", "-U", "football_user",
             "-d", "football_prediction_dev", "-c", "SELECT version();"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            stderr=subprocess.DEVNULL,
            text=True
        )

        # 提取版本信息
        version = output.strip()

        # 检查版本
        if "PostgreSQL 15" in version:
            result["status"] = "pass"
            result["version"] = "15"
            result["details"] = "✅ 连接到 PostgreSQL 15 (Docker)"
        elif "PostgreSQL 14" in version:
            result["status"] = "fail"
            result["version"] = "14"
            result["details"] = "❌ 连接到 PostgreSQL 14 (本地) - 配置错误！"
        else:
            result["status"] = "warning"
            # 提取版本号
            for word in version.split():
                if word[0].isdigit():
                    result["version"] = word.split(".")[0]
                    break
            result["details"] = f"⚠️  连接到 PostgreSQL {result['version']}"

    except Exception as e:
        result["status"] = "fail"
        result["details"] = f"❌ 数据库连接失败: {e}"

    return result


def check_matches_table_schema() -> Dict[str, Any]:
    """检查 matches 表 schema 完整性（通过 Docker Compose）"""
    result = {"status": "unknown", "details": "", "missing_columns": []}

    try:
        # 使用 docker-compose exec 来查询数据库
        output = subprocess.check_output(
            ["docker-compose", "exec", "-T", "db", "psql", "-U", "football_user",
             "-d", "football_prediction_dev", "-c",
             "SELECT column_name FROM information_schema.columns WHERE table_name = 'matches' ORDER BY column_name;"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            stderr=subprocess.DEVNULL,
            text=True
        )

        # 解析输出（跳过表头和分隔线）
        columns = set()
        for line in output.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('+') and not line.startswith('column'):
                columns.add(line)

        # 必需的列
        required_columns = {
            "match_id", "external_id", "league_name", "season",
            "home_team", "away_team", "match_time", "match_date",
            "status", "oddsportal_url"
        }

        missing_columns = required_columns - columns
        result["missing_columns"] = list(missing_columns)

        if missing_columns:
            result["status"] = "fail"
            result["details"] = f"❌ 缺少列: {', '.join(missing_columns)}"
        else:
            result["status"] = "pass"
            result["details"] = f"✅ matches 表 schema 完整 ({len(columns)} 列)"

    except Exception as e:
        result["status"] = "fail"
        result["details"] = f"❌ Schema 检查失败: {e}"

    return result


def print_header(title: str) -> None:
    """打印标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_check(check_name: str, result: Dict[str, Any]) -> None:
    """打印检查结果"""
    status_icon = {
        "pass": "✅ PASS",
        "fail": "❌ FAIL",
        "warning": "⚠️  WARN",
        "skip": "⊘ SKIP",
        "unknown": "❓ UNKNOWN"
    }

    icon = status_icon.get(result["status"], "❓ UNKNOWN")
    print(f"\n{icon}  {check_name}")
    print(f"   {result['details']}")

    # 打印额外信息
    if "version" in result:
        print(f"   版本: PostgreSQL {result['version']}")
    if "missing_columns" in result and result["missing_columns"]:
        print(f"   缺失列: {', '.join(result['missing_columns'])}")


def main():
    """主函数"""
    print_header("V143.9: 数据库大一统验证")

    # 执行所有检查
    checks = {
        "1. 本地 PostgreSQL 14 停止检查": check_local_postgresql_stopped(),
        "2. Docker PostgreSQL 15 运行检查": check_docker_postgresql_running(),
        "3. 数据库连接版本检查": check_database_connection(),
        "4. matches 表 schema 完整性": check_matches_table_schema(),
    }

    # 打印结果
    for check_name, result in checks.items():
        print_check(check_name, result)

    # 汇总结果
    print_header("验证汇总")

    pass_count = sum(1 for r in checks.values() if r["status"] == "pass")
    fail_count = sum(1 for r in checks.values() if r["status"] == "fail")
    warning_count = sum(1 for r in checks.values() if r["status"] == "warning")

    print(f"\n  通过: {pass_count}")
    print(f"  失败: {fail_count}")
    print(f"  警告: {warning_count}")
    print(f"  总计: {len(checks)}")

    # 最终判定
    all_passed = fail_count == 0

    print("\n" + "=" * 70)
    if all_passed:
        print("  🎉 数据库大一统验证通过！")
        print("  ✅ 系统已完全迁移到 Docker PostgreSQL 15")
    else:
        print("  ❌ 数据库大一统验证失败！")
        print("  ⚠️  请解决上述问题后继续")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
