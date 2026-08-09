"""Source loading and match-level evaluation dataset construction.

Consumes M3-R2 canonical accepted observations (per-match odds by phase and
bookmaker, canonical identities, kickoff times) and the pinned Football-Data
CSV rows they were extracted from (FTR labels). The join is by the
observation's raw_record_locator (csv:row=N) plus the source file the
observation came from — never by team name.
"""

from __future__ import annotations

import csv as csv_module
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

from src.ml.value_mvp.protocol import season_of_kickoff

if TYPE_CHECKING:
    from pathlib import Path

OBSERVATION_SOURCES: tuple[str, ...] = ("raw_odds_2223", "raw_odds_2324", "real_odds_raw")

_LOCATOR_RE = re.compile(r"csv:row=(\d+):")

_LABEL_INDEX = {"H": 0, "D": 1, "A": 2}


@dataclass
class Match:
    """One canonical match with odds by phase/bookmaker/selection and a label."""

    mid: str
    kickoff_at: str
    home: str
    away: str
    season: str
    label: int
    label_str: str
    home_goals: int = 0
    away_goals: int = 0
    odds: dict[str, dict[str, dict[str, float]]] = field(
        default_factory=dict
    )  # phase -> bookmaker -> selection -> odds
    sources: tuple[tuple[str, int], ...] = field(default_factory=tuple)  # (source, csv_row) pairs


def load_observations(observations_dir: Path) -> list[dict[str, Any]]:
    """Load all accepted observations; tag each with its source file name."""
    observations: list[dict[str, Any]] = []
    for source in OBSERVATION_SOURCES:
        path = observations_dir / f"{source}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"missing observations file: {path}")
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                obs = json.loads(line)
                obs["_source"] = source
                observations.append(obs)
    return observations


def load_csv_rows(csv_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load the pinned CSV rows per source."""
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for source in OBSERVATION_SOURCES:
        path = csv_dir / f"{source}.csv"
        if not path.exists():
            raise FileNotFoundError(f"missing csv file: {path}")
        with path.open("r", encoding="utf-8") as handle:
            rows_by_source[source] = list(csv_module.DictReader(handle))
    return rows_by_source


def _locator_row(locator: str) -> int:
    """Extract the csv row number from an observation raw_record_locator."""
    match = _LOCATOR_RE.search(locator)
    if match is None:
        raise ValueError(f"unparseable raw_record_locator: {locator}")
    return int(match.group(1))


def csv_row_for(csv_rows: dict[str, list[dict[str, Any]]], source: str, row: int) -> dict[str, Any]:
    """Return the CSV data row for locator row N (N = CSV line, header = line 1)."""
    rows = csv_rows[source]
    index = row - 2
    if index < 0 or index >= len(rows):
        raise ValueError(f"csv row out of range: {source}:{row}")
    return rows[index]


def build_dataset(
    observations: list[dict[str, Any]],
    csv_rows: dict[str, list[dict[str, Any]]],
    protocol: dict[str, Any],
) -> list[Match]:
    """Build the match-level evaluation dataset from observations and CSVs.

    Raises ValueError on population inconsistencies: missing matched_id,
    conflicting kickoff/teams per match, missing or conflicting FTR labels,
    or observations referencing CSV rows outside the pinned files.
    """
    season_rule = protocol["season_assignment_rule"]
    by_mid: dict[str, dict[str, Any]] = {}

    for obs in observations:
        match_link = obs.get("match_link") or {}
        mid = match_link.get("matched_id")
        if not mid:
            raise ValueError(f"observation without matched_id: {obs.get('raw_record_locator')}")
        entry = by_mid.setdefault(
            mid,
            {
                "kickoff_at": obs["kickoff_at"],
                "home": obs["home_team"],
                "away": obs["away_team"],
                "odds": {},
                "sources": set(),
            },
        )
        if obs["kickoff_at"] != entry["kickoff_at"]:
            raise ValueError(
                f"conflicting kickoff for {mid}: {obs['kickoff_at']} vs {entry['kickoff_at']}"
            )
        if obs["home_team"] != entry["home"] or obs["away_team"] != entry["away"]:
            raise ValueError(f"conflicting teams for {mid}")
        phase = obs["provider_collection_phase"]
        bookmaker = obs["bookmaker_source_id"]
        entry["odds"].setdefault(phase, {}).setdefault(bookmaker, {})[obs["selection"]] = float(
            obs["decimal_odds"]
        )
        entry["sources"].add((obs["_source"], _locator_row(obs["raw_record_locator"])))

    matches: list[Match] = []
    for mid in sorted(by_mid):
        entry = by_mid[mid]
        season = season_of_kickoff(entry["kickoff_at"], season_rule)
        label_str, home_goals, away_goals = _join_label_and_goals(mid, entry, csv_rows)
        matches.append(
            Match(
                mid=mid,
                kickoff_at=entry["kickoff_at"],
                home=entry["home"],
                away=entry["away"],
                season=season,
                label=_LABEL_INDEX[label_str],
                label_str=label_str,
                home_goals=home_goals,
                away_goals=away_goals,
                odds=entry["odds"],
                sources=tuple(sorted(entry["sources"])),
            )
        )
    return matches


def _join_label_and_goals(
    mid: str, entry: dict[str, Any], csv_rows: dict[str, list[dict[str, Any]]]
) -> tuple[str, int, int]:
    """Join FTR label and goals from the pinned CSV rows behind a match."""
    label_str: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    for source, row in sorted(entry["sources"]):
        row_dict = csv_row_for(csv_rows, source, row)
        candidate = row_dict.get("FTR")
        if candidate is None or candidate == "":
            raise ValueError(f"missing FTR for {mid} at {source}:{row}")
        if label_str is None:
            label_str = candidate
        elif candidate != label_str:
            raise ValueError(f"conflicting FTR for {mid}: {candidate} vs {label_str}")
        goals = _goals_pair(row_dict, source, row, mid)
        if home_goals is None:
            home_goals, away_goals = goals
        elif goals != (home_goals, away_goals):
            raise ValueError(f"conflicting goals for {mid}: {goals} vs {(home_goals, away_goals)}")
    if label_str is None:
        raise ValueError(f"no FTR label resolved for {mid}")
    return label_str, home_goals or 0, away_goals or 0


def _goals_pair(row_dict: dict[str, Any], source: str, row: int, mid: str) -> tuple[int, int]:
    """Parse FTHG/FTAG from a pinned CSV row as the match's goal label data."""
    try:
        return int(row_dict["FTHG"]), int(row_dict["FTAG"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"invalid goals for {mid} at {source}:{row}: {row_dict.get('FTHG')!r}/{row_dict.get('FTAG')!r}"
        ) from exc


def evaluation_population_hash(matches: list[Match]) -> str:
    """Deterministic SHA256 over the sorted evaluation population projection.

    Projection rows: season | kickoff_at | home | away | label | mid | sources.
    Predictions and wall-clock are never part of this hash.
    """
    lines = []
    for match in sorted(matches, key=lambda m: (m.season, m.kickoff_at, m.mid)):
        sources = ";".join(f"{s}:{r}" for s, r in sorted(match.sources))
        lines.append(
            f"{match.season}|{match.kickoff_at}|{match.home}|{match.away}|"
            f"{match.label_str}|{match.mid}|{sources}"
        )
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def season_counts(matches: list[Match]) -> dict[str, int]:
    """Per-season match counts."""
    counts: dict[str, int] = {}
    for match in matches:
        counts[match.season] = counts.get(match.season, 0) + 1
    return counts
