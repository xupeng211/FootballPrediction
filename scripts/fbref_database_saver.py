#!/usr/bin/env python3
"""
FBref数据入库转换器
后端工程师：DataFrame到Database的桥梁

Backend Engineer: 数据管道修复专家
Purpose: 修复数据入库断链，确保采集数据成功存储
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import json
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入数据库组件
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from src.database.models.match import Match

    DB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"数据库组件导入失败: {e}")
    DB_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FBrefDatabaseSaver:
    """
    FBref数据入库管理器

    功能：
    1. 队伍ID解析和创建
    2. 比赛数据转换和存储
    3. 统计数据JSON化处理
    4. 批量同步保存
    """

    def __init__(self):
        if not DB_AVAILABLE:
            raise ImportError("数据库组件不可用，无法初始化数据保存器")

        # 创建同步数据库连接
        try:
            # 优先使用Docker容器内连接，回退到localhost
            database_urls = [
                "postgresql://postgres:postgres-dev-password@db:5432/football_prediction",  # Docker内部
                "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",  # 本地
            ]

            self.engine = None
            for db_url in database_urls:
                try:
                    self.engine = create_engine(
                        db_url, connect_args={"connect_timeout": 10}
                    )
                    # 测试连接
                    with self.engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    logger.info(
                        f"✅ 数据库连接成功: {db_url.split('@')[1].split('/')[0]}"
                    )
                    break
                except Exception:
                    if self.engine:
                        self.engine.dispose()
                        self.engine = None
                    continue

            if not self.engine:
                raise Exception("所有数据库连接尝试均失败")

            self.SessionLocal = sessionmaker(bind=self.engine)

        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def get_or_create_team(
        self, session, team_name: str, country: str = "Unknown"
    ) -> int:
        """获取或创建队伍ID"""
        try:
            # 查询现有队伍
            result = session.execute(
                text("SELECT id FROM teams WHERE name = :name"), {"name": team_name}
            )
            team_id = result.scalar()

            if team_id:
                return team_id

            # 创建新队伍
            logger.info(f"🆕 创建新队伍: {team_name}")
            result = session.execute(
                text(
                    """
                    INSERT INTO teams (name, short_name, country, created_at, updated_at)
                    VALUES (:name, :short_name, :country, NOW(), NOW())
                    RETURNING id
                """
                ),
                {
                    "name": team_name,
                    "short_name": team_name[:10] if len(team_name) > 10 else team_name,
                    "country": country,
                },
            )
            session.commit()
            return result.scalar()

        except Exception as e:
            logger.error(f"❌ 队伍创建失败: {team_name} - {e}")
            session.rollback()
            raise

    def parse_score(self, score_str: str) -> tuple[Optional[int], Optional[int]]:
        """解析比分字符串"""
        if pd.isna(score_str) or score_str == "" or score_str == "-":
            return None, None

        try:
            if "–" in score_str:
                home_score, away_score = score_str.split("–")
            elif "-" in score_str:
                home_score, away_score = score_str.split("-")
            else:
                return None, None

            return int(home_score.strip()), int(away_score.strip())
        except (ValueError, AttributeError):
            return None, None

    def parse_match_date(self, date_str) -> Optional[datetime]:
        """解析比赛日期"""
        if pd.isna(date_str) or date_str == "":
            return None

        try:
            # 尝试多种日期格式
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except ValueError:
                    continue

            logger.warning(f"⚠️ 无法解析日期: {date_str}")
            return None
        except Exception as e:
            logger.error(f"❌ 日期解析异常: {date_str} - {e}")
            return None

    def convert_dataframe_to_match_records(
        self, df: pd.DataFrame, league_name: str, season: str
    ) -> list[dict]:
        """将DataFrame转换为比赛记录列表"""
        logger.info(f"🔄 转换DataFrame: {df.shape} -> 比赛记录")

        match_records = []
        processed_count = 0

        for _, row in df.iterrows():
            try:
                # 提取基本信息
                home_team = row.get("home", "")
                away_team = row.get("away", "")
                score_str = row.get("score", "")
                match_date_str = row.get("date", "")

                # 🔥 提取原始HTML文件路径 (ELT架构支持)
                raw_file_path = row.get("raw_file_path")

                if not home_team or not away_team:
                    logger.warning("⚠️ 跳过无效行: 主客队信息缺失")
                    continue

                # 解析比分
                home_score, away_score = self.parse_score(score_str)

                # 解析日期
                match_date = self.parse_match_date(match_date_str)

                # 提取xG数据
                xg_data = {}
                if "xg_home" in row and not pd.isna(row["xg_home"]):
                    xg_data["home_xg"] = float(row["xg_home"])
                if "xg_away" in row and not pd.isna(row["xg_away"]):
                    xg_data["away_xg"] = float(row["xg_away"])

                # 构建统计数据JSON（关键：包含所有原始数据，处理NaN值）
                # 清理原始数据，避免JSON序列化问题
                clean_row_data = {}
                match_report_url = None

                for key, value in row.items():
                    if pd.isna(value):
                        clean_row_data[key] = None
                    elif isinstance(value, (int, float)) and (
                        value != value
                    ):  # 检查NaN
                        clean_row_data[key] = None
                    else:
                        clean_row_data[key] = value

                        # 🔥 关键修复：特别处理Match Report URL
                        if key == "match_report_url" and value and not pd.isna(value):
                            match_report_url = str(value)
                            logger.info(
                                f"🔗 发现Match Report URL: {match_report_url[:50]}..."
                            )

                stats_data = {
                    "source": "fbref",
                    "league": league_name,
                    "season": season,
                    "raw_data": clean_row_data,
                    "xg": xg_data,
                }

                # 🔥 关键修复：将URL单独保存到raw_data中，确保可访问性
                if match_report_url:
                    stats_data["match_report_url"] = match_report_url
                    logger.info(
                        f"✅ Match Report URL已保存: {match_report_url[:50]}..."
                    )

                # 添加其他统计信息
                for col in df.columns:
                    if col not in ["home", "away", "score", "date"]:
                        value = row.get(col)
                        if not pd.isna(value):
                            stats_data[col] = value

                # 构建比赛记录
                match_record = {
                    "home_team_name": home_team,
                    "away_team_name": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "match_date": match_date,
                    "status": "completed" if home_score is not None else "scheduled",
                    "venue": row.get("venue"),
                    "league_name": league_name,
                    "season": season,
                    "stats": stats_data,
                    "data_source": "fbref",
                    "data_completeness": "complete" if xg_data else "partial",
                    "raw_file_path": raw_file_path,  # 🔥 ELT架构支持
                }

                match_records.append(match_record)
                processed_count += 1

                # 每处理100条记录输出一次进度
                if processed_count % 100 == 0:
                    logger.info(f"📊 已处理 {processed_count} 条记录...")

            except Exception as e:
                logger.error(f"❌ 行转换失败: {e}")
                logger.error(f"   问题数据: {row.to_dict()}")
                continue

        logger.info(f"✅ DataFrame转换完成: {len(match_records)} 条有效记录")
        return match_records

    def save_matches_to_database(self, match_records: list[dict]) -> int:
        """批量保存比赛记录到数据库"""
        if not match_records:
            logger.warning("⚠️ 没有比赛记录需要保存")
            return 0

        logger.info(f"💾 开始批量保存 {len(match_records)} 条比赛记录...")

        saved_count = 0
        session = self.SessionLocal()

        try:
            for record in match_records:
                try:
                    # 获取或创建队伍ID
                    home_team_id = self.get_or_create_team(
                        session, record["home_team_name"], "Unknown"
                    )
                    away_team_id = self.get_or_create_team(
                        session, record["away_team_name"], "Unknown"
                    )

                    # 检查是否已存在相同比赛
                    existing_result = session.execute(
                        text(
                            """
                            SELECT id FROM matches
                            WHERE home_team_id = :home_id
                            AND away_team_id = :away_id
                            AND match_date = :match_date
                        """
                        ),
                        {
                            "home_id": home_team_id,
                            "away_id": away_team_id,
                            "match_date": record["match_date"],
                        },
                    )
                    existing_id = existing_result.scalar()

                    if existing_id:
                        logger.debug(
                            f"⏭️ 跳过已存在比赛: {record['home_team_name']} vs {record['away_team_name']}"
                        )
                        continue

                    # 插入新比赛记录
                    session.execute(
                        text(
                            """
                            INSERT INTO matches (
                                home_team_id, away_team_id, home_score, away_score,
                                status, match_date, venue, season,
                                stats, data_source, data_completeness,
                                raw_file_path,
                                created_at, updated_at
                            ) VALUES (
                                :home_id, :away_id, :home_score, :away_score,
                                :status, :match_date, :venue, :season,
                                :stats, :data_source, :data_completeness,
                                :raw_file_path,
                                NOW(), NOW()
                            )
                        """
                        ),
                        {
                            "home_id": home_team_id,
                            "away_id": away_team_id,
                            "home_score": record["home_score"],
                            "away_score": record["away_score"],
                            "status": record["status"],
                            "match_date": record["match_date"],
                            "venue": record.get("venue"),
                            "season": record["season"],
                            "stats": json.dumps(record["stats"]),
                            "data_source": record["data_source"],
                            "data_completeness": record["data_completeness"],
                            "raw_file_path": record.get("raw_file_path"),  # 🔥 ELT架构支持
                        },
                    )

                    saved_count += 1

                    # 每10条记录提交一次
                    if saved_count % 10 == 0:
                        session.commit()
                        logger.info(f"💾 已保存 {saved_count} 条记录...")

                except Exception as e:
                    logger.error(f"❌ 保存记录失败: {e}")
                    session.rollback()
                    continue

            # 最终提交
            session.commit()
            logger.info(f"🎉 成功保存 {saved_count} 条比赛记录到数据库！")
            return saved_count

        except Exception as e:
            logger.error(f"❌ 数据库保存异常: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def save_dataframe_to_database(
        self, df: pd.DataFrame, league_name: str, season: str
    ) -> int:
        """
        DataFrame到数据库的完整流程

        Args:
            df: 比赛数据DataFrame
            league_name: 联赛名称
            season: 赛季

        Returns:
            成功保存的记录数量
        """
        logger.info(f"🔄 开始保存FBref数据: {league_name} {season}")
        logger.info(f"📊 输入数据: {df.shape}")

        # 步骤1: 转换DataFrame为比赛记录
        match_records = self.convert_dataframe_to_match_records(df, league_name, season)

        # 步骤2: 批量保存到数据库
        saved_count = self.save_matches_to_database(match_records)

        logger.info(f"✅ {league_name} {season} 数据保存完成: {saved_count} 条记录")
        return saved_count


# 测试函数
def test_database_saver():
    """测试数据库保存器"""
    try:
        saver = FBrefDatabaseSaver()

        # 创建测试数据
        test_data = pd.DataFrame(
            [
                {
                    "date": "2024-05-19",
                    "home": "Manchester City",
                    "away": "West Ham United",
                    "score": "2-1",
                    "xg_home": 2.3,
                    "xg_away": 1.1,
                    "venue": "Etihad Stadium",
                }
            ]
        )

        # 测试保存
        saved_count = saver.save_dataframe_to_database(
            test_data, "Premier League", "2023-2024"
        )
        logger.info(f"🧪 测试完成: 保存了 {saved_count} 条记录")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    test_database_saver()
