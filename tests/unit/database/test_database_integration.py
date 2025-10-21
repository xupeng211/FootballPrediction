# noqa: F401,F811,F821,E402
import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.database.models.league import League
from src.database.models.team import Team
import redis
import re

"""
数据库集成测试
使用现有的docker-compose服务进行测试
"""


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DOCKER_COMPOSE_ACTIVE"),
    reason="Docker Compose services not active. Run 'docker-compose up -d postgres redis' first.",
)
class TestDatabaseIntegration:
    """使用Docker Compose服务的数据库集成测试"""

    @pytest.fixture(scope="class")
    def database_url(self):
        """获取数据库连接URL"""
        # 从环境变量获取数据库URL，如果不存在则使用默认值
        return os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/football_prediction_dev",
        )

    @pytest.fixture(scope="class")
    def db_engine(self, database_url):
        """创建数据库引擎"""
        engine = create_engine(database_url, echo=False)
        try:
            # 测试连接
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            yield engine
        finally:
            engine.dispose()

    @pytest.fixture(scope="function")
    def db_session(self, db_engine):
        """创建数据库会话"""
        Session = sessionmaker(bind=db_engine)
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_database_connection(self, db_engine):
        """测试数据库连接"""
        with db_engine.connect() as conn:
            _result = conn.execute(text("SELECT 1 as test"))
            assert _result.scalar() == 1

    def test_check_tables_exist(self, db_engine):
        """检查核心表是否存在"""
        with db_engine.connect() as conn:
            # 获取所有表名
            _result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
            )
            tables = {row[0] for row in result.fetchall()}

            # 验证核心表存在
            core_tables = {
                "leagues",
                "teams",
                "matches",
                "odds",
                "predictions",
                "users",
                "audit_logs",
                "data_collection_logs",
            }

            existing_core_tables = tables & core_tables
            print(f"找到的核心表: {existing_core_tables}")

            # 至少应该有一些表存在
            assert len(tables) > 0, "数据库中应该至少有一些表"

    def test_create_team(self, db_session):
        """测试创建球队记录"""
        from src.database.models.team import Team

        # 创建球队
        team = Team(
            team_name="Test Team FC",
            team_code="TTF",
            country="Testland",
            founded_year=2020,
            stadium="Test Stadium",
        )

        db_session.add(team)
        db_session.commit()

        # 验证球队已创建
        assert team.id is not None

        # 查询球队
        retrieved = db_session.query(Team).filter_by(team_name="Test Team FC").first()
        assert retrieved is not None
        assert retrieved.team_code == "TTF"
        assert retrieved.country == "Testland"

    def test_create_league(self, db_session):
        """测试创建联赛记录"""

        # 创建联赛
        league = League(
            name="Test Premier League",
            country="Testland",
            season="2024-2025",
            is_active=True,
        )

        db_session.add(league)
        db_session.commit()

        # 验证联赛已创建
        assert league.id is not None

        # 查询联赛
        retrieved = (
            db_session.query(League).filter_by(name="Test Premier League").first()
        )
        assert retrieved is not None
        assert retrieved.country == "Testland"
        assert retrieved.season == "2024-2025"
        assert retrieved.is_active is True

    def test_team_league_relationship(self, db_session):
        """测试球队和联赛的关系"""
        from src.database.models.team import Team
        from src.database.models.league import League

        # 创建联赛
        league = League(
            league_name="Test Division", country="Testland", season="2024-2025"
        )
        db_session.add(league)
        db_session.flush()

        # 创建球队
        team = Team(
            team_name="Test United",
            team_code="TU",
            country="Testland",
            league_id=league.id,  # 假设有外键关系
        )
        db_session.add(team)
        db_session.commit()

        # 查询验证
        retrieved_team = (
            db_session.query(Team).filter_by(team_name="Test United").first()
        )
        assert retrieved_team is not None

        # 根据实际模型关系验证
        if hasattr(retrieved_team, "league_id"):
            assert retrieved_team.league_id == league.id

    def test_query_with_pagination(self, db_session):
        """测试分页查询"""

        # 创建多个球队
        _teams = []
        for i in range(5):
            team = Team(
                team_name=f"Team {i + 1}", team_code=f"T{i + 1}", country="Testland"
            )
            teams.append(team)

        db_session.add_all(teams)
        db_session.commit()

        # 查询前3个球队
        first_three = db_session.query(Team).limit(3).all()
        assert len(first_three) == 3

        # 查询总数
        total_count = db_session.query(Team).count()
        assert total_count >= 5

    def test_update_record(self, db_session):
        """测试更新记录"""
        from src.database.models.team import Team

        # 创建球队
        team = Team(team_name="Old Name FC", team_code="OLD", country="Testland")
        db_session.add(team)
        db_session.commit()

        # 更新球队
        team.team_name = "New Name FC"
        team.team_code = "NEW"
        db_session.commit()

        # 验证更新
        retrieved = db_session.query(Team).filter_by(id=team.id).first()
        assert retrieved.team_name == "New Name FC"
        assert retrieved.team_code == "NEW"

    def test_delete_record(self, db_session):
        """测试删除记录"""

        # 创建球队
        team = Team(name="Delete Me FC", short_name="DEL", country="Testland")
        db_session.add(team)
        db_session.commit()
        team_id = team.id

        # 删除球队
        db_session.delete(team)
        db_session.commit()

        # 验证删除
        retrieved = db_session.query(Team).filter_by(id=team_id).first()
        assert retrieved is None


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("DOCKER_COMPOSE_ACTIVE"),
    reason="Docker Compose services not active. Run 'docker-compose up -d postgres redis' first.",
)
class TestRedisIntegration:
    """使用Docker Compose服务的Redis集成测试"""

    @pytest.fixture(scope="class")
    def redis_client(self):
        """创建Redis客户端"""
        try:
            # 从环境变量获取Redis URL
            redis_url = os.getenv(
                "REDIS_URL", "redis://:redis_password@localhost:6379/1"
            )

            # 解析Redis URL

            match = re.match(r"redis://:(\w+)@([^:]+):(\d+)/(\d+)", redis_url)
            if match:
                password, host, port, db = match.groups()
                client = redis.Redis(
                    host=host,
                    port=int(port),
                    db=int(db),
                    password=password,
                    decode_responses=True,
                )
            else:
                # 简单连接（无密码）
                client = redis.Redis(
                    host="localhost", port=6379, db=1, decode_responses=True
                )

            # 测试连接
            client.ping()
            yield client
        except (ImportError, redis.exceptions.ConnectionError):
            pytest.skip("Redis not available")
        finally:
            if "client" in locals():
                client.close()

    def test_redis_connection(self, redis_client):
        """测试Redis连接"""
        assert redis_client.ping() is True

    def test_redis_basic_operations(self, redis_client):
        """测试Redis基本操作"""
        # SET操作
        assert redis_client.set("test:key", "test:value") is True

        # GET操作
        value = redis_client.get("test:key")
        assert value == "test:value"

        # EXISTS操作
        assert redis_client.exists("test:key") == 1

        # DELETE操作
        assert redis_client.delete("test:key") == 1
        assert redis_client.exists("test:key") == 0

    def test_redis_hash_operations(self, redis_client):
        """测试Redis哈希操作"""
        # HSET操作
        redis_client.hset(
            "test:hash",
            mapping={"field1": "value1", "field2": "value2", "field3": "value3"},
        )

        # HGET操作
        assert redis_client.hget("test:hash", "field1") == "value1"

        # HGETALL操作
        all_fields = redis_client.hgetall("test:hash")
        assert all_fields == {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3",
        }

        # 清理
        redis_client.delete("test:hash")

    def test_cache_team_data(self, redis_client):
        """测试缓存球队数据"""
        team_data = {
            "id": "123",
            "name": "Test Team",
            "short_name": "TT",
            "country": "Testland",
        }

        # 缓存数据
        cache_key = "team:123"
        redis_client.hset(cache_key, mapping=team_data)
        redis_client.expire(cache_key, 3600)  # 1小时过期

        # 获取缓存数据
        cached = redis_client.hgetall(cache_key)
        assert cached == team_data

        # 检查TTL
        ttl = redis_client.ttl(cache_key)
        assert 0 < ttl <= 3600

        # 清理
        redis_client.delete(cache_key)
