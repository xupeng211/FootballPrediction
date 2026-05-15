'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/raw_match_data_completeness_fidelity_audit.js');

function loadModuleFresh() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        'expected-raw-count': '10',
        'expected-seeded-raw-count': '8',
        'allow-network': 'no',
        'allow-db-write': 'no',
        'print-full-raw-data': 'no',
        'save-full-raw-data': 'no',
        ...overrides,
    };
}

function fakeRawData(overrides = {}) {
    const base = {
        _meta: {
            source: 'fotmob',
            hash_strategy: 'stable_raw_payload_v1',
            data_hash: 'hash',
            full_html_body_stored: false,
            http_response_string_stored: false,
        },
        content: {
            matchFacts: { events: [{ type: 'Goal', minute: 12 }] },
            lineup: { homeTeam: { starters: [{ id: 1, name: 'A' }] }, awayTeam: { starters: [{ id: 2, name: 'B' }] } },
            liveticker: [{ time: 1, event: 'kickoff' }],
            playerStats: { players: [{ id: 1, stats: { shots: 2 } }] },
            shotmap: { shots: [{ x: 1, y: 2, expectedGoals: 0.1 }] },
            stats: { Periods: { All: { stats: [{ title: 'xG', stats: [1.1, 0.7] }] } } },
            teamForm: { home: ['W'], away: ['L'] },
            h2h: { matches: [{ id: 10 }] },
            table: { all: [] },
            momentum: { main: [{ minute: 1, value: 2 }] },
            topPlayers: { homeTopPlayers: [] },
            insights: [{ type: 'streak' }],
            highlights: [{ id: 'clip' }],
        },
        general: { matchId: '4830747', status: 'finished' },
        header: { teams: [{ name: 'Auxerre' }, { name: 'Nice' }] },
        matchId: '4830747',
    };
    return {
        ...base,
        ...overrides,
        content: { ...base.content, ...(overrides.content || {}) },
        general: { ...base.general, ...(overrides.general || {}) },
        header: { ...base.header, ...(overrides.header || {}) },
    };
}

function fakeRawRow(externalId, overrides = {}) {
    const matchId = overrides.match_id || `53_20252026_${externalId}`;
    const rawData =
        overrides.raw_data || fakeRawData({ matchId: String(externalId), general: { matchId: String(externalId) } });
    return {
        id: overrides.id || Number(externalId) % 1000,
        match_id: matchId,
        external_id: String(externalId),
        data_version: overrides.data_version || 'fotmob_html_hyd_v1',
        data_hash: overrides.data_hash || `hash-${externalId}`,
        collected_at: overrides.collected_at || '2026-05-15T00:00:00.000Z',
        raw_data: rawData,
    };
}

function fakeRows() {
    const externalIds = ['4830746', '4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754'];
    const rows = externalIds.map(externalId => fakeRawRow(externalId));
    rows.push(fakeRawRow('4837496', { match_id: '140_20252026_4837496', data_version: 'PHASE4.23' }));
    const syntheticRaw = fakeRawData({ matchId: '900002', general: { matchId: '900002' } });
    delete syntheticRaw._meta;
    rows.push(
        fakeRawRow('900002', {
            match_id: '47_20242025_900002',
            data_version: 'PHASE4.43_SYNTHETIC',
            raw_data: syntheticRaw,
        })
    );
    return rows;
}

function fakeRowsNineFotMobOneSynthetic() {
    const rows = fakeRows().filter(row => row.data_version !== 'PHASE4.23');
    rows.push(fakeRawRow('4830755', { match_id: '53_20252026_4830755' }));
    return rows;
}

function fakeMatchRows(rawRows = fakeRows()) {
    return rawRows.map(row => ({
        match_id: row.match_id,
        external_id: row.external_id,
        home_team: `Home ${row.external_id}`,
        away_team: `Away ${row.external_id}`,
        status: 'finished',
        data_version: row.data_version,
    }));
}

function assertInvalid(overrides, pattern) {
    const { validateAuditInput } = loadModuleFresh();
    const result = validateAuditInput(validArgs(overrides));
    assert.equal(result.ok, false);
    assert.match(result.errors.join('; '), pattern);
}

test('valid input succeeds', () => {
    const { validateAuditInput } = loadModuleFresh();
    const result = validateAuditInput(validArgs());
    assert.equal(result.ok, true);
    assert.equal(result.value.source, 'fotmob');
});

test('source missing fails', () => assertInvalid({ source: '' }, /source=fotmob is required/));
test('source non-fotmob fails', () => assertInvalid({ source: 'other' }, /source must be fotmob/));
test('expected-raw-count missing fails', () => assertInvalid({ 'expected-raw-count': '' }, /expected-raw-count=10/));
test('expected-raw-count not 10 fails', () => assertInvalid({ 'expected-raw-count': '9' }, /must be 10/));
test('expected-seeded-raw-count not 8 fails', () => assertInvalid({ 'expected-seeded-raw-count': '7' }, /must be 8/));
test('allow-network=yes blocked', () => assertInvalid({ 'allow-network': 'yes' }, /allow-network=no is required/));
test('allow-db-write=yes blocked', () => assertInvalid({ 'allow-db-write': 'yes' }, /allow-db-write=no is required/));
test('print-full-raw-data=yes blocked', () =>
    assertInvalid({ 'print-full-raw-data': 'yes' }, /print-full-raw-data=no is required/));
test('save-full-raw-data=yes blocked', () =>
    assertInvalid({ 'save-full-raw-data': 'yes' }, /save-full-raw-data=no is required/));
test('parser-features=yes blocked', () =>
    assertInvalid({ 'parser-features': 'yes' }, /parser-features=yes is blocked/));
test('train=yes blocked', () => assertInvalid({ train: 'yes' }, /train=yes is blocked/));
test('predict=yes blocked', () => assertInvalid({ predict: 'yes' }, /predict=yes is blocked/));
test('execute=yes blocked', () => assertInvalid({ execute: 'yes' }, /execute=yes is blocked/));
test('commit=yes blocked', () => assertInvalid({ commit: 'yes' }, /commit=yes is blocked/));

test('classifyProvenance fotmob_html_hyd_v1 -> fotmob_html_hydration', () => {
    const { classifyProvenance } = loadModuleFresh();
    assert.equal(classifyProvenance('fotmob_html_hyd_v1'), 'fotmob_html_hydration');
});

test('classifyProvenance PHASE4.43_SYNTHETIC -> legacy_synthetic', () => {
    const { classifyProvenance } = loadModuleFresh();
    assert.equal(classifyProvenance('PHASE4.43_SYNTHETIC'), 'legacy_synthetic');
});

test('classifyProvenance unknown -> unknown', () => {
    const { classifyProvenance } = loadModuleFresh();
    assert.equal(classifyProvenance('PHASE4.23'), 'unknown');
});

test('synthetic row missing _meta becomes schema_anomaly not fatal', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: fakeRows(), matchRows: fakeMatchRows() });
    assert.equal(audit.synthetic_schema_anomalies.length, 1);
    assert.equal(audit.synthetic_schema_anomalies[0].external_id, '900002');
    assert.equal(audit.rows.find(row => row.external_id === '900002').strict_anomalies.length, 0);
});

test('synthetic row excluded_from_fotmob_source_fidelity=true', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: fakeRows(), matchRows: fakeMatchRows() });
    assert.equal(audit.rows.find(row => row.external_id === '900002').excluded_from_fotmob_source_fidelity, true);
});

test('fotmob row missing _meta becomes strict anomaly', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const rawData = fakeRawData();
    delete rawData._meta;
    const audit = buildRawMatchDataCompletenessAudit({
        rawRows: [fakeRawRow('4830747', { raw_data: rawData })],
        matchRows: [],
    });
    assert.deepEqual(audit.rows[0].strict_anomalies, ['missing__meta']);
});

test('listJsonPaths handles object', () => {
    const { listJsonPaths } = loadModuleFresh();
    assert.deepEqual(listJsonPaths({ a: 1, b: { c: 2 } }), ['a', 'b.c']);
});

test('listJsonPaths handles nested arrays', () => {
    const { listJsonPaths } = loadModuleFresh();
    assert.deepEqual(listJsonPaths({ a: [{ b: [1, 2] }] }), ['a[]', 'a[].b[]']);
});

test('summarizeJsonShape counts objects/arrays/scalars/leaves', () => {
    const { summarizeJsonShape } = loadModuleFresh();
    const summary = summarizeJsonShape({ a: [{ b: 1 }, { b: 2 }], c: true });
    assert.equal(summary.object_count, 3);
    assert.equal(summary.array_count, 1);
    assert.equal(summary.scalar_count, 3);
    assert.equal(summary.leaf_path_count, 2);
});

test('max_depth calculation stable', () => {
    const { summarizeJsonShape } = loadModuleFresh();
    assert.equal(summarizeJsonShape({ a: { b: [{ c: 1 }] } }).max_depth, 4);
});

test('summarizeModulePresence detects required top-level keys', () => {
    const { summarizeModulePresence } = loadModuleFresh();
    const presence = summarizeModulePresence(fakeRawData());
    assert.equal(presence._meta, true);
    assert.equal(presence.content, true);
    assert.equal(presence.general, true);
    assert.equal(presence.header, true);
    assert.equal(presence.matchId, true);
});

test('summarizeModulePresence detects content.matchFacts', () => {
    const { summarizeModulePresence } = loadModuleFresh();
    assert.equal(summarizeModulePresence(fakeRawData())['content.matchFacts'], true);
});

test('summarizeModulePresence detects content.lineup', () => {
    const { summarizeModulePresence } = loadModuleFresh();
    assert.equal(summarizeModulePresence(fakeRawData())['content.lineup'], true);
});

test('summarizeModulePresence detects content.liveticker', () => {
    const { summarizeModulePresence } = loadModuleFresh();
    assert.equal(summarizeModulePresence(fakeRawData())['content.liveticker'], true);
});

test('missing modules reported', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const rawData = fakeRawData({ content: { lineup: undefined } });
    delete rawData.content.lineup;
    const audit = buildRawMatchDataCompletenessAudit({
        rawRows: [fakeRawRow('4830747', { raw_data: rawData })],
        matchRows: [],
    });
    assert.deepEqual(audit.module_coverage.per_module_missing_external_ids['content.lineup'], ['4830747']);
});

test('detectBlockOrErrorMarkers detects error key', () => {
    const { detectBlockOrErrorMarkers } = loadModuleFresh();
    assert.equal(detectBlockOrErrorMarkers({ error: 'bad' }).has_error_key, true);
});

test('detectBlockOrErrorMarkers detects captcha/block markers', () => {
    const { detectBlockOrErrorMarkers } = loadModuleFresh();
    const markers = detectBlockOrErrorMarkers({ content: { message: 'Cloudflare captcha blocked 403' } });
    assert.equal(markers.has_captcha_marker, true);
    assert.equal(markers.has_block_marker, true);
});

test('detectLikelyTransformedPayload returns transformed when top-level keys are _meta/content/general/header/matchId', () => {
    const { detectLikelyTransformedPayload } = loadModuleFresh();
    assert.equal(detectLikelyTransformedPayload(fakeRawData()), 'transformed_hydration_payload');
});

test('detectLikelyTransformedPayload returns possible_full_next_data when props/pageProps present', () => {
    const { detectLikelyTransformedPayload } = loadModuleFresh();
    assert.equal(detectLikelyTransformedPayload({ props: { pageProps: { content: {} } } }), 'possible_full_next_data');
});

test('detectPotentialSourceFidelityRisk flags full_hydration_source_not_stored', () => {
    const { detectPotentialSourceFidelityRisk } = loadModuleFresh();
    assert.ok(
        detectPotentialSourceFidelityRisk(fakeRawData(), {
            provenance: 'fotmob_html_hydration',
        }).includes('full_hydration_source_not_stored')
    );
});

test('buildRawMatchDataCompletenessAudit summarizes 10 fake rows', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: fakeRows(), matchRows: fakeMatchRows() });
    assert.equal(audit.total_raw_rows, 10);
    assert.equal(audit.seeded_ligue1_raw_rows, 8);
});

test('provenance_group_counts include 9 fotmob + 1 synthetic in fake sample', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const rows = fakeRowsNineFotMobOneSynthetic();
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: rows, matchRows: fakeMatchRows(rows) });
    assert.equal(audit.provenance_group_counts.fotmob_html_hydration, 9);
    assert.equal(audit.provenance_group_counts.legacy_synthetic, 1);
});

test('module coverage matrix counts present/missing modules', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const rows = fakeRows().slice(0, 2);
    delete rows[1].raw_data.content.shotmap;
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: rows, matchRows: fakeMatchRows(rows) });
    assert.equal(audit.module_coverage.per_module_presence_counts['content.shotmap'], 1);
    assert.deepEqual(audit.module_coverage.per_module_missing_external_ids['content.shotmap'], [rows[1].external_id]);
});

test('suspicious small payload flagged', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const rows = fakeRows().slice(0, 2);
    rows[1] = fakeRawRow('4830747', {
        raw_data: { _meta: {}, content: {}, general: {}, header: {}, matchId: '4830747' },
    });
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: rows, matchRows: fakeMatchRows(rows) });
    assert.ok(audit.suspicious_small_payloads.some(row => row.external_id === '4830747'));
});

test('source_fidelity_assessment can be unknown when evidence insufficient', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const audit = buildRawMatchDataCompletenessAudit({
        rawRows: [fakeRawRow('900002', { data_version: 'PHASE4.43_SYNTHETIC' })],
        matchRows: [],
    });
    assert.equal(audit.source_fidelity_assessment.fotmob_rows_current_raw_data_is_full_next_data, 'unknown');
});

test('mixed provenance flagged', () => {
    const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
    const audit = buildRawMatchDataCompletenessAudit({ rawRows: fakeRows(), matchRows: fakeMatchRows() });
    assert.equal(audit.source_fidelity_assessment.table_has_mixed_provenance, true);
});

test('no fs write / mkdir', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /writeFile|writeFileSync|mkdir|createWriteStream/);
});

test('no child_process spawn', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /child_process|spawn|execFile|exec\(/);
});

test('no network access', async () => {
    const originalFetch = global.fetch;
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    let called = false;
    global.fetch = async () => {
        called = true;
        throw new Error('fetch blocked');
    };
    http.request = () => {
        called = true;
        throw new Error('http blocked');
    };
    https.request = () => {
        called = true;
        throw new Error('https blocked');
    };
    try {
        const { buildRawMatchDataCompletenessAudit } = loadModuleFresh();
        buildRawMatchDataCompletenessAudit({ rawRows: fakeRows(), matchRows: fakeMatchRows() });
        assert.equal(called, false);
    } finally {
        global.fetch = originalFetch;
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
    }
});

test('no DB write', async () => {
    const { runCli } = loadModuleFresh();
    const rawRows = fakeRows();
    const matchRows = fakeMatchRows(rawRows);
    const client = {
        queries: [],
        async query(sql) {
            this.queries.push(sql);
            assert.match(sql.trim(), /^SELECT/i);
            assert.doesNotMatch(sql, /\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|FOR UPDATE)\b/i);
            if (sql.includes('FROM raw_match_data') && !sql.includes('LEFT JOIN')) return { rows: rawRows };
            return { rows: matchRows };
        },
    };
    const result = await runCli(
        Object.entries(validArgs()).flatMap(([key, value]) => [`--${key}`, value]),
        {
            client,
            output: () => {},
        }
    );
    assert.equal(result.status, 0);
    assert.equal(client.queries.length, 2);
    assert.equal(result.payload.db_write_executed, false);
});

test('no ProductionHarvester/raw ingest import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|l2_raw_match_data_write/);
});

test('no parser/features/training import', () => {
    const source = fs.readFileSync(MODULE_PATH, 'utf8');
    assert.doesNotMatch(source, /feature_engine|train_model|predict_pipeline|l3_features|match_features_training/);
});
