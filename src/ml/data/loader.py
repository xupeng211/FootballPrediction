"""
DataLoader Implementation - TDD Green Phase Implementation

Phase 2: AI Modeling - 数据加载器实现

按照TDD原则，实现DataLoader类以满足测试用例的要求。
"""

import logging
from typing import Optional, List, Any, Dict
from datetime import datetime

import pandas as pd

from src.database import get_async_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DataLoader:
    """
    负责从数据库加载原始比赛数据并转换为 Pandas DataFrame。
    遵循 TDD 设计，确保数据格式符合 ML 模型要求。
    """

    def __init__(
        self,
        batch_size: int = 1000,
        selected_columns: Optional[List[str]] = None,
        max_records: Optional[int] = None,
    ):
        """
        初始化 DataLoader。

        Args:
            batch_size: 批量大小配置
            selected_columns: 选择的列列表
            max_records: 最大记录数限制
        """
        self.batch_size = batch_size
        self.selected_columns = selected_columns or []
        self.max_records = max_records

    async def load_raw_data(
        self,
        db_session=None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50000,
    ) -> pd.DataFrame:
        """
        加载已完赛(FT)的比赛数据。

        Args:
            db_session: 数据库会话对象
            start_date: 开始日期过滤
            end_date: 结束日期过滤
            limit: 最大加载记录数，默认为 50000

        Returns:
            pd.DataFrame: 包含比赛数据的 DataFrame。
            如果无数据，返回空的 DataFrame。
        """
        query = """
            SELECT
                id, fotmob_id, match_date, status,
                home_team_id, away_team_id,
                home_score, away_score,
                home_team_name, away_team_name,
                league_id, season,
                -- L2 Metrics
                home_possession, away_possession,
                home_total_shots, away_total_shots,
                home_shots_on_target, away_shots_on_target,
                home_expected_goals, away_expected_goals,
                home_big_chances_created, away_big_chances_created,
                home_accurate_passes, away_accurate_passes,
                home_accurate_crosses, away_accurate_crosses
            FROM matches
            WHERE status = 'FT'
        """

        # 添加日期过滤条件
        params = {}
        if start_date:
            query += " AND match_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND match_date <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY match_date DESC LIMIT :limit"
        params["limit"] = min(limit, self.max_records or limit)

        try:
            # 使用传入的会话或创建新会话
            if db_session:
                records = await self._execute_query(db_session, query, params)
            else:
                async with get_async_db_session() as session:
                    records = await self._execute_query(session, query, params)

            df = self._process_records(records)
            logger.info(f"成功加载 {len(df)} 条比赛数据")
            return df

        except Exception as e:
            logger.error(f"加载数据失败: {str(e)}")
            # 即使出错也返回空 DataFrame 以保持类型安全，但记录错误
            return pd.DataFrame()

    async def _execute_query(
        self, session, query: str, params: Dict[str, Any]
    ) -> List[Any]:
        """
        执行数据库查询。

        Args:
            session: 数据库会话
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果记录列表
        """
        result = await session.execute(text(query), params)
        return result.fetchall()

    def _process_records(self, records: List[Any]) -> pd.DataFrame:
        """
        将数据库记录转换为 DataFrame 并进行预处理。

        Args:
            records: 数据库查询结果记录

        Returns:
            处理后的 DataFrame
        """
        if not records:
            # 返回带有正确列名的空 DataFrame
            return self._get_empty_dataframe()

        # 转换为 DataFrame
        # 处理不同类型的数据库记录对象
        data = []
        for record in records:
            if hasattr(record, "_mapping"):
                # asyncpg.Row 对象
                data.append(dict(record._mapping))
            elif hasattr(record, "keys"):
                # SQLAlchemy Row 对象
                data.append({key: getattr(record, key) for key in record.keys()})
            else:
                # 字典或其他可迭代对象
                data.append(dict(record))
        df = pd.DataFrame(data)

        # 应用列选择过滤
        if self.selected_columns:
            # 确保只选择存在的列
            available_columns = [
                col for col in self.selected_columns if col in df.columns
            ]
            if available_columns:
                df = df[available_columns]

        # 类型转换和数据处理
        df = self._apply_type_conversions(df)
        df = self._apply_data_validations(df)

        return df

    def _get_empty_dataframe(self) -> pd.DataFrame:
        """
        返回带有正确列名的空 DataFrame。

        Returns:
            空的 DataFrame with expected columns
        """
        expected_columns = [
            "id",
            "fotmob_id",
            "match_date",
            "status",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "home_team_name",
            "away_team_name",
            "league_id",
            "season",
            "home_possession",
            "away_possession",
            "home_total_shots",
            "away_total_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_expected_goals",
            "away_expected_goals",
            "home_big_chances_created",
            "away_big_chances_created",
            "home_accurate_passes",
            "away_accurate_passes",
            "home_accurate_crosses",
            "away_accurate_crosses",
        ]

        # 应用列选择过滤
        if self.selected_columns:
            expected_columns = [
                col for col in self.selected_columns if col in expected_columns
            ]

        return pd.DataFrame(columns=expected_columns)

    def _apply_type_conversions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用类型转换。

        Args:
            df: 原始 DataFrame

        Returns:
            类型转换后的 DataFrame
        """
        # 日期时间转换
        if "match_date" in df.columns:
            df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")

        # 数值列转换
        numeric_cols = [
            "id",
            "fotmob_id",
            "league_id",
            "home_score",
            "away_score",
            "home_possession",
            "away_possession",
            "home_total_shots",
            "away_total_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_expected_goals",
            "away_expected_goals",
            "home_big_chances_created",
            "away_big_chances_created",
            "home_accurate_passes",
            "away_accurate_passes",
            "home_accurate_crosses",
            "away_accurate_crosses",
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    def _apply_data_validations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用数据验证和清理。

        Args:
            df: 类型转换后的 DataFrame

        Returns:
            验证后的 DataFrame
        """
        if df.empty:
            return df

        # 得分字段非负验证
        score_cols = ["home_score", "away_score"]
        for col in score_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)

        # 期望进球非负验证
        xg_cols = ["home_expected_goals", "away_expected_goals"]
        for col in xg_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)

        # 控球率范围验证 (0-100)
        possession_cols = ["home_possession", "away_possession"]
        for col in possession_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=0, upper=100)

        return df

    async def get_data_summary(self) -> Dict[str, Any]:
        """
        获取数据摘要信息。

        Returns:
            数据摘要字典
        """
        df = await self.load_raw_data()

        if df.empty:
            return {"total_records": 0, "date_range": None, "status": "empty"}

        return {
            "total_records": len(df),
            "date_range": {
                "start": df["match_date"].min(),
                "end": df["match_date"].max(),
            },
            "status": "success",
            "columns": list(df.columns),
            "null_counts": df.isnull().sum().to_dict(),
        }
