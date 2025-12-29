#!/usr/bin/env python3
"""
V37.4 L2 采集数据灾难恢复脚本
=====================================

用途：
1. 一键清空 raw_match_data 表（L2 详情数据）
2. 一键清空 collection_audit_logs 表（审计日志）

使用场景：
- API 封禁后需要重新采集
- 数据质量严重下降需要重置
- 测试环境数据清理

安全措施：
1. 二次确认机制
2. Dry-run 模式预览
3. 不可逆操作警告

作者: ML Architect
日期: 2025-12-29
Phase: Production-Grade
Version: V37.4
"""

import argparse
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings


# ============================================
# ANSI 颜色代码
# ============================================
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ============================================
# 数据库操作
# ============================================
def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


def count_raw_match_data(conn) -> int:
    """统计 raw_match_data 表记录数"""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM raw_match_data;")
        result = cur.fetchone()
        return result["count"] if result else 0


def count_audit_logs(conn) -> int:
    """统计 collection_audit_logs 表记录数"""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM collection_audit_logs;")
        result = cur.fetchone()
        return result["count"] if result else 0


def truncate_raw_match_data(conn, dry_run: bool = False) -> None:
    """清空 raw_match_data 表"""
    if dry_run:
        print(f"{Colors.YELLOW}[DRY-RUN] 将执行: TRUNCATE TABLE raw_match_data CASCADE;{Colors.RESET}")
        return

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw_match_data CASCADE;")
        conn.commit()
        print(f"{Colors.GREEN}✅ raw_match_data 表已清空{Colors.RESET}")


def truncate_audit_logs(conn, dry_run: bool = False) -> None:
    """清空 collection_audit_logs 表"""
    if dry_run:
        print(f"{Colors.YELLOW}[DRY-RUN] 将执行: TRUNCATE TABLE collection_audit_logs;{Colors.RESET}")
        return

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE collection_audit_logs;")
        conn.commit()
        print(f"{Colors.GREEN}✅ collection_audit_logs 表已清空{Colors.RESET}")


def truncate_all(conn, dry_run: bool = False) -> None:
    """清空所有 L2 采集相关表"""
    truncate_raw_match_data(conn, dry_run)
    truncate_audit_logs(conn, dry_run)


# ============================================
# 预览信息
# ============================================
def show_preview(conn) -> None:
    """显示当前数据统计"""
    raw_count = count_raw_match_data(conn)
    audit_count = count_audit_logs(conn)

    print(f"\n{Colors.BOLD}{Colors.BLUE}═════════════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  L2 采集数据统计预览{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}═════════════════════════════════════════════════════════{Colors.RESET}\n")

    print(f"📊 {Colors.BOLD}raw_match_data{Colors.RESET}: {raw_count:,} 条记录")
    print(f"📊 {Colors.BOLD}collection_audit_logs{Colors.RESET}: {audit_count:,} 条记录")

    if raw_count > 0:
        # 获取最早和最晚的采集时间
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    MIN(created_at) as earliest,
                    MAX(created_at) as latest
                FROM raw_match_data;
            """
            )
            result = cur.fetchone()
            if result and result["earliest"]:
                print("\n⏰ 采集时间范围:")
                print(f"   最早: {result['earliest']}")
                print(f"   最晚: {result['latest']}")

    print()


# ============================================
# 确认机制
# ============================================
def confirm_action(action: str) -> bool:
    """二次确认操作"""
    print(f"\n{Colors.RED}{Colors.BOLD}⚠️  警告：此操作不可逆！{Colors.RESET}")
    print(f"{Colors.RED}您即将执行: {action}{Colors.RESET}")
    print(f"{Colors.YELLOW}请输入 'YES I CONFIRM' 以确认操作:{Colors.RESET}")

    response = input("\n> ").strip()

    return response == "YES I CONFIRM"


# ============================================
# 主流程
# ============================================
def main():
    parser = argparse.ArgumentParser(
        description="V37.4 L2 采集数据灾难恢复脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览数据统计
  python scripts/maintenance/reset_l2_collection.py --preview

  # 清空 raw_match_data 表
  python scripts/maintenance/reset_l2_collection.py --raw-data --confirm

  # 清空所有 L2 采集表
  python scripts/maintenance/reset_l2_collection.py --all --confirm

  # Dry-run 模式（不实际执行）
  python scripts/maintenance/reset_l2_collection.py --all --dry-run
        """,
    )

    parser.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="预览当前数据统计",
    )

    parser.add_argument(
        "--raw-data",
        "-r",
        action="store_true",
        help="清空 raw_match_data 表",
    )

    parser.add_argument(
        "--audit-logs",
        "-a",
        action="store_true",
        help="清空 collection_audit_logs 表",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="清空所有 L2 采集表",
    )

    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Dry-run 模式（不实际执行）",
    )

    parser.add_argument(
        "--confirm",
        "-c",
        action="store_true",
        help="跳过二次确认（危险！）",
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="强制执行（跳过所有确认，极度危险！）",
    )

    args = parser.parse_args()

    # 如果没有任何操作，显示帮助
    if not any([args.preview, args.raw_data, args.audit_logs, args.all]):
        parser.print_help()
        return 0

    # 连接数据库
    try:
        conn = get_db_connection()
        print(f"{Colors.GREEN}✅ 数据库连接成功{Colors.RESET}\n")
    except Exception as e:
        print(f"{Colors.RED}❌ 数据库连接失败: {e}{Colors.RESET}")
        return 1

    try:
        # 预览模式
        if args.preview:
            show_preview(conn)
            return 0

        # 确定执行的操作
        action_desc = ""
        if args.all:
            action_desc = "清空所有 L2 采集表（raw_match_data + collection_audit_logs）"
        elif args.raw_data:
            action_desc = "清空 raw_match_data 表"
        elif args.audit_logs:
            action_desc = "清空 collection_audit_logs 表"

        # Dry-run 模式
        if args.dry_run:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}[DRY-RUN 模式]{Colors.RESET}")
            show_preview(conn)

            if args.all:
                truncate_all(conn, dry_run=True)
            elif args.raw_data:
                truncate_raw_match_data(conn, dry_run=True)
            elif args.audit_logs:
                truncate_audit_logs(conn, dry_run=True)

            print(f"\n{Colors.YELLOW}ℹ️  Dry-run 完成，未实际执行任何操作{Colors.RESET}")
            return 0

        # 强制模式（跳过所有确认）
        if args.force:
            print(f"\n{Colors.RED}{Colors.BOLD}🚨 强制执行模式{Colors.RESET}\n")

            if args.all:
                truncate_all(conn)
            elif args.raw_data:
                truncate_raw_match_data(conn)
            elif args.audit_logs:
                truncate_audit_logs(conn)

            print(f"\n{Colors.GREEN}✅ 操作完成{Colors.RESET}")
            return 0

        # 正常模式（需要确认）
        show_preview(conn)

        if not args.confirm:
            if not confirm_action(action_desc):
                print(f"\n{Colors.YELLOW}❌ 操作已取消{Colors.RESET}")
                return 0

        # 执行操作
        print(f"\n{Colors.BOLD}正在执行操作...{Colors.RESET}\n")

        if args.all:
            truncate_all(conn)
        elif args.raw_data:
            truncate_raw_match_data(conn)
        elif args.audit_logs:
            truncate_audit_logs(conn)

        # 显示操作后统计
        print(f"\n{Colors.BOLD}操作后统计:{Colors.RESET}")
        show_preview(conn)

        print(f"{Colors.GREEN}{Colors.BOLD}✅ 操作完成{Colors.RESET}\n")

        return 0

    except Exception as e:
        print(f"\n{Colors.RED}❌ 执行失败: {e}{Colors.RESET}\n")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
