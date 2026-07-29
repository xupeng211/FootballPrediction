'use strict';

// lifecycle: permanent
// 独立的 M3 canonical inventory insert-only writer。它不复用 FixtureRepository，
// 不执行 UPSERT/UPDATE/DELETE，也拒绝非 disposable 的运行授权。

const crypto = require('node:crypto');
const {
    CANONICAL_PROVIDER,
    CanonicalInventoryContractError,
    immutableFingerprint,
    sha256Text,
    stableStringify,
} = require('./CanonicalInventoryContract');
const {
    CanonicalInventoryAuthorizationError,
    validateProvenanceReceipt,
    validateRuntimeAuthorization,
} = require('./CanonicalInventoryAuthorization');

const SCHEMA_BASELINE = 'm3-canonical-inventory-v26.10';
const ADVISORY_LOCK_NAMESPACE = 1793;
const ADVISORY_LOCK_KEY = 1;
const MAX_EXCEPTION_SAMPLES = 20;

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
        candidate_id: row.candidate_id,
        terminal: row.terminal,
        reason: row.reason,
    }));
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
        String(row.status).trim().toLowerCase() === candidate.status
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
    };
}

class CanonicalInventoryWriter {
    constructor({ pool, target, codeRevision = 'unknown' } = {}) {
        if (!pool || typeof pool.connect !== 'function') {
            throw new CanonicalInventoryWriterError('writer requires a pg Pool');
        }
        if (!target?.serviceIdentity || !target?.databaseIdentity) {
            throw new CanonicalInventoryWriterError('writer requires explicit target identities');
        }
        this.pool = pool;
        this.target = target;
        this.codeRevision = codeRevision;
    }

    async inspectTarget(client) {
        const result = await client.query(`
            SELECT current_database() AS database_identity,
                   current_user AS current_user,
                   current_setting('transaction_read_only') AS transaction_read_only,
                   current_setting('server_version_num') AS server_version_num,
                   to_regclass('public.m3_canonical_source_artifacts') IS NOT NULL AS artifact_table,
                   to_regclass('public.m3_canonical_import_runs') IS NOT NULL AS run_table,
                   to_regclass('public.m3_canonical_match_lineages') IS NOT NULL AS lineage_table,
                   EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'matches_m3_fotmob_external_id_uq') AS provider_index,
                   EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'matches_m3_epl_fixture_identity_uq') AS fixture_index
        `);
        const identity = result.rows[0];
        if (identity.database_identity !== this.target.databaseIdentity) {
            throw new CanonicalInventoryWriterError('database identity mismatch', 'TARGET_IDENTITY_MISMATCH');
        }
        if (identity.transaction_read_only === 'on') {
            throw new CanonicalInventoryWriterError('target transaction is read-only', 'TARGET_READ_ONLY');
        }
        if (
            !identity.artifact_table ||
            !identity.run_table ||
            !identity.lineage_table ||
            !identity.provider_index ||
            !identity.fixture_index
        ) {
            throw new CanonicalInventoryWriterError('schema baseline is incomplete', 'SCHEMA_BASELINE_MISMATCH');
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
                (artifact_sha256, artifact_kind, parent_artifact_id, business_hash, identity_projection_hash, byte_size, candidate_count, competition, season_scope, per_season_counts)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb)
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
            ]
        );
        return result.rows[0];
    }

    async ensureArtifacts(client, input) {
        const shape = artifactShape(input.artifact, input);
        let parent = null;
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
            };
            parent = await this.findArtifact(client, parentShape.artifact_sha256);
            if (parent) await this.assertExistingArtifactEquivalent(client, parent, parentShape);
            else parent = await this.insertArtifact(client, parentShape);
        }
        let artifact = await this.findArtifact(client, shape.artifact_sha256);
        if (artifact) await this.assertExistingArtifactEquivalent(client, artifact, shape);
        else artifact = await this.insertArtifact(client, shape, parent?.artifact_id || null);
        if (input.artifact.kind === 'canary' && artifact.parent_artifact_id !== parent.artifact_id) {
            throw new CanonicalInventoryWriterError('canary parent artifact conflict', 'ARTIFACT_PARENT_CONFLICT');
        }
        return {
            artifact,
            parent,
            artifactWasPresent: Boolean(await this.findArtifact(client, shape.artifact_sha256)),
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
            [runId, artifact.artifact_id, receipt.execution_id, sha256Text(stableStringify(receipt)), this.codeRevision]
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
                        row.candidate.status,
                        row.candidate.status === 'finished',
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
                        (match_id, artifact_id, created_import_run_id, candidate_id, provider_match_id, immutable_fingerprint)
                    VALUES ($1, $2, $3, $4, $5, $6)
                `,
                    [
                        matchId,
                        artifact.artifact_id,
                        runId,
                        row.candidate.id,
                        row.candidate.source_match_id,
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
        const client = await this.pool.connect();
        try {
            const targetIdentity = await this.inspectTarget(client);
            const binding = {
                service_identity: this.target.serviceIdentity,
                database_identity: targetIdentity.database_identity,
                schema_baseline: SCHEMA_BASELINE,
                artifact: {
                    sha256: input.sha256,
                    business_hash: input.artifact.business_hash,
                    identity_projection_hash: input.artifact.identity_projection_hash,
                    kind: input.artifact.kind,
                    candidate_count: input.candidates.length,
                    competition: input.artifact.competition,
                    seasons: input.artifact.seasons,
                },
            };
            const receipt = validateRuntimeAuthorization(input.runtimeAuthorization, binding);
            const provenance = validateProvenanceReceipt(input.provenanceReceipt, {
                sha256: input.sha256,
                target_classification: 'disposable',
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
                await client.query('SELECT public.m3_canonical_inventory_acquire_locks_v1()');
                const { artifact } = await this.ensureArtifacts(client, input);
                const classified = [];
                for (const candidate of input.candidates) {
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
                if (reconciled !== input.candidates.length) {
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
                    },
                    artifact_sha256: input.sha256,
                    candidate_count: input.candidates.length,
                    terminal_counts: terminalCounts,
                    database_delta: {
                        matches: terminalCounts.inserted || 0,
                        artifacts: changing.length > 0 ? 1 : 0,
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
    matchesCandidateExactly,
};
