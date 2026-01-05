#!/usr/bin/env python3
"""
V144.5 FotMob Persistence Integration Tests

Test FotMob data persistence with real database connection (172.25.16.1).
Uses TCP handshake to verify database writes.
"""

import pytest
from datetime import datetime

import psycopg2
from pydantic import ValidationError

from src.api.collectors.schemas.l1_match_schema import L1MatchData, LeagueId, MatchStatus
from src.config_unified import get_settings


class TestDatabaseConnection:
    """Test database TCP connection (172.25.16.1)"""

    def test_database_tcp_handshake(self):
        """Test TCP handshake to Docker database via WSL2 bridge"""
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,  # Should be 172.25.16.1
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        assert conn is not None
        conn.close()

    def test_database_matches_table_exists(self):
        """Test that matches table exists"""
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'matches'
            );
        """
        )
        exists = cursor.fetchone()[0]
        assert exists is True
        cursor.close()
        conn.close()


class TestFotMobDataPersistence:
    """Test FotMob data persistence to database"""

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Setup database connection and cleanup"""
        settings = get_settings()
        self.conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        yield
        self.conn.close()

    def test_insert_and_retrieve_fotmob_match(self):
        """Test inserting and retrieving FotMob match data"""
        # Create test data
        test_data = L1MatchData(
            match_id="test_fotmob_v145_001",
            league_id="47",
            league_name="Premier League",
            season_id="2324",
            season_name="23/24",
            home_team="Arsenal",
            away_team="Chelsea",
            home_team_id=9825,
            away_team_id=9810,
            status=MatchStatus.FINISHED,
            match_time_utc="2024-01-06T15:00:00Z",
            home_score=2,
            away_score=2,
        )

        # Insert into database (note: match_time is NOT NULL in actual schema)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO matches AS m (
                match_id, league_id, league_name, season_id, season_name,
                home_team, away_team, home_team_id, away_team_id,
                status, match_time_utc, match_time, home_score, away_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team
            """,
            (
                test_data.match_id,
                test_data.league_id,
                test_data.league_name,
                test_data.season_id,
                test_data.season_name,
                test_data.home_team,
                test_data.away_team,
                test_data.home_team_id,
                test_data.away_team_id,
                test_data.status.value,
                test_data.match_time_utc,
                "2024-01-06 15:00:00+00",  # match_time (NOT NULL)
                test_data.home_score,
                test_data.away_score,
            ),
        )
        self.conn.commit()

        # Retrieve from database
        cursor.execute("SELECT * FROM matches WHERE match_id = %s", (test_data.match_id,))
        row = cursor.fetchone()
        cursor.close()

        # Verify data
        assert row is not None
        assert row[0] == test_data.match_id  # match_id
        assert row[4] == test_data.home_team  # home_team (V144.5: 修正列序)
        assert row[5] == test_data.away_team  # away_team (V144.5: 修正列序)

    def test_batch_insert_fotmob_matches(self):
        """Test batch insert of multiple FotMob matches"""
        # Create multiple test records
        test_matches = [
            {
                "match_id": "test_batch_v145_001",
                "league_id": "47",
                "league_name": "Premier League",
                "season_id": "2324",
                "season_name": "23/24",
                "home_team": "Liverpool",
                "away_team": "Man City",
                "home_team_id": 8650,
                "away_team_id": 8456,
                "status": "finished",
                "home_score": 1,
                "away_score": 1,
                "match_time": "2024-01-06 15:00:00+00",
            },
            {
                "match_id": "test_batch_v145_002",
                "league_id": "47",
                "league_name": "Premier League",
                "season_id": "2324",
                "season_name": "23/24",
                "home_team": "Man Utd",
                "away_team": "Tottenham",
                "home_team_id": 8456,
                "away_team_id": 8455,
                "status": "scheduled",
                "home_score": None,
                "away_score": None,
                "match_time": "2024-01-07 15:00:00+00",
            },
        ]

        # Batch insert
        cursor = self.conn.cursor()
        for match in test_matches:
            cursor.execute(
                """
                INSERT INTO matches AS m (
                    match_id, league_id, league_name, season_id, season_name,
                    home_team, away_team, home_team_id, away_team_id,
                    status, match_time, home_score, away_score
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (match_id) DO NOTHING
                """,
                (
                    match["match_id"],
                    match["league_id"],
                    match["league_name"],
                    match["season_id"],
                    match["season_name"],
                    match["home_team"],
                    match["away_team"],
                    match["home_team_id"],
                    match["away_team_id"],
                    match["status"],
                    match["match_time"],
                    match["home_score"],
                    match["away_score"],
                ),
            )
        self.conn.commit()

        # Verify count
        cursor.execute("SELECT COUNT(*) FROM matches WHERE match_id LIKE 'test_batch_v145_%'")
        count = cursor.fetchone()[0]
        cursor.close()

        assert count == 2


class TestFotMobDataTypeIntegrity:
    """Test data type integrity and encoding"""

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Setup database connection"""
        settings = get_settings()
        self.conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        yield
        self.conn.close()

    def test_unicode_team_names(self):
        """Test Unicode character handling in team names"""
        # Test with special characters (e.g., German umlauts, Spanish accents)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO matches AS m (
                match_id, league_id, league_name, season_id, season_name,
                home_team, away_team, home_team_id, away_team_id, status, match_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team
            """,
            (
                "test_unicode_v145_001",
                "54",  # Bundesliga
                "Bundesliga",
                "2324",
                "23/24",
                "FC Bayern München",  # German umlaut
                "Borussia Mönchengladbach",
                9825,
                9810,
                "scheduled",
                "2024-01-08 15:00:00+00",
            ),
        )
        self.conn.commit()

        # Retrieve and verify
        cursor.execute("SELECT home_team, away_team FROM matches WHERE match_id = %s", ("test_unicode_v145_001",))
        row = cursor.fetchone()
        cursor.close()

        assert row[0] == "FC Bayern München"
        assert row[1] == "Borussia Mönchengladbach"

    def test_score_integer_validation(self):
        """Test that scores are stored as integers"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO matches AS m (
                match_id, league_id, league_name, season_id, season_name,
                home_team, away_team, home_team_id, away_team_id,
                status, match_time, home_score, away_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score
            """,
            (
                "test_score_v145_001",
                "47",
                "Premier League",
                "2324",
                "23/24",
                "Arsenal",
                "Chelsea",
                9825,
                9810,
                "finished",
                "2024-01-09 15:00:00+00",
                3,  # Test integer score
                1,
            ),
        )
        self.conn.commit()

        # Retrieve and verify type
        cursor.execute("SELECT home_score, away_score FROM matches WHERE match_id = %s", ("test_score_v145_001",))
        row = cursor.fetchone()
        cursor.close()

        assert isinstance(row[0], int)
        assert row[0] == 3
        assert row[1] == 1

    def test_null_score_handling(self):
        """Test NULL score handling for scheduled matches"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO matches AS m (
                match_id, league_id, league_name, season_id, season_name,
                home_team, away_team, home_team_id, away_team_id, status, match_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO NOTHING
            """,
            (
                "test_null_score_v145_001",
                "47",
                "Premier League",
                "2324",
                "23/24",
                "Arsenal",
                "Chelsea",
                9825,
                9810,
                "scheduled",
                "2024-01-10 15:00:00+00",
            ),
        )
        self.conn.commit()

        # Verify NULL scores
        cursor.execute("SELECT home_score, away_score FROM matches WHERE match_id = %s", ("test_null_score_v145_001",))
        row = cursor.fetchone()
        cursor.close()

        assert row[0] is None  # home_score is NULL
        assert row[1] is None  # away_score is NULL


class TestFotMobEndToEndWorkflow:
    """Test end-to-end FotMob data workflow"""

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Setup database connection"""
        settings = get_settings()
        self.conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        yield
        # Cleanup
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM matches WHERE match_id LIKE 'test_e2e_v145_%'")
        self.conn.commit()
        cursor.close()
        self.conn.close()

    def test_parse_validate_persist_workflow(self):
        """Test complete workflow: Parse → Validate → Persist"""
        # Step 1: Parse mock FotMob API response
        mock_fotmob_response = {
            "match_id": "test_e2e_v145_001",
            "league_id": "47",
            "league_name": "Premier League",
            "season_id": "2324",
            "season_name": "23/24",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_team_id": 9825,
            "away_team_id": 9810,
            "status": "finished",
            "match_time_utc": "2024-01-06T15:00:00Z",
            "home_score": 2,
            "away_score": 2,
        }

        # Step 2: Validate with Pydantic
        match_data = L1MatchData(**mock_fotmob_response)
        assert match_data.match_id == "test_e2e_v145_001"

        # Step 3: Persist to database
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO matches AS m (
                match_id, league_id, league_name, season_id, season_name,
                home_team, away_team, home_team_id, away_team_id,
                status, match_time_utc, match_time, home_score, away_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (match_id) DO UPDATE SET
                home_team = EXCLUDED.home_team,
                away_team = EXCLUDED.away_team
            """,
            (
                match_data.match_id,
                match_data.league_id,
                match_data.league_name,
                match_data.season_id,
                match_data.season_name,
                match_data.home_team,
                match_data.away_team,
                match_data.home_team_id,
                match_data.away_team_id,
                match_data.status.value,
                match_data.match_time_utc,
                "2024-01-06 15:00:00+00",  # match_time (NOT NULL)
                match_data.home_score,
                match_data.away_score,
            ),
        )
        self.conn.commit()

        # Step 4: Verify persistence
        cursor.execute("SELECT * FROM matches WHERE match_id = %s", (match_data.match_id,))
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        assert row[0] == match_data.match_id
        assert row[4] == match_data.home_team  # V144.5: 修正列序
        assert row[5] == match_data.away_team  # V144.5: 修正列序
