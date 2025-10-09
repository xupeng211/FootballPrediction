"""
from ..base.base_task import BaseDataTask
from src.database.connection import get_async_session
from src.database.models.raw_data import RawMatchData, RawOddsData, RawScoresData

数据转换任务

负责将原始数据从Bronze层转换到Silver层。
"""



logger = logging.getLogger(__name__)


def _get_bronze_table_query(table_name: str) -> str:
    """获取Bronze层数据查询语句"""
    queries = {
        "raw_match_data": """
            SELECT id, match_data, created_at, updated_at, processed
            FROM raw_match_data
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
        "raw_odds_data": """
            SELECT id, odds_data, created_at, updated_at, processed
            FROM raw_odds_data
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """,
        "raw_scores_data": """
            SELECT id, scores_data, created_at, updated_at, processed
            FROM raw_scores_data
            WHERE processed = false
            ORDER BY created_at ASC
            LIMIT :batch_size
        """
    }
    return queries.get(table_name)


def _get_update_query(table_name: str):
    """获取更新处理状态的查询语句"""
    return text(f"""
        UPDATE {table_name}
        SET processed = true, updated_at = CURRENT_TIMESTAMP
        WHERE id = :record_id
    """)


async def _transform_to_silver_format(cleaned_data, bronze_table, record_id):
    """将数据转换为Silver层格式"""
    try:
        if bronze_table == "raw_match_data":
            # 转换比赛数据
            match_info = cleaned_data.get("match", {})
            return {
                "match_id": match_info.get("id"),
                "home_team": match_info.get("home_team"),
                "away_team": match_info.get("away_team"),
                "match_date": match_info.get("match_date"),
                "league_id": match_info.get("league_id"),
                "season": match_info.get("season"),
                "venue": match_info.get("venue"),
                "status": match_info.get("status"),
                "score": match_info.get("score", {}),
                "events": match_info.get("events", []),
                "raw_data_id": record_id,
                "processed_at": datetime.now().isoformat()
            }

        elif bronze_table == "raw_odds_data":
            # 转换赔率数据
            odds_info = cleaned_data.get("odds", {})
            return {
                "match_id": odds_info.get("match_id"),
                "bookmaker": odds_info.get("bookmaker"),
                "home_win": odds_info.get("home_win"),
                "draw": odds_info.get("draw"),
                "away_win": odds_info.get("away_win"),
                "over_under": odds_info.get("over_under", {}),
                "asian_handicap": odds_info.get("asian_handicap", {}),
                "raw_data_id": record_id,
                "processed_at": datetime.now().isoformat()
            }

        elif bronze_table == "raw_scores_data":
            # 转换比分数据
            scores_info = cleaned_data.get("scores", {})
            return {
                "match_id": scores_info.get("match_id"),
                "current_score": scores_info.get("current_score"),
                "minute": scores_info.get("minute"),
                "status": scores_info.get("status"),
                "events": scores_info.get("events", []),
                "raw_data_id": record_id,
                "processed_at": datetime.now().isoformat()
            }

        else:
            raise ValueError(f"未知的Bronze表: {bronze_table}")

    except Exception as e:
        logger.error(f"转换数据失败 {bronze_table}:{record_id}: {str(e)}")
        return None


async def _save_to_silver_layer(session, silver_data, bronze_table):
    """保存数据到Silver层"""
    try:
        if bronze_table == "raw_match_data":
            # 保存到processed_matches表
            query = text("""
                INSERT INTO processed_matches (
                    match_id, home_team, away_team, match_date, league_id,
                    season, venue, status, score, events, raw_data_id, processed_at
                ) VALUES (
                    :match_id, :home_team, :away_team, :match_date, :league_id,
                    :season, :venue, :status, :score, :events, :raw_data_id, :processed_at
                )
                ON CONFLICT (match_id) DO UPDATE SET
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    match_date = EXCLUDED.match_date,
                    league_id = EXCLUDED.league_id,
                    season = EXCLUDED.season,
                    venue = EXCLUDED.venue,
                    status = EXCLUDED.status,
                    score = EXCLUDED.score,
                    events = EXCLUDED.events,
                    processed_at = EXCLUDED.processed_at
            """)

        elif bronze_table == "raw_odds_data":
            # 保存到processed_odds表
            query = text("""
                INSERT INTO processed_odds (
                    match_id, bookmaker, home_win, draw, away_win,
                    over_under, asian_handicap, raw_data_id, processed_at
                ) VALUES (
                    :match_id, :bookmaker, :home_win, :draw, :away_win,
                    :over_under, :asian_handicap, :raw_data_id, :processed_at
                )
                ON CONFLICT (match_id, bookmaker) DO UPDATE SET
                    home_win = EXCLUDED.home_win,
                    draw = EXCLUDED.draw,
                    away_win = EXCLUDED.away_win,
                    over_under = EXCLUDED.over_under,
                    asian_handicap = EXCLUDED.asian_handicap,
                    processed_at = EXCLUDED.processed_at
            """)

        elif bronze_table == "raw_scores_data":
            # 保存到processed_scores表
            query = text("""
                INSERT INTO processed_scores (
                    match_id, current_score, minute, status,
                    events, raw_data_id, processed_at
                ) VALUES (
                    :match_id, :current_score, :minute, :status,
                    :events, :raw_data_id, :processed_at
                )
                ON CONFLICT (match_id) DO UPDATE SET
                    current_score = EXCLUDED.current_score,
                    minute = EXCLUDED.minute,
                    status = EXCLUDED.status,
                    events = EXCLUDED.events,
                    processed_at = EXCLUDED.processed_at
            """)

        await session.execute(query, silver_data)
        await session.commit()

        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"保存Silver层数据失败: {str(e)}")
        return False


async def _process_bronze_record(
    session,
    record_id: int,
    bronze_table: str,
    data_field: str
) -> bool:
    """处理单条Bronze记录"""
    try:
        # 1. 获取原始数据
        if bronze_table == "raw_match_data":
            query = select(RawMatchData).where(RawMatchData.id == record_id)
        elif bronze_table == "raw_odds_data":
            query = select(RawOddsData).where(RawOddsData.id == record_id)
        elif bronze_table == "raw_scores_data":
            query = select(RawScoresData).where(RawScoresData.id == record_id)
        else:
            logger.error(f"未知的Bronze表: {bronze_table}")
            return False

        result = await session.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            logger.warning(f"找不到记录 {bronze_table}:{record_id}")
            return False

        # 2. 解析JSON数据
        raw_data = getattr(record, data_field)
        if isinstance(raw_data, str):
            cleaned_data = json.loads(raw_data)
        else:
            cleaned_data = raw_data

        # 3. 转换为Silver格式
        silver_data = await _transform_to_silver_format(
            cleaned_data, bronze_table, record_id
        )

        if not silver_data:
            logger.error(f"数据转换失败 {bronze_table}:{record_id}")
            return False

        # 4. 保存到Silver层
        success = await _save_to_silver_layer(session, silver_data, bronze_table)

        if success:
            # 5. 更新处理状态
            update_query = _get_update_query(bronze_table)
            await session.execute(update_query, {"record_id": record_id})
            await session.commit()

        return success

    except Exception as e:
        logger.error(f"处理Bronze记录失败 {bronze_table}:{record_id}: {str(e)}")
        await session.rollback()
        return False


async def _process_bronze_table(
    bronze_table: str,
    batch_size: int = 1000
) -> Dict[str, int]:
    """处理整个Bronze表"""
    processed_count = 0
    failed_count = 0

    # 确定数据字段
    data_field_map = {
        "raw_match_data": "match_data",
        "raw_odds_data": "odds_data",
        "raw_scores_data": "scores_data"
    }
    data_field = data_field_map.get(bronze_table)

    async with get_async_session() as session:
        while True:
            # 获取未处理的记录
            query = text(_get_bronze_table_query(bronze_table))
            result = await session.execute(query, {"batch_size": batch_size})
            records = result.fetchall()

            if not records:
                break

            logger.info(f"处理 {bronze_table}: 找到 {len(records)} 条未处理记录")

            # 处理每条记录
            for record in records:
                success = await _process_bronze_record(
                    session,
                    record.id,
                    bronze_table,
                    data_field
                )

                if success:
                    processed_count += 1
                else:
                    failed_count += 1

    return {
        "processed": processed_count,
        "failed": failed_count,
        "total": processed_count + failed_count
    }


@app.task(base=BaseDataTask, bind=True)
def process_bronze_to_silver(self, batch_size: int = 1000):
    """
    将Bronze层数据转换到Silver层

    Args:
        batch_size: 每批处理的记录数
    """
    logger.info(f"开始处理Bronze到Silver转换，批大小: {batch_size}")

    try:
        async def _transformation_task():
            tables_to_process = [
                "raw_match_data",
                "raw_odds_data",
                "raw_scores_data"
            ]




            results = {}
            total_processed = 0
            total_failed = 0

            for table in tables_to_process:
                logger.info(f"处理表: {table}")
                table_result = await _process_bronze_table(table, batch_size)
                results[table] = table_result

                total_processed += table_result["processed"]
                total_failed += table_result["failed"]

                logger.info(
                    f"表 {table} 处理完成: 成功 {table_result['processed']}, "
                    f"失败 {table_result['failed']}"
                )

            return results, total_processed, total_failed

        # 运行异步转换任务
        results, total_processed, total_failed = asyncio.run(_transformation_task())

        logger.info(
            f"Bronze到Silver转换完成: 总计成功 {total_processed}, "
            f"失败 {total_failed}"
        )

        return {
            "status": "success",
            "results": results,
            "total_processed": total_processed,
            "total_failed": total_failed,
            "batch_size": batch_size,
            "execution_time": datetime.now().isoformat(),
        }

    except Exception as exc:
        retry_config = TaskRetryConfig.RETRY_CONFIGS.get("process_bronze_to_silver", {})
        max_retries = retry_config.get("max_retries", TaskRetryConfig.MAX_RETRIES)
        retry_delay = retry_config.get("retry_delay", TaskRetryConfig.DEFAULT_RETRY_DELAY)

        if self.request.retries < max_retries:
            logger.warning(f"数据转换失败，将在{retry_delay}秒后重试: {str(exc)}")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f"数据转换任务最终失败: {str(exc)}")
            raise