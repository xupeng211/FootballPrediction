#!/usr/bin/env python3
"""联赛到 OddsPortal URL 的映射工具。"""

from __future__ import annotations

import logging
from typing import ClassVar

logger = logging.getLogger(__name__)


class LeagueUrlMapper:
    """联赛 URL slug 映射器。"""

    LEAGUE_MAPPINGS: ClassVar[dict[str, tuple[str, str]]] = {
        "premier league": ("england", "premier-league"),
        "english premier league": ("england", "premier-league"),
        "epl": ("england", "premier-league"),
        "championship": ("england", "championship"),
        "efl cup": ("england", "efl-cup"),
        "fa cup": ("england", "fa-cup"),
        "la liga": ("spain", "laliga"),
        "primera divisin": ("spain", "laliga"),
        "segunda divisin": ("spain", "segunda-division"),
        "copa del rey": ("spain", "copa-del-rey"),
        "serie a": ("italy", "serie-a"),
        "serie b": ("italy", "serie-b"),
        "coppa italia": ("italy", "coppa-italia"),
        "bundesliga": ("germany", "bundesliga"),
        "1. bundesliga": ("germany", "bundesliga"),
        "2. bundesliga": ("germany", "2-bundesliga"),
        "dfb pokal": ("germany", "dfb-pokal"),
        "ligue 1": ("france", "ligue-1"),
        "ligue 2": ("france", "ligue-2"),
        "coupe de france": ("france", "coupe-de-france"),
        "primeira liga": ("portugal", "primeira-liga"),
        "taça de portugal": ("portugal", "tacca-de-portugal"),
        "taça da liga": ("portugal", "tacca-da-liga"),
        "eredivisie": ("netherlands", "eredivisie"),
        "eerste divisie": ("netherlands", "eerste-divisie"),
        "knvb beker": ("netherlands", "knvb-beker"),
        "first division a": ("belgium", "first-division-a"),
        "jupiler pro league": ("belgium", "first-division-a"),
        "belgian first division a": ("belgium", "first-division-a"),
        "belgian cup": ("belgium", "belgian-cup"),
        "premiership": ("scotland", "premiership"),
        "scottish premiership": ("scotland", "premiership"),
        "scottish championship": ("scotland", "championship"),
        "scottish cup": ("scotland", "scottish-cup"),
        "super lig": ("turkey", "super-lig"),
        "turkish super lig": ("turkey", "super-lig"),
        "super league greece": ("greece", "super-league"),
        "greek super league": ("greece", "super-league"),
        "russian premier league": ("russia", "premier-league"),
        "ukrainian premier league": ("ukraine", "premier-league"),
        "ekstraklasa": ("poland", "ekstraklasa"),
        "first league": ("czech-republic", "1-liga"),
        "czech first league": ("czech-republic", "1-liga"),
        "austrian bundesliga": ("austria", "bundesliga"),
        "super league": ("switzerland", "super-league"),
        "swiss super league": ("switzerland", "super-league"),
        "superliga": ("denmark", "superliga"),
        "danish superliga": ("denmark", "superliga"),
        "eliteserien": ("norway", "eliteserien"),
        "norwegian eliteserien": ("norway", "eliteserien"),
        "allsvenskan": ("sweden", "allsvenskan"),
        "brasileirao": ("brazil", "serie-a"),
        "brazilian serie a": ("brazil", "serie-a"),
        "primera division": ("argentina", "primera-division"),
        "argentine primera division": ("argentina", "primera-division"),
        "liga mx": ("mexico", "liga-mx"),
        "mexican primera division": ("mexico", "liga-mx"),
        "major league soccer": ("usa", "mls"),
        "mls": ("usa", "mls"),
        "chinese super league": ("china", "super-league"),
        "j1 league": ("japan", "j1-league"),
        "j league": ("japan", "j1-league"),
        "k league 1": ("south-korea", "k-league-1"),
        "a-league": ("australia", "a-league"),
        "champions league": ("europe", "champions-league"),
        "uefa champions league": ("europe", "champions-league"),
        "europa league": ("europe", "europa-league"),
        "uefa europa league": ("europe", "europa-league"),
        "conference league": ("europe", "conference-league"),
        "uefa conference league": ("europe", "conference-league"),
        "euro championship": ("europe", "euro"),
        "european championship": ("europe", "euro"),
        "world cup": ("world", "world-cup"),
        "copa america": ("south-america", "copa-america"),
    }

    def __init__(self) -> None:
        self._build_reverse_index()

    def _build_reverse_index(self) -> None:
        self._index: dict[str, tuple[str, str]] = {}
        for league_name, (country, slug) in self.LEAGUE_MAPPINGS.items():
            self._index[league_name.lower().strip()] = (country, slug)

    def get_league_slug(self, league_name: str, season: str) -> tuple[str, str] | None:
        del season
        if not league_name:
            return None

        normalized = league_name.lower().strip()
        if normalized in self._index:
            return self._index[normalized]

        for key, value in self._index.items():
            if normalized in key or key in normalized:
                return value

        logger.warning("League slug not found for: %s", league_name)
        return None

    def construct_results_url(
        self,
        league_name: str,
        season: str,
        base_url: str = "https://www.oddsportal.com",
    ) -> str | None:
        result = self.get_league_slug(league_name, season)
        if not result:
            return None

        country, slug = result
        season_formatted = season.strip()
        return f"{base_url}/football/{country}/{slug}-{season_formatted}/results/"

    def get_all_mappings(self) -> dict[str, tuple[str, str]]:
        return self.LEAGUE_MAPPINGS.copy()

    def is_supported(self, league_name: str) -> bool:
        normalized = league_name.lower().strip()
        if normalized in self._index:
            return True
        return any(normalized in key or key in normalized for key in self._index)
