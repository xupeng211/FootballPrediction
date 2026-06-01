#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 payload acquisition authorization gate is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-AUTHORIZATION-GATE';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-DRY-RUN-NO-WRITE';
const USER_AUTHORIZATION_QUOTE = '\u6211\u660e\u786e\u6388\u6743';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_authorization_gate.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_AUTHORIZATION_GATE.md';

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md',
    'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_PLAN.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const ALLOWED_ACTIONS_THIS_PR = [
    'create authorization manifest',
    'create authorization report',
    'create pre-execution checklist',
    'create future execution requirements',
    'create safety boundary',
    'create storage policy decision matrix',
    'create batch/rate-limit recommendation',
];

const FORBIDDEN_ACTIONS_THIS_PR = [
    'live fetch',
    'network fetch',
    'browser ' + 'automation',
    'payload ' + 'save',
    'raw payload acquisition execution',
    'DB write',
    'raw write',
    'raw_match_data ' + 'insert',
    'schema ' + 'migration',
    'ADG60 write',
];

const FUTURE_EXECUTION_PREREQUISITES = [
    'whether live/network fetch is allowed',
    'whether browser automation is allowed',
    'whether payload persistence is allowed',
    'exact storage location',
    'batch size',
    'rate limit / delay',
    'payload minimization policy',
    'hash policy',
    'cleanup policy',
    'no DB write unless separately authorized',
    'no raw_match_data insert unless separately authorized',
];

const TARGET_SCOPE = [
    'exactly 32 ADG59B accepted Ligue 1 targets',
    'no scope expansion',
    'no target discovery',
    'no extra leagues',
    'no extra seasons',
    'no extra matches',
];

const STORAGE_POLICY_REQUIREMENTS = [
    'default to metadata/hash-only source-controlled outputs',
    'do not commit full raw payload, full HTML, __NEXT_DATA__, pageProps, or source body',
    'require explicit storage location before any future payload persistence',
    'require gitignore or external storage review before any future local payload persistence',
    'document cleanup policy before any future dry-run writes files',
];

const BATCH_RATE_LIMIT_REQUIREMENTS = [
    'future dry-run must declare max batch size before any request-capable code is run',
    'future dry-run must declare delay/rate-limit policy before any request-capable code is run',
    'future dry-run must stop on identity mismatch, route/hash drift, or unexpected payload shape',
    'future dry-run must stay no-DB-write and no-raw_match_data-insert unless separately authorized',
];

const RISK_CONTROLS = [
    'anti-bot risk remains blocked until explicit live/network authorization',
    'wrong target risk controlled by exact 32-target scope and identity re-check',
    'payload persistence risk controlled by metadata/hash-only default',
    'DB write risk controlled by keeping write authorization separate',
    'dangerous script risk controlled by not executing historical recapture/write/backfill scripts',
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

function validateInputs({ preflight, inventory, plan, adg59b, currentState }) {
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
        ['plan_next_phase', plan.recommended_next_phase === PHASE],
        ['plan_acquisition_not_started', plan.acquisition_performed === false],
        ['plan_payload_not_saved', plan.payload_saved === false],
        ['plan_db_not_written', plan.db_write_performed === false],
        ['plan_raw_not_written', plan.raw_write_performed === false],
        ['plan_adg60_write_not_started', plan.adg60_write_performed === false],
        ['adg59b_target_count', adg59b.target_count === 32],
        ['adg59b_accepted_count', adg59b.accepted_count === 32],
        ['adg59b_suspension_resolved_count', adg59b.suspension_resolved_count === 32],
        ['current_state_adg60_blocked', currentState.includes('ADG60 remains blocked without separate explicit authorization')],
    ];
    const failures = checks.filter(([, passed]) => !passed).map(([name]) => name);
    if (failures.length > 0) {
        throw new Error(`Input validation failed: ${failures.join(', ')}`);
    }
}

function buildAuthorizationGate({ generatedAt = new Date().toISOString() } = {}) {
    const preflight = readJson('docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json');
    const inventory = readJson('docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json');
    const plan = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json');
    const adg59b = readJson('docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json');
    const currentState = readText('docs/data/FOTMOB_CURRENT_STATE.md');

    validateInputs({ preflight, inventory, plan, adg59b, currentState });

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
        schema_version: 'adg60_payload_acquisition_authorization_gate_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        user_authorization_quote: USER_AUTHORIZATION_QUOTE,
        authorization_interpretation: {
            summary:
                'Authorization to proceed to authorization-gated payload acquisition preparation only; not DB write, not raw write, not raw_match_data write, and not acquisition execution in this PR.',
            authorization_gate_only: true,
            db_write_authorized: false,
            raw_write_authorized: false,
            raw_match_data_write_authorized: false,
            acquisition_execution_authorized_this_pr: false,
            adg60_write_authorized: false,
        },
        source_inputs: SOURCE_INPUTS,
        target_count: preflight.target_count,
        current_blockers: {
            blocked_missing_payload: preflight.aggregate_counts.blocked_missing_payload,
            blocked_requires_explicit_write_authorization:
                preflight.aggregate_counts.blocked_requires_explicit_write_authorization,
            raw_write_ready_count: preflight.raw_write_ready_count,
            decision: preflight.decision,
        },
        target_scope: TARGET_SCOPE,
        allowed_actions_this_pr: ALLOWED_ACTIONS_THIS_PR,
        forbidden_actions_this_pr: FORBIDDEN_ACTIONS_THIS_PR,
        future_execution_prerequisites: FUTURE_EXECUTION_PREREQUISITES,
        storage_policy_requirements: STORAGE_POLICY_REQUIREMENTS,
        batch_rate_limit_requirements: BATCH_RATE_LIMIT_REQUIREMENTS,
        risk_controls: RISK_CONTROLS,
        safety,
        ...safety,
        recommended_next_phase: NEXT_PHASE,
        next_phase_boundary:
            'Next phase may prepare an executable dry-run, but still must not write DB or raw_match_data.',
    };
}

function formatReport(gate) {
    const quote = `\u201c${gate.user_authorization_quote}\u201d`;
    const lines = [
        '<!-- markdownlint-disable MD013 -->',
        '',
        '# FotMob Ligue 1 ADG60 Payload Acquisition Authorization Gate',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${gate.phase}`,
        '- scope: authorization gate only',
        `- user authorization quote: ${quote}`,
        '- authorization interpreted as: authorization to proceed to authorization-gated payload acquisition preparation, not DB write, not raw write, not acquisition execution in this PR',
        `- target_count: ${gate.target_count}`,
        `- current blocker: blocked_missing_payload=${gate.current_blockers.blocked_missing_payload}`,
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
        '## Exact Target Scope',
        '',
        ...gate.target_scope.map(item => `- ${item}`),
        '',
        '## Allowed Actions In This PR',
        '',
        ...gate.allowed_actions_this_pr.map(item => `- ${item}`),
        '',
        '## Forbidden Actions In This PR',
        '',
        ...gate.forbidden_actions_this_pr.map(item => `- ${item}`),
        '',
        '## Future Acquisition Execution Prerequisites',
        '',
        ...gate.future_execution_prerequisites.map(item => `- ${item}`),
        '',
        '## Storage Policy Requirements',
        '',
        ...gate.storage_policy_requirements.map(item => `- ${item}`),
        '',
        '## Batch And Rate-Limit Requirements',
        '',
        ...gate.batch_rate_limit_requirements.map(item => `- ${item}`),
        '',
        '## Risk Controls',
        '',
        ...gate.risk_controls.map(item => `- ${item}`),
        '',
        '## Recommended Next Phase',
        '',
        `- recommended next phase: ${gate.recommended_next_phase}`,
        '- Next phase may prepare an executable dry-run, but still must not write DB or raw_match_data.',
    ];
    return `${lines.join('\n')}\n`;
}

function main() {
    const gate = buildAuthorizationGate();
    writeJson(OUT_MANIFEST, gate);
    writeText(OUT_REPORT, formatReport(gate));
    console.log(
        JSON.stringify(
            {
                phase: gate.phase,
                target_count: gate.target_count,
                current_blocker: gate.current_blockers.blocked_missing_payload,
                acquisition_execution_performed: gate.acquisition_execution_performed,
                db_write_performed: gate.db_write_performed,
                raw_write_performed: gate.raw_write_performed,
                recommended_next_phase: gate.recommended_next_phase,
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
    USER_AUTHORIZATION_QUOTE,
    buildAuthorizationGate,
    formatReport,
};
