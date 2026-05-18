'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js');
const PREVIEW_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_preview.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const preview = require(PREVIEW_PATH);

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        route: 'html_hydration',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        renewedRawWriteAuthorization: true,
        finalDbWriteConfirmation: true,
        networkAuthorization: true,
        matchDetailRecaptureAuthorization: true,
        allowDbWrite: true,
        allowRawMatchDataWrite: true,
        allowControlledWrite: true,
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
        concurrency: 1,
        retry: 0,
        requestDelayMs: 0,
        printFullBody: false,
        saveFullBody: false,
        printFullJson: false,
        saveFullJson: false,
        printFullPageprops: false,
        saveFullPageprops: false,
        ...overrides,
    };
}

function fakePageProps(externalId, overrides = {}) {
    return {
        content: {
            matchFacts: { infoBox: { Tournament: 'Ligue 1' } },
            lineup: { home: [], away: [] },
            liveticker: { events: [] },
            playerStats: { players: [] },
            shotmap: { shots: [] },
            stats: { Periods: { All: { stats: [{ key: 'Expected goals', stats: [1.1, 0.9] }] } } },
            h2h: { matches: [] },
            table: { all: [] },
        },
        general: { matchId: externalId, leagueId: 53 },
        header: { teams: [{ name: `Home ${externalId}` }, { name: `Away ${externalId}` }] },
        seo: { eventJSONLD: { '@type': 'SportsEvent' } },
        translations: { ok: true },
        fallback: false,
        nav: { locale: 'en' },
        ongoing: false,
        ssr: true,
        ...overrides,
    };
}

function fakeHtml(externalId, pageProps = fakePageProps(externalId)) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></body></html>`;
}

function fetchResultFor(externalId, overrides = {}) {
    const body = overrides.body ?? fakeHtml(externalId, overrides.pageProps || fakePageProps(externalId));
    const status = overrides.http_status ?? overrides.status ?? 200;
    return {
        ok: overrides.ok ?? (status >= 200 && status < 300),
        request_url: `https://www.fotmob.com/match/${externalId}`,
        final_url: `https://www.fotmob.com/match/${externalId}`,
        http_status: status,
        content_type: overrides.content_type || 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body_sha256: `body-sha-${externalId}`,
        body,
        error: overrides.error,
    };
}

function baselineHash(externalId, overrides = {}) {
    return preview.computeStablePagePropsHash(fakePageProps(externalId, overrides));
}

function candidate(index, overrides = {}) {
    const externalId = String(4830460 + index);
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
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: `2025-08-${String((index % 20) + 1).padStart(2, '0')}T18:45:00.000Z`,
        match_date: `2025-08-${String((index % 20) + 1).padStart(2, '0')}T18:45:00.000Z`,
        status: 'finished',
        target_status: 'preflight_passed',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: baselineHash(externalId),
        write_status: 'blocked_missing_matches_fk_prerequisite',
        write_execution_status: 'blocked_missing_matches_fk_prerequisite',
        write_plan_status: 'eligible_for_insert',
        matches_seed_status: 'inserted_matches_identity',
        failure_reason: 'blocked_missing_matches_fk_prerequisite',
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution',
        ...overrides,
    };
}

function candidates(overridesByIndex = {}) {
    return Array.from({ length: 50 }, (_, index) => candidate(index, overridesByIndex[index] || {}));
}

function knownCompleted() {
    return ['4830746', '4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754'].map(externalId => ({
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
        target_status: 'already_completed',
    }));
}

function manifest(overrides = {}) {
    return {
        schema_version: 'target_manifest_proposal_v1',
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        known_completed_targets: knownCompleted(),
        candidate_targets: candidates(),
        matches_identity_seed_execution_status: 'completed',
        post_seed_matches_identity_verification_status: 'completed',
        raw_write_fk_prerequisite_status: 'satisfied',
        raw_write_retry_readiness_status: 'ready_for_renewed_authorization',
        eligible_raw_insert_count: 50,
        expected_raw_match_data_after_retry: 68,
        write_execution_status: 'blocked_missing_matches_fk_prerequisite',
        raw_match_data_write_status: 'not_executed',
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution',
        ...overrides,
    };
}

function protectedRows(overrides = {}) {
    const rows = {
        matches: 60,
        bookmaker_odds_history: 2,
        raw_match_data: 18,
        l3_features: 2,
        match_features_training: 2,
        predictions: 2,
        ...overrides,
    };
    return Object.entries(rows).map(([table_name, rowCount]) => ({ table_name, rows: rowCount }));
}

function constraintRows() {
    return [
        { conname: 'raw_match_data_match_id_data_version_key', definition: 'UNIQUE (match_id, data_version)' },
        { conname: 'raw_match_data_match_id_fkey', definition: 'FOREIGN KEY (match_id) REFERENCES matches(match_id)' },
        { conname: 'raw_data_not_empty', definition: 'CHECK raw_data_not_empty' },
        { conname: 'raw_data_has_match_id', definition: 'CHECK raw_data_has_match_id' },
        { conname: 'collected_at_not_null', definition: 'CHECK collected_at_not_null' },
    ];
}

function matchRows(targets = candidates(), overridesByIndex = {}) {
    return targets.map((target, index) => ({
        match_id: target.match_id,
        external_id: target.external_id,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date,
        status: target.status,
        is_finished: target.status === 'finished',
        data_source: 'fotmob',
        pipeline_status: 'pending',
        ...(overridesByIndex[index] || {}),
    }));
}

function fetchResultsByExternalId(targets = candidates(), overridesByExternalId = {}) {
    return Object.fromEntries(
        targets.map(target => [
            target.external_id,
            fetchResultFor(target.external_id, overridesByExternalId[target.external_id] || {}),
        ])
    );
}

function insertedRows(targets = candidates()) {
    return targets.map((target, index) => ({
        id: index + 100,
        match_id: target.match_id,
        external_id: target.external_id,
        data_version: 'fotmob_pageprops_v2',
        data_hash: target.baseline_hash,
        collected_at: '2026-05-18T00:00:00.000Z',
        has_meta: true,
        has_match_id: true,
        has_pageprops: true,
        meta_hash_strategy: 'stable_pageprops_payload_v1',
    }));
}

function fakeClient(options = {}) {
    const queries = [];
    return {
        queries,
        async query(sql, values = []) {
            queries.push({ sql: String(sql), values });
            const normalized = String(sql).trim().replace(/\s+/g, ' ').toUpperCase();
            if (['BEGIN', 'COMMIT', 'ROLLBACK'].includes(normalized)) return { rows: [] };
            if (/^INSERT INTO RAW_MATCH_DATA/.test(normalized)) {
                if (options.throwOnInsert) throw new Error('insert exploded');
                return { rows: options.insertRows || [] };
            }
            return { rows: [] };
        },
    };
}

function successDeps(targets = candidates(), overrides = {}) {
    const rows = insertedRows(targets);
    return {
        manifest: manifest({ candidate_targets: targets }),
        protectedTableRowsBefore: protectedRows(),
        protectedTableRowsInsideTransaction: protectedRows({ raw_match_data: 68 }),
        protectedTableRowsAfter: protectedRows({ raw_match_data: 68 }),
        constraintRows: constraintRows(),
        matchRows: matchRows(targets),
        existingV2Rows: [],
        existingV2RowsInsideTransaction: [],
        postWriteRowsInsideTransaction: rows,
        postWriteRowsAfter: rows,
        duplicateRowsInsideTransaction: [],
        duplicateRowsAfter: [],
        fetchResultsByExternalId: fetchResultsByExternalId(targets),
        client: fakeClient({ insertRows: rows }),
        progress: () => {},
        generatedAt: '2026-05-18T00:00:00.000Z',
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
        ...overrides,
    };
}

test('valid input succeeds', () => {
    const result = mod.validateExecutionInput(validInput());
    assert.equal(result.ok, true);
});

test('required authorization and write flags are enforced', () => {
    for (const [key, expected] of [
        ['renewedRawWriteAuthorization', false],
        ['finalDbWriteConfirmation', false],
        ['allowDbWrite', false],
        ['allowRawMatchDataWrite', false],
        ['allowControlledWrite', false],
    ]) {
        const result = mod.validateExecutionInput(validInput({ [key]: expected }));
        assert.equal(result.ok, false);
        assert.match(result.errors.join('\n'), /yes is required|missing/);
    }
});

test('blocked yes flags are rejected', () => {
    for (const key of [
        'allowMatchesWrite',
        'allowBookmakerOddsWrite',
        'allowFeatureWrite',
        'allowSchemaMigration',
        'allowParserImplementation',
        'allowFeatureExtraction',
        'allowTraining',
        'allowPrediction',
        'allowBrowserRuntime',
        'allowProxyRuntime',
        'printFullBody',
        'saveFullBody',
        'printFullJson',
        'saveFullJson',
        'printFullPageprops',
        'saveFullPageprops',
        'allowOddsWrite',
    ]) {
        const result = mod.validateExecutionInput(validInput({ [key]: true }));
        assert.equal(result.ok, false, key);
    }
});

test('manifest gate accepts post-seed retry readiness metadata', () => {
    const result = mod.validateManifestGate(manifest());
    assert.equal(result.ok, true);
    assert.equal(result.candidate_targets, 50);
    assert.deepEqual(result.matches_seed_status_distribution, { inserted_matches_identity: 50 });
});

test('manifest gate requires prior FK-blocked candidate state', () => {
    const result = mod.validateManifestGate(
        manifest({ candidate_targets: candidates({ 0: { write_status: 'not_started' } }) })
    );
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /write_status must be blocked_missing_matches_fk_prerequisite/);
});

test('DB baseline expects post-seed matches=60 and raw_match_data=18', async () => {
    const deps = successDeps(candidates(), {
        protectedTableRowsBefore: protectedRows({ matches: 10 }),
        client: fakeClient(),
    });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /DB_BASELINE_BLOCKED/);
    assert.equal(
        deps.client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        false
    );
});

test('missing matches identity rows block before network and transaction', async () => {
    const deps = successDeps(candidates(), {
        matchRows: matchRows(candidates()).slice(1),
        client: fakeClient(),
    });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'MATCHES_IDENTITY_GATE_BLOCKED');
    assert.equal(result.payload.matches_identity_gate.missing_matches_count, 1);
    assert.equal(
        deps.client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        false
    );
});

test('identity mismatch blocks before network and transaction', async () => {
    const deps = successDeps(candidates(), {
        matchRows: matchRows(candidates(), { 0: { external_id: '9999999' } }),
        client: fakeClient(),
    });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.equal(result.payload.matches_identity_gate.external_id_mismatch_count, 1);
    assert.equal(
        deps.client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        false
    );
});

test('existing v2 rows block before network and transaction', async () => {
    const targets = candidates();
    const deps = successDeps(targets, {
        existingV2Rows: [
            { match_id: targets[0].match_id, external_id: targets[0].external_id, data_version: 'fotmob_pageprops_v2' },
        ],
        client: fakeClient(),
    });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'EXISTING_V2_RAW_ROWS_BLOCKED');
    assert.equal(result.payload.existing_raw_gate.existing_v2_raw_rows_for_candidates, 1);
    assert.equal(
        deps.client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        false
    );
});

test('hash drift blocks before transaction', async () => {
    const targets = candidates();
    const driftExternalId = targets[0].external_id;
    const deps = successDeps(targets, {
        fetchResultsByExternalId: fetchResultsByExternalId(targets, {
            [driftExternalId]: { pageProps: fakePageProps(driftExternalId, { drift: true }) },
        }),
        client: fakeClient(),
    });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.equal(result.payload.blocked_reason, 'RECAPTURE_HASH_GATE_BLOCKED');
    assert.equal(result.payload.recapture_hash_gate.hash_drift_count, 1);
    assert.equal(
        deps.client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        false
    );
});

test('all gates pass inserts exactly 50 raw_match_data rows and commits', async () => {
    const deps = successDeps();
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 0);
    assert.equal(result.payload.inserted_raw_match_data_count, 50);
    assert.equal(result.payload.row_counts_before.raw_match_data, 18);
    assert.equal(result.payload.row_counts_after.raw_match_data, 68);
    assert.equal(result.payload.post_write_verification.protected_tables_unchanged, true);
    assert.equal(
        deps.client.queries.some(query => /^BEGIN$/i.test(query.sql)),
        true
    );
    assert.equal(
        deps.client.queries.some(query => /^COMMIT$/i.test(query.sql)),
        true
    );
    assert.equal(
        deps.client.queries.some(query => /^ROLLBACK$/i.test(query.sql)),
        false
    );
});

test('inserted count mismatch rolls back', async () => {
    const targets = candidates();
    const rows = insertedRows(targets).slice(0, 49);
    const deps = successDeps(targets, { client: fakeClient({ insertRows: rows }) });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /INSERTED_COUNT_MISMATCH:49/);
    assert.equal(
        deps.client.queries.some(query => /^ROLLBACK$/i.test(query.sql)),
        true
    );
});

test('protected table change inside transaction rolls back', async () => {
    const deps = successDeps(candidates(), {
        protectedTableRowsInsideTransaction: protectedRows({ raw_match_data: 68, predictions: 3 }),
    });
    const result = await mod.runCli(validInput(), deps);
    assert.equal(result.status, 1);
    assert.match(result.payload.blocked_reason, /IN_TRANSACTION_VERIFICATION_FAILED/);
    assert.equal(
        deps.client.queries.some(query => /^ROLLBACK$/i.test(query.sql)),
        true
    );
});

test('manifest update records L2V3 execution metadata', () => {
    const payload = {
        ok: true,
        recapture_hash_gate: { attempted_target_count: 50 },
        attempted_raw_insert_count: 50,
        inserted_raw_match_data_count: 50,
        row_counts_before: { raw_match_data: 18 },
        row_counts_after: { raw_match_data: 68 },
        post_write_verification: { protected_tables_unchanged: true, existing_v2_raw_rows_for_candidates: 50 },
        transaction: { committed: true },
        blockers: [],
        next_required_step: 'post_l2v3_pageprops_v2_canonical_read_completeness_audit',
    };
    const updated = mod.updateManifestWithExecution(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.phase_5_21_l2v3_execution_status, 'completed');
    assert.equal(updated.raw_write_execution_authorization_status, 'explicitly_authorized_by_user');
    assert.equal(updated.inserted_raw_match_data_count, 50);
    assert.equal(updated.raw_match_data_after_count, 68);
    assert.equal(updated.candidate_targets[0].write_status, 'inserted_raw_match_data');
});

test('report does not contain full raw_data/pageProps/source body', () => {
    const report = mod.buildReport({
        ok: true,
        authorization: {
            renewed_raw_write_authorization: true,
            final_db_write_confirmation: true,
            request_delay_ms: 0,
        },
        manifest_gate: { ok: true, candidate_targets: 50, known_completed_targets: 8, baseline_hash_ready_count: 50 },
        schema_gate: { unique_match_id_data_version_present: true, old_unique_match_id_absent: true, fk_present: true },
        matches_identity_gate: { matches_found_count: 50, missing_matches_count: 0, identity_mismatch_count: 0 },
        existing_raw_gate: { existing_v2_raw_rows_for_candidates: 0 },
        recapture_hash_gate: {
            attempted_target_count: 50,
            request_count: 50,
            recapture_success_count: 50,
            failed_count: 0,
            blocked_count: 0,
            hash_match_count: 50,
            hash_drift_count: 0,
        },
        transaction: { began: true, committed: true, rolled_back: false },
        attempted_raw_insert_count: 50,
        inserted_raw_match_data_count: 50,
        row_counts_before: { matches: 60, raw_match_data: 18 },
        row_counts_after: {
            matches: 60,
            raw_match_data: 68,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        next_required_step: 'post_l2v3_pageprops_v2_canonical_read_completeness_audit',
    });
    assert.doesNotMatch(report, /"pageProps":/);
    assert.doesNotMatch(report, /SECRET_PAGEPROPS_SHOULD_NOT_PRINT/);
});

test('no forbidden runtime imports while loading module', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|odds_harvest_pipeline/);
    assert.doesNotMatch(source, /unlinkSync|rmSync|rmdirSync/);
});

test('query path only issues raw_match_data insert and transaction statements', async () => {
    const deps = successDeps();
    await mod.runCli(validInput(), deps);
    const sql = deps.client.queries.map(query => query.sql).join('\n');
    assert.match(sql, /INSERT INTO raw_match_data/i);
    assert.doesNotMatch(sql, /INSERT INTO matches/i);
    assert.doesNotMatch(sql, /INSERT INTO bookmaker_odds_history/i);
    assert.doesNotMatch(sql, /INSERT INTO l3_features/i);
    assert.doesNotMatch(sql, /INSERT INTO match_features_training/i);
    assert.doesNotMatch(sql, /INSERT INTO predictions/i);
});
