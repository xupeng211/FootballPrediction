'use strict';
/* eslint-disable max-lines -- L2V3AO execution contract tests intentionally cover the full safety surface. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function target(index = 0, baselineHash = 'a'.repeat(64)) {
    const externalId = String(4831000 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        batch_id: mod.BATCH_ID,
        source: mod.SOURCE,
        route: mod.ROUTE,
        raw_data_version: mod.RAW_VERSION,
        hash_strategy: mod.HASH_STRATEGY,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        schedule_external_id: externalId,
        accepted_detail_external_id: externalId,
        recapture_expected_identity: externalId,
        current_mapping_effective_status: 'reaccepted',
        current_baseline_effective_status: 'reaccepted',
        re_acceptance_execution_performed: true,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        baseline_hash: baselineHash,
    };
}

function pagePropsFor(targetValue) {
    return {
        content: {
            stats: [],
        },
        general: {
            matchId: targetValue.external_id,
            homeTeam: targetValue.home_team,
            awayTeam: targetValue.away_team,
            matchTimeUTC: targetValue.kickoff_time,
            status: targetValue.status,
            pageUrl: `/match/${targetValue.external_id}`,
        },
        header: {
            teams: [{ name: targetValue.home_team }, { name: targetValue.away_team }],
            status: {
                utcTime: targetValue.kickoff_time,
            },
        },
    };
}

function htmlFor(pageProps) {
    return `<html><head><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></head><body>safe fixture</body></html>`;
}

function fetchResultFor(targetValue, pageProps = pagePropsFor(targetValue), overrides = {}) {
    const body = htmlFor(pageProps);
    const requestIdentity = targetValue.accepted_detail_external_id || targetValue.external_id;
    const requestUrl = mod.buildFotMobMatchUrl(requestIdentity);
    return {
        ok: true,
        request_url: requestUrl,
        final_url: requestUrl,
        http_status: 200,
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body,
        ...overrides,
    };
}

function buildTargets(count = 50, options = {}) {
    return Array.from({ length: count }, (_value, index) => {
        const draft = target(index);
        const pageProps = pagePropsFor(draft);
        const baseline = options.hashMismatchAt === index ? 'b'.repeat(64) : mod.computeStablePagePropsHash(pageProps);
        return target(index, baseline);
    });
}

function enrichedTargets(targets = []) {
    return targets.map(item => ({
        target_id: item.target_id,
        match_id: item.match_id,
        external_id: item.external_id,
        schedule_external_id: item.external_id,
        source_page_url: `/match/${item.external_id}#${item.external_id}`,
        source_page_url_base: `/match/${item.external_id}`,
        source_url_fragment_external_id: item.external_id,
        accepted_detail_external_id: item.accepted_detail_external_id || item.external_id,
        current_mapping_effective_status: 'reaccepted',
        current_baseline_effective_status: 'reaccepted',
        re_acceptance_execution_performed: true,
        schedule_date: item.kickoff_time,
        schedule_home_team: item.home_team,
        schedule_away_team: item.away_team,
        identity_evidence_status: 'complete',
    }));
}

function manifest(targets = buildTargets()) {
    return {
        batch_id: mod.BATCH_ID,
        source: mod.SOURCE,
        route: mod.ROUTE,
        raw_data_version: mod.RAW_VERSION,
        hash_strategy: mod.HASH_STRATEGY,
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        next_required_step: 'controlled_no_write_payload_recapture_execution',
        phase_5_21_l2v3an_planning_status: 'completed_controlled_no_write_payload_recapture_planning',
        raw_write_execution_ready: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        candidate_targets: targets,
    };
}

function planArtifact(overrides = {}) {
    return {
        artifact_status: 'completed_controlled_no_write_payload_recapture_planning',
        planned_source_type: 'controlled_live_recapture_in_memory',
        planned_target_count: 50,
        live_recapture_execution_performed: false,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        in_memory_only: true,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        ...overrides,
    };
}

function enrichedArtifact(targets = buildTargets()) {
    return {
        artifact_status: 'completed_controlled_no_write_enriched_target_regeneration_execution',
        regenerated_target_count: 50,
        enriched_targets: enrichedTargets(targets),
    };
}

function identityAcceptance() {
    return {
        artifact_status: 'completed_identity_mapping_acceptance_review_execution',
        accepted_mapping_count: 50,
    };
}

function baselineAcceptance() {
    return {
        artifact_status: 'completed_baseline_acceptance_execution',
        baseline_accepted_count: 50,
    };
}

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        planArtifact: mod.PLAN_ARTIFACT_PATH,
        enrichedTargets: mod.ENRICHED_TARGETS_PATH,
        identityAcceptance: mod.IDENTITY_ACCEPTANCE_PATH,
        baselineAcceptance: mod.BASELINE_ACCEPTANCE_PATH,
        source: mod.SOURCE,
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        route: mod.ROUTE,
        rawVersion: mod.RAW_VERSION,
        hashStrategy: mod.HASH_STRATEGY,
        batchId: mod.BATCH_ID,
        targetCount: 50,
        noWriteRecaptureAuthorization: true,
        networkAuthorization: true,
        matchDetailRecaptureAuthorization: true,
        allowNoWriteRecaptureExecution: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowMatchesWrite: false,
        allowMatchesExternalIdWrite: false,
        allowRawWriteExecution: false,
        allowRawWriteRunnerWriteMode: false,
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
        persistCookiesTokensHeaders: false,
        uncontrolledRetry: false,
        concurrency: 1,
        retry: 0,
        requestDelayMs: 0,
        timeoutMs: 1000,
        writeFiles: false,
        unknown: [],
        ...overrides,
    };
}

function dependencies(targets = buildTargets(), overrides = {}) {
    return {
        manifest: manifest(targets),
        planArtifact: planArtifact(),
        enrichedArtifact: enrichedArtifact(targets),
        identityAcceptance: identityAcceptance(),
        baselineAcceptance: baselineAcceptance(),
        fetchResults: targets.map(item => fetchResultFor(item)),
        progress: () => {},
        generatedAt: '2026-05-26T00:00:00.000Z',
        ...overrides,
    };
}

test('parseArgs and validation cover unknown, positional, missing, and numeric guardrails', () => {
    const parsed = mod.parseArgs([
        'positional',
        '--source',
        'fotmob',
        '--unknown-flag=yes',
        '--write-files=maybe',
        '--target-count=abc',
        '--request-delay-ms=-1',
        '--timeout-ms=0',
        '--concurrency=2',
        '--retry=1',
    ]);
    const validation = mod.validateExecutionInput(parsed);
    const errors = validation.errors.join('\n');

    assert.equal(parsed.source, 'fotmob');
    assert.deepEqual(parsed.unknown, ['positional', 'unknown-flag']);
    assert.equal(parsed.writeFiles, true);
    assert.equal(validation.ok, false);
    assert.match(errors, /unknown arguments: positional, unknown-flag/);
    assert.match(errors, /target-count must be 50/);
    assert.match(errors, /request-delay-ms must be a non-negative integer/);
    assert.match(errors, /timeout-ms must be a positive integer/);
    assert.match(errors, /concurrency must be 1/);
    assert.match(errors, /retry must be 0/);
    assert.match(errors, /missing no-write-recapture-authorization=yes/);
    assert.match(errors, /missing allow-db-write=no/);
});

test('fetchHtml records safe errors for missing fetch, fetch failure, body read failure, and HTTP status', async t => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = undefined;
    t.after(() => {
        globalThis.fetch = originalFetch;
    });

    const missing = await mod.fetchHtml('https://www.fotmob.com/match/1', { fetchFn: null });
    const thrown = await mod.fetchHtml('https://www.fotmob.com/match/2', {
        fetchFn: async () => {
            throw new Error('failed for https://secret.example/token');
        },
    });
    const bodyRead = await mod.fetchHtml('https://www.fotmob.com/match/3', {
        fetchFn: async () => ({
            ok: true,
            status: 200,
            url: 'https://www.fotmob.com/match/3',
            text: async () => {
                throw new Error('body read failed');
            },
        }),
    });
    const rateLimited = await mod.fetchHtml('https://www.fotmob.com/match/4', {
        fetchFn: async () => ({
            ok: false,
            status: 429,
            url: 'https://www.fotmob.com/match/4',
            text: async () => 'Too many requests',
        }),
    });

    assert.equal(missing.error, 'FETCH_DEPENDENCY_MISSING');
    assert.match(thrown.error, /FETCH_ERROR/);
    assert.doesNotMatch(thrown.error, /secret\.example/);
    assert.match(bodyRead.error, /FETCH_BODY_READ_ERROR/);
    assert.equal(rateLimited.ok, false);
    assert.equal(rateLimited.http_status, 429);
    assert.equal(rateLimited.body_byte_length, Buffer.byteLength('Too many requests', 'utf8'));
});

test('HTML extraction and URL helpers fail closed without leaking source payloads', () => {
    const invalid = mod.extractNextDataJsonFromHtml(null);
    const missing = mod.extractNextDataJsonFromHtml('<html></html>');
    const malformed = mod.extractNextDataJsonFromHtml(
        '<script id="__NEXT_DATA__" type="application/json">{bad json}</script>'
    );

    assert.equal(invalid.error, 'INVALID_HTML');
    assert.equal(missing.error, 'NO_NEXT_DATA');
    assert.match(malformed.error, /NEXT_DATA_PARSE_ERROR/);
    assert.equal(mod.externalIdFromUrl('/match/4831001#4831001'), '4831001');
    assert.equal(mod.externalIdFromUrl('not a url #4831002'), '4831002');
    assert.equal(mod.externalIdFromUrl(''), null);
    assert.throws(() => mod.buildFotMobMatchUrl('abc'), /INVALID_EXTERNAL_ID/);
    assert.deepEqual(mod.summarizeStructure(null), {
        top_level_keys: [],
        has_content: false,
        has_general: false,
        has_header: false,
        content_key_count: 0,
        pageprops_path_count: 0,
        pageprops_content_path_count: 0,
    });
});

test('candidate and input artifact gates reject unsafe or malformed recapture prerequisites', () => {
    const targets = buildTargets();
    const badTargets = targets.map(item => ({ ...item }));
    badTargets[0].external_id = 'not-numeric';
    badTargets[0].schedule_external_id = '999';
    badTargets[0].source_url_fragment_external_id = '998';
    badTargets[0].match_id = 'bad';
    badTargets[0].baseline_hash = 'bad';
    badTargets[0].home_team = 'fake placeholder';
    badTargets[1].external_id = badTargets[2].external_id;
    badTargets[1].match_id = badTargets[2].match_id;
    badTargets[3].route = 'api_match_details';
    badTargets[4].hash_strategy = 'unstable';

    const candidateGate = mod.validateCandidateTargets(manifest(badTargets), enrichedArtifact(targets));
    const candidateErrors = candidateGate.errors.join('\n');
    const artifactGate = mod.validateInputArtifacts({
        manifest: {
            ...manifest(targets),
            batch_id: 'wrong',
            next_required_step: 'raw_write_execution',
            phase_5_21_l2v3an_planning_status: 'pending',
            raw_write_execution_ready: true,
            db_write_performed: true,
            raw_match_data_insert_performed: true,
        },
        planArtifact: planArtifact({
            artifact_status: 'pending',
            planned_source_type: 'wrong',
            planned_target_count: 49,
            live_recapture_execution_performed: true,
            full_payload_storage_allowed: true,
            raw_write_execution_ready: true,
        }),
        enrichedArtifact: { artifact_status: 'pending', regenerated_target_count: 49, enriched_targets: [] },
        identityAcceptance: { artifact_status: 'pending', accepted_mapping_count: 49 },
        baselineAcceptance: { artifact_status: 'pending', baseline_accepted_count: 49 },
    });
    const artifactErrors = artifactGate.errors.join('\n');

    assert.equal(candidateGate.ok, false);
    assert.match(candidateErrors, /external_id must be numeric/);
    assert.match(candidateErrors, /source_url_fragment_external_id must match external_id/);
    assert.match(candidateErrors, /match_id must match league\/season\/external_id/);
    assert.match(candidateErrors, /baseline_hash must be 64 hex/);
    assert.match(candidateErrors, /fake\/invented\/placeholder marker blocked/);
    assert.match(candidateErrors, /duplicate external_id/);
    assert.match(candidateErrors, /duplicate match_id/);
    assert.match(candidateErrors, /route mismatch/);
    assert.match(candidateErrors, /hash_strategy mismatch/);
    assert.equal(artifactGate.ok, false);
    assert.match(artifactErrors, /manifest batch_id mismatch/);
    assert.match(artifactErrors, /manifest next_required_step must be controlled_no_write_payload_recapture_execution/);
    assert.match(artifactErrors, /L2V3AN must not have already performed live recapture/);
    assert.match(artifactErrors, /L2V3AN payload safety flags must remain no-store\/no-print\/in-memory/);
    assert.match(artifactErrors, /L2V3AE accepted mapping count must be 50/);
});

test('L2V3AO validates no-write live recapture authorization and blocks write flags', () => {
    const parsed = mod.parseArgs([
        '--manifest',
        mod.MANIFEST_PATH,
        '--plan-artifact',
        mod.PLAN_ARTIFACT_PATH,
        '--enriched-targets',
        mod.ENRICHED_TARGETS_PATH,
        '--identity-acceptance',
        mod.IDENTITY_ACCEPTANCE_PATH,
        '--baseline-acceptance',
        mod.BASELINE_ACCEPTANCE_PATH,
        '--source=fotmob',
        '--league-id=53',
        '--league-name=Ligue 1',
        '--season=2025/2026',
        '--route=html_hydration',
        '--raw-version=fotmob_pageprops_v2',
        '--hash-strategy=stable_pageprops_payload_v1',
        `--batch-id=${mod.BATCH_ID}`,
        '--target-count=50',
        '--no-write-recapture-authorization=yes',
        '--network-authorization=yes',
        '--match-detail-recapture-authorization=yes',
        '--allow-no-write-recapture-execution=yes',
        '--allow-db-write=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-raw-write-execution=yes',
        '--allow-raw-write-runner-write-mode=yes',
        '--print-full-pageprops=yes',
        '--final-db-write-confirmation=yes',
        '--concurrency=1',
        '--retry=0',
    ]);
    const validation = mod.validateExecutionInput(parsed);
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /allow-db-write=yes is blocked/);
    assert.match(errors, /allow-raw-match-data-write=yes is blocked/);
    assert.match(errors, /allow-raw-write-execution=yes is blocked/);
    assert.match(errors, /allow-raw-write-runner-write-mode=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
    assert.match(errors, /final-db-write-confirmation=yes is blocked/);
});

test('successful synthetic recapture remains no-write and not raw-write-ready', async () => {
    const targets = buildTargets();
    const result = await mod.runNoWritePayloadRecaptureExecution(validInput(), dependencies(targets));

    assert.equal(result.ok, true);
    assert.equal(result.artifact.no_write_payload_recapture_execution_performed, true);
    assert.equal(result.artifact.live_recapture_performed, true);
    assert.equal(result.artifact.network_request_performed, true);
    assert.equal(result.artifact.db_write_performed, false);
    assert.equal(result.artifact.raw_match_data_insert_performed, false);
    assert.equal(result.artifact.raw_write_execution_performed, false);
    assert.equal(result.artifact.raw_write_runner_write_mode_used, false);
    assert.equal(result.artifact.successful_recapture_count, 50);
    assert.equal(result.artifact.raw_write_execution_ready, false);
    assert.equal(result.artifact.requires_separate_raw_write_execution_authorization, true);
});

test('hash mismatch stops immediately and records only safe metadata', async () => {
    const targets = buildTargets(50, { hashMismatchAt: 0 });
    const result = await mod.runNoWritePayloadRecaptureExecution(validInput(), dependencies(targets));
    const combined = `${JSON.stringify(result.artifact)}\n${result.report}`;

    assert.equal(result.ok, false);
    assert.equal(result.status, 4);
    assert.equal(result.artifact.attempted_recapture_count, 1);
    assert.equal(result.artifact.stopped_early, true);
    assert.equal(result.artifact.stop_reason, 'hash_mismatch_unexplained');
    assert.equal(result.artifact.hash_mismatch_count, 1);
    assert.equal(result.artifact.db_write_performed, false);
    assert.equal(result.artifact.raw_match_data_insert_performed, false);
    assert.equal(combined.includes('"raw_data":'), false);
    assert.equal(combined.includes('"pageProps":'), false);
    assert.equal(combined.includes('__NEXT_DATA__'), false);
    assert.equal(combined.includes('<html'), false);
});

test('HTTP 403 and captcha markers stop without retry or payload persistence', async () => {
    const targets = buildTargets();
    const forbidden = {
        ok: false,
        request_url: mod.buildFotMobMatchUrl(targets[0].external_id),
        final_url: mod.buildFotMobMatchUrl(targets[0].external_id),
        http_status: 403,
        body_byte_length: 31,
        body: 'captcha attention required',
        error: 'HTTP_403',
    };
    const result = await mod.runNoWritePayloadRecaptureExecution(
        validInput(),
        dependencies(targets, { fetchResults: [forbidden] })
    );

    assert.equal(result.ok, false);
    assert.equal(result.artifact.attempted_recapture_count, 1);
    assert.equal(result.artifact.http_403_count, 1);
    assert.equal(result.artifact.stop_reason, 'http_403');
    assert.deepEqual(result.artifact.per_target_results[0].block_markers, ['captcha', 'cloudflare', 'http_403']);
    assert.equal(result.artifact.full_payload_saved, false);
    assert.equal(result.artifact.full_payload_printed, false);
});

test('HTTP 429, missing next data, missing pageProps, and schema drift stop with safe blockers', async () => {
    const targets = buildTargets();
    const rateLimited = await mod.recaptureTarget(targets[0], 0, validInput(), {
        fetchResults: [
            {
                ok: false,
                request_url: mod.buildFotMobMatchUrl(targets[0].external_id),
                final_url: mod.buildFotMobMatchUrl(targets[0].external_id),
                http_status: 429,
                body_byte_length: 17,
                body: 'rate limit',
                error: 'HTTP_429',
            },
        ],
    });
    const noNextData = await mod.recaptureTarget(targets[0], 0, validInput(), {
        fetchResults: [{ ...fetchResultFor(targets[0]), body: '<html></html>' }],
    });
    const noPageProps = await mod.recaptureTarget(targets[0], 0, validInput(), {
        fetchResults: [
            {
                ...fetchResultFor(targets[0]),
                body: htmlFor(null).replace('"pageProps":null', '"other":true'),
            },
        ],
    });
    const noContentPageProps = {
        ...pagePropsFor(targets[0]),
        content: undefined,
    };
    const noContentTarget = target(0, mod.computeStablePagePropsHash(noContentPageProps));
    const schemaDrift = await mod.recaptureTarget(noContentTarget, 0, validInput(), {
        fetchResults: [fetchResultFor(noContentTarget, noContentPageProps)],
    });

    assert.equal(rateLimited.stopping_rule_triggered, 'http_429');
    assert.equal(noNextData.stopping_rule_triggered, 'parse_failure');
    assert.match(noNextData.safe_error_summary, /NO_NEXT_DATA/);
    assert.equal(noPageProps.stopping_rule_triggered, 'parse_failure');
    assert.match(noPageProps.safe_error_summary, /PAGE_PROPS_NOT_FOUND/);
    assert.equal(schemaDrift.stopping_rule_triggered, 'unexpected_schema_drift');
    assert.equal(schemaDrift.full_payload_saved, false);
    assert.equal(schemaDrift.full_payload_printed, false);
});

test('identity mismatch stops before raw write readiness can be inferred', async () => {
    const targets = buildTargets();
    const wrongPageProps = pagePropsFor({ ...targets[0], external_id: '9999999' });
    const result = await mod.runNoWritePayloadRecaptureExecution(
        validInput(),
        dependencies(targets, {
            fetchResults: [fetchResultFor(targets[0], wrongPageProps)],
        })
    );

    assert.equal(result.ok, false);
    assert.equal(result.artifact.stop_reason, 'identity_mismatch');
    assert.equal(result.artifact.identity_mismatch_count, 1);
    assert.equal(result.artifact.raw_write_execution_ready, false);
    assert.equal(result.artifact.recapture_success_does_not_authorize_raw_write, true);
});

test('sequential recapture reports progress, partial summary, and stops after first blocker', async () => {
    const targets = buildTargets(3, { hashMismatchAt: 1 });
    const progress = [];
    const results = await mod.recaptureTargetsSequential(targets, validInput({ requestDelayMs: 0 }), {
        fetchResults: targets.map(item => fetchResultFor(item)),
        progress: item => progress.push(item),
    });
    const summary = mod.summarizeResults(results, 3);

    assert.equal(results.length, 2);
    assert.equal(progress.length, 2);
    assert.equal(summary.successful_recapture_count, 1);
    assert.equal(summary.blocked_recapture_count, 1);
    assert.equal(summary.recapture_result_status, 'partial_success_blocked_no_write');
    assert.equal(summary.next_required_step, 'partial_recapture_review_planning');
});

test('writes result artifact, report, and manifest metadata to explicit temp paths', async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ao-'));
    const artifactPath = path.join(tempDir, 'result.json');
    const reportPath = path.join(tempDir, 'report.md');
    const manifestPath = path.join(tempDir, 'manifest.json');
    const targets = buildTargets(50, { hashMismatchAt: 0 });
    const result = await mod.runNoWritePayloadRecaptureExecution(
        validInput({
            manifest: mod.MANIFEST_PATH,
            artifactOutput: artifactPath,
            reportOutput: reportPath,
            writeFiles: true,
        }),
        dependencies(targets, {
            writeJsonFile: (filePath, value) => {
                fs.writeFileSync(
                    filePath === mod.MANIFEST_PATH ? manifestPath : filePath,
                    `${JSON.stringify(value, null, 4)}\n`
                );
            },
            writeTextFile: (filePath, value) => {
                fs.writeFileSync(filePath, value);
            },
        })
    );

    assert.equal(result.ok, false);
    assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, mod.PHASE);
    assert.match(fs.readFileSync(reportPath, 'utf8'), /raw_write_execution_ready=false/);
    assert.equal(
        JSON.parse(fs.readFileSync(manifestPath, 'utf8')).next_required_step,
        'no_write_payload_recapture_blocker_investigation'
    );
});

test('runCli covers help, invalid input, and blocked JSON output without writes', async () => {
    const originalStdout = process.stdout.write;
    const chunks = [];
    process.stdout.write = value => {
        chunks.push(String(value));
        return true;
    };

    try {
        const help = await mod.runCli(['--help']);
        const invalid = await mod.runCli(['--source=fotmob']);
        const targets = buildTargets(50, { hashMismatchAt: 0 });
        const blocked = await mod.runCli(validInput(), dependencies(targets));

        assert.equal(help.status, 0);
        assert.match(chunks[0], /controlled no-write payload recapture execution/);
        assert.equal(invalid.status, 2);
        assert.equal(blocked.status, 4);
        assert.match(chunks.join('\n'), /"raw_match_data_insert_performed": false/);
        assert.match(chunks.join('\n'), /"raw_write_execution_ready": false/);
    } finally {
        process.stdout.write = originalStdout;
    }
});

test('module load avoids DB, browser, child process, and raw write runner imports', t => {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (/pg|playwright|puppeteer|child_process|single_league|renewed_pageprops_v2_raw_write/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });

    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runNoWritePayloadRecaptureExecution, 'function');
});

test('repository L2V3AO artifact, when present, preserves no-write safety', () => {
    const artifactPath = path.join(PROJECT_ROOT, mod.RESULT_ARTIFACT_PATH);
    if (!fs.existsSync(artifactPath)) return;
    const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
    const report = fs.readFileSync(path.join(PROJECT_ROOT, mod.REPORT_PATH), 'utf8');
    const manifestJson = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, mod.MANIFEST_PATH), 'utf8'));

    assert.equal(artifact.proposal_phase, mod.PHASE);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_runner_write_mode_used, false);
    assert.equal(artifact.full_payload_saved, false);
    assert.equal(artifact.full_payload_printed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(manifestJson.phase_5_21_l2v3ao_artifact_path, mod.RESULT_ARTIFACT_PATH);
    assert.match(report, /safe_metadata_only=true/);
});
