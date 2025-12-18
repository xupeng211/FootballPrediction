"""
OddsDAO单元测试
OddsDAO Unit Tests

测试OddsDAO的所有功能，包括基础CRUD和业务方法。
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# 导入Odds相关模块
from src.database.dao.schemas import OddsCreate, OddsUpdate
from src.database.dao.odds_dao import OddsDAO
from src.database.models.odds import Odds
from src.database.dao.exceptions import (
    RecordNotFoundError,
    ValidationError,
)


class TestOddsDAO:
    """OddsDAO测试类"""

    @pytest_asyncio.fixture
    async def async_session(self) -> AsyncSession:
        """创建测试数据库会话"""
        # 使用内存SQLite数据库进行测试
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False, future=True
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
    async def odds_dao(self, async_session: AsyncSession) -> OddsDAO:
        """创建OddsDAO实例"""
        return OddsDAO(model=Odds, session=async_session)

    @pytest_asyncio.fixture
    async def sample_odds_data(self) -> dict:
        """测试赔率数据"""
        return {
            "match_id": 1,
            "bookmaker": "Bet365",
            "home_win": Decimal("2.50"),
            "draw": Decimal("3.20"),
            "away_win": Decimal("2.80"),
            "over_under": Decimal("2.10"),
            "live_odds": False,
            "confidence_score": Decimal("0.85"),
            "total_volume": Decimal("100000.00"),
            "home_win_volume": Decimal("40000.00"),
            "draw_volume": Decimal("25000.00"),
            "away_win_volume": Decimal("35000.00"),
            "data_quality_score": Decimal("0.90"),
            "source_reliability": "high",
            "last_updated": datetime.utcnow(),
        }

    @pytest_asyncio.fixture
    async def created_odds(self, odds_dao: OddsDAO, sample_odds_data: dict) -> Odds:
        """创建测试赔率"""
        odds_create = OddsCreate(**sample_odds_data)
        return await odds_dao.create(obj_in=odds_create)

    # ==================== 基础CRUD测试 ====================

    @pytest.mark.asyncio
    async def test_create_odds(self, odds_dao: OddsDAO, sample_odds_data: dict):
        """测试创建赔率"""
        # 创建赔率
        odds_create = OddsCreate(**sample_odds_data)
        created_odds = await odds_dao.create(obj_in=odds_create)

        # 验证返回结果
        assert created_odds is not None
        assert created_odds.id is not None
        assert created_odds.match_id == sample_odds_data["match_id"]
        assert created_odds.bookmaker == sample_odds_data["bookmaker"]
        assert created_odds.home_win == sample_odds_data["home_win"]
        assert created_odds.draw == sample_odds_data["draw"]
        assert created_odds.away_win == sample_odds_data["away_win"]
        assert created_odds.confidence_score == sample_odds_data["confidence_score"]
        assert created_odds.created_at is not None
        assert created_odds.is_active is True

        # 验证数据库中的记录
        retrieved_odds = await odds_dao.get(created_odds.id)
        assert retrieved_odds is not None
        assert retrieved_odds.match_id == sample_odds_data["match_id"]
        assert retrieved_odds.bookmaker == sample_odds_data["bookmaker"]

    @pytest.mark.asyncio
    async def test_get_odds(self, odds_dao: OddsDAO, created_odds: Odds):
        """测试获取赔率"""
        # 获取赔率
        retrieved_odds = await odds_dao.get(created_odds.id)

        # 验证结果
        assert retrieved_odds is not None
        assert retrieved_odds.id == created_odds.id
        assert retrieved_odds.match_id == created_odds.match_id
        assert retrieved_odds.bookmaker == created_odds.bookmaker

    @pytest.mark.asyncio
    async def test_get_nonexistent_odds(self, odds_dao: OddsDAO):
        """测试获取不存在的赔率"""
        # 使用不存在的ID
        nonexistent_odds = await odds_dao.get(99999)
        assert nonexistent_odds is None

    @pytest.mark.asyncio
    async def test_update_odds(self, odds_dao: OddsDAO, created_odds: Odds):
        """测试更新赔率"""
        # 准备更新数据
        update_data = OddsUpdate(
            home_win=Decimal("2.40"), confidence_score=Decimal("0.88"), live_odds=True
        )

        # 执行更新
        updated_odds = await odds_dao.update(db_obj=created_odds, obj_in=update_data)

        # 验证更新结果
        assert updated_odds.home_win == Decimal("2.40")
        assert updated_odds.confidence_score == Decimal("0.88")
        assert updated_odds.live_odds is True
        assert updated_odds.bookmaker == created_odds.bookmaker  # 未更新字段保持不变

    @pytest.mark.asyncio
    async def test_delete_odds(self, odds_dao: OddsDAO, created_odds: Odds):
        """测试删除赔率"""
        odds_id = created_odds.id

        # 执行删除
        delete_result = await odds_dao.delete(id=odds_id)
        assert delete_result is True

        # 验证删除结果
        deleted_odds = await odds_dao.get(odds_id)
        assert deleted_odds is None

    @pytest.mark.asyncio
    async def test_crud_lifecycle(self, odds_dao: OddsDAO, sample_odds_data: dict):
        """测试完整的CRUD生命周期"""
        # 1. Create
        odds_create = OddsCreate(**sample_odds_data)
        created_odds = await odds_dao.create(obj_in=odds_create)
        assert created_odds.id is not None

        # 2. Read
        retrieved_odds = await odds_dao.get(created_odds.id)
        assert retrieved_odds is not None
        assert retrieved_odds.match_id == sample_odds_data["match_id"]

        # 3. Update
        update_data = OddsUpdate(confidence_score=Decimal("0.95"))
        updated_odds = await odds_dao.update(db_obj=retrieved_odds, obj_in=update_data)
        assert updated_odds.confidence_score == Decimal("0.95")

        # 4. Delete
        delete_result = await odds_dao.delete(id=updated_odds.id)
        assert delete_result is True

        # 验证删除
        final_odds = await odds_dao.get(updated_odds.id)
        assert final_odds is None

    # ==================== 业务方法测试 ====================

    @pytest.mark.asyncio
    async def test_get_by_match_and_bookmaker(
        self, odds_dao: OddsDAO, created_odds: Odds
    ):
        """测试根据比赛和博彩公司获取赔率"""
        # 根据比赛和博彩公司查找赔率
        found_odds = await odds_dao.get_by_match_and_bookmaker(
            match_id=created_odds.match_id, bookmaker=created_odds.bookmaker
        )

        # 验证结果
        assert found_odds is not None
        assert found_odds.id == created_odds.id
        assert found_odds.match_id == created_odds.match_id
        assert found_odds.bookmaker == created_odds.bookmaker

    @pytest.mark.asyncio
    async def test_get_latest_odds_by_bookmaker(
        self, odds_dao: OddsDAO, created_odds: Odds
    ):
        """测试获取博彩公司的最新赔率"""
        # 创建另一个相同博彩公司的赔率（时间更晚）
        newer_odds_data = {
            **created_odds.__dict__,
            "last_updated": datetime.utcnow() + timedelta(hours=1),
            "home_win": Decimal("2.30"),
        }
        # 移除不需要的字段
        for key in ["id", "created_at", "updated_at"]:
            newer_odds_data.pop(key, None)

        newer_odds_create = OddsCreate(**newer_odds_data)
        await odds_dao.create(obj_in=newer_odds_create)

        # 获取最新赔率
        latest_odds = await odds_dao.get_latest_odds_by_bookmaker(
            match_id=created_odds.match_id, bookmaker=created_odds.bookmaker
        )

        # 验证结果（应该是最新的）
        assert latest_odds is not None
        assert latest_odds.home_win == Decimal("2.30")

    @pytest.mark.asyncio
    async def test_get_all_odds_by_match(
        self, odds_dao: OddsDAO, sample_odds_data: dict
    ):
        """测试获取比赛的所有赔率"""
        # 创建多个博彩公司的赔率
        bookmakers = ["Bet365", "William Hill", "Betfair"]
        for bookmaker in bookmakers:
            odds_data = {**sample_odds_data, "bookmaker": bookmaker}
            odds_create = OddsCreate(**odds_data)
            await odds_dao.create(obj_in=odds_create)

        # 获取所有赔率
        all_odds = await odds_dao.get_all_odds_by_match(
            match_id=sample_odds_data["match_id"]
        )

        # 验证结果
        assert len(all_odds) >= len(bookmakers)
        for odds in all_odds:
            assert odds.match_id == sample_odds_data["match_id"]
            assert odds.bookmaker in bookmakers

    @pytest.mark.asyncio
    async def test_get_best_odds_by_match(
        self, odds_dao: OddsDAO, sample_odds_data: dict
    ):
        """测试获取最优赔率"""
        # 创建多个博彩公司的赔率，包含不同的主胜赔率
        odds_data_list = [
            {**sample_odds_data, "bookmaker": "Bet365", "home_win": Decimal("2.50")},
            {
                **sample_odds_data,
                "bookmaker": "William Hill",
                "home_win": Decimal("2.45"),
            },
            {**sample_odds_data, "bookmaker": "Betfair", "home_win": Decimal("2.40")},
        ]

        for odds_data in odds_data_list:
            odds_create = OddsCreate(**odds_data)
            await odds_dao.create(obj_in=odds_create)

        # 获取最优主胜赔率
        best_odds = await odds_dao.get_best_odds_by_match(
            match_id=sample_odds_data["match_id"], bet_type="home_win"
        )

        # 验证结果（应该是最低赔率，即最优赔率）
        assert best_odds is not None
        assert best_odds.home_win == Decimal("2.40")  # Betfair的2.40是最优的
        assert best_odds.bookmaker == "Betfair"

    @pytest.mark.asyncio
    async def test_get_live_odds(self, odds_dao: OddsDAO, sample_odds_data: dict):
        """测试获取实时赔率"""
        # 创建实时赔率
        live_odds_data = {
            **sample_odds_data,
            "bookmaker": "Bet365",
            "live_odds": True,
            "home_win": Decimal("2.20"),
        }
        odds_create = OddsCreate(**live_odds_data)
        await odds_dao.create(obj_in=odds_create)

        # 创建非实时赔率
        non_live_odds_data = {
            **sample_odds_data,
            "bookmaker": "William Hill",
            "live_odds": False,
        }
        odds_create2 = OddsCreate(**non_live_odds_data)
        await odds_dao.create(obj_in=odds_create2)

        # 获取实时赔率
        live_odds = await odds_dao.get_live_odds()

        # 验证结果
        assert len(live_odds) >= 1
        for odds in live_odds:
            assert odds.live_odds is True
            assert odds.is_active is True

    @pytest.mark.asyncio
    async def test_get_odds_by_confidence_threshold(
        self, odds_dao: OddsDAO, sample_odds_data: dict
    ):
        """测试根据置信度阈值获取赔率"""
        # 创建不同置信度的赔率
        confidence_levels = [0.6, 0.75, 0.85, 0.95]
        for i, confidence in enumerate(confidence_levels):
            odds_data = {
                **sample_odds_data,
                "bookmaker": f"Bookmaker{i}",
                "confidence_score": Decimal(str(confidence)),
            }
            odds_create = OddsCreate(**odds_data)
            await odds_dao.create(obj_in=odds_create)

        # 获取高置信度赔率
        high_confidence_odds = await odds_dao.get_odds_by_confidence_threshold(
            min_confidence=0.8
        )

        # 验证结果
        assert len(high_confidence_odds) >= 2  # 至少有0.85和0.95的
        for odds in high_confidence_odds:
            assert odds.confidence_score >= Decimal("0.8")

    @pytest.mark.asyncio
    async def test_search_odds_by_bookmaker(
        self, odds_dao: OddsDAO, sample_odds_data: dict
    ):
        """测试搜索博彩公司赔率"""
        # 创建特定博彩公司的赔率
        bookmakers = ["Bet365 Sports", "William Hill Betting", "Betfair Exchange"]
        for bookmaker in bookmakers:
            odds_data = {**sample_odds_data, "bookmaker": bookmaker}
            odds_create = OddsCreate(**odds_data)
            await odds_dao.create(obj_in=odds_create)

        # 搜索包含"Bet"的博彩公司
        search_results = await odds_dao.search_odds_by_bookmaker(
            bookmaker_keyword="Bet"
        )

        # 验证结果
        assert len(search_results) >= 2  # 应该包含Bet365和Betfair
        for odds in search_results:
            assert "Bet" in odds.bookmaker

    # ==================== 统计方法测试 ====================

    @pytest.mark.asyncio
    async def test_get_odds_count_by_bookmaker(
        self, odds_dao: OddsDAO, sample_odds_data: dict
    ):
        """测试按博彩公司统计赔率数量"""
        # 创建多个博彩公司的赔率
        bookmakers = [
            "Bet365",
            "William Hill",
            "Bet365",
            "William Hill",
        ]  # 重复测试聚合
        for bookmaker in bookmakers:
            odds_data = {**sample_odds_data, "bookmaker": bookmaker}
            odds_create = OddsCreate(**odds_data)
            await odds_dao.create(obj_in=odds_create)

        # 获取统计
        bookmaker_counts = await odds_dao.get_odds_count_by_bookmaker()

        # 验证结果
        assert isinstance(bookmaker_counts, dict)
        assert "Bet365" in bookmaker_counts
        assert "William Hill" in bookmaker_counts
        assert bookmaker_counts["Bet365"] == 2
        assert bookmaker_counts["William Hill"] == 2

    @pytest.mark.asyncio
    async def test_get_live_odds_count(self, odds_dao: OddsDAO, sample_odds_data: dict):
        """测试统计实时赔率数量"""
        # 创建实时和非实时赔率
        live_count = 3
        for i in range(live_count + 2):
            odds_data = {
                **sample_odds_data,
                "bookmaker": f"Bookmaker{i}",
                "live_odds": i < live_count,
            }
            odds_create = OddsCreate(**odds_data)
            await odds_dao.create(obj_in=odds_create)

        # 获取实时赔率数量
        live_odds_count = await odds_dao.get_live_odds_count()

        # 验证结果
        assert live_odds_count == live_count

    # ==================== 质量控制方法测试 ====================

    @pytest.mark.asyncio
    async def test_update_odds_quality_score(
        self, odds_dao: OddsDAO, created_odds: Odds
    ):
        """测试更新赔率质量分数"""
        # 更新质量分数
        result = await odds_dao.update_odds_quality_score(
            odds_id=created_odds.id, quality_score=0.95
        )

        # 验证更新结果
        assert result is True

        # 获取更新后的赔率验证
        updated_odds = await odds_dao.get(created_odds.id)
        assert updated_odds.data_quality_score == Decimal("0.95")
        assert updated_odds.updated_at is not None

    @pytest.mark.asyncio
    async def test_deactivate_old_odds(self, odds_dao: OddsDAO, sample_odds_data: dict):
        """测试停用旧赔率记录"""
        # 创建旧赔率记录（48小时前）
        old_odds_data = {
            **sample_odds_data,
            "bookmaker": "OldBookmaker",
            "last_updated": datetime.utcnow() - timedelta(hours=48),
        }
        odds_create = OddsCreate(**old_odds_data)
        old_odds = await odds_dao.create(obj_in=odds_create)

        # 创建新赔率记录（2小时前）
        new_odds_data = {
            **sample_odds_data,
            "bookmaker": "NewBookmaker",
            "last_updated": datetime.utcnow() - timedelta(hours=2),
        }
        odds_create2 = OddsCreate(**new_odds_data)
        new_odds = await odds_dao.create(obj_in=odds_create2)

        # 停用24小时前的赔率
        deactivated_count = await odds_dao.deactivate_old_odds(hours=24)

        # 验证结果
        assert deactivated_count == 1

        # 验证旧赔率已停用
        deactivated_old_odds = await odds_dao.get(old_odds.id)
        assert deactivated_old_odds.is_active is False

        # 验证新赔率仍活跃
        active_new_odds = await odds_dao.get(new_odds.id)
        assert active_new_odds.is_active is True

    # ==================== 异常处理测试 ====================

    @pytest.mark.asyncio
    async def test_update_nonexistent_odds_quality_score(self, odds_dao: OddsDAO):
        """测试更新不存在赔率的质量分数"""
        with pytest.raises(RecordNotFoundError):
            await odds_dao.update_odds_quality_score(odds_id=99999, quality_score=0.8)

    @pytest.mark.asyncio
    async def test_update_odds_with_invalid_quality_score(
        self, odds_dao: OddsDAO, created_odds: Odds
    ):
        """测试使用无效质量分数更新赔率"""
        with pytest.raises(ValidationError):
            await odds_dao.update_odds_quality_score(
                odds_id=created_odds.id, quality_score=1.5  # 超出范围
            )

    @pytest.mark.asyncio
    async def test_get_best_odds_with_invalid_bet_type(self, odds_dao: OddsDAO):
        """测试使用无效投注类型获取最优赔率"""
        with pytest.raises(ValidationError):
            await odds_dao.get_best_odds_by_match(match_id=1, bet_type="invalid_type")

    @pytest.mark.asyncio
    async def test_get_odds_by_confidence_with_invalid_threshold(
        self, odds_dao: OddsDAO
    ):
        """测试使用无效置信度阈值获取赔率"""
        with pytest.raises(ValidationError):
            await odds_dao.get_odds_by_confidence_threshold(
                min_confidence=1.5  # 超出范围
            )

    @pytest.mark.asyncio
    async def test_search_odds_with_short_keyword(self, odds_dao: OddsDAO):
        """测试使用过短关键词搜索博彩公司"""
        with pytest.raises(ValidationError):
            await odds_dao.search_odds_by_bookmaker(
                bookmaker_keyword="a"  # 关键词至少2个字符
            )

    @pytest.mark.asyncio
    async def test_deactivate_old_odds_with_invalid_hours(self, odds_dao: OddsDAO):
        """测试使用无效小时数停用旧赔率"""
        with pytest.raises(ValidationError):
            await odds_dao.deactivate_old_odds(hours=0)  # 小时数必须大于0
