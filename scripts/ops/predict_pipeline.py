#!/usr/bin/env python3
"""
TITAN-V4.46.6 预测管道 (Prediction Pipeline) - 战备大脑版
============================================================

完整的预测流水线：
1. 从数据库读取最新 L3 特征 (Elo + 赔率)
2. 加载 TITAN-V4.46.6 模型 + StandardScaler
3. 批量预测 + Kelly 准则计算
4. 输出格式化报告 + 数据库持久化

@module scripts.ops.predict_pipeline
@version V4.46.6-TITAN
@updated 2026-03-10
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置常量
# ============================================================================

MODEL_DIR = Path(__file__).parent.parent.parent / "models"

# 结果编码（必须与 train_model.py 完全一致！）
RESULT_MAP = {"H": 2, "D": 1, "A": 0}
RESULT_NAMES = ["AWAY", "DRAW", "HOME"]
RESULT_MAP_REVERSE = {2: "H", 1: "D", 0: "A"}

# ============================================================================
# 赛前可用特征定义 (必须与 train_model.py 完全一致!)
# V4.46.6+ 适配现有数据库版 - 基于 Elo + 赔率
# ============================================================================

PRE_MATCH_FEATURES = [
    # === Elo 评分特征 (核心) ===
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "expected_home_win",
    "expected_away_win",
    # === 赔率特征 (用于 Kelly 计算) ===
    "initial_home_odds",
    "initial_draw_odds",
    "initial_away_odds",
    "implied_prob_home",
    "implied_prob_draw",
    "implied_prob_away",
    # === 派生特征 ===
    "odds_ratio_home_away",
    "elo_odds_home_diff",
]

# 默认值映射
DEFAULT_FEATURE_VALUES = {
    # Elo
    "home_elo_pre": 1500.0,
    "away_elo_pre": 1500.0,
    "elo_diff": 0.0,
    "expected_home_win": 0.45,
    "expected_away_win": 0.30,
    # 赔率
    "initial_home_odds": 2.2,
    "initial_draw_odds": 3.3,
    "initial_away_odds": 3.0,
    "implied_prob_home": 0.45,
    "implied_prob_draw": 0.25,
    "implied_prob_away": 0.30,
    # 派生
    "odds_ratio_home_away": 0.73,
    "elo_odds_home_diff": 0.0,
}


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class MatchPrediction:
    """比赛预测结果"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    match_time: str

    # 概率预测
    home_prob: float
    draw_prob: float
    away_prob: float

    # 推荐投注
    recommendation: str  # HOME, DRAW, AWAY
    confidence: float    # 0-1

    # Kelly 准则
    kelly_fraction: float
    kelly_stake: float   # 建议投注比例

    # 赔率 (如果有)
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None

    # 价值分析
    value_edge: Optional[float] = None  # 期望价值


@dataclass
class PredictionReport:
    """预测报告"""
    generated_at: str
    total_matches: int
    predictions: List[Dict[str, Any]]
    summary: Dict[str, Any]


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )


# ============================================================================
# 特征提取 (必须与 train_model.py 完全一致!)
# ============================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def extract_elo_features(elo_data: Any) -> Dict[str, float]:
    """
    从 elo_features JSONB 提取 Elo 特征
    """
    features = {}

    if elo_data is None:
        return {k: DEFAULT_FEATURE_VALUES[k] for k in ["home_elo_pre", "away_elo_pre", "elo_diff", "expected_home_win", "expected_away_win"]}

    if isinstance(elo_data, str):
        try:
            elo_data = json.loads(elo_data)
        except:
            elo_data = {}

    if not isinstance(elo_data, dict):
        elo_data = {}

    home_elo = safe_float(elo_data.get('home_elo_pre', elo_data.get('home_elo', 1500)), 1500.0)
    away_elo = safe_float(elo_data.get('away_elo_pre', elo_data.get('away_elo', 1500)), 1500.0)

    features['home_elo_pre'] = home_elo
    features['away_elo_pre'] = away_elo
    features['elo_diff'] = safe_float(elo_data.get('elo_diff', home_elo - away_elo))
    features['expected_home_win'] = safe_float(elo_data.get('expected_home_win', 0.45))
    features['expected_away_win'] = safe_float(elo_data.get('expected_away_win', 0.30))

    return features


def extract_odds_features(odds_data: Any) -> Dict[str, float]:
    """
    从 odds_features JSONB 提取赔率特征
    """
    features = {}

    if odds_data is None:
        return {k: DEFAULT_FEATURE_VALUES[k] for k in [
            "initial_home_odds", "initial_draw_odds", "initial_away_odds",
            "implied_prob_home", "implied_prob_draw", "implied_prob_away"
        ]}

    if isinstance(odds_data, str):
        try:
            odds_data = json.loads(odds_data)
        except:
            odds_data = {}

    if not isinstance(odds_data, dict):
        odds_data = {}

    features['initial_home_odds'] = safe_float(odds_data.get('initial_home_odds', 2.2), 2.2)
    features['initial_draw_odds'] = safe_float(odds_data.get('initial_draw_odds', 3.3), 3.3)
    features['initial_away_odds'] = safe_float(odds_data.get('initial_away_odds', 3.0), 3.0)
    features['implied_prob_home'] = safe_float(odds_data.get('implied_prob_home', 0.45), 0.45)
    features['implied_prob_draw'] = safe_float(odds_data.get('implied_prob_draw', 0.25), 0.25)
    features['implied_prob_away'] = safe_float(odds_data.get('implied_prob_away', 0.30), 0.30)

    return features


def compute_derived_features(features: Dict[str, float]) -> Dict[str, float]:
    """
    计算派生特征 (必须与 train_model.py 完全一致!)
    """
    derived = {}

    home_odds = features.get('initial_home_odds', 2.2)
    away_odds = features.get('initial_away_odds', 3.0)
    derived['odds_ratio_home_away'] = home_odds / away_odds if away_odds > 0 else 0.73

    elo_home = features.get('expected_home_win', 0.45)
    odds_home = features.get('implied_prob_home', 0.45)
    derived['elo_odds_home_diff'] = elo_home - odds_home

    return derived


def extract_pre_match_features(
    elo_data: Any,
    odds_data: Any
) -> Dict[str, float]:
    """
    提取完整的赛前特征向量 (V4.46.6+ 适配现有数据库版)

    这是训练和预测的统一入口，必须保持完全一致!
    基于 Elo + 赔率 (现有数据结构)
    """
    features = {}

    # 1. 提取 Elo 特征 (核心)
    features.update(extract_elo_features(elo_data))

    # 2. 提取赔率特征 (用于 Kelly 计算)
    features.update(extract_odds_features(odds_data))

    # 3. 计算派生特征
    features.update(compute_derived_features(features))

    # 确保特征顺序和完整性
    result = {}
    for feat_name in PRE_MATCH_FEATURES:
        result[feat_name] = features.get(feat_name, DEFAULT_FEATURE_VALUES.get(feat_name, 0.0))

    return result


# ============================================================================
# TITAN 模型加载器
# ============================================================================

class TitanModelLoader:
    """TITAN-V4.46.6 模型加载器（带 StandardScaler）"""

    _instance = None
    _model = None
    _scaler = None
    _metadata = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """加载 TITAN-V4.46.6 模型、Scaler 和元数据"""
        # 尝试多个路径
        model_paths = [
            Path("/app/models/titan_v4466.joblib"),
            MODEL_DIR / "titan_v4466.joblib",
            MODEL_DIR / "xgboost_model.joblib",  # 兼容旧模型
        ]

        scaler_paths = [
            Path("/app/models/titan_v4466_scaler.joblib"),
            MODEL_DIR / "titan_v4466_scaler.joblib",
        ]

        metadata_paths = [
            Path("/app/models/titan_v4466_metadata.json"),
            MODEL_DIR / "titan_v4466_metadata.json",
            MODEL_DIR / "xgboost_model_metadata.json",  # 兼容旧模型
        ]

        # 加载模型
        for model_path in model_paths:
            if model_path.exists():
                try:
                    self._model = joblib.load(model_path)
                    logger.info(f"✅ TITAN 模型加载成功: {model_path}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ 模型加载失败 [{model_path}]: {e}")

        if self._model is None:
            logger.warning(f"⚠️ 未找到模型文件，尝试路径: {model_paths}")

        # 加载 Scaler
        for scaler_path in scaler_paths:
            if scaler_path.exists():
                try:
                    self._scaler = joblib.load(scaler_path)
                    logger.info(f"✅ StandardScaler 加载成功: {scaler_path}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Scaler 加载失败 [{scaler_path}]: {e}")

        if self._scaler is None:
            logger.warning("⚠️ 未找到 StandardScaler，预测可能不准确")

        # 加载元数据
        for metadata_path in metadata_paths:
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        self._metadata = json.load(f)
                    logger.info(f"✅ 模型元数据加载成功: {metadata_path}")
                    logger.info(f"   特征维度: {self._metadata.get('feature_count', 'unknown')}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ 元数据加载失败 [{metadata_path}]: {e}")

        if self._metadata is None:
            self._metadata = {
                "version": "V4.46.6",
                "feature_names": PRE_MATCH_FEATURES,
                "feature_count": len(PRE_MATCH_FEATURES)
            }

    @property
    def model(self):
        return self._model

    @property
    def scaler(self):
        return self._scaler

    @property
    def metadata(self):
        return self._metadata

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def has_scaler(self) -> bool:
        return self._scaler is not None

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        执行模型预测（带标准化）

        Args:
            X: 特征矩阵 (n_samples, n_features)

        Returns:
            概率矩阵 (n_samples, 3) - [AWAY, DRAW, HOME]
        """
        if not self.is_loaded:
            raise RuntimeError("模型未加载")

        # 标准化（如果有 Scaler）
        if self.has_scaler:
            X_scaled = self._scaler.transform(X)
        else:
            X_scaled = X

        return self._model.predict_proba(X_scaled)


# 全局模型实例
_titan_model: Optional[TitanModelLoader] = None


def get_titan_model() -> TitanModelLoader:
    """获取全局 TITAN 模型实例"""
    global _titan_model
    if _titan_model is None:
        _titan_model = TitanModelLoader()
    return _titan_model


# ============================================================================
# 数据加载
# ============================================================================

def load_pending_matches(conn, limit: int = 50, league: Optional[str] = None) -> List[Dict]:
    """
    加载待预测的比赛 (V4.46.6+ 适配现有数据库版)
    """
    cursor = conn.cursor()

    query = """
    SELECT
        m.match_id,
        m.home_team,
        m.away_team,
        m.league_name,
        m.match_date,
        m.status,
        l.elo_features,
        l.odds_features
    FROM matches m
    INNER JOIN l3_features l ON m.match_id = l.match_id
    LEFT JOIN predictions p ON m.match_id = p.match_id
    WHERE p.match_id IS NULL
      AND m.match_date > NOW()
      AND m.match_date < NOW() + INTERVAL '7 days'
    """

    params = []

    if league:
        query += " AND m.league_name = %s"
        params.append(league)

    query += " ORDER BY m.match_date ASC LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    matches = cursor.fetchall()
    cursor.close()

    return [dict(m) for m in matches]


# ============================================================================
# 预测逻辑
# ============================================================================

def predict_with_model(
    features: Dict[str, float],
    model: TitanModelLoader
) -> Tuple[float, float, float]:
    """
    使用 TITAN 模型执行预测

    Args:
        features: 特征字典
        model: TITAN 模型加载器

    Returns:
        (home_prob, draw_prob, away_prob)
    """
    try:
        # 构建特征向量（按 PRE_MATCH_FEATURES 顺序）
        feature_vector = np.array([[features.get(name, 0.0) for name in PRE_MATCH_FEATURES]])

        # 执行预测
        probs = model.predict(feature_vector)[0]

        # 模型输出顺序: [AWAY, DRAW, HOME]
        away_prob = float(probs[0])
        draw_prob = float(probs[1])
        home_prob = float(probs[2])

        # 确保概率在有效范围内
        home_prob = max(0.0, min(1.0, home_prob))
        draw_prob = max(0.0, min(1.0, draw_prob))
        away_prob = max(0.0, min(1.0, away_prob))

        # 归一化
        total = home_prob + draw_prob + away_prob
        if total > 0:
            home_prob /= total
            draw_prob /= total
            away_prob /= total

        return home_prob, draw_prob, away_prob

    except Exception as e:
        logger.error(f"模型预测失败: {e}")
        raise


def predict_with_elo_ensemble(features: Dict[str, float]) -> Tuple[float, float, float]:
    """
    使用 Elo + 赔率集成预测（回退策略）
    """
    # Elo 预期
    elo_home = features.get('expected_home_win', 0.45)
    elo_away = features.get('expected_away_win', 0.35)
    elo_draw = 1.0 - elo_home - elo_away

    # 赔率隐含概率
    odds_home = features.get('implied_prob_home', 0.45)
    odds_draw = features.get('implied_prob_draw', 0.25)
    odds_away = features.get('implied_prob_away', 0.30)

    # 历史先验
    prior_home, prior_draw, prior_away = 0.45, 0.25, 0.30

    # 加权融合
    home_prob = 0.4 * elo_home + 0.4 * odds_home + 0.2 * prior_home
    draw_prob = 0.4 * elo_draw + 0.4 * odds_draw + 0.2 * prior_draw
    away_prob = 0.4 * elo_away + 0.4 * odds_away + 0.2 * prior_away

    # 归一化
    total = home_prob + draw_prob + away_prob
    home_prob /= total
    draw_prob /= total
    away_prob /= total

    return home_prob, draw_prob, away_prob


def predict_match(
    features: Dict[str, float],
    model: Optional[TitanModelLoader] = None
) -> Tuple[float, float, float]:
    """
    执行单场预测

    策略:
    1. 如果 TITAN 模型可用，使用模型预测
    2. 否则使用 Elo + 赔率集成预测
    """
    if model is None:
        model = get_titan_model()

    if model.is_loaded:
        try:
            home_prob, draw_prob, away_prob = predict_with_model(features, model)
            logger.info(f"🤖 TITAN 模型预测: 主{home_prob:.1%} 平{draw_prob:.1%} 客{away_prob:.1%}")
            return home_prob, draw_prob, away_prob
        except Exception as e:
            logger.warning(f"TITAN 模型预测失败，回退到 Elo+赔率集成: {e}")

    # 回退到 Elo + 赔率集成预测
    home_prob, draw_prob, away_prob = predict_with_elo_ensemble(features)
    logger.info(f"📊 Elo+赔率集成预测: 主{home_prob:.1%} 平{draw_prob:.1%} 客{away_prob:.1%}")

    return home_prob, draw_prob, away_prob


# ============================================================================
# Kelly 准则
# ============================================================================

def calculate_kelly(prob: float, odds: float, fraction: float = 0.25) -> Tuple[float, float]:
    """
    计算 Fractional Kelly 投注比例

    Args:
        prob: 预测概率
        odds: 赔率
        fraction: Kelly 分数 (默认 1/4 Kelly)

    Returns:
        (kelly_fraction, edge): 建议投注比例, 期望价值
    """
    if odds <= 1.0:
        return 0.0, 0.0

    # 计算期望价值
    edge = (prob * odds) - 1

    if edge <= 0:
        return 0.0, edge

    # Kelly 公式: f = (bp - q) / b = (p * odds - 1) / (odds - 1)
    kelly_full = edge / (odds - 1)

    # 应用 Fractional Kelly (降低风险)
    kelly_fraction = kelly_full * fraction

    # 限制最大投注比例
    kelly_fraction = min(kelly_fraction, 0.10)  # 最大 10% 资金

    return kelly_fraction, edge


# ============================================================================
# 报告生成
# ============================================================================

def generate_recommendation(
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    home_odds: Optional[float] = None,
    draw_odds: Optional[float] = None,
    away_odds: Optional[float] = None,
    min_confidence: float = 0.35
) -> Tuple[str, float, float, float]:
    """
    生成投注推荐

    Returns:
        (recommendation, confidence, kelly_stake, value_edge)
    """
    probs = {'HOME': home_prob, 'DRAW': draw_prob, 'AWAY': away_prob}
    odds = {'HOME': home_odds, 'DRAW': draw_odds, 'AWAY': away_odds}

    best_outcome = max(probs, key=probs.get)
    best_prob = probs[best_outcome]
    best_odds = odds[best_outcome]

    # 计算置信度
    second_prob = sorted(probs.values())[-2]
    confidence = best_prob - second_prob + 0.5  # 归一化到 0-1
    confidence = min(max(confidence, 0), 1)

    # 计算 Kelly
    kelly_stake = 0.0
    value_edge = 0.0

    if best_odds and best_odds > 1.0:
        kelly_stake, value_edge = calculate_kelly(best_prob, best_odds)

    return best_outcome, confidence, kelly_stake, value_edge


def format_report(report: PredictionReport, output_format: str = 'text') -> str:
    """格式化输出报告"""
    if output_format == 'json':
        return json.dumps(asdict(report), indent=2, ensure_ascii=False, default=str)

    lines = []
    lines.append('')
    lines.append('╔══════════════════════════════════════════════════════════════════════════════╗')
    lines.append('║  🧠 TITAN-V4.46.6 AI 预测报告 - 战备大脑版 - StandardScaler Enabled          ║')
    lines.append('╚══════════════════════════════════════════════════════════════════════════════╝')
    lines.append('')
    lines.append(f"  生成时间: {report.generated_at}")
    lines.append(f"  比赛数量: {report.total_matches}")

    summary = report.summary
    model_version = summary.get('model_version', 'Unknown')
    titan_preds = summary.get('titan_predictions', 0)
    ensemble_preds = summary.get('ensemble_predictions', 0)
    lines.append(f"  模型版本: {model_version}")
    lines.append(f"  预测来源: TITAN={titan_preds}, 集成={ensemble_preds}")
    lines.append('')

    if not report.predictions:
        lines.append("  ⚠️  无待预测比赛")
        lines.append('')
        return '\n'.join(lines)

    sorted_preds = sorted(report.predictions, key=lambda x: x['confidence'], reverse=True)

    lines.append('  ┌────────────────────────────────────────────────────────────────────────────┐')
    lines.append('  │ 🏆 高置信度推荐 (Top 10)                                                    │')
    lines.append('  └────────────────────────────────────────────────────────────────────────────┘')
    lines.append('')

    for i, pred in enumerate(sorted_preds[:10], 1):
        rec_emoji = {'HOME': '🏠', 'DRAW': '🤝', 'AWAY': '✈️'}.get(pred['recommendation'], '❓')

        lines.append(f"  {i:2d}. {pred['home_team']:<22} vs {pred['away_team']:<22}")
        lines.append(f"      联赛: {pred['league']:<25} 时间: {pred['match_time'][:16]}")
        lines.append(f"      概率: 主{pred['home_prob']:.1%} 平{pred['draw_prob']:.1%} 客{pred['away_prob']:.1%}")
        lines.append(f"      推荐: {rec_emoji} {pred['recommendation']} (置信度: {pred['confidence']:.1%})")

        if pred.get('kelly_stake', 0) > 0:
            lines.append(f"      Kelly: {pred['kelly_stake']:.1%} 投注 | 价值: {pred.get('value_edge', 0):+.1%}")

        lines.append('')

    lines.append('  ┌────────────────────────────────────────────────────────────────────────────┐')
    lines.append('  │ 📊 预测分布统计                                                            │')
    lines.append('  └────────────────────────────────────────────────────────────────────────────┘')
    lines.append('')
    lines.append(f"      主胜推荐: {summary.get('home_count', 0)} 场 ({summary.get('home_pct', 0):.1f}%)")
    lines.append(f"      平局推荐: {summary.get('draw_count', 0)} 场 ({summary.get('draw_pct', 0):.1f}%)")
    lines.append(f"      客胜推荐: {summary.get('away_count', 0)} 场 ({summary.get('away_pct', 0):.1f}%)")
    lines.append(f"      平均置信度: {summary.get('avg_confidence', 0):.1%}")
    lines.append('')
    lines.append('══════════════════════════════════════════════════════════════════════════════')
    lines.append('  TITAN-V4.46.6 战备大脑版 - 训练-预测特征完全对齐 - StandardScaler 防退化')
    lines.append('══════════════════════════════════════════════════════════════════════════════')
    lines.append('')

    return '\n'.join(lines)


# ============================================================================
# 主流程
# ============================================================================

def run_prediction_pipeline(
    limit: int = 50,
    league: Optional[str] = None,
    output_format: str = 'text',
    dry_run: bool = False
) -> PredictionReport:
    """
    执行完整预测管道
    """
    logger.info('🚀 TITAN-V4.46.6 预测管道启动...')

    # 1. 加载 TITAN 模型
    logger.info('🧠 加载 TITAN 模型...')
    titan_model = get_titan_model()

    if titan_model.is_loaded:
        logger.info('✅ TITAN 模型就绪')
        if titan_model.has_scaler:
            logger.info('✅ StandardScaler 就绪')
        else:
            logger.warning('⚠️ StandardScaler 未加载，预测可能不准确')
    else:
        logger.warning('⚠️ TITAN 模型不可用，将使用 Elo+赔率集成预测')

    # 2. 连接数据库
    logger.info('📡 连接数据库...')
    conn = get_db_connection()

    # 3. 加载待预测比赛
    logger.info(f'📊 加载待预测比赛 (limit={limit}, league={league or "全部"})...')
    matches = load_pending_matches(conn, limit=limit, league=league)

    if not matches:
        logger.info('✅ 无待预测比赛')
        conn.close()
        return PredictionReport(
            generated_at=datetime.now().isoformat(),
            total_matches=0,
            predictions=[],
            summary={}
        )

    logger.info(f'📋 找到 {len(matches)} 场待预测比赛')

    # 4. 批量预测
    predictions = []
    home_count = draw_count = away_count = 0
    total_confidence = 0.0
    titan_count = 0
    ensemble_count = 0

    logger.info('🤖 执行 AI 预测...')

    for match in matches:
        try:
            # 提取赛前特征 (V4.46.6+ 适配版: Elo + 赔率)
            features = extract_pre_match_features(
                match.get('elo_features'),
                match.get('odds_features')
            )

            # 预测
            home_prob, draw_prob, away_prob = predict_match(features, titan_model)

            # 统计预测来源
            if titan_model.is_loaded:
                titan_count += 1
            else:
                ensemble_count += 1

            # 获取赔率 (从 odds_features 中提取，用于 Kelly 计算)
            odds_data = match.get('odds_features')
            home_odds = None
            draw_odds = None
            away_odds = None

            if odds_data:
                if isinstance(odds_data, str):
                    try:
                        odds_data = json.loads(odds_data)
                    except:
                        odds_data = {}
                if isinstance(odds_data, dict):
                    home_odds = safe_float(odds_data.get('initial_home_odds'), None)
                    draw_odds = safe_float(odds_data.get('initial_draw_odds'), None)
                    away_odds = safe_float(odds_data.get('initial_away_odds'), None)

            # 生成推荐
            recommendation, confidence, kelly_stake, value_edge = generate_recommendation(
                home_prob, draw_prob, away_prob,
                home_odds, draw_odds, away_odds
            )

            # 统计
            if recommendation == 'HOME':
                home_count += 1
            elif recommendation == 'DRAW':
                draw_count += 1
            else:
                away_count += 1
            total_confidence += confidence

            # 构建预测结果
            pred = MatchPrediction(
                match_id=match['match_id'],
                home_team=match['home_team'],
                away_team=match['away_team'],
                league=match['league_name'],
                match_time=str(match['match_date']),
                home_prob=round(home_prob, 4),
                draw_prob=round(draw_prob, 4),
                away_prob=round(away_prob, 4),
                recommendation=recommendation,
                confidence=round(confidence, 4),
                kelly_fraction=round(kelly_stake, 4),
                kelly_stake=round(kelly_stake, 4),
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
                value_edge=round(value_edge, 4) if value_edge else None
            )

            predictions.append(asdict(pred))

        except Exception as e:
            logger.error(f"预测失败 [{match['match_id']}]: {e}")
            continue

    # 5. 生成报告
    total = len(predictions)
    summary = {
        'home_count': home_count,
        'draw_count': draw_count,
        'away_count': away_count,
        'home_pct': (home_count / total * 100) if total > 0 else 0,
        'draw_pct': (draw_count / total * 100) if total > 0 else 0,
        'away_pct': (away_count / total * 100) if total > 0 else 0,
        'avg_confidence': (total_confidence / total) if total > 0 else 0,
        'titan_predictions': titan_count,
        'ensemble_predictions': ensemble_count,
        'model_version': 'TITAN-V4.46.6' if titan_model.is_loaded else 'Elo+Odds-Ensemble',
        'scaler_enabled': titan_model.has_scaler
    }

    report = PredictionReport(
        generated_at=datetime.now().isoformat(),
        total_matches=total,
        predictions=predictions,
        summary=summary
    )

    # 6. 写入数据库 (非 dry_run 模式)
    if not dry_run and predictions:
        logger.info('💾 写入预测结果到数据库...')
        cursor = conn.cursor()

        for pred in predictions:
            cursor.execute("""
                INSERT INTO predictions (
                    match_id, model_version, predicted_result,
                    confidence_home, confidence_draw, confidence_away,
                    confidence, recommendation, kelly_fraction, value_edge,
                    prediction_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (match_id, model_version) DO UPDATE SET
                    predicted_result = EXCLUDED.predicted_result,
                    confidence_home = EXCLUDED.confidence_home,
                    confidence_draw = EXCLUDED.confidence_draw,
                    confidence_away = EXCLUDED.confidence_away,
                    confidence = EXCLUDED.confidence,
                    recommendation = EXCLUDED.recommendation,
                    kelly_fraction = EXCLUDED.kelly_fraction,
                    value_edge = EXCLUDED.value_edge,
                    prediction_date = NOW(),
                    updated_at = NOW()
            """, (
                pred['match_id'],
                'TITAN-V4.46.6',
                pred['recommendation'],
                pred['home_prob'],
                pred['draw_prob'],
                pred['away_prob'],
                pred['confidence'],
                pred['recommendation'],
                pred['kelly_fraction'],
                pred.get('value_edge')
            ))

        conn.commit()
        cursor.close()
        logger.info(f'✅ 已写入 {len(predictions)} 条预测到 predictions 表')

    conn.close()

    logger.info(f'🎉 预测管道完成! TITAN: {titan_count}, 集成: {ensemble_count}')

    return report


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='TITAN-V4.46.6 预测管道',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 预测未来所有比赛
  python scripts/ops/predict_pipeline.py

  # 仅预测德甲
  python scripts/ops/predict_pipeline.py --league Bundesliga

  # 试运行 (不写入数据库)
  python scripts/ops/predict_pipeline.py --dry-run

  # JSON 输出
  python scripts/ops/predict_pipeline.py --format json
        '''
    )

    parser.add_argument('--limit', type=int, default=50, help='最大预测数量')
    parser.add_argument('--league', type=str, help='过滤联赛')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式')

    args = parser.parse_args()

    report = run_prediction_pipeline(
        limit=args.limit,
        league=args.league,
        output_format=args.format,
        dry_run=args.dry_run
    )

    print(format_report(report, args.format))


if __name__ == '__main__':
    main()
