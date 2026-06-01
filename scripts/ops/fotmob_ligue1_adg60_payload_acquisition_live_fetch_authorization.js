#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 live fetch authorization is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-AUTHORIZATION';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_authorization.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_AUTHORIZATION.md';

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md',
    'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_PLAN.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_AUTHORIZATION_GATE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_authorization_gate.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_DRY_RUN_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const TARGET_SCOPE = [
    'exactly 32 ADG59B accepted Ligue 1 targets',
    'no scope expansion',
    'no target discovery',
    'no extra leagues',
    'no extra seasons',
    'no extra matches',
    'no opportunistic collection',
];

const FETCH_METHOD_POLICY = {
    preferred: 'minimal direct detail endpoint / pageProps route if already source-controlled and stable; use corrected_route_hash_pair from ADG59B source-controlled artifacts',
    acceptable_only_if_explicitly_authorized: 'browser-backed capture (Playwright/Puppeteer/Chromium); requires separate authorization because of higher anti-bot risk',
    not_preferred: 'legacy API route guessing (FotMob legacy API endpoints returned 404; not reliable)',
    forbidden_without_separate_approval: [
        'uncontrolled crawler',
        'broad discovery',
        'recursive fetch',
        'full-site crawl',
    ],
};

const BATCH_POLICY = {
    initial_batch_size: 1,
    max_batch_size_before_review: 3,
    require_manual_review_after_first_successful_target: true,
    require_manual_review_after_any_mismatch: true,
    no_automatic_32_target_full_run_in_first_execution_pr: true,
    batch_size_increase_requires_separate_authorization_pr: true,
};

const RATE_LIMIT_POLICY = {
    minimum_delay_between_requests_seconds: { min: 20, max: 60 },
    randomized_human_like_delay_allowed: 'only_if_explicitly_authorized',
    stop_on_429: true,
    stop_on_403: true,
    stop_on_captcha: true,
    stop_on_anti_bot: true,
    stop_on_redirect_anomaly: true,
    no_retry_storm: true,
    no_parallel_fetch_in_first_execution_pr: true,
    max_requests_per_run_must_be_explicitly_declared: true,
};

const PAYLOAD_PERSISTENCE_POLICY = {
    payload_persistence_must_be_separately_authorized: true,
    full_raw_payload_not_committed_to_git: true,
    html_next_data_pageprops_source_body_not_committed_to_git: true,
    source_controlled_manifest_may_store_only: [
        'metadata',
        'hash',
        'size',
        'timestamp',
        'target_identity',
        'status',
    ],
    raw_payload_storage_path_must_be_gitignored: true,
    verify_gitignore_before_any_payload_persistence: true,
    cleanup_policy_required: true,
    payload_minimization_policy_required: true,
    stable_hash_policy_required: true,
    payload_saved_in_this_pr: false,
};

const DB_RAW_WRITE_POLICY = {
    db_write_prohibited: true,
    raw_write_prohibited: true,
    raw_match_data_insert_prohibited: true,
    schema_migration_prohibited: true,
    adg60_write_blocked: true,
    raw_write_ready_count_remains_0: true,
    future_payload_capture_success_does_not_imply_raw_write_ready: true,
    raw_write_ready_reconsideration_requires: [
        'source_controlled_metadata_hash_validation',
        'separate_write_authorization',
    ],
};

const STOP_CONDITIONS = [
    'target identity mismatch',
    'home/away orientation mismatch',
    'expected date mismatch',
    'competition mismatch',
    'missing corrected_hash_id',
    'missing route hash',
    'duplicate raw_match_data row already exists',
    'output directory not clean',
    'payload would be saved to git-tracked path',
    'full HTML would be saved',
    'full pageProps would be saved',
    'DB write attempted',
    'raw_match_data insert attempted',
    'unexpected network route',
    'unexpected redirect',
    '403 / 429 / captcha / anti-bot / blocked response',
    'unexpected schema / payload structure',
    'payload too large (> 5 MB per target)',
    'more targets than authorized batch',
    'any automatic retry loop',
];

const FUTURE_EXECUTION_PREREQUISITES = [
    'This authorization gate is merged and unmodified',
    'Authorization contract flags are re-checked',
    'Target scope is still exactly 32 ADG59B accepted Ligue 1 targets',
    'Batch size and rate-limit are explicitly declared in the execution PR',
    'Output directory is clean and gitignored',
    'Stop conditions are wired into the execution script',
    'No DB write, raw write, or raw_match_data insert code paths are reachable',
    'Execution PR explicitly references this authorization gate',
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

function validateInputs({ preflight, inventory, plan, gate, dryRun, adg59b, currentState }) {
    const checks = [
        ['preflight_target_count', preflight.target_count === 32],
        ['preflight_raw_write_ready_count', preflight.raw_write_ready_count === 0],
        ['blocked_missing_payload', preflight.aggregate_counts?.blocked_missing_payload === 32],
        [
            'blocked_requires_explicit_write_authorization',
            preflight.aggregate_counts?.blocked_requires_explicit_write_authorization === 32,
        ],
        ['inventory_phase', inventory.phase === 'ADG60-RAW-PAYLOAD-SOURCE-INVENTORY'],
        ['plan_phase', plan.phase === 'ADG60-PAYLOAD-ACQUISITION-PLAN'],
        ['gate_phase', gate.phase === 'ADG60-PAYLOAD-ACQUISITION-AUTHORIZATION-GATE'],
        ['dry_run_phase', dryRun.phase === 'ADG60-PAYLOAD-ACQUISITION-DRY-RUN-NO-WRITE'],
        ['dry_run_target_count', dryRun.target_count === 32],
        ['dry_run_matrix_count', dryRun.dry_run_matrix.length === 32],
        ['dry_run_command_preview_only', dryRun.command_preview.command_preview_only === true],
        ['dry_run_command_not_executed', dryRun.command_preview.executed === false],
        ['dry_run_live_fetch_not_performed', dryRun.live_fetch_performed === false],
        ['dry_run_network_fetch_not_performed', dryRun.network_fetch_performed === false],
        ['dry_run_payload_not_saved', dryRun.payload_saved === false],
        ['dry_run_acquisition_not_executed', dryRun.acquisition_execution_performed === false],
        ['dry_run_db_not_written', dryRun.db_write_performed === false],
        ['dry_run_raw_not_written', dryRun.raw_write_performed === false],
        ['dry_run_raw_match_data_not_inserted', dryRun.raw_match_data_insert_performed === false],
        ['dry_run_adg60_write_not_performed', dryRun.adg60_write_performed === false],
        ['dry_run_next_phase_is_this', dryRun.recommended_next_phase === PHASE],
        ['adg59b_target_count', adg59b.target_count === 32],
        ['adg59b_accepted_count', adg59b.accepted_count === 32],
        ['adg59b_suspension_resolved_count', adg59b.suspension_resolved_count === 32],
        ['current_state_adg60_blocked', currentState.includes('ADG60 remains blocked without separate explicit authorization')],
        ['current_state_raw_write_ready_0', currentState.includes('raw_write_ready_count: 0')],
    ];
    const failures = checks.filter(([, passed]) => !passed).map(([name]) => name);
    if (failures.length > 0) {
        throw new Error(`Input validation failed: ${failures.join(', ')}`);
    }
}

function buildLiveFetchAuthorization({ generatedAt = new Date().toISOString() } = {}) {
    const preflight = readJson('docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json');
    const inventory = readJson('docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json');
    const plan = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json');
    const gate = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_authorization_gate.json');
    const dryRun = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json');
    const adg59b = readJson('docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json');
    const currentState = readText('docs/data/FOTMOB_CURRENT_STATE.md');

    validateInputs({ preflight, inventory, plan, gate, dryRun, adg59b, currentState });

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
        schema_version: 'adg60_payload_acquisition_live_fetch_authorization_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        target_count: dryRun.target_count,
        accepted_count: adg59b.accepted_count,
        suspension_resolved_count: adg59b.suspension_resolved_count,
        raw_write_ready_count: 0,
        current_blockers: {
            blocked_missing_payload: dryRun.current_blockers.blocked_missing_payload,
            blocked_requires_explicit_write_authorization: dryRun.current_blockers.blocked_requires_explicit_write_authorization,
            raw_write_ready_count: 0,
            decision: 'blocked',
        },
        dry_run_matrix_count: dryRun.dry_run_matrix.length,
        command_preview_only: true,
        command_executed: false,
        authorization_contract: {
            authorization_stage_requested: true,
            live_fetch_may_be_requested_in_next_phase: true,
            network_fetch_may_be_requested_in_next_phase: true,
            browser_automation_may_be_requested_in_next_phase: false,
            current_pr_live_fetch_performed: false,
            current_pr_network_fetch_performed: false,
            current_pr_browser_automation_performed: false,
        },
        target_scope: TARGET_SCOPE,
        fetch_method_policy: FETCH_METHOD_POLICY,
        batch_policy: BATCH_POLICY,
        rate_limit_policy: RATE_LIMIT_POLICY,
        payload_persistence_policy: PAYLOAD_PERSISTENCE_POLICY,
        db_raw_write_policy: DB_RAW_WRITE_POLICY,
        stop_conditions: STOP_CONDITIONS,
        future_execution_prerequisites: FUTURE_EXECUTION_PREREQUISITES,
        safety,
        ...safety,
        recommended_next_phase: NEXT_PHASE,
        next_phase_boundary:
            'Next phase must execute live fetch for at most 1 target. DB write, raw write, and raw_match_data insert remain prohibited. If payload persistence is separately authorized, store only to gitignored external raw storage and commit only metadata/hash/status manifest. If payload persistence is NOT authorized, request/response metadata dry-run only (no body save).',
    };
}

function formatReport(auth) {
    const lines = [
        '<!-- markdownlint-disable MD013 -->',
        '',
        '# FotMob Ligue 1 ADG60 Payload Acquisition Live Fetch Authorization',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${auth.phase}`,
        '- scope: live-fetch authorization boundary only',
        '- based_on: ADG60 preflight no-write; ADG60 raw payload source inventory; ADG60 payload acquisition plan; ADG60 authorization gate; ADG60 dry-run no-write',
        `- target_count: ${auth.target_count}`,
        `- current blockers: blocked_missing_payload=${auth.current_blockers.blocked_missing_payload}; blocked_requires_explicit_write_authorization=${auth.current_blockers.blocked_requires_explicit_write_authorization}`,
        `- raw_write_ready_count: ${auth.raw_write_ready_count}`,
        `- dry-run matrix count: ${auth.dry_run_matrix_count}`,
        '- command_preview_only: true',
        '- command_executed: false',
        '- no live fetch in this PR',
        '- no network fetch in this PR',
        '- no browser automation in this PR',
        '- no payload save in this PR',
        '- no acquisition execution in this PR',
        '- no DB write',
        '- no raw write',
        '- no raw_match_data insert',
        '- no schema migration',
        '- no ADG60 write',
        '',
        'This PR defines a live/network fetch authorization boundary for ADG60 payload acquisition. It does not execute any fetch, save any payload, or write any data.',
        '',
        '## Authorization Contract',
        '',
        '### 1. Target Scope',
        '',
        ...auth.target_scope.map(item => `- ${item}`),
        '',
        '### 2. Live/Network Fetch Authorization Boundary',
        '',
        'This PR defines the authorization boundary only. Execution is deferred to future phases.',
        '',
        '| Authorization Flag | Value |',
        '| --- | --- |',
        `| authorization_stage_requested | ${auth.authorization_contract.authorization_stage_requested} |`,
        `| live_fetch_may_be_requested_in_next_phase | ${auth.authorization_contract.live_fetch_may_be_requested_in_next_phase} |`,
        `| network_fetch_may_be_requested_in_next_phase | ${auth.authorization_contract.network_fetch_may_be_requested_in_next_phase} |`,
        `| browser_automation_may_be_requested_in_next_phase | ${auth.authorization_contract.browser_automation_may_be_requested_in_next_phase} |`,
        `| current_pr_live_fetch_performed | ${auth.authorization_contract.current_pr_live_fetch_performed} |`,
        `| current_pr_network_fetch_performed | ${auth.authorization_contract.current_pr_network_fetch_performed} |`,
        `| current_pr_browser_automation_performed | ${auth.authorization_contract.current_pr_browser_automation_performed} |`,
        '',
        '- Browser automation is not recommended for the initial execution phase. Minimal direct detail endpoint access is preferred.',
        '- Any future live/network fetch execution must re-check this authorization gate before proceeding.',
        '',
        '### 3. Fetch Method Policy',
        '',
        'Recommended priority for future execution phases:',
        '',
        `- **Preferred**: ${auth.fetch_method_policy.preferred}`,
        `- **Acceptable only if explicitly authorized**: ${auth.fetch_method_policy.acceptable_only_if_explicitly_authorized}`,
        `- **Not preferred**: ${auth.fetch_method_policy.not_preferred}`,
        `- **Forbidden without separate approval**: ${auth.fetch_method_policy.forbidden_without_separate_approval.join('; ')}`,
        '',
        '### 4. Batch Policy',
        '',
        'Future live fetch execution must follow this policy:',
        '',
        `- initial batch size: ${auth.batch_policy.initial_batch_size} target only`,
        `- max batch size before manual review: ${auth.batch_policy.max_batch_size_before_review} targets`,
        '- require manual review after first successful target',
        '- require manual review after any mismatch',
        '- no automatic 32-target full run in first execution PR',
        '- batch size increase requires separate authorization PR',
        '',
        '### 5. Rate-Limit / Delay Policy',
        '',
        'Future execution must apply:',
        '',
        `- minimum delay between requests: ${auth.rate_limit_policy.minimum_delay_between_requests_seconds.min}-${auth.rate_limit_policy.minimum_delay_between_requests_seconds.max} seconds`,
        `- randomized human-like delay allowed: ${auth.rate_limit_policy.randomized_human_like_delay_allowed}`,
        '- stop on 429 / 403 / captcha / anti-bot / redirect anomaly',
        '- no retry storm',
        '- no parallel fetch in first execution PR',
        '- max requests per run must be explicitly declared before execution',
        '',
        '### 6. Payload Persistence Policy',
        '',
        'This PR does not save any payload.',
        '',
        'Future payload persistence, if separately authorized, must satisfy:',
        '',
        '- payload persistence must be separately authorized',
        '- full raw payload must not be committed to git',
        '- HTML / `__NEXT_DATA__` / pageProps / source body must not be committed to git',
        `- source-controlled manifests may store only: ${auth.payload_persistence_policy.source_controlled_manifest_may_store_only.join(', ')}`,
        '- raw payload storage path must be gitignored (`data/raw_external/`)',
        '- verify `.gitignore` coverage before any payload persistence',
        '- cleanup policy required before any local file output',
        '- payload minimization policy required before any acquisition',
        '- stable hash policy required before any acquisition',
        '',
        '### 7. DB / Raw Write Policy',
        '',
        'DB and raw write operations remain strictly prohibited:',
        '',
        '- DB write remains prohibited',
        '- raw write remains prohibited',
        '- raw_match_data insert remains prohibited',
        '- schema migration remains prohibited',
        '- ADG60 write remains blocked',
        '- raw_write_ready_count remains 0',
        '- future payload capture success does not imply raw_write_ready=true',
        '- raw_write_ready can only be reconsidered after source-controlled metadata/hash validation AND separate write authorization',
        '',
        '### 8. Stop Conditions',
        '',
        'Future live fetch execution must immediately stop on:',
        '',
        ...auth.stop_conditions.map(item => `- ${item}`),
        '',
        '## Future Execution Prerequisites',
        '',
        'Before any future live fetch execution PR, these must be confirmed:',
        '',
        ...auth.future_execution_prerequisites.map((item, idx) => `${idx + 1}. ${item}`),
        '',
        '## Safety',
        '',
        `- live_fetch_performed: ${auth.live_fetch_performed}`,
        `- network_fetch_performed: ${auth.network_fetch_performed}`,
        `- browser_automation_performed: ${auth.browser_automation_performed}`,
        `- payload_saved: ${auth.payload_saved}`,
        `- acquisition_execution_performed: ${auth.acquisition_execution_performed}`,
        `- db_write_performed: ${auth.db_write_performed}`,
        `- raw_write_performed: ${auth.raw_write_performed}`,
        `- raw_match_data_insert_performed: ${auth.raw_match_data_insert_performed}`,
        `- schema_migration_performed: ${auth.schema_migration_performed}`,
        `- adg60_write_performed: ${auth.adg60_write_performed}`,
        '',
        '## Recommended Next Phase',
        '',
        `- recommended next phase: ${auth.recommended_next_phase}`,
        '- next phase must execute live fetch for at most 1 target',
        '- next phase must still not DB write / raw_match_data insert',
        '- if payload persistence is separately authorized, store only to gitignored external raw storage and commit only metadata/hash/status manifest',
        '- if payload persistence is NOT authorized, perform request/response metadata dry-run only (no body save)',
    ];
    return `${lines.join('\n')}\n`;
}

function main() {
    const auth = buildLiveFetchAuthorization();
    writeJson(OUT_MANIFEST, auth);
    writeText(OUT_REPORT, formatReport(auth));
    console.log(
        JSON.stringify(
            {
                phase: auth.phase,
                target_count: auth.target_count,
                current_blockers: auth.current_blockers,
                live_fetch_performed: auth.live_fetch_performed,
                network_fetch_performed: auth.network_fetch_performed,
                browser_automation_performed: auth.browser_automation_performed,
                payload_saved: auth.payload_saved,
                acquisition_execution_performed: auth.acquisition_execution_performed,
                db_write_performed: auth.db_write_performed,
                raw_write_performed: auth.raw_write_performed,
                raw_match_data_insert_performed: auth.raw_match_data_insert_performed,
                adg60_write_performed: auth.adg60_write_performed,
                recommended_next_phase: auth.recommended_next_phase,
            },
            null,
            2
        )
    );
}

if (require.main === module) {
    main();
}

module.exports = {
    NEXT_PHASE,
    buildLiveFetchAuthorization,
    formatReport,
};
