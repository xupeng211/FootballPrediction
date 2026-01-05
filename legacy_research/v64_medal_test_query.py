#!/usr/bin/env python3
"""Query database for V64.0 Medal Test samples."""

import psycopg2
from src.config_unified import get_settings

def get_medal_test_samples(limit: int = 5) -> list[dict]:
    """Get real matches that haven't been harvested yet."""
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT match_id, home_team, away_team, league_name, match_date, url
        FROM metrics_multi_source_data
        WHERE opening_time_h IS NULL
          AND url IS NOT NULL
          AND url LIKE '%oddsportal.com%'
          AND (league_name ILIKE '%bundesliga%' OR league_name ILIKE '%premier league%' OR league_name ILIKE '%england%')
        ORDER BY RANDOM()
        LIMIT %s
    """, (limit,))

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    matches = []
    for r in results:
        matches.append({
            'match_id': r[0],
            'home_team': r[1],
            'away_team': r[2],
            'league_name': r[3],
            'match_date': r[4],
            'url': r[5]
        })

    return matches

if __name__ == '__main__':
    matches = get_medal_test_samples(5)
    print(f"Found {len(matches)} matches for Medal Test:")
    for m in matches:
        print(f"  - {m['home_team']} vs {m['away_team']} ({m['league_name']})")
        print(f"    URL: {m['url']}")
