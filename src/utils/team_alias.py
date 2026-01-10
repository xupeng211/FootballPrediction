#!/usr/bin/env python3
"""V150.49 Team Alias Engine - 原子词别名匹配系统.

本模块整合了 V150.41、V150.44 和 V150.49 中开发的所有别名匹配逻辑，
提供生产级的队名标准化、模糊匹配和置信度评分功能。

核心功能：
1. 队名标准化 - 处理缩写、大小写、特殊字符
2. 别名展开 - 生成所有可能的队名变体
3. 模糊匹配 - 基于字符串相似度的智能匹配
4. 置信度评分 - 0-100 分的质量评估

准入红线：严禁将置信度低于 85% 的匹配直接更新进数据库

Author: 高级首席架构师 & 数据质量专家
Version: V150.49
Date: 2026-01-11
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# 队名别名字典库（V150.41 综合版）
# ============================================================================

# 常见缩写映射表
TEAM_ABBREVIATIONS: Dict[str, str] = {
    # 常见缩写
    'utd': 'united',
    'untd': 'united',
    'unt': 'united',
    'fc': '',
    'afc': '',
    'city': 'city',  # 保持不变
    'spurs': 'tottenham',
    'thfc': 'tottenham',
    'whu': 'west ham',
    'wh': 'west ham',
    'wba': 'west bromwich albion',
    'wb': 'west bromwich albion',
    'bha': 'brighton',
    'bh': 'brighton',
    'scouse': 'liverpool',
    'reds': 'liverpool',
    'blues': 'chelsea',
    'gunners': 'arsenal',
    'saints': 'southampton',
    'posh': 'peterborough',  # 英冠
    'addicks': 'charlton',    # 英冠
    'robins': 'bristol city', # 英冠
    'tykes': 'barnsley',      # 英冠
}

# 多词队名映射表（用于识别完整队名）
MULTI_WORD_TEAMS: Dict[str, List[str]] = {
    'manchester united': ['man utd', 'manchester utd', 'man untd', 'manchester'],
    'manchester city': ['man city', 'mancity', 'manchester'],
    'west ham united': ['west ham', 'west ham utd', 'whu', 'wh'],
    'west bromwich albion': ['west brom', 'wba', 'west bromwich', 'wb'],
    'tottenham hotspur': ['tottenham', 'spurs', 'thfc', 'tot'],
    'crystal palace': ['crystal pal', 'palace', 'cp'],
    'newcastle united': ['newcastle', 'newcastle utd', 'newc', 'nufc'],
    'sheffield united': ['sheffield', 'sheffield utd', 'sheff utd', 'sufc'],
    'nottingham forest': ['nottingham', 'nottm forest', 'nottm', 'nffc'],
    'brighton hove albion': ['brighton', 'bha', 'brighton hove'],
    'leeds united': ['leeds', 'leeds utd', 'lufc'],
    'leicester city': ['leicester', 'leic city', 'lcfc'],
    'aston villa': ['aston villa', 'villa', 'avfc'],
    'london': '',  # 移除泛指
}

# 常见前缀/后缀标准化
TEAM_PREFIXES: List[str] = [
    'afc ', 'a.f.c. ', 'a.c. ',
    'fc ', 'f.c. ',
]

# 常见英超球队名（用于辅助 URL 解析）
COMMON_EPL_TEAMS: set[str] = {
    "manchester city", "manchester united", "manchester utd", "man utd",
    "liverpool", "chelsea", "arsenal", "tottenham hotspur", "spurs",
    "newcastle united", "newcastle", "brighton", "brighton hove albion",
    "west ham united", "west ham", "wolverhampton wanderers", "wolves",
    "aston villa", "leicester city", "leicester", "everton",
    "southampton", "nottingham forest", "nottm forest", "west bromwich albion", "west brom",
    "crystal palace", "bournemouth", "fulham",
    "leeds united", "burnley", "sheffield united", "norwich city",
    "watford", "brentford",
}


# ============================================================================
# 置信度阈值配置
# ============================================================================

CONFIDENCE_THRESHOLD = {
    'HIGH': 90,      # 自动准入
    'MEDIUM': 70,    # 需人工确认
    'LOW': 0,        # 匹配失败
    'SAFE_MIN': 85   # 最低安全线（准入红线）
}


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class MatchResult:
    """匹配结果"""
    fotmob_id: Optional[int]
    scraped_home: str
    scraped_away: str
    db_home: str
    db_away: str
    confidence: float
    tier: str
    url: str


@dataclass
class TeamAliasMatch:
    """队名别名匹配结果"""
    normalized_name: str
    aliases: List[str]
    similarity: float
    is_confident: bool


# ============================================================================
# 核心算法
# ============================================================================

def normalize_team_name(name: str) -> str:
    """
    标准化队名

    处理：
    - 大小写统一
    - 移除特殊字符
    - 处理缩写

    Args:
        name: 原始队名

    Returns:
        标准化后的队名
    """
    if not name:
        return ""

    # 转小写
    name = name.lower().strip()

    # 移除特殊字符
    name = re.sub(r'[^\w\s-]', '', name)

    # 处理缩写
    words = name.split()
    normalized_words = []

    for word in words:
        # 检查是否是已知缩写
        if word in TEAM_ABBREVIATIONS:
            replacement = TEAM_ABBREVIATIONS[word]
            if replacement:  # 不添加空替换
                normalized_words.append(replacement)
        else:
            normalized_words.append(word)

    # 重新组合
    name = ' '.join(normalized_words)

    # 移除多余空格
    name = ' '.join(name.split())

    return name


def expand_team_name(name: str) -> List[str]:
    """
    展开队名为所有可能的变体

    Args:
        name: 标准化后的队名

    Returns:
        所有可能的队名变体列表
    """
    variants = [name]

    # 检查是否匹配多词队名
    for full_name, abbreviations in MULTI_WORD_TEAMS.items():
        if name == full_name.lower():
            variants.extend(abbreviations)
        elif name in abbreviations:
            variants.append(full_name)

    return list(set(variants))


def calculate_similarity(name1: str, name2: str) -> float:
    """
    计算两个队名的相似度

    Args:
        name1: 队名1
        name2: 队名2

    Returns:
        相似度 (0-100)
    """
    if not name1 or not name2:
        return 0.0

    # 标准化
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)

    # === 特殊高频匹配强化 ===
    # Man Utd / Manchester Utd -> Manchester United
    # 检查原始输入和标准化后的组合
    combined1 = name1.lower() + ' ' + norm1
    combined2 = name2.lower() + ' ' + norm2

    # Man Utd patterns
    if ('man utd' in combined1 or 'manchester utd' in combined1) and 'manchester united' in combined2:
        return 97.0
    if ('man utd' in combined2 or 'manchester utd' in combined2) and 'manchester united' in combined1:
        return 97.0

    # Spurs -> Tottenham Hotspur
    if ('spurs' in combined1 or 'spurs' in combined2) and 'tottenham' in norm1 and 'tottenham' in norm2:
        return 96.0

    # 完全匹配
    if norm1 == norm2:
        return 100.0

    # 计算序列相似度
    seq_ratio = SequenceMatcher(None, norm1, norm2).ratio() * 100

    # 展开变体后再计算
    variants1 = expand_team_name(norm1)
    variants2 = expand_team_name(norm2)

    max_variant_score = seq_ratio
    for v1 in variants1:
        for v2 in variants2:
            variant_score = SequenceMatcher(None, v1, v2).ratio() * 100
            max_variant_score = max(max_variant_score, variant_score)

    return max_variant_score


def match_teams(scraped_home: str, scraped_away: str,
                db_home: str, db_away: str) -> Tuple[float, str]:
    """
    匹配两对队名并计算置信度

    Args:
        scraped_home: 采集的主队名
        scraped_away: 采集的客队名
        db_home: 数据库的主队名
        db_away: 数据库的客队名

    Returns:
        (置信度分数 0-100, 详细说明)
    """
    # 计算主队相似度
    home_sim = calculate_similarity(scraped_home, db_home)
    away_sim = calculate_similarity(scraped_away, db_away)

    # 计算反向相似度（处理主客颠倒的情况）
    home_reverse_sim = calculate_similarity(scraped_home, db_away)
    away_reverse_sim = calculate_similarity(scraped_away, db_home)

    # 正向匹配分数
    forward_score = (home_sim + away_sim) / 2

    # 反向匹配分数（如果两个都高，说明可能主客颠倒了）
    reverse_score = (home_reverse_sim + away_reverse_sim) / 2

    # 选择更高的分数
    best_score = max(forward_score, reverse_score)

    # 生成说明
    details = []
    details.append(f"Home: '{scraped_home}' vs '{db_home}' = {home_sim:.1f}%")
    details.append(f"Away: '{scraped_away}' vs '{db_away}' = {away_sim:.1f}%")

    if reverse_score > forward_score and reverse_score > 70:
        details.append(f"⚠️ 可能主客颠倒: {reverse_score:.1f}%")

    return best_score, '; '.join(details)


def determine_tier(confidence: float) -> str:
    """
    根据置信度确定等级

    Args:
        confidence: 置信度分数 (0-100)

    Returns:
        等级: 'HIGH', 'MEDIUM', 'LOW'
    """
    if confidence >= CONFIDENCE_THRESHOLD['HIGH']:
        return 'HIGH'
    elif confidence >= CONFIDENCE_THRESHOLD['MEDIUM']:
        return 'MEDIUM'
    else:
        return 'LOW'


def is_safe_confidence(confidence: float) -> bool:
    """
    检查置信度是否达到安全线

    Args:
        confidence: 置信度分数 (0-100)

    Returns:
        是否安全（>= 准入红线）
    """
    return confidence >= CONFIDENCE_THRESHOLD['SAFE_MIN']


def extract_team_names_from_url(url: str) -> Optional[Tuple[str, str]]:
    """
    从 OddsPortal URL 中提取队名

    URL 格式: /football/england/premier-league-{season}/{home}-{away}-{hash}/

    Args:
        url: OddsPortal URL

    Returns:
        (home_team, away_team) 或 None
    """
    # 提取联赛后的部分
    match = re.search(r'/football/england/premier-league-[^/]+/([^/]+)/?', url)
    if not match:
        return None

    teams_part = match.group(1)

    # 分割队名和 ID
    parts = teams_part.split('-')

    # 找到 8-12 字符 ID（排除纯小写字母）
    id_idx = None
    for i, part in enumerate(parts):
        if 8 <= len(part) <= 12:
            has_digit = any(c.isdigit() for c in part)
            has_upper = any(c.isupper() for c in part)
            is_id = has_digit or has_upper or not part.isalpha()
            if is_id:
                id_idx = i
                break

    # 获取队名部分
    if id_idx is not None:
        team_parts = parts[:id_idx]
    else:
        team_parts = parts

    if len(team_parts) < 2:
        return None

    # 智能分割主客队
    home, away = _split_teams_smartly(team_parts)

    if home is None or away is None:
        return None

    return (home, away)


def _split_teams_smartly(parts: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    智能分割主客队

    Args:
        parts: URL 分割后的部分（不含 ID）

    Returns:
        (home_team, away_team) 或 (None, None)
    """
    # 尝试所有可能的分割点，优先选择"两者都已知"的分割
    best_match = None
    fallback_match = None

    for i in range(1, len(parts)):
        home_parts = parts[:i]
        away_parts = parts[i:]

        home_candidate = ' '.join(home_parts).title()
        away_candidate = ' '.join(away_parts).title()

        # 标准化后检查是否匹配已知球队
        home_norm = normalize_team_name(home_candidate)
        away_norm = normalize_team_name(away_candidate)

        # 检查是否在已知球队列表中
        home_known = home_norm in COMMON_EPL_TEAMS
        away_known = away_norm in COMMON_EPL_TEAMS

        # 两者都是已知球队（最佳匹配）
        if home_known and away_known:
            return (home_candidate, away_candidate)

        # 至少一个已知且分割合理（备用匹配）
        if fallback_match is None:
            if home_known and len(away_parts) <= 3:
                fallback_match = (home_candidate, away_candidate)
            elif away_known and len(home_parts) <= 3:
                fallback_match = (home_candidate, away_candidate)

    # 如果没有找到最佳匹配，使用备用匹配
    if fallback_match is not None:
        return fallback_match

    # 如果无法智能分割，使用简单策略（首尾）
    if len(parts) == 2:
        return (parts[0].title(), parts[1].title())

    return (None, None)


# ============================================================================
# 便捷函数
# ============================================================================

def get_team_aliases(team_name: str) -> TeamAliasMatch:
    """
    获取队名的所有别名和相似度信息

    Args:
        team_name: 队名

    Returns:
        TeamAliasMatch 对象
    """
    normalized = normalize_team_name(team_name)
    aliases = expand_team_name(normalized)

    # 计算与标准名的相似度
    similarity = SequenceMatcher(None, normalized.lower(), team_name.lower()).ratio()
    is_confident = similarity >= 0.85

    return TeamAliasMatch(
        normalized_name=normalized,
        aliases=aliases,
        similarity=similarity * 100,
        is_confident=is_confident
    )


def batch_normalize_team_names(team_names: List[str]) -> Dict[str, str]:
    """
    批量标准化队名

    Args:
        team_names: 队名列表

    Returns:
        {原始队名: 标准化队名} 字典
    """
    return {name: normalize_team_name(name) for name in team_names}


# ============================================================================
# 单元测试
# ============================================================================

class _TeamAliasTests:
    """内部单元测试（用于验证别名引擎功能）"""

    @staticmethod
    def run_tests() -> bool:
        """运行所有单元测试"""
        import unittest

        class TestTeamAlias(unittest.TestCase):
            def test_normalize_abbreviations(self):
                """测试缩写标准化"""
                self.assertEqual(normalize_team_name('Man Utd'), 'man united')
                self.assertEqual(normalize_team_name('Spurs'), 'tottenham')
                self.assertEqual(normalize_team_name('WHU'), 'west ham')

            def test_expand_aliases(self):
                """测试别名展开"""
                variants = expand_team_name('man utd')
                self.assertIn('manchester united', variants)

            def test_similarity_perfect(self):
                """测试完全匹配相似度"""
                sim = calculate_similarity('Arsenal', 'Arsenal')
                self.assertEqual(sim, 100.0)

            def test_similarity_abbreviation(self):
                """测试缩写匹配相似度"""
                sim = calculate_similarity('Man Utd', 'Manchester United')
                self.assertGreaterEqual(sim, 95.0)

            def test_match_teams(self):
                """测试队名匹配"""
                score, details = match_teams('Arsenal', 'Chelsea', 'Arsenal', 'Chelsea')
                self.assertEqual(score, 100.0)

            def test_tier_classification(self):
                """测试等级分类"""
                self.assertEqual(determine_tier(95), 'HIGH')
                self.assertEqual(determine_tier(80), 'MEDIUM')
                self.assertEqual(determine_tier(50), 'LOW')

            def test_safe_confidence(self):
                """测试安全线检查"""
                self.assertTrue(is_safe_confidence(90))
                self.assertFalse(is_safe_confidence(80))

        # 运行测试
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTeamAlias)
        runner = unittest.TextTestRunner(verbosity=0)
        result = runner.run(suite)
        return result.wasSuccessful()


# 模块初始化时运行测试（可选）
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    success = _TeamAliasTests.run_tests()
    if success:
        logger.info("✅ 所有单元测试通过")
    else:
        logger.error("❌ 单元测试失败")
