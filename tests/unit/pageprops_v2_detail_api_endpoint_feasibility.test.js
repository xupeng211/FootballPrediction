'use strict';
/* eslint-disable max-lines -- L2V3S feasibility safety contract is intentionally audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_detail_api_endpoint_feasibility.js');
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

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        known_completed_targets: [
            {
                match_id: '53_20252026_4830746',
                external_id: '4830746',
                home_team: 'Angers',
                away_team: 'Strasbourg',
                match_date: '2026-05-10T19:00:00.000Z',
                status: 'finished',
            },
        ],
        candidate_targets: [],
        next_required_step: 'detail_api_endpoint_feasibility_verification',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
    };
}

function syntheticL2V3RArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3R',
        current_url_strategy: 'fotmob_match_external_id_route',
        uses_match_external_id_route: true,
        uses_source_inventory_page_url: false,
        fragment_reaches_server: false,
        slug_reuse_risk: true,
        precise_detail_endpoint_found: 'unknown',
        detail_url_construction_suspect_count: 42,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
    };
}

function syntheticL2V3QArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3Q',
        analyzed_target_count: 42,
        still_blocked_count: 42,
        analyzed_targets: [
            {
                match_id: '53_20252026_4830460',
                schedule_external_id: '4830460',
                schedule_home_team: 'Brest',
                schedule_away_team: 'Lille',
                schedule_date: '2025-08-17T13:00:00.000Z',
                observed_detail_external_id: '4830648',
                detail_url_construction_suspect: true,
                likely_reverse_fixture_or_slug_reuse: true,
            },
            {
                match_id: '53_20252026_4830458',
                schedule_external_id: '4830458',
                schedule_home_team: 'Angers',
                schedule_away_team: 'Paris FC',
                schedule_date: '2025-08-17T15:15:00.000Z',
                observed_detail_external_id: '4830627',
                detail_url_construction_suspect: true,
                likely_reverse_fixture_or_slug_reuse: true,
            },
        ],
    };
}

function sourceTextByPath() {
    return {
        'src/infrastructure/services/FotMobRawDetailFetcher.js':
            'buildFotMobMatchUrl externalId unsupported route: only html_hydration is supported',
        'src/infrastructure/network/FotMobApiClient.js': '/api/data/matchDetails fetchMatchDetails',
        'scripts/ops/l2_raw_detail_preview.js': 'api/data/matchDetails api_match_details alternate_route',
        'src/infrastructure/services/MarathonService.js':
            '_buildMatchDetailsApiUrls api/data/matchDetails api/matchDetails',
        'src/infrastructure/harvesters/strategies/FotMobStrategy.js':
            'fetchMatchDetails api/data/matchDetails _fetchMatchDetailsWithSession',
        'scripts/ops/l1_discovery_safe_preview.js': 'api/data/leagues source_inventory',
    };
}

function fakeJsonBody({ id = '4830460', home = 'Brest', away = 'Lille', date = '2025-08-17T13:00:00.000Z' } = {}) {
    return JSON.stringify({
        general: {
            matchId: id,
            homeTeam: { name: home },
            awayTeam: { name: away },
            matchTimeUTC: date,
            status: { type: 'finished' },
        },
        header: {
            teams: [{ name: home }, { name: away }],
        },
        content: {
            matchFacts: {
                matchId: id,
            },
        },
    });
}

function response(body, status = 200, contentType = 'application/json') {
    return {
        status,
        url: 'https://www.fotmob.com/api/data/matchDetails?matchId=4830460',
        headers: {
            get(name) {
                return String(name).toLowerCase() === 'content-type' ? contentType : '';
            },
        },
        async text() {
            return body;
        },
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runDetailApiEndpointFeasibility({
        manifest: syntheticManifest(),
        l2v3rArtifact: syntheticL2V3RArtifact(),
        l2v3qArtifact: syntheticL2V3QArtifact(),
        sourceTextByPath: sourceTextByPath(),
        writeFiles: false,
        controlledLiveCheck: false,
        networkAuthorization: false,
        ...overrides,
    });
}

test('L2V3S artifact records a no-write endpoint feasibility phase', async () => {
    const result = await buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3S');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.precise_detail_endpoint_found, 'unknown');

    assert.equal(manifest.phase_5_21_l2v3s_feasibility_status, artifact.artifact_status);
    assert.equal(manifest.detail_api_endpoint_feasibility_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
});

test('endpoint inventory finds API candidates but does not adopt them for raw write', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;
    const apiEndpoint = artifact.endpoint_inventory.find(item => item.endpoint_key === 'api_data_match_details');
    const currentHtml = artifact.endpoint_inventory.find(item => item.endpoint_key === 'html_match_external_id_route');

    assert.equal(artifact.analyzed_endpoint_count, 5);
    assert.equal(apiEndpoint.code_evidence_found, true);
    assert.equal(apiEndpoint.precise_detail_candidate, true);
    assert.equal(apiEndpoint.current_pageprops_detail_usage, false);
    assert.equal(currentHtml.current_pageprops_detail_usage, true);
    assert.equal(artifact.safety_contract.endpoint_feasibility_result_is_not_raw_write_authorization, true);
});

test('controlled live check success still does not authorize raw write or accepted mapping', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 1,
        fetchFn: async () => response(fakeJsonBody()),
    });
    const artifact = result.artifact;

    assert.equal(artifact.controlled_live_check_performed, true);
    assert.equal(artifact.checked_target_count, 1);
    assert.equal(artifact.precise_detail_endpoint_found, true);
    assert.equal(artifact.endpoint_avoids_slug_reuse, true);
    assert.equal(artifact.requested_observed_identity_match_count, 1);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.next_required_step, 'precise_detail_request_strategy_implementation');
    assert.equal(artifact.safety_contract.precise_detail_endpoint_found_does_not_imply_raw_write_ready, true);
});

test('requested observed mismatch remains blocked', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 1,
        fetchFn: async () => response(fakeJsonBody({ id: '4830648', home: 'Lille', away: 'Brest' })),
    });
    const target = result.artifact.controlled_endpoint_check.checked_targets[0];

    assert.equal(result.artifact.precise_detail_endpoint_found, 'unknown');
    assert.equal(result.artifact.endpoint_avoids_slug_reuse, 'unknown');
    assert.equal(result.artifact.requested_observed_identity_mismatch_count, 1);
    assert.equal(target.identity_match, false);
    assert.equal(target.team_safe_summary.status, 'reversed_order');
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
    assert.equal(result.artifact.accepted_mapping_count, 0);
});

test('block or parse failure stops controlled check without saving payload', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 3,
        fetchFn: async () => response('Forbidden', 403, 'text/plain'),
    });
    const artifact = result.artifact;
    const target = artifact.controlled_endpoint_check.checked_targets[0];

    assert.equal(artifact.checked_target_count, 1);
    assert.equal(artifact.block_or_captcha_count, 1);
    assert.equal(artifact.parse_failure_count, 1);
    assert.equal(artifact.controlled_endpoint_check.stopped_early, true);
    assert.match(artifact.controlled_endpoint_check.stop_reason, /CONTROLLED_BLOCK_SIGNAL/);
    assert.equal(target.full_payload_saved, false);
    assert.equal(target.full_payload_printed, false);
    assert.equal(target.db_write_performed, false);
    assert.equal(target.raw_insert_performed, false);
});

test('validation fails closed when previous L2V3R gate is not satisfied', async () => {
    const result = await buildSyntheticRunResult({
        l2v3rArtifact: {
            ...syntheticL2V3RArtifact(),
            raw_write_ready_for_execution: true,
        },
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 2);
    assert.match(result.errors.join('\n'), /raw_write_ready_for_execution/);
});

test('controlled live check requires network authorization and max target cap', () => {
    const missingAuth = mod.validateCliOptions({
        controlledLiveCheck: true,
        networkAuthorization: false,
        maxTargets: 1,
        unknown: [],
    });
    const tooMany = mod.validateCliOptions({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 4,
        unknown: [],
    });

    assert.equal(missingAuth.ok, false);
    assert.match(missingAuth.errors.join('\n'), /network-authorization/);
    assert.equal(tooMany.ok, false);
    assert.match(tooMany.errors.join('\n'), /max-targets/);
});

test('CLI parsing covers split values, unknowns, help, invalid integers, and boolean forms', () => {
    const parsed = mod.parseArgs([
        'positional',
        '--controlled-live-check',
        'yes',
        '--network_authorization=no',
        '--max-targets',
        '2',
        '--write-files=false',
        '--mystery',
        '--h',
    ]);
    const invalid = mod.validateCliOptions({
        controlledLiveCheck: false,
        networkAuthorization: false,
        maxTargets: Number.NaN,
        unknown: ['mystery'],
    });
    const negative = mod.validateCliOptions({
        controlledLiveCheck: false,
        networkAuthorization: false,
        maxTargets: -1,
        unknown: [],
    });

    assert.equal(parsed.controlledLiveCheck, true);
    assert.equal(parsed.networkAuthorization, false);
    assert.equal(parsed.maxTargets, 2);
    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['positional', 'mystery']);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /unknown arguments/);
    assert.match(invalid.errors.join('\n'), /max-targets/);
    assert.equal(negative.ok, false);
    assert.match(negative.errors.join('\n'), /max-targets/);
});

test('URL builder and request builder fail closed on invalid ids and support schedule id fallback', () => {
    assert.throws(() => mod.buildDetailApiUrl('abc'), /INVALID_EXTERNAL_ID/);

    const request = mod.buildDetailApiRequest({ schedule_external_id: '4830460' });

    assert.equal(request.route, 'api_match_details');
    assert.match(request.url, /matchId=4830460/);
    assert.match(request.headers.referer, /\/match\/4830460$/);
});

test('validateInputs covers manifest and L2V3R safety failures plus completed idempotent input', () => {
    const completedManifest = {
        ...syntheticManifest(),
        next_required_step: 'continued_detail_endpoint_investigation',
        phase_5_21_l2v3s_feasibility_status: 'completed_no_write_detail_api_endpoint_feasibility_verification',
    };
    const invalidManifest = mod.validateInputs(
        { ...syntheticManifest(), next_required_step: 'raw_write_retry', raw_write_ready_for_execution: true },
        syntheticL2V3RArtifact()
    );
    const invalidAccepted = mod.validateInputs(
        { ...syntheticManifest(), accepted_mapping_count: 1 },
        syntheticL2V3RArtifact()
    );
    const invalidR = mod.validateInputs(syntheticManifest(), {
        ...syntheticL2V3RArtifact(),
        current_url_strategy: 'source_inventory_page_url',
        uses_match_external_id_route: false,
        uses_source_inventory_page_url: true,
        fragment_reaches_server: true,
        slug_reuse_risk: false,
        precise_detail_endpoint_found: true,
        detail_url_construction_suspect_count: 41,
        raw_write_ready_for_execution: true,
        accepted_mapping_count: 1,
    });

    assert.equal(mod.validateInputs(completedManifest, syntheticL2V3RArtifact()).ok, true);
    assert.equal(invalidManifest.ok, false);
    assert.match(invalidManifest.errors.join('\n'), /next_required_step/);
    assert.match(invalidManifest.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.equal(invalidAccepted.ok, false);
    assert.match(invalidAccepted.errors.join('\n'), /accepted_mapping_count/);
    assert.equal(invalidR.ok, false);
    assert.match(invalidR.errors.join('\n'), /current_url_strategy/);
    assert.match(invalidR.errors.join('\n'), /uses_match_external_id_route/);
    assert.match(invalidR.errors.join('\n'), /uses_source_inventory_page_url/);
    assert.match(invalidR.errors.join('\n'), /fragment_reaches_server/);
    assert.match(invalidR.errors.join('\n'), /slug_reuse_risk/);
    assert.match(invalidR.errors.join('\n'), /precise_detail_endpoint_found/);
    assert.match(invalidR.errors.join('\n'), /detail_url_construction_suspect_count/);
});

test('source analysis can read repository files and endpoint inventory handles partial evidence', () => {
    const realAnalysis = mod.analyzeSourceFiles([
        {
            key: 'fotmob_api_client',
            path: 'src/infrastructure/network/FotMobApiClient.js',
            patterns: ['/api/data/matchDetails', 'fetchMatchDetails'],
        },
    ]);
    const partialInventory = mod.buildEndpointInventory([
        { key: 'source_inventory_preflight', evidence_found: false },
        { key: 'fotmob_raw_detail_fetcher', evidence_found: false },
        { key: 'fotmob_api_client', evidence_found: false },
        { key: 'l2_raw_detail_preview', evidence_found: true },
        { key: 'marathon_service', evidence_found: true },
    ]);
    const apiEndpoint = partialInventory.find(item => item.endpoint_key === 'api_data_match_details');
    const alternate = partialInventory.find(item => item.endpoint_key === 'api_match_details_alternate');

    assert.equal(realAnalysis[0].evidence_found, true);
    assert.equal(apiEndpoint.code_evidence_found, true);
    assert.equal(alternate.code_evidence_found, true);
});

test('safe endpoint summary covers object headers, invalid JSON, fetch error, and mismatch branches', () => {
    const target = {
        target_category: 'unresolved_large_gap',
        requested_schedule_external_id: '4830460',
        match_id: '53_20252026_4830460',
        requested_home_team: 'Brest',
        requested_away_team: 'Lille',
        requested_match_date: '2025-08-17T13:00:00.000Z',
        requested_status: 'finished',
    };
    const request = mod.buildDetailApiRequest({ external_id: '4830460' });
    const invalidJson = mod.buildSafeEndpointSummary({
        target,
        request,
        response: { statusCode: 'NaN', headers: { 'content-type': 'text/plain' } },
        bodyText: 'not-json',
    });
    const mismatch = mod.buildSafeEndpointSummary({
        target,
        request,
        response: { statusCode: 200, headers: { 'content-type': 'application/json' } },
        bodyText: fakeJsonBody({
            id: '4830460',
            home: 'Brest',
            away: 'Paris FC',
            date: '2025-08-18T13:00:00.000Z',
        }),
    });
    const fetchError = mod.buildSafeEndpointSummary({
        target,
        request,
        response: { status: 0 },
        bodyText: '',
        error: new Error('socket hang up'),
    });

    assert.equal(invalidJson.http_status, 0);
    assert.equal(invalidJson.parsed, false);
    assert.match(invalidJson.safe_error_summary, /JSON_PARSE_FAILED/);
    assert.equal(mismatch.team_safe_summary.status, 'mismatch');
    assert.equal(mismatch.date_rule_status, 'date_mismatch');
    assert.equal(mismatch.whether_endpoint_avoids_slug_reuse, 'unknown');
    assert.match(fetchError.safe_error_summary, /FETCH_ERROR/);
});

test('executeEndpointCheck covers missing fetch dependency and thrown fetch errors', async () => {
    const originalFetch = global.fetch;
    const target = mod.selectControlledLiveTargets(syntheticManifest(), syntheticL2V3QArtifact(), 1)[0];
    try {
        global.fetch = undefined;
        await assert.rejects(() => mod.executeEndpointCheck(target, {}), /FETCH_DEPENDENCY_MISSING/);
    } finally {
        global.fetch = originalFetch;
    }

    const summary = await mod.executeEndpointCheck(target, {
        fetchFn: async () => {
            throw new Error('network down');
        },
    });
    assert.equal(summary.http_status, 0);
    assert.match(summary.safe_error_summary, /FETCH_ERROR/);
});

test('controlled live checks continue when safe summaries pass and stop checks cover non-200', async () => {
    const targets = mod.selectControlledLiveTargets(syntheticManifest(), syntheticL2V3QArtifact(), 2);
    let calls = 0;
    const result = await mod.runControlledLiveChecks(targets, {
        fetchFn: async () => {
            calls += 1;
            return response(
                fakeJsonBody({
                    id: calls === 1 ? '4830460' : '4830458',
                    home: calls === 1 ? 'Brest' : 'Angers',
                    away: calls === 1 ? 'Lille' : 'Paris FC',
                    date: calls === 1 ? '2025-08-17T13:00:00.000Z' : '2025-08-17T15:15:00.000Z',
                })
            );
        },
    });

    assert.equal(result.checked_targets.length, 2);
    assert.equal(result.stopped_early, false);
    assert.equal(mod.summarizeControlledChecks(result, true).precise_detail_endpoint_found, true);
});

test('runCli covers help and invalid options; synthetic no-write success remains available without writing files', async () => {
    let helpOutput = '';
    let invalidOutput = '';
    const helpStatus = await mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = await mod.runCli(['--controlled-live-check=yes', '--network-authorization=no'], {
        stdout: text => (invalidOutput += text),
    });
    const successResult = await buildSyntheticRunResult({
        controlledLiveCheck: false,
        networkAuthorization: false,
        maxTargets: 0,
        writeFiles: false,
    });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /Usage:/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /network-authorization/);
    assert.equal(successResult.status, 0);
    assert.equal(successResult.ok, true);
    assert.equal(successResult.artifact.proposal_phase, 'Phase 5.21L2V3S');
    assert.equal(successResult.artifact.no_write, true);
});

test('L2V3S outputs avoid full raw data pageProps and source body payloads', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 1,
        fetchFn: async () => response(fakeJsonBody()),
    });
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('updated manifest is still rejected by the raw write runner gate', async () => {
    const result = await buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('runDetailApiEndpointFeasibility can write outputs to explicit temp paths', async () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3s-feasibility-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = await buildSyntheticRunResult({
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3S');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /endpoint feasibility result is not an accepted mapping/);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('repository L2V3S artifacts preserve feasibility-only and blocking semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_api_endpoint_feasibility.phase521l2v3s.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3S.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3S');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(manifest.phase_5_21_l2v3s_feasibility_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.match(report, /full API payload saved=false/);
});
