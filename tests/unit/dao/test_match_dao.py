"""
MatchDAO单元测试
MatchDAO Unit Tests

测试MatchDAO的核心功能，验证DAO层与模型的集成。
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

# 导入Match相关模块
from src.database.dao.schemas import MatchCreate, MatchUpdate
from src.database.dao.match_dao import MatchDAO
from src.database.models.match import Match
from src.database.dao.exceptions import (
    RecordNotFoundError,
    ValidationError,
    DatabaseConnectionError,
)


class TestMatchDAO:
    """MatchDAO测试类"""

    @pytest_asyncio.fixture
    async def async_session(self) -> AsyncSession:
        """创建测试数据库会话"""
        # 使用内存SQLite数据库进行测试
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            future=True
        )

        # 创建所有表
        from src.database.base import BaseModel
        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.create_all)

        # 创建会话工厂
        async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建并返回会话
        async with async_session_factory() as session:
            yield session

    @pytest_asyncio.fixture
    async def match_dao(self, async_session: AsyncSession) -> MatchDAO:
        """创建MatchDAO实例"""
        return MatchDAO(model=Match, session=async_session)

    @pytest_asyncio.fixture
    async def sample_match_data(self) -> dict:
        """测试比赛数据"""
        return {
            "home_team_id": 1,  # 添加必需的外键ID
            "away_team_id": 2,  # 添加必需的外键ID
            "home_team_name": "Arsenal",
            "away_team_name": "Chelsea",
            "league_id": 1,
            "match_time": datetime.utcnow() + timedelta(hours=24),
            "match_date": datetime.utcnow() + timedelta(hours=24),
            "venue": "Emirates Stadium",
            "status": "scheduled",
            "home_score": 0,
            "away_score": 0
        }

    @pytest_asyncio.fixture
    async def created_match(self, match_dao: MatchDAO, sample_match_data: dict) -> Match:
        """创建测试比赛"""
        match_create = MatchCreate(**sample_match_data)
        return await match_dao.create(obj_in=match_create)

    @pytest_asyncio.fixture
    async def sample_matches(self) -> List[dict]:
        """测试比赛数据列表"""
        now = datetime.utcnow()
        return [
            {
                "home_team_id": 201,
                "away_team_id": 202,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "league_id": 1,
                "match_time": now + timedelta(hours=12),
                "match_date": now + timedelta(hours=12),
                "venue": "Stadium A",
                "status": "scheduled",
                "home_score": 0,
                "away_score": 0
            },
            {
                "home_team_id": 203,
                "away_team_id": 204,
                "home_team_name": "Team C",
                "away_team_name": "Team D",
                "league_id": 2,
                "match_time": now + timedelta(hours=36),
                "match_date": now + timedelta(hours=36),
                "venue": "Stadium B",
                "status": "scheduled",
                "home_score": 0,
                "away_score": 0
            },
            {
                "home_team_id": 205,
                "away_team_id": 206,
                "home_team_name": "Team E",
                "away_team_name": "Team F",
                "league_id": 1,
                "match_time": now + timedelta(hours=1),
                "match_date": now + timedelta(hours=1),
                "venue": "Stadium C",
                "status": "scheduled",
                "home_score": 0,
                "away_score": 0
            }
        ]

    # ==================== 基础CRUD测试 ====================

    @pytest.mark.asyncio
    async def test_create_match(self, match_dao: MatchDAO, sample_match_data: dict):
        """测试创建比赛"""
        # 创建比赛
        match_create = MatchCreate(**sample_match_data)
        created_match = await match_dao.create(obj_in=match_create)

        # 验证返回结果
        assert created_match is not None
        assert created_match.id is not None
        assert created_match.home_team_name == sample_match_data["home_team_name"]
        assert created_match.away_team_name == sample_match_data["away_team_name"]
        assert created_match.league_id == sample_match_data["league_id"]
        assert created_match.venue == sample_match_data["venue"]
        assert created_match.status == sample_match_data["status"]
        assert created_match.created_at is not None

        # 验证数据库中的记录
        retrieved_match = await match_dao.get(created_match.id)
        assert retrieved_match is not None
        assert retrieved_match.home_team_name == sample_match_data["home_team_name"]

    @pytest.mark.asyncio
    async def test_get_match(self, match_dao: MatchDAO, created_match: Match):
        """测试获取比赛"""
        # 获取比赛
        retrieved_match = await match_dao.get(created_match.id)

        # 验证结果
        assert retrieved_match is not None
        assert retrieved_match.id == created_match.id
        assert retrieved_match.home_team_name == created_match.home_team_name
        assert retrieved_match.away_team_name == created_match.away_team_name

    @pytest.mark.asyncio
    async def test_get_nonexistent_match(self, match_dao: MatchDAO):
        """测试获取不存在的比赛"""
        # 使用不存在的ID
        nonexistent_match = await match_dao.get(99999)
        assert nonexistent_match is None

    @pytest.mark.asyncio
    async def test_update_match(self, match_dao: MatchDAO, created_match: Match):
        """测试更新比赛"""
        # 准备更新数据
        update_data = MatchUpdate(
            venue="Wembley Stadium",
            status="live"
        )

        # 执行更新
        updated_match = await match_dao.update(
            db_obj=created_match,
            obj_in=update_data
        )

        # 验证更新结果
        assert updated_match.venue == "Wembley Stadium"
        assert updated_match.status == "live"
        assert updated_match.home_team_name == created_match.home_team_name  # 未更新字段保持不变

    @pytest.mark.asyncio
    async def test_delete_match(self, match_dao: MatchDAO, created_match: Match):
        """测试删除比赛"""
        match_id = created_match.id

        # 执行删除
        delete_result = await match_dao.delete(id=match_id)
        assert delete_result is True

        # 验证删除结果
        deleted_match = await match_dao.get(match_id)
        assert deleted_match is None

    @pytest.mark.asyncio
    async def test_crud_lifecycle(self, match_dao: MatchDAO, sample_match_data: dict):
        """测试完整的CRUD生命周期"""
        # 1. Create
        match_create = MatchCreate(**sample_match_data)
        created_match = await match_dao.create(obj_in=match_create)
        assert created_match.id is not None

        # 2. Read
        retrieved_match = await match_dao.get(created_match.id)
        assert retrieved_match is not None
        assert retrieved_match.home_team_name == sample_match_data["home_team_name"]

        # 3. Update
        update_data = MatchUpdate(venue="Updated Venue")
        updated_match = await match_dao.update(
            db_obj=retrieved_match,
            obj_in=update_data
        )
        assert updated_match.venue == "Updated Venue"

        # 4. Delete
        delete_result = await match_dao.delete(id=updated_match.id)
        assert delete_result is True

        # 验证删除
        final_match = await match_dao.get(updated_match.id)
        assert final_match is None

    # ==================== 业务方法测试 ====================

    @pytest.mark.asyncio
    async def test_get_upcoming_matches(self, match_dao: MatchDAO, sample_matches: list[dict]):
        """测试获取即将开始的比赛"""
        # 创建测试数据
        now = datetime.utcnow()
        for match_data in sample_matches:
            match_create = MatchCreate(**match_data)
            await match_dao.create(obj_in=match_create)

        # 获取未来24小时内的比赛
        upcoming_matches = await match_dao.get_upcoming_matches(hours=24)

        # 验证结果：只应该包含未来24小时内的比赛
        assert len(upcoming_matches) >= 1
        for match in upcoming_matches:
            assert match.match_time >= now
            assert match.match_time <= now + timedelta(hours=24)
            assert match.status in ['scheduled', 'postponed']

        # 获取未来12小时内的比赛（更严格的时间范围）
        upcoming_12h = await match_dao.get_upcoming_matches(hours=12)
        for match in upcoming_12h:
            assert match.match_time <= now + timedelta(hours=12)

    @pytest.mark.asyncio
    async def test_get_upcoming_matches_with_league_filter(self, match_dao: MatchDAO, sample_matches: list[dict]):
        """测试按联赛过滤获取即将开始的比赛"""
        # 创建测试数据
        for match_data in sample_matches:
            match_create = MatchCreate(**match_data)
            await match_dao.create(obj_in=match_create)

        # 获取联赛1的未来比赛
        league_1_matches = await match_dao.get_upcoming_matches(hours=48, league_id=1)

        # 验证结果
        for match in league_1_matches:
            assert match.league_id == 1
            assert match.status in ['scheduled', 'postponed']

    @pytest.mark.asyncio
    async def test_get_matches_by_league(self, match_dao: MatchDAO, sample_matches: list[dict]):
        """测试根据联赛获取比赛"""
        # 创建测试数据
        for match_data in sample_matches:
            match_create = MatchCreate(**match_data)
            await match_dao.create(obj_in=match_create)

        # 获取联赛1的比赛
        league_1_matches = await match_dao.get_matches_by_league(league_id=1)

        # 验证结果
        assert len(league_1_matches) >= 1
        for match in league_1_matches:
            assert match.league_id == 1

        # 获取联赛2的比赛
        league_2_matches = await match_dao.get_matches_by_league(league_id=2)
        assert len(league_2_matches) >= 1
        for match in league_2_matches:
            assert match.league_id == 2

    @pytest.mark.asyncio
    async def test_get_matches_by_league_with_filters(self, match_dao: MatchDAO):
        """测试带过滤条件的联赛比赛查询"""
        # 创建不同状态的比赛
        now = datetime.utcnow()
        matches_data = [
            {
                "home_team_id": 101,
                "away_team_id": 102,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "league_id": 1,
                "match_time": now + timedelta(hours=1),
                "status": "scheduled"
            },
            {
                "home_team_id": 103,
                "away_team_id": 104,
                "home_team_name": "Team C",
                "away_team_name": "Team D",
                "league_id": 1,
                "match_time": now - timedelta(hours=1),
                "status": "finished"
            }
        ]

        for match_data in matches_data:
            match_create = MatchCreate(**match_data)
            await match_dao.create(obj_in=match_create)

        # 获取联赛1的已完场比赛
        finished_matches = await match_dao.get_matches_by_league(
            league_id=1,
            status="finished"
        )

        # 验证结果
        assert len(finished_matches) >= 1
        for match in finished_matches:
            assert match.league_id == 1
            assert match.status == "finished"

    @pytest.mark.asyncio
    async def test_get_live_matches(self, match_dao: MatchDAO):
        """测试获取正在进行的比赛"""
        # 创建正在进行的比赛
        live_match_data = {
            "home_team_id": 105,
            "away_team_id": 106,
            "home_team_name": "Live Team 1",
            "away_team_name": "Live Team 2",
            "league_id": 1,
            "match_time": datetime.utcnow(),
            "status": "live"
        }

        match_create = MatchCreate(**live_match_data)
        await match_dao.create(obj_in=match_create)

        # 获取正在进行的比赛
        live_matches = await match_dao.get_live_matches()

        # 验证结果
        assert len(live_matches) >= 1
        for match in live_matches:
            assert match.status == "live"

    @pytest.mark.asyncio
    async def test_get_finished_matches(self, match_dao: MatchDAO):
        """测试获取已完成的比赛"""
        # 创建已完成的比赛
        finished_match_data = {
            "home_team_id": 107,
            "away_team_id": 108,
            "home_team_name": "Finished Team 1",
            "away_team_name": "Finished Team 2",
            "league_id": 1,
            "match_time": datetime.utcnow() - timedelta(hours=2),
            "status": "finished"
        }

        match_create = MatchCreate(**finished_match_data)
        await match_dao.create(obj_in=match_create)

        # 获取最近7天已完成的比赛
        finished_matches = await match_dao.get_finished_matches(days=7)

        # 验证结果
        assert len(finished_matches) >= 1
        for match in finished_matches:
            assert match.status == "finished"

    @pytest.mark.asyncio
    async def test_search_matches(self, match_dao: MatchDAO):
        """测试搜索比赛"""
        # 创建测试比赛
        search_match_data = {
            "home_team_id": 109,
            "away_team_id": 110,
            "home_team_name": "Arsenal",
            "away_team_name": "Chelsea",
            "league_id": 1,
            "match_time": datetime.utcnow() + timedelta(hours=24),
            "status": "scheduled"
        }

        match_create = MatchCreate(**search_match_data)
        await match_dao.create(obj_in=match_create)

        # 搜索包含"Arsenal"的比赛
        search_results = await match_dao.search_matches(keyword="Arsenal")

        # 验证结果
        assert len(search_results) >= 1
        for match in search_results:
            assert "Arsenal" in match.home_team or "Arsenal" in match.away_team

    @pytest.mark.asyncio
    async def test_get_match_count_by_status(self, match_dao: MatchDAO):
        """测试按状态统计比赛数量"""
        # 创建不同状态的比赛
        status_matches = [
            {
                "home_team_id": 111 + i,
                "away_team_id": 114 + i,
                "home_team_name": f"Team {i}",
                "away_team_name": f"Opponent {i}",
                "league_id": 1,
                "match_time": datetime.utcnow(),
                "status": status
            }
            for i, status in enumerate(["scheduled", "live", "finished"])
        ]

        for match_data in status_matches:
            match_create = MatchCreate(**match_data)
            await match_dao.create(obj_in=match_create)

        # 获取状态统计
        status_counts = await match_dao.get_match_count_by_status()

        # 验证结果
        assert isinstance(status_counts, dict)
        assert "scheduled" in status_counts
        assert "live" in status_counts
        assert "finished" in status_counts

    @pytest.mark.asyncio
    async def test_update_match_status(self, match_dao: MatchDAO, created_match: Match):
        """测试更新比赛状态"""
        # 更新比赛状态为"live"
        result = await match_dao.update_match_status(
            match_id=created_match.id,
            new_status="live"
        )

        # 验证更新结果
        assert result is True

        # 获取更新后的比赛验证
        updated_match = await match_dao.get(created_match.id)
        assert updated_match.status == "live"
        assert updated_match.updated_at is not None

    # ==================== 异常处理测试 ====================

    @pytest.mark.asyncio
    async def test_update_nonexistent_match_status(self, match_dao: MatchDAO):
        """测试更新不存在比赛的状态"""
        with pytest.raises(RecordNotFoundError):
            await match_dao.update_match_status(
                match_id=99999,
                new_status="live"
            )

    @pytest.mark.asyncio
    async def test_update_match_with_invalid_status(self, match_dao: MatchDAO, created_match: Match):
        """测试使用无效状态更新比赛"""
        with pytest.raises(ValidationError):
            await match_dao.update_match_status(
                match_id=created_match.id,
                new_status="invalid_status"
            )

    @pytest.mark.asyncio
    async def test_get_upcoming_matches_with_invalid_parameters(self, match_dao: MatchDAO):
        """测试使用无效参数获取即将开始的比赛"""
        with pytest.raises(ValidationError):
            await match_dao.get_upcoming_matches(hours=0)  # hours必须大于0

        with pytest.raises(ValidationError):
            await match_dao.get_upcoming_matches(limit=0)  # limit必须大于0

    @pytest.mark.asyncio
    async def test_search_matches_with_short_keyword(self, match_dao: MatchDAO):
        """测试使用过短关键词搜索比赛"""
        with pytest.raises(ValidationError):
            await match_dao.search_matches(keyword="a")  # 关键词至少2个字符

    @pytest.mark.asyncio
    async def test_get_by_teams(self, match_dao: MatchDAO, sample_match_data: dict):
        """测试根据主客队获取比赛"""
        # 创建比赛
        match_create = MatchCreate(**sample_match_data)
        created_match = await match_dao.create(obj_in=match_create)

        # 根据主客队查找比赛
        found_match = await match_dao.get_by_teams(
            home_team=sample_match_data["home_team_name"],
            away_team=sample_match_data["away_team_name"],
            match_time=sample_match_data["match_time"]
        )

        # 验证结果
        assert found_match is not None
        assert found_match.id == created_match.id
        assert found_match.home_team_name == sample_match_data["home_team_name"]
        assert found_match.away_team_name == sample_match_data["away_team_name"]

    @pytest.mark.asyncio
    async def test_count_matches(self, match_dao: MatchDAO, sample_match_data: dict):
        """测试统计比赛数量"""
        # 创建比赛
        match_create = MatchCreate(**sample_match_data)
        await match_dao.create(obj_in=match_create)

        # 统计比赛数量
        count = await match_dao.count()

        # 验证结果
        assert count >= 1
        assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_exists_match(self, match_dao: MatchDAO, created_match: Match):
        """测试检查比赛是否存在"""
        # 检查存在的比赛
        exists = await match_dao.exists(filters={"id": created_match.id})
        assert exists is True

        # 检查不存在的比赛
        not_exists = await match_dao.exists(filters={"id": 99999})
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_bulk_create_matches(self, match_dao: MatchDAO):
        """测试批量创建比赛"""
        # 准备批量数据
        match_data_list = [
            MatchCreate(**{
                "home_team_id": 117 + i,
                "away_team_id": 120 + i,
                "home_team_name": f"Team {i}",
                "away_team_name": f"Opponent {i}",
                "league_id": 1,
                "match_time": datetime.utcnow() + timedelta(hours=i),
                "status": "scheduled"
            })
            for i in range(1, 4)
        ]

        # 批量创建
        created_matches = await match_dao.bulk_create(objects_in=match_data_list)

        # 验证结果
        assert len(created_matches) == 3
        for match in created_matches:
            assert match.id is not None
            assert match.home_team.startswith("Team")
            assert match.away_team.startswith("Opponent")

    @pytest.mark.asyncio
    async def test_get_multi_with_ordering(self, match_dao: MatchDAO):
        """测试带排序的批量查询"""
        # 创建多个比赛（不同时间）
        now = datetime.utcnow()
        for i in range(3):
            match_data = {
                "home_team_id": 123 + i,
                "away_team_id": 126 + i,
                "home_team_name": f"Team {i}",
                "away_team_name": f"Opponent {i}",
                "league_id": 1,
                "match_time": now + timedelta(hours=i),
                "status": "scheduled"
            }
            match_create = MatchCreate(**match_data)
            await match_dao.create(obj_in=match_create)

        # 按比赛时间升序查询
        matches_asc = await match_dao.get_multi(order_by="match_time")

        # 验证排序结果
        for i in range(1, len(matches_asc)):
            assert matches_asc[i].match_time >= matches_asc[i-1].match_time

        # 按比赛时间降序查询
        matches_desc = await match_dao.get_multi(order_by="-match_time")

        # 验证排序结果
        for i in range(1, len(matches_desc)):
            assert matches_desc[i].match_time <= matches_desc[i-1].match_time
