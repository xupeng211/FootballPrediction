'use strict';

// lifecycle: test-fixture
// M3_CANONICAL_DISPOSABLE_DB_WRITE_PROOF_V1: task-labelled synthetic PostgreSQL only.
// Bootstrap only the task-labelled disposable PostgreSQL database. It creates
// a minimal current matches shape, applies V26.10 once, then provisions a
// non-login lock-function owner and an insert-only proof writer role.

const fs = require('node:fs');
const path = require('node:path');
const { Client } = require('pg');
const { applyDisposableMigration, ensureMigrationLedger } = require('./canonicalMigrationHarness');

const ROOT = path.resolve(__dirname, '../../..');
const migration = fs.readFileSync(
    path.join(ROOT, 'database/migrations/V26.10__create_m3_canonical_inventory_contract.sql'),
    'utf8'
);

const config = {
    host: process.env.M3_CANONICAL_DB_HOST,
    port: Number(process.env.M3_CANONICAL_DB_PORT),
    database: process.env.M3_CANONICAL_DB_NAME,
    user: process.env.M3_CANONICAL_DB_ADMIN_USER,
    password: process.env.M3_CANONICAL_DB_ADMIN_PASSWORD,
};

async function main() {
    const client = new Client(config);
    await client.connect();
    try {
        await client.query('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"');
        await client.query(`
            CREATE TABLE public.matches (
                match_id VARCHAR(50) PRIMARY KEY,
                external_id VARCHAR(100),
                league_name VARCHAR(100) NOT NULL DEFAULT 'Premier League',
                season VARCHAR(20) NOT NULL DEFAULT '2324',
                home_team VARCHAR(200) NOT NULL,
                away_team VARCHAR(200) NOT NULL,
                match_date TIMESTAMPTZ,
                status VARCHAR(50) DEFAULT 'Scheduled',
                is_finished BOOLEAN DEFAULT FALSE,
                data_source VARCHAR(50) DEFAULT 'FotMob',
                pipeline_status VARCHAR(20) DEFAULT 'pending',
                source_type VARCHAR(32),
                evidence_level VARCHAR(24),
                is_production_scope BOOLEAN,
                is_reconciliation_eligible BOOLEAN,
                is_training_eligible BOOLEAN
            )
        `);
        await ensureMigrationLedger(client);
        const migrationResult = await applyDisposableMigration(client, {
            version: 'V26.10',
            filename: 'V26.10__create_m3_canonical_inventory_contract.sql',
            sql: migration,
        });
        await client.query(
            `
            INSERT INTO public.m3_canonical_target_identity (binding_key, service_identity, database_oid)
            SELECT 'canonical_inventory_v1', 'fp_m3_canonical_disposable_postgres15', oid
            FROM pg_database
            WHERE datname = current_database()
        `
        );
        await client.query(`
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'm3_canonical_owner') THEN CREATE ROLE m3_canonical_owner NOLOGIN; END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'm3_canonical_writer') THEN CREATE ROLE m3_canonical_writer LOGIN PASSWORD 'm3_canonical_writer_proof'; END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'm3_canonical_verifier') THEN CREATE ROLE m3_canonical_verifier LOGIN PASSWORD 'm3_canonical_verifier_proof' NOINHERIT; END IF;
            END $$;
            ALTER TABLE public.matches OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_target_identity OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_source_artifacts OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_import_runs OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_match_lineages OWNER TO m3_canonical_owner;
            ALTER FUNCTION public.m3_canonical_inventory_acquire_locks_v1() OWNER TO m3_canonical_owner;
        `);
        await client.query(`
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
            REVOKE ALL ON FUNCTION public.uuid_generate_v4() FROM PUBLIC;
            REVOKE ALL ON FUNCTION public.uuid_generate_v4() FROM m3_canonical_writer;
            REVOKE ALL ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() FROM PUBLIC;
            REVOKE ALL ON FUNCTION pg_catalog.pg_try_advisory_xact_lock(integer, integer) FROM PUBLIC;
            CREATE OR REPLACE FUNCTION public.m3_canonical_unrelated_probe() RETURNS integer LANGUAGE sql AS 'SELECT 1';
            REVOKE ALL ON FUNCTION public.m3_canonical_unrelated_probe() FROM PUBLIC;
            REVOKE TEMPORARY ON DATABASE ${JSON.stringify(config.database)} FROM PUBLIC;
            GRANT USAGE ON SCHEMA public TO m3_canonical_owner;
            GRANT CONNECT ON DATABASE ${JSON.stringify(config.database)} TO m3_canonical_writer;
            GRANT CONNECT ON DATABASE ${JSON.stringify(config.database)} TO m3_canonical_verifier;
            GRANT USAGE ON SCHEMA public TO m3_canonical_writer;
            GRANT USAGE ON SCHEMA public TO m3_canonical_verifier;
            GRANT SELECT, INSERT ON public.matches, public.m3_canonical_source_artifacts, public.m3_canonical_import_runs, public.m3_canonical_match_lineages TO m3_canonical_writer;
            GRANT SELECT ON public.m3_canonical_target_identity TO m3_canonical_writer;
            GRANT SELECT ON public.m3_canonical_schema_migrations TO m3_canonical_writer;
            GRANT SELECT ON public.matches, public.m3_canonical_target_identity, public.m3_canonical_source_artifacts, public.m3_canonical_import_runs, public.m3_canonical_match_lineages, public.m3_canonical_schema_migrations TO m3_canonical_verifier;
            GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO m3_canonical_writer;
            GRANT EXECUTE ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() TO m3_canonical_writer;
            GRANT EXECUTE ON FUNCTION pg_catalog.pg_try_advisory_xact_lock(integer, integer) TO m3_canonical_writer;
            ALTER ROLE m3_canonical_verifier SET default_transaction_read_only = on;
        `);
        process.stdout.write(
            JSON.stringify({
                status: 'bootstrapped',
                database: config.database,
                migration: 'V26.10',
                migration_status: migrationResult.status,
                writer_role: 'm3_canonical_writer',
                verifier_role: 'm3_canonical_verifier',
            }) + '\n'
        );
    } finally {
        await client.end();
    }
}

main().catch(error => {
    process.stderr.write(`${error.stack || error}\n`);
    process.exitCode = 1;
});
