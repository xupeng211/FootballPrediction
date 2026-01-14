#!/usr/bin/env python3
"""
V37.7 Feature Extraction - 特征炼金厂 (Feature Alchemy)

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

V36.3 更新：
- 支持三种 l3_odds_data 格式：
  1. 数组格式: {"home": [{"odds": "1.5"}], ...}
  2. Pinnacle 格式: {"pinnacle": {"home_odds": 1.5}}
  3. Average Odds 格式: {"closing_odds": {"Average Odds": {"home": 1.5}}}
- 失败记录保存到 logs/failed_features.json

V37.7 更新 (Bad Debt Fix):
- 修复增量逻辑：只排除 payout_ratio > 0 的比赛
- 允许重新提取 payout_ratio 为 NULL/0 的坏账比赛
- 根治"坏账累积"问题，无需手动运行 trigger_healing.py

Author: 高级数据架构师 & 机器学习专家
Date: 2026-01-12
Version: V37.7 (Bad Debt Fix + Auto-Healing)
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V33.2: 显式加载 .env 文件，确保环境变量正确注入
from dotenv import load_dotenv
import os
load_dotenv(override=True)

# V36.4 Final: 环境变量硬核固化 - DB_NAME 验证
DB_NAME = os.getenv('DB_NAME', '')
if DB_NAME != 'football_db':
    print("=" * 70)
    print("🚨 V36.4 Final: 环境变量验证失败！")
    print("=" * 70)
    print(f"❌ DB_NAME 必须等于 'football_db'")
    print(f"   当前值: '{DB_NAME}'")
    print()
    print("📋 当前环境变量:")
    for key, value in sorted(os.environ.items()):
        if 'DB_' in key or 'POSTGRES' in key or 'REDIS' in key or key.endswith('_PATH'):
            print(f"   {key} = {value}")
    print("=" * 70)
    sys.exit(1)

from src.config_unified import get_settings

logger = logging.getLogger(__name__)

# ============================================================================
# V36.3: 失败记录追踪
# ============================================================================

FAILED_FEATURES_LOG = Path("logs/failed_features.json")

def log_failed_extraction(match_id: str, format_type: str, raw_data: Any, reason: str):
    """记录提取失败的比赛数据到 failed_features.json

    Args:
        match_id: 比赛 ID
        format_type: 格式类型 (e.g., "unknown", "pinnacle", "array")
        raw_data: 原始数据
        reason: 失败原因
    """
    try:
        FAILED_FEATURES_LOG.parent.mkdir(exist_ok=True)

        # 读取现有记录
        existing = []
        if FAILED_FEATURES_LOG.exists():
            try:
                with open(FAILED_FEATURES_LOG, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError):
                existing = []

        # 添加新记录
        failure_record = {
            "match_id": match_id,
            "format_type": format_type,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "raw_data_sample": str(raw_data)[:500]  # 限制大小
        }

        existing.append(failure_record)

        # 保存（只保留最近 100 条）
        with open(FAILED_FEATURES_LOG, 'w', encoding='utf-8') as f:
            json.dump(existing[-100:], f, indent=2, ensure_ascii=False)

        logger.debug(f"记录失败提取: {match_id} - {reason}")

    except Exception as e:
        logger.warning(f"无法记录失败提取: {e}")


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """V36.0: 获取数据库连接（含显式验证日志）"""
    settings = get_settings()

    # V36.0: 显式验证数据库连接参数
    db_name = settings.database.name
    db_host = settings.database.host
    print(f"[DB_CONN] 当前连接数据库: {db_name} @ {db_host}")

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

    V36.3 支持两种数据格式：
    1. 旧格式 (dict): l3_features = {"opening": {"home": 1.85}, "closing": {...}}
    2. 新格式 (array): l3_odds_data = {"home": [{"odds": "1.85", ...}], ...}

    处理残缺 JSON 的健壮逻辑：
    - 缺少字段 → 返回 None 而不崩溃
    - null 值 → 保留为 Python None
    - 空字典 → 所有特征返回 None

    Args:
        match_data: 包含 l3_features 或 l3_odds_data 的比赛数据字典

    Returns:
        包含所有赔率特征的特征字典
    """
    features: Dict[str, Optional[float]] = {}

    # ============================================================================
    # V36.3: 双格式支持 - 优先尝试新格式 (l3_odds_data 数组)
    # ============================================================================

    if match_data and "l3_odds_data" in match_data:
        l3_odds_data = match_data.get("l3_odds_data")
        if l3_odds_data and isinstance(l3_odds_data, dict):
            # V38.0: Pinnacle flat format 检测
            # 格式: {"home_odds": 1.45, "draw_odds": 4.45, "away_odds": 6.75, "bookmaker": "Pinnacle"}
            if "home_odds" in l3_odds_data or "draw_odds" in l3_odds_data or "away_odds" in l3_odds_data:
                # 直接从 flat 字段提取赔率
                features["opening_home"] = l3_odds_data.get("home_odds")
                features["opening_draw"] = l3_odds_data.get("draw_odds")
                features["opening_away"] = l3_odds_data.get("away_odds")
                # Pinnacle flat format 没有 opening/closing 区分，使用相同值
                features["closing_home"] = l3_odds_data.get("home_odds")
                features["closing_draw"] = l3_odds_data.get("draw_odds")
                features["closing_away"] = l3_odds_data.get("away_odds")
                # 24h high/low 不可用
                features["high_24h_home"] = None
                features["high_24h_draw"] = None
                features["high_24h_away"] = None
                features["low_24h_home"] = None
                features["low_24h_draw"] = None
                features["low_24h_away"] = None

            # 数组格式提取：从 home/draw/away 数组中提取
            # Opening: 数组第一个元素
            # Closing: 数组最后一个元素
            elif "home" in l3_odds_data or "draw" in l3_odds_data or "away" in l3_odds_data:
                def safe_extract_array(
                    source: Optional[Dict[str, Any]],
                    bet_type: str,
                    index: int
                ) -> Optional[float]:
                    """从数组格式安全提取赔率

                    Args:
                        source: l3_odds_data 字典
                        bet_type: "home", "draw", "away"
                        index: 0 表示第一个 (Opening), -1 表示最后一个 (Closing)

                    Returns:
                        赔率值 (float) 或 None
                    """
                    if source is None or bet_type not in source:
                        return None
                    odds_array = source[bet_type]
                    if not odds_array or not isinstance(odds_array, list):
                        return None
                    try:
                        element = odds_array[index]
                        if element and isinstance(element, dict) and "odds" in element:
                            odds_str = element["odds"]
                            # 转换为 float
                            return float(odds_str) if odds_str else None
                    except (IndexError, ValueError, TypeError):
                        pass
                    return None

                # 提取 Opening (数组第一个元素)
                features["opening_home"] = safe_extract_array(l3_odds_data, "home", 0)
                features["opening_draw"] = safe_extract_array(l3_odds_data, "draw", 0)
                features["opening_away"] = safe_extract_array(l3_odds_data, "away", 0)

                # 提取 Closing (数组最后一个元素)
                features["closing_home"] = safe_extract_array(l3_odds_data, "home", -1)
                features["closing_draw"] = safe_extract_array(l3_odds_data, "draw", -1)
                features["closing_away"] = safe_extract_array(l3_odds_data, "away", -1)

                # 数组格式暂不支持 high_24h/low_24h（需要计算）
                features["high_24h_home"] = None
                features["high_24h_draw"] = None
                features["high_24h_away"] = None
            features["low_24h_home"] = None
            features["low_24h_draw"] = None
            features["low_24h_away"] = None

        else:
            # l3_odds_data 存在但无效，返回全 None
            return {
                "opening_home": None, "opening_draw": None, "opening_away": None,
                "closing_home": None, "closing_draw": None, "closing_away": None,
                "high_24h_home": None, "high_24h_draw": None, "high_24h_away": None,
                "low_24h_home": None, "low_24h_draw": None, "low_24h_away": None,
            }

    elif match_data and "l3_features" in match_data:
        # ============================================================================
        # 旧格式 (dict): l3_features 兼容模式
        # ============================================================================
        l3_features = match_data.get("l3_features")

        if l3_features is None or not isinstance(l3_features, dict):
            return {
                "opening_home": None, "opening_draw": None, "opening_away": None,
                "closing_home": None, "closing_draw": None, "closing_away": None,
                "high_24h_home": None, "high_24h_draw": None, "high_24h_away": None,
                "low_24h_home": None, "low_24h_draw": None, "low_24h_away": None,
            }

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
            return None if value is None else float(value)

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

    else:
        # 既没有 l3_odds_data 也没有 l3_features
        return {
            "opening_home": None, "opening_draw": None, "opening_away": None,
            "closing_home": None, "closing_draw": None, "closing_away": None,
            "high_24h_home": None, "high_24h_draw": None, "high_24h_away": None,
            "low_24h_home": None, "low_24h_draw": None, "low_24h_away": None,
        }

    # V34.0: 计算新特征
    # 1. payout_ratio: 博彩公司返还率
    closing_home = features.get("closing_home")
    closing_draw = features.get("closing_draw")
    closing_away = features.get("closing_away")
    features["payout_ratio"] = calculate_payout_ratio(closing_home, closing_draw, closing_away)

    # 2. movement_velocity: 赛前 2 小时变盘速度
    odds_history = match_data.get("odds_history", []) if match_data else []
    match_time_str = match_data.get("match_time") if match_data else None

    if match_time_str and odds_history:
        try:
            if isinstance(match_time_str, str):
                match_time_dt = datetime.fromisoformat(match_time_str.replace('Z', '+00:00'))
            else:
                match_time_dt = match_time_str
            features["movement_velocity"] = calculate_movement_velocity(odds_history, match_time_dt)
        except (ValueError, TypeError):
            features["movement_velocity"] = 0.0
    else:
        features["movement_velocity"] = 0.0

    return features


def calculate_payout_ratio(
    home_odds: Optional[float],
    draw_odds: Optional[float],
    away_odds: Optional[float]
) -> Optional[float]:
    """V34.0: 计算博彩公司返还率

    返还率公式: payout = 1 / (1/home + 1/draw + 1/away)

    理论值范围:
    - 正常盘口: 0.90-0.98 (博彩公司抽取 2-10% 水钱)
    - 异常高返还率 (>0.98): 可能是"冷门诱导"盘

    Args:
        home_odds: 主队赔率
        draw_odds: 平局赔率
        away_odds: 客队赔率

    Returns:
        返还率 (0-1)，如果任何赔率无效则返回 None
    """
    # 检查所有赔率是否有效
    if home_odds is None or draw_odds is None or away_odds is None:
        return None

    # 检查零值或负值
    if home_odds <= 0 or draw_odds <= 0 or away_odds <= 0:
        return None

    try:
        # 计算返还率
        implied_prob = (1.0 / home_odds) + (1.0 / draw_odds) + (1.0 / away_odds)
        payout = 1.0 / implied_prob

        # 返还率应在合理范围内 (0.85-1.0)
        if 0.85 <= payout <= 1.0:
            return payout
        else:
            # 异常值（可能是数据错误）
            return None

    except (ZeroDivisionError, ValueError):
        return None


def calculate_movement_velocity(
    odds_history: List[Dict[str, Any]],
    match_time: datetime
) -> float:
    """V34.0: 计算赛前 2 小时内的变盘速度

    变盘速度 = 赔率变动次数 / 实际时间跨度（小时）

    极端场景:
    - 10 分钟内跳动 5 次 = 30 次/小时 (高速度，主力资金活跃)
    - 2 小时内跳动 3 次 = 1.5 次/小时 (低速度，市场平稳)

    Args:
        odds_history: 赔率历史记录列表
            每条记录包含: home_odds, draw_odds, away_odds, collected_at
        match_time: 比赛开始时间

    Returns:
        变盘速度 (次/小时)，如果无法计算则返回 0
    """
    if not odds_history:
        return 0.0

    # 过滤有效记录：必须有 collected_at 且在赛前 2 小时窗口内
    valid_records = []
    window_start = match_time - timedelta(hours=2)

    for record in odds_history:
        # 检查是否有 collected_at 字段
        collected_at = record.get("collected_at")
        if collected_at is None:
            continue

        # 处理字符串格式的时间戳
        if isinstance(collected_at, str):
            try:
                collected_at = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
            except ValueError:
                continue

        # 检查是否在 2 小时窗口内
        if window_start <= collected_at <= match_time:
            valid_records.append({
                "home_odds": record.get("home_odds"),
                "draw_odds": record.get("draw_odds"),
                "away_odds": record.get("away_odds"),
                "collected_at": collected_at
            })

    if len(valid_records) < 2:
        # 至少需要 2 条记录才能检测变动
        return 0.0

    # 按时间排序
    valid_records.sort(key=lambda x: x["collected_at"])

    # 统计赔率变动次数
    change_count = 0
    prev_odds = None

    for record in valid_records:
        current_odds = (
            record["home_odds"],
            record["draw_odds"],
            record["away_odds"]
        )

        # 检查是否有任何赔率缺失
        if any(o is None for o in current_odds):
            continue

        if prev_odds is not None:
            # 检查是否有任何赔率发生变化
            # 使用容差 0.01 避免浮点数精度问题
            tolerance = 0.01
            if (abs(current_odds[0] - prev_odds[0]) > tolerance or
                abs(current_odds[1] - prev_odds[1]) > tolerance or
                abs(current_odds[2] - prev_odds[2]) > tolerance):
                change_count += 1

        prev_odds = current_odds

    # 计算实际时间跨度（小时）
    first_time = valid_records[0]["collected_at"]
    last_time = valid_records[-1]["collected_at"]
    time_span_seconds = (last_time - first_time).total_seconds()

    if time_span_seconds > 0:
        time_window_hours = time_span_seconds / 3600.0
        velocity = change_count / time_window_hours
    else:
        # 所有记录时间相同，无法计算速度
        velocity = 0.0

    return velocity


# ============================================================================
# 数据库操作
# ============================================================================

def fetch_from_clean_view(limit: int = 100, incremental: bool = True) -> List[Dict[str, Any]]:
    """从 v_matches_clean 视图获取数据并构建 l3_features

    V36.3: 双数据源支持
    1. 优先读取 matches.l3_odds_data (V36.3 数组格式)
    2. 回退到 odds 表 (旧格式)

    V29.1: 支持增量提取，默认排除已有特征的比赛。

    Args:
        limit: 最大返回记录数
        incremental: 是否使用增量模式（排除已处理比赛）- 默认 True

    Returns:
        包含 l3_odds_data 或 l3_features 的比赛数据列表
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # V37.7: 增量提取 - 只排除成功提取的比赛（payout_ratio > 0）
            # 修复坏账逻辑：允许重新提取 payout_ratio 为 NULL/0 的比赛
            where_clause = ""
            if incremental:
                where_clause = """WHERE m.match_id NOT IN (
                    SELECT match_id FROM match_features
                    WHERE payout_ratio IS NOT NULL AND payout_ratio > 0
                )"""

            # V36.3: 优先读取 l3_odds_data (新格式)，回退到 odds 表 (旧格式)
            # 新数据优先级: l3_odds_data > odds 表
            cur.execute(f"""
                SELECT
                    m.match_id,
                    m.league_name,
                    m.home_team,
                    m.away_team,
                    -- V36.3: 优先使用 l3_odds_data (数组格式)
                    m.l3_odds_data,
                    -- 旧格式兼容: 从 odds 表聚合
                    COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'bookmaker', o.bookmaker,
                            'home_odds', o.home_odds,
                            'draw_odds', o.draw_odds,
                            'away_odds', o.away_odds,
                            'collected_at', o.collected_at
                        ) ORDER BY o.collected_at
                    ) FILTER (WHERE o.bookmaker IS NOT NULL AND m.l3_odds_data IS NULL), '[]') as odds_data
                FROM matches m
                LEFT JOIN odds o ON m.match_id = o.match_id
                {where_clause}
                  AND (m.l3_odds_data IS NOT NULL OR o.match_id IS NOT NULL)
                GROUP BY m.match_id, m.league_name, m.home_team, m.away_team, m.l3_odds_data
                ORDER BY (m.l3_odds_data IS NOT NULL) DESC, m.updated_at DESC
                LIMIT %s
            """, (limit,))

            rows = cur.fetchall()

            # 构建数据结构
            results = []
            for row in rows:
                match_data = {
                    "match_id": row["match_id"],
                    "league_name": row["league_name"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                }

                # V36.3: 优先使用 l3_odds_data (新格式)
                l3_odds_data = row.get("l3_odds_data")
                if l3_odds_data:
                    match_id = match_data["match_id"]

                    # 格式 1: Pinnacle 格式 {"pinnacle": {"home_odds": 1.5}}
                    if "pinnacle" in l3_odds_data and isinstance(l3_odds_data.get("pinnacle"), dict):
                        pinnacle = l3_odds_data["pinnacle"]
                        converted = {
                            "home": [{"odds": str(pinnacle.get("home_odds"))}],
                            "draw": [{"odds": str(pinnacle.get("draw_odds"))}],
                            "away": [{"odds": str(pinnacle.get("away_odds"))}]
                        }
                        match_data["l3_odds_data"] = converted
                        results.append(match_data)
                        continue

                    # 格式 2: 数组格式 {"home": [{"odds": "1.5"}], ...}
                    elif "home" in l3_odds_data and isinstance(l3_odds_data.get("home"), list):
                        match_data["l3_odds_data"] = l3_odds_data
                        results.append(match_data)
                        continue

                    # 格式 3: Average Odds 格式 {"closing_odds": {"Average Odds": {"home": 1.5}}}
                    elif "closing_odds" in l3_odds_data or "opening_odds" in l3_odds_data:
                        try:
                            closing = l3_odds_data.get("closing_odds", {})
                            opening = l3_odds_data.get("opening_odds", {})

                            # 提取 Average Odds
                            closing_avg = closing.get("Average Odds", {})
                            opening_avg = opening.get("Average Odds", {})

                            converted = {
                                "home": [
                                    {"odds": str(opening_avg.get("home"))},
                                    {"odds": str(closing_avg.get("home"))}
                                ],
                                "draw": [
                                    {"odds": str(opening_avg.get("draw"))},
                                    {"odds": str(closing_avg.get("draw"))}
                                ],
                                "away": [
                                    {"odds": str(opening_avg.get("away"))},
                                    {"odds": str(closing_avg.get("away"))}
                                ]
                            }
                            match_data["l3_odds_data"] = converted
                            results.append(match_data)
                            continue
                        except (KeyError, TypeError, AttributeError) as e:
                            logger.warning(f"Average Odds 格式解析失败: {match_id} - {e}")
                            log_failed_extraction(
                                match_id, "average_odds", l3_odds_data,
                                f"解析失败: {str(e)}"
                            )
                            continue

                    # V38.0: 格式 4 - Pinnacle flat format {"home_odds": 1.45, "draw_odds": 4.45, "away_odds": 6.75}
                    elif "home_odds" in l3_odds_data or "draw_odds" in l3_odds_data or "away_odds" in l3_odds_data:
                        # 直接传递给 extract_features_from_json，它会处理这种格式
                        match_data["l3_odds_data"] = l3_odds_data
                        results.append(match_data)
                        continue

                    # 格式 5: 未知格式 - 记录并跳过
                    else:
                        logger.warning(f"Unknown l3_odds_data format for match {match_id}")
                        log_failed_extraction(
                            match_id, "unknown", l3_odds_data,
                            "无法识别的 l3_odds_data 格式"
                        )
                        continue

                # 回退: 从 odds_data 构建 l3_features (旧格式)
                odds_list = row.get("odds_data", [])

                # 构建 l3_features (即使为空也要添加到 results)
                l3_features = {}

                if odds_list:
                    # 简单策略：第一条作为 opening，最后一条作为 closing
                    # 实际项目中应根据 collected_at 时间戳判断

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
                        payout_ratio, movement_velocity,
                        updated_at
                    ) VALUES (
                        %s, %s, %s, %s,  %s, %s, %s,  %s, %s, %s,  %s, %s, %s,  %s, %s, CURRENT_TIMESTAMP
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
                        payout_ratio = EXCLUDED.payout_ratio,
                        movement_velocity = EXCLUDED.movement_velocity,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    match_id,
                    features.get("opening_home"), features.get("opening_draw"), features.get("opening_away"),
                    features.get("closing_home"), features.get("closing_draw"), features.get("closing_away"),
                    features.get("high_24h_home"), features.get("high_24h_draw"), features.get("high_24h_away"),
                    features.get("low_24h_home"), features.get("low_24h_draw"), features.get("low_24h_away"),
                    features.get("payout_ratio"),
                    features.get("movement_velocity", 0.0),
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
    parser.add_argument("--no-incremental", action="store_true",
                        help="非增量模式：重新处理所有比赛（包括已有特征的）")

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
        # V33.3 炼金触发器模式（静默模式优化）
        logger.info("🔥 V33.3 炼金触发器启动")
        logger.info(f"扫描间隔: {args.interval} 秒 ({args.interval // 60} 分钟)")

        poll_count = 0
        last_odds_count = None  # V33.3: 跟踪上次 odds 表记录数

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
                        # V33.3: 首先检查 odds 表是否有新数据
                        cur.execute("SELECT COUNT(*) as total_odds FROM odds")
                        row = cur.fetchone()
                        current_odds_count = row['total_odds'] if row else 0

                        # V33.3 静默模式：如果 odds 表没有新数据，跳过扫描
                        if last_odds_count is not None and current_odds_count == last_odds_count:
                            logger.info(f"🤫 静默模式: odds 表无新数据 ({current_odds_count} 条)")
                            logger.info(f"⏭️  跳过本次扫描，节省资源")
                        else:
                            # odds 表有新数据或首次扫描，执行完整检查
                            if last_odds_count is not None:
                                new_odds = current_odds_count - last_odds_count
                                logger.info(f"🆕 检测到 {new_odds} 条新 odds 数据")
                            else:
                                logger.info(f"🔄 首次扫描，当前 odds: {current_odds_count} 条")

                            # 统计差距
                            cur.execute("""
                                SELECT
                                    (SELECT COUNT(*) FROM v_matches_clean) as total_matches,
                                    (SELECT COUNT(*) FROM match_features) as extracted_features
                            """)
                            row = cur.fetchone()
                            total_matches = row['total_matches'] if row else 0
                            extracted_features = row['extracted_features'] if row else 0

                            gap = total_matches - extracted_features

                            logger.info(f"📊 数据状态:")
                            logger.info(f"   v_matches_clean: {total_matches}")
                            logger.info(f"   match_features: {extracted_features}")
                            logger.info(f"   odds 表: {current_odds_count}")
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
                                logger.info(f"✅ 数据已齐，无需提取")

                            # 更新上次 odds 记录数
                            last_odds_count = current_odds_count

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
        raw_data = fetch_from_clean_view(args.limit, incremental=not args.no_incremental)
        logger.info(f"获取 {len(raw_data)} 条记录")

        for match_data in raw_data[:3]:  # 显示前 3 条
            features = extract_features_from_json(match_data)
            logger.info(f"Match {match_data.get('match_id')}: {features}")
    else:
        results = process_features_pipeline(args.limit, incremental=not args.no_incremental)
        logger.info(f"✅ 处理完成，共 {len(results)} 条记录")


if __name__ == "__main__":
    main()
