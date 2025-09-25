"""
数据库业务逻辑约束测试

测试 CHECK 约束和触发器的正确性，验证非法数据插入时约束能正确触发。

测试环境设计说明：
1. 使用 SQLite in-memory 数据库 (:memory:) 的原因：
   - 完全隔离：每次测试都使用全新的内存数据库，避免测试间的数据污染
   - 高性能：内存数据库比磁盘数据库快几个数量级，提升测试执行速度
   - 零依赖：无需安装和配置 MySQL/PostgreSQL 等外部数据库服务
   - CI友好：在各种环境中都能快速启动，无需额外的基础设施

2. 自动创建 schema (Base.metadata.create_all) 的原因：
   - 测试自包含：每次测试运行都会自动创建完整的数据库结构
   - 版本同步：确保测试使用的表结构与当前代码中的模型定义完全一致
   - 零配置：无需预先准备测试数据库或运行migration脚本
   - 约束验证：自动包含所有模型中定义的CHECK约束和外键约束
"""

import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.database.config import get_test_database_config
from src.database.connection import get_session, initialize_test_database
from src.database.models import League, MarketType, Match, Odds, Team


def _setup_sqlite_constraints(engine):
    """
    为SQLite数据库设置自定义约束和触发器

    SQLite与PostgreSQL/MySQL的差异处理：
    1. 外键约束：SQLite默认禁用外键检查，需要通过PRAGMA foreign_keys=ON启用
    2. 自定义触发器：SQLite不支持某些高级约束，需要用触发器模拟
    3. 友好错误信息：为外键违反提供更清晰的错误消息，便于测试验证

    这确保了测试在SQLite环境中的行为与生产环境(PostgreSQL)保持一致。
    """
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """启用SQLite的外键约束检查"""
        cursor = dbapi_connection.cursor()
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # 直接在引擎上创建触发器
    with engine.connect() as connection:
        # 创建触发器检查主队和客队不能相同
        connection.execute(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS check_different_teams_insert
            BEFORE INSERT ON matches
            FOR EACH ROW
            WHEN NEW.home_team_id = NEW.away_team_id
            BEGIN
                SELECT RAISE(ABORT, 'Home team and away team cannot be the same');
            END;
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS check_different_teams_update
            BEFORE UPDATE ON matches
            FOR EACH ROW
            WHEN NEW.home_team_id = NEW.away_team_id
            BEGIN
                SELECT RAISE(ABORT, 'Home team and away team cannot be the same');
            END;
        """
            )
        )

        # 创建触发器检查外键约束并提供友好错误信息
        connection.execute(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS check_home_team_exists
            BEFORE INSERT ON matches
            FOR EACH ROW
            WHEN (SELECT COUNT(*) FROM teams WHERE id = NEW.home_team_id) = 0
            BEGIN
                SELECT RAISE(ABORT, 'Home team does not exist');
            END;
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS check_away_team_exists
            BEFORE INSERT ON matches
            FOR EACH ROW
            WHEN (SELECT COUNT(*) FROM teams WHERE id = NEW.away_team_id) = 0
            BEGIN
                SELECT RAISE(ABORT, 'Away team does not exist');
            END;
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS check_league_exists
            BEFORE INSERT ON matches
            FOR EACH ROW
            WHEN (SELECT COUNT(*) FROM leagues WHERE id = NEW.league_id) = 0
            BEGIN
                SELECT RAISE(ABORT, 'League does not exist');
            END;
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE TRIGGER IF NOT EXISTS check_match_exists_for_odds
            BEFORE INSERT ON odds
            FOR EACH ROW
            WHEN (SELECT COUNT(*) FROM matches WHERE id = NEW.match_id) = 0
            BEGIN
                SELECT RAISE(ABORT, 'Match does not exist');
            END;
        """
            )
        )

        connection.commit()


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """初始化测试数据库以进行约束测试

    测试数据库初始化策略：
    1. 使用 initialize_test_database() 专门为测试设计的初始化函数
    2. 避免异步引擎相关问题，仅创建同步连接（测试场景下足够）
    3. 自动执行 Base.metadata.create_all() 创建所有表和约束
    4. 为SQLite设置额外的触发器以模拟生产环境的约束行为

    这种设计确保测试环境完全自包含且与生产环境行为一致。
    """
    from src.database.connection import _db_manager

    config = get_test_database_config()
    initialize_test_database(config)

    # 为SQLite设置额外的约束和触发器
    if _db_manager._sync_engine:
        _setup_sqlite_constraints(_db_manager._sync_engine)


class TestMatchConstraints:
    """
    测试比赛表的约束条件

    验证 Match 模型中定义的所有 CHECK 约束和外键约束：
    - 比分范围约束（0-99）
    - 比赛时间约束（>2000-01-01）
    - 主客队不同约束
    - 外键引用约束（球队、联赛必须存在）

    每个测试都使用唯一的时间戳标识符，确保测试数据不冲突。
    """

    def setup_method(self):
        """设置测试数据"""
        # 使用时间戳创建唯一标识符避免测试间数据冲突
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳

        with get_session() as db:
            # 创建测试联赛
            self.test_league = League(
                league_name=f"Test League Match {timestamp}",
                country="Test Country",
                api_league_id=900000 + timestamp % 10000,
            )
            db.add(self.test_league)

            # 创建测试球队
            self.test_team1 = Team(
                team_name=f"Test Team 1 Match {timestamp}",
                team_code=f"MT1_{timestamp % 10000}",
                country="Test Country",
                api_team_id=800000 + timestamp % 10000,
            )
            self.test_team2 = Team(
                team_name=f"Test Team 2 Match {timestamp}",
                team_code=f"MT2_{timestamp % 10000}",
                country="Test Country",
                api_team_id=800001 + timestamp % 10000,
            )
            db.add_all([self.test_team1, self.test_team2])
            db.commit()

            # 获取ID用于后续测试
            self.league_id = self.test_league.id
            self.team1_id = self.test_team1.id
            self.team2_id = self.test_team2.id

    def teardown_method(self):
        """清理测试数据"""
        with get_session() as db:
            # 删除测试数据
            db.query(Match).filter(Match.league_id == self.league_id).delete()
            db.query(Team).filter(Team.id.in_([self.team1_id, self.team2_id])).delete()
            db.query(League).filter(League.id == self.league_id).delete()
            db.commit()

    def test_valid_match_creation(self):
        """测试创建有效的比赛记录"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=2,
                away_score=1,
                home_ht_score=1,
                away_ht_score=0,
            )
            db.add(match)
            db.commit()  # 应该成功
            assert match.id is not None

    def test_score_range_constraints_negative(self):
        """测试比分不能为负数"""
        with get_session() as db:
            # 测试主队比分为负数
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=-1,  # 无效比分
            )
            db.add(match)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含约束名称
            assert "ck_matches_home_score_range" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_score_range_constraints_too_high(self):
        """测试比分不能超过99"""
        with get_session() as db:
            # 测试主队比分超过99
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=100,  # 无效比分
            )
            db.add(match)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含约束名称
            assert "ck_matches_home_score_range" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_match_time_constraint(self):
        """测试比赛时间必须大于2000-01-01"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="1999-00",
                match_time=datetime(
                    1999, 12, 31, 15, 0, tzinfo=timezone.utc
                ),  # 无效时间
            )
            db.add(match)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含约束名称
            assert "ck_matches_match_time_range" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_same_team_constraint(self):
        """测试主队和客队不能相同"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team1_id,  # 主队和客队相同
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(match)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含预期的错误消息
            assert "Home team and away team cannot be the same" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_nonexistent_team_constraint(self):
        """测试不存在的球队ID"""
        with get_session() as db:
            match = Match(
                home_team_id=999999,  # 不存在的球队ID
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(match)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含预期的错误消息
            assert "Home team does not exist" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_nonexistent_league_constraint(self):
        """测试不存在的联赛ID"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=999999,  # 不存在的联赛ID
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(match)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含预期的错误消息
            assert "League does not exist" in str(exc_info.value)
            db.rollback()  # 回滚事务


class TestOddsConstraints:
    """
    测试赔率表的约束条件

    验证 Odds 模型中定义的约束：
    - 赔率数值约束（>1.01 或 NULL）
    - 盘口数值约束（0-10）
    - 外键约束（比赛必须存在）
    - NULL值的正确处理

    这些约束确保赔率数据的合理性和完整性。
    """

    def setup_method(self):
        """设置测试数据"""
        # 使用时间戳创建唯一标识符避免测试间数据冲突
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳

        with get_session() as db:
            # 创建测试联赛
            self.test_league = League(
                league_name=f"Test League Odds {timestamp}",
                country="Test Country",
                api_league_id=700000 + timestamp % 10000,
            )
            db.add(self.test_league)

            # 创建测试球队
            self.test_team1 = Team(
                team_name=f"Test Team 1 Odds {timestamp}",
                team_code=f"OT1_{timestamp % 10000}",
                country="Test Country",
                api_team_id=600000 + timestamp % 10000,
            )
            self.test_team2 = Team(
                team_name=f"Test Team 2 Odds {timestamp}",
                team_code=f"OT2_{timestamp % 10000}",
                country="Test Country",
                api_team_id=600001 + timestamp % 10000,
            )
            db.add_all([self.test_team1, self.test_team2])

            # 先提交联赛和球队，获取它们的ID
            db.commit()

            # 创建测试比赛，现在可以使用有效的ID
            self.test_match = Match(
                home_team_id=self.test_team1.id,
                away_team_id=self.test_team2.id,
                league_id=self.test_league.id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(self.test_match)
            db.commit()

            self.match_id = self.test_match.id

    def teardown_method(self):
        """清理测试数据"""
        with get_session() as db:
            # 删除测试数据
            db.query(Odds).filter(Odds.match_id == self.match_id).delete()
            db.query(Match).filter(Match.id == self.match_id).delete()
            db.query(Team).filter(
                Team.id.in_([self.test_team1.id, self.test_team2.id])
            ).delete()
            db.query(League).filter(League.id == self.test_league.id).delete()
            db.commit()

    def test_valid_odds_creation(self):
        """测试创建有效的赔率记录"""
        with get_session() as db:
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("2.50"),
                draw_odds=Decimal("3.20"),
                away_odds=Decimal("1.85"),
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)
            db.commit()  # 应该成功
            assert odds.id is not None

    def test_odds_minimum_value_constraint(self):
        """测试赔率必须大于1.01"""
        with get_session() as db:
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("1.00"),  # 无效赔率
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含约束名称
            assert "ck_odds_home_odds_range" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_odds_boundary_value(self):
        """测试赔率边界值"""
        with get_session() as db:
            # 测试正好1.01的边界值（应该失败）
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("1.01"),  # 边界值，应该失败
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含约束名称
            assert "ck_odds_home_odds_range" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_odds_valid_boundary(self):
        """测试有效的赔率边界值"""
        with get_session() as db:
            # 测试1.02的值（应该成功）
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("1.02"),  # 有效值
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)
            db.commit()  # 应该成功
            assert odds.id is not None

    def test_odds_match_reference_constraint(self):
        """测试赔率表的比赛引用约束"""
        with get_session() as db:
            odds = Odds(
                match_id=999999,  # 不存在的比赛ID
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("2.00"),
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含预期的错误消息
            assert "Match does not exist" in str(exc_info.value)
            db.rollback()  # 回滚事务

    def test_odds_null_values_allowed(self):
        """测试赔率的NULL值是被允许的"""
        with get_session() as db:
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=None,  # NULL值应该被允许
                draw_odds=None,
                away_odds=None,
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)
            db.commit()  # 应该成功
            assert odds.id is not None


class TestConstraintsIntegration:
    """
    测试约束的集成场景

    验证复杂场景下的约束行为：
    - 同时违反多个约束时的错误处理
    - UPDATE操作中的约束检查
    - 跨表约束的协同工作

    这些测试确保数据库约束在实际业务场景中的正确性。
    """

    def test_multiple_constraints_violation(self):
        """测试同时违反多个约束"""
        # 使用时间戳创建唯一标识符避免测试间数据冲突
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳

        with get_session() as db:
            # 这个测试需要创建一些基础数据
            league = League(
                league_name=f"Test League Multi {timestamp}",
                country="Test Country",
                api_league_id=500000 + timestamp % 10000,
            )
            team1 = Team(
                team_name=f"Test Team 1 Multi {timestamp}",
                team_code=f"IT1_{timestamp % 10000}",
                country="Test Country",
                api_team_id=400000 + timestamp % 10000,
            )
            team2 = Team(
                team_name=f"Test Team 2 Multi {timestamp}",
                team_code=f"IT2_{timestamp % 10000}",
                country="Test Country",
                api_team_id=400001 + timestamp % 10000,
            )
            db.add_all([league, team1, team2])
            db.commit()

            # 尝试创建一个违反多个约束的比赛
            match = Match(
                home_team_id=team1.id,
                away_team_id=team2.id,
                league_id=league.id,
                season="2024-25",
                match_time=datetime(
                    1999, 1, 1, 15, 0, tzinfo=timezone.utc
                ),  # 时间约束违反
                home_score=-5,  # 比分约束违反
                away_score=150,  # 比分约束违反
            )
            db.add(match)

            # 应该触发第一个遇到的约束错误
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证捕获到了约束错误（可能是时间或比分约束）
            error_msg = str(exc_info.value)
            assert (
                "ck_matches_match_time_range" in error_msg
                or "ck_matches_home_score_range" in error_msg
                or "ck_matches_away_score_range" in error_msg
            )
            db.rollback()  # 回滚事务

            # 清理
            db.rollback()
            db.query(Team).filter(Team.id.in_([team1.id, team2.id])).delete()
            db.query(League).filter(League.id == league.id).delete()
            db.commit()

    def test_constraints_with_updates(self):
        """测试约束在UPDATE操作中的行为"""
        # 使用时间戳创建唯一标识符避免测试间数据冲突
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳

        with get_session() as db:
            # 创建基础数据
            league = League(
                league_name=f"Test League Update {timestamp}",
                country="Test Country",
                api_league_id=300000 + timestamp % 10000,
            )
            team1 = Team(
                team_name=f"Test Team 1 Update {timestamp}",
                team_code=f"UT1_{timestamp % 10000}",
                country="Test Country",
                api_team_id=200000 + timestamp % 10000,
            )
            team2 = Team(
                team_name=f"Test Team 2 Update {timestamp}",
                team_code=f"UT2_{timestamp % 10000}",
                country="Test Country",
                api_team_id=200001 + timestamp % 10000,
            )
            db.add_all([league, team1, team2])
            # 先提交获取ID
            db.commit()

            # 创建有效的比赛
            match = Match(
                home_team_id=team1.id,
                away_team_id=team2.id,
                league_id=league.id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=2,
                away_score=1,
            )
            db.add(match)
            db.commit()

            # 尝试更新为无效值
            match.home_score = -1

            # 捕获约束违反异常
            with pytest.raises(IntegrityError) as exc_info:
                db.commit()

            # 验证错误信息包含约束名称
            assert "ck_matches_home_score_range" in str(exc_info.value)
            db.rollback()  # 回滚事务

            # 清理
            db.rollback()
            db.query(Match).filter(Match.id == match.id).delete()
            db.query(Team).filter(Team.id.in_([team1.id, team2.id])).delete()
            db.query(League).filter(League.id == league.id).delete()
            db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
