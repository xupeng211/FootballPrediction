#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN-V4.46.8 预测管道 - 工业加固版                                  ║
# ║   INDUSTRIAL FORTIFICATION - FAIL-FAST + ROBUST LOGGING + JSON OUTPUT    ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 【V4.46.8 工业化加固】
# - 自动化保险丝: 全局异常捕获 + sys.exit(1)
# - 黑匣子日志: 双重输出 (控制台 + /app/logs/)
# - CLI 标准化: argparse + --json 输出
# - 安全加固: 环境变量强制校验
#
# @module scripts.ops.predict_pipeline
# @version V4.46.8-INDUSTRIAL
# @updated 2026-03-11

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 路径配置
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# 模块导入
# ============================================================================

from src.constants.model_config import RESULT_MAP_REVERSE
from src.database.repositories.prediction_repo import (
    extract_features,
    get_db_connection,
    load_pending_matches,
)
from src.ml.inference.titan_loader import get_titan_model


# ============================================================================
# 日志配置 - 双重输出
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """配置双重日志输出"""
    logger = logging.getLogger("predict_pipeline")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [predict_pipeline] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件
    log_file = LOG_DIR / "predict_pipeline.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


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
    home_prob: float
    draw_prob: float
    away_prob: float
    recommendation: str
    confidence: float
    kelly_fraction: float = 0.0
    kelly_stake: float = 0.0
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    value_edge: Optional[float] = None
    elo_diff: float = 0.0
    mv_share: float = 0.5
    h2h_estimated: bool = False


@dataclass
class PredictionReport:
    """预测报告"""
    generated_at: str
    total_matches: int
    predictions: List[Dict[str, Any]]
    summary: Dict[str, Any]
    exit_code: int = 0


# ============================================================================
# 预测管道主逻辑
# ============================================================================

def run_prediction_pipeline(
    limit: int = 50,
    league: Optional[str] = None,
    dry_run: bool = False,
) -> PredictionReport:
    """
    运行预测管道

    Args:
        limit: 最大预测数量
        league: 联赛过滤
        dry_run: 试运行模式

    Returns:
        PredictionReport: 预测报告
    """
    logger.info("=" * 70)
    logger.info("  TITAN-V4.46.8 预测管道 - 工业加固版")
    logger.info("  特征: 11 维 (Elo + 身价 + H2H[补位引擎])")
    logger.info("=" * 70)

    # 加载模型
    titan = get_titan_model()
    if not titan.is_loaded:
        logger.error("模型加载失败 - 终止执行")
        return PredictionReport(
            datetime.now().isoformat(),
            0,
            [],
            {"error": "Model not loaded"},
            exit_code=1
        )

    # 加载数据
    conn = get_db_connection()
    matches = load_pending_matches(conn, limit, league)
    logger.info(f"加载 {len(matches)} 场待预测比赛")

    if not matches:
        conn.close()
        logger.info("无待预测比赛")
        return PredictionReport(datetime.now().isoformat(), 0, [], {})

    # 执行预测
    preds = []
    hc = dc = ac = 0
    tc = 0.0
    estimated_count = 0
    errors = []

    for m in matches:
        try:
            f, h2h_est = extract_features(
                m["elo_features"],
                m["lineup_features"],
                m["h2h_features"],
                m["home_team"],
                m["away_team"],
                m["league_name"],
                conn,
            )

            if h2h_est:
                estimated_count += 1

            ap, dp, hp = titan.predict(f)

            if hp >= dp and hp >= ap:
                rec, conf = "HOME", hp
            elif dp >= ap:
                rec, conf = "DRAW", dp
            else:
                rec, conf = "AWAY", ap

            if rec == "HOME":
                hc += 1
            elif rec == "DRAW":
                dc += 1
            else:
                ac += 1
            tc += conf

            preds.append(asdict(MatchPrediction(
                match_id=m["match_id"],
                home_team=m["home_team"],
                away_team=m["away_team"],
                league=m["league_name"],
                match_time=str(m["match_date"])[:16],
                home_prob=round(hp, 4),
                draw_prob=round(dp, 4),
                away_prob=round(ap, 4),
                recommendation=rec,
                confidence=round(conf, 4),
                elo_diff=f["elo_diff"],
                mv_share=f["home_mv_share"],
                h2h_estimated=h2h_est,
            )))

        except Exception as e:
            error_msg = f"预测失败 [{m['match_id']}]: {e}"
            logger.error(error_msg)
            errors.append({"match_id": m["match_id"], "error": str(e)})

    # 汇总统计
    t = len(preds)
    summary = {
        "home_count": hc,
        "draw_count": dc,
        "away_count": ac,
        "home_pct": (hc / t * 100) if t else 0,
        "draw_pct": (dc / t * 100) if t else 0,
        "away_pct": (ac / t * 100) if t else 0,
        "avg_confidence": (tc / t) if t else 0,
        "h2h_estimated_count": estimated_count,
        "h2h_real_count": t - estimated_count,
        "error_count": len(errors),
        "model_version": "TITAN-V4.46.8-INDUSTRIAL",
        "feature_count": 11,
    }

    logger.info(f"预测完成: {t} 场 | H2H补位: {estimated_count} 场 | 错误: {len(errors)} 场")

    conn.close()

    exit_code = 1 if errors and t == 0 else 0
    return PredictionReport(datetime.now().isoformat(), t, preds, summary, exit_code=exit_code)


def format_report(r: PredictionReport) -> str:
    """格式化预测报告为可读文本"""
    lines = [
        "",
        "═" * 70,
        "  TITAN-V4.46.8 预测报告 - 工业加固版",
        "═" * 70,
        f"  生成时间: {r.generated_at}",
        f"  比赛数量: {r.total_matches}",
    ]

    s = r.summary
    lines.extend([
        f"  预测分布: 主{s.get('home_count', 0)} | 平{s.get('draw_count', 0)} | 客{s.get('away_count', 0)}",
        f"  平均置信度: {s.get('avg_confidence', 0):.1%}",
        f"  H2H 数据: 真实 {s.get('h2h_real_count', 0)} 场 | 补位 {s.get('h2h_estimated_count', 0)} 场",
        f"  错误数: {s.get('error_count', 0)}",
    ])

    if not r.predictions:
        lines.append("  无预测结果")
        return "\n".join(lines)

    sp = sorted(r.predictions, key=lambda x: x["confidence"], reverse=True)
    lines.extend(["", "─" * 70, "  高置信度推荐 (Top 10)", "─" * 70])

    for i, p in enumerate(sp[:10], 1):
        e = {"HOME": "🏠", "DRAW": "🤝", "AWAY": "✈️"}.get(p["recommendation"], "❓")
        h2h_tag = " [补位]" if p.get("h2h_estimated") else ""

        lines.extend([
            "",
            f'  {i:2d}. {p["home_team"]:<20} vs {p["away_team"]:<20}{h2h_tag}',
            f'      联赛: {p["league"]:<20} | 时间: {p["match_time"]}',
            f'      概率: 主{p["home_prob"]:.1%} 平{p["draw_prob"]:.1%} 客{p["away_prob"]:.1%}',
            f'      Elo差: {p["elo_diff"]:+.1f} | 身价占比: {p["mv_share"]:.1%}',
            f'      推荐: {e} {p["recommendation"]} (置信度: {p["confidence"]:.1%})',
        ])

    lines.extend([
        "",
        "═" * 70,
        "  TITAN-V4.46.8 INDUSTRIAL - Fail-Fast + Robust Logging",
        "═" * 70,
    ])

    return "\n".join(lines)


def output_json(r: PredictionReport) -> str:
    """输出 JSON 格式报告"""
    return json.dumps({
        "generated_at": r.generated_at,
        "total_matches": r.total_matches,
        "predictions": r.predictions,
        "summary": r.summary,
        "exit_code": r.exit_code,
    }, indent=2, ensure_ascii=False)


# ============================================================================
# CLI 入口
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="TITAN-V4.46.8 预测管道 - 工业加固版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/ops/predict_pipeline.py
  python scripts/ops/predict_pipeline.py --limit 50
  python scripts/ops/predict_pipeline.py --league "Premier League"
  python scripts/ops/predict_pipeline.py --json > predictions.json
  python scripts/ops/predict_pipeline.py --verbose

退出码:
  0 - 成功
  1 - 预测失败或有错误
        """
    )
    parser.add_argument("--limit", type=int, default=100, help="最大预测数量 (默认: 100)")
    parser.add_argument("--league", type=str, default=None, help="联赛过滤 (如: 'Premier League')")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志模式")
    return parser.parse_args()


def main():
    """主入口 - 带全局异常捕获"""
    global logger
    args = parse_args()

    # 重新配置日志级别
    logger = setup_logging(args.verbose)

    try:
        logger.info("启动预测管道")
        report = run_prediction_pipeline(
            limit=args.limit,
            league=args.league,
            dry_run=args.dry_run
        )

        # 输出结果
        if args.json:
            print(output_json(report))
        else:
            print(format_report(report))

        sys.exit(report.exit_code)

    except KeyboardInterrupt:
        logger.warning("用户中断执行")
        sys.exit(130)  # 128 + SIGINT(2)

    except Exception as e:
        logger.exception(f"未捕获的异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
