#!/usr/bin/env node
/* eslint-disable complexity, no-promise-executor-return */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
// ADG12 uses global fetch() (Node 20+) for bounded public page-route requests
// No ProxyProvider needed: we WANT to detect 403/block/anti-bot, not bypass them

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG12';
const STATUS = 'completed_bounded_observed_identity_evidence_acquisition_execution';

const ADG11_PLAN_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_plan.adg11.json';
const ADG8_RESULT_PATH = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const PROPOSAL_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ENRICHED_TARGETS_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_OBSERVED_IDENTITY_EVIDENCE_ACQUISITION_RESULT_ADG12.md';

const REQUEST_TIMEOUT_MS = 20000;
const DELAY_MS_MIN = 10000;
const DELAY_MS_MAX = 15000;
const FOTMOB_BASE = 'https://www.fotmob.com';

const {
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const { extractFromHtml } = require('../../src/parsers/fotmob/NextDataParser');

const BATCH_A_IDS = ['4813735', '4830467', '4830468', '4830469', '4830470', '4830471',
    '4830458', '4830464', '4830466'];

const BLOCK_MARKERS = [
    'captcha', 'verify you are human', 'cloudflare', 'cf-chl',
    'attention required', 'just a moment', 'rate limit', 'too many requests',
    'access denied', 'request blocked', 'forbidden',
];

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(absolutePath(filePath), 'utf8'));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function randomDelayMs(min, max) {
    return Math.floor(Math.random() * (max - min + 1) + min);
}

function extractSafeMetadata(parsedData) {
    if (!parsedData?.success || !parsedData.data) return null;
    const pp = parsedData.data?.props?.pageProps;
    if (!pp) return null;
    const g = pp.general || {};
    return {
        observed_detail_id: String(g.matchId || pp.matchId || ''),
        observed_home_team: g.homeTeam?.name || null,
        observed_away_team: g.awayTeam?.name || null,
        observed_match_date: g.matchTimeUTC || null,
        observed_competition: g.leagueName || g.parentLeagueName || null,
        observed_status: g.status?.utcTime || null,
        hydration_marker_present: Boolean(g.matchId),
        safe_identity_marker_present: Boolean(g.homeTeam?.name && g.awayTeam?.name),
    };
}

function detectAntiBot(html) {
    const lower = html.toLowerCase();
    for (const marker of BLOCK_MARKERS) {
        if (lower.includes(marker)) return marker;
    }
    return null;
}

async function fetchPage(url) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
    try {
        const res = await fetch(url, {
            signal: ctrl.signal,
            headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FootballPrediction/4.51)' },
        });
        clearTimeout(timer);
        if (res.status !== 200) {
            return { httpStatus: res.status, html: null, redirectUrl: res.headers.get('location') || null };
        }
        const html = await res.text();
        return { httpStatus: 200, html, redirectUrl: null };
    } catch (e) {
        clearTimeout(timer);
        return { httpStatus: 0, html: null, error: e.message };
    }
}

function buildExistingEvidenceMap(adg8Result = {}) {
    const map = new Map();
    for (const r of adg8Result.audit_results || []) {
        if (r.schedule_external_id && r.observed_detail_id) {
            map.set(r.schedule_external_id, {
                observed_detail_id: r.observed_detail_id,
                observed_home_team: r.observed_home_team,
                observed_away_team: r.observed_away_team,
                observed_match_date: r.observed_match_date,
                observed_competition: r.observed_competition,
                evidence_source: 'adg8_source_controlled_reuse',
            });
        }
    }
    return map;
}

function buildSourcePageUrlMap(proposal = {}, enrichedArtifact = {}) {
    const map = new Map();
    // Prefer enriched targets (they have source_page_url)
    for (const t of enrichedArtifact.enriched_targets || []) {
        if (t.schedule_external_id) {
            map.set(String(t.schedule_external_id), {
                source_page_url: t.source_page_url,
                expected_home_team: t.schedule_home_team,
                expected_away_team: t.schedule_away_team,
                expected_match_date: t.schedule_date,
                expected_competition: null,
                match_id: t.match_id,
            });
        }
    }
    // Fill gaps from proposal
    for (const t of proposal.candidate_targets || []) {
        if (t.external_id && !map.has(String(t.external_id))) {
            map.set(String(t.external_id), {
                source_page_url: t.source_url || t.source_page_url,
                expected_home_team: t.schedule_home_team || t.home_team,
                expected_away_team: t.schedule_away_team || t.away_team,
                expected_match_date: t.schedule_date || t.match_date || t.kickoff_time,
                expected_competition: t.league_name,
                match_id: t.match_id,
            });
        }
    }
    // Add positive control manually
    map.set('4813735', {
        source_page_url: '/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735',
        expected_home_team: 'AFC Bournemouth',
        expected_away_team: 'Manchester City',
        expected_match_date: '2026-05-19T18:30:00.000Z',
        expected_competition: 'Premier League',
        match_id: '55_20252026_4813735',
    });
    return map;
}

function isSuspended(plan = {}, externalId) {
    const suspended = plan.planned_target_groups?.suspended_preservation_controls?.external_ids || [];
    return suspended.includes(externalId);
}

async function acquireSample(externalId, expectedData, existingEvidence, isSuspendedFlag) {
    const base = {
        schedule_external_id: externalId,
        expected_home_team: expectedData.expected_home_team,
        expected_away_team: expectedData.expected_away_team,
        expected_match_date: expectedData.expected_match_date,
        expected_competition: expectedData.expected_competition,
        match_id: expectedData.match_id || null,
        is_suspended_reference: isSuspendedFlag,
    };

    // Suspended: no fetch, just mark
    if (isSuspendedFlag) {
        return {
            ...base,
            evidence_acquisition_status: 'suspended_control_not_fetched',
            evidence_source: 'none_suspended_preservation',
            observed_detail_id: null,
            observed_home_team: null,
            observed_away_team: null,
            observed_match_date: null,
            observed_competition: null,
            page_http_status: null,
            anti_bot_signs: null,
            fetched: false,
            strict_guard_classification: 'suspended_control_still_blocked',
            strict_guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
            raw_write_execution_ready: false,
        };
    }

    // Reuse existing evidence
    if (existingEvidence) {
        const guardResult = validateStrictFixtureIdentity({
            schedule_external_id: externalId,
            detail_external_id_candidate: externalId,
            expected_home_team: base.expected_home_team,
            expected_away_team: base.expected_away_team,
            expected_match_date: base.expected_match_date,
            expected_competition: base.expected_competition,
            observed_detail_id: existingEvidence.observed_detail_id,
            observed_home_team: existingEvidence.observed_home_team,
            observed_away_team: existingEvidence.observed_away_team,
            observed_match_date: existingEvidence.observed_match_date,
            observed_competition: existingEvidence.observed_competition,
        });
        return {
            ...base,
            evidence_acquisition_status: 'evidence_reused_from_existing_source',
            evidence_source: existingEvidence.evidence_source,
            observed_detail_id: existingEvidence.observed_detail_id,
            observed_home_team: existingEvidence.observed_home_team,
            observed_away_team: existingEvidence.observed_away_team,
            observed_match_date: existingEvidence.observed_match_date,
            observed_competition: existingEvidence.observed_competition,
            page_http_status: null,
            anti_bot_signs: null,
            fetched: false,
            strict_guard_classification: guardResult.audit_classification,
            strict_guard_status: guardResult.fixture_identity_guard_status,
            date_delta_days: guardResult.date_delta_days,
            home_away_orientation: guardResult.home_away_orientation_status,
            raw_write_execution_ready: false,
        };
    }

    // Build URL
    const pagePath = expectedData.source_page_url || `/matches/unknown#${externalId}`;
    const url = pagePath.startsWith('http') ? pagePath : `${FOTMOB_BASE}${pagePath}`;

    // Fetch
    const { httpStatus, html, error } = await fetchPage(url);

    if (httpStatus !== 200 || !html) {
        return {
            ...base,
            evidence_acquisition_status: httpStatus === 0 ? 'network_unavailable_or_transient' : `http_${httpStatus}`,
            evidence_source: 'fetch_attempted_failed',
            observed_detail_id: null,
            observed_home_team: null,
            observed_away_team: null,
            observed_match_date: null,
            observed_competition: null,
            page_http_status: httpStatus || 0,
            anti_bot_signs: null,
            fetch_error: error || null,
            fetched: true,
            strict_guard_classification: 'insufficient_safe_evidence',
            strict_guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
            raw_write_execution_ready: false,
            full_response_saved: false,
        };
    }

    // Anti-bot check
    const antiBot = detectAntiBot(html);
    if (antiBot) {
        return {
            ...base,
            evidence_acquisition_status: 'anti_bot_or_access_block',
            evidence_source: 'fetch_blocked',
            observed_detail_id: null,
            observed_home_team: null,
            observed_away_team: null,
            observed_match_date: null,
            observed_competition: null,
            page_http_status: httpStatus,
            anti_bot_signs: antiBot,
            fetched: true,
            strict_guard_classification: 'anti_bot_or_access_block',
            strict_guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
            raw_write_execution_ready: false,
            full_response_saved: false,
            html_length: html.length,
        };
    }

    // Extract safe metadata only (never save full HTML)
    const parsed = extractFromHtml(html);
    const safeMeta = extractSafeMetadata(parsed);

    if (!safeMeta || !safeMeta.safe_identity_marker_present) {
        return {
            ...base,
            evidence_acquisition_status: safeMeta?.hydration_marker_present
                ? 'hydration_marker_present_identity_missing'
                : 'page_route_available_but_identity_not_observed',
            evidence_source: 'fetch_attempted_insufficient',
            observed_detail_id: safeMeta?.observed_detail_id || null,
            observed_home_team: safeMeta?.observed_home_team || null,
            observed_away_team: safeMeta?.observed_away_team || null,
            observed_match_date: safeMeta?.observed_match_date || null,
            observed_competition: safeMeta?.observed_competition || null,
            page_http_status: httpStatus,
            hydration_marker_present: safeMeta?.hydration_marker_present || false,
            safe_identity_marker_present: false,
            anti_bot_signs: null,
            fetched: true,
            strict_guard_classification: 'insufficient_safe_evidence',
            strict_guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
            raw_write_execution_ready: false,
            full_response_saved: false,
            html_length: html.length,
        };
    }

    // Run strict guard
    const guardResult = validateStrictFixtureIdentity({
        schedule_external_id: externalId,
        detail_external_id_candidate: externalId,
        expected_home_team: base.expected_home_team,
        expected_away_team: base.expected_away_team,
        expected_match_date: base.expected_match_date,
        expected_competition: base.expected_competition,
        observed_detail_id: safeMeta.observed_detail_id,
        observed_home_team: safeMeta.observed_home_team,
        observed_away_team: safeMeta.observed_away_team,
        observed_match_date: safeMeta.observed_match_date,
        observed_competition: safeMeta.observed_competition,
    });

    // html is now discarded from memory (eligible for GC) — never saved to disk
    return {
        ...base,
        evidence_acquisition_status: 'observed_identity_acquired',
        evidence_source: 'batch_a_public_page_route_acquisition',
        observed_detail_id: safeMeta.observed_detail_id,
        observed_home_team: safeMeta.observed_home_team,
        observed_away_team: safeMeta.observed_away_team,
        observed_match_date: safeMeta.observed_match_date,
        observed_competition: safeMeta.observed_competition,
        page_http_status: httpStatus,
        hydration_marker_present: safeMeta.hydration_marker_present,
        safe_identity_marker_present: safeMeta.safe_identity_marker_present,
        anti_bot_signs: null,
        fetched: true,
        strict_guard_classification: guardResult.audit_classification,
        strict_guard_status: guardResult.fixture_identity_guard_status,
        date_delta_days: guardResult.date_delta_days,
        home_away_orientation: guardResult.home_away_orientation_status,
        raw_write_execution_ready: false,
        full_response_saved: false,
        html_length: html.length,
    };
}

async function executeBatchA(deps = {}) {
    const plan = deps.plan || readJsonFile(ADG11_PLAN_PATH);
    const adg8Result = deps.adg8Result || readJsonFile(ADG8_RESULT_PATH);
    const proposal = deps.proposal || readJsonFile(PROPOSAL_PATH);
    const enrichedArtifact = deps.enrichedArtifact || readJsonFile(ENRICHED_TARGETS_PATH);

    const existingMap = buildExistingEvidenceMap(adg8Result);
    const urlMap = buildSourcePageUrlMap(proposal, enrichedArtifact);

    const results = [];
    let requestAttemptCount = 0;
    let evidenceReuseCount = 0;

    for (let i = 0; i < BATCH_A_IDS.length; i++) {
        const externalId = BATCH_A_IDS[i];
        const expectedData = urlMap.get(externalId) || {};
        const existingEvidence = existingMap.get(externalId) || null;
        const suspendedFlag = isSuspended(plan, externalId);

        const result = await acquireSample(externalId, expectedData, existingEvidence, suspendedFlag);
        results.push(result);

        if (result.fetched) requestAttemptCount++;
        if (result.evidence_source?.includes('reuse')) evidenceReuseCount++;

        // Delay between requests (skip after last)
        if (i < BATCH_A_IDS.length - 1 && result.fetched) {
            const delay = randomDelayMs(DELAY_MS_MIN, DELAY_MS_MAX);
            process.stdout.write(`  [delay ${delay}ms after ${externalId}]\n`);
            await sleep(delay);
        }
    }

    return { results, requestAttemptCount, evidenceReuseCount };
}

function countBy(list, pred) {
    return list.filter(pred).length;
}

async function buildArtifact(deps = {}) {
    const generatedAt = deps.generatedAt || new Date().toISOString();
    const { results, requestAttemptCount, evidenceReuseCount } = await executeBatchA(deps);

    const s = {
        batch_sample_count: results.length,
        positive_control_count: countBy(results, r => r.schedule_external_id === '4813735'),
        missing_observed_target_count: countBy(results, r =>
            ['4830467','4830468','4830469','4830470','4830471'].includes(r.schedule_external_id)),
        known_reverse_control_count: countBy(results, r =>
            ['4830458','4830464'].includes(r.schedule_external_id)),
        suspended_control_count: countBy(results, r => r.is_suspended_reference),
        request_attempt_count: requestAttemptCount,
        evidence_reuse_count: evidenceReuseCount,
        observed_identity_acquired_count: countBy(results, r =>
            r.evidence_acquisition_status === 'observed_identity_acquired'),
        observed_identity_missing_count: countBy(results, r =>
            r.evidence_acquisition_status.includes('missing') || r.evidence_acquisition_status.includes('insufficient')),
        strict_guard_passed_no_write_count: countBy(results, r =>
            r.strict_guard_status === FIXTURE_IDENTITY_GUARD_PASSED),
        strict_guard_blocked_count: countBy(results, r =>
            r.strict_guard_status === FIXTURE_IDENTITY_GUARD_BLOCKED),
        reverse_fixture_mapping_error_count: countBy(results, r =>
            r.strict_guard_classification === 'reverse_fixture_mapping_error'),
        suspended_control_still_blocked_count: countBy(results, r =>
            r.strict_guard_classification === 'suspended_control_still_blocked'),
        anti_bot_or_access_block_count: countBy(results, r =>
            r.strict_guard_classification === 'anti_bot_or_access_block'),
        network_unavailable_or_transient_count: countBy(results, r =>
            r.evidence_acquisition_status === 'network_unavailable_or_transient'),
        insufficient_safe_evidence_count: countBy(results, r =>
            r.strict_guard_classification === 'insufficient_safe_evidence'),
        raw_write_ready_count: 0,
        re_acceptance_candidate_count: 0,
    };

    const recommended = s.observed_identity_acquired_count >= 3
        ? 'batch_a_successful_acquisition; plan_batch_b_or_no_write_acceptance_review; do not raw write'
        : s.anti_bot_or_access_block_count > 0
            ? 'access_blocks_detected; recommend_alternative_evidence_strategy; do not raw write; do not bypass'
            : 'insufficient_evidence_acquired; recommend_evidence_strategy_review; do not raw write';

    return {
        schema_version: 'fotmob_observed_identity_evidence_acquisition_result_adg12_v1',
        phase: PHASE,
        generated_at: generatedAt,
        adg12_execution_status: STATUS,
        evidence_acquisition_performed: true,
        batch_id: 'ADG12_BATCH_A',
        no_browser_automation: true,
        no_direct_api_probing: true,
        no_proxy_bypass: true,
        no_captcha_bypass: true,
        no_access_control_bypass: true,
        no_uncontrolled_retry: true,
        no_db_write: true,
        no_raw_write: true,
        no_raw_match_data_insert: true,
        no_re_acceptance: true,
        no_suspension_reversal: true,
        source_inventory_mutation_performed: false,
        candidate_mutation_performed: false,
        full_body_saved: false,
        full_payload_saved: false,
        full_response_saved: false,
        ...s,
        recommended_next_step: recommended,
        batch_results: results,
    };
}

function buildReport(artifact = {}) {
    const lines = [
        '# FotMob Observed Identity Evidence Acquisition Result ADG12',
        '',
        `- Phase: ${artifact.phase}`,
        `- Status: ${artifact.adg12_execution_status}`,
        `- Batch: ${artifact.batch_id}`,
        `- evidence_acquisition_performed=true`,
        '',
        '## Batch A Results',
        '',
        '| external_id | status | observed_id | home vs away | guard | delta |',
        '| --- | --- | --- | --- | --- | --- |',
    ];
    for (const r of artifact.batch_results || []) {
        const teams = `${r.observed_home_team || '?'} vs ${r.observed_away_team || '?'}`;
        lines.push(`| ${r.schedule_external_id} | ${r.evidence_acquisition_status} | ${r.observed_detail_id || 'null'} | ${teams} | ${r.strict_guard_classification} | ${r.date_delta_days ?? 'null'} |`);
    }
    lines.push(
        '',
        '## Counts',
        '',
        `| Metric | Count |`,
        `| --- | --- |`,
        `| batch_sample_count | ${artifact.batch_sample_count} |`,
        `| positive_control | ${artifact.positive_control_count} |`,
        `| missing_observed_targets | ${artifact.missing_observed_target_count} |`,
        `| known_reverse_controls | ${artifact.known_reverse_control_count} |`,
        `| suspended_control | ${artifact.suspended_control_count} |`,
        `| request_attempts | ${artifact.request_attempt_count} |`,
        `| evidence_reuse | ${artifact.evidence_reuse_count} |`,
        `| observed_identity_acquired | ${artifact.observed_identity_acquired_count} |`,
        `| strict_guard_passed_no_write | ${artifact.strict_guard_passed_no_write_count} |`,
        `| strict_guard_blocked | ${artifact.strict_guard_blocked_count} |`,
        `| reverse_fixture_error | ${artifact.reverse_fixture_mapping_error_count} |`,
        `| suspended_still_blocked | ${artifact.suspended_control_still_blocked_count} |`,
        `| raw_write_ready | ${artifact.raw_write_ready_count} |`,
        '',
        '## Safety',
        '',
        '- no browser automation',
        '- no direct API probing',
        '- no proxy/captcha/access-control bypass',
        '- no DB writes / raw writes / raw_match_data inserts',
        '- no re-acceptance / suspension reversal',
        '- no full HTML/pageProps/raw_data saved to disk',
        '- no source inventory mutation / candidate mutation',
        '- raw_write_ready_count=0',
        '',
        `## Recommended Next Step`,
        '',
        artifact.recommended_next_step
    );
    return `${lines.join('\n')}\n`;
}

async function main() {
    process.stdout.write('ADG12 Batch A: bounded observed identity evidence acquisition\n');
    process.stdout.write(`Samples: ${BATCH_A_IDS.join(', ')}\n\n`);

    const artifact = await buildArtifact();
    writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
    writeTextFile(REPORT_OUTPUT_PATH, buildReport(artifact));

    process.stdout.write('\nDone.\n');
    return { status: 0 };
}

module.exports = { PHASE, STATUS, BATCH_A_IDS, fetchPage, extractSafeMetadata, detectAntiBot, acquireSample,
    executeBatchA, buildArtifact, buildReport, main };

if (require.main === module) {
    main().then(r => { process.exitCode = r.status; }).catch(e => {
        process.stderr.write(`${e.stack || e.message}\n`);
        process.exitCode = 1;
    });
}
