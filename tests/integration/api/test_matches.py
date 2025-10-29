"""
比赛 API 集成测试
测试比赛 API 与数据库的交互
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestMatchAPIIntegration:
    """比赛 API 集成测试"""

    @pytest.mark.asyncio
    async def test_create_match(self, api_client: AsyncClient, db_session, auth_headers: dict):
        """测试创建比赛"""
        # 先创建队伍
        from src.database.models import Team

        home_team = Team(name="Home Team API", city="City A", founded=2000)
        away_team = Team(name="Away Team API", city="City B", founded=2001)

        db_session.add(home_team)
        db_session.add(away_team)
        await db_session.commit()
        await db_session.refresh(home_team)
        await db_session.refresh(away_team)

        # 准备请求数据
        request_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": "2025-02-01T20:00:00Z",
            "competition": "Test Championship",
            "season": "2024/2025",
            "venue": "Test Stadium",
            "status": "UPCOMING",
        }

        # 发送请求
        response = await api_client.post("/api/v1/matches", json=request_data, headers=auth_headers)

        # 验证响应
        assert response.status_code == 201
        _data = response.json()
        assert data["home_team_id"] == request_data["home_team_id"]
        assert data["away_team_id"] == request_data["away_team_id"]
        assert data["competition"] == request_data["competition"]
        assert "id" in data

        # 验证数据库中的数据
from src.database.models import Match

        match = await db_session.get(Match, data["id"])
        assert match is not None
        assert match.home_team_id == request_data["home_team_id"]
        assert match.competition == request_data["competition"]

    @pytest.mark.asyncio
    async def test_get_matches(self, api_client: AsyncClient, db_session, auth_headers: dict):
        """测试获取比赛列表"""
        # 创建测试数据
from src.database.models import Match, Team

        _teams = []
        for i in range(4):
            team = Team(name=f"Team {i}", city=f"City {i}", founded=2000 + i)
            teams.append(team)
            db_session.add(team)

        await db_session.commit()

        _matches = []
        for i in range(5):
            match = Match(
                home_team_id=teams[i * 2 % 4].id,
                away_team_id=teams[(i * 2 + 1) % 4].id,
                match_date=datetime.now(timezone.utc),
                competition="Test League",
                season="2024/2025",
                status="UPCOMING" if i % 2 == 0 else "COMPLETED",
                home_score=i if i % 2 == 1 else None,
                away_score=(i + 1) if i % 2 == 1 else None,
            )
            matches.append(match)
            db_session.add(match)

        await db_session.commit()

        # 获取所有比赛
        response = await api_client.get("/api/v1/matches", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 5
        assert "pagination" in data

        # 按状态过滤
        response = await api_client.get(
            "/api/v1/matches", params={"status": "UPCOMING"}, headers=auth_headers
        )
        assert response.status_code == 200
        upcoming_data = response.json()
        assert all(m["status"] == "UPCOMING" for m in upcoming_data["data"])

    @pytest.mark.asyncio
    async def test_get_match_by_id(
        self, api_client: AsyncClient, sample_match_data, auth_headers: dict
    ):
        """测试通过 ID 获取比赛"""
        match = sample_match_data["match"]

        # 发送请求
        response = await api_client.get(f"/api/v1/matches/{match.id}", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert data["id"] == match.id
        assert data["home_team_id"] == match.home_team_id
        assert data["away_team_id"] == match.away_team_id
        assert data["competition"] == match.competition

    @pytest.mark.asyncio
    async def test_update_match_result(
        self, api_client: AsyncClient, db_session, sample_match_data, auth_headers: dict
    ):
        """测试更新比赛结果"""
        match = sample_match_data["match"]

        # 更新比赛结果
        update_data = {
            "status": "COMPLETED",
            "home_score": 3,
            "away_score": 1,
            "minute": 90,
        }

        response = await api_client.patch(
            f"/api/v1/matches/{match.id}/result", json=update_data, headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["home_score"] == 3
        assert data["away_score"] == 1

        # 验证数据库
from src.database.models import Match

        updated_match = await db_session.get(Match, match.id)
        assert updated_match.status == "COMPLETED"
        assert updated_match.home_score == 3
        assert updated_match.away_score == 1

    @pytest.mark.asyncio
    async def test_get_upcoming_matches(
        self, api_client: AsyncClient, db_session, auth_headers: dict
    ):
        """测试获取即将到来的比赛"""
        # 创建测试数据
from src.database.models import Match, Team

        now = datetime.now(timezone.utc)

        home_team = Team(name="Future Home", city="Future City", founded=2020)
        away_team = Team(name="Future Away", city="Future City", founded=2020)
        db_session.add_all([home_team, away_team])
        await db_session.commit()

        # 创建未来的比赛
        future_match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=now.replace(hour=20, minute=0, second=0, microsecond=0),
            competition="Future League",
            season="2024/2025",
            status="UPCOMING",
        )
        db_session.add(future_match)
        await db_session.commit()

        # 获取即将到来的比赛
        response = await api_client.get("/api/v1/matches/upcoming", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1
        assert all(m["status"] == "UPCOMING" for m in data["data"])

    @pytest.mark.asyncio
    async def test_get_live_matches(self, api_client: AsyncClient, db_session, auth_headers: dict):
        """测试获取正在进行中的比赛"""
        # 创建测试数据
from src.database.models import Match, Team

        home_team = Team(name="Live Home", city="Live City", founded=2020)
        away_team = Team(name="Live Away", city="Live City", founded=2020)
        db_session.add_all([home_team, away_team])
        await db_session.commit()

        # 创建进行中的比赛
        live_match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.now(timezone.utc),
            competition="Live League",
            season="2024/2025",
            status="LIVE",
            minute=45,
            home_score=1,
            away_score=1,
        )
        db_session.add(live_match)
        await db_session.commit()

        # 获取进行中的比赛
        response = await api_client.get("/api/v1/matches/live", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1
        assert all(m["status"] == "LIVE" for m in data["data"])

    @pytest.mark.asyncio
    async def test_match_search(self, api_client: AsyncClient, db_session, auth_headers: dict):
        """测试搜索比赛"""
        # 创建测试数据
from src.database.models import Match, Team

        team1 = Team(name="Search Team A", city="Search City", founded=2020)
        team2 = Team(name="Search Team B", city="Search City", founded=2020)
        team3 = Team(name="Other Team", city="Other City", founded=2020)
        db_session.add_all([team1, team2, team3])
        await db_session.commit()

        match1 = Match(
            home_team_id=team1.id,
            away_team_id=team2.id,
            match_date=datetime.now(timezone.utc),
            competition="Search Championship",
            season="2024/2025",
            status="UPCOMING",
        )
        match2 = Match(
            home_team_id=team3.id,
            away_team_id=team1.id,
            match_date=datetime.now(timezone.utc),
            competition="Other League",
            season="2024/2025",
            status="UPCOMING",
        )
        db_session.add_all([match1, match2])
        await db_session.commit()

        # 搜索包含 "Search" 的比赛
        response = await api_client.get(
            "/api/v1/matches/search", params={"q": "Search"}, headers=auth_headers
        )

        # 验证响应
        assert response.status_code == 200
        _data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2  # match1 和 match2 都包含 team1

    @pytest.mark.asyncio
    async def test_match_statistics(self, api_client: AsyncClient, db_session, auth_headers: dict):
        """测试比赛统计"""
        # 创建不同状态的比赛
from src.database.models import Match, Team

        _teams = []
        for i in range(6):
            team = Team(name=f"Stats Team {i}", city=f"Stats City {i}", founded=2020)
            teams.append(team)
            db_session.add(team)

        await db_session.commit()

        # 创建比赛
        statuses = ["UPCOMING", "LIVE", "COMPLETED"]
        for i, status in enumerate(statuses):
            for j in range(3):
                match = Match(
                    home_team_id=teams[i * 2].id,
                    away_team_id=teams[i * 2 + 1].id,
                    match_date=datetime.now(timezone.utc),
                    competition="Stats League",
                    season="2024/2025",
                    status=status,
                    home_score=j if status == "COMPLETED" else None,
                    away_score=(j + 1) if status == "COMPLETED" else None,
                )
                db_session.add(match)

        await db_session.commit()

        # 获取统计
        response = await api_client.get("/api/v1/matches/statistics", headers=auth_headers)

        # 验证响应
        assert response.status_code == 200
        _stats = response.json()
        assert "total_matches" in stats
        assert "status_counts" in stats
        assert "upcoming_count" in stats
        assert "live_count" in stats
        assert "completed_count" in stats
        assert stats["total_matches"] >= 9
        assert stats["upcoming_count"] >= 3
        assert stats["live_count"] >= 3
        assert stats["completed_count"] >= 3

    @pytest.mark.asyncio
    async def test_invalid_team_id(self, api_client: AsyncClient, auth_headers: dict):
        """测试无效的队伍 ID"""
        # 使用不存在的队伍 ID
        response = await api_client.post(
            "/api/v1/matches",
            json={
                "home_team_id": 99999,
                "away_team_id": 99998,
                "match_date": "2025-02-01T20:00:00Z",
                "competition": "Test",
                "season": "2024/2025",
            },
            headers=auth_headers,
        )

        # 应该返回错误
        assert response.status_code == 400 or response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_match(
        self, api_client: AsyncClient, sample_match_data, auth_headers: dict
    ):
        """测试重复比赛"""
        match = sample_match_data["match"]

        # 尝试创建相同的比赛
        response = await api_client.post(
            "/api/v1/matches",
            json={
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "match_date": match.match_date,
                "competition": match.competition,
                "season": match.season,
            },
            headers=auth_headers,
        )

        # 根据业务逻辑，可能允许或拒绝重复比赛
        # 这里假设允许不同的队伍在不同时间比赛
        assert response.status_code in [201, 400, 409]
