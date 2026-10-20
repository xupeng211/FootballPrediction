"""球队 URL 解析的离线回归测试。"""

from collections.abc import Callable
from importlib import import_module
from pathlib import Path

import pytest

LEAGUE_URL = "https://www.oddsportal.com/football/england/premier-league-2025-2026/"


@pytest.fixture
def extract_teams(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], tuple[str, str] | None]:
    """导入真实的纯 teams 包，避免触发 src 顶层业务初始化。"""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "src" / "utils"))
    return import_module("teams.url_tools").extract_team_names_from_url


@pytest.mark.parametrize("match_id", ["", "-AbCd1234", "-12345678"])
@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "/",
        "?utm_source=test",
        "#summary",
        "?utm_source=test#summary",
        "/?utm_source=test",
        "/#summary",
        "/?utm_source=test#summary",
        "?utm_source=test&utm_medium=link",
        "#summary?utm_source=test",
        "?next=/other/path#summary",
    ],
)
def test_extract_team_names_ignores_query_and_fragment(
    extract_teams, match_id: str, suffix: str
) -> None:
    assert extract_teams(f"{LEAGUE_URL}arsenal-chelsea{match_id}{suffix}") == ("Arsenal", "Chelsea")


@pytest.mark.parametrize("suffix", ["", "/", "?utm_source=test#summary"])
@pytest.mark.parametrize("match_id", ["", "-AbCd1234"])
def test_extract_team_names_preserves_multi_word_split(
    extract_teams, match_id: str, suffix: str
) -> None:
    assert extract_teams(f"{LEAGUE_URL}manchester-city-manchester-united{match_id}{suffix}") == (
        "Manchester City",
        "Manchester United",
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://www.oddsportal.com/",
        "https://www.oddsportal.com/football/spain/laliga-2025-2026/arsenal-chelsea",
        "https://www.oddsportal.com/football/england/championship-2025-2026/arsenal-chelsea",
        "https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea",
        LEAGUE_URL,
        f"{LEAGUE_URL}arsenal",
        f"{LEAGUE_URL}arsenal-AbCd1234",
    ],
)
@pytest.mark.parametrize("suffix", ["", "?utm_source=test#summary"])
def test_extract_team_names_rejects_unsupported_urls(extract_teams, url: str, suffix: str) -> None:
    assert extract_teams(url + suffix) is None
