#!/usr/bin/env python3
"""
CSV批量入库器 - 数据治理工程师专用
将FBref采集的CSV数据批量导入PostgreSQL数据库
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import json
import re

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.async_manager import get_async_db_session
from src.database.models.match import Match
from src.database.models.team import Team
from src.database.models.league import League
from sqlalchemy import select, insert, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/csv_ingestion.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class CSVDataIngester:
    """CSV数据批量入库器"""

    def __init__(self):
        self.csv_dir = Path("data/fbref")
        self.ingestion_stats = {
            "total_files": 0,
            "total_matches": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "xg_coverage": {},
            "leagues_processed": [],
        }

        # 创建日志目录
        Path("logs").mkdir(exist_ok=True)

    async def run(self):
        """执行批量入库"""
        logger.info("🚀 开始CSV批量入库...")
        start_time = datetime.now()

        # 扫描所有CSV文件
        csv_files = list(self.csv_dir.glob("*.csv"))
        self.ingestion_stats["total_files"] = len(csv_files)

        logger.info(f"📁 发现 {len(csv_files)} 个CSV文件")

        # 获取异步会话
        async with get_async_db_session() as session:
            for csv_file in csv_files:
                await self._process_csv_file(csv_file, session)
                await session.commit()  # 每个文件提交一次

        # 生成xG覆盖率报告
        self._generate_xg_coverage_report()

        # 生成最终报告
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("🎉 CSV批量入库完成!")
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")
        logger.info(f"📊 处理统计: {self.ingestion_stats}")

        return self.ingestion_stats

    async def _process_csv_file(self, csv_file: Path, session: AsyncSession):
        """处理单个CSV文件"""
        league_id = csv_file.stem.replace("_all_seasons_matches", "")
        logger.info(f"📄 处理文件: {csv_file.name} (联赛ID: {league_id})")

        try:
            # 读取CSV数据
            df = pd.read_csv(csv_file)
            if df.empty:
                logger.warning(f"⚠️  文件为空: {csv_file.name}")
                return

            # 数据清洗和转换
            df_cleaned = self._clean_and_transform_data(df, league_id)
            if df_cleaned.empty:
                logger.warning(f"⚠️  清洗后无有效数据: {csv_file.name}")
                return

            # xG覆盖率分析
            xg_stats = self._analyze_xg_coverage(df_cleaned, league_id)

            # 批量入库
            success_count = await self._batch_insert_matches(
                df_cleaned, session, league_id
            )

            # 更新统计
            self.ingestion_stats["total_matches"] += len(df_cleaned)
            self.ingestion_stats["successful_matches"] += success_count
            self.ingestion_stats["leagues_processed"].append(league_id)

            logger.info(
                f"✅ {csv_file.name}: {success_count}/{len(df_cleaned)} 场比赛入库成功"
            )
            logger.info(f"📊 xG覆盖率: {xg_stats}")

        except Exception as e:
            logger.error(f"❌ 处理文件失败 {csv_file.name}: {e}")
            self.ingestion_stats["failed_matches"] += len(df) if "df" in locals() else 0

    def _clean_and_transform_data(
        self, df: pd.DataFrame, league_id: str
    ) -> pd.DataFrame:
        """数据清洗和转换"""
        logger.info(f"🧹 开始数据清洗: {len(df)} 行原始数据")

        # 创建新DataFrame
        cleaned_data = []

        for idx, row in df.iterrows():
            try:
                # 检查必要字段
                if pd.isna(row.get("Home")) or pd.isna(row.get("Away")):
                    continue

                # 解析比分
                home_score = None
                away_score = None

                score = str(row.get("Score", "")).strip()
                if score and "–" in score:
                    # 使用en dash (U+2013) 分割比分
                    parts = score.split("–")
                    if len(parts) == 2:
                        try:
                            home_score = int(parts[0].strip())
                            away_score = int(parts[1].strip())
                        except ValueError:
                            # 如果不能转为整数，保持None
                            pass

                # 解析日期
                match_date = None
                date_str = str(row.get("Date", "")).strip()
                if date_str and date_str != "nan":
                    try:
                        # 处理可能的多种日期格式
                        match_date = pd.to_datetime(date_str).to_pydatetime()
                    except:
                        # 如果解析失败，记录警告但继续
                        pass

                # 解析xG数据
                home_xg = None
                away_xg = None

                if not pd.isna(row.get("xG")):
                    try:
                        home_xg = float(row.get("xG"))
                        if home_xg < 0 or home_xg > 10:  # 合理性检查
                            home_xg = None
                    except (ValueError, TypeError):
                        pass

                if not pd.isna(row.get("xG.1")):
                    try:
                        away_xg = float(row.get("xG.1"))
                        if away_xg < 0 or away_xg > 10:  # 合理性检查
                            away_xg = None
                    except (ValueError, TypeError):
                        pass

                # 构建匹配键 (用于去重)
                match_key = self._generate_match_key(
                    row.get("Home"), row.get("Away"), match_date
                )

                cleaned_record = {
                    "match_key": match_key,
                    "home_team_name": str(row.get("Home")).strip(),
                    "away_team_name": str(row.get("Away")).strip(),
                    "home_score": home_score,
                    "away_score": away_score,
                    "match_date": match_date,
                    "venue": (
                        str(row.get("Venue", "")).strip()
                        if not pd.isna(row.get("Venue"))
                        else None
                    ),
                    "attendance": None,
                    "league_id": league_id,
                    "season": "2024-2025",  # 基于数据推测
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                    "data_source": "fbref",
                    "raw_data": row.to_dict(),  # 保存原始数据
                }

                # 解析观众人数
                attendance = row.get("Attendance")
                if attendance and not pd.isna(attendance):
                    try:
                        cleaned_record["attendance"] = int(
                            str(attendance).replace(",", "")
                        )
                    except ValueError:
                        pass

                cleaned_data.append(cleaned_record)

            except Exception as e:
                logger.warning(f"⚠️ 行 {idx} 数据清洗失败: {e}")
                continue

        result_df = pd.DataFrame(cleaned_data)
        logger.info(f"✅ 清洗完成: {len(result_df)} 行有效数据")

        return result_df

    def _generate_match_key(
        self, home_team: str, away_team: str, match_date: datetime
    ) -> str:
        """生成比赛唯一键"""
        if match_date:
            date_str = match_date.strftime("%Y-%m-%d")
        else:
            date_str = "unknown"

        # 标准化队名
        home_clean = re.sub(r"[^a-zA-Z0-9]", "", str(home_team).lower())
        away_clean = re.sub(r"[^a-zA-Z0-9]", "", str(away_team).lower())

        return f"{home_clean}_{away_clean}_{date_str}"

    def _analyze_xg_coverage(self, df: pd.DataFrame, league_id: str) -> Dict:
        """分析xG覆盖率"""
        total_matches = len(df)
        matches_with_xg = df[(df["home_xg"].notna()) & (df["away_xg"].notna())].shape[0]

        xg_coverage = {
            "total_matches": total_matches,
            "matches_with_xg": matches_with_xg,
            "coverage_rate": (
                (matches_with_xg / total_matches * 100) if total_matches > 0 else 0
            ),
            "home_xg_mean": df["home_xg"].mean() if matches_with_xg > 0 else None,
            "away_xg_mean": df["away_xg"].mean() if matches_with_xg > 0 else None,
        }

        self.ingestion_stats["xg_coverage"][league_id] = xg_coverage

        return xg_coverage

    async def _batch_insert_matches(
        self, df: pd.DataFrame, session: AsyncSession, league_id: str
    ) -> int:
        """批量插入比赛数据"""
        logger.info(f"💾 开始批量插入: {len(df)} 场比赛")

        success_count = 0

        for idx, row in df.iterrows():
            try:
                # 查找或创建主队
                home_team_id = await self._get_or_create_team(
                    session, row["home_team_name"]
                )

                # 查找或创建客队
                away_team_id = await self._get_or_create_team(
                    session, row["away_team_name"]
                )

                # 查找联赛
                league_obj = await self._get_league_by_id(session, league_id)
                league_db_id = league_obj.id if league_obj else None

                # 检查比赛是否已存在
                existing_match = await self._find_existing_match(
                    session, home_team_id, away_team_id, row["match_date"]
                )

                if existing_match:
                    # 更新现有比赛
                    await self._update_match(
                        session, existing_match.id, row, league_db_id
                    )
                    success_count += 1
                else:
                    # 插入新比赛
                    await self._insert_new_match(
                        session, row, home_team_id, away_team_id, league_db_id
                    )
                    success_count += 1

                if success_count % 100 == 0:
                    await session.commit()  # 每100条提交一次

            except Exception as e:
                logger.warning(f"⚠️ 行 {idx} 入库失败: {e}")
                continue

        await session.commit()  # 最终提交
        logger.info(f"✅ 批量插入完成: {success_count} 场比赛成功")

        return success_count

    async def _get_or_create_team(self, session: AsyncSession, team_name: str) -> int:
        """获取或创建队伍"""
        # 查找现有队伍
        result = await session.execute(select(Team).where(Team.name == team_name))
        team = result.scalar_one_or_none()

        if team:
            return team.id

        # 创建新队伍
        new_team = Team(name=team_name)
        session.add(new_team)
        await session.flush()  # 获取ID

        logger.info(f"🏃 创建新队伍: {team_name} (ID: {new_team.id})")
        return new_team.id

    async def _get_league_by_id(
        self, session: AsyncSession, league_id: str
    ) -> Optional[League]:
        """根据ID获取联赛"""
        # 尝试多种匹配方式
        result = await session.execute(
            select(League).where(
                or_(
                    League.league_id == league_id,
                    League.name == league_id,
                    League.short_name == league_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _find_existing_match(
        self,
        session: AsyncSession,
        home_team_id: int,
        away_team_id: int,
        match_date: datetime,
    ) -> Optional[Match]:
        """查找现有比赛"""
        if not match_date:
            return None

        result = await session.execute(
            select(Match).where(
                and_(
                    Match.home_team_id == home_team_id,
                    Match.away_team_id == away_team_id,
                    Match.match_date == match_date,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _update_match(
        self,
        session: AsyncSession,
        match_id: int,
        row: pd.Series,
        league_id: Optional[int],
    ):
        """更新现有比赛"""
        update_data = {
            "home_score": row["home_score"],
            "away_score": row["away_score"],
            "venue": row["venue"],
            "attendance": row["attendance"],
            "league_id": league_id,
            "season": row["season"],
            "updated_at": datetime.now(),
            "data_source": row["data_source"],
            "data_completeness": (
                "complete" if row["home_xg"] and row["away_xg"] else "partial"
            ),
        }

        # 更新JSON字段
        stats_data = {"home_xg": row["home_xg"], "away_xg": row["away_xg"]}
        update_data["stats"] = stats_data

        # 保存原始数据
        update_data["match_metadata"] = {
            "raw_csv_data": row["raw_data"],
            "ingestion_timestamp": datetime.now().isoformat(),
        }

        await session.execute(
            update(Match).where(Match.id == match_id).values(**update_data)
        )

    async def _insert_new_match(
        self,
        session: AsyncSession,
        row: pd.Series,
        home_team_id: int,
        away_team_id: int,
        league_id: Optional[int],
    ):
        """插入新比赛"""
        new_match = Match(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=row["home_score"],
            away_score=row["away_score"],
            status="completed",
            match_date=row["match_date"] or datetime.now(),
            venue=row["venue"],
            attendance=row["attendance"],
            league_id=league_id,
            season=row["season"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            data_source=row["data_source"],
            data_completeness=(
                "complete" if row["home_xg"] and row["away_xg"] else "partial"
            ),
        )

        # 设置JSON字段
        stats_data = {"home_xg": row["home_xg"], "away_xg": row["away_xg"]}
        new_match.stats = stats_data

        # 保存原始数据
        new_match.match_metadata = {
            "raw_csv_data": row["raw_data"],
            "ingestion_timestamp": datetime.now().isoformat(),
        }

        session.add(new_match)

    def _generate_xg_coverage_report(self):
        """生成xG覆盖率报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 xG覆盖率分析报告")
        logger.info("=" * 60)

        total_matches = sum(
            stats["total_matches"]
            for stats in self.ingestion_stats["xg_coverage"].values()
        )
        total_with_xg = sum(
            stats["matches_with_xg"]
            for stats in self.ingestion_stats["xg_coverage"].values()
        )
        overall_coverage = (
            (total_with_xg / total_matches * 100) if total_matches > 0 else 0
        )

        logger.info(
            f"🌍 总体覆盖率: {overall_coverage:.1f}% ({total_with_xg:,}/{total_matches:,} 场比赛)"
        )
        logger.info("")

        # 按覆盖率分组显示
        high_coverage = []
        medium_coverage = []
        low_coverage = []

        for league_id, stats in self.ingestion_stats["xg_coverage"].items():
            if stats["coverage_rate"] >= 80:
                high_coverage.append((league_id, stats))
            elif stats["coverage_rate"] >= 20:
                medium_coverage.append((league_id, stats))
            else:
                low_coverage.append((league_id, stats))

        logger.info("🟢 高xG覆盖率联赛 (≥80%):")
        for league_id, stats in sorted(
            high_coverage, key=lambda x: x[1]["coverage_rate"], reverse=True
        ):
            logger.info(
                f"  {league_id:25s}: {stats['coverage_rate']:5.1f}% ({stats['matches_with_xg']:4d}/{stats['total_matches']:4d}) "
                f"[主队xG均:{stats['home_xg_mean']:.2f}, 客队xG均:{stats['away_xg_mean']:.2f}]"
            )

        if medium_coverage:
            logger.info("\n🟡 中等xG覆盖率联赛 (20-79%):")
            for league_id, stats in sorted(
                medium_coverage, key=lambda x: x[1]["coverage_rate"], reverse=True
            ):
                logger.info(
                    f"  {league_id:25s}: {stats['coverage_rate']:5.1f}% ({stats['matches_with_xg']:4d}/{stats['total_matches']:4d})"
                )

        if low_coverage:
            logger.info("\n🔴 低xG覆盖率联赛 (<20%):")
            for league_id, stats in sorted(
                low_coverage, key=lambda x: x[1]["coverage_rate"], reverse=True
            ):
                logger.info(
                    f"  {league_id:25s}: {stats['coverage_rate']:5.1f}% ({stats['matches_with_xg']:4d}/{stats['total_matches']:4d}) [仅比分数据]"
                )


async def main():
    """主函数"""
    logger.info("🔧 启动CSV批量入库器")

    ingester = CSVDataIngester()
    stats = await ingester.run()

    # 输出最终统计
    logger.info("\n" + "=" * 60)
    logger.info("📋 入库统计摘要")
    logger.info("=" * 60)
    logger.info(f"📁 处理文件数: {stats['total_files']}")
    logger.info(f"⚽ 总比赛数: {stats['total_matches']:,}")
    logger.info(f"✅ 成功入库: {stats['successful_matches']:,}")
    logger.info(f"❌ 失败数量: {stats['failed_matches']:,}")
    logger.info(
        f"📊 成功率: {stats['successful_matches']/stats['total_matches']*100:.1f}%"
    )

    return 0 if stats["successful_matches"] > 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
