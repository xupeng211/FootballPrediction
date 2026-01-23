#!/usr/bin/env python3
"""V41.700 Team Name Normalizer - 多国语言球队名标准化模块.

核心功能:
    1. 多国语言昵称映射 (意/德/法/西)
    2. 核心词提取算法
    3. 双层校验 (核心词 100% + 模糊匹配)

Usage:
    >>> from src.core.team_name_normalizer import normalize_team_name, calculate_similarity
    >>> normalize_team_name("Milan")
    'ac milan'
    >>> calculate_similarity("Milan", "AC Milan")
    95.0  # 核心词匹配加分
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from thefuzz import fuzz

# ============================================================================
# 多国语言昵称映射 (V41.700)
# ============================================================================

# 英超映射
ENGLISH_NICKNAMES = {
    "wolves": "wolverhampton wanderers",
    "spurs": "tottenham hotspur",
    "tottenham": "tottenham hotspur",
    "west ham": "west ham united",
    "man city": "manchester city",
    "manchester city": "manchester city",
    "manchester united": "manchester united",
    "man utd": "manchester united",
    "man united": "manchester united",
    "newcastle": "newcastle united",
    "newcastle united": "newcastle united",
    "nottingham": "nottingham forest",
    "nottingham forest": "nottingham forest",
    "nottm forest": "nottingham forest",
    "sheffield united": "sheffield united",
    "sheffield": "sheffield united",
    "burnley": "burnley",
    "leeds": "leeds united",
    "leeds united": "leeds united",
    "leicester": "leicester city",
    "leicester city": "leicester city",
    "brighton": "brighton & hove albion",
    "brighton & hove": "brighton & hove albion",
    "hove albion": "brighton & hove albion",
    "aston villa": "aston villa",
    "bournemouth": "bournemouth",
    "afc bournemouth": "bournemouth",
    "bourn": "bournemouth",
    "crystal palace": "crystal palace",
    "palace": "crystal palace",
    "ipswich": "ipswich town",
    "ipswich town": "ipswich town",
    "fulham": "fulham",
    "brentford": "brentford",
    "everton": "everton",
    "chelsea": "chelsea",
    "arsenal": "arsenal",
    "liverpool": "liverpool",
    "manchester": "manchester",  # 模糊匹配需小心
}

# 意甲映射 (Serie A)
ITALIAN_NICKNAMES = {
    "milan": "ac milan",
    "ac milan": "ac milan",
    "inter": "inter milan",
    "inter milan": "inter milan",
    "internazionale": "inter milan",
    "roma": "as roma",
    "as roma": "as roma",
    "roma": "as roma",
    "lazio": "ss lazio",
    "ss lazio": "ss lazio",
    "s.s. lazio": "ss lazio",
    "juventus": "juventus",
    "juve": "juventus",
    "juventus fc": "juventus",
    "napoli": "napoli",
    "fiorentina": "fiorentina",
    "firenze": "fiorentina",
    "atalanta": "atalanta",
    "bologna": "bologna",
    "torino": "torino",
    "genoa": "genoa",
    "sampdoria": "sampdoria",
    "sassuolo": "sassuolo",
    "verona": "hellas verona",
    "hellas": "hellas verona",
    "hellas verona": "hellas verona",
    "udinese": "udinese",
    "monza": "monza",
    "lecce": "lecce",
    "como": "como",
    "cagliari": "cagliari",
    "parma": "parma",
    "empoli": "empoli",
    "cremonese": "cremonese",
    " Venezia": "venezia",
    "palermo": "palermo",
}

# 德甲映射 (Bundesliga)
GERMAN_NICKNAMES = {
    "bayern": "bayern munchen",
    "bayern munchen": "bayern munchen",
    "bayern munich": "bayern munchen",
    "dortmund": "borussia dortmund",
    "borussia dortmund": "borussia dortmund",
    "leverkusen": "bayer leverkusen",
    "bayer leverkusen": "bayer leverkusen",
    "gladbach": "borussia monchengladbach",
    "monchengladbach": "borussia monchengladbach",
    "mönchengladbach": "borussia monchengladbach",
    "borussia monchengladbach": "borussia monchengladbach",
    "mainz": "mainz 05",
    "mainz 05": "mainz 05",
    "fsv mainz 05": "mainz 05",
    "rb leipzig": "rb leipzig",
    "leipzig": "rb leipzig",
    "eintracht": "eintracht frankfurt",
    "eintracht frankfurt": "eintracht frankfurt",
    "frankfurt": "eintracht frankfurt",
    "wolfsburg": "vfl wolfsburg",
    "vfl wolfsburg": "vfl wolfsburg",
    "freiburg": "sc freiburg",
    "sc freiburg": "sc freiburg",
    "hoffenheim": "tsg hoffenheim",
    "tsg hoffenheim": "tsg hoffenheim",
    "bochum": "vfl bochum",
    "vfl bochum": "vfl bochum",
    "augsburg": "fc augsburg",
    "fc augsburg": "fc augsburg",
    "stuttgart": "vfb stuttgart",
    "vfb stuttgart": "vfb stuttgart",
    "bremen": "werder bremen",
    "werder bremen": "werder bremen",
    "hamburg": "hsv",
    "hsv": "hamburger sv",
    "hamburger sv": "hamburger sv",
    "koln": "fc koln",
    "fc koln": "fc koln",
    "fc koln 1863": "fc koln",
    "munich": "bayern munchen",  # 需上下文
    "union berlin": "1. fc union berlin",
    "heidenheim": "1. fc heidenheim",
    "fc heidenheim": "1. fc heidenheim",
    "pauli": "fc st pauli",
    "st pauli": "fc st pauli",
    "fc st pauli": "fc st pauli",
    "holstein": "holstein kiel",
    "holstein kiel": "holstein kiel",
    "darmstadt": "sv darmstadt 98",
    "sv darmstadt 98": "sv darmstadt 98",
    "braunschweig": "eintracht braunschweig",
}

# 西甲映射 (La Liga)
SPANISH_NICKNAMES = {
    "real madrid": "real madrid",
    "madrid": "real madrid",
    "barcelona": "fc barcelona",
    "fc barcelona": "fc barcelona",
    "atletico madrid": "atletico madrid",
    "atletico": "atletico madrid",
    "atleti": "atletico madrid",
    "atlético madrid": "atletico madrid",
    "sevilla": "sevilla fc",
    "sevilla fc": "sevilla fc",
    "valencia": "valencia cf",
    "valencia cf": "valencia cf",
    "real betis": "real betis",
    "betis": "real betis",
    "real sociedad": "real sociedad",
    "real sociedad": "real sociedad",
    "athletic bilbao": "athletic bilbao",
    "athletic club": "athletic bilbao",
    "bilbao": "athletic bilbao",
    "villarreal": "villarreal cf",
    "villarreal cf": "villarreal cf",
    "real valladolid": "real valladolid",
    "valladolid": "real valladolid",
    "getafe": "getafe cf",
    "getafe cf": "getafe cf",
    "espanyol": "rcd espanyol",
    "rcd espanyol": "rcd espanyol",
    "espanyol": "rcd espanyol",
    "celta vigo": "celta vigo",
    "celta": "celta vigo",
    "real mallorca": "rCD mallorca",
    "mallorca": "rcd mallorca",
    "rcd mallorca": "rcd mallorca",
    "osasuna": "ca osasuna",
    "ca osasuna": "ca osasuna",
    "alaves": "deportivo alaves",
    "deportivo alaves": "deportivo alaves",
    "rayo": "rayo vallecano",
    "rayo vallecano": "rayo vallecano",
    "vallecano": "rayo vallecano",
    "girona": "girona fc",
    "girona fc": "girona fc",
    "leganes": "cd leganes",
    "cd leganes": "cd leganes",
    "almeria": "ud almeria",
    "ud almeria": "ud almeria",
    "las palmas": "ud las palmas",
    "ud las palmas": "ud las palmas",
    "elche": "elche cf",
    "elche cf": "elche cf",
    "levant": "levante ud",
    "levante ud": "levante ud",
}

# 法甲映射 (Ligue 1)
FRENCH_NICKNAMES = {
    "psg": "paris saint-germain",
    "paris saint-germain": "paris saint-germain",
    "paris": "paris saint-germain",
    "paris sg": "paris saint-germain",
    "monaco": "as monaco",
    "as monaco": "as monaco",
    "lyon": "olympique lyonnais",
    "olympique lyonnais": "olympique lyonnais",
    "ol": "olympique lyonnais",
    "marseille": "olympique marseille",
    "olympique marseille": "olympique marseille",
    "om": "olympique marseille",
    "lille": "losc lille",
    "losc lille": "losc lille",
    "nice": "ogc nice",
    "ogc nice": "ogc nice",
    "rennes": "stade rennais",
    "stade rennais": "stade rennais",
    "lens": "racing lens",
    "racing lens": "racing lens",
    "reims": "stade de reims",
    "stade de reims": "stade de reims",
    "nantes": "fc nantes",
    "fc nantes": "fc nantes",
    "strasbourg": "rc strasbourg",
    "rc strasbourg": "rc strasbourg",
    "toulouse": "toulouse fc",
    "toulouse fc": "toulouse fc",
    "montpellier": "montpellier hsc",
    "montpellier hsc": "montpellier hsc",
    "bordeaux": "fc girondins bordeaux",
    "fc girondins bordeaux": "fc girondins bordeaux",
    "angers": "angers sco",
    "angers sco": "angers sco",
    "brest": "stade brestois",
    "stade brestois": "stade brestois",
    "metz": "fc metz",
    "fc metz": "fc metz",
    "lorient": "fc lorient",
    "fc lorient": "fc lorient",
    "clermont": "clermont foot",
    "clermont foot": "clermont foot",
    "le havre": "havre ac",
    "havre ac": "havre ac",
    "auxerre": "aj auxerre",
    "aj auxerre": "aj auxerre",
    "nancy": "as nancy",
    "as nancy": "as nancy",
    "saint-etienne": "as saint-etienne",
    "as saint-etienne": "as saint-etienne",
    "etienne": "as saint-etienne",
    "psaint-germain": "paris saint-germain",
    "st etienne": "as saint-etienne",
}

# 合并所有映射
ALL_NICKNAMES = {}
ALL_NICKNAMES.update(ENGLISH_NICKNAMES)
ALL_NICKNAMES.update(ITALIAN_NICKNAMES)
ALL_NICKNAMES.update(GERMAN_NICKNAMES)
ALL_NICKNAMES.update(SPANISH_NICKNAMES)
ALL_NICKNAMES.update(FRENCH_NICKNAMES)


# ============================================================================
# 核心词提取算法
# ============================================================================


def extract_core_words(team_name: str) -> list[str]:
    """提取球队名的核心词汇.

    核心词定义:
        1. 城市名 (Paris, Milan, London, etc.)
        2. 独特标识符 (Inter, Juventus, PSG, etc.)
        3. 排除通用前缀 (FC, AS, SS, SD, etc.)

    Args:
        team_name: 原始球队名

    Returns:
        核心词列表 (按重要性排序)
    """
    if not team_name:
        return []

    # 标准化: 小写 + 移除重音符号
    name = team_name.lower().strip()
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])

    # 移除通用前缀
    prefixes_to_remove = ['fc ', 'fc', 'as ', 'as', 'ss ', 'ss', 's.s.', 'sd ', 'sd',
                          'rcd ', 'rcd', 'ud ', 'ud', 'cd ', 'cd', 'ac ', 'ac', 'rfc ', 'rfc',
                          'tsg ', 'tsg', 'vfl ', 'vfl', '1. ', '1.', 'fsv ', 'fsv',
                          'sc ', 'sc', 'losc ', 'losc', 'ogc ', 'ogc', 'hsc ', 'hsc',
                          'sco ', 'sco', 'uc ', 'uc', 'vs ', 'vs', 'atp ', 'atp',
                          'racing ', 'racing', 'stade ', 'stade', 'olympique ', 'olympique',
                          'girondins ', 'girondins', 'brestois ', 'brestois', 'havre ', 'havre']

    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
            break

    # 分割为单词
    words = re.split(r'[\s\-&]+', name)

    # 过滤停用词 (短单词和无意义词汇)
    stopwords = {'cf', 'fc', 'ac', 'as', 'ss', 'sd', 'rcd', 'ud', 'cd', 'vs',
                  'united', 'city', 'athletic', 'club', 'deportivo', 'inter',
                  'milan', 'fc', 'hotspur', 'albion', 'wanderers', 'rovers',
                  'palace', 'villa', 'forest', 'county', 'town', 'city'}

    # 提取有意义的核心词
    core_words = []
    for word in words:
        if len(word) >= 3 and word not in stopwords:
            core_words.append(word)

    # 特殊处理: 某些短词是核心标识
    special_short_words = {
        'milan', 'inter', 'juve', 'psg', 'om', 'ol', 'roma',
        'lazio', 'napoli', 'fiorentina', 'atalanta', 'bologna',
        'torino', 'genoa', 'verona', 'udinese', 'monza', 'como',
        'lecce', 'cagliari', 'sassuolo', 'empoli', 'cremonese',
        'venezia', 'palermo', 'spezia', 'genoa',
        'leverkusen', 'gladbach', 'hoffenheim', 'wolfsburg',
        'dortmund', 'leverkusen', 'freiburg', 'bremen', 'hamburg',
        'koln', 'mainz', 'augsburg', 'stuttgart', 'heidenheim',
        'bochum', 'pauli', 'holstein', 'darmstadt', 'braunschweig',
        'köln', 'mönchengladbach', 'fürth', 'hoffenheim',
        'monchengladbach', 'pauli', 'heidenheim',
        'madrid', 'barcelona', 'sevilla', 'valencia', 'betis',
        'sociedad', 'bilbao', 'villarreal', 'valladolid', 'getafe',
        'espanyol', 'celta', 'mallorca', 'osasuna', 'alaves',
        'rayo', 'girona', 'leganes', 'almeria', 'palmas',
        'elche', 'levant', 'granada', 'cadiz', 'almeria',
        ' PSG', 'om', 'ol',
    }

    for word in words:
        if word in special_short_words or word.lower() in special_short_words:
            if word not in core_words:
                core_words.append(word)

    return core_words


# ============================================================================
# 队名标准化
# ============================================================================


def normalize_team_name(team_name: str) -> str:
    """标准化球队名称 (V41.700 增强版).

    处理流程:
        1. 移除重音符号 (ö → o, é → e)
        2. 应用多国语言昵称映射
        3. 统一为小写

    Args:
        team_name: 原始球队名

    Returns:
        标准化后的球队名
    """
    if not team_name:
        return ""

    # 移除多余空格和特殊字符
    name = team_name.strip()

    # 移除重音符号 (德语、法语等)
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])

    # 统一为小写
    name = name.lower()

    # 应用昵称映射 (最长匹配优先)
    # 按长度降序排序以匹配最长键
    sorted_nicknames = sorted(ALL_NICKNAMES.items(), key=lambda x: len(x[0]), reverse=True)

    for nickname, full_name in sorted_nicknames:
        # 精确匹配
        if name == nickname:
            return full_name
        # 包含匹配 (避免误匹配)
        if len(nickname) >= 5 and nickname in name and len(nickname) >= len(name) * 0.7:
            return full_name

    return name


def calculate_similarity(name1: str, name2: str) -> float:
    """计算两个球队名的相似度 (V41.700 双层校验版).

    双层校验:
        1. 核心词匹配: 如果核心词 100% 匹配，加分
        2. 模糊匹配: thefuzz.ratio() 基础分

    Args:
        name1: 第一个球队名
        name2: 第二个球队名

    Returns:
        相似度分数 (0-100)
    """
    if not name1 or not name2:
        return 0.0

    # 标准化两个队名
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)

    # 基础相似度
    base_sim = fuzz.ratio(norm1, norm2)

    # 核心词加分
    core_words1 = set(extract_core_words(name1))
    core_words2 = set(extract_core_words(name2))

    core_boost = 0.0
    if core_words1 and core_words2:
        # 计算核心词重叠度
        overlap = core_words1 & core_words2
        union = core_words1 | core_words2

        if overlap:
            # 完全匹配: 大幅加分
            if overlap == union:
                core_boost = 30.0  # 核心词完全匹配
            else:
                # 部分匹配: 按比例加分
                jaccard = len(overlap) / len(union)
                core_boost = jaccard * 20.0  # 最多加 20 分

    # 特殊加分: 完全精确匹配
    if norm1 == norm2:
        base_sim = 100.0
    elif base_sim < 100 and norm1 in norm2 or norm2 in norm1:
        # 子串匹配加分
        base_sim = max(base_sim, 75.0)

    # 最终分数: 基础分 + 核心词加分 (最高 100)
    final_sim = min(base_sim + core_boost, 100.0)

    return final_sim


def calculate_match_similarity(db_home: str, db_away: str,
                             candidate_home: str, candidate_away: str) -> float:
    """计算比赛对的相似度 (V41.700).

    Args:
        db_home: 数据库主队名
        db_away: 数据库客队名
        candidate_home: 候选主队名
        candidate_away: 候选客队名

    Returns:
        总体相似度分数 (0-100)
    """
    home_sim = calculate_similarity(db_home, candidate_home)
    away_sim = calculate_similarity(db_away, candidate_away)

    return (home_sim + away_sim) / 2


# ============================================================================
# Export
# ============================================================================

__all__ = [
    "normalize_team_name",
    "extract_core_words",
    "calculate_similarity",
    "calculate_match_similarity",
]
