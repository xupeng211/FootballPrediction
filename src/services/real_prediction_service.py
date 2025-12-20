"""
真实预测服务 - Phase 4 集成

基于训练好的 baseline_v2_real.json 模型，提供真实比赛预测服务。
复用 PostgresDataLoader 获取比赛数据并应用相同的特征工程。
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import pandas as pd
from xgboost import XGBClassifier

from src.ml.data.postgres_loader import PostgresDataLoader

# 配置日志
logger = logging.getLogger(__name__)


class RealPredictionService:
    """
    真实预测服务

    基于训练好的 XGBoost 模型，为具体比赛提供预测概率。
    复用训练时的特征工程逻辑确保数据一致性。
    """

    def __init__(self, model_path: str = None):
        """
        初始化预测服务

        Args:
            model_path: 模型文件路径，默认使用训练好的模型
        """
        self.model = None
        self.feature_names = []
        self.data_loader = None
        self.model_loaded = False

        # 默认模型路径
        if model_path is None:
            project_root = Path(__file__).parent.parent.parent
            model_path = project_root / "scripts" / "models" / "baseline_v2_real.json"

        self.model_path = Path(model_path)

        logger.info(f"RealPredictionService 初始化完成，模型路径: {self.model_path}")

    async def load_model(self) -> bool:
        """
        加载训练好的模型

        Returns:
            bool: 加载是否成功
        """
        try:
            if not self.model_path.exists():
                logger.error(f"模型文件不存在: {self.model_path}")
                return False

            # 加载XGBoost模型
            self.model = XGBClassifier()
            self.model.load_model(str(self.model_path))

            # 加载特征信息
            info_path = str(self.model_path).replace(".json", "_info.json")
            if Path(info_path).exists():
                with open(info_path, "r", encoding="utf-8") as f:
                    model_info = json.load(f)
                    self.feature_names = model_info.get("feature_names", [])

            self.model_loaded = True

            logger.info(f"✅ 模型加载成功: {self.model_path}")
            logger.info(f"📋 特征数量: {len(self.feature_names)}")
            logger.info(f"📋 特征列表: {self.feature_names}")

            return True

        except Exception as e:
            logger.error(f"❌ 模型加载失败: {str(e)}")
            return False

    async def initialize(self) -> bool:
        """
        初始化服务（加载数据加载器和模型）

        Returns:
            bool: 初始化是否成功
        """
        # 初始化数据加载器
        self.data_loader = PostgresDataLoader(
            selected_columns=[
                "home_team_id",
                "away_team_id",
                "home_score",
                "away_score",
                "match_date",
                "status",
                "home_team_name",
                "away_team_name",
                "league_id",
            ]
        )

        # 加载模型
        return await self.load_model()

    async def get_match_data(self, match_id: int) -> Optional[pd.DataFrame]:
        """
        获取特定比赛的数据

        Args:
            match_id: 比赛ID

        Returns:
            pd.DataFrame: 比赛数据，如果未找到则返回None
        """
        try:
            # 修改数据加载器以获取特定比赛 - 使用参数化查询防止SQL注入
            query = """
                SELECT
                    id,
                    home_team_id,
                    away_team_id,
                    home_score,
                    away_score,
                    match_date,
                    status,
                    COALESCE(home_team_name, home_team_id::text) as home_team_name,
                    COALESCE(away_team_name, away_team_id::text) as away_team_name,
                    league_id
                FROM matches
                WHERE id = :match_id AND status = 'FT'
            """

            async with self.data_loader.db_manager.get_async_session() as session:
                from sqlalchemy import text

                result = await session.execute(text(query), {"match_id": match_id})
                records = result.fetchall()

                if not records:
                    logger.warning(f"未找到比赛ID {match_id} 的数据")
                    return None

                # 转换为DataFrame
                data = [dict(record._mapping) for record in records]
                df = pd.DataFrame(data)

                # 数据类型转换
                df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
                numeric_cols = [
                    "home_team_id",
                    "away_team_id",
                    "home_score",
                    "away_score",
                    "league_id",
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

                logger.info(f"✅ 获取比赛数据成功: ID {match_id}")
                return df

        except Exception as e:
            logger.error(f"❌ 获取比赛数据失败: {str(e)}")
            return None

    def create_features_for_prediction(self, match_data: pd.DataFrame, historical_data: pd.DataFrame) -> pd.DataFrame:
        """
        为预测创建特征

        Args:
            match_data: 当前比赛数据
            historical_data: 历史数据用于计算滚动特征

        Returns:
            pd.DataFrame: 包含特征的DataFrame
        """
        # 合并历史数据和当前比赛
        combined_data = pd.concat([historical_data, match_data], ignore_index=True)
        combined_data = combined_data.sort_values(["home_team_id", "match_date"])

        # 创建滚动特征（与训练时相同）
        combined_data["home_score_rolling_3"] = combined_data.groupby("home_team_id")["home_score"].transform(
            lambda x: x.rolling(3, min_periods=1).mean().shift(1)
        )

        combined_data["home_score_rolling_5"] = combined_data.groupby("home_team_id")["home_score"].transform(
            lambda x: x.rolling(5, min_periods=1).mean().shift(1)
        )

        combined_data = combined_data.sort_values(["away_team_id", "match_date"])

        combined_data["away_score_rolling_3"] = combined_data.groupby("away_team_id")["away_score"].transform(
            lambda x: x.rolling(3, min_periods=1).mean().shift(1)
        )

        combined_data["away_score_rolling_5"] = combined_data.groupby("away_team_id")["away_score"].transform(
            lambda x: x.rolling(5, min_periods=1).mean().shift(1)
        )

        # 提取当前比赛的特征（最后一行）
        current_match_features = combined_data.iloc[-1:].copy()

        return current_match_features

    async def predict_match(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        预测特定比赛的结果

        Args:
            match_id: 比赛ID

        Returns:
            dict: 预测结果，包含概率和比赛信息
        """
        if not self.model_loaded:
            logger.error("模型未加载，请先调用 initialize()")
            return None

        try:
            # 1. 获取当前比赛数据
            match_data = await self.get_match_data(match_id)
            if match_data is None or match_data.empty:
                return None

            match_info = match_data.iloc[0]
            logger.info(f"🏆 比赛: {match_info['home_team_name']} vs {match_info['away_team_name']}")
            logger.info(f"📅 日期: {match_info['match_date']}")
            logger.info(f"⚽ 真实比分: {match_info['home_score']} - {match_info['away_score']}")

            # 2. 获取历史数据用于计算滚动特征
            logger.info("📊 加载历史数据用于特征计算...")
            historical_data = await self.data_loader.load_data(limit=2000)

            if historical_data.empty:
                logger.error("无法加载历史数据")
                return None

            # 3. 创建特征
            logger.info("⚙️ 创建预测特征...")
            features_df = self.create_features_for_prediction(match_data, historical_data)

            # 4. 选择模型需要的特征
            required_features = [
                "home_score_rolling_3",
                "home_score_rolling_5",
                "away_score_rolling_3",
                "away_score_rolling_5",
                "home_team_id",
                "away_team_id",
                "league_id",
            ]

            available_features = [f for f in required_features if f in features_df.columns]

            if not available_features:
                logger.error("没有可用的特征进行预测")
                return None

            X = features_df[available_features]

            # 5. 进行预测
            logger.info("🔮 执行模型预测...")
            prediction_proba = self.model.predict_proba(X)[0]
            prediction_class = self.model.predict(X)[0]

            # 解析概率
            probabilities = {
                "away_win": float(prediction_proba[0]),  # 客队获胜概率
                "home_win": float(prediction_proba[1]),  # 主队获胜概率
            }

            # 6. 确定真实结果
            home_score = int(match_info["home_score"])
            away_score = int(match_info["away_score"])
            if home_score > away_score:
                actual_result = "home_win"
            elif away_score > home_score:
                actual_result = "away_win"
            else:
                actual_result = "draw"

            # 7. 构建返回结果
            result = {
                "match_id": match_id,
                "match_info": {
                    "home_team": match_info["home_team_name"],
                    "away_team": match_info["away_team_name"],
                    "home_team_id": int(match_info["home_team_id"]),
                    "away_team_id": int(match_info["away_team_id"]),
                    "match_date": str(match_info["match_date"]),
                    "actual_score": f"{home_score}-{away_score}",
                    "actual_result": actual_result,
                },
                "prediction": {
                    "predicted_class": ("home_win" if prediction_class == 1 else "away_win"),
                    "home_win_probability": probabilities["home_win"],
                    "away_win_probability": probabilities["away_win"],
                    "confidence": max(probabilities.values()),
                },
                "features_used": available_features,
                "feature_values": {col: float(X[col].iloc[0]) for col in available_features},
            }

            logger.info("🎯 预测完成:")
            logger.info(f"   主队获胜概率: {probabilities['home_win']:.2%}")
            logger.info(f"   客队获胜概率: {probabilities['away_win']:.2%}")
            logger.info(f"   预测结果: {result['prediction']['predicted_class']}")
            logger.info(f"   实际结果: {actual_result}")

            return result

        except Exception as e:
            logger.error(f"❌ 预测失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    async def predict_batch(self, match_ids: List[int]) -> List[Dict[str, Any]]:
        """
        批量预测多场比赛

        Args:
            match_ids: 比赛ID列表

        Returns:
            List[dict]: 预测结果列表
        """
        results = []
        for match_id in match_ids:
            result = await self.predict_match(match_id)
            if result:
                results.append(result)
            else:
                logger.warning(f"比赛 {match_id} 预测失败")

        return results

    async def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "model_loaded": self.model_loaded,
            "model_path": str(self.model_path),
            "feature_names": self.feature_names,
            "model_type": "XGBClassifier" if self.model_loaded else None,
        }
