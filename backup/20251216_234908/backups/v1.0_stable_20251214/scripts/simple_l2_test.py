#!/usr/bin/env python3
"""
简化的L2数据收集测试 - 手动添加一些xG数据
Simple L2 Data Collection Test - Manually add some xG data
"""

import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def add_mock_xg_data():
    """为现有比赛添加模拟的xG数据"""

    # 创建数据库连接
    engine = create_engine("sqlite:///data/football_prediction.db")
    SessionLocal = sessionmaker(bind=engine)

    # 手动更新一些比赛的xG数据
    mock_xg_data = [
        # Manchester United vs Fulham
        (4506263, 1.8, 0.9),
        # Liverpool vs Ipswich Town
        (4506264, 2.1, 0.7),
        # Arsenal vs Wolverhampton
        (4506265, 2.5, 0.8),
        # Chelsea vs Manchester City
        (4506271, 1.2, 1.9),
        # Tottenham Hotspur vs Everton
        (4506281, 2.3, 1.1),
    ]

    try:
        with SessionLocal() as session:
            for fotmob_id, home_xg, away_xg in mock_xg_data:
                # 更新比赛的xG数据
                result = session.execute(
                    text("UPDATE matches SET home_xg = :home_xg, away_xg = :away_xg WHERE fotmob_id = :fotmob_id"),
                    {"home_xg": home_xg, "away_xg": away_xg, "fotmob_id": str(fotmob_id)}
                )
                if result.rowcount > 0:
                    logger.info(f"Updated xG data for match {fotmob_id}: {home_xg}-{away_xg}")

            session.commit()

            # 验证结果
            xg_matches = session.execute(
                text("SELECT COUNT(*) FROM matches WHERE home_xg IS NOT NULL AND away_xg IS NOT NULL")
            ).fetchone()[0]

            logger.info(f"Successfully added xG data to {xg_matches} matches")
            return xg_matches

    except Exception as e:
        logger.error(f"Error adding mock xG data: {e}")
        return 0

if __name__ == "__main__":
    logger.info("Adding mock xG data to test the pipeline...")
    xg_count = add_mock_xg_data()
    print(f"\n🎉 Mock xG data added to {xg_count} matches!")