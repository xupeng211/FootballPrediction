# Football-Data Small DB Write Approval Form Template

> TEMPLATE ONLY / NOT APPROVED.
>
> This form is a machine-readable template for a future real small DB write
> approval. It does not authorize any write in Phase 4.68C.

```yaml
phase: PHASE4_REAL_SMALL_DB_WRITE_APPROVAL
approval_status: not_approved
operator:
reviewer:
source_manifest:
local_csv:
source_name:
source_url:
license_url:
terms_url:
human_approval_note:
max_insert_rows:
target_tables:
    - matches
allow_odds_insert: false
allow_raw_insert: false
allow_l3_insert: false
allow_training_features_insert: false
allow_predictions_insert: false
allow_training: false
allow_prediction: false
require_pg_dump: true
pg_dump_command_preview:
backup_path:
approved_candidate_match_ids: []
excluded_candidate_match_ids: []
manual_review_candidate_match_ids: []
expected_before_counts:
    matches:
    bookmaker_odds_history:
    raw_match_data:
    l3_features:
    match_features_training:
    predictions:
expected_after_counts:
    matches:
    bookmaker_odds_history:
    raw_match_data:
    l3_features:
    match_features_training:
    predictions:
rollback_plan_reviewed: false
post_write_validation_required: true
final_human_confirmation: false
```

## Notes

- `approval_status` defaults to `not_approved`.
- All actual write permissions default to disabled.
- Only a future real DB write phase may change `approval_status` to `approved_for_db_write`.
- This form must not be used to execute a DB write in Phase 4.68C.
- This file is a template, not an approval record.
- Codex must not set `final_human_confirmation` to `true`.
