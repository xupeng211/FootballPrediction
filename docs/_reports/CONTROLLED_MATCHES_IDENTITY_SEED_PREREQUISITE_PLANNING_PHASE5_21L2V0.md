# Controlled Matches Identity Seed Prerequisite Planning - Phase 5.21L2V0

## 1. Executive summary

- L2V raw write was blocked by the FK / matches existence gate.
- The 50 candidate match_id values are missing from matches.
- L2V0 is matches identity seed prerequisite planning only.
- No DB write, matches write, raw_match_data write, network access, match detail fetch, parser, features, or training was executed.
- Real matches insert must happen in Phase 5.21L2V1 with separate final DB-write authorization.

## 2. Current DB baseline

- matches=10
- raw_match_data=18
- bookmaker_odds_history=2
- protected tables: l3_features=2, match_features_training=2, predictions=2

## 3. Manifest input summary

- manifest path: `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json`
- candidate_targets=50
- known_completed_targets=8
- write_execution_status=blocked_missing_matches_fk_prerequisite
- candidate write_status distribution={"blocked_missing_matches_fk_prerequisite":50}
- required_next_step before planning=controlled_matches_identity_seed_prerequisite_planning

## 4. Matches schema readiness

- matches columns: match_id, external_id, league_name, season, home_team, away_team, home_score, away_score, actual_result, match_date, venue, status, is_finished, collection_date, created_at, updated_at, data_version, data_source, pipeline_status, home_corners, away_corners, home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards, referee
- required non-null columns: match_id, league_name, season, home_team, away_team
- primary key match_id present=true
- matches_pkey index present=true
- season_format check present=true
- status_lowercase check present=true
- pipeline_status check present=true
- manifest has all mapped required values=true
- schema ready=true

Constraints:

- conname=matches_pipeline_status_valid, contype=c, definition=CHECK (((pipeline_status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'harvested'::character varying, 'failed'::character varying, 'skipped'::character varying, 'RECON_LINKED'::character varying, 'RECON_MISMATCH'::character varying])::text[])))
- conname=matches_pkey, contype=p, definition=PRIMARY KEY (match_id)
- conname=season_format, contype=c, definition=CHECK (((season)::text ~ '^\d{4}/\d{4}$'::text))
- conname=status_lowercase, contype=c, definition=CHECK (((status)::text = lower((status)::text)))
- conname=valid_scores, contype=c, definition=CHECK ((((home_score IS NULL) AND (away_score IS NULL)) OR ((home_score >= 0) AND (away_score >= 0))))

Indexes:

- indexname=idx_matches_date, indexdef=CREATE INDEX idx_matches_date ON public.matches USING btree (match_date DESC)
- indexname=idx_matches_finished, indexdef=CREATE INDEX idx_matches_finished ON public.matches USING btree (is_finished) WHERE (is_finished = true)
- indexname=idx_matches_pipeline_status, indexdef=CREATE INDEX idx_matches_pipeline_status ON public.matches USING btree (pipeline_status)
- indexname=idx_matches_season, indexdef=CREATE INDEX idx_matches_season ON public.matches USING btree (season)
- indexname=idx_matches_status, indexdef=CREATE INDEX idx_matches_status ON public.matches USING btree (status)
- indexname=idx_matches_teams, indexdef=CREATE INDEX idx_matches_teams ON public.matches USING btree (home_team, away_team)
- indexname=matches_pkey, indexdef=CREATE UNIQUE INDEX matches_pkey ON public.matches USING btree (match_id)

## 5. Identity eligibility audit

- candidate_count=50
- eligible_matches_insert_count=50
- skipped_existing_matches_count=0
- blocked_count=0
- duplicate_match_id_count=0
- duplicate_external_id_count=0
- external_id_conflict_count=0
- match_id_conflict_count=0
- invalid_identity_count=0
- missing_required_field_count=0
- existing_matches_count=0
- missing_matches_count=50
- would_insert_matches_count=50
- would_update_matches_count=0
- expected_matches_after=60

## 6. Future L2V1 controlled matches seed plan

L2V1 must require `FINAL_DB_WRITE_CONFIRMATION=yes`, `ALLOW_DB_WRITE=yes`, and `ALLOW_MATCHES_WRITE=yes`. It must keep `ALLOW_RAW_MATCH_DATA_WRITE=no`, insert only the 50 missing matches identity rows, avoid raw writes, odds writes, parser/features/training, and use a single transaction. Success verification should confirm matches 10 -> 60, raw_match_data remains 18, and protected tables remain unchanged. After L2V1 succeeds, retrying L2V raw write still needs separate renewed authorization.

## 7. Manifest update result

- manifest updated=true
- matches_identity_seed_plan_status=ready_for_final_authorization
- matches_identity_seed_authorization_status=pending_final_db_write_confirmation
- eligible_matches_insert_count=50
- expected_matches_after=60
- required_next_step=controlled_matches_identity_seed_execution

## 8. DB safety result

- matches=10
- raw_match_data=18
- bookmaker_odds_history=2
- l3_features=2
- match_features_training=2
- predictions=2

## 9. Verification results

- new matches seed prerequisite planning tests: passed
- L2V execution tests: passed
- L2U planning tests: passed
- L2T preflight tests: passed
- FotMobRawDetailFetcher tests: passed
- RawMatchDataVersionSelector tests: passed
- Makefile planning target: passed
- npm test: passed
- npm run test:coverage: passed, lines=89.60, functions=84.84, branches=80.00
- eslint / prettier / git diff: passed
- DB row counts unchanged: confirmed by planning script and final SELECT-only DB check
- l1-config residue absent: confirmed
- docs/\_staging_preview absent: confirmed
- PR CI: pending
- main push CI: pending

## 10. Recommended next phase

Phase 5.21L2V1: controlled matches identity seed execution.

Requirements: explicit final DB-write authorization, only write matches table, no raw_match_data write, no FotMob/network access, no parser/features/training, use manifest identity fields, controlled transaction, verify matches 10 -> 60, raw_match_data remains 18, then retry L2V raw write only after separate renewed authorization.

## 11. Explicit non-execution

- no DB writes
- no matches writes
- no raw_match_data writes
- no bookmaker_odds_history writes
- no network / FotMob access
- no match detail pageProps fetch
- no controlled raw write
- no schema migration
- no parser implementation
- no feature extraction
- no l3_features write
- no match_features_training write
- no training/prediction
- no browser/proxy/captcha bypass
- no full raw_data/pageProps/source body print/save
- no file deletion
- no invented external_id / fake target data
