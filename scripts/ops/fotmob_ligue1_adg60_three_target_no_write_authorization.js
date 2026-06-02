#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 three-target authorization is merged
//
// WARNING: This helper is READ-ONLY. It reads existing manifests and generates
// a three-target authorization report/manifest. It does NOT perform any network
// request, DB write, browser automation, or payload persistence.
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-AUTHORIZATION';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_three_target_no_write_authorization.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_THREE_TARGET_NO_WRITE_AUTHORIZATION.md';
const REVIEWED_PR = 1408;
const REVIEWED_ONE_TARGET_PR = 1407;
const MAX_FUTURE_TARGET_COUNT = 3;
const CANDIDATE_TARGET_INDICES = [2, 3, 4];

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_LIVE_FETCH_ONE_TARGET_NO_WRITE_REVIEW.md',
    'docs/_manifests/fotmob_ligue1_adg60_live_fetch_one_target_no_write_review.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_ONE_TARGET_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_one_target_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_AUTHORIZATION.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_authorization.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_DRY_RUN_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
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

function validateInputs(reviewManifest, oneTargetManifest, dryRunManifest) {
    const checks = [
        ['review_accessibility_pass', reviewManifest.accessibility_review.verdict === 'pass'],
        ['review_payload_shape_pass', reviewManifest.payload_shape_review.verdict === 'pass'],
        ['review_safety_pass', reviewManifest.safety_review.verdict === 'pass'],
        ['one_target_reviewed_pr', reviewManifest.review_scope.reviewed_pr === REVIEWED_ONE_TARGET_PR],
        ['one_target_request_count', oneTargetManifest.execution_result.requestCount === 1],
        ['one_target_http_200', oneTargetManifest.execution_result.httpStatus === 200],
        ['one_target_body_not_persisted', oneTargetManifest.execution_result.bodyPersisted === false],
        ['dry_run_matrix_count', dryRunManifest.dry_run_matrix.length === 32],
        ['candidate_2_exists', dryRunManifest.dry_run_matrix.some(t => t.target_index === 2)],
        ['candidate_3_exists', dryRunManifest.dry_run_matrix.some(t => t.target_index === 3)],
        ['candidate_4_exists', dryRunManifest.dry_run_matrix.some(t => t.target_index === 4)],
    ];
    const failures = checks.filter(([, p]) => !p).map(([n]) => n);
    if (failures.length > 0) {
        throw new Error(`Input validation failed: ${failures.join(', ')}`);
    }
}

function getCandidateTargets(dryRunManifest) {
    return CANDIDATE_TARGET_INDICES.map(idx => {
        const t = dryRunManifest.dry_run_matrix.find(t => t.target_index === idx);
        return {
            target_index: t.target_index,
            target_match_id: t.target_match_id,
            expected_home: t.expected_home,
            expected_away: t.expected_away,
            expected_date: t.expected_date,
            competition: t.competition,
            corrected_hash_id: t.corrected_hash_id,
            corrected_route_hash_pair: t.corrected_route_hash_pair,
            identity_status: t.identity_status,
            route_hash_available: Boolean(t.corrected_route_hash_pair),
        };
    });
}

function buildAuthorization({ generatedAt = new Date().toISOString() } = {}) {
    const reviewManifest = readJson('docs/_manifests/fotmob_ligue1_adg60_live_fetch_one_target_no_write_review.json');
    const oneTargetManifest = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_one_target_no_write.json');
    const dryRunManifest = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json');

    validateInputs(reviewManifest, oneTargetManifest, dryRunManifest);

    const candidates = getCandidateTargets(dryRunManifest);

    const safety = {
        live_fetch_performed: false,
        network_fetch_performed: false,
        browser_automation_performed: false,
        payload_saved: false,
        response_body_saved: false,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        schema_migration_performed: false,
        adg60_write_performed: false,
        raw_write_ready_marked: false,
    };

    return {
        schema_version: 'adg60_three_target_no_write_authorization_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        reviewed_pr: REVIEWED_PR,
        reviewed_one_target_pr: REVIEWED_ONE_TARGET_PR,
        authorization_basis: {
            one_target_accessibility: reviewManifest.accessibility_review.verdict,
            one_target_payload_shape: reviewManifest.payload_shape_review.verdict,
            one_target_safety: reviewManifest.safety_review.verdict,
            evidence_quality: reviewManifest.evidence_quality_review.verdict,
            raw_write_ready: false,
            decision: 'Sufficient evidence to authorize a bounded 3-target authorization phase. Does not authorize execution, body persistence, DB write, or raw write.',
        },
        max_future_target_count: MAX_FUTURE_TARGET_COUNT,
        candidate_target_indices: CANDIDATE_TARGET_INDICES,
        candidates,
        candidate_target_policy: {
            source: 'ADG60 dry-run matrix (source-controlled)',
            selection_mode: 'sequential by target_index, starting from 2',
            no_target_discovery: true,
            no_extra_league: true,
            no_extra_season: true,
            no_extra_match: true,
            no_automatic_32_target_run: true,
            stop_if_missing_route_hash_or_identity: true,
            no_fallback_to_extra_targets_after_network_budget_consumed: true,
        },
        future_execution_policy: {
            max_network_requests: MAX_FUTURE_TARGET_COUNT,
            exactly_one_request_per_target: true,
            sequential_only: true,
            no_parallel_fetch: true,
            no_retry: true,
            delay_between_requests_seconds: { min: 20, max: 60 },
            timeout_seconds_per_request: 20,
            redirect: 'manual',
            execute_flag_required: true,
            stop_on_403: true,
            stop_on_429: true,
            stop_on_captcha: true,
            stop_on_anti_bot: true,
            stop_on_unexpected_redirect: true,
            stop_on_identity_mismatch: true,
            stop_on_route_hash_mismatch: true,
            stop_on_missing_metadata: true,
            stop_on_body_persistence_attempt: true,
            stop_on_db_write_attempt: true,
            stop_on_raw_match_data_insert_attempt: true,
        },
        payload_policy: {
            source_controlled_may_store: ['metadata', 'hash', 'status', 'size', 'content_type', 'schema_flags'],
            body_persistence_prohibited_unless_separate_authorization: true,
            full_html_not_committed: true,
            next_data_not_committed: true,
            pageprops_not_committed: true,
            raw_payload_not_committed: true,
            raw_storage_if_later_authorized_must_be_gitignored: true,
            raw_storage_if_later_authorized_requires_separate_review: true,
        },
        write_policy: {
            db_write_prohibited: true,
            raw_write_prohibited: true,
            raw_match_data_insert_prohibited: true,
            schema_migration_prohibited: true,
            adg60_write_blocked: true,
            raw_write_ready_remains_false: true,
            raw_write_ready_requires_separate_raw_storage_and_write_authorization_review: true,
        },
        browser_policy: {
            browser_automation_prohibited: true,
            playwright_prohibited: true,
            chromium_prohibited: true,
            browser_backed_capture_requires_separate_explicit_authorization_pr: true,
        },
        stop_conditions: [
            'target identity mismatch', 'home/away orientation mismatch',
            'expected date mismatch', 'competition mismatch',
            'missing corrected_hash_id', 'missing route hash',
            'duplicate raw_match_data row already exists', 'output directory not clean',
            'payload would be saved to git-tracked path', 'full HTML would be saved',
            'full pageProps would be saved', 'DB write attempted',
            'raw_match_data insert attempted', 'unexpected network route',
            'unexpected redirect', '403 / 429 / captcha / anti-bot / blocked response',
            'unexpected schema / payload structure', 'payload too large (> 5 MB per target)',
            'more targets than authorized batch (max=3)', 'any automatic retry loop',
            'parallel fetch attempted', 'browser automation attempted',
        ],
        review_policy: {
            review_required_after_3_targets: true,
            no_automatic_next_batch: true,
            no_automatic_32_target_run: true,
            any_failure_blocks_expansion: true,
            next_execution_requires_explicit_separate_pr: true,
        },
        readiness_decision: {
            ready_for_next_authorization_phase: true,
            current_phase_is_authorization_only: true,
            execution_deferred_to_separate_pr: true,
            raw_write_ready_remains_false: true,
            db_write_remains_prohibited: true,
            adg60_write_remains_blocked: true,
        },
        recommended_next_phase: NEXT_PHASE,
        safety,
        ...safety,
    };
}

function formatReport(manifest) {
    const cand = manifest.candidates || [];
    const lines = [
        '<!-- markdownlint-disable MD013 -->', '',
        '# FotMob Ligue 1 ADG60 Three Target No Write Authorization',
        '', '- lifecycle: phase-artifact', `- phase: ${manifest.phase}`,
        '- scope: authorization only',
        `- source review: PR #${manifest.reviewed_pr}`,
        `- source one-target result: PR #${manifest.reviewed_one_target_pr}`,
        '- no live fetch', '- no network fetch', '- no browser automation',
        '- no payload save', '- no DB write', '- no raw write',
        '- no raw_match_data insert', '- no schema migration', '- no ADG60 write',
        '', 'This PR authorizes a future bounded three-target live fetch no-write phase. It does not execute any fetch.',
        '', '## Why Next Authorization Is Justified',
        '', 'The one-target review confirmed:', '',
        `- **Accessibility**: ${manifest.authorization_basis.one_target_accessibility} — FotMob detail page is accessible`,
        `- **Payload shape**: ${manifest.authorization_basis.one_target_payload_shape} — \`__NEXT_DATA__\` and pageProps confirmed`,
        `- **Safety**: ${manifest.authorization_basis.one_target_safety} — constraints held`,
        `- **Evidence quality**: ${manifest.authorization_basis.evidence_quality}`,
        '', '## Authorization Scope',
        '', '### Target Scope',
        '', `- max future targets: **${manifest.max_future_target_count}**`,
        '- target source: existing ADG60 dry-run matrix (source-controlled)',
        `- candidate target indices: **[${manifest.candidate_target_indices.join(', ')}]**`,
        '', '| Target Index | Match ID | Match |',
        '|---|---|---|',
        ...cand.map(c => `| ${c.target_index} | \`${c.target_match_id}\` | ${c.expected_home} vs ${c.expected_away} |`),
        '', '- no target discovery', '- no extra leagues/seasons/matches',
        '- no automatic 32-target run',
        '',
        '### Future Execution Policy',
        '', `- max network requests: **${manifest.max_future_target_count}**`,
        '- sequential only, no parallel fetch, no retry',
        `- delay: ${manifest.future_execution_policy.delay_between_requests_seconds.min}-${manifest.future_execution_policy.delay_between_requests_seconds.max}s`,
        `- timeout: <= ${manifest.future_execution_policy.timeout_seconds_per_request}s`,
        `- redirect: ${manifest.future_execution_policy.redirect}`,
        '- stop on: 403/429/captcha/anti-bot/redirect/identity-mismatch/body-persistence/DB-write',
        '',
        '### Payload / Write / Browser Policy',
        '', '- **Payload**: metadata/hash only in git; body persistence requires separate authorization',
        '- **Write**: DB/raw/raw_match_data writes remain prohibited; ADG60 write blocked',
        '- **Browser**: prohibited; requires separate explicit authorization PR',
        '',
        '### Review Policy',
        '', '- review required after 3 targets',
        '- no automatic next batch or 32-target run',
        '- any failure blocks expansion',
        '',
        '## Stop Conditions', '',
        ...manifest.stop_conditions.map(c => `- ${c}`),
        '',
        '## Readiness Decision', '',
        `- ready: **${manifest.readiness_decision.ready_for_next_authorization_phase}**`,
        '- current phase is authorization only, execution deferred',
        '- raw_write_ready remains false',
        '- DB write remains prohibited',
        '',
        '## Safety', '',
        `- live_fetch_performed: ${manifest.live_fetch_performed}`,
        `- network_fetch_performed: ${manifest.network_fetch_performed}`,
        `- browser_automation_performed: ${manifest.browser_automation_performed}`,
        `- payload_saved: ${manifest.payload_saved}`,
        `- db_write_performed: ${manifest.db_write_performed}`,
        `- raw_write_performed: ${manifest.raw_write_performed}`,
        `- raw_match_data_insert_performed: ${manifest.raw_match_data_insert_performed}`,
        `- adg60_write_performed: ${manifest.adg60_write_performed}`,
        `- raw_write_ready_marked: ${manifest.raw_write_ready_marked}`,
        '',
        '## Recommended Next Phase', '',
        '```', manifest.recommended_next_phase, '```', '',
        'Next phase will execute live fetch for at most 3 targets with all the guards defined in this authorization.',
    ];
    return `${lines.join('\n')}\n`;
}

function main() {
    const auth = buildAuthorization();
    writeJson(OUT_MANIFEST, auth);
    writeText(OUT_REPORT, formatReport(auth));
    console.log(JSON.stringify({
        phase: auth.phase,
        reviewed_pr: auth.reviewed_pr,
        max_future_target_count: auth.max_future_target_count,
        candidate_indices: auth.candidate_target_indices,
        readiness: auth.readiness_decision.ready_for_next_authorization_phase,
        live_fetch_performed: auth.live_fetch_performed,
        db_write_performed: auth.db_write_performed,
        raw_write_ready_marked: auth.raw_write_ready_marked,
        recommended_next_phase: auth.recommended_next_phase,
    }, null, 2));
}

if (require.main === module) {
    main();
}

module.exports = {
    NEXT_PHASE,
    REVIEWED_PR,
    REVIEWED_ONE_TARGET_PR,
    MAX_FUTURE_TARGET_COUNT,
    CANDIDATE_TARGET_INDICES,
    validateInputs,
    getCandidateTargets,
    buildAuthorization,
    formatReport,
};
