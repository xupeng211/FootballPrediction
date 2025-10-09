"""
数据处理工具函数

提供计算比赛结果等通用功能
"""


def calculate_match_result(row) -> str:
    """
    计算比赛结果

    Args:
        row: 包含比分的行数据

    Returns:
        比赛结果 ("home", "away", "draw")
    """
    home_score = row["home_score"]
    away_score = row["away_score"]

    if (
        home_score is not None
        and away_score is not None
        and home_score > away_score
    ):
        return "home"
    elif home_score < away_score:
        return "away"
    else:
        return "draw"