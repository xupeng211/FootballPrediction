'use strict';
/* eslint-disable max-lines -- L2V3Y acquisition execution safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/pageprops_v2_controlled_source_inventory_acquisition_execute.js'
);
const rawWrite = require('../../scripts/ops/renewed_pageprops_v2_raw_write_execute');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

function readText(repoPath) {
    return fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8');
}

function candidate(index, overrides = {}) {
    const externalId = String(9000001 + index);
    return {
        target_id: `batch:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        schedule_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        source_page_url: null,
        source_page_url_base: null,
        source_url_fragment_external_id: null,
        source_inventory_record_key: null,
        identity_evidence_status: 'missing',
        ...overrides,
    };
}

function sourceRecord(index, overrides = {}) {
    const externalId = String(9000001 + index);
    const sourcePageUrl = `https://www.fotmob.com/matches/home-${index}-away-${index}/${externalId}#${externalId}`;
    return {
        external_id: externalId,
        source_page_url: sourcePageUrl,
        source_page_url_base: sourcePageUrl.split('#')[0],
        source_url_fragment_external_id: externalId,
        source_slug: `home-${index}-away-${index}`,
        source_route_code: externalId,
        source_inventory_record_key: `l1_api_data_leagues:matches.allMatches.${index}:${externalId}`,
        source_inventory_generated_at: '2026-05-21T14:20:00Z',
        schedule_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        ...overrides,
    };
}

function syntheticManifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        next_required_step: 'controlled_no_write_source_inventory_acquisition_execution',
        recommended_next_step: 'Phase 5.21L2V3Y: controlled no-write source inventory acquisition execution',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function syntheticL2V3XArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3X',
        artifact_status: 'completed_no_write_controlled_source_inventory_acquisition_planning',
        live_fetch_performed: false,
        db_write_performed: false,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        planned_source_endpoint: '/api/data/leagues?id=53&season=20252026',
        planned_acquisition_scope: 'ligue1_2025_2026_profile_001_current_50_candidates_metadata_only_source_inventory',
        planned_candidate_scope_count: 50,
        acquisition_execution_authorization_required: true,
        baseline_acceptance_required: true,
        final_db_write_authorization_required: true,
        next_required_step: 'controlled_no_write_source_inventory_acquisition_execution',
        ...overrides,
    };
}

function fakeResponse(body, status = 200, contentType = 'application/json') {
    const bodyText = typeof body === 'string' ? body : JSON.stringify(body);
    return {
        status,
        headers: {
            get(name) {
                if (name.toLowerCase() === 'content-type') return contentType;
                if (name.toLowerCase() === 'content-length') return String(Buffer.byteLength(bodyText, 'utf8'));
                return null;
            },
        },
        async text() {
            return bodyText;
        },
    };
}

function responseWithHeaders({
    body = '{}',
    status = 200,
    contentType = 'application/json',
    contentLength = null,
} = {}) {
    const bodyText = typeof body === 'string' ? body : JSON.stringify(body);
    return {
        status,
        headers: {
            get(name) {
                if (name.toLowerCase() === 'content-type') return contentType;
                if (name.toLowerCase() === 'content-length') return contentLength;
                return null;
            },
        },
        async text() {
            return bodyText;
        },
    };
}

function buildDeps(overrides = {}) {
    const requested = [];
    return {
        requested,
        deps: {
            manifest: syntheticManifest(overrides.manifest || {}),
            l2v3xArtifact: syntheticL2V3XArtifact(overrides.l2v3xArtifact || {}),
            generatedAt: '2026-05-21T14:20:00Z',
            async fetch(url, options) {
                requested.push({ url, options });
                return fakeResponse(overrides.body || { league: { id: 53 }, matches: [] }, overrides.status || 200);
            },
            sourceRecords:
                overrides.sourceRecords === undefined
                    ? Array.from({ length: 50 }, (_, index) => sourceRecord(index))
                    : overrides.sourceRecords,
            writeFiles: false,
        },
    };
}

async function buildSyntheticRunResult(overrides = {}) {
    const harness = buildDeps(overrides);
    const result = await mod.runControlledSourceInventoryAcquisitionExecution(harness.deps);
    return { ...result, requested: harness.requested };
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (/pg|child_process|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3Y performs controlled metadata-only source inventory acquisition execution', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3Y');
    assert.equal(artifact.acquisition_attempted, true);
    assert.equal(artifact.live_fetch_performed, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.endpoint_used, '/api/data/leagues?id=53&season=20252026');
    assert.equal(artifact.candidate_scope_count, 50);
    assert.equal(artifact.source_records_seen_count, 50);
    assert.equal(artifact.candidate_targets_matched_count, 50);
    assert.equal(artifact.candidate_targets_with_source_page_url, 50);
    assert.equal(artifact.candidate_targets_with_source_page_url_base, 50);
    assert.equal(artifact.candidate_targets_with_source_url_fragment_external_id, 50);
    assert.equal(artifact.candidate_targets_with_source_inventory_record_key, 50);
    assert.equal(artifact.identity_evidence_complete_count, 50);
    assert.equal(artifact.safe_metadata_record_count, 50);
    assert.equal(manifest.phase_5_21_l2v3y_execution_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(result.requested[0].url, 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026');
    assert.deepEqual(result.requested[0].options, { method: 'GET' });
});

test('acquired source URL evidence is not accepted mapping or raw write authorization', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.acquisition_result_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.acquired_source_url_evidence_is_not_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.identity_evidence_status_complete_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.source_url_fragment_external_id_match_is_not_accepted_mapping, true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
});

test('metadata-only output omits full API payload pageProps raw_data and source body', async () => {
    const result = await buildSyntheticRunResult({
        body: {
            nested: {
                raw_data: 'must not be persisted',
                pageProps: 'must not be persisted',
                html: '<!DOCTYPE html>',
                marker: '__NEXT_DATA__',
            },
        },
    });
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('must not be persisted'), false);
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('HTTP 403 or block markers stop execution and record blocked metadata only', async () => {
    const result = await buildSyntheticRunResult({
        status: 403,
        body: 'Forbidden',
        sourceRecords: [],
    });
    const artifact = result.artifact;

    assert.equal(artifact.endpoint_http_status, 403);
    assert.equal(artifact.endpoint_parsed, false);
    assert.equal(artifact.acquisition_blocked_count, 50);
    assert.equal(artifact.acquisition_failed_count, 0);
    assert.equal(artifact.candidate_targets_matched_count, 0);
    assert.equal(artifact.safe_metadata_record_count, 50);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3Z: continued source inventory acquisition investigation'
    );
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('invalid JSON or schema drift fails closed without writing raw readiness', async () => {
    const invalidJson = await buildSyntheticRunResult({
        body: '{not json',
        sourceRecords: [],
    });
    const emptyRecords = await buildSyntheticRunResult({
        body: { league: { id: 53 }, matches: [] },
        sourceRecords: [],
    });

    assert.equal(invalidJson.artifact.endpoint_parsed, false);
    assert.equal(invalidJson.artifact.acquisition_failed_count, 50);
    assert.equal(
        invalidJson.artifact.recommended_next_step,
        'Phase 5.21L2V3Z: source inventory schema adaptation planning'
    );
    assert.equal(emptyRecords.artifact.endpoint_parsed, true);
    assert.equal(emptyRecords.artifact.acquisition_failed_count, 50);
    assert.equal(emptyRecords.artifact.raw_write_ready_for_execution, false);
});

test('partial or missing source URL evidence remains non-executable', async () => {
    const records = Array.from({ length: 50 }, (_, index) =>
        sourceRecord(index, {
            source_page_url: index < 25 ? null : `https://www.fotmob.com/matches/x/${9000001 + index}`,
            source_page_url_base: index < 25 ? null : `https://www.fotmob.com/matches/x/${9000001 + index}`,
            source_url_fragment_external_id: null,
        })
    );
    const result = await buildSyntheticRunResult({ sourceRecords: records });

    assert.equal(result.artifact.identity_evidence_complete_count, 0);
    assert.equal(result.artifact.identity_evidence_partial_count, 50);
    assert.equal(result.artifact.candidate_targets_with_source_url_fragment_external_id, 0);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
    assert.equal(result.artifact.accepted_mapping_count, 0);
});

test('not found and fully missing evidence remain blockers', async () => {
    const notFound = await buildSyntheticRunResult({
        sourceRecords: Array.from({ length: 49 }, (_, index) => sourceRecord(index)),
    });
    const missingEvidence = await buildSyntheticRunResult({
        sourceRecords: Array.from({ length: 50 }, (_, index) =>
            sourceRecord(index, {
                source_page_url: null,
                source_page_url_base: null,
                source_url_fragment_external_id: null,
                source_slug: null,
                source_route_code: null,
                source_inventory_record_key: null,
            })
        ),
    });

    assert.equal(notFound.artifact.acquisition_not_found_count, 1);
    assert.equal(notFound.artifact.candidate_targets_matched_count, 49);
    assert.equal(
        notFound.artifact.recommended_next_step,
        'Phase 5.21L2V3Z: source inventory candidate matching investigation'
    );
    assert.equal(missingEvidence.artifact.identity_evidence_missing_count, 50);
    assert.equal(missingEvidence.artifact.candidate_targets_matched_count, 50);
    assert.equal(missingEvidence.artifact.raw_write_ready_for_execution, false);
    assert.equal(missingEvidence.artifact.accepted_mapping_count, 0);
});

test('fetchSourceInventoryJson fails closed on unavailable fetch, request failures, size limits, and status stops', async t => {
    const originalFetch = global.fetch;
    global.fetch = undefined;
    t.after(() => {
        global.fetch = originalFetch;
    });

    const unavailable = await mod.fetchSourceInventoryJson({});
    const requestFailure = await mod.fetchSourceInventoryJson({
        async fetch() {
            throw new Error('network down');
        },
    });
    const lengthTooLarge = await mod.fetchSourceInventoryJson({
        async fetch() {
            return responseWithHeaders({ contentLength: String(6 * 1024 * 1024) });
        },
    });
    const textFailure = await mod.fetchSourceInventoryJson({
        async fetch() {
            return {
                status: 200,
                headers: { get: () => 'application/json' },
                async text() {
                    throw new Error('stream closed');
                },
            };
        },
    });
    const bodyTooLarge = await mod.fetchSourceInventoryJson({
        async fetch() {
            return responseWithHeaders({ body: 'x'.repeat(5 * 1024 * 1024 + 1), contentLength: null });
        },
    });
    const blockMarker = await mod.fetchSourceInventoryJson({
        async fetch() {
            return fakeResponse('captcha required', 200, 'text/html');
        },
    });
    const rateLimited = await mod.fetchSourceInventoryJson({
        async fetch() {
            return fakeResponse('Too many requests', 429, 'text/plain');
        },
    });
    const non200 = await mod.fetchSourceInventoryJson({
        async fetch() {
            return fakeResponse('Server error', 500, 'text/plain');
        },
    });

    assert.equal(unavailable.stop_reason, 'fetch_unavailable');
    assert.equal(requestFailure.stop_reason, 'request_failed');
    assert.equal(lengthTooLarge.safe_error_summary, 'content_length_exceeded_metadata_only_limit');
    assert.equal(textFailure.stop_reason, 'response_text_read_failed');
    assert.equal(bodyTooLarge.safe_error_summary, 'response_body_exceeded_metadata_only_limit');
    assert.equal(blockMarker.stop_reason, 'http_block_or_captcha_signal');
    assert.deepEqual(blockMarker.blocked_markers, ['captcha']);
    assert.equal(rateLimited.stop_reason, 'rate_limit_signal');
    assert.equal(non200.stop_reason, 'widespread_non_200_response');
});

test('source inventory adapter injection paths use metadata-only parser options', () => {
    const seen = [];
    const injected = mod.parseSourceInventoryRecords(
        { league: { id: 53 } },
        {
            sourceInventoryAdapter: {
                parseSourceInventory(sourceJson, options) {
                    seen.push({ sourceJson, options });
                    return [sourceRecord(0)];
                },
            },
        },
        '2026-05-21T14:20:00Z'
    );
    const factory = mod.parseSourceInventoryRecords(
        { league: { id: 53 } },
        {
            createSourceInventoryAdapter() {
                return {
                    parseSourceInventory(sourceJson, options) {
                        seen.push({ sourceJson, options });
                        return [sourceRecord(1)];
                    },
                };
            },
        },
        '2026-05-21T14:21:00Z'
    );

    assert.equal(injected[0].external_id, '9000001');
    assert.equal(factory[0].external_id, '9000002');
    assert.equal(seen[0].options.leagueId, 53);
    assert.equal(seen[0].options.season, '2025/2026');
    assert.equal(seen[1].options.sourceInventoryGeneratedAt, '2026-05-21T14:21:00Z');
});

test('updated manifest is still rejected by raw write runner gate', async () => {
    const result = await buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('helper refuses DB write, raw write, acceptance, proxy, browser, and retry flags', () => {
    const parsed = mod.parseArgs([
        '--live-fetch=yes',
        '--source-inventory-authorization=yes',
        '--allow-db-write=yes',
        '--allow-raw-match-data-write=yes',
        '--accept-identity-mapping=yes',
        '--accept-baseline=yes',
        '--allow-proxy-runtime=yes',
        '--allow-browser-runtime=yes',
        '--allow-raw-write-retry=yes',
        '--retry=1',
    ]);
    const validation = mod.validateCliOptions(parsed);

    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /allow-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-match-data-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-identity-mapping=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-baseline=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-proxy-runtime=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-browser-runtime=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /retry must be 0/);
});

test('input gate reports unsafe manifest and L2V3X planning drift', () => {
    const validation = mod.validateInputs(
        syntheticManifest({
            candidate_targets: [candidate(0)],
            next_required_step: 'raw_write_retry',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3XArtifact({
            proposal_phase: 'Phase 5.21L2V3W',
            live_fetch_performed: true,
            db_write_performed: true,
            planned_source_endpoint: '/api/data/leagues?id=54&season=20252026',
            planned_acquisition_scope: 'expanded_scope',
            planned_candidate_scope_count: 51,
            acquisition_execution_authorization_required: false,
            baseline_acceptance_required: false,
            final_db_write_authorization_required: false,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
        })
    );
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /candidate_targets must contain 50/);
    assert.match(errors, /next_required_step/);
    assert.match(errors, /manifest raw_write_ready_for_execution/);
    assert.match(errors, /manifest accepted_mapping_count/);
    assert.match(errors, /L2V3X artifact must be present/);
    assert.match(errors, /L2V3X live_fetch_performed/);
    assert.match(errors, /L2V3X db_write_performed/);
    assert.match(errors, /planned_source_endpoint/);
    assert.match(errors, /planned_acquisition_scope/);
    assert.match(errors, /planned_candidate_scope_count/);
    assert.match(errors, /acquisition_execution_authorization_required/);
    assert.match(errors, /baseline_acceptance_required/);
    assert.match(errors, /final_db_write_authorization_required/);
    assert.match(errors, /L2V3X accepted_mapping_count/);
    assert.match(errors, /L2V3X raw_write_ready_for_execution/);
});

test('helper does not import DB, browser, proxy, odds, or harvest modules', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runControlledSourceInventoryAcquisitionExecution, 'function');
});

test('runControlledSourceInventoryAcquisitionExecution can write outputs to explicit temp paths', async () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3y-acquisition-execute-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');
    const harness = buildDeps({
        sourceRecords: Array.from({ length: 50 }, (_, index) => sourceRecord(index)),
    });

    try {
        const result = await mod.runControlledSourceInventoryAcquisitionExecution({
            ...harness.deps,
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3Y');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /acquisition result is not accepted mapping/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI parsing covers help, missing authorization, and unknown arguments', async () => {
    const helpOutput = [];
    const invalidOutput = [];
    const helpParsed = mod.parseArgs(['--help']);
    const parsed = mod.parseArgs([
        'positional',
        '--write-files',
        'false',
        '--live-fetch',
        'yes',
        '--source-inventory-authorization=true',
        '--retry',
        '0',
        '--not-a-real-flag=value',
    ]);
    const invalidParsed = mod.parseArgs(['--live-fetch=no', '--unknown']);
    const invalid = mod.validateCliOptions(invalidParsed);
    const helpStatus = await mod.runCli(['--help'], { stdout: text => helpOutput.push(text) });
    const invalidStatus = await mod.runCli(['--live-fetch=no', '--unknown'], {
        stdout: text => invalidOutput.push(text),
    });

    assert.equal(helpParsed.help, true);
    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.liveFetch, true);
    assert.equal(parsed.sourceInventoryAuthorization, true);
    assert.equal(parsed.retry, '0');
    assert.deepEqual(parsed.unknown, ['positional', 'not-a-real-flag']);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /live-fetch=yes is required/);
    assert.match(invalid.errors.join('\n'), /source-inventory-authorization=yes is required/);
    assert.match(invalid.errors.join('\n'), /unknown arguments/);
    assert.equal(helpStatus, 0);
    assert.match(helpOutput.join(''), /Usage:/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput.join(''), /live-fetch=yes is required/);
});

test('repository L2V3Y artifacts preserve acquisition execution safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Y.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3Y');
    assert.equal(artifact.acquisition_attempted, true);
    assert.equal(artifact.live_fetch_performed, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifest.phase_5_21_l2v3y_execution_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.match(report, /acquired source URL evidence is not raw write authorization/i);
});
