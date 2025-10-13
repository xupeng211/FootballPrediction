#!/usr/bin/env python3
"""
测试数据加载脚本
用于集成测试和 E2E 测试环境
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import argparse
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://test_user:test_pass@localhost:5433/football_test')

# 测试数据定义
TEAMS = [
    {"name": "Test Team A", "city": "Test City A", "founded": 2000},
    {"name": "Test Team B", "city": "Test City B", "founded": 2001},
    {"name": "Test Team C", "city": "Test City C", "founded": 2002},
    {"name": "Test Team D", "city": "Test City D", "founded": 2003},
]

LEAGUES = [
    {"name": "Test League 1", "country": "Test Country", "level": 1},
    {"name": "Test League 2", "country": "Test Country", "level": 2},
]

PLAYERS = [
    {"name": "Test Player 1", "position": "Forward", "age": 25, "team": "Test Team A"},
    {"name": "Test Player 2", "position": "Midfielder", "age": 27, "team": "Test Team B"},
    {"name": "Test Player 3", "position": "Defender", "age": 29, "team": "Test Team C"},
    {"name": "Test Player 4", "position": "Goalkeeper", "age": 31, "team": "Test Team D"},
]

MATCHES = [
    {"home_team": "Test Team A", "away_team": "Test Team B", "date": "2025-01-20", "status": "UPCOMING"},
    {"home_team": "Test Team C", "away_team": "Test Team D", "date": "2025-01-21", "status": "UPCOMING"},
    {"home_team": "Test Team A", "away_team": "Test Team C", "date": "2025-01-15", "status": "COMPLETED", "home_score": 2, "away_score": 1},
    {"home_team": "Test Team B", "away_team": "Test Team D", "date": "2025-01-16", "status": "COMPLETED", "home_score": 1, "away_score": 1},
]

USERS = [
    {"username": "test_user_1", "email": "test1@example.com", "password": "test_pass_1"},
    {"username": "test_user_2", "email": "test2@example.com", "password": "test_pass_2"},
    {"username": "test_admin", "email": "admin@example.com", "password": "admin_pass", "role": "admin"},
]

PREDICTIONS = [
    {"user": "test_user_1", "match": "Test Team A vs Test Team B", "prediction": "HOME_WIN", "confidence": 0.75},
    {"user": "test_user_2", "match": "Test Team C vs Test Team D", "prediction": "DRAW", "confidence": 0.60},
    {"user": "test_user_1", "match": "Test Team A vs Test Team C", "prediction": "HOME_WIN", "confidence": 0.80},
]

async def load_test_data(reset: bool = False):
    """加载测试数据到数据库"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text

        # 创建数据库连接
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # 如果需要重置数据
            if reset:
                logger.info("Resetting test data...")
                await session.execute(text("TRUNCATE TABLE predictions RESTART IDENTITY CASCADE"))
                await session.execute(text("TRUNCATE TABLE matches RESTART IDENTITY CASCADE"))
                await session.execute(text("TRUNCATE TABLE players RESTART IDENTITY CASCADE"))
                await session.execute(text("TRUNCATE TABLE teams RESTART IDENTITY CASCADE"))
                await session.execute(text("TRUNCATE TABLE leagues RESTART IDENTITY CASCADE"))
                await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
                await session.commit()
                logger.info("✅ Test data reset complete")

            # 检查是否已有数据
            result = await session.execute(text("SELECT COUNT(*) FROM teams"))
            team_count = result.scalar()

            if team_count > 0 and not reset:
                logger.info(f"Test data already exists ({team_count} teams). Skipping load.")
                return

            logger.info("Loading test data...")

            # 插入联赛数据
            for league in LEAGUES:
                await session.execute(
                    text("INSERT INTO leagues (name, country, level) VALUES (:name, :country, :level)"),
                    league
                )
            await session.commit()
            logger.info(f"✅ Inserted {len(LEAGUES)} leagues")

            # 插入队伍数据
            for team in TEAMS:
                await session.execute(
                    text("INSERT INTO teams (name, city, founded) VALUES (:name, :city, :founded)"),
                    team
                )
            await session.commit()
            logger.info(f"✅ Inserted {len(TEAMS)} teams")

            # 插入球员数据
            for player in PLAYERS:
                await session.execute(
                    text("""
                        INSERT INTO players (name, position, age, team_name)
                        VALUES (:name, :position, :age, :team)
                    """),
                    player
                )
            await session.commit()
            logger.info(f"✅ Inserted {len(PLAYERS)} players")

            # 插入比赛数据
            for match in MATCHES:
                # 获取队伍ID
                home_result = await session.execute(
                    text("SELECT id FROM teams WHERE name = :name"),
                    {"name": match["home_team"]}
                )
                away_result = await session.execute(
                    text("SELECT id FROM teams WHERE name = :name"),
                    {"name": match["away_team"]}
                )

                home_id = home_result.scalar()
                away_id = away_result.scalar()

                if home_id and away_id:
                    match_data = {
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "match_date": match["date"],
                        "status": match["status"],
                        "home_score": match.get("home_score"),
                        "away_score": match.get("away_score"),
                    }
                    await session.execute(
                        text("""
                            INSERT INTO matches (home_team_id, away_team_id, match_date, status, home_score, away_score)
                            VALUES (:home_team_id, :away_team_id, :match_date, :status, :home_score, :away_score)
                        """),
                        match_data
                    )
            await session.commit()
            logger.info(f"✅ Inserted {len(MATCHES)} matches")

            # 插入用户数据
            for user in USERS:
                await session.execute(
                    text("""
                        INSERT INTO users (username, email, password_hash, role, created_at, updated_at)
                        VALUES (:username, :email, :password, :role, :created_at, :updated_at)
                    """),
                    {
                        "username": user["username"],
                        "email": user["email"],
                        "password": user["password"],  # 实际应该使用 hash
                        "role": user.get("role", "user"),
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
            await session.commit()
            logger.info(f"✅ Inserted {len(USERS)} users")

            # 插入预测数据
            for prediction in PREDICTIONS:
                await session.execute(
                    text("""
                        INSERT INTO predictions (user_id, match_id, prediction, confidence, created_at)
                        VALUES (
                            (SELECT id FROM users WHERE username = :user),
                            (SELECT id FROM matches WHERE home_team_id = (SELECT id FROM teams WHERE name = :home)
                             AND away_team_id = (SELECT id FROM teams WHERE name = :away)),
                            :prediction, :confidence, :created_at
                        )
                    """),
                    {
                        "user": prediction["user"],
                        "home": prediction["match"].split(" vs ")[0],
                        "away": prediction["match"].split(" vs ")[1],
                        "prediction": prediction["prediction"],
                        "confidence": prediction["confidence"],
                        "created_at": datetime.now(timezone.utc),
                    }
                )
            await session.commit()
            logger.info(f"✅ Inserted {len(PREDICTIONS)} predictions")

            logger.info("✅ All test data loaded successfully")

        await engine.dispose()

    except ImportError:
        logger.warning("SQLAlchemy not available, creating mock data...")
        create_mock_data_files()
    except Exception as e:
        logger.error(f"Failed to load test data: {e}")
        raise

def create_mock_data_files():
    """创建模拟数据文件"""
    os.makedirs("tests/fixtures", exist_ok=True)

    # 保存测试数据到 JSON 文件
    test_data = {
        "teams": TEAMS,
        "leagues": LEAGUES,
        "players": PLAYERS,
        "matches": MATCHES,
        "users": USERS,
        "predictions": PREDICTIONS,
    }

    with open("tests/fixtures/test_data.json", "w") as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)

    logger.info("✅ Mock data files created in tests/fixtures/")

async def load_redis_test_data():
    """加载 Redis 测试数据"""
    try:
        import redis
        from json import dumps

        redis_url = os.getenv('REDIS_URL', 'redis://:test_pass@localhost:6380/1')
        r = redis.from_url(redis_url)

        # 测试连接
        r.ping()
        logger.info("✅ Redis connection successful")

        # 加载缓存数据
        test_cache_data = {
            "user:test_user_1:profile": dumps({"username": "test_user_1", "email": "test1@example.com"}),
            "user:test_user_2:profile": dumps({"username": "test_user_2", "email": "test2@example.com"}),
            "match:upcoming": dumps({"count": 2, "matches": MATCHES[:2]}),
            "prediction:stats": dumps({"total": len(PREDICTIONS), "accuracy": 0.75}),
        }

        for key, value in test_cache_data.items():
            r.setex(key, 3600, value)  # 1小时过期

        logger.info(f"✅ Loaded {len(test_cache_data)} Redis cache entries")

    except ImportError:
        logger.warning("Redis not available, skipping Redis test data")
    except Exception as e:
        logger.error(f"Failed to load Redis test data: {e}")

async def load_kafka_test_data():
    """加载 Kafka 测试数据"""
    try:
        from kafka import KafkaProducer
        from json import dumps
        import time

        kafka_broker = os.getenv('KAFKA_BROKER', 'localhost:9093')
        topic_prefix = os.getenv('KAFKA_TOPIC_PREFIX', 'test_')

        producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None
        )

        # 发送测试事件
        test_events = [
            {"event": "match_created", "data": MATCHES[0]},
            {"event": "prediction_made", "data": PREDICTIONS[0]},
            {"event": "user_registered", "data": USERS[0]},
        ]

        for event in test_events:
            topic = f"{topic_prefix}events"
            producer.send(topic, key=event["event"], value=event)

        producer.flush()
        producer.close()

        logger.info(f"✅ Sent {len(test_events)} Kafka test events")

    except ImportError:
        logger.warning("Kafka not available, skipping Kafka test data")
    except Exception as e:
        logger.error(f"Failed to load Kafka test data: {e}")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Load test data for integration and E2E tests")
    parser.add_argument("--env", default="test", help="Environment (test, staging)")
    parser.add_argument("--reset", action="store_true", help="Reset existing data before loading")
    parser.add_argument("--redis", action="store_true", help="Load Redis test data")
    parser.add_argument("--kafka", action="store_true", help="Load Kafka test data")
    parser.add_argument("--all", action="store_true", help="Load all test data (DB, Redis, Kafka)")

    args = parser.parse_args()

    logger.info(f"Loading test data for {args.env} environment...")

    # 加载数据库测试数据
    await load_test_data(reset=args.reset)

    # 加载 Redis 测试数据
    if args.redis or args.all:
        await load_redis_test_data()

    # 加载 Kafka 测试数据
    if args.kafka or args.all:
        await load_kafka_test_data()

    logger.info("✅ Test data loading completed")

if __name__ == "__main__":
    asyncio.run(main())