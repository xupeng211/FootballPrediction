#!/usr/bin/env python3
"""
V151.4 西甲列表页批量抓哈希引擎

核心功能：
1. 直接访问 OddsPortal 西甲赛果列表页
2. 从列表页一次性提取所有比赛 URL（含哈希）
3. 批量写入 matches_mapping 表

优势：
- 避免搜索接口的混淆问题
- 列表页数据结构化，成功率接近 100%
- 无需点击，直接解析 HTML

Author: 高级性能优化架构师 (Staff Performance Architect)
Date: 2026-01-11
Version: V151.4 (List Page Harvesting)
"""

import asyncio
import logging
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V29.0: 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(override=True)

import psycopg2
from playwright.async_api import async_playwright, Page, Browser
from src.config_unified import get_settings
from thefuzz import fuzz

# ============================================================================
# 配置
# ============================================================================

# V32.2: OddsPortal 联赛赛果页 URL 映射（支持多联赛）
LEAGUE_RESULTS_URLS = {
    "La Liga": {
        "latest": "https://www.oddsportal.com/football/spain/laliga/results/",
        "23-24": "https://www.oddsportal.com/football/spain/laliga-2023-2024/results/",
        "22-23": "https://www.oddsportal.com/football/spain/laliga-2022-2023/results/",
        "21-22": "https://www.oddsportal.com/football/spain/laliga-2021-2022/results/",
        "20-21": "https://www.oddsportal.com/football/spain/laliga-2020-2021/results/",
    },
    "Serie A": {
        "latest": "https://www.oddsportal.com/football/italy/serie-a/results/",
        "23-24": "https://www.oddsportal.com/football/italy/serie-a-2023-2024/results/",
        "22-23": "https://www.oddsportal.com/football/italy/serie-a-2022-2023/results/",
        "21-22": "https://www.oddsportal.com/football/italy/serie-a-2021-2022/results/",
        "20-21": "https://www.oddsportal.com/football/italy/serie-a-2020-2021/results/",
    },
    "Bundesliga": {
        "latest": "https://www.oddsportal.com/football/germany/bundesliga/results/",
        "23-24": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
        "22-23": "https://www.oddsportal.com/football/germany/bundesliga-2022-2023/results/",
        "21-22": "https://www.oddsportal.com/football/germany/bundesliga-2021-2022/results/",
        "20-21": "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/results/",
    },
    "Ligue 1": {
        "latest": "https://www.oddsportal.com/football/france/ligue-1/results/",
        "23-24": "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/",
        "22-23": "https://www.oddsportal.com/football/france/ligue-1-2022-2023/results/",
        "21-22": "https://www.oddsportal.com/football/france/ligue-1-2021-2022/results/",
        "20-21": "https://www.oddsportal.com/football/france/ligue-1-2020-2021/results/",
    },
    "Premier League": {
        "latest": "https://www.oddsportal.com/football/england/premier-league/results/",
        "23-24": "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
        "22-23": "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/",
        "21-22": "https://www.oddsportal.com/football/england/premier-league-2021-2022/results/",
        "20-21": "https://www.oddsportal.com/football/england/premier-league-2020-2021/results/",
    },
}

# 向后兼容
LA_LIGA_RESULTS_URLS = LEAGUE_RESULTS_URLS["La Liga"]

# 代理配置
PROXY_SERVER = "http://172.25.16.1:7890"

# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/harvest_league_urls.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 数据库操作
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )

# V33.0: 内存缓存 - 避免高频数据库访问
_FOTMOB_MATCHES_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_EXISTING_URLS_CACHE: set = None
_CACHE_TIMESTAMP = None
_CACHE_TTL_SECONDS = 300  # 5 分钟缓存过期时间


def fetch_fotmob_matches(league_name: str) -> List[Dict[str, Any]]:
    """V33.0: 从 matches 表获取指定联赛的比赛（带内存缓存）

    Args:
        league_name: 联赛名称 (如 "La Liga")

    Returns:
        比赛列表
    """
    # V33.0: 检查缓存
    global _FOTMOB_MATCHES_CACHE
    if league_name in _FOTMOB_MATCHES_CACHE:
        logger.debug(f"🎯 命中缓存: fetch_fotmob_matches({league_name})")
        return _FOTMOB_MATCHES_CACHE[league_name]

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            match_id as fotmob_id,
            home_team,
            away_team,
            match_date
        FROM matches
        WHERE league_name = %s
        ORDER BY match_date DESC
    """

    cursor.execute(query, (league_name,))
    columns = ['fotmob_id', 'home_team', 'away_team', 'match_date']

    matches = []
    for row in cursor.fetchall():
        matches.append(dict(zip(columns, row)))

    cursor.close()
    conn.close()

    # V33.0: 更新缓存
    _FOTMOB_MATCHES_CACHE[league_name] = matches
    logger.debug(f"💾 缓存已更新: fetch_fotmob_matches({league_name}) = {len(matches)} 场")

    return matches


def match_urls_in_database() -> set:
    """V33.0: 获取数据库中已存在的 oddsportal_url 集合（带内存缓存）

    Returns:
        已存在的 URL 集合
    """
    # V33.0: 检查缓存
    global _EXISTING_URLS_CACHE, _CACHE_TIMESTAMP, _CACHE_TTL_SECONDS
    import time
    current_time = time.time()

    if _EXISTING_URLS_CACHE is not None and _CACHE_TIMESTAMP is not None:
        cache_age = current_time - _CACHE_TIMESTAMP
        if cache_age < _CACHE_TTL_SECONDS:
            logger.debug(f"🎯 命中缓存: match_urls_in_database() ({len(_EXISTING_URLS_CACHE)} URLs)")
            return _EXISTING_URLS_CACHE

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT oddsportal_url FROM matches_mapping WHERE oddsportal_url IS NOT NULL")
    urls = {row[0] for row in cursor.fetchall()}

    cursor.close()
    conn.close()

    # V33.0: 更新缓存
    _EXISTING_URLS_CACHE = urls
    _CACHE_TIMESTAMP = current_time
    logger.debug(f"💾 缓存已更新: match_urls_in_database() = {len(urls)} URLs")

    return urls


# ============================================================================
# V32.2: 智能 URL 队名解析 (修复多词队名 Bug)
# ============================================================================

@lru_cache(maxsize=10)
def get_league_team_names(league_name: str) -> Dict[str, str]:
    """从数据库获取联赛的所有合法队名

    Args:
        league_name: 联赛名称

    Returns:
        队名字典 {标准名称: URL slug}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取联赛中的所有唯一队名
    cursor.execute("""
        SELECT DISTINCT home_team FROM matches
        WHERE league_name = %s
        UNION
        SELECT DISTINCT away_team FROM matches
        WHERE league_name = %s
        ORDER BY 1
    """, (league_name, league_name))

    team_names = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    # 构建队名到 URL slug 的映射
    team_slug_map = {}
    for team in team_names:
        # V32.2: 使用 team_name_to_slug 函数处理特殊映射
        slug = team_name_to_slug(team)
        team_slug_map[team] = slug

    return team_slug_map


def team_name_to_slug(team_name: str) -> str:
    """将队名转换为 URL slug 格式

    Args:
        team_name: 队名 (如 "Real Sociedad")

    Returns:
        URL slug (如 "real-sociedad")

    V33.2 特殊处理：
    西甲缩写:
    - Real Sociedad → real-sociedad
    - Atletico Madrid → atl-madrid
    - Athletic Bilbao → ath-bilbao
    - Real Betis → betis (URL 常省略 'Real')
    - Real Valladolid → valladolid (URL 常省略 'Real')

    英超昵称:
    - Wolverhampton Wanderers → wolves
    - West Ham United → west-ham
    - Tottenham Hotspur → tottenham
    - Luton Town → luton
    - Newcastle United → newcastle-utd
    - Sheffield United → sheffield-utd
    """
    # V33.2: 完整特殊映射表（西甲缩写 + 英超昵称 + 前缀省略）
    special_mappings = {
        # 西甲特殊缩写
        "Atletico Madrid": "atl-madrid",
        "Athletic Bilbao": "ath-bilbao",
        "Athletic Club": "ath-bilbao",
        "Real Betis": "betis",
        "Real Valladolid": "valladolid",  # V33.2: 移除 'Real' 前缀

        # 英超昵称映射
        "Wolverhampton Wanderers": "wolves",
        "West Ham United": "west-ham",
        "Tottenham Hotspur": "tottenham",
        "Luton Town": "luton",
        "Newcastle United": "newcastle-utd",
        "Sheffield United": "sheffield-utd",
    }

    if team_name in special_mappings:
        return special_mappings[team_name]

    # 标准转换
    slug = team_name.lower()
    # 空格替换为连字符
    slug = slug.replace(' ', '-')
    # V33.2: 移除 & 符号（Brighton & Hove Albion → brighton-hove-albion）
    slug = slug.replace('&', '')
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # 移除多余连字符
    slug = re.sub(r'-+', '-', slug).strip('-')

    return slug if slug else team_name.lower()


# ============================================================================
# V33.3: 动态别名系统 - 自进化队名匹配
# ============================================================================

def get_team_aliases_from_db(league_name: str = None) -> Dict[str, Tuple[str, float]]:
    """V33.3: 从数据库获取队名别名映射

    Args:
        league_name: 联赛名称（可选，用于过滤）

    Returns:
        {alias_slug: (canonical_name, confidence)} 字典
    """
    try:
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=None
        )

        cursor = conn.cursor()
        if league_name:
            cursor.execute("""
                SELECT alias_slug, canonical_name, confidence
                FROM team_aliases
                WHERE league_name = %s OR league_name IS NULL
                ORDER BY confidence DESC, usage_count DESC
            """, (league_name,))
        else:
            cursor.execute("""
                SELECT alias_slug, canonical_name, confidence
                FROM team_aliases
                ORDER BY confidence DESC, usage_count DESC
            """)

        aliases = {}
        for row in cursor.fetchall():
            alias_slug, canonical_name, confidence = row
            aliases[alias_slug] = (canonical_name, confidence)

        cursor.close()
        conn.close()
        return aliases

    except Exception as e:
        logger.warning(f"获取队名别名失败: {e}")
        return {}


def save_team_alias(
    alias_slug: str,
    canonical_name: str,
    league_name: str,
    alias_type: str = 'fuzzy',
    confidence: float = 0.7
) -> bool:
    """V34.0: 保存新队名别名到数据库（自学习 + 审核机制）

    V34.0 审核机制：
    - 70% <= confidence < 85%: 标记为 review_needed=TRUE，需人工确认
    - confidence >= 85%: 直接使用
    - confidence < 70%: 不保存（低置信度）

    Args:
        alias_slug: URL slug 别名
        canonical_name: 标准队名
        league_name: 联赛名称
        alias_type: 别名类型
        confidence: 置信度

    Returns:
        是否保存成功
    """
    # V34.0: 审核机制 - 低置信度不保存
    if confidence < 0.70:
        logger.debug(f"⚠️ 置信度过低 ({confidence:.2f})，跳过保存: {alias_slug}")
        return False

    # V34.0: 检查是否需要人工审核
    review_needed = 0.70 <= confidence < 0.85

    try:
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=None
        )

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO team_aliases (alias_slug, canonical_name, league_name, alias_type, confidence, review_needed)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (alias_slug, league_name) DO UPDATE SET
                confidence = GREATEST(team_aliases.confidence, EXCLUDED.confidence),
                usage_count = team_aliases.usage_count + 1,
                last_used_at = NOW(),
                review_needed = CASE
                    WHEN EXCLUDED.confidence >= 0.85 THEN FALSE
                    ELSE team_aliases.review_needed
                END
        """, (alias_slug, canonical_name, league_name, alias_type, confidence, review_needed))

        conn.commit()
        cursor.close()
        conn.close()

        status = "🔍 需审核" if review_needed else "✅"
        logger.info(f"{status} 自学习: 保存队名别名 {alias_slug} → {canonical_name} (conf={confidence:.2f})")
        return True

    except Exception as e:
        logger.error(f"保存队名别名失败: {e}")
        return False


def update_alias_usage(alias_slug: str, league_name: str) -> bool:
    """V33.3: 更新别名使用次数"""
    try:
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=None
        )

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE team_aliases
            SET usage_count = usage_count + 1,
                last_used_at = NOW()
            WHERE alias_slug = %s AND league_name = %s
        """, (alias_slug, league_name))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.warning(f"更新别名使用失败: {e}")
        return False


def parse_match_url_with_league_teams(
    url: str,
    league_name: str
) -> Tuple[str, str, float]:
    """V33.3: 智能解析比赛 URL，支持动态别名学习

    Args:
        url: OddsPortal 比赛 URL
        league_name: 联赛名称

    Returns:
        (home_team, away_team, confidence) 元组
        confidence: 匹配置信度 (0-1)

    V33.3 算法（自进化）：
    1. 从数据库查询已有别名映射（最高优先级）
    2. 将队名转换为 slug 格式
    3. 使用 greedy matching 从左到右匹配队名
    4. 模糊匹配成功后，自动保存到 team_aliases 表（学习）
    5. 更新别名使用统计
    """
    # V33.3 Step 1: 从数据库获取已有别名（最高优先级）
    db_aliases = get_team_aliases_from_db(league_name)

    # 提取 URL slug
    url_parts = url.strip('/').split('/')
    if len(url_parts) < 2:
        return ("", "", 0.0)

    # 最后部分是 match-{home}-{away}-{hash}
    match_part = url_parts[-1]

    # 移除哈希部分 (最后 6-12 位字母数字)
    match_part = re.sub(r'-[a-zA-Z0-9]{6,12}$', '', match_part)

    # 分割成 slug 列表
    slug_parts = match_part.split('-')

    # 使用 greedy matching 找到最佳队名分割
    best_home = ""
    best_away = ""
    best_score = 0.0
    best_both_from_db = False  # V36.4: Track if both teams from database (highest priority)

    # 获取联赛队名（用于模糊匹配回退）
    team_slug_map = get_league_team_names(league_name) if not db_aliases else {}

    # 合并数据库别名和生成的 slug 映射
    # 数据库别名格式: {alias_slug: (canonical_name, confidence)}
    # 生成的 slug 映射格式: {canonical_name: alias_slug}
    all_team_slugs = {}

    # 添加数据库别名（最高优先级）
    for alias_slug, (canonical_name, conf) in db_aliases.items():
        all_team_slugs[canonical_name] = alias_slug

    # 添加生成的 slug（用于模糊匹配）
    for team_name, team_slug in team_slug_map.items():
        if team_name not in all_team_slugs:
            all_team_slugs[team_name] = team_slug

    if not all_team_slugs:
        # 回退到简单解析
        return parse_match_url_simple(url)

    # V36.2: 创建反向映射 {slug: 队名} 以支持部分 slug 匹配
    # 保留原始 {队名: slug} 格式，同时创建 {slug: 队名} 反向映射
    slug_to_team = {}
    for team_name, team_slug in all_team_slugs.items():
        # V36.2: 如果一个 slug 映射到多个队名，优先选择更长的队名（更完整）
        if team_slug in slug_to_team:
            # 如果当前队名更长，替换
            if len(team_name) > len(slug_to_team[team_slug]):
                slug_to_team[team_slug] = team_name
        else:
            slug_to_team[team_slug] = team_name

        # 添加缩写映射（如 "atl" -> "Atletico Madrid"）
        slug_parts_ = team_slug.split('-')
        if len(slug_parts_) > 1:
            # V36.3: 对于多词队名，添加首部分缩写
            # 优先使用多词队名生成的缩写，避免被数据库别名覆盖
            # 例如：real-sociedad 的缩写 "real" 应该优先于数据库中的 "real" -> "Real Madrid"
            if slug_parts_[0] in slug_to_team:
                # 只有当前队名更长时才覆盖
                if len(team_name) > len(slug_to_team[slug_parts_[0]]):
                    slug_to_team[slug_parts_[0]] = team_name
            else:
                slug_to_team[slug_parts_[0]] = team_name

    # 尝试所有可能的分割点
    for split_point in range(1, len(slug_parts)):
        home_slug = '-'.join(slug_parts[:split_point])
        away_slug = '-'.join(slug_parts[split_point:])

        # 匹配主队
        home_match = None
        home_score = 0.0
        home_is_from_db = False

        # 优先检查数据库别名
        if db_aliases:
            if home_slug in db_aliases:
                home_match, home_score = db_aliases[home_slug]
                home_is_from_db = True
                update_alias_usage(home_slug, league_name)

        # 如果数据库中没找到，使用反向映射匹配
        if not home_match:
            if home_slug in slug_to_team:
                home_match = slug_to_team[home_slug]
                home_score = 1.0

        # 如果反向映射没找到，使用原始映射的模糊匹配
        if not home_match:
            for team_name, team_slug in all_team_slugs.items():
                # 模糊匹配
                score = fuzz.ratio(home_slug, team_slug) / 100.0
                if score > home_score and score > 0.7:  # 70% 相似度阈值
                    home_match = team_name
                    home_score = score

        # 匹配客队
        away_match = None
        away_score = 0.0
        away_is_from_db = False

        # 优先检查数据库别名
        if db_aliases:
            if away_slug in db_aliases:
                away_match, away_score = db_aliases[away_slug]
                away_is_from_db = True
                update_alias_usage(away_slug, league_name)

        # 如果数据库中没找到，使用反向映射匹配
        if not away_match:
            if away_slug in slug_to_team:
                away_match = slug_to_team[away_slug]
                away_score = 1.0

        # 如果反向映射没找到，使用原始映射的模糊匹配
        if not away_match:
            for team_name, team_slug in all_team_slugs.items():
                # 模糊匹配
                score = fuzz.ratio(away_slug, team_slug) / 100.0
                if score > away_score and score > 0.7:  # 70% 相似度阈值
                    away_match = team_name
                    away_score = score

        # 计算总置信度
        if home_match and away_match:
            total_score = (home_score + away_score) / 2.0
            # V36.4: 只有非数据库匹配时才添加长度奖励
            # 数据库直接命中保持 1.0 置信度，避免测试期望偏差
            if not home_is_from_db or not away_is_from_db:
                # V36.2: 添加长度奖励，优先选择更长的 slug（更完整的队名）
                # 这样可以避免 "real-sociedad" 被错误解析为 "Real" vs "Sociedad"
                length_bonus = (len(home_slug.split('-')) + len(away_slug.split('-'))) / 10.0
                total_score += length_bonus

            # V36.4: 优先级选择逻辑
            # 1. 如果当前两者都来自数据库，且之前不都是来自数据库，优先选择
            # 2. 否则，选择分数更高的
            current_both_from_db = home_is_from_db and away_is_from_db
            should_update = False

            if current_both_from_db and not best_both_from_db:
                # 数据库直接匹配优先
                should_update = True
            elif not current_both_from_db and best_both_from_db:
                # 不要用非数据库匹配替换数据库匹配
                should_update = False
            elif total_score > best_score:
                # 同类型匹配，选择分数更高的
                should_update = True

            if should_update:
                best_score = total_score
                best_home = home_match
                best_away = away_match
                best_both_from_db = current_both_from_db

                # V34.0 自学习：模糊匹配成功后，自动保存到数据库
                # 审核机制：
                # - confidence >= 85%: 直接使用
                # - 70% <= confidence < 85%: 保存但标记为需审核
                # - confidence < 70%: 不保存
                if total_score >= 0.70:
                    if not home_is_from_db and home_slug not in db_aliases:
                        save_team_alias(home_slug, home_match, league_name, 'fuzzy', home_score)
                    if not away_is_from_db and away_slug not in db_aliases:
                        save_team_alias(away_slug, away_match, league_name, 'fuzzy', away_score)

    if best_home and best_away:
        return (best_home, best_away, best_score)
    else:
        # 回退到简单解析
        return parse_match_url_simple(url)


def parse_match_url_simple(url: str) -> Tuple[str, str, float]:
    """简单 URL 解析（回退方案）

    V36.2: 增强版 - 支持通过 slug 反向映射查找完整队名

    Args:
        url: OddsPortal 比赛 URL

    Returns:
        (home_team, away_team, confidence) 元组
    """
    url_parts = url.strip('/').split('/')
    if len(url_parts) >= 2:
        match_part = url_parts[-1]
        # 移除哈希部分 (最后 6-12 位字母数字)
        name_part = re.sub(r'-[a-zA-Z0-9]{6,12}$', '', match_part)
        teams = name_part.split('-')
        if len(teams) >= 2:
            # V36.2: 尝试使用 slug 反向映射
            # 从 URL 中提取联赛名称
            league_name = None
            for part in url_parts:
                if 'spain' in part.lower():
                    league_name = "La Liga"
                    break
                elif 'england' in part.lower():
                    league_name = "Premier League"
                    break

            if league_name:
                # 获取联赛队名映射
                # V36.2: 直接调用函数而非导入（避免循环导入）
                try:
                    team_map = get_league_team_names(league_name)
                    # 创建反向映射
                    slug_to_team = {}
                    for team_name, team_slug in team_map.items():
                        # V36.2: 优先选择更长的队名（处理多映射情况）
                        if team_slug in slug_to_team:
                            if len(team_name) > len(slug_to_team[team_slug]):
                                slug_to_team[team_slug] = team_name
                        else:
                            slug_to_team[team_slug] = team_name
                        # 添加缩写映射
                        slug_parts = team_slug.split('-')
                        if len(slug_parts) > 1:
                            if slug_parts[0] in slug_to_team:
                                if len(team_name) > len(slug_to_team[slug_parts[0]]):
                                    slug_to_team[slug_parts[0]] = team_name
                            else:
                                slug_to_team[slug_parts[0]] = team_name

                    # 尝试找到最佳分割点
                    best_home = None
                    best_away = None
                    best_score = 0

                    for split_point in range(1, len(teams)):
                        home_slug = '-'.join(teams[:split_point])
                        away_slug = '-'.join(teams[split_point:])

                        if home_slug in slug_to_team and away_slug in slug_to_team:
                            # 找到匹配，优先更长的 slug
                            score = len(home_slug) + len(away_slug)
                            if score > best_score:
                                best_score = score
                                best_home = slug_to_team[home_slug]
                                best_away = slug_to_team[away_slug]

                    if best_home and best_away:
                        return (best_home, best_away, 0.6)
                except Exception:
                    pass

            # 回退到标题格式化
            # V36.4 Final: 增强队名推断，尝试从 slug_to_team 中查找完整队名
            home_team = ' '.join(teams[0].split()).title()
            away_team = ' '.join(teams[1].split()).title()

            # 尝试使用 slug_to_team 查找完整队名
            if slug_to_team:
                # 对于第一个 slug，尝试直接匹配
                if teams[0] in slug_to_team:
                    home_team = slug_to_team[teams[0]]
                # 如果没有直接匹配，尝试前缀匹配
                else:
                    for slug, full_name in slug_to_team.items():
                        if slug.startswith(teams[0]) or teams[0].startswith(slug):
                            home_team = full_name
                            break

                # 对于第二个 slug，尝试组合剩余部分
                remaining_slug = '-'.join(teams[1:])
                if remaining_slug in slug_to_team:
                    away_team = slug_to_team[remaining_slug]
                # 如果组合不匹配，尝试前缀匹配
                else:
                    for slug, full_name in slug_to_team.items():
                        if remaining_slug in slug or slug.startswith(teams[1]) or teams[1].startswith(slug):
                            away_team = full_name
                            break

            return (home_team, away_team, 0.5)  # 低置信度
    return ("", "", 0.0)


# ============================================================================

def batch_insert_urls(match_url_pairs: List[Dict[str, Any]]) -> int:
    """批量插入 URL 到 matches_mapping 表

    Args:
        match_url_pairs: [(fotmob_id, oddsportal_url, home_team, away_team, ...), ...]

    Returns:
        成功插入的记录数
    """
    if not match_url_pairs:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    inserted_count = 0
    for pair in match_url_pairs:
        try:
            cursor.execute("""
                INSERT INTO matches_mapping
                (fotmob_id, home_team, away_team, league_name, oddsportal_url,
                 match_date, confidence, mapping_method, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fotmob_id) DO UPDATE SET
                    oddsportal_url = EXCLUDED.oddsportal_url,
                    mapping_method = EXCLUDED.mapping_method,
                    updated_at = NOW()
            """, (
                pair['fotmob_id'],
                pair['home_team'],
                pair['away_team'],
                pair['league_name'],
                pair['oddsportal_url'],
                pair.get('match_date'),
                0.95,  # 列表页置信度较高
                'semantic',  # V151.4: 使用有效枚举值
                'pending'
            ))
            inserted_count += 1
        except Exception as e:
            logger.warning(f"插入失败 {pair['fotmob_id']}: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    return inserted_count

# ============================================================================
# 列表页爬取
# ============================================================================

async def fetch_league_results_page(
    url: str,
    proxy: Optional[str] = None,
    league_name: str = "La Liga"
) -> List[Dict[str, Any]]:
    """V32.2: 从联赛赛果页抓取所有比赛 URL（智能队名解析）

    Args:
        url: 赛果页 URL
        proxy: 代理服务器
        league_name: 联赛名称（用于队名匹配）

    Returns:
        [(fotmob_id, oddsportal_url, home_team, away_team), ...]
    """
    results = []

    logger.info(f"📄 正在访问: {url}")
    logger.info(f"🏆 联赛: {league_name}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy} if proxy else None
        )
        page = await browser.new_page()

        try:
            # 访问赛果页
            await page.goto(url, wait_until="networkidle", timeout=60000)
            logger.info("✅ 页面加载完成")

            # V151.4: 更长等待时间让 JS 渲染完成
            await asyncio.sleep(5)

            # V151.4: 新版页面结构 - 直接提取所有包含哈希的链接
            # 新格式: /football/spain/laliga-2023-2024/{home}-{away}-{hash}/
            match_pattern = r'/football/[^/]+/[^/]+/[^/]+-[^/]+-([a-zA-Z0-9]{8,12})/'

            # 获取所有链接
            all_links = await page.locator('a').all()
            logger.info(f"🔗 页面总链接数: {len(all_links)}")

            # 过滤出比赛链接
            for link in all_links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    # 检查是否匹配比赛链接格式
                    hash_match = re.search(match_pattern, href)
                    if not hash_match:
                        continue

                    match_id = hash_match.group(1)
                    full_url = urljoin("https://www.oddsportal.com/", href)

                    # V32.2: 使用智能队名解析（支持多词队名）
                    home_team, away_team, confidence = parse_match_url_with_league_teams(
                        full_url,
                        league_name
                    )

                    if not home_team or not away_team:
                        # 智能解析失败，跳过
                        logger.warning(f"  ⚠️ 无法解析队名: {full_url}")
                        continue

                    results.append({
                        "oddsportal_url": full_url,
                        "match_id": match_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "confidence": confidence,  # V32.2: 添加置信度
                    })

                    logger.info(f"  🎯 {home_team} vs {away_team} → {match_id} (置信度: {confidence:.2f})")

                except Exception as e:
                    logger.warning(f"  ⚠️ 链接解析失败: {e}")
                    continue

            logger.info(f"✅ 提取到 {len(results)} 个比赛链接")

        finally:
            await browser.close()

    return results

def save_unmatched_teams(unmatched_entries: List[Dict[str, Any]], league_name: str):
    """V33.0: 保存无法匹配的比赛到 JSON 文件

    Args:
        unmatched_entries: 无法匹配的比赛列表
        league_name: 联赛名称
    """
    if not unmatched_entries:
        return

    import json
    from datetime import datetime

    log_file = Path("logs/unmatched_teams.json")

    # 读取现有记录
    existing_records = []
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                existing_records = json.load(f)
        except Exception as e:
            logger.warning(f"读取 unmatched_teams.json 失败: {e}")

    # 添加时间戳和新记录
    timestamp = datetime.now().isoformat()
    for entry in unmatched_entries:
        entry['audit_timestamp'] = timestamp
        entry['league_name'] = league_name
        existing_records.append(entry)

    # 写回文件
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_records, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 保存了 {len(unmatched_entries)} 条无法匹配的记录到 {log_file}")
    except Exception as e:
        logger.error(f"❌ 保存 unmatched_teams.json 失败: {e}")


def match_fotmob_with_oddsportal(
    fotmob_matches: List[Dict[str, Any]],
    oddsportal_matches: List[Dict[str, Any]],
    league_name: str = "La Liga"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """V33.0: 将 FotMob 比赛与 OddsPortal URL 进行模糊匹配

    Args:
        fotmob_matches: FotMatches 表中的比赛
        oddsportal_matches: 从列表页抓取的比赛
        league_name: 联赛名称（V32.2 新增）

    Returns:
        (匹配成功的对, 无法匹配的记录) 元组
    """
    matched_pairs = []
    matched_urls = set()
    unmatched_entries = []

    for op_match in oddsportal_matches:
        op_home = op_match['home_team'].lower().strip()
        op_away = op_match['away_team'].lower().strip()
        op_url = op_match['oddsportal_url']

        # 如果 URL 已经匹配过，跳过
        if op_url in matched_urls:
            continue

        best_match = None
        best_score = 0

        for fm_match in fotmob_matches:
            fm_home = fm_match['home_team'].lower().strip()
            fm_away = fm_match['away_team'].lower().strip()

            # 简单匹配：两队名称都包含在 URL 中
            score = 0
            if op_home in fm_home or fm_home in op_home:
                score += 1
            if op_away in fm_away or fm_away in op_away:
                score += 1

            if score > best_score:
                best_score = score
                best_match = fm_match

        # 如果两队都匹配成功
        if best_match and best_score >= 2:
            matched_pairs.append({
                "fotmob_id": best_match['fotmob_id'],
                "home_team": best_match['home_team'],
                "away_team": best_match['away_team'],
                "league_name": league_name,  # V32.2: 使用传入的联赛名称
                "match_date": best_match.get('match_date'),
                "oddsportal_url": op_url,
            })
            matched_urls.add(op_url)
        else:
            # V33.0: 记录无法匹配的比赛
            unmatched_entries.append({
                "oddsportal_url": op_url,
                "parsed_home": op_match['home_team'],
                "parsed_away": op_match['away_team'],
                "best_score": best_score,
                "confidence": op_match.get('confidence', 0.0),
            })

    # V33.0: 保存无法匹配的记录
    if unmatched_entries:
        save_unmatched_teams(unmatched_entries, league_name)

    return matched_pairs, unmatched_entries

# ============================================================================
# 主流程
# ============================================================================

async def main(league: str = "La Liga", dry_run: bool = False, limit: Optional[int] = None):
    """主流程

    Args:
        league: 联赛名称 (默认: La Liga)
        dry_run: 干跑模式，不实际写入数据库
        limit: 限制处理数量
    """
    logger.info("=" * 70)
    logger.info("🚀 V151.4 列表页批量抓哈希引擎启动")
    logger.info("=" * 70)
    logger.info(f"目标联赛: {league}")
    logger.info(f"干跑模式: {dry_run}")

    if dry_run:
        logger.info("🔍 干跑模式 - 只验证流程，不写入数据库")

    # 步骤 1: 获取 FotMob 比赛列表
    logger.info("\n📋 步骤 1: 从 FotMob 获取比赛...")
    fotmob_matches = fetch_fotmob_matches(league)
    logger.info(f"✅ 找到 {len(fotmob_matches)} 场比赛")

    if limit:
        fotmob_matches = fotmob_matches[:limit]
        logger.info(f"📊 限制处理: {len(fotmob_matches)} 场")

    # 步骤 2: 从赛果页抓取 OddsPortal URL
    logger.info("\n🎯 步骤 2: 从赛果页抓取 OddsPortal URL...")

    # V32.2: 根据联赛参数动态选择 URL
    league_urls = LEAGUE_RESULTS_URLS.get(league)
    if not league_urls:
        logger.error(f"❌ 不支持的联赛: {league}")
        logger.info(f"支持的联赛: {', '.join(LEAGUE_RESULTS_URLS.keys())}")
        return

    all_oddsportal_matches = []
    for season_name, url in league_urls.items():
        logger.info(f"\n  📅 处理赛季: {season_name}")
        season_matches = await fetch_league_results_page(url, proxy=PROXY_SERVER, league_name=league)
        all_oddsportal_matches.extend(season_matches)

    logger.info(f"\n✅ 总共抓取到 {len(all_oddsportal_matches)} 个 OddsPortal URL")

    # 步骤 3: 模糊匹配
    logger.info("\n🔗 步骤 3: 执行模糊匹配...")
    matched_pairs, unmatched_entries = match_fotmob_with_oddsportal(fotmob_matches, all_oddsportal_matches, league)
    logger.info(f"✅ 成功匹配 {len(matched_pairs)} 场比赛")
    if unmatched_entries:
        logger.warning(f"⚠️ 无法匹配 {len(unmatched_entries)} 场比赛（已记录到 unmatched_teams.json）")

    # 步骤 4: 检查已存在的 URL
    logger.info("\n🔍 步骤 4: 检查已存在的 URL...")
    existing_urls = match_urls_in_database()
    new_pairs = [p for p in matched_pairs if p['oddsportal_url'] not in existing_urls]
    logger.info(f"✅ 过滤后待插入: {len(new_pairs)} 场")

    # 步骤 5: 批量插入
    if not dry_run:
        logger.info("\n💾 步骤 5: 批量插入数据库...")
        inserted_count = batch_insert_urls(new_pairs)
        logger.info(f"✅ 成功插入 {inserted_count} 条记录")
    else:
        logger.info("\n🔍 干跑模式 - 跳过数据库插入")
        logger.info(f"📊 将插入 {len(new_pairs)} 条记录")
        # 显示前 5 条预览
        for i, pair in enumerate(new_pairs[:5], 1):
            logger.info(f"  {i}. {pair['home_team']} vs {pair['away_team']}")
            logger.info(f"     URL: {pair['oddsportal_url']}")
        if len(new_pairs) > 5:
            logger.info(f"  ... 还有 {len(new_pairs) - 5} 条")

    # 总结
    logger.info("\n" + "=" * 70)
    logger.info("📊 V151.4 列表页抓取完成")
    logger.info("=" * 70)
    logger.info(f"联赛: {league}")
    logger.info(f"总抓取 URL: {len(all_oddsportal_matches)}")
    logger.info(f"成功匹配: {len(matched_pairs)}")
    if not dry_run:
        logger.info(f"新增记录: {len(new_pairs)}")
    logger.info(f"成功率: {len(matched_pairs)/max(len(fotmob_matches),1)*100:.1f}%")
    logger.info("=" * 70)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V151.4 列表页批量抓哈希引擎")
    parser.add_argument('--league', type=str, default='La Liga',
                        help='联赛名称 (默认: La Liga)')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式，只验证不写入数据库')
    parser.add_argument('--limit', type=int, default=None,
                        help='限制处理数量')

    args = parser.parse_args()

    asyncio.run(main(league=args.league, dry_run=args.dry_run, limit=args.limit))
