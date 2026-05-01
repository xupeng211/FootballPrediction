# Phase 4.16 Local HTML Odds Commit Report

> Status: local report draft. Do not commit unless explicitly approved.
>
> Scope: one local HTML odds commit for match `140_20252026_4837496`.
>
> Generated on: 2026-05-01

## 1. Current HEAD

```text
branch before report: main
report branch: docs/local-html-odds-commit-phase416
HEAD: c745bc15aa64cf1f3bf3ddb57b95a6bb3dc36ea2
```

## 2. Preconditions

Dev stack status before commit:

```text
db: healthy
dev: healthy
redis: healthy
prometheus: healthy
grafana: healthy
```

Data environment check:

```text
make data-check: passed
```

Target match before commit:

```text
match_id:        140_20252026_4837496
league_name:     Segunda Division
season:          2025/2026
home_team:       Cultural Leonesa
away_team:       Burgos CF
match_date:      2026-05-24 17:00:00+00
status:          scheduled
data_source:     manual_html_seed
data_version:    PHASE4.13
pipeline_status: pending
```

Target odds history before commit:

```text
target_odds_history_rows: 0
```

## 3. Commit Command

Only the authorized local file was used:

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/local_dom_ingestor.js \
    --file data/manual_html/test_sample.html \
    --commit
```

No network harvesting command was run.

## 4. Commit Result

The command completed successfully:

```text
[LOCAL-DOM] commit complete total=2 inserted=2 updated=0 migrationApplied=false
```

Parsed match:

```text
match_id: 140_20252026_4837496
league:   Segunda Division
home:     Cultural Leonesa
away:     Burgos CF
kickoff:  2026-05-24T17:00:00Z
rows:     2
```

## 5. Inserted Odds Rows

Target odds history after commit:

```text
target_odds_history_rows: 2
```

Rows:

```text
Bet365   | 1x2            | open={"home":2.1,"draw":3.2,"away":3.55} | close={"home":2,"draw":3.3,"away":3.8}
Pinnacle | Asian Handicap | open={"line":"-0.25","home":1.92,"away":1.96} | close={"line":"0","home":1.84,"away":2.05}
```

Collected timestamp:

```text
2026-05-01 09:53:32.276
```

## 6. Row Counts

After commit:

```text
matches                    1
bookmaker_odds_history     2
matches_oddsportal_mapping 0
l3_features                0
raw_match_data             0
```

## 7. Risks And Notes

- This was a local sample write only, not a real harvest.
- The parent `matches` row was seeded in Phase 4.13.
- The odds rows came only from `data/manual_html/test_sample.html`.
- Re-running the same commit would likely update the two existing rows because `bookmaker_odds_history` has a unique constraint on `(match_id, bookmaker_name, market_type)`.
- No rollback was performed or attempted.

## 8. Suggested Next Step

Recommended next phase:

1. Add a small, safety-gated Makefile target or runbook for single-file local odds commit.
2. Add a post-commit read-only verification command for target `match_id`.
3. Decide whether to keep this local sample DB state for later L3/ELO dry-run checks or restore from backup before broader testing.

Do not proceed to batch harvest or network dry-run without separate authorization.

## 9. Non-Execution Confirmation

Not executed:

- external network access
- real harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- seed commit
- `csv_bulk_loader --commit`
- Docker volume cleanup
- `git push`
- `git pull`
- `git fetch --all`
- code changes
- commit
