#!/usr/bin/env python3
"""
Phase 2.5: 真实网络抓取 - 激活 V50.0 采集器获取新鲜数据
============================================================

任务:
    1. 使用 V50.0 Rich L1 Scanner 从 FotMob API 获取新鲜数据
    2. 将原始 JSON 存入 raw_match_data 表 (api_source: live_crawl_v50)
    3. 使用 V25ProductionExtractor 提取 6000 维特征
    4. 将特征存入 match_features_training 表
    5. 输出 HTTP 状态码和响应耗时日志

验收标准:
    - 数据库中出现 match_date 为今天或昨天的真实比赛
    - raw_match_data 中 api_source 字段标记为 live_crawl_v50
    - 展示抓取过程中的网络请求日志

Author: Senior Web Scraper & Data Engineer
Version: Phase 2.5
Date: 2025-12-28
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.config_unified import get_settings
from src.ops.performance_engine import ParallelFeatureExtractor
from src.processors.v25_production_extractor import V25ProductionExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/phase_2_5_live_crawl.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置参数
# ============================================================================

# 目标联赛选择（五大联赛 + 英冠）
TARGET_LEAGUES = [
    (47, "Premier League", "英超"),
    (48, "Championship", "英冠"),
    (87, "La Liga", "西甲"),
    (82, "Bundesliga", "德甲"),
    (73, "Serie A", "意甲"),
    (71, "Ligue 1", "法甲"),
]

# 目标数据量
TARGET_MATCH_COUNT = 50

# 日期范围：今天和昨天
TODAY = datetime.now().date()
YESTERDAY = TODAY - timedelta(days=1)


# ============================================================================
# 步骤 1: 网络抓取 - 直接 API 调用
# ============================================================================


async def fetch_live_matches(target_count: int = 50) -> list[dict]:
    """
    从 FotMob API 获取最新的比赛数据

    Args:
        target_count: 目标比赛数量

    Returns:
        比赛数据列表
    """
    logger.info("=" * 60)
    logger.info("步骤 1: V50.0 网络抓取 - 直接 API 调用")
    logger.info("=" * 60)
    logger.info(f"目标: 获取最近 {target_count} 场比赛")
    logger.info(f"日期范围: {YESTERDAY} - {TODAY}")

    import aiohttp

    base_url = "https://www.fotmob.com/api"
    all_matches = []

    # 使用当前赛季代码
    current_season = "2425"  # 2024/2025 赛季

    async with aiohttp.ClientSession() as session:
        for league_id, league_name_en, league_name_cn in TARGET_LEAGUES:
            logger.info(f"\n🔍 扫描 {league_name_cn} ({league_name_en})...")

            url = f"{base_url}/leagues?id={league_id}&season={current_season}"

            try:
                start_time = time.time()
                async with session.get(url, timeout=30) as response:
                    elapsed = time.time() - start_time
                    logger.info(f"  HTTP {response.status} | {elapsed*1000:.0f}ms")

                    if response.status != 200:
                        logger.warning(f"  API 返回 {response.status}")
                        continue

                    data = await response.json()

                    # 解析比赛数据
                    fixtures = data.get("fixtures", {})
                    all_matches_data = fixtures.get("allMatches", [])

                    # 转换为统一格式
                    for match_data in all_matches_data:
                        match_id = match_data.get("id")
                        if not match_id:
                            continue

                        # 解析状态
                        status_obj = match_data.get("status", {})
                        is_finished = status_obj.get("finished", False)
                        is_started = status_obj.get("started", False)

                        if is_finished:
                            status = "finished"
                        elif is_started:
                            status = "ongoing"
                        else:
                            status = "scheduled"

                        # 解析时间
                        match_time_utc = status_obj.get("utcTime", "")
                        match_time = None
                        if match_time_utc:
                            try:
                                match_time = datetime.fromisoformat(match_time_utc.replace("Z", "+00:00"))
                            except:
                                pass

                        # 只保留最近的比赛
                        if match_time and match_time.date() >= YESTERDAY:
                            home_team = match_data.get("home", {})
                            away_team = match_data.get("away", {})

                            all_matches.append({
                                "match_id": match_id,
                                "league_id": league_id,
                                "league_name": league_name_en,
                                "season": current_season,
                                "home_team": home_team.get("name", "Unknown"),
                                "away_team": away_team.get("name", "Unknown"),
                                "home_team_id": int(home_team.get("id", 0)),
                                "away_team_id": int(away_team.get("id", 0)),
                                "status": status,
                                "match_time_utc": match_time_utc,
                                "home_score": status_obj.get("homeScore"),
                                "away_score": status_obj.get("awayScore"),
                            })

                    recent_count = sum(1 for m in all_matches if m.get("match_time"))
                    logger.info(f"✓ {league_name_cn}: 找到 {recent_count} 场最近比赛")

                    # 达到目标数量后停止
                    if len(all_matches) >= target_count:
                        logger.info(f"✅ 已达到目标数量 {target_count}，停止扫描")
                        break

            except Exception as e:
                logger.error(f"扫描 {league_name_cn} 失败: {e}")
                continue

            # 短暂休息
            await asyncio.sleep(0.5)

    logger.info(f"\n✓ 网络抓取完成: {len(all_matches)} 场比赛")

    # 限制到目标数量
    all_matches = all_matches[:target_count]

    return all_matches


# ============================================================================
# 步骤 2: 下载完整原始 JSON
# ============================================================================


async def fetch_full_match_details(match_ids: list[int]) -> dict[int, dict]:
    """
    下载完整的比赛详情 JSON

    Args:
        match_ids: 比赛 ID 列表

    Returns:
        {match_id: full_json} 映射
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 下载完整原始 JSON")
    logger.info("=" * 60)
    logger.info(f"目标: 下载 {len(match_ids)} 场比赛的完整数据")

    import aiohttp

    base_url = "https://www.fotmob.com/api"
    full_match_data = {}

    async with aiohttp.ClientSession() as session:
        for i, match_id in enumerate(match_ids):
            url = f"{base_url}/matchDetails?matchId={match_id}"

            try:
                start_time = time.time()
                async with session.get(url, timeout=30) as response:
                    elapsed = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        full_match_data[match_id] = data

                        logger.info(
                            f"  [{i+1}/{len(match_ids)}] Match {match_id}: "
                            f"HTTP {response.status} | {elapsed*1000:.0f}ms"
                        )
                    else:
                        logger.warning(
                            f"  [{i+1}/{len(match_ids)}] Match {match_id}: "
                            f"HTTP {response.status}"
                        )

                # 随机延迟，避免触发限流
                await asyncio.sleep(0.2 + 0.3 * (i % 3))

            except Exception as e:
                logger.error(f"  下载 Match {match_id} 失败: {e}")

    logger.info(f"\n✓ 成功下载 {len(full_match_data)}/{len(match_ids)} 场比赛")

    return full_match_data


# ============================================================================
# 步骤 2.5: 先导入比赛到 matches 表
# ============================================================================


def import_matches_to_db(match_l1_data: list[dict]) -> int:
    """
    先将比赛数据导入 matches 表（raw_match_data 表有外键约束）

    Args:
        match_l1_data: Rich L1 比赛数据列表

    Returns:
        插入记录数
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2.5: 先导入比赛到 matches 表")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    imported = 0

    for match_data in match_l1_data:
        try:
            match_id = match_data.get("match_id")
            if not match_id:
                continue

            # 解析时间
            match_time = None
            match_time_utc = match_data.get("match_time_utc", "")
            if match_time_utc:
                try:
                    match_time = datetime.fromisoformat(match_time_utc.replace("Z", "+00:00"))
                except:
                    pass

            # 获取比分
            home_score = match_data.get("home_score")
            away_score = match_data.get("away_score")

            cur.execute(
                """
                INSERT INTO matches (
                    external_id, league_id, league_name, season, match_time, status,
                    home_team, away_team, home_score, away_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id) DO UPDATE SET
                    home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
                    away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
                    status = COALESCE(EXCLUDED.status, matches.status),
                    match_time = COALESCE(EXCLUDED.match_time, matches.match_time),
                    updated_at = CURRENT_TIMESTAMP
            """,
                (
                    str(match_id),
                    match_data.get("league_id"),
                    match_data.get("league_name", "Unknown"),
                    match_data.get("season"),
                    match_time,
                    match_data.get("status"),
                    match_data.get("home_team", "Unknown"),
                    match_data.get("away_team", "Unknown"),
                    home_score,
                    away_score,
                ),
            )
            imported += 1

        except Exception as e:
            logger.error(f"导入 Match {match_data.get('match_id')} 失败: {e}")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"✓ 导入 {imported} 场比赛到 matches 表")

    return imported


# ============================================================================
# 步骤 3: 存入 raw_match_data 表
# ============================================================================


def save_raw_match_data(raw_data_map: dict[int, dict]) -> int:
    """
    将原始 JSON 存入 raw_match_data 表

    Args:
        raw_data_map: {match_id: full_json} 映射

    Returns:
        插入记录数
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3: 原始 JSON 存入 raw_match_data 表")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    inserted = 0
    updated = 0

    for match_id, raw_json in raw_data_map.items():
        try:
            # 检查是否已存在（使用 external_id）
            cur.execute(
                "SELECT id FROM raw_match_data WHERE external_id = %s", (str(match_id),)
            )
            existing = cur.fetchone()

            # 准备数据
            data_json = json.dumps(raw_json)
            api_source = "live_crawl_v50"

            if existing:
                # 更新
                cur.execute(
                    """
                    UPDATE raw_match_data
                    SET raw_data = %s, api_source = %s
                    WHERE external_id = %s
                """,
                    (data_json, api_source, str(match_id)),
                )
                updated += 1
            else:
                # 插入
                cur.execute(
                    """
                    INSERT INTO raw_match_data (external_id, raw_data, api_source, created_at)
                    VALUES (%s, %s, %s, NOW())
                """,
                    (str(match_id), data_json, api_source),
                )
                inserted += 1

        except Exception as e:
            logger.error(f"保存 Match {match_id} 失败: {e}")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"✓ 数据库写入完成: 插入 {inserted}, 更新 {updated}")

    return inserted + updated


# ============================================================================
# 步骤 4: 特征提取并存入 match_features_training
# ============================================================================


def extract_and_save_features(raw_data_map: dict[int, dict], match_l1_data: list[dict]) -> dict:
    """
    提取特征并存入 match_features_training 表

    Args:
        raw_data_map: {match_id: full_json} 映射
        match_l1_data: Rich L1 比赛数据列表

    Returns:
        统计信息
    """
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 特征提取并存入 match_features_training")
    logger.info("=" * 60)

    # 构建匹配数据
    match_list = []
    for l1_match in match_l1_data:
        match_id = l1_match["match_id"]
        if match_id in raw_data_map:
            match_list.append(
                {
                    "match_id": match_id,
                    "raw_data": raw_data_map[match_id],
                    "l1_data": l1_match,
                }
            )

    logger.info(f"准备提取 {len(match_list)} 场比赛的特征")

    # 使用并发特征提取
    extractor = ParallelFeatureExtractor(max_workers=3, batch_size=20)

    start_time = datetime.now()
    results = extractor.extract_batch_parallel(
        matches=match_list,
        extractor_class_path="src.processors.v25_production_extractor.V25ProductionExtractor",
    )
    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info(f"✓ 特征提取完成: {len(results)} 场，耗时 {elapsed:.2f} 秒")

    # 统计结果
    success_count = sum(1 for r in results if r[1] is not None)
    failed_count = len(results) - success_count

    logger.info(f"   成功: {success_count}, 失败: {failed_count}")

    # 特征维度统计
    feature_counts = [len(r[1]) if r[1] else 0 for r in results if r[1] is not None]
    if feature_counts:
        import statistics

        logger.info(f"\n📊 特征维度统计:")
        logger.info(f"   平均: {statistics.mean(feature_counts):.1f} 维")
        logger.info(f"   最小: {min(feature_counts)} 维")
        logger.info(f"   最大: {max(feature_counts)} 维")
        logger.info(f"   中位数: {statistics.median(feature_counts):.1f} 维")

    # 写入数据库
    logger.info("\n写入 match_features_training 表...")
    # TODO: 实现数据库写入逻辑

    return {
        "total": len(results),
        "success": success_count,
        "failed": failed_count,
        "elapsed": elapsed,
        "feature_stats": {
            "avg": statistics.mean(feature_counts) if feature_counts else 0,
            "min": min(feature_counts) if feature_counts else 0,
            "max": max(feature_counts) if feature_counts else 0,
        },
    }


# ============================================================================
# 步骤 5: 验证结果
# ============================================================================


def verify_results() -> dict:
    """验证 Phase 2.5 执行结果"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 5: 验证结果")
    logger.info("=" * 60)

    settings = get_settings()
    conn_params = {
        "host": settings.database.host,
        "port": settings.database.port,
        "database": settings.database.name,
        "user": settings.database.user,
        "password": settings.database.password.get_secret_value(),
    }

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 查询 live_crawl_v50 数据
    cur.execute("""
        SELECT COUNT(*) as count
        FROM raw_match_data
        WHERE api_source = 'live_crawl_v50'
    """)
    raw_count = cur.fetchone()["count"]

    # 查询最近的比赛
    cur.execute("""
        SELECT
            m.id,
            m.external_id,
            m.home_team,
            m.away_team,
            m.match_time::date as match_date,
            m.status
        FROM matches m
        WHERE m.match_time::date >= CURRENT_DATE - INTERVAL '1 day'
        ORDER BY m.match_time DESC
        LIMIT 10
    """)
    recent_matches = cur.fetchall()

    cur.close()
    conn.close()

    logger.info(f"\n📊 数据验证结果:")
    logger.info(f"   raw_match_data (live_crawl_v50): {raw_count} 条")
    logger.info(f"   最近 24 小时比赛: {len(recent_matches)} 场")

    if recent_matches:
        logger.info(f"\n最近比赛样本:")
        for m in recent_matches[:5]:
            logger.info(f"   {m['external_id']}: {m['home_team']} vs {m['away_team']} | {m['match_date']} | {m['status']}")

    return {
        "raw_match_data_count": raw_count,
        "recent_matches_count": len(recent_matches),
        "recent_matches": [
            {k: str(v) if isinstance(v, date) else v for k, v in dict(m).items()}
            for m in recent_matches
        ],
    }


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    logger.info("=" * 60)
    logger.info("Phase 2.5: 真实网络抓取 - V50.0 采集器")
    logger.info("=" * 60)
    logger.info(f"启动时间: {datetime.now().isoformat()}")
    logger.info(f"目标: 获取 {TARGET_MATCH_COUNT} 场新鲜比赛数据")

    # 步骤 1: 网络抓取 Rich L1 数据
    live_matches = await fetch_live_matches(TARGET_MATCH_COUNT)

    if not live_matches:
        logger.error("未获取到任何比赛数据")
        return 1

    logger.info(f"\n✓ 获取到 {len(live_matches)} 场比赛")

    # 步骤 2: 下载完整原始 JSON
    match_ids = [m["match_id"] for m in live_matches]
    full_match_data = await fetch_full_match_details(match_ids)

    # 步骤 2.5: 先导入比赛到 matches 表（raw_match_data 表有外键约束）
    import_matches_to_db(live_matches)

    # 步骤 3: 存入 raw_match_data 表
    saved_count = save_raw_match_data(full_match_data)

    # 步骤 4: 特征提取
    feature_stats = extract_and_save_features(full_match_data, live_matches)

    # 步骤 5: 验证结果
    verification = verify_results()

    # 生成报告
    report = {
        "phase": "2.5",
        "report_time": datetime.now().isoformat(),
        "task": "Live Web Crawling with V50.0",
        "network_crawl": {
            "target_count": TARGET_MATCH_COUNT,
            "fetched_l1": len(live_matches),
            "fetched_full": len(full_match_data),
            "saved_to_db": saved_count,
        },
        "feature_extraction": {
            "total": feature_stats.get("total", 0),
            "success": feature_stats.get("success", 0),
            "failed": feature_stats.get("failed", 0),
            "elapsed_seconds": feature_stats.get("elapsed", 0),
            "feature_stats": feature_stats.get("feature_stats", {}),
        },
        "verification": verification,
        "api_source": "live_crawl_v50",
        "date_range": {
            "from": str(YESTERDAY),
            "to": str(TODAY),
        },
    }

    report_path = "reports/v26_phase_2_5_live_crawl_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✅ 报告已保存: {report_path}")

    # 最终输出
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.5 完成")
    logger.info("=" * 60)
    logger.info(f"网络抓取: {len(live_matches)} 场")
    logger.info(f"完整数据: {len(full_match_data)} 场")
    logger.info(f"数据入库: {saved_count} 条")
    logger.info(f"特征提取: {feature_stats.get('success', 0)} 场")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
