#!/usr/bin/env python3
"""
V19.4 市场价格验证器 (Market Price Verifier)
=================================================

实时对比"API即时价格"与"回测用平均价格"，防止市场识破策略漏洞。

核心功能:
1. 获取实时赔率 (来自当前市场)
2. 加载历史平均赔率 (用于回测)
3. 价格偏离度计算
4. 标记贬值比赛

作者: V19.4 风控团队
日期: 2025-12-23
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PriceCheckResult:
    """价格检查结果"""

    match_id: str
    home_team: str
    away_team: str
    prediction: str

    # 价格数据
    historical_odds: float  # 回测用平均价格
    live_odds: float  # 当前市场价格
    odds_diff_pct: float  # 价格偏离百分比

    # 判断结果
    is_deprecated: bool  # 是否贬值
    is_safe: bool  # 是否安全
    recommendation: str  # 建议

    timestamp: datetime


class MarketPriceVerifier:
    """
    市场价格验证器

    功能:
    1. 从数据库加载历史平均赔率
    2. 从API获取当前实时赔率
    3. 计算价格偏离度
    4. 标记贬值比赛
    """

    # 价格偏离阈值（超过此阈值则标记为贬值）
    PRICE_DEPRECATION_THRESHOLD = 0.10  # 10%

    def __init__(self, odds_data_path: str = None):
        """
        初始化价格验证器

        Args:
            odds_data_path: 历史赔率数据路径
        """
        if odds_data_path is None:
            self.odds_data_path = "/home/user/projects/FootballPrediction/data/real_odds_raw.csv"
        else:
            self.odds_data_path = odds_data_path

        # 加载历史赔率数据
        self.historical_odds = self._load_historical_odds()

        logger.info(f"价格验证器初始化完成，历史数据: {len(self.historical_odds)} 场")

    def _load_historical_odds(self) -> pd.DataFrame:
        """加载历史赔率数据"""
        path = Path(self.odds_data_path)
        if not path.exists():
            logger.warning(f"历史赔率数据文件不存在: {self.odds_data_path}")
            return pd.DataFrame()

        df = pd.read_csv(path)
        df["match_date"] = pd.to_datetime(df["match_date"]).dt.tz_localize(None)

        # 计算平均赔率（使用 Bet365 作为主要基准）
        df["avg_home_odds"] = df[["b365_home_odds", "ps_home_odds"]].mean(axis=1, skipna=True)
        df["avg_draw_odds"] = df[["b365_draw_odds", "ps_draw_odds"]].mean(axis=1, skipna=True)
        df["avg_away_odds"] = df[["b365_away_odds", "ps_away_odds"]].mean(axis=1, skipna=True)

        return df

    def get_historical_odds(self, home_team: str, away_team: str, prediction: str) -> float | None:
        """
        获取历史平均赔率

        Args:
            home_team: 主队
            away_team: 客队
            prediction: 预测结果 (H/D/A)

        Returns:
            float: 历史平均赔率
        """
        if self.historical_odds.empty:
            return None

        # 查找匹配的比赛（考虑球队名称标准化）
        # 简化处理：直接匹配
        matches = self.historical_odds[
            (self.historical_odds["home_team"] == home_team) & (self.historical_odds["away_team"] == away_team)
        ]

        if len(matches) == 0:
            logger.debug(f"未找到历史赔率: {home_team} vs {away_team}")
            return None

        # 使用最新的赔率
        latest = matches.iloc[-1]

        if prediction == "H":
            return latest["avg_home_odds"]
        elif prediction == "D":
            return latest["avg_draw_odds"]
        else:  # 'A'
            return latest["avg_away_odds"]

    def fetch_live_odds(self, home_team: str, away_team: str, prediction: str) -> float | None:
        """
        获取实时市场赔率

        Args:
            home_team: 主队
            away_team: 客队
            prediction: 预测结果

        Returns:
            float: 实时赔率
        """
        # 预留接口：可集成 oddsportal、bet365 等API
        # 当前使用数据库查询最新赔率

        logger.debug(f"获取实时赔率: {home_team} vs {away_team}, 预测: {prediction}")

        # 从数据库查询最新赔率（使用统一配置）
        import psycopg2
        from psycopg2.extras import RealDictCursor

        from src.config_unified import get_settings

        try:
            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 查询最近的赔率数据
            query = """
            SELECT
                home_team, away_team,
                b365_home_odds, b365_draw_odds, b365_away_odds,
                collection_date
            FROM (
                SELECT
                    home_team, away_team,
                    b365_home_odds, b365_draw_odds, b365_away_odds,
                    collection_date,
                    ROW_NUMBER() OVER (PARTITION BY home_team, away_team ORDER BY collection_date DESC) as rn
                FROM odds_history
                WHERE home_team = %s AND away_team = %s
            ) ranked
            WHERE rn = 1
            """

            cursor.execute(query, (home_team, away_team))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                if prediction == "H":
                    return float(result["b365_home_odds"]) if result["b365_home_odds"] else None
                elif prediction == "D":
                    return float(result["b365_draw_odds"]) if result["b365_draw_odds"] else None
                else:
                    return float(result["b365_away_odds"]) if result["b365_away_odds"] else None

        except Exception as e:
            logger.debug(f"获取实时赔率失败: {e}")

        return None

    def verify_price(
        self, match_id: str, home_team: str, away_team: str, prediction: str, historical_odds: float = None
    ) -> PriceCheckResult:
        """
        验证价格是否贬值

        Args:
            match_id: 比赛ID
            home_team: 主队
            away_team: 客队
            prediction: 预测结果
            historical_odds: 历史赔率（可选，如果不提供则自动查询）

        Returns:
            PriceCheckResult: 价格检查结果
        """
        # 获取历史赔率
        if historical_odds is None:
            historical_odds = self.get_historical_odds(home_team, away_team, prediction)

        if historical_odds is None:
            # 没有历史数据，无法比较
            return PriceCheckResult(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                prediction=prediction,
                historical_odds=0.0,
                live_odds=0.0,
                odds_diff_pct=0.0,
                is_deprecated=False,
                is_safe=True,
                recommendation="NO_HISTORICAL_DATA",
                timestamp=datetime.now(),
            )

        # 获取实时赔率
        live_odds = self.fetch_live_odds(home_team, away_team, prediction)

        if live_odds is None:
            # 无法获取实时价格，使用历史价格作为估计
            live_odds = historical_odds
            odds_diff_pct = 0.0
            recommendation = "USE_HISTORICAL"
        else:
            # 计算偏离度
            odds_diff_pct = (live_odds - historical_odds) / historical_odds

        # 判断是否贬值
        # 注意：如果赔率下降（live_odds < historical_odds），说明市场赔率变差，这是贬值
        is_deprecated = odds_diff_pct < -self.PRICE_DEPRECATION_THRESHOLD
        is_safe = not is_deprecated

        if is_deprecated:
            recommendation = "[Price_Deprecated] 建议不执行"
        elif odds_diff_pct > 0.05:
            recommendation = "[Price_Improved] 可考虑增加下注"
        else:
            recommendation = "[Price_Normal] 正常执行"

        result = PriceCheckResult(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            prediction=prediction,
            historical_odds=historical_odds,
            live_odds=live_odds,
            odds_diff_pct=odds_diff_pct,
            is_deprecated=is_deprecated,
            is_safe=is_safe,
            recommendation=recommendation,
            timestamp=datetime.now(),
        )

        # 记录日志
        if is_deprecated:
            logger.warning(
                f"价格贬值警告: {home_team} vs {away_team} "
                f"预测:{prediction} 历史:{historical_odds:.2f} 当前:{live_odds:.2f} "
                f"偏离:{odds_diff_pct:.2%}"
            )

        return result

    def batch_verify(self, predictions: list[dict]) -> list[PriceCheckResult]:
        """
        批量验证价格

        Args:
            predictions: 预测列表，每个元素包含 match_id, home_team, away_team, prediction, odds

        Returns:
            List[PriceCheckResult]: 价格检查结果列表
        """
        results = []

        for pred in predictions:
            result = self.verify_price(
                match_id=pred.get("match_id", ""),
                home_team=pred.get("home_team", ""),
                away_team=pred.get("away_team", ""),
                prediction=pred.get("prediction", ""),
                historical_odds=pred.get("odds"),
            )
            results.append(result)

        return results

    def generate_price_report(self, results: list[PriceCheckResult]) -> pd.DataFrame:
        """
        生成价格验证报告

        Args:
            results: 价格检查结果列表

        Returns:
            pd.DataFrame: 报告数据框
        """
        report_data = []

        for r in results:
            report_data.append(
                {
                    "match_id": r.match_id,
                    "home_team": r.home_team,
                    "away_team": r.away_team,
                    "prediction": r.prediction,
                    "historical_odds": r.historical_odds,
                    "live_odds": r.live_odds,
                    "odds_diff_pct": r.odds_diff_pct,
                    "is_deprecated": r.is_deprecated,
                    "recommendation": r.recommendation,
                    "timestamp": r.timestamp,
                }
            )

        df = pd.DataFrame(report_data)

        # 保存报告
        report_dir = Path("/home/user/projects/FootballPrediction/data/risk")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"price_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(report_file, index=False)
        logger.info(f"价格验证报告已保存: {report_file}")

        return df


# ============================================
# 便捷函数
# ============================================


def verify_prediction_price(
    match_id: str, home_team: str, away_team: str, prediction: str, historical_odds: float = None
) -> PriceCheckResult:
    """
    验证单个预测的价格

    Args:
        match_id: 比赛ID
        home_team: 主队
        away_team: 客队
        prediction: 预测结果
        historical_odds: 历史赔率（可选）

    Returns:
        PriceCheckResult: 价格检查结果
    """
    verifier = MarketPriceVerifier()
    return verifier.verify_price(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        prediction=prediction,
        historical_odds=historical_odds,
    )


# ============================================
# 单元测试
# ============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 70)
    print("V19.4 市场价格验证器测试")
    print("=" * 70)

    verifier = MarketPriceVerifier()

    # 测试价格验证
    result = verifier.verify_price(
        match_id="test_001", home_team="Manchester City", away_team="Liverpool", prediction="H", historical_odds=1.80
    )

    print("\n价格验证结果:")
    print(f"  比赛: {result.home_team} vs {result.away_team}")
    print(f"  预测: {result.prediction}")
    print(f"  历史赔率: {result.historical_odds:.2f}")
    print(f"  实时赔率: {result.live_odds:.2f}")
    print(f"  偏离度: {result.odds_diff_pct:.2%}")
    print(f"  是否贬值: {result.is_deprecated}")
    print(f"  建议: {result.recommendation}")

    print("\n" + "=" * 70)
