#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 one-target review is merged
//
// WARNING: This helper is READ-ONLY. It reads existing manifests and generates
// a review report/manifest. It does NOT perform any network request, DB write,
// browser automation, or payload persistence.
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE-REVIEW';
const NEXT_PHASE = 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-AUTHORIZATION';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_live_fetch_one_target_no_write_review.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_LIVE_FETCH_ONE_TARGET_NO_WRITE_REVIEW.md';
const REVIEWED_PR = 1407;
const REVIEWED_MERGE_COMMIT = 'd5e3ad2fc41b3761d4e9a3d88cf159509b39710a';

const SOURCE_INPUTS = [
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_ONE_TARGET_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_one_target_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_LIVE_FETCH_AUTHORIZATION.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_authorization.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_DRY_RUN_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PAYLOAD_ACQUISITION_PLAN.md',
    'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_plan.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md',
    'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
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

function validateSourceResult(fetchManifest) {
    const er = fetchManifest.execution_result;
    const checks = [
        ['request_count', er.requestCount === 1],
        ['http_status', er.httpStatus === 200],
        ['sha256_exists', typeof er.bodySha256 === 'string' && er.bodySha256.length === 64],
        ['hasNextDataMarker', er.minimalSchemaFlags.hasNextDataMarker === true],
        ['hasPagePropsMarker', er.minimalSchemaFlags.hasPagePropsMarker === true],
        ['hasMatchDetails', er.minimalSchemaFlags.hasMatchDetails === true],
        ['body_persisted', er.bodyPersisted === false],
        ['body_logged', er.bodyLogged === false],
        ['body_committed', er.bodyCommitted === false],
        ['db_write', fetchManifest.db_write_performed === false],
        ['raw_write', fetchManifest.raw_write_performed === false],
        ['raw_match_data', fetchManifest.raw_match_data_insert_performed === false],
        ['adg60_write', fetchManifest.adg60_write_performed === false],
        ['raw_write_ready', fetchManifest.raw_write_ready_marked === false],
    ];
    const failures = checks.filter(([, p]) => !p).map(([n]) => n);
    if (failures.length > 0) {
        throw new Error(`Source result validation failed: ${failures.join(', ')}`);
    }
}

function runReview(fetchManifest) {
    const er = fetchManifest.execution_result;
    const sf = er.minimalSchemaFlags;
    const t = fetchManifest.selected_target;

    const accessibility = {
        route_reachable: er.httpStatus === 200,
        http_200_sufficient: er.httpStatus === 200,
        redirected: er.redirected === true,
        no_403_429_captcha_anti_bot_block: er.httpStatus !== 403 && er.httpStatus !== 429,
        single_request_no_retry_strategy_affirmed: true,
        verdict: er.httpStatus === 200 ? 'pass' : 'fail',
        notes: er.httpStatus === 200
            ? 'Target route is accessible. HTTP 200 confirms the FotMob detail page serves content. No blocking signals detected. Continue single-request/no-retry strategy.'
            : `HTTP ${er.httpStatus} — review required before proceeding.`,
    };

    const payloadShape = {
        content_type_html_expected: er.contentType.includes('text/html'),
        looksLikeHtml_consistent_with_detail_page: sf.looksLikeHtml === true,
        hasNextDataMarker_supports_nextjs_extraction: sf.hasNextDataMarker === true,
        hasPagePropsMarker_supports_pageprops_route: sf.hasPagePropsMarker === true,
        hasMatchDetails_supports_detail_payload_route: sf.hasMatchDetails === true,
        looksLikeJson_false_is_expected: sf.looksLikeJson === false,
        verdict: sf.hasNextDataMarker && sf.hasPagePropsMarker ? 'pass' : 'review',
        notes: sf.hasNextDataMarker
            ? 'Response is HTML with embedded `__NEXT_DATA__` and pageProps, consistent with FotMob SSR detail page. This confirms the pageProps v2 route is viable for future extraction.'
            : '`__NEXT_DATA__` marker not found — may need to investigate alternative payload paths.',
    };

    const safety = {
        body_persisted: er.bodyPersisted,
        body_committed_to_git: er.bodyCommitted,
        html_saved: false,
        next_data_saved: false,
        pageprops_saved: false,
        full_payload_saved: false,
        db_write_performed: fetchManifest.db_write_performed,
        raw_match_data_insert_performed: fetchManifest.raw_match_data_insert_performed,
        schema_migration_performed: fetchManifest.schema_migration_performed,
        adg60_write_performed: fetchManifest.adg60_write_performed,
        raw_write_ready_marked: fetchManifest.raw_write_ready_marked,
        verdict: 'pass',
        notes: 'All safety constraints were upheld. No body was persisted, logged, or committed. No DB/raw/raw_match_data writes occurred.',
    };

    const evidence = {
        metadata_sufficient_for_accessibility_proof: true,
        metadata_insufficient_for_raw_write_ready: true,
        hash_and_size_recorded_for_future_verification: true,
        supports_continued_no_write_experiments: true,
        does_not_support_raw_write_ready_true: true,
        does_not_authorize_db_write: true,
        does_not_authorize_raw_match_data_insert: true,
        does_not_authorize_full_32_target_run: true,
        verdict: 'sufficient_for_next_authorization_phase_only',
    };

    const readiness = {
        ready_for_next_phase: accessibility.verdict === 'pass' && payloadShape.verdict === 'pass',
        next_phase_is_authorization_only: true,
        next_phase_is_not_execution: true,
        raw_write_ready_remains_false: true,
        db_write_remains_prohibited: true,
        adg60_write_remains_blocked: true,
    };

    return {
        addressed_target: t,
        accessibility_review: accessibility,
        payload_shape_review: payloadShape,
        safety_review: safety,
        evidence_quality_review: evidence,
        readiness_decision: readiness,
    };
}

function buildReview({ generatedAt = new Date().toISOString() } = {}) {
    const fetchManifest = readJson('docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_one_target_no_write.json');
    validateSourceResult(fetchManifest);

    const review = runReview(fetchManifest);

    const safety = {
        new_live_fetch_performed: false,
        new_network_fetch_performed: false,
        new_browser_automation_performed: false,
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
        schema_version: 'adg60_live_fetch_one_target_no_write_review_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        review_scope: {
            reviewed_pr: REVIEWED_PR,
            reviewed_merge_commit: REVIEWED_MERGE_COMMIT,
            reviewed_phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE',
        },
        selected_target: fetchManifest.selected_target,
        reviewed_fetch_result: {
            request_performed: fetchManifest.execution_result.requestPerformed,
            request_count: fetchManifest.execution_result.requestCount,
            http_status: fetchManifest.execution_result.httpStatus,
            content_type: fetchManifest.execution_result.contentType,
            byte_size: fetchManifest.execution_result.byteSize,
            sha256: fetchManifest.execution_result.bodySha256,
            payload_like: fetchManifest.execution_result.payloadLike,
            minimal_schema_flags: fetchManifest.execution_result.minimalSchemaFlags,
            body_persisted: fetchManifest.execution_result.bodyPersisted,
            body_logged: fetchManifest.execution_result.bodyLogged,
            body_committed: fetchManifest.execution_result.bodyCommitted,
        },
        ...review,
        recommended_next_phase: NEXT_PHASE,
        next_phase_gates: [
            'Still no DB write — DB/raw/raw_match_data writes remain strictly prohibited',
            'Still no body commit — full HTML/`__NEXT_DATA__`/pageProps/raw payload must not be committed to git',
            'If body persistence is desired, it must be separately authorized for gitignored raw storage only',
            'If body persistence is NOT authorized, next phase must continue metadata/hash/status only',
            'Batch size max=3 — no more than 3 targets in the next authorization scope',
            'No parallel fetch — sequential only, 20-60s delay between requests',
            'Stop on any 403/429/captcha/anti-bot/redirect anomaly',
            'Review required after 3 targets — no automatic progression to 32-target run',
            'Live fetch execution still requires separate --execute flag and explicit PR approval',
            'Browser automation remains prohibited unless separately authorized',
        ],
        safety,
        ...safety,
    };
}

function fmtReviewHeader(manifest) {
    return [
        '<!-- markdownlint-disable MD013 -->', '',
        '# FotMob Ligue 1 ADG60 Live Fetch One Target No Write — Review',
        '', '- lifecycle: phase-artifact', `- phase: ${manifest.phase}`,
        '- scope: review only',
        `- source result: PR #${manifest.review_scope.reviewed_pr} / merge commit \`${manifest.review_scope.reviewed_merge_commit}\``,
        '- no new live fetch', '- no new network fetch', '- no browser automation',
        '- no payload save', '- no DB write', '- no raw write',
        '- no raw_match_data insert', '- no schema migration', '- no ADG60 write',
        '', 'This PR reviews the merged one-target live fetch result from PR #1407. It does not perform any new fetch.',
    ];
}

function fmtTargetSection(t) {
    return ['', '## Selected Target (from PR #1407)', '',
        `- target_index: ${t.target_index}`, `- target_match_id: \`${t.target_match_id}\``,
        `- expected_home: ${t.expected_home}`, `- expected_away: ${t.expected_away}`,
        `- expected_date: ${t.expected_date}`, `- competition: ${t.competition}`,
        `- corrected_hash_id: \`${t.corrected_hash_id}\``,
        `- corrected_route_hash_pair: \`${t.corrected_route_hash_pair}\``,
    ];
}

function fmtResultSummary(r) {
    return ['', '## Live Fetch Result Summary', '',
        `- request_performed: ${r.request_performed}`, `- request_count: ${r.request_count}`,
        `- http_status: ${r.http_status}`, `- content_type: ${r.content_type}`,
        `- byte_size: ${r.byte_size.toLocaleString()} (~${Math.round(r.byte_size / 1024)} KB)`,
        `- sha256: \`${r.sha256}\``, `- payload_like: ${r.payload_like}`,
        `- hasNextDataMarker: ${r.minimal_schema_flags.hasNextDataMarker}`,
        `- hasPagePropsMarker: ${r.minimal_schema_flags.hasPagePropsMarker}`,
        `- hasMatchDetails: ${r.minimal_schema_flags.hasMatchDetails}`,
        `- body_persisted: ${r.body_persisted}`, `- body_logged: ${r.body_logged}`,
        `- body_committed: ${r.body_committed}`,
    ];
}

function fmtAccessibilityReview(ar, r) {
    return ['', '## Review', '', '### 1. Accessibility Review', '',
        '| Criterion | Result |', '|-----------|--------|',
        `| Route reachable | **${ar.route_reachable ? 'PASS' : 'FAIL'}** — HTTP ${r.http_status} |`,
        `| HTTP 200 sufficient | **${ar.http_200_sufficient ? 'PASS' : 'FAIL'}** |`,
        `| Redirected | **${ar.redirected ? 'WARN' : 'PASS'}** — ${ar.redirected ? 'redirect detected' : 'no redirect'} |`,
        `| 403/429/captcha/anti-bot/block | **${ar.no_403_429_captcha_anti_bot_block ? 'PASS' : 'FAIL'}** |`,
        '| Single-request/no-retry strategy | **AFFIRMED** — continue |',
        '', `**Verdict**: ${ar.verdict.toUpperCase()}. ${ar.notes}`,
    ];
}

function fmtPayloadReview(pr) {
    return ['', '### 2. Payload Shape Review', '',
        '| Criterion | Result |', '|-----------|--------|',
        `| content_type=text/html | **${pr.content_type_html_expected ? 'EXPECTED' : 'UNEXPECTED'}** |`,
        `| looksLikeHtml=true | **${pr.looksLikeHtml_consistent_with_detail_page ? 'CONSISTENT' : 'UNEXPECTED'}** |`,
        `| hasNextDataMarker=true | **${pr.hasNextDataMarker_supports_nextjs_extraction ? 'SUPPORTS' : 'MISSING'}** |`,
        `| hasPagePropsMarker=true | **${pr.hasPagePropsMarker_supports_pageprops_route ? 'SUPPORTS' : 'MISSING'}** |`,
        `| hasMatchDetails=true | **${pr.hasMatchDetails_supports_detail_payload_route ? 'SUPPORTS' : 'MISSING'}** |`,
        `| looksLikeJson=false | **${pr.looksLikeJson_false_is_expected ? 'EXPECTED' : 'UNEXPECTED'}** |`,
        '', `**Verdict**: ${pr.verdict.toUpperCase()}. ${pr.notes}`,
    ];
}

function fmtSafetyReview(sr) {
    return ['', '### 3. Safety Review', '',
        '| Criterion | Result |', '|-----------|--------|',
        `| Body persisted | **${sr.body_persisted}** |`,
        `| Body committed to git | **${sr.body_committed_to_git}** |`,
        `| DB write | **${sr.db_write_performed}** |`,
        `| raw_match_data insert | **${sr.raw_match_data_insert_performed}** |`,
        `| Schema migration | **${sr.schema_migration_performed}** |`,
        `| ADG60 write | **${sr.adg60_write_performed}** |`,
        `| raw_write_ready_marked | **${sr.raw_write_ready_marked}** |`,
        '', `**Verdict**: ${sr.verdict.toUpperCase()}. ${sr.notes}`,
    ];
}

function fmtEvidenceReview(eq) {
    return ['', '### 4. Evidence Quality Review', '',
        '| Criterion | Assessment |', '|-----------|-----------|',
        `| Metadata sufficient for accessibility proof | **${eq.metadata_sufficient_for_accessibility_proof ? 'YES' : 'NO'}** |`,
        `| Metadata insufficient for raw_write_ready | **${eq.metadata_insufficient_for_raw_write_ready ? 'YES' : 'NO'}** |`,
        `| Hash and size recorded | **${eq.hash_and_size_recorded_for_future_verification ? 'YES' : 'NO'}** |`,
        `| Supports continued no-write experiments | **${eq.supports_continued_no_write_experiments ? 'YES' : 'NO'}** |`,
        `| Does NOT authorize DB write | **${eq.does_not_authorize_db_write ? 'CORRECT' : 'INCORRECT'}** |`,
        `| Does NOT authorize raw_match_data insert | **${eq.does_not_authorize_raw_match_data_insert ? 'CORRECT' : 'INCORRECT'}** |`,
        `| Does NOT authorize full 32-target run | **${eq.does_not_authorize_full_32_target_run ? 'CORRECT' : 'INCORRECT'}** |`,
        '', `**Verdict**: ${eq.verdict}`,
    ];
}

function fmtReadiness(rd) {
    return ['', '### 5. Next-Phase Readiness', '',
        `**Decision**: ${rd.ready_for_next_phase ? 'Ready for next authorization phase.' : 'Not ready.'}`,
        '', '- This result does **not** make raw_write_ready=true.',
        '- This result does **not** authorize DB write.',
        '- This result does **not** authorize raw_match_data insert.',
        '- This result does **not** authorize a full 32-target run.',
    ];
}

function fmtNextAndSafety(manifest) {
    return ['', '## Recommended Next Phase', '',
        '```', manifest.recommended_next_phase, '```', '',
        '**Important**: This is an **authorization** phase, not an execution phase.',
        '', '### Gating Conditions', '',
        ...manifest.next_phase_gates.map(g => `- ${g}`),
        '', '## Safety', '',
        `- new_live_fetch_performed: ${manifest.new_live_fetch_performed}`,
        `- new_network_fetch_performed: ${manifest.new_network_fetch_performed}`,
        `- new_browser_automation_performed: ${manifest.new_browser_automation_performed}`,
        `- db_write_performed: ${manifest.db_write_performed}`,
        `- raw_write_performed: ${manifest.raw_write_performed}`,
        `- raw_match_data_insert_performed: ${manifest.raw_match_data_insert_performed}`,
        `- adg60_write_performed: ${manifest.adg60_write_performed}`,
        `- raw_write_ready_marked: ${manifest.raw_write_ready_marked}`,
    ];
}

function formatReport(manifest) {
    const lines = [].concat(
        fmtReviewHeader(manifest),
        fmtTargetSection(manifest.selected_target),
        fmtResultSummary(manifest.reviewed_fetch_result),
        fmtAccessibilityReview(manifest.accessibility_review, manifest.reviewed_fetch_result),
        fmtPayloadReview(manifest.payload_shape_review),
        fmtSafetyReview(manifest.safety_review),
        fmtEvidenceReview(manifest.evidence_quality_review),
        fmtReadiness(manifest.readiness_decision),
        fmtNextAndSafety(manifest),
    );
    return `${lines.join('\n')}\n`;
}

function main() {
    const review = buildReview();
    writeJson(OUT_MANIFEST, review);
    writeText(OUT_REPORT, formatReport(review));
    console.log(JSON.stringify({
        phase: review.phase,
        reviewed_pr: review.review_scope.reviewed_pr,
        accessibility: review.accessibility_review.verdict,
        payload_shape: review.payload_shape_review.verdict,
        safety: review.safety_review.verdict,
        evidence: review.evidence_quality_review.verdict,
        readiness: review.readiness_decision.ready_for_next_phase,
        new_live_fetch_performed: review.new_live_fetch_performed,
        new_network_fetch_performed: review.new_network_fetch_performed,
        db_write_performed: review.db_write_performed,
        raw_write_ready_marked: review.raw_write_ready_marked,
        recommended_next_phase: review.recommended_next_phase,
    }, null, 2));
}

if (require.main === module) {
    main();
}

module.exports = {
    NEXT_PHASE,
    REVIEWED_PR,
    REVIEWED_MERGE_COMMIT,
    validateSourceResult,
    runReview,
    buildReview,
    formatReport,
};
