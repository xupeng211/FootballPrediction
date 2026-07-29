'use strict';

// lifecycle: permanent
// M3 integration proof against only the compose-labelled disposable PostgreSQL.

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { Client, Pool } = require('pg');
const { readOrdinaryArtifact } = require('../../../src/infrastructure/canonical/CanonicalInventoryContract');
const {
    CanonicalInventoryWriter,
    CanonicalInventoryWriterError,
    SCHEMA_BASELINE,
} = require('../../../src/infrastructure/canonical/CanonicalInventoryWriter');
const {
    buildDocument,
    parentMetadata,
    runtimeReceipt,
    syntheticCandidates,
    syntheticProvenance,
    writeDocument,
} = require('../../helpers/canonicalInventoryFixtures');

const config = {
    host: process.env.M3_CANONICAL_DB_HOST,
    port: Number(process.env.M3_CANONICAL_DB_PORT),
    database: process.env.M3_CANONICAL_DB_NAME,
    adminUser: process.env.M3_CANONICAL_DB_ADMIN_USER,
    adminPassword: process.env.M3_CANONICAL_DB_ADMIN_PASSWORD,
    writerUser: process.env.M3_CANONICAL_DB_WRITER_USER,
    writerPassword: process.env.M3_CANONICAL_DB_WRITER_PASSWORD,
};
const serviceIdentity = 'fp_m3_canonical_disposable_postgres15';
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-m3-canonical-proof-'));
let admin;
let pool;

function assertConfig() {
    assert.ok(config.database.startsWith('fp_m3_canonical_ephemeral_'));
    assert.equal(config.host, 'ephemeral-postgres');
    assert.equal(config.writerUser, 'm3_canonical_writer');
}
function candidateInput(file, document, receipt = {}) {
    const artifact = readOrdinaryArtifact(file.path, {
        sha256: file.sha256,
        parentDocument: receipt.parentDocument,
        parentBinding: receipt.parentBinding,
    });
    return {
        ...artifact,
        runtimeAuthorization:
            receipt.runtime ||
            runtimeReceipt({
                artifact: document.artifact,
                sha256: file.sha256,
                databaseIdentity: config.database,
                serviceIdentity,
            }),
        provenanceReceipt: receipt.provenance === undefined ? syntheticProvenance(file.sha256) : receipt.provenance,
    };
}
function writer() {
    return new CanonicalInventoryWriter({
        pool,
        target: { databaseIdentity: config.database, serviceIdentity },
        codeRevision: 'disposable-proof',
    });
}
async function counts() {
    const result = await admin.query(`
        SELECT (SELECT COUNT(*)::int FROM matches) AS matches,
               (SELECT COUNT(*)::int FROM m3_canonical_source_artifacts) AS artifacts,
               (SELECT COUNT(*)::int FROM m3_canonical_import_runs) AS runs,
               (SELECT COUNT(*)::int FROM m3_canonical_match_lineages) AS lineages
    `);
    return result.rows[0];
}
async function clearState() {
    await admin.query(
        'DELETE FROM m3_canonical_match_lineages; DELETE FROM m3_canonical_import_runs; DELETE FROM m3_canonical_source_artifacts; DELETE FROM matches;'
    );
}
async function expectZeroDelta(action) {
    const before = await counts();
    await assert.rejects(action);
    assert.deepEqual(await counts(), before);
}

test.before(async () => {
    assertConfig();
    admin = new Client({
        host: config.host,
        port: config.port,
        database: config.database,
        user: config.adminUser,
        password: config.adminPassword,
    });
    await admin.connect();
    pool = new Pool({
        host: config.host,
        port: config.port,
        database: config.database,
        user: config.writerUser,
        password: config.writerPassword,
        max: 4,
    });
});
test.after(async () => {
    await pool?.end();
    await admin?.end();
    fs.rmSync(temp, { recursive: true, force: true });
});

test('migration replay, identity constraints and least-privilege schema are active', async () => {
    const migration = fs.readFileSync(
        path.join(__dirname, '../../../database/migrations/V26.10__create_m3_canonical_inventory_contract.sql'),
        'utf8'
    );
    await admin.query(migration);
    await admin.query('BEGIN');
    await admin.query('CREATE TABLE public.m3_canonical_failed_migration_probe (id integer)');
    await assert.rejects(admin.query('SELECT missing_column FROM public.m3_canonical_failed_migration_probe'));
    await admin.query('ROLLBACK');
    assert.equal(
        (await admin.query("SELECT to_regclass('public.m3_canonical_failed_migration_probe') AS probe")).rows[0].probe,
        null
    );
    await admin.query(migration); // the known additive migration can resume after a rolled-back failure
    const schema = await admin.query(
        `SELECT to_regprocedure('public.m3_canonical_inventory_acquire_locks_v1()')::text AS lock_fn, pg_get_userbyid(proowner) AS owner FROM pg_proc WHERE oid = 'public.m3_canonical_inventory_acquire_locks_v1()'::regprocedure`
    );
    assert.equal(schema.rows[0].lock_fn, 'm3_canonical_inventory_acquire_locks_v1()');
    assert.equal(schema.rows[0].owner, 'm3_canonical_owner');
    await admin.query(
        "INSERT INTO matches (match_id, league_name, season, home_team, away_team) VALUES ('legacy-null', 'Legacy League', '2324', 'Legacy H', 'Legacy A')"
    );
    await assert.rejects(
        admin.query(
            "INSERT INTO matches (match_id, league_name, season, home_team, away_team, canonical_provider) VALUES ('bad-null', 'Premier League', '2022/2023', 'H', 'A', NULL)"
        )
    );
    await assert.rejects(
        admin.query(
            "INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team, canonical_provider) VALUES ('bad-provider', '1', 'Premier League', '2022/2023', 'H2', 'A2', 'other')"
        )
    );
    await admin.query("DELETE FROM matches WHERE match_id = 'legacy-null'");
});

test('Proof A/B: full 1,140 synthetic master inserts once then exact replays with zero delta', async () => {
    await clearState();
    const master = buildDocument(syntheticCandidates());
    const file = writeDocument(temp, 'master-a.json', master);
    const first = await writer().execute(candidateInput(file, master));
    assert.deepEqual(first.terminal_counts, { inserted: 1140 });
    assert.deepEqual(await counts(), { matches: 1140, artifacts: 1, runs: 1, lineages: 1140 });
    const replay = await writer().execute(candidateInput(file, master));
    assert.deepEqual(replay.terminal_counts, { exact_duplicate: 1140 });
    assert.deepEqual(replay.database_delta, { matches: 0, artifacts: 0, import_runs: 0, lineages: 0 });
    assert.deepEqual(await counts(), { matches: 1140, artifacts: 1, runs: 1, lineages: 1140 });
});

test('Proof C: one-row and ten-row canaries become master lineages without duplicate matches', async () => {
    await clearState();
    const master = buildDocument(syntheticCandidates());
    const masterFile = writeDocument(temp, 'master-c.json', master);
    const parent = parentMetadata(master, masterFile);
    const one = buildDocument(master.candidates.slice(0, 1), { kind: 'canary', parentMaster: parent });
    const oneFile = writeDocument(temp, 'canary-one.json', one);
    const oneResult = await writer().execute(
        candidateInput(oneFile, one, { parentDocument: master, parentBinding: masterFile })
    );
    assert.deepEqual(oneResult.terminal_counts, { inserted: 1 });
    await clearState();
    const ten = buildDocument(master.candidates.slice(0, 10), { kind: 'canary', parentMaster: parent });
    const tenFile = writeDocument(temp, 'canary-ten.json', ten);
    assert.deepEqual(
        (await writer().execute(candidateInput(tenFile, ten, { parentDocument: master, parentBinding: masterFile })))
            .terminal_counts,
        { inserted: 10 }
    );
    const masterResult = await writer().execute(candidateInput(masterFile, master));
    assert.deepEqual(masterResult.terminal_counts, { already_present_equivalent: 10, inserted: 1130 });
    assert.deepEqual(await counts(), { matches: 1140, artifacts: 2, runs: 2, lineages: 1150 });
});

test('Proof D: contract, authorization and divergent canonical conflicts rollback completely', async () => {
    await clearState();
    const master = buildDocument(syntheticCandidates());
    const base = writeDocument(temp, 'master-d.json', master);
    await writer().execute(candidateInput(base, master));
    const changed = structuredClone(master);
    changed.candidates[0].kickoff_at = '2022-08-02T12:30:00Z';
    const changedDocument = buildDocument(changed.candidates);
    const changedFile = writeDocument(temp, 'conflict-kickoff.json', changedDocument);
    await expectZeroDelta(() => writer().execute(candidateInput(changedFile, changedDocument)));
    const homeChanged = structuredClone(master);
    homeChanged.candidates[0].home_team = 'Synthetic changed home';
    const homeDocument = buildDocument(homeChanged.candidates);
    const homeFile = writeDocument(temp, 'conflict-home.json', homeDocument);
    await expectZeroDelta(() => writer().execute(candidateInput(homeFile, homeDocument)));
    const seasonChanged = structuredClone(master);
    [seasonChanged.candidates[0].season, seasonChanged.candidates[380].season] = [
        seasonChanged.candidates[380].season,
        seasonChanged.candidates[0].season,
    ];
    const seasonDocument = buildDocument(seasonChanged.candidates);
    const seasonFile = writeDocument(temp, 'conflict-season.json', seasonDocument);
    await expectZeroDelta(() => writer().execute(candidateInput(seasonFile, seasonDocument)));
    const fixtureChanged = structuredClone(master);
    fixtureChanged.candidates[0].source_match_id = '99999999';
    fixtureChanged.candidates[0].id = '47_20222023_99999999';
    const fixtureDocument = buildDocument(fixtureChanged.candidates);
    const fixtureFile = writeDocument(temp, 'conflict-fixture.json', fixtureDocument);
    await expectZeroDelta(() => writer().execute(candidateInput(fixtureFile, fixtureDocument)));
    const badHash = candidateInput(base, master);
    badHash.sha256 = '0'.repeat(64);
    await expectZeroDelta(() => writer().execute(badHash));
    const expired = candidateInput(base, master, {
        runtime: runtimeReceipt({
            artifact: master.artifact,
            sha256: base.sha256,
            databaseIdentity: config.database,
            serviceIdentity,
            expiresAt: '2000-01-01T00:00:00Z',
        }),
    });
    await expectZeroDelta(() => writer().execute(expired));
    const wrongTarget = candidateInput(base, master, {
        runtime: runtimeReceipt({
            artifact: master.artifact,
            sha256: base.sha256,
            databaseIdentity: 'not-this-db',
            serviceIdentity,
        }),
    });
    await expectZeroDelta(() => writer().execute(wrongTarget));
    await expectZeroDelta(() => writer().execute(candidateInput(base, master, { provenance: null })));
    const duplicate = structuredClone(master);
    duplicate.candidates[1].id = duplicate.candidates[0].id;
    assert.throws(() =>
        readOrdinaryArtifact(writeDocument(temp, 'duplicate.json', duplicate).path, {
            sha256: sha256File(temp, 'duplicate.json'),
        })
    );
    const missingStatus = structuredClone(master);
    delete missingStatus.candidates[0].status;
    await expectZeroDelta(async () =>
        readOrdinaryArtifact(writeDocument(temp, 'missing-status.json', missingStatus).path, {
            sha256: sha256File(temp, 'missing-status.json'),
        })
    );
    const outOfScope = structuredClone(master);
    outOfScope.candidates[0].season = '2025/2026';
    await expectZeroDelta(async () =>
        readOrdinaryArtifact(writeDocument(temp, 'out-of-scope.json', outOfScope).path, {
            sha256: sha256File(temp, 'out-of-scope.json'),
        })
    );
    const projection = structuredClone(master);
    projection.artifact.identity_projection_hash = '0'.repeat(64);
    await expectZeroDelta(async () =>
        readOrdinaryArtifact(writeDocument(temp, 'projection.json', projection).path, {
            sha256: sha256File(temp, 'projection.json'),
        })
    );
});

function sha256File(directory, name) {
    return crypto
        .createHash('sha256')
        .update(fs.readFileSync(path.join(directory, name)))
        .digest('hex');
}

test('Proof E/F: concurrent attempt fails closed and writer role cannot mutate or bypass locks', async () => {
    await clearState();
    const master = buildDocument(syntheticCandidates());
    const file = writeDocument(temp, 'master-ef.json', master);
    const holder = await pool.connect();
    await holder.query('BEGIN');
    await holder.query('SELECT pg_catalog.pg_try_advisory_xact_lock($1, $2)', [1793, 1]);
    await assert.rejects(
        writer().execute(candidateInput(file, master)),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'LOCK_BUSY'
    );
    await holder.query('ROLLBACK');
    holder.release();
    await assert.rejects(pool.query("UPDATE matches SET status = 'changed'"));
    await assert.rejects(pool.query('DELETE FROM matches'));
    await assert.rejects(pool.query('TRUNCATE matches'));
    await assert.rejects(pool.query('CREATE TEMP TABLE forbidden_temp (id int)'));
    await assert.rejects(pool.query('LOCK TABLE matches IN SHARE ROW EXCLUSIVE MODE'));
    await assert.doesNotReject(pool.query('SELECT public.m3_canonical_inventory_acquire_locks_v1()'));
});

test('schema baseline constant is explicit and source-linkage/staging tables stay untouched', async () => {
    assert.equal(SCHEMA_BASELINE, 'm3-canonical-inventory-v26.10');
    const touched = await admin.query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('odds_historical_staging_observations', 'raw_match_data')"
    );
    assert.equal(touched.rowCount, 0);
});
