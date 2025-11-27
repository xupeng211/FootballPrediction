#!/usr/bin/env python3
"""
批量数据处理脚本 / Mass Data Processing Script

直接处理28,704条原始数据，转换为matches表记录。
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_raw_data_batch():
    """批量处理原始数据"""
    logger.info("🚀 开始批量处理28,704条原始数据")

    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/football_prediction")
    engine = create_engine(database_url)
    Session = sessionmaker(engine)

    processed_count = 0
    matches_added = 0

    try:
        with Session() as session:
            # 分批处理，每次处理1000条
            batch_size = 1000
            offset = 0

            while True:
                # 获取一批未处理的数据
                query = text("""
                    SELECT id, external_id, match_data, collected_at
                    FROM raw_match_data
                    WHERE processed = FALSE
                    ORDER BY collected_at
                    LIMIT :batch_size OFFSET :offset
                """)

                result = await session.execute(query, {"batch_size": batch_size, "offset": offset})
                rows = result.fetchall()

                if not rows:
                    break

                logger.info(f"📦 处理批次 {offset//batch_size + 1}: {len(rows)} 条记录")

                for row in rows:
                    try:
                        raw_id, external_id, match_data, collected_at = row

                        # 解析JSON数据
                        if isinstance(match_data, str):
                            data = json.loads(match_data)
                        else:
                            data = match_data

                        # 提取比赛信息
                        raw_data = data.get('raw_data', {})
                        status = data.get('status', {})

                        # 获取基本信息
                        home_team = raw_data.get('home', {})
                        away_team = raw_data.get('away', {})
                        league_info = raw_data.get('league_info', {})

                        if not all([home_team.get('id'), away_team.get('id'), league_info.get('id')]):
                            continue

                        # 检查match是否已存在
                        existing_match = await session.execute(
                            text("SELECT id FROM matches WHERE external_id = :external_id"),
                            {"external_id": str(raw_data.get('id', external_id))}
                        )

                        if existing_match.fetchone():
                            # 标记为已处理
                            await session.execute(
                                text("UPDATE raw_match_data SET processed = TRUE WHERE id = :raw_id"),
                                {"raw_id": raw_id}
                            )
                            continue

                        # 插入match记录
                        match_insert = text("""
                            INSERT INTO matches (
                                external_id,
                                home_team_name,
                                away_team_name,
                                home_team_external_id,
                                away_team_external_id,
                                league_name,
                                league_external_id,
                                match_date,
                                status,
                                home_score,
                                away_score,
                                created_at,
                                updated_at
                            ) VALUES (
                                :external_id,
                                :home_team_name,
                                :away_team_name,
                                :home_team_external_id,
                                :away_team_external_id,
                                :league_name,
                                :league_external_id,
                                :match_date,
                                :status,
                                :home_score,
                                :away_score,
                                :created_at,
                                :updated_at
                            )
                        """)

                        await session.execute(match_insert, {
                            'external_id': str(raw_data.get('id', external_id)),
                            'home_team_name': home_team.get('longName', home_team.get('name', '')),
                            'away_team_name': away_team.get('longName', away_team.get('name', '')),
                            'home_team_external_id': str(home_team.get('id', '')),
                            'away_team_external_id': str(away_team.get('id', '')),
                            'league_name': league_info.get('name', ''),
                            'league_external_id': str(league_info.get('id', '')),
                            'match_date': datetime.strptime(raw_data.get('time', ''), '%d.%m.%Y %H:%M') if raw_data.get('time') else None,
                            'status': status.get('reason', {}).get('short', 'unknown'),
                            'home_score': home_team.get('score', 0),
                            'away_score': away_team.get('score', 0),
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        })

                        matches_added += 1

                        # 标记原始数据为已处理
                        await session.execute(
                            text("UPDATE raw_match_data SET processed = TRUE WHERE id = :raw_id"),
                            {"raw_id": raw_id}
                        )

                        processed_count += 1

                    except Exception as e:
                        logger.error(f"❌ 处理记录 {row[0]} 失败: {e}")
                        continue

                # 提交当前批次
                await session.commit()
                logger.info(f"✅ 批次完成，已处理 {processed_count} 条记录，添加 {matches_added} 场比赛")

                offset += batch_size

                # 如果这批数据少于batch_size，说明已经处理完了
                if len(rows) < batch_size:
                    break

    except Exception as e:
        logger.error(f"❌ 批量处理失败: {e}")
        raise

    logger.info("🎉 批量处理完成！")
    logger.info(f"📊 总计处理: {processed_count} 条原始数据")
    logger.info(f"🏆 新增比赛: {matches_added} 场")

if __name__ == "__main__":
    asyncio.run(process_raw_data_batch())
