"""SQL preview generator for FotMob registry seed dry-run.
lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN
"""


def _esc(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _emit(lines, table, columns, records, build_vals):
    lines.append(f"-- {table}")
    for r in records:
        lines.append(f"-- INSERT INTO {table} ({columns}) VALUES ({build_vals(r)});")
    lines.append("")


def generate(plan: dict) -> str:
    lines = [
        "-- ============================================================================",
        "-- DRY-RUN SQL PREVIEW ONLY",
        "-- DO NOT EXECUTE IN THIS PR",
        "-- Generated from fixture metadata only. No database write was performed.",
        "-- ============================================================================",
        "",
    ]

    teams = plan.get("teams", [])
    _emit(
        lines,
        "football_teams",
        "source, source_team_id, team_name, team_type, country, gender, active",
        teams,
        lambda t: ", ".join(
            [
                _esc(t.get("source", "fotmob")),
                _esc(t["source_team_id"]),
                _esc(t["team_name"]),
                _esc(t["team_type"]),
                _esc(t.get("country")),
                _esc(t.get("gender", "men")),
                _esc(t.get("active", True)),
            ]
        ),
    )

    competitions = plan.get("competitions", [])
    _emit(
        lines,
        "football_competitions",
        "source, source_competition_id, competition_name, competition_type, country, confederation, tier, active",
        competitions,
        lambda c: ", ".join(
            [
                _esc(c.get("source", "fotmob")),
                _esc(c["source_competition_id"]),
                _esc(c["competition_name"]),
                _esc(c["competition_type"]),
                _esc(c.get("country")),
                _esc(c.get("confederation")),
                _esc(c.get("tier")),
                _esc(c.get("active", True)),
            ]
        ),
    )

    editions_data = plan.get("competition_editions", [])
    _emit(
        lines,
        "football_competition_editions",
        "competition_id, season, edition_name, start_date, end_date, calendar_type, active",
        editions_data,
        lambda e: ", ".join(
            [
                f"/* competition_id from {e['competition_fixture_id']} */",
                _esc(e["season"]),
                _esc(e.get("edition_name")),
                _esc(e.get("start_date")),
                _esc(e.get("end_date")),
                _esc(e.get("calendar_type")),
                _esc(e.get("active", True)),
            ]
        ),
    )

    participations = plan.get("team_competition_participation", [])
    _emit(
        lines,
        "football_team_competition_participation",
        "team_id, competition_id, edition_id, participation_state, qualification_source",
        participations,
        lambda p: ", ".join(
            [
                f"/* team_id from {p['team_fixture_id']} */",
                f"/* competition_id from {p['competition_fixture_id']} */",
                f"/* edition_id from {p['edition_fixture_id']} */",
                _esc(p.get("participation_state", "unknown")),
                _esc(p.get("qualification_source")),
            ]
        ),
    )

    match_targets = plan.get("match_targets", [])
    _emit(
        lines,
        "football_match_targets",
        "source, source_match_id, competition_id, edition_id, match_date, home_team_id, away_team_id, match_status, target_state, priority, discovery_source, source_url, raw_json_status, attempt_count, last_error_code",
        match_targets,
        lambda mt: ", ".join(
            [
                _esc(mt.get("source", "fotmob")),
                _esc(mt["source_match_id"]),
                f"/* competition_id from {mt.get('competition_fixture_id', '')} */",
                f"/* edition_id from {mt.get('edition_fixture_id', '')} */",
                _esc(mt.get("match_date")),
                f"/* home_team_id from {mt.get('home_team_fixture_id', '')} */",
                f"/* away_team_id from {mt.get('away_team_fixture_id', '')} */",
                _esc(mt.get("match_status")),
                _esc(mt.get("target_state", "discovered")),
                str(mt.get("priority", 100)),
                _esc(mt.get("discovery_source")),
                _esc(mt.get("source_url")),
                _esc(mt.get("raw_json_status")),
                str(mt.get("attempt_count", 0)),
                _esc(mt.get("last_error_code")),
            ]
        ),
    )

    match_target_teams = plan.get("match_target_teams", [])
    _emit(
        lines,
        "football_match_target_teams",
        "match_target_id, team_id, role",
        match_target_teams,
        lambda mtt: ", ".join(
            [
                f"/* match_target_id from {mtt['match_target_fixture_id']} */",
                f"/* team_id from {mtt['team_fixture_id']} */",
                _esc(mtt.get("role", "participant")),
            ]
        ),
    )

    source_identities = plan.get("source_identities", [])
    _emit(
        lines,
        "football_source_identities",
        "source, entity_type, entity_id, source_entity_id",
        source_identities,
        lambda si: ", ".join(
            [
                _esc(si.get("source", "fotmob")),
                _esc(si.get("entity_type")),
                f"/* entity_id from {si.get('entity_fixture_id', '')} */",
                _esc(si.get("source_entity_id")),
            ]
        ),
    )

    lines.append("-- ============================================================================")
    lines.append("-- END OF DRY-RUN SQL PREVIEW")
    lines.append("-- All INSERT statements above are commented out.")
    lines.append("-- No database write was performed.")
    lines.append("-- ============================================================================")
    return "\n".join(lines)
