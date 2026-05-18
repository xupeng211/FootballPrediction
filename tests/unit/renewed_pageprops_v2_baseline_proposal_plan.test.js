'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/renewed_pageprops_v2_baseline_proposal_plan.js');
const PREVIEW_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_preview.js');
const RAW_WRITE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const preview = require(PREVIEW_PATH);
const rawWrite = require(RAW_WRITE_PATH);

function fakePageProps(externalId, overrides = {}) {
    return {
        content: {
            matchFacts: { infoBox: { Tournament: 'Ligue 1' } },
            lineup: { home: [], away: [] },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.2, 0.8] }] } } },
            DO_NOT_SAVE_FULL_PAGEPROPS: 'secret-marker',
        },
        fallback: false,
        general: { matchId: externalId, leagueId: 53 },
        header: { teams: [{ name: `Home ${externalId}` }, { name: `Away ${externalId}` }] },
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

function fetchResultFor(externalId, pageProps = fakePageProps(externalId), overrides = {}) {
    const body = fakeHtml(externalId, pageProps);
    return {
        ok: overrides.ok ?? true,
        request_url: `https://www.fotmob.com/match/${externalId}`,
        final_url: `https://www.fotmob.com/match/${externalId}`,
        http_status: overrides.http_status ?? 200,
        content_type: 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: `body-sha-${externalId}`,
        body,
        error: overrides.error,
    };
}

function baselineHash(externalId, overrides = {}) {
    return preview.computeStablePagePropsHash(fakePageProps(externalId, overrides));
}

function target(externalId, overrides = {}) {
    const lowPathCount = ['4830466', '4830461', '4830481', '4830496', '4830511'].includes(externalId);
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
        baseline_hash: baselineHash(externalId),
        write_plan_status: 'eligible_for_insert',
        matches_seed_status: 'inserted_matches_identity',
        pageprops_summary: {
            http_status: 200,
            parse_status: 'pageprops_v2_parsed',
            raw_data_shape_valid: true,
            has_meta: true,
            has_matchId: true,
            has_pageProps: true,
            pageProps_path_count: lowPathCount ? 2915 : 9500,
            pageProps_content_path_count: lowPathCount ? 365 : 7000,
        },
        phase_5_21_l2v3_status: 'blocked',
        ...overrides,
    };
}

function candidates() {
    const required = ['4830466', '4830461', '4830481', '4830496', '4830511', '4830463', '4830465', '4830508'];
    const filler = Array.from({ length: 42 }, (_, index) => String(4900000 + index));
    return [...required, ...filler].map(externalId => target(externalId));
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
        known_completed_targets: knownCompleted(),
        candidate_targets: candidates(),
        phase_5_21_l2v3_execution_status: 'blocked',
        renewed_controlled_pageprops_v2_raw_write_status: 'blocked',
        phase_5_21_l2v3b_review_status: 'completed_no_write',
        hash_drift_classification: 'partial_systemic_stable_content_drift',
        raw_write_retry_readiness_status: 'ready_for_renewed_authorization',
        ...overrides,
    };
}

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        proposalOutput: mod.PROPOSAL_PATH,
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
        repeatCount: 2,
        requestDelayMs: 0,
        generatedAt: '2026-05-18T00:00:00.000Z',
        ...overrides,
    };
}

test('valid input succeeds and remains no-write proposal-only', async () => {
    const writes = [];
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        fetchHtmlFn: url => {
            const externalId = url.split('/').pop();
            return fetchResultFor(externalId);
        },
        writeJsonFile: (filePath, data) => writes.push({ filePath, data }),
        writeReportFile: (filePath, data) => writes.push({ filePath, data }),
        generatedAt: '2026-05-18T00:00:00.000Z',
    });

    assert.equal(result.ok, true);
    assert.equal(result.proposal.no_write, true);
    assert.equal(result.proposal.db_write_performed, false);
    assert.equal(result.proposal.raw_insert_performed, false);
    assert.equal(result.proposal.recommendation.raw_write_ready_for_execution, false);
    assert.equal(result.proposal.recommendation.requires_separate_baseline_acceptance, true);
    assert.equal(result.proposal.recommendation.requires_separate_final_db_write_authorization, true);
    assert.equal(result.summary.checked_target_count, 8);
    assert.equal(writes.length, 3);
});

test('write and execution flags are blocked in L2V3C', () => {
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
        ['rawWriteReadyForExecution', true],
    ]) {
        const result = mod.validatePlanningInput(validInput({ [key]: value }));
        assert.equal(result.ok, false, `${key} should be blocked`);
    }
});

test('CLI parsing and input validation reject missing, unknown and invalid planning inputs', () => {
    const parsed = mod.parseArgs([
        '--manifest',
        mod.MANIFEST_PATH,
        '--source=fotmob',
        '--planning-authorization=no',
        '--allow-db-write=yes',
        '--sample-external-ids=4830466,4830463',
        '--unknown-flag=yes',
        'loose-arg',
    ]);

    assert.equal(parsed.manifest, mod.MANIFEST_PATH);
    assert.equal(parsed.sampleExternalIds, '4830466,4830463');
    assert.equal(parsed.planningAuthorization, false);
    assert.equal(parsed.allowDbWrite, true);
    assert.deepEqual(parsed.unknown, ['unknown-flag', 'loose-arg']);

    const missing = mod.validatePlanningInput({});
    assert.equal(missing.ok, false);
    assert.match(missing.errors.join('\n'), /missing manifest/);
    assert.match(missing.errors.join('\n'), /missing planning-authorization=yes/);

    const invalid = mod.validatePlanningInput(
        validInput({
            proposalOutput: 'docs/_manifests/wrong.json',
            leagueId: 54,
            targetCount: 49,
            repeatCount: 3,
            requestDelayMs: -1,
            acceptedBaseline: true,
            unknown: ['mystery'],
        })
    );
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /proposal-output must be/);
    assert.match(invalid.errors.join('\n'), /league-id must be 53/);
    assert.match(invalid.errors.join('\n'), /target-count must be 50/);
    assert.match(invalid.errors.join('\n'), /repeat-count must be 1 or 2/);
    assert.match(invalid.errors.join('\n'), /request-delay-ms must be a non-negative integer/);
    assert.match(invalid.errors.join('\n'), /accepted-baseline=yes is blocked/);
    assert.match(invalid.errors.join('\n'), /unknown arguments: mystery/);
});

test('manifest gate requires L2V3 blocked and L2V3B review metadata', () => {
    assert.equal(mod.validateManifestGate(manifest()).ok, true);
    assert.match(
        mod.validateManifestGate(manifest({ phase_5_21_l2v3b_review_status: 'missing' })).errors.join('\n'),
        /phase_5_21_l2v3b_review_status/
    );
});

test('manifest gate rejects wrong counts, status and candidate metadata', () => {
    const badCandidate = {
        ...target('bad'),
        match_id: '53_20252026_123',
        baseline_hash: 'not-a-hash',
        preflight_status: 'missing',
        matches_seed_status: 'not_inserted',
        pageprops_summary: null,
    };
    const result = mod.validateManifestGate(
        manifest({
            candidate_targets: [badCandidate],
            known_completed_targets: knownCompleted().slice(0, 7),
            phase_5_21_l2v3_execution_status: 'completed',
            renewed_controlled_pageprops_v2_raw_write_status: 'completed',
            hash_drift_classification: 'unknown',
        })
    );

    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /candidate_targets must be 50/);
    assert.match(result.errors.join('\n'), /known_completed_targets must be 8/);
    assert.match(result.errors.join('\n'), /phase_5_21_l2v3_execution_status must be blocked/);
    assert.match(result.errors.join('\n'), /renewed_controlled_pageprops_v2_raw_write_status must be blocked/);
    assert.match(result.errors.join('\n'), /hash_drift_classification must reflect/);
    assert.match(result.errors.join('\n'), /invalid external_id/);
    assert.match(result.errors.join('\n'), /match_id convention mismatch/);
    assert.match(result.errors.join('\n'), /baseline_hash invalid/);
    assert.match(result.errors.join('\n'), /preflight_status must be hash_baseline_ready/);
    assert.match(result.errors.join('\n'), /matches_seed_status must be inserted_matches_identity/);
    assert.match(result.errors.join('\n'), /pageprops_summary missing/);
});

test('default sample selects all low path-count targets plus normal controls', () => {
    const selection = mod.selectTargetsForPlanning(manifest(), []);
    assert.equal(selection.ok, true);
    assert.deepEqual(
        selection.targets.map(item => item.external_id),
        ['4830466', '4830461', '4830481', '4830496', '4830511', '4830463', '4830465', '4830508']
    );
    assert.equal(selection.lowPathTargets.length, 5);
});

test('sample selection blocks targets outside the manifest', () => {
    const selection = mod.selectTargetsForPlanning(manifest(), ['4830466', '9999999']);

    assert.equal(selection.ok, false);
    assert.match(selection.errors.join('\n'), /9999999/);
    assert.deepEqual(selection.requested_external_ids, ['4830466', '9999999']);
});

test('hash drift classification covers stable match, stable drift and unstable hash', () => {
    const stableMatch = mod.buildCheckedTargetProposal(target('4830463'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830463'),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
        {
            parsed: true,
            stable_hash: baselineHash('4830463'),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);
    const drift = mod.buildCheckedTargetProposal(target('4830466'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830466', { drift: true }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
        {
            parsed: true,
            stable_hash: baselineHash('4830466', { drift: true }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);
    const unstable = mod.buildCheckedTargetProposal(target('4830461'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830461', { a: 1 }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
        {
            parsed: true,
            stable_hash: baselineHash('4830461', { a: 2 }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);

    assert.equal(stableMatch.hash_status, 'stable_match');
    assert.equal(drift.hash_status, 'stable_drift');
    assert.equal(unstable.hash_status, 'unstable_hash');
    assert.equal(mod.classifyOverallDrift([drift, stableMatch]), 'single_target');
    assert.equal(mod.classifyOverallDrift([unstable, stableMatch]), 'unstable_hash_implementation');
});

test('hash drift classification covers block, fetch failure and systemic categories', () => {
    const lowDrift = mod.buildCheckedTargetProposal(target('4830466'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830466', { drift: true }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);
    const anotherLowDrift = mod.buildCheckedTargetProposal(target('4830461'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830461', { drift: true }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);
    const normalDrift = mod.buildCheckedTargetProposal(target('4830463'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830463', { drift: true }),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);
    const stableMatch = mod.buildCheckedTargetProposal(target('4830465'), [
        {
            parsed: true,
            stable_hash: baselineHash('4830465'),
            block_markers: [],
            metadata_identity_status: 'match_id_external_id_reconciled',
        },
    ]);

    assert.equal(
        mod.classifyTargetAttempts(target('4830466'), [
            { parsed: true, stable_hash: 'abc', block_markers: ['captcha'] },
        ]),
        'block_or_captcha'
    );
    assert.equal(mod.classifyTargetAttempts(target('4830466'), []), 'fetch_or_parse_failure');
    assert.equal(
        mod.classifyTargetAttempts(target('4830466'), [{ parsed: false, stable_hash: null, block_markers: [] }]),
        'fetch_or_parse_failure'
    );
    assert.equal(mod.classifyOverallDrift([]), 'unknown');
    assert.equal(mod.classifyOverallDrift([lowDrift, normalDrift]), 'fully_systemic');
    assert.equal(mod.classifyOverallDrift([lowDrift, anotherLowDrift, stableMatch]), 'low_path_count_subset');
    assert.equal(mod.classifyOverallDrift([lowDrift, normalDrift, stableMatch]), 'partial_systemic');
});

test('proposal preserves old baselines and marks renewed hashes as review-only', async () => {
    const result = await mod.runPlanning(validInput({ sampleExternalIds: ['4830466'] }), {
        manifest: manifest(),
        fetchHtmlFn: url => {
            const externalId = url.split('/').pop();
            return fetchResultFor(externalId, fakePageProps(externalId, { currentDrift: true }));
        },
        writeProposal: false,
        writeManifest: false,
        writeReport: false,
    });

    const checked = result.proposal.checked_targets[0];
    const original = manifest().candidate_targets.find(item => item.external_id === '4830466');
    assert.equal(checked.old_baseline_hash, original.baseline_hash);
    assert.notEqual(checked.renewed_candidate_hash, original.baseline_hash);
    assert.equal(result.proposal.proposal_status, 'renewed_baseline_review_required');
    assert.equal(result.proposal.recommendation.requires_human_review, true);
});

test('manifest update does not mark raw write ready for execution', async () => {
    const result = await mod.runPlanning(validInput({ sampleExternalIds: ['4830463'] }), {
        manifest: manifest(),
        fetchHtmlFn: url => {
            const externalId = url.split('/').pop();
            return fetchResultFor(externalId);
        },
        writeProposal: false,
        writeManifest: false,
        writeReport: false,
    });

    assert.equal(result.updated_manifest.phase_5_21_l2v3c_planning_status, 'completed_no_write');
    assert.equal(result.updated_manifest.renewed_baseline_requires_separate_baseline_acceptance, true);
    assert.equal(result.updated_manifest.renewed_baseline_requires_separate_final_db_write_authorization, true);
    assert.equal(result.updated_manifest.raw_write_retry_readiness_status, 'ready_for_renewed_authorization');
    assert.equal(result.updated_manifest.phase_5_21_l2v3c_db_write_performed, false);
    assert.equal(result.updated_manifest.phase_5_21_l2v3c_raw_insert_performed, false);
});

test('runPlanning returns controlled no-write failures before recapture', async () => {
    const invalidManifest = await mod.runPlanning(validInput(), {
        manifest: manifest({ candidate_targets: [] }),
        fetchHtmlFn: () => {
            throw new Error('must not fetch when manifest gate fails');
        },
        writeProposal: false,
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(invalidManifest.ok, false);
    assert.equal(invalidManifest.status, 3);

    const missingSelection = await mod.runPlanning(validInput({ sampleExternalIds: ['9999999'] }), {
        manifest: manifest(),
        fetchHtmlFn: () => {
            throw new Error('must not fetch when target selection fails');
        },
        writeProposal: false,
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(missingSelection.ok, false);
    assert.equal(missingSelection.status, 4);
});

test('metadata mismatch routes next step to identity reconciliation planning', async () => {
    const result = await mod.runPlanning(validInput({ sampleExternalIds: ['4830463'] }), {
        manifest: manifest(),
        fetchHtmlFn: url => {
            const externalId = url.split('/').pop();
            return fetchResultFor(externalId, fakePageProps('9999999'));
        },
        writeProposal: false,
        writeManifest: false,
        writeReport: false,
    });

    assert.equal(result.summary.metadata_target_mismatch_count, 1);
    assert.equal(result.summary.next_required_step, 'target_identity_reconciliation_planning');
    assert.equal(result.updated_manifest.next_required_step, 'target_identity_reconciliation_planning');
});

test('runCli supports help and writes only safe JSON summaries', async () => {
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
                `--proposal-output=${mod.PROPOSAL_PATH}`,
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
                '--sample-external-ids=4830463',
                '--request-delay-ms=0',
            ],
            {
                manifest: manifest(),
                fetchHtmlFn: url => fetchResultFor(url.split('/').pop()),
                writeProposal: false,
                writeManifest: false,
                writeReport: false,
                generatedAt: '2026-05-18T00:00:00.000Z',
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

test('proposal and report do not contain full raw_data/pageProps/source body markers', async () => {
    const result = await mod.runPlanning(validInput({ sampleExternalIds: ['4830466'] }), {
        manifest: manifest(),
        fetchHtmlFn: url => {
            const externalId = url.split('/').pop();
            return fetchResultFor(externalId);
        },
        writeProposal: false,
        writeManifest: false,
        writeReport: false,
    });
    const proposalText = JSON.stringify(result.proposal);
    assert.equal(proposalText.includes('secret-marker'), false);
    assert.equal(proposalText.includes('DO_NOT_SAVE_FULL_PAGEPROPS'), false);
    assert.equal(result.report.includes('secret-marker'), false);
    assert.equal(result.report.includes('<html>'), false);
});

test('raw write runner does not accept proposal-only metadata as execution readiness', () => {
    const candidate = target('4830466', {
        baseline_hash: baselineHash('4830466'),
        renewed_candidate_hash: baselineHash('4830466', { drift: true }),
        renewed_baseline_proposal_status: 'renewed_baseline_review_required',
        required_next_step: 'renewed_baseline_acceptance_review',
    });
    const result = rawWrite.validateManifestGate(
        manifest({
            candidate_targets: [candidate, ...candidates().slice(1)],
            next_required_step: 'renewed_baseline_acceptance_review',
        })
    );
    assert.equal(result.ok, false);
});
