#!/usr/bin/env python3
"""
V35.2 脏数据拦截演示
=====================
展示净水器如何识别并拦截不完整的脏数据
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


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
        return False, f"Missing both 'stats' and 'shotmap' (has_stats={has_stats}, has_shotmap={has_shotmap})"

    # 检查 3: 关键字段不能为空
    general = l2_data.get("general", {})
    if not general.get("homeTeam") or not general.get("awayTeam"):
        return False, "Missing home_team or away_team in general data"

    # 检查 4: match_id 必须存在且匹配
    api_match_id = general.get("matchId") or general.get("id")
    if api_match_id and int(api_match_id) != match_id:
        return False, f"Match ID mismatch: requested={match_id}, response={api_match_id}"

    # 检查 5: stats 数据质量检查
    if has_stats:
        stats = content["stats"]
        if not isinstance(stats, dict):
            return False, "Invalid 'stats' format (not a dict)"

        # 至少要有一些统计组
        if len(stats) < 2:
            return False, f"Insufficient stats groups ({len(stats)} < 2)"

    return True, "OK"


def demonstrate_dirty_data_rejection():
    """演示脏数据拦截"""

    print("=" * 70)
    print("V35.2 脏数据拦截演示")
    print("=" * 70)

    # 案例 1: 缺失 content 的脏数据
    dirty_data_1 = {
        "general": {"matchId": 4813374, "homeTeam": {"name": "Liverpool"}, "awayTeam": {"name": "Chelsea"}},
        # 缺失 content 字段
    }

    print("\n📋 案例 1: 缺失 'content' 字段的脏数据")
    print("-" * 70)
    print(json.dumps(dirty_data_1, indent=2)[:300] + "...")

    is_valid, reason = validate_payload(dirty_data_1, 4813374)
    print(f"\n校验结果: {'❌ 拒绝' if not is_valid else '✅ 通过'}")
    print(f"拒绝原因: {reason}")

    # 案例 2: 有 content 但缺失 stats 和 shotmap
    dirty_data_2 = {
        "content": {
            # 只有基本信息，没有 stats 和 shotmap
            "matchFacts": {"homeTeam": "Liverpool", "awayTeam": "Chelsea"}
        },
        "general": {"matchId": 4813375, "homeTeam": {"name": "Liverpool"}, "awayTeam": {"name": "Chelsea"}},
    }

    print("\n" + "=" * 70)
    print("📋 案例 2: 缺失 'stats' 和 'shotmap' 的脏数据")
    print("-" * 70)
    print(json.dumps(dirty_data_2, indent=2)[:400] + "...")

    is_valid, reason = validate_payload(dirty_data_2, 4813375)
    print(f"\n校验结果: {'❌ 拒绝' if not is_valid else '✅ 通过'}")
    print(f"拒绝原因: {reason}")

    # 案例 3: 缺失 homeTeam 的脏数据
    dirty_data_3 = {
        "content": {"stats": {"possession": {"home": 55, "away": 45}}},
        "general": {
            "matchId": 4813376,
            # 缺失 homeTeam 和 awayTeam
        },
    }

    print("\n" + "=" * 70)
    print("📋 案例 3: 缺失 homeTeam/awayTeam 的脏数据")
    print("-" * 70)
    print(json.dumps(dirty_data_3, indent=2)[:300] + "...")

    is_valid, reason = validate_payload(dirty_data_3, 4813376)
    print(f"\n校验结果: {'❌ 拒绝' if not is_valid else '✅ 通过'}")
    print(f"拒绝原因: {reason}")

    # 案例 4: 正常的全血数据
    clean_data = {
        "content": {
            "stats": {
                "possession": {"home": 55, "away": 45},
                "totalShots": {"home": 15, "away": 8},
                "shotsOnTarget": {"home": 6, "away": 2},
            },
            "shotmap": {"shots": [{"x": 80, "y": 40, "expectedGoals": 0.5}]},
        },
        "general": {"matchId": 4813377, "homeTeam": {"name": "Liverpool"}, "awayTeam": {"name": "Chelsea"}},
    }

    print("\n" + "=" * 70)
    print("📋 案例 4: 正常的全血数据")
    print("-" * 70)
    print(json.dumps(clean_data, indent=2)[:400] + "...")

    is_valid, reason = validate_payload(clean_data, 4813377)
    print(f"\n校验结果: {'✅ 通过' if is_valid else '❌ 拒绝'}")
    print(f"说明: {reason}")

    # 创建日志文件
    bad_matches_log = Path("data/logs/bad_matches_v35.2.log")
    bad_matches_log.parent.mkdir(parents=True, exist_ok=True)

    # 记录被拒绝的数据
    timestamp = datetime.now().isoformat()
    for case_id, data, reason in [
        (4813374, dirty_data_1, "Missing or invalid 'content' field"),
        (4813375, dirty_data_2, "Missing both 'stats' and 'shotmap'"),
        (4813376, dirty_data_3, "Missing home_team or awayTeam"),
    ]:
        log_entry = {
            "timestamp": timestamp,
            "match_id": case_id,
            "rejection_reason": reason,
            "data_preview": {
                "has_content": "content" in data,
                "has_stats": bool(data.get("content", {}).get("stats")),
                "has_shotmap": bool(data.get("content", {}).get("shotmap")),
                "has_general": bool(data.get("general")),
            },
        }
        with open(bad_matches_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(f"\n💾 脏数据日志: {bad_matches_log}")
    print("   已记录: 3 条被拦截的脏数据")

    print("\n" + "=" * 70)
    print("✅ 脏数据拦截演示完成")
    print("=" * 70)
    print("\n📊 拦截统计:")
    print("   ✅ 案例 1: 拒绝 - 缺失 'content' 字段")
    print("   ✅ 案例 2: 拒绝 - 缺失 'stats' 和 'shotmap'")
    print("   ✅ 案例 3: 拒绝 - 缺失 'homeTeam/awayTeam'")
    print("   ✅ 案例 4: 通过 - 完整全血数据")


if __name__ == "__main__":
    demonstrate_dirty_data_rejection()
