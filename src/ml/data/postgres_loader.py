"""
PostgreSQL 数据加载器 - Phase 4 真实数据集成

专门用于从 PostgreSQL 数据库加载真实的比赛数据，替换 Mock 加载器。
确保输出格式与 MockDataLoader 完全兼容。
"""

from datetime import datetime
import logging
from typing import Any

import pandas as pd
from sqlalchemy import text

from src.database.connection import get_database_manager

logger = logging.getLogger(__name__)


class PostgresDataLoader:
    """
    PostgreSQL 数据加载器

    负责从真实的 PostgreSQL 数据库中加载比赛数据，
    输出格式与 MockDataLoader 完全一致。
    """

    def __init__(
        self,
        batch_size: int = 1000,
        selected_columns: list[str] | None = None,
        max_records: int | None = None,
    ):
        """
        初始化 PostgresDataLoader

        Args:
            batch_size: 批量加载大小
            selected_columns: 选择的列名列表，None表示选择所有列
            max_records: 最大记录数限制
        """
        self.batch_size = batch_size
        self.selected_columns = selected_columns or [
            # 基础特征
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "match_date",
            "status",
            "home_team_name",
            "away_team_name",
            # Phase 8: Player Ratings (核心高级特征)
            "home_xi_rating",
            "away_xi_rating",
            "home_star_rating",
            "away_star_rating",
            "home_bench_rating",
            "away_bench_rating",
            # Phase 8: Metadata
            "referee",
            "stadium",
            "attendance",
            # Phase 8: 纪律信息
            "home_red_cards",
            "away_red_cards",
            "home_goals_ht",
            "away_goals_ht",
        ]
        self.max_records = max_records

        # 初始化数据库连接
        self.db_manager = get_database_manager()
        if not hasattr(self.db_manager, "_async_engine") or self.db_manager._async_engine is None:
            self.db_manager.initialize()

    async def load_data(
        self,
        limit: int = 50000,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status_filter: str = "FT",  # 只加载已完赛的比赛
    ) -> pd.DataFrame:
        """
        从数据库加载比赛数据

        Args:
            limit: 最大加载记录数
            start_date: 开始日期过滤
            end_date: 结束日期过滤
            status_filter: 比赛状态过滤 (默认只加载已完赛 FT)

        Returns:
            pd.DataFrame: 包含比赛数据的DataFrame，格式与MockDataLoader一致
        """
        # 构建SQL查询 - Phase 8升级：包含所有高级特征列
        query = """
            SELECT
                m.id,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                m.match_date,
                m.match_status as status,
                -- 球队信息
                COALESCE(ht.team_name, m.home_team_id::text) as home_team_name,
                COALESCE(at.team_name, m.away_team_id::text) as away_team_name,
                m.league_id,
                m.season,

                -- Phase 8: Player Ratings (核心高级特征)
                m.home_xi_rating,
                m.away_xi_rating,
                m.home_star_rating,
                m.away_star_rating,
                m.home_bench_rating,
                m.away_bench_rating,

                -- Phase 8: Metadata
                m.referee,
                m.stadium,
                m.attendance,
                m.venue,

                -- Phase 8: Advanced JSONB特征
                m.match_shotmap,
                m.match_detailed_stats,
                m.match_events,

                -- Phase 8: 纪律信息
                m.home_red_cards,
                m.away_red_cards,
                m.home_goals_ht,
                m.away_goals_ht,

                -- 传统特征
                m.weather_condition
            FROM matches m
            LEFT JOIN teams ht ON m.home_team_id = ht.id
            LEFT JOIN teams at ON m.away_team_id = at.id
            WHERE 1=1
        """

        params = {}

        # 添加状态过滤 - Phase 8：使用正确的状态字段名
        if status_filter:
            # 将FT转换为finished
            db_status = "finished" if status_filter == "FT" else status_filter
            query += " AND m.match_status = :status"
            params["status"] = db_status

        # 添加日期过滤 - Phase 8：使用正确的表别名
        if start_date:
            query += " AND m.match_date >= :start_date"
            params["start_date"] = start_date

        if end_date:
            query += " AND m.match_date <= :end_date"
            params["end_date"] = end_date

        # 添加限制和排序 - Phase 8：按时间倒序
        query += " ORDER BY m.match_date DESC LIMIT :limit"
        params["limit"] = min(limit, self.max_records or limit)

        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(text(query), params)
                records = result.fetchall()

                # 转换为DataFrame
                df = self._process_records(records)

                logger.info(f"成功从PostgreSQL加载 {len(df)} 条比赛数据")
                return df

        except Exception as e:
            logger.error(f"从PostgreSQL加载数据失败: {e!s}")
            # 返回空DataFrame而不是抛出异常
            return self._get_empty_dataframe()

    def _process_records(self, records: list[Any]) -> pd.DataFrame:
        """
        将数据库记录转换为DataFrame并处理格式

        Args:
            records: 数据库查询结果

        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        if not records:
            return self._get_empty_dataframe()

        # 转换记录为字典列表
        data = []
        for record in records:
            if hasattr(record, "_mapping"):
                # SQLAlchemy Row对象
                row_dict = dict(record._mapping)
            else:
                # 其他类型
                row_dict = dict(record)
            data.append(row_dict)

        df = pd.DataFrame(data)

        # 应用列选择过滤
        if self.selected_columns:
            available_columns = [col for col in self.selected_columns if col in df.columns]
            if available_columns:
                df = df[available_columns]

        # 数据类型转换和清理
        df = self._apply_data_transformations(df)

        return df

    def _apply_data_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用数据转换和清理

        Args:
            df: 原始DataFrame

        Returns:
            pd.DataFrame: 转换后的DataFrame
        """
        if df.empty:
            return df

        # 确保必要的列存在
        required_columns = ["home_team_id", "away_team_id", "home_score", "away_score"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0

        # 日期时间转换
        if "match_date" in df.columns:
            df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")

        # 数值列转换 - Phase 8：包含所有新的评分和统计列
        numeric_columns = [
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "league_id",
            "season",
            "attendance",
            # Phase 8: Player Ratings (核心高级特征)
            "home_xi_rating",
            "away_xi_rating",
            "home_star_rating",
            "away_star_rating",
            "home_bench_rating",
            "away_bench_rating",
            # Phase 8: 纪律信息
            "home_red_cards",
            "away_red_cards",
            "home_goals_ht",
            "away_goals_ht",
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # 得分数据验证 - 确保非负
        score_columns = ["home_score", "away_score"]
        for col in score_columns:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)

        return df

    def _get_empty_dataframe(self) -> pd.DataFrame:
        """
        返回正确结构的空DataFrame

        Returns:
            pd.DataFrame: 空的DataFrame，包含所有必要的列
        """
        columns = self.selected_columns or [
            # 基础特征
            "id",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "match_date",
            "status",
            "home_team_name",
            "away_team_name",
            "league_id",
            "season",
            # Phase 8: Player Ratings (核心高级特征)
            "home_xi_rating",
            "away_xi_rating",
            "home_star_rating",
            "away_star_rating",
            "home_bench_rating",
            "away_bench_rating",
            # Phase 8: Metadata
            "referee",
            "stadium",
            "attendance",
            "venue",
            # Phase 8: 纪律信息
            "home_red_cards",
            "away_red_cards",
            "home_goals_ht",
            "away_goals_ht",
            # 传统特征
            "weather_condition",
        ]

        return pd.DataFrame(columns=columns)

    async def get_data_summary(self) -> dict[str, Any]:
        """
        获取数据摘要信息

        Returns:
            Dict: 数据摘要，包含记录数、日期范围等信息
        """
        try:
            df = await self.load_data(limit=1)  # 只加载一条记录来获取结构

            if df.empty:
                return {
                    "status": "empty",
                    "message": "数据库中没有找到符合条件的比赛数据",
                    "total_records": 0,
                }

            # 获取总记录数 - Phase 8：使用正确的状态字段名
            async with self.db_manager.get_async_session() as session:
                count_query = "SELECT COUNT(*) as total FROM matches WHERE match_status = 'finished'"
                count_result = await session.execute(text(count_query))
                total_records = count_result.scalar()

            return {
                "status": "success",
                "total_records": total_records,
                "available_columns": list(df.columns),
                "sample_data": df.head(1).to_dict("records") if not df.empty else None,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"获取数据摘要失败: {e!s}",
                "total_records": 0,
            }

    async def test_connection(self) -> bool:
        """
        测试数据库连接是否正常

        Returns:
            bool: 连接是否成功
        """
        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e!s}")
            return False
