'use strict';

/* eslint-disable max-lines */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/post_seed_matches_identity_raw_write_readiness_audit.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const HASH = 'a'.repeat(64);

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        readinessAuditAuthorization: true,
        allowDbWrite: false,
        allowMatchesWrite: false,
        allowRawMatchDataWrite: false,
        allowControlledWrite: false,
        allowNetwork: false,
        allowMatchDetailFetch: false,
        allowSchemaMigration: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        ...overrides,
    };
}

function validArgv(overrides = {}) {
    const base = {
        manifest: mod.MANIFEST_PATH,
        source: 'fotmob',
        'league-id': '53',
        'league-name': 'Ligue 1',
        season: '2025/2026',
        'batch-id': mod.BATCH_ID,
        'target-count': '50',
        'readiness-audit-authorization': 'yes',
        'allow-db-write': 'no',
        'allow-matches-write': 'no',
        'allow-raw-match-data-write': 'no',
        'allow-controlled-write': 'no',
        'allow-network': 'no',
        'allow-match-detail-fetch': 'no',
        'allow-schema-migration': 'no',
        'allow-parser-implementation': 'no',
        'allow-feature-extraction': 'no',
        'allow-training': 'no',
        'allow-prediction': 'no',
        ...overrides,
    };
    return Object.entries(base).flatMap(([key, value]) => [`--${key}`, value]);
}

function candidate(index, overrides = {}) {
    const externalId = String(4830460 + index);
    const day = String((index % 20) + 1).padStart(2, '0');
    return {
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        source_inventory_route: 'source_inventory',
        raw_data_version: mod.DATA_VERSION,
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: `2025-08-${day}T18:45:00.000Z`,
        match_date: `2025-08-${day}T18:45:00.000Z`,
        status: 'finished',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: HASH,
        write_plan_status: 'eligible_for_insert',
        matches_seed_status: 'inserted_matches_identity',
        ...overrides,
    };
}

function candidates50(overridesByIndex = {}) {
    return Array.from({ length: 50 }, (_unused, index) => candidate(index, overridesByIndex[index] || {}));
}

function manifest(overrides = {}) {
    return {
        schema_version: 'target_manifest_proposal_v1',
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        known_completed_targets: Array.from({ length: 8 }, (_unused, index) => ({
            match_id: `53_20252026_${4830746 + index}`,
            external_id: String(4830746 + index),
        })),
        candidate_targets: candidates50(),
        matches_identity_seed_execution_status: 'completed',
        write_execution_status: 'blocked_missing_matches_fk_prerequisite',
        required_next_step: 'post_seed_matches_identity_verification_raw_write_retry_readiness_audit',
        ...overrides,
    };
}

function protectedRows(counts = mod.EXPECTED_DB_COUNTS) {
    return Object.entries(counts).map(([table_name, rows]) => ({ table_name, rows }));
}

function rawConstraints(overrides = {}) {
    const rows = [
        ['raw_match_data_match_id_data_version_key', 'u', 'UNIQUE (match_id, data_version)'],
        ['raw_match_data_match_id_fkey', 'f', 'FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE'],
        ['raw_match_data_pkey', 'p', 'PRIMARY KEY (id)'],
    ];
    if (overrides.oldUnique) rows.push(['raw_match_data_match_id_key', 'u', 'UNIQUE (match_id)']);
    return rows
        .filter(([name]) => !new Set(overrides.omit || []).has(name))
        .map(([conname, contype, definition]) => ({ conname, contype, definition }));
}

function matchRowsFor(candidates = candidates50(), overridesByIndex = {}) {
    return candidates.map((target, index) => ({
        match_id: target.match_id,
        external_id: target.external_id,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: target.home_team,
        away_team: target.away_team,
        match_date: target.match_date || target.kickoff_time,
        status: target.status,
        is_finished: target.status === 'finished',
        data_source: 'fotmob',
        pipeline_status: 'pending',
        ...(overridesByIndex[index] || {}),
    }));
}

function buildPayload(customManifest = manifest(), options = {}) {
    const targets = customManifest.candidate_targets || [];
    return mod.buildAuditPayload({
        input: validInput(),
        manifest: customManifest,
        protectedTableRows: protectedRows(options.counts || mod.EXPECTED_DB_COUNTS),
        candidateMatchRows: options.matchRows || matchRowsFor(targets),
        rawConstraintRows: options.constraints || rawConstraints(options.constraintOptions),
        existingV2Rows: options.existingV2Rows || [],
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
}

class FakeClient {
    constructor(options = {}) {
        this.options = options;
        this.queries = [];
    }

    async query(sql, params = []) {
        this.queries.push({ sql, params });
        const compact = String(sql).replace(/\s+/g, ' ').trim();
        if (/\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|LOCK|COPY|MERGE)\b/i.test(compact)) {
            throw new Error(`unexpected write query: ${compact}`);
        }
        if (compact.includes("SELECT 'matches' AS table_name")) {
            return { rows: protectedRows(this.options.counts || mod.EXPECTED_DB_COUNTS) };
        }
        if (compact.includes('FROM matches') && compact.includes('WHERE match_id = ANY')) {
            return { rows: this.options.matchRows || matchRowsFor(this.options.candidates || candidates50()) };
        }
        if (compact.includes('FROM pg_constraint')) {
            return { rows: this.options.constraints || rawConstraints() };
        }
        if (compact.includes('FROM raw_match_data')) {
            return { rows: this.options.existingV2Rows || [] };
        }
        return { rows: [], rowCount: 0 };
    }
}

test('valid input succeeds', () => {
    assert.equal(mod.validateAuditInput(validInput()).ok, true);
});

for (const [name, overrides] of [
    ['manifest missing fails', { manifest: null }],
    ['wrong manifest path fails', { manifest: 'docs/_manifests/wrong.json' }],
    ['source missing fails', { source: null }],
    ['source non-fotmob fails', { source: 'other' }],
    ['league-id missing fails', { leagueId: null }],
    ['league-id not 53 fails', { leagueId: 54 }],
    ['league-name missing fails', { leagueName: null }],
    ['league-name not Ligue 1 fails', { leagueName: 'Ligue 2' }],
    ['season missing fails', { season: null }],
    ['season not 2025/2026 fails', { season: '2024/2025' }],
    ['batch-id missing fails', { batchId: null }],
    ['batch-id wrong fails', { batchId: 'wrong' }],
    ['target-count not 50 fails', { targetCount: 49 }],
    ['readiness-audit-authorization=no blocked', { readinessAuditAuthorization: false }],
    ['allow-db-write=yes blocked', { allowDbWrite: true }],
    ['allow-matches-write=yes blocked', { allowMatchesWrite: true }],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }],
    ['allow-controlled-write=yes blocked', { allowControlledWrite: true }],
    ['allow-network=yes blocked', { allowNetwork: true }],
    ['allow-match-detail-fetch=yes blocked', { allowMatchDetailFetch: true }],
    ['allow-schema-migration=yes blocked', { allowSchemaMigration: true }],
    ['allow-parser-implementation=yes blocked', { allowParserImplementation: true }],
    ['allow-feature-extraction=yes blocked', { allowFeatureExtraction: true }],
    ['allow-training=yes blocked', { allowTraining: true }],
    ['allow-prediction=yes blocked', { allowPrediction: true }],
    ['execute-write=yes blocked', { executeWrite: true }],
    ['commit=yes blocked', { commit: true }],
    ['final-db-write-confirmation=yes blocked in audit phase', { finalDbWriteConfirmation: true }],
    ['allow-odds-write=yes blocked', { allowOddsWrite: true }],
]) {
    test(name, () => {
        assert.equal(mod.validateAuditInput(validInput(overrides)).ok, false);
    });
}

test('parseArgs maps Makefile flags', () => {
    const parsed = mod.parseArgs(validArgv());
    assert.equal(parsed.readinessAuditAuthorization, true);
    assert.equal(parsed.allowDbWrite, false);
});

test('parseArgs handles equals syntax, bare booleans, positional and unknown args', () => {
    const parsed = mod.parseArgs(['positional', '--source=fotmob', '--help', '--unexpected=value']);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['positional', 'unexpected']);
});

test('normalizeBooleanFlag covers aliases and fallback', () => {
    assert.equal(mod.normalizeBooleanFlag('y'), true);
    assert.equal(mod.normalizeBooleanFlag('off'), false);
    assert.equal(mod.normalizeBooleanFlag('maybe', 'fallback'), 'fallback');
});

test('missing no guardrail is blocked explicitly', () => {
    const result = mod.validateAuditInput(validInput({ allowNetwork: null }));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /missing allow-network=no/);
});

test('manifest candidate_targets not 50 fails', () => {
    assert.equal(buildPayload(manifest({ candidate_targets: candidates50().slice(0, 49) })).ok, false);
});

test('matches seed status not completed fails', () => {
    assert.equal(buildPayload(manifest({ matches_identity_seed_execution_status: 'blocked' })).ok, false);
});

test('manifest metadata mismatches are blocked', () => {
    const payload = buildPayload(
        manifest({
            schema_version: 'wrong',
            batch_id: 'wrong',
            source: 'other',
            league: { league_id: 1, league_name: 'Other', season: '2024/2025' },
            known_completed_targets: [],
            write_execution_status: 'completed',
        })
    );
    assert.equal(payload.ok, false);
    assert.match(payload.blocked_reason, /schema_version|batch_id|write_execution_status/);
});

for (const [name, override] of [
    ['candidate missing match_id blocked', { match_id: '' }],
    ['candidate invalid external_id blocked', { external_id: 'abc' }],
    ['candidate wrong match_id convention blocked', { match_id: '53_20252026_9999999' }],
    ['candidate missing home_team blocked', { home_team: '' }],
    ['candidate missing away_team blocked', { away_team: '' }],
    ['candidate missing match_date/kickoff_time blocked', { match_date: '', kickoff_time: '' }],
    ['candidate missing status blocked', { status: '' }],
    ['candidate missing baseline_hash blocked', { baseline_hash: '' }],
    ['candidate baseline_hash invalid blocked', { baseline_hash: 'not-a-hash' }],
    ['candidate preflight_status not hash_baseline_ready blocked', { preflight_status: 'pending' }],
    ['candidate write_plan_status blocked', { write_plan_status: 'blocked' }],
    ['candidate matches_seed_status blocked', { matches_seed_status: 'pending' }],
    ['candidate invented marker blocked', { invented_external_id: true }],
]) {
    test(name, () => {
        assert.equal(buildPayload(manifest({ candidate_targets: candidates50({ 0: override }) })).ok, false);
    });
}

test('duplicate match_id blocked', () => {
    const targets = candidates50({ 1: { match_id: '53_20252026_4830460', external_id: '4830460' } });
    const payload = buildPayload(manifest({ candidate_targets: targets }));
    assert.equal(payload.ok, false);
    assert.equal(payload.candidate_validation.duplicate_match_id_count, 1);
});

test('duplicate external_id blocked', () => {
    const targets = candidates50({ 1: { external_id: '4830460', match_id: '53_20252026_4830460' } });
    const payload = buildPayload(manifest({ candidate_targets: targets }));
    assert.equal(payload.ok, false);
    assert.equal(payload.candidate_validation.duplicate_external_id_count, 1);
});

test('missing matches rows -> readiness blocked', () => {
    const payload = buildPayload(manifest(), { matchRows: matchRowsFor(candidates50()).slice(0, 49) });
    assert.equal(payload.ok, false);
    assert.equal(payload.matches_identity_verification.missing_matches_count, 1);
});

test('identity mismatch -> readiness blocked', () => {
    const payload = buildPayload(manifest(), {
        matchRows: matchRowsFor(candidates50(), { 0: { season: '2024/2025' } }),
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.matches_identity_verification.identity_mismatch_count, 1);
});

test('external_id mismatch -> readiness blocked', () => {
    const payload = buildPayload(manifest(), { matchRows: matchRowsFor(candidates50(), { 0: { external_id: '1' } }) });
    assert.equal(payload.ok, false);
    assert.equal(payload.matches_identity_verification.external_id_mismatch_count, 1);
});

test('team/date/status mismatch -> readiness blocked', () => {
    const payload = buildPayload(manifest(), {
        matchRows: matchRowsFor(candidates50(), { 0: { home_team: 'Wrong', status: 'scheduled' } }),
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.matches_identity_verification.team_date_status_mismatch_count, 2);
});

test('is_finished, data_source, and pipeline_status mismatch -> readiness blocked', () => {
    const payload = buildPayload(manifest(), {
        matchRows: matchRowsFor(candidates50(), {
            0: { is_finished: false, data_source: 'other', pipeline_status: 'processing' },
        }),
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.matches_identity_verification.identity_mismatch_count, 3);
});

test('date object rows are normalized for comparison', () => {
    const targets = candidates50();
    const rows = matchRowsFor(targets, { 0: { match_date: new Date(targets[0].match_date) } });
    const payload = buildPayload(manifest({ candidate_targets: targets }), { matchRows: rows });
    assert.equal(payload.ok, true);
});

test('existing v2 raw rows -> readiness blocked', () => {
    const payload = buildPayload(manifest(), {
        existingV2Rows: [{ match_id: candidates50()[0].match_id, data_version: mod.DATA_VERSION }],
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.raw_write_readiness.existing_v2_raw_rows_for_candidates, 1);
});

test('raw_match_data UNIQUE(match_id,data_version) missing -> blocked', () => {
    const payload = buildPayload(manifest(), {
        constraints: rawConstraints({ omit: ['raw_match_data_match_id_data_version_key'] }),
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.raw_constraint_readiness.unique_match_id_data_version_present, false);
});

test('old UNIQUE(match_id) present -> blocked', () => {
    const payload = buildPayload(manifest(), { constraints: rawConstraints({ oldUnique: true }) });
    assert.equal(payload.ok, false);
    assert.equal(payload.raw_constraint_readiness.old_unique_match_id_present, true);
});

test('raw_match_data FK missing -> blocked', () => {
    const payload = buildPayload(manifest(), {
        constraints: rawConstraints({ omit: ['raw_match_data_match_id_fkey'] }),
    });
    assert.equal(payload.ok, false);
    assert.equal(payload.raw_constraint_readiness.raw_match_data_fk_present, false);
});

test('DB row count mismatch blocks readiness', () => {
    const payload = buildPayload(manifest(), { counts: { ...mod.EXPECTED_DB_COUNTS, raw_match_data: 19 } });
    assert.equal(payload.ok, false);
    assert.match(payload.blocked_reason, /raw_match_data=19 expected 18/);
});

test('all gates pass -> ready_for_renewed_authorization', () => {
    const payload = buildPayload();
    assert.equal(payload.ok, true);
    assert.equal(payload.raw_write_retry_readiness_status, 'ready_for_renewed_authorization');
});

test('expected_raw_match_data_after_retry = 68', () => {
    assert.equal(buildPayload().expected_raw_match_data_after_retry, 68);
});

test('manifest update sets raw_write_fk_prerequisite_status=satisfied', () => {
    const payload = buildPayload();
    const updated = mod.updateManifestWithReadiness(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.raw_write_fk_prerequisite_status, 'satisfied');
});

test('manifest update required_next_step renewed raw write execution', () => {
    const payload = buildPayload();
    const updated = mod.updateManifestWithReadiness(manifest(), payload, '2026-05-18T00:00:00.000Z');
    assert.equal(updated.required_next_step, mod.NEXT_STEP_AFTER_READY);
});

test('runCli updates manifest/report after SELECT-only audit', async () => {
    let updatedManifest = null;
    let report = null;
    const result = await mod.runCli(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        generatedAt: '2026-05-18T00:00:00.000Z',
        writeManifestFile: (_file, data) => {
            updatedManifest = data;
        },
        writeReportFile: (_file, content) => {
            report = content;
        },
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(updatedManifest.raw_write_retry_readiness_status, 'ready_for_renewed_authorization');
    assert.match(report, /Post-Seed Matches Identity Raw Write Readiness Audit/);
});

test('runCli invalid input exits non-zero before DB access', async () => {
    let queried = false;
    const client = {
        query: async () => {
            queried = true;
            return { rows: [] };
        },
    };
    const result = await mod.runCli(validArgv({ 'allow-network': 'yes' }), {
        client,
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(queried, false);
});

test('runCli catches read failures and can skip manifest/report writes', async () => {
    let manifestWritten = false;
    let reportWritten = false;
    const result = await mod.runCli(validArgv(), {
        client: new FakeClient(),
        manifest: null,
        writeManifest: false,
        writeReport: false,
        writeManifestFile: () => {
            manifestWritten = true;
        },
        writeReportFile: () => {
            reportWritten = true;
        },
        output: () => {},
    });
    assert.equal(result.status, 1);
    assert.equal(manifestWritten, false);
    assert.equal(reportWritten, false);
});

test('runCli write toggles can skip manifest and report output after success', async () => {
    let manifestWritten = false;
    let reportWritten = false;
    const result = await mod.runCli(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifest: false,
        writeReport: false,
        writeManifestFile: () => {
            manifestWritten = true;
        },
        writeReportFile: () => {
            reportWritten = true;
        },
        output: () => {},
    });
    assert.equal(result.status, 0);
    assert.equal(result.payload.manifest_updated, false);
    assert.equal(result.payload.report_updated, false);
    assert.equal(manifestWritten, false);
    assert.equal(reportWritten, false);
});

test('SELECT helper loaders default to empty rows when client omits rows', async () => {
    const client = { query: async () => ({}) };
    assert.deepEqual(await mod.loadProtectedTableBaselineRows(client), []);
    assert.deepEqual(await mod.loadCandidateMatches(client, []), []);
    assert.deepEqual(await mod.loadRawMatchDataConstraints(client), []);
    assert.deepEqual(await mod.loadExistingCandidateV2Rows(client, []), []);
});

test('no DB write', async () => {
    const client = new FakeClient();
    const result = await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.db_write_executed, false);
    assert.equal(
        client.queries.some(query => /\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE)\b/i.test(query.sql)),
        false
    );
});

test('no matches write', async () => {
    const client = new FakeClient();
    await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(
        client.queries.some(query => /^INSERT INTO matches/i.test(String(query.sql).trim())),
        false
    );
});

test('no raw_match_data write', async () => {
    const client = new FakeClient();
    const result = await mod.runCli(validArgv(), {
        client,
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.raw_match_data_write_executed, false);
});

test('no network', async () => {
    const result = await mod.runCli(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.network_executed, false);
});

test('no match detail fetch', async () => {
    const result = await mod.runCli(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.match_detail_fetch_executed, false);
});

test('no parser/features/training', async () => {
    const result = await mod.runCli(validArgv(), {
        client: new FakeClient(),
        manifest: manifest(),
        writeManifestFile: () => {},
        writeReportFile: () => {},
        output: () => {},
    });
    assert.equal(result.payload.parser_features_training_executed, false);
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.equal(
        /ProductionHarvester|raw_match_data_local_ingest|single_league_pageprops_v2_controlled_write_execute/.test(
            source
        ),
        false
    );
});

test('no odds_harvest_pipeline import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.equal(/odds_harvest_pipeline/.test(source), false);
});

test('no forbidden runtime imports while loading module', () => {
    const forbidden = [];
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (/ProductionHarvester|raw_match_data_local_ingest|odds_harvest_pipeline/.test(request)) {
            forbidden.push(request);
        }
        return originalLoad.apply(this, [request, parent, isMain]);
    };
    try {
        loadFreshModule();
    } finally {
        Module._load = originalLoad;
    }
    assert.deepEqual(forbidden, []);
});

test('queryReadOnly blocks non SELECT SQL and SELECT locks', async () => {
    const client = new FakeClient();
    await assert.rejects(() => mod.queryReadOnly(client, 'INSERT INTO matches(match_id) VALUES($1)', ['x']));
    await assert.rejects(() => mod.queryReadOnly(client, 'SELECT * FROM matches FOR UPDATE'));
});
