#!/usr/bin/env python3
"""
V29.0 Feature Extraction - 特征炼金厂 (Feature Alchemy)

功能：从数据库提取赔率特征，处理残缺 JSON

数据流：
1. fetch_from_clean_view() - 从 v_matches_clean 读取数据
2. 从 odds 表构建 l3_features 格式
3. extract_features_from_json() - 提取 Opening/Closing/High_24h/Low_24h
4. save_features_to_db() - 存入 match_features 表

TDD 流程：
- Red Phase: 测试失败（功能未实现）
- Green Phase: 实现功能，测试通过
- Refactor Phase: 优化代码（可选）

测试场景：
- 残缺的 JSON（缺少字段）→ 返回默认值而不崩溃 ✅
- 空的 JSON → 返回空特征字典 ✅
- 正常的 JSON → 正确提取特征 ✅
- None/null 处理 → 转换为 Python None ✅

Author: 高级数据架构师 & 机器学习专家
Date: 2026-01-11
Version: V29.0 (Feature Extraction)
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )


# ============================================================================
# 特征提取
# ============================================================================

def extract_features_from_json(match_data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """从比赛数据中提取赔率特征

    处理残缺 JSON 的健壮逻辑：
    - 缺少字段 → 返回 None 而不崩溃
    - null 值 → 保留为 Python None
    - 空字典 → 所有特征返回 None

    Args:
        match_data: 包含 l3_features 的比赛数据字典

    Returns:
        包含所有赔率特征的特征字典
    """
    features: Dict[str, Optional[float]] = {}

    # 安全提取辅助函数
    def safe_extract(
        source: Optional[Dict[str, Any]],
        category: str,
        field: str
    ) -> Optional[float]:
        """安全提取嵌套字段，处理 None 和缺失"""
        if source is None:
            return None
        if category not in source:
            return None
        category_data = source[category]
        if category_data is None or not isinstance(category_data, dict):
            return None
        value = category_data.get(field)
        # null 值转换为 None
        return None if value is None else float(value)

    # 获取 l3_features
    l3_features = match_data.get("l3_features") if match_data else None

    if l3_features is None or not isinstance(l3_features, dict):
        # l3_features 不存在，返回全 None 特征
        return {
            "opening_home": None, "opening_draw": None, "opening_away": None,
            "closing_home": None, "closing_draw": None, "closing_away": None,
            "high_24h_home": None, "high_24h_draw": None, "high_24h_away": None,
            "low_24h_home": None, "low_24h_draw": None, "low_24h_away": None,
        }

    # 提取初盘赔率 (Opening)
    features["opening_home"] = safe_extract(l3_features, "opening", "home")
    features["opening_draw"] = safe_extract(l3_features, "opening", "draw")
    features["opening_away"] = safe_extract(l3_features, "opening", "away")

    # 提取终盘赔率 (Closing)
    features["closing_home"] = safe_extract(l3_features, "closing", "home")
    features["closing_draw"] = safe_extract(l3_features, "closing", "draw")
    features["closing_away"] = safe_extract(l3_features, "closing", "away")

    # 提取 24h 最高赔率 (High 24h)
    features["high_24h_home"] = safe_extract(l3_features, "high_24h", "home")
    features["high_24h_draw"] = safe_extract(l3_features, "high_24h", "draw")
    features["high_24h_away"] = safe_extract(l3_features, "high_24h", "away")

    # 提取 24h 最低赔率 (Low 24h)
    features["low_24h_home"] = safe_extract(l3_features, "low_24h", "home")
    features["low_24h_draw"] = safe_extract(l3_features, "low_24h", "draw")
    features["low_24h_away"] = safe_extract(l3_features, "low_24h", "away")

    return features


# ============================================================================
# 数据库操作
# ============================================================================

def fetch_from_clean_view(limit: int = 100, incremental: bool = True) -> List[Dict[str, Any]]:
    """从 v_matches_clean 视图获取数据并构建 l3_features

    V29.1: 支持增量提取，默认排除已有特征的比赛。

    从 odds 表读取赔率数据，构建符合测试格式的 l3_features 结构。

    Args:
        limit: 最大返回记录数
        incremental: 是否使用增量模式（排除已处理比赛）- 默认 True

    Returns:
        包含 l3_features 的比赛数据列表
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # V29.1: 增量提取 - 排除已有特征的比赛
            # WHERE m.match_id NOT IN (SELECT match_id FROM match_features)
            where_clause = ""
            if incremental:
                where_clause = "WHERE m.match_id NOT IN (SELECT match_id FROM match_features)"

            # 获取比赛及其赔率数据
            cur.execute(f"""
                SELECT
                    m.match_id,
                    m.league_name,
                    m.home_team,
                    m.away_team,
                    COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'bookmaker', o.bookmaker,
                            'home_odds', o.home_odds,
                            'draw_odds', o.draw_odds,
                            'away_odds', o.away_odds,
                            'collected_at', o.collected_at
                        ) ORDER BY o.collected_at
                    ) FILTER (WHERE o.bookmaker IS NOT NULL), '[]') as odds_data
                FROM v_matches_clean m
                LEFT JOIN odds o ON m.match_id = o.match_id
                {where_clause}
                GROUP BY m.match_id, m.league_name, m.home_team, m.away_team
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()

            # 构建带 l3_features 的数据结构
            results = []
            for row in rows:
                match_data = {
                    "match_id": row["match_id"],
                    "league_name": row["league_name"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                }

                # 从 odds_data 构建 l3_features
                odds_list = row.get("odds_data", [])

                if odds_list:
                    # 简单策略：第一条作为 opening，最后一条作为 closing
                    # 实际项目中应根据 collected_at 时间戳判断
                    l3_features = {}

                    if odds_list:
                        first_odds = odds_list[0]
                        l3_features["opening"] = {
                            "home": first_odds.get("home_odds"),
                            "draw": first_odds.get("draw_odds"),
                            "away": first_odds.get("away_odds"),
                        }

                    if len(odds_list) > 1:
                        last_odds = odds_list[-1]
                        l3_features["closing"] = {
                            "home": last_odds.get("home_odds"),
                            "draw": last_odds.get("draw_odds"),
                            "away": last_odds.get("away_odds"),
                        }

                    # high_24h / low_24h - 简化实现，使用 max/min
                    all_home = [o.get("home_odds") for o in odds_list if o.get("home_odds")]
                    all_draw = [o.get("draw_odds") for o in odds_list if o.get("draw_odds")]
                    all_away = [o.get("away_odds") for o in odds_list if o.get("away_odds")]

                    if all_home:
                        l3_features["high_24h"] = {
                            "home": max(all_home),
                            "draw": max(all_draw) if all_draw else None,
                            "away": max(all_away) if all_away else None,
                        }
                        l3_features["low_24h"] = {
                            "home": min(all_home),
                            "draw": min(all_draw) if all_draw else None,
                            "away": min(all_away) if all_away else None,
                        }

                    match_data["l3_features"] = l3_features
                else:
                    # 无赔率数据，使用空字典
                    match_data["l3_features"] = {}

                results.append(match_data)

            return results

    finally:
        conn.close()


def save_features_to_db(features_list: List[Dict[str, Any]]) -> int:
    """保存特征到 match_features 表

    Args:
        features_list: 特征字典列表，每个字典包含 match_id 和赔率特征

    Returns:
        成功插入的记录数
    """
    if not features_list:
        logger.warning("没有特征需要保存")
        return 0

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            inserted_count = 0

            for features in features_list:
                match_id = features.get("match_id")
                if not match_id:
                    continue

                # 使用 UPSERT (ON CONFLICT) 处理重复
                cur.execute("""
                    INSERT INTO match_features (
                        match_id,
                        opening_home, opening_draw, opening_away,
                        closing_home, closing_draw, closing_away,
                        high_24h_home, high_24h_draw, high_24h_away,
                        low_24h_home, low_24h_draw, low_24h_away,
                        updated_at
                    ) VALUES (
                        %s, %s, %s, %s,  %s, %s, %s,  %s, %s, %s,  %s, %s, %s,  CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (match_id) DO UPDATE SET
                        opening_home = EXCLUDED.opening_home,
                        opening_draw = EXCLUDED.opening_draw,
                        opening_away = EXCLUDED.opening_away,
                        closing_home = EXCLUDED.closing_home,
                        closing_draw = EXCLUDED.closing_draw,
                        closing_away = EXCLUDED.closing_away,
                        high_24h_home = EXCLUDED.high_24h_home,
                        high_24h_draw = EXCLUDED.high_24h_draw,
                        high_24h_away = EXCLUDED.high_24h_away,
                        low_24h_home = EXCLUDED.low_24h_home,
                        low_24h_draw = EXCLUDED.low_24h_draw,
                        low_24h_away = EXCLUDED.low_24h_away,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    match_id,
                    features.get("opening_home"), features.get("opening_draw"), features.get("opening_away"),
                    features.get("closing_home"), features.get("closing_draw"), features.get("closing_away"),
                    features.get("high_24h_home"), features.get("high_24h_draw"), features.get("high_24h_away"),
                    features.get("low_24h_home"), features.get("low_24h_draw"), features.get("low_24h_away"),
                ))

                inserted_count += 1

            conn.commit()
            logger.info(f"成功保存 {inserted_count} 条特征记录")
            return inserted_count

    except Exception as e:
        conn.rollback()
        logger.error(f"保存特征失败: {e}")
        raise
    finally:
        conn.close()


# ============================================================================
# 完整流水线
# ============================================================================

def process_features_pipeline(limit: int = 100, incremental: bool = True) -> List[Dict[str, Any]]:
    """完整特征提取流水线

    V29.1: 支持增量提取模式，默认排除已处理比赛。

    流程：
    1. 从 v_matches_clean 获取数据（可选增量过滤）
    2. 提取特征
    3. 保存到 match_features 表

    Args:
        limit: 最大处理记录数
        incremental: 是否使用增量模式（排除已处理比赛）- 默认 True

    Returns:
        处理结果列表
    """
    mode = "增量" if incremental else "全量"
    logger.info(f"V29.1 特征炼金厂启动 ({mode}模式)，limit={limit}")

    try:
        # 1. 获取数据
        raw_data = fetch_from_clean_view(limit, incremental=incremental)
        logger.info(f"从 v_matches_clean 获取 {len(raw_data)} 条记录 ({mode})")

        # 2. 提取特征
        all_features = []
        for match_data in raw_data:
            features = extract_features_from_json(match_data)
            features["match_id"] = match_data.get("match_id")
            all_features.append(features)

        # 3. 保存特征
        saved_count = save_features_to_db(all_features)

        logger.info(f"特征提取完成: {saved_count}/{len(all_features)} 条保存成功")
        return all_features

    except Exception as e:
        logger.error(f"特征提取流水线失败: {e}")
        return []


# ============================================================================
# 主入口
# ============================================================================

def main():
    """主入口"""
    import argparse
    import time

    parser = argparse.ArgumentParser(description="V29.3 Feature Extraction - 炼金触发器")
    parser.add_argument("--limit", type=int, default=100,
                        help="最大处理记录数（默认: 100）")
    parser.add_argument("--dry-run", action="store_true",
                        help="干跑模式，不保存到数据库")
    parser.add_argument("--watch", action="store_true",
                        help="炼金触发器模式：每 10 分钟自动扫描新数据")
    parser.add_argument("--interval", type=int, default=600,
                        help="扫描间隔（秒），默认: 600 (10 分钟)")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("logs/v29_feature_extraction.log"),
            logging.StreamHandler()
        ]
    )

    if args.watch:
        # V29.3 炼金触发器模式
        logger.info("🔥 V29.3 炼金触发器启动")
        logger.info(f"扫描间隔: {args.interval} 秒 ({args.interval // 60} 分钟)")

        poll_count = 0
        while True:
            poll_count += 1
            logger.info(f"")
            logger.info("=" * 60)
            logger.info(f"🔍 第 {poll_count} 次扫描")
            logger.info("=" * 60)

            try:
                # 检查是否有新数据需要提取
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        # 统计差距
                        cur.execute("""
                            SELECT
                                (SELECT COUNT(*) FROM v_matches_clean) as total_matches,
                                (SELECT COUNT(*) FROM match_features) as extracted_features,
                                (SELECT COUNT(*) FROM odds) as total_odds
                        """)
                        row = cur.fetchone()
                        total_matches = row['total_matches'] if row else 0
                        extracted_features = row['extracted_features'] if row else 0
                        total_odds = row['total_odds'] if row else 0

                        gap = total_matches - extracted_features

                        logger.info(f"📊 数据状态:")
                        logger.info(f"   v_matches_clean: {total_matches}")
                        logger.info(f"   match_features: {extracted_features}")
                        logger.info(f"   odds 表: {total_odds}")
                        logger.info(f"   差距: {gap} 条待提取")

                        if gap > 0:
                            logger.info(f"✅ 检测到 {gap} 条新数据，开始提取...")

                            # 执行增量提取
                            results = process_features_pipeline(limit=args.limit, incremental=True)

                            if results:
                                logger.info(f"🎉 本次提取完成: {len(results)} 条特征")
                            else:
                                logger.warning(f"⚠️ 未提取到特征（可能 odds 表为空）")
                        else:
                            logger.info(f"✅ 数据已对齐，无需提取")

                finally:
                    conn.close()

            except Exception as e:
                logger.error(f"❌ 扫描失败: {e}")

            # 等待下一个扫描周期
            logger.info(f"⏰ 等待 {args.interval} 秒后进行下次扫描...")
            logger.info("=" * 60)
            time.sleep(args.interval)

    elif args.dry_run:
        logger.info("🔵 干跑模式：只提取特征，不保存到数据库")
        raw_data = fetch_from_clean_view(args.limit)
        logger.info(f"获取 {len(raw_data)} 条记录")

        for match_data in raw_data[:3]:  # 显示前 3 条
            features = extract_features_from_json(match_data)
            logger.info(f"Match {match_data.get('match_id')}: {features}")
    else:
        results = process_features_pipeline(args.limit)
        logger.info(f"✅ 处理完成，共 {len(results)} 条记录")


if __name__ == "__main__":
    main()
