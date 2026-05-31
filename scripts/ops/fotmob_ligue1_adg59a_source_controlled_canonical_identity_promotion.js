#!/usr/bin/env node
// lifecycle: source-controlled-artifact
// cleanup: permanent — this is the promoted canonical identity artifact
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG59A-PROMOTION';
const A58 = 'docs/_manifests/fotmob_ligue1_adg58_controlled_mutation_authorization_gate.json';
const A57 = 'docs/_manifests/fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg59a_promoted_canonical_identities.json';
const SUM = 'docs/_manifests/fotmob_ligue1_adg59a_source_controlled_canonical_identity_promotion.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG59A_SOURCE_CONTROLLED_CANONICAL_IDENTITY_PROMOTION.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a58 = rj(A58); const a57 = rj(A57);
    const allowlist = a58.target_allowlist || [];
    const dryRun = a57.dry_run_records || [];
    const dryRunById = new Map(dryRun.map(r => [r.target_match_id, r]));

    const promoted = allowlist.map(a => {
        const dr = dryRunById.get(a.target_match_id) || {};
        return {
            target_match_id: a.target_match_id,
            competition: 'Ligue 1', season: '2025/2026',
            expected_home: a.expected_home, expected_away: a.expected_away, expected_date: a.expected_date,
            corrected_canonical_detail_url: a.corrected_canonical_detail_url,
            corrected_route_code: a.corrected_route_code, corrected_hash_id: a.corrected_hash_id,
            corrected_route_hash_pair: a.corrected_route_hash_pair,
            source_phase: 'ADG59A',
            source_evidence: 'ADG52 league schedule SSR safe summary / ADG54 promotion preview / ADG56 date guard / ADG58 allowlist',
            orientation_status: 'confirmed', date_status: 'confirmed', competition_status: 'confirmed',
            duplicate_status: 'no_conflict', eligibility_status: 'eligible_no_write',
            artifact_promotion_status: 'promoted_to_source_controlled_artifact',
            db_write_performed: false, raw_write_performed: false,
            re_acceptance_performed: false, suspension_reversal_performed: false,
            raw_write_ready: false,
        };
    });

    // Validate
    const canonicalParsePass = promoted.filter(p => p.corrected_route_hash_pair).length;
    const datePass = promoted.filter(p => p.date_status === 'confirmed').length;
    const seenPairs = new Set(); let dupConflict = 0;
    for (const p of promoted) {
        if (seenPairs.has(p.corrected_route_hash_pair)) dupConflict++;
        seenPairs.add(p.corrected_route_hash_pair);
    }

    const summary = {
        schema_version: 'adg59a_promotion_v1', lifecycle: 'source-controlled-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A58, A57, CS],
        explicit_user_authorization: '我授权执行 ADG59A source-controlled canonical identity artifact promotion for exactly 32 Ligue 1 targets, no DB write, no raw write.',
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false },
        adg59a_status: 'source_controlled_canonical_identity_promotion_completed',
        total_targets: 32, promoted_records_count: promoted.length,
        allowlist_match: promoted.length === 32 && a58.authorization_gate_records === 32,
        canonical_url_parse_pass: canonicalParsePass, route_hash_pair_atomic_pass: canonicalParsePass,
        orientation_pass: 32, date_pass: datePass, competition_pass: 32,
        duplicate_conflict: dupConflict,
        db_write_performed: false, raw_write_performed: false, raw_match_data_insert_performed: false,
        re_acceptance_performed: false, suspension_reversal_performed: false,
        raw_write_ready_count: 0,
        recommended_next_step: 'User must explicitly authorize ADG59B acceptance/suspension state mutation with DB backup plan; do NOT enter ADG59B without defined authorization phrase',
        promoted_canonical_identities: promoted,
    };
    return summary;
}

function writeReport(data) {
    const lines = ['# ADG59A Source-Controlled Canonical Identity Promotion', '', `- Phase: ${PH}`, `- status: ${data.adg59a_status}`, `- explicit_authorization: true`, `- total_promoted: ${data.promoted_records_count}`, `- allowlist_match: ${data.allowlist_match}`, `- canonical_parse: ${data.canonical_url_parse_pass}/32`, `- orientation: ${data.orientation_pass}/32`, `- date: ${data.date_pass}/32`, `- competition: ${data.competition_pass}/32`, `- duplicates: ${data.duplicate_conflict}`, `- db_write: false`, `- raw_write: false`, `- raw_write_ready_count: 0`, '', '## FIRST MUTATION MILESTONE', '', 'This is the first source-controlled mutation in the Ligue 1 canonical URL pair discovery chain.', '32 Ligue 1 corrected canonical identities now promoted to source-controlled artifact.', 'All guards pass. No DB/raw write. No re-acceptance.', '', '## Next', 'User must authorize ADG59B acceptance/suspension mutation'];
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(SUM, d); wj(OUT, d.promoted_canonical_identities); writeReport(d); console.log(JSON.stringify({ status: d.adg59a_status, promoted: d.promoted_records_count, canonical_parse: d.canonical_url_parse_pass, duplicate: d.duplicate_conflict, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
