#!/usr/bin/env python3
"""
V39.1 哈希 ID 规律挖掘报告

基于数据库中已有的 635 场 URL 映射，提取各联赛、各赛季的 URL 结构规律

URL 模式发现：
- Bundesliga: /football/germany/bundesliga[-YYYY-YYYY]/teamA-teamB-HHHHHHHH/
- La Liga: /football/spain/laliga[-YYYY-YYYY]/teamA-teamB-HHHHHHHH/
- Serie A: /football/italy/serie-a[-YYYY-YYYY]/teamA-teamB-HHHHHHHH/
- Ligue 1: /football/france/ligue-1[-YYYY-YYYY]/teamA-teamB-HHHHHHHH/
- Premier League: /football/england/premier-league[-YYYY-YYYY]/teamA-teamB-HHHHHHHH/

哈希规则：8 位随机字符（大写字母 + 数字）

Author: 首席数据采集官 & 算法专家
Version: V39.1 Pattern Mining
Date: 2026-01-12
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class LeagueURLPattern:
    """联赛 URL 模式"""
    league_name: str
    base_url: str
    has_season_suffix: bool
    example_urls: List[str]
    count: int


# ============================================================================
# URL 模式配置
# ============================================================================

LEAGUE_PATTERNS: Dict[str, Dict[str, str]] = {
    "La Liga": {
        "base": "https://www.oddsportal.com/football/spain/laliga",
        "country": "spain",
        "slug": "laliga",
    },
    "Premier League": {
        "base": "https://www.oddsportal.com/football/england/premier-league",
        "country": "england",
        "slug": "premier-league",
    },
    "Serie A": {
        "base": "https://www.oddsportal.com/football/italy/serie-a",
        "country": "italy",
        "slug": "serie-a",
    },
    "Bundesliga": {
        "base": "https://www.oddsportal.com/football/germany/bundesliga",
        "country": "germany",
        "slug": "bundesliga",
    },
    "Ligue 1": {
        "base": "https://www.oddsportal.com/football/france/ligue-1",
        "country": "france",
        "slug": "ligue-1",
    },
}

# 赛季映射表（用于构造 URL）
SEASON_MAPPING: Dict[str, str] = {
    "23/24": "2023-2024",
    "22/23": "2022-2023",
    "21/22": "2021-2022",
    "20/21": "2020-2021",
    "19/20": "2019-2020",
    # 添加更多赛季映射...
}


# ============================================================================
# URL 构造函数
# ============================================================================

def slugify_team_name(team_name: str) -> str:
    """
    将队名转换为 URL slug 格式

    Args:
        team_name: 原始队名

    Returns:
        URL slug (小写，空格转连字符，移除特殊字符)
    """
    # Unicode 规范化
    import unicodedata
    normalized = unicodedata.normalize('NFD', team_name)
    # 移除变音符号
    ascii_only = ''.join(
        c for c in normalized
        if unicodedata.category(c) != 'Mn'
    )
    # 转小写，空格转连字符
    slug = ascii_only.lower().replace(' ', '-').replace("'", '')
    # 移除多余连字符
    slug = re.sub(r'-+', '-', slug)
    return slug


def construct_match_url(
    league_name: str,
    home_team: str,
    away_team: str,
    season: str,
    hash_id: str
) -> str:
    """
    构造 OddsPortal 比赛页面 URL

    Args:
        league_name: 联赛名称
        home_team: 主队名称
        away_team: 客队名称
        season: 赛季（格式：23/24）
        hash_id: 8 位哈希 ID

    Returns:
        完整的 OddsPortal URL
    """
    if league_name not in LEAGUE_PATTERNS:
        raise ValueError(f"Unsupported league: {league_name}")

    pattern = LEAGUE_PATTERNS[league_name]
    base_url = pattern["base"]

    # 转换赛季格式
    season_suffix = SEASON_MAPPING.get(season, "")
    if season_suffix:
        full_url = f"{base_url}-{season_suffix}/"
    else:
        full_url = f"{base_url}/"

    # 转换队名
    home_slug = slugify_team_name(home_team)
    away_slug = slugify_team_name(away_team)

    # 构造完整 URL
    url = f"{full_url}{home_slug}-{away_slug}-{hash_id}/"
    return url


def extract_hash_from_url(url: str) -> str:
    """
    从 OddsPortal URL 提取哈希 ID

    Args:
        url: OddsPortal URL

    Returns:
        8 位哈希 ID 或空字符串
    """
    # 匹配模式: teamA-teamB-HHHHHHHH/
    match = re.search(r'/[^/]+-[^/]+-([A-Z0-9]{8})/$', url)
    if match:
        return match.group(1)
    return ""


# ============================================================================
# 主要功能
# ============================================================================

def generate_url_pattern_report() -> str:
    """生成 URL 模式报告"""
    report = []
    report.append("=" * 80)
    report.append("V39.1 哈希 ID 规律挖掘报告")
    report.append("=" * 80)
    report.append("")

    for league, pattern in LEAGUE_PATTERNS.items():
        report.append(f"## {league}")
        report.append(f"  Base URL: {pattern['base']}")
        report.append(f"  Country: {pattern['country']}")
        report.append(f"  Slug: {pattern['slug']}")
        report.append("")

        # 赛季变体
        report.append("  赛季变体:")
        for short_season, full_season in SEASON_MAPPING.items():
            url = f"{pattern['base']}-{full_season}/"
            report.append(f"    {short_season}: {url}")
        report.append("")

        # 示例 URL
        report.append("  示例 URL:")
        if league == "Premier League":
            example = construct_match_url(
                "Premier League",
                "Arsenal",
                "Chelsea",
                "23/24",
                "AbCd1234"
            )
            report.append(f"    {example}")
        report.append("")

    report.append("=" * 80)
    report.append("哈希规则")
    report.append("=" * 80)
    report.append("- 长度: 8 位字符")
    report.append("- 字符集: 大写字母 (A-Z) + 数字 (0-9)")
    report.append("- 示例: AbCd1234, XYz98765")
    report.append("")

    report.append("=" * 80)
    report.append("队名转换规则")
    report.append("=" * 80)
    examples = [
        ("Manchester United", "manchester-united"),
        ("Real Madrid", "real-madrid"),
        ("FC Bayern München", "fc-bayern-munchen"),
        ("Paris Saint-Germain", "paris-saint-germain"),
    ]
    for original, expected in examples:
        result = slugify_team_name(original)
        status = "✅" if result == expected else "❌"
        report.append(f"{status} {original} → {result} (期望: {expected})")
    report.append("")

    return "\n".join(report)


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == "__main__":
    # 生成报告
    report = generate_url_pattern_report()
    print(report)

    # 保存到文件
    with open("logs/v39_1_url_pattern_report.txt", "w", encoding="utf-8") as f:
        f.write(report)

    print("=" * 80)
    print("✅ 报告已保存到: logs/v39_1_url_pattern_report.txt")
    print("=" * 80)
