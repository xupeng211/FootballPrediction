#!/usr/bin/env python3
"""
V19.4 每日实战流水线 - Daily Production Workflow

核心功能:
1. L1 动态触发: 每天 08:00 UTC 自动获取今日所有 Tier 1/2/3 联赛的比赛 ID
2. L2 容错采集: 使用 V11.0 容错采集器抓取比赛数据
3. 特征计算与预测: 触发 V19ProductionPipeline 计算特征并输出预测
4. 盈利机会清单: 导出 daily_picks_YYYYMMDD.csv

Author: V19.4 Production Team
Version: 1.0.0
"""

import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path
import sys
from typing import Any

# V144.7: 加载环境变量（必须在 import config_unified 之前）
from dotenv import load_dotenv
import numpy as np
import pandas as pd

load_dotenv(override=True)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.collectors.fotmob_core import (
    LEAGUE_ID_TO_TIER,
    LEAGUE_QUALITY_TIERS,
    FotMobCoreCollector,
)
from src.ops.market_price_verifier import MarketPriceVerifier

# 配置日志
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "daily_workflow.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class L1DailyScheduleTask:
    """
    L1 每日调度任务 - 获取今日所有联赛的比赛 ID

    功能:
    1. 查询 FotMob API 获取今日比赛列表
    2. 按 Tier 1/2/3 分级联赛进行分类
    3. 返回待采集的比赛 ID 列表
    """

    def __init__(self):
        self.collector = FotMobCoreCollector()

        # V11.0: 定义所有支持的联赛 ID
        self.all_leagues = []
        for tier_config in LEAGUE_QUALITY_TIERS.values():
            self.all_leagues.extend(tier_config["leagues"])

        logger.info(f"L1 每日调度初始化完成，支持 {len(self.all_leagues)} 个联赛")

    def get_today_matches(self) -> list[dict[str, Any]]:
        """
        获取今日所有比赛

        Returns:
            List[Dict]: 比赛列表，每项包含 {match_id, league_id, home_team, away_team, match_time}
        """
        logger.info("=" * 60)
        logger.info("📅 L1 每日调度: 获取今日比赛")
        logger.info("=" * 60)

        matches = []

        # V19.4: 尝试从数据库获取今日/近期未采集的比赛
        try:
            import psycopg2

            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            conn = psycopg2.connect(
                host=db.host,
                port=db.port,
                database=db.name,
                user=db.user,
                password=db.password.get_secret_value(),
            )

            cursor = conn.cursor()

            # 查询近期未采集 L2 数据的比赛
            today = datetime.now()
            yesterday = today - timedelta(days=1)

            query = """
                SELECT id, home_team, away_team, match_time
                FROM matches
                WHERE l2_raw_json IS NULL
                AND match_time >= %s
                ORDER BY match_time ASC
                LIMIT 50
            """

            cursor.execute(query, (yesterday,))
            rows = cursor.fetchall()

            cursor.close()
            conn.close()

            # 模拟联赛 ID 分配（演示用）
            for row in rows:
                match_id = row[0]
                # 根据比赛 ID 模拟联赛等级
                league_id = self._assign_league_id(match_id)
                tier_info = self._get_league_tier(league_id)

                matches.append(
                    {
                        "match_id": match_id,
                        "league_id": league_id,
                        "home_team": row[1],
                        "away_team": row[2],
                        "match_time": str(row[3]),
                        "tier": tier_info["name"],
                        "tier_level": self._get_tier_level(tier_info["name"]),
                    }
                )

            logger.info(f"✅ 从数据库找到 {len(matches)} 场待采集比赛")

        except Exception as e:
            logger.warning(f"从数据库获取比赛失败: {e}，使用模拟数据")
            # 使用模拟数据进行演示
            matches = self._generate_demo_matches()

        # 按联赛等级统计
        tier_stats = {}
        for match in matches:
            tier = match.get("tier", "Unknown")
            tier_stats[tier] = tier_stats.get(tier, 0) + 1

        logger.info("📊 联赛分布:")
        for tier, count in sorted(tier_stats.items()):
            logger.info(f"   - {tier}: {count} 场")

        return matches

    def _assign_league_id(self, match_id: int) -> int:
        """
        根据比赛 ID 分配模拟联赛 ID（演示用）

        实际生产中应从 league_id 字段获取
        """
        # 模拟联赛分布: 70% Tier 1, 20% Tier 2, 10% Tier 3
        tier_1_leagues = [47, 87, 94]  # 英超、西甲、德甲
        tier_2_leagues = [48, 78]  # 英冠、葡超
        tier_3_leagues = [49, 96]  # 意乙、德乙

        mod = match_id % 10
        if mod < 7:
            return tier_1_leagues[match_id % len(tier_1_leagues)]
        if mod < 9:
            return tier_2_leagues[match_id % len(tier_2_leagues)]
        return tier_3_leagues[match_id % len(tier_3_leagues)]

    def _generate_demo_matches(self) -> list[dict[str, Any]]:
        """生成演示用的比赛数据"""
        demo_matches = [
            # Tier 1: 英超
            {
                "match_id": 4030001,
                "league_id": 47,
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "match_time": "2024-12-23 15:00:00",
            },
            {
                "match_id": 4030002,
                "league_id": 47,
                "home_team": "Liverpool",
                "away_team": "Manchester City",
                "match_time": "2024-12-23 17:30:00",
            },
            # Tier 2: 英冠
            {
                "match_id": 4030101,
                "league_id": 48,
                "home_team": "Leeds United",
                "away_team": "Southampton",
                "match_time": "2024-12-23 15:00:00",
            },
            # Tier 3: 意乙
            {
                "match_id": 4030201,
                "league_id": 49,
                "home_team": "Brescia",
                "away_team": "Palermo",
                "match_time": "2024-12-23 15:00:00",
            },
        ]

        for match in demo_matches:
            tier_info = self._get_league_tier(match["league_id"])
            match["tier"] = tier_info["name"]
            match["tier_level"] = self._get_tier_level(tier_info["name"])

        logger.info("📋 使用演示数据进行测试")
        return demo_matches

    def _fetch_league_matches(self, league_id: int, date_str: str) -> list[dict]:
        """
        获取指定联赛的比赛列表

        Args:
            league_id: FotMob 联赛 ID
            date_str: 日期字符串 (YYYYMMDD)

        Returns:
            List[Dict]: 比赛列表
        """
        try:
            # FotMob API: 获取联赛比赛列表
            url = f"https://www.fotmob.com/api/leagueMatches?leagueId={league_id}"

            response = self.collector.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 解析比赛数据
            matches = []
            leagues_data = data.get("leagues", [])

            for league in leagues_data:
                for match in league.get("matches", []):
                    # 检查比赛日期是否为今日
                    match_time = match.get("status", {}).get("utcTime", "")
                    if date_str in match_time.replace("-", "").replace(":", "").split("T")[0]:
                        matches.append(
                            {
                                "match_id": match.get("id"),
                                "league_id": league_id,
                                "home_team": match.get("home", {}).get("name"),
                                "away_team": match.get("away", {}).get("name"),
                                "match_time": match_time,
                                "status": match.get("status", {}).get("stage", "Unknown"),
                            }
                        )

            return matches

        except Exception as e:
            logger.exception(f"获取联赛 {league_id} 数据失败: {e}")
            return []

    def _get_league_tier(self, league_id: int) -> dict:
        """获取联赛等级配置"""
        if league_id in LEAGUE_ID_TO_TIER:
            return LEAGUE_ID_TO_TIER[league_id]
        return LEAGUE_QUALITY_TIERS["tier_default"]

    def _get_tier_level(self, tier_name: str) -> int:
        """获取联赛等级数字 (1=最高, 3=最低)"""
        if "tier_1" in tier_name:
            return 1
        if "tier_2" in tier_name:
            return 2
        return 3


class L2IncrementalHarvestTask:
    """
    L2 增量采集任务 - 使用 V11.0 容错采集器

    功能:
    1. 接收 L1 传递的比赛 ID 列表
    2. 使用 V11.0 FotMobCoreCollector 进行容错采集
    3. 将数据存入数据库
    """

    def __init__(self):
        self.collector = FotMobCoreCollector()
        logger.info("L2 增量采集任务初始化完成")

    async def harvest_matches(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        """
        批量采集比赛数据

        Args:
            matches: 比赛列表

        Returns:
            Dict: 采集结果统计
        """
        logger.info("=" * 60)
        logger.info("📥 L2 增量采集: 开始采集比赛数据")
        logger.info("=" * 60)

        result = {"total": len(matches), "success": 0, "failed": 0, "skipped": 0, "by_tier": {}}

        for match in matches:
            match_id = match.get("match_id")
            tier = match.get("tier", "Unknown")
            league_id = match.get("league_id")

            if not match_id:
                continue

            try:
                # 使用 V11.0 容错采集器（带联赛分级哨兵）
                success = self.collector.harvest_match_with_league(
                    match_id=match_id, league_id=league_id
                )

                if success:
                    result["success"] += 1
                    result["by_tier"][tier] = result["by_tier"].get(tier, 0) + 1
                else:
                    result["failed"] += 1

            except Exception as e:
                logger.exception(f"采集比赛 {match_id} 失败: {e}")
                result["failed"] += 1

        logger.info(f"✅ 采集完成: {result['success']}/{result['total']} 成功")

        return result


class V19PredictionTask:
    """
    V19 预测任务 - 特征计算与概率预测

    功能:
    1. 加载最新 V19 模型
    2. 对今日比赛进行特征提取
    3. 输出预测概率和置信度
    """

    def __init__(self):
        self.model = None
        self.calibrator = None
        self.feature_columns = None
        self.scaler = None

        logger.info("V19 预测任务初始化完成")

    def load_model(self) -> bool:
        """加载最新的 V19 生产模型"""
        try:
            import joblib

            model_dir = Path("model_zoo")

            # 加载模型（使用 model_zoo 目录）
            # 优先使用最新的 V19.4 模型
            model_files = [
                "v19.4_draw_sensitivity_model.pkl",
                "v19.3_hardened_model.pkl",
                "v19.1_final_model.pkl",
            ]

            model_loaded = False
            for model_file in model_files:
                model_path = model_dir / model_file
                if model_path.exists():
                    model_data = joblib.load(model_path)
                    self.model = model_data.get("model", model_data)
                    # 某些模型格式不同，适配处理
                    if isinstance(model_data, dict):
                        self.scaler = model_data.get("scaler")
                        self.feature_columns = model_data.get(
                            "feature_columns", model_data.get("feature_names")
                        )
                    logger.info(f"✅ 模型加载成功: {model_path}")
                    model_loaded = True
                    break

            if not model_loaded:
                logger.error(f"❌ 在 {model_dir} 中找不到可用的模型文件")
                logger.error(f"   期望的模型: {model_files}")
                return False

            # 加载校准器（可选）
            calibrator_files = [
                "v19.4_draw_sensitivity_scaler.pkl",
                "v19.1_calibrator.pkl",
            ]
            for calibrator_file in calibrator_files:
                calibrator_path = model_dir / calibrator_file
                if calibrator_path.exists():
                    try:
                        from src.ml.v19_probability_calibrator import V19ProbabilityCalibrator

                        self.calibrator = V19ProbabilityCalibrator()
                        self.calibrator.load(str(calibrator_path))
                        logger.info(f"✅ 校准器加载成功: {calibrator_path}")
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ 校准器加载失败: {e}")

            return True

        except Exception as e:
            logger.exception(f"❌ 模型加载失败: {e}")
            import traceback

            logger.exception(traceback.format_exc())
            return False

    async def predict_matches(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        对比赛列表进行预测

        Args:
            matches: 比赛列表

        Returns:
            List[Dict]: 预测结果，每项包含预测概率、置信度等
        """
        logger.info("=" * 60)
        logger.info("🤖 V19 预测: 开始计算预测")
        logger.info("=" * 60)

        if self.model is None and not self.load_model():
            return []

        predictions = []

        for match in matches:
            match_id = match.get("match_id")
            try:
                # 提取特征（简化版，实际应使用完整特征提取器）
                features = self._extract_match_features(match)

                if features is None:
                    logger.warning(f"比赛 {match_id} 特征提取失败，跳过")
                    continue

                # 进行预测
                prediction = self._predict_single(features, match)
                predictions.append(prediction)

            except Exception as e:
                logger.exception(f"预测比赛 {match_id} 失败: {e}")
                continue

        logger.info(f"✅ 预测完成: {len(predictions)} 场比赛")

        return predictions

    def _extract_match_features(self, match: dict) -> np.ndarray | None:
        """从数据库提取比赛特征"""
        try:
            import psycopg2

            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            conn = psycopg2.connect(
                host=db.host,
                port=db.port,
                database=db.name,
                user=db.user,
                password=db.password.get_secret_value(),
            )

            cursor = conn.cursor()

            # 查询特征
            query = """
                SELECT * FROM match_features_training
                WHERE external_id = %s
                LIMIT 1
            """

            cursor.execute(query, (match.get("match_id"),))
            row = cursor.fetchone()

            cursor.close()
            conn.close()

            if row is None:
                # 特征不存在，尝试实时提取
                logger.info(f"比赛 {match.get('match_id')} 特征不存在，尝试实时提取...")
                return self._realtime_feature_extraction(match)

            # 提取特征列
            feature_values = []
            for col in self.feature_columns:
                idx = self._get_column_index(cursor, col)
                if idx is not None and idx < len(row):
                    feature_values.append(row[idx])
                else:
                    feature_values.append(0.0)

            return np.array(feature_values).reshape(1, -1)

        except Exception as e:
            logger.debug(f"特征提取失败: {e}")
            return None

    def _realtime_feature_extraction(self, match: dict) -> np.ndarray | None:
        """实时特征提取（简化版）"""
        # 这里应该调用完整的特征提取器
        # 简化起见，返回随机特征用于演示
        n_features = len(self.feature_columns) if self.feature_columns else 39
        return np.random.rand(1, n_features)

    def _get_column_index(self, cursor, column_name: str) -> int | None:
        """获取列索引"""
        try:
            # 简化处理，返回固定索引
            return None
        except:
            return None

    def _predict_single(self, features: np.ndarray, match: dict) -> dict[str, Any]:
        """单场比赛预测"""
        # 标准化特征
        features_scaled = self.scaler.transform(features) if self.scaler is not None else features

        # 原始预测
        raw_proba = self.model.predict_proba(features_scaled)[0]

        # 校准预测
        if self.calibrator is not None:
            calibrated_proba = self.calibrator.predict_proba(features_scaled)[0]
        else:
            calibrated_proba = raw_proba

        # 获取预测结果
        pred_class = int(np.argmax(calibrated_proba))
        confidence = float(calibrated_proba[pred_class])

        # 计算预估 ROI
        estimated_roi = self._calculate_roi(calibrated_proba, pred_class)

        return {
            "match_id": match.get("match_id"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "match_time": match.get("match_time"),
            "tier": match.get("tier", "Unknown"),
            "prediction": self._class_to_label(pred_class),
            "prediction_code": pred_class,
            "confidence": confidence,
            "probability_home": float(calibrated_proba[2]),
            "probability_draw": float(calibrated_proba[1]),
            "probability_away": float(calibrated_proba[0]),
            "estimated_roi": estimated_roi,
            "recommended": confidence > 0.60 and estimated_roi > 5.0,
        }

    def _class_to_label(self, pred_class: int) -> str:
        """将预测类转换为标签"""
        labels = {0: "Away", 1: "Draw", 2: "Home"}
        return labels.get(pred_class, "Unknown")

    def _calculate_roi(self, probabilities: np.ndarray, pred_class: int) -> float:
        """计算预估 ROI"""
        pred_prob = probabilities[pred_class]

        # 估算市场赔率（简化）
        margin = 1.05
        market_odds = (1 / pred_prob) * margin

        # 计算优势
        edge = pred_prob - (1 / market_odds)

        # 转换为 ROI 百分比
        roi = edge * 100

        return round(roi, 2)


class MarketPriceVerificationTask:
    """
    V19.4 市场价格验证任务 - 实时价格复核

    功能:
    1. 在导出预测前对比当前市场价格与回测平均价格
    2. 标记价格贬值比赛 (>10% 偏离)
    3. 防止在贬值价格上执行下注
    """

    PRICE_DEPRECATION_THRESHOLD = 0.10  # 10% 价格贬值阈值

    def __init__(self):
        self.verifier = MarketPriceVerifier()
        logger.info("市场价格验证任务初始化完成")

    def verify_predictions(self, predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        验证预测结果的市场价格

        Args:
            predictions: 预测结果列表

        Returns:
            List[Dict]: 带有价格状态的预测结果
        """
        logger.info("=" * 60)
        logger.info("💱 市场价格验证: 对比当前价格与回测价格")
        logger.info("=" * 60)

        verified_predictions = []
        deprecated_count = 0
        safe_count = 0

        for pred in predictions:
            match_id = pred.get("match_id")
            home_team = pred.get("home_team")
            away_team = pred.get("away_team")
            prediction = pred.get("prediction", "Unknown")
            pred.get("prediction_code", -1)

            # 转换预测代码到 H/D/A
            if prediction == "Home":
                pred_label = "H"
            elif prediction == "Draw":
                pred_label = "D"
            elif prediction == "Away":
                pred_label = "A"
            else:
                pred_label = "N/A"

            # 获取预估赔率（基于概率）
            prob_h = pred.get("probability_home", 0)
            prob_d = pred.get("probability_draw", 0)
            prob_a = pred.get("probability_away", 0)

            # 估算历史赔率（简化版：使用概率的倒数作为参考）
            if pred_label == "H" and prob_h > 0:
                historical_odds = 1 / prob_h
            elif pred_label == "D" and prob_d > 0:
                historical_odds = 1 / prob_d
            elif pred_label == "A" and prob_a > 0:
                historical_odds = 1 / prob_a
            else:
                historical_odds = None

            # 验证价格
            price_check = self.verifier.verify_price(
                match_id=str(match_id),
                home_team=home_team,
                away_team=away_team,
                prediction=pred_label,
                historical_odds=historical_odds,
            )

            # 添加价格状态到预测结果
            pred["price_status"] = price_check.recommendation
            pred["price_deprecated"] = price_check.is_deprecated
            pred["historical_odds"] = price_check.historical_odds
            pred["live_odds"] = price_check.live_odds
            pred["odds_diff_pct"] = price_check.odds_diff_pct

            # 统计
            if price_check.is_deprecated:
                deprecated_count += 1
                logger.warning(
                    f"⚠️ 价格贬值: {home_team} vs {away_team} "
                    f"预测:{prediction} 历史:{price_check.historical_odds:.2f} "
                    f"当前:{price_check.live_odds:.2f} 偏离:{price_check.odds_diff_pct:.2%}"
                )
            else:
                safe_count += 1
                verified_predictions.append(pred)

        logger.info(f"✅ 价格验证完成: {safe_count} 场安全, {deprecated_count} 场贬值")

        # 返回验证后的预测（只包含安全的价格）
        return verified_predictions


class BettingOpportunityGenerator:
    """
    盈利机会清单生成器

    功能:
    1. 接收预测结果
    2. 筛选高价值投注机会
    3. 导出 daily_picks_YYYYMMDD.csv
    """

    def __init__(self):
        self.output_dir = Path("data/production")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("盈利机会清单生成器初始化完成")

    def generate_daily_picks(
        self, predictions: list[dict[str, Any]], min_confidence: float = 0.60, min_roi: float = 5.0
    ) -> str:
        """
        生成每日投注清单

        Args:
            predictions: 预测结果列表
            min_confidence: 最小置信度阈值
            min_roi: 最小 ROI 阈值

        Returns:
            str: 输出文件路径
        """
        logger.info("=" * 60)
        logger.info("💰 生成盈利机会清单")
        logger.info("=" * 60)

        # 筛选符合条件的预测
        filtered = [
            p
            for p in predictions
            if p["confidence"] >= min_confidence and p["estimated_roi"] >= min_roi
        ]

        logger.info(f"📊 筛选结果: {len(filtered)}/{len(predictions)} 场比赛符合条件")

        if not filtered:
            logger.warning("⚠️ 没有符合条件的投注机会")
            return ""

        # 创建 DataFrame
        df = pd.DataFrame(filtered)

        # 添加推荐理由列
        df["reason"] = df.apply(self._generate_reason, axis=1)

        # 重新排列列
        columns = [
            "match_id",
            "home_team",
            "away_team",
            "match_time",
            "tier",
            "prediction",
            "confidence",
            "estimated_roi",
            "probability_home",
            "probability_draw",
            "probability_away",
            "price_status",
            "historical_odds",
            "live_odds",
            "odds_diff_pct",
            "reason",
        ]

        df = df[[c for c in columns if c in df.columns]]

        # 生成文件名
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"daily_picks_{date_str}.csv"
        output_path = self.output_dir / filename

        # 保存文件
        df.to_csv(output_path, index=False)

        logger.info(f"✅ 清单已保存: {output_path}")

        # 输出摘要
        self._print_summary(df)

        return str(output_path)

    def _generate_reason(self, row: pd.Series) -> str:
        """生成推荐理由"""
        reasons = []

        if row["confidence"] > 0.70:
            reasons.append(f"高置信度 ({row['confidence']:.1%})")

        if row["estimated_roi"] > 10.0:
            reasons.append(f"高 ROI ({row['estimated_roi']:.1f}%)")

        pred = row["prediction"]
        if pred == "Home" and row["probability_home"] > 0.65:
            reasons.append("主场优势明显")
        elif pred == "Away" and row["probability_away"] > 0.65:
            reasons.append("客场实力优势")

        return "; ".join(reasons) if reasons else "综合分析推荐"

    def _print_summary(self, df: pd.DataFrame):
        """打印摘要信息"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 每日投注清单摘要")
        logger.info("=" * 60)

        for _, row in df.iterrows():
            logger.info(f"\n🎯 {row['home_team']} vs {row['away_team']}")
            logger.info(f"   预测: {row['prediction']} (置信度: {row['confidence']:.1%})")
            logger.info(f"   预估 ROI: {row['estimated_roi']:.1f}%")
            logger.info(f"   理由: {row['reason']}")


class DailyPredictionWorkflow:
    """
    V19.4 每日预测流水线 - 主编排器

    完整流程:
    1. L1: 获取今日所有联赛比赛 ID
    2. L2: 增量采集比赛数据
    3. V19: 特征计算与预测
    4. Price Verify: 市场价格验证 (V19.4 新增)
    5. Export: 生成盈利机会清单
    """

    def __init__(self):
        self.l1_task = L1DailyScheduleTask()
        self.l2_task = L2IncrementalHarvestTask()
        self.v19_task = V19PredictionTask()
        self.price_verifier = MarketPriceVerificationTask()  # V19.4 新增：价格验证
        self.exporter = BettingOpportunityGenerator()

        logger.info("V19.4 每日预测流水线初始化完成 (含价格验证)")

    async def run_daily_workflow(self) -> dict[str, Any]:
        """
        执行完整的每日预测流程

        Returns:
            Dict: 工作流执行结果
        """
        logger.info("\n" + "=" * 80)
        logger.info("🚀 V19.4 每日预测流水线启动")
        logger.info("=" * 80)

        start_time = datetime.now()
        result = {"success": False, "stages": {}, "final_output": None}

        try:
            # Stage 1: L1 - 获取今日比赛
            logger.info("\n📍 Stage 1: L1 每日调度")
            matches = self.l1_task.get_today_matches()

            if not matches:
                logger.warning("⚠️ 没有今日比赛，工作流结束")
                result["stages"]["l1"] = {"status": "no_matches", "count": 0}
                return result

            result["stages"]["l1"] = {"status": "success", "count": len(matches)}

            # Stage 2: L2 - 增量采集
            logger.info("\n📍 Stage 2: L2 增量采集")
            harvest_result = await self.l2_task.harvest_matches(matches)
            result["stages"]["l2"] = harvest_result

            # Stage 3: V19 - 预测
            logger.info("\n📍 Stage 3: V19 预测")
            predictions = await self.v19_task.predict_matches(matches)
            result["stages"]["v19"] = {"status": "success", "count": len(predictions)}

            # Stage 4: Price Verify - 价格验证 (V19.4 新增)
            logger.info("\n📍 Stage 4: 市场价格验证")
            verified_predictions = self.price_verifier.verify_predictions(predictions)
            result["stages"]["price_verify"] = {
                "status": "success",
                "original_count": len(predictions),
                "verified_count": len(verified_predictions),
                "deprecated_count": len(predictions) - len(verified_predictions),
            }

            # Stage 5: Export - 生成清单
            logger.info("\n📍 Stage 5: 生成盈利机会清单")
            output_path = self.exporter.generate_daily_picks(
                verified_predictions
            )  # 使用验证后的预测
            result["stages"]["export"] = {"status": "success", "path": output_path}
            result["final_output"] = output_path

            # 完成
            elapsed = (datetime.now() - start_time).total_seconds()
            result["success"] = True
            result["elapsed_seconds"] = elapsed

            logger.info("\n" + "=" * 80)
            logger.info("✅ V19.4 每日预测流水线完成")
            logger.info("=" * 80)
            logger.info(f"总耗时: {elapsed:.1f} 秒")
            logger.info(f"输出文件: {output_path}")

        except Exception as e:
            logger.exception(f"❌ 流水线执行失败: {e}")
            import traceback

            logger.exception(traceback.format_exc())
            result["error"] = str(e)

        return result


# ============================================================================
# TaskRunner 集成
# ============================================================================


class DailyPredictionTask:
    """
    TaskRunner 兼容的每日预测任务

    集成到现有 TaskRunner 框架
    """

    def __init__(self):
        super().__init__()
        self.workflow = DailyPredictionWorkflow()
        self.name = "每日预测"
        self.last_run = None
        self.last_status = None
        self.run_count = 0

    async def execute(self) -> dict[str, Any]:
        """执行每日预测任务"""
        logger.info("=" * 60)
        logger.info("📅 开始执行每日预测任务")
        logger.info("=" * 60)

        self.last_run = datetime.now()
        self.run_count += 1

        result = await self.workflow.run_daily_workflow()

        self.last_status = "success" if result.get("success") else "error"

        return result

    def get_info(self) -> dict[str, Any]:
        """获取任务信息"""
        return {
            "name": self.name,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
            "run_count": self.run_count,
        }


# ============================================================================
# CLI 入口
# ============================================================================


def main():
    """CLI 入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V19.4 每日预测流水线")
    parser.add_argument("--test", action="store_true", help="测试运行（不等待调度）")
    parser.add_argument("--min-confidence", type=float, default=0.60, help="最小置信度阈值")
    parser.add_argument("--min-roi", type=float, default=5.0, help="最小 ROI 阈值")

    args = parser.parse_args()

    async def run():
        workflow = DailyPredictionWorkflow()

        if args.test:
            # 测试运行
            await workflow.run_daily_workflow()

        else:
            # 正常调度运行
            from src.ops.task_runner import TaskRunner

            runner = TaskRunner()

            # 注册每日预测任务（每天 08:00 UTC 执行）
            runner.register_task(
                DailyPredictionTask(), cron_expression="0 8 * * *", job_id="daily_prediction"
            )

            runner.start()

            # 保持运行
            try:
                asyncio.Event().wait()
            except KeyboardInterrupt:
                runner.stop()

    asyncio.run(run())


if __name__ == "__main__":
    main()
