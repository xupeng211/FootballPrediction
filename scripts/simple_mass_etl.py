#!/usr/bin/env python3
"""
简化批量ETL脚本 / Simple Mass ETL Script

快速将28,704条原始数据转换为matches表
"""

import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def simple_etl():
    """执行简化的ETL处理"""
    logger.info("🚀 开始简化ETL处理28,704条数据")

    # 连接数据库
    engine = create_engine("postgresql://postgres:postgres@db:5432/football_prediction")

    with engine.connect() as conn:
        # 获取总数据量
        total_result = conn.execute(
            text("SELECT COUNT(*) FROM raw_match_data WHERE processed = FALSE")
        )
        total_count = total_result.scalar()
        logger.info(f"📊 发现 {total_count} 条未处理数据")

        # 分批处理
        batch_size = 5000
        processed = 0
        matches_added = 0

        for offset in range(0, total_count, batch_size):
            logger.info(f"📦 处理批次 {offset // batch_size + 1} (offset: {offset})")

            # 获取一批数据
            query = text("""
                SELECT id, external_id, match_data, collected_at
                FROM raw_match_data
                WHERE processed = FALSE
                ORDER BY collected_at
                LIMIT :limit OFFSET :offset
            """)

            result = conn.execute(query, {"limit": batch_size, "offset": offset})
            rows = result.fetchall()

            batch_matches = []
            batch_processed_ids = []

            for row in rows:
                raw_id, external_id, match_data, collected_at = row

                try:
                    # 解析数据
                    data = (
                        json.loads(match_data)
                        if isinstance(match_data, str)
                        else match_data
                    )
                    raw_data = data.get("raw_data", {})

                    # 提取关键信息
                    home_team = raw_data.get("home", {})
                    away_team = raw_data.get("away", {})
                    league_info = raw_data.get("league_info", {})

                    if not all(
                        [
                            home_team.get("id"),
                            away_team.get("id"),
                            league_info.get("id"),
                        ]
                    ):
                        continue

                    # 检查是否已存在
                    existing_check = conn.execute(
                        text("SELECT id FROM matches WHERE external_id = :external_id"),
                        {"external_id": str(raw_data.get("id", external_id))},
                    ).scalar()

                    if existing_check:
                        batch_processed_ids.append(raw_id)
                        continue

                    # 准备插入数据
                    match_time = raw_data.get("time", "")
                    match_date = None
                    if match_time:
                        try:
                            match_date = datetime.strptime(match_time, "%d.%m.%Y %H:%M")
                        except Exception:
                            pass

                    match_data_insert = {
                        "external_id": str(raw_data.get("id", external_id)),
                        "home_team_name": home_team.get(
                            "longName", home_team.get("name", "")
                        ),
                        "away_team_name": away_team.get(
                            "longName", away_team.get("name", "")
                        ),
                        "home_team_external_id": str(home_team.get("id", "")),
                        "away_team_external_id": str(away_team.get("id", "")),
                        "league_name": league_info.get("name", ""),
                        "league_external_id": str(league_info.get("id", "")),
                        "match_date": match_date,
                        "status": data.get("status", {})
                        .get("reason", {})
                        .get("short", "unknown"),
                        "home_score": home_team.get("score", 0),
                        "away_score": away_team.get("score", 0),
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    }

                    batch_matches.append(match_data_insert)
                    batch_processed_ids.append(raw_id)

                except Exception:
                    logger.warning(f"⚠️ 跳过记录 {raw_id}: {e}")
                    continue

            # 批量插入matches
            if batch_matches:
                insert_query = text("""
                    INSERT INTO matches (
                        external_id, home_team_name, away_team_name,
                        home_team_external_id, away_team_external_id,
                        league_name, league_external_id, match_date, status,
                        home_score, away_score, created_at, updated_at
                    ) VALUES (
                        :external_id, :home_team_name, :away_team_name,
                        :home_team_external_id, :away_team_external_id,
                        :league_name, :league_external_id, :match_date, :status,
                        :home_score, :away_score, :created_at, :updated_at
                    )
                """)

                conn.execute(insert_query, batch_matches)
                matches_added += len(batch_matches)

            # 标记为已处理
            if batch_processed_ids:
                update_query = text(
                    "UPDATE raw_match_data SET processed = TRUE WHERE id = :raw_id"
                )
                for raw_id in batch_processed_ids:
                    conn.execute(update_query, {"raw_id": raw_id})

            processed += len(rows)
            conn.commit()

            logger.info(
                f"✅ 批次完成: 处理 {len(rows)} 条，新增 {len(batch_matches)} 场比赛"
            )

        logger.info("🎉 ETL完成!")
        logger.info(f"📊 总计处理: {processed} 条原始数据")
        logger.info(f"🏆 新增比赛: {matches_added} 场")


if __name__ == "__main__":
    simple_etl()
