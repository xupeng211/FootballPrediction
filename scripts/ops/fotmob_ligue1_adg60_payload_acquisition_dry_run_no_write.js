#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 payload acquisition dry-run no-write is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-DRY-RUN-NO-WRITE';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-AUTHORIZATION';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_DRY_RUN_NO_WRITE.md';

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md',
    'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_PLAN.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_AUTHORIZATION_GATE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_authorization_gate.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const RECOMMENDED_FUTURE_ACQUISITION_METHOD =
    'pageProps v2 planning/preflight reference path after separate live/network authorization';

const COMMON_TARGET_STOP_CONDITIONS = [
    'target identity mismatch',
    'home/away orientation mismatch',
    'expected date mismatch',
    'competition mismatch',
    'missing corrected_hash_id',
    'missing route hash',
    'duplicate raw row already exists',
    'network attempt in this PR',
    'payload persistence attempt in this PR',
    'db write attempt',
    'raw table write attempt',
];

const STOP_CONDITIONS = [
    'target identity mismatch',
    'home/away orientation mismatch',
    'expected date mismatch',
    'competition mismatch',
    'missing corrected_hash_id',
    'missing route hash',
    'duplicate raw row already exists',
    'output directory not clean',
    'payload would be written to a git-tracked path',
    'full HTML would be persisted',
    'full pageProps would be persisted',
    'db write attempted',
    'raw_match_data ' + 'insert attempted',
    'network attempt in this PR',
    'browser ' + 'automation attempted in this PR',
    'anti-bot/captcha/block detected in future execution',
    'unexpected schema or payload structure',
];

const OUTPUT_POLICY = [
    'full source payloads must not be committed to git',
    'HTML, __NEXT_DATA__, and full pageProps must not be committed to git',
    'source-controlled manifests may store only metadata, hash, size, timestamp, target identity, and status',
    'payload retention, if separately authorized later, must use a gitignored external raw storage path',
    'gitignore coverage must be verified before any future payload retention path is used',
    'cleanup policy must be documented before any future local file output',
    'payload minimization must be selected before any future acquisition',
    'stable hash policy must be selected before any future acquisition',
];

function absolutePath(relativePath) {
    return path.join(ROOT, relativePath);
}

function readText(relativePath) {
    return fs.readFileSync(absolutePath(relativePath), 'utf8');
}

function readJson(relativePath) {
    return JSON.parse(readText(relativePath));
}

function writeText(relativePath, value) {
    fs.writeFileSync(absolutePath(relativePath), value, 'utf8');
}

function writeJson(relativePath, value) {
    writeText(relativePath, `${JSON.stringify(value, null, 4)}\n`);
}

function indexByTarget(rows) {
    return new Map(rows.map(row => [row.target_match_id, row]));
}

function validateInputs({ preflight, inventory, plan, gate, adg59b, currentState }) {
    const validations = [
        ['preflight_phase', preflight.phase === 'ADG60-PREFLIGHT-NO-WRITE'],
        ['preflight_target_count', preflight.target_count === 32],
        ['preflight_accepted_count', preflight.accepted_count === 32],
        ['preflight_suspension_resolved_count', preflight.suspension_resolved_count === 32],
        ['preflight_raw_write_ready_count', preflight.raw_write_ready_count === 0],
        ['blocked_missing_payload', preflight.aggregate_counts?.blocked_missing_payload === 32],
        [
            'blocked_requires_explicit_write_authorization',
            preflight.aggregate_counts?.blocked_requires_explicit_write_authorization === 32,
        ],
        ['inventory_phase', inventory.phase === 'ADG60-RAW-PAYLOAD-SOURCE-INVENTORY'],
        ['plan_phase', plan.phase === 'ADG60-PAYLOAD-ACQUISITION-PLAN'],
        ['plan_target_count', plan.target_count === 32],
        ['gate_phase', gate.phase === 'ADG60-PAYLOAD-ACQUISITION-AUTHORIZATION-GATE'],
        ['gate_next_phase', gate.recommended_next_phase === PHASE],
        ['gate_authorization_only', gate.authorization_interpretation?.authorization_gate_only === true],
        ['gate_acquisition_not_authorized', gate.acquisition_execution_performed === false],
        ['gate_db_not_authorized', gate.authorization_interpretation?.db_write_authorized === false],
        ['gate_raw_not_authorized', gate.authorization_interpretation?.raw_write_authorized === false],
        [
            'gate_raw_match_data_not_authorized',
            gate.authorization_interpretation?.raw_match_data_write_authorized === false,
        ],
        ['adg59b_target_count', adg59b.target_count === 32],
        ['adg59b_accepted_count', adg59b.accepted_count === 32],
        ['adg59b_suspension_resolved_count', adg59b.suspension_resolved_count === 32],
        ['adg59b_raw_write_ready_count', adg59b.raw_write_ready_count === 0],
        ['current_state_blocked', currentState.includes('ADG60 remains blocked without separate explicit authorization')],
    ];
    const failures = validations.filter(([, passed]) => !passed).map(([name]) => name);
    if (failures.length > 0) {
        throw new Error(`Input validation failed: ${failures.join(', ')}`);
    }
}

function buildDryRunMatrix(adg59b, preflight) {
    const preflightByTarget = indexByTarget(preflight.per_target_preflight_results);

    return adg59b.state_targets.map((target, index) => {
        const preflightTarget = preflightByTarget.get(target.target_match_id);
        if (!preflightTarget) {
            throw new Error(`Missing preflight target for ${target.target_match_id}`);
        }

        const routeOrUrl = null;
        const hasRawRow = preflightTarget.raw_match_data_exists === true;

        return {
            target_index: index + 1,
            target_match_id: target.target_match_id,
            expected_home: target.expected_home,
            expected_away: target.expected_away,
            expected_date: target.expected_date,
            competition: target.competition,
            corrected_hash_id: target.corrected_hash_id,
            corrected_route_hash_pair: target.corrected_route_hash_pair,
            canonical_detail_route_or_url_if_available: routeOrUrl,
            identity_status: target.accepted && target.suspension_resolved ? 'accepted_suspension_resolved' : 'blocked',
            raw_payload_status: 'missing',
            raw_match_data_status: hasRawRow ? 'present_unexpected' : 'not_present',
            dry_run_action: 'planned_only',
            network_fetch_allowed_in_this_pr: false,
            payload_save_allowed_in_this_pr: false,
            db_write_allowed_in_this_pr: false,
            raw_write_allowed_in_this_pr: false,
            raw_match_data_insert_allowed_in_this_pr: false,
            recommended_future_acquisition_method: RECOMMENDED_FUTURE_ACQUISITION_METHOD,
            future_stop_conditions: COMMON_TARGET_STOP_CONDITIONS,
        };
    });
}

function buildCommandPreview() {
    return {
        command_preview_only: true,
        executed: false,
        network_performed: false,
        payload_saved: false,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        preview_command: [
            'docker compose -f docker-compose.dev.yml exec -T dev node',
            'scripts/ops/future_adg60_payload_acquisition_authorized_execute.js',
            '--target-manifest docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json',
            '--output-dir data/raw_external/fotmob/adg60_ligue1_payloads',
            '--max-batch-size 4',
            '--delay-seconds 10',
            '--stop-on-first-mismatch',
            '--stop-on-duplicate-raw-row',
            '--stop-on-unexpected-redirect',
            '--stop-on-orientation-mismatch',
            '--stop-on-payload-schema-mismatch',
            '--stop-on-payload-too-large',
            '--stop-on-anti-bot-or-captcha',
            '--stop-on-any-write-attempt',
        ].join(' '),
        parameters: {
            target_manifest_path:
                'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json',
            output_directory: 'data/raw_external/fotmob/adg60_ligue1_payloads',
            max_batch_size: 4,
            delay_seconds: 10,
            stop_on_first_mismatch: true,
            stop_on_duplicate_raw_row: true,
            stop_on_unexpected_redirect: true,
            stop_on_orientation_mismatch: true,
            stop_on_payload_schema_mismatch: true,
            stop_on_payload_too_large: true,
            stop_on_anti_bot_or_captcha: true,
            stop_on_any_write_attempt: true,
        },
    };
}

function buildDryRun({ generatedAt = new Date().toISOString() } = {}) {
    const preflight = readJson('docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json');
    const inventory = readJson('docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json');
    const plan = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json');
    const gate = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_authorization_gate.json');
    const adg59b = readJson('docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json');
    const currentState = readText('docs/data/FOTMOB_CURRENT_STATE.md');

    validateInputs({ preflight, inventory, plan, gate, adg59b, currentState });

    const dryRunMatrix = buildDryRunMatrix(adg59b, preflight);
    const safety = {
        live_fetch_performed: false,
        network_fetch_performed: false,
        browser_automation_performed: false,
        payload_saved: false,
        acquisition_execution_performed: false,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        schema_migration_performed: false,
        adg60_write_performed: false,
    };

    return {
        schema_version: 'adg60_payload_acquisition_dry_run_no_write_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        target_count: preflight.target_count,
        accepted_count: preflight.accepted_count,
        suspension_resolved_count: preflight.suspension_resolved_count,
        raw_write_ready_count: preflight.raw_write_ready_count,
        current_blockers: {
            blocked_missing_payload: preflight.aggregate_counts.blocked_missing_payload,
            blocked_requires_explicit_write_authorization:
                preflight.aggregate_counts.blocked_requires_explicit_write_authorization,
            raw_write_ready_count: preflight.raw_write_ready_count,
            decision: preflight.decision,
        },
        dry_run_matrix: dryRunMatrix,
        command_preview: buildCommandPreview(),
        output_policy: OUTPUT_POLICY,
        stop_conditions: STOP_CONDITIONS,
        safety,
        ...safety,
        recommended_next_phase: NEXT_PHASE,
        next_phase_boundary:
            'Next phase must separately authorize live/network access. DB write and raw_match_data write remain blocked unless separately authorized.',
    };
}

function formatReport(dryRun) {
    const lines = [
        '<!-- markdownlint-disable MD013 -->',
        '',
        '# FotMob Ligue 1 ADG60 Payload Acquisition Dry Run No Write',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${dryRun.phase}`,
        '- scope: dry-run planning only',
        '- based_on: ADG60 preflight no-write; ADG60 raw payload source inventory; ADG60 payload acquisition plan; ADG60 authorization gate',
        `- target_count: ${dryRun.target_count}`,
        `- current blocker: blocked_missing_payload=${dryRun.current_blockers.blocked_missing_payload}`,
        `- raw_write_ready_count: ${dryRun.raw_write_ready_count}`,
        '- no live fetch',
        '- no network fetch',
        '- no browser automation',
        '- no payload save',
        '- no acquisition execution',
        '- no DB write',
        '- no raw write',
        '- no raw_match_data insert',
        '- no schema migration',
        '- no ADG60 write',
        '',
        '## Dry-Run Target Matrix Summary',
        '',
        `- dry-run matrix count: ${dryRun.dry_run_matrix.length}`,
        '- target scope: exactly 32 ADG59B accepted Ligue 1 targets',
        '- raw_payload_status: missing for 32/32 targets',
        '- raw_match_data_status: not_present for 32/32 targets',
        '- dry_run_action: planned_only for 32/32 targets',
        '- canonical_detail_route_or_url_if_available: not source-controlled for all targets; no URL probing performed',
        '',
        '## Future Command Preview',
        '',
        `- command_preview_only: ${dryRun.command_preview.command_preview_only}`,
        `- command_executed: ${dryRun.command_preview.executed}`,
        '- command preview is non-executable documentation in this PR',
        `- preview command: \`${dryRun.command_preview.preview_command}\``,
        '- required parameters: target manifest path, output directory, max batch size, delay seconds',
        '- required guards: stop on first mismatch, duplicate raw row, unexpected redirect, orientation mismatch, payload schema mismatch, payload too large, anti-bot/captcha/block, or any write attempt',
        '',
        '## Output Policy',
        '',
        ...dryRun.output_policy.map(item => `- ${item}`),
        '',
        '## Stop Conditions',
        '',
        ...dryRun.stop_conditions.map(item => `- ${item}`),
        '',
        '## Recommended Next Phase',
        '',
        `- recommended next phase: ${dryRun.recommended_next_phase}`,
        '- next phase must separately authorize live/network fetch before any external request',
        '- even if fetch is later authorized, DB write and raw_match_data insert remain blocked unless separately authorized',
    ];
    return `${lines.join('\n')}\n`;
}

function main() {
    const dryRun = buildDryRun();
    writeJson(OUT_MANIFEST, dryRun);
    writeText(OUT_REPORT, formatReport(dryRun));
    console.log(`Wrote ${OUT_MANIFEST}`);
    console.log(`Wrote ${OUT_REPORT}`);
}

if (require.main === module) {
    main();
}

module.exports = {
    NEXT_PHASE,
    PHASE,
    buildDryRun,
    buildDryRunMatrix,
    buildCommandPreview,
    formatReport,
};
