'use strict';

// lifecycle: permanent
// 独立的 M3 canonical inventory insert-only writer。它不复用 FixtureRepository，
// 不执行 UPSERT/UPDATE/DELETE，也拒绝非 disposable 的运行授权。

const crypto = require('node:crypto');
const {
    CANONICAL_PROVIDER,
    immutableFingerprint,
    readOrdinaryArtifact,
    stableStringify,
} = require('./CanonicalInventoryContract');
const { validateProvenanceReceipt, validateRuntimeAuthorization } = require('./CanonicalInventoryAuthorization');

const SCHEMA_BASELINE = 'm3-canonical-inventory-v26.10';
const REQUIRED_MIGRATION_VERSION = 'V26.10';
const REQUIRED_MIGRATION_CHECKSUM = 'd4e83b7e6464dbb15e5ac3c2b15e5e848cac45607bc518e5ead684dbac54fed1';
const ADVISORY_LOCK_NAMESPACE = 1793;
const ADVISORY_LOCK_KEY = 1;
const MAX_EXCEPTION_SAMPLES = 20;
const GIT_REVISION = /^[0-9a-f]{40}$/;

class CanonicalInventoryWriterError extends Error {
    constructor(message, code = 'CANONICAL_WRITER_FAILURE', evidence = {}) {
        super(message);
        this.name = 'CanonicalInventoryWriterError';
        this.code = code;
        this.evidence = evidence;
    }
}

function createUuid() {
    return crypto.randomUUID();
}

function boundedEvidence(rows) {
    return rows.slice(0, MAX_EXCEPTION_SAMPLES).map(row => ({
        candidate_id: row.candidate.id,
        terminal: row.terminal,
        reason: row.reason,
    }));
}

function snapshotInputBinding(input) {
    if (
        !input?.path ||
        !Number.isInteger(input.byte_size) ||
        input.byte_size <= 0 ||
        !input?.artifact ||
        !input?.sha256
    ) {
        throw new CanonicalInventoryWriterError('artifact path and byte size are required', 'ARTIFACT_BINDING_MISSING');
    }
    return {
        path: input.path,
        byte_size: input.byte_size,
        sha256: input.sha256,
        artifact: structuredClone(input.artifact),
        parent_artifact_path: input.parent_artifact_path,
        runtime_authorization: structuredClone(input.runtimeAuthorization),
        provenance_receipt: structuredClone(input.provenanceReceipt),
    };
}

function assertArtifactStillImmutable(binding) {
    let rebound;
    try {
        rebound = readOrdinaryArtifact(binding.path, {
            sha256: binding.sha256,
            byte_size: binding.byte_size,
            parentArtifactPath: binding.parent_artifact_path,
            allowSyntheticTestOnly: binding.artifact.synthetic_test_only === true,
        });
    } catch (error) {
        throw new CanonicalInventoryWriterError('artifact changed before execution', 'ARTIFACT_MUTATED', {
            cause: error.code || error.message,
        });
    }
    if (stableStringify(rebound.artifact) !== stableStringify(binding.artifact)) {
        throw new CanonicalInventoryWriterError(
            'artifact content no longer matches authorized metadata',
            'ARTIFACT_MUTATED'
        );
    }
    return rebound;
}

function matchesCandidateExactly(row, candidate) {
    // PostgreSQL normalises a valid `...:00Z` value to `.000Z` on read. Compare
    // instants here, while lineage retains the source artifact's exact immutable
    // fingerprint; formatting alone must not turn a replay into a conflict.
    return (
        row.match_id === candidate.id &&
        String(row.external_id) === candidate.source_match_id &&
        row.league_name === candidate.competition &&
        row.season === candidate.season &&
        row.home_team === candidate.home_team &&
        row.away_team === candidate.away_team &&
        new Date(row.match_date).getTime() === new Date(candidate.kickoff_at).getTime() &&
        String(row.status).trim().toLowerCase() === candidate.application_status
    );
}

function classifyProviderDifference(candidate, existing) {
    if (existing.league_name !== candidate.competition) return 'conflict_competition';
    if (existing.season !== candidate.season) return 'conflict_season';
    if (existing.home_team !== candidate.home_team || existing.away_team !== candidate.away_team) {
        return 'conflict_home_away';
    }
    if (new Date(existing.match_date).getTime() !== new Date(candidate.kickoff_at).getTime()) return 'conflict_kickoff';
    return 'conflict_external_id';
}

function artifactShape(artifact, file) {
    return {
        artifact_sha256: file.sha256,
        artifact_kind: artifact.kind,
        business_hash: artifact.business_hash,
        identity_projection_hash: artifact.identity_projection_hash,
        byte_size: file.byte_size,
        candidate_count: artifact.candidate_count,
        competition: artifact.competition,
        season_scope: artifact.seasons,
        per_season_counts: artifact.per_season_counts,
        status_mapping_version: artifact.status_mapping_version,
    };
}

class CanonicalInventoryWriter {
    constructor({ pool, target, authorizationAuthority, codeRevision, afterAdvisoryLock = null } = {}) {
        if (!pool || typeof pool.connect !== 'function') {
            throw new CanonicalInventoryWriterError('writer requires a pg Pool');
        }
        if (
            !target?.serviceIdentity ||
            !target?.databaseIdentity ||
            !target?.writerRole ||
            target.classification !== 'disposable'
        ) {
            throw new CanonicalInventoryWriterError(
                'writer requires an independently configured disposable target identity',
                'TARGET_CLASSIFICATION_MISMATCH'
            );
        }
        if (!authorizationAuthority) {
            throw new CanonicalInventoryWriterError(
                'writer requires a trusted external authorization authority',
                'AUTHORIZATION_AUTHORITY_MISSING'
            );
        }
        if (typeof codeRevision !== 'string' || !GIT_REVISION.test(codeRevision)) {
            throw new CanonicalInventoryWriterError(
                'writer requires the actual 40-character git code revision',
                'CODE_REVISION_MISSING'
            );
        }
        this.pool = pool;
        this.target = target;
        this.authorizationAuthority = authorizationAuthority;
        this.codeRevision = codeRevision;
        this.afterAdvisoryLock = afterAdvisoryLock;
    }

    // eslint-disable-next-line complexity -- fixed schema and least-privilege boundary checks must fail closed together.
    async inspectTarget(client) {
        const result = await client.query(`
            SELECT current_database() AS database_identity,
                   current_user AS current_user,
                   session_user AS session_user,
                   current_setting('transaction_read_only') AS transaction_read_only,
                   current_setting('server_version_num') AS server_version_num,
                   to_regclass('public.m3_canonical_schema_migrations') IS NOT NULL AS migration_ledger_table,
                   to_regclass('public.m3_canonical_source_artifacts') IS NOT NULL AS artifact_table,
                   to_regclass('public.m3_canonical_import_runs') IS NOT NULL AS run_table,
                   to_regclass('public.m3_canonical_match_lineages') IS NOT NULL AS lineage_table,
                   EXISTS (
                       SELECT 1
                       FROM pg_index index_meta
                       JOIN pg_class index_class ON index_class.oid = index_meta.indexrelid
                       JOIN pg_namespace index_schema ON index_schema.oid = index_class.relnamespace
                       JOIN pg_class table_class ON table_class.oid = index_meta.indrelid
                       JOIN pg_namespace table_schema ON table_schema.oid = table_class.relnamespace
                       WHERE index_schema.nspname = 'public'
                         AND table_schema.nspname = 'public'
                         AND table_class.relname = 'matches'
                         AND index_class.relname = 'matches_m3_fotmob_external_id_uq'
                         AND index_meta.indisunique
                         AND index_meta.indisvalid
                         AND index_meta.indisready
                         AND ARRAY(
                             SELECT attribute.attname
                             FROM unnest(index_meta.indkey) WITH ORDINALITY AS key_column(attnum, ordinal)
                             JOIN pg_attribute attribute
                               ON attribute.attrelid = index_meta.indrelid
                              AND attribute.attnum = key_column.attnum
                             WHERE key_column.ordinal <= index_meta.indnkeyatts
                             ORDER BY key_column.ordinal
                         ) = ARRAY['external_id']::name[]
                         AND regexp_replace(
                             regexp_replace(lower(COALESCE(pg_get_expr(index_meta.indpred, index_meta.indrelid), '')), '::[a-z_ ]+', '', 'g'),
                             '[[:space:]()]',
                             '',
                             'g'
                         ) = 'canonical_provider=''fotmob'''
                   ) AS provider_index,
                   EXISTS (
                       SELECT 1
                       FROM pg_index index_meta
                       JOIN pg_class index_class ON index_class.oid = index_meta.indexrelid
                       JOIN pg_namespace index_schema ON index_schema.oid = index_class.relnamespace
                       JOIN pg_class table_class ON table_class.oid = index_meta.indrelid
                       JOIN pg_namespace table_schema ON table_schema.oid = table_class.relnamespace
                       WHERE index_schema.nspname = 'public'
                         AND table_schema.nspname = 'public'
                         AND table_class.relname = 'matches'
                         AND index_class.relname = 'matches_m3_epl_fixture_identity_uq'
                         AND index_meta.indisunique
                         AND index_meta.indisvalid
                         AND index_meta.indisready
                         AND ARRAY(
                             SELECT attribute.attname
                             FROM unnest(index_meta.indkey) WITH ORDINALITY AS key_column(attnum, ordinal)
                             JOIN pg_attribute attribute
                               ON attribute.attrelid = index_meta.indrelid
                              AND attribute.attnum = key_column.attnum
                             WHERE key_column.ordinal <= index_meta.indnkeyatts
                             ORDER BY key_column.ordinal
                         ) = ARRAY['league_name', 'season', 'home_team', 'away_team']::name[]
                         AND lower(COALESCE(pg_get_expr(index_meta.indpred, index_meta.indrelid), '')) LIKE '%league_name%premier league%'
                         AND lower(COALESCE(pg_get_expr(index_meta.indpred, index_meta.indrelid), '')) LIKE '%season%2022/2023%2023/2024%2024/2025%'
                         AND lower(COALESCE(pg_get_expr(index_meta.indpred, index_meta.indrelid), '')) LIKE '%canonical_provider%fotmob%'
                   ) AS fixture_index
        `);
        const identity = result.rows[0];
        if (identity.database_identity !== this.target.databaseIdentity) {
            throw new CanonicalInventoryWriterError('database identity mismatch', 'TARGET_IDENTITY_MISMATCH');
        }
        if (identity.current_user !== this.target.writerRole || identity.session_user !== this.target.writerRole) {
            throw new CanonicalInventoryWriterError('database writer role mismatch', 'TARGET_WRITER_ROLE_MISMATCH');
        }
        if (identity.transaction_read_only === 'on') {
            throw new CanonicalInventoryWriterError('target transaction is read-only', 'TARGET_READ_ONLY');
        }
        if (
            !identity.artifact_table ||
            !identity.run_table ||
            !identity.lineage_table ||
            !identity.migration_ledger_table ||
            !identity.provider_index ||
            !identity.fixture_index
        ) {
            throw new CanonicalInventoryWriterError('schema baseline is incomplete', 'SCHEMA_BASELINE_MISMATCH');
        }
        const permissions = await client.query(
            `
            WITH RECURSIVE read_tables(table_name) AS (
                VALUES
                    ('public.matches'::text),
                    ('public.m3_canonical_source_artifacts'::text),
                    ('public.m3_canonical_import_runs'::text),
                    ('public.m3_canonical_match_lineages'::text),
                    ('public.m3_canonical_schema_migrations'::text)
            ),
            insert_tables(table_name) AS (
                VALUES
                    ('public.matches'::text),
                    ('public.m3_canonical_source_artifacts'::text),
                    ('public.m3_canonical_import_runs'::text),
                    ('public.m3_canonical_match_lineages'::text)
            ),
            role_memberships(role_id) AS (
                SELECT roleid
                FROM pg_auth_members
                WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user)
                UNION
                SELECT membership.roleid
                FROM pg_auth_members membership
                JOIN role_memberships inherited ON membership.member = inherited.role_id
            ),
            required_functions(function_oid) AS (
                VALUES
                    ('pg_catalog.pg_try_advisory_xact_lock(integer,integer)'::regprocedure),
                    ('public.m3_canonical_inventory_acquire_locks_v1()'::regprocedure)
            )
            SELECT
                EXISTS (
                    SELECT 1
                    FROM public.m3_canonical_schema_migrations
                    WHERE version = $1 AND sha256_checksum = $2
                ) AS migration_baseline,
                has_database_privilege(current_user, current_database(), 'CONNECT') AS database_connect,
                NOT has_database_privilege(current_user, current_database(), 'TEMPORARY') AS database_temp_revoked,
                has_schema_privilege(current_user, 'public', 'USAGE') AS schema_usage,
                NOT has_schema_privilege(current_user, 'public', 'CREATE') AS schema_create_revoked,
                NOT EXISTS (SELECT 1 FROM role_memberships) AS no_role_memberships,
                NOT EXISTS (
                    SELECT 1
                    FROM pg_roles
                    WHERE rolname = current_user
                      AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
                ) AS role_attributes_restricted,
                (SELECT bool_and(has_table_privilege(current_user, table_name, 'SELECT')) FROM read_tables) AS table_select,
                (SELECT bool_and(has_table_privilege(current_user, table_name, 'INSERT')) FROM insert_tables) AS table_insert,
                (
                    SELECT bool_and(
                        NOT has_table_privilege(
                            current_user,
                            table_name,
                            'UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER'
                        )
                    )
                    FROM read_tables
                ) AS table_mutation_revoked,
                (
                    SELECT bool_and(class.relowner <> (SELECT oid FROM pg_roles WHERE rolname = current_user))
                    FROM read_tables
                    JOIN pg_class class ON class.oid = to_regclass(read_tables.table_name)
                ) AS table_ownership_restricted,
                (
                    SELECT bool_and(has_function_privilege(current_user, function_oid, 'EXECUTE'))
                    FROM required_functions
                ) AS required_functions_executable,
                (
                    SELECT bool_and(function.proowner <> (SELECT oid FROM pg_roles WHERE rolname = current_user))
                    FROM required_functions
                    JOIN pg_proc function ON function.oid = required_functions.function_oid
                ) AS function_ownership_restricted,
                (
                    SELECT bool_and(
                        NOT EXISTS (
                            SELECT 1
                            FROM aclexplode(COALESCE(function.proacl, acldefault('f', function.proowner))) AS acl
                            WHERE acl.grantee = 0 AND acl.privilege_type = 'EXECUTE'
                        )
                    )
                    FROM required_functions
                    JOIN pg_proc function ON function.oid = required_functions.function_oid
                ) AS required_functions_public_revoked
            `,
            [REQUIRED_MIGRATION_VERSION, REQUIRED_MIGRATION_CHECKSUM]
        );
        const boundary = permissions.rows[0];
        if (
            !boundary.migration_baseline ||
            !boundary.database_connect ||
            !boundary.database_temp_revoked ||
            !boundary.schema_usage ||
            !boundary.schema_create_revoked ||
            !boundary.no_role_memberships ||
            !boundary.role_attributes_restricted ||
            !boundary.table_select ||
            !boundary.table_insert ||
            !boundary.table_mutation_revoked ||
            !boundary.table_ownership_restricted ||
            !boundary.required_functions_executable ||
            !boundary.function_ownership_restricted ||
            !boundary.required_functions_public_revoked
        ) {
            throw new CanonicalInventoryWriterError(
                'target writer role violates the canonical least-privilege boundary',
                'BLOCKED_PERMISSION_BOUNDARY'
            );
        }
        return identity;
    }

    async findArtifact(client, sha256) {
        const result = await client.query(
            'SELECT * FROM public.m3_canonical_source_artifacts WHERE artifact_sha256 = $1',
            [sha256]
        );
        return result.rows[0] || null;
    }

    async assertExistingArtifactEquivalent(client, existing, expected) {
        for (const field of [
            'artifact_kind',
            'business_hash',
            'identity_projection_hash',
            'byte_size',
            'candidate_count',
            'competition',
            'status_mapping_version',
        ]) {
            if (String(existing[field]) !== String(expected[field])) {
                throw new CanonicalInventoryWriterError(
                    'existing artifact metadata conflicts',
                    'ARTIFACT_METADATA_CONFLICT'
                );
            }
        }
        if (
            stableStringify(existing.season_scope) !== stableStringify(expected.season_scope) ||
            stableStringify(existing.per_season_counts) !== stableStringify(expected.per_season_counts)
        ) {
            throw new CanonicalInventoryWriterError(
                'existing artifact population metadata conflicts',
                'ARTIFACT_METADATA_CONFLICT'
            );
        }
        return existing;
    }

    async insertArtifact(client, shape, parentArtifactId = null) {
        const result = await client.query(
            `
            INSERT INTO public.m3_canonical_source_artifacts
                (artifact_sha256, artifact_kind, parent_artifact_id, business_hash, identity_projection_hash, byte_size, candidate_count, competition, season_scope, per_season_counts, status_mapping_version)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11)
            RETURNING *
        `,
            [
                shape.artifact_sha256,
                shape.artifact_kind,
                parentArtifactId,
                shape.business_hash,
                shape.identity_projection_hash,
                shape.byte_size,
                shape.candidate_count,
                shape.competition,
                JSON.stringify(shape.season_scope),
                JSON.stringify(shape.per_season_counts),
                shape.status_mapping_version,
            ]
        );
        return result.rows[0];
    }

    async ensureArtifacts(client, input) {
        const shape = artifactShape(input.artifact, input);
        let parent = null;
        let parentInserted = false;
        if (input.artifact.kind === 'canary') {
            const declared = input.artifact.parent_master;
            const parentShape = {
                artifact_sha256: declared.sha256,
                artifact_kind: 'master',
                business_hash: declared.business_hash,
                identity_projection_hash: declared.identity_projection_hash,
                byte_size: declared.byte_size,
                candidate_count: declared.candidate_count,
                competition: input.artifact.competition,
                season_scope: input.artifact.seasons,
                per_season_counts: declared.per_season_counts,
                status_mapping_version: declared.status_mapping_version,
            };
            parent = await this.findArtifact(client, parentShape.artifact_sha256);
            if (parent) await this.assertExistingArtifactEquivalent(client, parent, parentShape);
            else {
                parent = await this.insertArtifact(client, parentShape);
                parentInserted = true;
            }
        }
        let artifact = await this.findArtifact(client, shape.artifact_sha256);
        let artifactInserted = false;
        if (artifact) await this.assertExistingArtifactEquivalent(client, artifact, shape);
        else {
            artifact = await this.insertArtifact(client, shape, parent?.artifact_id || null);
            artifactInserted = true;
        }
        if (input.artifact.kind === 'canary' && artifact.parent_artifact_id !== parent.artifact_id) {
            throw new CanonicalInventoryWriterError('canary parent artifact conflict', 'ARTIFACT_PARENT_CONFLICT');
        }
        return {
            artifact,
            parent,
            artifacts_inserted: Number(parentInserted) + Number(artifactInserted),
        };
    }

    async loadExistingMatches(client, candidate) {
        const result = await client.query(
            `
            SELECT match_id, external_id, league_name, season, home_team, away_team, match_date, status, canonical_provider
            FROM public.matches
            WHERE match_id = $1
               OR (canonical_provider = $2 AND external_id = $3)
               OR (canonical_provider = $2 AND league_name = $4 AND season = $5 AND home_team = $6 AND away_team = $7)
            ORDER BY match_id ASC
        `,
            [
                candidate.id,
                CANONICAL_PROVIDER,
                candidate.source_match_id,
                candidate.competition,
                candidate.season,
                candidate.home_team,
                candidate.away_team,
            ]
        );
        return result.rows;
    }

    async classifyCandidate(client, candidate, artifact) {
        const targetFingerprint = immutableFingerprint(candidate);
        const rows = await this.loadExistingMatches(client, candidate);
        const providerMatch = rows.find(
            row =>
                row.canonical_provider === CANONICAL_PROVIDER && String(row.external_id) === candidate.source_match_id
        );
        const fixtureMatch = rows.find(
            row =>
                row.canonical_provider === CANONICAL_PROVIDER &&
                row.league_name === candidate.competition &&
                row.season === candidate.season &&
                row.home_team === candidate.home_team &&
                row.away_team === candidate.away_team
        );
        const idMatch = rows.find(row => row.match_id === candidate.id);
        const existing = providerMatch || fixtureMatch || idMatch;
        if (!existing) return { candidate, terminal: 'inserted', fingerprint: targetFingerprint, match: null };
        if (providerMatch) {
            if (!matchesCandidateExactly(providerMatch, candidate)) {
                return {
                    candidate,
                    terminal: classifyProviderDifference(candidate, providerMatch),
                    fingerprint: targetFingerprint,
                    match: providerMatch,
                    reason: 'provider_identity_divergence',
                };
            }
            const currentLineage = await client.query(
                `
                SELECT 1 FROM public.m3_canonical_match_lineages
                WHERE artifact_id = $1 AND candidate_id = $2 AND match_id = $3 AND immutable_fingerprint = $4
            `,
                [artifact.artifact_id, candidate.id, providerMatch.match_id, targetFingerprint]
            );
            if (currentLineage.rowCount === 1) {
                return { candidate, terminal: 'exact_duplicate', fingerprint: targetFingerprint, match: providerMatch };
            }
            if (artifact.artifact_kind === 'master') {
                const parentLineage = await client.query(
                    `
                    SELECT 1
                    FROM public.m3_canonical_match_lineages lineage
                    JOIN public.m3_canonical_source_artifacts prior ON prior.artifact_id = lineage.artifact_id
                    WHERE lineage.match_id = $1 AND lineage.candidate_id = $2 AND lineage.immutable_fingerprint = $3
                      AND prior.parent_artifact_id = $4
                    LIMIT 1
                `,
                    [providerMatch.match_id, candidate.id, targetFingerprint, artifact.artifact_id]
                );
                if (parentLineage.rowCount === 1) {
                    return {
                        candidate,
                        terminal: 'already_present_equivalent',
                        fingerprint: targetFingerprint,
                        match: providerMatch,
                    };
                }
            }
            return {
                candidate,
                terminal: 'conflict_external_id',
                fingerprint: targetFingerprint,
                match: providerMatch,
                reason: 'equivalent row lacks permitted lineage',
            };
        }
        if (fixtureMatch) {
            const terminal =
                new Date(fixtureMatch.match_date).getTime() !== new Date(candidate.kickoff_at).getTime()
                    ? 'conflict_kickoff'
                    : 'conflict_business_identity';
            return {
                candidate,
                terminal,
                fingerprint: targetFingerprint,
                match: fixtureMatch,
                reason: 'fixture_identity_occupied',
            };
        }
        return {
            candidate,
            terminal: 'conflict_business_identity',
            fingerprint: targetFingerprint,
            match: idMatch,
            reason: 'match_id_occupied',
        };
    }

    async insertRun(client, artifact, receipt) {
        const runId = createUuid();
        await client.query(
            `
            INSERT INTO public.m3_canonical_import_runs
                (run_id, artifact_id, execution_id, authorization_receipt_sha256, code_revision)
            VALUES ($1, $2, $3, $4, $5)
        `,
            [runId, artifact.artifact_id, receipt.execution_id, receipt.receipt_sha256, receipt.code_revision]
        );
        return runId;
    }

    async persistClassified(client, classified, artifact, runId, provenanceKind) {
        for (const row of classified) {
            let matchId = row.match?.match_id;
            if (row.terminal === 'inserted') {
                matchId = row.candidate.id;
                await client.query(
                    `
                    INSERT INTO public.matches
                        (match_id, external_id, league_name, season, home_team, away_team, match_date, status, is_finished, data_source, pipeline_status, canonical_provider, source_type, evidence_level, is_production_scope, is_reconciliation_eligible, is_training_eligible)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz, $8, $9, 'FotMob', 'pending', $10, $11, $12, FALSE, FALSE, FALSE)
                `,
                    [
                        matchId,
                        row.candidate.source_match_id,
                        row.candidate.competition,
                        row.candidate.season,
                        row.candidate.home_team,
                        row.candidate.away_team,
                        row.candidate.kickoff_at,
                        row.candidate.application_status,
                        row.candidate.application_status === 'finished',
                        CANONICAL_PROVIDER,
                        provenanceKind === 'synthetic-test-only' ? 'synthetic' : 'fotmob_pageprops',
                        provenanceKind === 'synthetic-test-only' ? 'synthetic_invalid' : 'missing',
                    ]
                );
            }
            if (row.terminal === 'inserted' || row.terminal === 'already_present_equivalent') {
                await client.query(
                    `
                    INSERT INTO public.m3_canonical_match_lineages
                        (match_id, artifact_id, created_import_run_id, candidate_id, provider_match_id, provider_status, status_mapping_version, application_status, immutable_fingerprint)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                `,
                    [
                        matchId,
                        artifact.artifact_id,
                        runId,
                        row.candidate.id,
                        row.candidate.source_match_id,
                        row.candidate.provider_status,
                        row.candidate.status_mapping_version,
                        row.candidate.application_status,
                        row.fingerprint,
                    ]
                );
            }
        }
    }

    // eslint-disable-next-line complexity -- this fixed sequence mirrors the transactional safety contract.
    async execute(input) {
        if (!input?.artifact || !input?.candidates || !input?.sha256) {
            throw new CanonicalInventoryWriterError('validated artifact input is required');
        }
        const inputBinding = snapshotInputBinding(input);
        const client = await this.pool.connect();
        try {
            const targetIdentity = await this.inspectTarget(client);
            const binding = {
                service_identity: this.target.serviceIdentity,
                database_identity: targetIdentity.database_identity,
                schema_baseline: SCHEMA_BASELINE,
                target_classification: this.target.classification,
                writer_role: targetIdentity.current_user,
                code_revision: this.codeRevision,
                artifact: {
                    sha256: inputBinding.sha256,
                    business_hash: inputBinding.artifact.business_hash,
                    identity_projection_hash: inputBinding.artifact.identity_projection_hash,
                    kind: inputBinding.artifact.kind,
                    candidate_count: inputBinding.artifact.candidate_count,
                    competition: inputBinding.artifact.competition,
                    seasons: inputBinding.artifact.seasons,
                },
            };
            const receipt = validateRuntimeAuthorization(
                inputBinding.runtime_authorization,
                binding,
                this.authorizationAuthority
            );
            const preflightedInput = assertArtifactStillImmutable(inputBinding);
            const provenance = validateProvenanceReceipt(inputBinding.provenance_receipt, {
                sha256: inputBinding.sha256,
                target_classification: 'disposable',
                artifact_synthetic_test_only: preflightedInput.artifact.synthetic_test_only === true,
            });
            await client.query('BEGIN ISOLATION LEVEL SERIALIZABLE');
            try {
                await client.query("SET LOCAL lock_timeout = '5s'; SET LOCAL statement_timeout = '30s'");
                const lock = await client.query('SELECT pg_catalog.pg_try_advisory_xact_lock($1, $2) AS locked', [
                    ADVISORY_LOCK_NAMESPACE,
                    ADVISORY_LOCK_KEY,
                ]);
                if (!lock.rows[0].locked) {
                    throw new CanonicalInventoryWriterError('advisory transaction lock busy', 'LOCK_BUSY');
                }
                if (this.afterAdvisoryLock) await this.afterAdvisoryLock();
                await client.query('SELECT public.m3_canonical_inventory_acquire_locks_v1()');
                // Only the second physical-file read feeds persistence. In-memory
                // caller objects may change after authorization, but cannot change
                // the signed and hash-bound rows that reach this transaction.
                const verifiedInput = assertArtifactStillImmutable(inputBinding);
                const artifactState = await this.ensureArtifacts(client, verifiedInput);
                const { artifact } = artifactState;
                const classified = [];
                for (const candidate of verifiedInput.candidates) {
                    classified.push(await this.classifyCandidate(client, candidate, artifact));
                }
                const terminalCounts = classified.reduce(
                    (counts, row) => ({ ...counts, [row.terminal]: (counts[row.terminal] || 0) + 1 }),
                    {}
                );
                const failures = classified.filter(
                    row => !['inserted', 'exact_duplicate', 'already_present_equivalent'].includes(row.terminal)
                );
                if (failures.length > 0) {
                    throw new CanonicalInventoryWriterError(
                        `canonical conflict preflight failed: ${failures[0].terminal}`,
                        'CANONICAL_CONFLICT',
                        { samples: boundedEvidence(failures), terminal_counts: terminalCounts }
                    );
                }
                const changing = classified.filter(row => row.terminal !== 'exact_duplicate');
                if (changing.length > 0) {
                    const runId = await this.insertRun(client, artifact, receipt);
                    await this.persistClassified(client, classified, artifact, runId, provenance.kind);
                }
                const reconciled =
                    (terminalCounts.inserted || 0) +
                    (terminalCounts.exact_duplicate || 0) +
                    (terminalCounts.already_present_equivalent || 0);
                if (reconciled !== verifiedInput.candidates.length) {
                    throw new CanonicalInventoryWriterError(
                        'terminal arithmetic did not close',
                        'TERMINAL_ARITHMETIC_FAILURE'
                    );
                }
                await client.query('COMMIT');
                return {
                    status: 'committed',
                    target: {
                        database_identity: targetIdentity.database_identity,
                        current_user: targetIdentity.current_user,
                        session_user: targetIdentity.session_user,
                    },
                    artifact_sha256: verifiedInput.sha256,
                    candidate_count: verifiedInput.candidates.length,
                    terminal_counts: terminalCounts,
                    database_delta: {
                        matches: terminalCounts.inserted || 0,
                        artifacts: changing.length > 0 ? artifactState.artifacts_inserted : 0,
                        import_runs: changing.length > 0 ? 1 : 0,
                        lineages: changing.length,
                    },
                };
            } catch (error) {
                await client.query('ROLLBACK');
                throw error;
            }
        } finally {
            client.release();
        }
    }
}

module.exports = {
    ADVISORY_LOCK_KEY,
    ADVISORY_LOCK_NAMESPACE,
    CanonicalInventoryWriter,
    CanonicalInventoryWriterError,
    SCHEMA_BASELINE,
    classifyProviderDifference,
    assertArtifactStillImmutable,
    matchesCandidateExactly,
};
