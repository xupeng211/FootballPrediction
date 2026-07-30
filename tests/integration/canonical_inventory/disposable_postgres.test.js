'use strict';

// lifecycle: permanent
// M3 integration proof against only the compose-labelled disposable PostgreSQL.
// M3_CANONICAL_DISPOSABLE_DB_WRITE_PROOF_V1: compose-labelled synthetic target only.
/* eslint-disable max-lines -- the fixed proof stages and their schema-tamper matrices stay adjacent to the disposable harness they verify. */

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
    testAuthorizationAuthority,
    syntheticCandidates,
    syntheticProvenance,
    writeDocument,
} = require('../../helpers/canonicalInventoryFixtures');
const { applyDisposableMigration, checksum } = require('./canonicalMigrationHarness');

const config = {
    host: process.env.M3_CANONICAL_DB_HOST,
    port: Number(process.env.M3_CANONICAL_DB_PORT),
    database: process.env.M3_CANONICAL_DB_NAME,
    adminUser: process.env.M3_CANONICAL_DB_ADMIN_USER,
    adminPassword: process.env.M3_CANONICAL_DB_ADMIN_PASSWORD,
    writerUser: process.env.M3_CANONICAL_DB_WRITER_USER,
    writerPassword: process.env.M3_CANONICAL_DB_WRITER_PASSWORD,
    verifierUser: process.env.M3_CANONICAL_DB_VERIFIER_USER,
    verifierPassword: process.env.M3_CANONICAL_DB_VERIFIER_PASSWORD,
};
const serviceIdentity = 'fp_m3_canonical_disposable_postgres15';
const codeRevision = process.env.M3_CANONICAL_WRITER_CODE_REVISION;
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-m3-canonical-proof-'));
const schemaOnly = process.env.M3_CANONICAL_SCHEMA_ONLY === 'yes';
const proofProfile = process.env.M3_CANONICAL_PROOF_PROFILE || 'main';
const schemaTest = schemaOnly ? test : test.skip;
const proofTest = schemaOnly || proofProfile !== 'main' ? test.skip : test;
const canaryProofTest = schemaOnly || proofProfile !== 'canary' ? test.skip : test;
let admin;
let pool;
let verifier;
let ownerPhaseClosed = !schemaOnly;
let databaseInstanceOid;
let databaseInstanceNonce;
let primaryMaster;
let primaryMasterFile;

function assertConfig() {
    assert.ok(config.database.startsWith('fp_m3_canonical_ephemeral_'));
    assert.equal(config.host, proofProfile === 'canary' ? 'canary-postgres' : 'ephemeral-postgres');
    assert.equal(config.writerUser, 'm3_canonical_writer');
    assert.equal(config.verifierUser, 'm3_canonical_verifier');
    assert.match(codeRevision, /^[0-9a-f]{40}$/);
    if (schemaOnly) {
        assert.equal(config.adminUser, 'm3_canonical_admin');
        assert.ok(config.adminPassword);
    } else {
        assert.equal(process.env.M3_CANONICAL_DB_ADMIN_USER, undefined);
        assert.equal(process.env.M3_CANONICAL_DB_ADMIN_PASSWORD, undefined);
    }
}
function candidateInput(file, document, receipt = {}) {
    const artifact = readOrdinaryArtifact(file.path, {
        sha256: file.sha256,
        parentArtifactPath: receipt.parentArtifactPath,
        allowSyntheticTestOnly: true,
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
                databaseInstanceOid,
                databaseInstanceNonce,
                writerRole: config.writerUser,
                codeRevision,
            }),
        provenanceReceipt: receipt.provenance === undefined ? syntheticProvenance(file.sha256) : receipt.provenance,
    };
}
function canonicalWriter(options = {}) {
    return new CanonicalInventoryWriter({
        pool,
        target: {
            classification: 'disposable',
            databaseIdentity: config.database,
            serviceIdentity,
            writerRole: config.writerUser,
        },
        authorizationAuthority: testAuthorizationAuthority(),
        codeRevision,
        ...options,
    });
}
function writer(options = {}) {
    assert.equal(admin ?? null, null, 'owner/migrator session must be closed before canonical writer proof');
    assert.equal(ownerPhaseClosed, true, 'canonical writer proof requires a completed owner/migrator phase');
    return canonicalWriter(options);
}
function population(label, sourceIdOffset) {
    return syntheticCandidates({ label, sourceIdOffset });
}
async function counts() {
    const result = await verifier.query(`
        SELECT (SELECT COUNT(*)::int FROM matches) AS matches,
               (SELECT COUNT(*)::int FROM m3_canonical_source_artifacts) AS artifacts,
               (SELECT COUNT(*)::int FROM m3_canonical_import_runs) AS runs,
               (SELECT COUNT(*)::int FROM m3_canonical_match_lineages) AS lineages
    `);
    return result.rows[0];
}
function addCounts(before, delta) {
    return {
        matches: before.matches + (delta.matches || 0),
        artifacts: before.artifacts + (delta.artifacts || 0),
        runs: before.runs + (delta.runs || 0),
        lineages: before.lineages + (delta.lineages || 0),
    };
}
async function expectZeroDelta(action) {
    const before = await counts();
    await assert.rejects(action);
    assert.deepEqual(await counts(), before);
}

test.before(async () => {
    assertConfig();
    if (schemaOnly) {
        admin = new Client({
            host: config.host,
            port: config.port,
            database: config.database,
            user: config.adminUser,
            password: config.adminPassword,
        });
        await admin.connect();
    }
    pool = new Pool({
        host: config.host,
        port: config.port,
        database: config.database,
        user: config.writerUser,
        password: config.writerPassword,
        max: 4,
    });
    verifier = new Client({
        host: config.host,
        port: config.port,
        database: config.database,
        user: config.verifierUser,
        password: config.verifierPassword,
    });
    await verifier.connect();
    const targetIdentity = (
        await verifier.query(
            `
            SELECT (SELECT oid::text FROM pg_database WHERE datname = current_database()) AS database_instance_oid,
                   instance_nonce::text AS database_instance_nonce
            FROM public.m3_canonical_target_identity
            WHERE binding_key = 'canonical_inventory_v1'
        `
        )
    ).rows[0];
    databaseInstanceOid = targetIdentity.database_instance_oid;
    databaseInstanceNonce = targetIdentity.database_instance_nonce;
    assert.equal((await verifier.query('SHOW transaction_read_only')).rows[0].transaction_read_only, 'on');
    await assert.rejects(verifier.query('CREATE TEMP TABLE m3_canonical_verifier_write_probe (id integer)'));
});
test.after(async () => {
    await pool?.end();
    await verifier?.end();
    await admin?.end();
    fs.rmSync(temp, { recursive: true, force: true });
});

schemaTest('migration replay, identity constraints and least-privilege schema are active', async () => {
    const compose = fs.readFileSync(path.join(__dirname, 'docker-compose.disposable.yml'), 'utf8');
    assert.match(compose, /NODE_PATH:\s*\/app\/node_modules/);
    const migration = fs.readFileSync(
        path.join(__dirname, '../../../database/migrations/V26.10__create_m3_canonical_inventory_contract.sql'),
        'utf8'
    );
    const replay = await applyDisposableMigration(admin, {
        version: 'V26.10',
        filename: 'V26.10__create_m3_canonical_inventory_contract.sql',
        sql: migration,
    });
    assert.deepEqual(replay, { status: 'already_applied', checksum: checksum(migration) });
    await assert.rejects(
        applyDisposableMigration(admin, {
            version: 'V26.10',
            filename: 'V26.10__create_m3_canonical_inventory_contract.sql',
            sql: 'CREATE TABLE public.m3_checksum_probe_should_never_execute (id integer)',
        }),
        error => error.code === 'MIGRATION_CHECKSUM_CONFLICT'
    );
    await assert.equal(
        (await admin.query("SELECT to_regclass('public.m3_checksum_probe_should_never_execute') AS probe")).rows[0]
            .probe,
        null
    );
    await assert.rejects(
        applyDisposableMigration(admin, {
            version: 'V99.1',
            filename: 'V99.1__failed_probe.sql',
            sql: 'CREATE TABLE public.m3_canonical_failed_migration_probe (id integer); SELECT missing_column FROM public.m3_canonical_failed_migration_probe;',
        })
    );
    assert.equal(
        (await admin.query("SELECT to_regclass('public.m3_canonical_failed_migration_probe') AS probe")).rows[0].probe,
        null
    );
    assert.equal(
        (
            await admin.query(
                "SELECT COUNT(*)::int AS count FROM public.m3_canonical_schema_migrations WHERE version = 'V99.1'"
            )
        ).rows[0].count,
        0
    );
    const resumed = await applyDisposableMigration(admin, {
        version: 'V99.1',
        filename: 'V99.1__failed_probe.sql',
        sql: 'CREATE TABLE public.m3_canonical_failed_migration_probe (id integer)',
    });
    assert.equal(resumed.status, 'applied');
    await admin.query('DROP TABLE public.m3_canonical_failed_migration_probe');
    await admin.query("DELETE FROM public.m3_canonical_schema_migrations WHERE version = 'V99.1'");
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
            "INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team, canonical_provider) VALUES ('bad-null-provider', '2', 'Premier League', '2022/2023', 'H-null', 'A-null', NULL)"
        )
    );
    await assert.rejects(
        admin.query(
            "INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team, canonical_provider) VALUES ('bad-provider', '1', 'Premier League', '2022/2023', 'H2', 'A2', 'other')"
        )
    );
    await admin.query("DELETE FROM matches WHERE match_id = 'legacy-null'");
    const schemaInspector = new CanonicalInventoryWriter({
        pool,
        target: {
            classification: 'disposable',
            databaseIdentity: config.database,
            serviceIdentity,
            writerRole: config.adminUser,
        },
        authorizationAuthority: testAuthorizationAuthority(),
        codeRevision,
    });
    await admin.query('BEGIN');
    await admin.query('DROP INDEX public.matches_m3_fotmob_external_id_uq');
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('DROP INDEX public.matches_m3_epl_fixture_identity_uq');
    await admin.query(
        "CREATE UNIQUE INDEX matches_m3_epl_fixture_identity_uq ON public.matches (league_name, season, home_team, away_team) WHERE league_name = 'Premier League' AND season IN ('2022/2023', '2023/2024', '2024/2025') AND canonical_provider = 'fotmob' AND home_team = '__never__'"
    );
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('ALTER TABLE public.m3_canonical_match_lineages ALTER COLUMN provider_status DROP NOT NULL');
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    const lineageUnique = await admin.query(`
        SELECT conname
        FROM pg_constraint constraint_meta
        WHERE constraint_meta.conrelid = 'public.m3_canonical_match_lineages'::regclass
          AND constraint_meta.contype = 'u'
          AND ARRAY(
              SELECT attribute.attname
              FROM unnest(constraint_meta.conkey) WITH ORDINALITY AS key_column(attnum, ordinal)
              JOIN pg_attribute attribute
                ON attribute.attrelid = constraint_meta.conrelid
               AND attribute.attnum = key_column.attnum
              ORDER BY key_column.ordinal
          ) = ARRAY['artifact_id', 'candidate_id']::name[]
    `);
    assert.equal(lineageUnique.rowCount, 1);
    assert.match(lineageUnique.rows[0].conname, /^[a-z0-9_]+$/);
    await admin.query('BEGIN');
    await admin.query(
        `ALTER TABLE public.m3_canonical_match_lineages DROP CONSTRAINT ${lineageUnique.rows[0].conname}`
    );
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('ALTER TABLE public.matches DROP CONSTRAINT matches_canonical_provider_fotmob_only');
    await admin.query('ALTER TABLE public.matches ADD CONSTRAINT matches_canonical_provider_fotmob_only CHECK (true)');
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('ALTER TABLE public.matches DROP CONSTRAINT matches_m3_epl_canonical_identity_required');
    await admin.query(
        'ALTER TABLE public.matches ADD CONSTRAINT matches_m3_epl_canonical_identity_required CHECK (true)'
    );
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query(`
        CREATE OR REPLACE FUNCTION public.m3_canonical_inventory_acquire_locks_v1()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$ BEGIN NULL; END; $$
    `);
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query(`
        CREATE OR REPLACE FUNCTION public.m3_canonical_inventory_acquire_locks_v1()
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $$
        DECLARE ignored integer;
        BEGIN
            LOCK TABLE public.m3_canonical_source_artifacts IN SHARE ROW EXCLUSIVE MODE;
            LOCK TABLE public.m3_canonical_import_runs IN SHARE ROW EXCLUSIVE MODE;
            LOCK TABLE public.m3_canonical_match_lineages IN SHARE ROW EXCLUSIVE MODE;
            LOCK TABLE public.matches IN SHARE ROW EXCLUSIVE MODE;
            SELECT 1 INTO ignored;
        END;
        $$
    `);
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('ALTER FUNCTION public.m3_canonical_inventory_acquire_locks_v1() OWNER TO m3_canonical_writer');
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('DROP INDEX public.matches_m3_fotmob_external_id_uq');
    await admin.query(
        "CREATE UNIQUE INDEX matches_m3_fotmob_external_id_uq ON public.matches (external_id) WHERE canonical_provider = 'fotmob' AND season = '2022/2023'"
    );
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    await admin.query('BEGIN');
    await admin.query('DROP INDEX public.matches_m3_epl_fixture_identity_uq');
    await admin.query(
        "CREATE UNIQUE INDEX matches_m3_epl_fixture_identity_uq ON public.matches (league_name, season, home_team, away_team) WHERE league_name = 'Premier League' AND season = '2022/2023' AND canonical_provider = 'fotmob'"
    );
    await assert.rejects(
        schemaInspector.inspectTarget(admin),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    await admin.query('ROLLBACK');
    const findChecks = async (table, needle) =>
        (
            await admin.query(
                `SELECT constraint_meta.conname
                 FROM pg_constraint constraint_meta
                 WHERE constraint_meta.conrelid = $1::regclass
                   AND constraint_meta.contype = 'c'
                   AND pg_get_constraintdef(constraint_meta.oid) ILIKE $2
                 ORDER BY constraint_meta.conname`,
                [`public.${table}`, `%${needle}%`]
            )
        ).rows.map(row => row.conname);
    const expectSchemaTamperReject = async statements => {
        await admin.query('BEGIN');
        for (const statement of statements) await admin.query(statement);
        await assert.rejects(
            schemaInspector.inspectTarget(admin),
            error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
        );
        await admin.query('ROLLBACK');
    };
    // Every inventory CHECK is part of the write-time safety contract: weakened,
    // widened, narrowed, replaced, dropped or duplicated definitions fail closed.
    const artifactKindParent = (await findChecks('m3_canonical_source_artifacts', 'parent_artifact_id'))[0];
    assert.ok(artifactKindParent);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactKindParent}`,
        'ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_weakened_kind_parent CHECK (true)',
    ]);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactKindParent}`,
        "ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_narrowed_kind_parent CHECK (artifact_kind = 'master' AND parent_artifact_id IS NULL)",
    ]);
    const artifactCompetition = (await findChecks('m3_canonical_source_artifacts', 'premier league'))[0];
    assert.ok(artifactCompetition);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactCompetition}`,
        "ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_widened_competition CHECK (competition IN ('Premier League', 'Championship'))",
    ]);
    await expectSchemaTamperReject([
        'ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_additive_weakening CHECK (true)',
    ]);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_duplicated_competition CHECK (competition = 'Premier League')`,
    ]);
    const artifactStatusMapping = (await findChecks('m3_canonical_source_artifacts', 'status_mapping_version'))[0];
    assert.ok(artifactStatusMapping);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactStatusMapping}`,
        "ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_wrong_status_mapping CHECK (status_mapping_version = 'fotmob-status-to-matches-status/v2')",
    ]);
    const artifactShaFormat = (await findChecks('m3_canonical_source_artifacts', 'artifact_sha256'))[0];
    assert.ok(artifactShaFormat);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactShaFormat}`,
    ]);
    const artifactByteSize = (await findChecks('m3_canonical_source_artifacts', 'byte_size'))[0];
    assert.ok(artifactByteSize);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactByteSize}`,
    ]);
    const artifactCandidateCount = (await findChecks('m3_canonical_source_artifacts', 'candidate_count'))[0];
    assert.ok(artifactCandidateCount);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactCandidateCount}`,
        'ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT m3_widened_candidate_count CHECK (candidate_count > -1)',
    ]);
    const bindingKeyCheck = (await findChecks('m3_canonical_target_identity', 'binding_key'))[0];
    assert.ok(bindingKeyCheck);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_target_identity DROP CONSTRAINT ${bindingKeyCheck}`,
        'ALTER TABLE public.m3_canonical_target_identity ADD CONSTRAINT m3_weakened_binding_key CHECK (true)',
    ]);
    const serviceIdentityFormat = (await findChecks('m3_canonical_target_identity', "'^[a-z0-9]"))[0];
    assert.ok(serviceIdentityFormat);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_target_identity DROP CONSTRAINT ${serviceIdentityFormat}`,
    ]);
    const runReceiptFormat = (await findChecks('m3_canonical_import_runs', 'authorization_receipt_sha256'))[0];
    assert.ok(runReceiptFormat);
    await expectSchemaTamperReject([`ALTER TABLE public.m3_canonical_import_runs DROP CONSTRAINT ${runReceiptFormat}`]);
    const lineageStatusMapping = (await findChecks('m3_canonical_match_lineages', 'status_mapping_version'))[0];
    assert.ok(lineageStatusMapping);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_match_lineages DROP CONSTRAINT ${lineageStatusMapping}`,
    ]);
    const lineageFingerprintFormat = (await findChecks('m3_canonical_match_lineages', 'immutable_fingerprint'))[0];
    assert.ok(lineageFingerprintFormat);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_match_lineages DROP CONSTRAINT ${lineageFingerprintFormat}`,
    ]);
    const nonceUnique = (
        await admin.query(
            `SELECT constraint_meta.conname
             FROM pg_constraint constraint_meta
             WHERE constraint_meta.conrelid = 'public.m3_canonical_target_identity'::regclass
               AND constraint_meta.contype = 'u'
               AND ARRAY(
                   SELECT attribute.attname
                   FROM unnest(constraint_meta.conkey) AS key_column(attnum)
                   JOIN pg_attribute attribute
                     ON attribute.attrelid = constraint_meta.conrelid
                    AND attribute.attnum = key_column.attnum
               ) = ARRAY['instance_nonce']::name[]`
        )
    ).rows[0].conname;
    assert.ok(nonceUnique);
    await expectSchemaTamperReject([`ALTER TABLE public.m3_canonical_target_identity DROP CONSTRAINT ${nonceUnique}`]);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_target_identity DROP CONSTRAINT ${nonceUnique}`,
        'CREATE INDEX m3_nonce_plain_index ON public.m3_canonical_target_identity (instance_nonce)',
    ]);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_target_identity DROP CONSTRAINT ${nonceUnique}`,
        'ALTER TABLE public.m3_canonical_target_identity ADD CONSTRAINT m3_nonce_wrong_column UNIQUE (created_at)',
    ]);
    await expectSchemaTamperReject([
        `ALTER TABLE public.m3_canonical_target_identity DROP CONSTRAINT ${nonceUnique}`,
        "CREATE UNIQUE INDEX m3_nonce_partial_index ON public.m3_canonical_target_identity (instance_nonce) WHERE binding_key = 'canonical_inventory_v1'",
    ]);
    // A committed schema drift must stop the full write path before any
    // transaction, with zero database delta; the exact constraint definition is
    // then restored and re-verified so later proofs see the untampered schema.
    await admin.query(`ALTER TABLE public.m3_canonical_source_artifacts DROP CONSTRAINT ${artifactKindParent}`);
    const driftMaster = buildDocument(population('schema-drift-population', 6_500_000));
    const driftFile = writeDocument(temp, 'schema-drift-population.json', driftMaster);
    const beforeDrift = await counts();
    await assert.rejects(
        canonicalWriter().execute(candidateInput(driftFile, driftMaster)),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'SCHEMA_BASELINE_MISMATCH'
    );
    assert.deepEqual(await counts(), beforeDrift);
    await admin.query(
        `ALTER TABLE public.m3_canonical_source_artifacts ADD CONSTRAINT ${artifactKindParent} CHECK ((artifact_kind = 'master' AND parent_artifact_id IS NULL) OR (artifact_kind = 'canary' AND parent_artifact_id IS NOT NULL))`
    );
    const restoredSchemaClient = await pool.connect();
    try {
        await canonicalWriter().inspectTarget(restoredSchemaClient);
    } finally {
        restoredSchemaClient.release();
    }
    const targetIdentityClient = await pool.connect();
    try {
        await admin.query(
            "UPDATE public.m3_canonical_target_identity SET service_identity = 'fp_m3_canonical_untrusted_clone15' WHERE binding_key = 'canonical_inventory_v1'"
        );
        await assert.rejects(
            canonicalWriter().inspectTarget(targetIdentityClient),
            error => error instanceof CanonicalInventoryWriterError && error.code === 'TARGET_SERVICE_IDENTITY_MISMATCH'
        );
        await admin.query(
            "UPDATE public.m3_canonical_target_identity SET service_identity = 'fp_m3_canonical_disposable_postgres15', database_oid = '1'::oid WHERE binding_key = 'canonical_inventory_v1'"
        );
        await assert.rejects(
            canonicalWriter().inspectTarget(targetIdentityClient),
            error => error instanceof CanonicalInventoryWriterError && error.code === 'TARGET_SERVICE_IDENTITY_MISMATCH'
        );
    } finally {
        await admin.query(
            "UPDATE public.m3_canonical_target_identity SET service_identity = 'fp_m3_canonical_disposable_postgres15', database_oid = (SELECT oid FROM pg_database WHERE datname = current_database()) WHERE binding_key = 'canonical_inventory_v1'"
        );
        targetIdentityClient.release();
    }
    const wrongRoleDocument = buildDocument(syntheticCandidates());
    const wrongRoleFile = writeDocument(temp, 'wrong-writer-role.json', wrongRoleDocument);
    const wrongRoleWriter = new CanonicalInventoryWriter({
        pool,
        target: {
            classification: 'disposable',
            databaseIdentity: config.database,
            serviceIdentity,
            writerRole: config.adminUser,
        },
        authorizationAuthority: testAuthorizationAuthority(),
        codeRevision,
    });
    const beforeWrongRole = await counts();
    await assert.rejects(
        () => wrongRoleWriter.execute(candidateInput(wrongRoleFile, wrongRoleDocument)),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'TARGET_WRITER_ROLE_MISMATCH'
    );
    assert.deepEqual(await counts(), beforeWrongRole);
    const expectPermissionBoundary = async (grant, revoke) => {
        await admin.query(grant);
        const writerClient = await pool.connect();
        try {
            await assert.rejects(
                canonicalWriter().inspectTarget(writerClient),
                error => error instanceof CanonicalInventoryWriterError && error.code === 'BLOCKED_PERMISSION_BOUNDARY'
            );
        } finally {
            writerClient.release();
            await admin.query(revoke);
        }
    };
    await expectPermissionBoundary(
        'GRANT UPDATE ON public.matches TO m3_canonical_writer',
        'REVOKE UPDATE ON public.matches FROM m3_canonical_writer'
    );
    await expectPermissionBoundary(
        'GRANT UPDATE ON public.m3_canonical_target_identity TO m3_canonical_writer',
        'REVOKE UPDATE ON public.m3_canonical_target_identity FROM m3_canonical_writer'
    );
    await expectPermissionBoundary(
        'GRANT CREATE ON SCHEMA public TO m3_canonical_writer',
        'REVOKE CREATE ON SCHEMA public FROM m3_canonical_writer'
    );
    await expectPermissionBoundary(
        'GRANT EXECUTE ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() TO PUBLIC',
        'REVOKE ALL ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() FROM PUBLIC'
    );
    const directUuidClient = await pool.connect();
    try {
        await assert.rejects(
            () => directUuidClient.query('SELECT public.uuid_generate_v4()'),
            /permission denied for function uuid_generate_v4/
        );
    } finally {
        directUuidClient.release();
    }
    await admin.query('CREATE ROLE m3_canonical_disposable_prohibited_member NOLOGIN');
    try {
        await expectPermissionBoundary(
            'GRANT m3_canonical_disposable_prohibited_member TO m3_canonical_writer',
            'REVOKE m3_canonical_disposable_prohibited_member FROM m3_canonical_writer'
        );
    } finally {
        await admin.query('DROP ROLE m3_canonical_disposable_prohibited_member');
    }
    await admin.query(
        `
        INSERT INTO public.matches
            (match_id, external_id, league_name, season, home_team, away_team, match_date, status, canonical_provider)
        VALUES
            ('m3-rogue-outside-master', '79999999', 'Premier League', '2022/2023', 'Rogue Home', 'Rogue Away', '2022-08-01T12:00:00Z', 'scheduled', 'fotmob')
    `
    );
    const strictMaster = buildDocument(population('schema-master-population', 8_000_000));
    const strictMasterFile = writeDocument(temp, 'schema-master-population.json', strictMaster);
    const beforeStrictMaster = await counts();
    await assert.rejects(
        canonicalWriter().execute(candidateInput(strictMasterFile, strictMaster)),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'MASTER_TARGET_POPULATION_MISMATCH'
    );
    assert.deepEqual(await counts(), beforeStrictMaster);
    await admin.query("DELETE FROM public.matches WHERE match_id = 'm3-rogue-outside-master'");
    await admin.end();
    admin = null;
    ownerPhaseClosed = true;
});

proofTest('Proof A/B: full 1,140 synthetic master inserts once then exact replays with zero delta', async () => {
    const adminLogin = await verifier.query("SELECT rolcanlogin FROM pg_roles WHERE rolname = 'm3_canonical_admin'");
    assert.deepEqual(adminLogin.rows, [{ rolcanlogin: false }]);
    const before = await counts();
    assert.deepEqual(before, { matches: 0, artifacts: 0, runs: 0, lineages: 0 });
    const master = buildDocument(population('Proof A', 0));
    const file = writeDocument(temp, 'master-a.json', master);
    primaryMaster = master;
    primaryMasterFile = file;
    const first = await writer().execute(candidateInput(file, master));
    assert.deepEqual(first.terminal_counts, { inserted: 1140 });
    assert.deepEqual(first.database_delta, { matches: 1140, artifacts: 1, import_runs: 1, lineages: 1140 });
    assert.deepEqual(await counts(), addCounts(before, { matches: 1140, artifacts: 1, runs: 1, lineages: 1140 }));
    assert.deepEqual((await verifier.query('SELECT DISTINCT code_revision FROM m3_canonical_import_runs')).rows, [
        { code_revision: codeRevision },
    ]);
    assert.deepEqual(
        (
            await verifier.query(
                `SELECT lineage.provider_status, lineage.status_mapping_version, lineage.application_status, match.status
                 FROM m3_canonical_match_lineages lineage
                 JOIN matches match ON match.match_id = lineage.match_id
                 WHERE lineage.candidate_id = $1`,
                [master.candidates[0].id]
            )
        ).rows,
        [
            {
                provider_status: master.candidates[0].provider_status,
                status_mapping_version: master.candidates[0].status_mapping_version,
                application_status: 'finished',
                status: 'finished',
            },
        ]
    );
    const replay = await writer().execute(candidateInput(file, master));
    assert.deepEqual(replay.terminal_counts, { exact_duplicate: 1140 });
    assert.deepEqual(replay.database_delta, { matches: 0, artifacts: 0, import_runs: 0, lineages: 0 });
    assert.deepEqual(await counts(), addCounts(before, { matches: 1140, artifacts: 1, runs: 1, lineages: 1140 }));
});

canaryProofTest(
    'Proof C: staged one-row and ten-row canaries share one parent master without duplicate matches',
    async () => {
        const before = await counts();
        const master = buildDocument(population('Proof C one-row', 1_000_000));
        const masterFile = writeDocument(temp, 'master-c.json', master);
        const parent = parentMetadata(master, masterFile);
        const one = buildDocument(master.candidates.slice(0, 1), { kind: 'canary', parentMaster: parent });
        const oneFile = writeDocument(temp, 'canary-one.json', one);
        const oneResult = await writer().execute(candidateInput(oneFile, one, { parentArtifactPath: masterFile.path }));
        assert.deepEqual(oneResult.terminal_counts, { inserted: 1 });
        assert.deepEqual(oneResult.database_delta, { matches: 1, artifacts: 2, import_runs: 1, lineages: 1 });
        const ten = buildDocument(master.candidates.slice(0, 10), {
            kind: 'canary',
            parentMaster: parent,
        });
        const tenFile = writeDocument(temp, 'canary-ten.json', ten);
        const tenResult = await writer().execute(candidateInput(tenFile, ten, { parentArtifactPath: masterFile.path }));
        assert.deepEqual(tenResult.terminal_counts, { already_present_equivalent: 1, inserted: 9 });
        assert.deepEqual(tenResult.database_delta, { matches: 9, artifacts: 1, import_runs: 1, lineages: 10 });
        const masterResult = await writer().execute(candidateInput(masterFile, master));
        assert.deepEqual(masterResult.terminal_counts, { already_present_equivalent: 10, inserted: 1130 });
        assert.deepEqual(masterResult.database_delta, { matches: 1130, artifacts: 0, import_runs: 1, lineages: 1140 });
        assert.deepEqual(await counts(), addCounts(before, { matches: 1140, artifacts: 3, runs: 3, lineages: 1151 }));
    }
);

proofTest('Proof D: contract, authorization and divergent canonical conflicts rollback completely', async () => {
    assert.ok(primaryMaster && primaryMasterFile, 'Proof A must establish the canonical master first');
    const master = primaryMaster;
    const base = primaryMasterFile;
    const changed = structuredClone(master);
    changed.candidates[0].kickoff_at = '2022-08-02T12:30:00Z';
    const changedDocument = buildDocument(changed.candidates);
    const kickoffConflictCandidate = changedDocument.candidates.find(
        candidate => candidate.kickoff_at === '2022-08-02T12:30:00Z'
    );
    assert.ok(kickoffConflictCandidate);
    const changedFile = writeDocument(temp, 'conflict-kickoff.json', changedDocument);
    const beforeKickoffConflict = await counts();
    await assert.rejects(
        () => writer().execute(candidateInput(changedFile, changedDocument)),
        error => {
            assert.equal(error.code, 'CANONICAL_CONFLICT');
            assert.ok(error.evidence.samples.every(sample => typeof sample.candidate_id === 'string'));
            assert.deepEqual(
                error.evidence.samples.find(sample => sample.candidate_id === kickoffConflictCandidate.id),
                {
                    candidate_id: kickoffConflictCandidate.id,
                    terminal: 'conflict_kickoff',
                    reason: 'provider_identity_divergence',
                }
            );
            return true;
        }
    );
    assert.deepEqual(await counts(), beforeKickoffConflict);
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
            databaseInstanceOid,
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
            databaseInstanceOid,
        }),
    });
    await expectZeroDelta(() => writer().execute(wrongTarget));
    const wrongInstanceNonce = candidateInput(base, master, {
        runtime: runtimeReceipt({
            artifact: master.artifact,
            sha256: base.sha256,
            databaseIdentity: config.database,
            serviceIdentity,
            databaseInstanceOid,
            databaseInstanceNonce: '00000000-0000-4000-8000-000000000099',
            writerRole: config.writerUser,
            codeRevision,
        }),
    });
    await expectZeroDelta(() => writer().execute(wrongInstanceNonce));
    await expectZeroDelta(() => writer().execute(candidateInput(base, master, { provenance: null })));
    const duplicate = structuredClone(master);
    duplicate.candidates[1].id = duplicate.candidates[0].id;
    assert.throws(() =>
        readOrdinaryArtifact(writeDocument(temp, 'duplicate.json', duplicate).path, {
            sha256: sha256File(temp, 'duplicate.json'),
            allowSyntheticTestOnly: true,
        })
    );
    const missingStatus = structuredClone(master);
    delete missingStatus.candidates[0].provider_status;
    await expectZeroDelta(async () =>
        readOrdinaryArtifact(writeDocument(temp, 'missing-status.json', missingStatus).path, {
            sha256: sha256File(temp, 'missing-status.json'),
            allowSyntheticTestOnly: true,
        })
    );
    const outOfScope = structuredClone(master);
    outOfScope.candidates[0].season = '2025/2026';
    await expectZeroDelta(async () =>
        readOrdinaryArtifact(writeDocument(temp, 'out-of-scope.json', outOfScope).path, {
            sha256: sha256File(temp, 'out-of-scope.json'),
            allowSyntheticTestOnly: true,
        })
    );
    const projection = structuredClone(master);
    projection.artifact.identity_projection_hash = '0'.repeat(64);
    await expectZeroDelta(async () =>
        readOrdinaryArtifact(writeDocument(temp, 'projection.json', projection).path, {
            sha256: sha256File(temp, 'projection.json'),
            allowSyntheticTestOnly: true,
        })
    );
    const mutable = buildDocument(population('Proof D mutable', 4_000_000));
    const mutableFile = writeDocument(temp, 'mutated-between-preflight-and-write.json', mutable);
    const preflighted = candidateInput(mutableFile, mutable);
    fs.appendFileSync(mutableFile.path, '\n');
    await expectZeroDelta(() => writer().execute(preflighted));
    const parentMaster = buildDocument(population('Proof D parent', 5_000_000));
    const parentFile = writeDocument(temp, 'parent-mutated-after-canary-preflight.json', parentMaster);
    const parentBoundCanary = buildDocument(parentMaster.candidates.slice(0, 1), {
        kind: 'canary',
        parentMaster: parentMetadata(parentMaster, parentFile),
    });
    const parentBoundCanaryFile = writeDocument(temp, 'canary-with-mutated-parent.json', parentBoundCanary);
    const preflightedCanary = candidateInput(parentBoundCanaryFile, parentBoundCanary, {
        parentArtifactPath: parentFile.path,
    });
    fs.appendFileSync(parentFile.path, '\n');
    await expectZeroDelta(() => writer().execute(preflightedCanary));
});

proofTest(
    'writer re-reads the hash-bound artifact after authorization and ignores mutated caller candidates',
    async () => {
        assert.ok(primaryMaster && primaryMasterFile, 'Proof A must establish the canonical master first');
        const master = primaryMaster;
        const file = primaryMasterFile;
        const input = candidateInput(file, master);
        const originalHomeTeam = input.candidates[0].home_team;
        const boundWriter = writer({
            afterAdvisoryLock: () => {
                input.candidates[0].home_team = 'Injected in-memory candidate';
            },
        });
        assert.deepEqual((await boundWriter.execute(input)).terminal_counts, { exact_duplicate: 1140 });
        const persisted = await verifier.query('SELECT home_team FROM matches WHERE match_id = $1', [
            master.candidates[0].id,
        ]);
        assert.equal(persisted.rows[0].home_team, originalHomeTeam);
    }
);

function sha256File(directory, name) {
    return crypto
        .createHash('sha256')
        .update(fs.readFileSync(path.join(directory, name)))
        .digest('hex');
}

proofTest('Proof E/F: concurrent writers fail closed and writer role cannot mutate or bypass locks', async () => {
    const before = await counts();
    assert.ok(primaryMaster && primaryMasterFile, 'Proof A must establish the canonical master first');
    const master = primaryMaster;
    const file = primaryMasterFile;
    const different = structuredClone(master);
    different.candidates[0].provider_status = 'scheduled';
    const differentDocument = buildDocument(different.candidates);
    const differentFile = writeDocument(temp, 'master-ef-different-artifact.json', differentDocument);
    let releaseFirst;
    let signalLock;
    const acquired = new Promise(resolve => {
        signalLock = resolve;
    });
    const release = new Promise(resolve => {
        releaseFirst = resolve;
    });
    const firstWriter = writer({
        afterAdvisoryLock: async () => {
            signalLock();
            await release;
        },
    });
    const first = firstWriter.execute(candidateInput(file, master));
    await acquired;
    await assert.rejects(
        writer().execute(candidateInput(differentFile, differentDocument)),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'LOCK_BUSY'
    );
    releaseFirst();
    assert.deepEqual((await first).terminal_counts, { exact_duplicate: 1140 });
    assert.deepEqual(await counts(), before);
    await assert.rejects(pool.query("UPDATE matches SET status = 'changed'"));
    await assert.rejects(pool.query('DELETE FROM matches'));
    await assert.rejects(pool.query('TRUNCATE matches'));
    await assert.rejects(pool.query('CREATE TABLE public.forbidden_ddl_probe (id int)'));
    await assert.rejects(pool.query('CREATE TEMP TABLE forbidden_temp (id int)'));
    await assert.rejects(pool.query('LOCK TABLE matches IN SHARE ROW EXCLUSIVE MODE'));
    await assert.rejects(pool.query('SELECT public.m3_canonical_unrelated_probe()'));
    await assert.doesNotReject(pool.query('SELECT public.m3_canonical_inventory_acquire_locks_v1()'));
});

proofTest('schema baseline constant is explicit and source-linkage/staging tables stay untouched', async () => {
    assert.equal(SCHEMA_BASELINE, 'm3-canonical-inventory-v26.10');
    const touched = await verifier.query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('odds_historical_staging_observations', 'raw_match_data')"
    );
    assert.equal(touched.rowCount, 0);
});
