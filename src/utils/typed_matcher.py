"""
V171-Standard-03 类型注解示例
=============================

展示符合 Google Python Style Guide 的代码规范：
- 完整的类型注解 (Type Hints)
- 清晰的文档字符串 (Docstrings)
- 异步函数的 try-except 处理
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from psycopg2.extras import RealDictCursor

# ============================================================================
# 数据类定义 (带类型注解)
# ============================================================================


@dataclass
class MatchPrediction:
    """比赛预测结果数据类。

    Attributes:
        match_id: 比赛唯一标识符。
        home_team: 主队名称。
        away_team: 客队名称。
        predicted_result: 预测结果 ('home', 'draw', 'away')。
        confidence: 预测置信度 (0.0 - 1.0)。
        model_version: 模型版本号。
    """

    match_id: str
    home_team: str
    away_team: str
    predicted_result: str
    confidence: float
    model_version: str
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含所有属性的字典。
        """
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "predicted_result": self.predicted_result,
            "confidence": self.confidence,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class FuzzyMatchResult:
    """模糊匹配结果。

    Attributes:
        home_team: 主队名称 (标准化后)。
        away_team: 客队名称 (标准化后)。
        url_hash: 8 字符的 URL 哈希值。
        confidence: 匹配置信度 (0.0 - 1.0)。
    """

    home_team: str
    away_team: str
    url_hash: str
    confidence: float


# ============================================================================
# 核心函数 (带完整类型注解)
# ============================================================================


def normalize_team_name(name: str) -> str:
    """标准化队名。

    将队名转换为统一的小写格式，便于模糊匹配。

    Args:
        name: 原始队名。

    Returns:
        标准化后的队名 (小写，去除首尾空格)。

    Example:
        >>> normalize_team_name("Manchester United")
        'manchester united'
        >>> normalize_team_name("  Liverpool FC  ")
        'liverpool fc'
    """
    return name.lower().strip()


def calculate_league_distance(
    league_a: str,
    league_b: str,
    *,
    threshold: float = 0.7,
) -> float:
    """计算两个联赛名称的相似度。

    使用 Levenshtein 距离计算字符串相似度。

    Args:
        league_a: 第一个联赛名称。
        league_b: 第二个联赛名称。
        threshold: 相似度阈值，低于此值返回 0.0。

    Returns:
        相似度值 (0.0 - 1.0)，低于阈值时返回 0.0。

    Raises:
        ValueError: 当任一联赛名称为空时。
    """
    if not league_a or not league_b:
        raise ValueError("联赛名称不能为空")

    from rapidfuzz import fuzz

    score = fuzz.WRatio(league_a.lower(), league_b.lower()) / 100.0

    return score if score >= threshold else 0.0


async def fetch_match_prediction(
    match_id: str,
    *,
    timeout_seconds: int = 30,
) -> Optional[MatchPrediction]:
    """异步获取比赛预测结果。

    从数据库或预测服务获取比赛的预测数据。

    Args:
        match_id: 比赛唯一标识符。
        timeout_seconds: 请求超时时间 (秒)。

    Returns:
        预测结果，如果未找到或超时则返回 None。

    Example:
        >>> prediction = await fetch_match_prediction("EPL_20260228_LIV_WHU")
        >>> if prediction:
        ...     print(f"预测: {prediction.predicted_result}")
    """
    import asyncio

    try:
        # 模拟异步数据库查询
        await asyncio.sleep(0.1)

        # 实际实现会查询数据库
        return MatchPrediction(
            match_id=match_id,
            home_team="Liverpool",
            away_team="West Ham",
            predicted_result="home",
            confidence=0.68,
            model_version="V171.001",
            created_at=datetime.now(),
        )

    except asyncio.TimeoutError:
        return None
    except Exception as e:
        print(f"获取预测失败: {e}")
        return None


def fuzzy_match_teams(
    fotmob_home: str,
    fotmob_away: str,
    oddsportal_home: str,
    oddsportal_away: str,
    *,
    min_threshold: float = 0.65,
) -> FuzzyMatchResult | None:
    """模糊匹配 FotMob 和 OddsPortal 的队名。

    使用 RapidFuzz 计算队名相似度，判断是否为同一场比赛。

    Args:
        fotmob_home: FotMob 主队名。
        fotmob_away: FotMob 客队名。
        oddsportal_home: OddsPortal 主队名。
        oddsportal_away: OddsPortal 客队名。
        min_threshold: 最低相似度阈值。

    Returns:
        匹配结果，如果相似度低于阈值则返回 None。

    Example:
        >>> result = fuzzy_match_teams(
        ...     "Manchester United",
        ...     "Chelsea",
        ...     "manchester-united",
        ...     "chelsea",
        ... )
        >>> if result:
        ...     print(f"置信度: {result.confidence:.2%}")
    """
    from rapidfuzz import fuzz

    # 标准化队名
    fotmob_home_norm = normalize_team_name(fotmob_home)
    fotmob_away_norm = normalize_team_name(fotmob_away)
    oddsportal_home_norm = normalize_team_name(oddsportal_home)
    oddsportal_away_norm = normalize_team_name(oddsportal_away)

    # 计算相似度
    home_score = fuzz.WRatio(fotmob_home_norm, oddsportal_home_norm) / 100.0
    away_score = fuzz.WRatio(fotmob_away_norm, oddsportal_away_norm) / 100.0

    # 平均置信度
    avg_confidence = (home_score + away_score) / 2.0

    if avg_confidence < min_threshold:
        return None

    return FuzzyMatchResult(
        home_team=fotmob_home_norm,
        away_team=fotmob_away_norm,
        url_hash="",  # 由调用方填充
        confidence=avg_confidence,
    )


# ============================================================================
# 数据库操作 (带类型注解)
# ============================================================================


class PredictionRepository:
    """预测数据仓库。

    提供预测数据的 CRUD 操作。

    Attributes:
        connection: 数据库连接对象。
    """

    def __init__(self, connection: Any) -> None:
        """初始化仓库。

        Args:
            connection: psycopg2 数据库连接。
        """
        self._connection = connection

    def get_by_match_id(self, match_id: str) -> Optional[MatchPrediction]:
        """根据比赛 ID 获取预测。

        Args:
            match_id: 比赛唯一标识符。

        Returns:
            预测结果，如果不存在则返回 None。
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT match_id, home_team, away_team, predicted_result,
                       final_confidence, model_version, prediction_date
                FROM predictions
                WHERE match_id = %s
                """,
                (match_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return MatchPrediction(
                match_id=row[0],
                home_team=row[1],
                away_team=row[2],
                predicted_result=row[3],
                confidence=float(row[4]),
                model_version=row[5],
                created_at=row[6],
            )

    def save(self, prediction: MatchPrediction) -> bool:
        """保存预测结果。

        Args:
            prediction: 预测数据。

        Returns:
            保存成功返回 True，否则返回 False。
        """
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO predictions (
                        match_id, predicted_result, final_confidence,
                        model_version, prediction_date
                    ) VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (match_id, model_version) DO UPDATE SET
                        predicted_result = EXCLUDED.predicted_result,
                        final_confidence = EXCLUDED.final_confidence,
                        prediction_date = NOW()
                    """,
                    (
                        prediction.match_id,
                        prediction.predicted_result,
                        prediction.confidence,
                        prediction.model_version,
                    ),
                )
            self._connection.commit()
            return True

        except Exception as e:
            print(f"保存预测失败: {e}")
            self._connection.rollback()
            return False


# ============================================================================
# 主程序入口
# ============================================================================


async def main() -> int:
    """主程序入口。

    Returns:
        退出码 (0 表示成功)。
    """
    print("V171-Standard-03 类型注解示例")

    # 演示模糊匹配
    result = fuzzy_match_teams(
        fotmob_home="Manchester United",
        fotmob_away="Chelsea",
        oddsportal_home="manchester-united",
        oddsportal_away="chelsea",
    )

    if result:
        print(f"匹配成功: 置信度 {result.confidence:.2%}")
    else:
        print("匹配失败")

    # 演示异步获取预测
    prediction = await fetch_match_prediction("EPL_20260228_LIV_WHU")

    if prediction:
        print(f"预测: {prediction.home_team} vs {prediction.away_team}")
        print(f"结果: {prediction.predicted_result} ({prediction.confidence:.0%})")

    return 0


if __name__ == "__main__":
    import asyncio

    exit(asyncio.run(main()))
