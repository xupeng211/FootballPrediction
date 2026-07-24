-- lifecycle: permanent
-- Sandbox-only bootstrap. This file is never a production migration and is run only
-- by scripts/ops/odds_staging/m3_persistent_sandbox.sh against the exact sandbox DB.
\set ON_ERROR_STOP on
\getenv migrator_password M3_SANDBOX_MIGRATOR_PASSWORD
\getenv writer_password M3_SANDBOX_WRITER_PASSWORD
\getenv reader_password M3_SANDBOX_READER_PASSWORD
SELECT format('CREATE ROLE fp_m3_sandbox_migrator LOGIN NOINHERIT PASSWORD %L', :'migrator_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fp_m3_sandbox_migrator') \gexec
SELECT format('CREATE ROLE fp_m3_sandbox_writer LOGIN NOINHERIT PASSWORD %L', :'writer_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fp_m3_sandbox_writer') \gexec
SELECT format('CREATE ROLE fp_m3_sandbox_reader LOGIN NOINHERIT PASSWORD %L', :'reader_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fp_m3_sandbox_reader') \gexec

CREATE TABLE IF NOT EXISTS odds_staging_schema_migrations (
    version TEXT PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    sha256_checksum CHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT NOT NULL,
    execution_duration_ms INTEGER NOT NULL CHECK (execution_duration_ms >= 0)
);
ALTER TABLE odds_staging_schema_migrations OWNER TO fp_m3_sandbox_migrator;
SELECT format('REVOKE ALL PRIVILEGES ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO fp_m3_sandbox_migrator, fp_m3_sandbox_writer, fp_m3_sandbox_reader', current_database()) \gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO fp_m3_sandbox_migrator, fp_m3_sandbox_writer, fp_m3_sandbox_reader;
GRANT CREATE ON SCHEMA public TO fp_m3_sandbox_migrator;
GRANT SELECT, INSERT ON odds_staging_schema_migrations TO fp_m3_sandbox_migrator;

-- PostgreSQL defaults PUBLIC EXECUTE on newly created functions. Make the
-- sandbox contract explicit for both principals that can create objects.
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_owner REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_owner REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_migrator REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_migrator REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_migrator REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
