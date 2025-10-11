import pytest
from sqlalchemy import text
from src.database.models.team import Team
from src.database.models.match import Match

"""
使用TestContainers的数据库测试
提供真实的数据库测试环境
"""


@pytest.mark.integration
class TestDatabaseWithContainers:
    """使用真实PostgreSQL容器的数据库测试"""

    def test_database_connection(self, test_database_engine):
        """测试数据库连接"""
        with test_database_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_database_tables_created(self, test_database_engine):
        """测试数据库表是否正确创建"""
        # 检查表是否存在
        with test_database_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            tables = [row[0] for row in result.fetchall()]

            # 验证核心表存在
            assert "leagues" in tables
            assert "teams" in tables
            assert "matches" in tables

    def test_create_and_retrieve_team(self, test_db_session):
        """测试创建和检索球队"""

        # 创建球队
        team = Team(name="Test Team", short_name="TT", country="Test Country")
        test_db_session.add(team)
        test_db_session.commit()

        # 检索球队
        retrieved = test_db_session.query(Team).filter_by(name="Test Team").first()
        assert retrieved is not None
        assert retrieved.short_name == "TT"
        assert retrieved.country == "Test Country"

    def test_create_and_retrieve_league(self, test_db_session):
        """测试创建和检索联赛"""
        from src.database.models.league import League

        # 创建联赛
        league = League(name="Test League", country="Test Country", season="2024-2025")
        test_db_session.add(league)
        test_db_session.commit()

        # 检索联赛
        retrieved = test_db_session.query(League).filter_by(name="Test League").first()
        assert retrieved is not None
        assert retrieved.country == "Test Country"
        assert retrieved.season == "2024-2025"

    def test_create_and_retrieve_match(self, test_db_session, sample_test_data):
        """测试创建和检索比赛"""

        # 使用sample_test_data中的预创建数据
        match = sample_test_data["match"]

        # 检索比赛
        retrieved = test_db_session.query(Match).filter_by(id=match.id).first()
        assert retrieved is not None
        assert retrieved.home_team_id == sample_test_data["home_team"].id
        assert retrieved.away_team_id == sample_test_data["away_team"].id
        assert retrieved.status == "SCHEDULED"

    def test_team_match_relationship(self, test_db_session, sample_test_data):
        """测试球队和比赛的关系"""
        from src.database.models.match import Match

        # 查询主队比赛
        home_team = sample_test_data["home_team"]
        home_matches = (
            test_db_session.query(Match).filter_by(home_team_id=home_team.id).all()
        )

        assert len(home_matches) == 1
        assert home_matches[0].away_team_id == sample_test_data["away_team"].id

        # 查询客队比赛
        away_team = sample_test_data["away_team"]
        away_matches = (
            test_db_session.query(Match).filter_by(away_team_id=away_team.id).all()
        )

        assert len(away_matches) == 1
        assert away_matches[0].home_team_id == sample_test_data["home_team"].id

    def test_league_match_relationship(self, test_db_session, sample_test_data):
        """测试联赛和比赛的关系"""

        # 查询联赛下的比赛
        league = sample_test_data["league"]
        matches = test_db_session.query(Match).filter_by(league_id=league.id).all()

        assert len(matches) == 1
        assert matches[0].home_team_id == sample_test_data["home_team"].id


@pytest.mark.integration
class TestRedisWithContainers:
    """使用真实Redis容器的缓存测试"""

    def test_redis_connection(self, test_redis_client):
        """测试Redis连接"""
        assert test_redis_client.ping() is True

    def test_redis_set_and_get(self, test_redis_client):
        """测试Redis设置和获取"""
        # 设置值
        test_redis_client.set("test:key", "test:value")

        # 获取值
        value = test_redis_client.get("test:key")
        assert value == "test:value"

    def test_redis_set_with_ttl(self, test_redis_client):
        """测试Redis设置带TTL的值"""
        # 设置带TTL的值
        test_redis_client.set("test:ttl", "test:value", ex=60)

        # 检查值存在
        value = test_redis_client.get("test:ttl")
        assert value == "test:value"

        # 检查TTL
        ttl = test_redis_client.ttl("test:ttl")
        assert 0 < ttl <= 60

    def test_redis_delete(self, test_redis_client):
        """测试Redis删除"""
        # 设置值
        test_redis_client.set("test:delete", "test:value")

        # 确保值存在
        assert test_redis_client.exists("test:delete") == 1

        # 删除值
        result = test_redis_client.delete("test:delete")

        # 确保值被删除
        assert result == 1
        assert test_redis_client.exists("test:delete") == 0

    def test_redis_hash_operations(self, test_redis_client):
        """测试Redis哈希操作"""
        # 设置哈希字段
        test_redis_client.hset("test:hash", "field1", "value1")
        test_redis_client.hset("test:hash", "field2", "value2")

        # 获取哈希字段
        value1 = test_redis_client.hget("test:hash", "field1")
        value2 = test_redis_client.hget("test:hash", "field2")

        assert value1 == "value1"
        assert value2 == "value2"

        # 获取所有哈希字段
        all_fields = test_redis_client.hgetall("test:hash")
        assert all_fields == {"field1": "value1", "field2": "value2"}

    def test_redis_list_operations(self, test_redis_client):
        """测试Redis列表操作"""
        # 推送元素到列表
        test_redis_client.lpush("test:list", "item1", "item2", "item3")

        # 获取列表长度
        length = test_redis_client.llen("test:list")
        assert length == 3

        # 获取列表元素
        items = test_redis_client.lrange("test:list", 0, -1)
        assert items == ["item3", "item2", "item1"]


@pytest.mark.integration
class TestDatabaseRedisIntegration:
    """数据库和Redis集成测试"""

    def test_cache_team_data(
        self, test_db_session, test_redis_client, sample_test_data
    ):
        """测试缓存球队数据"""
        team = sample_test_data["home_team"]

        # 缓存球队数据
        cache_key = f"team:{team.id}"
        team_data = {
            "id": team.id,
            "name": team.name,
            "short_name": team.short_name,
            "country": team.country,
        }

        # 使用Redis哈希存储球队数据
        test_redis_client.hset(cache_key, mapping=team_data)

        # 从缓存检索数据
        cached_data = test_redis_client.hgetall(cache_key)

        assert int(cached_data["id"]) == team.id
        assert cached_data["name"] == team.name
        assert cached_data["short_name"] == team.short_name
        assert cached_data["country"] == team.country

    def test_cache_match_prediction(
        self, test_db_session, test_redis_client, sample_test_data
    ):
        """测试缓存比赛预测数据"""
        match = sample_test_data["match"]

        # 模拟预测数据
        prediction_data = {
            "match_id": match.id,
            "home_win_prob": 0.65,
            "draw_prob": 0.25,
            "away_win_prob": 0.10,
            "predicted_home_score": 2,
            "predicted_away_score": 1,
            "confidence": 0.85,
        }

        # 缓存预测数据
        cache_key = f"prediction:{match.id}"
        test_redis_client.set(cache_key, str(prediction_data), ex=3600)

        # 从缓存检索数据
        cached_value = test_redis_client.get(cache_key)
        assert cached_value is not None
        assert str(match.id) in cached_value
