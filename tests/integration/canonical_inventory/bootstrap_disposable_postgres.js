'use strict';

// lifecycle: test-fixture
// Bootstrap only the task-labelled disposable PostgreSQL database. It creates
// a minimal current matches shape, applies V26.10 once, then provisions a
// non-login lock-function owner and an insert-only proof writer role.

const fs = require('node:fs');
const path = require('node:path');
const { Client } = require('pg');

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
        await client.query(migration);
        await client.query(`
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'm3_canonical_owner') THEN CREATE ROLE m3_canonical_owner NOLOGIN; END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'm3_canonical_writer') THEN CREATE ROLE m3_canonical_writer LOGIN PASSWORD 'm3_canonical_writer_proof'; END IF;
            END $$;
            ALTER TABLE public.matches OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_source_artifacts OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_import_runs OWNER TO m3_canonical_owner;
            ALTER TABLE public.m3_canonical_match_lineages OWNER TO m3_canonical_owner;
            ALTER FUNCTION public.m3_canonical_inventory_acquire_locks_v1() OWNER TO m3_canonical_owner;
        `);
        await client.query(`
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
            REVOKE ALL ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() FROM PUBLIC;
            REVOKE ALL ON FUNCTION pg_catalog.pg_try_advisory_xact_lock(integer, integer) FROM PUBLIC;
            REVOKE TEMPORARY ON DATABASE ${JSON.stringify(config.database)} FROM PUBLIC;
            GRANT USAGE ON SCHEMA public TO m3_canonical_owner;
            GRANT CONNECT ON DATABASE ${JSON.stringify(config.database)} TO m3_canonical_writer;
            GRANT USAGE ON SCHEMA public TO m3_canonical_writer;
            GRANT SELECT, INSERT ON public.matches, public.m3_canonical_source_artifacts, public.m3_canonical_import_runs, public.m3_canonical_match_lineages TO m3_canonical_writer;
            GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO m3_canonical_writer;
            GRANT EXECUTE ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() TO m3_canonical_writer;
            GRANT EXECUTE ON FUNCTION pg_catalog.pg_try_advisory_xact_lock(integer, integer) TO m3_canonical_writer;
        `);
        process.stdout.write(
            JSON.stringify({
                status: 'bootstrapped',
                database: config.database,
                migration: 'V26.10',
                writer_role: 'm3_canonical_writer',
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
