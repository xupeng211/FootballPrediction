#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG59B source-controlled state artifact is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG59B-SOURCE-CONTROLLED-STATE';
const A59A = 'docs/_manifests/fotmob_ligue1_adg59a_source_controlled_canonical_identity_promotion.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG59B_SOURCE_CONTROLLED_ACCEPTANCE_SUSPENSION_STATE.md';
const AUTHORIZATION =
    '我授权执行 ADG59B acceptance/suspension state mutation for exactly the 32 ADG59A Ligue 1 targets, source-controlled state only, no DB write, no raw write, no raw_match_data insert, no live fetch, no network, no detail page fetch, no full payload save, no schema migration, no ADG60.';

function rj(p) {
    return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8'));
}

function wj(p, v) {
    fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8');
}

function wt(p, v) {
    fs.writeFileSync(path.join(PP, p), v, 'utf8');
}

function countWhere(records, predicate) {
    return records.filter(predicate).length;
}

function duplicateCount(records, field) {
    const seen = new Set();
    let duplicates = 0;
    for (const record of records) {
        const value = record[field];
        if (seen.has(value)) duplicates += 1;
        seen.add(value);
    }
    return duplicates;
}

function failedChecks(checks) {
    return checks.filter(check => check.failed).map(check => check.message);
}

function validateAdg59aSummary(adg59a, promoted) {
    return failedChecks([
        {
            failed: adg59a.adg59a_status !== 'source_controlled_canonical_identity_promotion_completed',
            message: 'ADG59A status is not completed',
        },
        {
            failed: adg59a.promoted_records_count !== 32 || adg59a.total_targets !== 32 || promoted.length !== 32,
            message: 'ADG59A target count must be 32',
        },
        {
            failed: adg59a.duplicate_conflict !== 0 || duplicateCount(promoted, 'target_match_id') !== 0,
            message: 'ADG59A target duplicate conflict must be 0',
        },
        {
            failed: duplicateCount(promoted, 'corrected_route_hash_pair') !== 0,
            message: 'ADG59A corrected route hash pairs must be unique',
        },
        {
            failed: adg59a.raw_write_ready_count !== 0,
            message: 'ADG59A raw_write_ready_count must be 0',
        },
        ...['db_write_performed', 'raw_write_performed', 'raw_match_data_insert_performed'].map(flag => ({
            failed: adg59a[flag] !== false,
            message: `ADG59A ${flag} must be false`,
        })),
    ]);
}

function validateAdg59aTarget(target) {
    return failedChecks([
        { failed: target.orientation_status !== 'confirmed', message: `${target.target_match_id}: orientation not confirmed` },
        { failed: target.date_status !== 'confirmed', message: `${target.target_match_id}: date not confirmed` },
        { failed: target.competition_status !== 'confirmed', message: `${target.target_match_id}: competition not confirmed` },
        {
            failed: target.re_acceptance_performed !== false,
            message: `${target.target_match_id}: re_acceptance before-state drift`,
        },
        {
            failed: target.suspension_reversal_performed !== false,
            message: `${target.target_match_id}: suspension before-state drift`,
        },
        { failed: target.raw_write_ready !== false, message: `${target.target_match_id}: raw_write_ready before-state drift` },
    ]);
}

function validateAdg59a(adg59a) {
    const promoted = adg59a.promoted_canonical_identities || [];
    return [
        ...validateAdg59aSummary(adg59a, promoted),
        ...promoted.flatMap(target => validateAdg59aTarget(target)),
    ];
}

function buildStateTarget(target) {
    return {
        target_match_id: target.target_match_id,
        competition: target.competition,
        season: target.season,
        expected_home: target.expected_home,
        expected_away: target.expected_away,
        expected_date: target.expected_date,
        corrected_route_hash_pair: target.corrected_route_hash_pair,
        corrected_hash_id: target.corrected_hash_id,
        source_phase: 'ADG59B',
        input_source_phase: target.source_phase,
        orientation_status: target.orientation_status,
        date_status: target.date_status,
        competition_status: target.competition_status,
        duplicate_status: target.duplicate_status,
        before: {
            re_acceptance_performed: target.re_acceptance_performed,
            suspension_reversal_performed: target.suspension_reversal_performed,
            raw_write_ready: target.raw_write_ready,
        },
        after: {
            accepted: true,
            suspension_resolved: true,
            raw_write_ready: false,
        },
        acceptance_state: 'accepted_source_controlled_only',
        suspension_state: 'resolved_source_controlled_only',
        accepted: true,
        suspension_resolved: true,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_ready: false,
    };
}

function build(input = {}) {
    const adg59a = input.adg59a || rj(A59A);
    const validationErrors = validateAdg59a(adg59a);
    if (validationErrors.length > 0) {
        throw new Error(`Cannot build ADG59B artifact: ${validationErrors.join('; ')}`);
    }

    const stateTargets = adg59a.promoted_canonical_identities.map(buildStateTarget);
    const duplicateConflict = duplicateCount(stateTargets, 'target_match_id') + duplicateCount(stateTargets, 'corrected_route_hash_pair');
    const artifact = {
        schema_version: 'adg59b_source_controlled_state_v1',
        lifecycle: 'source-controlled-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [A59A, CS],
        explicit_user_authorization: AUTHORIZATION,
        safety: {
            live_fetch_performed: false,
            network_request_performed: false,
            detail_page_fetch_performed: false,
            db_write_performed: false,
            update_insert_delete_performed: false,
            matches_table_modified: false,
            pipeline_status_modified: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            html_saved: false,
            full_payload_saved: false,
            next_data_saved: false,
            pageprops_saved: false,
            schema_migration_performed: false,
            acceptance_db_mutation_performed: false,
            suspension_db_mutation_performed: false,
            adg60_performed: false,
        },
        adg59b_status: 'source_controlled_acceptance_suspension_state_completed',
        mutation_scope: 'source_controlled_artifact_only',
        target_count: stateTargets.length,
        accepted_count: countWhere(stateTargets, target => target.accepted === true),
        suspension_resolved_count: countWhere(stateTargets, target => target.suspension_resolved === true),
        duplicate_conflict: duplicateConflict,
        orientation_pass: countWhere(stateTargets, target => target.orientation_status === 'confirmed'),
        date_pass: countWhere(stateTargets, target => target.date_status === 'confirmed'),
        competition_pass: countWhere(stateTargets, target => target.competition_status === 'confirmed'),
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_ready_count: countWhere(stateTargets, target => target.raw_write_ready === true),
        expected_db_invariant_baseline: {
            matches: 60,
            raw_match_data: 18,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
            bookmaker_odds_history: 2,
        },
        recommended_next_step:
            'ADG59B source-controlled state is complete. Do not enter ADG60 without separate explicit authorization.',
        state_targets: stateTargets,
    };
    return artifact;
}

function writeReport(data) {
    const lines = [
        '# ADG59B Source-Controlled Acceptance/Suspension State',
        '',
        `- Phase: ${PH}`,
        `- status: ${data.adg59b_status}`,
        '- lifecycle: source-controlled-artifact',
        `- mutation_scope: ${data.mutation_scope}`,
        `- target_count: ${data.target_count}`,
        `- accepted_count: ${data.accepted_count}`,
        `- suspension_resolved_count: ${data.suspension_resolved_count}`,
        `- duplicate_conflict: ${data.duplicate_conflict}`,
        `- orientation: ${data.orientation_pass}/32`,
        `- date: ${data.date_pass}/32`,
        `- competition: ${data.competition_pass}/32`,
        `- raw_write_ready_count: ${data.raw_write_ready_count}`,
        `- db_write: ${data.db_write_performed}`,
        `- raw_write: ${data.raw_write_performed}`,
        `- raw_match_data_insert: ${data.raw_match_data_insert_performed}`,
        '',
        '## State Change',
        '- before: re_acceptance_performed=false, suspension_reversal_performed=false',
        '- after: accepted=true, suspension_resolved=true',
        '- scope: artifact-level only; no DB acceptance or suspension mutation',
        '',
        '## Safety',
        '- no live fetch / network / detail fetch',
        '- no DB write / UPDATE / INSERT / DELETE',
        '- no matches or pipeline_status mutation',
        '- no raw write / raw_match_data insert',
        '- no HTML / full payload / NEXT_DATA / pageProps save',
        '- no schema migration / ADG60',
        '',
        '## Next',
        data.recommended_next_step,
    ];
    wt(RPT, `${lines.join('\n')}\n`);
}

if (require.main === module) {
    const data = build();
    wj(OUT, data);
    writeReport(data);
    console.log(
        JSON.stringify(
            {
                status: data.adg59b_status,
                target_count: data.target_count,
                accepted_count: data.accepted_count,
                suspension_resolved_count: data.suspension_resolved_count,
                duplicate_conflict: data.duplicate_conflict,
                raw_write_ready_count: data.raw_write_ready_count,
            },
            null,
            2
        )
    );
}

module.exports = { build, validateAdg59a };
