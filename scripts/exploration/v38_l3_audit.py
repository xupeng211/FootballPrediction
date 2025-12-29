#!/usr/bin/env python3
"""
V38.0 L3 特征工程审计 - 数据发现脚本
=======================================

任务：
A. 多维结构抽样（英超/意甲/老赛季）
B. 球员评分专项搜救
C. 关键特征覆盖率矩阵
D. 性能压力初探

作者: Data Discovery Specialist
日期: 2025-12-29
Phase: L3 Feature Engineering Audit
"""

import asyncio
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import asyncpg
from tabulate import tabulate

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================
# 数据库连接
# ============================================
async def get_db_pool():
    """获取数据库连接池"""
    import subprocess

    # 从 Docker 获取数据库密码
    result = subprocess.run(
        ["docker", "exec", "football_prediction_db", "printenv", "POSTGRES_PASSWORD"],
        capture_output=True,
        text=True,
    )
    db_password = result.stdout.strip() or "football123"

    return await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="football_prediction_dev",
        user="football_user",
        password=db_password,
        min_size=1,
        max_size=3,
    )


# ============================================
# 任务 A: 多维结构抽样
# ============================================
async def sample_match_structure(
    pool: asyncpg.Pool, league_id: int, season_start: str, season_end: str, label: str
) -> dict:
    """
    提取指定联赛/赛季的 JSON 结构样本

    返回 stats 下所有 key 的列表
    """
    # 转换字符串为 date 对象
    start_date = date.fromisoformat(season_start)
    end_date = date.fromisoformat(season_end)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT r.raw_data
            FROM raw_match_data r
            JOIN matches m ON r.match_id = m.match_id
            WHERE m.league_id = $1
              AND m.match_date >= $2
              AND m.match_date < $3
            ORDER BY m.match_date DESC
            LIMIT 5
            """,
            league_id,
            start_date,
            end_date,
        )

        if not rows:
            return {"label": label, "status": "no_data", "keys": []}

        # 提取所有唯一的 key
        all_keys = set()

        for row in rows:
            raw_data = row["raw_data"]
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            # 路径: raw_data -> 'raw_data' -> 'content' -> 'stats' -> 'Periods' -> 'All' -> 'stats'
            try:
                raw_api = raw_data.get("raw_data", {})
                content = raw_api.get("content", {})
                stats_obj = content.get("stats", {})

                if not stats_obj:
                    continue

                periods = stats_obj.get("Periods") or stats_obj.get("Period")
                if not periods or not isinstance(periods, dict):
                    continue

                all_stats = periods.get("All", {})
                if not all_stats:
                    continue

                stats_array = all_stats.get("stats", [])
                if not stats_array:
                    continue

                # 遍历 stats 数组提取所有 key
                for stat_group in stats_array:
                    for stat in stat_group.get("stats", []):
                        key = stat.get("key", "")
                        if key:
                            all_keys.add(key)

            except Exception:
                continue

        return {"label": label, "status": "success", "keys": sorted(list(all_keys))}


# ============================================
# 任务 B: 球员评分专项搜救
# ============================================
async def lineup_forensics(pool: asyncpg.Pool) -> dict:
    """
    深入分析 lineup 结构，查找评分字段
    """
    async with pool.acquire() as conn:
        # 获取最近一场英超比赛
        row = await conn.fetchrow(
            """
            SELECT r.raw_data, m.home_team, m.away_team, m.match_date
            FROM raw_match_data r
            JOIN matches m ON r.match_id = m.match_id
            WHERE m.league_id = 47
            ORDER BY m.match_date DESC NULLS LAST
            LIMIT 1
            """
        )

        if not row:
            return {"status": "no_data"}

        raw_data = row["raw_data"]
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        raw_api = raw_data.get("raw_data", {})
        content = raw_api.get("content", {})

        # 尝试不同的路径
        lineup_paths = [
            "lineup",
            "lineUps",
        ]

        result = {
            "status": "success",
            "match_info": f"{row['home_team']} vs {row['away_team']} on {row['match_date']}",
            "lineup_found": False,
            "players_found": False,
            "rating_keys": [],
            "sample_player": None,
        }

        lineup = None
        for path in lineup_paths:
            lineup = content.get(path)
            if lineup:
                result["lineup_found"] = True
                result["lineup_path"] = f"content -> {path}"
                break

        if not lineup:
            return result

        # 查找 starters 或 home/away
        teams_data = {}
        if "starters" in lineup:
            teams_data["starters"] = lineup["starters"]
        if "home" in lineup:
            teams_data["home"] = lineup["home"]
        if "away" in lineup:
            teams_data["away"] = lineup["away"]

        # 深度遍历查找球员数据
        for team_key, team_data in teams_data.items():
            players = team_data.get("players") if isinstance(team_data, dict) else []
            if players and isinstance(players, list) and len(players) > 0:
                result["players_found"] = True
                sample_player = players[0]

                # 提取所有键
                all_keys = list(sample_player.keys())

                # 查找评分相关的键
                rating_keywords = ["rating", "score", "points", "stats"]
                rating_keys = [k for k in all_keys if any(kw in k.lower() for kw in rating_keywords)]

                result["sample_player"] = {
                    "path": f"content -> lineup -> {team_key} -> players[0]",
                    "all_keys": all_keys,
                    "rating_keys": rating_keys,
                    "sample_data": {k: sample_player.get(k) for k in all_keys[:10]},  # 前10个字段
                }

                if rating_keys:
                    result["rating_keys"] = rating_keys
                    result["rating_sample"] = {k: sample_player.get(k) for k in rating_keys}

                break

        return result


# ============================================
# 任务 C: 关键特征覆盖率矩阵
# ============================================
async def coverage_matrix(pool: asyncpg.Pool) -> dict:
    """
    统计关键特征的非空比例
    """
    async with pool.acquire() as conn:
        # 获取总数
        total = await conn.fetchval("SELECT COUNT(*) FROM raw_match_data")

        # 定义要检查的路径
        paths = [
            ("expected_goals", "raw_data->'raw_data'->'content'->'stats'->'Periods'->'All'->'stats'"),
            ("big_chance_created", "raw_data->'raw_data'->'content'->'stats'->'Periods'->'All'->'stats'"),
            ("BallPossession", "raw_data->'raw_data'->'content'->'stats'->'Periods'->'All'->'stats'"),
            ("shots_on_target", "raw_data->'raw_data'->'content'->'stats'->'Periods'->'All'->'stats'"),
        ]

        results = []

        for feature_name, jsonb_path in paths:
            # 检查该路径是否存在非空值
            # 注意：这里使用简化检查，实际需要根据具体路径调整
            count = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM raw_match_data
                WHERE {jsonb_path} IS NOT NULL
                LIMIT 1
                """
            )

            # 使用更精确的方法：检查特定字段
            # 由于嵌套复杂，我们使用 jsonb_path_query
            results.append(
                {
                    "feature": feature_name,
                    "path": jsonb_path,
                    "has_data": count > 0,
                    "note": "需要深度扫描确认确切覆盖率",
                }
            )

        return {"total_records": total, "features": results}


# ============================================
# 任务 D: 性能压力初探
# ============================================
async def performance_test(pool: asyncpg.Pool) -> dict:
    """
    测试 JSONB 查询性能
    """
    async with pool.acquire() as conn:
        # 测试 1: 简单路径查询
        start = time.time()
        rows = await conn.fetch(
            """
            SELECT raw_data->'raw_data'->'content'->'stats'->'Periods'->'All'->'stats' as stats
            FROM raw_match_data
            LIMIT 1000
            """
        )
        simple_query_time = (time.time() - start) * 1000  # 转换为毫秒

        # 测试 2: 深度路径查询
        start = time.time()
        rows = await conn.fetch(
            """
            SELECT jsonb_path_query_first(
                raw_data->'raw_data',
                '$.content.stats.Periods.All.stats[*] ? (@.key == "expectedGoals").stats'
            ) as xg
            FROM raw_match_data
            WHERE jsonb_path_exists(
                raw_data->'raw_data',
                '$.content.stats.Periods.All.stats[*] ? (@.key == "expectedGoals")'
            )
            LIMIT 1000
            """
        )
        deep_query_time = (time.time() - start) * 1000

        # 测试 3: 聚合查询
        start = time.time()
        avg = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM raw_match_data
            WHERE raw_data->'raw_data'->'content' IS NOT NULL
            LIMIT 1000
            """
        )
        agg_query_time = (time.time() - start) * 1000

        return {
            "simple_query_ms": round(simple_query_time, 2),
            "deep_query_ms": round(deep_query_time, 2),
            "agg_query_ms": round(agg_query_time, 2),
            "rows_tested": 1000,
        }


# ============================================
# 报告生成
# ============================================
def generate_report(
    structure_samples: list,
    lineup_result: dict,
    coverage_result: dict,
    performance_result: dict,
) -> str:
    """生成综合审计报告"""

    report = []
    report.append("=" * 100)
    report.append(" " * 35 + "V38.0 L3 特征工程审计报告")
    report.append("=" * 100)
    report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # ==================== 任务 A: 多维结构抽样 ====================
    report.append("=" * 100)
    report.append("任务 A: 多维结构抽样 (Cross-Section Sampling)")
    report.append("=" * 100)
    report.append("\n目标: 对比英超、意甲、老赛季的 JSON 结构一致性\n")

    structure_table = []
    for sample in structure_samples:
        if sample["status"] == "no_data":
            structure_table.append([sample["label"], "❌ 无数据", "-"])
        elif sample["status"] == "success":
            keys_str = ", ".join(sample["keys"][:10])  # 显示前10个
            if len(sample["keys"]) > 10:
                keys_str += f" ... (+{len(sample['keys']) - 10} more)"
            structure_table.append([sample["label"], f"✅ {len(sample['keys'])} 个字段", keys_str])

    report.append(
        tabulate(
            structure_table,
            headers=["样本类型", "状态", "统计字段 (前10个)"],
            tablefmt="grid",
        )
    )

    # 一致性分析
    report.append("\n📊 结构一致性分析:")
    successful_samples = [s for s in structure_samples if s["status"] == "success"]
    if len(successful_samples) >= 2:
        all_keys_sets = [set(s["keys"]) for s in successful_samples]
        common_keys = set.intersection(*all_keys_sets) if all_keys_sets else set()
        all_unique_keys = set.union(*all_keys_sets) if all_keys_sets else set()

        consistency_rate = len(common_keys) / len(all_unique_keys) * 100 if all_unique_keys else 0

        report.append(f"  - 共同字段数量: {len(common_keys)}")
        report.append(f"  - 独特字段总数: {len(all_unique_keys)}")
        report.append(f"  - 结构一致性: {consistency_rate:.1f}%")

        if consistency_rate >= 90:
            report.append("  - ✅ 评估: 结构高度一致，可使用统一提取逻辑")
        elif consistency_rate >= 70:
            report.append("  - ⚠️ 评估: 结构基本一致，需处理少量差异")
        else:
            report.append("  - ❌ 评估: 结构差异较大，需要分联赛/赛季处理")
    else:
        report.append("  - ⚠️ 样本不足，无法进行一致性分析")

    # ==================== 任务 B: 球员评分专项搜救 ====================
    report.append("\n\n")
    report.append("=" * 100)
    report.append("任务 B: 球员评分专项搜救 (Lineup Forensics)")
    report.append("=" * 100)

    if lineup_result["status"] == "no_data":
        report.append("\n❌ 未找到任何比赛数据\n")
    else:
        report.append(f"\n比赛: {lineup_result['match_info']}")
        report.append(f"Lineup 路径: {lineup_result.get('lineup_path', '未找到')}")

        if lineup_result["players_found"] and lineup_result["sample_player"]:
            sample = lineup_result["sample_player"]
            report.append(f"\n球员路径: {sample['path']}")
            report.append(f"\n所有字段 ({len(sample['all_keys'])} 个):")
            report.append(f"  {', '.join(sample['all_keys'])}")

            if lineup_result["rating_keys"]:
                report.append("\n🎯 评分相关字段:")
                for key in lineup_result["rating_keys"]:
                    value = lineup_result["rating_sample"].get(key, "N/A")
                    report.append(f"  - {key}: {value}")

                report.append("\n✅ 结论: 球员评分字段已定位，可用于 L3 特征工程")
            else:
                report.append("\n⚠️ 结论: 未找到明确的评分字段，需要进一步探索")
        else:
            report.append("\n❌ 未找到球员数据")

    # ==================== 任务 C: 关键特征覆盖率矩阵 ====================
    report.append("\n\n")
    report.append("=" * 100)
    report.append("任务 C: 关键特征覆盖率矩阵")
    report.append("=" * 100)
    report.append(f"\n总记录数: {coverage_result['total_records']:,}\n")

    coverage_table = []
    for feature in coverage_result["features"]:
        status_icon = "✅" if feature["has_data"] else "❓"
        coverage_table.append([feature["feature"], status_icon, feature["note"]])

    report.append(tabulate(coverage_table, headers=["特征", "状态", "说明"], tablefmt="grid"))

    report.append("\n⚠️ 注意: 覆盖率需要更精确的深度扫描确认")

    # ==================== 任务 D: 性能压力初探 ====================
    report.append("\n\n")
    report.append("=" * 100)
    report.append("任务 D: 性能压力初探 (JSONB Query Performance)")
    report.append("=" * 100)
    report.append(f"\n测试规模: {performance_result['rows_tested']:,} 条记录\n")

    perf_table = [
        ["简单路径查询", f"{performance_result['simple_query_ms']:.2f}", "raw_data->'raw_data'->'content'->'stats'"],
        ["深度路径查询", f"{performance_result['deep_query_ms']:.2f}", "jsonb_path_query with filter"],
        ["聚合查询", f"{performance_result['agg_query_ms']:.2f}", "COUNT with path exists"],
    ]

    report.append(tabulate(perf_table, headers=["查询类型", "耗时 (ms)", "说明"], tablefmt="grid"))

    # 性能评估
    avg_time = (
        performance_result["simple_query_ms"] + performance_result["deep_query_ms"] + performance_result["agg_query_ms"]
    ) / 3

    report.append(f"\n平均查询耗时: {avg_time:.2f} ms")

    if avg_time < 100:
        report.append("✅ 评估: JSONB 查询性能优秀，适合实时特征提取")
    elif avg_time < 500:
        report.append("⚠️ 评估: JSONB 查询性能可接受，建议添加索引优化")
    else:
        report.append("❌ 评估: JSONB 查询性能较慢，建议考虑物化视图或预计算")

    # ==================== 总体结论 ====================
    report.append("\n\n")
    report.append("=" * 100)
    report.append("📋 总体结论与建议")
    report.append("=" * 100)

    successful_samples_count = len([s for s in structure_samples if s["status"] == "success"])
    rating_found = lineup_result.get("rating_keys") is not None and len(lineup_result["rating_keys"]) > 0

    if successful_samples_count >= 2 and rating_found:
        report.append("\n✅ 数据结构高度一致，球员评分字段已定位")
        report.append("   建议: 可以立即开始 L3 特征工程开发")
    elif successful_samples_count >= 2:
        report.append("\n⚠️ 数据结构基本一致，但球员评分字段需要进一步确认")
        report.append("   建议: 继续深入探索 lineup 数据结构")
    else:
        report.append("\n❌ 数据结构存在较大差异或数据不足")
        report.append("   建议: 需要扩大样本范围或考虑分联赛处理")

    report.append("\n" + "=" * 100)

    return "\n".join(report)


# ============================================
# 主流程
# ============================================
async def main():
    print("🔍 V38.0 L3 特征工程审计启动...")
    print("=" * 100)

    pool = await get_db_pool()

    try:
        # 任务 A: 多维结构抽样
        print("\n📊 [任务 A] 执行多维结构抽样...")
        structure_samples = await asyncio.gather(
            sample_match_structure(pool, 47, "2023-08-01", "2024-07-01", "英超 23/24 赛季"),
            sample_match_structure(pool, 55, "2023-08-01", "2024-07-01", "意甲 23/24 赛季"),
            sample_match_structure(pool, 47, "2020-08-01", "2021-07-01", "英超 20/21 赛季"),
        )
        print(f"  ✅ 完成 {len(structure_samples)} 个样本的结构分析")

        # 任务 B: 球员评分专项搜救
        print("\n🎯 [任务 B] 执行球员评分专项搜救...")
        lineup_result = await lineup_forensics(pool)
        print(f"  ✅ Lineup 路径: {lineup_result.get('lineup_path', '未找到')}")
        if lineup_result.get("rating_keys"):
            print(f"  ✅ 找到评分字段: {', '.join(lineup_result['rating_keys'])}")

        # 任务 C: 关键特征覆盖率矩阵
        print("\n📈 [任务 C] 计算关键特征覆盖率...")
        coverage_result = await coverage_matrix(pool)
        print(f"  ✅ 总记录数: {coverage_result['total_records']:,}")

        # 任务 D: 性能压力初探
        print("\n⚡ [任务 D] 执行性能压力测试...")
        performance_result = await performance_test(pool)
        print(
            f"  ✅ 平均查询耗时: {(performance_result['simple_query_ms'] + performance_result['deep_query_ms'] + performance_result['agg_query_ms']) / 3:.2f} ms"
        )

        # 生成综合报告
        print("\n📝 生成综合审计报告...")
        report = generate_report(
            structure_samples,
            lineup_result,
            coverage_result,
            performance_result,
        )

        print("\n" + report)

        # 保存报告
        report_path = project_root / "logs" / "v38_l3_audit_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📝 报告已保存至: {report_path}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
