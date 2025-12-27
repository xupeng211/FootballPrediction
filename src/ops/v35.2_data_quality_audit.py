#!/usr/bin/env python3
"""
V35.2 数据质量审计
==================
使用零容忍校验标准审计现有数据，标记不符合标准的记录
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings


def validate_payload(l2_data: dict, match_id: int) -> tuple:
    """
    V35.2: 零容忍数据校验

    Returns:
        (is_valid, reason): 是否通过校验及原因
    """
    # 检查 1: 必须有 content
    content = l2_data.get("content")
    if not content or not isinstance(content, dict):
        return False, "Missing or invalid 'content' field"

    # 检查 2: 必须有 stats 或 shotmap
    has_stats = bool(content.get("stats"))
    has_shotmap = bool(content.get("shotmap"))

    if not (has_stats or has_shotmap):
        return False, "Missing both 'stats' and 'shotmap'"

    # 检查 3: 关键字段不能为空
    general = l2_data.get("general", {})
    if not general.get("homeTeam") or not general.get("awayTeam"):
        return False, "Missing home_team or away_team"

    # 检查 4: stats 数据质量检查
    if has_stats:
        stats = content["stats"]
        if not isinstance(stats, dict):
            return False, "Invalid 'stats' format (not a dict)"

        # 至少要有一些统计组
        if len(stats) < 2:
            return False, f"Insufficient stats groups ({len(stats)} < 2)"

    return True, "OK"


def audit_database_data():
    """审计数据库中的现有数据"""

    print("=" * 70)
    print("V35.2 数据质量审计")
    print("=" * 70)

    settings = get_settings()
    db = settings.database

    # 检测环境 - 检查是否真的在 Docker 容器内
    def check_in_docker():
        try:
            with open("/proc/1/cgroup") as f:
                return "docker" in f.read()
        except:
            return False

    is_docker = check_in_docker()
    import socket

    db_host_env = os.getenv("DB_HOST", "db")
    db_port = int(os.getenv("DB_PORT", 5432))
    db_name = os.getenv("DB_NAME", "football_db")
    db_user = os.getenv("DB_USER", "football_user")
    db_pass = os.getenv("DB_PASSWORD", "football_pass")

    # 在非 Docker 环境下，优先使用 localhost
    if not is_docker:
        try:
            socket.create_connection(("localhost", db_port), timeout=1)
            db_host = "localhost"
            print(f"🔍 使用本地数据库: localhost:{db_port}")
        except:
            db_host = "localhost"  # 尝试 localhost
            print("⚠️ 尝试使用 localhost")
    else:
        db_host = db_host_env

    # 连接数据库
    print(f"连接参数: host={db_host}, port={db_port}, db={db_name}, user={db_user}")
    conn = psycopg2.connect(host=db_host, port=db_port, database=db_name, user=db_user, password=db_pass)

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 获取所有 V35.1 数据
    cursor.execute("""
        SELECT match_id, league_id, season_id, home_team, away_team,
               enriched_features, extraction_version
        FROM match_features_training
        WHERE extraction_version LIKE 'V35.1%'
        ORDER BY match_id
    """)

    records = cursor.fetchall()
    total_count = len(records)

    print(f"\n📊 审计范围: {total_count:,} 条记录")
    print("   数据版本: V35.1-HOLOGRAPHIC, V35.1-LEGACY")

    # 审计统计
    audit_results = {
        "total": total_count,
        "valid": 0,
        "rejected": 0,
        "by_reason": defaultdict(int),
        "by_version": defaultdict(lambda: {"valid": 0, "rejected": 0}),
    }

    rejected_matches = []

    for record in records:
        match_id = record["match_id"]
        enriched_features = record.get("enriched_features", {})

        # 构建 L2 数据结构用于验证
        # enriched_features 包含 holographic_features 和 raw_match_info
        l2_data = {
            "content": {},
            "general": {"homeTeam": record.get("home_team"), "awayTeam": record.get("away_team"), "matchId": match_id},
        }

        # 检查是否有 holographic_features
        if "holographic_features" in enriched_features:
            holographic = enriched_features["holographic_features"]

            # 尝试重构 content 字段
            if "raw_stats" in holographic:
                l2_data["content"]["stats"] = holographic["raw_stats"]
            if "shotmap_data" in holographic:
                l2_data["content"]["shotmap"] = holographic["shotmap_data"]

        # 执行零容忍校验
        is_valid, reason = validate_payload(l2_data, match_id)

        version = record.get("extraction_version", "UNKNOWN")

        if is_valid:
            audit_results["valid"] += 1
            audit_results["by_version"][version]["valid"] += 1
        else:
            audit_results["rejected"] += 1
            audit_results["by_version"][version]["rejected"] += 1
            audit_results["by_reason"][reason] += 1

            rejected_matches.append(
                {
                    "match_id": match_id,
                    "league_id": record.get("league_id"),
                    "season_id": record.get("season_id"),
                    "home_team": record.get("home_team"),
                    "away_team": record.get("away_team"),
                    "version": version,
                    "rejection_reason": reason,
                }
            )

    # 打印审计结果
    print("\n" + "=" * 70)
    print("审计结果")
    print("=" * 70)

    print(f"\n✅ 通过校验: {audit_results['valid']:,} ({audit_results['valid'] / audit_results['total'] * 100:.1f}%)")
    print(f"❌ 拒绝: {audit_results['rejected']:,} ({audit_results['rejected'] / audit_results['total'] * 100:.1f}%)")

    print("\n📋 按版本分布:")
    for version in sorted(audit_results["by_version"].keys()):
        stats = audit_results["by_version"][version]
        total = stats["valid"] + stats["rejected"]
        print(f"   {version}:")
        print(f"      通过: {stats['valid']:,} ({stats['valid'] / total * 100:.1f}%)")
        print(f"      拒绝: {stats['rejected']:,} ({stats['rejected'] / total * 100:.1f}%)")

    if audit_results["by_reason"]:
        print("\n🚫 拒绝原因分布:")
        for reason, count in sorted(audit_results["by_reason"].items(), key=lambda x: x[1], reverse=True):
            print(f"   {count:4d} - {reason}")

    # 保存被拒绝的比赛列表
    if rejected_matches:
        bad_matches_log = Path("data/logs/bad_matches_audit_v35.2.log")
        bad_matches_log.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()
        log_entry = {
            "audit_timestamp": timestamp,
            "total_audited": total_count,
            "total_rejected": len(rejected_matches),
            "rejected_matches": rejected_matches,
        }

        with open(bad_matches_log, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)

        print(f"\n💾 拒绝记录已保存: {bad_matches_log}")

    print("\n" + "=" * 70)
    print("✅ V35.2 数据质量审计完成")
    print("=" * 70)

    cursor.close()
    conn.close()

    return audit_results


if __name__ == "__main__":
    audit_database_data()
