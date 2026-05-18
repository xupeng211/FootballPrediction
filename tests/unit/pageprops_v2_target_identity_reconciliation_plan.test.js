'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js');
const PREVIEW_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_preview.js');
const RAW_WRITE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const preview = require(PREVIEW_PATH);
const rawWrite = require(RAW_WRITE_PATH);

const MISMATCH_IDS = Object.freeze([
    '4830466',
    '4830461',
    '4830481',
    '4830496',
    '4830511',
    '4830463',
    '4830465',
    '4830508',
]);

const OBSERVED = Object.freeze({
    4830466: ['4830759', 'Marseille', 'Rennes', '2026-05-17T19:00:00.000Z'],
    4830461: ['4830758', 'Lyon', 'Lens', '2026-05-17T19:00:00.000Z'],
    4830481: ['4830763', 'Strasbourg', 'Monaco', '2026-05-17T19:00:00.000Z'],
    4830496: ['4830757', 'Lorient', 'Le Havre', '2026-05-17T19:00:00.000Z'],
    4830511: ['4830760', 'Nantes', 'Toulouse', '2026-05-17T19:00:00.000Z'],
    4830463: ['4830622', 'Le Havre', 'Monaco', '2026-01-24T18:00:00.000Z'],
    4830465: ['4830619', 'Toulouse', 'Nice', '2026-01-17T18:00:00.000Z'],
    4830508: ['4830620', 'Auxerre', 'Paris Saint-Germain', '2026-01-23T19:00:00.000Z'],
});

function fakePageProps(externalId, overrides = {}) {
    const observed = OBSERVED[externalId] || [
        externalId,
        `Home ${externalId}`,
        `Away ${externalId}`,
        '2025-08-15T18:45:00.000Z',
    ];
    return {
        content: {
            matchFacts: { infoBox: { Tournament: 'Ligue 1' } },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.2, 0.8] }] } } },
            DO_NOT_SAVE_FULL_PAGEPROPS: 'secret-marker',
        },
        fallback: false,
        general: {
            matchId: observed[0],
            leagueId: 53,
            matchName: `${observed[1]}-vs-${observed[2]}`,
            matchTimeUTCDate: observed[3],
        },
        header: { teams: [{ name: observed[1] }, { name: observed[2] }] },
        nav: { locale: 'en' },
        ongoing: false,
        seo: { eventJSONLD: { '@type': 'SportsEvent' } },
        ssr: true,
        translations: { ok: true },
        ...overrides,
    };
}

function fakeHtml(externalId, pageProps = fakePageProps(externalId)) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></body></html>`;
}

function fetchResultFor(requestedExternalId, pageProps = fakePageProps(requestedExternalId), overrides = {}) {
    const body = fakeHtml(requestedExternalId, pageProps);
    return {
        ok: overrides.ok ?? true,
        request_url: `https://www.fotmob.com/match/${requestedExternalId}`,
        final_url: overrides.final_url || `https://www.fotmob.com/match/${requestedExternalId}`,
        http_status: overrides.http_status ?? 200,
        content_type: 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: `body-sha-${requestedExternalId}`,
        body,
        error: overrides.error,
    };
}

function hashFor(externalId) {
    return preview.computeStablePagePropsHash(fakePageProps(externalId));
}

function candidate(externalId, overrides = {}) {
    return {
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${externalId}`,
        away_team: `Away ${externalId}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: hashFor(externalId),
        write_plan_status: 'eligible_for_insert',
        write_status: 'blocked_missing_matches_fk_prerequisite',
        write_execution_status: 'RECAPTURE_HASH_GATE_BLOCKED',
        matches_seed_status: 'inserted_matches_identity',
        failure_reason: 'blocked_missing_matches_fk_prerequisite',
        source_inventory_route: 'source_inventory',
        source_url: null,
        ...overrides,
    };
}

function candidates50() {
    const filler = Array.from({ length: 42 }, (_, index) => String(4900000 + index));
    return [...MISMATCH_IDS, ...filler].map(externalId => candidate(externalId));
}

function knownCompleted() {
    return ['4830746', '4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754'].map(externalId => ({
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        external_id: externalId,
        match_id: `53_20252026_${externalId}`,
    }));
}

function manifest(overrides = {}) {
    return {
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: { league_id: 53, league_name: 'Ligue 1', season: '2025/2026' },
        known_completed_targets: knownCompleted(),
        candidate_targets: candidates50(),
        phase_5_21_l2v3c_planning_status: 'completed_no_write',
        phase_5_21_l2v3c_metadata_target_mismatch_count: 8,
        next_required_step: 'target_identity_reconciliation_planning',
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution_blocked_review',
        renewed_baseline_requires_separate_baseline_acceptance: true,
        renewed_baseline_requires_separate_final_db_write_authorization: true,
        raw_write_retry_readiness_status: 'ready_for_renewed_authorization',
        raw_match_data_write_status: 'not_executed',
        matches_identity_seed_execution_status: 'completed',
        post_seed_matches_identity_verification_status: 'completed',
        raw_write_fk_prerequisite_status: 'satisfied',
        eligible_raw_insert_count: 50,
        expected_raw_match_data_after_retry: 68,
        ...overrides,
    };
}

function proposalTarget(externalId, overrides = {}) {
    const pageProps = fakePageProps(externalId);
    const observed = OBSERVED[externalId];
    return {
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        old_baseline_hash: hashFor(externalId),
        renewed_candidate_hash: preview.computeStablePagePropsHash(pageProps),
        hash_status: 'metadata_target_mismatch',
        repeated_hash_stability: 'stable_current_hash',
        metadata_identity_status: 'metadata_target_mismatch',
        attempts: [
            {
                attempt: 1,
                match_id: `53_20252026_${externalId}`,
                external_id: externalId,
                http_status: 200,
                parsed: true,
                stable_hash: preview.computeStablePagePropsHash(pageProps),
                metadata_identity_status: 'metadata_target_mismatch',
                metadata_identity_observed: {
                    external_id: observed?.[0] || externalId,
                    home_team: observed?.[1] || `Home ${externalId}`,
                    away_team: observed?.[2] || `Away ${externalId}`,
                    match_time_utc: observed?.[3] || '2025-08-15T18:45:00.000Z',
                },
            },
        ],
        ...overrides,
    };
}

function renewedProposal(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3C',
        proposal_status: 'renewed_baseline_review_required',
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        summary: {
            metadata_target_mismatch_count: 8,
            next_required_step: 'target_identity_reconciliation_planning',
        },
        recommendation: {
            raw_write_ready_for_execution: false,
            requires_human_review: true,
            requires_separate_baseline_acceptance: true,
            requires_separate_final_db_write_authorization: true,
        },
        checked_targets: MISMATCH_IDS.map(externalId => proposalTarget(externalId)),
        ...overrides,
    };
}

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        renewedProposal: mod.RENEWED_PROPOSAL_PATH,
        reportOutput: mod.REPORT_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        route: 'html_hydration',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        planningAuthorization: true,
        targetIdentityReconciliationAuthorization: true,
        networkAuthorization: true,
        matchDetailRecaptureAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowControlledWrite: false,
        allowMatchesWrite: false,
        allowBookmakerOddsWrite: false,
        allowFeatureWrite: false,
        allowSchemaMigration: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        printFullBody: false,
        saveFullBody: false,
        printFullJson: false,
        saveFullJson: false,
        printFullPageprops: false,
        saveFullPageprops: false,
        retry: 0,
        requestDelayMs: 0,
        generatedAt: '2026-05-18T00:00:00.000Z',
        baseHead: 'f5e718728e32a5a6f2d54d3795e172222c80f7cd',
        branch: 'data/pageprops-v2-target-identity-reconciliation-phase521l2v3d',
        mainHead: 'f5e718728e32a5a6f2d54d3795e172222c80f7cd',
        mainCiStatus: 'success',
        pr1276State: 'MERGED',
        pr1276MergeCommit: '0d371eb412cf3ee19a6f72adb57a41bb19298f82',
        pr1277State: 'MERGED',
        pr1277MergeCommit: 'f5e718728e32a5a6f2d54d3795e172222c80f7cd',
        pr1277RetargetResult: 'retargeted_to_main_before_merge',
        ...overrides,
    };
}

test('valid L2V3D run stays no-write and classifies unresolved identity mismatches', async () => {
    const writes = [];
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchHtmlFn: url => fetchResultFor(url.split('/').pop()),
        writeJsonFile: (filePath, data) => writes.push({ filePath, data }),
        writeReportFile: (filePath, data) => writes.push({ filePath, data }),
    });

    assert.equal(result.ok, true);
    assert.equal(result.summary.no_write, true);
    assert.equal(result.summary.db_write_performed, false);
    assert.equal(result.summary.raw_insert_performed, false);
    assert.equal(result.summary.baseline_acceptance_performed, false);
    assert.equal(result.summary.raw_write_retry_performed, false);
    assert.equal(result.summary.checked_target_count, 8);
    assert.equal(result.summary.identity_mismatch_count, 8);
    assert.equal(result.summary.mismatch_type_counts.requested_vs_observed_external_id_mismatch, 8);
    assert.equal(result.summary.request_url_itself_wrong, false);
    assert.equal(result.summary.deterministic_observed_identity_with_l2v3c, true);
    assert.equal(result.summary.raw_write_ready_for_execution, false);
    assert.equal(result.summary.requires_separate_baseline_acceptance, true);
    assert.equal(result.summary.requires_separate_final_db_write_authorization, true);
    assert.equal(result.updated_manifest.raw_write_ready_for_execution, false);
    assert.equal(result.updated_manifest.target_identity_mismatch_blocks_baseline_acceptance, true);
    assert.equal(writes.length, 2);
});

test('write, baseline acceptance and raw retry flags are blocked', () => {
    for (const [key, value] of [
        ['allowDbWrite', true],
        ['allowRawMatchDataWrite', true],
        ['allowControlledWrite', true],
        ['allowMatchesWrite', true],
        ['allowBookmakerOddsWrite', true],
        ['allowFeatureWrite', true],
        ['allowSchemaMigration', true],
        ['allowParserImplementation', true],
        ['allowFeatureExtraction', true],
        ['allowTraining', true],
        ['allowPrediction', true],
        ['allowBrowserRuntime', true],
        ['allowProxyRuntime', true],
        ['finalDbWriteConfirmation', true],
        ['executeWrite', true],
        ['commit', true],
        ['acceptBaseline', true],
        ['acceptedBaseline', true],
        ['baselineAcceptanceAuthorization', true],
        ['rawWriteReadyForExecution', true],
        ['rawWriteRetryAuthorization', true],
    ]) {
        const result = mod.validatePlanningInput(validInput({ [key]: value }));
        assert.equal(result.ok, false, `${key} should be blocked`);
    }
});

test('input, manifest and renewed proposal gates fail closed before recapture', async () => {
    const invalidInput = mod.validatePlanningInput(validInput({ retry: 1, unknown: ['mystery'] }));
    assert.equal(invalidInput.ok, false);
    assert.match(invalidInput.errors.join('\n'), /retry must be 0/);
    assert.match(invalidInput.errors.join('\n'), /unknown arguments/);

    const invalidManifest = await mod.runPlanning(validInput(), {
        manifest: manifest({ phase_5_21_l2v3c_metadata_target_mismatch_count: 0 }),
        renewedProposal: renewedProposal(),
        fetchHtmlFn: () => {
            throw new Error('must not fetch');
        },
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(invalidManifest.ok, false);
    assert.equal(invalidManifest.status, 3);

    const invalidProposal = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal({ recommendation: { raw_write_ready_for_execution: true } }),
        fetchHtmlFn: () => {
            throw new Error('must not fetch');
        },
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(invalidProposal.ok, false);
    assert.equal(invalidProposal.status, 4);
});

test('argument parsing and validation cover unknown, positional and default branches', () => {
    const parsed = mod.parseArgs([
        '--manifest',
        mod.MANIFEST_PATH,
        '--source=fotmob',
        '--planning-authorization=maybe',
        '--allow-db-write',
        '--target-external-ids=4830466,4830466,4830461',
        '--unknown-flag=yes',
        'loose',
    ]);

    assert.equal(parsed.manifest, mod.MANIFEST_PATH);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.planningAuthorization, true);
    assert.equal(parsed.allowDbWrite, true);
    assert.equal(parsed.targetExternalIds, '4830466,4830466,4830461');
    assert.deepEqual(parsed.unknown, ['unknown-flag', 'loose']);
    assert.equal(mod.normalizeBooleanFlag('bogus', false), false);

    const missing = mod.validatePlanningInput({});
    assert.equal(missing.ok, false);
    assert.match(missing.errors.join('\n'), /missing manifest/);
    assert.match(missing.errors.join('\n'), /missing planning-authorization=yes/);

    const invalid = mod.validatePlanningInput(
        validInput({
            manifest: 'wrong.json',
            renewedProposal: 'wrong-proposal.json',
            reportOutput: 'wrong-report.md',
            source: 'other',
            leagueId: 54,
            leagueName: 'Other',
            season: '2024/2025',
            route: 'api',
            rawVersion: 'v1',
            hashStrategy: 'raw',
            batchId: 'wrong',
            targetCount: 49,
            requestDelayMs: -1,
        })
    );
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /manifest must be/);
    assert.match(invalid.errors.join('\n'), /renewed-proposal must be/);
    assert.match(invalid.errors.join('\n'), /report-output must be/);
    assert.match(invalid.errors.join('\n'), /league-id must be 53/);
    assert.match(invalid.errors.join('\n'), /request-delay-ms/);
});

test('manifest and proposal gates report malformed metadata', () => {
    const malformedManifest = manifest({
        batch_id: 'wrong',
        source: 'other',
        route: 'api',
        raw_data_version: 'v1',
        hash_strategy: 'raw',
        known_completed_targets: [],
        phase_5_21_l2v3c_planning_status: 'missing',
        phase_5_21_l2v3c_metadata_target_mismatch_count: 0,
        next_required_step: 'wrong_step',
        renewed_baseline_requires_separate_baseline_acceptance: false,
        renewed_baseline_requires_separate_final_db_write_authorization: false,
        raw_write_ready_for_execution: true,
        candidate_targets: [
            candidate('bad', {
                match_id: 'wrong',
                baseline_hash: 'not-a-hash',
                preflight_status: 'missing',
                matches_seed_status: 'missing',
            }),
        ],
    });
    const manifestGate = mod.validateManifestGate(malformedManifest);
    assert.equal(manifestGate.ok, false);
    assert.match(manifestGate.errors.join('\n'), /manifest batch_id mismatch/);
    assert.match(manifestGate.errors.join('\n'), /known_completed_targets/);
    assert.match(manifestGate.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(manifestGate.errors.join('\n'), /external_id must be numeric/);

    const proposalGate = mod.validateRenewedProposalGate(
        renewedProposal({
            proposal_phase: 'wrong',
            no_write: false,
            db_write_performed: true,
            raw_insert_performed: true,
            summary: { metadata_target_mismatch_count: 0, next_required_step: 'wrong' },
            recommendation: {
                raw_write_ready_for_execution: true,
                requires_separate_baseline_acceptance: false,
                requires_separate_final_db_write_authorization: false,
            },
            checked_targets: [
                proposalTarget('4830466', { hash_status: 'stable_match', metadata_identity_status: 'ok' }),
            ],
        })
    );
    assert.equal(proposalGate.ok, false);
    assert.match(proposalGate.errors.join('\n'), /proposal_phase/);
    assert.match(proposalGate.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(proposalGate.errors.join('\n'), /checked_targets/);
    assert.match(proposalGate.errors.join('\n'), /must be metadata_target_mismatch/);
});

test('selection detects missing manifest or proposal targets and dedupes requested ids', () => {
    const manifestGate = mod.validateManifestGate(manifest());
    const proposalGate = mod.validateRenewedProposalGate(renewedProposal());
    const selected = mod.selectMismatchTargets(manifestGate, proposalGate, ['4830466', '4830466', '9999999']);

    assert.equal(selected.ok, false);
    assert.deepEqual(selected.selected_external_ids, ['4830466', '9999999']);
    assert.match(selected.errors.join('\n'), /9999999/);

    const missingProposal = mod.selectMismatchTargets(manifestGate, { checkedTargets: [] }, ['4830466']);
    assert.equal(missingProposal.ok, false);
    assert.match(missingProposal.errors.join('\n'), /missing from L2V3C mismatch proposal/);
});

test('route and canonical redirect mismatches receive specific classification', async () => {
    const target = candidate('4830466');
    const proposal = proposalTarget('4830466');

    const wrongRoute = await mod.diagnoseTarget(target, proposal, 0, validInput(), {
        fetchHtmlFn: () => fetchResultFor('9999999'),
    });
    assert.equal(wrongRoute.mismatch_type, 'route_generation_mismatch');

    const redirect = await mod.diagnoseTarget(target, proposal, 0, validInput(), {
        fetchHtmlFn: () =>
            fetchResultFor('4830466', fakePageProps('4830466'), {
                final_url: 'https://www.fotmob.com/match/4830759',
            }),
    });
    assert.equal(redirect.mismatch_type, 'canonical_redirect_mismatch');
});

test('diagnostics cover fetch failure, invalid HTML and missing pageProps safely', async () => {
    const target = candidate('4830466');
    const proposal = proposalTarget('4830466');

    const httpFailure = await mod.diagnoseTarget(target, proposal, 0, validInput(), {
        fetchResultsByExternalId: {
            4830466: {
                ok: false,
                request_url: 'https://www.fotmob.com/match/4830466',
                final_url: 'https://www.fotmob.com/match/4830466',
                http_status: 403,
                body_byte_length: 0,
                error: 'HTTP_403',
            },
        },
    });
    assert.equal(httpFailure.parsed, false);
    assert.equal(httpFailure.safe_error_summary, 'HTTP_403');

    const invalidHtml = await mod.diagnoseTarget(target, proposal, 0, validInput(), {
        fetchResults: [
            {
                ok: true,
                request_url: 'https://www.fotmob.com/match/4830466',
                final_url: 'https://www.fotmob.com/match/4830466',
                http_status: 200,
                body_byte_length: 17,
                body: '<html></html>',
            },
        ],
    });
    assert.equal(invalidHtml.safe_error_summary, 'NO_NEXT_DATA');

    const missingPageProps = await mod.diagnoseTarget(target, proposal, 0, validInput(), {
        fetchHtmlFn: () => {
            const body = `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
                props: {},
            })}</script>`;
            return {
                ok: true,
                request_url: 'https://www.fotmob.com/match/4830466',
                final_url: 'https://www.fotmob.com/match/4830466?matchId=4830466',
                http_status: 200,
                body_byte_length: body.length,
                body,
            };
        },
    });
    assert.equal(missingPageProps.safe_error_summary, 'PAGE_PROPS_NOT_FOUND');
});

test('identity reconciliation can pass only when external_id, teams and date all match', async () => {
    const pageProps = fakePageProps('4830466', {
        general: {
            matchId: '4830466',
            leagueId: 53,
            matchName: 'Rennes-vs-Marseille',
            matchTimeUTCDate: '2025-08-15T18:45:00.000Z',
        },
        header: { teams: [{ name: 'Rennes' }, { name: 'Marseille' }] },
    });
    const target = candidate('4830466', {
        home_team: 'Rennes',
        away_team: 'Marseille',
        kickoff_time: '2025-08-15T18:45:00.000Z',
    });
    const diagnostic = await mod.diagnoseTarget(target, proposalTarget('4830466'), 0, validInput(), {
        fetchHtmlFn: () => fetchResultFor('4830466', pageProps),
    });

    assert.equal(diagnostic.identity_match, true);
    assert.equal(diagnostic.team_match, true);
    assert.equal(diagnostic.date_match, true);
    assert.equal(diagnostic.mismatch_type, 'identity_match');
});

test('classification and summary cover identity, team-date and unknown branches', () => {
    assert.deepEqual(mod.extractSafeIdentityFromPageProps(null), {
        external_id: null,
        match_identifier_fields: {},
        home_team: null,
        away_team: null,
        match_name: null,
        match_time_utc: null,
        status: null,
        league_id: null,
    });
    assert.equal(
        mod.classifyDiagnostic({
            parsed: false,
            requested_external_id: '1',
        }).mismatch_type,
        'unknown'
    );
    assert.equal(
        mod.classifyDiagnostic({
            parsed: true,
            requested_external_id: '1',
            observed_external_id: '1',
            team_match: false,
            date_match: true,
        }).mismatch_type,
        'team_date_status_mismatch'
    );

    const identitySummary = mod.buildSummary({
        diagnostics: [
            {
                identity_match: true,
                mismatch_type: 'identity_match',
                deterministic_observed_identity_with_l2v3c: true,
                deterministic_with_l2v3c: true,
            },
        ],
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        proposalGate: { checkedTargets: [proposalTarget('4830466')] },
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(identitySummary.root_cause_status, 'not_applicable');
    assert.equal(identitySummary.next_required_step, 'renewed_baseline_acceptance_review_planning');

    const unknownSummary = mod.buildSummary({
        diagnostics: [
            {
                identity_match: false,
                mismatch_type: 'team_date_status_mismatch',
                deterministic_observed_identity_with_l2v3c: false,
                deterministic_with_l2v3c: false,
            },
        ],
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        proposalGate: { checkedTargets: [proposalTarget('4830466')] },
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(unknownSummary.root_cause_status, 'unknown');
    assert.equal(unknownSummary.next_required_step, 'target_identity_reconciliation_follow_up_investigation');
});

test('report and manifest do not contain full raw_data, pageProps or source body markers', async () => {
    const result = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchHtmlFn: url => fetchResultFor(url.split('/').pop()),
        writeManifest: false,
        writeReport: false,
    });
    const manifestText = JSON.stringify(result.updated_manifest);
    const reportText = result.report;

    assert.equal(manifestText.includes('secret-marker'), false);
    assert.equal(manifestText.includes('DO_NOT_SAVE_FULL_PAGEPROPS'), false);
    assert.equal(reportText.includes('secret-marker'), false);
    assert.equal(reportText.includes('DO_NOT_SAVE_FULL_PAGEPROPS'), false);
    assert.equal(reportText.includes('<html>'), false);
    assert.equal(reportText.includes('__NEXT_DATA__'), true);
});

test('runPlanning can use file readers and default writers through injected safe functions', async () => {
    const writes = [];
    const result = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        readJsonFile: filePath => {
            if (filePath === mod.MANIFEST_PATH) return manifest();
            if (filePath === mod.RENEWED_PROPOSAL_PATH) return renewedProposal();
            throw new Error(`unexpected read ${filePath}`);
        },
        fetchHtmlFn: url => fetchResultFor(url.split('/').pop()),
        writeJsonFile: (filePath, data) => writes.push({ filePath, data }),
        writeReportFile: (filePath, data) => writes.push({ filePath, data }),
    });

    assert.equal(result.ok, true);
    assert.equal(writes.length, 2);
    assert.equal(writes[0].filePath, mod.MANIFEST_PATH);
    assert.equal(writes[1].filePath, mod.REPORT_PATH);
});

test('unresolved identity proposal is not executable by raw write runner', async () => {
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchHtmlFn: url => fetchResultFor(url.split('/').pop()),
        writeManifest: false,
        writeReport: false,
    });
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(result.updated_manifest.raw_write_ready_for_execution, false);
    assert.equal(
        result.updated_manifest.next_required_step,
        'target_identity_source_inventory_reconciliation_planning'
    );
    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step/);
});

test('runCli prints only safe JSON summary', async () => {
    const stdout = [];
    const originalWrite = process.stdout.write;
    process.stdout.write = chunk => {
        stdout.push(String(chunk));
        return true;
    };
    try {
        const help = await mod.runCli(['--help']);
        assert.equal(help.status, 0);
        assert.match(stdout.join(''), /Usage:/);

        stdout.length = 0;
        const result = await mod.runCli(
            [
                `--manifest=${mod.MANIFEST_PATH}`,
                `--renewed-proposal=${mod.RENEWED_PROPOSAL_PATH}`,
                `--report-output=${mod.REPORT_PATH}`,
                '--source=fotmob',
                '--league-id=53',
                '--league-name=Ligue 1',
                '--season=2025/2026',
                '--route=html_hydration',
                '--raw-version=fotmob_pageprops_v2',
                '--hash-strategy=stable_pageprops_payload_v1',
                `--batch-id=${mod.BATCH_ID}`,
                '--target-count=50',
                '--planning-authorization=yes',
                '--target-identity-reconciliation-authorization=yes',
                '--network-authorization=yes',
                '--match-detail-recapture-authorization=yes',
                '--allow-db-write=no',
                '--allow-raw-match-data-write=no',
                '--allow-controlled-write=no',
                '--allow-matches-write=no',
                '--allow-bookmaker-odds-write=no',
                '--allow-feature-write=no',
                '--allow-schema-migration=no',
                '--allow-parser-implementation=no',
                '--allow-feature-extraction=no',
                '--allow-training=no',
                '--allow-prediction=no',
                '--allow-browser-runtime=no',
                '--allow-proxy-runtime=no',
                '--print-full-body=no',
                '--save-full-body=no',
                '--print-full-json=no',
                '--save-full-json=no',
                '--print-full-pageprops=no',
                '--save-full-pageprops=no',
                '--target-external-ids=4830466',
                '--retry=0',
                '--request-delay-ms=0',
            ],
            {
                manifest: manifest(),
                renewedProposal: renewedProposal(),
                fetchHtmlFn: url => fetchResultFor(url.split('/').pop()),
                writeManifest: false,
                writeReport: false,
            }
        );
        assert.equal(result.status, 0);
        assert.match(stdout.join(''), /"ok": true/);
        assert.equal(stdout.join('').includes('secret-marker'), false);
        assert.equal(stdout.join('').includes('<html>'), false);
    } finally {
        process.stdout.write = originalWrite;
    }
});

test('runCli emits controlled failure summary for invalid input', async () => {
    const stdout = [];
    const originalWrite = process.stdout.write;
    process.stdout.write = chunk => {
        stdout.push(String(chunk));
        return true;
    };
    try {
        const result = await mod.runCli(['--manifest=wrong']);
        assert.equal(result.status, 2);
        assert.match(stdout.join(''), /"ok": false/);
        assert.match(stdout.join(''), /manifest must be/);
    } finally {
        process.stdout.write = originalWrite;
    }
});
