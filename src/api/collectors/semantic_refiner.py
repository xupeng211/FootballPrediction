#!/usr/bin/env python3
"""V150.1 Semantic Refiner - 语义校准器.

通过 L2 级语义验证（队名关键词 + URL 解析）来重新评估 pending 记录。

功能：
1. URL 队名提取：从 oddsportal_url 中提取真实队名
2. 关键词指纹库：识别队名变体（如 Man Utd, Spurs, Wolves）
3. 置信度重算：基于队名匹配度重新计算置信度
4. 错误匹配拒绝：URL 队名与 FotMob 队名不一致的标记为 rejected

Author: 高级数据科学家 & 逻辑审计专家
Version: V150.1
Date: 2026-01-08
"""

from dataclasses import dataclass
from datetime import timedelta
import logging
import re
from typing import Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# 队名关键词指纹库
# ============================================================================

# 常见英超球队名（用于辅助 URL 解析）
COMMON_EPL_TEAMS = {
    "manchester city",
    "manchester united",
    "manchester utd",
    "man utd",
    "liverpool",
    "chelsea",
    "arsenal",
    "tottenham hotspur",
    "spurs",
    "newcastle united",
    "newcastle",
    "brighton",
    "brighton & hove albion",
    "west ham united",
    "west ham",
    "wolverhampton wanderers",
    "wolves",
    "aston villa",
    "leicester city",
    "leicester",
    "everton",
    "southampton",
    "nottingham forest",
    "nottm forest",
    "west bromwich albion",
    "west brom",
    "crystal palace",
    "bournemouth",
    "afc bournemouth",
    "fulham",
    "leeds united",
    "burnley",
    "sheffield united",
    "norwich city",
    "watford",
    "brentford",
}

# 常见队名缩写/变体映射
TEAM_NAME_ALIASEES = {
    # 曼联变体
    "man utd": "manchester united",
    "man. utd": "manchester united",
    "manchester utd": "manchester united",
    "man-united": "manchester united",
    "man united": "manchester united",
    # 热刺变体
    "spurs": "tottenham hotspur",
    "tottenham": "tottenham hotspur",
    # 狼队变体
    "wolves": "wolverhampton wanderers",
    "wolverhampton": "wolverhampton wanderers",
    # 诺丁汉森林变体
    "nottm forest": "nottingham forest",
    "nottingham": "nottingham forest",
    # 西布朗变体
    "west brom": "west bromwich albion",
    "west bromwich": "west bromwich albion",
    # 布莱顿变体
    "brighton": "brighton & hove albion",
    # 莱斯特城变体
    "leicester": "leicester city",
    "leicester city": "leicester city",
    # 纽卡斯尔变体
    "newcastle": "newcastle united",
    "newcastle utd": "newcastle united",
    # 谢周三变体
    "sheffield wed": "sheffield wednesday",
    "sheffield wednesday": "sheffield wednesday",
    # 南安普顿变体
    "southampton": "southampton",
}

# 常见前缀/后缀标准化
TEAM_PREFIXES = [
    "afc ",
    "a.f.c. ",
    "a.c. ",
    "fc ",
    "f.c. ",
]


def normalize_team_name(name: str) -> str:
    """标准化队名.

    Args:
        name: 原始队名

    Returns:
        标准化后的队名（小写、去除前缀）
    """
    name = name.lower().strip()

    # 移除常见前缀
    for prefix in TEAM_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    # 应用别名映射
    if name in TEAM_NAME_ALIASEES:
        name = TEAM_NAME_ALIASEES[name]

    return name


# ============================================================================
# URL 解析器
# ============================================================================


def extract_team_names_from_url(url: str) -> tuple[str, str] | None:
    """从 OddsPortal URL 中提取队名.

    URL 格式: /football/england/premier-league/{home}-{away}-{8-char-id}/
             或 /football/england/premier-league/{home}-{away}/

    Args:
        url: OddsPortal URL

    Returns:
        (home_team, away_team) 或 None
    """
    # 提取联赛后的部分
    match = re.search(r"/football/england/premier-league/([^/]+)/?", url)
    if not match:
        return None

    teams_part = match.group(1)

    # 分割队名和 ID
    parts = teams_part.split("-")

    # DEBUG
    logger.debug(f"URL解析: teams_part={teams_part}, parts={parts}")

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
    team_parts = parts[:id_idx] if id_idx is not None else parts

    if len(team_parts) < 2:
        return None

    # 智能分割主客队（使用已知球队名列表）
    home, away = _split_teams_smartly(team_parts)

    if home is None or away is None:
        return None

    return (home, away)


def _split_teams_smartly(parts: list[str]) -> tuple[str, str] | tuple[None, None]:
    """智能分割主客队.

    Args:
        parts: URL 分割后的部分（不含 ID）

    Returns:
        (home_team, away_team) 或 (None, None)
    """
    # 尝试所有可能的分割点，优先选择"两者都已知"的分割
    fallback_match = None

    for i in range(1, len(parts)):
        home_parts = parts[:i]
        away_parts = parts[i:]

        home_candidate = " ".join(home_parts).title()
        away_candidate = " ".join(away_parts).title()

        # 标准化后检查是否匹配已知球队
        home_norm = normalize_team_name(home_candidate)
        away_norm = normalize_team_name(away_candidate)

        # 检查是否在已知球队列表中
        home_known = home_norm in COMMON_EPL_TEAMS or any(
            home_norm in alias.split() for alias in TEAM_NAME_ALIASEES
        )
        away_known = away_norm in COMMON_EPL_TEAMS or any(
            away_norm in alias.split() for alias in TEAM_NAME_ALIASEES
        )

        # 两者都是已知球队（最佳匹配）
        if home_known and away_known:
            return (home_candidate, away_candidate)

        # 至少一个已知且分割合理（备用匹配）
        if fallback_match is None:
            if (home_known and len(away_parts) <= 3) or (away_known and len(home_parts) <= 3):
                fallback_match = (home_candidate, away_candidate)

    # 如果没有找到最佳匹配，使用备用匹配
    if fallback_match is not None:
        return fallback_match

    # 如果无法智能分割，使用简单策略（首尾）
    if len(parts) == 2:
        return (parts[0].title(), parts[1].title())

    return (None, None)


# ============================================================================
# 语义校准器
# ============================================================================


@dataclass
class RefinementResult:
    """校准结果."""

    fotmob_id: str
    home_team: str
    away_team: str
    match_date: Any
    confidence: float
    oddsportal_url: str
    should_approve: bool
    should_reject: bool
    new_confidence: float
    reason: str


class SemanticRefiner:
    """V150.1 语义校准器."""

    def __init__(self, time_tolerance_hours: int = 2):
        """初始化.

        Args:
            time_tolerance_hours: 时间容差（小时）
        """
        self.time_tolerance = timedelta(hours=time_tolerance_hours)

    def refine_record(
        self,
        fotmob_id: str,
        home_team: str,
        away_team: str,
        match_date: Any,
        confidence: float,
        oddsportal_url: str,
    ) -> RefinementResult:
        """校准单条记录.

        Args:
            fotmob_id: FotMob ID
            home_team: 主队（FotMob）
            away_team: 客队（FotMob）
            match_date: 比赛时间
            confidence: 原始置信度
            oddsportal_url: OddsPortal URL

        Returns:
            RefinementResult: 校准结果
        """
        # 1. 提取 URL 中的队名
        url_teams = extract_team_names_from_url(oddsportal_url)

        if url_teams is None:
            # 无法解析 URL，保持原状态
            return RefinementResult(
                fotmob_id=fotmob_id,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                confidence=confidence,
                oddsportal_url=oddsportal_url,
                should_approve=False,
                should_reject=False,
                new_confidence=confidence,
                reason="URL 无法解析",
            )

        url_home, url_away = url_teams

        # 2. 标准化队名
        fotmob_home_norm = normalize_team_name(home_team)
        fotmob_away_norm = normalize_team_name(away_team)
        url_home_norm = normalize_team_name(url_home)
        url_away_norm = normalize_team_name(url_away)

        # 3. 检查队名是否匹配
        home_matches = self._team_names_match(fotmob_home_norm, url_home_norm)
        away_matches = self._team_names_match(fotmob_away_norm, url_away_norm)

        # 4. 判断是否应该拒绝
        if not home_matches or not away_matches:
            # URL 队名与 FotMob 队名不一致 → 拒绝
            return RefinementResult(
                fotmob_id=fotmob_id,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                confidence=confidence,
                oddsportal_url=oddsportal_url,
                should_approve=False,
                should_reject=True,
                new_confidence=0.0,
                reason=f"队名不匹配: FotMob[{home_team} vs {away_team}] vs URL[{url_home} vs {url_away}]",
            )

        # 5. 队名匹配，计算新的置信度
        # 基于原始置信度和队名匹配度
        base_confidence = confidence
        name_match_bonus = 0.1 if (home_matches and away_matches) else 0.0

        new_confidence = min(base_confidence + name_match_bonus, 1.0)

        # 6. 判断是否应该批准
        should_approve = new_confidence >= 0.85

        return RefinementResult(
            fotmob_id=fotmob_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            confidence=confidence,
            oddsportal_url=oddsportal_url,
            should_approve=should_approve,
            should_reject=False,
            new_confidence=new_confidence,
            reason=f"队名匹配提升: {confidence:.3f} → {new_confidence:.3f}",
        )

    def _team_names_match(self, name1: str, name2: str) -> bool:
        """判断两个队名是否匹配.

        Args:
            name1: 标准化后的队名1
            name2: 标准化后的队名2

        Returns:
            bool: 是否匹配
        """
        # 精确匹配
        if name1 == name2:
            return True

        # 包含关系（如 "manchester united" vs "manchester"）
        if name1 in name2 or name2 in name1:
            # 但需要足够长（避免 "man" 匹配 "manchester"）
            min_len = min(len(name1), len(name2))
            if min_len >= 4:
                return True

        return False


def get_refiner() -> SemanticRefiner:
    """获取语义校准器单例."""
    return SemanticRefiner()
