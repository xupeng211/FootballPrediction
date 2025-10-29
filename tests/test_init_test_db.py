# 测试数据库初始化脚本
import asyncio

from sqlalchemy import create_engine, text

from src.database.base import Base


async def create_test_tables():
    """创建测试表"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


async def init_test_database():
    """初始化测试数据库"""
    engine = await create_test_tables()

    # 插入测试数据
    with engine.connect() as conn:
        # 插入测试团队
        conn.execute(
            text(
                """
            INSERT INTO teams (id, name, founded_year, logo_url) VALUES
            (1, 'Test Team 1', 1900, 'logo1.png'),
            (2, 'Test Team 2', 1920, 'logo2.png')
        """
            )
        )

        # 插入测试比赛
        conn.execute(
            text(
                """
            INSERT INTO matches (id, home_team_id, away_team_id, match_date, venue) VALUES
            (1, 1, 2, '2024-01-01', 'Test Stadium'),
            (2, 2, 1, '2024-01-02', 'Another Stadium')
        """
            )
        )

    return engine


if __name__ == "__main__":
    asyncio.run(init_test_database())
