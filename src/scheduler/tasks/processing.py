"""
数据处理任务
Data Processing Tasks

包含Bronze层到Silver层的数据处理任务。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.data.quality.data_quality_monitor import DataQualityMonitor
from src.database.connection import get_async_session

from .base import BaseDataTask
from ..celery_config import app

logger = logging.getLogger(__name__)


def _get_bronze_table_query(table_name: str) -> str:
    """获取Bronze表查询语句"""
    queries = {
        "raw_matches": """
            SELECT id, data, created_at, source
            FROM raw_matches
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
        "raw_odds": """
            SELECT id, data, created_at, source
            FROM raw_odds
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
        "raw_scores": """
            SELECT id, data, created_at, source
            FROM raw_scores
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
    }
    return queries.get(table_name)


def _get_update_query(table_name: str):
    """获取更新查询语句"""
    from sqlalchemy import text

    queries = {
        "raw_matches": text(
            """
            UPDATE raw_matches
            SET processed = true, processed_at = NOW()
            WHERE id = :record_id
        """
        ),
        "raw_odds": text(
            """
            UPDATE raw_odds
            SET processed = true, processed_at = NOW()
            WHERE id = :record_id
        """
        ),
        "raw_scores": text(
            """
            UPDATE raw_scores
            SET processed = true, processed_at = NOW()
            WHERE id = :record_id
        """
        ),
    }
    return queries.get(table_name)


async def _transform_to_silver_format(cleaned_data, bronze_table, record_id):
    """转换为Silver层格式"""
    if bronze_table == "raw_matches":
        # 转换比赛数据
        return {
            "match_id": cleaned_data.get("match_id"),
            "home_team": cleaned_data.get("home_team"),
            "away_team": cleaned_data.get("away_team"),
            "match_date": cleaned_data.get("match_date"),
            "league_id": cleaned_data.get("league_id"),
            "venue": cleaned_data.get("venue"),
            "status": cleaned_data.get("status", "scheduled"),
            "source": cleaned_data.get("source"),
            "processed_at": datetime.now().isoformat(),
            "data_quality_score": cleaned_data.get("quality_score", 1.0),
        }

    elif bronze_table == "raw_odds":
        # 转换赔率数据
        return {
            "match_id": cleaned_data.get("match_id"),
            "bookmaker": cleaned_data.get("bookmaker"),
            "home_win_odds": cleaned_data.get("home_win_odds"),
            "draw_odds": cleaned_data.get("draw_odds"),
            "away_win_odds": cleaned_data.get("away_win_odds"),
            "timestamp": cleaned_data.get("timestamp"),
            "source": cleaned_data.get("source"),
            "processed_at": datetime.now().isoformat(),
            "data_quality_score": cleaned_data.get("quality_score", 1.0),
        }

    elif bronze_table == "raw_scores":
        # 转换比分数据
        return {
            "match_id": cleaned_data.get("match_id"),
            "home_score": cleaned_data.get("home_score"),
            "away_score": cleaned_data.get("away_score"),
            "match_status": cleaned_data.get("match_status"),
            "timestamp": cleaned_data.get("timestamp"),
            "source": cleaned_data.get("source"),
            "processed_at": datetime.now().isoformat(),
            "data_quality_score": cleaned_data.get("quality_score", 1.0),
        }
    else:
        raise ValueError(f"未知的Bronze表类型: {bronze_table}")


async def _save_to_silver_layer(session, silver_data, bronze_table):
    """保存到Silver层"""
    from sqlalchemy import text

    # 确定Silver表名
    silver_table_map = {
        "raw_matches": "silver_matches",
        "raw_odds": "silver_odds",
        "raw_scores": "silver_scores",
    }
    silver_table = silver_table_map.get(bronze_table)

    if not silver_table:
        raise ValueError(f"无法找到对应的Silver表: {bronze_table}")

    # 验证表名防止SQL注入
    valid_silver_tables = ["silver_matches", "silver_odds", "silver_scores"]
    if silver_table not in valid_silver_tables:
        raise ValueError(f"非法的Silver表名: {silver_table}")

    # 构建插入SQL
    if bronze_table == "raw_matches":
        insert_query = text(
            """
            INSERT INTO silver_matches
            (match_id, home_team, away_team, match_date, league_id, venue, status, source, processed_at, data_quality_score)
            VALUES (:match_id, :home_team, :away_team, :match_date, :league_id, :venue, :status, :source, :processed_at, :data_quality_score)
            ON CONFLICT (match_id) DO UPDATE SET
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            match_date = EXCLUDED.match_date,
            league_id = EXCLUDED.league_id,
            venue = EXCLUDED.venue,
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            processed_at = EXCLUDED.processed_at,
            data_quality_score = EXCLUDED.data_quality_score
        """
        )
        await session.execute(insert_query, silver_data)

    elif bronze_table == "raw_odds":
        insert_query = text(
            """
            INSERT INTO silver_odds
            (match_id, bookmaker, home_win_odds, draw_odds, away_win_odds, timestamp, source, processed_at, data_quality_score)
            VALUES (:match_id, :bookmaker, :home_win_odds, :draw_odds, :away_win_odds, :timestamp, :source, :processed_at, :data_quality_score)
            ON CONFLICT (match_id, bookmaker, timestamp) DO UPDATE SET
            home_win_odds = EXCLUDED.home_win_odds,
            draw_odds = EXCLUDED.draw_odds,
            away_win_odds = EXCLUDED.away_win_odds,
            source = EXCLUDED.source,
            processed_at = EXCLUDED.processed_at,
            data_quality_score = EXCLUDED.data_quality_score
        """
        )
        await session.execute(insert_query, silver_data)

    elif bronze_table == "raw_scores":
        insert_query = text(
            """
            INSERT INTO silver_scores
            (match_id, home_score, away_score, match_status, timestamp, source, processed_at, data_quality_score)
            VALUES (:match_id, :home_score, :away_score, :match_status, :timestamp, :source, :processed_at, :data_quality_score)
            ON CONFLICT (match_id, timestamp) DO UPDATE SET
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            match_status = EXCLUDED.match_status,
            source = EXCLUDED.source,
            processed_at = EXCLUDED.processed_at,
            data_quality_score = EXCLUDED.data_quality_score
        """
        )
        await session.execute(insert_query, silver_data)


async def _process_bronze_record(
    session, record, table_name: str, data_cleaner, quality_monitor
):
    """处理单个Bronze记录"""
    try:
        raw_data = record.data
        source = record.source
        record_id = record.id

        # 数据清洗
        cleaned_data = await data_cleaner.clean_football_data(
            raw_data,
            data_type=table_name.replace("raw_", ""),
            source=source,
        )

        # 数据质量验证
        quality_result = await quality_monitor.validate_data_quality(
            cleaned_data,
            data_type=table_name.replace("raw_", ""),
        )

        if quality_result.get("passed", False):
            # 转换为Silver层格式
            silver_data = await _transform_to_silver_format(
                cleaned_data, table_name, record_id
            )

            # 保存到Silver层
            await _save_to_silver_layer(session, silver_data, table_name)

            # 标记Bronze记录为已处理
            update_query = _get_update_query(table_name)
            if update_query:
                await session.execute(update_query, {"record_id": record_id})

            return True
        else:
            logger.warning(f"数据质量验证失败: {quality_result.get('issues', [])}")
            return False
    except Exception as e:
        logger.error(f"处理记录 {record.id} 时出错: {str(e)}")
        return False


async def _process_bronze_table(
    session, table_name: str, batch_size: int, data_cleaner, quality_monitor
):
    """处理单个Bronze表"""
    logger.info(f"处理 {table_name} 表的数据...")

    # 验证表名
    valid_tables = ["raw_matches", "raw_odds", "raw_scores"]
    if table_name not in valid_tables:
        logger.error(f"非法表名: {table_name}")
        return 0

    # 获取查询语句
    from sqlalchemy import text

    query = _get_bronze_table_query(table_name)
    if not query:
        logger.error(f"不支持的表名: {table_name}")
        return 0

    # 执行查询
    result = await session.execute(text(query), {"batch_size": batch_size})
    bronze_records = result.fetchall()

    if not bronze_records:
        logger.info(f"{table_name} 表没有需要处理的数据")
        return 0

    # 处理记录
    logger.info(f"清洗和验证 {table_name} 数据...")
    records_processed = 0

    for record in bronze_records:
        if await _process_bronze_record(
            session, record, table_name, data_cleaner, quality_monitor
        ):
            records_processed += 1

        if records_processed % 100 == 0:
            logger.info(f"已处理 {records_processed} 条记录...")

    logger.info(f"完成 {table_name} 表的批次处理，处理了 {len(bronze_records)} 条记录")
    return records_processed


@app.task(base=BaseDataTask, bind=True)
def process_bronze_to_silver(self, batch_size: int = 1000):
    """
    Bronze层到Silver层数据处理任务

    Args:
        batch_size: 批处理大小
    """
    try:
        logger.info("开始执行Bronze到Silver数据处理任务")

        async def _process_data():
            """异步处理数据"""
            async with get_async_session() as session:
                # 初始化处理器
                data_cleaner = FootballDataCleaner()
                quality_monitor = DataQualityMonitor()

                records_processed = 0
                batches_processed = 0

                # 从Bronze层读取原始数据
                logger.info("从Bronze层读取原始数据...")
                bronze_tables = [
                    "raw_matches",
                    "raw_odds",
                    "raw_scores",
                ]

                for table_name in bronze_tables:
                    try:
                        table_records = await _process_bronze_table(
                            session,
                            table_name,
                            batch_size,
                            data_cleaner,
                            quality_monitor,
                        )
                        records_processed += table_records
                        batches_processed += 1
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logger.error(f"处理 {table_name} 表时出错: {str(e)}")
                        continue

                return records_processed, batches_processed

        # 运行异步数据处理
        records_processed, batches_processed = asyncio.run(_process_data())

        logger.info(
            f"Bronze到Silver数据处理任务完成: 处理了 {records_processed} 条记录，{batches_processed} 个批次"
        )

        return {
            "status": "success",
            "records_processed": records_processed,
            "batches_processed": batches_processed,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Bronze到Silver数据处理任务失败: {str(exc)}")
        raise