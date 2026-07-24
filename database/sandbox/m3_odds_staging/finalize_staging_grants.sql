-- lifecycle: permanent
-- Sandbox-only grants, executed only after V26.8 and V26.9 have been applied.
REVOKE ALL ON odds_historical_import_runs, odds_historical_source_files,
    odds_historical_staging_observations, odds_historical_quarantine FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM fp_m3_sandbox_migrator;
GRANT SELECT, INSERT, UPDATE (status, actual_accepted_count, actual_quarantine_count, duplicate_count, failure_reason, completed_at, failed_at, rolled_back_at, updated_at)
    ON odds_historical_import_runs TO fp_m3_sandbox_writer;
GRANT SELECT, INSERT ON odds_historical_source_files TO fp_m3_sandbox_writer;
GRANT SELECT, INSERT ON odds_historical_staging_observations TO fp_m3_sandbox_writer;
GRANT SELECT, INSERT ON odds_historical_quarantine TO fp_m3_sandbox_writer;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, fp_m3_sandbox_reader;
REVOKE SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public FROM fp_m3_sandbox_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO fp_m3_sandbox_writer;
GRANT SELECT ON odds_historical_import_runs, odds_historical_source_files, odds_historical_staging_observations TO fp_m3_sandbox_reader;
REVOKE ALL ON odds_historical_quarantine FROM fp_m3_sandbox_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_owner REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_owner REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_migrator REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_migrator REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE fp_m3_sandbox_migrator REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
