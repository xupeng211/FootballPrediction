#!/usr/bin/env python3
"""V143.6: Diagnostic script for Match Slug parsing issue.

This script simulates the entire flow from URL extraction to team parsing
to identify where the problem occurs.

Author: Diagnostic
Version: V143.6
Date: 2026-01-06
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.text_processor import TeamNameNormalizer


def simulate_url_parsing(url_path: str) -> tuple[str | None, str | None]:
    """Simulate the URL parsing logic from harvester_service.py.

    Args:
        url_path: The URL path extracted from the page

    Returns:
        Tuple of (home_team, away_team) or (None, None) if parsing failed
    """
    # Simulate Premier League team names from database
    db_team_names = {
        "Arsenal",
        "Aston Villa",
        "Bournemouth",
        "Brentford",
        "Brighton",
        "Chelsea",
        "Crystal Palace",
        "Everton",
        "Fulham",
        "Liverpool",
        "Manchester City",
        "Manchester United",
        "Newcastle United",
        "Nottingham Forest",
        "Tottenham",
        "West Ham",
        "Wolves",
    }

    normalizer = TeamNameNormalizer()

    # Step 1: Extract teams_part from URL path (harvester_service.py:1049-1055)
    path_parts = url_path.rstrip("/").split("/")
    teams_part = path_parts[-1] if len(path_parts) > 1 else url_path

    print(f"  URL path: {url_path}")
    print(f"  Initial teams_part: {teams_part}")

    # Step 2: Remove hash and query parameters (harvester_service.py:1054)
    teams_part = teams_part.split("#")[0].split("?")[0]
    print(f"  After removing hash/query: {teams_part}")

    # Step 3: Strip URL hash suffix (harvester_service.py:1056-1100)
    slug_parts = teams_part.split("-")
    if len(slug_parts) > 2:
        last_part = slug_parts[-1]
        is_hash = False

        if 7 <= len(last_part) <= 8:
            has_lower = any(c.islower() for c in last_part)
            has_upper = any(c.isupper() for c in last_part)
            has_digit = any(c.isdigit() for c in last_part)

            common_team_words = {
                "fc", "utd", "city", "united", "academy", "bilbao",
                "real", "de", "la", "al", "inter", "ac", "roma",
                "palace", "bvb", "rbl", "ssc", "afc", "cfc",
            }

            if (
                (has_lower and has_upper)
                or (has_lower and has_digit)
                or (
                    last_part.islower()
                    and last_part not in common_team_words
                    and len(last_part) >= 7
                )
            ):
                is_hash = True

        if is_hash:
            teams_part = "-".join(slug_parts[:-1])
            print(f"  After stripping hash: {teams_part}")

    # Step 4: Parse team slugs using TeamNameNormalizer
    team_slugs = normalizer.parse_team_slug_full_path(
        teams_part, db_team_names, threshold=85.0
    )

    if team_slugs:
        home_team = " ".join(word.title() for word in team_slugs[0].split("-"))
        away_team = " ".join(word.title() for word in team_slugs[1].split("-"))
        return home_team, away_team
    else:
        return None, None


def main():
    """Run diagnostic tests."""
    print("=" * 80)
    print("V143.6: Match Slug Parsing Diagnostic")
    print("=" * 80)
    print()

    # Test cases based on the user's description
    test_cases = [
        # Standard two-word slugs
        "/football/england/premier-league-2023-2024/arsenal-everton/",
        "/football/england/premier-league-2023-2024/brentford-everton/",

        # Three-word slugs with suffix
        "/football/england/premier-league-2023-2024/brentford-newcastle-utd/",

        # With hash suffix
        "/football/england/premier-league-2023-2024/arsenal-everton-a1B2c3D4/",

        # Manchester derby
        "/football/england/premier-league-2023-2024/manchester-city-manchester-united/",

        # London derby
        "/football/england/premier-league-2023-2024/arsenal-tottenham/",

        # Edge case: league-only page (should be filtered)
        "/football/england/premier-league-2023-2024/",

        # Edge case: standings page (should be filtered)
        "/football/england/premier-league-2023-2024/standings/",

        # Edge case: outrights page (should be filtered)
        "/football/england/premier-league-2023-2024/outrights/",
    ]

    for url_path in test_cases:
        print(f"\n{'─' * 80}")
        home, away = simulate_url_parsing(url_path)

        if home and away:
            print(f"  ✅ SUCCESS: {home} vs {away}")
        else:
            print(f"  ❌ FAILED: Could not parse teams")

    print()
    print("=" * 80)
    print("Diagnostic Summary")
    print("=" * 80)

    # Count successes and failures
    success_count = 0
    failure_count = 0

    for url_path in test_cases:
        home, away = simulate_url_parsing(url_path)
        if home and away:
            success_count += 1
        else:
            failure_count += 1

    print(f"\n  ✅ Successful parses: {success_count}")
    print(f"  ❌ Failed parses: {failure_count}")
    print()

    # Check if the issue is in URL filtering
    print("=" * 80)
    print("Potential Issue: URL Filtering Logic")
    print("=" * 80)
    print()
    print("If the unit tests pass but actual harvesting fails, the issue")
    print("might be in the JavaScript URL filtering logic in harvester_service.py")
    print("(lines 953-1019). The regex patterns might be too aggressive.")
    print()


if __name__ == "__main__":
    main()
