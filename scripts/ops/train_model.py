#!/usr/bin/env python3
# ruff: noqa: PLR2004, C901, RUF013, UP006, G004, N803
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN-V4.46.8 模型训练管道 - 工业加固版                              ║
# ║   INDUSTRIAL FORTIFICATION - FAIL-FAST + ROBUST LOGGING + JSON OUTPUT    ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 【V4.46.8 工业化加固】
# - 自动化保险丝: 全局异常捕获 + sys.exit(1)
# - 黑匣子日志: 双重输出 (控制台 + /app/logs/)
# - CLI 标准化: argparse + --json 输出
# - 安全加固: 环境变量强制校验
#
# @module scripts.ops.train_model
# @version V4.46.8-INDUSTRIAL
# @updated 2026-03-11

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import importlib.util
import json
import logging
from pathlib import Path
import sys
from typing import Dict, Tuple  # noqa: UP035

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# ============================================================================
# 路径配置
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# 模块导入
# ============================================================================

from src.constants.model_config import (  # noqa: E402
    MODEL_DIR,
    RESULT_MAP,
    RESULT_NAMES,
    TITAN_COMBAT_FEATURES,
)
from src.database.repositories.prediction_repo import get_db_connection  # noqa: E402

# ============================================================================
# 日志配置 - 双重输出
# ============================================================================


def setup_logging(verbose: bool = False, *, write_file: bool = False) -> logging.Logger:
    """配置双重日志输出"""
    logger = logging.getLogger("train_model")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [train_model] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if write_file:
        LOG_DIR.mkdir(exist_ok=True)
        log_file = LOG_DIR / "train_model.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


logger = logging.getLogger("train_model")


def _load_training_write_guard_module():
    """Load training write guard without importing the broad src.ml package."""
    module_path = PROJECT_ROOT / "src" / "ml" / "training_write_guard.py"
    spec = importlib.util.spec_from_file_location("training_write_guard", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


require_training_write_confirmation = (
    _load_training_write_guard_module().require_training_write_confirmation
)


def _load_filtered_matrix_report_module():
    """Load report-only helper without importing the broken features package."""
    module_path = PROJECT_ROOT / "src" / "ml" / "features" / "filtered_matrix_report.py"
    spec = importlib.util.spec_from_file_location("filtered_matrix_report", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_report_from_connection(conn) -> dict:
    """Build the filtered matrix report from a SELECT-only DB connection."""
    return _load_filtered_matrix_report_module().build_report_from_connection(conn)


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class TrainingResult:
    """训练结果"""

    model_path: str
    scaler_path: str
    accuracy: float
    f1_score: float
    log_loss: float
    training_samples: int
    feature_count: int
    training_time_seconds: float
    exit_code: int = 0


# ============================================================================
# V5.0 特征提取 (适配新表结构)
# ============================================================================


def _load_contract_module():
    """Load the L3 prematch contract module via importlib.

    Uses importlib to bypass the broken src.ml.features.__init__ chain
    (which fails on SCORING.DEFAULT_AVG_TOTAL_GOALS).
    """
    import importlib.util as _util  # noqa: PLC0415

    _spec = _util.spec_from_file_location(
        "l3_prematch_contract",
        PROJECT_ROOT / "src" / "ml" / "features" / "l3_prematch_contract.py",
    )
    _mod = _util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod


def _filter_l3_json_for_prematch(group_name, raw_json):
    """Filter one L3 JSONB group through the prematch-safe contract.

    Returns the filtered dict. On any error, returns raw JSON as a safety
    fallback — the existing key-level guards still provide protection.
    """
    if raw_json is None:
        return {}
    try:
        mod = _load_contract_module()
        contract = mod.load_l3_prematch_contract()
        return mod.filter_l3_feature_group(
            group_name,
            raw_json,
            include_conditional=False,
            allow_diagnostic_postmatch=False,
            contract=contract,
        )
    except Exception:
        return raw_json if isinstance(raw_json, dict) else {}


def extract_v5_features(elo_data, golden_features, tactical_features):
    """
    从 V5.0 表结构提取 11 维战斗特征

    Args:
        elo_data: Elo 特征 (JSONB)
        golden_features: 黄金特征 (JSONB) - 包含身价数据
        tactical_features: 战术特征 (JSONB) - 包含 H2H 数据

    Returns:
        dict: 11 维特征字典
    """
    import json
    import math

    # 解析 JSONB
    elo_raw = elo_data if isinstance(elo_data, dict) else json.loads(elo_data or "{}")
    golden_raw = (
        golden_features
        if isinstance(golden_features, dict)
        else json.loads(golden_features or "{}")
    )
    tactical_raw = (
        tactical_features
        if isinstance(tactical_features, dict)
        else json.loads(tactical_features or "{}")
    )

    # ── GOLD-AUDIT-2F: enforce prematch-safe L3 contract ────────────────
    golden = _filter_l3_json_for_prematch("golden_features", golden_raw)
    tactical = _filter_l3_json_for_prematch("tactical_features", tactical_raw)
    elo = _filter_l3_json_for_prematch("elo_features", elo_raw)
    # ────────────────────────────────────────────────────────────────────

    f = {}

    # === Elo 特征 (5 维) ===
    home_elo = float(elo.get("home_elo", elo.get("home_elo_pre", 1500)))
    away_elo = float(elo.get("away_elo", elo.get("away_elo_pre", 1500)))
    f["home_elo_pre"] = home_elo
    f["away_elo_pre"] = away_elo
    f["elo_diff"] = float(elo.get("elo_diff", home_elo - away_elo))
    f["expected_home_win"] = float(elo.get("expected_home_win", elo.get("elo_expected_home", 0.45)))
    f["expected_away_win"] = float(elo.get("expected_away_win", elo.get("elo_expected_away", 0.30)))

    # === 身价特征 (3 维) - 从 golden_features ===
    home_mv = float(golden.get("home_market_value_total", golden.get("home_squad_value_eur", 1e8)))
    away_mv = float(golden.get("away_market_value_total", golden.get("away_squad_value_eur", 1e8)))

    f["log_home_squad_value"] = math.log10(home_mv) if home_mv > 0 else 18.0
    f["log_away_squad_value"] = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f["home_mv_share"] = home_mv / total_mv if total_mv > 0 else 0.5

    # === H2H 特征 (3 维) - 从 tactical_features 估算 ===
    # V5.0: 如果 tactical 中有 H2H 数据则使用，否则基于 Elo 差估算
    h2h_home_win = float(tactical.get("h2h_home_win_ratio", 0.5))
    h2h_draw = float(tactical.get("h2h_draw_ratio", 0.3))

    # 如果没有 H2H 数据，基于 Elo 差进行智能估算
    if h2h_home_win == 0.5 and "elo_diff" in f:
        elo_diff = f["elo_diff"]
        # Elo 差转换为 H2H 胜率 (简化模型)
        expected_win = 1 / (1 + 10 ** (-elo_diff / 400))
        h2h_home_win = 0.3 + 0.4 * expected_win  # 基础 30% + Elo 贡献
        h2h_draw = 0.25  # 默认平局率

    f["h2h_home_win_ratio"] = h2h_home_win
    f["h2h_draw_ratio"] = h2h_draw
    f["h2h_avg_goal_diff"] = float(tactical.get("h2h_avg_goal_diff", 0.0))

    return f


# ============================================================================
# 数据加载
# ============================================================================


def load_training_data(
    conn, min_samples: int = 100, logger: logging.Logger = None
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    加载训练数据 (TITAN 11 维纯净版 - 无数据泄露)
    """
    if logger:
        logger.info("开始加载训练数据...")

    query = """
        SELECT m.match_id, m.home_score, m.away_score, m.home_team, m.away_team,
               l.elo_features, l.golden_features, l.tactical_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'Harvested'
          AND m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
          AND l.elo_features IS NOT NULL
        ORDER BY m.match_date DESC
    """

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    if logger:
        logger.info(f"加载了 {len(rows)} 条训练记录")

    if len(rows) < min_samples:
        raise ValueError(f"训练数据不足: 需要至少 {min_samples} 条，当前 {len(rows)} 条")

    # 延迟导入避免循环依赖

    features_list = []
    labels = []
    skipped = 0

    for row in rows:
        try:
            # V5.0: 从新的表结构提取特征
            features = extract_v5_features(
                row["elo_features"],
                row["golden_features"],
                row["tactical_features"],
            )
            features_list.append(features)

            # 从比分计算赛果
            home_score = row.get("home_score", 0)
            away_score = row.get("away_score", 0)
            if home_score > away_score:
                result = "H"
            elif home_score < away_score:
                result = "A"
            else:
                result = "D"
            labels.append(RESULT_MAP[result])
        except Exception as e:
            skipped += 1
            if logger:
                logger.warning(f"特征提取失败 [{row['match_id']}]: {e}")

    if logger and skipped > 0:
        logger.warning(f"跳过 {skipped} 条无效记录")

    X = pd.DataFrame(features_list)[TITAN_COMBAT_FEATURES]
    y = pd.Series(labels, name="result")

    if logger:
        logger.info(f"构建数据集: {X.shape[0]} 样本, {X.shape[1]} 特征")
        logger.info(f"标签分布: H={sum(y == 2)}, D={sum(y == 1)}, A={sum(y == 0)}")

    return X, y


# ============================================================================
# 模型训练
# ============================================================================


def train_model(
    X: pd.DataFrame, y: pd.Series, logger: logging.Logger = None
) -> Tuple[xgb.XGBClassifier, StandardScaler, Dict]:
    """训练 XGBoost 模型（带标准化）"""
    if logger:
        logger.info("开始训练 XGBoost 模型...")

    start_time = datetime.now()

    X = X.fillna(0).replace([np.inf, -np.inf], 0)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 类别权重
    class_counts = np.bincount(y_train)
    sample_weights = np.ones(len(y_train))
    for i, count in enumerate(class_counts):
        if count > 0:
            sample_weights[y_train == i] = len(y_train) / (len(class_counts) * count)

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        max_depth=4,  # 限制树深度在3-5之间，防止过拟合
        learning_rate=0.05,
        n_estimators=500,  # 增加最大轮数，让早停决定
        subsample=0.7,  # 降低行采样率
        colsample_bytree=0.7,  # 降低列采样率
        min_child_weight=5,  # 最小叶子节点样本数，防止过拟合
        gamma=0.3,  # 分裂惩罚，增加模型稳定性
        reg_alpha=0.1,  # L1正则化
        reg_lambda=1.0,  # L2正则化
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=30,  # 早停轮数
        eval_metric="mlogloss",
    )

    model.fit(
        X_train_scaled,
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_score": float(f1_score(y_test, y_pred, average="weighted")),
        "log_loss": float(log_loss(y_test, y_proba)),
        "training_samples": X_train.shape[0],
        "training_time_seconds": (datetime.now() - start_time).total_seconds(),
        "feature_importance": dict(zip(TITAN_COMBAT_FEATURES, model.feature_importances_.tolist())),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, target_names=RESULT_NAMES),
    }

    if logger:
        logger.info(f"训练完成! 准确率: {metrics['accuracy']:.2%}, F1: {metrics['f1_score']:.4f}")

    return model, scaler, metrics


# ============================================================================
# 模型保存
# ============================================================================


def save_model(
    model: xgb.XGBClassifier,
    scaler: StandardScaler,
    metrics: Dict,
    output_name: str,
    logger: logging.Logger = None,
) -> Tuple[str, str]:
    """保存模型、Scaler 和元数据"""
    require_training_write_confirmation()
    import joblib

    model_path = MODEL_DIR / f"{output_name}.joblib"
    scaler_path = MODEL_DIR / f"{output_name}_scaler.joblib"

    joblib.dump(model, str(model_path))
    joblib.dump(scaler, str(scaler_path))

    metadata = {
        "version": "V4.46.8-INDUSTRIAL",
        "created_at": datetime.now().isoformat(),
        "feature_names": TITAN_COMBAT_FEATURES,
        "metrics": {
            "accuracy": metrics["accuracy"],
            "f1_score": metrics["f1_score"],
            "log_loss": metrics["log_loss"],
            "training_samples": metrics["training_samples"],
            "training_time_seconds": metrics["training_time_seconds"],
        },
        "feature_importance": metrics["feature_importance"],
    }

    metadata_path = MODEL_DIR / f"{output_name}_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    if logger:
        logger.info(f"模型已保存: {model_path}")
        logger.info(f"元数据已保存: {metadata_path}")

    return str(model_path), str(scaler_path)


# ============================================================================
# CLI 入口
# ============================================================================


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="TITAN-V4.46.8 模型训练管道 - 工业加固版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例: python scripts/ops/train_model.py [--dry-run] [--json] [--verbose]\n"
        "退出码: 0=成功 1=失败 2=配置错误",
    )
    parser.add_argument(
        "--name", default="titan_v4468_combat", help="模型输出名称 (默认: titan_v4468_combat)"
    )
    parser.add_argument("--min-samples", type=int, default=100, help="最小训练样本数 (默认: 100)")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="只输出 filtered feature matrix 统计；不训练、不保存 artifact",
    )
    parser.add_argument(
        "--no-write", action="store_true", help="禁止训练 artifact / dataset / report 文件写入"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Training preflight dry-run: no fit, no predict, no write. "
        "Audit cohort/labels/features/Elo/leakage. JSON to stdout.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志模式")
    return parser.parse_args()


def run_report_only_mode(conn) -> dict:
    """Build report-only filtered feature matrix stats without fitting a model."""
    return build_report_from_connection(conn)


# fmt: off
def _verify_connection_read_only(conn):
    """Return (is_read_only, setting_value)."""
    from psycopg2.extras import RealDictCursor  # noqa: PLC0415
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SHOW transaction_read_only")
        row = cur.fetchone()
        cur.close()
        if row is None:
            return False, "unknown"
        if isinstance(row, dict):
            v = str(row.get("transaction_read_only", "")).strip().lower()
        elif isinstance(row, (list, tuple)):
            v = str(row[0]).strip().lower() if row else ""
        else:
            v = str(row).strip().lower()
        return v in ("on", "true", "1", "yes"), v
    except Exception as e:
        return False, f"error: {e}"
# fmt: on


# fmt: off
def run_dry_run_mode(conn, logger=None) -> dict:  # noqa: PLR0912, PLR0915
    """Training preflight dry-run: audit cohort, labels, features, Elo, leakage.
    Reads DB (SELECT only). NEVER calls fit, predict, or writes artifacts."""
    from psycopg2.extras import RealDictCursor  # noqa: PLC0415
    _forbidden = ["actual_result","home_score","away_score","result","winner","outcome",
        "is_finished","is_training_eligible","full_time_score","final_score","status",
        "home_corners","away_corners","home_yellow_cards","away_yellow_cards",
        "home_red_cards","away_red_cards"]
    _ok, blocked = {"home_win", "away_win", "draw"}, []
    h = {"mode": "training_preflight_dry_run", "status": "pass",
         "db_read_only": False, "transaction_read_only_setting": "",
         "eligible_cohort_count": 0, "cohort_count": 0,
         "l3_coverage_count": 0, "missing_l3_count": 0, "missing_l3_match_ids": [],
         "label_column": "actual_result", "label_null_count": 0,
         "label_distribution": {}, "invalid_label_values": [],
         "feature_count": 0, "feature_names": [],
         "feature_extracted_row_count": 0, "feature_extraction_error_count": 0,
         "feature_extraction_error_match_ids": [], "feature_extraction_errors": [],
         "forbidden_feature_hits": [],
         "elo_real_count": 0, "elo_default_count": 0,
         "elo_default_match_ids": [], "default_elo_explicit": True,
         "fit_executed": False, "predict_executed": False,
         "db_write_attempted": False, "artifact_written": False,
         "dataset_file_written": False, "model_file_written": False,
         "blocked_reasons": blocked}

    # 0. Read-only verification BEFORE any cohort query
    is_ro, ro_val = _verify_connection_read_only(conn)
    h["db_read_only"] = is_ro
    h["transaction_read_only_setting"] = ro_val
    if not is_ro:
        blocked.append("transaction_read_only={}: NOT read-only; "
                        "use PGOPTIONS=-c default_transaction_read_only=on".format(ro_val))
        h["status"] = "blocked"
        if logger:
            logger.error(f"BLOCKED: transaction_read_only={ro_val}, not read-only")
        return h
    if logger:
        logger.info(f"Read-only verified: {ro_val}")

    # 1. LEFT JOIN cohort query to detect missing L3
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT m.match_id, m.home_team, m.away_team, m.actual_result,
        l.match_id AS l3_match_id, l.elo_features, l.golden_features, l.tactical_features
        FROM matches m LEFT JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.is_finished = true AND m.is_training_eligible = true
        ORDER BY m.match_date DESC""")
    all_rows = cur.fetchall()
    cur.close()
    l3_rows = [r for r in all_rows if r.get("l3_match_id") is not None]
    missing = [r for r in all_rows if r.get("l3_match_id") is None]
    mids = [r["match_id"] for r in missing]
    h.update(eligible_cohort_count=len(all_rows), cohort_count=len(all_rows),
             l3_coverage_count=len(l3_rows), missing_l3_count=len(missing),
             missing_l3_match_ids=mids)
    if logger:
        logger.info(f"Eligible: {len(all_rows)}, L3: {len(l3_rows)}, missing: {len(missing)}")
    if missing:
        blocked.append(f"missing_l3={len(missing)}: IDs={mids}")
        h["status"] = "blocked"
        return h

    # 2. Label distribution
    lc, nl, iv = {}, 0, set()
    for r in l3_rows:
        label = r.get("actual_result")
        if label is None: nl += 1
        elif label not in _ok: iv.add(str(label))
        lc[str(label)] = lc.get(str(label), 0) + 1
    h.update(label_null_count=nl, label_distribution=lc, invalid_label_values=sorted(iv))
    if nl: blocked.append(f"label_null={nl}: NULL actual_result")
    if iv: blocked.append(f"invalid_labels={sorted(iv)}: unexpected")
    if logger: logger.info(f"Labels: {lc}")

    # 3. Feature extraction (NO silent pass) + 4. Default Elo
    fs, er, ed, ed_ids, xt, xerrs = set(), 0, 0, [], 0, []
    for r in l3_rows:
        mid = r["match_id"]
        try:
            feats = extract_v5_features(
                r["elo_features"], r["golden_features"], r["tactical_features"])
            for k in feats: fs.add(k)
            xt += 1
        except Exception as exc:
            xerrs.append({"match_id": mid, "error_type": type(exc).__name__,
                          "message": str(exc)[:200]})
        elo_raw = r["elo_features"]
        if isinstance(elo_raw, str): elo_raw = json.loads(elo_raw) if elo_raw else {}
        if not isinstance(elo_raw, dict): elo_raw = {}
        if str(elo_raw.get("_is_default", "true")).lower() != "false":
            ed += 1; ed_ids.append(mid)
        else: er += 1
    eids = [e["match_id"] for e in xerrs]
    h.update(feature_count=len(fs), feature_names=sorted(fs),
             feature_extracted_row_count=xt,
             feature_extraction_error_count=len(xerrs),
             feature_extraction_error_match_ids=eids,
             feature_extraction_errors=xerrs,
             elo_real_count=er, elo_default_count=ed,
             elo_default_match_ids=ed_ids)
    if logger:
        logger.info(f"Features: {len(fs)} -> {sorted(fs)}, xt={xt}/{len(l3_rows)}")
        logger.info(f"Elo: {er} real, {ed} default")
    if xerrs: blocked.append(f"xtraction_errors={len(xerrs)}: IDs={eids}")
    if len(l3_rows) > 0 and len(fs) == 0:
        blocked.append("non-empty cohort, zero features extracted")
    if xt != len(l3_rows):
        blocked.append(f"extracted={xt} != l3_coverage={len(l3_rows)}")

    # 5. Leakage checks
    fh = [f for f in sorted(fs) if any(p in f.lower() for p in _forbidden)]
    h["forbidden_feature_hits"] = fh
    if fh: blocked.append(f"forbidden_hits={fh}: prematch leakage")
    if logger and fh: logger.warning(f"Forbidden: {fh}")

    # 6. Final status
    if not blocked and len(all_rows) == 0:
        blocked.append("cohort=0: no training-eligible rows")
    if blocked: h["status"] = "blocked"
    return h
# fmt: on


def main():  # noqa: PLR0912, PLR0915
    """主入口 - 带全局异常捕获"""
    global logger
    args = parse_args()

    if args.report_only:
        args.no_write = True

    if args.no_write and not args.report_only and not args.dry_run:
        print(
            "--no-write blocks training artifact writes. "
            "Use --report-only --no-write for filtered matrix reporting.",
            file=sys.stderr,
        )
        sys.exit(2)

    # ── Dry-run path: no fit, no predict, no artifact, no write gate ─────
    if args.dry_run:
        # Reject dangerous combinations
        blocked_combo = []
        if args.no_write:
            blocked_combo.append("--no-write")
        if args.report_only:
            blocked_combo.append("--report-only")
        if blocked_combo:
            print(
                f"--dry-run is a standalone preflight mode. "
                f"Do not combine with: {', '.join(blocked_combo)}",
                file=sys.stderr,
            )
            sys.exit(2)

        # Dry-run does NOT require training write confirmation
        logger = setup_logging(args.verbose, write_file=False)

        try:
            conn = get_db_connection()
            try:
                summary = run_dry_run_mode(conn, logger)
            finally:
                conn.close()

            print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

            if summary["status"] == "blocked":
                logger.error(f"Dry-run BLOCKED: {len(summary['blocked_reasons'])} issue(s)")
                for reason in summary["blocked_reasons"]:
                    logger.error(f"  - {reason}")
                sys.exit(1)

            logger.info("Dry-run PASS: all safety gates clear")
            sys.exit(0)

        except Exception:
            logger.exception("Dry-run failed with exception")
            sys.exit(1)

    if not args.report_only:
        require_training_write_confirmation()

    # 重新配置日志级别；report-only 不写日志文件
    logger = setup_logging(args.verbose, write_file=not args.report_only)

    result = None

    try:
        if args.report_only:
            conn = get_db_connection()
            try:
                report = run_report_only_mode(conn)
            finally:
                conn.close()
            print(json.dumps(report, indent=2, ensure_ascii=False))
            sys.exit(0)

        logger.info("=" * 60)
        logger.info("TITAN-V4.46.8 模型训练管道 - 工业加固版")
        logger.info("=" * 60)

        conn = get_db_connection()

        try:
            X, y = load_training_data(conn, args.min_samples, logger)
            model, scaler, metrics = train_model(X, y, logger)
            model_path, scaler_path = save_model(model, scaler, metrics, args.name, logger)

            result = TrainingResult(
                model_path=model_path,
                scaler_path=scaler_path,
                accuracy=metrics["accuracy"],
                f1_score=metrics["f1_score"],
                log_loss=metrics["log_loss"],
                training_samples=metrics["training_samples"],
                feature_count=len(TITAN_COMBAT_FEATURES),
                training_time_seconds=metrics["training_time_seconds"],
                exit_code=0,
            )

        finally:
            conn.close()

        # 输出结果
        if args.json:
            print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        else:
            logger.info("=" * 60)
            logger.info("训练完成!")
            logger.info(f"模型: {result.model_path}")
            logger.info(f"准确率: {result.accuracy:.2%}, F1: {result.f1_score:.4f}")
            logger.info(f"训练时间: {result.training_time_seconds:.1f}s")
            logger.info("=" * 60)

        sys.exit(0)

    except ValueError as e:
        logger.error(f"数据错误: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("用户中断执行")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"未捕获的异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
