#!/usr/bin/env python3
"""
足球预测自动化管道 / Football Prediction Automated Pipeline

该脚本自动执行完整的数据处理流程：
1. 数据同步：从外部API获取最新比赛数据
2. 数据清洗：ETL过程将数据写入Silver层
3. 特征更新：重新计算特征生成训练数据集
4. 模型重训：使用最新数据重新训练XGBoost模型
5. 预测未来：对未来7天的比赛进行预测

This script automates the complete data processing pipeline:
1. Data Sync: Fetch latest match data from external APIs
2. Data Cleaning: ETL process to write data to Silver layer
3. Feature Update: Recalculate features to generate training dataset
4. Model Retrain: Retrain XGBoost model with latest data
5. Future Predictions: Predict matches for the next 7 days

使用方法 / Usage:
    python scripts/daily_pipeline.py

定时任务设置 / Cron Setup:
    # 每天凌晨3点运行
    0 3 * * * /usr/bin/python3 /path/to/FootballPrediction/scripts/daily_pipeline.py >> /path/to/logs/pipeline.log 2>&1
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        break

# 导入项目模块
try:
    import pandas as pd
    import numpy as np
    import xgboost as xgb
    import json
    from src.data.collectors.fixtures_collector import FixturesCollector
    from src.data.processing.football_data_cleaner import FootballDataCleaner
    from src.features.simple_feature_calculator import SimpleFeatureCalculator
    from src.database.async_manager import get_db_session, initialize_database
    from src.database.models.raw_data import RawMatchData
    from src.database.models.match import Match
    from sqlalchemy import select
except ImportError:
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [PIPELINE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DailyPipeline:
    """每日自动化管道."""

    def __init__(self):
        """初始化管道."""
        self.start_time = datetime.now()
        self.pipeline_steps = 5
        self.current_step = 0
        self.errors = []

    def _get_target_seasons(self) -> list[int]:
        """
        获取目标赛季列表.

        根据当前日期智能判断当前赛季和上一赛季：
        - 足球赛季通常跨年，从8月开始到次年5月结束
        - 如果当前月份 >= 7，当前赛季 = 当前年份
        - 如果当前月份 < 7，当前赛季 = 去年年份
        - 返回 [当前赛季, 上一赛季] 以保证数据完整性

        Returns:
            list[int]: 目标赛季列表 [current_season, previous_season]
        """
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year

        # 判断当前赛季
        if current_month >= 7:
            # 7月及以后，当前赛季 = 当前年份
            current_season = current_year
        else:
            # 6月及以前，当前赛季 = 去年年份
            current_season = current_year - 1

        # 计算上一赛季
        previous_season = current_season - 1

        target_seasons = [current_season, previous_season]

        logger.info("🗓️  智能赛季判断:")
        logger.info(f"    当前日期: {current_date.strftime('%Y-%m-%d')}")
        logger.info(f"    当前赛季: {current_season}")
        logger.info(f"    上一赛季: {previous_season}")
        logger.info(f"    目标赛季列表: {target_seasons}")

        return target_seasons

    def log_step(self, step_name: str, status: str = "START"):
        """记录管道步骤.

        Args:
            step_name: 步骤名称
            status: 状态 (START/COMPLETED/FAILED)
        """
        if status == "START":
            self.current_step += 1
            logger.info(
                f"[{self.current_step}/{self.pipeline_steps}] {step_name} - 开始"
            )
        elif status == "COMPLETED":
            logger.info(
                f"[{self.current_step}/{self.pipeline_steps}] {step_name} - ✅ 完成"
            )
        elif status == "FAILED":
            logger.error(
                f"[{self.current_step}/{self.pipeline_steps}] {step_name} - ❌ 失败"
            )

    async def step_1_data_sync(self) -> bool:
        """步骤1：数据同步 - 获取最新比赛数据（支持多赛季智能采集）."""
        step_name = "数据同步 (Data Sync)"
        self.log_step(step_name, "START")

        try:
            # 初始化数据库连接
            initialize_database()
            logger.info("数据库连接初始化成功")

            # 获取目标赛季列表
            target_seasons = self._get_target_seasons()

            # 创建数据采集器
            collector = FixturesCollector(data_source="football_api")

            # 定义目标联赛
            target_leagues = [
                "PL",
                "PD",
                "BL1",
                "SA",
                "FL1",
            ]  # 欧洲五大联赛：英超、西甲、德甲、意甲、法甲

            total_records_collected = 0
            total_success = 0
            total_errors = 0

            logger.info(f"🏆 开始多赛季数据采集，目标联赛: {target_leagues}")
            logger.info(f"📅 目标赛季: {target_seasons}")

            # 遍历每个赛季进行采集
            for season in target_seasons:
                logger.info(f"🔄 正在采集 {season} 赛季数据...")

                try:
                    # 采集当前赛季的所有联赛数据
                    season_result = await collector.collect_fixtures(
                        leagues=target_leagues, season=season
                    )

                    if season_result.success:
                        season_records = season_result.data.get("records_collected", 0)
                        total_records_collected += season_records
                        total_success += 1

                        logger.info(
                            f"✅ {season} 赛季数据采集成功，收集到 {season_records} 条记录"
                        )

                        # 如果有详细的联赛统计信息，也记录下来
                        if "league_stats" in season_result.data:
                            league_stats = season_result.data["league_stats"]
                            logger.info(f"📊 {season} 赛季联赛统计:")
                            for league, stats in league_stats.items():
                                logger.info(f"    - {league}: {stats}")
                    else:
                        total_errors += 1
                        error_msg = season_result.error or "未知错误"
                        logger.error(f"❌ {season} 赛季数据采集失败: {error_msg}")
                        self.errors.append(f"{season}赛季数据采集失败: {error_msg}")

                except Exception:
                    total_errors += 1
                    logger.error(f"❌ {season} 赛季数据采集异常: {e}")
                    self.errors.append(f"{season}赛季数据采集异常: {str(e)}")

            # 评估整体采集结果
            logger.info("=" * 60)
            logger.info("📊 多赛季采集统计摘要")
            logger.info("=" * 60)
            logger.info(f"🎯 目标赛季数: {len(target_seasons)}")
            logger.info(f"✅ 成功采集赛季数: {total_success}")
            logger.info(f"❌ 失败采集赛季数: {total_errors}")
            logger.info(f"📄 总记录收集数: {total_records_collected}")

            # 判断整体是否成功
            if total_success > 0:
                self.log_step(step_name, "COMPLETED")
                logger.info(f"数据同步成功，共采集到 {total_records_collected} 条记录")
                return True
            else:
                self.log_step(step_name, "FAILED")
                self.errors.append("所有赛季数据采集均失败")
                return False

        except Exception:
            self.log_step(step_name, "FAILED")
            error_msg = str(e)
            self.errors.append(f"数据同步异常: {error_msg}")
            logger.error(f"数据同步异常: {e}")
            return False

    async def step_2_data_cleaning(self) -> bool:
        """步骤2：数据清洗 - ETL到Silver层."""
        step_name = "数据清洗 (ETL)"
        self.log_step(step_name, "START")

        try:
            # 这里复用ETL脚本的逻辑
            from scripts.run_etl_silver import SilverETLProcessor

            processor = SilverETLProcessor()
            success = await processor.run_etl()

            if success:
                self.log_step(step_name, "COMPLETED")
                logger.info("数据清洗完成，数据已写入Silver层")
                return True
            else:
                self.log_step(step_name, "FAILED")
                self.errors.append("数据清洗失败")
                return False

        except Exception:
            self.log_step(step_name, "FAILED")
            error_msg = str(e)
            self.errors.append(f"数据清洗异常: {error_msg}")
            logger.error(f"数据清洗异常: {e}")
            return False

    def step_3_feature_generation(self) -> bool:
        """步骤3：特征生成 - 更新特征数据集."""
        step_name = "特征生成 (Feature Generation)"
        self.log_step(step_name, "START")

        try:
            # 从数据库加载Silver层数据
            logger.info("从Silver层数据库加载比赛数据...")

            import psycopg2

            # 优先读取环境变量 DATABASE_URL
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                # 回退逻辑：使用单独的环境变量
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "football_prediction_2024")
                db_host = os.getenv("DB_HOST", "db")  # Docker里是 db，不是localhost
                db_port = os.getenv("DB_PORT", "5432")
                db_name = os.getenv("POSTGRES_DB", "football_prediction")
                db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            # Pandas 需要同步驱动，移除 asyncpg
            if "+asyncpg" in db_url:
                db_url = db_url.replace("+asyncpg", "")

            conn = psycopg2.connect(db_url)
            query = """
            SELECT
                m.id as match_id,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                m.status,
                m.match_date,
                t1.name as home_team_name,
                t2.name as away_team_name
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            ORDER BY m.match_date ASC
            """

            matches_df = pd.read_sql_query(query, conn)
            conn.close()

            logger.info(f"加载了 {len(matches_df)} 条比赛记录")

            # 生成特征
            calculator = SimpleFeatureCalculator(matches_df)
            features_df = calculator.generate_features_dataset()

            # 保存特征数据
            features_df.to_csv("data/dataset_v1.csv", index=False)

            self.log_step(step_name, "COMPLETED")
            logger.info(f"特征生成完成，生成 {len(features_df)} 条特征记录")
            return True

        except Exception:
            self.log_step(step_name, "FAILED")
            error_msg = str(e)
            self.errors.append(f"特征生成异常: {error_msg}")
            logger.error(f"特征生成异常: {e}")
            return False

    def step_4_model_training(self) -> bool:
        """步骤4：模型训练 - 重训XGBoost模型."""
        step_name = "模型训练 (Model Training)"
        self.log_step(step_name, "START")

        try:
            # 加载特征数据
            df = pd.read_csv("data/dataset_v1.csv")
            df["match_date"] = pd.to_datetime(df["match_date"])
            df = df.sort_values("match_date").reset_index(drop=True)

            # 定义特征列（包含新的高级特征）
            feature_columns = [
                # 基础特征
                "home_team_id",
                "away_team_id",
                "home_last_5_points",
                "away_last_5_points",
                "home_last_5_avg_goals",
                "away_last_5_avg_goals",
                "h2h_last_3_home_wins",
                # 高级特征 - 体能、实力、士气
                "home_last_5_goal_diff",
                "away_last_5_goal_diff",
                "home_win_streak",
                "away_win_streak",
                "home_last_5_win_rate",
                "away_last_5_win_rate",
                "home_rest_days",
                "away_rest_days",
            ]

            # 准备数据
            X = df[feature_columns].copy()
            y = df["match_result"].copy()

            # 时间序列切分
            split_point = int(len(X) * 0.8)
            X_train = X[:split_point]
            X_test = X[split_point:]
            y_train = y[:split_point]
            y_test = y[split_point:]

            # 训练XGBoost模型
            params = {
                "objective": "multi:softmax",
                "num_class": 3,
                "max_depth": 6,
                "learning_rate": 0.1,
                "n_estimators": 100,
                "random_state": 42,
                "eval_metric": "mlogloss",
                "use_label_encoder": False,
            }

            model = xgb.XGBClassifier(**params)
            model.fit(X_train, y_train)

            # 评估模型
            y_pred = model.predict(X_test)
            accuracy = (y_pred == y_test).mean()

            # 保存模型
            os.makedirs("models", exist_ok=True)
            model.save_model("models/football_model_v1.json")

            # 保存元数据
            import json

            metadata = {
                "model_version": "v1",
                "training_date": datetime.now().isoformat(),
                "feature_names": feature_columns,
                "target_classes": ["平局", "主队胜", "客队胜"],
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "test_accuracy": float(accuracy),
                "num_features": len(feature_columns),
            }

            with open(
                "models/football_model_v1_metadata.json", "w", encoding="utf-8"
            ) as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            self.log_step(step_name, "COMPLETED")
            logger.info(
                f"模型训练完成，测试准确率: {accuracy:.4f} ({accuracy * 100:.2f}%)"
            )
            return True

        except Exception:
            self.log_step(step_name, "FAILED")
            error_msg = str(e)
            self.errors.append(f"模型训练异常: {error_msg}")
            logger.error(f"模型训练异常: {e}")
            return False

    def step_5_predict_future(self) -> bool:
        """步骤5：未来预测 - 预测未来7天的比赛."""
        step_name = "未来预测 (Future Predictions)"
        self.log_step(step_name, "START")

        try:
            # 加载模型
            model = xgb.XGBClassifier()
            model.load_model("models/football_model_v1.json")

            # 加载元数据
            with open("models/football_model_v1_metadata.json", encoding="utf-8") as f:
                metadata = json.load(f)

            feature_names = metadata["feature_names"]
            result_names = {0: "平局", 1: "主队胜", 2: "客队胜"}

            # 从数据库获取未来比赛
            import psycopg2

            db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", 5432)),
                "database": os.getenv("DB_NAME", "football_prediction"),
                "user": os.getenv("DB_USER", "postgres"),
                "password": os.getenv("DB_PASSWORD", "postgres-dev-password"),
            }

            conn = psycopg2.connect(**db_config)

            # 查询未来7天内的比赛
            now = datetime.now()
            future_date = now + timedelta(days=7)

            query = """
            SELECT
                m.id,
                m.home_team_id,
                m.away_team_id,
                m.match_date,
                m.status,
                t1.name as home_team_name,
                t2.name as away_team_name,
                COALESCE(m.home_score, 0) as home_score,
                COALESCE(m.away_score, 0) as away_score
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE m.match_date >= %s AND m.match_date <= %s AND m.status != 'FINISHED'
            ORDER BY m.match_date ASC
            """

            future_matches_df = pd.read_sql_query(
                query, conn, params=[now, future_date]
            )
            conn.close()

            if len(future_matches_df) == 0:
                logger.info("⚠️  未找到未来7天内的比赛")
                logger.info("可能原因:")
                logger.info("  1. 当前赛季已结束")
                logger.info("  2. 数据库中未安排未来比赛")
                logger.info("  3. 所有未来比赛已完成或取消")
                self.log_step(step_name, "COMPLETED")
                return True

            # 为未来比赛生成特征
            # 需要从历史数据计算特征
            all_matches_df = pd.read_csv("data/dataset_v1.csv")
            all_matches_df["match_date"] = pd.to_datetime(all_matches_df["match_date"])

            # 合并历史数据和未来比赛数据
            combined_df = pd.concat(
                [
                    all_matches_df[["home_team_id", "away_team_id", "match_date"]],
                    future_matches_df[["home_team_id", "away_team_id", "match_date"]],
                ],
                ignore_index=True,
            )
            combined_df = combined_df.sort_values("match_date").reset_index(drop=True)

            # 计算特征
            calculator = SimpleFeatureCalculator(all_matches_df)

            # 为每场未来比赛计算特征
            future_features = []
            for _, match in future_matches_df.iterrows():
                try:
                    # 使用calculated方法计算特征
                    match.to_dict()

                    # 计算主队近期战绩
                    home_points, home_avg_goals = (
                        calculator.calculate_team_recent_stats(
                            match["home_team_id"], match["match_date"]
                        )
                    )

                    # 计算客队近期战绩
                    away_points, away_avg_goals = (
                        calculator.calculate_team_recent_stats(
                            match["away_team_id"], match["match_date"]
                        )
                    )

                    # 计算历史交锋
                    h2h_wins = calculator.calculate_h2h_stats(
                        match["home_team_id"],
                        match["away_team_id"],
                        match["match_date"],
                    )

                    features = {
                        "home_team_id": match["home_team_id"],
                        "away_team_id": match["away_team_id"],
                        "home_last_5_points": home_points,
                        "away_last_5_points": away_points,
                        "home_last_5_avg_goals": home_avg_goals,
                        "away_last_5_avg_goals": away_avg_goals,
                        "h2h_last_3_home_wins": h2h_wins,
                        "match_date": match["match_date"],
                        "home_team_name": match["home_team_name"],
                        "away_team_name": match["away_team_name"],
                    }
                    future_features.append(features)

                except Exception:
                    logger.warning(f"计算比赛 {match['id']} 特征失败: {e}")
                    continue

            if len(future_features) == 0:
                logger.warning("⚠️  无法为未来比赛计算特征")
                self.log_step(step_name, "COMPLETED")
                return True

            # 进行预测
            features_df = pd.DataFrame(future_features)
            X_future = features_df[feature_names]
            predictions = model.predict(X_future)
            probabilities = model.predict_proba(X_future)

            # 输出预测结果
            logger.info("=" * 60)
            logger.info("🔮 未来比赛预测结果")
            logger.info("=" * 60)

            for i, (_, match) in enumerate(future_matches_df.iterrows()):
                pred = predictions[i]
                probs = probabilities[i]

                match_date = match["match_date"].strftime("%Y-%m-%d")
                home_team = match["home_team_name"]
                away_team = match["away_team_name"]

                logger.info(f"[{match_date}] {home_team} (主) vs {away_team} (客)")
                logger.info(f"预测: {result_names[pred]}")
                logger.info(
                    f"概率: 平局 {probs[0]:.1%} | 主胜 {probs[1]:.1%} | 客胜 {probs[2]:.1%}"
                )
                logger.info("-" * 50)

            logger.info(f"📊 共预测 {len(future_features)} 场未来比赛")

            self.log_step(step_name, "COMPLETED")
            return True

        except Exception:
            self.log_step(step_name, "FAILED")
            error_msg = str(e)
            self.errors.append(f"未来预测异常: {error_msg}")
            logger.error(f"未来预测异常: {e}")
            return False

    async def run(self) -> bool:
        """运行完整的管道流程.

        Returns:
            bool: 管道是否成功完成
        """
        logger.info("=" * 60)
        logger.info("🚀 足球预测自动化管道启动")
        logger.info(f"⏰ 启动时间: {self.start_time}")
        logger.info("=" * 60)

        try:
            # 执行管道步骤
            step1_success = await self.step_1_data_sync()
            if not step1_success:
                logger.error("❌ 管道在步骤 1 失败")
                logger.error(f"错误列表: {self.errors}")
                return False

            step2_success = await self.step_2_data_cleaning()
            if not step2_success:
                logger.error("❌ 管道在步骤 2 失败")
                logger.error(f"错误列表: {self.errors}")
                return False

            step3_success = self.step_3_feature_generation()
            if not step3_success:
                logger.error("❌ 管道在步骤 3 失败")
                logger.error(f"错误列表: {self.errors}")
                return False

            step4_success = self.step_4_model_training()
            if not step4_success:
                logger.error("❌ 管道在步骤 4 失败")
                logger.error(f"错误列表: {self.errors}")
                return False

            step5_success = self.step_5_predict_future()
            if not step5_success:
                logger.error("❌ 管道在步骤 5 失败")
                logger.error(f"错误列表: {self.errors}")
                return False

            # 计算总耗时
            end_time = datetime.now()
            duration = end_time - self.start_time

            logger.info("=" * 60)
            logger.info("🎉 管道执行完成！")
            logger.info(f"⏱️  总耗时: {duration}")
            logger.info(f"✅ 成功执行所有 {self.pipeline_steps} 个步骤")
            logger.info("=" * 60)

            return True

        except Exception:
            logger.error(f"💥 管道执行异常: {e}")
            self.errors.append(f"管道异常: {str(e)}")
            return False


async def main():
    """主函数."""
    logger.info("🏈 足球预测自动化管道启动")

    try:
        pipeline = DailyPipeline()
        success = await pipeline.run()

        if success:
            logger.info("✅ 管道执行成功！")
            sys.exit(0)
        else:
            logger.error("❌ 管道执行失败！")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，管道停止")
        sys.exit(1)
    except Exception:
        logger.error(f"💥 管道异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
