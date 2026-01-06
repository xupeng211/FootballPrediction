#!/usr/bin/env python3
"""
英超赛季全量收割脚本 - V7.0 固化版
目标: 收割 380 场英超 2024/2025 赛季比赛数据
静默收割模式：随机延迟 1-3 秒防止 IP 被封
"""

from datetime import UTC, datetime
import json
import logging
import os
import random
import sys
import time
from typing import Any

from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# Add src to path
sys.path.insert(0, "/home/user/projects/FootballPrediction/src")

from data_access.processors.bulletproof_feature_extractor import BulletproofFeatureExtractor

# Setup logging
log_dir = "/home/user/projects/FootballPrediction/logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(f"{log_dir}/season_reharvest.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理类 - 使用统一配置系统"""

    def __init__(self):
        self.conn = None
        self.db_available = False
        # 使用统一配置系统
        try:
            self._connect_from_config()
            self.db_available = True
        except Exception as e:
            logger.warning(f"⚠️ 数据库不可用，仅保存到 CSV: {e}")
            self.db_available = False

    def _connect_from_config(self):
        """使用统一配置系统连接数据库"""
        try:
            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            self.conn = psycopg2.connect(
                host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
            )
            logger.info(f"✅ 数据库连接成功: {db.host}:{db.port}/{db.name}")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def _connect(self):
        """连接数据库（向后兼容）"""
        # 已在 __init__ 中处理

    def create_database(self):
        """创建数据库（如果不存在）"""
        try:
            # Connect to default postgres database
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "db"),
                port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "football_user"),
                password=os.getenv("DB_PASSWORD", "football_pass"),
            )
            conn.autocommit = True
            cur = conn.cursor()

            # Create database
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (os.getenv("DB_NAME", "football_db"),))
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {os.getenv('DB_NAME', 'football_db')} OWNER football_user")
                logger.info("✅ 数据库创建成功")
            else:
                logger.info("ℹ️ 数据库已存在")

            cur.close()
            conn.close()

            # Reconnect to the new database
            self._connect()
            return True
        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            return False

    def create_tables(self):
        """创建表结构"""
        try:
            with self.conn.cursor() as cur:
                # Check if table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'match_features_training'
                    );
                """)
                table_exists = cur.fetchone()[0]

                if not table_exists:
                    # Create base table
                    logger.info("📦 创建基础表结构...")
                    cur.execute("""
                        CREATE TABLE match_features_training (
                            id SERIAL PRIMARY KEY,
                            external_id VARCHAR(50) NOT NULL UNIQUE,
                            match_time TIMESTAMP WITH TIME ZONE NOT NULL,
                            home_team VARCHAR(100) NOT NULL,
                            away_team VARCHAR(100) NOT NULL,

                            -- 基础特征
                            home_possession REAL,
                            away_possession REAL,
                            home_total_shots INTEGER,
                            away_total_shots INTEGER,
                            home_xg REAL,
                            away_xg REAL,
                            home_corners INTEGER,
                            away_corners INTEGER,
                            home_shots_on_target INTEGER,
                            away_shots_on_target INTEGER,
                            home_avg_rating REAL,
                            away_avg_rating REAL,

                            -- 事件特征
                            home_red_cards INTEGER DEFAULT 0,
                            away_red_cards INTEGER DEFAULT 0,
                            home_substitutions INTEGER DEFAULT 0,
                            away_substitutions INTEGER DEFAULT 0,
                            home_early_goal INTEGER DEFAULT 0,
                            away_early_goal INTEGER DEFAULT 0,
                            home_penalties INTEGER DEFAULT 0,
                            away_penalties INTEGER DEFAULT 0,

                            -- 衍生特征
                            home_xg_per_shot REAL,
                            away_xg_per_shot REAL,
                            rating_diff REAL,

                            -- 元数据
                            league_id VARCHAR(50) DEFAULT '47',
                            league_name VARCHAR(100) DEFAULT 'Premier League',
                            is_real_data BOOLEAN DEFAULT TRUE,
                            feature_version VARCHAR(20) DEFAULT 'v7.0',
                            data_source VARCHAR(50) DEFAULT 'harvested',
                            extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)

                    # Create indexes
                    cur.execute("CREATE INDEX idx_match_features_external_id ON match_features_training(external_id);")
                    cur.execute("CREATE INDEX idx_match_features_match_time ON match_features_training(match_time);")
                    cur.execute("CREATE INDEX idx_match_features_league ON match_features_training(league_id);")

                    logger.info("✅ 表结构创建成功")
                else:
                    logger.info("ℹ️ 表已存在，跳过创建")

                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ 创建表失败: {e}")
            self.conn.rollback()
            return False

    def truncate_table(self):
        """清空表数据"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE match_features_training RESTART IDENTITY CASCADE;")
                self.conn.commit()
                logger.info("✅ 表数据已清空")
                return True
        except Exception as e:
            logger.error(f"❌ 清空表失败: {e}")
            return False

    def insert_match_features(self, features: dict[str, Any]) -> bool:
        """插入比赛特征数据"""
        try:
            with self.conn.cursor() as cur:
                # Prepare insert/update query
                columns = list(features.keys())
                placeholders = ", ".join(["%s"] * len(columns))
                columns_str = ", ".join(columns)

                # ON CONFLICT clause for upsert
                update_cols = [f"{col} = EXCLUDED.{col}" for col in columns if col != "external_id"]
                conflict_cols = "external_id"

                query = f"""
                    INSERT INTO match_features_training ({columns_str})
                    VALUES ({placeholders})
                    ON CONFLICT ({conflict_cols}) DO UPDATE SET
                        {", ".join(update_cols)},
                        updated_at = NOW()
                    RETURNING id;
                """

                cur.execute(query, list(features.values()))
                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ 插入数据失败: {e}")
            self.conn.rollback()
            return False

    def get_data_quality_report(self, limit: int = 5) -> list[dict]:
        """获取数据质量报告"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        external_id,
                        home_team,
                        away_team,
                        match_time,
                        home_xg,
                        away_xg,
                        home_possession,
                        home_total_shots,
                        home_red_cards,
                        away_red_cards,
                        home_substitutions,
                        away_substitutions,
                        rating_diff,
                        home_xg_per_shot,
                        away_xg_per_shot,
                        extracted_at
                    FROM match_features_training
                    ORDER BY match_time ASC
                    LIMIT %s;
                """
                cur.execute(query, (limit,))
                results = cur.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ 获取数据质量报告失败: {e}")
            return []

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("🔒 数据库连接已关闭")


class SeasonReharvester:
    """赛季收割器 - 静默收割模式"""

    def __init__(self):
        self.feature_extractor = BulletproofFeatureExtractor()
        self.db = DatabaseManager()
        self.league_id = "47"  # 英超联赛ID
        self.season = "2024/2025"
        self.base_url = "https://www.fotmob.com/api"
        self.session = requests.Session()
        # 设置 UA 伪装
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        # 收割数据存储
        self.harvested_data = []
        self.failed_matches = []

    def get_season_matches(self) -> list[dict]:
        """获取赛季所有比赛"""
        try:
            logger.info(f"🔍 获取英超 {self.season} 赛季比赛列表...")

            # 使用 FotMob API 获取联赛比赛
            url = f"{self.base_url}/leagues"
            params = {"id": self.league_id, "tab": "results"}

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 提取比赛数据 - 正确路径：fixtures.allMatches
            fixtures = data.get("fixtures", {})
            matches_data = fixtures.get("allMatches", []) or []

            if not matches_data:
                logger.warning("⚠️ 未获取到比赛数据")
                return []

            # 过滤已完成的比赛
            matches = []
            for match in matches_data:
                match_id = match.get("id")
                status = match.get("status", {})

                if match_id and isinstance(status, dict):
                    finished = status.get("finished", False)

                    if finished:
                        matches.append(
                            {
                                "match_id": str(match_id),
                                "home_team": match.get("home", {}).get("name", "Unknown"),
                                "away_team": match.get("away", {}).get("name", "Unknown"),
                                "status": "finished",
                            }
                        )

            logger.info(f"✅ 获取到 {len(matches)} 场已完成的比赛")
            return matches
        except Exception as e:
            logger.error(f"❌ 获取比赛列表失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return []

    def harvest_match(self, match_id: str) -> dict[str, Any] | None:
        """收割单场比赛 - 静默模式"""
        try:
            # Get match data from FotMob API
            url = f"{self.base_url}/matchDetails"
            params = {"matchId": match_id}

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()

            match_data = response.json()

            if not match_data:
                logger.warning(f"⚠️ 比赛 {match_id} 无数据")
                return None

            # Extract features using BulletproofFeatureExtractor
            features = self.feature_extractor.extract(match_data)

            # Add metadata
            features["external_id"] = match_id
            features["league_id"] = self.league_id
            features["league_name"] = "Premier League"
            features["is_real_data"] = True
            features["feature_version"] = "v7.0"
            features["data_source"] = "fotmob_api"

            # Ensure required fields
            if "match_time" not in features:
                features["match_time"] = datetime.now(UTC)

            # Store in memory
            self.harvested_data.append(features)

            return features

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API 请求失败 - 比赛 {match_id}: {e}")
            self.failed_matches.append({"match_id": match_id, "error": str(e), "timestamp": datetime.now().isoformat()})
            return None
        except Exception as e:
            logger.error(f"❌ 收割比赛 {match_id} 失败: {e}")
            self.failed_matches.append({"match_id": match_id, "error": str(e), "timestamp": datetime.now().isoformat()})
            return None

    def save_harvested_data(self):
        """保存收割的数据到 CSV 文件"""
        if not self.harvested_data:
            logger.warning("⚠️ 没有收割数据可保存")
            return False

        try:
            # 创建 DataFrame
            df = pd.DataFrame(self.harvested_data)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/home/user/projects/FootballPrediction/data/harvested_matches_v7_{timestamp}.csv"

            # 保存到 CSV
            df.to_csv(filename, index=False)

            logger.info(f"✅ 收割数据已保存到: {filename}")
            logger.info(f"  总计: {len(df)} 场比赛")
            logger.info(f"  特征数量: {df.shape[1]}")

            # 同时保存到 final_v7_solid_features.csv（覆盖原文件）
            final_filename = "/home/user/projects/FootballPrediction/data/final_v7_solid_features.csv"
            df.to_csv(final_filename, index=False)
            logger.info(f"✅ 已更新 final_v7_solid_features.csv: {len(df)} 场比赛")

            # 保存失败列表
            if self.failed_matches:
                failed_filename = f"/home/user/projects/FootballPrediction/data/failed_matches_{timestamp}.json"
                with open(failed_filename, "w") as f:
                    json.dump(self.failed_matches, f, indent=2)
                logger.info(f"⚠️ 失败列表已保存到: {failed_filename} ({len(self.failed_matches)} 场)")

            return True

        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}")
            return False

    def run(self):
        """运行收割流程"""
        try:
            # Step 1: Setup database (if available)
            logger.info("=" * 60)
            logger.info("🚀 开始英超赛季全量收割 - V7.0")
            logger.info("=" * 60)

            if self.db.db_available:
                try:
                    self.db.create_database()
                    self.db.create_tables()
                    self.db.truncate_table()
                except Exception as e:
                    logger.warning(f"⚠️ 数据库设置失败，跳过数据库操作: {e}")
            else:
                logger.info("ℹ️ 跳过数据库设置，仅保存到 CSV")

            # Step 2: Get matches
            matches = self.get_season_matches()

            if not matches:
                logger.error("❌ 没有找到比赛数据")
                return

            # Step 3: Harvest matches - 静默全量收割
            total_matches = len(matches)
            success_count = 0
            failure_count = 0

            logger.info(f"📊 开始静默全量收割 {total_matches} 场比赛...")
            logger.info("🔇 静默模式: 随机延迟 1-3 秒，防止 IP 被封")
            logger.info("-" * 60)

            for i, match in enumerate(matches, 1):
                match_id = match["match_id"]
                home_team = match["home_team"]
                away_team = match["away_team"]

                logger.info(f"[{i}/{total_matches}] 收割中: {home_team} vs {away_team}")

                # Harvest features
                features = self.harvest_match(match_id)

                if features:
                    success_count += 1
                    logger.info(f"  ✅ 成功 (累计: {success_count})")

                    # 保存到数据库（可选）
                    if self.db.db_available:
                        try:
                            self.db.insert_match_features(features)
                        except Exception as e:
                            logger.warning(f"  ⚠️ 数据库插入失败: {e}")
                else:
                    failure_count += 1
                    logger.warning(f"  ❌ 收割失败 (累计失败: {failure_count})")

                # Progress report every 50 matches
                if i % 50 == 0:
                    logger.info("=" * 60)
                    logger.info(f"📊 进度报告: {i}/{total_matches} ({i / total_matches * 100:.1f}%)")
                    logger.info(f"  成功: {success_count}, 失败: {failure_count}")
                    logger.info(f"  成功率: {success_count / i * 100:.1f}%")
                    logger.info("=" * 60)

                # 静默延迟：随机 1-3 秒
                delay = random.uniform(1.0, 3.0)
                logger.debug(f"  💤 延迟 {delay:.1f} 秒...")
                time.sleep(delay)

            # Step 4: Save harvested data
            self.save_harvested_data()

            # Final report
            logger.info("=" * 60)
            logger.info("🎉 全量收割完成!")
            logger.info(f"  总计: {total_matches} 场")
            logger.info(f"  成功: {success_count} 场 ({success_count / total_matches * 100:.1f}%)")
            logger.info(f"  失败: {failure_count} 场 ({failure_count / total_matches * 100:.1f}%)")
            logger.info(f"  收割数据: {len(self.harvested_data)} 场比赛")
            logger.info("=" * 60)

            # Show data quality report
            logger.info("\n📋 前 5 场比赛数据质量报告:")
            logger.info("-" * 60)
            quality_report = self.db.get_data_quality_report(limit=5)

            for match in quality_report:
                logger.info(f"\n🏟️  {match['home_team']} vs {match['away_team']}")
                logger.info(f"  时间: {match['match_time']}")
                logger.info(f"  xG: {match['home_xg']} - {match['away_xg']}")
                logger.info(f"  控球: {match['home_possession']}% - {match['away_possession']}%")
                logger.info(f"  射门: {match['home_total_shots']} - {match['away_total_shots']}")
                logger.info(f"  红牌: {match['home_red_cards']} - {match['away_red_cards']}")
                logger.info(f"  换人: {match['home_substitutions']} - {match['away_substitutions']}")
                logger.info(f"  评分差: {match['rating_diff']}")
                logger.info(f"  xG/射门: {match['home_xg_per_shot']} - {match['away_xg_per_shot']}")

        except KeyboardInterrupt:
            logger.info("\n⚠️ 用户中断操作")
        except Exception as e:
            logger.error(f"❌ 收割过程出错: {e}", exc_info=True)
        finally:
            self.db.close()


if __name__ == "__main__":
    # Load environment
    load_dotenv()

    # Run harvester
    harvester = SeasonReharvester()
    harvester.run()
