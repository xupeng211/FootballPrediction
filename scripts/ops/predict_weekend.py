#!/usr/bin/env python3
"""
V3.0-PRO 交钥匙预测系统 - 工业级版本
=====================================

满血版预测引擎：Elo + 身价 + 伤病 + 赔率

V3.0-PRO 工业级重构:
- 使用 logging 模块替代 print
- EV 计算封装为独立工具类
- 完整的 Docstrings 和类型注解
- 结构化日志输出

特征来源:
- team_elo_ratings: 球队最新 Elo 评分
- l3_features.golden_features: 身价、伤病等基本面（身价单位：欧元）
- l2_match_data: 开盘/收盘赔率

用法:
    docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py
    docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --league "La Liga"
    docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --save
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import psycopg2

# ============================================================================
# 常量配置
# ============================================================================

# Elo 常量
DEFAULT_ELO_RATING = 1500.0
HOME_ADVANTAGE_ELO = 50
ELO_SCALE_FACTOR = 400

# 身价权重 (每 1 亿欧元 = 2% 概率调整)
MARKET_VALUE_WEIGHT = 0.02
MARKET_VALUE_SCALE = 1e8  # 1 亿欧元

# 伤病权重 (每 1 人 = 0.5% 概率调整)
INJURY_WEIGHT = 0.005

# EV 阈值
EV_HIGH_VALUE_THRESHOLD = 0.05
EV_STRONG_RECOMMEND_THRESHOLD = 0.10
EV_EDGE_THRESHOLD = 0.0

# 平局概率
DRAW_BASE_PROBABILITY = 0.28
DRAW_ADJUST_MAX = 0.08

# ============================================================================
# 日志配置
# ============================================================================

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    配置结构化日志系统。

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARN, ERROR)

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger("Predictor")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除现有处理器
    logger.handlers.clear()

    # 控制台处理器 - 结构化 JSON 格式
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # JSON 格式化器
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "component": record.name,
                "message": record.getMessage(),
            }
            if hasattr(record, 'context') and record.context:
                log_entry["context"] = record.context
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_entry)

    console_handler.setFormatter(JsonFormatter())
    logger.addHandler(console_handler)

    return logger


# ============================================================================
# 数据类定义
# ============================================================================

class BetOutcome(Enum):
    """投注结果类型枚举"""
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


@dataclass
class ProbabilitySet:
    """概率集合"""
    home: float
    draw: float
    away: float

    def __post_init__(self):
        """验证概率和为 1"""
        total = self.home + self.draw + self.away
        if abs(total - 1.0) > 0.01:
            # 归一化
            self.home /= total
            self.draw /= total
            self.away /= total

    def get_confidence(self, outcome: BetOutcome) -> float:
        """获取指定结果的置信度"""
        return getattr(self, outcome.value)


@dataclass
class EVResult:
    """期望值结果"""
    home: float
    draw: float
    away: float

    def best_outcome(self) -> Tuple[BetOutcome, float]:
        """获取最佳投注结果"""
        outcomes = [
            (BetOutcome.HOME, self.home),
            (BetOutcome.DRAW, self.draw),
            (BetOutcome.AWAY, self.away)
        ]
        return max(outcomes, key=lambda x: x[1])

    def is_positive(self, outcome: BetOutcome) -> bool:
        """判断指定结果是否有正 EV"""
        return getattr(self, outcome.value) > 0


@dataclass
class Odds:
    """赔率数据"""
    home: Optional[float] = None
    draw: Optional[float] = None
    away: Optional[float] = None

    def is_valid(self) -> bool:
        """检查赔率是否有效"""
        return all([
            self.home is not None and self.home > 1.0,
            self.draw is not None and self.draw > 1.0,
            self.away is not None and self.away > 1.0
        ])


@dataclass
class MatchPrediction:
    """比赛预测结果"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    match_date: datetime

    # Elo 数据
    home_elo: float
    away_elo: float
    elo_diff: float

    # 特征数据
    mv_gap: float  # 身价差（欧元）
    injury_gap: int  # 伤病差

    # 预测结果
    probs: ProbabilitySet
    prediction: BetOutcome
    confidence: float
    ev: EVResult
    odds: Optional[Odds]

    # 元数据
    computed_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# EV 计算工具类
# ============================================================================

class EVCalculator:
    """
    期望值计算器

    封装 EV 计算逻辑，确保数学正确性。

    核心公式:
        EV = P × Odds - 1

    其中:
        - P: 模型预测概率
        - Odds: 市场赔率
        - EV > 0: 正期望值，建议投注
        - EV < 0: 负期望值，不推荐投注

    Examples:
        >>> calc = EVCalculator()
        >>> probs = ProbabilitySet(home=0.647, draw=0.20, away=0.153)
        >>> odds = Odds(home=1.47, draw=4.0, away=6.0)
        >>> ev = calc.calculate(probs, odds)
        >>> ev.home
        -0.04891  # 0.647 × 1.47 - 1 = -0.0489
    """

    def __init__(
        self,
        high_value_threshold: float = EV_HIGH_VALUE_THRESHOLD,
        strong_recommend_threshold: float = EV_STRONG_RECOMMEND_THRESHOLD
    ):
        """
        初始化 EV 计算器。

        Args:
            high_value_threshold: 高价值 EV 阈值（默认 5%）
            strong_recommend_threshold: 强烈推荐 EV 阈值（默认 10%）
        """
        self.high_value_threshold = high_value_threshold
        self.strong_recommend_threshold = strong_recommend_threshold

    def calculate(self, probs: ProbabilitySet, odds: Optional[Odds] = None) -> EVResult:
        """
        计算期望值。

        有真实赔率时: EV = P × Odds - 1
        无赔率时: 使用保守估算

        Args:
            probs: 模型预测概率
            odds: 市场赔率（可选）

        Returns:
            EVResult: 三个结果的期望值
        """
        if odds and odds.is_valid():
            return self._calculate_with_odds(probs, odds)
        else:
            return self._calculate_theoretical(probs)

    def _calculate_with_odds(self, probs: ProbabilitySet, odds: Odds) -> EVResult:
        """
        使用真实赔率计算 EV。

        公式: EV = P × Odds - 1

        Args:
            probs: 模型预测概率
            odds: 市场赔率

        Returns:
            EVResult: 期望值结果
        """
        return EVResult(
            home=probs.home * odds.home - 1,
            draw=probs.draw * odds.draw - 1,
            away=probs.away * odds.away - 1
        )

    def _calculate_theoretical(self, probs: ProbabilitySet) -> EVResult:
        """
        无赔率时的保守 EV 估算。

        基于模型置信度与"公平市场赔率"的差距估算。
        假设市场赔率是公平的（含 5% 抽水）。

        Args:
            probs: 模型预测概率

        Returns:
            EVResult: 理论期望值
        """
        def calc_single_ev(p: float) -> float:
            """
            计算单个结果的 EV。

            条件分支从高到低排序，确保正确匹配。
            """
            # 市场隐含概率（含 5% vig）
            market_implied_prob = p * 1.05
            theoretical_ev = p - market_implied_prob

            # 从高到低匹配（V3.0 修复）
            if p > 0.70:
                # 极高置信度
                return min(0.10, theoretical_ev + 0.05)
            elif p > 0.60:
                # 高置信度
                return min(0.05, theoretical_ev + 0.02)
            elif p > 0.50:
                # 中高置信度
                return min(0.03, theoretical_ev)
            elif p > 0.40:
                # 中等置信度
                return max(-0.05, theoretical_ev - 0.02)
            else:
                # 低置信度
                return max(-0.10, theoretical_ev - 0.05)

        return EVResult(
            home=calc_single_ev(probs.home),
            draw=calc_single_ev(probs.draw),
            away=calc_single_ev(probs.away)
        )

    def is_high_value(self, ev: float) -> bool:
        """判断是否为高价值 EV"""
        return ev > self.high_value_threshold

    def is_strong_recommend(self, ev: float) -> bool:
        """判断是否为强烈推荐"""
        return ev > self.strong_recommend_threshold


# ============================================================================
# 预测器类
# ============================================================================

class WeekendPredictor:
    """
    V3.0-PRO 交钥匙预测器

    职责：
    1. 从数据库获取比赛数据
    2. 计算 Elo 基础概率
    3. 应用身价和伤病调整
    4. 计算期望值并排序
    5. 输出预测报告
    """

    def __init__(self, log_level: str = "INFO"):
        """
        初始化预测器。

        Args:
            log_level: 日志级别
        """
        self.conn = None
        self.elo_cache: Dict[str, float] = {}
        self.ev_calculator = EVCalculator()
        self.logger = setup_logging(log_level)

    def init(self) -> None:
        """初始化数据库连接和缓存"""
        self.conn = self._get_db_connection()
        self._load_elo_ratings()
        self.logger.info(
            "预测器初始化完成",
            extra={"context": {"elo_teams": len(self.elo_cache)}}
        )

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("数据库连接已关闭")

    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'db'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'football_db'),
            user=os.getenv('DB_USER', 'football_user'),
            password=os.getenv('DB_PASSWORD', '')
        )

    def _load_elo_ratings(self) -> None:
        """加载所有球队 Elo 评分到缓存"""
        cur = self.conn.cursor()
        cur.execute("SELECT team_name, elo_rating FROM team_elo_ratings")
        for row in cur.fetchall():
            self.elo_cache[row[0]] = float(row[1])

    def _get_elo(self, team_name: str) -> float:
        """获取球队 Elo，默认 1500"""
        return self.elo_cache.get(team_name, DEFAULT_ELO_RATING)

    def _calculate_elo_probabilities(
        self,
        home_elo: float,
        away_elo: float
    ) -> ProbabilitySet:
        """
        计算 Elo 期望概率。

        公式: E_home = 1 / (1 + 10^((away_elo - home_elo - home_advantage) / 400))

        Args:
            home_elo: 主队 Elo
            away_elo: 客队 Elo

        Returns:
            ProbabilitySet: 三个结果的概率
        """
        # 主场优势加成
        effective_home_elo = home_elo + HOME_ADVANTAGE_ELO

        # 标准 Elo 期望公式
        home_expected = 1 / (1 + 10 ** ((away_elo - effective_home_elo) / ELO_SCALE_FACTOR))

        # 平局概率（根据实力差距调整）
        elo_diff = abs(home_elo - away_elo)
        draw_prob = DRAW_BASE_PROBABILITY - min(DRAW_ADJUST_MAX, elo_diff / 2000)

        # 剩余概率分配
        remaining = 1 - draw_prob
        away_prob = remaining * (1 - home_expected)
        home_prob = remaining * home_expected

        return ProbabilitySet(home=home_prob, draw=draw_prob, away=away_prob)

    def _adjust_for_market_value(
        self,
        probs: ProbabilitySet,
        mv_gap: float
    ) -> ProbabilitySet:
        """
        根据身价差距调整概率。

        每 1 亿欧元差距 = 2% 概率调整

        Args:
            probs: 基础概率
            mv_gap: 身价差（欧元），正值=主队身价更高

        Returns:
            ProbabilitySet: 调整后的概率
        """
        mv_effect = (mv_gap / MARKET_VALUE_SCALE) * MARKET_VALUE_WEIGHT

        adjusted_home = probs.home + mv_effect
        adjusted_away = probs.away - mv_effect

        # 归一化
        total = adjusted_home + probs.draw + adjusted_away

        return ProbabilitySet(
            home=max(0.05, min(0.85, adjusted_home / total)),
            draw=max(0.10, min(0.40, probs.draw / total)),
            away=max(0.05, min(0.85, adjusted_away / total))
        )

    def _adjust_for_injury(
        self,
        probs: ProbabilitySet,
        injury_gap: int
    ) -> ProbabilitySet:
        """
        根据伤病差距调整概率。

        injury_gap = 主队伤病 - 客队伤病
        正值 = 主队伤病更多，降低主胜概率

        Args:
            probs: 基础概率
            injury_gap: 伤病差

        Returns:
            ProbabilitySet: 调整后的概率
        """
        injury_effect = injury_gap * INJURY_WEIGHT

        adjusted_home = probs.home - injury_effect
        adjusted_away = probs.away + injury_effect

        total = adjusted_home + probs.draw + adjusted_away

        return ProbabilitySet(
            home=max(0.05, min(0.85, adjusted_home / total)),
            draw=probs.draw,
            away=max(0.05, min(0.85, adjusted_away / total))
        )

    def fetch_upcoming_matches(
        self,
        league: Optional[str] = None,
        days: int = 4
    ) -> List[tuple]:
        """获取未来 N 天的比赛"""
        cur = self.conn.cursor()

        if league:
            query = """
                SELECT match_id, home_team, away_team, league_name, match_date, season
                FROM matches
                WHERE match_date >= NOW()
                  AND match_date < NOW() + INTERVAL '%s days'
                  AND league_name = %s
                  AND season = '2024/2025'
                ORDER BY match_date
            """
            cur.execute(query, (days, league))
        else:
            query = """
                SELECT match_id, home_team, away_team, league_name, match_date, season
                FROM matches
                WHERE match_date >= NOW()
                  AND match_date < NOW() + INTERVAL '%s days'
                  AND season = '2024/2025'
                ORDER BY match_date
            """
            cur.execute(query, (days,))

        return cur.fetchall()

    def fetch_l3_features(self, match_id: str) -> Optional[Dict]:
        """获取 L3 特征"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT golden_features, tactical_features
            FROM l3_features
            WHERE match_id = %s
        """, (match_id,))

        row = cur.fetchone()
        if not row:
            return None

        return {
            'golden': row[0] or {},
            'tactical': row[1] or {}
        }

    def fetch_odds(self, match_id: str) -> Optional[Odds]:
        """获取赔率数据"""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT raw_data
                FROM raw_match_data
                WHERE match_id = %s
            """, (match_id,))

            row = cur.fetchone()
            if not row or not row[0]:
                return None

            raw_data = row[0]
            odds_data = raw_data.get('odds', {})
            if not odds_data:
                return None

            odds_1x2 = odds_data.get('1x2', {})
            closing = odds_1x2.get('closing', {})

            if closing:
                return Odds(
                    home=closing.get('home', closing.get('1')),
                    draw=closing.get('draw', closing.get('X')),
                    away=closing.get('away', closing.get('2'))
                )

            return None
        except Exception:
            return None

    def predict_match(self, match: tuple) -> MatchPrediction:
        """
        预测单场比赛。

        Args:
            match: 比赛数据元组

        Returns:
            MatchPrediction: 预测结果
        """
        match_id, home_team, away_team, league_name, match_date, season = match

        # 1. 获取 Elo
        home_elo = self._get_elo(home_team)
        away_elo = self._get_elo(away_team)

        # 2. 计算 Elo 基础概率
        probs = self._calculate_elo_probabilities(home_elo, away_elo)

        # 3. 获取 L3 特征并调整
        l3 = self.fetch_l3_features(match_id)
        mv_gap = 0.0
        injury_gap = 0

        if l3:
            golden = l3.get('golden', {})
            mv_gap = float(golden.get('market_value_gap', 0) or 0)
            injury_gap = int(golden.get('injury_count_gap', 0) or 0)

            probs = self._adjust_for_market_value(probs, mv_gap)
            probs = self._adjust_for_injury(probs, injury_gap)

        # 4. 获取赔率
        odds = self.fetch_odds(match_id)

        # 5. 计算 EV
        ev = self.ev_calculator.calculate(probs, odds)

        # 6. 确定预测结果
        prediction = BetOutcome(max(probs.__dict__, key=probs.__dict__.get))
        confidence = probs.get_confidence(prediction)

        return MatchPrediction(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            league=league_name,
            match_date=match_date,
            home_elo=home_elo,
            away_elo=away_elo,
            elo_diff=home_elo - away_elo,
            mv_gap=mv_gap,
            injury_gap=injury_gap,
            probs=probs,
            prediction=prediction,
            confidence=confidence,
            ev=ev,
            odds=odds
        )

    def save_prediction(self, pred: MatchPrediction) -> None:
        """保存预测到数据库"""
        cur = self.conn.cursor()

        best_ev = pred.ev.best_outcome()[1]

        if best_ev == pred.ev.home:
            recommended = f"主胜 ({pred.home_team})"
        elif best_ev == pred.ev.draw:
            recommended = "平局"
        else:
            recommended = f"客胜 ({pred.away_team})"

        result_map = {
            BetOutcome.HOME: 'Home',
            BetOutcome.DRAW: 'Draw',
            BetOutcome.AWAY: 'Away'
        }

        cur.execute("""
            INSERT INTO predictions (
                match_id, model_version, predicted_result,
                confidence_home, confidence_draw, confidence_away,
                final_confidence, edge, recommended_bet, prediction_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (match_id, model_version) DO UPDATE SET
                predicted_result = EXCLUDED.predicted_result,
                confidence_home = EXCLUDED.confidence_home,
                confidence_draw = EXCLUDED.confidence_draw,
                confidence_away = EXCLUDED.confidence_away,
                final_confidence = EXCLUDED.final_confidence,
                edge = EXCLUDED.edge,
                recommended_bet = EXCLUDED.recommended_bet,
                prediction_date = NOW()
        """, (
            pred.match_id,
            'V3.0-PRO',
            result_map[pred.prediction],
            pred.probs.home,
            pred.probs.draw,
            pred.probs.away,
            pred.confidence,
            best_ev,
            recommended
        ))

        self.conn.commit()

    def run(
        self,
        league: Optional[str] = None,
        save: bool = False,
        days: int = 4
    ) -> List[MatchPrediction]:
        """
        执行预测。

        Args:
            league: 指定联赛
            save: 是否保存到数据库
            days: 预测天数

        Returns:
            预测结果列表
        """
        self.logger.info(
            "开始预测",
            extra={"context": {"league": league, "days": days, "save": save}}
        )

        # 获取比赛
        matches = self.fetch_upcoming_matches(league, days)
        self.logger.info(
            "获取比赛完成",
            extra={"context": {"count": len(matches)}}
        )

        if not matches:
            self.logger.warn("无比赛数据")
            return []

        # 执行预测
        predictions = []
        for match in matches:
            pred = self.predict_match(match)
            predictions.append(pred)

            if save:
                self.save_prediction(pred)

        # 按 EV 排序
        predictions.sort(key=lambda x: x.ev.best_outcome()[1], reverse=True)

        # 打印报告
        self._print_report(predictions)

        return predictions

    def _print_report(self, predictions: List[MatchPrediction]) -> None:
        """打印预测报告"""
        print("\n" + "=" * 80)
        print("   V3.0-PRO 预测报告 - 按 EV (期望值) 排序")
        print("   ⚠️ EV = P × Odds - 1 (负值表示不推荐投注)")
        print("=" * 80)

        # 高价值投注
        high_value = [
            p for p in predictions
            if p.ev.best_outcome()[1] > self.ev_calculator.high_value_threshold
        ]

        if high_value:
            print(f"\n   高价值投注 (EV > {self.ev_calculator.high_value_threshold:.0%}):")
            print("   " + "-" * 76)

            for i, p in enumerate(high_value, 1):
                best_outcome, best_ev = p.ev.best_outcome()

                if best_outcome == BetOutcome.HOME:
                    outcome_str = f"主胜 ({p.home_team})"
                    odds_val = p.odds.home if p.odds else self._simulate_odds(p.probs).home
                elif best_outcome == BetOutcome.DRAW:
                    outcome_str = "平局"
                    odds_val = p.odds.draw if p.odds else self._simulate_odds(p.probs).draw
                else:
                    outcome_str = f"客胜 ({p.away_team})"
                    odds_val = p.odds.away if p.odds else self._simulate_odds(p.probs).away

                print(f"\n   [{i}] {p.home_team} vs {p.away_team}")
                print(f"       联赛: {p.league} | 时间: {p.match_date.strftime('%m/%d %H:%M')}")
                print(f"       Elo: {p.home_elo:.0f} vs {p.away_elo:.0f} (差 {p.elo_diff:+.0f})")
                print(f"       身价差: {self._format_value(p.mv_gap)} 欧元 | 伤病差: {p.injury_gap:+d} 人")
                print(f"       概率: 主 {p.probs.home:.1%} | 平 {p.probs.draw:.1%} | 客 {p.probs.away:.1%}")
                print(f"       EV: 主 {p.ev.home:+.1%} | 平 {p.ev.draw:+.1%} | 客 {p.ev.away:+.1%}")
                print(f"       建议: {outcome_str} @ {odds_val:.2f} (EV: {best_ev:+.1%})")
        else:
            print(f"\n   ⚠️ 无高价值投注 (所有 EV < {self.ev_calculator.high_value_threshold:.0%})")
            print("   这表明当前场次可能没有明显的投注价值")

        # 统计
        positive_ev_count = sum(1 for p in predictions if p.ev.best_outcome()[1] > 0)
        print(f"\n   统计: {len(predictions)} 场比赛, {positive_ev_count} 场有正 EV")

        print("\n" + "=" * 80)
        print("   投注策略建议:")
        print(f"   1. 只投注 EV > {self.ev_calculator.high_value_threshold:.0%} 的场次")
        print("   2. 使用 Fractional Kelly 控制仓位 (建议 1/4 Kelly)")
        print("   3. ⚠️ EV < 0 表示负期望值，不应投注！")
        print("=" * 80 + "\n")

    def _format_value(self, value: float) -> str:
        """格式化身价数值"""
        if value == 0:
            return "0"

        abs_val = abs(value)
        sign = "+" if value > 0 else ""

        if abs_val >= 1e9:
            return f"{sign}{value/1e9:.2f}亿"
        elif abs_val >= 1e7:
            return f"{sign}{value/1e7:.1f}千万"
        elif abs_val >= 1e6:
            return f"{sign}{value/1e6:.0f}万"
        else:
            return f"{sign}{value:.0f}"

    def _simulate_odds(self, probs: ProbabilitySet) -> Odds:
        """根据概率模拟市场赔率（含 5% 抽水）"""
        vig = 0.05
        return Odds(
            home=1 / (probs.home * (1 + vig)) if probs.home > 0 else 10,
            draw=1 / (probs.draw * (1 + vig)) if probs.draw > 0 else 10,
            away=1 / (probs.away * (1 + vig)) if probs.away > 0 else 10
        )


# ============================================================================
# 主入口
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='V3.0-PRO 交钥匙预测系统')
    parser.add_argument('--league', type=str, help='指定联赛')
    parser.add_argument('--days', type=int, default=4, help='预测未来 N 天')
    parser.add_argument('--save', action='store_true', help='保存到数据库')
    parser.add_argument('--log-level', type=str, default='INFO', help='日志级别')

    args = parser.parse_args()

    predictor = WeekendPredictor(log_level=args.log_level)
    try:
        predictor.init()
        predictor.run(league=args.league, save=args.save, days=args.days)
    finally:
        predictor.close()


if __name__ == "__main__":
    main()
