-- lifecycle: permanent
-- M3 canonical inventory contract. Additive only: this migration never backfills,
-- updates, or deletes existing matches. It is applied only to disposable targets
-- in this implementation phase; persistent execution needs separate authorization.

ALTER TABLE public.matches
    ADD COLUMN IF NOT EXISTS canonical_provider VARCHAR(32);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'matches_canonical_provider_fotmob_only' AND conrelid = 'public.matches'::regclass) THEN
        ALTER TABLE public.matches
            ADD CONSTRAINT matches_canonical_provider_fotmob_only
            CHECK (canonical_provider IS NULL OR canonical_provider = 'fotmob');
    END IF;
END;
$$;

-- IS NOT TRUE is deliberate: legacy rows outside the M3 EPL scope retain their
-- nullable provider values, whereas every in-scope canonical row fails closed.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'matches_m3_epl_canonical_identity_required' AND conrelid = 'public.matches'::regclass) THEN
        ALTER TABLE public.matches
            ADD CONSTRAINT matches_m3_epl_canonical_identity_required
            CHECK (
                (league_name = 'Premier League' AND season IN ('2022/2023', '2023/2024', '2024/2025')) IS NOT TRUE
                OR (
                    canonical_provider IS NOT NULL
                    AND canonical_provider = 'fotmob'
                    AND external_id IS NOT NULL
                )
            );
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS matches_m3_fotmob_external_id_uq
    ON public.matches (external_id)
    WHERE canonical_provider = 'fotmob';

-- Kickoff is intentionally not part of this key: a timing drift is a conflict,
-- not permission to create a second canonical fixture row.
CREATE UNIQUE INDEX IF NOT EXISTS matches_m3_epl_fixture_identity_uq
    ON public.matches (league_name, season, home_team, away_team)
    WHERE league_name = 'Premier League'
      AND season IN ('2022/2023', '2023/2024', '2024/2025')
      AND canonical_provider = 'fotmob';

-- This target-local binding is provisioned by the environment owner before a
-- writer can run. It prevents a signed receipt for one disposable instance
-- from being replayed against another similarly named/schema-compatible one.
CREATE TABLE IF NOT EXISTS public.m3_canonical_target_identity (
    binding_key VARCHAR(64) PRIMARY KEY CHECK (binding_key = 'canonical_inventory_v1'),
    service_identity VARCHAR(128) NOT NULL UNIQUE
        CHECK (service_identity ~ '^[a-z0-9][a-z0-9_.:-]{2,127}$'),
    database_oid OID NOT NULL,
    -- This owner-provisioned nonce is deliberately rotated after a restore.
    -- PostgreSQL OIDs are cluster-local and therefore cannot by themselves
    -- prevent a receipt from being replayed against a restored lookalike.
    instance_nonce UUID NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.m3_canonical_source_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artifact_sha256 CHAR(64) NOT NULL UNIQUE CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_kind VARCHAR(16) NOT NULL CHECK (artifact_kind IN ('master', 'canary')),
    parent_artifact_id UUID REFERENCES public.m3_canonical_source_artifacts(artifact_id) ON DELETE RESTRICT,
    business_hash CHAR(64) NOT NULL CHECK (business_hash ~ '^[0-9a-f]{64}$'),
    identity_projection_hash CHAR(64) NOT NULL CHECK (identity_projection_hash ~ '^[0-9a-f]{64}$'),
    byte_size BIGINT NOT NULL CHECK (byte_size > 0),
    candidate_count INTEGER NOT NULL CHECK (candidate_count > 0),
    competition VARCHAR(100) NOT NULL CHECK (competition = 'Premier League'),
    season_scope JSONB NOT NULL,
    per_season_counts JSONB NOT NULL,
    status_mapping_version VARCHAR(64) NOT NULL CHECK (status_mapping_version = 'fotmob-status-to-matches-status/v1'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (artifact_kind = 'master' AND parent_artifact_id IS NULL)
        OR (artifact_kind = 'canary' AND parent_artifact_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.m3_canonical_import_runs (
    run_id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL REFERENCES public.m3_canonical_source_artifacts(artifact_id) ON DELETE RESTRICT,
    execution_id VARCHAR(128) NOT NULL UNIQUE,
    authorization_receipt_sha256 CHAR(64) NOT NULL CHECK (authorization_receipt_sha256 ~ '^[0-9a-f]{64}$'),
    code_revision VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS public.m3_canonical_match_lineages (
    lineage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id VARCHAR(50) NOT NULL REFERENCES public.matches(match_id) ON DELETE RESTRICT,
    artifact_id UUID NOT NULL REFERENCES public.m3_canonical_source_artifacts(artifact_id) ON DELETE RESTRICT,
    created_import_run_id UUID NOT NULL,
    candidate_id VARCHAR(100) NOT NULL,
    provider_match_id VARCHAR(100) NOT NULL,
    provider_status VARCHAR(50) NOT NULL,
    status_mapping_version VARCHAR(64) NOT NULL CHECK (status_mapping_version = 'fotmob-status-to-matches-status/v1'),
    application_status VARCHAR(50) NOT NULL,
    immutable_fingerprint CHAR(64) NOT NULL CHECK (immutable_fingerprint ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (created_import_run_id, artifact_id)
        REFERENCES public.m3_canonical_import_runs(run_id, artifact_id) ON DELETE RESTRICT,
    UNIQUE (artifact_id, candidate_id),
    UNIQUE (match_id, artifact_id)
);

CREATE OR REPLACE FUNCTION public.m3_canonical_inventory_acquire_locks_v1()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    LOCK TABLE public.m3_canonical_source_artifacts IN SHARE ROW EXCLUSIVE MODE;
    LOCK TABLE public.m3_canonical_import_runs IN SHARE ROW EXCLUSIVE MODE;
    LOCK TABLE public.m3_canonical_match_lineages IN SHARE ROW EXCLUSIVE MODE;
    LOCK TABLE public.matches IN SHARE ROW EXCLUSIVE MODE;
END;
$$;

-- Role provisioning is an environment-owned deployment action. This migration
-- removes the ambient execution path; disposable proof provisions a non-login
-- owner and an explicit writer role before testing the function.
REVOKE ALL ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() FROM PUBLIC;

COMMENT ON FUNCTION public.m3_canonical_inventory_acquire_locks_v1() IS
'M3 controlled lock sequence for insert-only canonical inventory writer; execute must be granted explicitly.';
COMMENT ON COLUMN public.matches.canonical_provider IS
'M3 canonical identity namespace; nullable only for legacy/out-of-scope rows.';
