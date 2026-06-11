"""FotMobRawParser contract validation — Python-side smoke test.

Validates that the JS parser is importable and produces output matching
the contract defined in docs/data/FOTMOB_RAW_PARSER_CONTRACT.md.

Uses a minimal inline payload via subprocess; no full raw data saved/printed.

lifecycle: permanent
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = ROOT / "src" / "parsers" / "fotmob" / "FotMobRawParser.js"


def _run_parser(payload: dict, external_id: str = "test-001") -> dict:
    """Execute the parser via Node.js subprocess and return the parsed result."""
    script = f"""
    const {{ parseFotMobRaw }} = require({json.dumps(str(PARSER_PATH))});
    const payload = {json.dumps(payload)};
    const result = parseFotMobRaw(payload, {json.dumps(external_id)});
    console.log(JSON.stringify(result));
    """
    proc = subprocess.run(
        ["node", "--eval", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=15,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node.js 执行失败: {proc.stderr.strip()}")
    return json.loads(proc.stdout.strip())


def _build_minimal_valid_payload() -> dict:
    """构建 contract 定义的最小有效 payload."""
    return {
        "_meta": {"fetchedAt": "2026-06-10T12:00:00Z", "hash": "abc123"},
        "matchId": "4830507",
        "general": {
            "matchId": 4830507,
            "homeTeam": {"id": 85, "name": "PSG", "shortName": "PSG"},
            "awayTeam": {"id": 96, "name": "Angers", "shortName": "ANG"},
            "leagueId": 47,
            "leagueName": "Ligue 1",
            "matchRound": "Round 1",
            "matchTimeUTC": "2026-06-10T19:00:00.000Z",
            "started": True,
            "finished": True,
        },
        "header": {
            "teams": [
                {"id": 85, "name": "PSG", "score": 2},
                {"id": 96, "name": "Angers", "score": 1},
            ],
            "status": {
                "started": True,
                "finished": True,
                "cancelled": False,
                "scoreStr": "2-1",
                "utcTime": "2026-06-10T19:00:00.000Z",
                "halfs": {},
                "reason": {},
            },
            "events": {"homeTeamGoals": 2, "awayTeamGoals": 1, "homeTeamRedCards": 0, "awayTeamRedCards": 0},
        },
        "content": {
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {
                                "key": "expected_goals",
                                "title": "Expected Goals",
                                "stats": [
                                    {"key": "homeValue", "value": 1.8},
                                    {"key": "awayValue", "value": 0.6},
                                ],
                            }
                        ]
                    },
                    "FirstHalf": {"stats": []},
                    "SecondHalf": {"stats": []},
                }
            },
            "lineup": {
                "homeTeam": {
                    "id": 85, "name": "PSG", "formation": "4-3-3",
                    "starters": [{"id": 1, "name": {"fullName": "Player 1"}, "position": "FW", "shirtNumber": 7, "rating": 8.0}],
                    "subs": [],
                    "coach": {"id": 99, "name": "Coach"},
                    "rating": 7.0, "averageStarterAge": 25, "totalStarterMarketValue": "€500M", "unavailable": [],
                },
                "awayTeam": {
                    "id": 96, "name": "Angers", "formation": "5-4-1",
                    "starters": [],
                    "subs": [],
                    "coach": {},
                    "rating": 6.0, "averageStarterAge": 26, "totalStarterMarketValue": "€45M", "unavailable": [],
                },
            },
            "matchFacts": {
                "events": {
                    "events": [
                        {"id": 1, "type": "Goal", "minute": 23, "teamId": 85, "playerId": 1, "playerName": "Player 1", "assistPlayerId": None, "outcome": "goal"},
                    ],
                    "ongoing": None,
                    "eventTypes": [],
                    "penaltyShootoutEvents": [],
                }
            },
            "shotmap": {"shots": []},
            "playerStats": {},
            "table": {},
            "h2h": {"matches": [], "summary": {}},
        },
    }


# ---- 测试用例 ----


def test_parser_file_exists():
    """验证 parser 文件存在于正确位置."""
    assert PARSER_PATH.exists(), f"Parser 文件不存在: {PARSER_PATH}"
    assert PARSER_PATH.is_file(), f"路径不是文件: {PARSER_PATH}"


def test_parser_successful_parse():
    """验证完整的成功解析路径."""
    payload = _build_minimal_valid_payload()
    result = _run_parser(payload, "4830507")

    assert result["ok"] is True, f"解析应成功: {result.get('error')}"
    data = result["data"]

    # match
    assert data["match"]["matchId"] == "4830507"
    assert data["match"]["externalId"] == "4830507"
    assert data["match"]["leagueName"] == "Ligue 1"
    assert data["match"]["started"] is True
    assert data["match"]["finished"] is True

    # teams
    assert data["homeTeam"]["name"] == "PSG"
    assert data["homeTeam"]["score"] == 2
    assert data["awayTeam"]["name"] == "Angers"
    assert data["awayTeam"]["score"] == 1

    # stats — periods-aware
    assert isinstance(data["stats"], list)
    for s in data["stats"]:
        assert "period" in s
        assert "key" in s
        assert "homeValue" in s
        assert "awayValue" in s

    # events
    assert isinstance(data["events"], list)
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "Goal"

    # lineup
    assert isinstance(data["lineup"]["home"]["starters"], list)
    assert isinstance(data["lineup"]["away"]["starters"], list)

    # shotmap
    assert "shots" in data["shotmap"]

    # playerStats
    assert isinstance(data["playerStats"], dict)

    # meta
    assert data["meta"]["dataVersion"] == "fotmob_live_v1"
    assert data["meta"]["parserVersion"] == "1.0.0"


def test_parser_missing_required_section():
    """缺失必选段应返回 ok=false."""
    payload = _build_minimal_valid_payload()
    del payload["general"]

    result = _run_parser(payload, "test")
    assert result["ok"] is False
    assert "MISSING_REQUIRED_SECTION" in result["error"]


def test_parser_missing_team_identity():
    """缺失球队身份应返回 MISSING_TEAM_IDENTITY."""
    payload = _build_minimal_valid_payload()
    del payload["general"]["homeTeam"]

    result = _run_parser(payload, "test")
    assert result["ok"] is False
    assert result["error"] == "MISSING_TEAM_IDENTITY"


def test_parser_invalid_match_id():
    """无效 matchId 应返回 INVALID_MATCH_ID."""
    payload = _build_minimal_valid_payload()
    payload["matchId"] = None
    payload["general"]["matchId"] = None

    result = _run_parser(payload, "test")
    assert result["ok"] is False
    assert result["error"] == "INVALID_MATCH_ID"


def test_parser_missing_stats_returns_empty():
    """缺失 stats 应返回空数组."""
    payload = _build_minimal_valid_payload()
    del payload["content"]["stats"]

    result = _run_parser(payload, "4830507")
    assert result["ok"] is True
    assert result["data"]["stats"] == []


def test_parser_missing_events_returns_empty():
    """缺失 events 应返回空数组."""
    payload = _build_minimal_valid_payload()
    del payload["content"]["matchFacts"]["events"]

    result = _run_parser(payload, "4830507")
    assert result["ok"] is True
    assert result["data"]["events"] == []


def test_parser_missing_lineup_returns_empty_containers():
    """缺失 lineup 应返回空容器结构."""
    payload = _build_minimal_valid_payload()
    del payload["content"]["lineup"]

    result = _run_parser(payload, "4830507")
    assert result["ok"] is True
    assert result["data"]["lineup"]["home"]["starters"] == []
    assert result["data"]["lineup"]["away"]["subs"] == []
    assert result["data"]["lineup"]["home"]["coach"] == {}


def test_parser_deterministic():
    """相同输入应产生相同输出."""
    payload = _build_minimal_valid_payload()
    r1 = _run_parser(payload, "4830507")
    r2 = _run_parser(payload, "4830507")

    assert r1["ok"] and r2["ok"]
    assert r1["data"] == r2["data"]


def test_parser_output_structure_matches_contract():
    """验证输出结构包含 contract §6 定义的所有顶层字段."""
    payload = _build_minimal_valid_payload()
    result = _run_parser(payload, "4830507")

    assert result["ok"] is True
    data = result["data"]

    required_keys = {"match", "homeTeam", "awayTeam", "stats", "lineup", "events", "shotmap", "playerStats", "meta"}
    actual_keys = set(data.keys())
    assert required_keys.issubset(actual_keys), f"缺少 contract 必选字段: {required_keys - actual_keys}"
