#!/usr/bin/env python3
"""
M4模块: 比赛结果标签定义

定义用于1X2分类任务的标签枚举和转换函数。
严格遵循TDD设计，提供精确的比赛结果分类逻辑。

核心功能:
1. MatchOutcome枚举定义 (HOME_WIN, DRAW, AWAY_WIN)
2. 比分到标签的转换函数
3. 输入验证和异常处理
4. 与现有特征schema的兼容性

设计原则:
- 类型安全: 使用Enum确保标签一致性
- 健壮性: 处理各种输入异常情况
- 可扩展性: 支持未来添加新的标签类型
- 性能优化: 高效的转换逻辑
"""

from enum import Enum
from typing import Union, Tuple
import logging

logger = logging.getLogger(__name__)


class MatchOutcome(str, Enum):
    """
    比赛结果枚举

    定义标准的三分类比赛结果，用于1X2预测任务。
    继承自str确保JSON序列化兼容性。
    """

    HOME_WIN = "HOME_WIN"  # 主队获胜
    DRAW = "DRAW"  # 平局
    AWAY_WIN = "AWAY_WIN"  # 客队获胜

    @classmethod
    def get_all_outcomes(cls) -> list[str]:
        """获取所有可能的结果"""
        return [outcome.value for outcome in cls]

    def get_description(self) -> str:
        """获取结果描述"""
        descriptions = {
            MatchOutcome.HOME_WIN: "主队获胜",
            MatchOutcome.DRAW: "平局",
            MatchOutcome.AWAY_WIN: "客队获胜",
        }
        return descriptions[self]

    def is_win(self, team_side: str) -> bool:
        """
        判断指定方是否获胜

        Args:
            team_side: 球队方 ("home" 或 "away")

        Returns:
            bool: 是否获胜

        Raises:
            ValueError: 当team_side不是home或away时
        """
        if team_side.lower() == "home":
            return self == MatchOutcome.HOME_WIN
        elif team_side.lower() == "away":
            return self == MatchOutcome.AWAY_WIN
        else:
            raise ValueError(f"team_side必须是'home'或'away'，当前值: {team_side}")


def score_to_label(
    home_score: Union[int, float, str], away_score: Union[int, float, str]
) -> MatchOutcome:
    """
    将比分转换为比赛结果标签

    根据最终比分确定比赛结果，支持多种输入类型。
    包含严格的输入验证和异常处理。

    Args:
        home_score: 主队得分，支持int、float或str类型
        away_score: 客队得分，支持int、float或str类型

    Returns:
        MatchOutcome: 比赛结果标签

    Raises:
        ValueError: 当输入无法转换为有效数字时
        TypeError: 当输入类型不支持时

    Examples:
        >>> score_to_label(2, 1)
        <MatchOutcome.HOME_WIN: 'HOME_WIN'>
        >>> score_to_label(0, 0)
        <MatchOutcome.DRAW: 'DRAW'>
        >>> score_to_label(1, 3)
        <MatchOutcome.AWAY_WIN: 'AWAY_WIN'>
        >>> score_to_label("2", "1")  # 支持字符串输入
        <MatchOutcome.HOME_WIN: 'HOME_WIN'>
    """
    try:
        # 转换输入为整数（处理字符串和浮点数输入）
        if isinstance(home_score, str):
            home_score = (
                int(float(home_score)) if "." in home_score else int(home_score)
            )
        elif isinstance(home_score, float):
            home_score = int(home_score)

        if isinstance(away_score, str):
            away_score = (
                int(float(away_score)) if "." in away_score else int(away_score)
            )
        elif isinstance(away_score, float):
            away_score = int(away_score)

        # 验证分数非负
        if home_score < 0 or away_score < 0:
            raise ValueError(f"比分不能为负数: 主队{home_score}, 客队{away_score}")

        # 确定比赛结果
        if home_score > away_score:
            result = MatchOutcome.HOME_WIN
        elif home_score < away_score:
            result = MatchOutcome.AWAY_WIN
        else:
            result = MatchOutcome.DRAW

        return result

    except (ValueError, TypeError) as e:
        logger.error(f"比分转换失败: 主队={home_score}, 客队={away_score}, 错误={e}")
        raise  # 直接重新抛出原始异常，保持错误消息


def label_to_numeric(outcome: MatchOutcome) -> int:
    """
    将标签转换为数值

    用于机器学习模型的数值编码。

    Args:
        outcome: 比赛结果标签

    Returns:
        int: 数值编码 (0: AWAY_WIN, 1: DRAW, 2: HOME_WIN)

    Examples:
        >>> label_to_numeric(MatchOutcome.HOME_WIN)
        2
        >>> label_to_numeric(MatchOutcome.DRAW)
        1
        >>> label_to_numeric(MatchOutcome.AWAY_WIN)
        0
    """
    mapping = {MatchOutcome.AWAY_WIN: 0, MatchOutcome.DRAW: 1, MatchOutcome.HOME_WIN: 2}
    return mapping[outcome]


def numeric_to_label(numeric_label: int) -> MatchOutcome:
    """
    将数值转换为标签

    用于机器学习模型预测结果的解码。

    Args:
        numeric_label: 数值编码 (0: AWAY_WIN, 1: DRAW, 2: HOME_WIN)

    Returns:
        MatchOutcome: 比赛结果标签

    Raises:
        ValueError: 当数值标签无效时

    Examples:
        >>> numeric_to_label(2)
        <MatchOutcome.HOME_WIN: 'HOME_WIN'>
        >>> numeric_to_label(1)
        <MatchOutcome.DRAW: 'DRAW'>
        >>> numeric_to_label(0)
        <MatchOutcome.AWAY_WIN: 'AWAY_WIN'>
    """
    mapping = {0: MatchOutcome.AWAY_WIN, 1: MatchOutcome.DRAW, 2: MatchOutcome.HOME_WIN}

    if numeric_label not in mapping:
        raise ValueError(f"无效的数值标签: {numeric_label}，有效值: 0, 1, 2")

    return mapping[numeric_label]


def validate_scores(
    home_score: Union[int, float, str], away_score: Union[int, float, str]
) -> Tuple[int, int]:
    """
    验证并标准化比分输入

    Args:
        home_score: 主队得分
        away_score: 客队得分

    Returns:
        Tuple[int, int]: 标准化后的比分 (整数元组)

    Raises:
        ValueError: 当比分无效时
    """
    try:
        # 转换为整数
        home_int = (
            int(float(home_score)) if isinstance(home_score, str) else int(home_score)
        )
        away_int = (
            int(float(away_score)) if isinstance(away_score, str) else int(away_score)
        )

        # 验证非负
        if home_int < 0 or away_int < 0:
            raise ValueError(f"比分不能为负数: 主队={home_int}, 客队={away_int}")

        # 验证合理范围（防止输入错误）
        if home_int > 50 or away_int > 50:
            logger.warning(f"比分异常高: 主队={home_int}, 客队={away_int}")

        return home_int, away_int

    except (ValueError, TypeError) as e:
        raise ValueError(f"无效的比分输入: 主队={home_score}, 客队={away_score}") from e


def get_label_probabilities() -> dict[MatchOutcome, float]:
    """
    获取默认的标签先验概率

    Returns:
        dict[MatchOutcome, float]: 各结果的默认先验概率

    Note:
        这是基于足球比赛历史统计的近似值:
        - 主队获胜概率约 46%
        - 平局概率约 26%
        - 客队获胜概率约 28%
    """
    return {
        MatchOutcome.HOME_WIN: 0.46,
        MatchOutcome.DRAW: 0.26,
        MatchOutcome.AWAY_WIN: 0.28,
    }


# 便捷函数用于批量处理
def batch_scores_to_labels(
    score_pairs: list[Tuple[Union[int, float, str], Union[int, float, str]]],
) -> list[MatchOutcome]:
    """
    批量将比分对转换为标签

    Args:
        score_pairs: 比分对的列表 [(home_score, away_score), ...]

    Returns:
        list[MatchOutcome]: 标签列表

    Raises:
        ValueError: 当任何比分对无效时
    """
    results = []
    errors = []

    for i, (home, away) in enumerate(score_pairs):
        try:
            label = score_to_label(home, away)
            results.append(label)
        except ValueError as e:
            errors.append(f"索引{i}: {e}")

    if errors:
        raise ValueError(f"批量转换失败: {'; '.join(errors)}")

    return results


# 常用映射表
LABEL_DESCRIPTIONS = {
    MatchOutcome.HOME_WIN: "主队获胜",
    MatchOutcome.DRAW: "平局",
    MatchOutcome.AWAY_WIN: "客队获胜",
}

NUMERIC_LABELS = {
    MatchOutcome.HOME_WIN: 2,
    MatchOutcome.DRAW: 1,
    MatchOutcome.AWAY_WIN: 0,
}

REVERSE_NUMERIC_LABELS = {v: k for k, v in NUMERIC_LABELS.items()}


if __name__ == "__main__":
    # 模块测试

    test_cases = [
        (2, 1, MatchOutcome.HOME_WIN),
        (0, 0, MatchOutcome.DRAW),
        (1, 3, MatchOutcome.AWAY_WIN),
        ("3", "1", MatchOutcome.HOME_WIN),
        (2.0, 1.0, MatchOutcome.HOME_WIN),
        (0, 5, MatchOutcome.AWAY_WIN),
    ]

    for home, away, expected in test_cases:
        try:
            result = score_to_label(home, away)
            status = "✅" if result == expected else "❌"
        except Exception as e:
            status = f"❌ Error: {e}"
            pass

    for outcome in MatchOutcome:
        numeric = label_to_numeric(outcome)
        back_to_label = numeric_to_label(numeric)
        status = "✅" if back_to_label == outcome else "❌"

    batch_scores = [(2, 1), (0, 0), (1, 3)]
    try:
        batch_results = batch_scores_to_labels(batch_scores)
    except Exception as e:
        pass
