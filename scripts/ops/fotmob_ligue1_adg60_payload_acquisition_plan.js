#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 payload acquisition plan is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-PLAN';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-AUTHORIZATION-GATE';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_PLAN.md';

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md',
    'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const TARGET_FIELD_REQUIREMENTS = [
    'target_match_id',
    'corrected_hash_id',
    'corrected_route_hash_pair',
    'expected_home',
    'expected_away',
    'expected_date',
    'competition',
    'canonical_detail_route_or_url_if_available',
];

const REUSABLE_REFERENCE_PATHS = [
    {
        path: 'scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js',
        category: 'pageProps v2 planning',
        reuse: 'reusable_with_guardrails',
    },
    {
        path: 'scripts/ops/single_league_pageprops_v2_controlled_write_plan.js',
        category: 'pageProps v2 controlled-write planning reference',
        reuse: 'reference_only',
    },
    {
        path: 'scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js',
        category: 'raw payload acquisition preflight reference',
        reuse: 'reusable_with_guardrails',
    },
    {
        path: 'scripts/ops/l2_raw_match_data_ingest_plan.js',
        category: 'raw ingest planning reference',
        reuse: 'reusable_with_guardrails',
    },
    {
        path: 'scripts/ops/raw_match_data_completeness_fidelity_audit.js',
        category: 'completeness/source fidelity audit reference',
        reuse: 'reusable_with_guardrails',
    },
    {
        path: 'scripts/ops/fotmob_ligue1_canonical_detail_url_discovery_adg39.js',
        category: 'detail URL / route-hash reference',
        reuse: 'reusable_with_guardrails',
    },
    {
        path: 'scripts/ops/pageprops_v2_continued_detail_endpoint_investigation.js',
        category: 'detail endpoint investigation reference',
        reuse: 'reusable_with_guardrails',
    },
    {
        path: 'scripts/ops/pageprops_v2_detail_api_endpoint_feasibility.js',
        category: 'legacy API feasibility reference',
        reuse: 'reusable_with_guardrails',
    },
];

const FORBIDDEN_EXECUTION_PATHS = [
    {
        path: 'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js',
        reason: 'live recapture capable; reference-only until separate authorization',
    },
    {
        path: 'scripts/ops/pageprops_v2_no_write_preview.js',
        reason: 'live preview capable; do not run in this plan phase',
    },
    {
        path: 'scripts/ops/single_league_small_batch_pageprops_v2_preflight.js',
        reason: 'network/detail preflight capable; needs future authorization gate',
    },
    {
        path: 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js',
        reason: 'controlled raw write execution path; do not use',
    },
    {
        path: 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js',
        reason: 'raw write execution path; do not use',
    },
    {
        path: 'scripts/ops/l2_raw_match_data_write.js',
        reason: 'raw table write path; do not use',
    },
    {
        path: 'scripts/ops/l2_remaining_raw_match_data_write.js',
        reason: 'raw table write path; do not use',
    },
    {
        path: 'scripts/ops/backfill_historical_raw_match_data.js',
        reason: 'historical backfill write-capable path; do not use',
    },
    {
        path: 'scripts/ops/html_hydration_source_fidelity_live_compare.js',
        reason: 'live source compare path; not authorized here',
    },
    {
        path: 'scripts/ops/fotmob_ligue1_ssr_pageprops_bounded_probe_adg46.js',
        reason: 'SSR probe/live page path; not authorized here',
    },
    {
        path: 'scripts/ops/fotmob_ligue1_ssr_pageprops_discovery_gate_adg46.js',
        reason: 'SSR discovery/live page path; not authorized here',
    },
    {
        path: 'src/infrastructure/services/BrowserProvider.js',
        reason: 'browser-capable runtime service; not part of this plan execution',
    },
];

const AUTHORIZATION_CHECKLIST = [
    'exact 32 ADG59B accepted Ligue 1 target scope',
    'explicit live/network access permission',
    'explicit browser automation permission or prohibition',
    'explicit payload persistence permission or prohibition',
    'allowed storage location',
    'maximum batch size',
    'rate limit and delay policy',
    'separate DB write authorization if ever needed',
    'separate raw_match_data write authorization if ever needed',
];

const PRE_EXECUTION_CHECKLIST = [
    '32 target identities still match target_match_id, corrected_hash_id, and corrected_route_hash_pair',
    'no duplicate raw_match_data rows for the 32 targets',
    'DB invariant unchanged before execution',
    'output directory clean and explicitly approved',
    'no full HTML persistence unless separately authorized',
    'no full pageProps dump unless separately authorized',
    'payload minimization policy selected',
    'stable hash generation policy selected',
    'rollback and cleanup policy documented',
];

const STORAGE_POLICY = [
    'Do not store full raw payload in docs/_manifests.',
    'Prefer metadata and stable hashes in source-controlled manifests.',
    'Use a dedicated non-source-controlled raw external location only if explicitly authorized.',
    'Add or verify gitignore coverage before any local payload persistence.',
    'Use external storage for large payloads if retention is required.',
    'Do not commit full raw payload, full HTML, pageProps, or source body to git.',
];

const RISK_CONTROLS = [
    'anti-bot risk: require explicit live access authorization, low batch size, and delay policy',
    'stale route/hash risk: verify route/hash identity immediately before any future acquisition',
    'wrong orientation risk: re-check expected home/away/date/competition for all targets',
    'duplicate raw row risk: SELECT-only duplicate audit before any write authorization',
    'full HTML persistence risk: default to metadata/hash-only outputs',
    'DB write risk: keep acquisition and raw write phases separate',
    'dangerous historical script risk: use only reference paths; do not run write-capable scripts',
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

function assertInputs(preflight, inventory, adg59b, currentState) {
    const validations = [
        ['target_count', preflight.target_count === 32],
        ['accepted_count', preflight.accepted_count === 32],
        ['suspension_resolved_count', preflight.suspension_resolved_count === 32],
        ['raw_write_ready_count', preflight.raw_write_ready_count === 0],
        ['blocked_missing_payload', preflight.aggregate_counts?.blocked_missing_payload === 32],
        [
            'blocked_requires_explicit_write_authorization',
            preflight.aggregate_counts?.blocked_requires_explicit_write_authorization === 32,
        ],
        ['adg60_write_blocked', /ADG60 write remains blocked/i.test(preflight.recommended_next_step || '')],
        ['candidate_files_reviewed', inventory.candidate_files_reviewed_count === 133],
        [
            'inventory_candidates',
            Array.isArray(inventory.reusable_candidates) && Array.isArray(inventory.dangerous_candidates),
        ],
        ['adg59b_target_state', adg59b.target_count === 32 && adg59b.accepted_count === 32],
        [
            'current_state_block',
            currentState.includes('ADG60 remains blocked without separate explicit authorization'),
        ],
    ];
    const failures = validations.filter(([, passed]) => !passed).map(([name]) => name);
    if (failures.length > 0) {
        throw new Error(`Input validation failed: ${failures.join(', ')}`);
    }
}

function buildPlan({ generatedAt = new Date().toISOString() } = {}) {
    const preflight = readJson('docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json');
    const inventory = readJson('docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json');
    const adg59b = readJson('docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json');
    const currentState = readText('docs/data/FOTMOB_CURRENT_STATE.md');

    assertInputs(preflight, inventory, adg59b, currentState);

    return {
        schema_version: 'adg60_payload_acquisition_plan_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        safety: {
            live_fetch_performed: false,
            network_fetch_performed: false,
            browser_automation_performed: false,
            payload_saved: false,
            db_write_performed: false,
            raw_write_performed: false,
            raw_match_data_insert_performed: false,
            schema_migration_performed: false,
            adg60_write_performed: false,
        },
        target_count: preflight.target_count,
        accepted_count: preflight.accepted_count,
        suspension_resolved_count: preflight.suspension_resolved_count,
        raw_write_ready_count: preflight.raw_write_ready_count,
        current_blockers: {
            blocked_missing_payload: preflight.aggregate_counts.blocked_missing_payload,
            blocked_requires_explicit_write_authorization:
                preflight.aggregate_counts.blocked_requires_explicit_write_authorization,
            decision: preflight.decision,
        },
        target_scope: {
            only_adg59b_accepted_ligue1_targets: true,
            allow_extra_target_discovery: false,
            allow_scope_expansion: false,
        },
        target_field_requirements: TARGET_FIELD_REQUIREMENTS,
        acquisition_source_strategy: {
            preferred: 'pageProps v2 planning/preflight reference path',
            not_preferred: 'legacy API routes',
            forbidden_in_this_pr: [
                'live recapture execution',
                'controlled write execution',
                'raw write execution',
            ],
        },
        reusable_reference_paths: REUSABLE_REFERENCE_PATHS,
        forbidden_execution_paths: FORBIDDEN_EXECUTION_PATHS,
        authorization_required: true,
        authorization_checklist: AUTHORIZATION_CHECKLIST,
        pre_execution_checklist: PRE_EXECUTION_CHECKLIST,
        storage_policy_recommendation: STORAGE_POLICY,
        risk_controls: RISK_CONTROLS,
        acquisition_performed: false,
        payload_saved: false,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        adg60_write_performed: false,
        recommended_next_phase: NEXT_PHASE,
    };
}

function formatReport(plan) {
    const lines = [
        '<!-- markdownlint-disable MD013 -->',
        '',
        '# FotMob Ligue 1 ADG60 Payload Acquisition Plan',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${plan.phase}`,
        '- scope: plan only',
        '- based_on: ADG60 preflight no-write',
        '- based_on: ADG60 raw payload source inventory',
        `- target_count: ${plan.target_count}`,
        `- current blocker: blocked_missing_payload=${plan.current_blockers.blocked_missing_payload}`,
        '- no live fetch',
        '- no network fetch',
        '- no browser automation',
        '- no payload save',
        '- no DB write',
        '- no raw write',
        '- no raw_match_data insert',
        '- no schema migration',
        '- no ADG60 write',
        '',
        'This PR does not acquire raw payload. It only plans an authorization-gated acquisition workflow.',
        '',
        '## Target Scope',
        '',
        '- Scope is exactly the 32 ADG59B accepted Ligue 1 targets.',
        '- Do not add matches, discover new targets, or widen the batch.',
        `- Required target fields: ${plan.target_field_requirements.join(', ')}.`,
        '',
        '## Reusable Reference Paths',
        '',
        ...plan.reusable_reference_paths.map(item => `- ${item.path} (${item.category}; ${item.reuse})`),
        '',
        '## Dangerous Paths Not To Execute',
        '',
        ...plan.forbidden_execution_paths.map(item => `- ${item.path}: ${item.reason}`),
        '',
        '## Proposed Acquisition Strategy',
        '',
        '- Preferred path: pageProps v2 planning/preflight references.',
        '- Not preferred: legacy API routes.',
        '- Forbidden in this PR: live recapture, controlled write, raw write execution.',
        '',
        '## Authorization Gate Checklist',
        '',
        ...plan.authorization_checklist.map(item => `- ${item}`),
        '',
        '## Pre-Execution Checklist',
        '',
        ...plan.pre_execution_checklist.map(item => `- ${item}`),
        '',
        '## Storage Policy Recommendation',
        '',
        ...plan.storage_policy_recommendation.map(item => `- ${item}`),
        '',
        '## Risk Controls',
        '',
        ...plan.risk_controls.map(item => `- ${item}`),
        '',
        '## Recommended Next Step',
        '',
        `- recommended next phase: ${plan.recommended_next_phase}`,
        '- Next phase should be authorization gate only, not acquisition execution.',
    ];
    return `${lines.join('\n')}\n`;
}

function main() {
    const plan = buildPlan();
    writeJson(OUT_MANIFEST, plan);
    writeText(OUT_REPORT, formatReport(plan));
    console.log(
        JSON.stringify(
            {
                phase: plan.phase,
                target_count: plan.target_count,
                current_blocker: plan.current_blockers.blocked_missing_payload,
                reusable_reference_paths: plan.reusable_reference_paths.length,
                forbidden_execution_paths: plan.forbidden_execution_paths.length,
                acquisition_performed: plan.acquisition_performed,
                recommended_next_phase: plan.recommended_next_phase,
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
    AUTHORIZATION_CHECKLIST,
    FORBIDDEN_EXECUTION_PATHS,
    NEXT_PHASE,
    REUSABLE_REFERENCE_PATHS,
    buildPlan,
    formatReport,
};
