#!/usr/bin/env python3
"""Team slug 全路径解析 mixin。"""
# ruff: noqa: PLR0912, PLR0915, PLR2004

from __future__ import annotations

import logging

from thefuzz import fuzz

logger = logging.getLogger(__name__)


class TeamSlugParserMixin:
    """为 TeamNameNormalizer 提供全路径 slug 解析能力。"""

    def are_same_team(self, name1: str, name2: str) -> bool:
        raise NotImplementedError

    def normalize(self, team_name: str) -> str:
        raise NotImplementedError

    def parse_team_slug_full_path(
        self,
        teams_part: str,
        db_team_names: set[str],
        threshold: int = 85,
    ) -> list[str] | None:
        parts = teams_part.split("-")
        is_cold_start = len(db_team_names) == 0

        best_split: list[str] | None = None
        best_combined_score = 0.0
        suffixes = {"united", "city", "utd", "fc", "afc", "cfc", "rc", "bilbao"}

        if is_cold_start:
            has_year = any(
                len(part) == 4 and part.isdigit() and part.startswith("20") for part in parts
            )
            league_keywords = {
                "league",
                "ligue",
                "bundesliga",
                "serie",
                "premier",
                "laliga",
                "eredivisie",
            }
            has_league_keyword = any(keyword in teams_part.lower() for keyword in league_keywords)

            if has_year or has_league_keyword:
                logger.debug("[V143.8] Cold start: Rejected league/season slug: %s", teams_part)
                return None

            if teams_part.lower() in {"standings", "table", "outrights", "fixtures", "results"}:
                logger.debug("[V143.7] Cold start: Rejected navigation page: %s", teams_part)
                return None

            if len(parts) < 2:
                logger.debug("[V143.7] Cold start: Rejected single-word slug: %s", teams_part)
                return None

        for i in range(1, len(parts)):
            home_slug = "-".join(parts[:i])
            away_slug = "-".join(parts[i:])

            home_parts = home_slug.split("-")
            away_parts = away_slug.split("-")

            if is_cold_start:
                if len(away_parts) == 1 and away_parts[0].lower() in suffixes:
                    continue
                if len(home_parts) == 1 and home_parts[0].lower() in suffixes:
                    continue
            else:
                if len(home_parts) > 1 and home_parts[-1].lower() in suffixes:
                    home_display = " ".join(word.title() for word in home_parts)
                    is_known_team = any(
                        self.are_same_team(home_display, db_name) for db_name in db_team_names
                    )
                    if not is_known_team:
                        continue

                if len(away_parts) == 1 and away_parts[0].lower() in suffixes:
                    away_display = " ".join(word.title() for word in away_parts)
                    is_known_team = any(
                        self.are_same_team(away_display, db_name) for db_name in db_team_names
                    )
                    if not is_known_team:
                        continue

                if len(away_parts) > 1 and away_parts[0].lower() in suffixes:
                    away_display = " ".join(word.title() for word in away_parts)
                    is_known_team = any(
                        self.are_same_team(away_display, db_name) for db_name in db_team_names
                    )
                    if not is_known_team:
                        continue

            home_display = " ".join(word.title() for word in home_slug.split("-"))
            away_display = " ".join(word.title() for word in away_slug.split("-"))

            if is_cold_start:
                home_word_count = len(home_parts)
                away_word_count = len(away_parts)
                word_count_balance = abs(home_word_count - away_word_count)
                combined_score = 100.0 - (word_count_balance * 5.0)

                if combined_score < 85.0:
                    continue
            else:
                max_home_score = 0.0
                max_away_score = 0.0

                for db_name in db_team_names:
                    db_word_count = len(db_name.split())

                    if self.are_same_team(home_display, db_name):
                        if len(home_parts) == db_word_count:
                            base_score = 100.0
                        elif len(home_parts) < db_word_count and len(home_parts) >= 2:
                            base_score = 95.0
                        elif len(home_parts) == 1 and db_word_count >= 2:
                            base_score = 92.0
                        else:
                            base_score = 85.0
                        word_count_bonus = 1.0 + (db_word_count - len(home_parts)) * 0.1
                        max_home_score = max(max_home_score, base_score * word_count_bonus)
                    else:
                        norm_home = self.normalize(home_display)
                        norm_db = self.normalize(db_name)
                        token_sort_score = fuzz.token_sort_ratio(norm_home, norm_db)
                        standard_score = fuzz.ratio(norm_home, norm_db)
                        home_score = float(max(token_sort_score, standard_score))
                        word_count_ratio = db_word_count / len(home_parts)
                        if word_count_ratio >= 1.0:
                            home_score *= 1.0 + (word_count_ratio - 1.0) * 0.2
                        max_home_score = max(max_home_score, home_score)

                    if self.are_same_team(away_display, db_name):
                        db_word_count = len(db_name.split())
                        if len(away_parts) == db_word_count:
                            base_score = 100.0
                        elif len(away_parts) < db_word_count and len(away_parts) >= 2:
                            base_score = 95.0
                        elif len(away_parts) == 1 and db_word_count >= 2:
                            base_score = 92.0
                        else:
                            base_score = 85.0
                        word_count_bonus = 1.0 + (db_word_count - len(away_parts)) * 0.1
                        max_away_score = max(max_away_score, base_score * word_count_bonus)
                    else:
                        norm_away = self.normalize(away_display)
                        norm_db = self.normalize(db_name)
                        token_sort_score = fuzz.token_sort_ratio(norm_away, norm_db)
                        standard_score = fuzz.ratio(norm_away, norm_db)
                        away_score = float(max(token_sort_score, standard_score))
                        word_count_ratio = db_word_count / len(away_parts)
                        if word_count_ratio >= 1.0:
                            away_score *= 1.0 + (word_count_ratio - 1.0) * 0.2
                        max_away_score = max(max_away_score, away_score)

                combined_score = (max_home_score + max_away_score) / 2
                if max_home_score < threshold or max_away_score < threshold:
                    continue

            if best_split is None or combined_score > best_combined_score:
                best_combined_score = combined_score
                best_split = [home_slug, away_slug]
            elif combined_score == best_combined_score:
                current_balance = abs(len(home_parts) - len(away_parts))
                best_balance = (
                    abs(len(best_split[0].split("-")) - len(best_split[1].split("-")))
                    if best_split
                    else 999
                )
                if current_balance < best_balance:
                    best_split = [home_slug, away_slug]

        if best_split is None and not is_cold_start:
            logger.debug(
                "[V143.9] No split met threshold, using intelligent fallback: %s", teams_part
            )
            special_patterns = {
                "utd": ["sheffield", "newcastle"],
                "united": ["manchester"],
            }
            fallback_best_split: list[str] | None = None
            fallback_best_combined_score = 0.0

            for i in range(1, len(parts)):
                home_slug = "-".join(parts[:i])
                away_slug = "-".join(parts[i:])

                home_parts = home_slug.split("-")
                away_parts = away_slug.split("-")

                should_reject_split = False
                if len(away_parts) >= 1 and away_parts[0].lower() in suffixes:
                    suffix_to_attach = away_parts[0].lower()
                    for pattern, cities in special_patterns.items():
                        if (
                            suffix_to_attach == pattern
                            and len(home_parts) >= 1
                            and any(city.lower() == home_parts[-1].lower() for city in cities)
                        ):
                            should_reject_split = True
                            break

                if should_reject_split:
                    continue
                if len(away_parts) == 1 and away_parts[0].lower() in suffixes:
                    continue
                if len(home_parts) == 1 and home_parts[0].lower() in suffixes:
                    continue

                home_word_count = len(home_parts)
                away_word_count = len(away_parts)
                word_count_balance = abs(home_word_count - away_word_count)
                combined_score = 100.0 - (word_count_balance * 5.0)

                if combined_score < 85.0:
                    continue

                if fallback_best_split is None or combined_score > fallback_best_combined_score:
                    fallback_best_combined_score = combined_score
                    fallback_best_split = [home_slug, away_slug]
                elif combined_score == fallback_best_combined_score:
                    best_balance = (
                        abs(
                            len(fallback_best_split[0].split("-"))
                            - len(fallback_best_split[1].split("-"))
                        )
                        if fallback_best_split
                        else 999
                    )
                    if word_count_balance < best_balance:
                        fallback_best_split = [home_slug, away_slug]

            if fallback_best_split is not None:
                best_combined_score = fallback_best_combined_score
                best_split = fallback_best_split

        if best_split:
            home_display = " ".join(word.title() for word in best_split[0].split("-"))
            away_display = " ".join(word.title() for word in best_split[1].split("-"))
            logger.info(
                "  ✨ Team match: [%s] vs [%s] (score: %s%%)",
                home_display,
                away_display,
                int(best_combined_score),
            )
        else:
            logger.warning("  ⚠️  Failed to parse team slug: %s", teams_part)

        return best_split
