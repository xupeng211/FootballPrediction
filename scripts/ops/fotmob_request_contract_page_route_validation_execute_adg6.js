#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const { extractFromHtml, validateNextDataStructure } = require('../../src/parsers/fotmob/NextDataParser');
const {
    normalizePageUrlBase,
    reconcileRouteIdentity,
    REVERSE_FIXTURE_DETECTED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG6';
const STATUS = 'completed_bounded_request_contract_page_route_validation_execution';
const PLAN_MANIFEST_PATH = 'docs/_manifests/fotmob_request_contract_page_route_validation_plan.adg5.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_request_contract_page_route_validation_result.adg6.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_REQUEST_CONTRACT_PAGE_ROUTE_VALIDATION_RESULT_ADG6.md';
const CLASSIFICATIONS = Object.freeze([
    'page_route_identity_validated',
    'page_route_available_but_identity_not_observed',
    'direct_api_request_contract_blocked',
    'request_contract_headers_session_locale_required',
    'anti_bot_or_access_block',
    'redirect_or_locale_mismatch',
    'hydration_marker_missing',
    'identity_mismatch',
    'reverse_fixture_or_home_away_inversion',
    'suspended_reference_blocked',
    'insufficient_safe_evidence',
    'network_unavailable_or_transient',
]);
const REQUEST_TIMEOUT_MS = 20000;
const BLOCK_MARKERS = Object.freeze([
    ['captcha', /captcha|verify you are human|human verification/i],
    ['cloudflare', /cloudflare|cf-chl|attention required|just a moment/i],
    ['rate_limit', /rate limit|too many requests/i],
    ['access_wall', /access denied|request blocked|forbidden/i],
]);
const POSITIVE_SAMPLE_OUTPUT_ID = 'positive_bournemouth_mancity_4813735';

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

function normalizeText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function sha256Text(value) {
    return crypto
        .createHash('sha256')
        .update(String(value ?? ''))
        .digest('hex');
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        writeFiles: true,
        timeoutMs: REQUEST_TIMEOUT_MS,
        help: false,
        unknown: [],
    };
    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const key = arg.replace(/^--/, '').split('=')[0];
        const value = arg.includes('=')
            ? arg.slice(arg.indexOf('=') + 1)
            : argv[index + 1] && !String(argv[index + 1]).startsWith('--')
              ? argv[++index]
              : true;
        if (key === 'help' || key === 'h') {
            options.help = true;
            continue;
        }
        if (key === 'write-files' || key === 'write_files') {
            options.writeFiles = !['0', 'false', 'no'].includes(String(value).trim().toLowerCase());
            continue;
        }
        if (key === 'timeout-ms' || key === 'timeout_ms') {
            options.timeoutMs = Number.parseInt(String(value), 10);
            continue;
        }
        options.unknown.push(key);
    }
    return options;
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (options.unknown?.length) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) {
        errors.push('timeoutMs must be a positive integer');
    }
    return { ok: errors.length === 0, errors };
}

function buildSamples(plan = {}) {
    const planned = plan.planned_samples || {};
    return [
        planned.positive_sample,
        ...(planned.request_contract_validation_required_samples || []),
        ...(planned.suspended_reference_samples || []),
    ].filter(Boolean);
}

function normalizeOutputSampleId(sample = {}) {
    if (sample.sample_group === 'positive_sample') {
        return POSITIVE_SAMPLE_OUTPUT_ID;
    }
    return sample.sample_id;
}

function detectAntiBotSigns(body = '', response = {}) {
    const signs = [];
    const contentType = normalizeText(response.headers?.get?.('content-type')) || '';
    if (/text\/html/i.test(contentType) === false) {
        signs.push('unexpected_content_type');
    }
    for (const [name, pattern] of BLOCK_MARKERS) {
        if (pattern.test(body)) {
            signs.push(name);
        }
    }
    return [...new Set(signs)];
}

async function fetchPageRoute(url, { timeoutMs = REQUEST_TIMEOUT_MS, fetchFn = globalThis.fetch } = {}) {
    if (typeof fetchFn !== 'function') {
        throw new Error('FETCH_DEPENDENCY_MISSING');
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetchFn(url, {
            method: 'GET',
            redirect: 'follow',
            signal: controller.signal,
            headers: {
                accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'identity',
                'cache-control': 'no-cache',
                pragma: 'no-cache',
                'user-agent':
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            },
        });
        const body = await response.text();
        return {
            ok: response.ok === true,
            request_url: url,
            final_url: response.url || url,
            http_status: Number(response.status) || 0,
            content_type: response.headers?.get?.('content-type') || null,
            body_byte_length: Buffer.byteLength(body, 'utf8'),
            body_sha256: sha256Text(body),
            body,
        };
    } finally {
        clearTimeout(timer);
    }
}

function safeObservedDate(pageProps = {}) {
    return (
        normalizeText(pageProps?.general?.matchTimeUTC) ||
        normalizeText(pageProps?.general?.matchDate) ||
        normalizeText(pageProps?.header?.status?.utcTime) ||
        null
    );
}

function safeObservedTeams(pageProps = {}) {
    const teams = Array.isArray(pageProps?.header?.teams) ? pageProps.header.teams : [];
    const general = pageProps?.general || {};
    const home =
        normalizeText(general?.homeTeam?.name) ||
        normalizeText(general?.homeTeam) ||
        normalizeText(teams[0]?.name) ||
        null;
    const away =
        normalizeText(general?.awayTeam?.name) ||
        normalizeText(general?.awayTeam) ||
        normalizeText(teams[1]?.name) ||
        null;
    return { home, away };
}

function normalizeTeam(value) {
    return String(value ?? '')
        .trim()
        .toLowerCase()
        .replace(/\s+/g, ' ');
}

function summarizeRedirect(sample = {}, fetchResult = {}) {
    const requested = normalizeText(sample.page_route_url_without_fragment);
    const finalUrl = normalizeText(fetchResult.final_url);
    if (!requested || !finalUrl) return 'unavailable';
    if (requested === finalUrl) return 'none';
    try {
        const requestedUrl = new URL(requested);
        const final = new URL(finalUrl);
        const parts = [];
        if (requestedUrl.origin !== final.origin) parts.push('origin_changed');
        if (requestedUrl.pathname !== final.pathname) parts.push('path_changed');
        if (requestedUrl.pathname.split('/')[1] !== final.pathname.split('/')[1]) {
            parts.push('locale_or_prefix_changed');
        }
        return parts.length > 0 ? parts.join(',') : 'changed';
    } catch {
        return 'changed';
    }
}

function buildObservedIdentityContext(sample = {}, fetchResult = {}, pageProps = null) {
    const observedId = normalizeText(pageProps?.general?.matchId || pageProps?.matchId || pageProps?.match_id);
    const observedTeams = safeObservedTeams(pageProps);
    const observedDate = safeObservedDate(pageProps);
    const expectedDateKnown = Boolean(normalizeText(sample.expected_match_date));
    const expectedHome = normalizeTeam(sample.expected_home_team);
    const expectedAway = normalizeTeam(sample.expected_away_team);
    const observedHome = normalizeTeam(observedTeams.home);
    const observedAway = normalizeTeam(observedTeams.away);
    const teamOrderMatches = Boolean(
        expectedHome &&
            expectedAway &&
            observedHome &&
            observedAway &&
            expectedHome === observedHome &&
            expectedAway === observedAway
    );
    const reconciliation = reconcileRouteIdentity({
        target: {
            source_page_url: sample.source_page_url,
            source_page_url_base: normalizePageUrlBase(sample.page_route_url_without_fragment),
            page_url_base: normalizePageUrlBase(sample.page_route_url_without_fragment),
            home_team: sample.expected_home_team,
            away_team: sample.expected_away_team,
            match_date: sample.expected_match_date,
            season: sample.expected_competition === 'Ligue 1' ? '2025/2026' : null,
            status: null,
            external_id: sample.detail_external_id_candidate,
            schedule_external_id: sample.source_url_fragment_external_id,
            accepted_detail_external_id: sample.detail_external_id_candidate,
            recapture_expected_identity: sample.detail_external_id_candidate,
        },
        observedPayload: {
            general: {
                matchId: observedId,
                homeTeam: observedTeams.home,
                awayTeam: observedTeams.away,
                matchTimeUTC: observedDate,
                pageUrl: normalizePageUrlBase(fetchResult.final_url),
            },
            header: {
                teams: [{ name: observedTeams.home }, { name: observedTeams.away }],
                status: {
                    utcTime: observedDate,
                },
            },
        },
        finalUrl: fetchResult.final_url,
    });
    return {
        observedId,
        observedTeams,
        observedDate,
        expectedDateKnown,
        teamOrderMatches,
        reconciliation,
    };
}

function classifyPreParseSample({ fetchResult = {}, antiBotSigns = [], parseResult = null, requestContractStatus, redirectSummary }) {
    if (fetchResult.network_error === true) {
        return {
            validation_classification: 'network_unavailable_or_transient',
            requestContractStatus,
            redirectSummary,
        };
    }
    if ([401, 403, 429].includes(fetchResult.http_status) || antiBotSigns.length > 0) {
        return { validation_classification: 'anti_bot_or_access_block', requestContractStatus, redirectSummary };
    }
    if (redirectSummary !== 'none' && redirectSummary !== 'unavailable') {
        return { validation_classification: 'redirect_or_locale_mismatch', requestContractStatus, redirectSummary };
    }
    if (!parseResult?.success) {
        return {
            validation_classification:
                parseResult?.error === 'NO_NEXT_DATA'
                    ? 'hydration_marker_missing'
                    : 'page_route_available_but_identity_not_observed',
            requestContractStatus,
            redirectSummary,
        };
    }
    return null;
}

function classifySuspendedReference(reconciliation, requestContractStatus, redirectSummary) {
    return {
        validation_classification: 'suspended_reference_blocked',
        requestContractStatus,
        redirectSummary,
        reference_page_identity_validated:
            reconciliation.schedule_external_id_vs_detail_external_id_status === 'identity_match' &&
            reconciliation.team_date_status_match_status === 'compatible',
    };
}

function classifyValidatedOrBlockedIdentity({
    sample,
    observedId,
    expectedDateKnown,
    teamOrderMatches,
    reconciliation,
    requestContractStatus,
    redirectSummary,
}) {
    if (
        observedId === normalizeText(sample.detail_external_id_candidate) &&
        teamOrderMatches === true &&
        expectedDateKnown === false
    ) {
        return {
            validation_classification: 'page_route_identity_validated',
            requestContractStatus,
            redirectSummary,
        };
    }
    if (reconciliation.reverse_fixture_detected === true) {
        return {
            validation_classification: 'reverse_fixture_or_home_away_inversion',
            requestContractStatus,
            redirectSummary,
        };
    }
    if (reconciliation.schedule_external_id_vs_detail_external_id_status === 'requested_vs_observed_external_id_mismatch') {
        return {
            validation_classification: 'identity_mismatch',
            requestContractStatus,
            redirectSummary,
        };
    }
    if (
        reconciliation.schedule_external_id_vs_detail_external_id_status === 'identity_match' &&
        reconciliation.team_date_status_match_status === 'compatible'
    ) {
        return {
            validation_classification: 'page_route_identity_validated',
            requestContractStatus,
            redirectSummary,
        };
    }
    if (reconciliation.page_url_base_match_status === 'match' && observedId) {
        return {
            validation_classification: 'page_route_available_but_identity_not_observed',
            requestContractStatus,
            redirectSummary,
        };
    }
    return { validation_classification: 'insufficient_safe_evidence', requestContractStatus, redirectSummary };
}

function classifySample({ sample = {}, fetchResult = {}, antiBotSigns = [], parseResult = null, pageProps = null }) {
    const requestContractStatus = 'direct_api_request_contract_blocked';
    const redirectSummary = summarizeRedirect(sample, fetchResult);
    const preParseClassification = classifyPreParseSample({
        fetchResult,
        antiBotSigns,
        parseResult,
        requestContractStatus,
        redirectSummary,
    });
    if (preParseClassification) {
        return preParseClassification;
    }
    if (!pageProps) {
        return { validation_classification: 'insufficient_safe_evidence', requestContractStatus, redirectSummary };
    }

    const { observedId, expectedDateKnown, teamOrderMatches, reconciliation } = buildObservedIdentityContext(
        sample,
        fetchResult,
        pageProps
    );

    if (sample.sample_group === 'suspended_reference') {
        return classifySuspendedReference(reconciliation, requestContractStatus, redirectSummary);
    }

    return classifyValidatedOrBlockedIdentity({
        sample,
        observedId,
        expectedDateKnown,
        teamOrderMatches,
        reconciliation,
        requestContractStatus,
        redirectSummary,
    });
}

async function executeSample(sample = {}, options = {}, dependencies = {}) {
    const baseRecord = {
        sample_id: normalizeOutputSampleId(sample),
        sample_group: sample.sample_group,
        source_page_url: sample.source_page_url,
        source_url_path_slug: sample.source_url_path_slug,
        source_url_fragment_external_id: sample.source_url_fragment_external_id,
        detail_external_id_candidate: sample.detail_external_id_candidate,
        detail_identity_source: sample.detail_identity_source,
        expected_home_team: sample.expected_home_team,
        expected_away_team: sample.expected_away_team,
        expected_match_date: sample.expected_match_date,
        expected_competition: sample.expected_competition,
        page_route_url_without_fragment: sample.page_route_url_without_fragment,
        no_full_body_saved: true,
        no_db_write: true,
        no_raw_write: true,
    };

    let fetchResult;
    try {
        fetchResult = await fetchPageRoute(sample.page_route_url_without_fragment, {
            timeoutMs: options.timeoutMs,
            fetchFn: dependencies.fetchFn,
        });
    } catch (error) {
        return {
            ...baseRecord,
            page_http_status: null,
            page_content_type: null,
            redirect_summary: 'unavailable',
            hydration_marker_present: false,
            safe_identity_marker_present: false,
            observed_detail_id_if_safely_available: null,
            observed_home_team_if_safely_available: null,
            observed_away_team_if_safely_available: null,
            observed_date_if_safely_available: null,
            anti_bot_signs: [],
            request_contract_status: 'direct_api_request_contract_blocked',
            validation_classification: 'network_unavailable_or_transient',
            network_error: error.message,
            body_sha256: null,
            body_byte_length: 0,
        };
    }

    const antiBotSigns = detectAntiBotSigns(fetchResult.body, {
        headers: {
            get: () => fetchResult.content_type,
        },
    });
    const parseResult =
        antiBotSigns.length > 0 || fetchResult.http_status >= 400 ? null : extractFromHtml(fetchResult.body);
    const pageProps =
        parseResult?.success === true && validateNextDataStructure(parseResult.data).valid
            ? parseResult.data.props.pageProps
            : null;
    const observedTeams = pageProps ? safeObservedTeams(pageProps) : { home: null, away: null };
    const observedId =
        pageProps && normalizeText(pageProps?.general?.matchId || pageProps?.matchId || pageProps?.match_id);
    const observedDate = pageProps ? safeObservedDate(pageProps) : null;
    const classification = classifySample({
        sample,
        fetchResult,
        antiBotSigns,
        parseResult,
        pageProps,
    });
    return {
        ...baseRecord,
        page_http_status: fetchResult.http_status,
        page_content_type: fetchResult.content_type,
        redirect_summary: classification.redirectSummary,
        hydration_marker_present: Boolean(parseResult?.success === true),
        safe_identity_marker_present: Boolean(observedId || observedTeams.home || observedTeams.away || observedDate),
        observed_detail_id_if_safely_available: observedId,
        observed_home_team_if_safely_available: observedTeams.home,
        observed_away_team_if_safely_available: observedTeams.away,
        observed_date_if_safely_available: observedDate,
        anti_bot_signs: antiBotSigns,
        request_contract_status: classification.requestContractStatus,
        validation_classification: classification.validation_classification,
        reference_page_identity_validated: classification.reference_page_identity_validated === true,
        body_sha256: fetchResult.body_sha256,
        body_byte_length: fetchResult.body_byte_length,
    };
}

function buildSummary(sampleResults = []) {
    const count = classification =>
        sampleResults.filter(item => item.validation_classification === classification).length;
    return {
        page_route_identity_validated_count: count('page_route_identity_validated'),
        page_route_available_but_identity_not_observed_count: count('page_route_available_but_identity_not_observed'),
        anti_bot_or_access_block_count: count('anti_bot_or_access_block'),
        request_contract_headers_session_locale_required_count: count(
            'request_contract_headers_session_locale_required'
        ),
        redirect_or_locale_mismatch_count: count('redirect_or_locale_mismatch'),
        hydration_marker_missing_count: count('hydration_marker_missing'),
        identity_mismatch_count: count('identity_mismatch'),
        suspended_reference_blocked_count: count('suspended_reference_blocked'),
        insufficient_safe_evidence_count: count('insufficient_safe_evidence'),
        network_unavailable_or_transient_count: count('network_unavailable_or_transient'),
        reverse_fixture_or_home_away_inversion_count: count('reverse_fixture_or_home_away_inversion'),
    };
}

function buildRecommendedNextStep(summary = {}) {
    if (summary.page_route_identity_validated_count >= 4) {
        return 'bounded no-write page-route recapture planning';
    }
    if (summary.anti_bot_or_access_block_count >= 4) {
        return 'request-contract review / source strategy decision';
    }
    if (
        summary.page_route_available_but_identity_not_observed_count >= 3 ||
        summary.insufficient_safe_evidence_count >= 3
    ) {
        return 'safe identity marker extraction implementation planning';
    }
    if (summary.identity_mismatch_count > 0 || summary.reverse_fixture_or_home_away_inversion_count > 0) {
        return 'identity mapping correction / source inventory audit';
    }
    return 'bounded no-write page-route recapture planning';
}

function buildArtifact(plan = {}, sampleResults = [], generatedAt = new Date().toISOString()) {
    const summary = buildSummary(sampleResults);
    return {
        schema_version: 'fotmob_request_contract_page_route_validation_result_adg6_v1',
        phase: PHASE,
        generated_at: generatedAt,
        artifact_status: STATUS,
        adg6_execution_status: STATUS,
        validation_execution_performed: true,
        validation_scope: 'bounded_request_contract_page_route_validation',
        positive_sample_executed: sampleResults.some(item => item.sample_group === 'positive_sample'),
        planned_42_target_sample_count: plan.planned_42_target_sample_count,
        executed_42_target_sample_count: sampleResults.filter(
            item => item.sample_group === 'request_contract_validation_required'
        ).length,
        planned_suspended_reference_sample_count: plan.planned_suspended_reference_sample_count,
        executed_suspended_reference_sample_count: sampleResults.filter(
            item => item.sample_group === 'suspended_reference'
        ).length,
        ...summary,
        direct_api_request_contract_blocked: true,
        raw_write_ready_count: 0,
        re_acceptance_candidate_count: 0,
        db_write_performed: false,
        raw_write_execution_performed: false,
        full_body_saved: false,
        full_payload_saved: false,
        browser_automation_performed: false,
        network_request_performed: true,
        samples: sampleResults,
        recommended_next_step: buildRecommendedNextStep(summary),
        classifications: CLASSIFICATIONS,
    };
}

function buildReport(artifact = {}) {
    const lines = [
        '# FotMob Request-Contract / Page-Route Validation Result ADG6',
        '',
        `- Phase: ${artifact.phase}`,
        `- Status: ${artifact.artifact_status}`,
        `- validation_execution_performed=${artifact.validation_execution_performed}`,
        `- positive_sample_executed=${artifact.positive_sample_executed}`,
        `- executed_42_target_sample_count=${artifact.executed_42_target_sample_count}`,
        `- executed_suspended_reference_sample_count=${artifact.executed_suspended_reference_sample_count}`,
        `- page_route_identity_validated_count=${artifact.page_route_identity_validated_count}`,
        `- anti_bot_or_access_block_count=${artifact.anti_bot_or_access_block_count}`,
        `- insufficient_safe_evidence_count=${artifact.insufficient_safe_evidence_count}`,
        `- identity_mismatch_count=${artifact.identity_mismatch_count}`,
        `- suspended_reference_blocked_count=${artifact.suspended_reference_blocked_count}`,
        `- direct_api_request_contract_blocked=${artifact.direct_api_request_contract_blocked}`,
        `- raw_write_ready_count=${artifact.raw_write_ready_count}`,
        `- db_write_performed=${artifact.db_write_performed}`,
        `- raw_write_execution_performed=${artifact.raw_write_execution_performed}`,
        `- full_body_saved=${artifact.full_body_saved}`,
        '',
        '## Sample Summary',
        '',
    ];
    for (const sample of artifact.samples || []) {
        lines.push(
            `- ${sample.sample_id}: ${sample.validation_classification}; http=${sample.page_http_status}; redirect=${sample.redirect_summary}; observed_detail_id=${sample.observed_detail_id_if_safely_available || 'null'}`
        );
    }
    lines.push('', `Recommended next step: ${artifact.recommended_next_step}`);
    return `${lines.join('\n')}\n`;
}

async function runFotmobRequestContractPageRouteValidationExecuteAdg6(options = {}, dependencies = {}) {
    const plan = dependencies.plan || readJsonFile(PLAN_MANIFEST_PATH);
    const samples = dependencies.samples || buildSamples(plan);
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const sampleResults = [];
    for (const sample of samples) {
        sampleResults.push(await executeSample(sample, options, dependencies));
    }
    const artifact = buildArtifact(plan, sampleResults, generatedAt);
    const report = buildReport(artifact);
    if (options.writeFiles !== false) {
        writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(REPORT_OUTPUT_PATH, report);
    }
    return { ok: true, artifact, report };
}

async function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        process.stdout.write(
            'Usage: node scripts/ops/fotmob_request_contract_page_route_validation_execute_adg6.js [--write-files=false] [--timeout-ms=20000]\n'
        );
        return { status: 0 };
    }
    const validation = validateCliOptions(options);
    if (!validation.ok) {
        process.stderr.write(`${validation.errors.join('\n')}\n`);
        return { status: 1 };
    }
    const result = await runFotmobRequestContractPageRouteValidationExecuteAdg6(options);
    process.stdout.write(
        `${JSON.stringify(
            {
                adg6_execution_status: result.artifact.artifact_status,
                validation_execution_performed: result.artifact.validation_execution_performed,
                page_route_identity_validated_count: result.artifact.page_route_identity_validated_count,
                anti_bot_or_access_block_count: result.artifact.anti_bot_or_access_block_count,
                insufficient_safe_evidence_count: result.artifact.insufficient_safe_evidence_count,
                raw_write_ready_count: result.artifact.raw_write_ready_count,
            },
            null,
            2
        )}\n`
    );
    return { status: 0 };
}

module.exports = {
    PHASE,
    STATUS,
    PLAN_MANIFEST_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    CLASSIFICATIONS,
    POSITIVE_SAMPLE_OUTPUT_ID,
    parseArgs,
    validateCliOptions,
    buildSamples,
    normalizeOutputSampleId,
    detectAntiBotSigns,
    fetchPageRoute,
    safeObservedDate,
    safeObservedTeams,
    summarizeRedirect,
    classifySample,
    executeSample,
    buildSummary,
    buildRecommendedNextStep,
    buildArtifact,
    buildReport,
    runFotmobRequestContractPageRouteValidationExecuteAdg6,
    main,
};

if (require.main === module) {
    main()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
