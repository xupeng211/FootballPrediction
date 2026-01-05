#!/usr/bin/env python3
"""V143.6: Diagnostic script for JavaScript URL filtering logic.

This script tests the JavaScript URL filtering logic from harvester_service.py
to identify if valid match URLs are being incorrectly filtered out.

Author: Diagnostic
Version: V143.6
Date: 2026-01-06
"""

import re


def simulate_javascript_url_filtering(href: str) -> tuple[bool, str]:
    """Simulate the JavaScript URL filtering logic from harvester_service.py.

    This is a Python translation of the JavaScript code at lines 953-1019.

    Args:
        href: The href attribute from the anchor tag

    Returns:
        Tuple of (should_include, reason)
        - should_include: True if the URL should be included in results
        - reason: Description of why it was included or excluded
    """
    # Base check: must be /football/ link
    if not href or "/football/" not in href:
        return False, "Not a /football/ link"

    # Exclude fixtures/results directories (already processed)
    if "/fixtures/" in href or "/results/" in href:
        return False, "Fixtures/results directory"

    # 1. Outrights (冠军投注页面)
    if re.search(r'\boutrights\b', href, re.IGNORECASE):
        return False, "Outrights page"

    # 2. Standings/Tables (积分榜页面)
    if re.search(r'\b(standings|table)\b', href, re.IGNORECASE):
        return False, "Standings/tables page"

    # 3. Blocked leagues - regex pattern catches at ANY position
    blocked_leagues = [
        'premier-league', 'laliga', 'serie-a', 'bundesliga',
        'ligue-1', 'eredivisie', 'champions-league',
        'europa-league', 'conference-league'
    ]
    blocked_pattern = re.compile(r'\b(' + '|'.join(blocked_leagues) + r')\b', re.IGNORECASE)

    path_parts = href.strip('/').split('/')
    last_part = path_parts[-1] if path_parts else ''

    # If last part is EXACTLY a blocked league (standalone league page)
    if blocked_pattern.search(last_part):
        return False, f"Blocked league: {last_part}"

    # 4. League-only pages without team patterns
    # Match pages should have: /country/league-season/team1-team2/
    # League-only pages have: /country/league-season/ or /country/league/

    def has_team_pattern(part: str) -> bool:
        """Check if a URL part has team pattern."""
        # Check for -vs- pattern
        if re.search(r'-vs-', part, re.IGNORECASE):
            return True

        # Check for hyphenated words (team names)
        if '-' in part:
            # Exclude league-only parts
            if re.search(r'\bleague\b', part, re.IGNORECASE):
                return False
            # Exclude year patterns
            if re.search(r'\b20\d{2}\b', part):
                return False
            # At least 2 words with hyphens
            if len(part.split('-')) >= 2:
                return True

        return False

    has_pattern = any(has_team_pattern(part) for part in path_parts)

    # If no team pattern AND path is too short, likely a league page
    if not has_pattern and len(path_parts) < 5:
        return False, f"No team pattern, short path ({len(path_parts)} parts)"

    # Passed all checks
    return True, "Valid match URL"


def main():
    """Run diagnostic tests on JavaScript URL filtering logic."""
    print("=" * 80)
    print("V143.6: JavaScript URL Filtering Logic Diagnostic")
    print("=" * 80)
    print()

    # Test cases covering various URL patterns
    test_cases = [
        # Valid match URLs (should PASS)
        ("/football/england/premier-league-2023-2024/arsenal-everton/", True, "Standard match"),
        ("/football/england/premier-league-2023-2024/brentford-newcastle-utd/", True, "Three-word slug"),
        ("/football/england/premier-league-2023-2024/manchester-city-manchester-united/", True, "Manchester derby"),
        ("/football/england/premier-league-2023-2024/arsenal-everton-a1B2c3D4/", True, "With hash suffix"),
        ("/football/england/premier-league-2023-2024/arsenal-everton-1X2/", True, "With 1X2 suffix"),
        ("/football/england/premier-league-2023-2024/arsenal-vs-everton/", True, "With -vs- pattern"),

        # Invalid URLs (should FAIL)
        ("/football/england/premier-league-2023-2024/", False, "League-only page"),
        ("/football/england/premier-league-2023-2024/standings/", False, "Standings page"),
        ("/football/england/premier-league-2023-2024/outrights/", False, "Outrights page"),
        ("/football/england/premier-league/", False, "League root page"),
        ("/football/england/premier-league-2023-2024/results/", False, "Results directory"),
        ("/football/england/premier-league-2023-2024/fixtures/", False, "Fixtures directory"),

        # Edge cases
        ("/football/england/premier-league-2023-2024/table/", False, "Table page"),
        ("/football/england/championship-2023-2024/leeds-united-sheffield-united/", True, "Championship match"),
    ]

    passed = 0
    failed = 0

    for href, expected, description in test_cases:
        should_include, reason = simulate_javascript_url_filtering(href)

        # Check if result matches expectation
        if should_include == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        expected_str = "INCLUDE" if expected else "EXCLUDE"
        actual_str = "INCLUDE" if should_include else "EXCLUDE"

        print(f"{status}: {description}")
        print(f"  URL: {href}")
        print(f"  Expected: {expected_str} | Actual: {actual_str}")
        print(f"  Reason: {reason}")
        print()

    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"  Passed: {passed}/{len(test_cases)}")
    print(f"  Failed: {failed}/{len(test_cases)}")
    print()

    if failed > 0:
        print("⚠️  WARNING: Some URLs are being incorrectly filtered!")
        print()
        print("Possible issues:")
        print("  1. Regex patterns are too aggressive")
        print("  2. Team pattern detection logic is too strict")
        print("  3. Path length check is filtering valid matches")
        print()

    # Check for potential false positives
    print("=" * 80)
    print("Checking for False Positives (valid URLs incorrectly filtered)")
    print("=" * 80)
    print()

    false_positives = []
    for href, expected, description in test_cases:
        if expected:  # Should be included
            should_include, reason = simulate_javascript_url_filtering(href)
            if not should_include:
                false_positives.append((href, description, reason))

    if false_positives:
        print("❌ Found FALSE POSITIVES (valid URLs being filtered):")
        for href, description, reason in false_positives:
            print(f"  - {description}: {href}")
            print(f"    Reason: {reason}")
        print()
    else:
        print("✅ No false positives detected")
        print()

    # Check for potential false negatives
    print("=" * 80)
    print("Checking for False Negatives (invalid URLs not filtered)")
    print("=" * 80)
    print()

    false_negatives = []
    for href, expected, description in test_cases:
        if not expected:  # Should be excluded
            should_include, reason = simulate_javascript_url_filtering(href)
            if should_include:
                false_negatives.append((href, description, reason))

    if false_negatives:
        print("❌ Found FALSE NEGATIVES (invalid URLs not filtered):")
        for href, description, reason in false_negatives:
            print(f"  - {description}: {href}")
            print(f"    Reason: {reason}")
        print()
    else:
        print("✅ No false negatives detected")
        print()


if __name__ == "__main__":
    main()
